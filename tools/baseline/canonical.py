"""Canonical JSON form and tolerance comparison for the regression baseline.

This module has no GTK or GElectrical imports, so the comparison side of the
baseline (``tests/test_baseline.py``) and future headless engines can use it.

Normalization rules (docs/migration/regression-baseline.md section 4):

* dict keys become strings and are sorted on output;
* tuples become lists, sets become sorted lists;
* NumPy scalars become Python numbers, NumPy arrays become lists;
* ``NaN``/``inf`` are written as the strings ``"NaN"``, ``"Infinity"`` and
  ``"-Infinity"``;
* floats are written with ``repr`` precision (lossless round trip).

Tolerances (section 3) are applied by :func:`compare`, which walks two
canonical trees and returns human-readable differences.
"""

import json
import math
import re

NAN = 'NaN'
POS_INF = 'Infinity'
NEG_INF = '-Infinity'
SPECIAL_FLOATS = (NAN, POS_INF, NEG_INF)


# ---------------------------------------------------------------------------
# Canonical form
# ---------------------------------------------------------------------------

def _key(value):
    """Return a string dict key for any hashable value."""
    if isinstance(value, str):
        return value
    if isinstance(value, tuple):
        return str(tuple(_plain_key_part(v) for v in value))
    return str(_plain_key_part(value))


def _plain_key_part(value):
    try:
        import numpy as np
        if isinstance(value, np.generic):
            return value.item()
    except ImportError:  # pragma: no cover
        pass
    if isinstance(value, tuple):
        return tuple(_plain_key_part(v) for v in value)
    return value


