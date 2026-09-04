from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

import numpy as np

import preflight


def measurement(
    period: float,
    block_periods: list[float] | None = None,
    axis_scale: tuple[float, float] = (0.998, 1.002),
    orientation_degrees: float = 4.0,
) -> dict:
    values = block_periods or [period] * 6
    blocks = {f"{index // 3},{index % 3}": value for index, value in enumerate(values)}
    local_samples = []
    for y in (256.0, 512.0, 768.0, 1024.0, 1280.0):
        for x in (256.0, 512.0, 768.0, 1024.0, 1280.0, 1536.0):
            block_key = f"{min(int(y // 512), 1)},{min(int(x // 512), 2)}"
            local_samples.append(
                {
                    "center_y_green_px": y,
                    "center_x_green_px": x,
                    "period_green_px": blocks[block_key],
                }
            )
    phases = [
        {
            "period_green_px": period * (1.0 - 0.00005),
            "image_shape_green_px": [1536, 2048],
        },
        {
            "period_green_px": period * (1.0 + 0.00005),
            "image_shape_green_px": [1536, 2048],
        },
    ]
    return {
        "period_green_px": period,
        "axis_periods_green_px": [
            period * axis_scale[0],
            period * axis_scale[1],
        ],
        "orientation_degrees_mod_90": orientation_degrees,
        "block_periods_green_px": blocks,
        "green_phases": phases,
        "local_period_samples": local_samples,
    }


class DecisionTests(unittest.TestCase):
    def test_direct_period_ratio_passes(self) -> None:
        result = preflight.evaluate_measurements(
            measurement(64.0),
            measurement(64.0 / 2.05),
        )
        self.assertAlmostEqual(result["sampling_ratio"], 2.05, places=12)
        self.assertEqual(result["verdict"], "PASS")
        self.assertGreaterEqual(result["interval"]["lower"], 2.0)

    def test_point_at_threshold_fails_on_lower_bound(self) -> None:
        result = preflight.evaluate_measurements(
            measurement(64.0),
            measurement(32.0),
        )
        self.assertEqual(result["sampling_ratio"], 2.0)
        self.assertLess(result["interval"]["lower"], 2.0)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("not safely at or above 2.0", result["action"])

    def test_local_scale_defect_cannot_average_to_pass(self) -> None:
        reference = measurement(64.0)
        scored_values = [64.0 / 2.08] * 6
        scored_values[4] = 64.0 / 1.96
        result = preflight.evaluate_measurements(
            reference,
            measurement(float(np.median(scored_values)), scored_values),
        )
        self.assertEqual(result["verdict"], "FAIL")
        self.assertLess(result["interval"]["local_spatial_ratio_envelope"][0], 2.0)

    def test_one_retained_site_cannot_be_medianed_out(self) -> None:
        reference = measurement(64.0)
        scored = measurement(64.0 / 2.02)
        center = np.asarray([767.5, 1023.5])
        for reference_sample, scored_sample in zip(
            reference["local_period_samples"],
            scored["local_period_samples"],
            strict=True,
        ):
            mapped = preflight._map_reference_coordinate_yx(
                np.asarray(
                    [
                        reference_sample["center_y_green_px"],
                        reference_sample["center_x_green_px"],
                    ]
                ),
                center,
                2.02,
                0.0,
            )
            scored_sample["center_y_green_px"] = float(mapped[0])
            scored_sample["center_x_green_px"] = float(mapped[1])
        # One quality-retained site is unsafe while its block's other sites
        # remain nominal.  The point may remain nominal; the lower envelope may not.
        reference["local_period_samples"][0]["period_green_px"] = (
            scored["local_period_samples"][0]["period_green_px"] * 1.99
        )
        result = preflight.evaluate_measurements(reference, scored)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertLess(
            result["interval"]["local_spatial_ratio_envelope"][0],
            2.0,
        )

    def test_yx_rotation_maps_to_the_physical_site(self) -> None:
        coordinate = np.asarray([256.0, 256.0])
        center = np.asarray([767.5, 1023.5])
        mapped = preflight._map_reference_coordinate_yx(
            coordinate,
            center,
            2.02,
            10.0,
        )
        radians = math.radians(10.0)
        offset_y, offset_x = coordinate - center
        expected = center + np.asarray(
            [
                math.cos(radians) * offset_y + math.sin(radians) * offset_x,
                -math.sin(radians) * offset_y + math.cos(radians) * offset_x,
            ]
        ) / 2.02
        np.testing.assert_allclose(mapped, expected, rtol=0.0, atol=1e-12)

    def test_rotated_mapping_cannot_miss_a_bad_site(self) -> None:
        reference = measurement(64.0, orientation_degrees=4.0)
        scored = measurement(64.0 / 2.02, orientation_degrees=14.0)
        center = np.asarray([767.5, 1023.5])
        correctly_mapped = []
        oppositely_mapped = []
        for index, sample in enumerate(reference["local_period_samples"]):
            coordinate = np.asarray(
                [sample["center_y_green_px"], sample["center_x_green_px"]]
            )
            for angle, collection in (
                (10.0, correctly_mapped),
                (-10.0, oppositely_mapped),
            ):
                mapped = preflight._map_reference_coordinate_yx(
                    coordinate,
                    center,
                    2.02,
                    angle,
                )
                collection.append(
                    {
                        "center_y_green_px": float(mapped[0]),
                        "center_x_green_px": float(mapped[1]),
                        "period_green_px": (
                            64.0 / 1.99
                            if angle == 10.0 and index == 0
                            else 64.0 / 2.02
                        ),
                    }
                )
        scored["local_period_samples"] = correctly_mapped + oppositely_mapped
        result = preflight.evaluate_measurements(reference, scored)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertAlmostEqual(
            result["interval"]["local_spatial_ratio_envelope"][0],
            1.99,
            places=12,
        )

    def test_output_action_is_console_ascii(self) -> None:
        result = preflight.evaluate_measurements(
            measurement(64.0),
            measurement(64.0 / 1.98),
        )
        result["action"].encode("ascii")


