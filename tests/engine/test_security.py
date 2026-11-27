"""Security hardening (M3, ADR 0011): no code execution from project,
database, clipboard or report data."""

import ast
import glob
import json
import os
import zipfile

import pytest

from gelectrical import persistence, undo
from gelectrical.core.database import DatabaseReferenceError, parse_data_reference
from gelectrical.core.expressions import ExpressionError, ExpressionNotAllowed, compile_expression
from gelectrical.model.clipboard import CLIPBOARD_FORMAT, ClipboardError, decode_elements
from gelectrical.model.project import ProjectModel

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAMPLE = os.path.join(ROOT, 'sample_files', 'sample.gepro')
INJECTION = "__import__('os').system('echo injected')"


def _load(filename):
    project = ProjectModel(stack=undo.Stack())
    persistence.load_project(project, filename)
    return project


# -- static check -----------------------------------------------------------

FORBIDDEN_CALLS = {'eval', 'exec', 'compile', '__import__'}
FORBIDDEN_ATTRIBUTES = {('pickle', 'loads'), ('pickle', 'load'), ('marshal', 'loads'),
                        ('yaml', 'load'), ('shelve', 'open')}
STATIC_CHECK_ALLOW = {
    # Imports a module named in the capture harness's own constant list
    ('tools/baseline/capture.py', '__import__'),
}


def _python_files():
    files = glob.glob(os.path.join(ROOT, 'gelectrical', '**', '*.py'), recursive=True)
    files += glob.glob(os.path.join(ROOT, 'tools', '**', '*.py'), recursive=True)
    files += glob.glob(os.path.join(ROOT, 'modern', '**', '*.py'), recursive=True)
    files.append(os.path.join(ROOT, 'gelectrical_launcher.py'))
    return sorted(f for f in files if '/node_modules/' not in f.replace(os.sep, '/'))


def test_no_code_execution_calls():
    """No eval/exec/compile/__import__/pickle.loads in engine, UI, tools
    or backend code (ADR 0011 verification)."""
    found = []
    for filename in _python_files():
        rel = os.path.relpath(filename, ROOT).replace(os.sep, '/')
        with open(filename, encoding='utf-8') as fp:
            tree = ast.parse(fp.read(), filename)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALLS:
                    name = func.id
                elif (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                      and (func.value.id, func.attr) in FORBIDDEN_ATTRIBUTES):
                    name = '%s.%s' % (func.value.id, func.attr)
                else:
                    continue
                if (rel, name) not in STATIC_CHECK_ALLOW:
                    found.append('%s:%d %s' % (rel, node.lineno, name))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [alias.name for alias in node.names]
                module = getattr(node, 'module', None) or ''
                if 'pickle' in names or module == 'pickle' or 'mako' in module or \
                        any(n.startswith('mako') for n in names):
                    found.append('%s:%d import %s' % (rel, node.lineno, module or names))
    assert found == []


# -- database references ----------------------------------------------------

def test_database_reference():
    assert parse_data_reference("('mcb_lnt', '', 'lnt_mcb_b.json')") == ('mcb_lnt', '', 'lnt_mcb_b.json')
    assert parse_data_reference(" ('fuse_lnt', '2.csv', 'params.json') ") == \
        ('fuse_lnt', '2.csv', 'params.json')


@pytest.mark.parametrize('value', [
    INJECTION,
    "('a', 'b')",
    "['a', 'b', 'c', 'd']",
    "('../etc', '', 'passwd')",
    "('a', '/etc/passwd', 'p.json')",
    "('a', 'b.csv', '')",
    "('a', 'C:\\\\x.csv', 'p.json')",
    "('a', 1, 'p.json')",
    "'abc'",
    '',
])
def test_database_reference_rejected(value):
    with pytest.raises(DatabaseReferenceError):
        parse_data_reference(value)


def test_bundled_database_references_parse():
    import csv
    count = 0
    for filename in glob.glob(os.path.join(ROOT, 'gelectrical', 'database', '*.csv')):
        with open(filename, encoding='utf-8') as fp:
            reader = csv.reader(fp, delimiter=';')
            header = next(reader)
            columns = [i for i, name in enumerate(header) if name in ('pcurve_l', 'pcurve_g')]
            for row in reader:
                for i in columns:
                    if i < len(row) and row[i]:
                        subdir, data, params = parse_data_reference(row[i])
                        assert os.path.exists(os.path.join(ROOT, 'gelectrical', 'database', subdir, params))
                        count += 1
    assert count > 400


