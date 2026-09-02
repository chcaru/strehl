"""M-PHASE0-ZFIELD shared estimators.

Everything here is written against the preregistration in
`experiments/M-PHASE0-ZFIELD/PREREGISTRATION.md` sections 4 and 5. No statistic
in this file was tuned after looking at a result.

Units are frame indices throughout. See preregistration limit 3: physical step
size per stack is NOT FOUND in the corpus, and A5's admission rule is written in
frame-index units anyway, so no conversion is required for the bar.
"""

import numpy as np

# 5-point 4th-difference kernel. Annihilates any local cubic, so a smooth focus
# curve contributes nothing to leading order. Sum of squares is 1+16+36+16+1 = 70.
D4_KERNEL = np.array([1.0, -4.0, 6.0, -4.0, 1.0])
D4_SS = 70.0
MAD_TO_SD = 1.0 / 0.674489750196082


def fourth_diff(cube):
    """4th difference along the frame axis. cube is [frame, y, x]."""
    if cube.shape[0] < 5:
        raise ValueError("fourth_diff needs at least 5 frames")
    c = cube.astype(np.float64, copy=False)
    return (
        c[0:-4] - 4.0 * c[1:-3] + 6.0 * c[2:-2] - 4.0 * c[3:-1] + c[4:]
    )


def sigma_r(cube):
    """Per-pixel response noise sd, measured from the cube itself.

    MAD across the frame axis of the 4th difference, converted to a Gaussian sd
    and divided by sqrt(70) to undo the kernel's noise gain. Robust to the peak's
    real structure because the peak is a minority of frames.
    """
    d = fourth_diff(cube)
    med = np.median(d, axis=0)
    mad = np.median(np.abs(d - med), axis=0)
    return (mad * MAD_TO_SD) / np.sqrt(D4_SS)


def peak_stats(cube):
    """argmax frame, parabola second difference D, and sub-frame zhat.

    Returns (k, D, zhat, interior). D = y_l + y_r - 2*y_c is negative at a
    maximum and equals 2a for the fitted parabola y = a x^2 + b x + c.
    `interior` is False where the argmax is on the first or last frame, so no
    three-point fit exists.
    """
    n = cube.shape[0]
    k = np.argmax(cube, axis=0).astype(np.int32)
    interior = (k > 0) & (k < n - 1)
    ks = np.clip(k, 1, n - 2)
    yy, xx = np.indices(k.shape)
    y_l = cube[ks - 1, yy, xx].astype(np.float64)
    y_c = cube[ks, yy, xx].astype(np.float64)
    y_r = cube[ks + 1, yy, xx].astype(np.float64)
    D = y_l + y_r - 2.0 * y_c
    with np.errstate(divide="ignore", invalid="ignore"):
        off = np.where(D < 0.0, (y_l - y_r) / (2.0 * D), np.nan)
    # A three-point parabola cannot place its peak outside the middle interval.
    off = np.where(np.abs(off) <= 0.5, off, np.nan)
    zhat = ks.astype(np.float64) + off
    return k, D, zhat, interior


