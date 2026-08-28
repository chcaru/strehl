#!/usr/bin/env python3
"""V-ORACLE shared library: a per-tile, band-agnostic, noise-corrected structure
statistic, and the RAW loading path it runs on.

THE QUESTION.  Where the merged master is smoothly blurred, does a source frame
exist that is SHARPER there?  If no frame is sharp -> capture gap, not our bug.
If one is -> merge defect.

WHY THE STATISTIC IS SHAPED THE WAY IT IS.

  * Band-agnostic.  V-LINEAR measured the signal/noise band boundary moving
    0.17 -> 0.48 cyc/px across the corpus and found pyramid band 0 to be noise
    or mixed on 5 of 9 subjects.  So this never gates on a chosen band.  It
    computes a noise-corrected SIGNAL power in every band of a difference-of-
    Gaussian ladder and reports the whole vector.  A band that is pure noise on
    a given subject contributes ~0 signal power by construction rather than
    contributing grain, so including it is safe rather than merely tolerable.

  * Noise-corrected, by an estimator that does not look at the tile's own high
    frequencies.  Raw band power counts noise as sharpness; on this corpus a
    single frame carries up to 10x the merge's pixel noise, so an uncorrected
    ratio hands the source frame a win wherever NEITHER arm has detail --
    exactly the flat regions this question is about.  Two independent
    corrections are implemented and cross-checked:

      PTC   - a photon-transfer fit of band variance against tile mean level,
              taken from the LOWER ENVELOPE over all tiles and frames of the
              stack.  Featureless bokeh supplies the envelope.  Independent of
              any one tile's structure.
      COV   - cross-covariance of the two Bayer green sub-planes G1 and G2,
              which see the same scene with INDEPENDENT noise.  Model-free.
              Attenuated at the finest scales by the half-pixel diagonal offset
              between the two green sites, so it is used as a check on PTC at
              coarse scales, never as the primary at the finest.

Everything in stage A stays inside one transformation: rawpy CFA green,
black-subtracted, no demosaic, no white balance, no matrix.  Frames are only
ever compared against other frames here.
"""
from __future__ import annotations

import os

import numpy as np
import rawpy

RAW = r"D:\personal\macro"
MASTERS = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
OUT = r"D:\strehl-out\V-ORACLE"

# Difference-of-Gaussian ladder, in GREEN-PLANE pixels.  Band b isolates
# roughly [1/(2*pi*s_{b+1}), 1/(2*pi*s_b)] cyc/px.  Five bands span Nyquist
# down to broad structure; the statistic reports all five and never picks one.
SIGMAS = [0.0, 0.8, 1.6, 3.2, 6.4, 12.8]
NBAND = len(SIGMAS) - 1


def frames_of(subject: str) -> list[str]:
    d = os.path.join(RAW, subject)
    fs = sorted(f for f in os.listdir(d) if f.lower().endswith((".arw", ".sr2")))
    return [os.path.join(d, f) for f in fs]


def green_pair(path: str) -> tuple[np.ndarray, np.ndarray]:
    """The two Bayer green sub-planes, black-subtracted, as float32.

    Returned SEPARATELY, not averaged: their noise is independent, which is the
    whole basis of the COV cross-check.  rawpy's raw_image_visible is a view
    into LibRaw's buffer and is invalid once the context manager exits
    (AGENTS.md rule 32), so both planes are copied inside the `with`.
    """
    with rawpy.imread(path) as r:
        cfa = r.raw_image_visible
        pat = r.raw_pattern
        blk = list(r.black_level_per_channel)
        # LibRaw's colour indices are 0=R 1=G 2=B 3=G2.  A 2x2 Bayer pattern
        # therefore carries green at index 1 and index 3, NOT twice at 1 --
        # focuscurve.py's `pat == 1` finds only one of the two green sites.
        sites = []
        for ci in (1, 3):
            ys, xs = np.where(pat == ci)
            assert len(ys) == 1, f"colour {ci}: expected 1 site, got {len(ys)}"
            sites.append((int(ys[0]), int(xs[0]), blk[ci]))
        assert len(sites) == 2
        h, w = cfa.shape[0] // 2, cfa.shape[1] // 2
        out = []
        for y, x, b in sites:
            out.append(cfa[y::2, x::2][:h, :w].astype(np.float32) - float(b))
    return out[0], out[1]


