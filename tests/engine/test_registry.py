"""Element registry (M2 step 3, D14)."""

import json
import os

from gelectrical.core import fields
from gelectrical.elementmodel import registry

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_registry_matches_legacy_window_registry():
    """Same codes as the GTK window registered (recorded in the baseline)"""
    with open(os.path.join(ROOT, 'tests', 'baseline', 'environment.json'), encoding='utf-8') as fp:
        env = json.load(fp)
    assert sorted(registry.ELEMENT_MODELS) == env['registered_element_codes']


def test_codes_unique_and_consistent():
    for code, cls in registry.ELEMENT_MODELS.items():
        assert cls.code == code
    assert len(registry.ELEMENT_MODELS) == 31
    assert 'element_async_motor' not in registry.ELEMENT_MODELS


def test_every_element_constructs_headless():
    for code, cls in registry.ELEMENT_MODELS.items():
        element = cls(project_settings=fields.new_project_settings())
        assert element.code == code
        assert isinstance(element.fields, dict)


def test_get_element_class_structural():
    assert registry.get_element_class('element_wire').code == 'element_wire'
    assert registry.get_element_class('element_assembly').code == 'element_assembly'


def test_palette_entries_respect_advanced_mode():
    basic = {e[0] for e in registry.palette_entries(False)}
    full = {e[0] for e in registry.palette_entries(True)}
    assert basic < full
    assert 'element_ward' in full and 'element_ward' not in basic
    assert 'element_display_node' not in full  # no palette icon


def test_get_element_models_returns_copy():
    models = registry.get_element_models()
    models.pop('element_load')
    assert 'element_load' in registry.ELEMENT_MODELS
