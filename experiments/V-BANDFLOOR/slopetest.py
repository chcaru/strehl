"""Commission ORCH's energy-vs-scale SLOPE heuristic against split-half truth.

ORCH proposes (msg 6): "Read the absolute FLAT column. RISES with scale =
structure. FALLS with scale = noise." and offers it as a cheaper replacement
for V-LINEAR's in-focus/defocus qualification test.

A slope is read off ONE image. Reproducibility is read off TWO disjoint frame
halves. So the decisive test is a pair of plants with the SAME power spectrum
that differ ONLY in whether they are reproducible:

  CORRELATED : low-pass field, INDEPENDENT realisation in each half -> NOISE
  STRUCTURE  : low-pass field, IDENTICAL realisation in both halves -> SIGNAL

Both have a rising energy-vs-scale slope. If ORCH's heuristic returns the same
verdict for both, it cannot qualify a band, because it is blind to the only
property that distinguishes signal from noise.

Fooling direction, declared up front: the slope heuristic reads the SHAPE of a
power spectrum. Any reddened noise -- and post-warp resampling reddens noise,
the run banner itself prints a measured floor of 1.55x white on leaf-2-cpl --
has a rising slope and will be called structure.
"""
import argparse
import os
import numpy as np
from scipy.ndimage import gaussian_filter
import bandmetrics as bm
import nscale as ns

SIGMAS = [0.6366, 0.9362, 2.0, 4.0, 8.0, 16.0]   # committed contrast_ms.py
OUT = r"C:\dev\strehl-out\V-BANDFLOOR"
S = 256
NSITE = 12


def octaves(x):
    bands, prev = [], x
    for s in SIGMAS:
        cur = gaussian_filter(x, s)
        bands.append(prev - cur)
        prev = cur
    return bands


def sites(a):
    """ORCH's site selection, verbatim: mid-scale gradient, 12 lowest/highest."""
    mid = gaussian_filter(a, 2.0)
    gy, gx = np.gradient(mid)
    g = np.hypot(gy, gx)
    H, W = a.shape
    ny, nx = H // S, W // S
    tg = g[: ny * S, : nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
    order = np.argsort(tg.ravel())
    return order[:NSITE], order[-NSITE:], nx


def tiles(idx, arr, nx):
    out = []
    for f in idx:
        ty, tx = divmod(int(f), nx)
        out.append(arr[ty * S:ty * S + S, tx * S:tx * S + S])
    return out


def energy(idx, arr, nx):
    return float(np.mean([t.std() for t in tiles(idx, arr, nx)]))


def sigfrac(idx, be, bo, nx):
    """Split-half signal fraction for one band over the selected sites."""
    X = np.array([t.ravel() for t in tiles(idx, be, nx)], dtype=np.float64)
    Y = np.array([t.ravel() for t in tiles(idx, bo, nx)], dtype=np.float64)
    X = X - X.mean(1, keepdims=True)
    Y = Y - Y.mean(1, keepdims=True)
    cov = (X * Y).mean(1)
    var = 0.5 * ((X * X).mean(1) + (Y * Y).mean(1))
    return float(np.median(cov / np.maximum(var, 1e-30)))


def report(tag, ge, go):
    fl, ed, nx = sites(ge)
    be, bo = octaves(ge), octaves(go)
    ef = [energy(fl, b, nx) for b in be]
    sf = [sigfrac(fl, be[j], bo[j], nx) for j in range(len(SIGMAS))]
    slope = ef[-1] / max(ef[0], 1e-30)
    verdict = "STRUCTURE" if slope > 1.0 else "NOISE"
    print("  %-12s FLAT energy %s" % (tag, " ".join("%8.2f" % v for v in ef)))
    print("  %-12s  slope(last/first) %6.3f -> ORCH says %-9s | split-half signal frac %s"
          % ("", slope, verdict, " ".join("%6.3f" % v for v in sf)))
    return slope, verdict, sf[0]


def lp(shape, seed, sig=1.6):
    r = np.random.default_rng(seed).normal(size=shape)
    r = gaussian_filter(r, sig)
    return r / r.std()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", required=True, help="subdir/prefix, e.g. nscale/112MSDCF")
    ap.add_argument("--arm", default="A-unset")
    ap.add_argument("--k", type=float, default=3.0, help="plant amplitude x flat band-0 std")
    a = ap.parse_args()

    sub, pre = a.pair.split("/")
    pe = os.path.join(OUT, sub, "%s__EVEN__%s.tiff" % (pre, a.arm))
    po = os.path.join(OUT, sub, "%s__ODD__%s.tiff" % (pre, a.arm))
    ge, cme, cfe = ns.load64(pe)
    go, cmo, cfo = ns.load64(po)
    fl, ed, nx = sites(ge)
    b0 = octaves(ge)[0]
    amp = a.k * energy(fl, b0, nx)
    print("=== SLOPE HEURISTIC COMMISSIONING on %s (%s) ===" % (a.pair, a.arm))
    print("clip EVEN %.4f%%  ODD %.4f%%   plant amplitude %.1f DN (%.1fx flat band-0 std)"
          % (100 * cfe, 100 * cfo, amp, a.k))
    print("bands (committed contrast_ms.py sigmas):", SIGMAS)
    print()
    print("PLANT: none (the real merged master)")
    report("NULL", ge, go)
    print()
    print("PLANT: white noise, INDEPENDENT per half  -> truly noise, falling slope")
    w = amp * 1.0
    report("WHITE", ge + np.random.default_rng(11).normal(0, w, ge.shape),
           go + np.random.default_rng(12).normal(0, w, go.shape))
    print()
    print("PLANT: low-pass field, INDEPENDENT per half -> truly NOISE, rising slope")
    f1, f2 = lp(ge.shape, 21), lp(ge.shape, 22)
    report("CORRELATED", ge + amp * f1, go + amp * f2)
    print()
    print("PLANT: low-pass field, IDENTICAL in both halves -> truly SIGNAL, same spectrum")
    f3 = lp(ge.shape, 31)
    report("STRUCTURE", ge + amp * f3, go + amp * f3)


if __name__ == "__main__":
    main()

