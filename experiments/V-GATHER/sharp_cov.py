"""FIELD COVERAGE -- the statistic that prices the PRODUCT rather than the cost.

A per-site peak-detail ratio asks "is the master sharper than the best frame
HERE". A single frame wins that by definition wherever it is in focus, minus
resampling, which is why a well-built ratio lands near 1.0 on a working
stacker. It measures the cost and none of the benefit.

Nobody stacks 299 frames to beat the best frame at one point. They stack to
have the WHOLE SUBJECT sharp at once. So:

    B_i   detail of the best single frame AT SITE i -- the per-site oracle,
          what a perfect selector could achieve there. Measured, not planted.
    M_i   detail of the master at site i.
    cov(X; t) = fraction of sites where X_i >= t * B_i.

Three properties this has and a sharpness ratio does not:

  * The CEILING IS SET BY THE DATA. The oracle cannot be exceeded, so the
    "real subjects read above the RECONSTRUCT arm" pathology cannot occur.
  * The FLOOR IS MEASURED, NOT PLANTED. Any single frame scores its own depth
    of field, a physically meaningful number nobody had to invent.
  * It is GAUGE-INVARIANT BY CONSTRUCTION when M and B come from the same
    pipeline -- which kills the auto-exposure defect at the root instead of
    correcting for it.

Per-site detail is F2's F, which is already commissioned: NULL exact to
1.000000, amplitude invariant to machine precision, physics arm <= 1, real
pixel plants monotone. Coverage is its CDF.
"""
import os, sys, numpy as np, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands as SB
import sharp_F2 as S2

TOLS = (0.30, 0.50, 0.70, 0.80, 0.90, 1.00)


def cov_from(r, tols=TOLS):
    """CDF of the per-site detail ratio over sites that passed the gate."""
    f = r["F"][r["ok"]]
    f = f[np.isfinite(f)]
    if f.size == 0:
        return None, 0
    return np.array([float((f >= t).mean()) for t in tols]), int(f.size)


def oracle_numerator(z, **kw):
    """A synthetic master assembled by taking the per-site argmax frame.

    This is the CEILING ARM. It cannot be beaten and it must score 1.000 at
    every tolerance <= 1. A ceiling that cannot be reached means the scale is
    wrong, and it says so before any real subject does.
    """
    base = S2.evaluate(z, **kw)
    A = z["A"].astype(np.float64)
    bk = base["bestk"]
    return A[bk, np.arange(A.shape[1])]


def frame_coverage(z, tols=TOLS):
    """PHYSICS-FIXED ARM and the FLOOR, in one pass.

    Every f####.tiff is a STREHL_ONLY_FRAME render: one source frame, no
    election, through the identical pipeline. Such a render CANNOT reconstruct,
    so its coverage is its own depth of field and cannot be 1.0. If it is, the
    statistic is not measuring coverage.
    """
    nf = z["A"].shape[0]
    out = np.full((nf, len(tols)), np.nan)
    for j in range(nf):
        c, n = cov_from(S2.evaluate(z, numer=j), tols)
        if c is not None:
            out[j] = c
    return out


def oracle_coherence(z):
    """DENOMINATOR ARM: is the oracle selecting DEPTH, or is it selecting NOISE?

    A focus stack of a 3-D subject has a depth map. The frame that wins at site
    i should therefore be close to the frame that wins at the site next to it.
    If the winning index is spatially incoherent the oracle is chasing noise --
    which is exactly how statistic E came to select the most defocused frame.

    Compared against a shuffle of the same values, so the null is the same
    marginal distribution with the geometry destroyed.
    """
    r = S2.evaluate(z)
    sites = np.array([list(s) for s in z["sites"]])
    ok = r["ok"]
    if ok.sum() < 12:
        return None
    ys, xs, bk = sites[ok, 0], sites[ok, 1], r["bestk"][ok].astype(float)
    ys = ys.astype(float); xs = xs.astype(float)
    d2 = (ys[:, None] - ys[None, :]) ** 2 + (xs[:, None] - xs[None, :]) ** 2
    np.fill_diagonal(d2, np.inf)
    nn = np.argmin(d2, axis=1)
    real = float(np.mean(np.abs(bk - bk[nn])))
    rng = np.random.default_rng(11)
    sh = [float(np.mean(np.abs(bk - rng.permutation(bk)[nn]))) for _ in range(200)]
    return real, float(np.mean(sh)), float(np.std(sh))