def canon(obj):
    """Return ``obj`` converted to plain JSON-compatible Python data."""
    # Local import keeps this module importable without NumPy/pandas.
    try:
        import numpy as np
    except ImportError:  # pragma: no cover
        np = None
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        pd = None

    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj):
            return NAN
        if math.isinf(obj):
            return POS_INF if obj > 0 else NEG_INF
        return obj
    if np is not None:
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return canon(float(obj))
        if isinstance(obj, np.ndarray):
            return [canon(v) for v in obj.tolist()]
    if pd is not None:
        if isinstance(obj, pd.DataFrame):
            return dataframe_to_canon(obj)
        if obj is pd.NA or obj is pd.NaT:
            return NAN
    if isinstance(obj, dict):
        return {_key(k): canon(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [canon(v) for v in obj]
    if isinstance(obj, (set, frozenset)):
        items = [canon(v) for v in obj]
        return sorted(items, key=lambda v: json.dumps(v, sort_keys=True))
    if callable(obj):
        return None
    return repr(obj)


def dataframe_to_canon(df):
    """DataFrame -> {row_index: {column: value}} with string keys."""
    result = {}
    for index, row in df.iterrows():
        result[_key(index)] = {str(col): canon(row[col]) for col in df.columns}
    return result


def dumps(obj):
    """Serialize canonical data deterministically."""
    return json.dumps(canon(obj), sort_keys=True, indent=1, ensure_ascii=False,
                      allow_nan=False) + '\n'


def write_json(path, obj):
    with open(path, 'w', encoding='utf-8', newline='\n') as fp:
        fp.write(dumps(obj))


def read_json(path):
    with open(path, 'r', encoding='utf-8') as fp:
        return json.load(fp)


# ---------------------------------------------------------------------------
# Tolerances
# ---------------------------------------------------------------------------

# (abs_tol, rel_tol) pairs from regression-baseline.md section 3.
TOL_FIELD = (1e-12, 1e-9)        # element field values, pandapower inputs
TOL_VM_PU = (1e-8, 0.0)          # bus voltage magnitude (p.u.)
TOL_ANGLE = (1e-6, 0.0)          # voltage angle (degrees)
TOL_FLOW = (1e-9, 1e-6)          # branch currents (kA), powers (MW/Mvar)
TOL_PERCENT = (1e-6, 1e-6)       # loading, losses, voltage drop (%)
TOL_SC = (1e-9, 1e-7)            # short-circuit currents (kA), impedances (ohm)
TOL_CURVE = (1e-12, 1e-9)        # curve points (A, s)
TOL_POLYGON = (1e-9, 1e-9)       # polygon vertices
EXACT = None

DRAWING_PIXEL_FRACTION = 0.001   # at most 0.1 % differing pixels
DRAWING_CHANNEL_TOLERANCE = 32   # anti-aliasing tolerance per colour channel
# Headless engine with the Cairo toy text API (owner decision, M2, 2026-11-27):
# glyph rendering differs from the PangoCairo baseline, geometry does not.
# Applies only to headless captures with Cairo text; all other captures use
# DRAWING_PIXEL_FRACTION.
HEADLESS_CAIRO_TEXT_PIXEL_FRACTION = 0.01   # at most 1 % differing pixels

_PERCENT_UNITS = ('%',)
_ANGLE_RE = re.compile(r'(^|_)va(_|$)|degree')
_PERCENT_RE = re.compile(r'loading|percent|perc|delv')
_VM_RE = re.compile(r'(^|_)vm(_|$)')


def _column_tolerance(column):
    """Tolerance for a pandapower result column name."""
    if _VM_RE.search(column):
        return TOL_VM_PU
    if _ANGLE_RE.search(column):
        return TOL_ANGLE
    if _PERCENT_RE.search(column):
        return TOL_PERCENT
    return TOL_FLOW


def _sc_column_tolerance(column):
    if _VM_RE.search(column):
        return TOL_VM_PU
    if _ANGLE_RE.search(column):
        return TOL_ANGLE
    return TOL_SC


def _result_field_tolerance(code, unit):
    """Tolerance for an element/node ``res_fields`` entry."""
    if code.startswith(('ikss', 'ipss', 'zk', 'ith', 'ip_')) or '_sc' in code:
        return TOL_SC
    if unit in _PERCENT_UNITS:
        return TOL_PERCENT
    if unit in ('pu', 'p.u.') or code.startswith('vm'):
        return TOL_VM_PU
    if unit in ('°', 'deg', 'degree'):
        return TOL_ANGLE
    return TOL_FLOW


def tolerance_for(artefact, path, unit=''):
    """Return ``(abs_tol, rel_tol)`` for a float at ``path`` or ``None``.

    ``artefact`` is the file name (``model.json``, ``pf.json`` ...), ``path``
    the list of keys/indices from the document root to the value and
    ``unit`` the ``unit`` entry of the enclosing field dict, if any.
    """
    keys = [p for p in path if isinstance(p, str)]
    if artefact in ('model.json', 'roundtrip.json', 'pp_input.json', 'd8.json'):
        return TOL_FIELD
    if artefact == 'curves.json':
        if 'polygon' in keys or 'polygon_log' in keys:
            return TOL_POLYGON
        return TOL_CURVE
    if artefact == 'pf.json':
        return _column_tolerance(keys[-1]) if keys else TOL_FLOW
    if artefact == 'sc.json':
        return _sc_column_tolerance(keys[-1]) if keys else TOL_SC
    if artefact in ('results.json', 'node_results.json'):
        # path: <element or node>, <field code>, ... 'value' [, graph data]
        if len(keys) >= 2:
            return _result_field_tolerance(keys[1], unit)
        return TOL_FLOW
    if artefact == 'topology.json':
        # r_grid / DF values are field-derived
        return TOL_FIELD
    if artefact in ('undo.json', 'renumber.json', 'diagnostics.json',
                    'rules.json', 'status.json'):
        return EXACT
    return EXACT


def _close(a, b, tol):
    abs_tol, rel_tol = tol
    return abs(a - b) <= abs_tol + rel_tol * abs(b)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def compare(actual, expected, artefact, max_diffs=50):
    """Compare two canonical trees; return a list of difference strings.

    ``expected`` is the stored baseline, ``actual`` the fresh capture.
    Floats use :func:`tolerance_for`; everything else must be equal.
    """
    diffs = []
    stats = {'max_abs': 0.0, 'compared': 0}

    def fmt(path):
        return '/'.join(str(p) for p in path) or '<root>'

    def walk(a, b, path, unit):
        if len(diffs) >= max_diffs:
            return
        if isinstance(b, dict):
            if not isinstance(a, dict):
                diffs.append('%s: type %s != %s' % (fmt(path), type(a).__name__, 'dict'))
                return
            missing = sorted(set(b) - set(a))
            extra = sorted(set(a) - set(b))
            if missing:
                diffs.append('%s: missing keys %s' % (fmt(path), missing[:10]))
            if extra:
                diffs.append('%s: unexpected keys %s' % (fmt(path), extra[:10]))
            field_unit = b.get('unit', unit) if isinstance(b.get('unit', None), str) else unit
            for k in sorted(set(a) & set(b)):
                walk(a[k], b[k], path + [k], field_unit)
            return
        if isinstance(b, list):
            if not isinstance(a, list):
                diffs.append('%s: type %s != list' % (fmt(path), type(a).__name__))
                return
            if len(a) != len(b):
                diffs.append('%s: length %d != %d' % (fmt(path), len(a), len(b)))
                return
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, path + [i], unit)
            return
        if _is_number(b) and _is_number(a):
            stats['compared'] += 1
            if a == b:
                return
            tol = tolerance_for(artefact, path, unit)
            delta = abs(a - b)
            stats['max_abs'] = max(stats['max_abs'], delta)
            if tol is None or not _close(a, b, tol):
                diffs.append('%s: %r != %r (|d|=%.3g, tol=%s)' % (fmt(path), a, b, delta, tol))
            return
        if a != b:
            diffs.append('%s: %r != %r' % (fmt(path), _short(a), _short(b)))

    walk(actual, expected, [], '')
    compare.last_stats = stats
    return diffs


compare.last_stats = {}


def _short(value, limit=120):
    text = repr(value)
    return text if len(text) <= limit else text[:limit] + '...'


# ---------------------------------------------------------------------------
# Text normalization (report.txt)
# ---------------------------------------------------------------------------

_DATE_PATTERNS = [
    re.compile(r'\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?([+-]\d{2}:?\d{2}|Z)?)?'),
    re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}'),
    re.compile(r'\b\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b'),
]


def normalize_text(text):
    """Remove dates and collapse whitespace line by line."""
    for pattern in _DATE_PATTERNS:
        text = pattern.sub('<DATE>', text)
    lines = [' '.join(line.split()) for line in text.splitlines()]
    return '\n'.join(line for line in lines if line) + '\n'
