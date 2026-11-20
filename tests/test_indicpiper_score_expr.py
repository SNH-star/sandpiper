"""api.api.indicpiper_score_expr: IndicPiper thresholds typed as a fraction or a percentage."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from api.api import indicpiper_score_expr  # noqa: E402


@pytest.mark.parametrize('typed, stored', [
    ('>=0.1', '>=0.1'),      # 0-1 is already a fraction
    ('>0.5', '>0.5'),
    ('>=10', '>=0.1'),       # 1-100 is a percentage
    ('> 50', '>0.5'),
    ('<=100', '<=1'),
    ('>=1', '>=0.01'),       # 1 means 1%, not 100%
    ('<1', '<0.01'),
    ('>0', '>0'),
])
def test_accepts_fractions_and_percentages(typed, stored):
    assert indicpiper_score_expr(typed) == stored


@pytest.mark.parametrize('typed', ['>=200', '>100.5', '<-1', 'soil', '=5', ''])
def test_rejects_out_of_range_or_malformed(typed):
    assert indicpiper_score_expr(typed) is None
