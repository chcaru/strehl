from __future__ import annotations

import inspect
import math
import unittest

import numpy as np

import checker


def signed_manifest(depths: list[int]) -> dict:
    sites = [
        {
            "best_node": depth,
            "eligible": True,
            "election_regularized": [None] * 31,
            "site_id": f"site-{index}",
            "x": 128 * index,
            "y": 0,
        }
        for index, depth in enumerate(depths)
    ]
    unsigned = {
        "capture_id": "unit",
        "definitions_sha256": checker.DEFINITIONS_SHA256,
        "eligible_count": len(sites),
        "input_digest": "unit-input",
        "node_count": 31,
        "protocol": checker.PROTOCOL,
        "site_count": len(sites),
        "sites": sites,
    }
    return unsigned | {"manifest_sha256": checker.payload_sha256(unsigned)}


class M5CheckerTests(unittest.TestCase):
    def test_manifest_builder_has_no_candidate_input(self) -> None:
        parameters = inspect.signature(checker.build_manifest).parameters
        self.assertNotIn("candidate", parameters)
        manifest_parser = next(
            action
            for action in checker.parser()._subparsers._group_actions
            if action.dest == "command"
        ).choices["manifest"]
        destinations = {action.dest for action in manifest_parser._actions}
        self.assertNotIn("candidate", destinations)

    def test_one_sided_wilson_convention(self) -> None:
        expected_all_success = 500.0 / (500.0 + checker.WILSON_Z**2)
        self.assertAlmostEqual(
            checker.wilson_lower(500, 500), expected_all_success, places=15
        )
        self.assertLess(checker.wilson_lower(495, 500), 0.98)
        self.assertGreater(checker.wilson_lower(496, 500), 0.98)

    def test_wilson_aggregation_collapses_same_physical_site(self) -> None:
        def score(candidate: str, failed: set[int]) -> dict:
            return {
                "candidate_id": candidate,
                "capture_id": "same-session",
                "site_rows": [
                    {
                        "passed": index not in failed,
                        "site_id": f"site-{index:03d}",
                    }
                    for index in range(160)
                ],
            }

        result = checker.aggregate_scores(
            [score("required-a", set()), score("required-b", {7})]
        )
        row = result["per_capture"]["same-session"]
        self.assertEqual(row["outputs_collapsed"], 2)
        self.assertEqual(row["eligible_physical_sites"], 160)
        self.assertEqual(row["passed_physical_sites"], 159)
        self.assertEqual(result["pooled"]["eligible_physical_sites"], 160)
        self.assertFalse(result["pooled"]["minimum_sites_pass"])

    def test_wilson_aggregation_uses_required_output_intersection(self) -> None:
        result = checker.aggregate_scores(
            [
                {
                    "candidate_id": "a",
                    "capture_id": "session",
                    "site_rows": [
                        {"passed": True, "site_id": "shared"},
                        {"passed": True, "site_id": "only-a"},
                    ],
                },
                {
                    "candidate_id": "b",
                    "capture_id": "session",
                    "site_rows": [
                        {"passed": False, "site_id": "shared"},
                        {"passed": True, "site_id": "only-b"},
                    ],
                },
            ]
        )
        row = result["per_capture"]["session"]
        self.assertEqual(row["eligible_physical_sites"], 1)
        self.assertEqual(row["passed_physical_sites"], 0)
        self.assertEqual(
            row["excluded_not_eligible_in_every_required_output"], 2
        )

    def test_pooled_wilson_uses_distinct_capture_site_units(self) -> None:
        scores = []
        for capture in range(4):
            scores.append(
                {
                    "candidate_id": f"candidate-{capture}",
                    "capture_id": f"capture-{capture}",
                    "site_rows": [
                        {"passed": True, "site_id": f"site-{index:03d}"}
                        for index in range(160)
                    ],
                }
            )
        result = checker.aggregate_scores(scores)
        self.assertEqual(result["pooled"]["eligible_physical_sites"], 640)
        self.assertTrue(result["pooled"]["rate_pass"])

    def test_nonplanar_run_is_order_invariant(self) -> None:
        depths = np.asarray([8, 2, 5, 2, 11, 8, 5])
        passed = np.asarray([False, True, False, False, True, True, True])
        first = checker.failed_run(depths, passed)
        permutation = np.asarray([4, 1, 6, 0, 3, 5, 2])
        second = checker.failed_run(depths[permutation], passed[permutation])
        self.assertEqual(first, second)
        # Duplicate depth 2 fails because one of its two physical sites fails.
        self.assertIn(2, first["failed_depths"])

    def test_single_depth_is_unmeasured_not_zero(self) -> None:
        result = checker.failed_run(np.asarray([7, 7]), np.asarray([True, True]))
        self.assertFalse(result["measured"])
        self.assertIsNone(result["fraction"])

    def test_coherence_is_gain_invariant(self) -> None:
        source = np.asarray(
            [
                [1.0 + 2.0j, 3.0 - 1.0j, -0.5 + 0.2j],
                [2.0 - 1.0j, -1.0 + 0.5j, 0.3 + 0.7j],
            ]
        )
        base = checker.coherence(source[0], source)
        scaled = checker.coherence(7.25 * source[0], source)
        np.testing.assert_allclose(base, scaled, rtol=0.0, atol=1.0e-15)
        self.assertAlmostEqual(float(base[0]), 1.0, places=15)

    def test_fov_counts_reference_area_not_bbox(self) -> None:
        reference = np.ones((10, 10), dtype=bool)
        output = reference.copy()
        output[:, :1] = False
        self.assertEqual(checker.retained_fov(reference, output), 0.9)
        output[:, :1] = True
        output[4:6, 4:9] = False
        self.assertEqual(checker.retained_fov(reference, output), 0.9)

    def test_manifest_hash_rejects_tampering(self) -> None:
        manifest = signed_manifest([5, 6, 7])
        checker.validate_manifest(manifest)
        manifest["sites"][0]["best_node"] = 9
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            checker.validate_manifest(manifest)

    def test_slab_is_shortest_then_earliest(self) -> None:
        manifest = signed_manifest(list(range(5, 26)))
        slab = checker.choose_depth_slab(manifest)
        self.assertEqual(slab["length_nodes"], 3)
        self.assertEqual(slab["start_node"], 5)
        self.assertGreaterEqual(slab["covered_depth_fraction"], 0.10)

    def test_zero_energy_coherence_fails_closed(self) -> None:
        result = checker.coherence(
            np.zeros(3, dtype=np.complex128),
            np.ones((2, 3), dtype=np.complex128),
        )
        np.testing.assert_array_equal(result, np.zeros(2))
        self.assertTrue(np.all(np.isfinite(result)))

    def test_regularizer_preserves_constant_interior(self) -> None:
        curve = np.full((2, 12), 3.25)
        result = checker.regularize_curve(curve)
        np.testing.assert_allclose(result[:, 1:-1], 3.25)
        self.assertTrue(np.all(np.isnan(result[:, (0, -1)])))

    def test_definitions_hash_is_lowercase_sha256(self) -> None:
        self.assertEqual(len(checker.DEFINITIONS_SHA256), 64)
        self.assertTrue(
            all(character in "0123456789abcdef" for character in checker.DEFINITIONS_SHA256)
        )
        self.assertTrue(math.isfinite(checker.WILSON_Z))


if __name__ == "__main__":
    unittest.main(verbosity=2)
