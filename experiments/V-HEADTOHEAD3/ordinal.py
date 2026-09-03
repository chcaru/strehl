"""Tone-invariant primitives for V-HEADTOHEAD3.

The measurement path operates on each arm's native pixels.  scipy.ndimage is
used only for geometry/registration, never for a reported spectrum.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import tifffile
from scipy import ndimage
from scipy.stats import rankdata


BANDS: tuple[tuple[float, float], ...] = (
    (0.02, 0.05),
    (0.05, 0.10),
    (0.10, 0.20),
    (0.20, 0.25),
    (0.25, 0.30),
    (0.30, 0.40),
)
BAND_NAMES: tuple[str, ...] = tuple(f"{lo:.2f}-{hi:.2f}" for lo, hi in BANDS)
SEED = 20260902
ROI_SIZE = 512
SAMPLE_STEP = 8


@dataclass(frozen=True)
class Pair:
    key: str
    strehl: Path
    comparator: Path
    label: str
    strehl_sha256: str
    comparator_sha256: str


PAIRS: dict[str, Pair] = {
    "113": Pair(
        "113",
        Path(r"C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff"),
        Path(r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"),
        "Zerene Stacker PMax",
        "4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F",
        "B240FE4016E97EBB194497B2798A095C63C490C4FFF54018D48D34C7523719A0",
    ),
    "113-sharp": Pair(
        "113-sharp",
        Path(r"C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff"),
        Path(r"D:\edited\macro\test\2026-05-07-21.31.06 ZS PMax.tif"),
        "Zerene Stacker PMax (Lightroom Sharpness 40, colour NR 25)",
        "4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F",
        "4D490F71EF63DA33758A49BF583AD2166CD014A5401ED64EDB5E5EDCABB47A3E",
    ),
    "cb": Pair(
        "cb",
        Path(r"C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff"),
        Path(r"C:\dev\macro\out\coffee-bean\stack.tif"),
        "focus-stack fork",
        "F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC",
        "8636C20D73CA0CB1F57DB89BF8553ABC166E0FBC517E5C62A07C74DEE509066E",
    ),
}


def sha256(path: Path, chunk: int = 8 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest().upper()


def green_memmap(path: Path) -> np.ndarray:
    a = tifffile.memmap(path)
    if a.ndim != 3 or a.shape[2] < 2:
        raise ValueError(f"{path}: expected HxWxC TIFF, got {a.shape}")
    return a[:, :, 1]


def midrank_field(a: np.ndarray) -> np.ndarray:
    """Average ranks, centred and scaled exactly as preregistered."""
    x = np.asarray(a)
    n = x.size
    if n < 2:
        raise ValueError("rank field needs at least two samples")
    r = rankdata(x.ravel(), method="average").reshape(x.shape)
    return (r - (n + 1.0) / 2.0) / n


def _spectral_shares(field: np.ndarray, band_scale: float = 1.0) -> np.ndarray:
    x = np.asarray(field, np.float64)
    if x.ndim != 2:
        raise ValueError("spectral field must be 2-D")
    wy = np.hanning(x.shape[0])
    wx = np.hanning(x.shape[1])
    z = (x - np.mean(x)) * wy[:, None] * wx[None, :]
    power = np.abs(np.fft.fft2(z)) ** 2
    fy = np.fft.fftfreq(x.shape[0])[:, None]
    fx = np.fft.fftfreq(x.shape[1])[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    values = []
    for lo, hi in BANDS:
        mask = (radius >= lo * band_scale) & (radius < hi * band_scale)
        values.append(float(np.sum(power[mask], dtype=np.float64)))
    values = np.asarray(values, np.float64)
    total = float(np.sum(values))
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("zero/non-finite admitted spectral power")
    return values / total


def ordinal_shares(a: np.ndarray, band_scale: float = 1.0) -> np.ndarray:
    return _spectral_shares(midrank_field(a), band_scale)


def raw_shares(a: np.ndarray, band_scale: float = 1.0) -> np.ndarray:
    x = np.asarray(a, np.float64)
    lo = float(np.min(x))
    hi = float(np.max(x))
    if not hi > lo:
        raise ValueError("raw field is constant")
    return _spectral_shares((x - lo) / (hi - lo), band_scale)


def tie_census(a: np.ndarray) -> tuple[int, float]:
    _, counts = np.unique(np.asarray(a), return_counts=True)
    return int(counts.size), float(np.max(counts) / np.asarray(a).size)


def rail_fraction(
    a: np.ndarray, rails: tuple[float, float] | None = None
) -> float:
    x = np.asarray(a)
    if rails is not None:
        return float(np.mean((x == rails[0]) | (x == rails[1])))
    if np.issubdtype(x.dtype, np.integer):
        info = np.iinfo(x.dtype)
        return float(np.mean((x == info.min) | (x == info.max)))
    # The focus-stack fork is a normalised floating TIFF.  Exact 0/1 are its
    # container rails; values outside this interval are not silently clipped.
    return float(np.mean((x == 0.0) | (x == 1.0)))


def phase_correction(
    reference: np.ndarray, moving: np.ndarray, max_shift: int | None = None
) -> tuple[int, int, float]:
    """Return the integer correction to apply to ``moving``.

    A moving array planted at displacement (+dy,+dx) returns (-dy,-dx).
    """
    a = np.asarray(reference, np.float64)
    b = np.asarray(moving, np.float64)
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError("phase correlation requires equal 2-D shapes")
    win = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    fa = np.fft.fft2((a - np.mean(a)) * win)
    fb = np.fft.fft2((b - np.mean(b)) * win)
    cross = fa * np.conj(fb)
    cross /= np.abs(cross) + np.finfo(np.float64).eps
    corr = np.fft.ifft2(cross).real
    if max_shift is not None:
        allowed_y = np.minimum(np.arange(a.shape[0]), a.shape[0] - np.arange(a.shape[0]))
        allowed_x = np.minimum(np.arange(a.shape[1]), a.shape[1] - np.arange(a.shape[1]))
        allowed = (allowed_y[:, None] <= max_shift) & (
            allowed_x[None, :] <= max_shift
        )
        corr = np.where(allowed, corr, -np.inf)
    iy, ix = np.unravel_index(np.argmax(corr), corr.shape)
    dy = int(iy - a.shape[0] if iy > a.shape[0] // 2 else iy)
    dx = int(ix - a.shape[1] if ix > a.shape[1] // 2 else ix)
    return dy, dx, float(corr[iy, ix])


def overlap_after_shift(
    reference: np.ndarray, moving: np.ndarray, correction: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray]:
    """Return equal interior views after applying a non-wrapping correction."""
    dy, dx = correction
    h, w = reference.shape
    ry0 = max(0, dy)
    ry1 = min(h, h + dy)
    rx0 = max(0, dx)
    rx1 = min(w, w + dx)
    my0 = max(0, -dy)
    my1 = min(h, h - dy)
    mx0 = max(0, -dx)
    mx1 = min(w, w - dx)
    return (
        np.asarray(reference)[ry0:ry1, rx0:rx1],
        np.asarray(moving)[my0:my1, mx0:mx1],
    )


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    x = np.asarray(a, np.float64).ravel()
    y = np.asarray(b, np.float64).ravel()
    x -= np.mean(x)
    y -= np.mean(y)
    den = math.sqrt(float(np.dot(x, x) * np.dot(y, y)))
    return float(np.dot(x, y) / den) if den > 0 else float("nan")


def resized_rank(a: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    r = midrank_field(a)
    zoom = (shape[0] / r.shape[0], shape[1] / r.shape[1])
    z = ndimage.zoom(r, zoom, order=1, mode="reflect", prefilter=False)
    if z.shape != shape:
        # scipy's shape rounding can differ by one across versions.
        out = np.empty(shape, np.float64)
        sy = min(shape[0], z.shape[0])
        sx = min(shape[1], z.shape[1])
        out[:sy, :sx] = z[:sy, :sx]
        if sy < shape[0]:
            out[sy:, :sx] = z[sy - 1, :sx]
        if sx < shape[1]:
            out[:, sx:] = out[:, sx - 1 : sx]
        z = out
    return z


def sampled_rank(path: Path, step: int = SAMPLE_STEP) -> np.ndarray:
    green = green_memmap(path)
    # Sample first, rank second: a monotone remap preserves these samples and
    # their order exactly.  Block means would not have that property.
    sample = np.asarray(green[::step, ::step], np.float64)
    return midrank_field(sample)


def _scale_score(
    strehl_rank: np.ndarray,
    comparator_rank: np.ndarray,
    scale: float,
    tile: int = 128,
    ntile: int = 6,
) -> tuple[float, np.ndarray]:
    moved = ndimage.zoom(
        comparator_rank, scale, order=1, mode="reflect", prefilter=False
    )
    max_y = min(strehl_rank.shape[0], moved.shape[0]) - tile
    max_x = min(strehl_rank.shape[1], moved.shape[1]) - tile
    if max_y <= tile or max_x <= tile:
        return float("-inf"), np.empty((0, 3))
    ys = np.linspace(tile // 2, max_y - tile // 2, ntile).astype(int)
    xs = np.linspace(tile // 2, max_x - tile // 2, ntile).astype(int)
    rows = []
    for y in ys:
        for x in xs:
            a = strehl_rank[y : y + tile, x : x + tile]
            b = moved[y : y + tile, x : x + tile]
            dy, dx, _ = phase_correction(a, b, max_shift=tile // 4)
            aa, bb = overlap_after_shift(a, b, (dy, dx))
            # Phase peak is jagged when zoom changes the raster size by one
            # pixel.  Score the aligned rank content instead; this remains
            # strictly monotone-invariant and has a real scale optimum.
            rows.append((dy, dx, pearson(aa, bb)))
    offsets = np.asarray(rows, np.float64)
    return float(np.median(offsets[:, 2])), offsets


def fit_geometry(
    strehl_path: Path,
    comparator_path: Path,
    coarse: Sequence[float] | None = None,
) -> dict:
    """Fit scale and global correction from monotone-invariant sampled ranks."""
    sr = sampled_rank(strehl_path)
    cr = sampled_rank(comparator_path)
    if coarse is None:
        coarse = np.arange(0.96, 1.081, 0.005)
    coarse_rows = []
    for scale in coarse:
        score, _ = _scale_score(sr, cr, float(scale))
        coarse_rows.append((float(scale), score))
    best_i = int(np.argmax([x[1] for x in coarse_rows]))
    coarse_interior = 0 < best_i < len(coarse_rows) - 1
    best_coarse = coarse_rows[best_i][0]
    fine_scales = np.arange(best_coarse - 0.006, best_coarse + 0.0061, 0.001)
    fine_rows = []
    fine_offsets = []
    for scale in fine_scales:
        score, offsets = _scale_score(sr, cr, float(scale))
        fine_rows.append((float(scale), score))
        fine_offsets.append(offsets)
    fine_i = int(np.argmax([x[1] for x in fine_rows]))
    fine_interior = 0 < fine_i < len(fine_rows) - 1
    scale, score = fine_rows[fine_i]
    offsets = fine_offsets[fine_i]
    correction = np.median(offsets[:, :2], axis=0) * SAMPLE_STEP
    residual = (offsets[:, :2] - np.median(offsets[:, :2], axis=0)) * SAMPLE_STEP
    rms = float(np.sqrt(np.mean(np.sum(residual * residual, axis=1))))
    return {
        "scale": float(scale),
        "score": float(score),
        "coarse_interior": bool(coarse_interior),
        "fine_interior": bool(fine_interior),
        "global_correction": [float(correction[0]), float(correction[1])],
        "residual_rms": rms,
        "coarse_sweep": coarse_rows,
        "fine_sweep": fine_rows,
        "sample_shapes": [list(sr.shape), list(cr.shape)],
    }


def crop_centered(a: np.ndarray, cy: float, cx: float, side: int) -> np.ndarray | None:
    y0 = int(round(cy - side / 2.0))
    x0 = int(round(cx - side / 2.0))
    if y0 < 0 or x0 < 0 or y0 + side > a.shape[0] or x0 + side > a.shape[1]:
        return None
    return np.asarray(a[y0 : y0 + side, x0 : x0 + side])


def _null_correlations(reference: np.ndarray, moving: np.ndarray) -> np.ndarray:
    a = reference[::4, ::4]
    b = moving[::4, ::4]
    rng = np.random.default_rng(0xC0FFEE)
    rows = []
    # Shifts are at least 64 full-resolution pixels on one axis.
    while len(rows) < 64:
        dy = int(rng.integers(16, a.shape[0] - 16))
        dx = int(rng.integers(16, a.shape[1] - 16))
        if rng.integers(2):
            dy = -dy
        if rng.integers(2):
            dx = -dx
        rows.append(pearson(a, np.roll(b, (dy, dx), axis=(0, 1))))
    return np.asarray(rows, np.float64)


def candidate_centres(shape: tuple[int, int]) -> list[tuple[int, int]]:
    h, w = shape
    return [
        (y, x)
        for y in range(512, h - 383, 512)
        for x in range(512, w - 383, 512)
    ]


def measure_roi(
    strehl_green: np.ndarray,
    comparator_green: np.ndarray,
    centre: tuple[int, int],
    geometry: dict,
    strehl_rails: tuple[float, float] | None = None,
    comparator_rails: tuple[float, float] | None = None,
) -> dict:
    """Measure one candidate ROI; return diagnostics even when it fails a gate."""
    scale = float(geometry["scale"])
    gy, gx = map(float, geometry["global_correction"])
    cy, cx = centre
    s_crop = crop_centered(strehl_green, cy, cx, ROI_SIZE)
    c_side = int(round(ROI_SIZE / scale))
    ccy = (cy - gy) / scale
    ccx = (cx - gx) / scale
    c_initial = crop_centered(comparator_green, ccy, ccx, c_side)
    c_no_registration = crop_centered(
        comparator_green, cy / scale, cx / scale, c_side
    )
    base = {
        "centre": [cy, cx],
        "comparator_side": c_side,
        "reason": None,
    }
    if s_crop is None or c_initial is None or c_no_registration is None:
        return {**base, "reason": "bounds"}

    sr = midrank_field(s_crop)
    cr0 = resized_rank(c_initial, sr.shape)
    local = phase_correction(sr, cr0, max_shift=64)
    corr_dy, corr_dx = local[:2]

    # A correction shifts the moving pixels.  Moving the native crop centre in
    # the opposite direction produces the same alignment without resampling.
    corrected_ccy = ccy - corr_dy / scale
    corrected_ccx = ccx - corr_dx / scale
    c_crop = crop_centered(comparator_green, corrected_ccy, corrected_ccx, c_side)
    if c_crop is None:
        return {**base, "reason": "corrected-bounds", "local": [corr_dy, corr_dx]}
    cr = resized_rank(c_crop, sr.shape)

    # Correlations are diagnostics/gates only; reported spectra stay native.
    cr_none = resized_rank(c_no_registration, sr.shape)
    corr_none = pearson(sr[::4, ::4], cr_none[::4, ::4])
    corr_fixed = pearson(sr[::4, ::4], cr[::4, ::4])
    total_dy = gy + corr_dy
    total_dx = gx + corr_dx
    wrong_ccy = (cy + total_dy) / scale
    wrong_ccx = (cx + total_dx) / scale
    c_wrong = crop_centered(comparator_green, wrong_ccy, wrong_ccx, c_side)
    corr_wrong = float("nan")
    if c_wrong is not None:
        wr = resized_rank(c_wrong, sr.shape)
        corr_wrong = pearson(sr[::4, ::4], wr[::4, ::4])
    nulls = _null_correlations(sr, cr)
    null_gate = float(np.quantile(nulls, 0.999))

    s_rail = rail_fraction(s_crop, strehl_rails)
    c_rail = rail_fraction(c_crop, comparator_rails)
    s_unique, s_largest_tie = tie_census(s_crop)
    c_unique, c_largest_tie = tie_census(c_crop)
    reason = None
    if corr_fixed <= null_gate:
        reason = "registration-null"
    elif corr_fixed - corr_none < 0.02:
        reason = "registration-gain"
    elif s_rail > 0.01 or c_rail > 0.01:
        reason = "rail"

    row = {
        **base,
        "reason": reason,
        "local_correction": [corr_dy, corr_dx],
        "phase_peak": float(local[2]),
        "corr_none": corr_none,
        "corr_fixed": corr_fixed,
        "corr_wrong": corr_wrong,
        "null_gate": null_gate,
        "strehl_rail": s_rail,
        "comparator_rail": c_rail,
        "strehl_unique": s_unique,
        "comparator_unique": c_unique,
        "strehl_largest_tie": s_largest_tie,
        "comparator_largest_tie": c_largest_tie,
    }
    if reason is None:
        ss = ordinal_shares(s_crop, 1.0)
        cs = ordinal_shares(c_crop, scale)
        row["strehl_shares"] = ss.tolist()
        row["comparator_shares"] = cs.tolist()
        row["log_ratio"] = np.log(ss / cs).tolist()
        row["texture"] = float(
            math.sqrt(float(np.sum(ss[:3])) * float(np.sum(cs[:3])))
        )
    return row


def bootstrap_effect(
    detail: np.ndarray,
    flat: np.ndarray,
    n_boot: int = 10_000,
    seed: int = SEED,
) -> dict:
    """Separate paired-log-ratio bootstraps for detail and flat strata."""
    if detail.ndim != 2 or flat.ndim != 2:
        raise ValueError("detail and flat arrays must be ROI x band")
    rng = np.random.default_rng(seed)
    point_detail = np.mean(detail, axis=0)
    point_flat = np.mean(flat, axis=0)
    detail_draws = np.empty((n_boot, detail.shape[1]), np.float64)
    flat_draws = np.empty((n_boot, flat.shape[1]), np.float64)
    for i in range(n_boot):
        di = rng.integers(0, detail.shape[0], detail.shape[0])
        fi = rng.integers(0, flat.shape[0], flat.shape[0])
        detail_draws[i] = np.mean(detail[di], axis=0)
        flat_draws[i] = np.mean(flat[fi], axis=0)
    detail_lo, detail_hi = np.quantile(detail_draws, [0.025, 0.975], axis=0)
    flat_lo, flat_hi = np.quantile(flat_draws, [0.025, 0.975], axis=0)
    return {
        "r_detail": np.exp(point_detail).tolist(),
        "r_flat": np.exp(point_flat).tolist(),
        "detail_ci_low": np.exp(detail_lo).tolist(),
        "detail_ci_high": np.exp(detail_hi).tolist(),
        "flat_ci_low": np.exp(flat_lo).tolist(),
        "flat_ci_high": np.exp(flat_hi).tolist(),
        "theta_detail": point_detail.tolist(),
        "theta_flat": point_flat.tolist(),
    }


def classify(
    low: float,
    high: float,
    flat_low: float,
    flat_high: float,
    sensitive: bool = True,
) -> str:
    if not sensitive:
        return "NOT SENSITIVE"
    if low > 1.05:
        provisional = "LEADS"
    elif high < 1.0 / 1.05:
        provisional = "TRAILS"
    else:
        provisional = "UNRESOLVED"
    flat = (
        "LEADS"
        if flat_low > 1.05
        else "TRAILS"
        if flat_high < 1.0 / 1.05
        else "UNRESOLVED"
    )
    return "UNRESOLVED (FLAT VETO)" if provisional == flat != "UNRESOLVED" else provisional


def robustness_downgrade(current: str, label: str, triggered: bool) -> str:
    """Apply a robustness veto without overwriting lack of band sensitivity."""
    if not triggered or current == "NOT SENSITIVE":
        return current
    return label


def leave_one_out_classes(detail: np.ndarray, flat: np.ndarray) -> list[list[str]]:
    """Deterministic point-estimate classes for preregistered reversal check."""
    out: list[list[str]] = []
    del flat  # Flat is a veto, not part of the primary point estimator.
    for i in range(detail.shape[0]):
        d = np.delete(detail, i, axis=0)
        ratio = np.exp(np.mean(d, axis=0))
        out.append(
            [
                "LEADS" if x > 1.05 else "TRAILS" if x < 1 / 1.05 else "UNRESOLVED"
                for x in ratio
            ]
        )
    return out


def quadrant_ratios(rows: list[dict], detail_cut: float, shape: tuple[int, int]) -> list:
    h, w = shape
    result = []
    for qy in range(2):
        for qx in range(2):
            selected = [
                r
                for r in rows
                if r["texture"] >= detail_cut
                and (r["centre"][0] >= h / 2) == bool(qy)
                and (r["centre"][1] >= w / 2) == bool(qx)
            ]
            if selected:
                arr = np.asarray([r["log_ratio"] for r in selected])
                result.append(
                    {
                        "quadrant": [qy, qx],
                        "n": len(selected),
                        "r_detail": np.exp(np.mean(arr, axis=0)).tolist(),
                    }
                )
    return result


def pct(values: Iterable[float], q: float) -> float:
    return float(np.quantile(np.asarray(list(values), np.float64), q))
