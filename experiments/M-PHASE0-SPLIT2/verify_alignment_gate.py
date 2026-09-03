"""Independent OpenCV spatial verification of the subpixel alignment gate."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import rawpy


LANE = Path(__file__).resolve().parent
OUT = LANE / "out"
CAPTURE = Path(
    r"D:\personal\macro\requests\12-bee-iso-var-no-bracket-32-repeat-diff-light"
)
LIMIT_NATIVE_PIXEL = 0.10


def normalize(image: np.ndarray) -> np.ndarray:
    image = np.asarray(image, dtype=np.float32)
    image = image - float(np.mean(image))
    return image / max(float(np.std(image)), 1e-12)


def ecc_alignment(
    reference: np.ndarray,
    moving: np.ndarray,
) -> tuple[float, float]:
    warp = np.eye(2, 3, dtype=np.float32)
    criteria = (
        cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
        300,
        1e-8,
    )
    _, fitted = cv2.findTransformECC(
        normalize(reference),
        normalize(moving),
        warp,
        cv2.MOTION_TRANSLATION,
        criteria,
        None,
        5,
    )
    # OpenCV reports the feature displacement from template to input. The gate
    # stores the translation to apply to moving, hence the sign reversal.
    return -float(fitted[1, 2]), -float(fitted[0, 2])


def quadrants(
    reference: np.ndarray,
    moving: np.ndarray,
) -> list[tuple[float, float]]:
    half = reference.shape[0] // 2
    return [
        ecc_alignment(
            reference[y : y + half, x : x + half],
            moving[y : y + half, x : x + half],
        )
        for y in (0, half)
        for x in (0, half)
    ]


def residual_rms_native(
    global_shift: tuple[float, float],
    local_shifts: list[tuple[float, float]],
) -> float:
    return 2.0 * math.sqrt(
        sum(
            (shift[0] - global_shift[0]) ** 2
            + (shift[1] - global_shift[1]) ** 2
            for shift in local_shifts
        )
        / len(local_shifts)
    )


BLOBS = (
    (31.0, 43.0, 3.0, 2.0),
    (52.0, 198.0, 7.0, -1.4),
    (77.0, 119.0, 5.0, 1.1),
    (95.0, 223.0, 11.0, 0.9),
    (121.0, 36.0, 4.0, -1.7),
    (142.0, 151.0, 8.0, 1.5),
    (166.0, 89.0, 6.0, -1.2),
    (188.0, 211.0, 4.0, 1.8),
    (217.0, 57.0, 9.0, 1.0),
    (231.0, 174.0, 5.0, -1.3),
)


def analytic_quadrant(
    displacement: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray]:
    dy, dx = displacement
    y, x = np.indices((256, 256), dtype=np.float64)

    def evaluate(y_coordinate: np.ndarray, x_coordinate: np.ndarray) -> np.ndarray:
        result = np.zeros((256, 256), dtype=np.float64)
        for cy, cx, sigma, amplitude in BLOBS:
            squared = (y_coordinate - cy) ** 2 + (x_coordinate - cx) ** 2
            result += amplitude * np.exp(-0.5 * squared / sigma**2)
        return result

    return evaluate(y, x), evaluate(y - dy, x - dx)


def analytic_fixture(warped: bool) -> tuple[np.ndarray, np.ndarray, float]:
    base = (1.25, -0.40)
    residuals = (
        ((-0.06, 0.0), (0.06, 0.0), (-0.06, 0.0), (0.06, 0.0))
        if warped
        else ((0.0, 0.0),) * 4
    )
    reference = np.zeros((512, 512), dtype=np.float64)
    moving = np.zeros_like(reference)
    for index, residual in enumerate(residuals):
        ref, mov = analytic_quadrant(
            (base[0] + residual[0], base[1] + residual[1])
        )
        y = 256 * (index // 2)
        x = 256 * (index % 2)
        reference[y : y + 256, x : x + 256] = ref
        moving[y : y + 256, x : x + 256] = mov
    true_rms = 2.0 * math.sqrt(
        sum(dy * dy + dx * dx for dy, dx in residuals) / 4.0
    )
    return reference, moving, true_rms


def fixture_reading(warped: bool) -> dict[str, object]:
    reference, moving, true_rms = analytic_fixture(warped)
    global_shift = ecc_alignment(reference, moving)
    local = quadrants(reference, moving)
    return {
        "warped": warped,
        "true_residual_rms_native_pixels": true_rms,
        "global_alignment_quad_pixels": list(global_shift),
        "quadrant_alignments_quad_pixels": [list(value) for value in local],
        "measured_residual_rms_native_pixels": residual_rms_native(
            global_shift,
            local,
        ),
    }


def internal(plant_zero_residual: bool) -> int:
    clean = fixture_reading(False)
    warped = fixture_reading(True)
    measured_warp = (
        0.0
        if plant_zero_residual
        else float(warped["measured_residual_rms_native_pixels"])
    )
    if float(clean["measured_residual_rms_native_pixels"]) >= 0.03:
        print(f"ECC CHECK RED clean: {clean}")
        return 1
    if float(warped["true_residual_rms_native_pixels"]) <= LIMIT_NATIVE_PIXEL:
        print(f"ECC CHECK RED invalid plant: {warped}")
        return 1
    if measured_warp <= LIMIT_NATIVE_PIXEL:
        print(f"ECC CHECK RED missed warp: {warped}")
        return 1
    print("ECC CHECK GREEN")
    return 0


def decode_crop(path: Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        visible = raw.raw_image_visible
        side = 512
        y = (visible.shape[0] // 2 - side) // 2
        x = (visible.shape[1] // 2 - side) // 2
        green_1 = visible[
            2 * y : 2 * (y + side) : 2,
            2 * x + 1 : 2 * (x + side) + 1 : 2,
        ]
        green_2 = visible[
            2 * y + 1 : 2 * (y + side) + 1 : 2,
            2 * x : 2 * (x + side) : 2,
        ]
        return 0.5 * (
            green_1.astype(np.float64) + green_2.astype(np.float64)
        ) - 512.0


def run_child(plant: bool) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(Path(__file__).resolve()), "--internal"]
    if plant:
        command.append("--plant-zero-residual")
    return subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def main() -> int:
    if "--internal" in sys.argv:
        return internal("--plant-zero-residual" in sys.argv)

    clean = run_child(False)
    plant = run_child(True)
    if clean.returncode != 0 or plant.returncode != 1:
        raise RuntimeError(
            f"ECC commissioning failed clean={clean.returncode}, plant={plant.returncode}"
        )

    primary = json.loads((OUT / "alignment-gate.json").read_text(encoding="utf-8"))
    verified_runs = []
    for run in primary["runs"]:
        files = [frame["file"] for frame in run["frames"]]
        reference = decode_crop(CAPTURE / files[0])
        rows = []
        maximum = 0.0
        for filename in files:
            moving = decode_crop(CAPTURE / filename)
            global_shift = ecc_alignment(reference, moving)
            local = quadrants(reference, moving)
            value = residual_rms_native(global_shift, local)
            maximum = max(maximum, value)
            rows.append(
                {
                    "file": filename,
                    "global_alignment_quad_pixels": list(global_shift),
                    "quadrant_alignments_quad_pixels": [
                        list(item) for item in local
                    ],
                    "nontranslation_residual_rms_native_pixels": value,
                }
            )
        verified_runs.append(
            {
                "pass": run["pass"],
                "maximum_nontranslation_residual_rms_native_pixels": maximum,
                "passes": maximum <= LIMIT_NATIVE_PIXEL,
                "frames": rows,
            }
        )

    primary_decisions = [
        bool(run["passes_translation_only_gate"]) for run in primary["runs"]
    ]
    independent_decisions = [bool(run["passes"]) for run in verified_runs]
    result = {
        "status": (
            "VERIFIED"
            if primary_decisions == independent_decisions
            else "NOT_ROBUST"
        ),
        "commission": {
            "clean_exit": clean.returncode,
            "zero_residual_plant_exit": plant.returncode,
            "plant_went_red": plant.returncode == 1,
            "clean_fixture": fixture_reading(False),
            "warped_fixture": fixture_reading(True),
        },
        "method": (
            "OpenCV ECC spatial-domain translation fit; independent of "
            "skimage phase_cross_correlation and align.py"
        ),
        "primary_decisions": primary_decisions,
        "independent_decisions": independent_decisions,
        "runs": verified_runs,
    }
    (OUT / "alignment-gate-verification.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "primary_decisions": primary_decisions,
                "independent_decisions": independent_decisions,
                "maximum_independent_rms": [
                    run["maximum_nontranslation_residual_rms_native_pixels"]
                    for run in verified_runs
                ],
            },
            indent=2,
        )
    )
    return 0 if result["status"] == "VERIFIED" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ECC VERIFY FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
