"""M46 -- an admissible detail metric?  Library.

NEW FILE.  m41lib.py, m41lib2.py and m41lib3.py have all produced results that
are reported in docs/research/M41-r3-kill-measured.md and are frozen (rule 15).
They are IMPORTED here, never edited: the merge (arm A), the ring FRC, the
censoring-aware crossing, hp_sd, band_power and the exact Fourier Gaussian all
come from them unchanged, so M46's numbers are comparable to M41's line by line.

What is new here and why.

1.  TWO-CAPTURE FRC.  M41's split was even/odd frames of ONE capture, which
    shares the scene AND the fixed pattern.  112MSDCF/113MSDCF are two
    independent captures of one static subject (facts 49, 52), so the read-noise
    realisation and the shot noise are independent and only the fixed pattern is
    common.  Fact 478's (1 - rho) law says the recovery should rise.

2.  THE PHOTOMETRIC ORDERING, fixed in PREREGISTRATION.md sec 4.1 before it was
    measured.  The pair differs by one stop.  The photon-transfer model is
    evaluated on each capture's OWN UNSCALED DN and the variance is then carried
    through the scale as c^2 var.  Applying the model after rescaling would
    charge a frame with shot noise for photons it never collected, which either
    manufactures or destroys exactly the correlation being measured.

3.  THREE PLANT MODELS, not two.  PREREGISTRATION sec 4.2 registered PM-1
    ("post-capture") and PM-2 ("pre-capture").  Writing the code showed PM-1 was
    AMBIGUOUS between two physically different things, so it is split and both
    are run -- an added arm, never a removed one (deviation D6):

      PM_A  Y_i = H*L + P + N_i        blur optical, fixed pattern OUTSIDE it
      PM_B  Y_i = H*(L + P) + N_i      blur optical, fixed pattern INSIDE it
                                        (this is fact 477's model, because its
                                         sources were observed ROIs with the
                                         pattern already baked in)
      PM_C  Y_i = H*(L + P + N_i)      a LINEAR POST-FILTER on the captured
                                        image -- what a merge that low-passes
                                        its own output actually does

    Rule 20 note written before running: PM_C should give recovery ~0 for every
    correlation-based metric, because H attenuates the common and the
    independent power by the same |H|^2 and a ratio of the two cannot move.  If
    a metric DOES move under PM_C it is not measuring per-ring SNR and the
    model of it here is wrong.

4.  AN ORACLE.  oracle_fsc correlates the observation against the KNOWN latent.
    It is not shippable and is never proposed as one; it exists so that "nothing
    passes the bar" is falsifiable rather than a tautology (PREREGISTRATION
    sec 3).
"""
import os, sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_M41 = os.path.join(os.path.dirname(os.path.dirname(_HERE)), "m41-r3-kill", "src")
if _M41 not in sys.path:
    sys.path.insert(0, _M41)

import m41lib as L1          # frozen: arms, frc, hp_sd, band_power, focus_fields
import m41lib3 as L3         # frozen: censoring-aware cross, exact Fourier Gaussian

OUT = os.path.join(os.path.dirname(_HERE), "out")
os.makedirs(OUT, exist_ok=True)

BLACK = L1.BLACK
F_SIG = L1.F_SIG
NBIN = 64
THR = 1.0 / 7.0


# ------------------------------------------------------------------ decode
def quad_green(path):
    """Green quad plane, black-subtracted.  Rule 7: raw_image_visible only."""
    import rawpy
    with rawpy.imread(path) as r:
        v = r.raw_image_visible
        g1 = v[0::2, 1::2].astype(np.float32)
        g2 = v[1::2, 0::2].astype(np.float32)
    return 0.5 * (g1 + g2) - BLACK


def noise_var_dn(level_dn, g, rn_e):
    """Photon-transfer variance in DN^2 for the GREEN QUAD plane (the /2 is the
    two-green average).  Evaluated on UNSCALED DN by contract -- see the header."""
    return 0.5 * (g * np.maximum(level_dn, 0.0) + (rn_e * g) ** 2)