def sigma_z(sig_r, D, off=None):
    """First-order peak-location sd. DIAGNOSTIC ONLY -- see Amendment 1.

    sigma_r * sqrt(1 + 12 * off^2) / (|D| * sqrt(2)), the general-offset form of
    preregistration section 4. `off` is the sub-frame offset; omitting it
    reproduces the symmetric-point form that section 4 registered and Amendment
    A1.1 disclosed as an error.

    Amendment A1.2 retired this estimator for census use: even corrected it
    under-reports by 1.34x against planted truth, and Amendment A1.3 shows it
    calls 90-98% of a pure-noise cube confidently placeable. Use
    `bootstrap_sigma_z`. This remains only so the note can quote both numbers.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        s = sig_r / (np.abs(D) * np.sqrt(2.0))
        if off is not None:
            s = s * np.sqrt(1.0 + 12.0 * np.nan_to_num(off) ** 2)
    return np.where(D < 0.0, s, np.inf)


BOOT_WIN, BOOT_ORD, BOOT_REPS = 9, 3, 64


def bootstrap_sigma_z(curves, sig_r, reps=BOOT_REPS, seed=7,
                      win=BOOT_WIN, order=BOOT_ORD):
    """Per-pixel parametric bootstrap sd of zhat, in frame units.

    `curves` is [frame, P], `sig_r` is [P]. Registered by Amendment A1.2 as the
    census estimator. Smooths the measured curve to a working truth, adds fresh
    noise at each pixel's own measured sigma_r, and re-runs the *actual*
    argmax-plus-parabola estimator, so every discreteness the real estimator has
    is inherited rather than modelled.

    Commissioned in z2_controls C2 (ratio 1.139 against planted truth, erring
    conservative) and C4 (a pure-noise cube reports sigma_z of order the stack
    length, so it is correctly called unplaceable).
    """
    from scipy.signal import savgol_filter

    n, P = curves.shape
    if n < win:
        raise ValueError(f"bootstrap needs at least {win} frames, got {n}")
    sm = savgol_filter(curves.astype(np.float64), win, order, axis=0, mode="interp")
    rng = np.random.default_rng(seed)
    cols = np.arange(P)
    z = np.empty((reps, P))
    for r in range(reps):
        c = sm + sig_r[None, :] * rng.standard_normal((n, P))
        k = np.argmax(c, axis=0)
        ks = np.clip(k, 1, n - 2)
        y_l, y_c, y_r = c[ks - 1, cols], c[ks, cols], c[ks + 1, cols]
        D = y_l + y_r - 2.0 * y_c
        with np.errstate(divide="ignore", invalid="ignore"):
            off = np.where(D < 0.0, (y_l - y_r) / (2.0 * D), 0.0)
        off = np.where(np.abs(off) <= 0.5, off, 0.0)
        z[r] = ks + off
    return np.std(z, axis=0)


def noise_autocorr(cube, max_lag=24, n_frames=8, seed=0):
    """Spatial autocorrelation of the response noise, along x and along y.

    Uses the 4th-difference field, which is noise-dominated by construction, and
    a random subset of its frames. Returns (rho_x, rho_y), each length max_lag+1
    with rho[0] == 1.
    """
    d = fourth_diff(cube)
    rng = np.random.default_rng(seed)
    idx = rng.choice(d.shape[0], size=min(n_frames, d.shape[0]), replace=False)
    f = d[np.sort(idx)]
    f = f - f.mean(axis=(1, 2), keepdims=True)
    denom = float(np.mean(f * f))
    out = []
    for axis in (2, 1):
        rho = np.empty(max_lag + 1)
        rho[0] = 1.0
        for L in range(1, max_lag + 1):
            a = np.take(f, range(0, f.shape[axis] - L), axis=axis)
            b = np.take(f, range(L, f.shape[axis]), axis=axis)
            rho[L] = float(np.mean(a * b)) / denom
        out.append(rho)
    return out[0], out[1]


def n_eff(rho_x, rho_y, w):
    """Effective independent sample count in a w x w window under correlated noise.

    Var(mean of w^2 correlated samples) = sigma^2 * S_x * S_y / w^4 with
    S = sum_{d=-(w-1)}^{w-1} (w - |d|) * rho(|d|). Independent noise gives
    S_x = S_y = w and hence n_eff = w^2; fully correlated noise gives
    S = w^2 and hence n_eff = 1.
    """
    def s_of(rho):
        tot = float(w) * 1.0
        for d in range(1, w):
            r = rho[d] if d < len(rho) else 0.0
            tot += 2.0 * (w - d) * r
        return tot
    sx, sy = s_of(rho_x), s_of(rho_y)
    denom = sx * sy
    if denom <= 0.0:
        return 1.0
    return max(1.0, min(float(w) ** 4 / denom, float(w) ** 2))


def partition(sz_pp, half, gain):
    """EASY / WINNABLE / LOST fractions over the finite-sigma_z pixels.

    gain is the pooling factor sqrt(n_eff), so sz_surface = sz_pp / gain.
    Returns (easy, winnable, lost, n_valid) with the three as fractions of
    n_valid. Pixels with non-finite sigma_z are counted as LOST, because the
    surface cannot place them either.
    """
    finite = np.isfinite(sz_pp)
    n_valid = int(sz_pp.size)
    sz_s = np.where(finite, sz_pp / gain, np.inf)
    easy = np.count_nonzero(finite & (sz_pp <= half))
    win = np.count_nonzero(finite & (sz_pp > half) & (sz_s <= half))
    lost = n_valid - easy - win
    return easy / n_valid, win / n_valid, lost / n_valid, n_valid


def quantiles(a, qs=(5, 25, 50, 75, 95)):
    f = a[np.isfinite(a)]
    if f.size == 0:
        return {str(q): None for q in qs}
    v = np.percentile(f, qs)
    return {str(q): float(x) for q, x in zip(qs, v)}
