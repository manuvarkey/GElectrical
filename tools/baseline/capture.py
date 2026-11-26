#!/usr/bin/env python3
"""Capture the GElectrical regression baseline from the legacy GTK code.

Milestone M1 (docs/migration/regression-baseline.md). For every project the
legacy ``MainWindow`` is built (needs a display; use ``xvfb-run`` on Linux),
the project is opened and canonical JSON artefacts are written to
``<out>/<project-name>/``. Each project runs in its own subprocess so that
module-level state (defect D4) cannot leak between projects.

Usage::

    pixi run -e test baseline-capture                 # all projects -> tests/baseline
    pixi run -e test baseline-capture --out /tmp/b    # capture elsewhere
    pixi run -e test baseline-capture path/to/x.gepro # selected projects

The capture is read-only with respect to the engine: it calls existing
legacy methods in the order the GTK callbacks use them.
"""

import argparse
import glob
import hashlib
import io
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import warnings
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import canonical  # noqa: E402
from canonical import canon, write_json  # noqa: E402

DEFAULT_OUT = os.path.join(ROOT, 'tests', 'baseline')

# Analysis modes: (name, pf_method, power_flow_3ph)
MODES = [
    ('pf_bal', 'Power flow', False),
    ('pf_3ph', 'Power flow', True),
    ('pfdiv_bal', 'Power flow with diversity', False),
    ('pfdiv_3ph', 'Power flow with diversity', True),
    ('ts_bal', 'Time series', False),
    ('ts_3ph', 'Time series', True),
]

RENUMBER_MODES = ('All', 'New elements only', 'Selected elements only')

PP_INPUT_TABLES = ('bus', 'line', 'trafo', 'trafo3w', 'switch', 'ext_grid', 'gen',
                   'sgen', 'asymmetric_sgen', 'storage', 'impedance', 'dcline',
                   'load', 'asymmetric_load', 'shunt', 'ward', 'xward', 'motor')
PP_INPUTS_AFTER_RUN = ('sgen', 'asymmetric_sgen', 'load', 'asymmetric_load', 'trafo')
BUS_COLUMNS = ('bus', 'from_bus', 'to_bus', 'hv_bus', 'lv_bus', 'mv_bus')
FIELD_SKIP_KEYS = ('validation_func', 'tooltip')
DRAWING_DPI = 150

_HEX_RE = re.compile(r'0x[0-9a-fA-F]+')


# ---------------------------------------------------------------------------
# Project discovery and naming
# ---------------------------------------------------------------------------

def default_projects():
    files = sorted(glob.glob(os.path.join(ROOT, 'sample_files', '**', '*.gepro'), recursive=True))
    files += sorted(f for f in glob.glob(os.path.join(ROOT, 'tests', 'projects', '**', '*.gepro'),
                                         recursive=True)
                    if os.sep + 'malicious' + os.sep not in f)
    return files


def project_name(filename):
    """Stable artefact folder name for a project file."""
    rel = os.path.relpath(os.path.abspath(filename), ROOT).replace(os.sep, '/')
    stem = os.path.splitext(os.path.basename(rel))[0]
    if rel.startswith('sample_files/'):
        return 'sample__' + stem
    if rel.startswith('tests/projects/edge/'):
        return 'edge__' + stem
    if rel.startswith('tests/projects/'):
        return stem
    return 'other__' + stem


def normalize_message(text):
    text = str(text).replace(ROOT, '<ROOT>')
    text = text.replace(tempfile.gettempdir(), '<TMP>')
    return _HEX_RE.sub('0x?', text)


# ---------------------------------------------------------------------------
# Environment manifest
# ---------------------------------------------------------------------------

def _version(module_name):
    try:
        module = __import__(module_name)
        return getattr(module, '__version__', None) or getattr(module, 'version', 'unknown')
    except Exception as exc:  # pragma: no cover
        return 'unavailable: %s' % exc


def font_fingerprint(misc):
    """Resolved fonts used by drawings; raster comparison depends on them."""
    faces = {'SCHEM_FONT_FACE': misc.SCHEM_FONT_FACE,
             'GRAPH_FONT_FACE': misc.GRAPH_FONT_FACE,
             'REPORT_FONT_FACE': misc.REPORT_FONT_FACE}
    resolved = {}
    fc_match = shutil.which('fc-match')
    for key, face in faces.items():
        if fc_match:
            try:
                out = subprocess.run([fc_match, face], capture_output=True, text=True,
                                     timeout=20).stdout.strip()
            except Exception as exc:  # pragma: no cover
                out = 'error: %s' % exc
        else:
            out = 'fc-match unavailable'
        resolved[key] = {'face': face, 'match': out}
    return resolved


