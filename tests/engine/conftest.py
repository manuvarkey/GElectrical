"""Engine unit tests (M2): run without GTK or a display.

``gi`` is blocked for the whole session so that an accidental GTK import in
engine code fails the tests.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

if 'gi' not in sys.modules:
    sys.modules['gi'] = None
