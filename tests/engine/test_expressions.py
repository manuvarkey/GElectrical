"""core.expressions (M3, ADR 0011): safe expression evaluation."""

import glob
import json
import math
import os
import zipfile

import pytest

from gelectrical.core.expressions import (ExpressionError, Policy, compile_expression,
                                          evaluate, evaluate_numeric, format_template,
                                          parse_template)
from gelectrical.core.fields import FIELD_POLICY, FieldDict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE_JSON = sorted(glob.glob(os.path.join(ROOT, 'gelectrical', 'database', '**', '*.json'),
                                 recursive=True))
PROJECTS = sorted(glob.glob(os.path.join(ROOT, 'sample_files', '**', '*.gepro'), recursive=True)
                  + glob.glob(os.path.join(ROOT, 'tests', 'projects', '**', '*.gepro'), recursive=True))


def fields(**values):
    return FieldDict({key: {'value': value} for key, value in values.items()})


# -- language ---------------------------------------------------------------

@pytest.mark.parametrize('text, expected', [
    ('1 + 2*3', 7),
    ('2**10', 1024),
    ('7 // 2 + 7 % 2', 4),
    ('-3 + +1', -2),
    ('1/4', 0.25),
    ('1 < 2 <= 2 != 3', True),
    ('1 < 2 > 3', False),
    ('not 0', True),
    ('0 or 5', 5),
    ('3 and 0', 0),
    ('1 if 2 > 1 else 3', 1),
    ('max(1, 2, 3) + min([4, 5])', 7),
    ('abs(-2.5)', 2.5),
    ('(1, 2)[1]', 2),
    ('{0: 0.08, 0.1: 0.14}[0.1]', 0.14),
    ("'SP' not in ('SP', 'DP')", False),
    ('None is None', True),
    ("'%g' % (2.50)", '2.5'),
])
def test_language(text, expected):
    assert evaluate(text) == expected


def test_conditional_and_bool_ops_are_lazy():
    # The untaken branch would divide by zero
    assert evaluate('1 if d.t == 0 else 1/d.t', {'d': fields(t=0)}, FIELD_POLICY) == 1
    assert evaluate('d.t != 0 and 1/d.t', {'d': fields(t=0)}, FIELD_POLICY) is False
    assert evaluate('d.t == 0 or 1/d.t', {'d': fields(t=0)}, FIELD_POLICY) is True


def test_field_attributes():
    namespace = {'f': fields(In=100, st_on=True), 'd': fields(i_r=0.8)}
    assert evaluate('1.2*f.In*d.i_r', namespace, FIELD_POLICY) == pytest.approx(96)
    assert evaluate('f.st_on is True', namespace, FIELD_POLICY) is True
    with pytest.raises(ExpressionError, match='Unknown field'):
        evaluate('f.missing', namespace, FIELD_POLICY)
    # Real attributes of FieldDict are not reachable
    for name in ('store', 'keys', 'items', 'get'):
        with pytest.raises(ExpressionError):
            evaluate('f.%s' % name, namespace, FIELD_POLICY)


def test_names_and_errors():
    assert evaluate('x * 2', {'x': 4}) == 8
    with pytest.raises(ExpressionError, match='not defined'):
        evaluate('y')
    with pytest.raises(ExpressionError, match='ZeroDivisionError'):
        evaluate('1/0')
    with pytest.raises(ExpressionError, match='Invalid expression'):
        evaluate('1 +')
    with pytest.raises(ExpressionError, match='must be text'):
        evaluate(None)


def test_methods_need_a_registered_type():
    class Model:
        def contains(self, x):
            return x > 1

        def secret(self):
            raise AssertionError('must not be called')

    policy = Policy(methods={Model: ('contains',)})
    assert evaluate('m.contains(2)', {'m': Model()}, policy) is True
    with pytest.raises(ExpressionError, match='not allowed'):
        evaluate('m.secret()', {'m': Model()}, policy)
    # Without a method policy no method call is accepted at all
    with pytest.raises(ExpressionError, match='not allowed'):
        evaluate('m.contains(2)', {'m': Model()})


