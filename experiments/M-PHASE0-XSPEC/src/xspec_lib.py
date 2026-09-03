"""Complex cross-spectral instruments for M-PHASE0-XSPEC.

The primary coordinates are full-resolution sensor pixels even though samples
live on the green quincunx.  No function in this module writes capture data.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import rawpy


ACTIVE_SHAPE = (4688, 7028)
RAW_PATTERN = ((0, 1), (3, 2))
BLACK_LEVEL = 512.0
CAMERA_WHITE_LEVEL = 15360.0
GAIN_DN_PER_E = 100.0 / 436.8
READ_NOISE_E = 4.20
READ_VARIANCE_DN2 = (READ_NOISE_E * GAIN_DN_PER_E) ** 2

PATCH = 128
GRID_SHAPE = (14, 18)
WELCH_GRIDS = (64, 48, 32)
REG_BAND = (0.02, 0.12)
ODD_BAND = (0.06, 0.22)
INVERSION_BANDS = ((0.06, 0.12), (0.12, 0.18), (0.18, 0.26))


@dataclass
class CrossBundle:
    cross: np.ndarray
    auto_a: np.ndarray
    auto_b: np.ndarray
    block_rc: tuple[tuple[int, int], ...]
    n: int

    def subset(self, indices: Sequence[int]) -> "CrossBundle":
        idx = np.asarray(indices, dtype=int)
        return CrossBundle(
            self.cross[idx],
            self.auto_a[idx],
            self.auto_b[idx],
            tuple(self.block_rc[i] for i in idx),
            self.n,
        )


_COARSE_CACHE: dict[tuple[int, float], tuple[np.ndarray, np.ndarray, np.ndarray]] = {}


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_active(path: str | Path) -> tuple[np.ndarray, dict]:
    """Copy rawpy's visible undemosaicked mosaic before its owner is freed."""
    with rawpy.imread(str(path)) as raw:
        active = np.array(raw.raw_image_visible, dtype=np.uint16, copy=True)
        pattern = (
            None
            if raw.raw_pattern is None
            else tuple(tuple(int(v) for v in row) for row in raw.raw_pattern)
        )
        camera_white = [float(x) for x in raw.camera_white_level_per_channel]
        meta = {
            "shape": list(active.shape),
            "dtype": str(active.dtype),
            "raw_pattern": None
            if pattern is None
            else [list(row) for row in pattern],
            "black_levels": [float(x) for x in raw.black_level_per_channel],
            "raw_white_level": float(raw.white_level),
            "camera_white_levels": camera_white,
        }
    if active.shape != ACTIVE_SHAPE:
        raise ValueError(f"unexpected active shape {active.shape}: {path}")
    if pattern != RAW_PATTERN:
        raise ValueError(f"unexpected CFA pattern {pattern}: {path}")
    if any(abs(x - BLACK_LEVEL) > 1e-9 for x in meta["black_levels"]):
        raise ValueError(f"unexpected black levels {meta['black_levels']}: {path}")
    if any(abs(x - CAMERA_WHITE_LEVEL) > 1e-9 for x in camera_white):
        raise ValueError(f"unexpected camera white levels {camera_white}: {path}")
    return active, meta


def candidate_centres(
    rows: int = GRID_SHAPE[0],
    cols: int = GRID_SHAPE[1],
    size: int = PATCH,
) -> list[dict]:
    margin = size + 2

    def even_grid(lo: int, hi: int, count: int) -> list[int]:
        values = np.linspace(lo, hi, count)
        out = [int(round(float(v) / 2.0) * 2) for v in values]
        if len(set(out)) != count:
            raise ValueError("candidate grid collapsed after even rounding")
        return out

    rr = even_grid(margin, ACTIVE_SHAPE[0] - 1 - margin, rows)
    cc = even_grid(margin, ACTIVE_SHAPE[1] - 1 - margin, cols)
    return [
        {"grid_row": ir, "grid_col": ic, "row": r, "col": c}
        for ir, r in enumerate(rr)
        for ic, c in enumerate(cc)
    ]


