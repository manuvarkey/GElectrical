# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Equipment library: catalogue of an element's database, item values and
applying an item to the element (legacy *Load values from database*)"""

import os

from gelectrical.core.database import load_database, validate_database_item
from gelectrical.core.undoable import get_undoable_set_field, group

from ..protocol import ServiceError, FILE_ERROR, not_found, validation
from ..registry import query, command
from .common import find_element, require_str


def _database(ctx, uid):
    page, index, drawing_model, element = find_element(ctx.project, uid)
    path = getattr(element, 'database_path', None)
    if not path:
        raise not_found('Element has no equipment database', field='uid')
    try:
        return element, path, load_database(path)
    except (OSError, KeyError, ValueError) as exc:
        raise ServiceError(FILE_ERROR, 'Equipment database could not be read: %s' % exc) from None


def _item(data, category, item):
    require_str(category, 'category', allow_empty=False, max_length=1000)
    require_str(item, 'item', allow_empty=False, max_length=1000)
    try:
        return data[category][item]
    except KeyError:
        raise not_found('Unknown database item', field='item') from None


@query('library.catalogue')
def catalogue(ctx, uid, search=''):
    """Categories and item names of the element's database (optional case-insensitive search)"""
    element, path, data = _database(ctx, uid)
    require_str(search, 'search', max_length=1000)
    key = search.lower()
    categories = []
    for category, items in data.items():
        names = [name for name in items if not key or key in name.lower() or key in category.lower()]
        if names:
            categories.append({'category': category, 'items': names})
    return {'database': os.path.basename(path), 'categories': categories}


@query('library.item')
def item(ctx, uid, category, item):
    """Text values of one database item"""
    element, path, data = _database(ctx, uid)
    return {'category': category, 'item': item, 'values': dict(_item(data, category, item))}


@command('library.apply', label='Update data from database')
def apply(ctx, uid, category, item):
    """Load the values of a database item into the element (one undo entry)"""
    element, path, data = _database(ctx, uid)
    values = _item(data, category, item)
    try:
        validated = validate_database_item(element.fields, values, path)
    except KeyError as exc:
        raise validation('Database column %s is not a field of the element' % exc, field='item') from None
    setter = get_undoable_set_field(ctx.session.stack, None, element)
    with group(ctx.session, 'Update data from database'):
        for code, value in validated.items():
            setter(code, value)
    return {'uid': uid, 'fields': sorted(validated)}
