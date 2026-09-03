"""Core numerical instrument for M-PHASE0-VEIL2.

The functions here do not generate commissioning fixtures.  `commission.py`
owns the stimuli, including intentionally bad inputs.  Keeping stimulus and
checker on different code paths is necessary but not sufficient; the RED
plants are what demonstrate that each gate can actually fail.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import cv2
import numpy as np
import tifffile
from scipy.ndimage import convolve1d

KERNEL = np.asarray([1, 4, 6, 4, 1], dtype=np.float32) / 16.0
BOOT_SEED = 5_903_002
BOOT_REPS = 20_000


def reduce5(src: np.ndarray) -> np.ndarray:
    """Rust `pyramid::reduce`: nearest-border blur, then even decimation."""
    a = np.asarray(src, dtype=np.float32)
    if a.ndim != 2:
        raise ValueError(f"reduce5 needs 2-D input, got {a.shape}")
    h = convolve1d(a, KERNEL, axis=1, mode="nearest")
    v = convolve1d(h, KERNEL, axis=0, mode="nearest")
    return np.ascontiguousarray(v[::2, ::2], dtype=np.float32)


def expand5(src: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Rust `pyramid::expand`, including its explicit even/odd phases."""
    a = np.asarray(src, dtype=np.float32)
    if a.ndim != 2:
        raise ValueError(f"expand5 needs 2-D input, got {a.shape}")
    dh, dw = shape
    sh, sw = a.shape
    if (dh + 1) // 2 != sh or (dw + 1) // 2 != sw:
        raise ValueError(f"{a.shape} cannot expand to {shape}")

    x = np.arange(dw)
    c = x // 2
    left = np.clip(c - 1, 0, sw - 1)
    right = np.clip(c + 1, 0, sw - 1)
    tmp = np.empty((sh, dw), dtype=np.float32)
    even = (x & 1) == 0
    tmp[:, even] = (
        0.125 * a[:, left[even]]
        + 0.75 * a[:, c[even]]
        + 0.125 * a[:, right[even]]
    )
    tmp[:, ~even] = 0.5 * (a[:, c[~even]] + a[:, right[~even]])

    y = np.arange(dh)
    c = y // 2
    up = np.clip(c - 1, 0, sh - 1)
    down = np.clip(c + 1, 0, sh - 1)
    dst = np.empty((dh, dw), dtype=np.float32)
    even = (y & 1) == 0
    dst[even, :] = (
        0.125 * tmp[up[even], :]
        + 0.75 * tmp[c[even], :]
        + 0.125 * tmp[down[even], :]
    )
    dst[~even, :] = 0.5 * (tmp[c[~even], :] + tmp[down[~even], :])
    return dst


def pyramid_base(src: np.ndarray, bands: int = 7) -> np.ndarray:
    """Reconstruct only the coarsest Gaussian residual of a Rust pyramid."""
    sizes = [tuple(np.asarray(src).shape)]
    z = np.asarray(src, dtype=np.float32)
    for _ in range(bands):
        nxt = reduce5(z)
        if min(nxt.shape) < 8:
            break
        z = nxt
        sizes.append(tuple(z.shape))
    for shape in reversed(sizes[:-1]):
        z = expand5(z, shape)
    return z


def read_tiff(path: Path) -> np.ndarray:
    arr = tifffile.imread(str(path))
    if arr.dtype != np.uint16:
        raise ValueError(f"{path}: dtype {arr.dtype}, expected uint16")
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError(f"{path}: shape {arr.shape}, expected HxWx3")
    return arr


def channel_float(arr: np.ndarray, channel: int) -> np.ndarray:
    return np.asarray(arr[:, :, channel], dtype=np.float32)


def crop(a: np.ndarray, roi: Sequence[int]) -> np.ndarray:
    y0, y1, x0, x1 = (int(v) for v in roi)
    if not (0 <= y0 < y1 <= a.shape[0] and 0 <= x0 < x1 <= a.shape[1]):
        raise ValueError(f"ROI {tuple(roi)} outside {a.shape}")
    return a[y0:y1, x0:x1]


