# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Session management and runtime information"""

from gelectrical import __version__

from .. import registry
from ..protocol import EVENTS, ERROR_CODES, MAX_LINE_LENGTH, MAX_ID_LENGTH
from ..registry import runtime_method


@runtime_method('runtime.info')
def info(ctx):
    """Backend version, limits, events and the method list"""
    return {'name': 'GElectrical backend', 'version': __version__,
            'protocol': 1,
            'limits': {'line_length': MAX_LINE_LENGTH, 'id_length': MAX_ID_LENGTH},
            'events': list(EVENTS), 'error_codes': list(ERROR_CODES),
            'methods': sorted(registry.METHODS)}


@runtime_method('session.list')
def list_sessions(ctx):
    """Open document sessions and the active one"""
    runtime = ctx.runtime
    return {'sessions': [runtime.sessions[s].state() for s in runtime.sessions], 'active': runtime.active}


@runtime_method('session.create')
def create(ctx, session=None):
    """Open a new document session with a new project"""
    created = ctx.runtime.create_session(session)
    return created.state()


@runtime_method('session.activate')
def activate(ctx, session):
    """Mark the session the desktop shows (MCP acts on it)"""
    target = ctx.runtime.get_session(session)
    ctx.runtime.active = target.id
    return {'active': target.id}


@runtime_method('session.close')
def close(ctx, session):
    """Close a document session (unsaved changes are discarded)"""
    return ctx.runtime.close_session(session)
