"""M128 commissioning battery.

Synthetic controls use the M128 crossing locator and M88's validated SFR
instrument.  The only deliberate uses of M88's locator are the required C0
library regression and C7 comparison arm.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
M88_ROOT = ROOT.parent / "M88-optical-ceiling"
M88_SRC = M88_ROOT / "src"
M88_CONTROL = M88_ROOT / "out" / "s03_controls.json"
M88_SCRIPT = M88_SRC / "s03_controls.py"
M88_LIB = M88_SRC / "m88lib.py"

sys.path.insert(0, str(HERE))
import sfr_run as S  # noqa: E402

L = S.L

EXPECTED_M88_SHA256 = (
    "7d08a7eadba3f4b36f5e84bd41a2b632c49d01914d59b5079a2f8da9c2acb950"
)

FC_VALUES = (87.0, 105.54, 135.17, 60.0, 200.0)
ANGLES_DEG = (-0.68, -3.0, 5.0)
APERTURES = (5.6, 8.0, 11.0)
B_VALUES = (3.0763, 3.7319, 2.4020)
LAMBDA_MM = 550e-6
RISE_A_UM_CYMM = 1009.41

FRAME_H = 440
FRAME_W = 1800
PLANT_SUB = 6
REPLICATES = 3
C9_REPLICATES = 5
REGISTRATION_SWEEP = (1, 2, 4, 8, 16, 32, 64, 128, 256, "inf")

GAIN_E_PER_DN = 2.3
READ_NOISE_DN = 3.0

CLEAN_BRIGHT_DN = 4000.0
CLEAN_DARK_DN = 200.0
SUBJECT_BRIGHT_DN = 2600.0
SUBJECT_DARK_DN = 60.0
RIDGE_PEAK_DN = 6394.0
RIDGE_OFFSET_UM = -150.0
RIDGE_SIGMA_UM = 12.0
GLARE_NEAR_DN = 480.0
GLARE_EXCESS_DN = GLARE_NEAR_DN - SUBJECT_DARK_DN
GLARE_PLATEAU_UM = 8.0 * 2.0 * L.PITCH_UM
GLARE_FAR_UM = 80.0 * 2.0 * L.PITCH_UM
GLARE_TAU_UM = (GLARE_FAR_UM - GLARE_PLATEAU_UM) / math.log(
    GLARE_EXCESS_DN / 5.0
)
RAGGED_RMS_GREEN_PX = 1.23

BASE_SETTINGS = {
    "half_um": 96.0,
    "bin_um": 0.64,
    "taper": 0.10,
    "core_um": 48.0,
    "axis": "horizontal",
    "deramp": True,
    "f_lo": 10.0,
    "f_hi": 150.0,
}

FLAT_MIN_CONTRAST_DN = 500.0
FLAT_MAX_FIT_RMS = 0.10

DESCRIPTIONS = {
    "C0": "M88 validated-instrument byte regression",
    "C1": "Clean analytic edge plants over cutoff and slant",
    "C2": "Analytic plants with measured razor contamination",
    "C3": "Disjoint along-edge crops of one synthetic frame",
    "C4": "Flat-field ROI with no edge",
    "C5": "Three-aperture planted ladders",
    "C6": "Positive-improvement sharpness ladder",
    "C7": "Crossing locator versus M88 ridge locator",
    "C8": "Synthetic half-width and bin-width settings sweep",
    "C9": "Along-edge registration smoothing-length commissioning",
}

BARS = {
    "C0": (
        "Existing and regenerated M88 s03_controls.json must be byte-identical "
        "at SHA-256 7d08a7ea...c950."
    ),
    "C1": (
        "For every planted cutoff/slant combination, the median of three "
        "independent noisy recoveries must be within +/-3%."
    ),
    "C2": (
        "For every planted cutoff/slant combination, both the full measured "
        "contamination and each single-contaminant diagnostic must recover "
        "cutoff within +/-5%."
    ),
    "C3": "Two non-overlapping same-frame crop estimates must agree within 5%.",
    "C4": (
        "The crossing pipeline must raise EdgeFitError, or be objectively "
        "rejected by contrast <500 DN, unsuccessful fit, or fit RMS >0.10."
    ),
    "C5": (
        "For each planted B, the primary fit_fc reduction must recover B "
        "within +/-5%; the rise-ladder result is reported as secondary."
    ),
    "C6": (
        "Recovered cutoff must be monotone and within +/-5% at every one of "
        "at least five planted sharpness values."
    ),
    "C7": (
        "On the identical full C2 plant, crossing must be within 5% and M88 "
        "must be outside 5% or refuse; an accurate M88 result means the bevel "
        "plant did not reproduce the registered failure."
    ),
    "C8": (
        "At least one registered setting must recover the known full-C2 truth "
        "within 5%; choose minimum absolute error, then fit RMS."
    ),
    "C9": (
        "The planted wander must retain >=95% RMS after cubic removal, and a "
        "shape-selected plateau W must recover all three planted cutoffs "
        "within +/-3%."
    ),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def array_sha256(a: np.ndarray) -> str:
    return sha256_bytes(np.ascontiguousarray(a).tobytes())


def json_ready(value):
    if isinstance(value, np.generic):
        return json_ready(value.item())
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(v) for v in value]
    return value


def record(cid: str, measurements, status: str, headline: str):
    return {
        "id": cid,
        "description": DESCRIPTIONS[cid],
        "measurements": measurements,
        "bar": BARS[cid],
        "status": status,
        "headline": headline,
    }


def skipped(cid: str, reason: str):
    return record(cid, {"reason": reason}, "SKIP", reason)


def errored(cid: str, exc: Exception):
    text = f"{type(exc).__name__}: {exc}"
    return record(cid, {"exception": text}, "ERROR", text)


def add_noise(img_dn: np.ndarray, seed: int) -> np.ndarray:
    """Poisson shot noise at 2.3 e-/DN plus 3 DN Gaussian read noise."""
    rng = np.random.default_rng(seed)
    electrons = np.maximum(img_dn, 0.0) * GAIN_E_PER_DN
    noisy = rng.poisson(electrons).astype(np.float64) / GAIN_E_PER_DN
    noisy += rng.normal(0.0, READ_NOISE_DN, size=img_dn.shape)
    return noisy


def fit_fields(result: dict) -> dict:
    keys = (
        "fc_cymm",
        "sigma_um",
        "amp",
        "rms_resid",
        "success",
        "n_pts",
        "angle_deg",
        "resid_sd_px",
        "contrast",
        "lo_dn",
        "hi_dn",
        "min_bin_count",
    )
    return {k: result[k] for k in keys}


def _roi_parts(noisy, crop):
    sub, xs, ys = L.green_sites(noisy, "G1")
    if crop is None:
        row0, col0, nrow, ncol = 0, 0, sub.shape[0], sub.shape[1]
    else:
        row0, col0, nrow, ncol = crop
    s = sub[row0 : row0 + nrow, col0 : col0 + ncol]
    xr = xs[col0 : col0 + ncol]
    yr = ys[row0 : row0 + nrow]
    return s, xr, yr


def _line_y(line: dict, x_sensor: np.ndarray) -> np.ndarray:
    if abs(line["ny"]) < 1e-12:
        raise L.EdgeFitError("registered locus requires a near-horizontal edge")
    return line["y0"] - (x_sensor - line["x0"]) * line["nx"] / line["ny"]


def _box_smooth(values: np.ndarray, width: int) -> np.ndarray:
    if width <= 1:
        return values.copy()
    left = (width - 1) // 2
    right = width // 2
    padded = np.pad(values, (left, right), mode="reflect")
    return np.convolve(padded, np.ones(width) / width, mode="valid")


def _registration_from_crossings(
    s: np.ndarray,
    xr: np.ndarray,
    yr: np.ndarray,
    line: dict,
    registration_w: int | str,
) -> dict:
    x_local, y_local, _, _ = S.geom.crossings(
        s, 0, s.shape[0], bright_first=True
    )
    if len(x_local) < 64:
        raise L.EdgeFitError(f"only {len(x_local)} clean crossings in ROI")
    keep = np.ones(len(x_local), bool)
    p = np.polyfit(x_local, y_local, 1)
    for _ in range(4):
        residual = y_local - np.polyval(p, x_local)
        sd = float(np.std(residual[keep])) if keep.any() else 0.0
        if sd <= 0:
            break
        next_keep = np.abs(residual) <= 3.0 * sd
        if next_keep.sum() < 64:
            break
        keep = next_keep
        p = np.polyfit(x_local[keep], y_local[keep], 1)

    indices = np.rint(x_local).astype(int)
    d_across = float(yr[1] - yr[0])
    crossing_y = yr[0] + y_local * d_across
    crossing_x = xr[indices]
    residual_y = crossing_y - _line_y(line, crossing_x)
    full_residual = np.interp(
        xr,
        crossing_x[keep],
        residual_y[keep],
        left=residual_y[keep][0],
        right=residual_y[keep][-1],
    )
    if registration_w == "inf":
        correction_y = np.zeros_like(full_residual)
    else:
        width = int(registration_w)
        if width < 1 or width > len(full_residual):
            raise ValueError(
                f"registration W={width} outside [1,{len(full_residual)}]"
            )
        correction_y = _box_smooth(full_residual, width)
    return {
        "registration_w": registration_w,
        "correction_y_sensor_px": correction_y,
        "xr_sensor_px": xr,
        "line": line,
        "n_crossings": int(len(x_local)),
        "n_crossings_kept": int(keep.sum()),
        "raw_crossing_residual_rms_sensor_px": float(
            np.sqrt(np.mean(residual_y[keep] ** 2))
        ),
    }


def _registered_sfr(
    noisy: np.ndarray,
    settings: dict,
    crop: tuple[int, int, int, int] | None,
    registration_w: int | str,
):
    if settings["axis"] != "horizontal":
        raise ValueError("smoothed-locus registration is horizontal-only")
    s, xr, yr = _roi_parts(noisy, crop)
    line = S.line_from_crossings(
        s, xr, yr, bright_first=True, axis=settings["axis"]
    )
    registration = _registration_from_crossings(
        s, xr, yr, line, registration_w
    )
    xx, yy = np.meshgrid(xr, yr)
    yy_registered = yy - registration["correction_y_sensor_px"][None, :]
    sfr = L.sfr_from_sites2(
        s.ravel().astype(float),
        xx.ravel(),
        yy_registered.ravel(),
        line,
        settings["bin_um"],
        settings["half_um"],
        settings["taper"],
        detrend_iters=2,
        core_um=settings["core_um"],
        deramp=settings["deramp"],
    )
    return sfr, line, registration


def run_noisy(
    noisy: np.ndarray,
    settings: dict,
    locator: str = "crossing",
    crop: tuple[int, int, int, int] | None = None,
    registration_w: int | str = "inf",
) -> dict:
    if locator != "crossing":
        sub, xs, ys = L.green_sites(noisy, "G1")
        if crop is None:
            row0, col0, nrow, ncol = 0, 0, sub.shape[0], sub.shape[1]
        else:
            row0, col0, nrow, ncol = crop
        result = S.run_roi(
            sub,
            xs,
            ys,
            row0,
            col0,
            nrow,
            ncol,
            bin_um=settings["bin_um"],
            half_um=settings["half_um"],
            taper=settings["taper"],
            axis=settings["axis"],
            deramp=settings["deramp"],
            core_um=settings["core_um"],
            f_lo=settings["f_lo"],
            f_hi=settings["f_hi"],
            locator=locator,
            bright_first=True,
        )
        result["_registration"] = None
        return result

    sfr, line, registration = _registered_sfr(
        noisy, settings, crop, registration_w
    )
    fit = L.fit_fc(
        sfr["freq_cymm"],
        sfr["mtf"],
        settings["f_lo"],
        settings["f_hi"],
    )
    reads = {}
    for frequency in S.F_READ:
        index = int(np.argmin(np.abs(sfr["freq_cymm"] - frequency)))
        reads[f"{frequency:.1f}"] = float(sfr["mtf"][index])
    return {
        "angle_deg": line["angle_deg"],
        "resid_sd_px": line["resid_sd_px"],
        "contrast": line["contrast"],
        "lo_dn": line["lo_dn"],
        "hi_dn": line["hi_dn"],
        "slope_l": sfr["slope_l"],
        "slope_r": sfr["slope_r"],
        "min_bin_count": int(np.min(sfr["count"])),
        "reads": reads,
        "esf_contrast": sfr["contrast"],
        "_registration": registration,
        **fit,
    }


def sfr_for_rise(
    noisy: np.ndarray,
    settings: dict,
    crop: tuple[int, int, int, int] | None = None,
    registration_w: int | str = "inf",
) -> dict:
    sfr, _, _ = _registered_sfr(
        noisy, settings, crop, registration_w
    )
    return sfr


def rise_1090(centres_um: np.ndarray, esf: np.ndarray) -> float:
    e = np.asarray(esf, float)
    c = np.asarray(centres_um, float)
    k = max(3, len(e) // 40)
    lo = float(np.median(e[:k]))
    hi = float(np.median(e[-k:]))
    if hi < lo:
        e, lo, hi = -e, -lo, -hi
    span = hi - lo
    if span <= 0:
        return float("nan")
    monotone = np.maximum.accumulate(e)
    x10 = np.interp(lo + 0.1 * span, monotone, c)
    x90 = np.interp(lo + 0.9 * span, monotone, c)
    return float(x90 - x10)


def clean_plant(fc_cymm: float, angle_deg: float, sigma_um: float = 0.0):
    return L.synth_edge_frame2(
        FRAME_H,
        FRAME_W,
        fc_cymm,
        angle_deg,
        CLEAN_BRIGHT_DN,
        CLEAN_DARK_DN,
        sigma_um=sigma_um,
        sub=PLANT_SUB,
        axis="horizontal",
    )


def subject_base(fc_cymm: float, angle_deg: float):
    return L.synth_edge_frame2(
        FRAME_H,
        FRAME_W,
        fc_cymm,
        angle_deg,
        SUBJECT_BRIGHT_DN,
        SUBJECT_DARK_DN,
        sub=PLANT_SUB,
        axis="horizontal",
    )


def ragged_offsets(ncols: int, seed: int) -> np.ndarray:
    """Long-wave, non-polynomial wander sampled on the green sublattice."""
    rng = np.random.default_rng(seed)
    ngreen = (ncols + 1) // 2
    xg = np.arange(ngreen, dtype=float)
    green = np.zeros(ngreen, dtype=float)
    # Periods span 37.5-225 green columns on the 900-column plant. This is a
    # broad long-wave band rather than a polynomial bow.
    for k in range(4, 25):
        amp = k ** -0.75
        phase_c = rng.normal()
        phase_s = rng.normal()
        green += amp * (
            phase_c * np.cos(2.0 * np.pi * k * xg / ngreen)
            + phase_s * np.sin(2.0 * np.pi * k * xg / ngreen)
        )
    green -= np.polyval(np.polyfit(xg, green, 1), xg)
    green *= RAGGED_RMS_GREEN_PX / np.sqrt(np.mean(green * green))
    sensor_x_in_green_units = (np.arange(ncols, dtype=float) - 1.0) / 2.0
    return 2.0 * np.interp(
        sensor_x_in_green_units,
        xg,
        green,
        left=green[0],
        right=green[-1],
    )


def wander_diagnostics(offsets_sensor_px: np.ndarray) -> dict:
    green = offsets_sensor_px[1::2] / 2.0
    x = np.arange(len(green), dtype=float)
    line_resid = green - np.polyval(np.polyfit(x, green, 1), x)
    cubic_resid = green - np.polyval(np.polyfit(x, green, 3), x)
    rms_line = float(np.sqrt(np.mean(line_resid * line_resid)))
    rms_cubic = float(np.sqrt(np.mean(cubic_resid * cubic_resid)))
    power = np.abs(np.fft.rfft(line_resid)) ** 2
    freq_index = np.arange(len(power))
    max_long_k = int(np.floor(len(green) / 32.0))
    long_power = float(
        power[(freq_index >= 1) & (freq_index <= max_long_k)].sum()
    )
    total_power = float(power[1:].sum())
    dominant_k = int(np.argmax(power[1:]) + 1)
    return {
        "line_rms_green_px": rms_line,
        "cubic_residual_rms_green_px": rms_cubic,
        "cubic_over_line_rms": rms_cubic / rms_line,
        "power_fraction_wavelength_ge_32_green_columns": (
            long_power / total_power
        ),
        "dominant_wavelength_green_columns": len(green) / dominant_k,
    }


def shifted_silhouette(
    base: np.ndarray, angle_deg: float, offsets_sensor_px: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    a = np.radians(angle_deg)
    nx = -np.sin(a)
    ny = np.cos(a)
    x0 = 0.5 * base.shape[1]
    y0 = 0.5 * base.shape[0]
    y = np.arange(base.shape[0], dtype=float)
    shifted = np.empty_like(base)
    for col, off in enumerate(offsets_sensor_px):
        shifted[:, col] = np.interp(
            y - off / ny,
            y,
            base[:, col],
            left=base[0, col],
            right=base[-1, col],
        )
    xx = np.arange(base.shape[1], dtype=float)[None, :]
    yy = np.arange(base.shape[0], dtype=float)[:, None]
    d_sensor_px = (
        (xx - x0) * nx + (yy - y0) * ny - offsets_sensor_px[None, :]
    )
    return shifted, d_sensor_px * L.PITCH_UM


def residual_smear_um(
    result: dict,
    angle_deg: float,
    offsets_sensor_px: np.ndarray,
) -> float:
    registration = result["_registration"]
    xr = registration["xr_sensor_px"]
    line = registration["line"]
    a = np.radians(angle_deg)
    nx = -np.sin(a)
    ny = np.cos(a)
    true_y = (
        0.5 * FRAME_H
        - (xr - 0.5 * FRAME_W) * nx / ny
        + offsets_sensor_px[np.rint(xr).astype(int)] / ny
    )
    remaining_normal_px = (
        true_y
        - registration["correction_y_sensor_px"]
        - _line_y(line, xr)
    ) * line["ny"]
    remaining_normal_px -= np.mean(remaining_normal_px)
    return float(
        np.sqrt(np.mean(remaining_normal_px * remaining_normal_px))
        * L.PITCH_UM
    )


def unshifted_geometry(base: np.ndarray, angle_deg: float):
    a = np.radians(angle_deg)
    nx = -np.sin(a)
    ny = np.cos(a)
    xx = np.arange(base.shape[1], dtype=float)[None, :]
    yy = np.arange(base.shape[0], dtype=float)[:, None]
    d_sensor_px = (
        (xx - 0.5 * base.shape[1]) * nx
        + (yy - 0.5 * base.shape[0]) * ny
    )
    return base.copy(), d_sensor_px * L.PITCH_UM


def compose_subject(
    silhouette: np.ndarray,
    d_um: np.ndarray,
    bevel: bool,
    glare: bool,
) -> tuple[np.ndarray, dict]:
    out = silhouette.copy()
    diagnostics = {}
    if bevel:
        ridge_unit = np.exp(
            -0.5 * ((d_um - RIDGE_OFFSET_UM) / RIDGE_SIGMA_UM) ** 2
        )
        peak_index = np.unravel_index(np.argmax(ridge_unit), ridge_unit.shape)
        ridge_amp = (
            RIDGE_PEAK_DN - silhouette[peak_index]
        ) / ridge_unit[peak_index]
        out += ridge_amp * ridge_unit
        diagnostics["ridge_amplitude_dn"] = float(ridge_amp)
        diagnostics["ridge_peak_dn"] = float(np.max(out))
    if glare:
        dark_fraction = np.clip(
            (SUBJECT_BRIGHT_DN - silhouette)
            / (SUBJECT_BRIGHT_DN - SUBJECT_DARK_DN),
            0.0,
            1.0,
        )
        decay_distance = np.maximum(d_um - GLARE_PLATEAU_UM, 0.0)
        glare_field = (
            GLARE_EXCESS_DN
            * dark_fraction
            * np.exp(-decay_distance / GLARE_TAU_UM)
        )
        out += glare_field
    if bevel or glare:
        diagnostics.update(level_diagnostics(out, d_um))
    return out, diagnostics


def level_diagnostics(img: np.ndarray, d_um: np.ndarray) -> dict:
    def band(lo: float, hi: float):
        m = (d_um >= lo) & (d_um < hi)
        return float(np.median(img[m])) if m.any() else float("nan")

    return {
        "blade_face_dn": band(-500.0, -250.0),
        "silhouette_centre_dn": band(-1.0, 1.0),
        "dark_near_8_green_px_dn": band(
            GLARE_PLATEAU_UM - 8.0, GLARE_PLATEAU_UM + 8.0
        ),
        "dark_far_80_green_px_dn": band(
            GLARE_FAR_UM - 16.0, GLARE_FAR_UM + 16.0
        ),
        "frame_min_dn": float(np.min(img)),
        "frame_max_dn": float(np.max(img)),
    }


def subject_variants(
    fc_cymm: float, angle_deg: float, geometry_seed: int
) -> tuple[dict[str, np.ndarray], dict]:
    base = subject_base(fc_cymm, angle_deg)
    zero_silhouette, zero_d = unshifted_geometry(base, angle_deg)
    offsets = ragged_offsets(base.shape[1], geometry_seed)
    ragged_silhouette, ragged_d = shifted_silhouette(
        base, angle_deg, offsets
    )
    all_img, all_diag = compose_subject(
        ragged_silhouette, ragged_d, bevel=True, glare=True
    )
    bevel_img, bevel_diag = compose_subject(
        zero_silhouette, zero_d, bevel=True, glare=False
    )
    ragged_img, _ = compose_subject(
        ragged_silhouette, ragged_d, bevel=False, glare=False
    )
    glare_img, glare_diag = compose_subject(
        zero_silhouette, zero_d, bevel=False, glare=True
    )
    return (
        {
            "all": all_img,
            "bevel_only": bevel_img,
            "raggedness_only": ragged_img,
            "glare_only": glare_img,
        },
        {
            "geometry_seed": geometry_seed,
            "offset_rms_sensor_px": float(
                np.sqrt(np.mean(offsets * offsets))
            ),
            "offset_rms_green_px": float(
                np.sqrt(np.mean(offsets * offsets)) / 2.0
            ),
            "correlation_model": (
                "Random Fourier coefficients over wavelengths 37.5-225 "
                "green columns, amplitude proportional to k^-0.75, then "
                "linear detrend"
            ),
            "wander_shape": wander_diagnostics(offsets),
            "all_levels": all_diag,
            "bevel_levels": bevel_diag,
            "glare_levels": glare_diag,
        },
    )


def combination_stats(cases: list[dict], bar_pct: float) -> dict:
    good = [
        c
        for c in cases
        if c.get("recovered_fc_cymm") is not None
        and c.get("all_replicates_succeeded", False)
    ]
    errors = [abs(c["error_pct"]) for c in good]
    passed = [c for c in good if abs(c["error_pct"]) <= bar_pct]
    worst = max(good, key=lambda c: abs(c["error_pct"])) if good else None
    return {
        "passed_combinations": len(passed),
        "total_combinations": len(cases),
        "median_abs_error_pct": (
            float(np.median(errors)) if errors else None
        ),
        "max_abs_error_pct": max(errors) if errors else None,
        "worst_case": (
            {
                "fc_cymm": worst["planted_fc_cymm"],
                "angle_deg": worst["angle_deg"],
                "recovered_fc_cymm": worst["recovered_fc_cymm"],
                "error_pct": worst["error_pct"],
            }
            if worst
            else None
        ),
        "all_within_bar": len(passed) == len(cases),
    }


def control_c9():
    geometry_seed = 91000
    offsets = ragged_offsets(FRAME_W, geometry_seed)
    wander = wander_diagnostics(offsets)
    plant_valid = (
        abs(wander["line_rms_green_px"] - RAGGED_RMS_GREEN_PX) <= 0.01
        and wander["cubic_over_line_rms"] >= 0.95
        and wander["power_fraction_wavelength_ge_32_green_columns"] >= 0.80
    )

    curves = []
    level_check = None
    for fi, fc in enumerate((87.0, 105.54, 135.17)):
        base = subject_base(fc, -0.68)
        silhouette, d_um = shifted_silhouette(base, -0.68, offsets)
        img, diagnostics = compose_subject(
            silhouette, d_um, bevel=True, glare=True
        )
        if level_check is None:
            level_check = diagnostics
        noisy_frames = []
        for ri in range(C9_REPLICATES):
            seed = 92000 + 100 * fi + ri
            noisy_frames.append((seed, add_noise(img, seed)))
        points = []
        for registration_w in REGISTRATION_SWEEP:
            replicates = []
            for seed, noisy in noisy_frames:
                try:
                    fit = run_noisy(
                        noisy,
                        BASE_SETTINGS,
                        locator="crossing",
                        registration_w=registration_w,
                    )
                    replicates.append(
                        {
                            "seed": seed,
                            **fit_fields(fit),
                            "error_pct": 100.0
                            * (fit["fc_cymm"] / fc - 1.0),
                            "residual_smear_um": residual_smear_um(
                                fit, -0.68, offsets
                            ),
                            "n_crossings": fit["_registration"][
                                "n_crossings"
                            ],
                            "n_crossings_kept": fit["_registration"][
                                "n_crossings_kept"
                            ],
                        }
                    )
                except L.EdgeFitError as exc:
                    replicates.append({"seed": seed, "refused": str(exc)})
            valid = [r for r in replicates if "fc_cymm" in r]
            recovered = (
                float(np.median([r["fc_cymm"] for r in valid]))
                if len(valid) == C9_REPLICATES
                else None
            )
            smear = (
                float(np.median([r["residual_smear_um"] for r in valid]))
                if len(valid) == C9_REPLICATES
                else None
            )
            points.append(
                {
                    "W_green_columns": registration_w,
                    "recovered_fc_cymm": recovered,
                    "error_pct": (
                        100.0 * (recovered / fc - 1.0)
                        if recovered is not None
                        else None
                    ),
                    "residual_smear_um": smear,
                    "replicates": replicates,
                }
            )
        curves.append({"planted_fc_cymm": fc, "points": points})

    def point_for(curve, registration_w):
        return next(
            p
            for p in curve["points"]
            if p["W_green_columns"] == registration_w
        )

    truth_ok = {}
    for registration_w in REGISTRATION_SWEEP:
        points = [point_for(c, registration_w) for c in curves]
        truth_ok[registration_w] = all(
            p["error_pct"] is not None and abs(p["error_pct"]) <= 3.0
            for p in points
        )

    finite_w = [w for w in REGISTRATION_SWEEP if w != "inf"]
    plateau_blocks = []
    current = []
    for index, registration_w in enumerate(finite_w):
        if registration_w == 1 or not truth_ok[registration_w]:
            if len(current) >= 2:
                plateau_blocks.append(current)
            current = []
            continue
        if not current:
            current = [registration_w]
            continue
        previous = finite_w[index - 1]
        stable = all(
            abs(
                point_for(curve, registration_w)["recovered_fc_cymm"]
                - point_for(curve, previous)["recovered_fc_cymm"]
            )
            / curve["planted_fc_cymm"]
            <= 0.03
            for curve in curves
        )
        if stable:
            current.append(registration_w)
        else:
            if len(current) >= 2:
                plateau_blocks.append(current)
            current = [registration_w]
    if len(current) >= 2:
        plateau_blocks.append(current)

    recommended_w = None
    selected_block = None
    if plateau_blocks:
        selected_block = min(
            plateau_blocks,
            key=lambda block: (
                -len(block),
                max(
                    abs(
                        point_for(curve, block[-1])["recovered_fc_cymm"]
                        - point_for(curve, block[0])["recovered_fc_cymm"]
                    )
                    / curve["planted_fc_cymm"]
                    for curve in curves
                ),
            ),
        )
        recommended_w = selected_block[len(selected_block) // 2]

    monotonic = {}
    descending = ["inf", 256, 128, 64, 32, 16, 8, 4, 2, 1]
    for curve in curves:
        values = [
            point_for(curve, registration_w)["recovered_fc_cymm"]
            for registration_w in descending
        ]
        exact = all(
            values[i + 1] >= values[i] for i in range(len(values) - 1)
        )
        within_one_pct = all(
            values[i + 1] >= values[i] - 0.01 * curve["planted_fc_cymm"]
            for i in range(len(values) - 1)
        )
        monotonic[f"{curve['planted_fc_cymm']:.2f}"] = {
            "as_W_falls_exact": exact,
            "as_W_falls_with_1pct_tolerance": within_one_pct,
        }
    rule20_triggered = (
        recommended_w is None
        and all(v["as_W_falls_exact"] for v in monotonic.values())
    )
    curve_shape = []
    for curve in curves:
        finite_points = [
            point
            for point in curve["points"]
            if point["error_pct"] is not None
        ]
        best = min(finite_points, key=lambda point: abs(point["error_pct"]))
        boundary_hits = sum(
            replicate.get("fc_cymm", 0.0) >= 399.9
            for point in finite_points
            for replicate in point["replicates"]
        )
        curve_shape.append(
            {
                "planted_fc_cymm": curve["planted_fc_cymm"],
                "closest_sampled_W": best["W_green_columns"],
                "closest_recovered_fc_cymm": best["recovered_fc_cymm"],
                "closest_error_pct": best["error_pct"],
                "fit_fc_upper_boundary_hits": boundary_hits,
                **monotonic[f"{curve['planted_fc_cymm']:.2f}"],
            }
        )

    effective_w = recommended_w if recommended_w is not None else "inf"
    effective_smear = {
        f"{curve['planted_fc_cymm']:.2f}": point_for(
            curve, effective_w
        )["residual_smear_um"]
        for curve in curves
    }
    passed = plant_valid and recommended_w is not None
    measurements = {
        "settings": BASE_SETTINGS,
        "angle_deg": -0.68,
        "geometry_seed": geometry_seed,
        "wander_validation": wander,
        "wander_valid": plant_valid,
        "contamination_levels": level_check,
        "smoother": (
            "Centred W-column box average of the one-pass crossing residual "
            "about line_from_crossings; missing crossings are interpolated. "
            "Coordinates are shifted before m88lib.sfr_from_sites2."
        ),
        "aggregation": (
            "Median of 5 independently noisy frames; each planted cutoff's "
            "identical five noisy arrays are reused at every W."
        ),
        "selection_rule": (
            "Recommend only an intermediate contiguous block of at least two "
            "sampled W values where all three cutoffs are within 3% and each "
            "adjacent recovery changes by <=3%. Choose the sampled middle of "
            "the longest block. Truth is used only for the registered 3% bar; "
            "no isolated best-looking W is selected."
        ),
        "curves": curves,
        "truth_bar_by_W": [
            {"W_green_columns": w, "all_three_within_3pct": truth_ok[w]}
            for w in REGISTRATION_SWEEP
        ],
        "all_three_within_3pct_W": [
            w for w in REGISTRATION_SWEEP if truth_ok[w]
        ],
        "curve_shape": curve_shape,
        "plateau_blocks": plateau_blocks,
        "selected_plateau": selected_block,
        "recommended_W_green_columns": recommended_w,
        "effective_W_for_reruns": effective_w,
        "effective_residual_smear_um_by_fc": effective_smear,
        "rule20_monotonicity": monotonic,
        "rule20_registered_failure_mode_triggered": rule20_triggered,
        "fallback": (
            None
            if recommended_w is not None
            else (
                "No safe plateau exists. Use W=inf (straight-line fallback) "
                "for the required synthetic reruns and freeze no finite W."
            )
        ),
    }
    if recommended_w is not None:
        headline = (
            f"W={recommended_w} green columns; all three within 3%; "
            f"residual smear {effective_smear}"
        )
    else:
        headline = (
            "no common intermediate plateau; no finite W commissioned; "
            "synthetic reruns use straight-line fallback"
        )
    return record("C9", measurements, "PASS" if passed else "FAIL", headline)


def control_c0():
    existing = M88_CONTROL.read_bytes()
    existing_hash = sha256_bytes(existing)
    print(f"C0 existing M88 SHA-256: {existing_hash}")
    scratch = OUT / ".commission-c0-scratch"
    if scratch.exists():
        shutil.rmtree(scratch)
    captured = io.StringIO()
    try:
        spec = importlib.util.spec_from_file_location(
            "m88_s03_commission", M88_SCRIPT
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("could not load M88 s03_controls.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.OUT = scratch
        with contextlib.redirect_stdout(captured):
            module.main()
        generated_path = scratch / "s03_controls.json"
        generated = generated_path.read_bytes()
        generated_hash = sha256_bytes(generated)
        same = generated == existing
        passed = (
            existing_hash == EXPECTED_M88_SHA256
            and generated_hash == EXPECTED_M88_SHA256
            and same
        )
        measurements = {
            "existing_path": str(M88_CONTROL),
            "producer": str(M88_SCRIPT),
            "existing_bytes": len(existing),
            "generated_bytes": len(generated),
            "existing_sha256": existing_hash,
            "generated_sha256": generated_hash,
            "expected_sha256": EXPECTED_M88_SHA256,
            "byte_identical": same,
            "producer_rng_seeds": {
                "C1": [11, 12, 13, 14, 15],
                "C2": [21],
                "C3": [31],
                "C4": [41],
                "C5": [51, 52],
                "C6": [61],
            },
            "producer_stdout_last_line": captured.getvalue().splitlines()[-1],
            "scope_note": (
                "Required M88 library regression only; it does not certify "
                "the M128 locator."
            ),
        }
        headline = (
            f"{existing_hash}; regenerated {'byte-identical' if same else 'DIFFERENT'}"
        )
        return record("C0", measurements, "PASS" if passed else "FAIL", headline)
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)


def control_c1(registration_w: int | str):
    cases = []
    for fi, fc in enumerate(FC_VALUES):
        for ai, angle in enumerate(ANGLES_DEG):
            img = clean_plant(fc, angle)
            replicates = []
            for ri in range(REPLICATES):
                seed = 11000 + 100 * fi + 10 * ai + ri
                noisy = add_noise(img, seed)
                try:
                    result = run_noisy(
                        noisy,
                        BASE_SETTINGS,
                        locator="crossing",
                        registration_w=registration_w,
                    )
                    item = fit_fields(result)
                    item["seed"] = seed
                    item["error_pct"] = 100.0 * (
                        result["fc_cymm"] / fc - 1.0
                    )
                except L.EdgeFitError as exc:
                    item = {"seed": seed, "refused": str(exc)}
                replicates.append(item)
            recovered = [
                r["fc_cymm"] for r in replicates if "fc_cymm" in r
            ]
            median_fc = (
                float(np.median(recovered))
                if len(recovered) == REPLICATES
                else None
            )
            cases.append(
                {
                    "planted_fc_cymm": fc,
                    "angle_deg": angle,
                    "noise_seeds": [r["seed"] for r in replicates],
                    "replicates": replicates,
                    "all_replicates_succeeded": len(recovered) == REPLICATES,
                    "recovered_fc_cymm": median_fc,
                    "error_pct": (
                        100.0 * (median_fc / fc - 1.0)
                        if median_fc is not None
                        else None
                    ),
                }
            )
    stats = combination_stats(cases, 3.0)
    chosen = next(
        c
        for c in cases
        if c["planted_fc_cymm"] == 87.0 and c["angle_deg"] == -0.68
    )
    wrong_truth = 1.25 * chosen["planted_fc_cymm"]
    wrong_error = 100.0 * (
        chosen["recovered_fc_cymm"] / wrong_truth - 1.0
    )
    wrong = {
        "case": "87 cy/mm, -0.68 deg",
        "recovered_fc_cymm": chosen["recovered_fc_cymm"],
        "deliberately_wrong_truth_cymm": wrong_truth,
        "error_pct": wrong_error,
        "bar_pct": 3.0,
        "rejected": abs(wrong_error) > 3.0,
    }
    passed = stats["all_within_bar"] and wrong["rejected"]
    measurements = {
        "settings": BASE_SETTINGS,
        "registration_W_green_columns": registration_w,
        "frame_shape_sensor_px": [FRAME_H, FRAME_W],
        "signal_levels_dn": {
            "bright": CLEAN_BRIGHT_DN,
            "dark": CLEAN_DARK_DN,
        },
        "noise_model": {
            "gain_e_per_dn": GAIN_E_PER_DN,
            "read_noise_dn": READ_NOISE_DN,
            "sd_at_1500_dn": math.sqrt(
                1500.0 / GAIN_E_PER_DN + READ_NOISE_DN**2
            ),
        },
        "aggregation": "median of 3 independent noisy frames per combination",
        "summary": stats,
        "cases": cases,
        "rule20_failure_demonstration": wrong,
    }
    headline = (
        f"{stats['passed_combinations']}/{stats['total_combinations']} within 3%; "
        f"worst |error|={stats['max_abs_error_pct']:.3f}%"
    )
    return record("C1", measurements, "PASS" if passed else "FAIL", headline)


def control_c2(registration_w: int | str):
    by_variant = {
        "all": [],
        "bevel_only": [],
        "raggedness_only": [],
        "glare_only": [],
    }
    representative = None
    for fi, fc in enumerate(FC_VALUES):
        for ai, angle in enumerate(ANGLES_DEG):
            geometry_seed = 21000 + 100 * fi + ai
            variants, diagnostics = subject_variants(
                fc, angle, geometry_seed
            )
            for variant_name, img in variants.items():
                replicates = []
                for ri in range(REPLICATES):
                    seed = 22000 + 100 * fi + 10 * ai + ri
                    noisy = add_noise(img, seed)
                    try:
                        result = run_noisy(
                            noisy,
                            BASE_SETTINGS,
                            locator="crossing",
                            registration_w=registration_w,
                        )
                        item = fit_fields(result)
                        item["seed"] = seed
                        item["error_pct"] = 100.0 * (
                            result["fc_cymm"] / fc - 1.0
                        )
                        item["resid_rms_green_px"] = (
                            result["resid_sd_px"] / 2.0
                        )
                    except L.EdgeFitError as exc:
                        item = {"seed": seed, "refused": str(exc)}
                    replicates.append(item)
                    if (
                        representative is None
                        and variant_name == "all"
                        and fc == 105.54
                        and angle == -0.68
                        and ri == 0
                    ):
                        representative = {
                            "planted_fc_cymm": fc,
                            "angle_deg": angle,
                            "geometry_seed": geometry_seed,
                            "noise_seed": seed,
                            "noisy_array_sha256": array_sha256(noisy),
                            "plant_diagnostics": diagnostics,
                        }
                recovered = [
                    r["fc_cymm"] for r in replicates if "fc_cymm" in r
                ]
                median_fc = (
                    float(np.median(recovered))
                    if len(recovered) == REPLICATES
                    else None
                )
                by_variant[variant_name].append(
                    {
                        "planted_fc_cymm": fc,
                        "angle_deg": angle,
                        "geometry_seed": geometry_seed,
                        "noise_seeds": [r["seed"] for r in replicates],
                        "replicates": replicates,
                        "all_replicates_succeeded": (
                            len(recovered) == REPLICATES
                        ),
                        "recovered_fc_cymm": median_fc,
                        "error_pct": (
                            100.0 * (median_fc / fc - 1.0)
                            if median_fc is not None
                            else None
                        ),
                    }
                )
    summaries = {
        name: combination_stats(cases, 5.0)
        for name, cases in by_variant.items()
    }
    chosen = next(
        c
        for c in by_variant["bevel_only"]
        if c["planted_fc_cymm"] == 105.54 and c["angle_deg"] == -0.68
    )
    wrong_truth = 200.0
    wrong_error = 100.0 * (
        chosen["recovered_fc_cymm"] / wrong_truth - 1.0
    )
    wrong = {
        "case": "bevel-only 105.54 cy/mm, -0.68 deg",
        "recovered_fc_cymm": chosen["recovered_fc_cymm"],
        "deliberately_wrong_truth_cymm": wrong_truth,
        "error_pct": wrong_error,
        "bar_pct": 5.0,
        "rejected": abs(wrong_error) > 5.0,
    }
    passed = all(s["all_within_bar"] for s in summaries.values())
    passed = passed and wrong["rejected"]
    measurements = {
        "settings": BASE_SETTINGS,
        "registration_W_green_columns": registration_w,
        "contamination_model": {
            "blade_face_dn": SUBJECT_BRIGHT_DN,
            "far_dark_dn": SUBJECT_DARK_DN,
            "ridge_target_peak_dn": RIDGE_PEAK_DN,
            "ridge_offset_um": RIDGE_OFFSET_UM,
            "ridge_offset_green_px": abs(RIDGE_OFFSET_UM)
            / (2.0 * L.PITCH_UM),
            "ridge_sigma_um": RIDGE_SIGMA_UM,
            "ragged_target_rms_green_px": RAGGED_RMS_GREEN_PX,
            "glare_near_target_dn": GLARE_NEAR_DN,
            "glare_plateau_um": GLARE_PLATEAU_UM,
            "glare_far_um": GLARE_FAR_UM,
            "glare_tau_um": GLARE_TAU_UM,
        },
        "aggregation": "median of 3 independent noisy frames per combination",
        "summaries": summaries,
        "cases_by_variant": by_variant,
        "representative_full_case": representative,
        "rule20_failure_demonstration": wrong,
    }
    all_stats = summaries["all"]
    headline = (
        f"full contamination: {all_stats['passed_combinations']}/"
        f"{all_stats['total_combinations']} within 5%; worst |error|="
        f"{all_stats['max_abs_error_pct']:.3f}%"
    )
    return record("C2", measurements, "PASS" if passed else "FAIL", headline)


def build_representative_c2():
    fi = FC_VALUES.index(105.54)
    ai = ANGLES_DEG.index(-0.68)
    geometry_seed = 21000 + 100 * fi + ai
    noise_seed = 22000 + 100 * fi + 10 * ai
    variants, diagnostics = subject_variants(
        105.54, -0.68, geometry_seed
    )
    noisy = add_noise(variants["all"], noise_seed)
    return noisy, {
        "planted_fc_cymm": 105.54,
        "angle_deg": -0.68,
        "geometry_seed": geometry_seed,
        "noise_seed": noise_seed,
        "noisy_array_sha256": array_sha256(noisy),
        "plant_diagnostics": diagnostics,
    }


def control_c3(registration_w: int | str):
    fc = 105.54
    angle = -3.0
    fi = FC_VALUES.index(fc)
    ai = ANGLES_DEG.index(angle)
    geometry_seed = 31000
    variants, diagnostics = subject_variants(fc, angle, geometry_seed)
    noise_seed = 31001
    noisy = add_noise(variants["all"], noise_seed)
    sub, _, _ = L.green_sites(noisy, "G1")
    half = sub.shape[1] // 2
    crops = (
        (0, 0, sub.shape[0], half),
        (0, half, sub.shape[0], sub.shape[1] - half),
    )
    results = []
    for crop in crops:
        try:
            r = run_noisy(
                noisy,
                BASE_SETTINGS,
                locator="crossing",
                crop=crop,
                registration_w=registration_w,
            )
            results.append({"crop": list(crop), **fit_fields(r)})
        except L.EdgeFitError as exc:
            results.append({"crop": list(crop), "refused": str(exc)})
    if len(results) == 2 and all("fc_cymm" in r for r in results):
        f0, f1 = results[0]["fc_cymm"], results[1]["fc_cymm"]
        disagreement = 100.0 * abs(f0 - f1) / (0.5 * (f0 + f1))
        passed = disagreement <= 5.0
    else:
        disagreement = None
        passed = False
    measurements = {
        "planted_fc_cymm": fc,
        "registration_W_green_columns": registration_w,
        "angle_deg": angle,
        "geometry_seed": geometry_seed,
        "noise_seed": noise_seed,
        "noisy_array_sha256": array_sha256(noisy),
        "crops": results,
        "disagreement_pct": disagreement,
        "plant_diagnostics": diagnostics,
        "unused_seed_indices": [fi, ai],
    }
    headline = (
        f"crop disagreement={disagreement:.3f}%"
        if disagreement is not None
        else "one or both crops refused"
    )
    return record("C3", measurements, "PASS" if passed else "FAIL", headline)


def control_c4():
    seed = 41000
    flat = np.full((FRAME_H, FRAME_W), 1500.0, dtype=float)
    noisy = add_noise(flat, seed)
    try:
        result = run_noisy(noisy, BASE_SETTINGS, locator="crossing")
        objective_reasons = []
        if result["contrast"] < FLAT_MIN_CONTRAST_DN:
            objective_reasons.append(
                f"contrast {result['contrast']:.3f} < {FLAT_MIN_CONTRAST_DN}"
            )
        if not result["success"]:
            objective_reasons.append("fit success is false")
        if result["rms_resid"] > FLAT_MAX_FIT_RMS:
            objective_reasons.append(
                f"fit RMS {result['rms_resid']:.6f} > {FLAT_MAX_FIT_RMS}"
            )
        passed = bool(objective_reasons)
        measurements = {
            "seed": seed,
            "outcome": "returned_then_objectively_rejected"
            if passed
            else "returned_and_not_rejected",
            "objective_rejection_reasons": objective_reasons,
            "fit": fit_fields(result),
        }
        headline = measurements["outcome"]
    except L.EdgeFitError as exc:
        passed = True
        measurements = {
            "seed": seed,
            "outcome": "refused_with_EdgeFitError",
            "exception": str(exc),
        }
        headline = f"refused with EdgeFitError: {exc}"
    return record("C4", measurements, "PASS" if passed else "FAIL", headline)


def control_c5(registration_w: int | str):
    ladders = []
    for bi, planted_b in enumerate(B_VALUES):
        aperture_rows = []
        for ai, aperture in enumerate(APERTURES):
            planted_fc = 1.0 / (LAMBDA_MM * planted_b * aperture)
            img = clean_plant(planted_fc, -3.0, sigma_um=2.0)
            reps = []
            for ri in range(REPLICATES):
                seed = 51000 + 100 * bi + 10 * ai + ri
                noisy = add_noise(img, seed)
                try:
                    fit = run_noisy(
                        noisy,
                        BASE_SETTINGS,
                        locator="crossing",
                        registration_w=registration_w,
                    )
                    sfr = sfr_for_rise(
                        noisy,
                        BASE_SETTINGS,
                        registration_w=registration_w,
                    )
                    start_diagnostic = []
                    for fc_init in (30.0, 45.0, 60.0, 90.0, 135.0, 200.0):
                        alternative = L.fit_fc(
                            sfr["freq_cymm"],
                            sfr["mtf"],
                            BASE_SETTINGS["f_lo"],
                            BASE_SETTINGS["f_hi"],
                            fc_init=fc_init,
                        )
                        start_diagnostic.append(
                            {
                                "fc_init": fc_init,
                                "fc_cymm": alternative["fc_cymm"],
                                "cost": alternative["cost"],
                                "success": alternative["success"],
                            }
                        )
                    best_start = min(
                        start_diagnostic, key=lambda item: item["cost"]
                    )
                    reps.append(
                        {
                            "seed": seed,
                            **fit_fields(fit),
                            "rise_um": rise_1090(
                                sfr["centres_um"], sfr["esf"]
                            ),
                            "fit_initialization_diagnostic": start_diagnostic,
                            "lowest_cost_multistart_fc_cymm": best_start[
                                "fc_cymm"
                            ],
                            "lowest_cost_multistart_cost": best_start["cost"],
                        }
                    )
                except L.EdgeFitError as exc:
                    reps.append({"seed": seed, "refused": str(exc)})
            valid = [r for r in reps if "fc_cymm" in r]
            aperture_rows.append(
                {
                    "aperture": aperture,
                    "planted_fc_cymm": planted_fc,
                    "replicates": reps,
                    "recovered_fc_cymm": (
                        float(np.median([r["fc_cymm"] for r in valid]))
                        if len(valid) == REPLICATES
                        else None
                    ),
                    "rise_um": (
                        float(np.median([r["rise_um"] for r in valid]))
                        if len(valid) == REPLICATES
                        else None
                    ),
                    "diagnostic_multistart_fc_cymm": (
                        float(
                            np.median(
                                [
                                    r["lowest_cost_multistart_fc_cymm"]
                                    for r in valid
                                ]
                            )
                        )
                        if len(valid) == REPLICATES
                        else None
                    ),
                }
            )
        complete = all(
            row["recovered_fc_cymm"] is not None for row in aperture_rows
        )
        if complete:
            b_per_aperture = [
                1.0
                / (
                    LAMBDA_MM
                    * row["aperture"]
                    * row["recovered_fc_cymm"]
                )
                for row in aperture_rows
            ]
            primary_b = float(np.mean(b_per_aperture))
            primary_error = 100.0 * (primary_b / planted_b - 1.0)
            nn = np.asarray(APERTURES) ** 2
            rr = np.asarray([row["rise_um"] for row in aperture_rows]) ** 2
            coef, *_ = np.linalg.lstsq(
                np.column_stack([nn, np.ones(3)]), rr, rcond=None
            )
            slope, intercept = float(coef[0]), float(coef[1])
            secondary_b = (
                math.sqrt(slope) / (RISE_A_UM_CYMM * LAMBDA_MM)
                if slope > 0
                else None
            )
            secondary_error = (
                100.0 * (secondary_b / planted_b - 1.0)
                if secondary_b is not None
                else None
            )
            diagnostic_b_per_aperture = [
                1.0
                / (
                    LAMBDA_MM
                    * row["aperture"]
                    * row["diagnostic_multistart_fc_cymm"]
                )
                for row in aperture_rows
            ]
            diagnostic_multistart_b = float(
                np.mean(diagnostic_b_per_aperture)
            )
            diagnostic_multistart_error = 100.0 * (
                diagnostic_multistart_b / planted_b - 1.0
            )
        else:
            b_per_aperture = []
            primary_b = primary_error = None
            slope = intercept = secondary_b = secondary_error = None
            diagnostic_b_per_aperture = []
            diagnostic_multistart_b = diagnostic_multistart_error = None
        ladders.append(
            {
                "planted_B": planted_b,
                "shared_sigma_um": 2.0,
                "apertures": aperture_rows,
                "B_per_aperture": b_per_aperture,
                "primary_B": primary_b,
                "primary_error_pct": primary_error,
                "secondary_rise_ladder_B": secondary_b,
                "secondary_error_pct": secondary_error,
                "diagnostic_multistart_B_per_aperture": (
                    diagnostic_b_per_aperture
                ),
                "diagnostic_multistart_B": diagnostic_multistart_b,
                "diagnostic_multistart_error_pct": (
                    diagnostic_multistart_error
                ),
                "rise_fit_slope_um2_per_N2": slope,
                "rise_fit_intercept_um2": intercept,
                "primary_within_5pct": (
                    primary_error is not None
                    and abs(primary_error) <= 5.0
                ),
            }
        )
    first = ladders[0]
    wrong_truth = first["planted_B"] * 1.25
    wrong_error = (
        100.0 * (first["primary_B"] / wrong_truth - 1.0)
        if first["primary_B"] is not None
        else None
    )
    wrong = {
        "case": f"planted B={first['planted_B']}",
        "recovered_B": first["primary_B"],
        "deliberately_wrong_truth_B": wrong_truth,
        "error_pct": wrong_error,
        "bar_pct": 5.0,
        "rejected": wrong_error is not None and abs(wrong_error) > 5.0,
    }
    passed = all(row["primary_within_5pct"] for row in ladders)
    passed = passed and wrong["rejected"]
    measurements = {
        "settings": BASE_SETTINGS,
        "registration_W_green_columns": registration_w,
        "lambda_mm": LAMBDA_MM,
        "rise_calibration_a_um_cymm": RISE_A_UM_CYMM,
        "fit_initialization_diagnostic_note": (
            "Rule-24 choice-point diagnostic only: repeat fit_fc from six "
            "initial cutoffs and report the lowest-cost solution. The "
            "registered acceptance result remains the driver/default "
            "fc_init=90 route."
        ),
        "ladders": ladders,
        "rule20_failure_demonstration": wrong,
    }
    headline = "; ".join(
        f"B {row['planted_B']:.4f}->{row['primary_B']:.4f}"
        if row["primary_B"] is not None
        else f"B {row['planted_B']:.4f}->REFUSED"
        for row in ladders
    )
    return record("C5", measurements, "PASS" if passed else "FAIL", headline)


def control_c6(registration_w: int | str):
    planted = (60.0, 87.0, 105.54, 135.17, 200.0)
    rows = []
    for fi, fc in enumerate(planted):
        img = clean_plant(fc, -3.0)
        reps = []
        for ri in range(REPLICATES):
            seed = 61000 + 10 * fi + ri
            noisy = add_noise(img, seed)
            try:
                fit = run_noisy(
                    noisy,
                    BASE_SETTINGS,
                    locator="crossing",
                    registration_w=registration_w,
                )
                reps.append({"seed": seed, **fit_fields(fit)})
            except L.EdgeFitError as exc:
                reps.append({"seed": seed, "refused": str(exc)})
        valid = [r["fc_cymm"] for r in reps if "fc_cymm" in r]
        recovered = (
            float(np.median(valid)) if len(valid) == REPLICATES else None
        )
        rows.append(
            {
                "planted_fc_cymm": fc,
                "recovered_fc_cymm": recovered,
                "error_pct": (
                    100.0 * (recovered / fc - 1.0)
                    if recovered is not None
                    else None
                ),
                "replicates": reps,
            }
        )
    complete = all(row["recovered_fc_cymm"] is not None for row in rows)
    recovered_values = [row["recovered_fc_cymm"] for row in rows]
    monotone = complete and bool(np.all(np.diff(recovered_values) > 0.0))
    all_within = complete and all(abs(row["error_pct"]) <= 5.0 for row in rows)
    predicted_ratio = planted[-1] / planted[0]
    recovered_ratio = (
        recovered_values[-1] / recovered_values[0] if complete else None
    )
    wrong_truth = 135.17
    wrong_error = (
        100.0 * (recovered_values[-1] / wrong_truth - 1.0)
        if complete
        else None
    )
    wrong = {
        "case": "sharpest 200 cy/mm plant",
        "recovered_fc_cymm": recovered_values[-1] if complete else None,
        "deliberately_wrong_truth_cymm": wrong_truth,
        "error_pct": wrong_error,
        "bar_pct": 5.0,
        "rejected": wrong_error is not None and abs(wrong_error) > 5.0,
    }
    passed = monotone and all_within and wrong["rejected"]
    measurements = {
        "settings": BASE_SETTINGS,
        "registration_W_green_columns": registration_w,
        "angle_deg": -3.0,
        "rows": rows,
        "monotone": monotone,
        "all_within_5pct": all_within,
        "predicted_sharpest_to_softest_ratio": predicted_ratio,
        "recovered_sharpest_to_softest_ratio": recovered_ratio,
        "rule20_failure_demonstration": wrong,
    }
    max_error = (
        max(abs(row["error_pct"]) for row in rows) if complete else None
    )
    headline = (
        f"monotone={monotone}; worst |error|={max_error:.3f}%"
        if max_error is not None
        else "one or more plants refused"
    )
    return record("C6", measurements, "PASS" if passed else "FAIL", headline)


def control_c7(registration_w: int | str):
    noisy, context = build_representative_c2()
    sub, xs, ys = L.green_sites(noisy, "G1")
    crossing_line = S.line_from_crossings(
        sub, xs, ys, bright_first=True, axis="horizontal"
    )
    m88_line = L.fit_edge_line(sub, xs, ys, axis="horizontal")
    x_mid = float(np.median(xs))
    crossing_y = float(_line_y(crossing_line, np.asarray([x_mid]))[0])
    m88_y = float(_line_y(m88_line, np.asarray([x_mid]))[0])
    m88_minus_crossing_um = (
        (m88_y - crossing_y) * crossing_line["ny"] * L.PITCH_UM
    )
    ridge_location_failure = abs(m88_minus_crossing_um) >= 100.0
    results = {}
    for locator in ("crossing", "m88"):
        try:
            fit = run_noisy(
                noisy,
                BASE_SETTINGS,
                locator=locator,
                registration_w=(
                    registration_w if locator == "crossing" else "inf"
                ),
            )
            item = fit_fields(fit)
            item["error_pct"] = 100.0 * (
                fit["fc_cymm"] / context["planted_fc_cymm"] - 1.0
            )
        except L.EdgeFitError as exc:
            item = {"refused": str(exc)}
        results[locator] = item
    crossing_ok = (
        "error_pct" in results["crossing"]
        and abs(results["crossing"]["error_pct"]) <= 5.0
    )
    m88_bad = (
        "refused" in results["m88"]
        or abs(results["m88"]["error_pct"]) > 5.0
    )
    passed = crossing_ok and m88_bad and ridge_location_failure
    if "refused" in results["m88"]:
        comparison = (
            f"M88 refused; locator offset {m88_minus_crossing_um:+.1f} um"
        )
    else:
        comparison = (
            f"M88 selects {m88_minus_crossing_um:+.1f} um from crossing "
            f"(the bevel ridge); crossing fc error "
            f"{results['crossing'].get('error_pct'):.3f}%, M88 fc error "
            f"{results['m88']['error_pct']:.3f}%"
        )
    measurements = {
        "same_C2_case": context,
        "settings": BASE_SETTINGS,
        "crossing_registration_W_green_columns": registration_w,
        "comparison_footing": (
            "Equal registration footing: both arms use one fitted line."
            if registration_w == "inf"
            else (
                "Unequal registration footing: crossing uses the commissioned "
                f"W={registration_w} smoothed locus; M88 has no such stage "
                "and uses one fitted line. This favours crossing and conflates "
                "edge selection with registration performance."
            )
        ),
        "locator_geometry": {
            "comparison_x_sensor_px": x_mid,
            "crossing_y_sensor_px": crossing_y,
            "m88_y_sensor_px": m88_y,
            "m88_minus_crossing_normal_um": m88_minus_crossing_um,
            "registered_ridge_offset_um": RIDGE_OFFSET_UM,
            "m88_selected_ridge_by_location": ridge_location_failure,
            "crossing_line": crossing_line,
            "m88_line": m88_line,
        },
        "locators": results,
        "crossing_within_5pct": crossing_ok,
        "m88_badly_biased_or_refused": m88_bad,
        "synthetic_bevel_reproduces_locator_failure": ridge_location_failure,
        "adequacy_statement": (
            "The synthetic bevel does reproduce the locator failure: M88 "
            "selects the ridge about 150 um from the silhouette."
            if ridge_location_failure
            else (
                "LOUD FINDING: M88 is geometrically fine on this synthetic "
                "contamination, so the bevel plant is inadequate."
            )
        ),
    }
    return record("C7", measurements, "PASS" if passed else "FAIL", comparison)


def control_c8(registration_w: int | str):
    noisy, context = build_representative_c2()
    rows = []
    for half_um in (192.0, 128.0, 96.0, 64.0, 48.0):
        for bin_um in (0.64, 0.32):
            settings = dict(BASE_SETTINGS)
            settings["half_um"] = half_um
            settings["bin_um"] = bin_um
            settings["core_um"] = min(48.0, 0.5 * half_um)
            delta_f = 1000.0 / (2.0 * half_um)
            try:
                fit = run_noisy(
                    noisy,
                    settings,
                    locator="crossing",
                    registration_w=registration_w,
                )
                error = 100.0 * (
                    fit["fc_cymm"] / context["planted_fc_cymm"] - 1.0
                )
                rows.append(
                    {
                        "half_um": half_um,
                        "bin_um": bin_um,
                        "taper": settings["taper"],
                        "core_um": settings["core_um"],
                        "delta_f_cymm": delta_f,
                        "nominal_points_10_to_150": (
                            1.0 + (150.0 - 10.0) / delta_f
                        ),
                        **fit_fields(fit),
                        "error_pct": error,
                        "abs_error_pct": abs(error),
                        "within_5pct": abs(error) <= 5.0,
                    }
                )
            except L.EdgeFitError as exc:
                rows.append(
                    {
                        "half_um": half_um,
                        "bin_um": bin_um,
                        "taper": settings["taper"],
                        "core_um": settings["core_um"],
                        "delta_f_cymm": delta_f,
                        "refused": str(exc),
                        "within_5pct": False,
                    }
                )
    viable = [r for r in rows if r.get("within_5pct", False)]
    recommended = (
        min(viable, key=lambda r: (r["abs_error_pct"], r["rms_resid"]))
        if viable
        else None
    )
    passed = recommended is not None
    finite_rows = [r for r in rows if "abs_error_pct" in r]
    best_any = (
        min(finite_rows, key=lambda r: (r["abs_error_pct"], r["rms_resid"]))
        if finite_rows
        else None
    )
    half_values = [r["half_um"] for r in finite_rows]
    endpoint_note = None
    if best_any and best_any["half_um"] in (min(half_values), max(half_values)):
        endpoint_note = (
            "Best observed half-width is a sweep endpoint; no turnover was "
            "found within the registered half-width range."
        )
    measurements = {
        "same_C2_case": context,
        "registration_W_green_columns": registration_w,
        "selection_rule": (
            "Among settings within 5%, minimise absolute cutoff error, then "
            "fit RMS. If none are within 5%, freeze no setting."
        ),
        "evidence_table": rows,
        "recommended_settings": (
            {
                "half_um": recommended["half_um"],
                "bin_um": recommended["bin_um"],
                "taper": recommended["taper"],
                "core_um": recommended["core_um"],
            }
            if recommended
            else None
        ),
        "best_observed_even_if_failing": best_any,
        "endpoint_note": endpoint_note,
    }
    headline = (
        "recommended "
        f"({recommended['half_um']}, {recommended['bin_um']}, "
        f"{recommended['taper']}, {recommended['core_um']})"
        if recommended
        else "no setting met the 5% truth bar"
    )
    return record("C8", measurements, "PASS" if passed else "FAIL", headline)


def run_control(cid: str, fn):
    print(f"\n=== {cid}: {DESCRIPTIONS[cid]} ===")
    try:
        result = fn()
    except Exception as exc:
        result = errored(cid, exc)
    print(f"{cid} {result['status']}: {result['headline']}")
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    output_path = OUT / "controls.json"
    superseded = None
    if output_path.exists():
        try:
            previous = json.loads(output_path.read_text(encoding="utf-8"))
            previous_ids = {
                item.get("id") for item in previous.get("controls", [])
            }
            if "C9" not in previous_ids:
                superseded = previous
            else:
                superseded = previous.get("superseded_straight_line_run")
        except (OSError, json.JSONDecodeError):
            superseded = None

    by_id = {}
    execution_order = []

    def execute(cid, fn):
        execution_order.append(cid)
        by_id[cid] = run_control(cid, fn)

    # The blank refusal is run first among image controls (rule 9), then C9
    # freezes registration before all controls affected by it are rerun.
    execute("C0", control_c0)
    execute("C4", control_c4)
    execute("C9", control_c9)
    c9_measurements = by_id["C9"].get("measurements", {})
    effective_w = c9_measurements.get("effective_W_for_reruns", "inf")

    execute("C1", lambda: control_c1(effective_w))
    execute("C2", lambda: control_c2(effective_w))
    execute("C3", lambda: control_c3(effective_w))
    execute("C5", lambda: control_c5(effective_w))
    execute("C6", lambda: control_c6(effective_w))
    execute("C7", lambda: control_c7(effective_w))
    execute("C8", lambda: control_c8(effective_w))

    controls = [by_id[f"C{i}"] for i in range(10)]

    counts = {
        "passed": sum(c["status"] == "PASS" for c in controls),
        "failed": sum(c["status"] == "FAIL" for c in controls),
        "skipped": sum(c["status"] == "SKIP" for c in controls),
        "errored": sum(c["status"] == "ERROR" for c in controls),
        "total": len(controls),
    }
    counted = (
        counts["passed"]
        + counts["failed"]
        + counts["skipped"]
        + counts["errored"]
    )
    if counted != counts["total"] or counts["total"] != 10:
        raise RuntimeError(
            f"outcome partition invalid: counted={counted}, total={counts['total']}"
        )

    recommendation = by_id["C8"].get("measurements", {}).get(
        "recommended_settings"
    )
    baseline_comparison = {}
    if superseded:
        old_by_id = {
            item["id"]: item for item in superseded.get("controls", [])
        }
        for cid in ("C1", "C2", "C5", "C6", "C8"):
            old = old_by_id.get(cid)
            new = by_id[cid]
            baseline_comparison[cid] = {
                "before_status": old.get("status") if old else None,
                "before_headline": old.get("headline") if old else None,
                "after_status": new["status"],
                "after_headline": new["headline"],
                "verdict_changed": (
                    old is not None and old.get("status") != new["status"]
                ),
            }

    payload = {
        "experiment": "M128-razor-ladder",
        "battery": "commissioning",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "instrument": {
            "m88lib_path": str(M88_LIB),
            "m88lib_sha256": sha256_file(M88_LIB),
            "m88_pitch_um": L.PITCH_UM,
            "m128_driver_path": str(HERE / "sfr_run.py"),
            "m128_driver_sha256": sha256_file(HERE / "sfr_run.py"),
            "certified_locator": "line_from_crossings",
            "locator_exceptions": (
                "C0 is the explicitly required M88 library regression; C7's "
                "M88 arm is comparison-only. Every M128 acceptance arm uses "
                "line_from_crossings, including finite-W registration."
            ),
        },
        "execution_order": execution_order,
        "reported_order": [f"C{i}" for i in range(10)],
        "execution_order_disclosure": (
            "C4 ran before image-recovery controls to satisfy AGENTS rule 9. "
            "C9 then ran before C1/C2/C5/C6/C8 so its selected W governed "
            "their required reruns. Records are reported in numeric ID order."
        ),
        "noise_model": {
            "gain_e_per_dn": GAIN_E_PER_DN,
            "shot_sd_dn_formula": "sqrt(signal_dn / 2.3)",
            "read_noise_dn": READ_NOISE_DN,
            "total_sd_at_1500_dn": math.sqrt(
                1500.0 / GAIN_E_PER_DN + READ_NOISE_DN**2
            ),
        },
        "specification_disclosures": [
            (
                "The commissioning request reuses C7 and C8 for locator and "
                "settings controls, while PREREGISTRATION section 5 names "
                "later real-data jitter and M104c controls under those IDs. "
                "This battery follows the explicit commissioning definitions "
                "and does not claim to discharge those later real-data gates."
            ),
            (
                "PREREGISTRATION amendment A1 is implemented as C9. Finite-W "
                "registration retains line_from_crossings as the one-pass "
                "robust locator and smooths measured crossing residuals along "
                "the edge before calling the immutable M88 SFR."
            ),
            (
                "No real M128 measurement frame was opened. C0 alone ran the "
                "frozen M88 regression required by the brief."
            ),
        ],
        "controls": controls,
        "summary": counts,
        "recommended_settings": recommendation,
        "C9_effective_W_for_reruns": effective_w,
        "superseded_straight_line_comparison": baseline_comparison,
        "superseded_straight_line_run": superseded,
        "real_measurement_frames_analysed": False,
        "real_data_stop_gate_triggered": (
            by_id["C2"]["status"] != "PASS"
            or by_id["C9"]["status"] != "PASS"
        ),
        "all_commissioning_controls_passed": all(
            item["status"] == "PASS" for item in controls
        ),
        "reproduction_commands": [
            "$env:PYTHONIOENCODING='utf-8'",
            "$env:PYTHONDONTWRITEBYTECODE='1'",
            (
                "Set-Location "
                "'C:\\dev\\blog\\death-of-software\\projects\\strehl\\"
                "experiments\\M128-razor-ladder'"
            ),
            "python -m py_compile src\\commission.py",
            "python -B src\\commission.py",
            (
                "(Get-FileHash -Algorithm SHA256 "
                "'..\\M88-optical-ceiling\\out\\s03_controls.json').Hash"
            ),
        ],
    }

    output_path.write_text(
        json.dumps(json_ready(payload), indent=2, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )

    print("\n=== COMPLETE OUTCOME PARTITION ===")
    print(f"{'ID':<3} {'OUTCOME':<7} MEASURED")
    for item in controls:
        print(f"{item['id']:<3} {item['status']:<7} {item['headline']}")
    print(
        "\nCOUNTS: "
        f"PASSED={counts['passed']} + FAILED={counts['failed']} + "
        f"SKIPPED={counts['skipped']} + ERRORED={counts['errored']} = "
        f"TOTAL={counts['total']}"
    )
    if by_id["C9"]["status"] != "PASS":
        print(
            "C9 CONTRADICTION: no registration setting met the registered "
            "plant bar; no finite W is commissioned."
        )
    if by_id["C2"]["status"] != "PASS":
        print(
            "STOP GATE: C2 failed. The lane method is not commissioned for "
            "this subject contamination. No real data were analysed."
        )
    c7_measurements = by_id["C7"].get("measurements", {})
    if c7_measurements:
        print(f"C7: {by_id['C7']['headline']}")
        print(f"    {c7_measurements.get('comparison_footing')}")
    print(f"C8 recommendation: {recommendation}")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
