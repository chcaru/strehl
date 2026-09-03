"""Run the preregistered M-PHASE0-XSPEC capture measurement."""

from __future__ import annotations

from collections import defaultdict
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
REPO = ROOT.parent.parent
sys.path.insert(0, str(HERE))

import xspec_lib as X  # noqa: E402


STACKS = {
    "bee-1-cpl": {
        "root": Path(r"D:\personal\macro\bee-1-cpl"),
        "expected_frames": 299,
        "iso": 100,
        "aperture": 5.6,
    },
    "wrapped-text-1": {
        "root": Path(r"D:\personal\macro\wrapped-text-1"),
        "expected_frames": 130,
        "iso": 100,
        "aperture": 5.6,
    },
}
REPEAT_ROOT = Path(
    r"D:\personal\macro\requests\12-bee-iso-var-no-bracket-32-repeat-diff-light"
)
REPEAT_CENTRES = (
    (1200, 1200),
    (1200, 3514),
    (1200, 5828),
    (3488, 1200),
    (3488, 3514),
    (3488, 5828),
)
BOOTSTRAP_DRAWS = 10_000
INVERSION_BOOTSTRAP_DRAWS = 300


def dump_json(path: Path, payload) -> None:
    def clean(value):
        if isinstance(value, dict):
            return {str(k): clean(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [clean(v) for v in value]
        if isinstance(value, np.generic):
            return clean(value.item())
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(clean(payload), fh, indent=2)
        fh.write("\n")


def git_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        check=True,
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    return proc.stdout.strip()


def directory_fingerprint(root: Path) -> dict:
    files = [p for p in root.iterdir() if p.is_file()]
    stats = [p.stat() for p in files]
    return {
        "root": str(root),
        "file_count_all": len(files),
        "bytes_all": int(sum(s.st_size for s in stats)),
        "latest_mtime_ns": int(max((s.st_mtime_ns for s in stats), default=0)),
    }


def raw_files(root: Path) -> list[Path]:
    return sorted(root.glob("*.ARW"), key=lambda p: p.name.lower())


def exiftool_path() -> str:
    found = shutil.which("exiftool")
    if found:
        return found
    fallback = Path(r"C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe")
    if fallback.exists():
        return str(fallback)
    raise FileNotFoundError("exiftool is required for the ISO-100 repeat split")


def iso100_repeat_paths() -> tuple[list[Path], dict]:
    args = [
        exiftool_path(),
        "-json",
        "-n",
        "-ext",
        "ARW",
        "-ISO",
        "-DateTimeOriginal",
        "-FileName",
        "-Directory",
        str(REPEAT_ROOT),
    ]
    proc = subprocess.run(
        args,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"exiftool exited {proc.returncode}: {proc.stderr}")
    rows = json.loads(proc.stdout)
    selected = sorted(
        [row for row in rows if int(row.get("ISO", -1)) == 100],
        key=lambda row: (row.get("DateTimeOriginal", ""), row["FileName"]),
    )
    if len(selected) != 64:
        raise ValueError(f"expected 64 ISO-100 repeats, found {len(selected)}")
    paths = [Path(row["SourceFile"]) for row in selected]
    return paths, {
        "command": args,
        "all_records": len(rows),
        "iso100_records": len(selected),
        "first": selected[0],
        "last": selected[-1],
    }


def calibrate_phase_floor() -> dict:
    paths, exif = iso100_repeat_paths()
    print(f"phase-floor capture: loading {len(paths)} ISO-100 repeats", flush=True)
    patches = np.empty(
        (len(paths), len(REPEAT_CENTRES), X.PATCH, X.PATCH),
        dtype=np.float32,
    )
    loader_meta = None
    for i, path in enumerate(paths):
        active, meta = X.load_active(path)
        if loader_meta is None:
            loader_meta = meta
        elif meta != loader_meta:
            raise ValueError(f"repeat RAW layout changed at {path}")
        for roi, (row, col) in enumerate(REPEAT_CENTRES):
            patches[i, roi] = X.extract_gq(active, row, col)
        if (i + 1) % 16 == 0:
            print(f"  repeat decode {i+1}/{len(paths)}", flush=True)

    payload = {
        "root": str(REPEAT_ROOT),
        "paths": [str(p) for p in paths],
        "split": {"bright": [0, 32], "warm": [32, 64]},
        "centres": [list(x) for x in REPEAT_CENTRES],
        "exif": exif,
        "loader": loader_meta,
        "grids": {},
    }
    for n in X.WELCH_GRIDS:
        records = {"bright": [], "warm": []}
        for light, base in (("bright", 0), ("warm", 32)):
            for pair in range(16):
                ia = base + 2 * pair
                ib = ia + 1
                for roi in range(len(REPEAT_CENTRES)):
                    try:
                        bundle = X.cross_bundle(patches[ia, roi], patches[ib, roi], n)
                        fit = X.fit_phase_shift(bundle)
                        phase = X.phase_field_and_floor(
                            bundle, (fit["dx"], fit["dy"])
                        )
                        records[light].append(
                            {
                                "pair": pair,
                                "roi": roi,
                                "files": [paths[ia].name, paths[ib].name],
                                "observed_rms_rad": phase["observed_rms_rad"],
                                "nominal_floor_rad": phase["nominal_floor_rad"],
                                "ratio_nominal": phase["observed_rms_rad"]
                                / max(
                                    phase["nominal_floor_rad"],
                                    np.finfo(float).tiny,
                                ),
                                "median_coherence": phase["median_coherence"],
                                "bins": phase["bins"],
                                "shift": [fit["dx"], fit["dy"]],
                            }
                        )
                    except Exception as exc:
                        records[light].append(
                            {
                                "pair": pair,
                                "roi": roi,
                                "files": [paths[ia].name, paths[ib].name],
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                        )
        bright = [row for row in records["bright"] if "error" not in row]
        warm = [row for row in records["warm"] if "error" not in row]
        q = float(np.median([row["ratio_nominal"] for row in bright]))
        holdout = np.asarray(
            [row["ratio_nominal"] / q for row in warm], dtype=np.float64
        )
        commissioned = bool(
            len(bright) >= 60
            and len(warm) >= 60
            and 0.75 <= float(np.median(holdout)) <= 1.33
            and float(np.mean((holdout >= 0.5) & (holdout <= 2.0))) >= 0.80
        )
        payload["grids"][str(n)] = {
            "q": q,
            "bright_accepted": len(bright),
            "warm_accepted": len(warm),
            "warm_median_observed_over_predicted": float(np.median(holdout)),
            "warm_ci95_observed_over_predicted": [
                float(np.percentile(holdout, 2.5)),
                float(np.percentile(holdout, 97.5)),
            ],
            "warm_within_factor_two_fraction": float(
                np.mean((holdout >= 0.5) & (holdout <= 2.0))
            ),
            "commissioned": commissioned,
            "records": records,
        }
        print(
            f"  grid {n}: q={q:.4f}, warm obs/pred={np.median(holdout):.4f}, "
            f"within2={np.mean((holdout>=0.5)&(holdout<=2.0)):.3f}, "
            f"{'PASS' if commissioned else 'FAIL'}",
            flush=True,
        )
    return payload


def scan_stack(name: str, spec: dict, centres: list[dict]) -> dict:
    files = raw_files(spec["root"])
    if len(files) != spec["expected_frames"]:
        raise ValueError(
            f"{name}: expected {spec['expected_frames']} ARWs, found {len(files)}"
        )
    k = len(files)
    p = len(centres)
    election = np.empty((k, p), dtype=np.float64)
    low = np.empty((k, p), dtype=np.float64)
    noise = np.empty((k, p), dtype=np.float64)
    levels = np.empty((k, p), dtype=np.float64)
    loader_meta = None
    t0 = time.time()
    print(f"{name}: focus scan {k} frames x {p} candidates", flush=True)
    for i, path in enumerate(files):
        active, meta = X.load_active(path)
        if loader_meta is None:
            loader_meta = meta
        elif meta != loader_meta:
            raise ValueError(f"{name}: RAW layout changed at {path}")
        election[i], low[i], noise[i], levels[i] = X.focus_scores(active, centres)
        if (i + 1) % 20 == 0 or i + 1 == k:
            print(f"  {name} focus {i+1}/{k}", flush=True)
    selection = X.select_tiles(election, low, noise, centres)
    path = OUT / f"focus-scan-{name}.npz"
    np.savez_compressed(
        path,
        election_signal=election,
        low_power=low,
        noise=noise,
        levels=levels,
        centres=np.asarray(
            [[c["grid_row"], c["grid_col"], c["row"], c["col"]] for c in centres],
            dtype=np.int32,
        ),
        frames=np.asarray([f.name for f in files]),
        peak_indices=selection["peak_indices"],
        low_peak_indices=selection["low_peak_indices"],
        occlusion_all=selection["occlusion_all"],
        placebo_all=selection["placebo_all"],
    )
    print(
        f"  {name}: eligible {selection['eligible_count']}/{p}, "
        f"selected {len(selection['selected'])}, {time.time()-t0:.1f}s",
        flush=True,
    )
    return {
        "name": name,
        "root": spec["root"],
        "files": files,
        "loader": loader_meta,
        "selection": selection,
        "focus_scan": path,
    }


def collect_selected_patches(scan: dict) -> dict[int, dict[int, np.ndarray]]:
    selected = scan["selection"]["selected"]
    need: dict[int, list[dict]] = defaultdict(list)
    for tile in selected:
        for frame in range(tile["peak"] - 5, tile["peak"] + 6):
            need[frame].append(tile)
    patches: dict[int, dict[int, np.ndarray]] = {
        tile["tile_id"]: {} for tile in selected
    }
    frames = scan["files"]
    print(
        f"{scan['name']}: extracting selected patches from {len(need)} unique frames",
        flush=True,
    )
    for done, frame in enumerate(sorted(need), start=1):
        active, _ = X.load_active(frames[frame])
        tiles = need[frame]
        batch = X.extract_gq_batch(active, tiles)
        for tile, patch in zip(tiles, batch):
            patches[tile["tile_id"]][frame] = np.array(
                patch, dtype=np.float32, copy=True
            )
        if done % 20 == 0 or done == len(need):
            print(f"  {scan['name']} extract {done}/{len(need)}", flush=True)
    return patches


def compact_phase(phase: dict) -> dict:
    return {
        key: phase[key]
        for key in (
            "observed_rms_rad",
            "nominal_floor_rad",
            "bins",
            "median_coherence",
        )
    }


def analyse_stack(scan: dict, floor_calibration: dict) -> dict:
    patches = collect_selected_patches(scan)
    selected = scan["selection"]["selected"]
    result = {"name": scan["name"], "grids": {}}
    for n in X.WELCH_GRIDS:
        q = float(floor_calibration["grids"][str(n)]["q"])
        odd_records = []
        reg_records = []
        inversion_records = []
        errors = []
        print(f"{scan['name']}: analysing Fourier grid {n}", flush=True)
        for tile_index, tile in enumerate(selected):
            peak = tile["peak"]
            tile_patches = patches[tile["tile_id"]]
            cache = {}
            coords = None
            for frame in range(peak - 5, peak + 6):
                fft, block_rc = X.block_ffts(tile_patches[frame], n)
                cache[frame] = fft
                if coords is None:
                    coords = block_rc
                elif coords != block_rc:
                    raise AssertionError("cached Welch coordinates changed")
            ref_fft = cache[peak]
            ref_patch = tile_patches[peak]

            for d in range(1, 6):
                # Odd phase is formed directly across the symmetric pair.
                odd_bundle = X.cross_bundle_from_ffts(
                    cache[peak + d], cache[peak - d], coords, n
                )
                try:
                    odd_fit = X.fit_phase_shift(odd_bundle)
                    phase = X.phase_field_and_floor(
                        odd_bundle, (odd_fit["dx"], odd_fit["dy"])
                    )
                    floor = q * phase["nominal_floor_rad"]
                    observed = phase["observed_rms_rad"]
                    odd_records.append(
                        {
                            "tile_id": tile["tile_id"],
                            "d": d,
                            "row": tile["row"],
                            "col": tile["col"],
                            "peak": peak,
                            "observed_rms_rad": observed,
                            "nominal_floor_rad": phase["nominal_floor_rad"],
                            "calibrated_floor_rad": floor,
                            "observed_over_floor": observed
                            / max(floor, np.finfo(float).tiny),
                            "excess_rms_rad": math.sqrt(
                                max(observed * observed - floor * floor, 0.0)
                            ),
                            "bins": phase["bins"],
                            "median_coherence": phase["median_coherence"],
                            "shift": [odd_fit["dx"], odd_fit["dy"]],
                        }
                    )
                except Exception as exc:
                    errors.append(
                        {
                            "kind": "odd",
                            "tile_id": tile["tile_id"],
                            "d": d,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )

                for side in (-1, 1):
                    frame = peak + side * d
                    bundle = X.cross_bundle_from_ffts(
                        cache[frame], ref_fft, coords, n
                    )
                    try:
                        split = X.split_registration(
                            tile_patches[frame],
                            ref_patch,
                            n,
                            bundle=bundle,
                        )
                        fit = split["phase_full"]
                        reg_records.append(
                            {
                                "tile_id": tile["tile_id"],
                                "d": d,
                                "side": side,
                                "row": tile["row"],
                                "col": tile["col"],
                                "peak": peak,
                                "phase_precision_sensor_px": split[
                                    "phase_precision_sensor_px"
                                ],
                                "spatial_precision_sensor_px": split[
                                    "spatial_precision_sensor_px"
                                ],
                                "shift": [fit["dx"], fit["dy"]],
                                "median_coherence": fit["median_coherence"],
                                "bins": fit["bins"],
                                "spatial_edge_hit": any(
                                    x["edge_hit"] for x in split["spatial_halves"]
                                ),
                            }
                        )
                    except Exception as exc:
                        errors.append(
                            {
                                "kind": "registration",
                                "tile_id": tile["tile_id"],
                                "d": d,
                                "side": side,
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                        )
                        continue

                    for band_index, band in enumerate(X.INVERSION_BANDS):
                        try:
                            inv = X.band_correlation(
                                bundle,
                                (fit["dx"], fit["dy"]),
                                band,
                            )
                            eligible = bool(
                                inv["bins"] >= 12
                                and inv["median_coherence"] >= 0.20
                            )
                            if eligible and inv["rho"] <= -0.10:
                                inv = X.band_correlation(
                                    bundle,
                                    (fit["dx"], fit["dy"]),
                                    band,
                                    bootstrap=INVERSION_BOOTSTRAP_DRAWS,
                                    seed=(
                                        1_000_000 * n
                                        + 10_000 * tile["tile_id"]
                                        + 100 * d
                                        + 10 * (side + 1)
                                        + band_index
                                    ),
                                )
                            inverted = bool(
                                eligible
                                and inv["rho"] <= -0.20
                                and math.isfinite(inv["ci95"][1])
                                and inv["ci95"][1] < 0.0
                            )
                            inversion_records.append(
                                {
                                    "tile_id": tile["tile_id"],
                                    "d": d,
                                    "side": side,
                                    "band_index": band_index,
                                    "band": list(band),
                                    "rho": inv["rho"],
                                    "ci95": inv["ci95"],
                                    "bins": inv["bins"],
                                    "median_coherence": inv["median_coherence"],
                                    "eligible": eligible,
                                    "inverted": inverted,
                                    "occlusion": tile["occlusion"],
                                    "placebo_occlusion": tile[
                                        "placebo_occlusion"
                                    ],
                                }
                            )
                        except Exception as exc:
                            errors.append(
                                {
                                    "kind": "inversion",
                                    "tile_id": tile["tile_id"],
                                    "d": d,
                                    "side": side,
                                    "band_index": band_index,
                                    "error": f"{type(exc).__name__}: {exc}",
                                }
                            )
            if (tile_index + 1) % 20 == 0 or tile_index + 1 == len(selected):
                print(
                    f"  {scan['name']} grid {n}: tile "
                    f"{tile_index+1}/{len(selected)}",
                    flush=True,
                )
        result["grids"][str(n)] = {
            "odd": odd_records,
            "registration": reg_records,
            "inversion": inversion_records,
            "errors": errors,
        }
    return result


def median_ci(records: list[dict], key: str, seed: int) -> dict:
    point, ci = X.cluster_bootstrap(
        records,
        lambda rows: np.median([row[key] for row in rows]),
        draws=BOOTSTRAP_DRAWS,
        seed=seed,
    )
    return {"median": point, "ci95": ci}


def ratio_ci(records: list[dict], numerator: str, denominator: str, seed: int) -> dict:
    point, ci = X.cluster_bootstrap(
        records,
        lambda rows: np.median([row[numerator] for row in rows])
        / max(
            float(np.median([row[denominator] for row in rows])),
            np.finfo(float).tiny,
        ),
        draws=BOOTSTRAP_DRAWS,
        seed=seed,
    )
    return {"ratio_of_medians": point, "ci95": ci}


def field_annuli(records: list[dict]) -> list[dict]:
    half_diag = math.hypot(X.ACTIVE_SHAPE[0] / 2.0, X.ACTIVE_SHAPE[1] / 2.0)
    edges = (0.0, math.sqrt(1.0 / 3.0), math.sqrt(2.0 / 3.0), float("inf"))
    names = ("inner", "middle", "outer")
    out = []
    for i, name in enumerate(names):
        rows = []
        for row in records:
            radius = math.hypot(
                row["row"] - X.ACTIVE_SHAPE[0] / 2.0,
                row["col"] - X.ACTIVE_SHAPE[1] / 2.0,
            ) / half_diag
            if edges[i] <= radius < edges[i + 1]:
                rows.append(row)
        out.append(
            {
                "name": name,
                "radius_fraction": [edges[i], edges[i + 1]],
                "records": len(rows),
                "tiles": len({row["tile_id"] for row in rows}),
                "median_observed_over_floor": float(
                    np.median([row["observed_over_floor"] for row in rows])
                )
                if rows
                else float("nan"),
                "median_excess_rms_rad": float(
                    np.median([row["excess_rms_rad"] for row in rows])
                )
                if rows
                else float("nan"),
            }
        )
    return out


def summarize_stack_grid(records: dict, seed: int) -> dict:
    odd = records["odd"]
    reg = [
        row
        for row in records["registration"]
        if not row["spatial_edge_hit"]
        and math.isfinite(row["phase_precision_sensor_px"])
        and math.isfinite(row["spatial_precision_sensor_px"])
    ]
    odd_ratio = median_ci(odd, "observed_over_floor", seed)
    odd_excess = median_ci(odd, "excess_rms_rad", seed + 1)
    phase_precision = median_ci(reg, "phase_precision_sensor_px", seed + 2)
    spatial_precision = median_ci(reg, "spatial_precision_sensor_px", seed + 3)
    precision_ratio = ratio_ci(
        reg,
        "phase_precision_sensor_px",
        "spatial_precision_sensor_px",
        seed + 4,
    )
    odd_pass = bool(
        odd_ratio["median"] >= 2.0 and odd_ratio["ci95"][0] >= 1.5
    )
    registration_pass = bool(
        phase_precision["ci95"][1] < 0.100
        and precision_ratio["ci95"][1] < 1.0
    )
    return {
        "odd_records": len(odd),
        "odd_tiles": len({row["tile_id"] for row in odd}),
        "odd_observed_over_floor": odd_ratio,
        "odd_excess_rms_rad": odd_excess,
        "odd_pass": odd_pass,
        "field_annuli": field_annuli(odd),
        "registration_records_all": len(records["registration"]),
        "registration_records_accepted": len(reg),
        "registration_phase_precision_sensor_px": phase_precision,
        "registration_spatial_precision_sensor_px": spatial_precision,
        "registration_phase_over_spatial": precision_ratio,
        "registration_pass": registration_pass,
        "errors": len(records["errors"]),
    }


def inversion_tile_rows(
    stack_records: dict,
    selected: list[dict],
) -> list[dict]:
    by_tile: dict[int, list[dict]] = defaultdict(list)
    for row in stack_records["inversion"]:
        by_tile[row["tile_id"]].append(row)
    out = []
    for tile in selected:
        rows = by_tile[tile["tile_id"]]
        out.append(
            {
                "key": f"{tile['tile_id']}",
                "eligible": any(row["eligible"] for row in rows),
                "inverted": any(row["inverted"] for row in rows),
                "occlusion": tile["occlusion"],
                "placebo_occlusion": tile["placebo_occlusion"],
            }
        )
    return out


def inversion_summary(tile_rows: list[dict], seed: int) -> dict:
    occ = [x for x in tile_rows if x["eligible"] and x["occlusion"]]
    placebo = [
        x for x in tile_rows if x["eligible"] and x["placebo_occlusion"]
    ]
    occ_inv = sum(x["inverted"] for x in occ)
    placebo_inv = sum(x["inverted"] for x in placebo)
    p_occ = occ_inv / len(occ) if occ else float("nan")
    p_placebo = placebo_inv / len(placebo) if placebo else float("nan")
    point_rr = (
        p_occ / p_placebo
        if p_placebo > 0
        else (float("inf") if p_occ > 0 else float("nan"))
    )
    rng = np.random.default_rng(seed)
    rr = np.empty(BOOTSTRAP_DRAWS, dtype=np.float64)
    for i in range(BOOTSTRAP_DRAWS):
        sample = [
            tile_rows[j]
            for j in rng.integers(0, len(tile_rows), len(tile_rows))
        ]
        so = [x for x in sample if x["eligible"] and x["occlusion"]]
        sp = [
            x
            for x in sample
            if x["eligible"] and x["placebo_occlusion"]
        ]
        po = sum(x["inverted"] for x in so) / len(so) if so else 0.0
        pp = sum(x["inverted"] for x in sp) / len(sp) if sp else 0.0
        rr[i] = po / pp if pp > 0 else (float("inf") if po > 0 else 0.0)
    rr_ci = [
        float(np.percentile(rr, 2.5)),
        float(np.percentile(rr, 97.5)),
    ]
    wilson = X.wilson_interval(occ_inv, len(occ))
    adequate = len(occ) >= 20
    passed = bool(
        adequate
        and occ_inv >= 5
        and wilson[0] > 0.01
        and rr_ci[0] > 2.0
    )
    status = "PASS" if passed else ("FAIL" if adequate else "INDETERMINATE")
    return {
        "status": status,
        "eligible_occlusion_tiles": len(occ),
        "inverted_occlusion_tiles": int(occ_inv),
        "occlusion_fraction": p_occ,
        "occlusion_wilson95": wilson,
        "eligible_placebo_tiles": len(placebo),
        "inverted_placebo_tiles": int(placebo_inv),
        "placebo_fraction": p_placebo,
        "risk_ratio": point_rr,
        "risk_ratio_ci95": rr_ci,
        "eligible_tiles_all": sum(x["eligible"] for x in tile_rows),
        "inverted_tiles_all": sum(
            x["eligible"] and x["inverted"] for x in tile_rows
        ),
    }


def classify_grid(
    stack_summaries: dict,
    inversion: dict,
    floor_ok: bool,
    tile_ok: bool,
) -> str:
    if not floor_ok or not tile_ok:
        return "NOT ROBUST"
    odd_passes = sum(x["odd_pass"] for x in stack_summaries.values())
    registration_pass = all(
        x["registration_pass"] for x in stack_summaries.values()
    )
    if odd_passes == 2:
        return "SURVIVE"
    if (
        odd_passes == 1
        or registration_pass
        or inversion["status"] == "PASS"
        or inversion["status"] == "INDETERMINATE"
    ):
        return "NARROWED"
    return "KILL"


def summarize(
    calibration: dict,
    scans: dict,
    measurements: dict,
) -> dict:
    summary = {"grids": {}}
    for n in X.WELCH_GRIDS:
        key = str(n)
        stack_summaries = {
            name: summarize_stack_grid(
                measurements[name]["grids"][key],
                seed=20260902 + n * 100 + i * 10,
            )
            for i, name in enumerate(STACKS)
        }
        tile_rows = []
        for name in STACKS:
            rows = inversion_tile_rows(
                measurements[name]["grids"][key],
                scans[name]["selection"]["selected"],
            )
            for row in rows:
                row["key"] = f"{name}:{row['key']}"
            tile_rows.extend(rows)
        inv = inversion_summary(tile_rows, seed=20270000 + n)
        floor_ok = bool(calibration["grids"][key]["commissioned"])
        tile_ok = all(
            len(scans[name]["selection"]["selected"]) >= 160 for name in STACKS
        )
        verdict = classify_grid(stack_summaries, inv, floor_ok, tile_ok)
        summary["grids"][key] = {
            "floor_commissioned": floor_ok,
            "tile_population_ok": tile_ok,
            "stacks": stack_summaries,
            "inversion": inv,
            "verdict": verdict,
            "deciding_odd_lower95": min(
                row["odd_observed_over_floor"]["ci95"][0]
                for row in stack_summaries.values()
            ),
        }
    grid_verdicts = [summary["grids"][str(n)]["verdict"] for n in X.WELCH_GRIDS]
    summary["grid_verdicts"] = dict(zip((str(n) for n in X.WELCH_GRIDS), grid_verdicts))
    summary["verdict"] = (
        grid_verdicts[0]
        if len(set(grid_verdicts)) == 1
        else "NOT ROBUST"
    )
    summary["primary_deciding_odd_lower95"] = summary["grids"]["64"][
        "deciding_odd_lower95"
    ]
    return summary


def inventory(scans: dict, calibration: dict, before: dict, after: dict) -> dict:
    stacks = {}
    for name, scan in scans.items():
        files = scan["files"]
        selected = scan["selection"]["selected"]
        stacks[name] = {
            "root": str(scan["root"]),
            "raw_frames": len(files),
            "first_file": files[0].name,
            "last_file": files[-1].name,
            "first_sha256": X.file_sha256(files[0]),
            "last_sha256": X.file_sha256(files[-1]),
            "loader": scan["loader"],
            "candidate_tiles": scan["selection"]["candidate_count"],
            "eligible_tiles": scan["selection"]["eligible_count"],
            "selected_tiles": len(selected),
            "selected": selected,
            "focus_scan": str(scan["focus_scan"].relative_to(ROOT)),
        }
    return {
        "measurement_git_sha": git_sha(),
        "python": sys.version,
        "numpy": np.__version__,
        "frequency_grids": list(X.WELCH_GRIDS),
        "active_shape_rawpy": list(X.ACTIVE_SHAPE),
        "stacks": stacks,
        "repeat_root": str(REPEAT_ROOT),
        "repeat_iso100_frames": len(calibration["paths"]),
        "source_tree_before": before,
        "source_tree_after": after,
        "source_tree_unchanged": before == after,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    commission_path = OUT / "commission.json"
    commission = json.load(open(commission_path, encoding="utf-8"))
    if commission.get("status") != "GREEN":
        raise RuntimeError("commission.json is not GREEN; refusing outcome run")

    before = {
        name: directory_fingerprint(spec["root"]) for name, spec in STACKS.items()
    }
    before["repeat"] = directory_fingerprint(REPEAT_ROOT)

    calibration = calibrate_phase_floor()
    dump_json(OUT / "calibration.json", calibration)

    centres = X.candidate_centres()
    scans = {
        name: scan_stack(name, spec, centres) for name, spec in STACKS.items()
    }
    measurements = {
        name: analyse_stack(scans[name], calibration) for name in STACKS
    }
    for name, result in measurements.items():
        dump_json(OUT / f"records-{name}.json", result)

    after = {
        name: directory_fingerprint(spec["root"]) for name, spec in STACKS.items()
    }
    after["repeat"] = directory_fingerprint(REPEAT_ROOT)
    inv = inventory(scans, calibration, before, after)
    dump_json(OUT / "inventory.json", inv)
    if not inv["source_tree_unchanged"]:
        raise RuntimeError("capture tree fingerprint changed during the run")

    summary = summarize(calibration, scans, measurements)
    dump_json(OUT / "summary.json", summary)
    print("\nM-PHASE0-XSPEC summary", flush=True)
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

