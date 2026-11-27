# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Program settings storage (same file and format as the legacy GTK app:
``settings.ini`` with truncated field dictionaries in the user data
directory) and the user equipment library folder.

``GELECTRICAL_USER_DATA_DIR`` overrides the user data directory (tests,
portable installs). Font and theme settings are stored but not yet applied
to rendering (A11, milestone M11).
"""

import copy
import json
import logging
import os

from gelectrical.core import constants, paths
from gelectrical.core.fields import new_program_settings, update_fields_dict, get_fields_dict_trunc

from ..dto import fields_schema, field_values
from ..protocol import ServiceError, FILE_ERROR, invalid
from ..registry import runtime_method
from .common import validate_field_value

log = logging.getLogger(__name__)


def default_user_data_dir():
    override = os.environ.get('GELECTRICAL_USER_DATA_DIR')
    if override:
        return override
    import appdirs
    dirs = appdirs.AppDirs(constants.PROGRAM_NAME, constants.PROGRAM_AUTHOR, version=constants.PROGRAM_VER)
    return dirs.user_data_dir


class SettingsStore:
    """Program settings of one backend process"""

    def __init__(self, data_dir=None, persist=True):
        self.data_dir = data_dir or default_user_data_dir()
        self.persist = persist
        self.filename = os.path.join(self.data_dir, 'settings.ini')
        self.library_dir = os.path.join(self.data_dir, 'database')
        self.values = new_program_settings()
        if persist:
            self._load()
        self.values['Paths']['library_path']['value'] = self.library_dir
        paths.set_user_library_dir(self.library_dir)

    def _load(self):
        try:
            os.makedirs(self.library_dir, exist_ok=True)
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as fp:
                    stored = json.load(fp)
                self.values = update_fields_dict(new_program_settings(), stored)
                log.info('SettingsStore - load - program settings opened at ' + self.filename)
            else:
                self.save()
        except Exception:
            # Same fallback as the legacy app
            log.exception('SettingsStore - load - falling back on default values')
            self.values = new_program_settings()

    def save(self):
        if not self.persist:
            return
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            temp = self.filename + '.tmp'
            with open(temp, 'w', encoding='utf-8') as fp:
                json.dump(get_fields_dict_trunc(self.values), fp, indent=4)
            os.replace(temp, self.filename)
        except OSError as exc:
            raise ServiceError(FILE_ERROR, 'Program settings could not be saved: %s' % exc) from None

    def update(self, values):
        """Validate ``{page: {code: value}}`` completely, then apply and save"""
        if not isinstance(values, dict) or not values:
            raise invalid('Expected an object of setting pages', field='values')
        updated = copy.deepcopy(self.values)
        for page, page_values in values.items():
            if page not in updated or not isinstance(page_values, dict):
                raise invalid('Unknown settings page %r' % page, field='values')
            for code, value in page_values.items():
                updated[page][code]['value'] = validate_field_value(updated[page], code, value,
                                                                    field_name='values.' + page)
        for page in updated:
            for code in updated[page]:
                self.values[page][code]['value'] = updated[page][code]['value']
        self.save()


@runtime_method('settings.get')
def get(ctx):
    """Program settings pages with field schemas and values"""
    store = ctx.runtime.settings
    return {'pages': {page: {'fields': fields_schema(fields), 'values': field_values(fields)}
                      for page, fields in store.values.items()},
            'library_dir': store.library_dir}


@runtime_method('settings.set')
def set_settings(ctx, values):
    """Change program settings (``{page: {code: value}}``; not undoable, like the legacy dialog)"""
    ctx.runtime.settings.update(values)
    return get(ctx)
