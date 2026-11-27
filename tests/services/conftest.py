"""Service and protocol tests (milestone M4): headless, no GTK, no display.

``gi`` is blocked for the session. Program settings go to a temporary user
data directory (``GELECTRICAL_USER_DATA_DIR``).
"""

import os
import shutil
import sys
import tempfile
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if 'gi' not in sys.modules:
    sys.modules['gi'] = None

_DATA_DIR = tempfile.mkdtemp(prefix='gelectrical_services_')
os.environ['GELECTRICAL_USER_DATA_DIR'] = _DATA_DIR

SAMPLE = os.path.join(ROOT, 'sample_files', 'sample.gepro')
MULTISHEET = os.path.join(ROOT, 'tests', 'projects', 'cov_multisheet.gepro')
RADIAL = os.path.join(ROOT, 'tests', 'projects', 'cov_radial_lv.gepro')


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(_DATA_DIR, ignore_errors=True)


@pytest.fixture
def events():
    return []


@pytest.fixture
def runtime(events):
    from modern.backend.runtime import Runtime
    from modern.backend.services.settings import SettingsStore
    rt = Runtime(emit=events.append, settings=SettingsStore(_DATA_DIR, persist=False))
    yield rt
    rt.close()


def wait_job(runtime, job_id, session=None, timeout=300):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = runtime.call('analysis.job', {'job': job_id}, session=session)
        if job['status'] not in ('queued', 'running'):
            return job
        time.sleep(0.05)
    raise TimeoutError(job_id)


def first_sheet(runtime, session=None):
    return runtime.call('project.state', session=session)['sheets'][0]['uid']


def strip_uids(value):
    """Storage model without the additive identity keys"""
    if isinstance(value, dict):
        return {k: strip_uids(v) for k, v in value.items() if k not in ('uid', 'children_uids', 'app')}
    if isinstance(value, (list, tuple)):
        return [strip_uids(v) for v in value]
    return value
