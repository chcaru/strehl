"""M182 kernel trade: analytic sweep plus probes through production Rust.

Run from the repository root:

    python experiments/M182-kernel-trade/analyze.py

The script writes only inside its own experiment directory. It does not inspect
the RAW corpus. Frequencies are cycles per gather-plane sample unless a field
explicitly says otherwise.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import subprocess
import sys
from copy import deepcopy
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESTORE = ROOT / "crates" / "strehl-core" / "src" / "restore.rs"
ALIGN = ROOT / "crates" / "strehl-core" / "src" / "align.rs"
ALIGN_CMD = ROOT / "crates" / "strehl-cli" / "src" / "align_cmd.rs"
MANIFEST = HERE / "Cargo.toml"
PROBE = HERE / "probe.tsv"
RESULTS = HERE / "results.json"
MTF_CURVE = HERE / "mtf-curve.csv"
RESTORATION_CURVE = HERE / "restoration-curve.csv"
TAP_PHASES = HERE / "tap-phase-sums.csv"

KERNELS = (
    "nearest",
    "bilinear",
    "catmull-rom",
    "clamped-catmull-rom",
    "lanczos2",
    "lanczos3",
)
LINEAR_KERNELS = tuple(k for k in KERNELS if k != "clamped-catmull-rom")
OFFSETS = {
    "nearest": (0, 1),
    "bilinear": (0, 1),
    "catmull-rom": (-1, 0, 1, 2),
    "lanczos2": (-1, 0, 1, 2),
    "lanczos3": (-2, -1, 0, 1, 2, 3),
}
RAW_PHASE_INTERVALS = 1_000_000
REPORTED_TAP_PHASE_INTERVALS = 4_096
DC_TOLERANCE = 1e-6
MODEL_MEASUREMENT_TOLERANCE = 2e-6
SELECTED_INDICES = (64, 128, 192)
RESTORATION_INDICES = (64, 128, 192, 256)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def require_once(text: str, anchor: str, label: str) -> None:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"{label}: expected unique anchor, found {count}: {anchor!r}")


def check_source_anchors() -> dict:
    restore = RESTORE.read_text(encoding="utf-8")
    align = ALIGN.read_text(encoding="utf-8")
    align_cmd = ALIGN_CMD.read_text(encoding="utf-8")
    anchors = [
        (
            "restore-supported",
            restore,
            "!matches!(r, Resampler::ClampedCatmullRom)",
        ),
        (
            "restore-nearest-tie",
            restore,
            "            if a < 0.5 {\n                1.0\n            } else {\n                0.0\n            }",
        ),
        (
            "restore-bilinear-tap",
            restore,
            "        Resampler::Bilinear => (1.0 - a).max(0.0),",
        ),
        (
            "restore-catmull-inner",
            restore,
            "                1.5 * a * a * a - 2.5 * a * a + 1.0",
        ),
        (
            "restore-catmull-outer",
            restore,
            "                -0.5 * a * a * a + 2.5 * a * a - 4.0 * a + 2.0",
        ),
        (
            "restore-lanczos-tap",
            restore,
            "                (pt.sin() / pt) * ((pt / n).sin() / (pt / n))",
        ),
        (
            "restore-frequency-unit",
            restore,
            "/// Phase-averaged MTF of one gather, at `f` cycles per **sample of the plane",
        ),
        (
            "align-enum",
            align,
            "pub enum Resampler {\n    Nearest,\n    Bilinear,\n    CatmullRom,\n    ClampedCatmullRom,\n    Lanczos2,\n    Lanczos3,\n}",
        ),
        (
            "align-clamped-sampler",
            align,
            "pub fn sample_clamped_catmull_rom(p: PlaneRef<'_>, x: f64, y: f64) -> f32 {",
        ),
        (
            "align-lanczos2-sampler",
            align,
            "pub fn sample_lanczos2(p: PlaneRef<'_>, x: f64, y: f64) -> f32 {",
        ),
        (
            "align-lanczos3-sampler",
            align,
            "pub fn sample_lanczos3(p: PlaneRef<'_>, x: f64, y: f64) -> f32 {",
        ),
        (
            "default-resampler",
            align_cmd,
            'pub const DEFAULT_RESAMPLER_NAME: &str = "catmull-rom";',
        ),
    ]
    for label, text, anchor in anchors:
        require_once(text, anchor, label)
    tap_start = restore.index("fn tap(r: Resampler, t: f64) -> f64 {")
    tap_end = restore.index("\nfn support(r: Resampler)", tap_start)
    tap_block = restore[tap_start:tap_end]
    return {
        "anchors": [
            {"id": label, "count": text.count(anchor), "anchor": anchor}
            for label, text, anchor in anchors
        ],
        "files": {
            str(RESTORE.relative_to(ROOT)).replace("\\", "/"): sha256_file(RESTORE),
            str(ALIGN.relative_to(ROOT)).replace("\\", "/"): sha256_file(ALIGN),
            str(ALIGN_CMD.relative_to(ROOT)).replace("\\", "/"): sha256_file(ALIGN_CMD),
        },
        "tap_block_sha256": sha256_bytes(tap_block.encode("utf-8")),
    }


def raw_tap(kernel: str, t: float) -> float:
    """Exact f64 formulas in restore.rs::tap, intentionally unnormalised."""
    a = abs(t)
    if kernel == "nearest":
        return 1.0 if a < 0.5 else 0.0
    if kernel == "bilinear":
        return max(1.0 - a, 0.0)
    if kernel == "catmull-rom":
        if a < 1.0:
            return 1.5 * a * a * a - 2.5 * a * a + 1.0
        if a < 2.0:
            return -0.5 * a * a * a + 2.5 * a * a - 4.0 * a + 2.0
        return 0.0
    if kernel in {"lanczos2", "lanczos3"}:
        support = 2.0 if kernel == "lanczos2" else 3.0
        if a >= support:
            return 0.0
        if a < 1e-12:
            return 1.0
        pt = math.pi * t
        return (math.sin(pt) / pt) * (math.sin(pt / support) / (pt / support))
    raise ValueError(f"{kernel} has no tap(): the production function rejects it")


def sweep_raw_taps() -> dict:
    out = {}
    for kernel in LINEAR_KERNELS:
        minimum = math.inf
        minimum_phase = 0.0
        max_negative_mass = 0.0
        max_negative_phase = 0.0
        sum_min = math.inf
        sum_min_phase = 0.0
        sum_max = -math.inf
        sum_max_phase = 0.0
        max_sum_error = 0.0
        max_sum_error_phase = 0.0
        effective_minimum = math.inf
        effective_negative_mass = 0.0
        zero_sum_phases = 0
        for i in range(RAW_PHASE_INTERVALS + 1):
            phase = i / RAW_PHASE_INTERVALS
            weights = [raw_tap(kernel, n - phase) for n in OFFSETS[kernel]]
            local_min = min(weights)
            if local_min < minimum:
                minimum = local_min
                minimum_phase = phase
            negative_mass = -sum(min(0.0, value) for value in weights)
            if negative_mass > max_negative_mass:
                max_negative_mass = negative_mass
                max_negative_phase = phase
            total = sum(weights)
            if total < sum_min:
                sum_min = total
                sum_min_phase = phase
            if total > sum_max:
                sum_max = total
                sum_max_phase = phase
            error = abs(total - 1.0)
            if error > max_sum_error:
                max_sum_error = error
                max_sum_error_phase = phase
            if abs(total) < 1e-15:
                zero_sum_phases += 1
            else:
                normalized = [value / total for value in weights]
                effective_minimum = min(effective_minimum, min(normalized))
                effective_negative_mass = max(
                    effective_negative_mass,
                    -sum(min(0.0, value) for value in normalized),
                )
        out[kernel] = {
            "tap_defined": True,
            "phase_intervals": RAW_PHASE_INTERVALS,
            "phase_endpoints_included": True,
            "most_negative_raw_tap": minimum,
            "most_negative_raw_tap_phase": minimum_phase,
            "maximum_raw_negative_mass": max_negative_mass,
            "maximum_raw_negative_mass_phase": max_negative_phase,
            "raw_sum_min": sum_min,
            "raw_sum_min_phase": sum_min_phase,
            "raw_sum_max": sum_max,
            "raw_sum_max_phase": sum_max_phase,
            "raw_sum_max_abs_error": max_sum_error,
            "raw_sum_max_abs_error_phase": max_sum_error_phase,
            "raw_zero_sum_phase_count": zero_sum_phases,
            "most_negative_normalized_tap": effective_minimum,
            "maximum_normalized_negative_mass": effective_negative_mass,
        }
    out["clamped-catmull-rom"] = {
        "tap_defined": False,
        "reason": "restore.rs::tap reaches unreachable! for the nonlinear clamped variant",
        "underlying_pre_clamp_kernel": "catmull-rom",
        "underlying_pre_clamp": deepcopy(out["catmull-rom"]),
    }
    return out


def write_tap_phase_sums() -> None:
    """Report every member of a separate dense phase grid, not only extrema."""
    with TAP_PHASES.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "kernel",
                "phase",
                "restore_raw_tap_sum",
                "gather_mtf_sum_after_normalization",
                "shipping_constant_plane_response",
                "underlying_preclamp_raw_sum",
                "note",
            ]
        )
        for kernel in KERNELS:
            for i in range(REPORTED_TAP_PHASE_INTERVALS + 1):
                phase = i / REPORTED_TAP_PHASE_INTERVALS
                if kernel == "clamped-catmull-rom":
                    underlying = sum(
                        raw_tap("catmull-rom", n - phase)
                        for n in OFFSETS["catmull-rom"]
                    )
                    writer.writerow(
                        [
                            kernel,
                            f"{phase:.12f}",
                            "",
                            "",
                            "1.000000000000",
                            f"{underlying:.12f}",
                            "tap() undefined; nonlinear output clamp",
                        ]
                    )
                    continue
                raw_sum = sum(raw_tap(kernel, n - phase) for n in OFFSETS[kernel])
                effective_sum = "" if abs(raw_sum) < 1e-15 else "1.000000000000"
                note = ""
                if kernel == "nearest" and abs(phase - 0.5) < 1e-15:
                    note = (
                        "restore tap model has zero sum at exact tie; "
                        "shipping round() chooses the upper sample"
                    )
                writer.writerow(
                    [
                        kernel,
                        f"{phase:.12f}",
                        f"{raw_sum:.12f}",
                        effective_sum,
                        "1.000000000000",
                        "",
                        note,
                    ]
                )


def run_probe() -> tuple[str, str]:
    command = [
        "cargo",
        "run",
        "--quiet",
        "--release",
        "--manifest-path",
        str(MANIFEST),
    ]
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Rust probe exited {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
    PROBE.write_text(proc.stdout, encoding="utf-8", newline="\n")
    return proc.stdout, proc.stderr


def parse_probe(text: str) -> dict:
    parsed = {
        "tap_probe": {},
        "overshoot": {},
        "support": {},
        "mtf": {kernel: {} for kernel in KERNELS},
        "fidelity": {kernel: {} for kernel in KERNELS},
        "control": {},
        "fir": {},
        "restoration": {},
        "apply": {},
    }
    header = None
    trailer = None
    for line_number, line in enumerate(text.splitlines(), 1):
        fields = line.split("\t")
        kind = fields[0]
        try:
            if kind == "H":
                header = fields
            elif kind == "T":
                parsed["tap_probe"][fields[1]] = {
                    "most_negative_effective_delta_response": float(fields[2]),
                    "maximum_effective_negative_mass": float(fields[3]),
                    "maximum_basis_sum_error": float(fields[4]),
                    "maximum_constant_dc_error": float(fields[5]),
                    "phase_samples": 131_072,
                }
            elif kind == "O":
                parsed["overshoot"][fields[1]] = {
                    "step": {
                        "dn": float(fields[2]),
                        "fraction_of_1000_dn_range": float(fields[2]) / 1000.0,
                        "phase": float(fields[3]),
                        "x": float(fields[4]),
                    },
                    "impulse": {
                        "dn": float(fields[5]),
                        "fraction_of_1000_dn_range": float(fields[5]) / 1000.0,
                        "phase": float(fields[6]),
                        "x": float(fields[7]),
                    },
                }
            elif kind == "P":
                parsed["support"][fields[1]] = fields[2] == "true"
            elif kind == "M":
                kernel = fields[1]
                index = int(fields[2])
                parsed["mtf"][kernel][index] = {
                    "frequency_plane": float(fields[3]),
                    "model": None if fields[4] == "NA" else float(fields[4]),
                    "empirical": None if fields[5] == "NA" else float(fields[5]),
                }
            elif kind == "C":
                parsed["control"] = {
                    "name": fields[1],
                    "frequency_plane": float(fields[2]),
                    "baseline": float(fields[3]),
                    "inert_dc_offset": float(fields[4]),
                    "sharpened": float(fields[5]),
                    "blurred": float(fields[6]),
                }
            elif kind == "Q":
                parsed["fidelity"][fields[1]][int(fields[2])] = {
                    "frequency_plane": float(fields[3]),
                    "rms_error_relative_to_unit_amplitude_truth": float(fields[4]),
                }
            elif kind == "F":
                kernel = fields[1]
                key = fields[2]
                parsed["fir"][(kernel, key)] = {
                    "kernel": kernel,
                    "lambda_noise_to_signal": float(fields[2]),
                    "noise_sd_ratio_1d": float(fields[3]),
                    "noise_sd_ratio_2d": float(fields[4]),
                    "minimum_realized_gain": float(fields[5]),
                    "maximum_realized_gain": float(fields[6]),
                    "half_taps": [float(value) for value in fields[7].split(",")],
                }
            elif kind == "R":
                kernel = fields[1]
                key = fields[2]
                index = int(fields[3])
                parsed["restoration"][(kernel, key, index)] = {
                    "frequency_plane": float(fields[4]),
                    "gather_mtf": float(fields[5]),
                    "realized_gain": float(fields[6]),
                    "restored_mtf": float(fields[7]),
                }
            elif kind == "A":
                parsed["apply"] = {
                    "name": fields[1],
                    "lambda_noise_to_signal": float(fields[2]),
                    "input_sd": float(fields[3]),
                    "output_sd": float(fields[4]),
                    "measured_sd_ratio": float(fields[5]),
                    "predicted_sd_ratio_from_realized_taps": float(fields[6]),
                }
            elif kind == "Z":
                trailer = fields
            else:
                raise ValueError(f"unknown record kind {kind!r}")
        except (IndexError, ValueError) as exc:
            raise RuntimeError(f"probe line {line_number} malformed: {line!r}") from exc
    if header is None or trailer != ["Z", "ok"]:
        raise RuntimeError("probe did not emit its H header and Z ok trailer")
    if tuple(parsed["tap_probe"]) != KERNELS:
        raise RuntimeError("tap probe did not emit the six kernels in enum order")
    for kernel in KERNELS:
        if len(parsed["mtf"][kernel]) != 257:
            raise RuntimeError(f"{kernel}: incomplete MTF curve")
    return parsed


def primary_mtf(row: dict) -> float:
    return row["model"] if row["model"] is not None else row["empirical"]


def crossing(curve: list[tuple[float, float]], level: float) -> float | None:
    for (f0, y0), (f1, y1) in zip(curve, curve[1:]):
        if y0 == level:
            return f0
        if (y0 - level) * (y1 - level) <= 0.0 and y1 != y0:
            return f0 + (level - y0) * (f1 - f0) / (y1 - y0)
    if curve[-1][1] == level:
        return curve[-1][0]
    return None


def derive_mtf(parsed: dict) -> tuple[dict, float]:
    maximum_model_measurement_error = 0.0
    for kernel in LINEAR_KERNELS:
        for row in parsed["mtf"][kernel].values():
            if row["empirical"] is not None:
                maximum_model_measurement_error = max(
                    maximum_model_measurement_error,
                    abs(row["model"] - row["empirical"]),
                )

    catmull = {
        index: primary_mtf(row) for index, row in parsed["mtf"]["catmull-rom"].items()
    }
    summary = {}
    for kernel in KERNELS:
        points = parsed["mtf"][kernel]
        curve = [
            (points[index]["frequency_plane"], primary_mtf(points[index]))
            for index in sorted(points)
        ]
        minimum_frequency, minimum_mtf = min(curve, key=lambda item: item[1])
        selected = {}
        for index in SELECTED_INDICES:
            frequency, value = curve[index]
            selected[str(index)] = {
                "nyquist_fraction": frequency / 0.5,
                "frequency_plane_cycles_per_sample": frequency,
                "frequency_demosaiced_output_cycles_per_pixel": frequency / 2.0,
                "mtf": value,
                "relative_to_catmull_rom": value / catmull[index],
                "rms_error_relative_to_unit_amplitude_truth": parsed["fidelity"][kernel][
                    index
                ]["rms_error_relative_to_unit_amplitude_truth"],
            }
        mtf50 = crossing(curve, 0.5)
        mtf10 = crossing(curve, 0.1)
        catmull_curve = [
            (
                parsed["mtf"]["catmull-rom"][index]["frequency_plane"],
                catmull[index],
            )
            for index in sorted(catmull)
        ]

        def interpolate_catmull(frequency: float | None) -> float | None:
            if frequency is None:
                return None
            for (f0, y0), (f1, y1) in zip(catmull_curve, catmull_curve[1:]):
                if f0 <= frequency <= f1:
                    if f1 == f0:
                        return y0
                    t = (frequency - f0) / (f1 - f0)
                    return y0 + t * (y1 - y0)
            return catmull_curve[-1][1]

        catmull_at_mtf50 = interpolate_catmull(mtf50)
        catmull_at_mtf10 = interpolate_catmull(mtf10)
        summary[kernel] = {
            "method": (
                "restore::gather_mtf (64-phase model)"
                if kernel != "clamped-catmull-rom"
                else "shipping sampler, 64-phase cosine fundamental (nonlinear; not an OTF)"
            ),
            "selected": selected,
            "minimum_in_band_mtf": minimum_mtf,
            "minimum_in_band_frequency_plane": minimum_frequency,
            "minimum_2d_diagonal_mtf": minimum_mtf * minimum_mtf,
            "maximum_1d_inverse_gain": 1.0 / minimum_mtf,
            "maximum_2d_diagonal_inverse_gain": 1.0 / (minimum_mtf * minimum_mtf),
            "mtf50_frequency_plane": mtf50,
            "mtf50_nyquist_fraction": None if mtf50 is None else mtf50 / 0.5,
            "mtf50_relative_to_catmull_rom": (
                None if catmull_at_mtf50 is None else 0.5 / catmull_at_mtf50
            ),
            "mtf10_frequency_plane": mtf10,
            "mtf10_nyquist_fraction": None if mtf10 is None else mtf10 / 0.5,
            "mtf10_relative_to_catmull_rom": (
                None if catmull_at_mtf10 is None else 0.1 / catmull_at_mtf10
            ),
        }
    return summary, maximum_model_measurement_error


def write_mtf_curve(parsed: dict) -> None:
    catmull = {
        index: primary_mtf(row) for index, row in parsed["mtf"]["catmull-rom"].items()
    }
    with MTF_CURVE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "kernel",
                "frequency_plane_cycles_per_sample",
                "nyquist_fraction",
                "frequency_demosaiced_output_cycles_per_pixel",
                "primary_method",
                "primary_mtf",
                "relative_to_catmull_rom",
                "model_mtf",
                "shipping_sampler_empirical_mtf",
            ]
        )
        for kernel in KERNELS:
            for index in range(257):
                row = parsed["mtf"][kernel][index]
                frequency = row["frequency_plane"]
                value = primary_mtf(row)
                writer.writerow(
                    [
                        kernel,
                        f"{frequency:.12f}",
                        f"{frequency / 0.5:.12f}",
                        f"{frequency / 2.0:.12f}",
                        "model" if row["model"] is not None else "empirical-fundamental",
                        f"{value:.12f}",
                        f"{value / catmull[index]:.12f}",
                        "" if row["model"] is None else f"{row['model']:.12f}",
                        "" if row["empirical"] is None else f"{row['empirical']:.12f}",
                    ]
                )


def derive_restoration(parsed: dict, mtf_summary: dict) -> dict:
    ideal = {}
    for kernel in KERNELS:
        if not parsed["support"][kernel]:
            ideal[kernel] = {
                "supported": False,
                "reason": "nonlinear clamped gather has no shift-invariant response to invert",
            }
            continue
        fir = parsed["fir"][(kernel, "0.000000000000")]
        selected = {}
        for index in RESTORATION_INDICES:
            row = parsed["restoration"][(kernel, "0.000000000000", index)]
            selected[str(index)] = row
        ideal[kernel] = {
            "supported": True,
            **fir,
            "selected": selected,
        }

    bilinear_trade = {}
    catmull_curve = {
        index: primary_mtf(parsed["mtf"]["catmull-rom"][index])
        for index in range(257)
    }
    for lambda_value in (0.0, 0.001, 0.01, 0.03, 0.1, 0.15, 0.2, 0.3):
        key = f"{lambda_value:.12f}"
        fir = parsed["fir"][("bilinear", key)]
        ratios = []
        selected = {}
        for index in range(257):
            row = parsed["restoration"][("bilinear", key, index)]
            ratio = row["restored_mtf"] / catmull_curve[index]
            ratios.append(ratio)
            if index in RESTORATION_INDICES:
                selected[str(index)] = {
                    **row,
                    "relative_to_unrestored_catmull_rom": ratio,
                }
        bilinear_trade[key] = {
            **fir,
            "selected": selected,
            "fraction_of_sampled_band_at_or_above_catmull_rom": sum(
                value >= 1.0 - 1e-12 for value in ratios
            )
            / len(ratios),
            "minimum_relative_to_catmull_rom": min(ratios),
            "maximum_relative_to_catmull_rom": max(ratios),
        }

    high_noise = {}
    for kernel in LINEAR_KERNELS:
        high_noise[kernel] = parsed["fir"][(kernel, "1000000.000000000000")]

    return {
        "frequency_convention": {
            "primary": "cycles per gather-plane sample",
            "nyquist_plane": 0.5,
            "demosaiced_output_conversion": "f_output_cycles_per_pixel = f_plane / 2",
            "grid_factor": 1.0,
            "grid_factor_equivalence": (
                "Within the representable gather band, this is equivalent to grid_factor=2 "
                "evaluated at half the output-pixel frequency; no above-knee fold is evaluated."
            ),
        },
        "controlled_spectrum": (
            "flat S(f)=1 with lambda=sigma^2/S; exact autocorrelation r[0]=1+lambda, "
            "r[k>0]=0; gain_cap=4; production design_fir half_taps=4"
        ),
        "ideal_inverse": ideal,
        "bilinear_trade": bilinear_trade,
        "high_noise_null": high_noise,
        "apply_control": parsed["apply"],
        "conditioning": {
            kernel: {
                "restoration_supported": parsed["support"][kernel],
                "minimum_in_band_mtf_1d": mtf_summary[kernel]["minimum_in_band_mtf"],
                "minimum_in_band_mtf_2d_diagonal": mtf_summary[kernel][
                    "minimum_2d_diagonal_mtf"
                ],
                "maximum_inverse_gain_1d": mtf_summary[kernel]["maximum_1d_inverse_gain"],
                "maximum_inverse_gain_2d_diagonal": mtf_summary[kernel][
                    "maximum_2d_diagonal_inverse_gain"
                ],
            }
            for kernel in KERNELS
        },
    }


def write_restoration_curve(parsed: dict) -> None:
    catmull = {
        index: primary_mtf(parsed["mtf"]["catmull-rom"][index])
        for index in range(257)
    }
    with RESTORATION_CURVE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(
            [
                "kernel",
                "lambda_sigma2_over_signal_power",
                "frequency_plane_cycles_per_sample",
                "frequency_demosaiced_output_cycles_per_pixel",
                "gather_mtf",
                "realized_restoration_gain",
                "restored_mtf",
                "restored_relative_to_unrestored_catmull_rom",
            ]
        )
        for (kernel, key, index), row in sorted(parsed["restoration"].items()):
            frequency = row["frequency_plane"]
            writer.writerow(
                [
                    kernel,
                    key,
                    f"{frequency:.12f}",
                    f"{frequency / 2.0:.12f}",
                    f"{row['gather_mtf']:.12f}",
                    f"{row['realized_gain']:.12f}",
                    f"{row['restored_mtf']:.12f}",
                    f"{row['restored_mtf'] / catmull[index]:.12f}",
                ]
            )


def command_version(command: list[str]) -> str:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return (proc.stdout or proc.stderr).strip()


def main() -> int:
    print("M182: checking unique production-source anchors")
    source = check_source_anchors()
    print(f"  12/12 anchors matched exactly once")

    print(f"M182: sweeping raw restore.rs taps over {RAW_PHASE_INTERVALS + 1:,} phases")
    raw = sweep_raw_taps()
    write_tap_phase_sums()
    for kernel in LINEAR_KERNELS:
        row = raw[kernel]
        print(
            f"  {kernel:<12} min {row['most_negative_raw_tap']:+.9f}  "
            f"negative mass {row['maximum_raw_negative_mass']:.9f}  "
            f"raw sum error {row['raw_sum_max_abs_error']:.9f}"
        )
    print("  clamped-catmull-rom: no tap() (production rejects nonlinear kernel)")

    print("M182: running production Rust probe")
    probe_text, probe_stderr = run_probe()
    parsed = parse_probe(probe_text)
    print(f"  {len(probe_text.splitlines()):,} records; trailer Z ok")

    mtf_summary, model_measurement_error = derive_mtf(parsed)
    print(f"  max model-vs-shipping MTF error {model_measurement_error:.3e}")
    write_mtf_curve(parsed)
    restoration = derive_restoration(parsed, mtf_summary)
    write_restoration_curve(parsed)

    control = parsed["control"]
    controls = {
        "production_restore_selftest": {"pass": True},
        "model_vs_shipping_mtf": {
            "maximum_absolute_error": model_measurement_error,
            "tolerance": MODEL_MEASUREMENT_TOLERANCE,
            "pass": model_measurement_error < MODEL_MEASUREMENT_TOLERANCE,
        },
        "convex_kernel_overshoot_null": {
            "nearest_step_dn": parsed["overshoot"]["nearest"]["step"]["dn"],
            "nearest_impulse_dn": parsed["overshoot"]["nearest"]["impulse"]["dn"],
            "bilinear_step_dn": parsed["overshoot"]["bilinear"]["step"]["dn"],
            "bilinear_impulse_dn": parsed["overshoot"]["bilinear"]["impulse"]["dn"],
            "pass": all(
                parsed["overshoot"][kernel][plant]["dn"] == 0.0
                for kernel in ("nearest", "bilinear")
                for plant in ("step", "impulse")
            ),
        },
        "mtf_direction_control": {
            **control,
            "inert_absolute_difference": abs(
                control["inert_dc_offset"] - control["baseline"]
            ),
            "positive_sharpening_ratio": control["sharpened"] / control["baseline"],
            "negative_blur_ratio": control["blurred"] / control["baseline"],
            "pass": (
                abs(control["inert_dc_offset"] - control["baseline"]) < 1e-9
                and control["sharpened"] > control["baseline"] * 1.2
                and control["blurred"] < control["baseline"] * 0.8
            ),
        },
        "restore_application_noise_prediction": {
            **parsed["apply"],
            "absolute_error": abs(
                parsed["apply"]["measured_sd_ratio"]
                - parsed["apply"]["predicted_sd_ratio_from_realized_taps"]
            ),
            "tolerance": 0.005,
            "pass": abs(
                parsed["apply"]["measured_sd_ratio"]
                - parsed["apply"]["predicted_sd_ratio_from_realized_taps"]
            )
            < 0.005,
        },
        "high_noise_identity_null": {
            "pass": all(
                row["noise_sd_ratio_2d"] == 1.0
                and row["minimum_realized_gain"] == 1.0
                and row["maximum_realized_gain"] == 1.0
                and row["half_taps"] == [1.0, 0.0, 0.0, 0.0, 0.0]
                for row in restoration["high_noise_null"].values()
            )
        },
    }
    if not all(control_row["pass"] for control_row in controls.values() if "pass" in control_row):
        raise RuntimeError(f"one or more controls failed: {controls}")

    result = {
        "schema": "m182-kernel-trade-v1",
        "frequency_convention": {
            "primary": "cycles per gather-plane sample",
            "plane_nyquist": 0.5,
            "demosaiced_output_conversion": "divide plane frequency by 2",
            "selected_nyquist_fractions": [0.25, 0.5, 0.75],
        },
        "methods": {
            "raw_tap_sweep_phases": RAW_PHASE_INTERVALS + 1,
            "reported_tap_sum_curve_phases": REPORTED_TAP_PHASE_INTERVALS + 1,
            "shipping_tap_probe_phases": 131_072,
            "mtf_phase_average_phases": 64,
            "mtf_curve_points_inclusive_of_dc_and_nyquist": 257,
            "step_input_range_dn": 1000.0,
            "synthetic_only": True,
        },
        "source": source,
        "raw_taps": raw,
        "shipping_effective_tap_probe": parsed["tap_probe"],
        "overshoot": parsed["overshoot"],
        "restoration_supported": parsed["support"],
        "mtf": mtf_summary,
        "restoration": restoration,
        "controls": controls,
        "artifacts": {
            "probe_tsv_sha256": sha256_bytes(probe_text.encode("utf-8")),
            "probe_tsv_lines": len(probe_text.splitlines()),
            "probe_stderr": probe_stderr,
            "mtf_curve": MTF_CURVE.name,
            "mtf_curve_sha256": sha256_file(MTF_CURVE),
            "mtf_curve_lines": len(MTF_CURVE.read_text(encoding="utf-8").splitlines()),
            "restoration_curve": RESTORATION_CURVE.name,
            "restoration_curve_sha256": sha256_file(RESTORATION_CURVE),
            "restoration_curve_lines": len(
                RESTORATION_CURVE.read_text(encoding="utf-8").splitlines()
            ),
            "tap_phase_sums": TAP_PHASES.name,
            "tap_phase_sums_sha256": sha256_file(TAP_PHASES),
            "tap_phase_sums_lines": len(
                TAP_PHASES.read_text(encoding="utf-8").splitlines()
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "rustc": command_version(["rustc", "--version"]),
            "cargo": command_version(["cargo", "--version"]),
            "repository_head_at_measurement": command_version(
                ["git", "rev-parse", "HEAD"]
            ),
        },
    }
    RESULTS.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"M182: wrote {RESULTS.relative_to(ROOT)}")
    print(f"M182: wrote {MTF_CURVE.relative_to(ROOT)}")
    print(f"M182: wrote {RESTORATION_CURVE.relative_to(ROOT)}")
    print(f"M182: wrote {TAP_PHASES.relative_to(ROOT)}")
    print("M182: all measurement controls PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