def paper_normalize(a: np.ndarray, paper_roi: Sequence[int]) -> tuple[np.ndarray, float]:
    anchor = float(np.median(crop(a, paper_roi)))
    if not math.isfinite(anchor) or anchor <= 0:
        raise ValueError(f"invalid paper anchor {anchor}")
    return np.asarray(a, dtype=np.float32) / anchor, anchor


def _f64_from_hex(s: str) -> float:
    return struct.unpack(">d", bytes.fromhex(s))[0]


@dataclass(frozen=True)
class Similarity:
    a_re: float
    a_im: float
    b_re: float
    b_im: float

    def fitted(self, k: float) -> "Similarity":
        # `fit_to_cover`: S_k.then(t), so a is multiplied and b is unchanged.
        return Similarity(k * self.a_re, k * self.a_im, self.b_re, self.b_im)


def parse_warpmap(path: Path) -> tuple[dict, dict[int, Similarity]]:
    meta: dict[str, object] = {}
    warps: dict[int, Similarity] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        p = line.split()
        if p[0] == "plane":
            w, h = (int(v) for v in p[1].split("x"))
            meta["plane"] = [h, w]
        elif p[0] == "frames":
            meta["frames"] = int(p[1])
        elif p[0] == "reference":
            meta["reference"] = int(p[1])
        elif p[0] == "resampler":
            meta["resampler"] = p[1]
        elif p[0].isdigit() and len(p) >= 7 and p[1] == "placed":
            i = int(p[0])
            warps[i] = Similarity(
                _f64_from_hex(p[2]),
                _f64_from_hex(p[3]),
                _f64_from_hex(p[4]),
                _f64_from_hex(p[5]),
            )
    if "plane" not in meta or not warps:
        raise ValueError(f"{path}: incomplete warpmap")
    return meta, warps


def remap_similarity(
    src: np.ndarray,
    t: Similarity,
    interpolation: int = cv2.INTER_CUBIC,
) -> np.ndarray:
    """Gather a frame using `Similarity::apply_at` (reference -> frame)."""
    h, w = src.shape[:2]
    yy, xx = np.indices((h, w), dtype=np.float32)
    cx, cy = np.float32(w * 0.5), np.float32(h * 0.5)
    xr, yr = xx - cx, yy - cy
    mx = t.a_re * xr - t.a_im * yr + t.b_re + cx
    my = t.a_im * xr + t.a_re * yr + t.b_im + cy
    if src.ndim == 2:
        border = 0.0
    else:
        border = (0.0,) * src.shape[2]
    return cv2.remap(
        src,
        mx,
        my,
        interpolation,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=border,
    )


def correlation(x: np.ndarray, y: np.ndarray) -> float:
    a = np.asarray(x, dtype=np.float64).ravel()
    b = np.asarray(y, dtype=np.float64).ravel()
    a -= a.mean()
    b -= b.mean()
    den = math.sqrt(float(a @ a) * float(b @ b))
    return float(a @ b / den) if den > 0 else float("nan")


def projection(subject: np.ndarray, reference: np.ndarray) -> float:
    s = np.asarray(subject, dtype=np.float64).ravel()
    r = np.asarray(reference, dtype=np.float64).ravel()
    s -= s.mean()
    r -= r.mean()
    den = float(r @ r)
    return float(r @ s / den) if den > 0 else float("nan")


def spatial_blocks(shape: tuple[int, int], block: int = 16) -> list[tuple[slice, slice]]:
    h, w = shape
    out = []
    for y in range(0, h, block):
        for x in range(0, w, block):
            out.append((slice(y, min(y + block, h)), slice(x, min(x + block, w))))
    return out


def _correlation_sufficient(
    x: np.ndarray,
    y: np.ndarray,
    blocks: Sequence[tuple[slice, slice]],
) -> np.ndarray:
    """Per-block sufficient statistics for exact concatenated correlation."""
    rows = []
    for s in blocks:
        a = np.asarray(x[s], dtype=np.float64).ravel()
        b = np.asarray(y[s], dtype=np.float64).ravel()
        rows.append(
            [
                a.size,
                a.sum(),
                b.sum(),
                a @ a,
                b @ b,
                a @ b,
            ]
        )
    return np.asarray(rows, dtype=np.float64)


