from __future__ import annotations

import math
import copy
import unittest

import numpy as np

from m3_checker import (
    SiteProfiles,
    load_checker_definition,
    paired_p99,
    score_site,
    summarize,
    wilson_upper_one_sided,
)


class M3CheckerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.definition, _ = load_checker_definition()
        self.offsets = np.arange(-400.0, 401.0)
        self.base = 0.1 + 0.6 / (1.0 + np.exp(-self.offsets / 2.0))
        yy, xx = np.indices((128, 128), dtype=np.float64)
        self.patch = 0.1 + 0.6 / (1.0 + np.exp(-(xx - 63.5) / 2.0))

    def site(self, output: np.ndarray, site_id: str = "s") -> SiteProfiles:
        return SiteProfiles(
            site_id=site_id,
            capture_id="m3-duck-tape",
            offsets_native_px=self.offsets,
            source_profiles=self.base[None, :],
            output_profile=output,
            normalization_source_index=0,
            far_reference_source_index=0,
            sharp_source_index=0,
            output_patch=self.patch,
            sharp_source_patch=self.patch,
        )

    def test_identity_is_exactly_quiet(self) -> None:
        result = score_site(self.site(self.base.copy()), self.definition)
        self.assertEqual(result["h_e"], 0.0)
        self.assertEqual(result["v_e"], 0.0)
        self.assertAlmostEqual(result["edge_width_ratio"], 1.0, places=12)
        self.assertAlmostEqual(result["rho_edge"], 1.0, places=12)
        self.assertFalse(result["affected"])

    def test_positive_rim_is_charged_at_planted_magnitude(self) -> None:
        output = self.base.copy()
        output[(self.offsets >= 12) & (self.offsets <= 24)] += 0.06 * 0.6
        result = score_site(self.site(output), self.definition)
        self.assertAlmostEqual(result["h_e"], 0.06, places=12)
        self.assertTrue(result["affected"])

    def test_negative_rim_is_also_charged(self) -> None:
        output = self.base.copy()
        output[(self.offsets >= 12) & (self.offsets <= 24)] -= 0.06 * 0.6
        result = score_site(self.site(output), self.definition)
        self.assertAlmostEqual(result["h_e"], 0.06, places=12)
        self.assertTrue(result["affected"])

    def test_halo_support_is_consumed_from_frozen_definition(self) -> None:
        output = self.base.copy()
        output[(self.offsets >= 12) & (self.offsets <= 24)] += 0.06 * 0.6
        changed = copy.deepcopy(self.definition)
        changed["halo"]["support_abs_native_px"] = [2, 10]
        result = score_site(self.site(output), changed)
        self.assertEqual(result["h_e"], 0.0)

    def test_two_sided_veil_is_charged_at_planted_magnitude(self) -> None:
        output = self.base.copy()
        support = (np.abs(self.offsets) >= 16) & (np.abs(self.offsets) <= 200)
        output[support] += 0.06 * 0.6
        result = score_site(self.site(output), self.definition)
        self.assertAlmostEqual(result["v_e"], 0.06, places=12)
        self.assertAlmostEqual(result["v_e_negative_side"], 0.06, places=12)
        self.assertAlmostEqual(result["v_e_positive_side"], 0.06, places=12)
        self.assertTrue(result["affected"])

    def test_nonfinite_output_is_charged_not_removed(self) -> None:
        output = self.base.copy()
        output[400] = math.nan
        result = score_site(self.site(output), self.definition)
        self.assertEqual(result["status"], "INVALID_OUTPUT_CHARGED")
        self.assertTrue(math.isinf(result["h_e"]))
        self.assertTrue(result["affected"])

    def test_one_sided_veil_exposes_literal_pooled_dilution(self) -> None:
        output = self.base.copy()
        # Keep this diagnostic outside the halo window so only the registered
        # pooled veil reduction can respond.
        support = (self.offsets >= 33) & (self.offsets <= 232)
        output[support] += 0.06 * 0.6
        result = score_site(self.site(output), self.definition)
        self.assertAlmostEqual(
            result["v_e_positive_side"], 0.06 * 168.0 / 185.0, places=12
        )
        self.assertAlmostEqual(result["v_e_negative_side"], 0.0, places=12)
        self.assertAlmostEqual(result["v_e"], 0.06 * 168.0 / 370.0, places=12)
        self.assertGreater(result["v_side_max_diagnostic"], 0.05)
        self.assertFalse(result["affected"])

    def test_empty_or_wrong_capture_population_is_unmeasured(self) -> None:
        self.assertEqual(
            summarize([], definition=self.definition)["verdict"],
            "UNMEASURED_CAPTURE_INADEQUATE",
        )
        result = score_site(self.site(self.base.copy()), self.definition)
        repeated = [dict(result, site_id=f"s{index}") for index in range(500)]
        self.assertEqual(
            summarize(repeated, definition=self.definition)["verdict"],
            "UNMEASURED_CAPTURE_INADEQUATE",
        )

    def test_wilson_uses_one_sided_95_percent_bound(self) -> None:
        self.assertLess(wilson_upper_one_sided(4, 500), 0.02)
        self.assertGreater(wilson_upper_one_sided(5, 500), 0.02)

    def test_paired_comparator_requires_identical_sites(self) -> None:
        strehl = [{"site_id": "a", "h_e": 0.01, "v_e": 0.0}]
        comparator = {"c": [{"site_id": "b", "h_e": 0.02, "v_e": 0.0}]}
        self.assertEqual(paired_p99(strehl, comparator)["verdict"], "UNMEASURED")

    def test_paired_comparator_chooses_lowest_p99_on_same_sites(self) -> None:
        strehl = [
            {"site_id": "a", "h_e": 0.02, "v_e": 0.01},
            {"site_id": "b", "h_e": 0.03, "v_e": 0.01},
        ]
        comparators = {
            "worse": [
                {"site_id": "a", "h_e": 0.04, "v_e": 0.01},
                {"site_id": "b", "h_e": 0.05, "v_e": 0.01},
            ],
            "best": [
                {"site_id": "a", "h_e": 0.01, "v_e": 0.01},
                {"site_id": "b", "h_e": 0.02, "v_e": 0.01},
            ],
        }
        result = paired_p99(strehl, comparators)
        self.assertEqual(result["best_comparator"], "best")
        self.assertEqual(result["verdict"], "FAIL")


if __name__ == "__main__":
    unittest.main()
