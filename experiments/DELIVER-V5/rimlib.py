"""rimlib.py -- the injected-rim statistic for DELIVER-V5, plus the reduction.

THE STATISTIC (hull excess).  A separable resampler whose 1-D kernel weights sum
to 1 produces each output pixel as a weighted sum of the master pixels inside its
support.  If every weight is non-negative the output must lie inside
[min, max] of that support.  So an output value OUTSIDE the local master range
is information that was not in the master: it is manufactured, and its existence
proves a negative weight.  This is a theorem, evaluated per pixel.  There is no
edge finder, no plateau, no site picking and therefore no phantom-site mode.

Re-derived here rather than imported from experiments/V-REVIEW/, per this
project's rule that numbers are re-derived with code you write.  Section 4 of
commission_rim.py checks that my implementation reproduces that lane's published
corpus figures; agreement across two independent implementations is the point.

TWO HULLS, and the difference matters:

  hull_block   EXACT.  Valid only for an integer-factor reduction where each
               output pixel reads exactly one k x k block.  The bound is the
               block's own min and max, so it is as tight as the theorem allows.
               This is what DELIVER-V5's own output is measured against.

  hull_window  GENEROUS.  A dilate/erode over a support window, for kernels whose
               support is wider and phase-dependent.  A LARGER window can only
               make the bound more forgiving, so a non-zero reading here is
               still proof.  Used to compare kernels on equal terms.

WHAT THIS STATISTIC IS BLIND TO, stated up front because a zero here is going to
be quoted:  it measures ONLY whether a value was manufactured outside the local
range.  It is blind to blur, to aliasing, and to resolution loss.  `nearest`
aliases catastrophically and scores exactly 0.000, which is arm C6 of the
commissioning bench and is the reason a second statistic (`area_err`) exists.
A rim reading of zero is NOT a claim that a reduction is good.

Units are 8-bit DN throughout, because the reduction happens after 16->8 and
8-bit DN is what the viewer's eye receives.
"""
import numpy as np

# ---------------------------------------------------------------- conversion

def to8(a16):
    """16 -> 8 bit, round to nearest, clipped.

    NOTE the .clip BEFORE the cast.  (65535 + 128) >> 8 == 256, which wraps to 0
    as a uint8.  Omitting the clip turns pure white into pure black; see
    commission_rim.py arm W1, which tests exactly this on real code in the tree.
    """
    return ((a16.astype(np.uint32) + 128) >> 8).clip(0, 255).astype(np.uint8)


# ----------------------------------------------------------------- reduction

def box_reduce(a, k):
    """Exact integer-factor area average, computed here in numpy.

    Deliberately NOT PIL.  The brief says do not assume PIL's Image.BOX is what
    you think it is; this does not need PIL to be anything, and
    commission_rim.py arm P1 then checks PIL against it rather than trusting it.

    Returns float64.  Rounding to 8 bit is a separate, explicit step so the
    hull test can be run on the unrounded value as well as the shipped one.
    """
    if a.shape[0] % k or a.shape[1] % k:
        raise ValueError("box_reduce needs an exact factor: %s by %d"
                         % (a.shape[:2], k))
    h, w = a.shape[0] // k, a.shape[1] // k
    if a.ndim == 2:
        return a.astype(np.float64).reshape(h, k, w, k).mean(axis=(1, 3))
    c = a.shape[2]
    return a.astype(np.float64).reshape(h, k, w, k, c).mean(axis=(1, 3))


def block_minmax(a, k):
    """Per-block min and max of the master: the exact hull for box_reduce."""
    h, w = a.shape[0] // k, a.shape[1] // k
    if a.ndim == 2:
        r = a.reshape(h, k, w, k)
        return r.min(axis=(1, 3)), r.max(axis=(1, 3))
    c = a.shape[2]
    r = a.reshape(h, k, w, k, c)
    return r.min(axis=(1, 3)), r.max(axis=(1, 3))


# --------------------------------------------------------------------- hulls

def hull_block(master8, out, k):
    """Exact hull excess for an integer-factor reduction.  Returns (exc, dfc)."""
    lo, hi = block_minmax(master8, k)
    o = out.astype(np.float64)
    return np.maximum(o - hi, 0.0), np.maximum(lo - o, 0.0)


def hull_window(master8, out, support=18):
    """Generous hull for an arbitrary-scale reduction to out.shape."""
    import cv2
    a = np.ascontiguousarray(master8)
    if a.ndim == 3:
        excs, dfcs = [], []
        for c in range(a.shape[2]):
            e, d = hull_window(a[..., c], out[..., c], support)
            excs.append(e)
            dfcs.append(d)
        return np.stack(excs, -1), np.stack(dfcs, -1)
    h, w = a.shape
    nh, nw = out.shape[:2]
    kk = np.ones((2 * support + 1, 2 * support + 1), np.uint8)
    hi = cv2.dilate(a, kk)
    lo = cv2.erode(a, kk)
    xs = np.clip(np.round((np.arange(nw) + 0.5) * (w / nw) - 0.5).astype(int), 0, w - 1)
    ys = np.clip(np.round((np.arange(nh) + 0.5) * (h / nh) - 0.5).astype(int), 0, h - 1)
    HI = hi[np.ix_(ys, xs)].astype(np.float64)
    LO = lo[np.ix_(ys, xs)].astype(np.float64)
    o = out.astype(np.float64)
    return np.maximum(o - HI, 0.0), np.maximum(LO - o, 0.0)


def rim_stats(exc, dfc):
    both = np.maximum(exc, dfc)
    n = both.size
    return {
        "max_bright": float(exc.max()),
        "max_dark": float(dfc.max()),
        "max": float(both.max()),
        "p99_99": float(np.percentile(both, 99.99)),
        "n_gt_1dn": int((both > 1.0).sum()),
        "n_gt_2dn": int((both > 2.0).sum()),
        "n_px": int(n),
    }


# ------------------------------------------------- the second, non-blind axis

def area_err(master8, out, k):
    """Max |out - exact area average| in DN.

    The statistic hull excess is blind to: it charges a reduction for departing
    from the ideal area average in EITHER direction, so `nearest` -- which scores
    0.000 on rim -- scores large here.  Box at an integer factor is the area
    average by construction, so this is 0 for the shipped path by definition and
    is quoted to show the two axes disagree, not to flatter anything.
    """
    ideal = box_reduce(master8, k)
    return float(np.abs(out.astype(np.float64) - ideal).max())