def _correlation_from_sufficient(rows: np.ndarray) -> float:
    n, sx, sy, sxx, syy, sxy = np.asarray(rows, dtype=np.float64).sum(axis=0)
    if n <= 0:
        return float("nan")
    vx = sxx - sx * sx / n
    vy = syy - sy * sy / n
    cov = sxy - sx * sy / n
    den = math.sqrt(max(vx, 0.0) * max(vy, 0.0))
    return float(cov / den) if den > 0 else float("nan")


def classify_interval(lo: float, hi: float, replicated: bool = False) -> str:
    if lo >= 0.50 and replicated:
        return "SURVIVE"
    if lo > 0.25:
        return "NARROWED"
    if hi <= 0.25:
        return "KILL"
    return "NOT ROBUST"


def score_site(
    master: np.ndarray,
    foreground: Sequence[np.ndarray],
    background: Sequence[np.ndarray],
    roi: Sequence[int],
    *,
    bands: int = 7,
    reps: int = BOOT_REPS,
    seed: int = BOOT_SEED,
) -> dict:
    """Score one already registered and paper-normalized channel."""
    bm = pyramid_base(master, bands)
    bf = np.stack([pyramid_base(z, bands) for z in foreground])
    bb = np.stack([pyramid_base(z, bands) for z in background])
    hm = master - bm
    hf = np.stack([z - b for z, b in zip(foreground, bf)])
    hb = np.stack([z - b for z, b in zip(background, bb)])

    rm = crop(bm, roi)
    rf = np.stack([crop(z, roi) for z in bf])
    rb = np.stack([crop(z, roi) for z in bb])
    hmr = crop(hm, roi)
    hfr = np.median(np.stack([crop(z, roi) for z in hf]), axis=0)
    hbr = np.median(np.stack([crop(z, roi) for z in hb]), axis=0)

    fmed = np.median(rf, axis=0)
    bmed = np.median(rb, axis=0)
    means = {
        "master": float(rm.mean()),
        "foreground": float(fmed.mean()),
        "background": float(bmed.mean()),
    }
    den = means["foreground"] - means["background"]
    theta = (means["master"] - means["background"]) / den if den else float("nan")
    d_corr = correlation(hmr, hbr) - correlation(hmr, hfr)
    detail = {
        "corr_background": correlation(hmr, hbr),
        "corr_foreground": correlation(hmr, hfr),
        "corr_margin": d_corr,
        "projection_background": projection(hmr, hbr),
    }

    blocks = spatial_blocks(rm.shape, 16)
    bm_block = np.asarray([float(rm[s].mean()) for s in blocks])
    bf_block = np.asarray([[float(z[s].mean()) for s in blocks] for z in rf])
    bb_block = np.asarray([[float(z[s].mean()) for s in blocks] for z in rb])
    detail_b_stats = _correlation_sufficient(hmr, hbr, blocks)
    detail_f_stats = _correlation_sufficient(hmr, hfr, blocks)
    rng = np.random.default_rng(seed)
    theta_boot = np.empty(reps, dtype=np.float64)
    d_boot = np.empty(reps, dtype=np.float64)
    nblock = len(blocks)
    for i in range(reps):
        fi = rng.integers(0, len(foreground), len(foreground))
        bi = rng.integers(0, len(background), len(background))
        si = rng.integers(0, nblock, nblock)
        fm = np.median(bf_block[fi], axis=0)[si].mean()
        bg = np.median(bb_block[bi], axis=0)[si].mean()
        mm = bm_block[si].mean()
        theta_boot[i] = (mm - bg) / (fm - bg) if fm != bg else np.nan

        # Spatial cluster bootstrap for the detail gate. Frame uncertainty is
        # already represented in theta; using the frozen medians here keeps the
        # two effects identifiable.
        d_boot[i] = _correlation_from_sufficient(
            detail_b_stats[si]
        ) - _correlation_from_sufficient(detail_f_stats[si])

    finite = theta_boot[np.isfinite(theta_boot)]
    df = d_boot[np.isfinite(d_boot)]
    if len(finite) < reps * 0.99 or len(df) < reps * 0.99:
        raise ValueError("bootstrap produced too many non-finite replicates")
    return {
        "bands": bands,
        "roi": [int(v) for v in roi],
        "means": means,
        "denominator": float(den),
        "theta": float(theta),
        "theta_se": float(finite.std(ddof=1)),
        "theta_ci95": [float(v) for v in np.percentile(finite, [2.5, 97.5])],
        "detail": detail,
        "detail_margin_se": float(df.std(ddof=1)),
        "detail_margin_ci95": [float(v) for v in np.percentile(df, [2.5, 97.5])],
        "bootstrap": {"seed": seed, "reps": reps, "clusters": nblock},
    }