def environment_manifest(misc=None):
    lock = os.path.join(ROOT, 'pixi.lock')
    lock_hash = None
    if os.path.exists(lock):
        with open(lock, 'rb') as fp:
            lock_hash = hashlib.sha256(fp.read()).hexdigest()
    manifest = {
        'python': platform.python_version(),
        'platform': platform.platform(),
        'system': platform.system(),
        'machine': platform.machine(),
        'packages': {name: _version(name) for name in
                     ('pandapower', 'numpy', 'scipy', 'pandas', 'shapely', 'networkx',
                      'numba', 'matplotlib', 'weasyprint', 'cairo')},
        'pixi_lock_sha256': lock_hash,
        'drawing_dpi': DRAWING_DPI,
    }
    if misc is not None:
        manifest['program_version'] = misc.PROGRAM_VER
        manifest['project_file_version'] = misc.PROJECT_FILE_VER
        manifest['fonts'] = font_fingerprint(misc)
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
        manifest['gtk'] = '%d.%d.%d' % (Gtk.get_major_version(), Gtk.get_minor_version(),
                                        Gtk.get_micro_version())
        manifest['pygobject'] = gi.__version__
    except Exception:  # pragma: no cover
        pass
    return manifest


# ---------------------------------------------------------------------------
# Canonical state extraction
# ---------------------------------------------------------------------------

def ekey_str(ekey):
    return '%d,%d' % tuple(ekey)


def field_state(field):
    state = {}
    for key, value in field.items():
        if key in FIELD_SKIP_KEYS or callable(value):
            continue
        if key == 'selection_image_list' and value:
            value = [os.path.basename(v) if isinstance(v, str) else v for v in value]
        state[key] = canon(value)
    return state


def fields_state(fields):
    return {code: field_state(field) for code, field in fields.items()}


def element_state(element, gid_index):
    state = {'code': element.code,
             'x': element.x,
             'y': element.y,
             'orientation': element.orientation,
             'ports': canon(element.ports),
             'fields': fields_state(element.fields)}
    if element.code == 'element_wire':
        state['points'] = canon(element.points)
    if element.code == 'element_assembly':
        state['children_codes'] = canon(element.children_codes)
        state['element_rect_width'] = element.element_rect_width
        state['element_rect_height'] = element.element_rect_height
    gid_assembly = element.get_gid_assembly()
    state['assembly_parent'] = gid_index.get(gid_assembly) if gid_assembly else None
    return state


def canonical_model(session):
    project = session.project
    sheets = []
    for drawing_model in project.drawing_models:
        gid_index = {e.get_gid(): i for i, e in enumerate(drawing_model.elements)}
        sheets.append({'fields': fields_state(drawing_model.fields),
                       'elements': [element_state(e, gid_index) for e in drawing_model.elements]})
    return {'project_fields': {page: fields_state(fields) for page, fields in project.fields.items()},
            'loadprofiles': canon(project.loadprofiles),
            'sheets': sheets}


def stored_model(session):
    """The storage model exactly as ``MainWindow.on_save`` would write it."""
    proj_settings, proj_pages = session.project.get_model()
    return canon({'document': proj_settings, 'pages': dict(proj_pages)})


def read_gepro(filename):
    from zipfile import ZipFile
    with ZipFile(filename, 'r') as projzip:
        with projzip.open('document.json') as fp:
            document = json.load(fp)
        pages = {}
        for name in document['_files']:
            with projzip.open(name) as fp:
                pages[name] = json.load(fp)
    return document, pages


def value_differences(actual, expected, path=''):
    """Structured leaf differences (stored -> loaded); floats via TOL_FIELD."""
    out = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            sub = '%s/%s' % (path, key)
            if key not in actual:
                out.append({'path': sub, 'stored': expected[key], 'loaded': '<missing>'})
            elif key not in expected:
                out.append({'path': sub, 'stored': '<missing>', 'loaded': actual[key]})
            else:
                out.extend(value_differences(actual[key], expected[key], sub))
        return out
    if isinstance(expected, list) and isinstance(actual, list) and len(expected) == len(actual):
        for i, (a, b) in enumerate(zip(actual, expected)):
            out.extend(value_differences(a, b, '%s/%d' % (path, i)))
        return out
    numeric = (isinstance(actual, (int, float)) and isinstance(expected, (int, float))
               and not isinstance(actual, bool) and not isinstance(expected, bool))
    if numeric:
        abs_tol, rel_tol = canonical.TOL_FIELD
        if abs(actual - expected) <= abs_tol + rel_tol * abs(expected):
            return out
    elif actual == expected:
        return out
    if isinstance(expected, (dict, list)) or isinstance(actual, (dict, list)):
        out.append({'path': path, 'stored': '<structure %s>' % _digest(expected),
                    'loaded': '<structure %s>' % _digest(actual)})
    else:
        out.append({'path': path, 'stored': expected, 'loaded': actual})
    return out