# ------------------------------------------------------- photometric scale
def photometric_scale(a, b):
    """Scale c such that c*b matches a in level.  Robust: ratio of medians of
    the two ROI means, computed on black-subtracted DN, so it is a pure
    exposure ratio and carries no black-level term.

    Rule 20: this FAILS visibly if the two ROIs do not view the same scene --
    the returned c then disagrees with the EXIF prediction, which is why the
    caller checks it against EXIF rather than trusting it."""
    ma, mb = float(np.median(a)), float(np.median(b))
    return ma / max(mb, 1e-9)


# ------------------------------------------------------------- alignment
def _hann2(n, m):
    return np.outer(np.hanning(n), np.hanning(m))


def phase_shift(a, b, upsample=64):
    """Sub-pixel shift (dy, dx) that best moves `b` onto `a`, by phase
    correlation with a local upsampled DFT refinement.

    Rule 20: misregistration is the other way to fake a null here -- an
    uncorrected sub-pixel shift destroys high-frequency correlation and looks
    exactly like "the metric has no power".  The caller reports the measured
    shift AND runs a deliberate-misalignment control."""
    n, m = a.shape
    w = _hann2(n, m)
    A = np.fft.fft2((a - a.mean()) * w)
    B = np.fft.fft2((b - b.mean()) * w)
    R = A * np.conj(B)
    R /= np.maximum(np.abs(R), 1e-30)
    cc = np.abs(np.fft.ifft2(R))
    py, px = np.unravel_index(np.argmax(cc), cc.shape)
    dy = py - n if py > n // 2 else py
    dx = px - m if px > m // 2 else px
    # local upsampled refinement on a 3x3 neighbourhood of the integer peak
    best, bdy, bdx = -np.inf, float(dy), float(dx)
    step = 1.0 / upsample
    for oy in np.arange(-1.0, 1.0 + step, step * 8):
        for ox in np.arange(-1.0, 1.0 + step, step * 8):
            v = _corr_at(R, dy + oy, dx + ox, n, m)
            if v > best:
                best, bdy, bdx = v, dy + oy, dx + ox
    for oy in np.arange(-0.125, 0.125 + step, step):
        for ox in np.arange(-0.125, 0.125 + step, step):
            v = _corr_at(R, bdy + oy, bdx + ox, n, m)
            if v > best:
                best, bdy, bdx = v, bdy + oy, bdx + ox
    return float(bdy), float(bdx)


def _corr_at(R, dy, dx, n, m):
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(m)[None, :]
    return float(np.abs(np.sum(R * np.exp(2j * np.pi * (fy * dy + fx * dx)))))


def fshift(img, dy, dx):
    """Fourier shift by (dy, dx).  Circular, so the caller must crop a margin."""
    n, m = img.shape
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(m)[None, :]
    return np.real(np.fft.ifft2(np.fft.fft2(img) *
                                np.exp(-2j * np.pi * (fy * dy + fx * dx)))).astype(np.float32)


# ------------------------------------------------------------------ metrics
def frc_curve(a, b, nbin=NBIN):
    """m41lib.frc unchanged (imported, not copied)."""
    ff, fr, cnt = L1.frc(a, b, nbin=nbin)
    return ff, fr


def frc_cross_c(a, b, nbin=NBIN, thr=THR):
    """(crossing, censored).  Censored means the curve never fell below `thr`
    for two adjacent rings, so the value is ff[-1] -- a LOWER BOUND.  Fact 475
    is what happens when this flag is dropped."""
    ff, fr = frc_curve(a, b, nbin)
    return L3.cross(ff, fr, thr=thr)


def frc_at(a, b, f=F_SIG, nbin=NBIN):
    ff, fr = frc_curve(a, b, nbin)
    return float(np.interp(f, ff, fr))


