#!/usr/bin/env python3
"""Compare two baseline captures with the documented tolerances.

Used by ``tests/test_baseline.py`` and on the command line to check that two
captures are identical within tolerance (M1 determinism check)::

    pixi run -e test python tools/baseline/compare.py ACTUAL_DIR EXPECTED_DIR

No GTK import: works on any machine with NumPy (PNG comparison needs pycairo).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import canonical  # noqa: E402

INFORMATIONAL = ('environment.json',)


def list_files(root):
    files = set()
    for folder, _, names in os.walk(root):
        for name in names:
            files.add(os.path.relpath(os.path.join(folder, name), root).replace(os.sep, '/'))
    return files


def fonts_match(actual_root, expected_root):
    """True when both captures resolved the same drawing fonts."""
    try:
        a = canonical.read_json(os.path.join(actual_root, 'environment.json')).get('fonts')
        b = canonical.read_json(os.path.join(expected_root, 'environment.json')).get('fonts')
    except (OSError, ValueError):
        return False
    return a is not None and a == b


def png_difference(actual, expected):
    """Fraction of pixels whose colour differs by more than the AA tolerance."""
    import cairo
    import numpy as np
    sa = cairo.ImageSurface.create_from_png(actual)
    sb = cairo.ImageSurface.create_from_png(expected)
    if (sa.get_width(), sa.get_height()) != (sb.get_width(), sb.get_height()):
        return 1.0
    shape = (sa.get_height(), sa.get_stride())
    da = np.frombuffer(sa.get_data(), dtype=np.uint8).reshape(shape)[:, :sa.get_width() * 4]
    db = np.frombuffer(sb.get_data(), dtype=np.uint8).reshape(shape)[:, :sb.get_width() * 4]
    da = da.reshape(sa.get_height(), sa.get_width(), 4)[:, :, :3].astype(int)
    db = db.reshape(sb.get_height(), sb.get_width(), 4)[:, :, :3].astype(int)
    differing = (np.abs(da - db) > canonical.DRAWING_CHANNEL_TOLERANCE).any(axis=2)
    return float(differing.mean())


def compare_project(actual_dir, expected_dir, compare_drawings=True):
    """Return (failures, notes) for one project folder."""
    failures, notes = [], []
    actual_files, expected_files = list_files(actual_dir), list_files(expected_dir)
    for missing in sorted(expected_files - actual_files):
        failures.append('%s: missing in capture' % missing)
    for extra in sorted(actual_files - expected_files):
        failures.append('%s: not in baseline' % extra)
    for rel in sorted(actual_files & expected_files):
        a, b = os.path.join(actual_dir, rel), os.path.join(expected_dir, rel)
        name = os.path.basename(rel)
        if name.endswith('.json'):
            diffs = canonical.compare(canonical.read_json(a), canonical.read_json(b), name)
            failures.extend('%s: %s' % (rel, d) for d in diffs)
        elif name.endswith('.txt'):
            with open(a, encoding='utf-8') as fa, open(b, encoding='utf-8') as fb:
                ta, tb = fa.read().splitlines(), fb.read().splitlines()
            if ta != tb:
                import difflib
                diff = list(difflib.unified_diff(tb, ta, 'baseline', 'capture', lineterm='', n=1))
                failures.append('%s: text differs\n%s' % (rel, '\n'.join(diff[:40])))
        elif name.endswith('.png'):
            if not compare_drawings:
                notes.append('%s: skipped (font resolution differs from baseline)' % rel)
                continue
            fraction = png_difference(a, b)
            if fraction > canonical.DRAWING_PIXEL_FRACTION:
                failures.append('%s: %.4f %% pixels differ (limit %.2f %%)'
                                % (rel, fraction * 100, canonical.DRAWING_PIXEL_FRACTION * 100))
        else:
            with open(a, 'rb') as fa, open(b, 'rb') as fb:
                if fa.read() != fb.read():
                    failures.append('%s: bytes differ' % rel)
    return failures, notes


def environment_differences(actual_root, expected_root):
    try:
        a = canonical.read_json(os.path.join(actual_root, 'environment.json'))
        b = canonical.read_json(os.path.join(expected_root, 'environment.json'))
    except (OSError, ValueError) as exc:
        return ['environment.json unreadable: %s' % exc]
    keys = ('python', 'packages', 'pixi_lock_sha256', 'fonts', 'system', 'gtk')
    return ['%s: capture %r, baseline %r' % (k, a.get(k), b.get(k))
            for k in keys if a.get(k) != b.get(k)]


def compare_roots(actual_root, expected_root):
    drawings = fonts_match(actual_root, expected_root)
    projects = sorted(d for d in os.listdir(expected_root)
                      if os.path.isdir(os.path.join(expected_root, d)))
    result = {}
    for name in projects:
        actual_dir = os.path.join(actual_root, name)
        if not os.path.isdir(actual_dir):
            result[name] = (['project missing in capture'], [])
            continue
        result[name] = compare_project(actual_dir, os.path.join(expected_root, name), drawings)
    for name in sorted(os.listdir(actual_root)):
        if os.path.isdir(os.path.join(actual_root, name)) and name not in result:
            result[name] = (['project not in baseline'], [])
    return result


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    actual_root, expected_root = argv
    for line in environment_differences(actual_root, expected_root):
        print('ENV ', line)
    result = compare_roots(actual_root, expected_root)
    bad = 0
    for name, (failures, notes) in result.items():
        status = 'FAIL' if failures else 'OK  '
        bad += bool(failures)
        print(status, name)
        for line in failures[:30] + notes:
            print('     ', line)
    print('%d/%d projects identical within tolerance' % (len(result) - bad, len(result)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
