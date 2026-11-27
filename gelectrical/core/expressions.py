#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# expressions
#
#  Copyright 2026 Manu Varkey <manuvarkey@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

"""Safe expression evaluation (ADR 0011, milestone M3).

Expressions stored in databases and project files (protection curves),
rules-check expressions, numeric field entry and symbol label templates are
evaluated here instead of with Python ``eval``.

The evaluator walks a validated Python AST. Only these constructs are
accepted:

- literals: numbers, strings, booleans, ``None``, tuples, lists and dicts;
- names supplied in the namespace of the call;
- attribute access on objects whose type has a registered *attribute
  resolver* (for example ``FieldDict``: ``f.In``);
- arithmetic, comparisons, boolean operators and conditional expressions;
- subscripts on tuples, lists, dicts and strings (no slices);
- calls to whitelisted functions (``max(...)``) and to whitelisted methods of
  registered types (``model.contains(...)``).

Names and attributes that start with ``_`` are rejected, as are imports,
lambdas, comprehensions, starred arguments, slices and any other node type.
Size, depth and the cost of powers and sequence repetition are bounded.
Every failure raises :class:`ExpressionError`; use of a construct outside
the whitelist or beyond the limits raises its subclass
:class:`ExpressionNotAllowed`. Nothing is executed or silently replaced.

The module has no project imports so that any engine module can use it.
"""

import ast
import functools
import math
import operator

__all__ = ['ExpressionError', 'ExpressionNotAllowed', 'Policy', 'compile_expression', 'evaluate',
           'evaluate_numeric', 'format_template', 'parse_template',
           'NUMERIC_POLICY', 'DEFAULT_FUNCTIONS']

# Limits
MAX_LENGTH = 2000        # characters of one expression
MAX_NODES = 400          # AST nodes of one expression
MAX_DEPTH = 40           # AST nesting depth
MAX_SEQUENCE = 10000     # length of a sequence built by repetition
MAX_POWER_BITS = 100000  # bits of an integer power result


class ExpressionError(ValueError):
    """An expression is not allowed or failed to evaluate"""

    def __init__(self, message, expression=None):
        self.expression = expression
        if expression is not None:
            message = '%s (expression %r)' % (message, _shorten(expression))
        super().__init__(message)


class ExpressionNotAllowed(ExpressionError):
    """An expression uses a construct outside the whitelist (a possible
    code injection). Callers report it instead of skipping the value."""


def _shorten(text, length=120):
    text = str(text)
    return text if len(text) <= length else text[:length] + '...'


# Functions available to curve, rules and label expressions. These match the
# Python builtins that the stored expressions use (``max``, ``min``) plus a
# few side-effect free numeric helpers.
DEFAULT_FUNCTIONS = {'abs': abs,
                     'min': min,
                     'max': max,
                     'round': round,
                     'int': int,
                     'float': float,
                     'bool': bool,
                     'str': str,
                     'len': len,
                     'sum': sum,
                     'sqrt': math.sqrt,
                     'log10': math.log10,
                     }

NUMERIC_FUNCTIONS = {'abs': abs,
                     'min': min,
                     'max': max,
                     'round': round,
                     'sqrt': math.sqrt,
                     }


class Policy:
    """What an expression may use besides literals and operators.

    functions:  name -> callable, callable by name
    attributes: type -> resolver(obj, name) returning the attribute value or
                raising ``ExpressionError``; ``obj.name`` is allowed only for
                objects of these types (subclasses included)
    methods:    type -> set of method names callable as ``obj.name(...)``
    names:      allow namespace names (``False`` for pure numeric input)
    strings:    allow string literals
    containers: allow tuple, list and dict literals and subscripts
    """

    def __init__(self, functions=None, attributes=None, methods=None,
                 names=True, strings=True, containers=True):
        self.functions = dict(DEFAULT_FUNCTIONS if functions is None else functions)
        self.attributes = dict(attributes or {})
        self.methods = {key: frozenset(value) for key, value in (methods or {}).items()}
        self.names = names
        self.strings = strings
        self.containers = containers

    def extend(self, functions=None, attributes=None, methods=None):
        """New policy with additional functions, resolvers and methods"""
        new = Policy(self.functions, self.attributes, self.methods,
                     self.names, self.strings, self.containers)
        new.functions.update(functions or {})
        new.attributes.update(attributes or {})
        for key, value in (methods or {}).items():
            new.methods[key] = frozenset(new.methods.get(key, frozenset()) | set(value))
        return new

    def resolver(self, obj):
        for cls in type(obj).__mro__:
            if cls in self.attributes:
                return self.attributes[cls]
        return None

    def allowed_methods(self, obj):
        allowed = set()
        for cls in type(obj).__mro__:
            allowed |= self.methods.get(cls, frozenset())
        return allowed


