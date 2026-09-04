from __future__ import annotations

import copy
import math
import unittest

import numpy as np

from m3_checker_v2 import (
    SiteProfiles,
    load_checker_definition,
    score_site,
    summarize,
    validate_geometry,
)


class M3CheckerV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.definition, _ = load_checker_definition()
        self.offsets = np.arange(-400.0, 401.0, 1.0)
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

    def test_one_sided_veil_uses_side_max(self) -> None:
        output = self.base.copy()
        support = (self.offsets >= 33.0) & (self.offsets <= 232.0)
        output[support] += 0.06 * 0.6
        result = score_site(self.site(output), self.definition)
        self.assertEqual(result["v_e_negative_side"], 0.0)
        self.assertGreater(result["v_e_positive_side"], 0.05)
        self.assertEqual(result["v_e"], result["v_e_positive_side"])
        self.assertAlmostEqual(
            result["v_e_pooled_diagnostic"], 0.5 * result["v_e"], places=12
        )
        self.assertTrue(result["affected"])

    def test_broad_veil_uses_broad_step(self) -> None:
        source = self.base.copy()
        broad_left = (self.offsets >= -400.0) & (self.offsets <= -320.0)
        broad_right = (self.offsets >= 320.0) & (self.offsets <= 400.0)
        source[broad_left] = 0.25
        source[broad_right] = 0.55
        output = source.copy()
        output[(self.offsets >= 16.0) & (self.offsets <= 200.0)] += 0.03
        site = copy.copy(self.site(output))
        site = SiteProfiles(
            **{**site.__dict__, "source_profiles": source[None, :]}
        )
        result = score_site(site, self.definition)
        self.assertAlmostEqual(result["broad_source_step"], 0.30, places=12)
        self.assertAlmostEqual(result["v_e"], 0.10, places=12)

    def test_literal_headline_rejects_one_sparse_failure(self) -> None:
        clean = score_site(self.site(self.base.copy()), self.definition)
        bad_output = self.base.copy()
        bad_output[(self.offsets >= 34.0) & (self.offsets <= 200.0)] += 0.06 * 0.6
        bad = score_site(self.site(bad_output, site_id="bad"), self.definition)
        captures = self.definition["site_population"]["required_capture_ids"]
        rows = [
            dict(clean, site_id=f"s{i}", capture_id=captures[i % len(captures)])
            for i in range(500)
        ]
        rows[0] = dict(bad, capture_id=captures[0])
        summary = summarize(rows, definition=self.definition)
        self.assertLessEqual(summary["affected_edge_rate"], 0.01)
        self.assertFalse(summary["checks"]["headline_maximum"])
        self.assertEqual(summary["verdict"], "FAIL")

    def test_nonfinite_output_is_charged(self) -> None:
        output = self.base.copy()
        output[10] = math.nan
        result = score_site(self.site(output), self.definition)
        self.assertEqual(result["status"], "INVALID_OUTPUT_CHARGED")
        self.assertTrue(result["affected"])

    def test_warp_gate_has_both_directions(self) -> None:
        passing = {
            "scale_disagreement_percent": 0.05,
            "rotation_disagreement_degrees": 0.01,
            "nontranslation_residual_rms_output_px": 0.05,
            "input_only": True,
        }
        failing = dict(passing, scale_disagreement_percent=0.11)
        self.assertEqual(
            validate_geometry(passing, self.definition)["verdict"], "PASS"
        )
        self.assertEqual(
            validate_geometry(failing, self.definition)["verdict"],
            "UNMEASURED_WARP_INADEQUATE",
        )


if __name__ == "__main__":
    unittest.main()
