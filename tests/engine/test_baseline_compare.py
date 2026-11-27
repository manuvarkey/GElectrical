"""Baseline comparison helpers (tools/baseline/canonical.py)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), 'tools', 'baseline'))

import canonical  # noqa: E402


def test_signed_zero_is_normalized_in_text():
    n = canonical.normalize_signed_zero
    assert n('1.0 < -0.0') == '1.0 < 0.0'
    assert n('[-0.0 | μ: 0.0 | -0.0]') == '[0.0 | μ: 0.0 | 0.0]'
    assert n('| -0') == '| 0'
    # Only the sign of an exact zero token is ignored
    for text in ('-0.05', '-0.001', '-0.0e5', 'x-0.0', 'a -10', '-1.0'):
        assert n(text) == text


def test_compare_ignores_sign_of_zero_in_strings_only():
    assert canonical.compare({'v': 'Pa: [-0.0 | 0.0]'}, {'v': 'Pa: [0.0 | 0.0]'}, 'results.json') == []
    assert canonical.compare({'v': '-0.1'}, {'v': '0.1'}, 'results.json') != []
