"""M57 -- library for spectral-SHAPE detail metrics.

Question 164: "Is there a detail metric that escapes single-frequency
blindness?"  Fact 708 says the blindness belongs to evaluating at ONE
FREQUENCY, not to lacking ground truth.  This library implements the
candidates that use the SHAPE of the common-power spectrum instead.

WHAT IS IMPORTED AND FROZEN
  m41lib      focus_fields, arm_A, hp_sd (frozen under rule 15, never edited)
  m46lib      blur (exact Fourier Gaussian), synth_broadband, noise_var_dn,
              make_fpn, F_SIG, BLACK

WHAT IS NEW HERE
  rings()        ring geometry byte-compatible with M46 Appendix A.1.7
  cross_ring()   per-ring mean real cross-power = canonical `sigpow` at any ring
  dsig()         K1 -- equivalent-blur difference, in PIXELS, from the WLS slope
                 of log[C2(f)/C1(f)] on -4 pi^2 f^2 over a fixed ring band
  rmtf2()        K2 -- two-ring relative MTF
  ccent()        K3 -- common-power spectral centroid of ONE pair
  Jackknife standard errors by leave-one-angular-sector-out, which is
  correlation-aware: C1 and C2 are computed from the SAME modes, so the
  jackknife sees the (large) positive covariance between them.

WHY THIS IS NOT FORECLOSED BY FACT 617
  Fact 617 proves a NORMALISED CORRELATION at one frequency cannot move under a
  linear post-filter, because H scales the common and the uncommon power of the
  SAME ring identically.  K1 and K2 are ratios of cross-powers at DIFFERENT
  frequencies: a post-filter multiplies the numerator by |H(f2)|^2 and the
  denominator by |H(f1)|^2, and those differ.  The proof does not reach them.
  That is stated in PREREGISTRATION.md section 0 and is DERIVED, not measured.

RULE NOTES
  rule 4   any merge used here is the regularised arm A, never a raw argmax; the
           near-selector case is reached with the GATE, and is labelled.
  rule 7   raw_image_visible only.
  rule 9   every real-data cell has a flat-ROI twin, computed first.
  rule 10  no spatial sd is ever compared to a temporal sigma here.
  rule 18  each candidate's fooling direction is stated in its docstring.
  rule 23  sobel is never applied to a cube; focus_fields is m41lib's, which
           extracts the 2-D plane first.
  rule 39  every d has a null and that null's standard error.
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_EXP = os.path.dirname(os.path.dirname(_HERE))
for _p in (os.path.join(_EXP, "m46-detail-metric", "src"),
           os.path.join(_EXP, "m41-r3-kill", "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import m41lib as L1        # frozen
import m46lib as M         # frozen

OUT = os.path.join(os.path.dirname(_HERE), "out")
os.makedirs(OUT, exist_ok=True)

BLACK = M.BLACK
F_SIG = M.F_SIG            # 0.2762 cyc/px, fact 27's measured optical cutoff
NBIN = 64
N_STD = 512

# ---- PR11: the band is fixed ONCE, here, before any stack is scored --------
# f_hi is fact 27's measured optical cutoff.  f_lo = 0.05 cyc/px is a 20 px
# period: above the window mainlobe and below any structure the ROI framing
# imposes.  Neither is re-chosen per stack, per ROI or after seeing a score.
F_LO = 0.05
F_HI = F_SIG
N_SECT = 16                # angular sectors for the jackknife

# Shipped sensor constants, crates/strehl-core/src/profile.rs (READ, not edited).
# g = max(iso, base_iso)/gain_divisor.  read_noise_e_high was 1.47 when m41lib
# was written and is 1.2392 since M48; m41lib's default is left alone (rule 15)
# and the corrected value is passed in explicitly wherever it matters.
GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
RN_E_HIGH = 1.2392
RN_E_LOW = 4.20
SECOND_BASE_ISO = 400.0


def gain_dn_per_e(iso):
    return max(float(iso), BASE_ISO) / GAIN_DIVISOR


def read_noise_e(iso):
    return RN_E_HIGH if float(iso) >= SECOND_BASE_ISO else RN_E_LOW


# ---------------------------------------------------------------- geometry
def rings(n, nbin=NBIN):
    """M46 Appendix A.1.7 ring geometry, re-implemented from the prose.

    rmax = floor(n/2) (integer division FIRST); edges = linspace(0, rmax, nbin+1);
    lower-inclusive / upper-exclusive; rings with fewer than 8 modes are DROPPED
    and dropping renumbers (A.1.8).  Returns a list of (mask, count, centre_cycpx).
    """
    rmax = n // 2
    edges = np.linspace(0.0, float(rmax), nbin + 1)
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2.0 + (xx - n // 2) ** 2.0)
    out = []
    for i in range(nbin):
        m = (rr >= edges[i]) & (rr < edges[i + 1])
        c = int(m.sum())
        if c < 8:
            continue
        out.append((m, c, 0.5 * (edges[i] + edges[i + 1]) / n))
    return out


def sectors(n, nsect=N_SECT):
    """Angular sector index per mode, for the leave-one-out jackknife.

    Sectors are angular so that leaving one out removes an equal share of EVERY
    ring, which keeps the ring band intact in each replicate.
    """
    yy, xx = np.mgrid[0:n, 0:n]
    th = np.arctan2(yy - n // 2, xx - n // 2)
    return np.floor((th + np.pi) / (2.0 * np.pi) * nsect).astype(np.int32) % nsect


_GRID_CACHE = {}


def ring_grid(n, nbin=NBIN, nsect=N_SECT):
    """Flat (ring, sector) label array, cached.  `lab` is -1 for a mode in no
    surviving ring, else ring_position * nsect + sector, so ONE bincount gets
    every partial sum.  Purely a speed rewrite of `rings` + `sectors`; the
    geometry is identical and s1 asserts that against `rings()` directly.
    """
    key = (n, nbin, nsect)
    if key in _GRID_CACHE:
        return _GRID_CACHE[key]
    rs = rings(n, nbin)
    sec = sectors(n, nsect)
    lab = np.full((n, n), -1, np.int64)
    for i, (m, _, _) in enumerate(rs):
        lab[m] = i * nsect + sec[m]
    f = np.array([c for (_, _, c) in rs])
    cnt_s = np.bincount(lab[lab >= 0], minlength=len(rs) * nsect).reshape(len(rs), nsect)
    val = (lab, f, cnt_s, len(rs))
    _GRID_CACHE[key] = val
    return val


def spectra(a, b):
    """A.1.3-A.1.6: mean removal, THEN symmetric Hann outer product, unnormalised
    forward fft2 in f64, fftshift.  Returns (A, B) complex128."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    n = a.shape[0]
    w1 = np.hanning(n)                      # SYMMETRIC (n-1 denominator), A.1.4
    w = np.outer(w1, w1)
    A = np.fft.fftshift(np.fft.fft2((a - a.mean()) * w))
    B = np.fft.fftshift(np.fft.fft2((b - b.mean()) * w))
    return A, B


