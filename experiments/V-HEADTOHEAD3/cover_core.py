"""Author primitives for the preregistered V-HEADTOHEAD3 cover-mode arm."""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import tifffile
from scipy import ndimage

from ordinal import (
    _null_correlations,
    _scale_score,
    crop_centered,
    midrank_field,
    overlap_after_shift,
    pearson,
    phase_correction,
    rail_fraction,
    resized_rank,
    sampled_rank,
)


BANDS: tuple[tuple[float, float], ...] = (
    (0.02, 0.05),
    (0.05, 0.10),
    (0.10, 0.20),
    (0.20, 0.25),
)
BAND_NAMES = tuple(f"{lo:.2f}-{hi:.2f}" for lo, hi in BANDS)
UNLICENSED = "UNLICENSED_GT_0.25"
SIDE = 512
BORDER = 256
SEED = 20260903

EXE = Path(r"C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe")
SOURCE = Path(r"D:\personal\macro\113MSDCF")
SCALE_MASTER = Path(r"C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff")
PMAX = {
    "113": Path(r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"),
    "113-sharp": Path(r"D:\edited\macro\test\2026-05-07-21.31.06 ZS PMax.tif"),
}
HASHES = {
    EXE: "2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7",
    SCALE_MASTER: "4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F",
    PMAX["113"]: "B240FE4016E97EBB194497B2798A095C63C490C4FFF54018D48D34C7523719A0",
    PMAX["113-sharp"]: "4D490F71EF63DA33758A49BF583AD2166CD014A5401ED64EDB5E5EDCABB47A3E",
}
PROVENANCE_SCHEMA = "V-HEADTOHEAD3-COVER-RENDER-1"


def sha256(path: Path, chunk: int = 8 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            h.update(block)
    return h.hexdigest().upper()


def verify_hashes() -> None:
    for path, expected in HASHES.items():
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(f"hash changed: {path}: {actual} != {expected}")


def source_manifest(source: Path = SOURCE) -> dict:
    entries = []
    for path in sorted(
        (
            path
            for path in source.rglob("*")
            if path.is_file() and path.suffix.lower() in {".arw", ".xmp"}
        ),
        key=lambda value: value.relative_to(source).as_posix().lower(),
    ):
        entries.append(
            {
                "path": path.relative_to(source).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    counts = {
        suffix: sum(Path(row["path"]).suffix.lower() == suffix for row in entries)
        for suffix in (".arw", ".xmp")
    }
    canonical = json.dumps(
        entries,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "digest": hashlib.sha256(canonical).hexdigest().upper(),
        "counts": counts,
        "entries": entries,
    }


def render_argv(mode: str, output: Path) -> list[str]:
    argv = [
        str(EXE),
        "stack",
        str(SOURCE),
        "-o",
        str(output.resolve()),
        "--srgb",
    ]
    if mode == "crop":
        argv.extend(("--cover", "crop"))
    elif mode != "scale":
        raise ValueError(f"unknown cover mode {mode!r}")
    return argv


def parse_render_log(log: str, mode: str) -> dict:
    alignment = re.search(
        r"(\d+)\s+placed\s*/\s*(\d+)\s+refused",
        log,
        re.IGNORECASE,
    )
    if alignment is None:
        raise ValueError("render log has no placed/refused record")
    result: dict = {
        "mode": mode,
        "placed": int(alignment.group(1)),
        "refused": int(alignment.group(2)),
    }
    if mode == "scale":
        fit = re.search(
            r"field of view scaled to\s+([0-9.]+)",
            log,
            re.IGNORECASE,
        )
        if fit is None:
            raise ValueError("scale render log has no scale coverage banner")
        result["k"] = float(fit.group(1))
        result["unity_scale"] = False
    elif mode == "crop":
        fit = re.search(
            r"CROPPED to the region EVERY frame covers\s*--\s*"
            r"(\d+)\s*x\s*(\d+)\s*plane px.*?"
            r"at\s*\((\d+),\s*(\d+)\)\s*of\s*(\d+)\s*x\s*(\d+).*?"
            r"UNITY SCALE.*?\(k=([0-9.]+)\)",
            log,
            re.IGNORECASE | re.DOTALL,
        )
        if fit is None:
            raise ValueError("crop render log has no unity-scale crop banner")
        result.update(
            {
                "plane_dimensions": [int(fit.group(2)), int(fit.group(1))],
                "plane_origin": [int(fit.group(4)), int(fit.group(3))],
                "full_plane_dimensions": [
                    int(fit.group(6)),
                    int(fit.group(5)),
                ],
                "k": float(fit.group(7)),
                "unity_scale": True,
            }
        )
    else:
        raise ValueError(f"unknown cover mode {mode!r}")
    return result


def validate_provenance(
    payload: dict,
    crop_path: Path,
    scale_path: Path,
    pmax_path: Path,
    frozen_pmax_hash: str,
    frozen_scale_hash: str,
    frozen_subject: str,
    *,
    verify_live_source: bool = True,
) -> None:
    """Fail closed unless the treatment record binds every live input."""
    errors: list[str] = []
    if payload.get("schema") != PROVENANCE_SCHEMA:
        errors.append("schema")
    executable = payload.get("executable", {})
    if executable.get("path") != str(EXE):
        errors.append("executable path")
    if executable.get("sha256") != HASHES[EXE] or sha256(EXE) != HASHES[EXE]:
        errors.append("executable hash")
    source = payload.get("source", {})
    if source.get("path") != str(SOURCE):
        errors.append("source path")
    pre = source.get("pre", {})
    post = source.get("post", {})
    if (
        pre.get("digest") != post.get("digest")
        or pre.get("counts") != {".arw": 63, ".xmp": 63}
        or post.get("counts") != {".arw": 63, ".xmp": 63}
    ):
        errors.append("source pre/post manifest")
    if verify_live_source:
        live = source_manifest()
        if (
            live.get("digest") != pre.get("digest")
            or live.get("counts") != pre.get("counts")
        ):
            errors.append("live source manifest")
    comparators = payload.get("comparators", {})
    actual_pmax = sha256(pmax_path)
    if comparators.get(frozen_subject) != frozen_pmax_hash or actual_pmax != frozen_pmax_hash:
        errors.append("comparator hash")
    effective = payload.get("environment", {}).get("effective_strehl", {})
    if set(effective) != {"STREHL_CACHE_DIR"}:
        errors.append("inherited STREHL environment")
    cache = Path(str(effective.get("STREHL_CACHE_DIR", "")))
    try:
        cache.resolve().relative_to((Path(__file__).parent / "out").resolve())
    except (ValueError, OSError):
        errors.append("private cache path")
    if payload.get("environment", {}).get("rayon_num_threads") != 8:
        errors.append("render thread cap")
    if payload.get("environment", {}).get("numeric_thread_caps") != {
        "OMP_NUM_THREADS": 8,
        "OPENBLAS_NUM_THREADS": 8,
        "MKL_NUM_THREADS": 8,
        "NUMEXPR_NUM_THREADS": 8,
    }:
        errors.append("numerical thread caps")
    arms = payload.get("arms", {})
    for mode, live_path in (("scale", scale_path), ("crop", crop_path)):
        arm = arms.get(mode, {})
        if arm.get("path") != str(live_path.resolve()):
            errors.append(f"{mode} path")
        if arm.get("argv") != render_argv(mode, live_path):
            errors.append(f"{mode} argument vector")
        if arm.get("exit_code") != 0:
            errors.append(f"{mode} exit")
        if not live_path.is_file() or arm.get("sha256") != sha256(live_path):
            errors.append(f"{mode} live hash")
        try:
            facts = parse_render_log(str(arm.get("log", "")), mode)
        except ValueError:
            errors.append(f"{mode} log")
            continue
        if arm.get("facts") != facts:
            errors.append(f"{mode} parsed facts")
        if facts["placed"] != 63 or facts["refused"] != 0:
            errors.append(f"{mode} placement")
        if mode == "crop" and not facts["unity_scale"]:
            errors.append("crop not unity scale")
    scale = arms.get("scale", {})
    crop = arms.get("crop", {})
    if (
        frozen_scale_hash != HASHES[SCALE_MASTER]
        or scale.get("sha256") != frozen_scale_hash
        or sha256(scale_path) != HASHES[SCALE_MASTER]
    ):
        errors.append("scale byte identity")
    if scale.get("sha256") == crop.get("sha256"):
        errors.append("no crop intervention")
    if errors:
        raise ValueError("invalid render provenance: " + ", ".join(errors))


def green(path: Path) -> np.ndarray:
    image = tifffile.memmap(path)
    if image.ndim != 3 or image.shape[2] < 2:
        raise ValueError(f"expected HxWxRGB TIFF: {path}: {image.shape}")
    return image[:, :, 1]


def _window(shape: tuple[int, int]) -> np.ndarray:
    return np.hanning(shape[0])[:, None] * np.hanning(shape[1])[None, :]


def radius(shape: tuple[int, int]) -> np.ndarray:
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.fftfreq(shape[1])[None, :]
    return np.sqrt(fy * fy + fx * fx)


def rank_energy(
    image: np.ndarray,
    native_scale: float = 1.0,
) -> tuple[float | None, ...]:
    """Return Q in PMax-native scene bands.

    ``native_scale`` is arm pixels per one PMax pixel, so PMax-native edges
    divide by it in the arm raster.
    """
    if not native_scale > 0:
        raise ValueError("native scale must be positive")
    q = midrank_field(np.asarray(image))
    q -= np.mean(q)
    variance = float(np.mean(q * q))
    if not variance > 0:
        raise ValueError("constant rank crop")
    window = _window(q.shape)
    power = np.abs(np.fft.fft2(q * window)) ** 2
    frequency = radius(q.shape)
    denominator = q.size * float(np.sum(window * window)) * variance
    result: list[float | None] = []
    for lo, hi in BANDS:
        mapped_lo = lo / native_scale
        mapped_hi = hi / native_scale
        if mapped_hi > 0.25:
            result.append(None)
            continue
        mask = (frequency >= mapped_lo) & (frequency < mapped_hi)
        result.append(float(np.sum(power[mask], dtype=np.float64) / denominator))
    return tuple(result)


def raw_energy(image: np.ndarray) -> tuple[float, ...]:
    x = np.asarray(image, np.float64)
    x -= np.mean(x)
    variance = float(np.mean(x * x))
    window = _window(x.shape)
    power = np.abs(np.fft.fft2(x * window)) ** 2
    frequency = radius(x.shape)
    denominator = x.size * float(np.sum(window * window)) * variance
    return tuple(
        float(
            np.sum(
                power[(frequency >= lo) & (frequency < hi)],
                dtype=np.float64,
            )
            / denominator
        )
        for lo, hi in BANDS
    )


def fit_geometry(
    arm_path: Path,
    pmax_path: Path,
    coarse: Sequence[float] | None = None,
) -> dict:
    """Image-measured arm-pixels/PMax-pixel scale with 2e-4 refinement."""
    arm = sampled_rank(arm_path)
    pmax = sampled_rank(pmax_path)
    if coarse is None:
        coarse = np.arange(0.94, 1.0801, 0.005)
    coarse_rows: list[tuple[float, float]] = []
    coarse_offsets: list[np.ndarray] = []
    for scale in coarse:
        score, offsets = _scale_score(arm, pmax, float(scale))
        coarse_rows.append((float(scale), score))
        coarse_offsets.append(offsets)
    best = int(np.argmax([row[1] for row in coarse_rows]))
    coarse_interior = 0 < best < len(coarse_rows) - 1
    centre = coarse_rows[best][0]
    fine = np.arange(centre - 0.005, centre + 0.00501, 0.0002)
    fine_rows: list[tuple[float, float]] = []
    fine_offsets: list[np.ndarray] = []
    for scale in fine:
        score, offsets = _scale_score(arm, pmax, float(scale))
        fine_rows.append((float(scale), score))
        fine_offsets.append(offsets)
    selected = int(np.argmax([row[1] for row in fine_rows]))
    fine_interior = 0 < selected < len(fine_rows) - 1
    scale, score = fine_rows[selected]
    offsets = fine_offsets[selected]
    correction = np.median(offsets[:, :2], axis=0) * 8
    residual = (offsets[:, :2] - np.median(offsets[:, :2], axis=0)) * 8
    return {
        "scale": float(scale),
        "score": float(score),
        "coarse_interior": bool(coarse_interior),
        "fine_interior": bool(fine_interior),
        "global_correction": [
            float(correction[0]),
            float(correction[1]),
        ],
        "residual_rms": float(
            np.sqrt(np.mean(np.sum(residual * residual, axis=1)))
        ),
        "sample_shapes": [list(arm.shape), list(pmax.shape)],
        "coarse_sweep": coarse_rows,
        "fine_sweep": fine_rows,
    }


def map_site(
    arm: np.ndarray,
    pmax: np.ndarray,
    pmax_centre: Sequence[int],
    geometry: dict,
    *,
    require_border: bool = False,
) -> dict:
    """Hold a native PMax crop fixed and move the arm crop to its scene."""
    scale = float(geometry["scale"])
    gy, gx = map(float, geometry["global_correction"])
    py, px = map(float, pmax_centre)
    arm_side = int(round(SIDE * scale))
    base_y = scale * py + gy
    base_x = scale * px + gx
    p_crop = crop_centered(pmax, py, px, SIDE)
    a_initial = crop_centered(arm, base_y, base_x, arm_side)
    result = {
        "centre": [int(py), int(px)],
        "arm_side": arm_side,
        "base_arm_centre": [base_y, base_x],
        "reason": None,
    }
    if p_crop is None or a_initial is None:
        return {**result, "reason": "bounds"}
    ar0 = midrank_field(a_initial)
    pr = resized_rank(p_crop, ar0.shape)
    correction = phase_correction(ar0, pr, max_shift=64)
    ay = base_y + correction[0]
    ax = base_x + correction[1]
    a_crop = crop_centered(arm, ay, ax, arm_side)
    if a_crop is None:
        return {**result, "reason": "corrected-bounds"}
    ar = midrank_field(a_crop)
    pr = resized_rank(p_crop, ar.shape)
    corr_initial = pearson(ar0[::4, ::4], resized_rank(p_crop, ar0.shape)[::4, ::4])
    corr_fixed = pearson(ar[::4, ::4], pr[::4, ::4])
    null_gate = float(np.quantile(_null_correlations(ar, pr), 0.999))
    a_rail = rail_fraction(a_crop)
    p_rail = rail_fraction(p_crop)
    y0 = int(round(ay - arm_side / 2))
    x0 = int(round(ax - arm_side / 2))
    clearance = int(
        min(y0, x0, arm.shape[0] - (y0 + arm_side), arm.shape[1] - (x0 + arm_side))
    )
    reason = None
    if corr_fixed <= null_gate:
        reason = "registration-null"
    elif corr_fixed - corr_initial < 0.02:
        reason = "registration-gain"
    elif a_rail > 0.01 or p_rail > 0.01:
        reason = "rail"
    elif require_border and clearance < BORDER:
        reason = "border"
    return {
        **result,
        "reason": reason,
        "arm_centre": [ay, ax],
        "local_correction": [int(correction[0]), int(correction[1])],
        "phase_peak": float(correction[2]),
        "corr_initial": corr_initial,
        "corr_fixed": corr_fixed,
        "null_gate": null_gate,
        "arm_rail": a_rail,
        "pmax_rail": p_rail,
        "border_clearance": clearance,
        "arm_q": list(rank_energy(a_crop, scale)),
        "pmax_q": list(rank_energy(p_crop, 1.0)),
        "pmax_texture": float(sum(rank_energy(p_crop, 1.0)[:3])),
    }


def candidate_centres(shape: tuple[int, int]) -> list[tuple[int, int]]:
    h, w = shape
    return [
        (y, x)
        for y in range(512, h - 511, 512)
        for x in range(512, w - 511, 512)
    ]


def freeze_sites(scale_path: Path, pmax_path: Path) -> dict:
    geometry = fit_geometry(scale_path, pmax_path)
    if not geometry["coarse_interior"] or not geometry["fine_interior"]:
        raise RuntimeError("freeze geometry lacks an interior scale optimum")
    scale = green(scale_path)
    pmax = green(pmax_path)
    rows = [
        map_site(scale, pmax, centre, geometry)
        for centre in candidate_centres(pmax.shape)
    ]
    eligible = [row for row in rows if row["reason"] is None]
    sites: list[dict] = []
    for qy in (0, 1):
        for qx in (0, 1):
            quadrant = sorted(
                (
                    row
                    for row in eligible
                    if (row["centre"][0] >= pmax.shape[0] / 2) == bool(qy)
                    and (row["centre"][1] >= pmax.shape[1] / 2) == bool(qx)
                ),
                key=lambda row: (
                    row["pmax_texture"],
                    row["centre"][0],
                    row["centre"][1],
                ),
            )
            if len(quadrant) < 8:
                raise RuntimeError(f"only {len(quadrant)} eligible sites in quadrant")
            flat_n = max(2, len(quadrant) // 4)
            detail_n = max(4, math.ceil(len(quadrant) / 2))
            for row in quadrant[:flat_n]:
                sites.append({"centre": row["centre"], "label": "flat"})
            for row in quadrant[-detail_n:]:
                sites.append({"centre": row["centre"], "label": "detail"})
    sites.sort(key=lambda row: (row["label"], row["centre"][0], row["centre"][1]))
    return {
        "geometry": geometry,
        "candidate_count": len(rows),
        "eligible_count": len(eligible),
        "reasons": {
            reason: sum(1 for row in rows if (row["reason"] or "eligible") == reason)
            for reason in sorted({row["reason"] or "eligible" for row in rows})
        },
        "sites": sites,
        "site_digest": site_digest(sites),
    }


def site_digest(sites: Sequence[dict]) -> str:
    canonical = [
        {
            "centre": [int(row["centre"][0]), int(row["centre"][1])],
            "label": str(row["label"]),
        }
        for row in sites
    ]
    payload = json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def bootstrap(rows: Sequence[dict], seed: int = SEED) -> list[dict | str]:
    rng = np.random.default_rng(seed)
    result: list[dict | str] = []
    for band in range(len(BANDS)):
        if any(
            row["scale_q"][band] is None
            or row["crop_q"][band] is None
            or row["pmax_q"][band] is None
            for row in rows
        ):
            result.append(UNLICENSED)
            continue
        scale_logs = np.asarray(
            [
                math.log(row["scale_q"][band] / row["pmax_q"][band])
                for row in rows
            ]
        )
        crop_logs = np.asarray(
            [
                math.log(row["crop_q"][band] / row["pmax_q"][band])
                for row in rows
            ]
        )
        gain_logs = crop_logs - scale_logs
        draws = np.empty((10_000, 3), np.float64)
        for i in range(len(draws)):
            ix = rng.integers(0, len(rows), len(rows))
            draws[i] = (
                np.mean(scale_logs[ix]),
                np.mean(crop_logs[ix]),
                np.mean(gain_logs[ix]),
            )
        lo = np.exp(np.quantile(draws, 0.025, axis=0))
        hi = np.exp(np.quantile(draws, 0.975, axis=0))
        point = np.exp(
            [np.mean(scale_logs), np.mean(crop_logs), np.mean(gain_logs)]
        )
        result.append(
            {
                "scale_over_pmax": interval(point[0], lo[0], hi[0]),
                "crop_over_pmax": interval(point[1], lo[1], hi[1]),
                "crop_over_scale": interval(point[2], lo[2], hi[2]),
            }
        )
    return result


def competitive_class(low: float, high: float) -> str:
    if low > 1.05:
        return "LEADS"
    if high < 1.0 / 1.05:
        return "TRAILS"
    return "UNRESOLVED"


def interval(point: float, low: float, high: float) -> dict:
    return {
        "point": float(point),
        "ci_low": float(low),
        "ci_high": float(high),
        "class": competitive_class(float(low), float(high)),
    }


def cover_verdict(
    scale_class: str,
    crop_class: str,
    gain_low: float,
    gain_high: float,
    quadrants: Iterable[float],
    loo_reversal: bool,
) -> str:
    quadrants = list(quadrants)
    spatial = len(quadrants) == 4 and all(value > 1.0 for value in quadrants)
    if (
        scale_class == "TRAILS"
        and crop_class != "TRAILS"
        and gain_low > 1.02
        and spatial
        and not loo_reversal
    ):
        return "RECOVERED_BY_CROP"
    if (
        scale_class == "TRAILS"
        and crop_class == "TRAILS"
        and gain_low > 1.02
        and spatial
        and not loo_reversal
    ):
        return "PARTIAL_RECOVERY"
    if gain_low >= 0.98 and gain_high <= 1.02:
        return "COVER_NOT_CAUSE"
    if gain_high < 0.98:
        return "CROP_DEGRADES"
    return "UNRESOLVED"