NUMERIC_POLICY = Policy(functions=NUMERIC_FUNCTIONS, names=False,
                        strings=False, containers=False)


# Validation

_BIN_OPS = {ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow}

_UNARY_OPS = {ast.UAdd: operator.pos,
              ast.USub: operator.neg,
              ast.Not: operator.not_}

_CMP_OPS = {ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
            ast.Is: operator.is_,
            ast.IsNot: operator.is_not,
            ast.In: lambda a, b: a in b,
            ast.NotIn: lambda a, b: a not in b}

_CONSTANT_TYPES = (bool, int, float, str, type(None))


def _validate(node, policy, text, depth=0):
    """Check that ``node`` only uses allowed constructs; returns node count"""
    if depth > MAX_DEPTH:
        raise ExpressionNotAllowed('Expression is nested too deeply', text)
    count = 1
    kind = type(node)

    def child(sub):
        return _validate(sub, policy, text, depth + 1)

    if kind is ast.Constant:
        if not isinstance(node.value, _CONSTANT_TYPES):
            raise ExpressionNotAllowed('Literal of type %s is not allowed' % type(node.value).__name__, text)
        if isinstance(node.value, str) and not policy.strings:
            raise ExpressionNotAllowed('Text is not allowed in a numeric expression', text)
    elif kind is ast.Name:
        if node.id.startswith('_'):
            raise ExpressionNotAllowed('Name %r is not allowed' % node.id, text)
        if not policy.names and node.id not in policy.functions:
            raise ExpressionNotAllowed('Name %r is not allowed in a numeric expression' % node.id, text)
    elif kind is ast.Attribute:
        if node.attr.startswith('_') or not policy.attributes:
            raise ExpressionNotAllowed('Attribute %r is not allowed' % node.attr, text)
        count += child(node.value)
    elif kind in (ast.Tuple, ast.List):
        if not policy.containers:
            raise ExpressionNotAllowed('Sequences are not allowed in a numeric expression', text)
        for elt in node.elts:
            if isinstance(elt, ast.Starred):
                raise ExpressionNotAllowed('Starred expressions are not allowed', text)
            count += child(elt)
    elif kind is ast.Dict:
        if not policy.containers:
            raise ExpressionNotAllowed('Dictionaries are not allowed in a numeric expression', text)
        for key, value in zip(node.keys, node.values):
            if key is None:
                raise ExpressionNotAllowed('Dictionary unpacking is not allowed', text)
            count += child(key) + child(value)
    elif kind is ast.Subscript:
        if not policy.containers:
            raise ExpressionNotAllowed('Subscripts are not allowed in a numeric expression', text)
        if isinstance(node.slice, ast.Slice):
            raise ExpressionNotAllowed('Slices are not allowed', text)
        count += child(node.value) + child(node.slice)
    elif kind is ast.BinOp:
        if type(node.op) not in _BIN_OPS:
            raise ExpressionNotAllowed('Operator %s is not allowed' % type(node.op).__name__, text)
        count += child(node.left) + child(node.right)
    elif kind is ast.UnaryOp:
        if type(node.op) not in _UNARY_OPS:
            raise ExpressionNotAllowed('Operator %s is not allowed' % type(node.op).__name__, text)
        count += child(node.operand)
    elif kind is ast.BoolOp:
        for value in node.values:
            count += child(value)
    elif kind is ast.Compare:
        for op in node.ops:
            if type(op) not in _CMP_OPS:
                raise ExpressionNotAllowed('Comparison %s is not allowed' % type(op).__name__, text)
        count += child(node.left)
        for comparator in node.comparators:
            count += child(comparator)
    elif kind is ast.IfExp:
        count += child(node.test) + child(node.body) + child(node.orelse)
    elif kind is ast.Call:
        func = node.func
        if isinstance(func, ast.Name):
            if func.id not in policy.functions:
                raise ExpressionNotAllowed('Function %r is not allowed' % func.id, text)
        elif isinstance(func, ast.Attribute):
            if func.attr.startswith('_') or not policy.methods:
                raise ExpressionNotAllowed('Method %r is not allowed' % func.attr, text)
            count += child(func.value)
        else:
            raise ExpressionNotAllowed('Only named functions can be called', text)
        for arg in node.args:
            if isinstance(arg, ast.Starred):
                raise ExpressionNotAllowed('Starred arguments are not allowed', text)
            count += child(arg)
        for keyword in node.keywords:
            if keyword.arg is None or keyword.arg.startswith('_'):
                raise ExpressionNotAllowed('Keyword unpacking is not allowed', text)
            count += child(keyword.value)
    else:
        raise ExpressionNotAllowed('%s is not allowed' % kind.__name__, text)
    return count


