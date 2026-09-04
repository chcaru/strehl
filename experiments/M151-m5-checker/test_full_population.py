from __future__ import annotations

import unittest

import cv2
import numpy as np

import commission
import full_population
from checker import build_manifest


class FullPopulationTests(unittest.TestCase):
    @staticmethod
    def peaked_prepared(best_node: int) -> dict[str, np.ndarray]:
        nodes = 15
        election = np.ones((1, nodes, 16), dtype=np.float64)
        evaluation = np.ones_like(election)
        election[:, (0, -1), :] = np.nan
        evaluation[:, (0, -1), :] = np.nan
        election[:, best_node, :] = 8.0
        evaluation[:, best_node, :] = 10.0
        return {
            "election_crosspower": election,
            "evaluation_crosspower": evaluation,
            "site_ids": np.asarray(["site"]),
            "site_xy": np.asarray([[0, 0]], dtype=np.int64),
        }

    def test_active_area_has_1944_complete_tiles(self) -> None:
        identifiers, coordinates, geometry = full_population.full_sites(4688, 7028)
        self.assertEqual(len(identifiers), 1944)
        self.assertEqual(coordinates.shape, (1944, 2))
        self.assertEqual(len({tuple(row) for row in coordinates.tolist()}), 1944)
        self.assertEqual(geometry["candidate_columns"], 54)
        self.assertEqual(geometry["candidate_rows"], 36)
        self.assertEqual(geometry["right_remainder_px"], 116)
        self.assertEqual(geometry["bottom_remainder_px"], 80)
        self.assertLessEqual(
            int(np.max(coordinates[:, 0])) + full_population.TILE_SIDE, 7028
        )
        self.assertLessEqual(
            int(np.max(coordinates[:, 1])) + full_population.TILE_SIDE, 4688
        )

    def test_batched_spectra_match_scalar_extractor(self) -> None:
        rng = np.random.default_rng(20260905)
        half_tiles = rng.random((7, 64, 64), dtype=np.float32)
        batched_election, batched_evaluation = full_population.block_spectra(
            half_tiles
        )
        for index, half_tile in enumerate(half_tiles):
            tile = cv2.resize(
                half_tile,
                (full_population.TILE_SIDE, full_population.TILE_SIDE),
                interpolation=cv2.INTER_LINEAR,
            )
            scalar_election, scalar_evaluation, _ = commission.tile_features(tile)
            np.testing.assert_allclose(
                batched_election[index],
                scalar_election,
                rtol=2.0e-6,
                atol=1.0e-5,
            )
            np.testing.assert_allclose(
                batched_evaluation[index],
                scalar_evaluation,
                rtol=2.0e-6,
                atol=1.0e-5,
            )

    def test_point_prefilter_preserves_exact_eligibility(self) -> None:
        nodes = 12
        election = np.ones((3, nodes, 16), dtype=np.float64)
        evaluation = np.ones_like(election)
        election[:, (0, -1), :] = np.nan
        evaluation[:, (0, -1), :] = np.nan
        election[:, 5, :] = 8.0
        evaluation[0, 5, :] = 4.0
        evaluation[1, 5, :] = 1.0
        evaluation[2, 5, :] = 1.8
        identifiers = ["passing", "flat", "subthreshold"]
        coordinates = np.asarray([[0, 0], [128, 0], [256, 0]], dtype=np.int64)

        complete = build_manifest(
            election,
            evaluation,
            identifiers,
            coordinates,
            input_digest="unit",
            capture_id="complete",
        )
        point = full_population.point_rows(election, evaluation)
        optimized, _ = full_population.exact_eligibility(
            {
                "election_crosspower": election,
                "evaluation_crosspower": evaluation,
                "site_ids": np.asarray(identifiers),
                "site_xy": coordinates,
            },
            capture_id="optimized",
        )

        self.assertEqual(int(np.count_nonzero(point["point_mask"])), 1)
        self.assertEqual(complete["eligible_count"], 1)
        self.assertEqual(optimized["bootstrap_eligible_count"], 1)
        self.assertEqual(optimized["bootstrap_tested_point_eligible"], 1)
        self.assertEqual(optimized["point_ineligible_skipped_bootstrap"], 2)

    def test_rehearsal_gate_averages_passes_before_election(self) -> None:
        peak_four = self.peaked_prepared(4)
        peak_ten = self.peaked_prepared(10)
        separate_four, _ = full_population.exact_eligibility(
            peak_four, capture_id="separate-four"
        )
        separate_ten, _ = full_population.exact_eligibility(
            peak_ten, capture_id="separate-ten"
        )
        self.assertEqual(separate_four["bootstrap_eligible_count"], 1)
        self.assertEqual(separate_ten["bootstrap_eligible_count"], 1)

        gate = full_population.rehearsal_gate(
            peak_four,
            peak_ten,
            peak_four,
            peak_ten,
            minimum=1,
        )
        self.assertFalse(gate["pass"])
        self.assertEqual(gate["counts"]["pass_averaged_sw4"], 0)
        self.assertEqual(gate["counts"]["pass_averaged_sw10"], 0)
        self.assertEqual(gate["counts"]["required_step_width_intersection"], 0)

        healthy = full_population.rehearsal_gate(
            peak_four,
            peak_four,
            peak_four,
            peak_four,
            minimum=1,
        )
        self.assertTrue(healthy["pass"])
        self.assertEqual(healthy["counts"]["required_step_width_intersection"], 1)

        shifted = {
            key: value.copy() for key, value in peak_four.items()
        }
        shifted["site_xy"] = np.asarray([[128, 0]], dtype=np.int64)
        mismatched_geometry = full_population.rehearsal_gate(
            peak_four,
            peak_four,
            shifted,
            shifted,
            minimum=1,
        )
        self.assertFalse(mismatched_geometry["pass"])
        self.assertEqual(
            mismatched_geometry["counts"]["required_step_width_intersection"],
            0,
        )

    def test_rehearsal_gate_rejects_duplicate_physical_coordinates(self) -> None:
        malformed = self.peaked_prepared(4)
        malformed["site_ids"] = np.asarray(["first", "second"])
        malformed["site_xy"] = np.asarray([[0, 0], [0, 0]], dtype=np.int64)
        malformed["election_crosspower"] = np.repeat(
            malformed["election_crosspower"], 2, axis=0
        )
        malformed["evaluation_crosspower"] = np.repeat(
            malformed["evaluation_crosspower"], 2, axis=0
        )
        with self.assertRaisesRegex(ValueError, "duplicate physical"):
            full_population.rehearsal_gate(
                malformed,
                malformed,
                malformed,
                malformed,
                minimum=1,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
