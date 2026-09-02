"""Core estimator for M-PHASE0-RHO.

All frequencies are cycles per full-resolution sensor pixel. The module never
decodes a RAW file and never imports planted synthetic truth.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import hashlib
import math
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy.optimize import least_squares
from scipy.special import logsumexp


G_SHIFT = np.array([0.5, 0.5], dtype=float)
RB_SHIFTS = (
    np.array([0.5, 0.0], dtype=float),
    np.array([0.0, 0.5], dtype=float),
    np.array([0.5, 0.5], dtype=float),
)
POWER_R0 = 0.02


def wrap_sensor_band(f: np.ndarray) -> np.ndarray:
    """Wrap frequency coordinates into [-0.5, 0.5)."""
    a = np.asarray(f, dtype=float)
    return np.mod(a + 0.5, 1.0) - 0.5


def in_green_base(f: np.ndarray, tol: float = 1e-12) -> bool:
    a = np.asarray(f, dtype=float)
    return bool(np.abs(a).sum() <= 0.5 + tol)


def in_rb_base(f: np.ndarray, tol: float = 1e-12) -> bool:
    a = np.asarray(f, dtype=float)
    return bool(np.max(np.abs(a)) <= 0.25 + tol)


def _point_key(f: np.ndarray) -> tuple[int, int]:
    a = np.asarray(f, dtype=float)
    return tuple(int(round(v * 1_000_000_000)) for v in a)


def _group_key(points: Iterable[np.ndarray]) -> tuple[tuple[int, int], ...]:
    return tuple(sorted(_point_key(p) for p in points))


def alias_groups(target: str, grid: int = 8) -> list[dict]:
    """Unique one-times CFA alias groups on the grid used by p1_bar.py.

    The returned base member is inside the sampled channel's first Brillouin
    zone. Alias members are the other representatives inside the full sensor
    Nyquist square. A white spectrum therefore has rho exactly one.
    """
    if grid <= 0:
        raise ValueError("grid must be positive")
    coords = -0.5 + (np.arange(grid, dtype=float) + 0.5) / grid
    seen: dict[tuple[tuple[int, int], ...], dict] = {}
    for fy in coords:
        for fx in coords:
            f = np.array([fx, fy], dtype=float)
            if target == "G-1x":
                points = [f, wrap_sensor_band(f + G_SHIFT)]
                bases = [p for p in points if in_green_base(p)]
            elif target == "RB-1x":
                points = [f] + [wrap_sensor_band(f + s) for s in RB_SHIFTS]
                bases = [p for p in points if in_rb_base(p)]
            else:
                raise ValueError(f"unsupported target {target!r}")
            key = _group_key(points)
            if key in seen:
                continue
            if not bases:
                raise ValueError(
                    f"{target} group has {len(bases)} base members: {points!r}"
                )
            # The 8 by 8 p1 grid lands on some Brillouin-zone boundaries, where
            # both members are valid representatives. Pick the lower radius,
            # then a fixed coordinate key on an exact tie. The final analysis
            # reports the boundary-swap sensitivity separately.
            base = np.asarray(
                min(
                    bases,
                    key=lambda p: (
                        round(float(np.linalg.norm(p)), 14),
                        _point_key(p),
                    ),
                ),
                dtype=float,
            )
            aliases = [
                np.asarray(p, dtype=float)
                for p in points
                if _point_key(p) != _point_key(base)
            ]
            seen[key] = {"base": base, "aliases": aliases}
    return list(seen.values())


def angular_log_factor(
    f: np.ndarray,
    c2: float = 0.0,
    s2: float = 0.0,
    c4: float = 0.0,
    s4: float = 0.0,
) -> np.ndarray:
    a = np.asarray(f, dtype=float)
    theta = np.arctan2(a[..., 1], a[..., 0])
    return (
        c2 * np.cos(2.0 * theta)
        + s2 * np.sin(2.0 * theta)
        + c4 * np.cos(4.0 * theta)
        + s4 * np.sin(4.0 * theta)
    )


def model_power_unit(
    f: np.ndarray,
    beta: float,
    c2: float = 0.0,
    s2: float = 0.0,
    c4: float = 0.0,
    s4: float = 0.0,
) -> np.ndarray:
    a = np.asarray(f, dtype=float)
    r = np.maximum(np.linalg.norm(a, axis=-1), POWER_R0)
    return np.power(r, -float(beta)) * np.exp(
        angular_log_factor(a, c2, s2, c4, s4)
    )


def rho_from_params(
    target: str,
    beta: float,
    angular: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
    grid: int = 8,
) -> float:
    """A2.2 ratio of mean per-alias power to mean base power."""
    c2, s2, c4, s4 = angular
    groups = alias_groups(target, grid)
    base = 0.0
    alias = 0.0
    n_alias = 0
    for group in groups:
        base += float(model_power_unit(group["base"], beta, c2, s2, c4, s4))
        for f in group["aliases"]:
            alias += float(model_power_unit(f, beta, c2, s2, c4, s4))
            n_alias += 1
    aliases_per_group = n_alias / len(groups)
    return alias / (aliases_per_group * base)


def component_ratios(
    target: str,
    beta: float,
    angular: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
    grid: int = 8,
) -> np.ndarray:
    c2, s2, c4, s4 = angular
    out = []
    for group in alias_groups(target, grid):
        bp = float(model_power_unit(group["base"], beta, c2, s2, c4, s4))
        for f in group["aliases"]:
            ap = float(model_power_unit(f, beta, c2, s2, c4, s4))
            out.append(ap / bp)
    return np.asarray(out, dtype=float)


def window_2d(n: int, kind: str) -> np.ndarray:
    if kind == "hann":
        w = np.hanning(n + 1)[:n]
    elif kind == "kaiser8":
        w = np.kaiser(n, 8.0)
    elif kind == "none":
        w = np.ones(n)
    else:
        raise ValueError(f"unsupported window {kind!r}")
    return np.outer(w, w)


def welch_psd2(
    patch: np.ndarray, tile: int = 256, window: str = "hann"
) -> tuple[np.ndarray, int]:
    """Welch PSD normalized so white variance is the expected bin power."""
    a = np.asarray(patch, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("patch must be square")
    if tile > a.shape[0] or tile < 16 or tile % 2:
        raise ValueError("tile must be even and fit inside the patch")
    step = tile // 2
    starts = list(range(0, a.shape[0] - tile + 1, step))
    win = window_2d(tile, window)
    norm = float(np.sum(win * win))
    acc = np.zeros((tile, tile), dtype=float)
    count = 0
    for y in starts:
        for x in starts:
            q = a[y : y + tile, x : x + tile]
            q = (q - float(np.mean(q))) * win
            f = np.fft.fft2(q)
            acc += (f.real * f.real + f.imag * f.imag) / norm
            count += 1
    if count == 0:
        raise ValueError("no Welch tiles")
    return acc / count, count


def gq_frequency_grid(n: int) -> tuple[np.ndarray, np.ndarray]:
    """Map GQ DFT bins to full-sensor frequency coordinates."""
    fu = np.fft.fftfreq(n)[:, None] * np.ones((1, n))
    fv = np.fft.fftfreq(n)[None, :] * np.ones((n, 1))
    fx = (fu - fv) / 2.0
    fy = (fu + fv) / 2.0
    return fx, fy


def gq_partner(fx: np.ndarray, fy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = wrap_sensor_band(np.stack([fx, fy], axis=-1) + G_SHIFT)
    return p[..., 0], p[..., 1]


def extract_gq(
    active: np.ndarray, rc: int, cc: int, size: int
) -> np.ndarray:
    """Extract the no-interpolation green quincunx patch used by M5."""
    a = np.asarray(active)
    if a.ndim != 2:
        raise ValueError("active array must be 2D")
    if rc % 2 or cc % 2:
        raise ValueError("GQ centre must be even in both sensor coordinates")
    u0 = (rc + cc) // 2
    v0 = (rc - cc) // 2
    k = np.arange(size) - size // 2
    u = (u0 + k)[:, None]
    v = (v0 + k)[None, :]
    rows = u + v
    cols = u - v + 1
    if (
        rows.min() < 0
        or cols.min() < 0
        or rows.max() >= a.shape[0]
        or cols.max() >= a.shape[1]
    ):
        raise ValueError("GQ patch leaves active array")
    return np.asarray(a[rows, cols], dtype=float)


def legal_frequency_mask(
    fx: np.ndarray, fy: np.ndarray, lattice: str
) -> np.ndarray:
    if lattice == "GQ":
        return np.abs(fx) + np.abs(fy) <= 0.5 + 1e-12
    if lattice in ("G1", "G2", "R", "B"):
        return (np.abs(fx) <= 0.25 + 1e-12) & (
            np.abs(fy) <= 0.25 + 1e-12
        )
    raise ValueError(f"unknown lattice {lattice!r}")


def sector_index(theta: np.ndarray, sectors: int = 16) -> np.ndarray:
    x = np.mod(theta + np.pi, 2.0 * np.pi)
    return np.floor(x * sectors / (2.0 * np.pi)).astype(int) % sectors


@dataclass
class FitResult:
    beta: float
    beta_se: float
    log_amplitude: float
    angular: tuple[float, float, float, float]
    rho_g: float
    rho_rb: float
    rho_g_grid16: float
    rho_g_grid32: float
    n_fit: int
    n_holdout: int
    welch_blocks: int
    max_fit_frequency: float
    frequency_span: float
    holdout_median_abs_dex: float
    holdout_p90_abs_dex: float
    fit_median_abs_dex: float
    noise_floor: float
    noise_se: float
    significant_bins: int
    total_candidate_bins: int
    component_p10: float
    component_median: float
    component_p90: float
    extrapolation_median: float
    extrapolation_max: float

    def to_dict(self) -> dict:
        d = asdict(self)
        d["angular"] = list(self.angular)
        return d


def _log_model(
    params: np.ndarray,
    base: np.ndarray,
    alias: np.ndarray,
    angular_model: bool,
) -> np.ndarray:
    alpha = float(params[0])
    beta = float(params[1])
    if angular_model:
        c2, s2, c4, s4 = (float(v) for v in params[2:6])
    else:
        c2 = s2 = c4 = s4 = 0.0
    lb = (
        -beta
        * np.log(
            np.maximum(np.linalg.norm(base, axis=-1), POWER_R0)
        )
        + angular_log_factor(base, c2, s2, c4, s4)
    )
    la = (
        -beta
        * np.log(
            np.maximum(np.linalg.norm(alias, axis=-1), POWER_R0)
        )
        + angular_log_factor(alias, c2, s2, c4, s4)
    )
    return alpha + logsumexp(np.stack([lb, la], axis=0), axis=0)


def fit_gq_powerlaw(
    patch: np.ndarray,
    noise_floor: float = 0.0,
    tile: int = 256,
    window: str = "hann",
    rmin: float = 0.04,
    rmax: float = 0.46,
    angular_model: bool = True,
    holdout_mod: int = 4,
    min_significance: float = 3.0,
) -> FitResult:
    """Fit the captured-scene power law through the GQ alias sum."""
    psd, blocks = welch_psd2(patch, tile=tile, window=window)
    fx, fy = gq_frequency_grid(tile)
    ax, ay = gq_partner(fx, fy)
    base = np.stack([fx, fy], axis=-1)
    alias = np.stack([ax, ay], axis=-1)
    r = np.hypot(fx, fy)
    theta = np.arctan2(fy, fx)

    corrected = psd - float(noise_floor)
    noise_se = float(noise_floor) / math.sqrt(max(blocks, 1))
    legal = legal_frequency_mask(fx, fy, "GQ")
    one_side = (fy > 0) | ((np.abs(fy) < 1e-15) & (fx > 0))
    candidate = legal & one_side & (r >= rmin) & (r <= rmax)
    significance = max(min_significance * noise_se, 0.0)
    positive = corrected > max(significance, np.finfo(float).tiny)
    keep = candidate & positive & np.isfinite(corrected)

    total_candidate = int(np.sum(candidate))
    significant_bins = int(np.sum(keep))
    if significant_bins < 40:
        raise ValueError(
            f"only {significant_bins} significant bins, need at least 40"
        )
    rr = r[keep]
    span = float(rr.max() / rr.min())
    if span < 2.5:
        raise ValueError(f"frequency span {span:.3f} is below 2.5")
    if float(rr.max()) < 0.25:
        raise ValueError("fit does not reach 0.25 sensor cycles/pixel")

    b = base[keep]
    a = alias[keep]
    y = np.log(corrected[keep])
    sec = sector_index(theta[keep], sectors=16)
    hold = (sec % holdout_mod) == 0
    train = ~hold
    if int(train.sum()) < 40 or int(hold.sum()) < 8:
        raise ValueError("fit or holdout sector has too few bins")

    p0 = np.array(
        [float(np.median(y)), 2.0, 0.0, 0.0, 0.0, 0.0],
        dtype=float,
    )
    if angular_model:
        lower = np.array([-100.0, 0.0, -3.0, -3.0, -3.0, -3.0])
        upper = np.array([100.0, 10.0, 3.0, 3.0, 3.0, 3.0])
        use0 = p0
    else:
        lower = np.array([-100.0, 0.0])
        upper = np.array([100.0, 10.0])
        use0 = p0[:2]

    def resid(p: np.ndarray, mask: np.ndarray) -> np.ndarray:
        return _log_model(p, b[mask], a[mask], angular_model) - y[mask]

    fit = least_squares(
        lambda p: resid(p, train),
        use0,
        bounds=(lower, upper),
        loss="soft_l1",
        f_scale=0.35 * math.log(10.0),
        max_nfev=400,
    )
    if not fit.success:
        raise ValueError(f"spectral fit failed: {fit.message}")
    params = fit.x
    beta = float(params[1])
    if angular_model:
        angular = tuple(float(v) for v in params[2:6])
    else:
        angular = (0.0, 0.0, 0.0, 0.0)

    # Local linear covariance is only a conditional fit uncertainty. The final
    # analysis uses a block and scene bootstrap.
    if fit.jac.shape[0] > fit.jac.shape[1]:
        jtj = fit.jac.T @ fit.jac
        try:
            cov = np.linalg.inv(jtj)
            scale = float(np.sum(fit.fun**2) / max(fit.fun.size - fit.x.size, 1))
            beta_se = float(math.sqrt(max(cov[1, 1] * scale, 0.0)))
        except np.linalg.LinAlgError:
            beta_se = float("nan")
    else:
        beta_se = float("nan")

    pred_all = _log_model(params, b, a, angular_model)
    err_dex = np.abs(pred_all - y) / math.log(10.0)
    fit_err = err_dex[train]
    hold_err = err_dex[hold]
    rg = rho_from_params("G-1x", beta, angular, grid=8)
    rrho = rho_from_params("RB-1x", beta, angular, grid=8)
    comps = component_ratios("G-1x", beta, angular, grid=8)

    # Same-sector support is the diamond boundary along each alias direction.
    # For direction theta, r_max = 0.5 / (|cos| + |sin|).
    ratios = []
    for group in alias_groups("G-1x", 8):
        for f in group["aliases"]:
            ar = float(np.linalg.norm(f))
            at = math.atan2(float(f[1]), float(f[0]))
            direct = 0.5 / (abs(math.cos(at)) + abs(math.sin(at)))
            ratios.append(max(1.0, ar / direct))

    return FitResult(
        beta=beta,
        beta_se=beta_se,
        log_amplitude=float(params[0]),
        angular=angular,
        rho_g=rg,
        rho_rb=rrho,
        rho_g_grid16=rho_from_params("G-1x", beta, angular, grid=16),
        rho_g_grid32=rho_from_params("G-1x", beta, angular, grid=32),
        n_fit=int(train.sum()),
        n_holdout=int(hold.sum()),
        welch_blocks=blocks,
        max_fit_frequency=float(rr.max()),
        frequency_span=span,
        holdout_median_abs_dex=float(np.median(hold_err)),
        holdout_p90_abs_dex=float(np.percentile(hold_err, 90)),
        fit_median_abs_dex=float(np.median(fit_err)),
        noise_floor=float(noise_floor),
        noise_se=noise_se,
        significant_bins=significant_bins,
        total_candidate_bins=total_candidate,
        component_p10=float(np.percentile(comps, 10)),
        component_median=float(np.median(comps)),
        component_p90=float(np.percentile(comps, 90)),
        extrapolation_median=float(np.median(ratios)),
        extrapolation_max=float(np.max(ratios)),
    )


def peak_frequency_sensor(
    patch: np.ndarray, lattice: str = "GQ"
) -> tuple[float, float]:
    """Frequency of the strongest non-DC Fourier bin in sensor units."""
    a = np.asarray(patch, dtype=float)
    f = np.fft.fft2(a - float(np.mean(a)))
    p = f.real * f.real + f.imag * f.imag
    p[0, 0] = 0.0
    i, j = np.unravel_index(int(np.argmax(p)), p.shape)
    fu = float(np.fft.fftfreq(a.shape[0])[i])
    fv = float(np.fft.fftfreq(a.shape[1])[j])
    if lattice == "GQ":
        return (fu - fv) / 2.0, (fu + fv) / 2.0
    if lattice in ("G1", "G2", "R", "B"):
        return fv / 2.0, fu / 2.0
    raise ValueError(f"unknown lattice {lattice!r}")


def real_cross_psd(
    a: np.ndarray,
    b: np.ndarray,
    tile: int = 256,
    window: str = "hann",
    shift_sensor: tuple[float, float] = (0.0, 0.0),
) -> tuple[np.ndarray, int]:
    """Real, phase-corrected Welch cross-periodogram for two GQ patches."""
    x = np.asarray(a, dtype=float)
    y = np.asarray(b, dtype=float)
    if x.shape != y.shape or x.ndim != 2 or x.shape[0] != x.shape[1]:
        raise ValueError("cross-spectrum patches must be equal square arrays")
    step = tile // 2
    starts = list(range(0, x.shape[0] - tile + 1, step))
    win = window_2d(tile, window)
    norm = float(np.sum(win * win))
    acc = np.zeros((tile, tile), dtype=complex)
    count = 0
    for i in starts:
        for j in starts:
            xa = x[i : i + tile, j : j + tile]
            ya = y[i : i + tile, j : j + tile]
            fa = np.fft.fft2((xa - float(np.mean(xa))) * win)
            fb = np.fft.fft2((ya - float(np.mean(ya))) * win)
            acc += fa * np.conjugate(fb) / norm
            count += 1
    acc /= max(count, 1)
    fx, fy = gq_frequency_grid(tile)
    dx, dy = shift_sensor
    # b(x) = a(x + d) gives B = A exp(+2 pi i f.d), hence
    # A conj(B) carries exp(-2 pi i f.d). Multiply by the positive ramp.
    ramp = np.exp(2j * np.pi * (fx * dx + fy * dy))
    return np.real(acc * ramp), count


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()