# -- rules check ------------------------------------------------------------

def test_rule_expressions_compile():
    from gelectrical.model.rulescheck import RULES_POLICY, electrical_rules, rule_expressions
    expressions = rule_expressions(electrical_rules)
    assert len(expressions) > 50
    for expression in expressions:
        compile_expression(expression, RULES_POLICY)


def test_rule_policy_rejects_other_methods():
    from gelectrical.model.rulescheck import RULES_POLICY
    from gelectrical.core.expressions import evaluate
    from gelectrical.model.protection import ProtectionModel
    model = ProtectionModel('t', {}, {'curve_u': [], 'curve_l': []})
    with pytest.raises(ExpressionNotAllowed):
        evaluate('m.evaluate_curves({})', {'m': model}, RULES_POLICY)
    with pytest.raises(ExpressionNotAllowed):
        evaluate('m.data_struct', {'m': model}, RULES_POLICY)


# -- protection curves ------------------------------------------------------

def _protection_model(select, curve_value):
    from gelectrical.model.protection import ProtectionModel
    curve = [['point', curve_value, 1.0], ['point', '2*f.In', 0.1], ['point', '3*f.In', 0.01]]
    curves = {'select_expr_list': [select], 'curve_u1': curve, 'curve_l1': curve}
    return ProtectionModel('t', {'x': ['X', '', 1, None]}, curves)


def test_protection_curve_injection_is_rejected():
    fields = {'In': {'value': 10.0}}
    model = _protection_model('d.x == 1', '1.5*f.In')
    model.evaluate_curves(fields)
    assert list(model.linestring_upper.coords)[0] == (15.0, 1.0)
    with pytest.raises(ExpressionNotAllowed):
        _protection_model(INJECTION, '1.5*f.In').evaluate_curves(fields)
    with pytest.raises(ExpressionNotAllowed):
        _protection_model('d.x == 1', INJECTION).evaluate_curves(fields)


def test_protection_curve_runtime_error_skips_point_as_before():
    """A value that fails to evaluate (unknown field) skips that curve item,
    as with eval before M3."""
    fields = {'In': {'value': 10.0}}
    model = _protection_model('d.x == 1', 'f.missing*2')
    model.evaluate_curves(fields)
    assert list(model.linestring_upper.coords) == [(20.0, 0.1), (30.0, 0.01)]


def _inject(src, dst, where):
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, 'w') as zout:
        done = False
        for info in zin.infolist():
            data = zin.read(info.filename)
            if not done and info.filename != 'document.json' and info.filename.endswith('.json'):
                obj = json.loads(data)
                for element in obj[1]['elements']:
                    curve = element['fields'].get('pcurve_l')
                    if curve and curve['value']:
                        data_struct = curve['value']['data']
                        if where == 'select':
                            data_struct['select_expr_list'] = [INJECTION]
                            data_struct['curve_u1'] = data_struct.get('curve_u1', data_struct.get('curve_u'))
                            data_struct['curve_l1'] = data_struct.get('curve_l1', data_struct.get('curve_l'))
                        else:
                            key = [k for k in data_struct if k.startswith('curve')][0]
                            data_struct[key][0][1] = INJECTION
                        done = True
                        break
                data = json.dumps(obj).encode('utf-8')
            zout.writestr(info, data)
    assert done


@pytest.mark.parametrize('where', ['select', 'curve'])
def test_malicious_project_rejected(tmp_path, where, monkeypatch):
    calls = []
    monkeypatch.setattr(os, 'system', lambda *args: calls.append(args))
    bad = tmp_path / 'bad.gepro'
    _inject(SAMPLE, str(bad), where)
    with pytest.raises(ExpressionNotAllowed, match=r'Element element_\w+ .*not allowed'):
        _load(str(bad))
    assert calls == []


# -- clipboard --------------------------------------------------------------

