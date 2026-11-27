#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Measure the cost of snapshot transactions (ADR 0009, milestone M4).

For each project: elements, serialized size, snapshot capture time, the
time of a one-field command (capture + diff), undo and redo, and a delete
(rebuild of changed elements on undo). A synthetic project with many
elements is built through the services first (``--synthetic N``).

    pixi run python tools/measure_services.py [--synthetic 2000] [files...]
"""

import argparse
import json
import os
import statistics
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.modules.setdefault('gi', None)
os.environ.setdefault('GELECTRICAL_USER_DATA_DIR', tempfile.mkdtemp(prefix='gelectrical_measure_'))

from modern.backend import document  # noqa: E402
from modern.backend.runtime import Runtime  # noqa: E402
from modern.backend.services.settings import SettingsStore  # noqa: E402


def timed(func, repeat=5):
    values = []
    for _ in range(repeat):
        start = time.perf_counter()
        func()
        values.append((time.perf_counter() - start) * 1000)
    return round(statistics.median(values), 2)


def build_synthetic(runtime, count, path):
    sheet = runtime.call('project.state')['sheets'][0]['uid']
    sheets = [sheet]
    for _ in range(max(0, count // 200 - 1)):
        sheets.append(runtime.call('drawing.add_sheet', {})['value']['uid'])
    for n in range(count):
        target = sheets[n % len(sheets)]
        x = 64 + (n // len(sheets)) % 40 * 48
        y = 64 + (n // len(sheets)) // 40 * 160
        runtime.call('drawing.insert', {'sheet': target, 'code': 'element_load', 'x': x, 'y': y})
    runtime.call('project.save_as', {'path': path})
    return path


def measure(runtime, path):
    runtime.call('project.open', {'path': path})
    session = runtime.get_session()

    def on_owner(func):
        return lambda: runtime.run_on_owner(func).result()

    project = session.project
    elements = sum(len(document.stored_elements(d)) for d in project.drawing_models)
    settings, pages = document.storage_model(project)
    size = len(json.dumps([settings, pages]))
    capture_ms = timed(on_owner(lambda: document.capture(session.project)))
    sheet = runtime.call('project.state')['sheets'][0]['uid']
    uid = [e['uid'] for e in runtime.call('drawing.sheet', {'sheet': sheet})['elements'] if 'ref' in e['fields']][-1]
    counter = iter(range(10 ** 6))
    command_ms = timed(lambda: runtime.call('drawing.set_fields',
                                            {'uids': [uid], 'values': {'ref': 'M%d' % next(counter)}}))
    undo_ms = timed(lambda: runtime.call('history.undo'))
    redo_ms = timed(lambda: runtime.call('history.redo'))
    first = runtime.call('drawing.sheet', {'sheet': sheet})['elements'][0]['uid']
    start = time.perf_counter()
    runtime.call('drawing.delete', {'uids': [first]})
    delete_ms = round((time.perf_counter() - start) * 1000, 2)
    start = time.perf_counter()
    runtime.call('history.undo')
    undo_delete_ms = round((time.perf_counter() - start) * 1000, 2)
    return {'project': os.path.relpath(path, ROOT) if path.startswith(ROOT) else os.path.basename(path),
            'elements': elements, 'json_kb': round(size / 1024, 1), 'capture_ms': capture_ms,
            'set_field_ms': command_ms, 'undo_ms': undo_ms, 'redo_ms': redo_ms,
            'delete_ms': delete_ms, 'undo_delete_ms': undo_delete_ms}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('files', nargs='*')
    parser.add_argument('--synthetic', type=int, default=2000, help='elements of the synthetic project (0: none)')
    args = parser.parse_args(argv)
    files = args.files or [os.path.join(ROOT, 'sample_files', 'sample.gepro'),
                           os.path.join(ROOT, 'tests', 'projects', 'cov_multisheet.gepro')]
    runtime = Runtime(settings=SettingsStore(os.environ['GELECTRICAL_USER_DATA_DIR'], persist=False))
    rows = []
    try:
        if args.synthetic:
            path = os.path.join(tempfile.mkdtemp(prefix='gelectrical_synthetic_'), 'synthetic.gepro')
            build_synthetic(runtime, args.synthetic, path)
            files = files + [path]
        for filename in files:
            rows.append(measure(runtime, os.path.abspath(filename)))
    finally:
        runtime.close()
    keys = list(rows[0])
    print('| ' + ' | '.join(keys) + ' |')
    print('|' + ' --- |' * len(keys))
    for row in rows:
        print('| ' + ' | '.join(str(row[k]) for k in keys) + ' |')


if __name__ == '__main__':
    main()
