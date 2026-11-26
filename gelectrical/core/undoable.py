#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# undoable
#
#  Copyright 2014 Manu Varkey <manuvarkey@gmail.com>
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

"""Undoable actions for the legacy undo stack (``gelectrical.undo.Stack``).

``@undoable`` generators append to ``args[0].stack``; ``group(self, desc)``
collects the actions of a block into one undo entry. No GUI imports."""

class _Action:
    ''' This represents an action which can be done and undone.
    
    It is the result of a call on an undoable function and has
    three methods: ``do()``, ``undo()`` and ``text()``.  The first value
    returned by the internal call in ``do()`` is the value which will 
    subsequently be returned by ``text``.  Any remaining values are 
    returned by ``do()``.
    '''

    def __init__(self, generator, args, kwargs):
        self._generator = generator
        self.args = args
        self.kwargs = kwargs
        self._text = ''

    def do(self):
        'Do or redo the action'
        self._runner = self._generator(*self.args, **self.kwargs)
        rets = next(self._runner)
        if isinstance(rets, tuple):
            self._text = rets[0]
            return rets[1:]
        elif rets is None:
            self._text = ''
            return None
        else:
            self._text = rets
            return None

    def undo(self):
        'Undo the action'
        try:
            next(self._runner)
        except StopIteration:
            pass
        # Delete it so that its not accidentally called again
        del self._runner

    def text(self):
        'Return the descriptive text of the action'
        return self._text

def undoable(generator):
    ''' Decorator which creates a new undoable action type. 
    
    This decorator should be used on a generator of the following format::
    
        @undoable
        def operation(*args):
            do_operation_code
            yield 'descriptive text'
            undo_operator_code
    '''

    def inner(*args, **kwargs):
        action = _Action(generator, args, kwargs)
        ret = action.do()
        args[0].stack.append(action)
        if isinstance(ret, tuple):
            if len(ret) == 1:
                return ret[0]
            elif len(ret) == 0:
                return None
        return ret

    return inner
    
class _Group:
    ''' A undoable group context manager. '''

    def __init__(self, desc, stack):
        self._desc = desc
        self._stack = []
        self.stack = stack

    def __enter__(self):
        self.stack.setreceiver(self._stack)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.stack.resetreceiver()
            self.stack.append(self)
        return False

    def undo(self):
        for undoable in reversed(self._stack):
            undoable.undo()

    def do(self):
        for undoable in self._stack:
            undoable.do()

    def text(self):
        return self._desc.format(count=len(self._stack))

def group(self, desc):
    ''' Return a context manager for grouping undoable actions. 
    
    All actions which occur within the group will be undone by a single call
    of `stack.undo
    '''
    return _Group(desc, self.stack)

def get_undoable_set_field(stack, refresh, element):
    # Special class implementing undo for set text function
    class UndoableSetTextValue:
        def __init__(self, stack, refresh):
            self.stack = stack
            self.refresh = refresh
    
        @undoable
        def set_text_field_value_undo(self, code, value):
            oldval = element.get_text_field(code)['value']
            modified = element.set_text_field_value(code, value)
            if self.refresh:
                self.refresh() 
            yield "Modify '{}' field  of '{}' element".format(code, element.name)
            # Undo action
            element.set_text_field_value(code, oldval)
            if modified:
                for code, value in modified.items():
                    element.set_text_field_value(code, value)
            if self.refresh:
                self.refresh() 
    return UndoableSetTextValue(stack, refresh).set_text_field_value_undo


def get_undoable_set_field_multiple(stack, refresh, elements, multiselect_fields):
    # Special class implementing undo for set text function
    class UndoableSetTextValue:
        def __init__(self, stack, refresh):
            self.stack = stack
            self.refresh = refresh
    
        @undoable
        def set_text_field_value_undo(self, code, value):
            oldvals = []
            for element in elements:
                oldval = element.get_text_field(code)['value']
                element.set_text_field_value(code, value)
                oldvals.append(oldval)
            multiselect_fields[code]['value'] = value
            if self.refresh:
                self.refresh() 
            yield "Modify '{}' field  of '{}' (multiple) elements".format(code, elements[0].name)
            # Undo action
            for oldval, element in zip(oldvals, elements):
                element.set_text_field_value(code, oldval)
            if self.refresh:
                self.refresh() 
    return UndoableSetTextValue(stack, refresh).set_text_field_value_undo
    