def gq_indices(
    centres: Sequence[dict | tuple[int, int]], size: int = PATCH
) -> tuple[np.ndarray, np.ndarray]:
    """Broadcastable sensor row/column indices for green-quincunx crops."""
    k = np.arange(size, dtype=int) - size // 2
    all_rows = []
    all_cols = []
    for centre in centres:
        if isinstance(centre, dict):
            rc, cc = int(centre["row"]), int(centre["col"])
        else:
            rc, cc = (int(v) for v in centre)
        if rc % 2 or cc % 2:
            raise ValueError("GQ centre must be even in both sensor coordinates")
        u0 = (rc + cc) // 2
        v0 = (rc - cc) // 2
        u = (u0 + k)[:, None]
        v = (v0 + k)[None, :]
        rows = u + v
        cols = u - v + 1
        if (
            rows.min() < 0
            or cols.min() < 0
            or rows.max() >= ACTIVE_SHAPE[0]
            or cols.max() >= ACTIVE_SHAPE[1]
        ):
            raise ValueError(f"GQ patch leaves active bounds at {(rc, cc)}")
        all_rows.append(rows)
        all_cols.append(cols)
    return np.stack(all_rows), np.stack(all_cols)


def extract_gq(
    active: np.ndarray, row: int, col: int, size: int = PATCH
) -> np.ndarray:
    rows, cols = gq_indices([(row, col)], size)
    return np.asarray(active[rows[0], cols[0]], dtype=np.float32) - BLACK_LEVEL


def extract_gq_batch(
    active: np.ndarray,
    centres: Sequence[dict],
    size: int = PATCH,
) -> np.ndarray:
    rows, cols = gq_indices(centres, size)
    return np.asarray(active[rows, cols], dtype=np.float32) - BLACK_LEVEL


def symmetric_hann(n: int) -> np.ndarray:
    if n < 2:
        raise ValueError("Hann length must be at least two")
    x = np.arange(n, dtype=np.float64)
    w = 0.5 - 0.5 * np.cos(2.0 * np.pi * x / (n - 1))
    return np.outer(w, w)