def _policy_key(policy):
    return (policy.names, policy.strings, policy.containers,
            bool(policy.attributes), bool(policy.methods),
            frozenset(policy.functions))


@functools.lru_cache(maxsize=8192)
def _compile(text, key):
    names, strings, containers, attributes, methods, functions = key
    policy = Policy(functions={name: None for name in functions},
                    attributes={object: None} if attributes else None,
                    methods={object: ()} if methods else None,
                    names=names, strings=strings, containers=containers)
    if len(text) > MAX_LENGTH:
        raise ExpressionNotAllowed('Expression is longer than %d characters' % MAX_LENGTH, text)
    try:
        tree = ast.parse(text.strip(), mode='eval')
    except (SyntaxError, ValueError) as e:
        raise ExpressionError('Invalid expression: %s' % getattr(e, 'msg', e), text) from None
    if _validate(tree.body, policy, text) > MAX_NODES:
        raise ExpressionNotAllowed('Expression has more than %d elements' % MAX_NODES, text)
    return tree.body


def compile_expression(text, policy=None):
    """Parse and validate ``text``; returns the AST body. Cached."""
    if not isinstance(text, str):
        raise ExpressionError('Expression must be text, not %s' % type(text).__name__)
    policy = policy or Policy()
    return _compile(text, _policy_key(policy))


# Evaluation