class RingStats:
    """Per-ring cross- and auto-power, with per-sector partial sums.

    `c[i]` is the mean per-mode real cross-power of ring i -- i.e. canonical
    `sigpow` (M46 A.0.3) evaluated at ring i instead of only at f_sig.  The
    per-sector partials exist so a jackknife can be taken without recomputing
    the FFTs.
    """

    def __init__(self, a, b, nbin=NBIN, nsect=N_SECT):
        n = a.shape[0]
        A, B = spectra(a, b)
        lab, f, cnt_s, nr = ring_grid(n, nbin, nsect)
        self.n = n
        self.f = f
        self.nsect = nsect
        sel = lab >= 0
        ll = lab[sel]
        x = (A.real * B.real + A.imag * B.imag)[sel]     # Re(A conj B), A.1.10
        pa = (np.abs(A) ** 2)[sel]
        pb = (np.abs(B) ** 2)[sel]
        nz = nr * nsect
        self.csum_s = np.bincount(ll, weights=x, minlength=nz).reshape(nr, nsect)
        self.cnt_s = cnt_s.astype(np.float64)
        self.csum = self.csum_s.sum(1)
        self.cnt = self.cnt_s.sum(1)
        self.pasum = np.bincount(ll, weights=pa, minlength=nz).reshape(nr, nsect).sum(1)
        self.pbsum = np.bincount(ll, weights=pb, minlength=nz).reshape(nr, nsect).sum(1)

    @property
    def c(self):
        return self.csum / self.cnt

    def c_jack(self, s):
        """Ring means with angular sector `s` removed."""
        return (self.csum - self.csum_s[:, s]) / (self.cnt - self.cnt_s[:, s])

    def frc(self):
        return self.csum / np.sqrt(self.pasum * self.pbsum)

    def at(self, f):
        j = int(np.argmin(np.abs(self.f - f)))
        return float(self.c[j]), j

    def c_var(self):
        """Jackknife variance of each ring mean over angular sectors.

        DERIVED, and the reason it exists: `dsig` regresses log C, and
        E[log C] = log E[C] - Var(C)/(2 E[C]^2) + O(Var^2).  Independent noise
        has zero MEAN cross-power but non-zero VARIANCE, and that variance grows
        towards f_hi where the scene power falls, so the Jensen term is a
        frequency-dependent DOWNWARD bias in log C that has the same shape as a
        blur.  S5 measured it at up to 0.29 px on real data.  This estimate is
        what K6/K7 use to remove it.  No tunable constant.
        """
        m = self.nsect
        v = np.stack([self.c_jack(s) for s in range(m)], 1)
        return (m - 1.0) / m * ((v - v.mean(1, keepdims=True)) ** 2).sum(1)


