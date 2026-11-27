"""Generated artefacts are current and DTOs conform to the JSON Schemas (M4)"""

import json
import os

import pytest

from modern.backend import registry, schemas

from conftest import ROOT, MULTISHEET, first_sheet, wait_job

SCHEMA_DIR = os.path.join(ROOT, 'modern', 'backend', 'schemas')
PROTOCOL_DOC = os.path.join(ROOT, 'docs', 'architecture', 'backend-protocol.md')
BEGIN = '<!-- BEGIN GENERATED METHOD TABLE -->'
END = '<!-- END GENERATED METHOD TABLE -->'


def test_committed_schemas_are_current():
    expected = schemas.documents()
    present = sorted(f for f in os.listdir(SCHEMA_DIR) if f.endswith('.json'))
    assert present == sorted(expected), 'run: python -m modern.backend --write-schemas modern/backend/schemas'
    for filename, document in expected.items():
        with open(os.path.join(SCHEMA_DIR, filename), encoding='utf-8') as fp:
            assert fp.read() == schemas.render(document), filename


def test_protocol_method_table_is_current():
    with open(PROTOCOL_DOC, encoding='utf-8') as fp:
        text = fp.read()
    table = text.split(BEGIN, 1)[1].split(END, 1)[0].strip()
    assert table == registry.method_table_markdown().strip(), \
        'run: python -m modern.backend --write-docs'


# -- minimal validator for the keywords used by modern.backend.schemas ---------

def validate(value, schema, path='$'):
    if '$ref' in schema:
        return validate(value, schemas.SCHEMAS[schema['$ref'][:-len('.json')]], path)
    if 'anyOf' in schema:
        errors = []
        for option in schema['anyOf']:
            try:
                validate(value, option, path)
                return
            except AssertionError as exc:
                errors.append(str(exc))
        raise AssertionError('%s: no option matched (%s)' % (path, '; '.join(errors)))
    if 'enum' in schema:
        assert value in schema['enum'], '%s: %r not in %r' % (path, value, schema['enum'])
    kind = schema.get('type')
    checks = {'object': lambda v: isinstance(v, dict), 'array': lambda v: isinstance(v, list),
              'string': lambda v: isinstance(v, str), 'boolean': lambda v: isinstance(v, bool),
              'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
              'number': lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
              'null': lambda v: v is None}
    if kind:
        assert checks[kind](value), '%s: expected %s, got %r' % (path, kind, value)
    if kind == 'object':
        for key in schema.get('required', ()):
            assert key in value, '%s: missing %s' % (path, key)
        properties = schema.get('properties', {})
        for key, item in value.items():
            if key in properties:
                validate(item, properties[key], '%s.%s' % (path, key))
            else:
                assert schema.get('additionalProperties', True) is not False, '%s: unexpected %s' % (path, key)
    if kind == 'array' and 'items' in schema:
        for index, item in enumerate(value):
            validate(item, schema['items'], '%s[%d]' % (path, index))


def test_dtos_conform_to_schemas(runtime, events):
    runtime.call('project.open', {'path': MULTISHEET})
    for element_type in runtime.call('catalog.element_types', {'advanced': True})['types']:
        validate(element_type, schemas.SCHEMAS['ElementType'])
    for sheet in runtime.call('project.state')['sheets']:
        validate(runtime.call('drawing.sheet', {'sheet': sheet['uid'], 'detail': True}), schemas.SCHEMAS['Sheet'])
        validate(runtime.call('drawing.sheet', {'sheet': sheet['uid']}), schemas.SCHEMAS['Sheet'])
    uid = runtime.call('drawing.sheet', {'sheet': first_sheet(runtime)})['elements'][0]['uid']
    validate(runtime.call('drawing.element', {'uid': uid}), schemas.SCHEMAS['Element'])
    result = runtime.call('drawing.set_fields', {'uids': [uid], 'values': {'ref': 'SCHEMA'}})
    validate(result, schemas.SCHEMAS['CommandResult'])
    for page in runtime.call('project.settings')['pages'].values():
        for field in page['fields']:
            validate(field, schemas.SCHEMAS['FieldSchema'])
    job = wait_job(runtime, runtime.call('analysis.start', {'rules_check': True})['job'])
    assert job['status'] == 'finished'
    results = runtime.call('analysis.results')
    for records in results['elements'].values():
        for record in records:
            validate(record, schemas.SCHEMAS['ResultField'])
    for message in results['diagnostics'] + (results['rules'] or []):
        validate(message, schemas.SCHEMAS['Message'])
    for event in events:
        validate(json.loads(json.dumps(event)), schemas.SCHEMAS['Event'])