def test_clipboard_round_trip():
    project = _load(SAMPLE)
    drawing = project.drawing_models[0]
    for element in drawing.elements:
        element.set_selection(True)
    text = drawing.get_clipboard_text()
    payload = json.loads(text)
    assert payload['format'] == CLIPBOARD_FORMAT and payload['version'] == 1
    selected, assembly_dict = drawing.get_selected(assembly_info=True)
    elements, pasted_assemblies = drawing.elements_from_clipboard(text)
    # Same elements as the legacy insertion path (get_model -> set_model copy)
    expected = [drawing.get_element_copy(e).get_model() for e in selected]
    assert json.dumps([e.get_model() for e in elements]) == json.dumps(expected)
    assert pasted_assemblies == assembly_dict
    # Pasting goes through the floating model and inserts copies
    drawing.add_floating_model(elements, pasted_assemblies)
    before = len(drawing.elements)
    drawing.make_floating_model_permenant()
    assert len(drawing.elements) == before + len(elements)


def _payload(**changes):
    element = {'code': 'element_busbar', 'x': 0, 'y': 0, 'orientation': 'horizontal',
               'ports': [[0, 0]], 'fields': {'ref': {'value': 'B1', 'type': 'str'}}}
    payload = {'format': CLIPBOARD_FORMAT, 'version': 1, 'elements': [element], 'assemblies': {}}
    for key, value in changes.items():
        if key.startswith('e_'):
            element[key[2:]] = value
        else:
            payload[key] = value
    return json.dumps(payload)


@pytest.mark.parametrize('text', [
    'gASVAAAAAAAAAA==',  # legacy pickle/base64 payload
    'not json',
    json.dumps(['DrawingGroup', []]),
    _payload(format='other'),
    _payload(version=2),
    _payload(elements=[]),
    _payload(e_code='element_unknown'),
    _payload(e_x='0'),
    _payload(e_orientation='diagonal'),
    _payload(e_ports=[[0]]),
    _payload(e_fields={'ref': 'B1'}),
    _payload(assemblies={'0': [0]}),
    _payload(assemblies={'x': []}),
])
def test_clipboard_rejects_invalid(text):
    with pytest.raises(ClipboardError):
        decode_elements(text, {'element_busbar', 'element_assembly', 'element_wire'})


def test_clipboard_valid_payload():
    models, assemblies = decode_elements(_payload(), {'element_busbar'})
    assert models[0]['code'] == 'element_busbar' and assemblies == {}


# -- reports (D10) ----------------------------------------------------------

def test_report_template_autoescape():
    from gelectrical.reports.export import report_environment
    env = report_environment()
    template = env.from_string('{{ x }}')
    assert template.render(x='<b>') == '<b>'  # templates from strings: no autoescape
    html = env.get_template('report.html')
    assert html.environment.autoescape('report.html') is True
    assert html.environment.autoescape('report.css') is False


def test_report_escapes_project_text(tmp_path):
    from gelectrical.analysis import AnalysisSettings, run_analysis
    from gelectrical.reports import export_pdf_report
    project = _load(SAMPLE)
    run_analysis(project, AnalysisSettings.from_project(project))
    fields = project.get_project_fields()
    fields['project_name']['value'] = '<script>alert(1)</script> & Co'
    fields['drawing_field_address']['value'] = 'Line 1\n<img src="file:///etc/passwd">'
    export_pdf_report(project, str(tmp_path), {'powerflow': False, 'sc_sym': False, 'sc_gf': False})
    html = (tmp_path / 'report.html').read_text(encoding='utf-8')
    assert '<script>' not in html and '&lt;script&gt;alert(1)&lt;/script&gt; &amp; Co' in html
    assert '<img src="file:///etc/passwd">' not in html
    assert 'Line 1</br>&lt;img' in html
    assert (tmp_path / 'report.pdf').exists()


def test_report_url_fetcher(tmp_path):
    from gelectrical.reports.export import report_url_fetcher
    css = tmp_path / 'report.css'
    css.write_text('p {}', encoding='utf-8')
    other = tmp_path / 'secret.txt'
    other.write_text('secret', encoding='utf-8')
    fetcher = report_url_fetcher([str(css)])
    assert fetcher(css.as_uri()).read() == b'p {}'
    assert fetcher('data:text/plain;base64,aGk=') is not None
    for url in (other.as_uri(), 'https://example.com/x.png', 'ftp://example.com/x'):
        with pytest.raises(ValueError):
            fetcher(url)
