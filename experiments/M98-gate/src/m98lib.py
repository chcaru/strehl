"""M98 -- library for the gate adjudication.

WHAT THIS IS
  Both contested quantities, computed from the SAME pair of half-merges:
    A_hf   band-integrated ring CROSS-power  -- M85's "high-frequency amplitude",
           made noise-free by taking the cross-power of two renders with
           independent noise instead of the auto-power of one.
    dsig   m57lib's equivalent-Gaussian-blur difference in px -- M92's quantity,
           unmodified, imported not reimplemented.

  The reason they must come from the same data: the gate changes the merge's
  noise by ~6.6x (fact 1196), and a single-render band-power metric cannot tell
  signal from noise.  M85's instrument is an auto-power and is therefore
  inflated at low gate by the noise it carries.  That inflation pushes M85's
  ratio DOWN (its denominator is the noisy gate-0 reading), so 0.985x is a lower
  bound on true HF retention -- M85's conclusion survives its own confound, and
  this library removes the confound rather than arguing about it.

WHAT IS IMPORTED AND FROZEN
  m57lib   RingStats, dsig, band_index, F_SIG   (rule 15 -- never edited here)
  m41lib   hp_sd                                (frozen)

RULE NOTES
  rule 9   every headline has a flat-ROI twin and it is computed FIRST.
  rule 10  sigma_flat is a TEMPORAL sigma, sd of (a-b)/2 over two half-merges
           with disjoint frames.  No spatial sd is compared to it.
  rule 18  fooling directions are on each function.
  rule 23  no separable filter is ever applied to an array with a frame axis.
"""
import hashlib
import os
import sys