def band_index(f, f_lo=F_LO, f_hi=F_HI):
    return np.where((f >= f_lo) & (f <= f_hi))[0]


def _golden(fn, lo, hi, it=90):
    """Deterministic bounded minimiser.  No scipy, no seed, no tolerance knob."""
    r = 0.6180339887498949
    c, d = hi - r * (hi - lo), lo + r * (hi - lo)
    fc, fd = fn(c), fn(d)
    for _ in range(it):
        if fc < fd:
            hi, d, fd = d, c, fc
            c = hi - r * (hi - lo)
            fc = fn(c)
        else:
            lo, c, fc = c, d, fd
            d = lo + r * (hi - lo)
            fd = fn(d)
    return 0.5 * (lo + hi)


def _dsig_lin_core(c1, c2, v1, v2, f, idx, blo=-4.0, bhi=4.0):
    """K6 -- fit C2 = C1 * exp(-4 pi^2 b f^2) in the LINEAR domain.

    There is no logarithm, so there is no Jensen term to bias.  The weight is
    the total variance of the residual under errors in BOTH configurations,
    which is forced by the model rather than chosen:
        Var[C2 - C1 e^{-x b}] = V2 + e^{-2 x b} V1.
    Returns (px, b).
    """
    a1, a2 = c1[idx], c2[idx]
    w1, w2 = v1[idx], v2[idx]
    x = 4.0 * np.pi ** 2 * f[idx] ** 2

    def cost(b):
        e = np.exp(-x * b)
        r = a2 - a1 * e
        var = w2 + (e ** 2) * w1
        return float((r * r / np.maximum(var, 1e-300)).sum())

    b = _golden(cost, blo, bhi)
    return float(np.sign(b) * np.sqrt(abs(b))), b


def _dsig_db_core(c1, c2, v1, v2, f, idx):
    """K7 -- K1's log fit with the second-order Jensen term removed.

    E[log C] = log E[C] - Var(C)/(2 E[C]^2) + O(Var^2), so adding
    Var/(2 C^2) back to each log recovers log E[C] to that order.  One term,
    no tunable constant.  Returns (px, b, resid_rms, sweep).
    """
    a1, a2 = c1[idx], c2[idx]
    if np.any(a1 <= 0) or np.any(a2 <= 0):
        return np.nan, np.nan, np.nan, np.nan
    y = (np.log(a2) + v2[idx] / (2.0 * a2 ** 2)) \
        - (np.log(a1) + v1[idx] / (2.0 * a1 ** 2))
    x = -4.0 * np.pi ** 2 * f[idx] ** 2
    xm = x - x.mean()
    b = float((xm * y).sum() / (xm * xm).sum())
    res = y - y.mean() - b * xm
    return (float(np.sign(b) * np.sqrt(abs(b))), b,
            float(np.sqrt((res ** 2).mean())),
            float(abs(b) * (x.max() - x.min())))


