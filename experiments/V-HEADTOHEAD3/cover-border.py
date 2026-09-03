"""Commission, render, and measure the 113 cover-border profile amendment."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Sequence

import numpy as np
import tifffile

import cover_core as cc


SCHEMA = "V-HEADTOHEAD3-COVER-BORDER-1"
RENDER_SCHEMA = "V-HEADTOHEAD3-COVER-BORDER-RENDER-1"
LABEL = "GEOMETRY_AND_BAND_DEPTH_NOT_RESOLUTION"
THREAD_CAP = 8
THRESHOLD = 0.001
DEEP_START = 768
PROFILE_EDGES = (
    0,
    2,
    4,
    8,
    16,
    32,
    64,
    96,
    128,
    160,
    192,
    256,
    320,
    384,
    448,
    512,
    640,
    768,
)
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SCALE7 = OUT / "113-cover-scale-control.tiff"
CROP7 = OUT / "113-cover-crop.tiff"
SCALE2 = OUT / "113-cover-scale-b2.tiff"
CROP2 = OUT / "113-cover-crop-b2.tiff"
BASE_PROVENANCE = OUT / "COVER-RENDER-PROVENANCE.json"
RENDER_PROVENANCE = OUT / "COVER-BORDER-RENDER-PROVENANCE.json"
CACHE = OUT / "cache"
WARP_MAP = CACHE / "113MSDCF-7f5a36c866189cc7.warpmap.txt"
EXPECTED = {
    "scale7": "4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F",
    "crop7": "5B5F863AB2602EA18DB995FEA6361D4AB86B8FF24ECBCB9D2A470E637091F18B",
    "warp_map": "A5DF650CCE1224A7B6F54B5570B0BC1E643F1728B030D2496BD2BC13E462623E",
    "source_manifest": "A6275BE83552AC1BE4E23381A42BF1024FB33C217A9529DCDCC018BB4992AC5D",
}
EXACT_K = 0.9808883167827137
EXACT_UPSAMPLE_PERCENT = 1.9484056329646338
EXPECTED_CROP_RECT = {
    "plane_dimensions": [2298, 3448],
    "plane_origin": [23, 34],
    "full_plane_dimensions": [2344, 3516],
}


def render_environment() -> dict[str, str]:
    env = dict(os.environ)
    for name in tuple(env):
        if name.upper().startswith("STREHL_"):
            del env[name]
    env["STREHL_CACHE_DIR"] = str(CACHE.resolve())
    env["RAYON_NUM_THREADS"] = str(THREAD_CAP)
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "BLIS_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "OMP_THREAD_LIMIT",
        "TBB_NUM_THREADS",
    ):
        env[name] = str(THREAD_CAP)
    return env


def render_argv(mode: str, output: Path) -> list[str]:
    argv = [
        str(cc.EXE),
        "stack",
        str(cc.SOURCE),
        "-o",
        str(output.resolve()),
        "--srgb",
        "--pyramid-bands",
        "2",
    ]
    if mode == "crop":
        argv.extend(("--cover", "crop"))
    elif mode != "scale":
        raise ValueError(f"unknown mode {mode!r}")
    return argv


def _render_one(mode: str, output: Path, env: dict[str, str]) -> dict:
    argv = render_argv(mode, output)
    run = subprocess.run(
        argv,
        cwd=str(HERE.parent.parent),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    log = run.stdout + ("\n" if run.stdout and run.stderr else "") + run.stderr
    if run.returncode != 0:
        raise RuntimeError(f"{mode} two-band render failed:\n{log}")
    if not output.is_file():
        raise RuntimeError(f"{mode} two-band render produced no file")
    facts = cc.parse_render_log(log, mode)
    shape = list(tifffile.memmap(output).shape)
    expected_shape = list(tifffile.memmap(SCALE7 if mode == "scale" else CROP7).shape)
    if shape != expected_shape:
        raise RuntimeError(f"{mode} two/seven-band shape mismatch")
    if facts["placed"] != 63 or facts["refused"] != 0:
        raise RuntimeError(f"{mode} placement count changed")
    if not math.isclose(float(facts["k"]), 0.9809, abs_tol=5e-5):
        raise RuntimeError(f"{mode} coverage k changed")
    if mode == "crop":
        for name, expected in EXPECTED_CROP_RECT.items():
            if facts.get(name) != expected:
                raise RuntimeError(f"crop {name} changed")
        if facts.get("unity_scale") is not True:
            raise RuntimeError("crop is not unity scale")
    return {
        "path": str(output.resolve()),
        "argv": argv,
        "exit_code": run.returncode,
        "sha256": cc.sha256(output),
        "shape": shape,
        "facts": facts,
        "log": log,
    }


def render() -> dict:
    cc.verify_hashes()
    if cc.sha256(SCALE7) != EXPECTED["scale7"]:
        raise RuntimeError("seven-band scale hash changed")
    if cc.sha256(CROP7) != EXPECTED["crop7"]:
        raise RuntimeError("seven-band crop hash changed")
    if cc.sha256(WARP_MAP) != EXPECTED["warp_map"]:
        raise RuntimeError("cached warp map changed")
    occupied = [path for path in (SCALE2, CROP2, RENDER_PROVENANCE) if path.exists()]
    if occupied:
        raise RuntimeError(f"refusing to overwrite outputs: {occupied}")
    base = json.loads(BASE_PROVENANCE.read_text(encoding="utf-8"))
    cc.validate_provenance(
        base,
        CROP7,
        SCALE7,
        cc.PMAX["113"],
        cc.HASHES[cc.PMAX["113"]],
        EXPECTED["scale7"],
        "113",
    )
    before = cc.source_manifest()
    if (
        before["digest"] != EXPECTED["source_manifest"]
        or before["counts"] != {".arw": 63, ".xmp": 63}
    ):
        raise RuntimeError("source manifest changed before two-band render")
    env = render_environment()
    effective = {
        name: value
        for name, value in env.items()
        if name.upper().startswith("STREHL_")
    }
    if effective != {"STREHL_CACHE_DIR": str(CACHE.resolve())}:
        raise RuntimeError(f"unexpected effective STREHL variables: {effective}")
    scale = _render_one("scale", SCALE2, env)
    crop = _render_one("crop", CROP2, env)
    after = cc.source_manifest()
    if after["digest"] != before["digest"] or after["counts"] != before["counts"]:
        raise RuntimeError("source bytes changed during two-band renders")
    if cc.sha256(WARP_MAP) != EXPECTED["warp_map"]:
        raise RuntimeError("cached warp map changed during render")
    payload = {
        "schema": RENDER_SCHEMA,
        "label": LABEL,
        "executable": {
            "path": str(cc.EXE),
            "sha256": cc.sha256(cc.EXE),
        },
        "source": {
            "path": str(cc.SOURCE),
            "manifest_sha256": before["digest"],
            "counts": before["counts"],
        },
        "warp_map": {
            "path": str(WARP_MAP.resolve()),
            "sha256": cc.sha256(WARP_MAP),
            "frames": 63,
            "placed": 63,
            "reference": 31,
            "k": EXACT_K,
            "upsample_percent": EXACT_UPSAMPLE_PERCENT,
        },
        "seven_band": {
            "scale": {
                "path": str(SCALE7.resolve()),
                "sha256": cc.sha256(SCALE7),
            },
            "crop": {
                "path": str(CROP7.resolve()),
                "sha256": cc.sha256(CROP7),
            },
        },
        "two_band": {"scale": scale, "crop": crop},
        "environment": {
            "effective_strehl": effective,
            "rayon_num_threads": int(env["RAYON_NUM_THREADS"]),
            "numeric_thread_cap": THREAD_CAP,
        },
    }
    RENDER_PROVENANCE.write_text(
        json.dumps(payload, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    return payload


def _inner_count(height: int, width: int, inset: int) -> int:
    return max(0, height - 2 * inset) * max(0, width - 2 * inset)


def _ring_sum(image: np.ndarray, lo: int, hi: int) -> float:
    height, width = image.shape
    if lo < 0 or hi <= lo:
        raise ValueError("invalid annulus")
    y0, y1 = lo, height - lo
    x0, x1 = lo, width - lo
    iy0, iy1 = min(hi, height - hi), max(hi, height - hi)
    ix0, ix1 = min(hi, width - hi), max(hi, width - hi)
    total = float(np.sum(image[y0:y1, x0:x1], dtype=np.float64))
    if iy1 <= iy0 or ix1 <= ix0:
        return total
    return total - float(
        np.sum(image[iy0:iy1, ix0:ix1], dtype=np.float64)
    )


def border_rows(
    bands7: np.ndarray,
    bands2: np.ndarray,
    threshold: float = THRESHOLD,
    deep_start: int = DEEP_START,
    edges: Sequence[int] = PROFILE_EDGES,
) -> tuple[list[dict], int | None, float]:
    a = np.asarray(bands7)
    b = np.asarray(bands2)
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError("border profile requires equal two-dimensional planes")
    if not math.isfinite(threshold) or threshold < 0.0:
        raise ValueError("invalid threshold")
    height, width = a.shape
    max_distance = (min(height, width) - 1) // 2
    if deep_start < 0 or deep_start > max_distance:
        raise ValueError("invalid deep start")
    deep_a = float(
        np.mean(
            a[deep_start : height - deep_start, deep_start : width - deep_start],
            dtype=np.float64,
        )
    )
    deep_b = float(
        np.mean(
            b[deep_start : height - deep_start, deep_start : width - deep_start],
            dtype=np.float64,
        )
    )
    if not deep_b > 0.0:
        raise ValueError("non-positive deep control mean")
    deep_ratio = deep_a / deep_b
    boundaries = sorted(
        {
            int(edge)
            for edge in edges
            if type(edge) is int and 0 <= edge <= max_distance
        }
    )
    if not boundaries or boundaries[0] != 0:
        raise ValueError("profile edges must begin at zero")
    rows = []
    for index, lo in enumerate(boundaries):
        hi = (
            boundaries[index + 1]
            if index + 1 < len(boundaries)
            else max_distance + 1
        )
        count = _inner_count(height, width, lo) - _inner_count(height, width, hi)
        if count <= 0:
            continue
        mean7 = _ring_sum(a, lo, hi) / count
        mean2 = _ring_sum(b, lo, hi) / count
        if not mean2 > 0.0:
            raise ValueError("non-positive annulus control mean")
        ratio = mean7 / mean2
        rows.append(
            {
                "lo": lo,
                "hi": hi,
                "samples": count,
                "mean_bands7": mean7,
                "mean_bands2": mean2,
                "ratio": ratio,
                "normalised_effect": ratio / deep_ratio - 1.0,
            }
        )
    safe = None
    for row in rows:
        candidate = int(row["lo"])
        if candidate < 8:
            continue
        tail = [entry for entry in rows if int(entry["lo"]) >= candidate]
        if tail and all(
            abs(float(entry["normalised_effect"])) <= threshold
            for entry in tail
        ):
            safe = candidate
            break
    return rows, safe, deep_ratio


def commission() -> dict:
    yy, xx = np.indices((96, 128))
    control = 0.8 * (10_000.0 + xx + 2.0 * yy)
    baseline = 1.1 * control
    distance = np.minimum.reduce(
        (
            yy,
            95 - yy,
            xx,
            127 - xx,
        )
    )
    planted = baseline.copy()
    planted[distance < 16] *= 1.02
    rows, safe, deep = border_rows(
        planted,
        control,
        deep_start=32,
    )
    outer = rows[0]
    oracle_rows = []
    oracle_edges = tuple(edge for edge in PROFILE_EDGES if edge <= 47)
    for index, lo in enumerate(oracle_edges):
        hi = oracle_edges[index + 1] if index + 1 < len(oracle_edges) else 48
        mask = (distance >= lo) & (distance < hi)
        oracle_rows.append(
            (
                lo,
                hi,
                int(np.count_nonzero(mask)),
                float(np.mean(planted[mask])),
                float(np.mean(control[mask])),
            )
        )
    annulus_oracle = all(
        row["lo"] == oracle[0]
        and row["hi"] == oracle[1]
        and row["samples"] == oracle[2]
        and math.isclose(row["mean_bands7"], oracle[3], abs_tol=1e-12)
        and math.isclose(row["mean_bands2"], oracle[4], abs_tol=1e-12)
        for row, oracle in zip(rows, oracle_rows)
    )
    improved = baseline.copy()
    improved[distance < 16] *= 1.0005
    _, improved_safe, _ = border_rows(
        improved,
        control,
        deep_start=32,
    )
    null_rows, null_safe, null_deep = border_rows(
        baseline,
        control,
        deep_start=32,
    )
    threshold_plant = baseline.copy()
    threshold_plant[distance < 16] *= 1.002
    _, threshold_safe, _ = border_rows(
        threshold_plant,
        control,
        deep_start=32,
    )
    _, loose_safe, _ = border_rows(
        threshold_plant,
        control,
        threshold=0.01,
        deep_start=32,
    )
    _, changed_edge_safe, _ = border_rows(
        planted,
        control,
        deep_start=32,
        edges=tuple(edge for edge in PROFILE_EDGES if edge != 16),
    )
    swapped_rows, _, _ = border_rows(
        control,
        planted,
        deep_start=32,
    )
    unnormalised_outer = outer["ratio"] - 1.0
    controls = {
        "annulus_external_oracle": annulus_oracle,
        "two_percent_outer_effect": math.isclose(
            outer["normalised_effect"],
            0.02,
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
        "two_percent_safe_inset": safe == 16,
        "improvement_safe_inset": improved_safe == 8,
        "untuned_null_safe_inset": null_safe == 8,
        "untuned_null_effect": all(
            abs(float(row["normalised_effect"])) <= 1e-12
            for row in null_rows
        ),
        "deep_ratio_external": math.isclose(deep, 1.1, abs_tol=1e-15),
        "null_deep_ratio_external": math.isclose(
            null_deep,
            1.1,
            abs_tol=1e-15,
        ),
        "threshold_plant": threshold_safe == 16,
    }
    mutants = {
        "swapped_bands": swapped_rows[0]["normalised_effect"] < 0.0,
        "deep_normalisation_omitted": not math.isclose(
            unnormalised_outer,
            0.02,
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
        "threshold_changed": loose_safe != threshold_safe,
        "annulus_edge_changed": changed_edge_safe != safe,
    }
    green = all(controls.values()) and all(mutants.values())
    return {
        "schema": SCHEMA + "-COMMISSION",
        "status": "GREEN" if green else "RED",
        "green": green,
        "controls": controls,
        "caught_red_mutants": mutants,
        "control_count": len(controls),
        "mutant_count": len(mutants),
        "readings": {
            "two_percent_safe_inset": safe,
            "improved_safe_inset": improved_safe,
            "null_safe_inset": null_safe,
            "threshold_plant_safe_inset": threshold_safe,
            "loose_threshold_safe_inset": loose_safe,
        },
    }


def validate_render_provenance(payload: dict) -> None:
    failures = []
    if payload.get("schema") != RENDER_SCHEMA:
        failures.append("schema")
    if payload.get("label") != LABEL:
        failures.append("label")
    if payload.get("executable", {}).get("sha256") != cc.HASHES[cc.EXE]:
        failures.append("executable")
    source = payload.get("source", {})
    if (
        source.get("manifest_sha256") != EXPECTED["source_manifest"]
        or source.get("counts") != {".arw": 63, ".xmp": 63}
    ):
        failures.append("source")
    warp = payload.get("warp_map", {})
    if (
        warp.get("sha256") != EXPECTED["warp_map"]
        or warp.get("frames") != 63
        or warp.get("placed") != 63
        or warp.get("reference") != 31
        or warp.get("k") != EXACT_K
        or warp.get("upsample_percent") != EXACT_UPSAMPLE_PERCENT
    ):
        failures.append("warp map")
    if payload.get("seven_band", {}).get("scale", {}).get("sha256") != EXPECTED[
        "scale7"
    ]:
        failures.append("scale7")
    if payload.get("seven_band", {}).get("crop", {}).get("sha256") != EXPECTED[
        "crop7"
    ]:
        failures.append("crop7")
    if payload.get("environment") != {
        "effective_strehl": {"STREHL_CACHE_DIR": str(CACHE.resolve())},
        "rayon_num_threads": THREAD_CAP,
        "numeric_thread_cap": THREAD_CAP,
    }:
        failures.append("environment")
    for mode, path in (("scale", SCALE2), ("crop", CROP2)):
        arm = payload.get("two_band", {}).get(mode, {})
        if (
            arm.get("path") != str(path.resolve())
            or arm.get("argv") != render_argv(mode, path)
            or arm.get("exit_code") != 0
            or arm.get("sha256") != cc.sha256(path)
        ):
            failures.append(f"{mode} two-band")
        try:
            facts = cc.parse_render_log(str(arm.get("log", "")), mode)
        except ValueError:
            failures.append(f"{mode} log")
        else:
            if arm.get("facts") != facts:
                failures.append(f"{mode} facts")
    if (
        cc.sha256(SCALE7) != EXPECTED["scale7"]
        or cc.sha256(CROP7) != EXPECTED["crop7"]
        or cc.sha256(WARP_MAP) != EXPECTED["warp_map"]
    ):
        failures.append("live frozen inputs")
    if failures:
        raise RuntimeError("render provenance failed: " + ", ".join(failures))


def _green(path: Path) -> np.ndarray:
    image = tifffile.memmap(path)
    if image.ndim != 3 or image.shape[2] < 2:
        raise ValueError(f"{path}: expected HxWxC TIFF")
    return image[:, :, 1]


def measure() -> dict:
    commissioned = commission()
    if not commissioned["green"]:
        raise RuntimeError("border instrument commission failed")
    payload = json.loads(RENDER_PROVENANCE.read_text(encoding="utf-8"))
    validate_render_provenance(payload)
    profiles = {}
    for mode, seven, two in (
        ("scale", SCALE7, SCALE2),
        ("crop", CROP7, CROP2),
    ):
        rows, safe, deep_ratio = border_rows(_green(seven), _green(two))
        profiles[mode] = {
            "safe_inset_px": safe,
            "deep_ratio": deep_ratio,
            "rows": rows,
        }
    specific = profiles["scale"]["safe_inset_px"] == 8
    crop_safe = profiles["crop"]["safe_inset_px"]
    rois_clear = (
        specific
        and crop_safe is not None
        and int(crop_safe) <= cc.BORDER
    )
    if not specific:
        disposition = "PROFILE_NOT_SPECIFIC_ON_113"
    elif crop_safe is None:
        disposition = "CROP_SAFE_INSET_UNBOUNDED"
    elif crop_safe <= cc.BORDER:
        disposition = "EXISTING_256PX_ROIS_CLEAR_PROFILE"
    else:
        disposition = "EXISTING_256PX_ROIS_NOT_CLEAR_PROFILE"
    return {
        "schema": SCHEMA,
        "status": "GREEN",
        "label": LABEL,
        "commission": {
            "controls_green": commissioned["control_count"],
            "plants_red": commissioned["mutant_count"],
        },
        "render_provenance": str(RENDER_PROVENANCE.resolve()),
        "frames": 63,
        "placed": 63,
        "refused": 0,
        "k": EXACT_K,
        "upsample_percent": EXACT_UPSAMPLE_PERCENT,
        "crop_rect_xywh": [34, 23, 3448, 2298],
        "profile": {
            "threshold": THRESHOLD,
            "deep_start_px": DEEP_START,
            "scale": profiles["scale"],
            "crop": profiles["crop"],
            "specific": specific,
        },
        "existing_roi_minimum_clearance_px": cc.BORDER,
        "existing_rois_clear_profile": rois_clear,
        "disposition": disposition,
        "resolution_verdict": "NOT_MEASURED_Q25_REFUSED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("commission", "render", "measure"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "commission":
        if args.output is not None:
            parser.error("commission accepts no output path")
        result = commission()
        code = 0 if result["green"] else 2
    elif args.command == "render":
        if args.output is not None:
            parser.error("render writes its frozen provenance path")
        result = render()
        code = 0
    else:
        result = measure()
        code = 0
    if args.output is not None:
        args.output.write_text(
            json.dumps(result, indent=2, allow_nan=False),
            encoding="utf-8",
        )
    print(
        "COVER_BORDER_JSON="
        + json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
