"""Independent stimuli for XSPEC commissioning.

This module deliberately does not import xspec_lib.  Its frequency geometry and
image transforms are separate implementations so estimator defects cannot write
their own expected inputs.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, shift as scipy_shift


def textured_scene(n: int = 128, seed: int = 424242) -> np.ndarray:
    rng = np.random.default_rng(seed)
    white = rng.normal(size=(n, n))
    scene = gaussian_filter(white, 0.75, mode="reflect")
    y, x = np.mgrid[:n, :n]
    scene += 0.35 * np.cos(2.0 * np.pi * (0.071 * x + 0.043 * y))
    scene += 0.25 * np.sin(2.0 * np.pi * (0.113 * x - 0.037 * y))
    scene -= float(np.mean(scene))
    scene /= float(np.std(scene))
    return scene * 600.0 + 1800.0


def spatial_shift_gq(scene: np.ndarray, du: float, dv: float) -> np.ndarray:
    """Return moving(u,v)=scene(u+du,v+dv), using an independent spline path."""
    return scipy_shift(
        np.asarray(scene, dtype=float),
        shift=(-float(du), -float(dv)),
        order=3,
        mode="reflect",
        prefilter=True,
    )


def odd_phase_pair(
    scene: np.ndarray,
    strength: float = 0.55,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Apply opposite Hermitian trefoil phases; both outputs remain real."""
    a = np.asarray(scene, dtype=float)
    n = a.shape[0]
    fu = np.fft.fftfreq(n)[:, None] * np.ones((1, n))
    fv = np.fft.fftfreq(n)[None, :] * np.ones((n, 1))
    fx = (fu - fv) / 2.0
    fy = (fu + fv) / 2.0
    basis = (fx**3 - 3.0 * fx * fy**2) / (0.22**3)
    phase = float(strength) * basis
    f = np.fft.fft2(a - float(np.mean(a)))
    plus = np.fft.ifft2(f * np.exp(1j * phase)).real + float(np.mean(a))
    minus = np.fft.ifft2(f * np.exp(-1j * phase)).real + float(np.mean(a))
    return plus, minus, {
        "strength": float(strength),
        "basis_rms_006_022": float(
            np.sqrt(np.mean(basis[(np.hypot(fx, fy) >= 0.06) & (np.hypot(fx, fy) < 0.22)] ** 2))
        ),
    }


def even_blur_translated_pair(
    scene: np.ndarray,
    sigma: float = 1.2,
    du: float = 0.31,
    dv: float = -0.22,
) -> tuple[np.ndarray, np.ndarray, dict]:
    base = gaussian_filter(np.asarray(scene, dtype=float), sigma, mode="reflect")
    moved = spatial_shift_gq(base, du, dv)
    return moved, base, {
        "sigma": float(sigma),
        "du": float(du),
        "dv": float(dv),
        "dx_sensor": float(du - dv),
        "dy_sensor": float(du + dv),
    }


def noisy_pairs(
    count: int,
    sigma: float,
    *,
    seed: int,
    scene: np.ndarray | None = None,
) -> list[tuple[np.ndarray, np.ndarray]]:
    base = textured_scene() if scene is None else np.asarray(scene, dtype=float)
    rng = np.random.default_rng(seed)
    return [
        (
            base + rng.normal(0.0, sigma, size=base.shape),
            base + rng.normal(0.0, sigma, size=base.shape),
        )
        for _ in range(count)
    ]


def independent_grid_counts(n: int) -> dict:
    """Loop implementation of the registered GQ frequency predicate."""
    counts = {}
    bands = {
        "registration": (0.02, 0.12),
        "odd": (0.06, 0.22),
        "inv0": (0.06, 0.12),
        "inv1": (0.12, 0.18),
        "inv2": (0.18, 0.26),
    }
    values = np.fft.fftfreq(n)
    for name, (lo, hi) in bands.items():
        total = 0
        for u in values:
            for v in values:
                fx = (float(u) - float(v)) / 2.0
                fy = (float(u) + float(v)) / 2.0
                legal = abs(fx) + abs(fy) <= 0.5
                one_side = fy > 0.0 or (fy == 0.0 and fx > 0.0)
                radius = float(np.hypot(fx, fy))
                if legal and one_side and lo <= radius < hi:
                    total += 1
        counts[name] = total
    return counts

