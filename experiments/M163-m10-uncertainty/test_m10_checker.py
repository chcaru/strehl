from __future__ import annotations

import unittest

import numpy as np

from m10_checker import UncertaintyInput, score_legacy, score_repaired


PASSING_VALUES = {
    "valid_fraction": 1.0,
    "rank_correlation": 1.0,
    "median_abs_error_steps": 0.0,
    "p95_abs_error_steps": 0.0,
    "ruler_slope_error_fraction": 0.0,
    "flat_null_p95_range_steps": 0.0,
    "synthetic_layer_confusion_fraction": 0.0,
}


class M10CheckerTests(unittest.TestCase):
    def test_legacy_decision_is_invariant_to_reported_uncertainty(self) -> None:
        zero = score_legacy(PASSING_VALUES, np.zeros(10_000))
        infinite = score_legacy(PASSING_VALUES, np.full(10_000, np.inf))
        random = score_legacy(
            PASSING_VALUES, np.random.default_rng(7).uniform(0.0, 100.0, 10_000)
        )
        self.assertEqual(zero, infinite)
        self.assertEqual(zero, random)
        self.assertTrue(zero["pass"])

    def test_nonfinite_uncertainty_fails_without_throwing(self) -> None:
        n = 10_000
        result = score_repaired(
            PASSING_VALUES,
            UncertaintyInput(
                residual_steps=np.zeros(n),
                candidate_sigma_steps=np.full(n, np.inf),
                truth_sigma_steps=np.zeros(n),
                valid=np.ones(n, dtype=bool),
            ),
        )
        self.assertFalse(result["pass"])
        self.assertEqual(
            result["uncertainty"]["metrics"]["reported_sigma_fraction"], 0.0
        )

    def test_exact_truth_with_exact_zero_uncertainty_passes(self) -> None:
        n = 10_000
        result = score_repaired(
            PASSING_VALUES,
            UncertaintyInput(
                residual_steps=np.zeros(n),
                candidate_sigma_steps=np.zeros(n),
                truth_sigma_steps=np.zeros(n),
                valid=np.ones(n, dtype=bool),
            ),
        )
        self.assertTrue(result["pass"])
        self.assertTrue(
            result["uncertainty"]["metrics"]["exact_zero_error_zero_uncertainty"]
        )

    def test_shape_mismatch_fails_without_throwing(self) -> None:
        result = score_repaired(
            PASSING_VALUES,
            UncertaintyInput(
                residual_steps=np.zeros(10_000),
                candidate_sigma_steps=np.zeros(9_999),
                truth_sigma_steps=np.zeros(10_000),
                valid=np.ones(10_000, dtype=bool),
            ),
        )
        self.assertFalse(result["pass"])
        self.assertFalse(result["uncertainty"]["components"]["shapes_match"])


if __name__ == "__main__":
    unittest.main()
