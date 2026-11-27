# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Undo and redo (snapshot history, ADR 0009)"""

from ..registry import query, session_method


@query('history.state')
def state(ctx):
    """Undo/redo availability and labels"""
    return ctx.session.history.state()


@session_method('history.undo')
def undo(ctx):
    """Undo the last command (one entry per command)"""
    return ctx.session.undo(source=ctx.source).to_dict()


@session_method('history.redo')
def redo(ctx):
    """Redo the last undone command"""
    return ctx.session.redo(source=ctx.source).to_dict()
