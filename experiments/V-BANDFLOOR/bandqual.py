r"""QUALIFY EACH BAND ON THE MERGED MASTER.

ORCH's corrected criterion rests on V-LINEAR's finding that 0.25-0.5 cyc/px is
a NOISE band. That was measured on SINGLE-FRAME develops, by comparing an
in-focus frame against a defocused one. It is then transferred to the MERGED
master. The transfer is not free: the merge combines up to 299 frames, and the
noise gate AVERAGES wherever no frame clears the floor (32-83% duty at band 0
on this subject), so noise in the master is suppressed by up to sqrt(N) while
signal is not. A band that is noise-dominated in one frame need not be
noise-dominated after merging.

THE DIRECT TEST, on the master itself. Noise is not reproducible across
DISJOINT frame subsets; scene content is. Render EVEN-index and ODD-index
frames as two independent stacks and, per band, correlate them.

    r ~ 0     the band is noise            -> ORCH's claim for band 0
    r high    the band carries real signal -> ORCH's claim for band 1

Band edges and site selection are copied EXACTLY from ORCH's contrast_ms.py so
the answer is on their bands, not mine. Pearson r is invariant to an affine
level change, so this is insensitive to the tone-placement confound.

FOOLING DIRECTIONS: (a) misregistration between halves decorrelates real
content and would understate every band -- the coarse bands are the control,
they must come back ~1; (b) anything reproducible for a non-scene reason
(fixed-pattern noise) reads as signal -- previously excluded on this corpus by
a cross-subject control (r=+0.0026); (c) demosaic interpolation is a
deterministic function of the below-Nyquist content, so it is reproducible and
WILL read as signal -- this measures reproducibility, not independent
information.
"""
import argparse
import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

SIGMAS = [0.6366, 0.9362, 2.0, 4.0, 8.0, 16.0]     # ORCH's contrast_ms.py
S = 256


def lum(p):
    a = tifffile.imread(p)
    if a.ndim == 3:
        return a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


def octaves(x):
    out, prev = [], x
    for s in SIGMAS:
        cur = gaussian_filter(x, s)
        out.append(prev - cur)
        prev = cur
    return out


