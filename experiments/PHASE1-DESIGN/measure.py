#!/usr/bin/env python3
"""Run the preregistered W1 global-k width/Pareto gate.

Exit 0 means one fixed global k clears every requirement.  Exit 20 means the
scientifically successful negative result NO_COMMON_K.  Other nonzero exits
mean the instrument or its sealed inputs were invalid.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import sys
import time
from pathlib import Path
from typing import Sequence

import numpy as np

import reference as R


GATE_RESULT = R.RESULTS / "gate.json"
NEGATIVE_EXIT = 20
LEGACY_GATE = 4.5
SNR_REF = 64.0
WIDTH_BAR = 0.05
DETAIL_BAR = 0.95
FLAT_BAR = 0.90


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_sealed_inputs() -> tuple[dict, dict, dict]:
    if not R.MANIFEST_PATH.exists() or not R.COMMISSION_PATH.exists() or not R.PREREG_PATH.exists():
        raise RuntimeError("sealed manifest, preregistration, and commissioning artifact are required")
    manifest = load_json(R.MANIFEST_PATH)
    commission = load_json(R.COMMISSION_PATH)
    if (
        manifest.get("schema") != R.SCHEMA
        or commission.get("schema") != R.SCHEMA
        or manifest.get("epoch") != R.EPOCH
        or commission.get("epoch") != R.EPOCH
        or manifest.get("design_sha") != R.DESIGN_SHA256
        or commission.get("design_sha") != R.DESIGN_SHA256
    ):
        raise RuntimeError("revised W1 schema/epoch/design seal mismatch")
    if set(manifest.get("captures", {})) != set(R.CAPTURE_ORDER):
        raise RuntimeError("manifest capture ledger is not the exact three-capture development allowlist")
    if commission.get("status") != "PASS":
        raise RuntimeError("commissioning artifact is absent or not PASS")
    manifest_hash = R.sha256(R.MANIFEST_PATH)
    if manifest_hash != R.FROZEN_MANIFEST_SHA256:
        raise RuntimeError(f"manifest hash mismatch: {manifest_hash} != {R.FROZEN_MANIFEST_SHA256}")
    expected = commission.get("hashes", {})
    current_paths = {
        "reference.py": Path(R.__file__).resolve(),
        "measure.py": Path(__file__).resolve(),
        "PREREGISTRATION.md": R.PREREG_PATH,
        "results/preregistered-manifest.json": R.MANIFEST_PATH,
    }
    for key, path in current_paths.items():
        got = R.sha256(path)
        if expected.get(key) != got:
            raise RuntimeError(f"stale commissioning artifact: {key} is {got}, commissioned {expected.get(key)}")
    for name, cfg in R.CAPTURES.items():
        got = R.sha256(Path(cfg["transform"]))
        want = commission.get("transforms", {}).get(name)
        if got != want:
            raise RuntimeError(f"{name}: transform hash mismatch {got} != {want}")
        mcap = manifest["captures"][name]
        raws = R.ordered_raws(cfg)
        if len(raws) != len(mcap["raws"]):
            raise RuntimeError(f"{name}: manifest frame count changed")
        print(f"{name}: validating {len(raws)} sealed RAW hashes", flush=True)
        for path, entry in zip(raws, mcap["raws"], strict=True):
            relative = str(path.relative_to(cfg["path"])).replace("\\", "/")
            if relative != entry["relative"] or path.stat().st_size != entry["bytes"]:
                raise RuntimeError(f"{name}: manifest identity changed at {path}")
            got = R.sha256(path)
            if got != entry["sha256"]:
                raise RuntimeError(f"{name}: RAW hash changed at {path}")
    calibration = commission.get("affine_calibration", {})
    if set(calibration.get("records", {})) != set(R.CAPTURE_ORDER):
        raise RuntimeError("commissioned actual-affine beta ledger is incomplete")
    for name, config in R.CAPTURES.items():
        values = np.asarray([row.get("beta") for row in calibration["records"][name]], dtype=np.float64)
        if values.shape != (config["frames"], R.BANDS) or not np.all(np.isfinite(values) & (values > 0)):
            raise RuntimeError(f"{name}: invalid commissioned actual-affine beta shape {values.shape}")
    frozen = np.asarray(commission.get("frozen_nu_eff"), dtype=np.float64)
    if not np.array_equal(frozen, np.asarray(R.FROZEN_NU_EFF, dtype=np.float64)):
        raise RuntimeError("commissioned nu_eff does not equal preregistered frozen vector")
    return manifest, commission, calibration


def tile_mask(tiles: Sequence[Sequence[int]]) -> np.ndarray:
    mask = np.zeros((R.SCORE_SIZE, R.SCORE_SIZE), dtype=np.float32)
    occupied = np.zeros_like(mask, dtype=bool)
    for x, y in tiles:
        if x < 0 or y < 0 or x + R.TILE > R.SCORE_SIZE or y + R.TILE > R.SCORE_SIZE:
            raise RuntimeError(f"tile {(x, y)} leaves score crop")
        if np.any(occupied[y : y + R.TILE, x : x + R.TILE]):
            raise RuntimeError(f"tiles overlap within one preregistered ROI at {(x, y)}")
        occupied[y : y + R.TILE, x : x + R.TILE] = True
        mask[y : y + R.TILE, x : x + R.TILE] = 1.0
    if len(tiles) != 32:
        raise RuntimeError(f"expected 32 bootstrap tiles, found {len(tiles)}")
    return mask


def score_slice(band: int) -> tuple[slice, slice]:
    start = R.HALO >> band
    extent = R.SCORE_SIZE >> band
    return slice(start, start + extent), slice(start, start + extent)


def exponent_at(band: int) -> float:
    return min(2.0 * 1.4 ** (R.BANDS - 1 - band), 8.0)


def legacy_weight(energy: np.ndarray, floor: np.ndarray, band: int) -> np.ndarray:
    excess = np.maximum(np.asarray(energy, dtype=np.float64) - floor, 0.0)
    ratio = excess / np.maximum(floor, 1.0) / SNR_REF
    p = exponent_at(band)
    if p == 2.0:
        out = ratio * ratio
    elif p == 1.0:
        out = ratio
    else:
        with np.errstate(divide="ignore", invalid="ignore"):
            out = np.exp(np.clip(p * np.log(ratio), -80.0, 80.0))
        out[excess <= 0] = 0.0
    if not np.all(np.isfinite(out) & (out >= 0)):
        raise RuntimeError(f"legacy band {band}: invalid soft weights")
    return out


def _weighted_mean(array: np.ndarray, mask: np.ndarray) -> float:
    den = float(np.sum(mask, dtype=np.float64))
    if den <= 0:
        raise RuntimeError("empty ROI mask")
    return float(np.sum(np.asarray(array, dtype=np.float64) * mask, dtype=np.float64) / den)


def candidate_neff_means(
    energies: np.ndarray,
    floors: np.ndarray,
    nu: float,
    masks: dict[str, np.ndarray],
) -> dict[str, list[float]]:
    """All 161 k values without materialising a k-by-image cube."""
    n, h, w = energies.shape
    e2 = energies.reshape(n, -1).astype(np.float64, copy=False)
    f2 = floors.reshape(n, -1).astype(np.float64, copy=False)
    count = h * w
    mask_vectors = {name: mask.reshape(-1).astype(np.float64) for name, mask in masks.items()}
    sums = {name: np.zeros(len(R.K_GRID), dtype=np.float64) for name in masks}
    mask_sums = {name: float(np.sum(value)) for name, value in mask_vectors.items()}
    step = 4096
    for lo in range(0, count, step):
        hi = min(lo + step, count)
        e = e2[:, lo:hi]
        f = f2[:, lo:hi]
        winner = np.argmax(e, axis=0)  # NumPy's first maximum is the stable lower ordinal.
        columns = np.arange(hi - lo)
        ew = e[winner, columns]
        fw = f[winner, columns]
        qw = np.maximum(ew - fw, 0.0)
        sigw = (2.0 * fw * fw + 4.0 * fw * qw) / nu
        q = np.maximum(e - f, 0.0)
        sig = (2.0 * f * f + 4.0 * f * q) / nu
        denominator = np.sqrt(sig + sigw[None, :])
        threshold = (ew[None, :] - e) / denominator
        threshold[winner, columns] = 0.0
        grid_index = np.ceil(np.maximum(threshold, 0.0) / 0.05 - 1e-11).astype(np.int32)
        inv_floor = 1.0 / f
        delta = np.zeros((len(R.K_GRID), hi - lo), dtype=np.float64)
        delta2 = np.zeros_like(delta)
        local_columns = np.arange(hi - lo)
        above = qw > 0
        for frame in range(n):
            valid = above & (grid_index[frame] <= len(R.K_GRID) - 1)
            if np.any(valid):
                gi = grid_index[frame, valid]
                ci = local_columns[valid]
                wt = inv_floor[frame, valid]
                np.add.at(delta, (gi, ci), wt)
                np.add.at(delta2, (gi, ci), wt * wt)
        sumw = np.cumsum(delta, axis=0)
        sumw2 = np.cumsum(delta2, axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            neff = sumw * sumw / sumw2
        neff[:, ~above] = float(n)
        if not np.all(np.isfinite(neff) & (neff >= 1.0 - 1e-8) & (neff <= n + 1e-6)):
            raise RuntimeError("candidate produced invalid Kish n_eff")
        for name, mask in mask_vectors.items():
            sums[name] += neff @ mask[lo:hi]
    return {name: (value / mask_sums[name]).tolist() for name, value in sums.items()}


def analyze_capture_width(name: str, config: dict, calibration: dict) -> dict:
    start_time = time.perf_counter()
    meta, transforms = R.parse_warpmap(Path(config["transform"]))
    if meta["plane"][0] not in (3516, 3520) or meta["plane"][1] != 2344 or len(transforms) != config["frames"]:
        raise RuntimeError(f"{name}: transform geometry/count mismatch")
    raws = R.ordered_raws(config)
    labels = {
        "detail": tile_mask(config["detail_tiles"]),
        "flat": tile_mask(config["flat_tiles"]),
    }
    label_pyramids = {label: R.gaussian_pyramid(mask, R.BANDS) for label, mask in labels.items()}
    energies: list[list[np.ndarray]] = [[] for _ in range(R.BANDS)]
    floors: list[list[np.ndarray]] = [[] for _ in range(R.BANDS)]
    legacy_sumw: list[np.ndarray | None] = [None] * R.BANDS
    legacy_sumw2: list[np.ndarray | None] = [None] * R.BANDS
    isos: list[float] = []
    beta_records: list[list[float]] = []

    for index, (path, transform) in enumerate(zip(raws, transforms, strict=True)):
        print(f"{name}: width pass frame {index + 1}/{len(raws)}", flush=True)
        planes, decode = R.prepared_crop(path, transform, config["score_origin"], meta["plane"])
        _, g1, g2, _ = planes
        luma = 0.5 * (g1 + g2)
        a, b0 = R.noise_coefficients(decode["iso"])
        decision = R.anscombe(luma, a, b0)
        v_a = R.anscombe_variance(luma, a, b0)
        decision_pyr = R.laplacian_pyramid(decision, R.BANDS)
        va_pyr = R.gaussian_pyramid(v_a, R.BANDS)
        linear_pyr = R.laplacian_pyramid(luma, R.BANDS)
        variance_pyr = R.gaussian_pyramid(a * luma + b0, R.BANDS)
        frame_beta = R.beta_for_frame(calibration, name, index)
        beta_records.append(frame_beta.tolist())
        isos.append(float(decode["iso"]))
        for band in range(R.BANDS):
            ys, xs = score_slice(band)
            e = R.smooth5(decision_pyr[band] * decision_pyr[band])[ys, xs]
            f = (frame_beta[band] * va_pyr[band])[ys, xs].astype(np.float32)
            if not np.all(np.isfinite(e) & np.isfinite(f) & (f > 0)):
                raise RuntimeError(f"{name} frame {index} band {band}: invalid candidate E/F")
            energies[band].append(e.astype(np.float32))
            floors[band].append(f)
            legacy_e = R.smooth5(linear_pyr[band] * linear_pyr[band])
            legacy_floor = LEGACY_GATE * frame_beta[band] * variance_pyr[band]
            weight = legacy_weight(legacy_e, legacy_floor, band)[ys, xs]
            if legacy_sumw[band] is None:
                legacy_sumw[band] = np.array(weight, dtype=np.float64, copy=True)
                legacy_sumw2[band] = np.asarray(weight, dtype=np.float64) ** 2
            else:
                legacy_sumw[band] += weight
                legacy_sumw2[band] += weight * weight
        del planes, g1, g2, luma, decision, v_a, decision_pyr, va_pyr, linear_pyr, variance_pyr
        gc.collect()

    band_rows = []
    for band in range(R.BANDS):
        e = np.stack(energies[band], axis=0)
        f = np.stack(floors[band], axis=0)
        sw = legacy_sumw[band]
        sw2 = legacy_sumw2[band]
        assert sw is not None and sw2 is not None
        with np.errstate(divide="ignore", invalid="ignore"):
            legacy_neff = sw * sw / sw2
        legacy_neff[sw <= 0] = float(len(raws))
        masks = {label: label_pyramids[label][band] for label in labels}
        candidate = candidate_neff_means(e, f, R.FROZEN_NU_EFF[band], masks)
        row = {"band": band, "shape": list(e.shape[1:]), "rois": {}}
        for label, mask in masks.items():
            legacy_mean = _weighted_mean(legacy_neff, mask)
            ratios = (np.asarray(candidate[label]) / legacy_mean).tolist()
            row["rois"][label] = {
                "legacy_mean_neff": legacy_mean,
                "candidate_mean_neff": candidate[label],
                "ratio": ratios,
                "width_error": [abs(v - 1.0) for v in ratios],
            }
        band_rows.append(row)
        energies[band].clear()
        floors[band].clear()
        del e, f, legacy_neff
        gc.collect()

    result = {
        "capture": name,
        "frames": len(raws),
        "bands": band_rows,
        "iso_values": sorted(set(isos)),
        "frame_beta": beta_records,
        "seconds": time.perf_counter() - start_time,
    }
    R.write_json(R.RESULTS / f"width-{name}.json", result)
    return result


def width_survivors(width_results: dict[str, dict]) -> tuple[list[float], list[dict]]:
    survivors: list[float] = []
    summary: list[dict] = []
    for grid_index, k in enumerate(R.K_GRID):
        failures = []
        worst = 0.0
        predicates = 0
        for capture, result in width_results.items():
            for band in result["bands"]:
                for roi, values in band["rois"].items():
                    predicates += 1
                    error = float(values["width_error"][grid_index])
                    worst = max(worst, error)
                    if error > WIDTH_BAR + 1e-12:
                        failures.append(
                            {
                                "capture": capture,
                                "band": band["band"],
                                "roi": roi,
                                "ratio": values["ratio"][grid_index],
                                "error": error,
                            }
                        )
        if predicates != len(R.CAPTURES) * R.BANDS * 2:
            raise RuntimeError(f"k={k:.2f}: expected 42 width predicates, found {predicates}")
        passed = not failures
        if passed:
            survivors.append(k)
        summary.append(
            {"k": k, "pass": passed, "predicates": predicates, "worst_error": worst, "failures": failures}
        )
    return survivors, summary


def render_capture(
    name: str,
    config: dict,
    calibration: dict,
    k_values: Sequence[float],
) -> tuple[dict[float, tuple[np.ndarray, ...]], tuple[np.ndarray, ...], dict]:
    """Decode once, then render legacy and every requested candidate k."""
    start_time = time.perf_counter()
    meta, transforms = R.parse_warpmap(Path(config["transform"]))
    raws = R.ordered_raws(config)
    e_levels: list[list[np.ndarray]] = [[] for _ in range(R.BANDS)]
    f_levels: list[list[np.ndarray]] = [[] for _ in range(R.BANDS)]
    plane_levels: list[list[list[np.ndarray]]] = [
        [[] for _ in range(R.BANDS + 1)] for _ in range(4)
    ]
    legacy_levels: list[list[np.ndarray]] = [[] for _ in range(R.BANDS)]
    lows = [np.full((R.WORK_SIZE, R.WORK_SIZE), np.inf, dtype=np.float32) for _ in range(4)]
    highs = [np.full((R.WORK_SIZE, R.WORK_SIZE), -np.inf, dtype=np.float32) for _ in range(4)]

    for index, (path, transform) in enumerate(zip(raws, transforms, strict=True)):
        print(f"{name}: render pass frame {index + 1}/{len(raws)}", flush=True)
        planes, decode = R.prepared_crop(path, transform, config["score_origin"], meta["plane"])
        for plane_index, plane in enumerate(planes):
            np.minimum(lows[plane_index], plane, out=lows[plane_index])
            np.maximum(highs[plane_index], plane, out=highs[plane_index])
        luma = 0.5 * (planes[1] + planes[2])
        a, b0 = R.noise_coefficients(decode["iso"])
        decision_pyr = R.laplacian_pyramid(R.anscombe(luma, a, b0), R.BANDS)
        va_pyr = R.gaussian_pyramid(R.anscombe_variance(luma, a, b0), R.BANDS)
        luma_pyr = R.laplacian_pyramid(luma, R.BANDS)
        variance_pyr = R.gaussian_pyramid(a * luma + b0, R.BANDS)
        pyramids = [R.laplacian_pyramid(plane, R.BANDS) for plane in planes]
        frame_beta = R.beta_for_frame(calibration, name, index)
        for band in range(R.BANDS):
            e = R.smooth5(decision_pyr[band] * decision_pyr[band])
            f = (frame_beta[band] * va_pyr[band]).astype(np.float32)
            if not np.all(np.isfinite(f) & (f > 0)):
                raise RuntimeError(f"{name} frame {index} band {band}: invalid F")
            e_levels[band].append(e)
            f_levels[band].append(f)
            le = R.smooth5(luma_pyr[band] * luma_pyr[band])
            lf = LEGACY_GATE * frame_beta[band] * variance_pyr[band]
            legacy_levels[band].append(legacy_weight(le, lf, band).astype(np.float32))
            for plane_index in range(4):
                plane_levels[plane_index][band].append(pyramids[plane_index][band])
        for plane_index in range(4):
            plane_levels[plane_index][-1].append(pyramids[plane_index][-1])
        del planes, pyramids, luma, decision_pyr, va_pyr, luma_pyr, variance_pyr
        gc.collect()

    candidate_pyramids = {float(k): [None] * (R.BANDS + 1) for k in k_values}
    legacy_pyramid: list[np.ndarray | None] = [None] * (R.BANDS + 1)
    for band in range(R.BANDS):
        print(f"{name}: merging band {band}", flush=True)
        e = np.stack(e_levels[band], axis=0).astype(np.float64)
        f = np.stack(f_levels[band], axis=0).astype(np.float64)
        coefficients = [
            np.stack(plane_levels[plane_index][band], axis=0).astype(np.float64)
            for plane_index in range(4)
        ]
        lw = np.stack(legacy_levels[band], axis=0).astype(np.float64)
        lden = np.sum(lw, axis=0)
        fallback = lden <= 0
        legacy_bands = []
        for cfa in coefficients:
            numerator = np.sum(lw * cfa, axis=0)
            merged = np.empty_like(lden)
            merged[~fallback] = numerator[~fallback] / lden[~fallback]
            merged[fallback] = np.mean(cfa[:, fallback], axis=0)
            legacy_bands.append(merged.astype(np.float32))
        legacy_pyramid[band] = tuple(legacy_bands)

        winner = np.argmax(e, axis=0)
        yy, xx = np.indices(winner.shape)
        ew = e[winner, yy, xx]
        fw = f[winner, yy, xx]
        qw = np.maximum(ew - fw, 0.0)
        sigw = (2.0 * fw * fw + 4.0 * fw * qw) / R.FROZEN_NU_EFF[band]
        q = np.maximum(e - f, 0.0)
        sig = (2.0 * f * f + 4.0 * f * q) / R.FROZEN_NU_EFF[band]
        threshold = (ew[None, :] - e) / np.sqrt(sigw[None, :] + sig)
        threshold[winner, yy, xx] = 0.0
        below = qw <= 0
        for k in k_values:
            admitted = threshold <= float(k) + 1e-12
            weights = np.where(admitted, 1.0 / f, 0.0)
            weights[:, below] = 1.0
            den = np.sum(weights, axis=0)
            if np.any(~np.isfinite(den) | (den <= 0)):
                raise RuntimeError(f"{name} k={k} band={band}: candidate sum_w invalid")
            candidate_pyramids[float(k)][band] = tuple(
                (np.sum(weights * cfa, axis=0) / den).astype(np.float32) for cfa in coefficients
            )
        e_levels[band].clear()
        f_levels[band].clear()
        for plane_index in range(4):
            plane_levels[plane_index][band].clear()
        legacy_levels[band].clear()
        del e, f, coefficients, lw, threshold, sig, weights
        gc.collect()

    bases = tuple(
        np.mean(np.stack(plane_levels[plane_index][-1], axis=0).astype(np.float64), axis=0).astype(np.float32)
        for plane_index in range(4)
    )
    legacy_pyramid[-1] = bases
    for k in k_values:
        candidate_pyramids[float(k)][-1] = bases

    def finish(level_tuples: Sequence[tuple[np.ndarray, ...] | None]) -> tuple[np.ndarray, ...]:
        if any(level is None for level in level_tuples):
            raise RuntimeError("incomplete reconstruction pyramid")
        ys, xs = score_slice(0)
        outputs = []
        for plane_index in range(4):
            levels = [level[plane_index] for level in level_tuples if level is not None]
            reconstructed = np.clip(R.collapse_pyramid(levels), lows[plane_index], highs[plane_index])
            outputs.append(reconstructed[ys, xs].copy())
        return tuple(outputs)

    legacy = finish(legacy_pyramid)
    candidates = {k: finish(levels) for k, levels in candidate_pyramids.items()}
    provenance = {
        "frames": len(raws),
        "seconds": time.perf_counter() - start_time,
        "hull": "separate aligned-input level-0 clamp for R/G1/G2/B",
        "cfa_planes": ["R", "G1", "G2", "B"],
        "linear_base": "arithmetic mean",
    }
    del e_levels, f_levels, plane_levels, legacy_levels, candidate_pyramids, legacy_pyramid
    gc.collect()
    return candidates, legacy, provenance


def capture_metrics(
    capture: str,
    config: dict,
    candidates: dict[float, tuple[np.ndarray, ...]],
    legacy: tuple[np.ndarray, ...],
) -> dict:
    if len(legacy) != 4 or any(len(value) != 4 for value in candidates.values()):
        raise RuntimeError(f"{capture}: metrics require reconstructed R/G1/G2/B")
    legacy_detail = R.metric_values(legacy[1], legacy[2], config["detail_tiles"], "detail")
    legacy_flat = R.metric_values(legacy[1], legacy[2], config["flat_tiles"], "flat")
    capture_index = list(R.CAPTURES).index(capture)
    seed = R.BOOTSTRAP_SEED + 1009 * capture_index
    out = {}
    for k, planes in candidates.items():
        candidate_detail = R.metric_values(planes[1], planes[2], config["detail_tiles"], "detail")
        candidate_flat = R.metric_values(planes[1], planes[2], config["flat_tiles"], "flat")
        detail = R.bootstrap_ratio(
            candidate_detail,
            legacy_detail,
            "detail",
            seed=seed,
            replicates=R.BOOTSTRAP_REPLICATES,
        )
        flat = R.bootstrap_ratio(
            candidate_flat,
            legacy_flat,
            "flat",
            seed=seed,
            replicates=R.BOOTSTRAP_REPLICATES,
        )
        out[str(f"{k:.2f}")] = {
            "detail": detail,
            "flat": flat,
            "pass_detail": detail["lower95"] >= DETAIL_BAR,
            "pass_flat": flat["upper95"] <= FLAT_BAR,
        }
    return out


def contiguous_ranges(values: Sequence[float]) -> list[list[float]]:
    if not values:
        return []
    groups = [[values[0], values[0]]]
    for value in values[1:]:
        if abs(value - groups[-1][1] - 0.05) <= 1e-12:
            groups[-1][1] = value
        else:
            groups.append([value, value])
    return groups


def run_self_test() -> int:
    def fake_result(lo: int, hi: int) -> dict:
        errors = [0.0 if lo <= i <= hi else 0.06 for i in range(len(R.K_GRID))]
        ratios = [1.0 + value for value in errors]
        return {
            "bands": [
                {
                    "band": band,
                    "rois": {
                        roi: {"width_error": list(errors), "ratio": list(ratios)}
                        for roi in ("detail", "flat")
                    },
                }
                for band in range(R.BANDS)
            ]
        }

    common = {
        "flat-on-ruler": fake_result(20, 40),
        "coffee-bubbles": fake_result(30, 50),
        "113MSDCF": fake_result(35, 45),
    }
    survivors, rows = width_survivors(common)
    if survivors[0] != R.K_GRID[35] or survivors[-1] != R.K_GRID[40]:
        raise RuntimeError(f"global-intersection self-test failed: {survivors}")
    disjoint = {
        "flat-on-ruler": fake_result(0, 20),
        "coffee-bubbles": fake_result(30, 50),
        "113MSDCF": fake_result(60, 80),
    }
    none, _ = width_survivors(disjoint)
    if none or any(row["predicates"] != 42 for row in rows):
        raise RuntimeError("NO_COMMON_K/predicate-count self-test failed")
    print("measure self-test: null=GREEN planted-disjoint-captures=RED")
    return 0


def run_gate() -> int:
    started = time.perf_counter()
    manifest, commission, calibration = validate_sealed_inputs()
    width_results = {}
    for name, config in R.CAPTURES.items():
        width_results[name] = analyze_capture_width(name, config, calibration)
    survivors, width_grid = width_survivors(width_results)
    print(f"global width survivors: {survivors}", flush=True)

    metrics: dict[str, dict] = {}
    render_provenance = {}
    if survivors:
        for name, config in R.CAPTURES.items():
            candidates, legacy, provenance = render_capture(name, config, calibration, survivors)
            metrics[name] = capture_metrics(name, config, candidates, legacy)
            render_provenance[name] = provenance
            del candidates, legacy
            gc.collect()

    passing = []
    for k in survivors:
        key = f"{k:.2f}"
        if all(metrics[name][key]["pass_detail"] and metrics[name][key]["pass_flat"] for name in R.CAPTURES):
            passing.append(k)
    selected = min(passing) if passing else None
    verdict = f"COMMON_K={selected:.2f}" if selected is not None else "NO_COMMON_K"
    table = []
    if selected is not None:
        report_key = f"{selected:.2f}"
        grid_index = R.K_GRID.index(selected)
        for name, config in R.CAPTURES.items():
            width_ok = all(
                band["rois"][roi]["width_error"][grid_index] <= WIDTH_BAR + 1e-12
                for band in width_results[name]["bands"]
                for roi in band["rois"]
            )
            row_metrics = metrics[name][report_key]
            table.append(
                {
                    "capture": name,
                    "frames": config["frames"],
                    "k": selected,
                    "width_pass": width_ok,
                    "detail_lower95": row_metrics["detail"]["lower95"],
                    "flat_upper95": row_metrics["flat"]["upper95"],
                    "pass": bool(width_ok and row_metrics["pass_detail"] and row_metrics["pass_flat"]),
                }
            )
    payload = {
        "schema": R.SCHEMA,
        "epoch": R.EPOCH,
        "design_sha": R.DESIGN_SHA256,
        "verdict": verdict,
        "selected_k": selected,
        "width_survivors": survivors,
        "passing_k": passing,
        "passing_ranges": contiguous_ranges(passing),
        "bars": {"width": WIDTH_BAR, "detail_lower95": DETAIL_BAR, "flat_upper95": FLAT_BAR},
        "table": table,
        "width_grid": width_grid,
        "width_result_files": {name: f"width-{name}.json" for name in R.CAPTURES},
        "metrics": metrics,
        "render_provenance": render_provenance,
        "sealed": {
            "manifest_sha256": R.sha256(R.MANIFEST_PATH),
            "preregistration_sha256": R.sha256(R.PREREG_PATH),
            "reference_sha256": R.sha256(Path(R.__file__).resolve()),
            "measure_sha256": R.sha256(Path(__file__).resolve()),
            "commissioning_sha256": R.sha256(R.COMMISSION_PATH),
            "commissioning_status": commission["status"],
        },
        "frequency_license": {
            "scored_output_cycles_per_pixel": list(R.FREQ_OUTPUT),
            "maximum": R.FREQ_OUTPUT[1],
            "status": "LICENSED_LE_0.25",
        },
        "seconds": time.perf_counter() - started,
    }
    R.write_json(GATE_RESULT, payload)
    print(verdict)
    for row in table:
        state = "PASS" if row["pass"] else "FAIL"
        print(
            f"{row['capture']:15s} n={row['frames']:3d} k={row['k']:.2f} "
            f"detail lower95={row['detail_lower95']:.6f} "
            f"flat upper95={row['flat_upper95']:.6f} {state}"
        )
    print(f"results: {GATE_RESULT}")
    return 0 if selected is not None else NEGATIVE_EXIT


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--gate", action="store_true")
    group.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run_gate() if args.gate else run_self_test()
    except Exception as exc:
        print(f"measure.py: ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
