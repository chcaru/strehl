"""Ring statistic: a dip that RECOVERS, which a gradient does not do.

An illumination ramp falls away monotonically and never comes back. A ring is a
local maximum followed by a trough followed by a recovery. Requiring the
recovery is what separates the two, and it is why the earlier version scored
coffee-bean's backdrop falloff as a 2.8 percent "null".

    peak at t1 -> trough at t2 > t1 -> recovery = max(v[t2:]) - v[t2]
    accepted only when recovery >= RECOVER_FRAC * (v[t1] - v[t2])

Reported as a fraction of that group's far field. The same function scores a
NULL WINDOW out in flat backdrop, giving each subject its own noise floor.
"""
import numpy as np

RING_LO, RING_HI = 0.0, 140.0
NULL_LO, NULL_HI = 170.0, 300.0
RECOVER_FRAC = 0.5


def dip(grid, med, far, lo, hi):
    grid = np.asarray(grid, float); med = np.asarray(med, float)
    best = dict(drop=0.0, frac=0.0, t_peak=float("nan"), t_trough=float("nan"),
                recov=0.0)
    idx = np.nonzero((grid >= lo) & (grid <= hi))[0]
    if idx.size < 3:
        return best
    for a in range(idx[0], idx[-1]):
        for b in range(a + 1, idx[-1] + 1):
            drop = med[a] - med[b]
            if drop <= best["drop"]:
                continue
            tail = med[b:]
            recov = float(tail.max() - med[b]) if tail.size else 0.0
            if recov >= RECOVER_FRAC * drop:
                best = dict(drop=float(drop), frac=float(drop / far),
                            t_peak=float(grid[a]), t_trough=float(grid[b]),
                            recov=recov)
    return best


def ring_and_null(grid, med, far):
    return (dip(grid, med, far, RING_LO, RING_HI),
            dip(grid, med, far, NULL_LO, NULL_HI))
