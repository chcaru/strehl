"""Measure rho on controlled captures and an ordinary-scene census."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
STREHL = ROOT.parent.parent
sys.path.insert(0, str(HERE))

import data_lib as D  # noqa: E402
import rho_lib as R  # noqa: E402


ORDINARY_SCENES = (
    "bee-1-cpl",
    "dry-erase-marker-head-cpl",
    "flower-inner-edge-cpl",
    "pencil-steep-angle-cpl",
    "wrapped-text-1",
)
QUANTILES = (0.25, 0.50, 0.75)
SCENE_CLIP_MAX = 1e-4
SCENE_BLACK_MAX = 0.01
LOW_SNR_MIN = 5.0


def high_band_mean(psd: np.ndarray) -> float:
    fx, fy = R.gq_frequency_grid(psd.shape[0])
    radius = np.hypot(fx, fy)
    keep = (
        R.legal_frequency_mask(fx, fy, "GQ")
        & (radius >= 0.25)
        & (radius < 0.50)
    )
    return float(np.mean(psd[keep]))


def quality_metrics(
    raw_signal: np.ndarray, calibrated: np.ndarray, full_floor: float
) -> dict:
    psd, blocks = R.welch_psd2(calibrated, tile=256, window="hann")
    fx, fy = R.gq_frequency_grid(256)
    radius = np.hypot(fx, fy)
    legal = R.legal_frequency_mask(fx, fy, "GQ")
    low = legal & (radius >= 0.04) & (radius <= 0.12)
    high = legal & (radius >= 0.25) & (radius < 0.50)
    low_scene = float(np.mean(psd[low]) - full_floor)
    high_scene = float(np.mean(psd[high]) - full_floor)
    low_snr = low_scene / max(float(full_floor), np.finfo(float).tiny)
    corrected = np.maximum(psd[legal] - full_floor, 0.0)
    if float(np.sum(corrected)) > 0.0:
        concentration = float(
            np.sum(np.sort(corrected)[-10:]) / np.sum(corrected)
        )
    else:
        concentration = float("nan")
    clip = float(np.mean(raw_signal >= 14848.0))
    black = float(np.mean(raw_signal <= 0.0))
    return {
        "clip_fraction": clip,
        "black_fraction": black,
        "p999_raw_dn": float(np.percentile(raw_signal + D.BLACK_LEVEL, 99.9)),
        "mean_signal_dn": float(np.mean(raw_signal)),
        "full_noise_floor_dn2": float(full_floor),
        "low_scene_power": low_scene,
        "low_snr": float(low_snr),
        "high_scene_power": high_scene,
        "high_scene_to_noise": float(
            high_scene / max(float(full_floor), np.finfo(float).tiny)
        ),
        "spectral_top10_concentration": concentration,
        "welch_blocks": blocks,
        "passes_clip": bool(clip <= SCENE_CLIP_MAX),
        "passes_black": bool(black <= SCENE_BLACK_MAX),
        "passes_texture": bool(low_snr >= LOW_SNR_MIN),
    }


def fit_safe(
    patch: np.ndarray,
    floor: float,
    *,
    tile: int = 256,
    window: str = "hann",
    rmin: float = 0.04,
    rmax: float = 0.46,
    required_max_frequency: float = 0.25,
) -> dict:
    try:
        fit = R.fit_gq_powerlaw(
            patch,
            noise_floor=max(float(floor), 0.0),
            tile=tile,
            window=window,
            rmin=rmin,
            rmax=rmax,
            angular_model=True,
            required_max_frequency=required_max_frequency,
        )
        payload = fit.to_dict()
        payload["status"] = "PASS"
        payload["model_gate"] = bool(
            fit.holdout_median_abs_dex <= 0.30
            and fit.holdout_p90_abs_dex <= 0.60
            and fit.beta <= 8.0
        )
        if not payload["model_gate"]:
            payload["status"] = "REJECT"
            payload["reason"] = "holdout or commissioned-beta gate"
        return payload
    except Exception as exc:
        return {
            "status": "REJECT",
            "model_gate": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }


def fit_psd_safe(psd: np.ndarray, sem: np.ndarray, blocks: int) -> dict:
    try:
        fit = R.fit_gq_powerlaw_psd(
            psd,
            blocks=blocks,
            noise_floor=0.0,
            rmin=0.04,
            rmax=0.46,
            angular_model=True,
            required_max_frequency=0.25,
            signed_se=sem,
        )
        payload = fit.to_dict()
        payload["status"] = "PASS"
        payload["model_gate"] = bool(
            fit.holdout_median_abs_dex <= 0.30
            and fit.holdout_p90_abs_dex <= 0.60
            and fit.beta <= 8.0
        )
        if not payload["model_gate"]:
            payload["status"] = "REJECT"
            payload["reason"] = "cross-spectrum holdout or beta gate"
        return payload
    except Exception as exc:
        return {
            "status": "REJECT",
            "model_gate": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }


def stochastic_floors(
    raw_signal: np.ndarray,
    roi: int,
    maps: dict,
    gain: float,
    read_variance: float,
    frame_count: int,
) -> dict:
    dark = np.asarray(maps["dark"][roi], dtype=float)
    scene = np.maximum(np.asarray(raw_signal, dtype=float) - dark, 0.0)
    out = {}
    for split in ("a", "b"):
        response = np.asarray(maps[f"gain_{split}"][roi], dtype=float)
        read = float(np.mean(read_variance / (response * response)))
        full = float(
            np.mean((gain * scene + read_variance) / (response * response))
        )
        out[split] = {
            "read": read / frame_count,
            "full": full / frame_count,
        }
    out["none"] = {
        "read": float(read_variance / frame_count),
        "full": float(
            (gain * np.mean(scene) + read_variance) / frame_count
        ),
    }
    return out


def fit_variants(
    raw_mean: np.ndarray,
    calibrated_a: np.ndarray,
    calibrated_b: np.ndarray,
    calibrated_none: np.ndarray,
    floors: dict,
    empirical_floor: float | None = None,
) -> dict:
    fits = {
        "raw_a": fit_safe(calibrated_a, 0.0),
        "dark_a": fit_safe(calibrated_a, floors["a"]["read"]),
        "full_a": fit_safe(calibrated_a, floors["a"]["full"]),
        "full_b": fit_safe(calibrated_b, floors["b"]["full"]),
        "full_no_response": fit_safe(
            calibrated_none, floors["none"]["full"]
        ),
    }
    if empirical_floor is not None and empirical_floor > 0.0:
        fits["empirical_a"] = fit_safe(calibrated_a, empirical_floor)
    fits["bands"] = {
        "0.04-0.20": fit_safe(
            calibrated_a,
            floors["a"]["full"],
            rmin=0.04,
            rmax=0.20,
            required_max_frequency=0.18,
        ),
        "0.06-0.30": fit_safe(
            calibrated_a,
            floors["a"]["full"],
            rmin=0.06,
            rmax=0.30,
            required_max_frequency=0.25,
        ),
        "0.08-0.46": fit_safe(
            calibrated_a,
            floors["a"]["full"],
            rmin=0.08,
            rmax=0.46,
            required_max_frequency=0.25,
        ),
    }
    return fits


def analyze_single_patch(
    raw_signal: np.ndarray,
    roi: int,
    maps: dict,
    gain: float,
    read_variance: float,
    identity: dict,
) -> dict:
    raw_signal = np.asarray(raw_signal, dtype=float)
    none = D.calibrate_patch(raw_signal, roi, maps, None)
    cal_a = D.calibrate_patch(raw_signal, roi, maps, "a")
    cal_b = D.calibrate_patch(raw_signal, roi, maps, "b")
    floors = stochastic_floors(
        raw_signal, roi, maps, gain, read_variance, frame_count=1
    )
    quality = quality_metrics(raw_signal, cal_a, floors["a"]["full"])
    record = {
        **identity,
        "roi": roi,
        "centre": list(D.ROI_CENTRES[roi]),
        "frame_count": 1,
        "quality": quality,
        "floors": floors,
    }
    if not (
        quality["passes_clip"]
        and quality["passes_black"]
        and quality["passes_texture"]
    ):
        record["status"] = "REJECT"
        record["reason"] = "capture-quality gate"
        record["fits"] = {}
        return record
    record["fits"] = fit_variants(
        raw_signal, cal_a, cal_b, none, floors
    )
    record["status"] = (
        "PASS"
        if record["fits"]["full_a"].get("status") == "PASS"
        else "REJECT"
    )
    if record["status"] != "PASS":
        record["reason"] = record["fits"]["full_a"].get("reason")
    return record


def analyze_repeat_group(
    rows: list[dict],
    roi_indices: tuple[int, ...],
    maps: dict,
    gain: float,
    read_variance: float,
    identity: dict,
) -> list[dict]:
    n = len(rows)
    sums = {
        key: {
            roi: np.zeros((D.GQ_SIZE, D.GQ_SIZE), dtype=np.float64)
            for roi in roi_indices
        }
        for key in ("raw", "none", "a", "b")
    }
    variance_sum = {
        key: {roi: 0.0 for roi in roi_indices}
        for key in ("none", "a", "b")
    }
    empirical = {roi: [] for roi in roi_indices}
    cross_values = {roi: [] for roi in roi_indices}
    cross_pairs = {roi: [] for roi in roi_indices}
    cross_count = {roi: 0 for roi in roi_indices}
    previous = {}
    clip_sum = {roi: 0.0 for roi in roi_indices}
    black_sum = {roi: 0.0 for roi in roi_indices}

    for frame_index, row in enumerate(rows):
        patches, _ = D.load_gq_patches(row["SourceFile"])
        for roi in roi_indices:
            raw = np.asarray(patches[roi], dtype=float)
            none = D.calibrate_patch(raw, roi, maps, None)
            cal_a = D.calibrate_patch(raw, roi, maps, "a")
            cal_b = D.calibrate_patch(raw, roi, maps, "b")
            sums["raw"][roi] += raw
            sums["none"][roi] += none
            sums["a"][roi] += cal_a
            sums["b"][roi] += cal_b
            clip_sum[roi] += float(np.mean(raw >= 14848.0))
            black_sum[roi] += float(np.mean(raw <= 0.0))

            dark = np.asarray(maps["dark"][roi], dtype=float)
            scene = np.maximum(raw - dark, 0.0)
            variance_sum["none"][roi] += float(
                gain * np.mean(scene) + read_variance
            )
            for split, calibrated in (("a", cal_a), ("b", cal_b)):
                response = np.asarray(
                    maps[f"gain_{split}"][roi], dtype=float
                )
                variance_sum[split][roi] += float(
                    np.mean(
                        (gain * scene + read_variance)
                        / (response * response)
                    )
                )

            if frame_index % 2 == 0:
                previous[roi] = cal_a.astype(np.float32)
            else:
                prior = previous.pop(roi)
                diff_psd, _ = R.welch_psd2(
                    (prior - cal_a) / np.sqrt(2.0),
                    tile=256,
                    window="hann",
                )
                empirical[roi].append(high_band_mean(diff_psd))
                cross, auto_a, auto_b, blocks = R.complex_cross_psd(
                    prior, cal_a, tile=256, window="hann"
                )
                try:
                    shift = R.fit_cross_translation(cross, auto_a, auto_b)
                    accepted = bool(
                        shift["median_coherence"] >= 0.95
                        and shift["se_dx"] <= 0.02
                        and shift["se_dy"] <= 0.02
                    )
                except Exception as exc:
                    shift = {
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                    accepted = False
                shift["accepted"] = accepted
                shift["files"] = [
                    rows[frame_index - 1]["FileName"],
                    row["FileName"],
                ]
                cross_pairs[roi].append(shift)
                if accepted:
                    cross_values[roi].append(
                        R.derotate_cross_psd(
                            cross, (shift["dx"], shift["dy"])
                        )
                    )
                    cross_count[roi] += 1

    records = []
    for roi in roi_indices:
        raw_mean = sums["raw"][roi] / n
        none = sums["none"][roi] / n
        cal_a = sums["a"][roi] / n
        cal_b = sums["b"][roi] / n
        response_a = np.asarray(maps["gain_a"][roi], dtype=float)
        response_b = np.asarray(maps["gain_b"][roi], dtype=float)
        floors = {
            "none": {
                "read": read_variance / n,
                "full": variance_sum["none"][roi] / (n * n),
            },
            "a": {
                "read": float(
                    np.mean(read_variance / (response_a * response_a)) / n
                ),
                "full": variance_sum["a"][roi] / (n * n),
            },
            "b": {
                "read": float(
                    np.mean(read_variance / (response_b * response_b)) / n
                ),
                "full": variance_sum["b"][roi] / (n * n),
            },
        }
        empirical_floor = (
            float(np.mean(empirical[roi]) / n)
            if empirical[roi]
            else None
        )
        quality = quality_metrics(raw_mean, cal_a, floors["a"]["full"])
        quality["clip_fraction"] = clip_sum[roi] / n
        quality["black_fraction"] = black_sum[roi] / n
        quality["passes_clip"] = bool(
            quality["clip_fraction"] <= SCENE_CLIP_MAX
        )
        quality["passes_black"] = bool(
            quality["black_fraction"] <= SCENE_BLACK_MAX
        )
        record = {
            **identity,
            "roi": roi,
            "centre": list(D.ROI_CENTRES[roi]),
            "frame_count": n,
            "files": [row["FileName"] for row in rows],
            "quality": quality,
            "floors": floors,
            "empirical_floor_a": empirical_floor,
            "cross_pairs": cross_pairs[roi],
            "cross_pairs_accepted": cross_count[roi],
        }
        if not (
            quality["passes_clip"]
            and quality["passes_black"]
            and quality["passes_texture"]
        ):
            record["status"] = "REJECT"
            record["reason"] = "capture-quality gate"
            record["fits"] = {}
            records.append(record)
            continue
        fits = fit_variants(
            raw_mean,
            cal_a,
            cal_b,
            none,
            floors,
            empirical_floor=empirical_floor,
        )
        if cross_count[roi] >= 4:
            cross_stack = np.stack(cross_values[roi])
            fits["cross_a"] = fit_psd_safe(
                np.mean(cross_stack, axis=0),
                np.std(cross_stack, axis=0, ddof=1)
                / np.sqrt(cross_stack.shape[0]),
                blocks=49 * cross_count[roi],
            )
        record["fits"] = fits
        primary_key = (
            "empirical_a"
            if identity.get("arm") in ("iso", "iso-bee", "repeat-primary")
            and "empirical_a" in fits
            else "full_a"
        )
        record["primary_fit_key"] = primary_key
        record["status"] = (
            "PASS" if fits[primary_key].get("status") == "PASS" else "REJECT"
        )
        if record["status"] != "PASS":
            record["reason"] = fits[primary_key].get("reason")
        records.append(record)
    return records


def summarize_metadata(records: list[dict], root: Path) -> dict:
    settings = Counter(
        (
            row.get("Model"),
            row.get("ISO"),
            row.get("ExposureTime"),
            row.get("FNumber"),
            row.get("SonyRawFileType"),
        )
        for row in records
    )
    return {
        "root": str(root),
        "raw_files": len(records),
        "models": dict(Counter(row.get("Model") for row in records)),
        "settings": [
            {
                "model": key[0],
                "iso": key[1],
                "exposure": key[2],
                "aperture": key[3],
                "raw_type": key[4],
                "count": count,
            }
            for key, count in sorted(
                settings.items(), key=lambda x: tuple(str(v) for v in x[0])
            )
        ],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    noise = json.load(open(OUT / "noise-model.json", encoding="utf-8"))
    if not noise["gates"]["licensed_full_subtraction"]:
        raise RuntimeError("noise model is not licensed")
    if not noise["gates"]["licensed_response_correction"]:
        raise RuntimeError("response correction is not licensed")
    gain = float(noise["primary_gain_dn_per_e"])
    read_variance = float(noise["primary_read_variance_dn2"])

    flat_records = D.exif_records([D.FLAT_ROOT])
    dark_root = D.REQUEST_ROOT / "6-11-extended-dark-frames"
    dark_records = D.exif_records([dark_root])
    maps, map_summary = D.build_calibration_maps(flat_records, dark_records)

    paper_root = D.REQUEST_ROOT / "10-paper-iso-var"
    bee_root = (
        D.REQUEST_ROOT
        / "12-bee-iso-var-no-bracket-32-repeat-diff-light"
    )
    fabric_root = D.REQUEST_ROOT / "7-aperture-pairs"
    paper_records = D.exif_records([paper_root])
    bee_records = D.exif_records([bee_root])
    fabric_records = D.exif_records([fabric_root])
    ordinary_roots = [D.MACRO_ROOT / name for name in ORDINARY_SCENES]
    ordinary_records = D.exif_records(ordinary_roots)

    measurements = []
    used_paths = set()

    paper_primary = D.group_records(
        paper_records, ISO=100, ExposureTime=0.5
    )
    used_paths.update(row["SourceFile"] for row in paper_primary)
    measurements.extend(
        analyze_repeat_group(
            paper_primary,
            tuple(range(len(D.ROI_CENTRES))),
            maps,
            gain,
            read_variance,
            {
                "scene": "paper",
                "arm": "repeat-primary",
                "iso": 100,
                "exposure": 0.5,
                "aperture": 5.6,
            },
        )
    )

    for iso in sorted(
        {
            int(row["ISO"])
            for row in paper_records
            if row.get("ExposureTime") == 0.125
        }
    ):
        rows = D.group_records(
            paper_records, ISO=iso, ExposureTime=0.125
        )
        used_paths.update(row["SourceFile"] for row in rows)
        measurements.extend(
            analyze_repeat_group(
                rows,
                (4,),
                maps,
                gain,
                read_variance,
                {
                    "scene": "paper",
                    "arm": "iso",
                    "iso": iso,
                    "exposure": 0.125,
                    "aperture": 5.6,
                },
            )
        )

    bee_iso100 = D.group_records(bee_records, ISO=100, ExposureTime=1.6)
    if len(bee_iso100) != 64:
        raise ValueError(f"expected 64 ISO 100 bee frames, got {len(bee_iso100)}")
    for light, rows in (("bright", bee_iso100[:32]), ("warm", bee_iso100[32:])):
        used_paths.update(row["SourceFile"] for row in rows)
        measurements.extend(
            analyze_repeat_group(
                rows,
                tuple(range(len(D.ROI_CENTRES))),
                maps,
                gain,
                read_variance,
                {
                    "scene": "bee",
                    "arm": "repeat-primary",
                    "light": light,
                    "iso": 100,
                    "exposure": 1.6,
                    "aperture": 5.6,
                },
            )
        )

    for iso in sorted({int(row["ISO"]) for row in bee_records}):
        rows = D.group_records(bee_records, ISO=iso, ExposureTime=1.6)
        if len(rows) != 64:
            raise ValueError(
                f"expected 64 bee frames at ISO {iso}, got {len(rows)}"
            )
        bright = rows[:32]
        used_paths.update(row["SourceFile"] for row in bright)
        measurements.extend(
            analyze_repeat_group(
                bright,
                (4,),
                maps,
                gain,
                read_variance,
                {
                    "scene": "bee",
                    "arm": "iso-bee",
                    "light": "bright",
                    "iso": iso,
                    "exposure": 1.6,
                    "aperture": 5.6,
                },
            )
        )

    by_source = {row["SourceFile"].replace("\\", "/"): row for row in fabric_records}
    fabric_cache = {}
    focus_out = STREHL / "experiments" / "M129-fabric-spectral-ladder" / "out"
    for aperture in ("f5.6", "f8", "f11", "f14", "f18"):
        focus = json.load(
            open(focus_out / f"focusmap-{aperture}.json", encoding="utf-8")
        )
        rcs = np.asarray(focus["rcs"])
        ccs = np.asarray(focus["ccs"])
        best = np.asarray(focus["best"])
        directory = next(fabric_root.glob(f"fabric-weave-{aperture}-*"))
        files = sorted(directory.glob("*.ARW"))
        chosen = {}
        for roi, (rc, cc) in enumerate(D.ROI_CENTRES):
            ir = int(np.argmin(np.abs(rcs - rc)))
            ic = int(np.argmin(np.abs(ccs - cc)))
            index = min(int(best[ir, ic]), len(files) - 1)
            chosen[roi] = (index, files[index])
        for path in {p for _, p in chosen.values()}:
            patches, _ = D.load_gq_patches(path)
            fabric_cache[str(path)] = patches
            used_paths.add(str(path))
        for roi, (index, path) in chosen.items():
            meta = by_source.get(str(path).replace("\\", "/"), {})
            measurements.append(
                analyze_single_patch(
                    fabric_cache[str(path)][roi],
                    roi,
                    maps,
                    gain,
                    read_variance,
                    {
                        "scene": "fabric",
                        "arm": "aperture",
                        "iso": int(meta.get("ISO", 100)),
                        "exposure": float(meta.get("ExposureTime", 1.3)),
                        "aperture": float(meta.get("FNumber", aperture[1:])),
                        "file": path.name,
                        "frame_index": index,
                        "focus_source": "M129 low-band focus map",
                    },
                )
            )

    ordinary_by_dir = defaultdict(list)
    for row in ordinary_records:
        ordinary_by_dir[Path(row["Directory"]).name].append(row)
    for scene in ORDINARY_SCENES:
        rows = sorted(
            ordinary_by_dir[scene],
            key=lambda x: x["FileName"].lower(),
        )
        if not rows:
            raise ValueError(f"no ordinary records for {scene}")
        indices = sorted(
            {
                int(round(q * (len(rows) - 1)))
                for q in QUANTILES
            }
        )
        for index in indices:
            row = rows[index]
            path = Path(row["SourceFile"])
            patches, _ = D.load_gq_patches(path)
            used_paths.add(row["SourceFile"])
            for roi, patch in enumerate(patches):
                measurements.append(
                    analyze_single_patch(
                        patch,
                        roi,
                        maps,
                        gain,
                        read_variance,
                        {
                            "scene": scene,
                            "arm": "ordinary-census",
                            "quantile_index": index,
                            "quantile_fraction": float(
                                index / max(len(rows) - 1, 1)
                            ),
                            "iso": int(row["ISO"]),
                            "exposure": float(row["ExposureTime"]),
                            "aperture": float(row["FNumber"]),
                            "file": row["FileName"],
                        },
                    )
                )

    selected = []
    for path in sorted(used_paths, key=str.lower):
        selected.append(
            {
                "path": str(path),
                "sha256": R.file_sha256(path),
            }
        )

    first = selected[0]["path"]
    active_a, layout_a = D.load_active(first)
    active_b, layout_b = D.load_active(first)
    checksum_a = R.file_sha256(first)
    pixel_a = hashlib.sha256(active_a.tobytes()).hexdigest()
    pixel_b = hashlib.sha256(active_b.tobytes()).hexdigest()
    loader_check = {
        "file": first,
        "layout_first": layout_a,
        "layout_second": layout_b,
        "file_sha256": checksum_a,
        "pixel_sha256_first": pixel_a,
        "pixel_sha256_second": pixel_b,
        "pixel_checksum_equal": bool(pixel_a == pixel_b),
        "mean_first": float(np.mean(active_a)),
        "mean_second": float(np.mean(active_b)),
        "std_first": float(np.std(active_a)),
        "std_second": float(np.std(active_b)),
    }

    inventory = {
        "read_only_root": str(D.MACRO_ROOT),
        "camera_models": sorted(
            {
                row.get("Model")
                for row in (
                    paper_records
                    + bee_records
                    + fabric_records
                    + ordinary_records
                )
            }
        ),
        "sensor_variation_identified": False,
        "sensor_variation_reason": "all usable captures are ILCE-7CM2",
        "groups": {
            "paper": summarize_metadata(paper_records, paper_root),
            "bee": summarize_metadata(bee_records, bee_root),
            "fabric": summarize_metadata(fabric_records, fabric_root),
            "ordinary": summarize_metadata(
                ordinary_records, D.MACRO_ROOT
            ),
        },
        "calibration_map": map_summary,
        "selected_files": selected,
        "loader_check": loader_check,
    }
    with open(OUT / "inventory.json", "w", encoding="utf-8") as fh:
        json.dump(inventory, fh, indent=2)
    with open(OUT / "scene-estimates.json", "w", encoding="utf-8") as fh:
        json.dump(measurements, fh, indent=2)

    passed = [
        row
        for row in measurements
        if row["status"] == "PASS"
        and row.get("fits", {})
        .get(row.get("primary_fit_key", "full_a"), {})
        .get("status")
        == "PASS"
    ]
    print(
        f"scene records: PASS {len(passed)} / REJECT "
        f"{len(measurements) - len(passed)}"
    )
    for arm in sorted({row["arm"] for row in measurements}):
        subset = [row for row in passed if row["arm"] == arm]
        values = [
            row["fits"][row.get("primary_fit_key", "full_a")]["rho_g"]
            for row in subset
        ]
        if values:
            print(
                f"{arm:18s} n={len(values):3d} "
                f"rho median {np.median(values):.6g} "
                f"p10-p90 {np.percentile(values, 10):.6g}-"
                f"{np.percentile(values, 90):.6g}"
            )
    return 0 if len(passed) >= 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