def paper_null_gate(
    master: np.ndarray,
    background: np.ndarray,
    roi: Sequence[int],
    bands: int = 7,
) -> dict:
    d = crop(pyramid_base(master, bands) - pyramid_base(background, bands), roi)
    med = float(np.median(d))
    spread = float(np.percentile(d, 95) - np.percentile(d, 5))
    return {
        "median": med,
        "p95_p05": spread,
        "pass": abs(med) <= 0.02 and spread <= 0.04,
    }


def tone_locality_gate(
    baseline: np.ndarray,
    candidate: np.ndarray,
    target_roi: Sequence[int],
    anchor_rois: Sequence[Sequence[int]],
) -> dict:
    delta = candidate - baseline
    observed = float(np.mean(crop(delta, target_roi)))
    target = abs(observed)
    anchors = [abs(float(np.mean(crop(delta, r)))) for r in anchor_rois]
    x = np.asarray(
        [float(np.mean(crop(baseline, r))) for r in anchor_rois],
        dtype=np.float64,
    )
    y = np.asarray(
        [float(np.mean(crop(candidate, r))) for r in anchor_rois],
        dtype=np.float64,
    )
    design = np.column_stack([x, np.ones(len(x), dtype=np.float64)])
    slope, intercept = np.linalg.lstsq(design, y, rcond=None)[0]
    target_baseline = float(np.mean(crop(baseline, target_roi)))
    predicted = float(slope * target_baseline + intercept - target_baseline)
    frac = abs(predicted) / max(target, 1e-12)
    return {
        "target_effect": target,
        "target_effect_signed": observed,
        "anchor_effects": anchors,
        "affine_slope": float(slope),
        "affine_intercept": float(intercept),
        "affine_predicted_target_effect": predicted,
        "affine_explained_fraction": frac,
        "max_anchor_fraction": max(anchors, default=float("inf"))
        / max(target, 1e-12),
        "pass": target > 0 and frac <= 0.25,
    }


def geometry_gate(shifts: Sequence[Sequence[float]]) -> dict:
    z = np.asarray(shifts, dtype=np.float64)
    if z.shape != (2, 2):
        raise ValueError("geometry gate requires two (dy,dx) shifts")
    disagreement = float(np.linalg.norm(z[0] - z[1]))
    return {"disagreement_px": disagreement, "pass": disagreement <= 0.75}


def detrended_wander(delta: np.ndarray) -> dict:
    """P95-P05 after removing exactly one fitted plane, never curvature."""
    a = np.asarray(delta, dtype=np.float64)
    yy, xx = np.indices(a.shape, dtype=np.float64)
    X = np.column_stack([np.ones(a.size), xx.ravel(), yy.ravel()])
    coef, *_ = np.linalg.lstsq(X, a.ravel(), rcond=None)
    resid = a.ravel() - X @ coef
    spread = float(np.percentile(resid, 95) - np.percentile(resid, 5))
    return {
        "p95_p05_dn": spread,
        "plane": [float(v) for v in coef],
        "pass": spread <= 100.0,
    }


def layer_truth_gate(
    *,
    distinct_contents_observed: bool,
    separated_frame_runs: bool,
    peak_count: int,
) -> dict:
    # Peak count is reported but deliberately not used: M63 showed why.
    ok = bool(distinct_contents_observed and separated_frame_runs)
    return {
        "distinct_contents_observed": bool(distinct_contents_observed),
        "separated_frame_runs": bool(separated_frame_runs),
        "peak_count_diagnostic_only": int(peak_count),
        "pass": ok,
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()
