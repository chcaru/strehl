"""Orientation-resolved through-focus estimator for M-PHASE0-ASTIG.

This module contains no synthetic truth and never opens a RAW file.  It accepts
2-D image cubes or per-block sufficient statistics, computes the registered
Gx^2/Gy^2 responses, and fits baseline-subtracted three-point log parabolas.

The optional ``defect`` arguments exist only so ``commission.py`` can prove each
control goes red.  ``real_measure.py`` never forwards one and asserts that fact.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

import numpy as np
from scipy.ndimage import sobel


RADII = (0.25, 0.50, 0.75, 0.90)
SECTORS = ("left", "right", "top", "bottom")
TILE_SIZE = 192
BLOCK_GRID = 4
BOOTSTRAPS = 2_000
BOOTSTRAP_SEED = 0xA5716
SOBEL_MARGIN = 4
MIN_PROMINENCE = 1.10
MAX_OFFSET = 0.75
MAX_ARM_CI_WIDTH = 1.50
MIN_BOOTSTRAP_VALID = 0.90


@dataclass(frozen=True)
class Peak:
    valid: bool
    z: float | None
    index: int | None
    offset: float | None
    baseline: float | None
    prominence: float | None
    log_curvature: float | None
    reason: str | None


def fixed_tile_centres(
    height: int,
    width: int,
    tile_size: int = TILE_SIZE,
) -> list[dict]:
    """Return the content-independent centre/cardinal sampling geometry."""
    if height < tile_size + 16 or width < tile_size + 16:
        raise ValueError("active green plane is too small for registered tiles")
    cy = (height - 1) / 2.0
    cx = (width - 1) / 2.0
    half = tile_size // 2
    room_x = cx - half - 8
    room_y = cy - half - 8
    out = [
        {
            "sector": "centre",
            "radius": 0.0,
            "cy": int(round(cy)),
            "cx": int(round(cx)),
        }
    ]
    for radius in RADII:
        dx = int(round(radius * room_x))
        dy = int(round(radius * room_y))
        out.extend(
            [
                {
                    "sector": "left",
                    "radius": radius,
                    "cy": int(round(cy)),
                    "cx": int(round(cx)) - dx,
                },
                {
                    "sector": "right",
                    "radius": radius,
                    "cy": int(round(cy)),
                    "cx": int(round(cx)) + dx,
                },
                {
                    "sector": "top",
                    "radius": radius,
                    "cy": int(round(cy)) - dy,
                    "cx": int(round(cx)),
                },
                {
                    "sector": "bottom",
                    "radius": radius,
                    "cy": int(round(cy)) + dy,
                    "cx": int(round(cx)),
                },
            ]
        )
    return out


def _hann2(height: int, width: int) -> np.ndarray:
    return np.outer(np.hanning(height), np.hanning(width))


def _block_slices(length: int, blocks: int) -> list[slice]:
    edges = np.linspace(0, length, blocks + 1, dtype=int)
    return [slice(int(a), int(b)) for a, b in zip(edges[:-1], edges[1:])]


def component_arrays(frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Registered per-frame 2-D Sobel components, in DN per green pixel."""
    a = np.asarray(frame, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError("component_arrays requires one 2-D frame")
    gx = sobel(a, axis=1, mode="nearest") / 8.0
    gy = sobel(a, axis=0, mode="nearest") / 8.0
    return gx, gy


def frame_sufficient_stats(
    frame: np.ndarray,
    block_grid: int = BLOCK_GRID,
    margin: int = SOBEL_MARGIN,
) -> np.ndarray:
    """Return [block, sx, sy, sl, sw] for one tile.

    ``sx`` and ``sy`` are weighted sums of squared Sobel components. ``sl`` is
    weighted luma and ``sw`` is weight.  These are sufficient to combine blocks
    under a paired bootstrap without re-filtering the image.
    """
    a = np.asarray(frame, dtype=np.float64)
    if min(a.shape) <= 2 * margin + block_grid:
        raise ValueError("tile is too small for margin and block grid")
    gx, gy = component_arrays(a)
    core = np.s_[margin : a.shape[0] - margin, margin : a.shape[1] - margin]
    a = a[core]
    gx = gx[core]
    gy = gy[core]
    weight = _hann2(*a.shape)
    ys = _block_slices(a.shape[0], block_grid)
    xs = _block_slices(a.shape[1], block_grid)
    rows = []
    for sy in ys:
        for sx in xs:
            w = weight[sy, sx]
            p = a[sy, sx]
            dx = gx[sy, sx]
            dy = gy[sy, sx]
            rows.append(
                (
                    float(np.sum(w * dx * dx)),
                    float(np.sum(w * dy * dy)),
                    float(np.sum(w * p)),
                    float(np.sum(w)),
                )
            )
    return np.asarray(rows, dtype=np.float64)


def cube_sufficient_stats(
    cube: np.ndarray,
    block_grid: int = BLOCK_GRID,
    margin: int = SOBEL_MARGIN,
) -> np.ndarray:
    """Return registered sufficient statistics for ``[frame,y,x]`` input."""
    a = np.asarray(cube)
    if a.ndim != 3:
        raise ValueError("cube must have shape [frame,y,x]")
    # Deliberately loop: scipy.ndimage.sobel on the cube would smooth in frame.
    return np.stack(
        [frame_sufficient_stats(f, block_grid, margin) for f in a],
        axis=0,
    )


def aggregate_curves(
    stats: np.ndarray,
    counts_x: np.ndarray | None = None,
    counts_y: np.ndarray | None = None,
    defect: str | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Aggregate block sufficient statistics into Ex/Ey response curves."""
    a = np.asarray(stats, dtype=np.float64)
    if a.ndim != 3 or a.shape[2] != 4:
        raise ValueError("stats must have shape [frame,block,4]")
    blocks = a.shape[1]
    if counts_x is None:
        counts_x = np.ones(blocks, dtype=np.float64)
    if counts_y is None:
        counts_y = counts_x
    ax = np.einsum("b,fbv->fv", counts_x, a)
    ay = np.einsum("b,fbv->fv", counts_y, a)

    def one(agg: np.ndarray, component: int) -> np.ndarray:
        sw = np.maximum(agg[:, 3], 1e-30)
        mean_luma = agg[:, 2] / sw
        return (agg[:, component] / sw) / np.maximum(mean_luma * mean_luma, 1e-30)

    ex = one(ax, 0)
    ey = one(ay, 1)
    if defect == "pool-arms":
        pooled = ex + ey
        return pooled, pooled.copy()
    return ex, ey


def fit_log_peak(
    curve: Iterable[float],
    *,
    baseline: float | None = None,
    apply_gates: bool = True,
    defect: str | None = None,
    mode: str = "log",
) -> Peak:
    """Fit M33's three-point log parabola to one response curve."""
    if mode not in ("log", "linear"):
        raise ValueError("mode must be 'log' or 'linear'")
    e = np.asarray(tuple(curve), dtype=np.float64)
    if e.ndim != 1 or e.size < 7 or not np.all(np.isfinite(e)):
        return Peak(False, None, None, None, None, None, None, "bad curve")
    if np.max(e) <= 0:
        return Peak(False, None, None, None, None, None, None, "nonpositive curve")
    b = float(np.quantile(e, 0.05)) if baseline is None else float(baseline)
    k = int(np.argmax(e))
    prominence = float(np.max(e) / max(float(np.median(e)), 1e-30))
    if apply_gates and not (2 <= k <= e.size - 3):
        return Peak(False, None, k, None, b, prominence, None, "boundary maximum")
    if not (1 <= k <= e.size - 2):
        return Peak(False, None, k, None, b, prominence, None, "no neighbours")
    floor = max(float(np.max(e)) * 1e-12, 1e-30)
    s = np.maximum(e - b, floor)
    transformed = np.log(s) if mode == "log" else s
    lm, l0, lp = transformed[k - 1 : k + 2]
    denom = float(lm - 2.0 * l0 + lp)
    curvature = -denom
    if defect == "integer-argmax":
        offset = 0.0
    else:
        offset = float(-0.5 * (lp - lm) / denom) if denom != 0 else float("nan")
    if not np.isfinite(offset) or denom >= 0:
        return Peak(False, None, k, offset, b, prominence, curvature, "not concave")
    if apply_gates and abs(offset) > MAX_OFFSET:
        return Peak(False, None, k, offset, b, prominence, curvature, "vertex outside")
    if apply_gates and prominence < MIN_PROMINENCE:
        return Peak(False, None, k, offset, b, prominence, curvature, "low prominence")
    return Peak(True, float(k + offset), k, offset, b, prominence, curvature, None)


def mapped_delta(
    zx: float,
    zy: float,
    sector: str,
    defect: str | None = None,
) -> float:
    """Map global x/y gradient peaks to tangential-minus-sagittal lines."""
    if sector in ("left", "right", "centre"):
        value = zx - zy
    elif sector in ("top", "bottom"):
        value = zx - zy if defect == "no-vertical-swap" else zy - zx
    else:
        raise ValueError(f"unknown sector {sector!r}")
    if defect == "absolute-delta":
        value = abs(value)
    if defect == "constant-plus-one":
        value += 1.0
    if defect == "global-reference":
        # Commissioning plant: compare against a fixed zero-depth reference
        # instead of the paired local arm, so common field curvature leaks in.
        value += (zx + zy) / 2.0
    return float(value)


def _fit_pair(
    ex: np.ndarray,
    ey: np.ndarray,
    sector: str,
    *,
    apply_gates: bool,
    defect: str | None,
    baseline: float | None = None,
    fit_mode: str = "log",
) -> tuple[Peak, Peak, float | None, float | None]:
    px = fit_log_peak(
        ex,
        baseline=baseline,
        apply_gates=apply_gates,
        defect="integer-argmax" if defect == "integer-argmax" else None,
        mode=fit_mode,
    )
    py = fit_log_peak(
        ey,
        baseline=baseline,
        apply_gates=apply_gates,
        defect="integer-argmax" if defect == "integer-argmax" else None,
        mode=fit_mode,
    )
    if not px.valid or not py.valid:
        return px, py, None, None
    assert px.z is not None and py.z is not None
    delta = mapped_delta(px.z, py.z, sector, defect)
    return px, py, delta, float((px.z + py.z) / 2.0)


def measure_stats(
    stats: np.ndarray,
    sector: str,
    *,
    bootstraps: int = BOOTSTRAPS,
    seed: int = BOOTSTRAP_SEED,
    apply_gates: bool = True,
    defect: str | None = None,
    baseline: float | None = None,
    fit_mode: str = "log",
    keep_bootstrap: bool = False,
) -> dict:
    """Fit a paired tile and estimate uncertainty by paired block bootstrap."""
    allowed = {
        None,
        "pool-arms",
        "no-vertical-swap",
        "absolute-delta",
        "constant-plus-one",
        "global-reference",
        "integer-argmax",
        "force-flat",
        "independent-bootstrap",
    }
    if defect not in allowed:
        raise ValueError(f"unknown commissioning defect {defect!r}")
    effective_gates = apply_gates and defect != "force-flat"
    ex, ey = aggregate_curves(
        stats,
        defect="pool-arms" if defect == "pool-arms" else None,
    )
    px, py, delta, mu = _fit_pair(
        ex,
        ey,
        sector,
        apply_gates=effective_gates,
        defect=defect,
        baseline=baseline,
        fit_mode=fit_mode,
    )
    out = {
        "valid": bool(px.valid and py.valid),
        "x_peak": asdict(px),
        "y_peak": asdict(py),
        "delta": delta,
        "mu": mu,
        "ex": ex.tolist(),
        "ey": ey.tolist(),
        "bootstraps_requested": int(bootstraps),
    }
    if not out["valid"] or bootstraps <= 0:
        out.update(
            {
                "bootstrap_valid": 0,
                "bootstrap_valid_fraction": 0.0,
                "valid_after_uncertainty": False,
            }
        )
        return out

    rng = np.random.default_rng(seed)
    blocks = stats.shape[1]
    probs = np.full(blocks, 1.0 / blocks)
    cx = rng.multinomial(blocks, probs, size=bootstraps)
    cy = (
        rng.multinomial(blocks, probs, size=bootstraps)
        if defect == "independent-bootstrap"
        else cx
    )
    deltas = []
    mus = []
    zxs = []
    zys = []
    sample_delta = np.full(bootstraps, np.nan, dtype=np.float64)
    sample_mu = np.full(bootstraps, np.nan, dtype=np.float64)
    for sample_index, (bx, by) in enumerate(zip(cx, cy)):
        b_ex, b_ey = aggregate_curves(stats, bx, by)
        bpx, bpy, bd, bm = _fit_pair(
            b_ex,
            b_ey,
            sector,
            apply_gates=effective_gates,
            defect=defect,
            baseline=baseline,
            fit_mode=fit_mode,
        )
        if bpx.valid and bpy.valid and bd is not None and bm is not None:
            assert bpx.z is not None and bpy.z is not None
            zxs.append(bpx.z)
            zys.append(bpy.z)
            deltas.append(bd)
            mus.append(bm)
            sample_delta[sample_index] = bd
            sample_mu[sample_index] = bm
    valid_fraction = len(deltas) / bootstraps
    out["bootstrap_valid"] = len(deltas)
    out["bootstrap_valid_fraction"] = valid_fraction
    if not deltas:
        out["valid_after_uncertainty"] = False
        return out

    def summary(values: list[float]) -> dict:
        a = np.asarray(values)
        lo, hi = np.quantile(a, [0.025, 0.975])
        return {
            "mean": float(np.mean(a)),
            "sd": float(np.std(a, ddof=1)) if len(a) > 1 else 0.0,
            "lo95": float(lo),
            "hi95": float(hi),
            "width95": float(hi - lo),
        }

    out["bootstrap"] = {
        "zx": summary(zxs),
        "zy": summary(zys),
        "delta": summary(deltas),
        "mu": summary(mus),
    }
    if keep_bootstrap:
        out["bootstrap_samples"] = {
            "delta": sample_delta.tolist(),
            "mu": sample_mu.tolist(),
        }
    arm_width_ok = (
        out["bootstrap"]["zx"]["width95"] <= MAX_ARM_CI_WIDTH
        and out["bootstrap"]["zy"]["width95"] <= MAX_ARM_CI_WIDTH
    )
    out["valid_after_uncertainty"] = bool(
        valid_fraction >= MIN_BOOTSTRAP_VALID and arm_width_ok
    )
    if not out["valid_after_uncertainty"]:
        reasons = []
        if valid_fraction < MIN_BOOTSTRAP_VALID:
            reasons.append("bootstrap-valid fraction")
        if not arm_width_ok:
            reasons.append("arm CI width")
        out["uncertainty_rejection"] = ", ".join(reasons)
    return out


def measure_cube(
    cube: np.ndarray,
    sector: str,
    *,
    block_grid: int = BLOCK_GRID,
    bootstraps: int = BOOTSTRAPS,
    seed: int = BOOTSTRAP_SEED,
    apply_gates: bool = True,
    defect: str | None = None,
    fit_mode: str = "log",
    baseline: float | None = None,
    keep_bootstrap: bool = False,
) -> dict:
    stats = cube_sufficient_stats(cube, block_grid=block_grid)
    return measure_stats(
        stats,
        sector,
        bootstraps=bootstraps,
        seed=seed,
        apply_gates=apply_gates,
        defect=defect,
        fit_mode=fit_mode,
        baseline=baseline,
        keep_bootstrap=keep_bootstrap,
    )


def response_block_stats(
    ex_blocks: np.ndarray,
    ey_blocks: np.ndarray,
    mean_luma: float = 1.0,
) -> np.ndarray:
    """Adapt independently generated block-response cubes for bootstrap tests."""
    ex = np.asarray(ex_blocks, dtype=np.float64)
    ey = np.asarray(ey_blocks, dtype=np.float64)
    if ex.shape != ey.shape or ex.ndim != 2:
        raise ValueError("response blocks must both be [frame,block]")
    ones = np.ones_like(ex)
    return np.stack((ex, ey, mean_luma * ones, ones), axis=2)