def _blur(a: np.ndarray, sigma: float) -> np.ndarray:
    """Isotropic Gaussian blur of a 2-D PLANE.

    AGENTS.md rule 23: a separable filter touches every axis of the array it is
    given.  That is exactly what is wanted here and is safe *because* `a` is
    asserted 2-D -- there is no frame axis for it to smooth along.  Never pass a
    (frames, y, x) cube to this.
    """
    assert a.ndim == 2, f"_blur wants a 2-D plane, got {a.ndim}-D"
    if sigma <= 0.0:
        return a
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(a, sigma, mode="reflect", truncate=3.0)


def bands(a: np.ndarray) -> list[np.ndarray]:
    """Difference-of-Gaussian band decomposition, full resolution, no decimation.

    No decimation on purpose: a decimated pyramid aliases the noise differently
    per level, which would make the PTC fit level-dependent in a way that is not
    physical.  Cost is a few seconds per frame and this runs once per frame.
    """
    prev = _blur(a, SIGMAS[0])
    out = []
    for s in SIGMAS[1:]:
        cur = _blur(a, s)
        out.append(prev - cur)
        prev = cur
    return out


def tile_stats(g1: np.ndarray, g2: np.ndarray, ts: int) -> dict:
    """Per-tile, per-band: mean level, band variance, and G1xG2 band covariance.

    Returns arrays shaped (nr, nc) for level and (NBAND, nr, nc) for the rest.
    `var` is the mean of the two sub-planes' band variances (signal + noise);
    `cov` is their band cross-covariance (signal only, in expectation).
    """
    h, w = g1.shape
    nr, nc = h // ts, w // ts
    g1 = g1[: nr * ts, : nc * ts]
    g2 = g2[: nr * ts, : nc * ts]

    def bmean(x):
        # Block mean without materialising a transposed copy: reduce straight
        # over the two intra-tile axes.  Bit-identical to the reshape/transpose
        # form and ~3x cheaper on a 3514x2344 plane.
        return x.reshape(nr, ts, nc, ts).mean(axis=(1, 3))

    level = bmean(0.5 * (g1 + g2))
    b1, b2 = bands(g1), bands(g2)
    var = np.zeros((NBAND, nr, nc), np.float64)
    cov = np.zeros((NBAND, nr, nc), np.float64)
    for b in range(NBAND):
        p1, p2 = b1[b].astype(np.float64), b2[b].astype(np.float64)
        # Bands are zero-mean by construction (DoG kills DC); use raw second
        # moments so a tile-mean subtraction cannot eat real low-frequency
        # structure inside the tile.
        var[b] = 0.5 * (bmean(p1 * p1) + bmean(p2 * p2))
        cov[b] = bmean(p1 * p2)
    return {"level": level, "var": var, "cov": cov, "nr": nr, "nc": nc}


# ---------------------------------------------------------------------------
# The PRIMARY noise correction: photon-transfer subtraction.
#
# The G1xG2 covariance is model-free but it is NOT usable at fine scales: the
# two green sites are offset by (0.5,0.5) green px, and V-ORACLE's C5 measured
# the resulting attenuation going through zero at a diagonal period of ~4 green
# px and INVERTING below it (recovery -0.96 at period 2.2 px).  A statistic that
# returns negative signal for the sharpest detail in the frame would have driven
# this whole investigation to "capture gap" by construction.  So the covariance
# is demoted to a cross-check in bands 2-4, where C5 measures recovery
# 0.83-0.95, and the primary estimator is the one below, which has no spatial
# offset anywhere in it.
#
#   Var(band b, tile) = Signal(b, tile) + kappa_b * sigma_pix^2(level)
#   sigma_pix^2(level) = level / g + rn2          (photon transfer, per stack)
#
# kappa_b is a property of the band kernel alone and is measured exactly, from
# synthetic unit-variance white noise pushed through the real `bands()` code
# path -- not derived on paper, so it cannot disagree with the implementation.
# (g, rn2) is fitted from the LOWER ENVELOPE of var/kappa against level over
# every tile of every sampled frame: featureless regions supply the envelope.
# ---------------------------------------------------------------------------

_KAPPA = None


def kappa(n: int = 1024, seed: int = 7) -> np.ndarray:
    """Per-band variance gain of `bands()` on unit-variance white noise."""
    global _KAPPA
    if _KAPPA is None:
        rng = np.random.default_rng(seed)
        w = rng.normal(0.0, 1.0, (n, n)).astype(np.float32)
        _KAPPA = np.array([float((b * b).mean()) for b in bands(w)])
    return _KAPPA