def dsig_lin(rs1, rs2, f_lo=F_LO, f_hi=F_HI, jack=True):
    """K6 -- POST-HOC.  Designed after S5 measured K1 failing its noise null.
    Kill conditions are pre-registered in PREREGISTRATION-2.md before it ran.

    Rule 18: it inherits every one of K1's fooling directions (common injected
    structure, OTF zeros inside the band, the pedestal floor).  It removes ONE
    failure -- the log-transform bias at finite SNR -- and nothing else.
    """
    assert np.allclose(rs1.f, rs2.f), "ring grids differ"
    idx = band_index(rs1.f, f_lo, f_hi)
    v1, v2 = rs1.c_var(), rs2.c_var()
    px, b = _dsig_lin_core(rs1.c, rs2.c, v1, v2, rs1.f, idx)
    out = dict(px=px, slope=b, nring=len(idx), ok=bool(np.isfinite(px)))
    if not jack:
        out["se_px"] = np.nan
        return out
    vals = []
    for s in range(rs1.nsect):
        p, bb = _dsig_lin_core(rs1.c_jack(s), rs2.c_jack(s), v1, v2, rs1.f, idx)
        if np.isfinite(bb):
            vals.append(bb)
    vals = np.array(vals)
    m = len(vals)
    if m < 3:
        out["se_px"] = np.nan
        return out
    se_b = float(np.sqrt((m - 1.0) / m * ((vals - vals.mean()) ** 2).sum()))
    out["se_slope"] = se_b
    out["se_px"] = float(se_b / (2.0 * max(abs(b), 1e-12) ** 0.5))
    return out


def dsig_db(rs1, rs2, f_lo=F_LO, f_hi=F_HI, jack=True):
    """K7 -- POST-HOC.  K1 with the Jensen term removed.  See `dsig_lin`."""
    assert np.allclose(rs1.f, rs2.f), "ring grids differ"
    idx = band_index(rs1.f, f_lo, f_hi)
    v1, v2 = rs1.c_var(), rs2.c_var()
    px, b, rms, sweep = _dsig_db_core(rs1.c, rs2.c, v1, v2, rs1.f, idx)
    out = dict(px=px, slope=b, nring=len(idx), ok=bool(np.isfinite(px)),
               resid=rms, sweep=sweep,
               gof=float(rms / sweep) if sweep and sweep > 0 else np.nan)
    if not jack or not out["ok"]:
        out["se_px"] = np.nan
        return out
    vals = []
    for s in range(rs1.nsect):
        p, bb, _r, _s = _dsig_db_core(rs1.c_jack(s), rs2.c_jack(s), v1, v2,
                                      rs1.f, idx)
        if np.isfinite(bb):
            vals.append(bb)
    vals = np.array(vals)
    m = len(vals)
    if m < 3:
        out["se_px"] = np.nan
        return out
    se_b = float(np.sqrt((m - 1.0) / m * ((vals - vals.mean()) ** 2).sum()))
    out["se_slope"] = se_b
    out["se_px"] = float(se_b / (2.0 * max(abs(b), 1e-12) ** 0.5))
    return out


# ------------------------------------------------------------- candidates
def _dsig_from_c(c1, c2, f, idx):
    """WLS-free core: ordinary least squares of log(c2/c1) on -4 pi^2 f^2.

    Returns (sigma_eq_px, sigma_eq_squared, n_used, resid_rms, sweep).
    `sigma_eq_squared` is the slope and is the natural linear quantity; the px
    value is sign(b) * sqrt(|b|) and is what a human reads.

    `resid_rms` is the RMS of the fit residual in nats and `sweep` is
    |b| * (x.max() - x.min()), the log-ratio change the fitted Gaussian
    accounts for across the band.  Together they are the MODEL-VIOLATION
    DIAGNOSTIC: the derivation assumes the two configurations differ by a
    Gaussian, and a departure means the reported px number is an extrapolation
    rather than a measurement.  See `gof` below.

    NaN when any ring in the band has a non-positive c1 or c2 -- the log is not
    defined and coercing it would be exactly the kind of silent choice this
    corpus keeps dying to.  The caller must check.
    """
    a1 = c1[idx]
    a2 = c2[idx]
    if np.any(a1 <= 0) or np.any(a2 <= 0):
        return np.nan, np.nan, 0, np.nan, np.nan
    y = np.log(a2) - np.log(a1)
    x = -4.0 * np.pi ** 2 * f[idx] ** 2
    xm = x - x.mean()
    b = float((xm * y).sum() / (xm * xm).sum())
    res = y - y.mean() - b * xm
    rms = float(np.sqrt((res ** 2).mean()))
    sweep = float(abs(b) * (x.max() - x.min()))
    return float(np.sign(b) * np.sqrt(abs(b))), b, len(idx), rms, sweep