# -- rejected constructs ----------------------------------------------------

MALICIOUS = [
    "__import__('os').system('echo pwned')",
    "f.__class__",
    "f._FieldDict__x",
    "().__class__.__bases__[0].__subclasses__()",
    "(lambda: 1)()",
    "[x for x in (1, 2)]",
    "{x: 1 for x in (1, 2)}",
    "open('/etc/passwd').read()",
    "eval('1')",
    "exec('x=1')",
    "getattr(f, 'store')",
    "globals()",
    "f.In.__class__",
    "(1).real",
    "'abc'.upper()",
    "x[1:2]",
    "max(*[1, 2])",
    "dict(**{'a': 1})",
    "(x := 1)",
    "1j",
    "b'abc'",
    "f'{1}'",
    "...",
    "{1, 2}",
    "x.y()",
    "x[0](1)",
]


@pytest.mark.parametrize('text', MALICIOUS)
def test_malicious_expressions_are_rejected(text):
    namespace = {'f': fields(In=1), 'x': [1, 2, 3]}
    with pytest.raises(ExpressionError):
        evaluate(text, namespace, FIELD_POLICY)


def test_resource_limits():
    with pytest.raises(ExpressionError, match='too large'):
        evaluate('9**9**9')
    with pytest.raises(ExpressionError, match='too long'):
        evaluate("'a'*10**9")
    with pytest.raises(ExpressionError, match='too long'):
        evaluate("[0]*10**9")
    with pytest.raises(ExpressionError, match='longer than'):
        evaluate('1+' * 1500 + '1')
    with pytest.raises(ExpressionError, match='nested too deeply'):
        evaluate('-' * 100 + '1')
    with pytest.raises(ExpressionError, match='more than'):
        evaluate('[' + ','.join(['1'] * 450) + ']')
    # Float overflow is an evaluation error, not a crash
    with pytest.raises(ExpressionError, match='OverflowError'):
        evaluate('10.0**400')


def test_text_formatting_needs_literal_format():
    assert evaluate("'%g' % (x)", {'x': 1.5}) == '1.5'
    with pytest.raises(ExpressionError, match='literal format'):
        evaluate('s % (x)', {'s': '%s', 'x': 1})


# -- numeric entry ----------------------------------------------------------

@pytest.mark.parametrize('text, expected', [
    ('5', 5), (' 5 ', 5), ('2*(3.5+1)', 9.0), ('1e3/4', 250.0), ('-2', -2),
    ('abs(-2)', 2), ('max(1, 2)', 2), ('sqrt(16)', 4.0), ('True', True),
])
def test_numeric(text, expected):
    assert evaluate_numeric(text) == expected


@pytest.mark.parametrize('text', ['', '1,000', "'1'", 'x', 'f.In', '05', "__import__('os')",
                                  '[1]', 'int(2)', '1 if 1 else 2 == "a"'])
def test_numeric_rejects(text):
    with pytest.raises(ExpressionError):
        evaluate_numeric(text)


def test_field_validation_func_uses_numeric_subset():
    from gelectrical.core.fields import get_fields_from_params
    params = {'x': ['X', '', 1.0, None, '', (2, 0, 10)]}
    validate = get_fields_from_params(params)['x']['validation_func']
    assert validate('2*3.333') == 6.67
    assert validate('100') == 10
    assert validate("__import__('os').getcwd()") == 0


# -- label templates --------------------------------------------------------

def test_parse_template():
    assert parse_template("${'%g'%(In)}A, ${type}") == ((True, "'%g'%(In)"), (False, 'A, '),
                                                       (True, 'type'))
    assert parse_template('plain') == ((False, 'plain'),)
    assert parse_template("${ {'a': 1}['a'] }") == ((True, " {'a': 1}['a'] "),)
    assert parse_template("${'}'}x") == ((True, "'}'"), (False, 'x'))
    with pytest.raises(ExpressionError, match='Unterminated'):
        parse_template('${x')


