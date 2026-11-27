"""The fine band's noise expectation against the level, measured on the stack itself.

Most (tile, plane) samples of a stack are out of focus, so within a narrow range of levels the
MEDIAN Laplacian energy per pixel is the noise's. A table over levels, monotone, interpolated in
between. (A product implementation takes this from the engine's injected noise model instead:
the 4-neighbour Laplacian of independent photosites has 20 times a photosite's variance.)
"""
import numpy as np


def fit(lap_pp, mean, bins=28, seed=1):
    lv, e = np.asarray(mean).ravel(), np.asarray(lap_pp).ravel()
    pick = np.random.default_rng(seed).choice(lv.size, size=min(lv.size, 3_000_000), replace=False)
    lv, e = np.maximum(lv[pick], 0), e[pick]
    edges = np.unique(np.percentile(lv, np.linspace(0, 99.8, bins + 1)))
    xs, ys = [], []
    for a, b in zip(edges[:-1], edges[1:]):
        s = (lv >= a) & (lv <= b)
        if s.sum() > 300:
            xs.append(float(np.median(lv[s]))); ys.append(float(np.median(e[s])))
    xs, ys = np.array(xs), np.maximum.accumulate(np.array(ys))
    return xs, ys


def apply(table, level):
    xs, ys = table
    lv = np.maximum(level, 0)
    out = np.interp(lv, xs, ys)
    # beyond the last bin: photon noise, linear in the level
    hi = lv > xs[-1]
    if np.any(hi):
        slope = (ys[-1] - ys[-2]) / max(xs[-1] - xs[-2], 1e-6)
        out = np.where(hi, ys[-1] + slope * (lv - xs[-1]), out)
    return out


def dark_floor(table):
    """A level below which brightness is not trusted as a divisor: 8 read-noise deviations."""
    return 8.0 * float(np.sqrt(table[1][0] / 20.0))