def _digest(value):
    return hashlib.sha256(canonical.dumps(value).encode('utf-8')).hexdigest()[:16]


def d8_report(filename, session):
    """Compare values stored in the file with the values after loading (D8).

    ``changed``: field present in the file whose value differs after load;
    ``added``: field missing from the file and created by the current code;
    ``removed``: field in the file that the current code drops.
    """
    document, pages = read_gepro(filename)
    loaded = stored_model(session)
    stored = canon({'proj_fields': document.get('proj_fields'), 'pages': pages})
    actual = {'proj_fields': loaded['document']['proj_fields'], 'pages': loaded['pages']}
    report = {'changed': [], 'added': [], 'removed': []}
    for diff in value_differences(actual, stored):
        if diff['stored'] == '<missing>':
            report['added'].append(diff['path'])
        elif diff['loaded'] == '<missing>':
            report['removed'].append(diff['path'])
        else:
            report['changed'].append(diff)
    report['counts'] = {k: len(v) for k, v in report.items()}
    return report


# -- topology ---------------------------------------------------------------

def node_keys(networkmodel):
    """Map global node number -> canonical node key (sorted local nodes)."""
    local = {}
    for p0, gnode in networkmodel.node_mapping.items():
        local.setdefault(gnode, []).append(p0)
    keys = {}
    for gnode in networkmodel.global_nodes:
        if gnode in local:
            keys[gnode] = 'N[' + '|'.join(sorted(local[gnode])) + ']'
        else:
            ports = sorted(str(p) for p in networkmodel.port_mapping_inverted.get(gnode, ()))
            keys[gnode] = 'P[' + '|'.join(ports) + ']'
    return keys


def graph_edges(graph, keys, max_gnode):
    edges = []
    for u, v, data in graph.edges(data=True):
        ekey = ekey_str(data['key'])

        def name(n):
            if n in keys:
                return keys[n]
            return 'T[%s]' % ekey  # virtual source/sink terminal of this element
        a, b = sorted((name(u), name(v)))
        edges.append([a, b, ekey, data.get('code'), data.get('ref')])
    return sorted(edges, key=lambda e: json.dumps(e))


def topology(session):
    project = session.project
    nm = project.networkmodel
    keys = node_keys(nm)
    max_gnode = max(nm.global_nodes) if nm.global_nodes else 0

    def terminal_names(nodes, graph):
        names = []
        for n in nodes:
            for _, _, data in graph.edges(n, data=True):
                names.append('T[%s]' % ekey_str(data['key']))
        return sorted(set(names))

    nodes = []
    for gnode in sorted(nm.global_nodes, key=lambda g: keys[g]):
        nodes.append({'key': keys[gnode],
                      'ports': sorted(str(p) for p in nm.port_mapping_inverted.get(gnode, ())),
                      'elements': sorted(ekey_str(e) for e in nm.gnode_element_mapping.get(gnode, [])),
                      'df': canon(nm.gnode_df_mapping.get(gnode)),
                      'r_grid': canon(nm.gnode_res_mapping.get(gnode))})

    def rel(func, ekey, kind):
        try:
            value = func(ekey)
        except Exception as exc:
            return {'error': normalize_message('%s: %s' % (type(exc).__name__, exc))}
        if value is None:
            return None
        # Legacy queries return dicts keyed by (page, index) for elements and
        # (page, gnode) for node display elements.
        if kind == 'node':
            return sorted('%d:%s' % (k[0], keys.get(k[1], str(k[1]))) for k in value)
        return sorted(ekey_str(k) for k in value)

    relations = {}
    for ekey, element in sorted(nm.base_elements.items()):
        if not nm.gnode_element_mapping_inverted.get(ekey):
            continue
        relations[ekey_str(ekey)] = {
            'code': element.code,
            'node_keys': [keys[g] for g in nm.gnode_element_mapping_inverted[ekey]],
            'upstream_elements': rel(nm.get_upstream_element, ekey, 'element'),
            'downstream_elements': rel(nm.get_downstream_element, ekey, 'element'),
            'upstream_node': rel(nm.get_upstream_node_of_element, ekey, 'node'),
            'downstream_node': rel(nm.get_downstream_node_of_element, ekey, 'node'),
        }
    return {'nodes': nodes,
            'virtual_node_count': len(nm.virtual_global_nodes),
            'edges': graph_edges(nm.graph, keys, max_gnode),
            'edges_with_status': graph_edges(nm.graph_with_status, keys, max_gnode),
            'source_terminals': terminal_names(nm.graph_source_nodes, nm.graph),
            'source_terminals_with_status': terminal_names(nm.graph_source_nodes_with_status, nm.graph),
            'sink_terminals': terminal_names(nm.graph_sink_nodes, nm.graph),
            'elements': relations}


