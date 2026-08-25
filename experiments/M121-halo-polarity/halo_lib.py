"""M121 -- the halo edge-profile instrument.

WHAT IT MEASURES
================

At a step edge, take the perpendicular profile `p(d)`, oriented so that luma
INCREASES with `d`.  Call the far plateaus `lo` (d << 0) and `hi` (d >> 0) and
the amplitude `A = hi - lo > 0`.  Per side, both dimensionless:

    bright(d) = (p(+d) - hi) / A        d >= 0
    dark(d)   = (lo - p(-d)) / A        d >= 0

Both are POSITIVE when that side is pushed AWAY from the other side, i.e. when
the artifact raises local edge contrast.  The two live hypotheses are then read
off a linear decomposition of the pair:

    S(d) = bright(d) - dark(d)      ADDITIVE component -- both sides lifted
    C(d) = bright(d) + dark(d)      CONTRAST component -- both pushed outward

  * CONTRAST-ENHANCING (ORCH's selection-spill mechanism, an unsharp-mask
    overshoot whose polarity is set by the edge):  C > 0, S = 0.
  * ADDITIVE BRIGHT GLOW (a rim that is bright at every edge regardless of
    edge polarity):                                S > 0, C = 0.

WHY THE DECOMPOSITION AND NOT THE RAW PAIR
------------------------------------------
The edge TRANSITION itself is a confound and it is not a small one.  Inside the
transition the profile has not reached either plateau, so `bright` and `dark`
are both large and NEGATIVE there -- an artifact-free edge reads as strongly
"contrast-reducing" if the pair is read raw.  A symmetric blur makes the
transition antisymmetric about the edge centre, contributing `-e(d)` to both
`bright` and `dark`; that cancels exactly in `S` and doubles in `C`.

So `S` is transition-immune by construction and is the PRIMARY sign
discriminator.  `C` is transition-contaminated and is only read beyond a
per-edge `settle_distance()`.  The N3 plants commission both: the additive
plant must drive `S` to the planted amplitude while leaving `C` at zero, and
the contrast plant must do the reverse.  An instrument that cannot separate
them is not permitted to score a real pixel (rule 20, discipline 839).

Rule 18 -- how each statistic can be fooled:
  * `C` rises for ANY image sharper than its own far plateau suggests,
    including honest ringing from a resampler.  M93's arms are rendered with
    alignment OFF, so no resampler runs; and N1 scores an unmerged frame
    through the identical pipeline.
  * `S` rises for a genuinely brighter neighbourhood -- e.g. a level shift
    between merged and single frames -- but is per-edge plateau-normalised on
    BOTH sides, so a uniform gain or offset cancels.
  * Both are inflated if a far plateau is contaminated by a NEIGHBOURING edge,
    so isolation is enforced per side and plateau flatness is asserted.
  * `S` is only transition-immune insofar as the edge's blur is symmetric.  An
    asymmetric PSF leaks transition into `S`; N1 (a real unmerged frame, real
    PSF, identical pipeline) is the control that bounds that leak empirically.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import map_coordinates, uniform_filter

# --- profile geometry, in plane pixels ------------------------------------
DMAX = 48.0          # profile half-length
DSTEP = 0.25         # sample spacing along the normal
PLATEAU = (30.0, 45.0)   # |d| window the far plateau is taken over
NEAR = (1.5, 28.0)   # |d| window the overshoot extremum is searched in
# Bands the signed statistics are averaged over, in plane px.  The 12-18 and
# 18-24 bands straddle E1's derived spill cutoff of 22 px, so P-WIDTH is read
# off the band table and not only off a fitted width.
BANDS = ((1.5, 6.0), (6.0, 12.0), (12.0, 18.0), (18.0, 24.0), (24.0, 30.0))


def _sobel2(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """3x3 Sobel on a 2-D plane, written out.

    Rule 23: `scipy.ndimage.sobel(cube, axis=k)` smooths every axis except `k`.
    Nothing here is ever handed a cube -- these operate on one 2-D plane and the
    kernels are written explicitly so the smoothing axis cannot be implicit.
    """
    assert a.ndim == 2, a.shape
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32) / 8.0
    ky = kx.T.copy()
    from scipy.signal import convolve2d
    gx = convolve2d(a, kx[::-1, ::-1], mode="same", boundary="symm")
    gy = convolve2d(a, ky[::-1, ::-1], mode="same", boundary="symm")
    return gx.astype(np.float32), gy.astype(np.float32)


def gradient(a: np.ndarray, smooth: int = 2):
    """Smoothed gradient field.  Returns (gx, gy, mag)."""
    b = uniform_filter(a.astype(np.float32), size=2 * smooth + 1) if smooth else a.astype(np.float32)
    gx, gy = _sobel2(b)
    return gx, gy, np.hypot(gx, gy)


def edge_seeds(mag: np.ndarray, frac: float, border: int, stride: int, rng) -> np.ndarray:
    """Candidate edge pixels: local maxima of |grad| above a percentile.

    `frac` is a percentile of the interior |grad| distribution, so the threshold
    is a property of the image being scanned rather than a DN constant carried
    across images (AGENTS.md "never carry a threshold across stacks").
    """
    h, w = mag.shape
    m = mag[border:h - border, border:w - border]
    thr = np.percentile(m, frac)
    # non-maximum suppression on a 3x3 neighbourhood
    from scipy.ndimage import maximum_filter
    peak = (mag >= maximum_filter(mag, size=3)) & (mag > thr)
    peak[:border] = peak[-border:] = False
    peak[:, :border] = peak[:, -border:] = False
    ys, xs = np.nonzero(peak)
    idx = np.arange(ys.size)
    rng.shuffle(idx)
    idx = idx[::stride] if stride > 1 else idx
    return np.stack([ys[idx], xs[idx]], axis=1)


def sample_profile(img: np.ndarray, y: float, x: float, ny: float, nx: float,
                   dmax: float = DMAX, dstep: float = DSTEP) -> tuple[np.ndarray, np.ndarray]:
    d = np.arange(-dmax, dmax + 0.5 * dstep, dstep, dtype=np.float64)
    ys = y + d * ny
    xs = x + d * nx
    p = map_coordinates(img, np.stack([ys, xs]), order=1, mode="nearest")
    return d, p


def _recentre(d: np.ndarray, p: np.ndarray) -> float:
    """Sub-pixel 50%-crossing nearest d = 0, so profiles align before averaging."""
    lo = np.median(p[(d <= -PLATEAU[0]) & (d >= -PLATEAU[1])])
    hi = np.median(p[(d >= PLATEAU[0]) & (d <= PLATEAU[1])])
    if hi <= lo:
        return np.nan
    half = 0.5 * (lo + hi)
    s = np.sign(p - half)
    cross = np.nonzero(np.diff(s) > 0)[0]
    if cross.size == 0:
        return np.nan
    k = cross[np.argmin(np.abs(d[cross]))]
    # linear interpolation between k and k+1
    y0, y1 = p[k], p[k + 1]
    if y1 == y0:
        return float(d[k])
    return float(d[k] + (half - y0) / (y1 - y0) * (d[k + 1] - d[k]))


def measure_edge(img: np.ndarray, y: int, x: int, gx: float, gy: float,
                 dmax: float = DMAX, flat_tol: float = 0.10):
    """One edge -> a recentred, amplitude-normalised profile plus per-side flags.

    Returns None when the edge has no usable step at this scale.
    """
    n = np.hypot(gx, gy)
    if n <= 0:
        return None
    ny, nx = gy / n, gx / n          # normal points toward INCREASING luma
    d, p = sample_profile(img, y, x, ny, nx, dmax)
    shift = _recentre(d, p)
    if not np.isfinite(shift) or abs(shift) > 4.0:
        return None
    d2, p2 = sample_profile(img, y + shift * ny, x + shift * nx, ny, nx, dmax)

    mlo = (d2 <= -PLATEAU[0]) & (d2 >= -PLATEAU[1])
    mhi = (d2 >= PLATEAU[0]) & (d2 <= PLATEAU[1])
    lo, hi = float(np.median(p2[mlo])), float(np.median(p2[mhi]))
    A = hi - lo
    if A <= 0:
        return None
    # plateau flatness, per side, as a fraction of A.  A side that fails is not
    # used; it is not a reason to drop the other side.
    sd_lo = float(p2[mlo].std()) / A
    sd_hi = float(p2[mhi].std()) / A
    # 10-90% rise distance: the edge's own transition width, measured on the
    # monotone part of the profile so a rim beyond the 90% point cannot inflate
    # it.  This is what tells us whether the instrument is being run at the
    # operating point it was commissioned at.
    lo90, hi10 = lo + 0.10 * A, lo + 0.90 * A
    inside = d2[(p2 >= lo90) & (p2 <= hi10) & (np.abs(d2) <= PLATEAU[0])]
    rise = float(inside.max() - inside.min()) if inside.size >= 2 else np.nan
    return {
        "d": d2, "p": p2, "lo": lo, "hi": hi, "A": A,
        "sd_lo": sd_lo, "sd_hi": sd_hi, "rise": rise,
        "flat_lo": sd_lo <= flat_tol, "flat_hi": sd_hi <= flat_tol,
        "ny": ny, "nx": nx, "y": y + shift * ny, "x": x + shift * nx,
    }


def overshoot_curves(e: dict):
    """Decompose the near-edge departure into an ADDITIVE and a CONTRAST part.

    With the profile oriented so luma increases with `d`, and `lo`/`hi` the far
    plateaus, `A = hi - lo`:

        bright(d) = (p(+d) - hi) / A        d >= 0
        dark(d)   = (lo - p(-d)) / A        d >= 0

    Both are positive when that side is pushed AWAY from the other side.  Then

        S(d) = bright(d) - dark(d)   = [(p(+d)-hi) + (p(-d)-lo)] / A
        C(d) = bright(d) + dark(d)   = [(p(+d)-hi) - (p(-d)-lo)] / A

    `S` is the component that lifts BOTH sides -- an additive glow.  `C` is the
    component that pushes both sides outward -- a contrast overshoot.

    **`S` is immune to the edge transition by construction.**  A symmetric blur
    makes the profile antisymmetric about the edge centre, so the transition
    contributes `-e(d)` to `bright` and `-e(d)` to `dark`, which cancels in `S`
    and doubles in `C`.  That is why `S` is the primary sign discriminator: it
    needs no arbitrary exclusion zone, and N3's additive plant is the control
    that proves it fires.  `C` is contaminated by the transition near `d = 0`
    and is only read beyond the per-edge settle distance.
    """
    d, p, A, lo, hi = e["d"], e["p"], e["A"], e["lo"], e["hi"]
    dist = d[d >= 0]
    bright = (p[d >= 0] - hi) / A
    dark = (lo - p[d <= 0][::-1]) / A
    return dist, bright, dark, bright - dark, bright + dark


def settle_distance(e: dict, frac: float = 0.05, hold: float = 2.0) -> float:
    """How far out the monotone edge TRANSITION reaches, in px.

    Walking outward from `d = 0` on each side, the first distance at which the
    profile's own |slope| has been below `frac` of its peak for `hold` px.  A
    planted rim is flat in its interior, so its plateau is *inside* this
    distance and the rim is not excluded by it; only the ramp is.
    """
    d, p = e["d"], e["p"]
    step = float(d[1] - d[0])
    slope = np.abs(np.diff(p)) / step
    dm = 0.5 * (d[1:] + d[:-1])
    thr = frac * slope.max()
    need = int(round(hold / step))
    out = 0.0
    for sgn in (+1, -1):
        m = (dm * sgn) >= 0
        s = slope[m]
        x = np.abs(dm[m])
        order = np.argsort(x)
        s, x = s[order], x[order]
        quiet = s < thr
        run = 0
        found = np.nan
        for i in range(quiet.size):
            run = run + 1 if quiet[i] else 0
            if run >= need:
                found = float(x[i - need + 1])
                break
        out = max(out, 0.0 if not np.isfinite(found) else found)
    return out


def peak_in_near(dist: np.ndarray, curve: np.ndarray, near=NEAR) -> tuple[float, float]:
    """SIGNED extremum of `curve` in the near band.

    This used to be a plain `argmax`, which cannot return a negative number --
    so the instrument was structurally incapable of reporting the additive-glow
    case it exists to discriminate, and N3's specificity plant caught it before
    a single real pixel had been scored (rule 20, discipline 822).  It is now
    the value at the argmax of |curve|, which carries its sign.
    """
    m = (dist >= near[0]) & (dist <= near[1])
    if not m.any():
        return np.nan, np.nan
    k = int(np.argmax(np.abs(curve[m])))
    return float(curve[m][k]), float(dist[m][k])


def band_mean(dist: np.ndarray, curve: np.ndarray, a: float, b: float) -> float:
    """Signed mean of `curve` over `a <= d <= b`.  Noise-averaged, keeps sign."""
    m = (dist >= a) & (dist <= b)
    return float(curve[m].mean()) if m.any() else np.nan


def width_at_frac(dist: np.ndarray, curve: np.ndarray, peak: float, frac: float,
                  d0: float = NEAR[0]) -> float:
    """Outermost distance at which `curve` still carries `frac` of `peak`.

    Sign-aware: `curve * sign(peak)` is compared against `frac * |peak|`, so a
    negative (additive-glow) rim gets a width too.
    """
    if not np.isfinite(peak) or peak == 0.0:
        return np.nan
    sgn = np.sign(peak)
    m = (dist >= d0) & (dist <= PLATEAU[0])
    above = dist[m][(curve[m] * sgn) >= frac * abs(peak)]
    return float(above.max()) if above.size else np.nan


def outer_cutoff(dist: np.ndarray, curve: np.ndarray, peak: float,
                 d0: float, frac: float = 0.10) -> float:
    """First distance beyond `d0` at which `curve` drops below `frac` of `peak`
    and STAYS below.  This is the statistic P-WIDTH actually predicts: the
    box-mean cascade has a hard cutoff, so the rim should not merely decay but
    stop."""
    if not np.isfinite(peak) or peak == 0.0:
        return np.nan
    sgn = np.sign(peak)
    m = (dist >= d0) & (dist <= PLATEAU[0])
    x, c = dist[m], curve[m] * sgn
    below = c < frac * abs(peak)
    if not below.any():
        return np.nan
    # last index that is still above threshold; cutoff is just past it
    above_idx = np.nonzero(~below)[0]
    if above_idx.size == 0:
        return float(x[0])
    return float(x[above_idx[-1]])
