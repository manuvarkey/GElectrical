# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Project service: new, open, save, state and project settings"""

import copy
import logging
import os

from gelectrical import persistence
from gelectrical.core.expressions import ExpressionNotAllowed
from gelectrical.core.fields import apply_alter_values

from .. import document
from ..dto import fields_schema, field_values
from ..protocol import ServiceError, FILE_ERROR, VALIDATION_ERROR, invalid, validation
from ..registry import query, command, session_method
from .common import require_str, validate_field_value

log = logging.getLogger(__name__)


def _check_path(path, field='path', must_exist=False):
    require_str(path, field, allow_empty=False, max_length=4096)
    if '\x00' in path:
        raise invalid('Invalid path', field=field)
    path = os.path.abspath(path)
    if must_exist and not os.path.isfile(path):
        raise ServiceError(FILE_ERROR, 'File not found: ' + path, field=field)
    return path


@query('project.state')
def state(ctx):
    """Session state: path, revision, dirty flag, history, sheets, analysis"""
    return ctx.session.state()


@session_method('project.new')
def new(ctx):
    """Replace the document with a new project (history cleared, not undoable)"""
    ctx.session.reset_document()
    return ctx.session.state()


@session_method('project.open')
def open_project(ctx, path):
    """Open a ``.gepro`` file into this session (history cleared)"""
    path = _check_path(path, must_exist=True)
    try:
        document_data, pages = persistence.read_gepro(path)
    except persistence.ProjectFileError as exc:
        message = str(exc)
        if 'Wrong file type' in message:
            message = 'Project could not be opened: Wrong file type selected'
        else:
            message = 'Project could not be opened: Error opening file'
            log.warning('project.open - %s - %s', path, exc)
        raise ServiceError(FILE_ERROR, message, field='path') from None

    def loader(project):
        if project.set_model(document_data, pages) is False:
            raise ServiceError(FILE_ERROR, 'Project could not be opened: Project data incomplete', field='path')
        document.apply_file_uids(project, pages)

    try:
        ctx.session.reset_document(loader, path=path)
    except ServiceError:
        raise
    except ExpressionNotAllowed as exc:
        raise ServiceError(FILE_ERROR, 'Project could not be opened: unsupported expression - ' + str(exc),
                           field='path') from None
    except Exception:
        log.exception('project.open - error parsing project file - ' + path)
        raise ServiceError(FILE_ERROR, 'Project could not be opened: Error opening file', field='path') from None
    log.info('project.open - Project opened - ' + path)
    return ctx.session.state()


def _save(session, path):
    settings, pages = document.storage_model(session.project)
    try:
        persistence.write_gepro(path, settings, pages, atomic=True, backup=True,
                                app=document.APP_PROVENANCE)
    except persistence.ProjectFileError as exc:
        raise ServiceError(FILE_ERROR, 'Project could not be saved: ' + str(exc), field='path') from None
    session.mark_saved(path)
    session.emit({'event': 'changed', 'session': session.id, 'revision': session.revision,
                  'changes': [{'kind': 'saved'}], 'source': 'desktop', 'dirty': session.dirty})
    log.info('project.save - Project saved - ' + path)
    return session.state()


@session_method('project.save')
def save(ctx):
    """Save to the current file (atomic, previous file kept as ``.bak``)"""
    if not ctx.session.path:
        raise ServiceError(VALIDATION_ERROR, 'Project has no file name; use project.save_as', field='path')
    return _save(ctx.session, ctx.session.path)


@session_method('project.save_as')
def save_as(ctx, path):
    """Save to a new file (``.gepro`` added when missing)"""
    path = _check_path(path)
    if not path.endswith('.gepro'):
        path += '.gepro'
    if not os.path.isdir(os.path.dirname(path)):
        raise ServiceError(FILE_ERROR, 'Folder does not exist', field='path')
    return _save(ctx.session, path)


@query('project.settings')
def settings(ctx):
    """Project settings pages (Information, Simulation, Reports, Rules Check)"""
    fields = ctx.project.get_project_fields(full=True)
    return {'pages': {page: {'fields': fields_schema(page_fields), 'values': field_values(page_fields)}
                      for page, page_fields in fields.items()}}


@command('project.set_settings', label='Update project settings')
def set_settings(ctx, values):
    """Change project settings (``{page: {code: value}}``), one undo entry"""
    if not isinstance(values, dict) or not values:
        raise invalid('Expected an object of setting pages', field='values')
    project = ctx.project
    new_fields = copy.deepcopy(project.get_project_fields(full=True))
    for page, page_values in values.items():
        if page not in new_fields or not isinstance(page_values, dict) or not page_values:
            raise validation('Unknown settings page %r' % page, field='values')
        for code, value in page_values.items():
            new_fields[page][code]['value'] = validate_field_value(new_fields[page], code, value,
                                                                   field_name='values.' + page)
            if new_fields[page][code].get('alter_structure'):
                apply_alter_values(new_fields[page], code)
    project.update_project_fields(new_fields)
    return settings(ctx)
