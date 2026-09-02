"""Geometry-specific real-data controls for the rho instrument.

These controls are deliberately not used in the natural-scene census.  The
calibration grid checks sensor-frequency coordinates with known periodic
content.  The razor checks the low-frequency spectrum of a physical step edge
without demosaicing.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import rawpy
from scipy.ndimage import gaussian_filter1d
from scipy.special import erf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rho_lib as R  # noqa: E402


ROOT = HERE.parent
OUT = ROOT / "out"
GRID_ROOT = Path(r"D:\personal\macro\requests\30-calibration-grid")
RAZOR_ROOT = Path(
    r"D:\personal\macro\requests\19-razor-edge"
    r"\horizontal-flat\razor-edge-horizontal-flat-sw4-f8-cpl"
)


def load_active(path: Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        return np.array(raw.raw_image_visible, copy=True)


def strongest_peak(
    psd: np.ndarray,
    fx: np.ndarray,
    fy: np.ndarray,
    mask: np.ndarray,
) -> tuple[float, float, float]:
    score = np.where(mask, psd, -np.inf)
    i, j = np.unravel_index(int(np.argmax(score)), score.shape)
    return float(fx[i, j]), float(fy[i, j]), float(psd[i, j])


def synthetic_grid_control() -> dict:
    n = 1024
    f0 = 0.0573
    u, v = np.indices((n, n), dtype=float)
    # q[u,v] is sensor position (x,y)=(u-v,u+v).
    q = np.cos(2 * np.pi * f0 * (u - v))
    q += 0.8 * np.cos(2 * np.pi * f0 * (u + v))
    psd, blocks = R.welch_psd2(q, 256)
    fx, fy = R.gq_frequency_grid(256)
    legal = R.legal_frequency_mask(fx, fy, "GQ")
    xmask = legal & (fx > 0.03) & (fx < 0.09) & (np.abs(fy) <= 0.006)
    ymask = legal & (fy > 0.03) & (fy < 0.09) & (np.abs(fx) <= 0.006)
    px = strongest_peak(psd, fx, fy, xmask)
    py = strongest_peak(psd, fx, fy, ymask)
    recovered = [px[0], py[1]]
    errors = [abs(x - f0) for x in recovered]
    tolerance = 1.5 / 512
    factor_two_errors = [abs(2 * x - f0) for x in recovered]
    return {
        "planted_cyc_per_sensor_px": f0,
        "recovered_cyc_per_sensor_px": recovered,
        "absolute_errors": errors,
        "tolerance": tolerance,
        "blocks": blocks,
        "known_answer": {
            "status": "PASS" if max(errors) <= tolerance else "FAIL",
            "criterion": "both sensor axes recover the planted frequency within 1.5 FFT bins",
        },
        "factor_two_defect": {
            "status": "CAUGHT"
            if min(factor_two_errors) > tolerance
            else "MISSED",
            "defective_absolute_errors": factor_two_errors,
            "criterion": "doubling the sensor-frequency conversion must fail the same tolerance",
        },
    }


def analyze_grid_frame(path: Path) -> dict:
    active = load_active(path)
    q = R.extract_gq(
        active,
        active.shape[0] // 2,
        active.shape[1] // 2,
        1024,
    )
    psd, blocks = R.welch_psd2(q, 256)
    fx, fy = R.gq_frequency_grid(256)
    legal = R.legal_frequency_mask(fx, fy, "GQ")
    xmask = legal & (fx > 0.03) & (fx < 0.09) & (np.abs(fy) <= 0.006)
    ymask = legal & (fy > 0.03) & (fy < 0.09) & (np.abs(fx) <= 0.006)
    px = strongest_peak(psd, fx, fy, xmask)
    py = strongest_peak(psd, fx, fy, ymask)

    def ladder(axis: str, f0: float) -> list[dict]:
        found = []
        for harmonic in range(1, int(math.floor(0.49 / f0)) + 1):
            target = harmonic * f0
            if axis == "x":
                distance = np.hypot(fx - target, fy)
            else:
                distance = np.hypot(fx, fy - target)
            peak_mask = legal & (distance <= 0.006)
            bg_mask = legal & (distance > 0.008) & (distance <= 0.018)
            if not np.any(peak_mask) or not np.any(bg_mask):
                continue
            peak = float(np.max(psd[peak_mask]))
            background = float(np.median(psd[bg_mask]))
            found.append(
                {
                    "harmonic": harmonic,
                    "target": target,
                    "peak_to_local_median": peak / max(background, 1e-30),
                }
            )
        return found

    return {
        "path": str(path),
        "sha256": R.file_sha256(path),
        "blocks": blocks,
        "fundamental_x_cyc_per_sensor_px": abs(px[0]),
        "fundamental_y_cyc_per_sensor_px": abs(py[1]),
        "x_peak": list(px),
        "y_peak": list(py),
        "x_harmonics": ladder("x", abs(px[0])),
        "y_harmonics": ladder("y", abs(py[1])),
    }


def real_grid_control() -> dict:
    frames = []
    for run in sorted(p for p in GRID_ROOT.iterdir() if p.is_dir()):
        files = sorted(run.glob("*.ARW"))
        if files:
            frames.append(analyze_grid_frame(files[len(files) // 2]))
    fx = np.array([r["fundamental_x_cyc_per_sensor_px"] for r in frames])
    fy = np.array([r["fundamental_y_cyc_per_sensor_px"] for r in frames])
    all_ladders = [
        h
        for r in frames
        for key in ("x_harmonics", "y_harmonics")
        for h in r[key]
    ]
    strong = sum(h["peak_to_local_median"] >= 10 for h in all_ladders)
    f0 = float(np.median(np.r_[fx, fy]))
    # The grid README specifies 0.01 mm divisions.  Sensor pitch is 5.12 um.
    inferred_magnification = (1 / f0) * 5.12 / 10.0
    axis_disagreement = float(np.median(np.abs(fx - fy) / ((fx + fy) / 2)))
    return {
        "source": str(GRID_ROOT),
        "frames": frames,
        "frame_count": len(frames),
        "median_fundamental_cyc_per_sensor_px": f0,
        "period_sensor_px": 1 / f0,
        "grid_division_um": 10.0,
        "sensor_pitch_um": 5.12,
        "inferred_magnification_if_one_division_is_the_fundamental": inferred_magnification,
        "median_axis_fractional_disagreement": axis_disagreement,
        "strong_harmonics": strong,
        "tested_harmonics": len(all_ladders),
        "status": "PASS"
        if len(frames) >= 3 and axis_disagreement < 0.05 and strong >= 12
        else "FAIL",
        "criterion": (
            "at least three runs, x/y fundamentals agree within 5%, "
            "and at least 12 registered harmonics exceed 10x local median power"
        ),
        "interpretation": (
            "The periodic target validates sensor-frequency axes but is too "
            "coherent to license the broadband natural-scene rho model."
        ),
    }


def edge_spectrum_from_plane(
    g: np.ndarray,
    coarse_row: int | None = None,
) -> tuple[dict, np.ndarray, np.ndarray]:
    c0 = max(16, int(round(g.shape[1] * 0.057)))
    c1 = min(g.shape[1] - 16, int(round(g.shape[1] * 0.94)))
    row_profile = np.mean(g[:, c0:c1], axis=1)
    coarse_gradient = -np.gradient(gaussian_filter1d(row_profile, 1.0))
    margin = max(32, g.shape[0] // 10)
    if coarse_row is None:
        coarse_row = margin + int(np.argmax(coarse_gradient[margin:-margin]))
    radius = max(30, g.shape[0] // 52)
    r0 = max(0, coarse_row - radius)
    r1 = min(g.shape[0], coarse_row + radius + 1)

    points = []
    width = max(16, (c1 - c0) // 96)
    for start in range(c0, c1 - width + 1, width):
        profile = np.mean(g[r0:r1, start : start + width], axis=1)
        gradient = -np.gradient(gaussian_filter1d(profile, 1.0))
        imax = int(np.argmax(gradient))
        lo = max(0, imax - 3)
        hi = min(len(gradient), imax + 4)
        weights = np.maximum(gradient[lo:hi], 0)
        position = r0 + (
            float(np.sum(np.arange(lo, hi) * weights) / np.sum(weights))
            if np.sum(weights) > 0
            else float(imax)
        )
        points.append((start + (width - 1) / 2, position, float(gradient[imax])))

    points_array = np.asarray(points)
    strength_floor = max(1e-9, float(np.median(points_array[:, 2]) * 0.15))
    keep = points_array[:, 2] > strength_floor
    residual = np.zeros(len(points_array))
    mad = float("nan")
    for _ in range(6):
        fit = np.polyfit(points_array[keep, 0], points_array[keep, 1], 1)
        residual = points_array[:, 1] - np.polyval(fit, points_array[:, 0])
        centered = residual[keep] - np.median(residual[keep])
        mad = 1.4826 * float(np.median(np.abs(centered)))
        keep = (points_array[:, 2] > strength_floor) & (
            np.abs(residual) < max(3 * mad, 2.0)
        )

    band_sensor_px = 100.0
    sample_width_sensor_px = 0.1
    rows = np.arange(max(0, coarse_row - 150), min(g.shape[0], coarse_row + 151))
    cols = np.arange(c0, c1)
    distance_lattice = (
        rows[:, None] - (fit[0] * cols[None, :] + fit[1])
    ) / math.sqrt(1 + fit[0] ** 2)
    distance_sensor = 2 * distance_lattice
    values = g[rows[0] : rows[-1] + 1, c0:c1]
    edges = np.arange(
        -band_sensor_px,
        band_sensor_px + sample_width_sensor_px,
        sample_width_sensor_px,
    )
    index = np.floor(
        (distance_sensor.ravel() - edges[0]) / sample_width_sensor_px
    ).astype(int)
    valid = (index >= 0) & (index < len(edges) - 1)
    sums = np.bincount(
        index[valid],
        weights=values.ravel()[valid],
        minlength=len(edges) - 1,
    )
    counts = np.bincount(index[valid], minlength=len(edges) - 1)
    centers = (edges[:-1] + edges[1:]) / 2
    populated = counts > 0
    esf = np.interp(centers, centers[populated], (sums / counts.clip(min=1))[populated])
    low = float(np.median(esf[centers < -60]))
    high = float(np.median(esf[centers > 60]))
    normalized = (esf - low) / (high - low)
    lsf = np.gradient(normalized, sample_width_sensor_px)
    lsf -= np.median(np.r_[lsf[:400], lsf[-400:]])
    frequency = np.fft.rfftfreq(len(lsf), d=sample_width_sensor_px)
    transfer_power = np.abs(np.fft.rfft(lsf)) ** 2
    power = np.full_like(transfer_power, np.nan)
    power[1:] = transfer_power[1:] / (2 * np.pi * frequency[1:]) ** 2
    fit_mask = (frequency >= 0.005) & (frequency <= 0.03) & (power > 0)
    beta = -float(
        np.polyfit(np.log(frequency[fit_mask]), np.log(power[fit_mask]), 1)[0]
    )
    defective_power = transfer_power
    defective_beta = -float(
        np.polyfit(
            np.log(frequency[fit_mask]),
            np.log(defective_power[fit_mask]),
            1,
        )[0]
    )
    details = {
        "coarse_edge_row_g1": coarse_row,
        "line_slope_g1_rows_per_g1_column": float(fit[0]),
        "line_intercept_g1_row": float(fit[1]),
        "kept_segments": int(np.sum(keep)),
        "total_segments": len(points),
        "segment_residual_mad_g1_px": mad,
        "esf_bin_width_sensor_px": sample_width_sensor_px,
        "median_samples_per_esf_bin": float(np.median(counts)),
        "fit_band_cyc_per_sensor_px": [0.005, 0.03],
        "beta": beta,
        "defective_lsf_as_esf_beta": defective_beta,
        "side_levels_dn": [low, high],
    }
    return details, frequency, power


def synthetic_edge_control() -> dict:
    rows, cols = 900, 1800
    slope = -0.006
    intercept = rows * 0.52
    yy, xx = np.indices((rows, cols), dtype=float)
    distance_sensor = 2 * (
        yy - (slope * xx + intercept)
    ) / math.sqrt(1 + slope**2)
    g = 2200 - 1400 * 0.5 * (1 + erf(distance_sensor / (math.sqrt(2) * 1.2)))
    details, _, _ = edge_spectrum_from_plane(g, int(round(intercept)))
    tolerance = 0.35
    return {
        "expected_beta": 2.0,
        "recovered_beta": details["beta"],
        "absolute_error": abs(details["beta"] - 2.0),
        "tolerance": tolerance,
        "known_answer": {
            "status": "PASS"
            if abs(details["beta"] - 2.0) <= tolerance
            else "FAIL",
            "criterion": "step-edge power slope is beta=2 within 0.35",
        },
        "lsf_as_esf_defect": {
            "status": "CAUGHT"
            if abs(details["defective_lsf_as_esf_beta"] - 2.0) > tolerance
            else "MISSED",
            "defective_beta": details["defective_lsf_as_esf_beta"],
            "criterion": "differentiating the edge but still expecting beta=2 must fail",
        },
    }


def edge_score(g: np.ndarray) -> tuple[float, int]:
    c0 = max(16, int(round(g.shape[1] * 0.057)))
    c1 = min(g.shape[1] - 16, int(round(g.shape[1] * 0.94)))
    profile = np.mean(g[:, c0:c1], axis=1)
    gradient = -np.gradient(gaussian_filter1d(profile, 1.0))
    margin = max(32, g.shape[0] // 10)
    row = margin + int(np.argmax(gradient[margin:-margin]))
    return float(gradient[row]), row


def real_razor_control() -> dict:
    files = sorted(RAZOR_ROOT.glob("*.ARW"))
    candidates = []
    selected_plane = None
    selected_path = None
    selected_row = None
    for index in range(0, len(files), 5):
        active = load_active(files[index])
        g1 = active[0::2, 1::2].astype(float)
        score, row = edge_score(g1)
        candidates.append(
            {
                "index": index,
                "path": str(files[index]),
                "edge_score_dn_per_g1_px": score,
                "coarse_edge_row_g1": row,
            }
        )
        if selected_plane is None or score > max(
            x["edge_score_dn_per_g1_px"] for x in candidates[:-1]
        ):
            selected_plane = g1
            selected_path = files[index]
            selected_row = row
    assert selected_plane is not None and selected_path is not None
    details, _, _ = edge_spectrum_from_plane(selected_plane, selected_row)
    beta = details["beta"]
    return {
        "source": str(RAZOR_ROOT),
        "selection_rule": (
            "among every fifth frame, select the largest negative derivative "
            "of the full-width G1 row profile"
        ),
        "candidates": candidates,
        "selected_path": str(selected_path),
        "selected_sha256": R.file_sha256(selected_path),
        **details,
        "expected_geometric_step_beta": 2.0,
        "status": "PASS" if 2.0 <= beta <= 3.0 else "FAIL",
        "criterion": (
            "undemosaiced slanted-edge low-band power slope lies in [2,3]; "
            "the geometric step supplies beta=2 and optical MTF steepens it"
        ),
        "interpretation": (
            "This validates the edge-spectrum convention.  It does not estimate "
            "natural-scene rho because a blade edge is not a stationary field."
        ),
    }


def main() -> None:
    result = {
        "schema_version": 1,
        "role": (
            "geometry-specific controls only; no value here enters the "
            "natural-scene rho census"
        ),
        "synthetic_grid": synthetic_grid_control(),
        "real_calibration_grid": real_grid_control(),
        "synthetic_edge": synthetic_edge_control(),
        "real_razor_edge": real_razor_control(),
    }
    known = [
        result["synthetic_grid"]["known_answer"]["status"],
        result["real_calibration_grid"]["status"],
        result["synthetic_edge"]["known_answer"]["status"],
        result["real_razor_edge"]["status"],
    ]
    defects = [
        result["synthetic_grid"]["factor_two_defect"]["status"],
        result["synthetic_edge"]["lsf_as_esf_defect"]["status"],
    ]
    result["tally"] = {
        "PASS": known.count("PASS"),
        "FAIL": known.count("FAIL"),
        "CAUGHT": defects.count("CAUGHT"),
        "MISSED": defects.count("MISSED"),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "diagnostics.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"diagnostics: PASS {result['tally']['PASS']} / "
        f"FAIL {result['tally']['FAIL']}; "
        f"CAUGHT {result['tally']['CAUGHT']} / "
        f"MISSED {result['tally']['MISSED']}"
    )
    print(
        "grid f0 "
        f"{result['real_calibration_grid']['median_fundamental_cyc_per_sensor_px']:.6f}; "
        "razor beta "
        f"{result['real_razor_edge']['beta']:.3f}"
    )
    if result["tally"]["FAIL"] or result["tally"]["MISSED"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