# -- pandapower tables ------------------------------------------------------

def _install_build_spy(misc):
    """Record node/element maps per build mode on the PandaPowerModel instance."""
    from gelectrical.model import pandapower as ppmodule
    cls = ppmodule.PandaPowerModel
    if getattr(cls, '_baseline_spy', False):
        return
    original = cls.build_power_model

    def build_power_model(self, mode=misc.POWER_MODEL_POWERFLOW):
        result = original(self, mode)
        maps = self.__dict__.setdefault('_baseline_maps', {})
        maps[mode] = (dict(self.power_nodes_inverted), dict(self.power_elements_inverted))
        return result

    cls.build_power_model = build_power_model
    cls._baseline_spy = True


def table_state(net, table, bus_keys, element_keys=None):
    df = net[table]
    rows = canonical.dataframe_to_canon(df)
    for index, row in rows.items():
        for col in BUS_COLUMNS:
            if col in row and isinstance(row[col], int):
                row[col] = bus_keys.get(row[col], 'bus:%s' % row[col])
        if table == 'switch' and row.get('et') == 'b' and isinstance(row.get('element'), int):
            row['element'] = bus_keys.get(row['element'], 'bus:%s' % row['element'])
        if table == 'bus':
            row['node_key'] = bus_keys.get(int(index), None)
            if isinstance(row.get('name'), str) and row['name'].isdigit():
                row['name'] = '<gnode>'
        if element_keys is not None:
            ekey = element_keys.get((table, int(index)))
            row['__element'] = ekey_str(ekey) if ekey else None
    return rows


def bus_key_map(node_inv, keys):
    return {int(bus): keys.get(gnode, 'gnode:%s' % gnode) for bus, gnode in node_inv.items()}


def pp_input_state(session, misc):
    pm = session.project.powermodel
    keys = node_keys(session.project.networkmodel)
    maps = getattr(pm, '_baseline_maps', {})
    nets = {'powerflow': (pm.power_model, misc.POWER_MODEL_POWERFLOW),
            'linefault': (pm.power_model_lf, misc.POWER_MODEL_LINEFAULT),
            'groundfault': (pm.power_model_gf, misc.POWER_MODEL_GROUNDFAULT)}
    state = {}
    for name, (net, mode) in nets.items():
        node_inv, el_inv = maps.get(mode, ({}, {}))
        bus_keys = bus_key_map(node_inv, keys)
        tables = {}
        for table in PP_INPUT_TABLES:
            if table in net and len(net[table]):
                tables[table] = table_state(net, table, bus_keys, el_inv)
        state[name] = {'f_hz': canon(net.f_hz), 'sn_mva': canon(net.sn_mva), 'tables': tables}
    return state


def result_tables(net, bus_keys, prefix='res_', exclude_sc=True):
    tables = {}
    for name in sorted(net.keys()):
        if not name.startswith(prefix) or name.endswith('_est'):
            continue
        if exclude_sc and '_sc' in name:
            continue
        df = net[name]
        if not hasattr(df, 'iterrows') or not len(df):
            continue
        rows = canonical.dataframe_to_canon(df)
        if name.startswith('res_bus'):
            rows = {bus_keys.get(int(k), 'bus:%s' % k): v for k, v in rows.items()}
        tables[name] = rows
    return tables


def pf_state(session, misc):
    pm = session.project.powermodel
    keys = node_keys(session.project.networkmodel)
    node_inv, el_inv = getattr(pm, '_baseline_maps', {}).get(misc.POWER_MODEL_POWERFLOW, ({}, {}))
    bus_keys = bus_key_map(node_inv, keys)
    inputs_after = {}
    for table in PP_INPUTS_AFTER_RUN:
        if table in pm.power_model and len(pm.power_model[table]):
            inputs_after[table] = table_state(pm.power_model, table, bus_keys, el_inv)
    return {'converged': canon(getattr(pm.power_model, 'converged', None)),
            'results': result_tables(pm.power_model, bus_keys),
            'inputs_after_run': inputs_after}


