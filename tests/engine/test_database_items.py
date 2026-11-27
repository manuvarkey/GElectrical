"""Equipment library helpers moved from the GTK database dialog (M4):
every item of every bundled library converts to field values of its element
without errors, and file references resolve."""

import pytest

import gelectrical.model.project  # noqa: F401  (import order: elementmodel first is circular)
from gelectrical.core.database import load_database, validate_database_item
from gelectrical.core.fields import new_project_settings
from gelectrical.elementmodel import registry


def _elements_with_database():
    out = []
    for code, cls in registry.ELEMENT_MODELS.items():
        element = cls(project_settings=new_project_settings())
        if getattr(element, 'database_path', None):
            out.append((code, element))
    return out


ELEMENTS = _elements_with_database()


def test_some_elements_have_libraries():
    assert {'element_line', 'element_line_cable'} <= {code for code, _ in ELEMENTS}


@pytest.mark.parametrize('code, element', ELEMENTS, ids=[code for code, _ in ELEMENTS])
def test_library_items_validate(code, element):
    data = load_database(element.database_path)
    assert data
    for category, items in data.items():
        for name, item in items.items():
            values = validate_database_item(element.fields, item, element.database_path)
            assert set(values) == set(item)
            for field_code, value in values.items():
                field_type = element.fields[field_code]['type']
                if field_type in ('graph', 'data') and item[field_code]:
                    assert value is not None, (category, name, field_code)
                elif field_type == 'float':
                    assert isinstance(value, float) or value == 0
                elif field_type == 'int':
                    assert isinstance(value, int)
