"""Bootstrap CI for the band deltas, because a delta without one is a rumour.

Band B (0.20-0.25 cyc/px) is a thin annulus holding roughly 2.7x fewer Fourier
bins than the wideband W, so the disjoint statistic is intrinsically noisier
than the max one. `bee-1-cpl` made that concrete: it read -7.32% on `disj` and
+0.51% on `max`, on a subject whose gate barely acts at all (band-0 averaged
0.4%). One of those two numbers is measuring something that is not there.

This resamples TILES -- the unit that is actually replicated -- and pairs the
resample between the two arms, so the common ceiling and the common tile
population cancel exactly the way they do in the point estimate. An unpaired
bootstrap would inflate every interval by the between-tile variance that the
paired design already removes.
"""
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bandceiling as bc                                          # noqa: E402
from bandsweep import ARMS, SWEEP, cache_path                     # noqa: E402
from orch_sharp1to1 import CROP, luma                             # noqa: E402

NBOOT = 2000


def per_tile(subject, arm, sites, cache):
    """Per-tile ratios, kept unpooled so the bootstrap has something to resample."""
    my = luma(tifffile.imread(os.path.join(SWEEP, arm, subject + ".tiff"))
              [..., :3].astype(np.float64))
    mx, dj = [], []
    for si, (y, x) in enumerate(sites):
        mb = bc.tile_bands(my[y:y + CROP, x:x + CROP])
        c = cache[si]
        valid = ~np.isnan(c[..., 0])
        w = np.where(valid, c[..., 2], -np.inf).max(axis=0)
        a = np.where(valid, c[..., 0], -np.inf)
        pick = a.argmax(axis=0)
        b_sel = np.take_along_axis(c[..., 1], pick[None], axis=0)[0]
        with np.errstate(divide="ignore", invalid="ignore"):
            mx.append((mb[..., 2] / w).ravel())
            dj.append((mb[..., 1] / b_sel).ravel())
    return np.concatenate(mx), np.concatenate(dj)


def run(subject, seed=0):
    z = np.load(cache_path(subject), allow_pickle=True)
    sites, cache = z["sites"], z["cache"]
    cols = {a: per_tile(subject, a, sites, cache) for a in ARMS
            if os.path.exists(os.path.join(SWEEP, a, subject + ".tiff"))}
    base = cols["WHITE200"]
    rng = np.random.default_rng(seed)
    n = len(base[0])
    idx = rng.integers(0, n, size=(NBOOT, n))
    out = {}
    for a, v in cols.items():
        row = []
        for k in (0, 1):
            good = np.isfinite(base[k]) & np.isfinite(v[k]) & (base[k] > 0) & (v[k] > 0)
            b, c = base[k][good], v[k][good]
            m = len(b)
            ii = idx[:, :m] % m
            d = 100 * (np.median(c[ii], axis=1) / np.median(b[ii], axis=1) - 1)
            row.append((100 * (np.median(c) / np.median(b) - 1),
                        float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))))
        out[a] = row
    return out, n


if __name__ == "__main__":
    print("Paired tile bootstrap, %d resamples. CI excluding 0 = the arm moved." % NBOOT)
    print("%-22s %-9s %22s %22s" % ("subject", "arm", "d% max [95% CI]", "d% disj [95% CI]"))
    for s in sys.argv[1:]:
        o, n = run(s)
        for a in ARMS:
            if a not in o:
                continue
            (pm, lm, hm), (pd, ld, hd) = o[a]
            star = lambda l, h: " " if (l <= 0 <= h) else "*"
            print("%-22s %-9s %8.2f [%7.2f,%7.2f]%s %8.2f [%7.2f,%7.2f]%s"
                  % (s, a, pm, lm, hm, star(lm, hm), pd, ld, hd, star(ld, hd)))
        print("%-22s %d tiles" % (s, n))