def sc_state(session, misc):
    pm = session.project.powermodel
    keys = node_keys(session.project.networkmodel)
    maps = getattr(pm, '_baseline_maps', {})
    state = {}
    for name, net, mode in (('linefault', pm.power_model_lf, misc.POWER_MODEL_LINEFAULT),
                            ('groundfault', pm.power_model_gf, misc.POWER_MODEL_GROUNDFAULT)):
        node_inv, _ = maps.get(mode, ({}, {}))
        state[name] = result_tables(net, bus_key_map(node_inv, keys), prefix='res_', exclude_sc=False)
        state[name] = {k: v for k, v in state[name].items() if '_sc' in k}
    return state


def results_state(session):
    out = {}
    for ekey, element in session.elements():
        if element.code in session.misc.DISPLAY_ELEMENT_CODES:
            continue
        if element.res_fields:
            out[ekey_str(ekey)] = {'code': element.code, **{
                code: field_state(f) for code, f in element.res_fields.items()}}
    return out


def node_results_state(session):
    pm = session.project.powermodel
    keys = node_keys(session.project.networkmodel)
    return {keys.get(gnode, 'gnode:%s' % gnode): fields_state(fields)
            for gnode, fields in pm.node_results.items()}


def messages_state(data):
    """Canonical diagnostics/rules message structure, sorted."""
    data = canon(data)
    if isinstance(data, dict):
        return {k: sorted(v, key=lambda m: json.dumps(m, sort_keys=True))
                if isinstance(v, list) else v for k, v in data.items()}
    return data


# -- curves -----------------------------------------------------------------

def _coords(geom):
    if geom is None:
        return None
    try:
        if geom.is_empty:
            return []
        if geom.geom_type == 'Polygon':
            return canon([list(c) for c in geom.exterior.coords])
        return canon([list(c) for c in geom.coords])
    except Exception as exc:  # pragma: no cover
        return {'error': normalize_message(exc)}


def curves_state(session):
    out = {}
    for ekey, element in session.elements():
        entry = {}
        for attr in ('line_protection_model', 'ground_protection_model', 'damage_model'):
            model = getattr(element, attr, None)
            if model is None:
                continue
            entry[attr] = {
                'title': model.title,
                'type': model.data_struct.get('type'),
                'upper': _coords(model.linestring_upper),
                'lower': _coords(model.linestring_lower),
                'upper_log': _coords(model.linestring_upper_log),
                'lower_log': _coords(model.linestring_lower_log),
                'polygon': _coords(model.polygon),
                'polygon_log': _coords(model.polygon_log),
            }
        if entry:
            entry['code'] = element.code
            out[ekey_str(ekey)] = entry
    return out


# -- drawings and report ----------------------------------------------------

def render_drawings(session, folder):
    """Rasterize each sheet like ``ProjectModel.export_drawing`` (PNG)."""
    import cairo
    project = session.project
    misc = session.misc
    files = []
    if project.program_state['dark_mode']:
        misc.reset_dark_mode_drawing_values()
    try:
        scale = DRAWING_DPI / 72.0
        for page, drawing_model in enumerate(project.drawing_models):
            width = int(round(drawing_model.fields['page_width']['value'] * scale))
            height = int(round(drawing_model.fields['page_height']['value'] * scale))
            surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
            context = cairo.Context(surface)
            context.set_source_rgb(1, 1, 1)
            context.paint()
            context.scale(scale, scale)
            drawing_model.export_drawing(context)
            surface.flush()
            name = 'drawing_%d.png' % page
            surface.write_to_png(os.path.join(folder, name))
            files.append(name)
    finally:
        if project.program_state['dark_mode']:
            misc.set_dark_mode_drawing_values()
    return files


class _TextExtractor(HTMLParser):
    SKIP = ('style', 'script', 'svg', 'head')
    BLOCK = ('p', 'div', 'br', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'table',
             'caption', 'section', 'thead', 'tbody')

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append('\n')
        elif tag in ('td', 'th'):
            self.parts.append(' | ')
        elif tag == 'img':
            self.parts.append('[img]')

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCK:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def report_text(html):
    parser = _TextExtractor()
    parser.feed(html)
    return canonical.normalize_text(''.join(parser.parts))


# ---------------------------------------------------------------------------
# Capture steps
# ---------------------------------------------------------------------------