def dsig(rs1, rs2, f_lo=F_LO, f_hi=F_HI, jack=True):
    """K1 -- EQUIVALENT-BLUR DIFFERENCE, in pixels.

    Positive  => configuration 2 delivers LESS resolution than configuration 1,
                 by the same amount a Gaussian of this sigma would cost.
    Zero      => same delivered resolution (any amount of noise difference).
    Negative  => configuration 2 delivers MORE resolution.

    Rule 18 -- how it can be fooled.  It reads the ratio of COMMON power
    spectra.  Anything that adds structure COMMON to both half-merges and
    concentrated at high frequency will be scored as resolution: fixed-pattern
    noise, PRNU, a shared guide frame, a shared sharpening kernel, aliased
    content.  It cannot be fooled by anything INDEPENDENT between the halves,
    which is all of shot and read noise.  It saturates rather than inverting
    when the common-mode pedestal dominates (PR10).

    Returns dict(px, slope, se_px, se_slope, nring, ok).
    """
    assert np.allclose(rs1.f, rs2.f), "ring grids differ"
    idx = band_index(rs1.f, f_lo, f_hi)
    px, b, nr, rms, sweep = _dsig_from_c(rs1.c, rs2.c, rs1.f, idx)
    out = dict(px=px, slope=b, nring=nr, ok=bool(nr > 0 and np.isfinite(px)),
               resid=rms, sweep=sweep,
               gof=float(rms / sweep) if sweep and np.isfinite(sweep) and sweep > 0
               else np.nan)
    if not jack or not out["ok"]:
        out["se_px"] = np.nan
        out["se_slope"] = np.nan
        return out
    vals = []
    for s in range(rs1.nsect):
        p, bb, k, _r, _s = _dsig_from_c(rs1.c_jack(s), rs2.c_jack(s), rs1.f, idx)
        if k:
            vals.append(bb)
    vals = np.array(vals)
    m = len(vals)
    if m < 3:
        out["se_px"] = np.nan
        out["se_slope"] = np.nan
        return out
    se_b = float(np.sqrt((m - 1.0) / m * ((vals - vals.mean()) ** 2).sum()))
    out["se_slope"] = se_b
    # delta method: sigma = sqrt(b)  =>  d sigma/d b = 1/(2 sqrt(|b|))
    out["se_px"] = float(se_b / (2.0 * max(abs(b), 1e-12) ** 0.5)) if b != 0 else np.nan
    return out


def rmtf2(rs1, rs2, f_lo=F_LO, f_hi=F_HI):
    """K2 -- two-ring relative MTF, [C2/C1](f_hi) / [C2/C1](f_lo).

    Rule 18: same fooling direction as K1 and strictly less information, since
    it throws away every ring between the two.  Kept as the simplest member of
    the family so that "the band buys something" is measurable rather than
    assumed.  < 1 means configuration 2 lost resolution.
    """
    jl = int(np.argmin(np.abs(rs1.f - f_lo)))
    jh = int(np.argmin(np.abs(rs1.f - f_hi)))
    c1, c2 = rs1.c, rs2.c
    if c1[jl] == 0 or c1[jh] == 0 or c2[jl] == 0:
        return np.nan
    return float((c2[jh] / c1[jh]) / (c2[jl] / c1[jl]))


def ccent(rs, f_lo=F_LO, f_hi=F_HI):
    """K3 -- common-power spectral centroid of ONE pair, in cyc/px.

    sqrt(sum f^2 C(f) / sum C(f)) over the band.  Degree 0 in photometric gain
    because a constant multiplier cancels.  ABSOLUTE, not a contrast -- it is
    the only candidate here that reports a number for a single merge.

    Rule 18: it is dominated by the ROI's own scene spectrum, so it is
    comparable only within one ROI; and a common-mode pedestal raises it, since
    a flat pedestal has all its mass at the top of the band.
    """
    idx = band_index(rs.f, f_lo, f_hi)
    c = rs.c[idx]
    f = rs.f[idx]
    den = c.sum()
    if den <= 0:
        return np.nan
    return float(np.sqrt(max((f * f * c).sum() / den, 0.0)))