def frequency_grid(n: int, scale: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    """Full-sensor frequency coordinates for an n by n GQ DFT."""
    fu = np.fft.fftfreq(n)[:, None] * np.ones((1, n))
    fv = np.fft.fftfreq(n)[None, :] * np.ones((n, 1))
    fx = (fu - fv) * 0.5 * float(scale)
    fy = (fu + fv) * 0.5 * float(scale)
    return fx, fy


def frequency_mask(
    n: int,
    band: tuple[float, float],
    *,
    one_side: bool = True,
    min_coherence: float | None = None,
    coherence: np.ndarray | None = None,
    scale: float = 1.0,
) -> np.ndarray:
    fx, fy = frequency_grid(n, scale=scale)
    radius = np.hypot(fx, fy)
    legal = np.abs(fx) + np.abs(fy) <= 0.5
    keep = legal & (radius >= band[0]) & (radius < band[1])
    if one_side:
        keep &= (fy > 0.0) | ((fy == 0.0) & (fx > 0.0))
    if min_coherence is not None:
        if coherence is None:
            raise ValueError("coherence is required with min_coherence")
        keep &= np.asarray(coherence) >= float(min_coherence)
    return keep


def focus_scores(
    active: np.ndarray,
    centres: Sequence[dict],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Election and disjoint low-band scores for all fixed candidate tiles."""
    patches = extract_gq_batch(active, centres, PATCH)
    levels = np.mean(patches, axis=(1, 2), dtype=np.float64)
    win = symmetric_hann(PATCH).astype(np.float32)
    norm = float(np.sum(win * win))
    demeaned = patches - np.mean(patches, axis=(1, 2), keepdims=True)
    fft = np.fft.fft2(demeaned * win[None, :, :], axes=(-2, -1))
    power = np.abs(fft) ** 2 / norm
    elect = frequency_mask(PATCH, (0.10, 0.22), one_side=False)
    low = frequency_mask(PATCH, (0.02, 0.06), one_side=False)
    elect_power = np.mean(power[:, elect], axis=1)
    low_power = np.mean(power[:, low], axis=1)
    noise = GAIN_DN_PER_E * np.maximum(levels, 0.0) + READ_VARIANCE_DN2
    signal = elect_power - noise
    return (
        signal.astype(np.float64),
        low_power.astype(np.float64),
        noise.astype(np.float64),
        levels.astype(np.float64),
    )


def smooth_focus(values: np.ndarray) -> np.ndarray:
    x = np.asarray(values, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError("focus matrix must be frames by tiles")
    if x.shape[0] < 3:
        return x.copy()
    out = x.copy()
    out[1:-1] = 0.25 * x[:-2] + 0.5 * x[1:-1] + 0.25 * x[2:]
    out[0] = 0.75 * x[0] + 0.25 * x[1]
    out[-1] = 0.25 * x[-2] + 0.75 * x[-1]
    return out


def select_tiles(
    election_signal: np.ndarray,
    low_power: np.ndarray,
    noise: np.ndarray,
    centres: Sequence[dict],
    count: int = 200,
    half_window: int = 5,
    min_snr: float = 5.0,
) -> dict:
    sm = smooth_focus(election_signal)
    low_sm = smooth_focus(low_power)
    peaks = np.argmax(sm, axis=0)
    low_peaks = np.argmax(low_sm, axis=0)
    peak_signal = sm[peaks, np.arange(sm.shape[1])]
    peak_noise = noise[peaks, np.arange(sm.shape[1])]
    snr = peak_signal / np.maximum(peak_noise, np.finfo(float).tiny)
    eligible = (
        (peaks >= half_window)
        & (peaks < sm.shape[0] - half_window)
        & (snr >= min_snr)
        & np.isfinite(snr)
    )
    order = sorted(
        np.flatnonzero(eligible),
        key=lambda i: (-float(snr[i]), int(centres[i]["row"]), int(centres[i]["col"])),
    )
    chosen = order[:count]

    low_map = np.asarray(low_peaks).reshape(GRID_SHAPE)
    occ_all = np.zeros(GRID_SHAPE, dtype=bool)
    for ir in range(GRID_SHAPE[0]):
        for ic in range(GRID_SHAPE[1]):
            here = int(low_map[ir, ic])
            neighbours = []
            if ir:
                neighbours.append(int(low_map[ir - 1, ic]))
            if ir + 1 < GRID_SHAPE[0]:
                neighbours.append(int(low_map[ir + 1, ic]))
            if ic:
                neighbours.append(int(low_map[ir, ic - 1]))
            if ic + 1 < GRID_SHAPE[1]:
                neighbours.append(int(low_map[ir, ic + 1]))
            occ_all[ir, ic] = any(abs(here - x) >= 10 for x in neighbours)
    placebo_all = np.roll(np.roll(occ_all, 3, axis=0), 5, axis=1)

    selected = []
    for tile_id, i in enumerate(chosen):
        c = dict(centres[i])
        c.update(
            {
                "tile_id": tile_id,
                "candidate_index": int(i),
                "peak": int(peaks[i]),
                "low_peak": int(low_peaks[i]),
                "texture_snr": float(snr[i]),
                "occlusion": bool(occ_all[c["grid_row"], c["grid_col"]]),
                "placebo_occlusion": bool(
                    placebo_all[c["grid_row"], c["grid_col"]]
                ),
            }
        )
        selected.append(c)
    return {
        "selected": selected,
        "eligible_count": int(np.sum(eligible)),
        "candidate_count": len(centres),
        "peak_indices": peaks.astype(int),
        "low_peak_indices": low_peaks.astype(int),
        "occlusion_all": occ_all,
        "placebo_all": placebo_all,
    }


def block_starts(patch: int, n: int) -> list[int]:
    if n <= 0 or n > patch or n % 2:
        raise ValueError("Welch size must be positive, even, and fit")
    return list(range(0, patch - n + 1, n // 2))


def block_ffts(
    patch: np.ndarray,
    n: int,
    *,
    window: str = "hann",
) -> tuple[np.ndarray, tuple[tuple[int, int], ...]]:
    a = np.asarray(patch, dtype=np.float64)
    if a.shape != (PATCH, PATCH):
        raise ValueError(f"expected {(PATCH, PATCH)} patch, got {a.shape}")
    starts = block_starts(PATCH, n)
    if window == "hann":
        win = symmetric_hann(n)
    elif window == "rect":
        win = np.ones((n, n), dtype=np.float64)
    else:
        raise ValueError(f"unknown window {window!r}")
    norm = math.sqrt(float(np.sum(win * win)))
    ffts = []
    coords = []
    for ir, row in enumerate(starts):
        for ic, col in enumerate(starts):
            block = a[row : row + n, col : col + n]
            block = (block - float(np.mean(block))) * win
            ffts.append(np.fft.fft2(block) / norm)
            coords.append((ir, ic))
    return np.stack(ffts), tuple(coords)


def cross_bundle(
    a: np.ndarray,
    b: np.ndarray,
    n: int,
    *,
    window: str = "hann",
) -> CrossBundle:
    fa, rca = block_ffts(a, n, window=window)
    fb, rcb = block_ffts(b, n, window=window)
    if rca != rcb:
        raise AssertionError("Welch block coordinates differ")
    return CrossBundle(
        cross=fa * np.conjugate(fb),
        auto_a=np.abs(fa) ** 2,
        auto_b=np.abs(fb) ** 2,
        block_rc=rca,
        n=n,
    )


def cross_bundle_from_ffts(
    fa: np.ndarray,
    fb: np.ndarray,
    block_rc: tuple[tuple[int, int], ...],
    n: int,
) -> CrossBundle:
    if fa.shape != fb.shape or fa.ndim != 3 or fa.shape[1:] != (n, n):
        raise ValueError("cached FFT shapes do not match")
    if fa.shape[0] != len(block_rc):
        raise ValueError("cached FFT/block-coordinate count differs")
    return CrossBundle(
        cross=fa * np.conjugate(fb),
        auto_a=np.abs(fa) ** 2,
        auto_b=np.abs(fb) ** 2,
        block_rc=block_rc,
        n=n,
    )


def bundle_means(bundle: CrossBundle) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    cross = np.mean(bundle.cross, axis=0)
    pa = np.mean(bundle.auto_a, axis=0)
    pb = np.mean(bundle.auto_b, axis=0)
    coherence = np.abs(cross) ** 2 / np.maximum(
        pa * pb, np.finfo(float).tiny
    )
    coherence = np.clip(coherence, 0.0, 1.0)
    return cross, pa, pb, coherence


def fit_phase_shift(
    bundle: CrossBundle,
    *,
    frequency_scale: float = 1.0,
    shift_sign: float = 1.0,
    swap_axes: bool = False,
    unit_scale: float = 1.0,
) -> dict:
    """Fit moving(x)=reference(x+d), returning d in sensor (x,y) pixels."""
    cross, pa, pb, coherence = bundle_means(bundle)
    fx, fy = frequency_grid(bundle.n, scale=frequency_scale)
    keep = frequency_mask(
        bundle.n,
        REG_BAND,
        coherence=coherence,
        min_coherence=0.20,
        scale=frequency_scale,
    )
    if int(np.sum(keep)) < 20:
        raise ValueError(f"only {int(np.sum(keep))} coherent registration bins")
    coarse = frequency_mask(
        bundle.n,
        (REG_BAND[0], 0.06),
        coherence=coherence,
        min_coherence=0.20,
        scale=frequency_scale,
    )
    if int(np.sum(coarse)) < 8:
        coarse = keep
    c0 = cross[coarse]
    w0 = np.abs(c0) * np.maximum(coherence[coarse], 1e-6)
    phasor0 = c0 / np.maximum(np.abs(c0), np.finfo(float).tiny)
    cache_key = (bundle.n, float(frequency_scale))
    if cache_key not in _COARSE_CACHE:
        geom = frequency_mask(
            bundle.n,
            (REG_BAND[0], 0.06),
            scale=frequency_scale,
        )
        shifts = np.asarray(
            [(dx, dy) for dx in range(-8, 9) for dy in range(-8, 9)],
            dtype=np.float64,
        )
        phase = (
            shifts[:, 0, None] * fx[geom][None, :]
            + shifts[:, 1, None] * fy[geom][None, :]
        )
        _COARSE_CACHE[cache_key] = (
            geom,
            shifts,
            np.exp(-2j * np.pi * phase),
        )
    geom, shifts, ramps = _COARSE_CACHE[cache_key]
    valid = coherence[geom] >= 0.20
    if int(np.sum(valid)) >= 8:
        cg = cross[geom][valid]
        wg = np.abs(cg) * np.maximum(coherence[geom][valid], 1e-6)
        pg = cg / np.maximum(np.abs(cg), np.finfo(float).tiny)
        scores = np.abs(ramps[:, valid] @ (wg * pg)) / np.sum(wg)
    else:
        # The registered fallback is the full coherent registration band.
        shifts = np.asarray(
            [(dx, dy) for dx in range(-8, 9) for dy in range(-8, 9)],
            dtype=np.float64,
        )
        phase = (
            shifts[:, 0, None] * fx[coarse][None, :]
            + shifts[:, 1, None] * fy[coarse][None, :]
        )
        ramps_fallback = np.exp(-2j * np.pi * phase)
        scores = np.abs(ramps_fallback @ (w0 * phasor0)) / np.sum(w0)
    best_i = int(np.argmax(scores))
    dx, dy = (float(v) for v in shifts[best_i])

    weight = np.abs(cross[keep]) * np.maximum(coherence[keep], 1e-6)
    weight /= max(float(np.median(weight)), np.finfo(float).tiny)
    design = np.column_stack([fx[keep], fy[keep], np.ones(int(np.sum(keep)))])
    intercept = 0.0
    for _ in range(3):
        residual_cross = cross[keep] * np.exp(
            -2j * np.pi * (fx[keep] * dx + fy[keep] * dy)
        )
        unit = residual_cross / np.maximum(
            np.abs(residual_cross), np.finfo(float).tiny
        )
        # Estimate circular intercept before calling angle().  Without this,
        # an exact contrast inversion straddles the +pi/-pi branch cut and a
        # least-squares slope can counterfeit a many-pixel translation.
        phase0 = float(np.angle(np.sum(weight * unit)))
        centred = residual_cross * np.exp(-1j * phase0)
        target = np.angle(centred) / (2.0 * np.pi)
        rw = np.sqrt(weight)
        coef, _, _, _ = np.linalg.lstsq(
            design * rw[:, None], target * rw, rcond=None
        )
        dx += float(coef[0])
        dy += float(coef[1])
        intercept = phase0 / (2.0 * np.pi) + float(coef[2])
        if math.hypot(float(coef[0]), float(coef[1])) < 1e-5:
            break

    residual_cross = cross[keep] * np.exp(
        -2j * np.pi * (fx[keep] * dx + fy[keep] * dy)
    )
    residual_cycles = np.angle(
        residual_cross * np.exp(-2j * np.pi * intercept)
    ) / (2.0 * np.pi)
    out_dx = dx * float(shift_sign) * float(unit_scale)
    out_dy = dy * float(shift_sign) * float(unit_scale)
    if swap_axes:
        out_dx, out_dy = out_dy, out_dx
    return {
        "dx": float(out_dx),
        "dy": float(out_dy),
        "fit_dx": float(dx),
        "fit_dy": float(dy),
        "phase_intercept_cycles": intercept,
        "bins": int(np.sum(keep)),
        "median_coherence": float(np.median(coherence[keep])),
        "p10_coherence": float(np.percentile(coherence[keep], 10)),
        "weighted_residual_rms_cycles": float(
            np.sqrt(np.average(residual_cycles**2, weights=weight))
        ),
    }


def derotate(
    cross: np.ndarray,
    n: int,
    shift: tuple[float, float],
    *,
    frequency_scale: float = 1.0,
) -> np.ndarray:
    fx, fy = frequency_grid(n, scale=frequency_scale)
    dx, dy = shift
    return np.asarray(cross) * np.exp(-2j * np.pi * (fx * dx + fy * dy))


def phase_field_and_floor(
    bundle: CrossBundle,
    shift: tuple[float, float],
    *,
    floor_multiplier: float = 1.0,
    omit_derotation: bool = False,
    magnitude_only: bool = False,
    frequency_scale: float = 1.0,
) -> dict:
    cross, pa, pb, coherence = bundle_means(bundle)
    if magnitude_only:
        cross = np.abs(cross).astype(complex)
    if not omit_derotation:
        cross = derotate(
            cross, bundle.n, shift, frequency_scale=frequency_scale
        )
    keep = frequency_mask(
        bundle.n,
        ODD_BAND,
        coherence=coherence,
        min_coherence=0.20,
        scale=frequency_scale,
    )
    if int(np.sum(keep)) < 20:
        raise ValueError(f"only {int(np.sum(keep))} coherent odd-phase bins")
    weight = np.sqrt(pa[keep] * pb[keep]) * coherence[keep]
    theta = np.angle(cross[keep]) * 0.5
    observed = float(np.sqrt(np.average(theta * theta, weights=weight)))
    gamma = np.clip(coherence[keep], 1e-6, 1.0 - 1e-6)
    var = (1.0 - gamma) / (2.0 * len(bundle.block_rc) * gamma)
    nominal = float(
        0.5 * np.sqrt(np.average(var, weights=weight))
    )
    fx, fy = frequency_grid(bundle.n, scale=frequency_scale)
    return {
        "observed_rms_rad": observed,
        "nominal_floor_rad": nominal * float(floor_multiplier),
        "bins": int(np.sum(keep)),
        "median_coherence": float(np.median(coherence[keep])),
        "theta": theta,
        "fx": fx[keep],
        "fy": fy[keep],
        "weight": weight,
    }


def _spatial_score(a: np.ndarray, b: np.ndarray, du: int, dv: int) -> float:
    n = a.shape[0]
    au0, au1 = (0, n - du) if du >= 0 else (-du, n)
    bu0, bu1 = (du, n) if du >= 0 else (0, n + du)
    av0, av1 = (0, n - dv) if dv >= 0 else (-dv, n)
    bv0, bv1 = (dv, n) if dv >= 0 else (0, n + dv)
    xa = a[au0:au1, av0:av1].astype(np.float64, copy=False)
    xb = b[bu0:bu1, bv0:bv1].astype(np.float64, copy=False)
    xa = xa - float(np.mean(xa))
    xb = xb - float(np.mean(xb))
    den = math.sqrt(float(np.sum(xa * xa) * np.sum(xb * xb)))
    return float(np.sum(xa * xb) / max(den, np.finfo(float).tiny))


def _parabolic_offset(left: float, centre: float, right: float) -> float:
    den = left - 2.0 * centre + right
    if not np.isfinite(den) or abs(den) < 1e-12:
        return 0.0
    return float(np.clip(0.5 * (left - right) / den, -1.0, 1.0))


def fit_spatial_shift(
    a: np.ndarray,
    b: np.ndarray,
    n: int,
    parity: int | None = None,
    max_gq_shift: int = 4,
) -> dict:
    starts = block_starts(PATCH, n)
    blocks = []
    for ir, row in enumerate(starts):
        for ic, col in enumerate(starts):
            if parity is not None and (ir + ic) % 2 != parity:
                continue
            blocks.append(
                (
                    np.asarray(a[row : row + n, col : col + n]),
                    np.asarray(b[row : row + n, col : col + n]),
                )
            )
    if len(blocks) < 2:
        raise ValueError("too few spatial blocks")
    shifts = list(range(-max_gq_shift, max_gq_shift + 1))
    surface = np.zeros((len(shifts), len(shifts)), dtype=np.float64)
    margin = max_gq_shift
    for x, y in blocks:
        xa = np.asarray(
            x[margin : n - margin, margin : n - margin],
            dtype=np.float64,
        )
        xa -= float(np.mean(xa))
        xnorm = math.sqrt(float(np.sum(xa * xa)))
        shifted = np.stack(
            [
                np.asarray(
                    y[
                        margin + du : n - margin + du,
                        margin + dv : n - margin + dv,
                    ],
                    dtype=np.float64,
                )
                for du in shifts
                for dv in shifts
            ]
        )
        shifted -= np.mean(shifted, axis=(1, 2), keepdims=True)
        ynorm = np.sqrt(np.sum(shifted * shifted, axis=(1, 2)))
        scores = np.sum(shifted * xa[None, :, :], axis=(1, 2))
        scores /= np.maximum(xnorm * ynorm, np.finfo(float).tiny)
        surface += scores.reshape(len(shifts), len(shifts))
    surface /= len(blocks)
    iu, iv = np.unravel_index(int(np.argmax(surface)), surface.shape)
    du = float(shifts[iu])
    dv = float(shifts[iv])
    if 0 < iu < len(shifts) - 1:
        du += _parabolic_offset(
            surface[iu - 1, iv], surface[iu, iv], surface[iu + 1, iv]
        )
    if 0 < iv < len(shifts) - 1:
        dv += _parabolic_offset(
            surface[iu, iv - 1], surface[iu, iv], surface[iu, iv + 1]
        )
    # Sensor y = u+v and x = u-v.
    return {
        "dx": float(du - dv),
        "dy": float(du + dv),
        "du": du,
        "dv": dv,
        "score": float(surface[iu, iv]),
        "blocks": len(blocks),
        "edge_hit": bool(
            iu in (0, len(shifts) - 1) or iv in (0, len(shifts) - 1)
        ),
    }


def split_registration(
    a: np.ndarray,
    b: np.ndarray,
    n: int,
    *,
    bundle: CrossBundle | None = None,
) -> dict:
    bundle = cross_bundle(a, b, n) if bundle is None else bundle
    if bundle.n != n:
        raise ValueError("cached bundle uses the wrong Fourier grid")
    halves = [
        [i for i, rc in enumerate(bundle.block_rc) if sum(rc) % 2 == parity]
        for parity in (0, 1)
    ]
    phase = [fit_phase_shift(bundle.subset(idx)) for idx in halves]
    spatial = [fit_spatial_shift(a, b, n, parity=p) for p in (0, 1)]
    p_phase = 0.5 * math.hypot(
        phase[0]["dx"] - phase[1]["dx"],
        phase[0]["dy"] - phase[1]["dy"],
    )
    p_spatial = 0.5 * math.hypot(
        spatial[0]["dx"] - spatial[1]["dx"],
        spatial[0]["dy"] - spatial[1]["dy"],
    )
    full = fit_phase_shift(bundle)
    return {
        "phase_precision_sensor_px": float(p_phase),
        "spatial_precision_sensor_px": float(p_spatial),
        "phase_full": full,
        "phase_halves": phase,
        "spatial_halves": spatial,
        "bundle": bundle,
    }


def band_correlation(
    bundle: CrossBundle,
    shift: tuple[float, float],
    band: tuple[float, float],
    *,
    bootstrap: int = 0,
    seed: int = 0,
    clip_negative: bool = False,
    magnitude_only: bool = False,
) -> dict:
    cross, pa, pb, coherence = bundle_means(bundle)
    if magnitude_only:
        cross = np.abs(cross).astype(complex)
    cross = derotate(cross, bundle.n, shift)
    keep = frequency_mask(
        bundle.n,
        band,
        coherence=coherence,
        min_coherence=0.20,
    )
    bins = int(np.sum(keep))
    if bins == 0:
        raise ValueError("no coherent bins in inversion band")

    def score(c: np.ndarray, aa: np.ndarray, bb: np.ndarray) -> float:
        num = float(np.sum(np.real(c[keep])))
        den = math.sqrt(
            float(np.sum(aa[keep])) * float(np.sum(bb[keep]))
        )
        value = num / max(den, np.finfo(float).tiny)
        return max(value, 0.0) if clip_negative else value

    value = score(cross, pa, pb)
    ci = [float("nan"), float("nan")]
    if bootstrap:
        rng = np.random.default_rng(seed)
        values = np.empty(bootstrap, dtype=np.float64)
        for i in range(bootstrap):
            idx = rng.integers(0, len(bundle.block_rc), len(bundle.block_rc))
            c = np.mean(bundle.cross[idx], axis=0)
            if magnitude_only:
                c = np.abs(c).astype(complex)
            c = derotate(c, bundle.n, shift)
            aa = np.mean(bundle.auto_a[idx], axis=0)
            bb = np.mean(bundle.auto_b[idx], axis=0)
            values[i] = score(c, aa, bb)
        ci = [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]
    return {
        "rho": float(value),
        "ci95": ci,
        "bins": bins,
        "median_coherence": float(np.median(coherence[keep])),
    }


def cluster_bootstrap(
    records: Sequence[dict],
    value,
    *,
    draws: int = 10_000,
    seed: int = 20260902,
) -> tuple[float, list[float]]:
    by_tile: dict[int, list[dict]] = {}
    for row in records:
        by_tile.setdefault(int(row["tile_id"]), []).append(row)
    tiles = sorted(by_tile)
    if not tiles:
        return float("nan"), [float("nan"), float("nan")]
    point = float(value(records))
    rng = np.random.default_rng(seed)
    samples = np.empty(draws, dtype=np.float64)
    for i in range(draws):
        chosen = rng.integers(0, len(tiles), len(tiles))
        rows = [
            row
            for j in chosen
            for row in by_tile[tiles[int(j)]]
        ]
        samples[i] = float(value(rows))
    return point, [
        float(np.nanpercentile(samples, 2.5)),
        float(np.nanpercentile(samples, 97.5)),
    ]


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total <= 0:
        return [float("nan"), float("nan")]
    p = successes / total
    den = 1.0 + z * z / total
    centre = (p + z * z / (2.0 * total)) / den
    half = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total**2)) / den
    return [float(max(0.0, centre - half)), float(min(1.0, centre + half))]
