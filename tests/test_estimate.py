"""Estimation helpers: the multiple-testing adjustment and the plan's reading rule."""
import numpy as np
import pytest
from statsmodels.stats.multitest import multipletests

from embanks import estimate


def test_holm_matches_statsmodels():
    p = np.random.default_rng(0).uniform(0, 0.2, 16)
    assert np.allclose(estimate.holm(p), multipletests(p, method="holm")[1])


@pytest.mark.parametrize("lo_s, hi_s, effect, expected", [
    (0.1, 0.5, 0.3, "relationship, small: higher"),      # inside the band of 0.25 x 2 = 0.5
    (0.4, 1.2, 0.8, "relationship, large: higher"),
    (-0.3, 0.2, -0.05, "no large effect"),
    (-0.9, 0.2, -0.35, "can't tell"),
])
def test_reading_follows_the_plan(lo_s, hi_s, effect, expected):
    row = {"lo_s": lo_s, "hi_s": hi_s, "effect": effect, "sd_y": 2.0}
    assert estimate.read(row, 0.25).startswith(expected)
