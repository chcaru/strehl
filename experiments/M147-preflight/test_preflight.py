from __future__ import annotations

import math
import unittest

import numpy as np

import preflight


def measurement(
    period: float,
    block_periods: list[float] | None = None,
    axis_scale: tuple[float, float] = (0.998, 1.002),
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
        "orientation_degrees_mod_90": 4.0,
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

    def test_output_action_is_console_ascii(self) -> None:
        result = preflight.evaluate_measurements(
            measurement(64.0),
            measurement(64.0 / 1.98),
        )
        result["action"].encode("ascii")


class HarmonicTests(unittest.TestCase):
    @staticmethod
    def tile(fundamental: float, harmonic: float) -> np.ndarray:
        y, x = np.indices((512, 512), dtype=np.float32)
        theta = math.radians(4.0)
        u = x * math.cos(theta) + y * math.sin(theta)
        v = -x * math.sin(theta) + y * math.cos(theta)
        phase_u = 2.0 * math.pi * u / 64.0
        phase_v = 2.0 * math.pi * v / 64.0
        return (
            2000.0
            + fundamental * (np.cos(phase_u) + np.cos(phase_v))
            + harmonic * (np.cos(2.0 * phase_u) + np.cos(2.0 * phase_v))
        ).astype(np.float32)

    def test_second_harmonic_exposes_primitive_alternative(self) -> None:
        candidate = preflight._tile_candidate(self.tile(90.0, 900.0))
        self.assertIsNotNone(candidate)
        assert candidate is not None
        self.assertAlmostEqual(candidate["period_green_px"], 32.0, delta=0.2)
        relative = candidate["subharmonic_relative_db"]["2"]
        self.assertGreaterEqual(
            relative,
            preflight.FROZEN_PARAMETERS["estimator"][
                "subharmonic_ambiguity_relative_db"
            ],
        )


class ContractTests(unittest.TestCase):
    def test_parameter_hash_is_canonical(self) -> None:
        expected = preflight.hashlib.sha256(
            preflight.canonical_json(preflight.FROZEN_PARAMETERS).encode("ascii")
        ).hexdigest()
        self.assertEqual(preflight.PARAMETERS_SHA256, expected)
        self.assertEqual(len(expected), 64)


if __name__ == "__main__":
    unittest.main()
