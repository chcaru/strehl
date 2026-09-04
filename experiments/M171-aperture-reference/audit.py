#!/usr/bin/env python3
"""M171 metadata-only aperture-reference physics preflight.

This program never decodes a RAW pixel.  ExifTool reads metadata from the
read-only capture tree, then this program evaluates the frozen physical gate in
PREREGISTRATION.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np


SCHEMA = "M171-aperture-reference-audit-v1"
RAW_ROOT = Path(r"D:\personal\macro\requests\19-razor-edge")

EXPECTED_STACKS = {
    "diagonal-tilt-all-axes/diagonal-tilt-all-axes-sw4-f5.6-cpl": {
        "count": 279,
        "f_number": 5.6,
        "exposure_s": 2.5,
    },
    "diagonal-tilt-all-axes/diagonal-tilt-all-axes-sw4-f8-cpl": {
        "count": 210,
        "f_number": 8.0,
        "exposure_s": 2.5,
    },
    "diagonal-tilt-all-axes/diagonal-tilt-all-axes-sw4-f11-cpl": {
        "count": 143,
        "f_number": 11.0,
        "exposure_s": 2.5,
    },
    "horizontal-flat/razor-edge-horizontal-flat-sw4-f5.6-cpl": {
        "count": 67,
        "f_number": 5.6,
        "exposure_s": 3.2,
    },
    "horizontal-flat/razor-edge-horizontal-flat-sw4-f8-cpl": {
        "count": 50,
        "f_number": 8.0,
        "exposure_s": 3.2,
    },
    "horizontal-flat/razor-edge-horizontal-flat-sw4-f11-cpl": {
        "count": 40,
        "f_number": 11.0,
        "exposure_s": 3.2,
    },
}
EXPECTED_MODEL = "ILCE-7CM2"
EXPECTED_LENS_MODEL = "FE 100mm F2.8 Macro GM OSS + 2X Teleconverter"
EXPECTED_LENS_TYPE3 = 33094
EXPECTED_FOCAL_LENGTH_MM = 200.0
EXPECTED_MAX_APERTURE = 5.6
EXPECTED_ISO = 100

# Official Sony specifications used only for the pixel-pitch derivation.
SENSOR_WIDTH_MM = 35.9
SENSOR_HEIGHT_MM = 23.9
EFFECTIVE_WIDTH_PX = 7008
EFFECTIVE_HEIGHT_PX = 4672

WAVELENGTH_MM = 550e-6
AIRY_DIAMETER_FACTOR = 2.44
MTF_SCALE = 2.0 / math.pi

# Directional controls are independent of the capture metadata.
DIRECTIONAL_BASE_N = 8.0
DIRECTIONAL_IMPROVEMENT_N = 5.6
DIRECTIONAL_DEGRADATION_N = 11.0
DIRECTIONAL_FREQUENCY_LPMM = 40.0

# This is an existence counterexample, not an estimate of the captured lens.
# A physically valid pupil with this much primary spherical aberration at the
# widest aperture is consistent with the EXIF because EXIF contains no
# wavefront measurement or certified lower transfer bound.
COUNTEREXAMPLE_W040_WAVES = 0.60
COUNTEREXAMPLE_WORKING_FACTOR = 3.72
COUNTEREXAMPLE_FREQUENCY_LPMM = 20.0
PUPIL_FINE_SIDE = 1024
PUPIL_COARSE_SIDE = 512
PUPIL_IDEAL_VALIDATION_BAR = 0.0002
PUPIL_CONVERGENCE_BAR = 0.001

SOURCE_URLS = {
    "sensor": (
        "https://helpguide.sony.net/ilc/2360/v1/en/"
        "contents/231h_specifications_ilc2360.html"
    ),
    "pixel_dimensions": (
        "https://helpguide.sony.net/ilc/2360/v1/en/"
        "contents/0404M_jpeg_image_size.html"
    ),
    "lens": "https://www.sony.jp/ichigan/products/SEL100M28GM/spec.html",
    "viltrox_tc": "https://viltrox.com/products/tc-2-0x-teleconverter-for-sony",
    "sony_tc_stop_loss": (
        "https://www.sony.jp/ichigan/products/SEL20TC/feature_1.html"
    ),
    "airy": (
        "https://www.edmundoptics.com/knowledge-center/application-notes/"
        "imaging/limitations-on-resolution-and-contrast-the-airy-disk/"
    ),
    "mtf": (
        "https://www.edmundoptics.com/knowledge-center/application-notes/"
        "optics/introduction-to-modulation-transfer-function/"
    ),
}


class AuditError(RuntimeError):
    """A typed hard failure of the frozen preflight."""


def close(a: float, b: float, tolerance: float = 1e-9) -> bool:
    return math.isfinite(a) and abs(a - b) <= tolerance


def airy_diameter_um(f_number: float) -> float:
    return AIRY_DIAMETER_FACTOR * (WAVELENGTH_MM * 1000.0) * f_number


def diffraction_mtf(frequency_lpmm: float, f_number: float) -> float:
    """Ideal incoherent MTF of a clear circular pupil."""

    x = frequency_lpmm * WAVELENGTH_MM * f_number
    if x <= 0.0:
        return 1.0
    if x >= 1.0:
        return 0.0
    return MTF_SCALE * (
        math.acos(x) - x * math.sqrt(max(0.0, 1.0 - x * x))
    )


def pupil_mtf_row(
    w040_waves: float, side: int = PUPIL_FINE_SIDE
) -> tuple[np.ndarray, int]:
    """Numerical aberrated OTF from the pupil autocorrelation.

    The pupil radius occupies one quarter of the zero-padded grid.  A normalized
    frequency of one therefore corresponds to a two-radius autocorrelation
    shift, the ideal circular-pupil cutoff.
    """

    radius = side // 4
    yy, xx = np.indices((side, side), dtype=np.float64)
    center = side // 2
    rho = np.hypot(xx - center, yy - center) / radius
    inside = rho <= 1.0
    pupil = np.zeros((side, side), dtype=np.complex128)
    pupil[inside] = np.exp(
        2j * math.pi * w040_waves * np.power(rho[inside], 4)
    )
    spectrum = np.fft.fft2(np.fft.ifftshift(pupil))
    autocorrelation = np.fft.fftshift(
        np.fft.ifft2(np.abs(spectrum) ** 2)
    ).real
    autocorrelation /= autocorrelation[center, center]
    return autocorrelation[center, :], radius


def sample_pupil_mtf(
    row: np.ndarray, radius: int, normalized_frequency: float
) -> float:
    if not math.isfinite(normalized_frequency):
        raise AuditError("non-finite normalized pupil frequency")
    if normalized_frequency <= 0.0:
        return 1.0
    if normalized_frequency >= 1.0:
        return 0.0
    center = len(row) // 2
    position = center + 2.0 * radius * normalized_frequency
    lo = int(math.floor(position))
    if lo >= len(row) - 1:
        cutoff_position = center + 2.0 * radius
        weight = (position - (len(row) - 1)) / (
            cutoff_position - (len(row) - 1)
        )
        return float(abs((1.0 - weight) * row[-1]))
    weight = position - lo
    value = (1.0 - weight) * row[lo] + weight * row[lo + 1]
    return float(abs(value))


def pupil_model_validation() -> dict[str, Any]:
    row, radius = pupil_mtf_row(0.0)
    errors = []
    validation_points = np.concatenate(
        [np.linspace(0.01, 0.95, 95), np.array([0.99, 0.995, 0.999])]
    )
    for normalized in validation_points:
        numerical = sample_pupil_mtf(row, radius, float(normalized))
        analytic = diffraction_mtf(
            float(normalized) / WAVELENGTH_MM, 1.0
        )
        errors.append(abs(numerical - analytic))
    maximum = float(max(errors))
    if maximum >= PUPIL_IDEAL_VALIDATION_BAR:
        raise AuditError(
            "pupil autocorrelation validation error "
            f"{maximum} >= {PUPIL_IDEAL_VALIDATION_BAR}"
        )
    return {
        "status": "PASS",
        "grid_side": PUPIL_FINE_SIDE,
        "max_abs_error_vs_analytic": maximum,
        "bar": PUPIL_IDEAL_VALIDATION_BAR,
    }


def evaluate_aberrated_rows(side: int) -> list[dict[str, Any]]:
    rows = []
    for f_number in (5.6, 8.0, 11.0):
        waves = COUNTEREXAMPLE_W040_WAVES * (5.6 / f_number) ** 4
        pupil_row, radius = pupil_mtf_row(waves, side=side)
        working_n = COUNTEREXAMPLE_WORKING_FACTOR * f_number
        normalized = (
            COUNTEREXAMPLE_FREQUENCY_LPMM * WAVELENGTH_MM * working_n
        )
        rows.append(
            {
                "recorded_f_number": f_number,
                "illustrative_working_f_number": working_n,
                "w040_waves": waves,
                "normalized_frequency": normalized,
                "actual_mtf": sample_pupil_mtf(
                    pupil_row, radius, normalized
                ),
                "ideal_mtf": diffraction_mtf(
                    COUNTEREXAMPLE_FREQUENCY_LPMM, working_n
                ),
            }
        )
    return rows


def aberration_counterexample() -> dict[str, Any]:
    rows = evaluate_aberrated_rows(PUPIL_FINE_SIDE)
    coarse_rows = evaluate_aberrated_rows(PUPIL_COARSE_SIDE)
    convergence = max(
        abs(fine["actual_mtf"] - coarse["actual_mtf"])
        for fine, coarse in zip(rows, coarse_rows, strict=True)
    )
    if convergence >= PUPIL_CONVERGENCE_BAR:
        raise AuditError(
            "aberrated pupil grid convergence "
            f"{convergence} >= {PUPIL_CONVERGENCE_BAR}"
        )
    reversal = rows[1]["actual_mtf"] > rows[0]["actual_mtf"]
    two_decimal_stable = all(
        round(fine["actual_mtf"], 2) == round(coarse["actual_mtf"], 2)
        for fine, coarse in zip(rows, coarse_rows, strict=True)
    )
    if not two_decimal_stable:
        raise AuditError("aberrated pupil two-decimal report is grid-unstable")
    return {
        "status": "PASS" if reversal else "FAIL",
        "purpose": (
            "existence proof only; W040 and working factor are not estimates "
            "of the capture"
        ),
        "frequency_lpmm": COUNTEREXAMPLE_FREQUENCY_LPMM,
        "w040_at_recorded_f5_6_waves": COUNTEREXAMPLE_W040_WAVES,
        "working_factor": COUNTEREXAMPLE_WORKING_FACTOR,
        "fine_grid_side": PUPIL_FINE_SIDE,
        "coarse_grid_side": PUPIL_COARSE_SIDE,
        "coarse_to_fine_max_abs_delta": convergence,
        "two_decimal_report_stable": two_decimal_stable,
        "rows": rows,
        "f8_exceeds_f5_6": reversal,
    }


def counterexample_verdict(counterexample: dict[str, Any]) -> str:
    if counterexample["f8_exceeds_f5_6"]:
        return "NOT_FORCED"
    return "INDETERMINATE"


def directional_controls() -> dict[str, Any]:
    base = diffraction_mtf(DIRECTIONAL_FREQUENCY_LPMM, DIRECTIONAL_BASE_N)
    improved = diffraction_mtf(
        DIRECTIONAL_FREQUENCY_LPMM, DIRECTIONAL_IMPROVEMENT_N
    )
    degraded = diffraction_mtf(
        DIRECTIONAL_FREQUENCY_LPMM, DIRECTIONAL_DEGRADATION_N
    )
    passed = improved > base > degraded
    if not passed:
        raise AuditError(
            "planted ideal improvement/degradation direction was not detected"
        )
    return {
        "status": "PASS",
        "frequency_lpmm": DIRECTIONAL_FREQUENCY_LPMM,
        "planted_improvement": {
            "f_number": DIRECTIONAL_IMPROVEMENT_N,
            "mtf": improved,
            "strictly_above_base": improved > base,
        },
        "base": {"f_number": DIRECTIONAL_BASE_N, "mtf": base},
        "planted_degradation": {
            "f_number": DIRECTIONAL_DEGRADATION_N,
            "mtf": degraded,
            "strictly_below_base": degraded < base,
        },
    }


def canonical_stack(directory: str, root: Path) -> str:
    normalized = directory.replace("\\", "/").rstrip("/")
    normalized_root = str(root).replace("\\", "/").rstrip("/")
    prefix = normalized_root + "/"
    if normalized.lower().startswith(prefix.lower()):
        return normalized[len(prefix) :]
    raise AuditError(f"metadata directory outside read-only root: {directory}")


def numeric(record: dict[str, Any], key: str) -> float:
    try:
        value = float(record[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise AuditError(f"missing/non-numeric EXIF {key}") from exc
    if not math.isfinite(value):
        raise AuditError(f"non-finite EXIF {key}")
    return value


def required_text(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AuditError(f"missing/empty EXIF {key}")
    return value


def validate_metadata(
    records: list[dict[str, Any]], root: Path
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        stack = canonical_stack(str(record.get("Directory", "")), root)
        grouped.setdefault(stack, []).append(record)

    if set(grouped) != set(EXPECTED_STACKS):
        missing = sorted(set(EXPECTED_STACKS) - set(grouped))
        extra = sorted(set(grouped) - set(EXPECTED_STACKS))
        raise AuditError(f"stack mismatch; missing={missing}; extra={extra}")

    summaries = []
    for stack in sorted(EXPECTED_STACKS):
        expected = EXPECTED_STACKS[stack]
        members = grouped[stack]
        if len(members) != expected["count"]:
            raise AuditError(
                f"{stack}: count {len(members)} != {expected['count']}"
            )
        for record in members:
            if required_text(record, "Model") != EXPECTED_MODEL:
                raise AuditError(f"{stack}: unexpected camera model")
            if required_text(record, "LensModel") != EXPECTED_LENS_MODEL:
                raise AuditError(f"{stack}: unexpected lens model")
            if int(numeric(record, "LensType3")) != EXPECTED_LENS_TYPE3:
                raise AuditError(f"{stack}: unexpected LensType3")
            if not close(
                numeric(record, "FNumber"),
                float(expected["f_number"]),
                0.01,
            ):
                raise AuditError(f"{stack}: unexpected FNumber")
            if not close(
                numeric(record, "MaxApertureValue"),
                EXPECTED_MAX_APERTURE,
                0.02,
            ):
                raise AuditError(f"{stack}: unexpected MaxApertureValue")
            if not close(
                numeric(record, "FocalLength"),
                EXPECTED_FOCAL_LENGTH_MM,
                0.01,
            ):
                raise AuditError(f"{stack}: unexpected FocalLength")
            if not close(
                numeric(record, "FocalLengthIn35mmFormat"),
                EXPECTED_FOCAL_LENGTH_MM,
                0.01,
            ):
                raise AuditError(
                    f"{stack}: unexpected FocalLengthIn35mmFormat"
                )
            if int(numeric(record, "ISO")) != EXPECTED_ISO:
                raise AuditError(f"{stack}: unexpected ISO")
            if not close(
                numeric(record, "ExposureTime"),
                float(expected["exposure_s"]),
                1e-6,
            ):
                raise AuditError(f"{stack}: unexpected ExposureTime")

        dates = sorted(
            required_text(member, "DateTimeOriginal") for member in members
        )
        focus = [numeric(member, "FocusPosition2") for member in members]
        summaries.append(
            {
                "stack": stack,
                "count": len(members),
                "f_number": float(expected["f_number"]),
                "max_aperture": numeric(members[0], "MaxApertureValue"),
                "focal_length_mm": numeric(members[0], "FocalLength"),
                "focal_length_35mm_mm": numeric(
                    members[0], "FocalLengthIn35mmFormat"
                ),
                "iso": int(numeric(members[0], "ISO")),
                "exposure_s": numeric(members[0], "ExposureTime"),
                "first_capture": dates[0],
                "last_capture": dates[-1],
                "focus_position2_min": min(focus),
                "focus_position2_max": max(focus),
            }
        )
    return summaries


def synthetic_metadata(root: Path) -> list[dict[str, Any]]:
    records = []
    for stack, expected in EXPECTED_STACKS.items():
        for index in range(int(expected["count"])):
            records.append(
                {
                    "Directory": str(root / Path(stack)),
                    "Model": "ILCE-7CM2",
                    "LensModel": (
                        "FE 100mm F2.8 Macro GM OSS + 2X Teleconverter"
                    ),
                    "LensType3": 33094,
                    "FNumber": float(expected["f_number"]),
                    "MaxApertureValue": 5.59591869015324,
                    "FocalLength": 200.0,
                    "FocalLengthIn35mmFormat": 200.0,
                    "ISO": 100,
                    "ExposureTime": float(expected["exposure_s"]),
                    "DateTimeOriginal": (
                        f"2026:08:30 12:{index // 60:02d}:{index % 60:02d}"
                    ),
                    "FocusPosition2": 58 + index % 4,
                }
            )
    return records


def run_exiftool(root: Path) -> tuple[list[dict[str, Any]], str]:
    if not root.is_dir():
        raise AuditError(f"RAW root does not exist: {root}")
    fields = [
        "Directory",
        "Model",
        "LensModel",
        "LensType3",
        "FNumber",
        "MaxApertureValue",
        "FocalLength",
        "FocalLengthIn35mmFormat",
        "ExposureTime",
        "ISO",
        "DateTimeOriginal",
        "FocusPosition2",
    ]
    command = ["exiftool", "-r", "-ext", "ARW", "-json", "-n"]
    command.extend(f"-{field}" for field in fields)
    command.append(str(root))
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise AuditError(
            f"ExifTool exited {completed.returncode}: {completed.stderr.strip()}"
        )
    try:
        records = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AuditError("ExifTool did not emit valid JSON") from exc
    if not isinstance(records, list):
        raise AuditError("ExifTool JSON top level is not a list")
    version = subprocess.run(
        ["exiftool", "-ver"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    return records, version


def tree_inventory(root: Path) -> dict[str, int]:
    file_count = 0
    byte_count = 0
    for directory, _, filenames in os.walk(root):
        for filename in filenames:
            stat = (Path(directory) / filename).stat()
            file_count += 1
            byte_count += stat.st_size
    return {"file_count": file_count, "byte_count": byte_count}


def physics_payload() -> dict[str, Any]:
    pitch_x_um = SENSOR_WIDTH_MM * 1000.0 / EFFECTIVE_WIDTH_PX
    pitch_y_um = SENSOR_HEIGHT_MM * 1000.0 / EFFECTIVE_HEIGHT_PX
    nyquist_x = 1000.0 / (2.0 * pitch_x_um)
    nyquist_y = 1000.0 / (2.0 * pitch_y_um)
    frequencies = [10.0, 20.0, 40.0, 60.0, 80.0, nyquist_x]
    rows = []
    for f_number in (5.6, 8.0, 11.0):
        rows.append(
            {
                "recorded_system_f_number": f_number,
                "airy_first_zero_diameter_um": airy_diameter_um(f_number),
                "airy_diameter_sensor_px_x": (
                    airy_diameter_um(f_number) / pitch_x_um
                ),
                "cutoff_lpmm": 1.0 / (WAVELENGTH_MM * f_number),
                "ideal_mtf": {
                    f"{frequency:.12g}": diffraction_mtf(
                        frequency, f_number
                    )
                    for frequency in frequencies
                },
            }
        )

    double_counted = [
        {
            "f_number": f_number,
            "airy_first_zero_diameter_um": airy_diameter_um(f_number),
        }
        for f_number in (11.0, 16.0, 22.0)
    ]
    return {
        "wavelength_nm": WAVELENGTH_MM * 1e6,
        "sensor": {
            "official_size_mm": [SENSOR_WIDTH_MM, SENSOR_HEIGHT_MM],
            "official_effective_dimensions_px": [
                EFFECTIVE_WIDTH_PX,
                EFFECTIVE_HEIGHT_PX,
            ],
            "derived_pitch_um": {
                "horizontal": pitch_x_um,
                "vertical": pitch_y_um,
            },
            "derived_nyquist_lpmm": {
                "horizontal": nyquist_x,
                "vertical": nyquist_y,
            },
        },
        "recorded_system_f_number_rows": rows,
        "question_values_if_tc_were_double_counted": double_counted,
        "formulae": {
            "airy_first_zero_diameter": "2.44 * wavelength * N",
            "cutoff": "1 / (wavelength * N)",
            "ideal_incoherent_mtf": (
                "(2/pi) * (acos(x) - x*sqrt(1-x^2)), "
                "x = frequency*wavelength*N"
            ),
            "working_f_number": "Nw = (1 + magnification/pupil_magnification) * N",
        },
        "working_f_number_status": (
            "NOT IDENTIFIED BY EXIF: capture magnification and pupil "
            "magnification are not both recorded"
        ),
    }


def build_result(
    records: list[dict[str, Any]],
    root: Path,
    metadata_source: str,
    exiftool_version: str,
) -> dict[str, Any]:
    summaries = validate_metadata(records, root)
    physics = physics_payload()
    directions = directional_controls()
    validation = pupil_model_validation()
    counterexample = aberration_counterexample()

    corrected_reporting = (
        all(close(row["max_aperture"], 5.6, 0.02) for row in summaries)
        and all(close(row["focal_length_mm"], 200.0, 0.01) for row in summaries)
    )
    if not corrected_reporting:
        raise AuditError("EXIF does not establish TC-corrected reporting")

    verdict = counterexample_verdict(counterexample)
    result = {
        "schema": SCHEMA,
        "status": "PASS",
        "scope": "metadata and physics only; zero RAW pixels decoded",
        "metadata_source": metadata_source,
        "exiftool_version": exiftool_version,
        "raw_root": str(root),
        "raw_tree_write_operations": 0,
        "file_count": len(records),
        "stacks": summaries,
        "exif_interpretation": {
            "teleconverter_magnification": 2.0,
            "nominal_f_number_multiplier": 2.0,
            "nominal_light_factor": 4.0,
            "nominal_stop_cost": 2.0,
            "bare_lens_max_aperture": 2.8,
            "expected_post_tc_max_aperture": 5.6,
            "observed_max_aperture": summaries[0]["max_aperture"],
            "observed_focal_length_mm": summaries[0]["focal_length_mm"],
            "verdict": (
                "EXIF FNumber is already TC-corrected; multiplying the "
                "recorded 5.6/8/11 by two would double-count the TC"
            ),
        },
        "physics": physics,
        "directional_controls": directions,
        "pupil_model_validation": validation,
        "aberration_counterexample": counterexample,
        "actual_transfer_identification": {
            "independent_lower_bound_available": False,
            "ideal_mtf_is_upper_bound_only": True,
            "actual_lens_tc_wavefront_in_exif": False,
            "focus_state_bound_in_exif": False,
        },
        "verdict": verdict,
        "reason": (
            "The ideal diffraction order is monotone, but EXIF supplies no "
            "lower bound on realized transfer.  A valid aberrated pupil with "
            "the same f-number metadata reverses f/5.6 and f/8."
        ),
        "candidate_built": False,
        "m167_executed": False,
        "confidence_interval": "NO CI",
        "sources": SOURCE_URLS,
    }
    return result


def assert_self_test(result: dict[str, Any]) -> None:
    physics = result["physics"]
    pitch = physics["sensor"]["derived_pitch_um"]["horizontal"]
    if not close(pitch, 5.122716894977169, 1e-12):
        raise AuditError(f"pixel-pitch reference mismatch: {pitch}")
    if not close(airy_diameter_um(8.0), 10.736, 1e-12):
        raise AuditError("Airy-diameter reference mismatch")
    mtf_f8_40 = diffraction_mtf(40.0, 8.0)
    if not close(mtf_f8_40, 0.7770721787377866, 1e-12):
        raise AuditError(f"MTF reference mismatch: {mtf_f8_40}")
    if result["verdict"] != "NOT_FORCED":
        raise AuditError("frozen physical stop verdict was not NOT_FORCED")
    if (
        counterexample_verdict({"f8_exceeds_f5_6": False})
        != "INDETERMINATE"
    ):
        raise AuditError("counterexample-negative verdict mapping is broken")
    if not result["aberration_counterexample"]["f8_exceeds_f5_6"]:
        raise AuditError("counterexample reversal missing")
    directions = result["directional_controls"]
    if not directions["planted_improvement"]["strictly_above_base"]:
        raise AuditError("planted improvement was not detected")
    if not directions["planted_degradation"]["strictly_below_base"]:
        raise AuditError("planted degradation was not detected")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    resolved = path.resolve()
    if resolved.drive.lower() == "d:":
        raise AuditError(f"refusing to write under read-only D: tree: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def source_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, default=RAW_ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_test:
            records = synthetic_metadata(args.raw_root)
            result = build_result(
                records,
                args.raw_root,
                metadata_source="synthetic-self-test",
                exiftool_version="NOT_INVOKED",
            )
            assert_self_test(result)
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "verdict": result["verdict"],
                        "planted_improvement": result[
                            "directional_controls"
                        ]["planted_improvement"],
                        "planted_degradation": result[
                            "directional_controls"
                        ]["planted_degradation"],
                        "counterexample_f8_exceeds_f5_6": result[
                            "aberration_counterexample"
                        ]["f8_exceeds_f5_6"],
                    },
                    sort_keys=True,
                )
            )
            return 0

        if args.output is None:
            raise AuditError("--output is required outside --self-test")
        tree_before = tree_inventory(args.raw_root)
        records, version = run_exiftool(args.raw_root)
        tree_after = tree_inventory(args.raw_root)
        if tree_before != tree_after:
            raise AuditError(
                f"read-only RAW tree changed: {tree_before} -> {tree_after}"
            )
        result = build_result(
            records,
            args.raw_root,
            metadata_source="ExifTool metadata-only recursive census",
            exiftool_version=version,
        )
        result["raw_tree_inventory_before"] = tree_before
        result["raw_tree_inventory_after"] = tree_after
        result["raw_tree_inventory_unchanged"] = True
        result["audit_source_sha256"] = source_sha256()
        assert_self_test(result)
        write_json(args.output, result)
        print(
            f"PASS: {len(records)} metadata records; "
            f"physical verdict={result['verdict']}; RAW pixels decoded=0"
        )
        return 0
    except (AuditError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
