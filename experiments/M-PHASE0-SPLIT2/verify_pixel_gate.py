"""Independent spatial-domain verification of the load-bearing pixel gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rawpy


LANE = Path(__file__).resolve().parent
OUT = LANE / "out"
CAPTURE = Path(
    r"D:\personal\macro\requests\12-bee-iso-var-no-bracket-32-repeat-diff-light"
)
SIDE = 512
SEARCH = 3
MARGIN = SEARCH + 2


def best_displacement(
    reference: np.ndarray,
    moving: np.ndarray,
    *,
    force_zero: bool = False,
) -> tuple[tuple[int, int], float, float]:
    """Return moving-feature displacement by direct normalized correlation."""
    if reference.shape != moving.shape or reference.ndim != 2:
        raise ValueError("direct correlation needs equal 2-D arrays")
    if force_zero:
        candidates = [(0, 0)]
    else:
        candidates = [
            (dy, dx)
            for dy in range(-SEARCH, SEARCH + 1)
            for dx in range(-SEARCH, SEARCH + 1)
        ]
    side_y = reference.shape[0] - 2 * MARGIN
    side_x = reference.shape[1] - 2 * MARGIN
    ref = reference[MARGIN : MARGIN + side_y, MARGIN : MARGIN + side_x]
    ref = ref.astype(np.float64) - float(np.mean(ref))
    ref /= max(float(np.sqrt(np.mean(ref * ref))), 1e-30)
    rows = []
    for dy, dx in candidates:
        mov = moving[
            MARGIN + dy : MARGIN + dy + side_y,
            MARGIN + dx : MARGIN + dx + side_x,
        ]
        mov = mov.astype(np.float64) - float(np.mean(mov))
        mov /= max(float(np.sqrt(np.mean(mov * mov))), 1e-30)
        rows.append(((dy, dx), float(np.mean(ref * mov))))
    rows.sort(key=lambda row: row[1], reverse=True)
    second = rows[1][1] if len(rows) > 1 else float("-inf")
    return rows[0][0], rows[0][1], second


def synthetic_fixture() -> tuple[np.ndarray, np.ndarray]:
    reference = np.zeros((64, 64), dtype=np.float64)
    for y, x, value in (
        (8, 11, 4.0),
        (13, 47, -2.0),
        (21, 19, 7.0),
        (37, 42, 3.0),
        (48, 15, -5.0),
        (52, 51, 6.0),
    ):
        reference[y - 2 : y + 3, x - 2 : x + 3] = value
    moving = np.zeros_like(reference)
    moving[1:, :] = reference[:-1, :]
    return reference, moving


def internal(force_zero: bool) -> int:
    reference, moving = synthetic_fixture()
    displacement, _, _ = best_displacement(
        reference, moving, force_zero=force_zero
    )
    if displacement != (1, 0):
        print(f"DIRECT CHECK RED: {displacement}, expected fixed (1, 0)")
        return 1
    print("DIRECT CHECK GREEN: fixed displacement (1, 0)")
    return 0


def decode_focus_crop(path: Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        visible = raw.raw_image_visible
        quad_height = visible.shape[0] // 2
        quad_width = visible.shape[1] // 2
        y = (quad_height - SIDE) // 2
        x = (quad_width - SIDE) // 2
        green_1 = visible[2 * y : 2 * (y + SIDE) : 2, 2 * x + 1 : 2 * (x + SIDE) + 1 : 2]
        green_2 = visible[2 * y + 1 : 2 * (y + SIDE) + 1 : 2, 2 * x : 2 * (x + SIDE) : 2]
        return 0.5 * (
            green_1.astype(np.float64) + green_2.astype(np.float64)
        ) - 512.0


def run_child(force_zero: bool) -> subprocess.CompletedProcess[str]:
    arguments = [sys.executable, str(Path(__file__).resolve()), "--internal"]
    if force_zero:
        arguments.append("--plant-zero")
    return subprocess.run(
        arguments,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def main() -> int:
    if "--internal" in sys.argv:
        return internal("--plant-zero" in sys.argv)

    clean = run_child(False)
    planted = run_child(True)
    if clean.returncode != 0 or planted.returncode != 1:
        raise RuntimeError(
            f"direct verifier commissioning failed: clean={clean.returncode}, "
            f"plant={planted.returncode}"
        )

    gate = json.loads((OUT / "pixel-gate.json").read_text(encoding="utf-8"))
    first_number = int(str(gate["first_file"])[3:8])
    files = [f"DSC{number:05d}.ARW" for number in range(first_number, first_number + 32)]
    reference = decode_focus_crop(CAPTURE / files[0])
    displacements = []
    correlations = []
    margins = []
    for filename in files:
        displacement, best, second = best_displacement(
            reference,
            decode_focus_crop(CAPTURE / filename),
        )
        displacements.append(list(displacement))
        correlations.append(best)
        margins.append(best - second)

    fft_alignment_shifts = [row for row in gate["stability"]["shifts"]]
    expected_alignment = [[-dy, -dx] for dy, dx in displacements]
    result = {
        "status": "VERIFIED_RED" if gate["status"] == "PIXEL_GATE_RED" else "MISMATCH",
        "commission": {
            "clean_exit": clean.returncode,
            "zero_only_plant_exit": planted.returncode,
            "plant_went_red": planted.returncode == 1,
        },
        "method": (
            "direct spatial normalized correlation over all integer "
            "displacements in [-3,3]^2; no FFT and no import from frc.py"
        ),
        "feature_displacements_relative_to_frame_0": displacements,
        "best_correlations": correlations,
        "best_minus_second_best": margins,
        "fft_alignment_shifts": fft_alignment_shifts,
        "expected_fft_alignment_from_direct_displacement": expected_alignment,
        "all_methods_agree": expected_alignment == fft_alignment_shifts,
        "maximum_absolute_displacement_quad_pixels": max(
            max(abs(dy), abs(dx)) for dy, dx in displacements
        ),
    }
    if result["status"] != "VERIFIED_RED" or not result["all_methods_agree"]:
        raise RuntimeError(f"independent gate verification failed: {result}")
    (OUT / "pixel-gate-verification.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"VERIFY FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(1)