def fit_ptc(levels: np.ndarray, var: np.ndarray, frac: float = 0.05,
            nbin: int = 24) -> tuple[float, float, dict]:
    """Fit sigma_pix^2 = level/g + rn2 from the lower envelope of var/kappa.

    `levels` is (M,), `var` is (NBAND, M).  Returns (g, rn2, diag).  The
    envelope is the `frac` quantile within each level bin, taken over all bands
    jointly after dividing out kappa -- so the fit is over-determined NBAND-fold
    and the per-band scatter of the result is a real internal check.
    """
    k = kappa()
    s2 = var / k[:, None]                       # per-band estimate of sigma_pix^2
    lo = np.quantile(s2, frac, axis=0)          # across bands: the quietest band
    edges = np.quantile(levels, np.linspace(0, 1, nbin + 1))
    edges = np.unique(edges)
    xs, ys, ns = [], [], []
    for i in range(len(edges) - 1):
        m = (levels >= edges[i]) & (levels < edges[i + 1])
        if m.sum() < 8:
            continue
        xs.append(float(np.median(levels[m])))
        ys.append(float(np.quantile(lo[m], frac)))
        ns.append(int(m.sum()))
    xs, ys = np.array(xs), np.array(ys)
    A = np.vstack([xs, np.ones_like(xs)]).T
    sol, *_ = np.linalg.lstsq(A, ys, rcond=None)
    slope, rn2 = float(sol[0]), float(sol[1])
    g = 1.0 / slope if slope > 0 else float("inf")
    pred = A @ sol
    return g, rn2, {"bin_level": xs.tolist(), "bin_sigma2": ys.tolist(),
                    "bin_n": ns, "resid": (ys - pred).tolist(),
                    "slope": slope}


def signal_ptc(st: dict, g: float, rn2: float) -> np.ndarray:
    """Noise-corrected per-band signal POWER per tile, shape (NBAND, nr, nc)."""
    k = kappa()
    s2 = st["level"] / g + rn2
    return st["var"] - k[:, None, None] * s2[None, :, :]


# ---------------------------------------------------------------------------
# THE SHIPPED FRAME-SIDE STATISTIC: through-focus contrast.
#
# Both noise corrections above have a defect that the commissioning found:
#   - the G1xG2 covariance INVERTS below a diagonal period of ~4 green px
#     (commission.py C5), so it reports negative signal for the finest detail;
#   - the photon-transfer subtraction needs a fit whose lower envelope is
#     contaminated by real structure in the coarse bands (commission_ptc.py P2
#     measured the independently-fitted gain spreading 162x across bands, and a
#     physically impossible negative read-noise intercept).
#
# The statistic below needs NEITHER, because it never estimates the noise at
# all.  Every frame of a stack is the same sensor at the same ISO at nearly the
# same level, so the noise term kappa_b * sigma^2(level) is COMMON TO ALL FRAMES
# in a tile and cancels identically when frames are compared to each other:
#
#     contrast(b, tile) = max_k Var(b,k,tile) - quantile_q_k Var(b,k,tile)
#
# This is "how much more band power does the best-focused frame carry here than
# the out-of-focus frames do".  In a tile the bracket never brought into focus
# it is zero, whatever the noise level.  In a tile some frame resolved, it is
# the resolved modulation.  That is exactly the quantity the capture-gap-versus-
# merge-defect question turns on, and it is band-agnostic: no band is selected,
# gated or thresholded; a band that is pure noise on this subject contributes a
# flat curve and therefore zero contrast, by construction rather than by choice.
#
# Residual level drift across the bracket is the one thing that does not cancel,
# so it is corrected explicitly with the measured per-tile level and a per-stack
# gain -- and because only the DIFFERENTIAL matters, an error in that gain is
# second order.  `level_correct=False` disables it, which is the control.
# ---------------------------------------------------------------------------

def through_focus_contrast(var_k: np.ndarray, level_k: np.ndarray,
                           g: float, q: float = 0.25,
                           level_correct: bool = True):
    """var_k: (K, NBAND, nr, nc).  level_k: (K, nr, nc).  Returns dict of maps."""
    v = var_k.astype(np.float64).copy()
    if level_correct:
        k = kappa()
        base = np.median(level_k, axis=0)[None, :, :]
        v -= k[None, :, None, None] * ((level_k - base) / g)[:, None, :, :]
    hi = v.max(axis=0)
    arg = v.argmax(axis=0)
    lo = np.quantile(v, q, axis=0)
    return {"contrast": hi - lo, "hi": hi, "lo": lo, "best_k": arg}