@pytest.mark.parametrize('template, values, expected', [
    ("${'%g'%(In)}A, ${'%g'%(Isc)}kA", {'In': 63.0, 'Isc': 10}, '63A, 10kA'),
    ('${int(length_km*1000)}m', {'length_km': 0.1234}, '123m'),
    ('${-q_kvar}kVAr', {'q_kvar': -5.5}, '5.5kVAr'),
    ('${name}, ${ref}', {'name': 'Load <1>', 'ref': 'L1'}, 'Load <1>, L1'),
    ('${text}', {'text': '${evil}'}, '${evil}'),
    ('${flag}', {'flag': True}, 'True'),
    ('${value}', {'value': None}, 'None'),
])
def test_format_template(template, values, expected):
    assert format_template(template, values) == expected


def test_all_code_label_templates_parse():
    """Every label template of every registered element parses (D3)."""
    from gelectrical.model.project import ProjectModel
    from gelectrical.elementmodel import registry
    project = ProjectModel()
    count = 0
    for cls in registry._ELEMENT_CLASSES:
        try:
            element = cls(project_settings=project.fields)
        except TypeError:
            element = cls()
        for model in element.text_model or []:
            for is_expression, text in parse_template(model[1]):
                if is_expression:
                    compile_expression(text)
                    count += 1
    assert count > 50


# -- bundled and stored expressions ----------------------------------------

def _curve_expressions(data_struct, out):
    """Collect curve expressions of every protection data structure found
    anywhere in ``data_struct`` (nested dicts and lists)"""
    if isinstance(data_struct, list):
        for item in data_struct:
            _curve_expressions(item, out)
        return
    if not isinstance(data_struct, dict):
        return
    if {'type', 'parameters', 'data'} <= set(data_struct) and isinstance(data_struct['data'], dict):
        data = data_struct['data']
        out.update(data.get('select_expr_list', []))
        for key, curve in data.items():
            if key.startswith('curve'):
                for function, *args in curve:
                    if len(args) == 1 and isinstance(args[0], dict):
                        args = list(args[0].values())
                    out.update(arg for arg in args if isinstance(arg, str))
    for value in data_struct.values():
        _curve_expressions(value, out)


def _stored_expressions():
    expressions = set()
    for filename in DATABASE_JSON:
        with open(filename, encoding='utf-8') as fp:
            _curve_expressions(json.load(fp), expressions)
    for filename in PROJECTS:
        with zipfile.ZipFile(filename) as z:
            for name in z.namelist():
                if name.endswith('.json'):
                    _curve_expressions(json.loads(z.read(name)), expressions)
    return sorted(expressions)


STORED = _stored_expressions()


def test_inventory_is_not_empty():
    assert len(STORED) > 400


class _AnyFields(FieldDict):
    """Field dictionary returning a test value for every field name"""

    def __init__(self, values):
        super().__init__({})
        self.values = values

    def __getitem__(self, key):
        return self.values.get(key, 2.0)

    __getattr__ = __getitem__


def _any_field_attribute(obj, name):
    return obj[name]


def test_stored_expressions_match_python_eval():
    """Every curve expression in the bundled databases and in the sample and
    test projects parses under the whitelist and evaluates to the same value
    as Python ``eval`` did (oracle on trusted, bundled data only)."""
    policy = FIELD_POLICY.extend(attributes={_AnyFields: _any_field_attribute})
    for flags in (True, False):
        f = _AnyFields({'In': 100.0, 'Isc': 25.0, 'In_set': 1.0})
        d = _AnyFields({'lt_on': flags, 'st_on': flags, 'i2t_on': flags, 'i_i_on': flags,
                        'trip_on': flags, 't_m': 0.1})
        namespace = {'f': f, 'd': d}
        for text in STORED:
            compile_expression(text, FIELD_POLICY)
            try:
                expected = eval(text, dict(namespace))  # noqa: S307 - test oracle
            except Exception:
                expected = 'error'
            try:
                actual = evaluate(text, namespace, policy)
            except ExpressionError:
                actual = 'error'
            if isinstance(expected, float) and isinstance(actual, float):
                assert actual == expected or (math.isnan(actual) and math.isnan(expected)), text
            else:
                assert actual == expected, text