def oracle_fsc_at(obs, latent, f=F_SIG, nbin=NBIN):
    """Fourier shell correlation of an observation against the KNOWN latent.
    NOT SHIPPABLE -- it needs the truth.  Positive control on the BAR."""
    return frc_at(obs, latent, f=f, nbin=nbin)


def hp_sd(a):
    return L1.hp_sd(a)


def p_ratio(a, fc=F_SIG):
    return L3.p_ratio(a, fc)


def mean_grad(a):
    return L3.mean_grad(a)


# ------------------------------------------------------------- plant models
def blur(img, sb):
    """Exact Fourier Gaussian, MTF = exp(-2 pi^2 sb^2 f^2).  Imported."""
    return L3.gauss_blur(img, sb)


def make_fpn(shape, seed, sigma):
    """A FIXED pattern: one draw, reused for every capture, never redrawn.
    D3 -- this is not a nuisance to be removed, it is the quantity measured."""
    return (np.random.default_rng(seed).standard_normal(shape) * sigma).astype(np.float32)


def realise(latent, fpn, sigma, sb, model, rng):
    """One noisy capture under plant model `model`.

      PM_A  H*L + P + N       PM_B  H*(L+P) + N       PM_C  H*(L + P + N)

    Only PM_C attenuates the independent noise, because only PM_C is a filter
    applied AFTER capture.  That is the whole distinction."""
    n = rng.standard_normal(latent.shape).astype(np.float32) * sigma
    if model == "PM_A":
        return blur(latent, sb) + fpn + n
    if model == "PM_B":
        return blur(latent + fpn, sb) + n
    if model == "PM_C":
        return blur(latent + fpn + n, sb)
    raise ValueError(model)


def truth(latent, fpn, sb, model):
    """The NOISELESS source under the same model -- the truth channel `pred`.
    PM_C's noiseless limit is PM_B's, which is stated rather than hidden: with
    N = 0 the two are the same image, and that is why PM_C's recovery
    denominator is not degenerate even though its numerator cannot move."""
    if model == "PM_A":
        return blur(latent, sb) + fpn
    return blur(latent + fpn, sb)


# ------------------------------------------------------------ recovery ratio
def rec_lin(m0, msb, p0, psb):
    """Fact 477's linear recovery, UNCHANGED so the numbers are comparable to
    the table the acceptance bar was set from.  Returns None when either channel
    is censored or the truth channel does not move -- undefined, never zero."""
    if m0 is None or msb is None or p0 is None or psb is None:
        return None
    d = p0 - psb
    if abs(d) < 1e-12:
        return None
    return (m0 - msb) / d


def fmt(v, w=7, p=3):
    return "  --   " if v is None else f"{v:+{w}.{p}f}"


# ------------------------------------------------------------------ sources
def synth_broadband(n, seed, cutoff=None):
    """White-ish field with power in EVERY ring to Nyquist.  Rule 13's escape
    hatch: a metric that reads nothing here cannot blame the scene.  With
    `cutoff` set, the field is BAND-LIMITED BY CONSTRUCTION -- zero power above
    `cutoff` cyc/px -- which is the decisive input for question 120, because any
    ring power measured above the cutoff is then leakage, 100%."""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((n, n)).astype(np.float32)
    F = np.fft.rfft2(x)
    FY = np.broadcast_to(np.fft.fftfreq(n)[:, None], (n, n // 2 + 1))
    FX = np.broadcast_to(np.fft.rfftfreq(n)[None, :], (n, n // 2 + 1))
    rr = np.sqrt(FX * FX + FY * FY)
    F = F / (1.0 + (rr / 0.15) ** 1.0)             # a 1/f-ish scene spectrum
    if cutoff is not None:
        F = np.where(rr <= cutoff, F, 0.0)
    y = np.fft.irfft2(F, s=(n, n)).astype(np.float32)
    return y / max(y.std(), 1e-9)