class HarmonicTests(unittest.TestCase):
    @staticmethod
    def tile(
        fundamental: float,
        harmonic_2: float = 0.0,
        harmonic_3: float = 0.0,
    ) -> np.ndarray:
        y, x = np.indices((512, 512), dtype=np.float32)
        theta = math.radians(4.0)
        u = x * math.cos(theta) + y * math.sin(theta)
        v = -x * math.sin(theta) + y * math.cos(theta)
        phase_u = 2.0 * math.pi * u / 64.0
        phase_v = 2.0 * math.pi * v / 64.0
        return (
            2000.0
            + fundamental * (np.cos(phase_u) + np.cos(phase_v))
            + harmonic_2 * (np.cos(2.0 * phase_u) + np.cos(2.0 * phase_v))
            + harmonic_3 * (np.cos(3.0 * phase_u) + np.cos(3.0 * phase_v))
        ).astype(np.float32)

    def test_second_harmonic_exposes_primitive_alternative(self) -> None:
        candidate = preflight._tile_candidate(self.tile(90.0, 900.0))
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertAlmostEqual(candidate["period_green_px"], 32.0, delta=0.2)
        alternative_snr = candidate["subharmonic_peak_snr_db"]["2"]
        self.assertGreaterEqual(
            alternative_snr,
            preflight.FROZEN_PARAMETERS["estimator"][
                "minimum_subharmonic_peak_snr_db"
            ],
        )

    def _assert_weak_primitive_refused(self, factor: int) -> None:
        tile = (
            self.tile(20.0, harmonic_2=900.0)
            if factor == 2
            else self.tile(20.0, harmonic_3=900.0)
        )
        candidate = preflight._tile_candidate(tile)
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertLess(candidate["subharmonic_relative_db"][str(factor)], -30.0)
        self.assertGreaterEqual(
            candidate["subharmonic_peak_snr_db"][str(factor)],
            preflight.FROZEN_PARAMETERS["estimator"][
                "minimum_subharmonic_peak_snr_db"
            ],
        )
        self.assertGreaterEqual(
            candidate["subharmonic_peak_prominence_db"][str(factor)],
            preflight.FROZEN_PARAMETERS["estimator"][
                "minimum_subharmonic_peak_prominence_db"
            ],
        )
        candidates = []
        for y in (256.0, 768.0, 1280.0):
            for x in (256.0, 768.0, 1280.0, 1792.0):
                candidates.append(
                    {
                        **candidate,
                        "center_y_green_px": y,
                        "center_x_green_px": x,
                    }
                )
        with self.assertRaises(preflight.MeasurementRefusal) as caught:
            preflight._find_cluster(
                candidates,
                (1536, 2048),
                "weak-alias-test",
            )
        self.assertEqual(caught.exception.code, "AMBIGUOUS_HARMONIC")

    def test_weak_second_harmonic_primitive_refuses(self) -> None:
        self._assert_weak_primitive_refused(2)

    def test_weak_third_harmonic_primitive_refuses(self) -> None:
        self._assert_weak_primitive_refused(3)


class ContractTests(unittest.TestCase):
    def test_parameter_hash_is_canonical(self) -> None:
        expected = preflight.hashlib.sha256(
            preflight.canonical_json(preflight.FROZEN_PARAMETERS).encode("ascii")
        ).hexdigest()
        self.assertEqual(preflight.PARAMETERS_SHA256, expected)
        self.assertEqual(len(expected), 64)

    def test_decode_refusal_preserves_file_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            reference = Path(directory) / "broken-reference.ARW"
            scored = Path(directory) / "broken-scored.ARW"
            reference.write_bytes(b"not a raw reference")
            scored.write_bytes(b"not a raw scored")
            artifact, exit_code = preflight.run_preflight(reference, scored)
        self.assertEqual(exit_code, 2)
        self.assertEqual(artifact["status"], "REFUSED")
        self.assertEqual(artifact["decision"]["reason_code"], "RAW_DECODE_FAILED")
        self.assertEqual(
            artifact["inputs"]["reference"]["sha256"],
            preflight.hashlib.sha256(b"not a raw reference").hexdigest(),
        )


if __name__ == "__main__":
    unittest.main()