class _Evaluator:

    def __init__(self, namespace, policy, text):
        self.namespace = namespace
        self.policy = policy
        self.text = text

    def error(self, message):
        return ExpressionError(message, self.text)

    def not_allowed(self, message):
        return ExpressionNotAllowed(message, self.text)

    def eval(self, node):
        method = getattr(self, 'eval_' + type(node).__name__)
        return method(node)

    def eval_Constant(self, node):
        return node.value

    def eval_Name(self, node):
        if node.id in self.namespace:
            return self.namespace[node.id]
        raise self.error('Name %r is not defined' % node.id)

    def eval_Attribute(self, node):
        obj = self.eval(node.value)
        resolver = self.policy.resolver(obj)
        if resolver is None:
            raise self.not_allowed('Attribute %r of %s is not allowed' % (node.attr, type(obj).__name__))
        return resolver(obj, node.attr)

    def eval_Tuple(self, node):
        return tuple(self.eval(elt) for elt in node.elts)

    def eval_List(self, node):
        return [self.eval(elt) for elt in node.elts]

    def eval_Dict(self, node):
        return {self.eval(key): self.eval(value) for key, value in zip(node.keys, node.values)}

    def eval_Subscript(self, node):
        obj = self.eval(node.value)
        index = self.eval(node.slice)
        if not isinstance(obj, (tuple, list, dict, str)):
            raise self.not_allowed('Subscript of %s is not allowed' % type(obj).__name__)
        try:
            return obj[index]
        except (KeyError, IndexError, TypeError) as e:
            raise self.error('Subscript failed: %s' % e) from None

    def eval_BinOp(self, node):
        left = self.eval(node.left)
        right = self.eval(node.right)
        op = type(node.op)
        if op is ast.Mod and isinstance(left, str):
            # Text formatting ('%g' % x) only with a literal format string
            if not isinstance(node.left, ast.Constant):
                raise self.not_allowed('Text formatting needs a literal format string')
        elif op is ast.Pow:
            self.check_power(left, right)
        elif op is ast.Mult:
            self.check_repeat(left, right)
            self.check_repeat(right, left)
        return self.apply(_BIN_OPS[op], left, right)

    def check_power(self, base, exponent):
        if (isinstance(base, int) and isinstance(exponent, int)
                and not isinstance(base, bool) and exponent > 0):
            if max(base.bit_length(), 1) * exponent > MAX_POWER_BITS:
                raise self.not_allowed('Power result is too large')

    def check_repeat(self, seq, count):
        if isinstance(seq, (str, list, tuple)) and isinstance(count, int):
            if len(seq) * count > MAX_SEQUENCE:
                raise self.not_allowed('Repeated sequence is too long')

    def apply(self, func, *args):
        try:
            return func(*args)
        except ExpressionError:
            raise
        except Exception as e:
            raise self.error('%s: %s' % (type(e).__name__, e)) from None

    def eval_UnaryOp(self, node):
        return self.apply(_UNARY_OPS[type(node.op)], self.eval(node.operand))

    def eval_BoolOp(self, node):
        # Python semantics: short circuit, the deciding operand is returned
        if isinstance(node.op, ast.And):
            value = True
            for sub in node.values:
                value = self.eval(sub)
                if not value:
                    return value
            return value
        else:
            value = False
            for sub in node.values:
                value = self.eval(sub)
                if value:
                    return value
            return value

    def eval_Compare(self, node):
        left = self.eval(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self.eval(comparator)
            if not self.apply(_CMP_OPS[type(op)], left, right):
                return False
            left = right
        return True

    def eval_IfExp(self, node):
        return self.eval(node.body) if self.eval(node.test) else self.eval(node.orelse)

    def eval_Call(self, node):
        func = node.func
        if isinstance(func, ast.Name):
            target = self.policy.functions.get(func.id)
            if target is None:
                raise self.not_allowed('Function %r is not allowed' % func.id)
        else:
            obj = self.eval(func.value)
            if func.attr not in self.policy.allowed_methods(obj):
                raise self.not_allowed('Method %r of %s is not allowed' % (func.attr, type(obj).__name__))
            target = getattr(obj, func.attr)
        args = [self.eval(arg) for arg in node.args]
        kwargs = {keyword.arg: self.eval(keyword.value) for keyword in node.keywords}
        return self.apply(lambda: target(*args, **kwargs))


def evaluate(text, namespace=None, policy=None):
    """Evaluate expression ``text`` with names from ``namespace``.

    Raises :class:`ExpressionError` when the expression is not allowed or
    fails to evaluate."""
    policy = policy or Policy()
    tree = compile_expression(text, policy)
    return _Evaluator(namespace or {}, policy, text).eval(tree)


def evaluate_numeric(text):
    """Evaluate numeric user input such as ``'2*(3.5+1)'`` or ``'1e3/3'``.

    Only numbers, arithmetic and ``abs``, ``min``, ``max``, ``round`` and
    ``sqrt`` are accepted. Returns an int, float or bool (as Python ``eval``
    of the same text did)."""
    if not isinstance(text, str):
        text = str(text)
    value = evaluate(text, None, NUMERIC_POLICY)
    if not isinstance(value, (int, float)):
        raise ExpressionError('Result is not a number', text)
    return value


# Label templates: literal text with ${expression} fields

@functools.lru_cache(maxsize=4096)
def parse_template(template):
    """Split ``template`` into a tuple of ``(is_expression, text)`` parts.

    ``${...}`` delimits an expression; braces inside string literals and
    nested braces are matched."""
    parts = []
    pos = 0
    length = len(template)
    while pos < length:
        start = template.find('${', pos)
        if start < 0:
            parts.append((False, template[pos:]))
            break
        if start > pos:
            parts.append((False, template[pos:start]))
        index = start + 2
        depth = 0
        quote = None
        while index < length:
            char = template[index]
            if quote:
                if char == '\\':
                    index += 1
                elif char == quote:
                    quote = None
            elif char in ('"', "'"):
                quote = char
            elif char == '{':
                depth += 1
            elif char == '}':
                if depth == 0:
                    break
                depth -= 1
            index += 1
        else:
            raise ExpressionError('Unterminated ${ in template', template)
        parts.append((True, template[start + 2:index]))
        pos = index + 1
    return tuple(parts)


def format_template(template, namespace, policy=None):
    """Render ``template`` replacing each ``${expression}`` by ``str`` of
    its value (the behaviour of the former Mako templates)."""
    output = []
    for is_expression, text in parse_template(template):
        if is_expression:
            output.append(str(evaluate(text, namespace, policy)))
        else:
            output.append(text)
    return ''.join(output)