class WarningCollector(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.records = []

    def emit(self, record):
        self.records.append('%s: %s' % (record.name, normalize_message(record.getMessage())))


def run_mode(session, pf_method, three_phase, extra=None):
    """Run the analysis chain of ``MainWindow.on_run_analysis`` + rules check.

    Returns the status dict; mirrors the GUI in stopping at the first
    exception (the GUI's worker thread aborts there) and in not running the
    remaining steps after critical diagnostics.
    """
    misc = session.misc
    project = session.project
    sim = session.sim
    sim['pf_method']['value'] = pf_method
    sim['power_flow_3ph']['value'] = three_phase
    status = {'pf_method': pf_method, 'power_flow_3ph': three_phase, 'steps': [], 'warnings': []}
    collector = WarningCollector()
    pp_logger = logging.getLogger('pandapower')
    pp_logger.addHandler(collector)
    if extra is None:
        extra = {}

    def step(name, func):
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                value = func()
            for w in caught:
                first_line = normalize_message(w.message).strip().splitlines()[0]
                status['warnings'].append('%s: %s' % (w.category.__name__, first_line))
            status['steps'].append({'step': name, 'ok': True})
            return True, value
        except Exception as exc:
            status['steps'].append({'step': name, 'ok': False,
                                    'error': normalize_message('%s: %s' % (type(exc).__name__, exc))})
            status['traceback'] = normalize_message(traceback.format_exc(limit=6))
            return False, None

    try:
        ok, _ = step('setup_base_model', project.setup_base_model)
        if ok and 'topology' in extra:
            extra['topology'] = topology(session)
        ok = ok and step('build_power_model', project.build_power_model)[0]
        if ok and 'pp_input' in extra:
            extra['pp_input'] = pp_input_state(session, misc)
        if ok:
            session.messages.clear()
            ok, ret_code = step('run_diagnostics', project.run_diagnostics)
            status['diagnostics_ret_code'] = ret_code
            if 'diagnostics' in extra and session.messages:
                extra['diagnostics'] = messages_state(session.messages[-1])
            if ok and ret_code == misc.ERROR:
                status['stopped'] = 'Diagnostics returned critical errors'
                ok = False
        if ok:
            if pf_method == 'Time series':
                ok = step('run_powerflow_timeseries', project.run_powerflow_timeseries)[0]
            else:
                ok = step('run_powerflow', lambda: project.run_powerflow(pf_method))[0]
            if ok:
                extra['pf'] = pf_state(session, misc)
        ok = ok and step('run_sym_sccalc', project.run_sym_sccalc)[0]
        ok = ok and step('run_linetoground_sccalc', project.run_linetoground_sccalc)[0]
        if ok:
            extra['sc'] = sc_state(session, misc)
        ok = ok and step('update_results', project.update_results)[0]
        if ok:
            extra['results'] = results_state(session)
            extra['node_results'] = node_results_state(session)
            session.messages.clear()
            ok = step('run_rulescheck', project.run_rulescheck)[0]
            if ok and session.messages:
                extra['rules'] = messages_state(session.messages[-1])
        status['completed'] = ok
    finally:
        pp_logger.removeHandler(collector)
    status['warnings'] = sorted(set(status['warnings'] + collector.records))
    return status


def capture_project(filename, out_dir, legacy):
    os.makedirs(out_dir, exist_ok=True)
    misc = legacy.import_legacy()[1]
    _install_build_spy(misc)
    summary = {'project': os.path.relpath(filename, ROOT).replace(os.sep, '/'), 'modes': {}}

    # 1. Load, canonical model, D8 report, curves
    s = legacy.LegacySession()
    try:
        s.open(filename)
        model = canonical_model(s)
        write_json(os.path.join(out_dir, 'model.json'), model)
        write_json(os.path.join(out_dir, 'd8.json'), d8_report(filename, s))
        write_json(os.path.join(out_dir, 'curves.json'), curves_state(s))
        first_stored = stored_model(s)
        tmp = tempfile.mkdtemp(prefix='gelectrical_rt_')
        rt_file = os.path.join(tmp, 'roundtrip.gepro')
        s.save(rt_file)
    finally:
        s.close()

    # 2. Round trip: save -> load in a fresh window
    s = legacy.LegacySession()
    try:
        s.open(rt_file)
        roundtrip = canonical_model(s)
        if canonical.dumps(roundtrip) == canonical.dumps(model):
            # Store the full model only when it differs (avoids a 1:1 copy)
            roundtrip = {'equal_to_model': True}
        write_json(os.path.join(out_dir, 'roundtrip.json'), roundtrip)
        second_stored = stored_model(s)
        summary['roundtrip_stored_equal'] = (canonical.dumps(first_stored) ==
                                             canonical.dumps(second_stored))
    finally:
        s.close()
        shutil.rmtree(tmp, ignore_errors=True)

    # 3. Analysis modes (fresh window each)
    file_settings = None
    for name, pf_method, three_phase in MODES:
        s = legacy.LegacySession()
        try:
            s.open(filename)
            if file_settings is None:
                file_settings = (s.sim['pf_method']['value'], bool(s.sim['power_flow_3ph']['value']))
            first = name == MODES[0][0]
            extra = dict.fromkeys(('topology', 'pp_input', 'diagnostics')) if first else {}
            status = run_mode(s, pf_method, three_phase, extra)
            mode_dir = os.path.join(out_dir, name)
            os.makedirs(mode_dir, exist_ok=True)
            if first:
                for key in ('topology', 'pp_input', 'diagnostics'):
                    if extra.get(key) is not None:
                        write_json(os.path.join(out_dir, key + '.json'), extra[key])
            for key in ('pf', 'sc', 'results', 'node_results', 'rules'):
                if extra.get(key) is not None:
                    write_json(os.path.join(mode_dir, key + '.json'), extra[key])
            is_file_mode = (pf_method, three_phase) == file_settings
            status['file_settings_mode'] = is_file_mode
            if is_file_mode:
                # Report and drawing exactly as the analysis export produces them
                rep_dir = tempfile.mkdtemp(prefix='gelectrical_rep_')
                try:
                    if status.get('completed'):
                        try:
                            s.project.export_pdf_report(rep_dir, {'powerflow': True,
                                                                  'sc_sym': True, 'sc_gf': True})
                        except Exception as exc:
                            status['report_error'] = normalize_message(
                                '%s: %s' % (type(exc).__name__, exc))
                        html_file = os.path.join(rep_dir, 'report.html')
                        if os.path.exists(html_file):
                            with open(html_file, encoding='utf-8') as fp:
                                text = report_text(fp.read())
                            with open(os.path.join(out_dir, 'report.txt'), 'w',
                                      encoding='utf-8', newline='\n') as fp:
                                fp.write(text)
                        status['report_pdf'] = os.path.exists(os.path.join(rep_dir, 'report.pdf'))
                finally:
                    shutil.rmtree(rep_dir, ignore_errors=True)
                status['drawings'] = render_drawings(s, out_dir)
            write_json(os.path.join(mode_dir, 'status.json'), status)
            summary['modes'][name] = bool(status.get('completed'))
        finally:
            s.close()

    # 4. Renumbering
    renumber = {}
    for mode in RENUMBER_MODES:
        s = legacy.LegacySession()
        try:
            s.open(filename)
            renumber[mode] = renumber_capture(s, mode)
        finally:
            s.close()
    write_json(os.path.join(out_dir, 'renumber.json'), renumber)

    # 5. Undo/redo script
    s = legacy.LegacySession()
    try:
        s.open(filename)
        write_json(os.path.join(out_dir, 'undo.json'), undo_capture(s))
    finally:
        s.close()
    return summary


def refs(session):
    return {ekey_str(k): e.fields['ref']['value'] for k, e in session.elements()
            if 'ref' in e.fields}


def renumber_capture(session, mode):
    before = refs(session)
    if mode == 'Selected elements only':
        # Select every second element of the first sheet, in index order
        for index, element in enumerate(session.project.drawing_models[0].elements):
            if index % 2 == 1:
                element.set_selection(True)
    result = {'before': before}
    try:
        session.project.renumber_elements(mode)
        result['after'] = refs(session)
        result['undo_text'] = session.stack.undotext()
        session.stack.undo()
        result['undo_restores'] = refs(session) == before
    except Exception as exc:
        result['error'] = normalize_message('%s: %s' % (type(exc).__name__, exc))
    return result


def model_summary(session):
    sheets = []
    for drawing_model in session.project.drawing_models:
        sheets.append([[e.code, e.fields.get('ref', {}).get('value')] for e in drawing_model.elements])
    return {'sheets': sheets,
            'stored_sha256': _digest(stored_model(session))}


def undo_capture(session):
    """Scripted edit sequence, then undo all / redo all / undo all."""
    project = session.project
    misc = session.misc
    stack = session.stack
    initial = stored_model(session)
    log = {'actions': [], 'undo': [], 'redo': [], 'undo_again': []}

    def snapshot(label):
        return {'label': label, 'undocount': stack.undocount(), 'redocount': stack.redocount(),
                'undotext': stack.undotext(), 'redotext': stack.redotext(),
                'model': model_summary(session)}

    drawing_model = project.drawing_models[0]
    target = None
    for ekey, element in session.elements():
        if 'ref' in element.fields and element.code not in misc.DISPLAY_ELEMENT_CODES:
            target = element
            break

    def act_field():
        if target is None:
            raise RuntimeError('no element with a ref field')
        setter = misc.get_undoable_set_field(stack, None, target)
        setter('ref', 'UNDO-TEST')

    def act_insert():
        Load = project.program_state['element_models']['element_load']
        element = Load((800, 800), project_settings=project.program_state['project_settings'])
        element.fields['load_profile']['selection_list'] = project.loadprofiles
        drawing_model.insert_element_at_index(element)

    def act_delete_first():
        if drawing_model.elements:
            drawing_model.delete_rows([0])
        else:
            raise RuntimeError('no element to delete')

    actions = [('modify_ref_field', act_field),
               ('insert_load', act_insert),
               ('delete_element_0', act_delete_first),
               ('renumber_all', lambda: project.renumber_elements('All')),
               ('setup_base_model', project.setup_base_model)]
    for label, func in actions:
        try:
            func()
            entry = snapshot(label)
        except Exception as exc:
            entry = snapshot(label)
            entry['error'] = normalize_message('%s: %s' % (type(exc).__name__, exc))
        log['actions'].append(entry)

    def drain(direction, key):
        guard = 0
        while (stack.canundo() if direction == 'undo' else stack.canredo()) and guard < 50:
            text = stack.undotext() if direction == 'undo' else stack.redotext()
            try:
                getattr(stack, direction)()
                entry = snapshot(text)
            except Exception as exc:
                entry = snapshot(text)
                entry['error'] = normalize_message('%s: %s' % (type(exc).__name__, exc))
                log[key].append(entry)
                break
            log[key].append(entry)
            guard += 1

    drain('undo', 'undo')
    after_undo = stored_model(session)
    drain('redo', 'redo')
    drain('undo', 'undo_again')
    log['undo_all_restores_initial'] = canonical.dumps(after_undo) == canonical.dumps(initial)
    log['undo_all_differences'] = value_differences(after_undo, initial)[:50]
    return log


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def run_single(filename, out_dir):
    import legacy
    legacy.isolate_environment()
    logging.basicConfig(level=logging.ERROR, format='%(levelname)s - %(name)s - %(message)s')
    summary = capture_project(os.path.abspath(filename), out_dir, legacy)
    print(json.dumps(summary))


def capture_all(projects, out_root, hash_seed='0', clean=True):
    """Capture ``projects`` into ``out_root``; return (summaries, failures)."""
    os.makedirs(out_root, exist_ok=True)
    summaries, failures = {}, []
    for filename in projects:
        name = project_name(filename)
        out_dir = os.path.join(out_root, name)
        if clean and os.path.isdir(out_dir):
            shutil.rmtree(out_dir)
        env = dict(os.environ)
        env['PYTHONHASHSEED'] = str(hash_seed)
        proc = subprocess.run([sys.executable, os.path.abspath(__file__), '--single',
                               os.path.abspath(filename), '--out', out_dir],
                              capture_output=True, text=True, env=env, cwd=ROOT)
        if proc.returncode != 0:
            failures.append((name, proc.stdout[-4000:] + proc.stderr[-4000:]))
            print('FAIL', name, file=sys.stderr)
            continue
        last = [line for line in proc.stdout.splitlines() if line.startswith('{')]
        summaries[name] = json.loads(last[-1]) if last else {}
        print('OK  ', name, summaries[name].get('modes'), file=sys.stderr)
    # Environment manifest (from a child process with the same isolation)
    env = dict(os.environ)
    proc = subprocess.run([sys.executable, os.path.abspath(__file__), '--environment'],
                          capture_output=True, text=True, env=env, cwd=ROOT)
    if proc.returncode == 0:
        manifest = json.loads(proc.stdout.strip().splitlines()[-1])
    else:
        manifest = {'error': proc.stderr[-2000:]}
    manifest['projects'] = sorted(summaries)
    write_json(os.path.join(out_root, 'environment.json'), manifest)
    return summaries, failures


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('projects', nargs='*')
    parser.add_argument('--out', default=DEFAULT_OUT)
    parser.add_argument('--single', help=argparse.SUPPRESS)
    parser.add_argument('--environment', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--hash-seed', default='0',
                        help='PYTHONHASHSEED for the capture subprocesses (default 0)')
    args = parser.parse_args(argv)

    if args.single:
        run_single(args.single, args.out)
        return 0
    if args.environment:
        import legacy
        legacy.isolate_environment()
        misc = legacy.import_legacy()[1]
        manifest = environment_manifest(misc)
        session = legacy.LegacySession()
        try:
            manifest['registered_element_codes'] = sorted(
                session.project.program_state['element_models'])
            manifest['dark_mode'] = session.project.program_state['dark_mode']
        finally:
            session.close()
        print(json.dumps(canon(manifest)))
        return 0

    projects = args.projects or default_projects()
    summaries, failures = capture_all(projects, args.out, args.hash_seed)
    for name, output in failures:
        print('\n==== %s ====\n%s' % (name, output), file=sys.stderr)
    print('%d/%d projects captured into %s' % (len(summaries), len(projects), args.out))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
