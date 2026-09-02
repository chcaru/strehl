"""Measure the ISO 100 read and photon-noise model from repeated RAW captures."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
sys.path.insert(0, str(HERE))

import data_lib as D  # noqa: E402
import rho_lib as R  # noqa: E402


FLAT_EXPOSURES = (
    0.004,
    0.008,
    0.01666667,
    0.03333333,
    0.05,
    0.07692308,
    0.1,
    0.125,
    0.2,
)
DARK_EXPOSURES = (1.0, 2.5, 5.0, 10.0)
PSD_BANDS = (
    (0.00, 0.05),
    (0.05, 0.15),
    (0.15, 0.25),
    (0.25, 0.35),
    (0.35, 0.50),
)


def _phase_samples(active: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    signal = active.astype(np.float32) - D.BLACK_LEVEL
    return signal[0::16, 1::16].ravel(), signal[1::16, 0::16].ravel()


def _psd_bands(psd: np.ndarray) -> list[dict]:
    fx, fy = R.gq_frequency_grid(psd.shape[0])
    radius = np.hypot(fx, fy)
    legal = R.legal_frequency_mask(fx, fy, "GQ")
    rows = []
    for lo, hi in PSD_BANDS:
        mask = legal & (radius >= lo) & (radius < hi)
        rows.append(
            {
                "lo": lo,
                "hi": hi,
                "mean": float(np.mean(psd[mask])),
                "median": float(np.median(psd[mask])),
                "bins": int(np.sum(mask)),
            }
        )
    return rows


def _trimmed_variance(mu: np.ndarray, var: np.ndarray) -> dict:
    keep = (
        np.isfinite(mu)
        & np.isfinite(var)
        & (mu > 20.0)
        & (mu < 14000.0)
        & (var >= 0.0)
    )
    if int(np.sum(keep)) < 100:
        return {
            "usable": False,
            "pixels": int(np.sum(keep)),
            "signal_mean": float(np.mean(mu)),
            "signal_median": float(np.median(mu)),
            "signal_p01": float(np.percentile(mu, 1)),
            "signal_p99": float(np.percentile(mu, 99)),
            "reason": "fewer than 100 unsaturated calibration samples",
        }
    ceiling = float(np.percentile(var[keep], 99.5))
    keep &= var <= ceiling
    return {
        "usable": True,
        "pixels": int(np.sum(keep)),
        "signal_mean": float(np.mean(mu[keep])),
        "signal_median": float(np.median(mu[keep])),
        "variance_mean": float(np.mean(var[keep])),
        "variance_median": float(np.median(var[keep])),
        "variance_trim_ceiling": ceiling,
    }


def measure_flat_group(rows: list[dict], exposure: float, run: int) -> dict:
    if len(rows) < 10:
        raise ValueError(
            f"flat exposure {exposure}, run {run} has {len(rows)} frames"
        )
    phase_1 = []
    phase_2 = []
    patches = []
    layout = None
    for row in rows:
        active, layout = D.load_active(row["SourceFile"])
        a, b = _phase_samples(active)
        phase_1.append(a)
        phase_2.append(b)
        patches.append(
            R.extract_gq(active, 2344, 3514, 1024).astype(np.float32)
            - D.BLACK_LEVEL
        )
    phase_1 = np.stack(phase_1)
    phase_2 = np.stack(phase_2)
    patches = np.stack(patches)

    frame_level = np.median(
        np.concatenate(
            [
                np.median(phase_1, axis=1)[:, None],
                np.median(phase_2, axis=1)[:, None],
            ],
            axis=1,
        ),
        axis=1,
    )
    target = float(np.median(frame_level))
    scale = target / frame_level
    phase_1 *= scale[:, None]
    phase_2 *= scale[:, None]
    patches *= scale[:, None, None]

    p1 = _trimmed_variance(
        np.mean(phase_1, axis=0), np.var(phase_1, axis=0, ddof=1)
    )
    p2 = _trimmed_variance(
        np.mean(phase_2, axis=0), np.var(phase_2, axis=0, ddof=1)
    )

    pair_psds = []
    for i in range(0, len(patches), 2):
        psd, _ = R.welch_psd2(
            (patches[i] - patches[i + 1]) / np.sqrt(2.0),
            tile=256,
            window="hann",
        )
        pair_psds.append(psd)
    mean_psd = np.mean(pair_psds, axis=0)
    high = _psd_bands(mean_psd)
    plateau_rows = [x for x in high if x["lo"] >= 0.25]
    plateau = float(
        np.average(
            [x["mean"] for x in plateau_rows],
            weights=[x["bins"] for x in plateau_rows],
        )
    )
    saturation = float(np.mean(patches >= 14848.0))
    return {
        "exposure": exposure,
        "run": run,
        "frames": len(rows),
        "first_file": rows[0]["FileName"],
        "last_file": rows[-1]["FileName"],
        "layout": layout,
        "frame_level_min": float(np.min(frame_level)),
        "frame_level_max": float(np.max(frame_level)),
        "frame_level_cv": float(np.std(frame_level, ddof=1) / np.mean(frame_level)),
        "scale_mean": float(np.mean(scale)),
        "scale2_mean": float(np.mean(scale * scale)),
        "saturation_fraction": saturation,
        "noise_plateau": plateau,
        "photon_predictor": float(target * np.mean(scale)),
        "read_predictor": float(np.mean(scale * scale)),
        "G1": p1,
        "G2": p2,
        "difference_psd": high,
    }


def measure_dark_group(rows: list[dict], exposure: float) -> dict:
    if len(rows) != 22:
        raise ValueError(f"dark exposure {exposure} has {len(rows)} frames")
    samples = []
    patches = []
    for row in rows:
        active, _ = D.load_active(row["SourceFile"])
        a, b = _phase_samples(active)
        samples.append(np.concatenate([a, b]))
        patches.append(
            R.extract_gq(active, 2344, 3514, 1024).astype(np.float32)
            - D.BLACK_LEVEL
        )
    samples = np.stack(samples)
    patches = np.stack(patches)
    mu = np.mean(samples, axis=0)
    var = np.var(samples, axis=0, ddof=1)
    keep = np.isfinite(mu) & np.isfinite(var) & (var >= 0.0)
    ceiling = float(np.percentile(var[keep], 99.5))
    keep &= var <= ceiling
    stats = {
        "usable": True,
        "pixels": int(np.sum(keep)),
        "signal_mean": float(np.mean(mu[keep])),
        "signal_median": float(np.median(mu[keep])),
        "variance_mean": float(np.mean(var[keep])),
        "variance_median": float(np.median(var[keep])),
        "variance_trim_ceiling": ceiling,
    }

    pair_psds = []
    for i in range(0, len(patches), 2):
        psd, _ = R.welch_psd2(
            (patches[i] - patches[i + 1]) / np.sqrt(2.0),
            tile=256,
            window="hann",
        )
        pair_psds.append(psd)
    mean_psd = np.mean(pair_psds, axis=0)

    split = len(patches) // 2
    master_a = np.mean(patches[:split], axis=0)
    master_b = np.mean(patches[split:], axis=0)
    fixed = (master_a + master_b) / 2.0
    fixed_psd, _ = R.welch_psd2(fixed, tile=256, window="hann")
    temporal_psd = mean_psd / len(patches)
    fixed_corrected = fixed_psd - temporal_psd
    return {
        "exposure": exposure,
        "frames": len(rows),
        "first_file": rows[0]["FileName"],
        "last_file": rows[-1]["FileName"],
        "temporal": stats,
        "difference_psd": _psd_bands(mean_psd),
        "fixed_pattern_psd": _psd_bands(fixed_corrected),
        "master_split_rms_dn": float(
            np.std(master_a - master_b) / np.sqrt(2.0)
        ),
    }


def fit_ptc(groups: list[dict], phase: str, read_variance: float) -> dict:
    usable = [
        g
        for g in groups
        if g[phase].get("usable")
        and g["saturation_fraction"] <= 1e-4
        and g["frame_level_cv"] <= 0.15
    ]
    if len(usable) < 6:
        raise ValueError(f"only {len(usable)} usable PTC groups for {phase}")
    x = np.array(
        [
            g[phase]["signal_mean"] * g["scale_mean"]
            for g in usable
        ],
        dtype=float,
    )
    y = np.array([g[phase]["variance_mean"] for g in usable], dtype=float)
    read_term = np.array([g["scale2_mean"] for g in usable], dtype=float)
    order = np.argsort(x)
    x = x[order]
    y = y[order]
    read_term = read_term[order]
    train = np.arange(x.size) % 2 == 0
    gain_train = float(
        np.dot(x[train], y[train] - read_variance * read_term[train])
        / np.dot(x[train], x[train])
    )
    pred = gain_train * x[~train] + read_variance * read_term[~train]
    rel = np.abs(pred - y[~train]) / y[~train]
    gain_all = float(
        np.dot(x, y - read_variance * read_term) / np.dot(x, x)
    )
    return {
        "phase": phase,
        "gain_dn_per_e": gain_all,
        "read_variance_dn2_fixed": float(read_variance),
        "train_gain_dn_per_e": gain_train,
        "held_out_exposures": [
            float(usable[i]["exposure"]) for i in order[~train]
        ],
        "held_out_relative_errors": [float(v) for v in rel],
        "held_out_median_relative_error": float(np.median(rel)),
        "held_out_max_relative_error": float(np.max(rel)),
        "points": [
            {
                "photon_predictor": float(a),
                "read_predictor": float(c),
                "variance": float(b),
            }
            for a, b, c in zip(x, y, read_term)
        ],
    }


def fit_plateau(groups: list[dict], read_variance: float) -> dict:
    usable = [
        g
        for g in groups
        if g["saturation_fraction"] <= 1e-4
        and g["frame_level_cv"] <= 0.15
        and g["noise_plateau"] > 0.0
    ]
    if len(usable) < 6:
        raise ValueError(f"only {len(usable)} usable plateau groups")
    x = np.array([g["photon_predictor"] for g in usable], dtype=float)
    z = np.array([g["read_predictor"] for g in usable], dtype=float)
    y = np.array([g["noise_plateau"] for g in usable], dtype=float)
    order = np.argsort(x)
    x, y, z = x[order], y[order], z[order]
    train = np.arange(x.size) % 2 == 0
    gain_train = float(
        np.dot(x[train], y[train] - read_variance * z[train])
        / np.dot(x[train], x[train])
    )
    pred = gain_train * x[~train] + read_variance * z[~train]
    rel = np.abs(pred - y[~train]) / y[~train]
    gain_all = float(
        np.dot(x, y - read_variance * z) / np.dot(x, x)
    )
    return {
        "gain_dn_per_e": gain_all,
        "read_variance_dn2_fixed": float(read_variance),
        "train_gain_dn_per_e": gain_train,
        "held_out_relative_errors": [float(v) for v in rel],
        "held_out_median_relative_error": float(np.median(rel)),
        "held_out_max_relative_error": float(np.max(rel)),
        "points": [
            {
                "photon_predictor": float(a),
                "read_predictor": float(c),
                "noise_plateau": float(b),
            }
            for a, b, c in zip(x, y, z)
        ],
    }


def split_light_runs(rows: list[dict]) -> list[list[dict]]:
    ordered = sorted(rows, key=lambda x: x["DateTimeOriginal"])
    runs = []
    current = []
    previous = None
    for row in ordered:
        stamp = datetime.strptime(row["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S")
        if previous is not None and (stamp - previous).total_seconds() > 30:
            runs.append(current)
            current = []
        current.append(row)
        previous = stamp
    if current:
        runs.append(current)
    return runs


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    flat_records = D.exif_records([D.FLAT_ROOT])
    dark_root = D.REQUEST_ROOT / "6-11-extended-dark-frames"
    dark_records = D.exif_records([dark_root])

    flat_groups = []
    for exposure in FLAT_EXPOSURES:
        rows = D.group_records(
            flat_records, ISO=100, ExposureTime=float(exposure)
        )
        runs = split_light_runs(rows)
        print(
            f"flat {exposure:g} s: {len(rows)} frames in "
            f"{len(runs)} light runs"
        )
        for run, group in enumerate(runs, 1):
            flat_groups.append(measure_flat_group(group, exposure, run))

    dark_groups = []
    for exposure in DARK_EXPOSURES:
        rows = D.group_records(
            dark_records, ISO=100, ExposureTime=float(exposure)
        )
        print(f"dark {exposure:g} s: {len(rows)} frames")
        dark_groups.append(measure_dark_group(rows, exposure))

    _, response = D.build_calibration_maps(flat_records, dark_records)
    read_variance = float(
        np.mean(
            [
                np.mean(
                    [
                        row["mean"]
                        for row in g["difference_psd"]
                        if row["lo"] >= 0.25
                    ]
                )
                for g in dark_groups[:3]
            ]
        )
    )
    ptc_g1 = fit_ptc(flat_groups, "G1", read_variance)
    ptc_g2 = fit_ptc(flat_groups, "G2", read_variance)
    plateau = fit_plateau(flat_groups, read_variance)
    held = max(
        ptc_g1["held_out_median_relative_error"],
        ptc_g2["held_out_median_relative_error"],
        plateau["held_out_median_relative_error"],
    )
    response_gate = response["median_gain_split_correlation"] >= 0.90
    payload = {
        "camera": D.CAMERA_MODEL,
        "frequency_unit": "cycles per full-resolution sensor pixel",
        "flat_groups": flat_groups,
        "dark_groups": dark_groups,
        "ptc": {"G1": ptc_g1, "G2": ptc_g2, "spectral_plateau": plateau},
        "response_map": response,
        "gates": {
            "held_out_variance_median_le_20pct": bool(held <= 0.20),
            "held_out_variance_worst_median": float(held),
            "response_split_correlation_ge_0_90": bool(response_gate),
            "licensed_full_subtraction": bool(held <= 0.20),
            "licensed_response_correction": bool(response_gate),
        },
        "primary_gain_dn_per_e": float(plateau["gain_dn_per_e"]),
        "primary_read_variance_dn2": read_variance,
    }
    with open(OUT / "noise-model.json", "w", encoding="utf-8") as fh:
        json.dump(
            payload,
            fh,
            indent=2,
            default=lambda x: x.item() if isinstance(x, np.generic) else str(x),
        )
    print(json.dumps(payload["gates"], indent=2))
    print(
        "gain %.6f DN/e, read variance %.6f DN^2"
        % (
            payload["primary_gain_dn_per_e"],
            payload["primary_read_variance_dn2"],
        )
    )
    return 0 if payload["gates"]["licensed_full_subtraction"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