def sites(a, n):
    """contrast_ms.py's own selection: mid-scale gradient, 256px tiles."""
    g = np.hypot(*np.gradient(gaussian_filter(a, 2.0)))
    H, W = a.shape
    ny, nx = H // S, W // S
    tg = g[:ny * S, :nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
    o = np.argsort(tg.ravel())
    return {"FLAT": o[:n], "EDGE": o[-n:]}, ny, nx


def tvec(arr, f, nx):
    ty, tx = divmod(int(f), nx)
    return arr[ty * S:(ty + 1) * S, tx * S:(tx + 1) * S].ravel()


def stats(ea, ob, idx, nx):
    rs, sf = [], []
    for f in idx:
        x, y = tvec(ea, f, nx), tvec(ob, f, nx)
        x = x - x.mean(); y = y - y.mean()
        d = np.sqrt((x * x).sum() * (y * y).sum())
        r = (x * y).sum() / d if d > 0 else 0.0
        cov = (x * y).mean()
        var = 0.5 * ((x * x).mean() + (y * y).mean())
        rs.append(r)
        sf.append(cov / var if var > 0 else 0.0)
    return np.array(rs), np.array(sf)


def boot(v, seed=9, nb=4000):
    rng = np.random.default_rng(seed)
    i = rng.integers(0, len(v), size=(nb, len(v)))
    m = np.median(v[i], axis=1)
    return float(np.median(v)), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def table(pe, po, n, tag, quiet=False):
    ge, go = lum(pe), lum(po)
    assert ge.shape == go.shape
    sd, ny, nx = sites(ge, n)
    be, bo = octaves(ge), octaves(go)
    edges = [1.0 / (2.0 * np.pi * s) for s in SIGMAS]
    if not quiet:
        print("\n%s   shape %s   %d tiles per class" % (tag, ge.shape, n))
        print("  %-5s %-14s %-8s | %-26s | %-26s" % ("band", "cyc/px", "ORCH", "FLAT  r [95% CI]", "EDGE  r [95% CI]"))
    out = []
    for j in range(len(SIGMAS)):
        hi = 0.5 if j == 0 else edges[j - 1]
        lo = edges[j]
        row = {}
        line = "  %-5d %-14s %-8s |" % (j, "%.3f-%.3f" % (lo, hi),
                                        {0: "NOISE", 1: "SIGNAL"}.get(j, ""))
        for k in ("FLAT", "EDGE"):
            r, sf = stats(be[j], bo[j], sd[k], nx)
            m = boot(r)
            row[k] = m
            line += " %+.4f [%+.4f,%+.4f] |" % m
        out.append(row)
        if not quiet:
            print(line)
    return out


def commission(pe, po, n):
    print("COMMISSIONING bandqual on real pixels (per-band split-half reproducibility)")
    ge, go = lum(pe), lum(po)
    sd, ny, nx = sites(ge, n)
    be, bo = octaves(ge), octaves(go)
    rng = np.random.default_rng(4)
    rows = []
    base = {}
    for j in (0, 1, 3):
        r, _ = stats(be[j], bo[j], sd["FLAT"], nx)
        base[j] = boot(r)
    print("  baseline FLAT r: band0 %+.4f  band1 %+.4f  band3 %+.4f"
          % (base[0][0], base[1][0], base[3][0]))
    r, _ = stats(be[0], be[0], sd["FLAT"], nx)
    ok1 = boot(r)[0] > 0.999
    print("  POSITIVE identical            band0 FLAT r %+.4f  %s" % (boot(r)[0], "OK" if ok1 else "FAIL"))
    perm = be[0].copy()
    for f in sd["FLAT"]:
        ty, tx = divmod(int(f), nx)
        s_ = (slice(ty * S, (ty + 1) * S), slice(tx * S, (tx + 1) * S))
        perm[s_] = rng.permutation(perm[s_].ravel()).reshape(S, S)
    r, _ = stats(perm, bo[0], sd["FLAT"], nx)
    ok2 = abs(boot(r)[0]) < 0.05
    print("  NEGATIVE within-tile permute  band0 FLAT r %+.4f  %s" % (boot(r)[0], "OK" if ok2 else "FAIL"))
    loc = float(np.std([tvec(be[0], f, nx) for f in sd["FLAT"]]))
    nz1 = rng.normal(0, 2 * loc, ge.shape); nz2 = rng.normal(0, 2 * loc, ge.shape)
    r, _ = stats(be[0] + nz1, bo[0] + nz2, sd["FLAT"], nx)
    ok3 = boot(r)[2] < base[0][0]
    print("  DEFECT   independent noise    band0 FLAT r %+.4f  %s (must FALL)" % (boot(r)[0], "OK" if ok3 else "FAIL"))
    sh = rng.normal(0, 2 * loc, ge.shape)
    r, _ = stats(be[0] + sh, bo[0] + sh, sd["FLAT"], nx)
    ok4 = boot(r)[1] > base[0][0]
    print("  IMPROVE  shared texture       band0 FLAT r %+.4f  %s (must RISE)" % (boot(r)[0], "OK" if ok4 else "FAIL"))
    n_ok = sum([ok1, ok2, ok3, ok4])
    print("\n  COMMISSIONED %d/4" % n_ok)
    return 0 if n_ok == 4 else 1


ap = argparse.ArgumentParser()
ap.add_argument("--even", required=True)
ap.add_argument("--odd", required=True)
ap.add_argument("-n", type=int, default=12)
ap.add_argument("--commission", action="store_true")
a = ap.parse_args()
if a.commission:
    sys.exit(commission(a.even, a.odd, a.n))
table(a.even, a.odd, a.n, "per-band split-half reproducibility")
