from __future__ import annotations

import math
import unittest

import numpy as np

import census
from census_common import (
    band_rms_tiles,
    canonical_json,
    deterministic_frame_indices,
    load_definition,
    nearest_rank,
    temporal_sigma_green_luma_dn,
)


class DeterminismTests(unittest.TestCase):
    def test_frame_indices_cover_endpoints_without_duplicates(self) -> None:
        indices = deterministic_frame_indices(299, 17)
        self.assertEqual(indices[0], 0)
        self.assertEqual(indices[-1], 298)
        self.assertEqual(len(indices), 17)
        self.assertEqual(len(set(indices)), 17)

    def test_short_stack_uses_every_frame(self) -> None:
        self.assertEqual(deterministic_frame_indices(4, 17), [0, 1, 2, 3])

    def test_nearest_rank_does_not_interpolate(self) -> None:
        values = np.arange(1.0, 101.0)
        self.assertEqual(nearest_rank(values, 0.99), 99.0)
        self.assertEqual(nearest_rank(values, 0.50), 50.0)

    def test_definition_is_ascii_canonicalizable(self) -> None:
        definition, digest = load_definition()
        canonical_json(definition).encode("ascii")
        self.assertEqual(len(digest), 64)


class NoiseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definition, _ = load_definition()
        self.model = self.definition["noise"]["temporal_model"]

    def test_temporal_sigma_increases_with_signal(self) -> None:
        dark = temporal_sigma_green_luma_dn(0.0, 100.0, self.model)
        bright = temporal_sigma_green_luma_dn(4000.0, 100.0, self.model)
        self.assertGreater(bright, dark)

    def test_iso_50_uses_iso_100_readout_gain(self) -> None:
        low = temporal_sigma_green_luma_dn(0.0, 50.0, self.model)
        base = temporal_sigma_green_luma_dn(0.0, 100.0, self.model)
        self.assertAlmostEqual(low, base, places=12)

    def test_band_statistic_responds_to_in_band_pattern(self) -> None:
        size = 64
        yy, xx = np.indices((size, size), dtype=np.float32)
        flat = np.zeros((1, size, size), dtype=np.float32)
        # Period 20 native pixels = 10 green samples, inside 20--60 native px.
        signal = np.sin(2.0 * math.pi * xx / 10.0)[None, ...].astype(np.float32)
        parameters = self.definition["noise"]["flat_band"]
        flat_rms = band_rms_tiles(
            flat,
            2.0,
            parameters["low_frequency_cycles_per_native_px"],
            parameters["high_frequency_cycles_per_native_px"],
        )[0]
        signal_rms = band_rms_tiles(
            signal,
            2.0,
            parameters["low_frequency_cycles_per_native_px"],
            parameters["high_frequency_cycles_per_native_px"],
        )[0]
        self.assertEqual(flat_rms, 0.0)
        self.assertGreater(signal_rms, 0.5)

    def test_out_of_band_constant_is_zero(self) -> None:
        tile = np.full((1, 64, 64), 1234.0, dtype=np.float32)
        parameters = self.definition["noise"]["flat_band"]
        result = band_rms_tiles(
            tile,
            2.0,
            parameters["low_frequency_cycles_per_native_px"],
            parameters["high_frequency_cycles_per_native_px"],
        )[0]
        self.assertEqual(result, 0.0)


class EdgeEligibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definition, _ = load_definition()
        self.selector = self.definition["edge_selector"]
        self.model = self.definition["noise"]["temporal_model"]
        self.source = {
            "file": "synthetic.ARW",
            "decoded_green_sha256": "0" * 64,
        }

    @staticmethod
    def vertical_step(step: float, width: float = 2.0) -> np.ndarray:
        _, xx = np.indices((512, 512), dtype=np.float64)
        return (1000.0 + step / (1.0 + np.exp(-(xx - 256.0) / width))).astype(
            np.float32
        )

    def evaluate(self, image: np.ndarray) -> tuple[dict | None, str]:
        return census.evaluate_edge_candidate(
            image=image,
            y_green=256.0,
            x_green=256.0,
            normal_y=0.0,
            normal_x=1.0,
            reach_native_px=400,
            iso=100.0,
            model=self.model,
            selector=self.selector,
            source_record=self.source,
            source_frame_index=8,
        )

    def test_clean_step_is_broad_eligible(self) -> None:
        site, reason = self.evaluate(self.vertical_step(1000.0))
        self.assertEqual(reason, "eligible")
        self.assertIsNotNone(site)
        assert site is not None
        self.assertGreater(site["narrow_step_sigma"], 10.0)
        self.assertGreater(site["broad_step_sigma"], 10.0)
        self.assertEqual(site["reach_native_px"], 400)

    def test_sub_noise_step_is_rejected(self) -> None:
        site, reason = self.evaluate(self.vertical_step(1.0))
        self.assertIsNone(site)
        self.assertEqual(reason, "step_below_10_sigma")

    def test_double_edge_is_rejected(self) -> None:
        _, xx = np.indices((512, 512), dtype=np.float64)
        image = (
            1000.0
            + 800.0 / (1.0 + np.exp(-(xx - 248.0) / 1.5))
            - 500.0 / (1.0 + np.exp(-(xx - 264.0) / 1.5))
        ).astype(np.float32)
        site, reason = self.evaluate(image)
        self.assertIsNone(site)
        self.assertIn(
            reason,
            {
                "not_one_dark_to_bright_crossing",
                "central_profile_not_monotone_enough",
                "narrow_broad_step_disagree",
                "midpoint_too_far_from_candidate",
            },
        )

    def test_deduplication_keeps_higher_quality(self) -> None:
        low = {
            "x_native_px": 100.0,
            "y_native_px": 100.0,
            "quality": 12.0,
            "source_file": "b.ARW",
        }
        high = {
            "x_native_px": 110.0,
            "y_native_px": 100.0,
            "quality": 20.0,
            "source_file": "a.ARW",
        }
        far = {
            "x_native_px": 300.0,
            "y_native_px": 100.0,
            "quality": 11.0,
            "source_file": "c.ARW",
        }
        selected = census.deduplicate_sites([low, far, high], 64.0)
        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["source_file"], "a.ARW")
        self.assertEqual(selected[1]["source_file"], "c.ARW")


class PopulationTests(unittest.TestCase):
    @staticmethod
    def capture(capture_id: str, count: int, quota: int | None = None) -> dict:
        result = {
            "capture_id": capture_id,
            "eligible_site_count": count,
            "eligible_sites_quality_order": [
                {
                    "x_native_px": float(index),
                    "y_native_px": 0.0,
                    "quality": float(count - index),
                }
                for index in range(count)
            ],
        }
        if quota is not None:
            result["quota"] = quota
        return result

    def test_m3_selection_enforces_each_capture_and_total(self) -> None:
        definition, _ = load_definition()
        captures = [self.capture(f"c{index}", 130) for index in range(4)]
        result = census.select_m3(captures, definition)
        self.assertEqual(result["verdict"], "SUFFICIENT")
        self.assertEqual(result["selected_site_count"], 500)
        selected_counts: dict[str, int] = {}
        for site in result["selected_sites"]:
            selected_counts[site["capture_id"]] = (
                selected_counts.get(site["capture_id"], 0) + 1
            )
        self.assertGreaterEqual(min(selected_counts.values()), 50)

    def test_m3_short_capture_cannot_be_hidden_by_others(self) -> None:
        definition, _ = load_definition()
        captures = [
            self.capture("short", 49),
            self.capture("a", 300),
            self.capture("b", 300),
            self.capture("c", 300),
        ]
        result = census.select_m3(captures, definition)
        self.assertEqual(result["verdict"], "NEEDS_NEW_CAPTURE")
        self.assertEqual(result["per_capture_shortfalls"]["short"], 1)

    def test_m4_fixed_mix_cannot_be_diluted(self) -> None:
        definition, _ = load_definition()
        flats = [
            self.capture("flat-a", 84, 84),
            self.capture("flat-b", 83, 83),
            self.capture("flat-c", 83, 83),
        ]
        edges = [self.capture(f"edge-{index}", 50, 50) for index in range(5)]
        result = census.select_m4(flats, edges, [], definition)
        self.assertEqual(
            result["verdict"], "SUFFICIENT_CONDITIONAL_ON_OWNER_ADOPTING_FROZEN_MIX"
        )
        self.assertEqual(result["selected_flat_site_count"], 250)
        self.assertEqual(result["selected_edge_site_count"], 250)

    def test_m4_category_shortfall_cannot_be_filled_from_other_category(self) -> None:
        definition, _ = load_definition()
        flats = [
            self.capture("flat-a", 83, 84),
            self.capture("flat-b", 1000, 83),
            self.capture("flat-c", 1000, 83),
        ]
        edges = [self.capture(f"edge-{index}", 1000, 50) for index in range(5)]
        result = census.select_m4(flats, edges, [], definition)
        self.assertEqual(result["verdict"], "NEEDS_NEW_CAPTURE")
        self.assertEqual(result["flat_shortfalls"]["flat-a"], 1)


if __name__ == "__main__":
    unittest.main()