def sigpow(rs):
    """K0 -- the incumbent, canonical M46 Appendix A.1.10 form, as a CONTROL.

    Rule 18: facts 703/704 -- non-monotone in true resolution above ~0.7 px of
    blur, and degree 2 in photometric gain with no normalisation.
    """
    return rs.at(F_SIG)[0]


# ------------------------------------------------------------------ plants
def pillbox_blur(img, r):
    """Geometric defocus: H = 2 J1(2 pi r f)/(2 pi r f), WITH its contrast
    reversals.  m41lib.otf_defocus is the same function; this applies it as an
    image filter on the full complex grid."""
    if r <= 1e-9:
        return np.asarray(img, np.float32)
    n, m = img.shape
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(m)[None, :]
    H = L1.otf_defocus(r, np.broadcast_to(fx, (n, m)).copy(),
                       np.broadcast_to(fy, (n, m)).copy())
    return np.real(np.fft.ifft2(np.fft.fft2(img) * H)).astype(np.float32)


def gauss_mtf(f, sb):
    """MTF of m46lib.blur: exp(-2 pi^2 sb^2 f^2).  The cross-power carries |H|^2."""
    return np.exp(-2.0 * np.pi ** 2 * sb ** 2 * f ** 2)


# ------------------------------------------------------------- real merges
def load_cube(files, roi, pad=32):
    """Green quad plane cube.  Rule 32: allocate AND copy inside the `with`."""
    import rawpy
    x, y, w, h = roi
    x0, y0, x1, y1 = x - pad, y - pad, x + w + pad, y + h + pad
    out = np.empty((len(files), y1 - y0, x1 - x0), np.float32)
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            v = r.raw_image_visible
            g1 = v[2 * y0:2 * y1:2, 2 * x0 + 1:2 * x1 + 1:2].astype(np.float32)
            g2 = v[2 * y0 + 1:2 * y1 + 1:2, 2 * x0:2 * x1:2].astype(np.float32)
        out[i] = 0.5 * (g1 + g2) - BLACK
    return out


def merge_subset(cube, coarse, reg, idx, pad=32, gate=0.5):
    """Arm A (regularised winner field + noise-gated average) over a frame
    subset.  Rule 4: the winner comes from the REGULARISED field, never a raw
    argmax.  Documented copy of m41lib.arm_A restricted to `idx`; the caller
    asserts equality with m41lib.arm_A at idx = all, gate = 0.5.
    """
    c, cf, rg = cube[idx], coarse[idx], reg[idx]
    w = np.argmax(rg, axis=0)
    peak = np.take_along_axis(cf, w[None], 0)[0]
    acc = cf >= (gate * peak)[None]
    acc[w, np.arange(c.shape[1])[:, None], np.arange(c.shape[2])[None]] = True
    nn = acc.sum(0).astype(np.float32)
    m = (c * acc).sum(0) / np.maximum(nn, 1.0)
    if pad:
        m = m[pad:-pad, pad:-pad]
    return m.astype(np.float32), float(nn[pad:-pad, pad:-pad].mean() if pad else nn.mean())


def splits(nf, seed=7):
    """The split rules of M46 A.3.1 / fact 702, same construction as M55 e9."""
    idx = np.arange(nf)
    h = nf // 2
    out = {"parity": (idx[0::2], idx[1::2]),
           "contiguous": (idx[:h], idx[h:2 * h])}
    for blk in (2, 4, 8):
        grp = (idx // blk) % 2
        out[f"block-{blk}"] = (idx[grp == 0], idx[grp == 1])
    r = np.random.default_rng(seed).permutation(idx)
    out["random"] = (np.sort(r[:h]), np.sort(r[h:2 * h]))
    return out


def quads(nf):
    """Four interleaved quarters -- the basis for the PR6 re-pairing null."""
    idx = np.arange(nf)
    return [idx[i::4] for i in range(4)]


def fmt(v, w=9, p=5):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return " " * (w - 3) + "n/a"
    return f"{v:+{w}.{p}f}"
