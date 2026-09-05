from __future__ import annotations

import unittest

import numpy as np

from commission_m3_side_max import (
    PROFILE_OFFSETS,
    SOURCE_TRACE_OFFSETS,
    TraceLocation,
    allocate_trace_locations,
    evaluate_side_asymmetry,
    extract_empirical_trace,
    load_canonical_checker,
    load_frozen_sites,
    load_study_definition,
    verify_frozen_dependencies,
)
from census_common import load_definition


class M3SideMaxCommissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.study, _ = load_study_definition()

    def test_canonical_checker_hashes_are_pinned(self) -> None:
        checker, definition, definition_hash = load_canonical_checker(self.study)
        self.assertEqual(
            definition_hash,
            self.study["authority"]["canonical_definition_sha256"],
        )
        self.assertTrue(hasattr(checker, "score_site"))
        self.assertEqual(
            definition["veil"]["reduction"],
            "maximum of the two signed-side arithmetic means",
        )

    def test_historical_and_local_dependencies_are_pinned(self) -> None:
        _, census_definition_hash = load_definition()
        verify_frozen_dependencies(self.study, census_definition_hash)

    def test_population_is_exactly_the_frozen_500(self) -> None:
        sites = load_frozen_sites(self.study)
        self.assertEqual(len(sites), 500)
        self.assertEqual(len({site["site_id"] for site in sites}), 500)

    def test_trace_allocation_is_deterministic_and_line_unique(self) -> None:
        sites = load_frozen_sites(self.study)
        first = allocate_trace_locations(sites, (2344, 3514), 123)
        second = allocate_trace_locations(sites, (2344, 3514), 123)
        self.assertEqual(first, second)
        horizontal = [
            item.line for item in first if item.orientation == "horizontal"
        ]
        vertical = [item.line for item in first if item.orientation == "vertical"]
        self.assertEqual(len(horizontal), len(set(horizontal)))
        self.assertEqual(len(vertical), len(set(vertical)))

    def test_trace_interpolation_and_reversal(self) -> None:
        image = np.tile(np.arange(1000, dtype=np.float64), (1000, 1))
        location = TraceLocation("horizontal", line=10, center=500, reverse=False)
        forward = extract_empirical_trace(image, location)
        reverse = extract_empirical_trace(
            image, TraceLocation("horizontal", 10, 500, True)
        )
        self.assertEqual(forward.size, PROFILE_OFFSETS.size)
        self.assertEqual(SOURCE_TRACE_OFFSETS.size, 403)
        np.testing.assert_allclose(reverse, forward[::-1], rtol=0.0, atol=0.0)
        self.assertAlmostEqual(forward[0], 300.0)
        self.assertAlmostEqual(forward[-1], 700.0)

    def test_side_max_bounds_pooled_mean(self) -> None:
        rng = np.random.default_rng(152)
        negative = rng.uniform(1.0e-6, 0.1, size=1000)
        positive = rng.uniform(1.0e-6, 0.1, size=1000)
        legacy = 0.5 * (negative + positive)
        amended = np.maximum(negative, positive)
        self.assertTrue(np.all(amended >= legacy))
        self.assertTrue(np.all(amended <= 2.0 * legacy))

    def test_exercise_gate_rejects_equal_sides(self) -> None:
        negative = np.full(500, 0.002)
        positive = negative.copy()
        ratios = np.ones(500)
        metrics, passed = evaluate_side_asymmetry(
            negative,
            positive,
            ratios,
            self.study["empirical_noise"]["exercise_gate"],
        )
        self.assertFalse(passed)
        self.assertEqual(metrics["asymmetric_site_count"], 0)

    def test_exercise_gate_accepts_two_sided_asymmetry(self) -> None:
        negative = np.concatenate([np.full(250, 0.0022), np.full(250, 0.0018)])
        positive = np.full(500, 0.002)
        legacy = 0.5 * (negative + positive)
        ratios = np.maximum(negative, positive) / legacy
        metrics, passed = evaluate_side_asymmetry(
            negative,
            positive,
            ratios,
            self.study["empirical_noise"]["exercise_gate"],
        )
        self.assertTrue(passed)
        self.assertEqual(metrics["negative_side_dominates_count"], 250)
        self.assertEqual(metrics["positive_side_dominates_count"], 250)


if __name__ == "__main__":
    unittest.main()