import numpy as np
import tifffile

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXP = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_EXP, "m57-shape-metric", "src"),
           os.path.join(_EXP, "m46-detail-metric", "src"),
           os.path.join(_EXP, "m41-r3-kill", "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import m57lib as K       # noqa: E402  frozen
import m41lib as L1      # noqa: E402  frozen

OUT = os.path.join(os.path.dirname(_HERE), "out")
os.makedirs(OUT, exist_ok=True)

FRAMES = r"C:\dev\strehl-out\M98\frames"
RENDERS = r"C:\dev\strehl-out\M98\renders"
LOGS = r"C:\dev\strehl-out\M98\logs"

GATES = (0.0, 0.5, 1.0, 2.0, 4.0)
ARMS = ("ALN", "ZOOM")

ROI = 512
COLS, ROWS = 6, 4

# Bands, fixed at pre-registration.  F_SIG = 0.2762 cyc/px is fact 27's measured
# optical cutoff at f/11; nothing above it is scene signal.
F_LO_DSIG, F_HI_DSIG = 0.05, K.F_SIG      # m57lib's own band, unchanged
F_LO_HF, F_HI_HF = 0.15, K.F_SIG          # the high half -- M85's "HF amplitude"


def render_path(stack, arm, gate, half):
    return os.path.join(RENDERS, f"{stack}-{arm}-g{gate:g}-{half}.tif")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_rgb(path):
    """16-bit RGB TIFF -> float64 (H, W, 3).  No scaling, no gamma."""
    a = tifffile.imread(path)
    if a.ndim != 3 or a.shape[2] != 3:
        raise ValueError(f"{path}: expected HxWx3, got {a.shape}")
    return a.astype(np.float64)


def green(path):
    """The green plane of a binned linear camera-native render.

    The merge emits G = (G1+G2)/2 per sensor quad, so one output pixel is one
    real quad and the green plane is the measurement plane the corpus uses.
    """
    return read_rgb(path)[:, :, 1]


def roi_grid(h, w, n=ROI, cols=COLS, rows=ROWS):
    """Procedural 6x4 lattice of nxn ROIs.  Defined before any number existed so
    it cannot be chosen to suit a result."""
    out = []
    for j in range(rows):
        cy = int(round(h * (2 * j + 1) / (2.0 * rows)))
        for i in range(cols):
            cx = int(round(w * (2 * i + 1) / (2.0 * cols)))
            y = min(max(cy - n // 2, 0), h - n)
            x = min(max(cx - n // 2, 0), w - n)
            out.append((int(x), int(y)))
    return out


def crop(a, xy, n=ROI):
    x, y = xy
    return a[y:y + n, x:x + n]


def hp_sd(a):
    """m41lib's frozen 9x9 high-pass sd.  The same statistic M92 stratified on,
    so the terciles here and there mean the same thing."""
    return L1.hp_sd(a)


def a_hf(rs, f_lo=F_LO_HF, f_hi=F_HI_HF):
    """Band-integrated ring CROSS-power -- M85's quantity, noise-free.

    Rule 18: rises if the merge manufactures detail COMMON to both halves
    (shared resampling ringing, PRNU, aliasing).  Admissible against collapse,
    inadmissible as proof of quality.  It cannot be raised by anything
    independent between the halves, which is all of shot and read noise.
    Returns NaN if any ring in the band is non-positive -- the caller checks.
    """
    idx = K.band_index(rs.f, f_lo, f_hi)
    c = rs.c[idx]
    if np.any(c <= 0):
        return np.nan
    return float(c.mean())


def sigma_flat(a, b):
    """TEMPORAL sigma of one half-merge, from the difference of two half-merges
    with disjoint frames: sd((a-b)/2) estimates each half's own noise when the
    two carry the same signal.  Rule 10: this is never compared to a spatial sd.

    KNOWN CONTAMINATION, stated where it is used.  The two halves do not carry
    exactly the same signal: at a low gate each half elects a different frame,
    so (a-b) carries half-to-half SIGNAL disagreement as well as noise, and that
    term does not average down.  It therefore OVER-states the noise most at low
    gate, which biases the noise-reduction ratio TOWARDS 1 and makes it a
    conservative, insensitive bar.  `n_incoh` below is the clean replacement.
    """
    d = (a - b) * 0.5
    return float(d.std())


def n_incoh(rs, f_lo=F_LO_HF, f_hi=F_HI_HF):
    """Band-integrated INCOHERENT power of a half-merge pair: the part of the
    spectrum the two halves do NOT share.

        N(f) = (P_a(f) + P_b(f))/2 - C(f)

    Independent noise contributes to P_a and P_b and not to C, so N is the
    noise power of one half plus any half-to-half signal disagreement.  Its
    ratio across gates is the local noise reduction.

    Rule 10: this is a difference of two POWER spectra of the same pair, not a
    spatial sd standing in for a temporal sigma.
    Rule 18: it is raised, not lowered, by half-to-half disagreement, so a
    noise-reduction ratio read from it is an UPPER bound on the true ratio --
    conservative in the direction that makes the gate look worse.
    """
    idx = K.band_index(rs.f, f_lo, f_hi)
    pa = (rs.pasum / rs.cnt)[idx]
    pb = (rs.pbsum / rs.cnt)[idx]
    c = rs.c[idx]
    return float((0.5 * (pa + pb) - c).mean())


def n_eff_local(rs0, rst, f_lo=F_LO_HF, f_hi=F_HI_HF):
    """Local effective frame count at gate T, DERIVED from the noise it bought.

    At gate 0 the merge takes exactly one frame per pixel, so N(0) is
    single-frame noise power.  Ideal averaging of `n` frames gives N(T) = N(0)/n,
    so n_eff_local = N(0)/N(T).  Fact 1196 measured noise tracking 1/sqrt(n_eff)
    within 0.74-1.18x, which is the accuracy this inherits.
    """
    n0 = n_incoh(rs0, f_lo, f_hi)
    nt = n_incoh(rst, f_lo, f_hi)
    if not np.isfinite(n0) or not np.isfinite(nt) or nt <= 0:
        return np.nan
    return float(n0 / nt)


def stats_across(vals):
    """Empirical mean and standard error across ROIs -- M92's error model, never
    a jackknife.  Rule 39: the null this is read against is reported beside it.
    """
    v = np.asarray([x for x in vals if np.isfinite(x)], dtype=np.float64)
    n = v.size
    if n == 0:
        return dict(n=0, mean=np.nan, sd=np.nan, se=np.nan, sigma=np.nan,
                    npos=0, nneg=0)
    mean = float(v.mean())
    sd = float(v.std(ddof=1)) if n > 1 else np.nan
    se = sd / np.sqrt(n) if n > 1 else np.nan
    return dict(n=int(n), mean=mean, sd=sd, se=se,
                sigma=float(abs(mean) / se) if se and se > 0 else np.nan,
                npos=int((v > 0).sum()), nneg=int((v < 0).sum()))


def terciles(hp):
    """Split ROI indices into detail terciles by hp_sd.  Declared at
    pre-registration (discipline 603)."""
    order = np.argsort(np.asarray(hp))
    k = len(order) // 3
    return dict(low=list(order[:k]), mid=list(order[k:2 * k]),
                high=list(order[2 * k:]))


# ---------------------------------------------------------------------------
# PAIR REGISTRATION -- an instrument repair, declared as a departure (report S9)
#
# WHY THIS IS HERE.  Each half-merge solves its OWN alignment, and
# `align_cmd::fit_to_cover` then scales the field of view by whatever `k <= 1`
# makes every frame of THAT half cover every pixel.  The two halves get
# different `k`, and because the output keeps its pixel dimensions the render is
# upsampled by `1/k` -- so the two halves come out at DIFFERENT MAGNIFICATIONS.
# Read off the render logs:
#
#     bee-3-cpl   half A k = 0.9227, half B k = 0.9360  ->  ratio 1.01441
#     112MSDCF    half A k = 0.9760, half B k = 0.9767  ->  ratio 1.00072
#
# 1.44% over a 3516 px plane is up to 25 px of relative displacement at the
# edge, which annihilates cross-power at f = 0.2 cyc/px (a 5 px period).  That
# is exactly what the first bee-3-cpl pass measured: 0 of 24 ROIs returned a
# finite `dsig`.  It is an artefact of splitting the bracket, not a property of
# the gate, and correcting it is not optional.
#
# WHY IT CANNOT MANUFACTURE THE RESULT.  The similarity is fitted ONCE on the
# gate-0 pair and then applied unchanged at every gate, so it has no way to
# express a gate-dependent difference.  A blur difference does not displace
# anything, so nothing the gate does is absorbed here.  And the fitted scale is
# checked against `k_A / k_B` from the render logs, which is an INDEPENDENT
# number the fit never sees.
# ---------------------------------------------------------------------------

def _hann2(shape):
    return np.outer(np.hanning(shape[0]), np.hanning(shape[1]))


def shift_of(a, b, max_px=96):
    """Sub-pixel (dy, dx) with `a(y, x) ~ b(y - dy, x - dx)`.

    Phase correlation with a parabolic peak refinement.  Rule 18: a flat or
    noise-dominated pair returns a peak at an arbitrary location, so the caller
    checks the peak's sharpness -- `pk_ratio` -- before trusting it.
    """
    w = _hann2(a.shape)
    fa = np.fft.fft2((a - a.mean()) * w)
    fb = np.fft.fft2((b - b.mean()) * w)
    r = fa * np.conj(fb)
    m = np.abs(r)
    m[m == 0] = 1.0
    cc = np.real(np.fft.ifft2(r / m))
    cc = np.fft.fftshift(cc)
    n0, n1 = a.shape
    c0, c1 = n0 // 2, n1 // 2
    lo0, hi0 = max(c0 - max_px, 1), min(c0 + max_px + 1, n0 - 1)
    lo1, hi1 = max(c1 - max_px, 1), min(c1 + max_px + 1, n1 - 1)
    sub = cc[lo0:hi0, lo1:hi1]
    k = np.unravel_index(np.argmax(sub), sub.shape)
    iy, ix = k[0] + lo0, k[1] + lo1
    peak = cc[iy, ix]
    med = float(np.median(np.abs(cc)))

    def parab(m1, c, p1):
        d = m1 - 2.0 * c + p1
        return 0.0 if d == 0 else 0.5 * (m1 - p1) / d

    sy = parab(cc[iy - 1, ix], peak, cc[iy + 1, ix])
    sx = parab(cc[iy, ix - 1], peak, cc[iy, ix + 1])
    dy = (iy + np.clip(sy, -1, 1)) - c0
    dx = (ix + np.clip(sx, -1, 1)) - c1
    return float(dy), float(dx), float(peak / med if med > 0 else np.nan)


def fit_similarity(centres, shifts, h, w):
    """Least-squares (s, ty, tx) for `d = t + s * (p - centre)`.

    A uniform scale about the plane centre plus a translation -- exactly the
    model `fit_to_cover` composes, so this is the form of the artefact and not a
    curve chosen to fit it.  Returns the fit and the per-ROI residual, which is
    the model-adequacy check.
    """
    cy, cx = 0.5 * h, 0.5 * w
    rows, rhs = [], []
    for (px, py), (dy, dx) in zip(centres, shifts):
        rows.append([1.0, 0.0, py + 0.5 * ROI - cy])
        rhs.append(dy)
        rows.append([0.0, 1.0, px + 0.5 * ROI - cx])
        rhs.append(dx)
    A = np.asarray(rows)
    y = np.asarray(rhs)
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    ty, tx, s = (float(v) for v in sol)
    resid = y - A @ sol
    return dict(ty=ty, tx=tx, s=s,
                resid_rms=float(np.sqrt((resid ** 2).mean())),
                resid_max=float(np.abs(resid).max()))


def apply_similarity(b, fit, h=None, w=None):
    """Resample `b` onto the grid `a` lives on, using a frozen similarity."""
    from scipy import ndimage
    n0, n1 = b.shape
    cy, cx = 0.5 * (h or n0), 0.5 * (w or n1)
    yy, xx = np.mgrid[0:n0, 0:n1].astype(np.float64)
    sy = yy - fit["ty"] - fit["s"] * (yy - cy)
    sx = xx - fit["tx"] - fit["s"] * (xx - cx)
    return ndimage.map_coordinates(b, [sy, sx], order=3, mode="nearest")


def fourier_shift(a, dy, dx):
    """Shift by (dy, dx) with an exact Fourier phase ramp."""
    n0, n1 = a.shape
    fy = np.fft.fftfreq(n0)[:, None]
    fx = np.fft.fftfreq(n1)[None, :]
    ph = np.exp(-2j * np.pi * (fy * dy + fx * dx))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * ph))


def cover_scales(stack, arm, gate=0.0):
    """`fit_to_cover`'s scale `k` for each half, read out of the render log.

    This is the INDEPENDENT number the similarity fit is checked against: the
    merge printed it before any analysis existed, and the fit never sees it.
    Returns None if either log is missing or does not carry the line.
    """
    import re
    out = {}
    for half in ("A", "B"):
        p = os.path.join(LOGS, f"{stack}-{arm}-g{gate:g}-{half}.log")
        if not os.path.exists(p):
            return None
        m = re.search(r"field of view scaled to ([0-9.]+)",
                      open(p, encoding="utf-8", errors="replace").read())
        if not m:
            return None
        out[half] = float(m.group(1))
    return out


def gauss_blur_fft(a, sigma):
    """Exact Fourier Gaussian, so the planted sigma is the sigma and not a
    kernel truncation of it.  Used only by the power control PC."""
    n0, n1 = a.shape
    fy = np.fft.fftfreq(n0)[:, None]
    fx = np.fft.fftfreq(n1)[None, :]
    h = np.exp(-2.0 * np.pi ** 2 * sigma ** 2 * (fy ** 2 + fx ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * h))
