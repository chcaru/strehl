"""ARE THE TWO HALF-STACKS OF EACH ARM ACTUALLY IN REGISTER?

WHY THIS HAD TO BE MEASURED BEFORE cohfree.py's NUMBER COULD BE BELIEVED.
cohfree.py reports strehl's coherent fraction at 0.05-0.10 cyc/px as 0.897
while enfuse's is 0.978.  At a period of 10-20 px there is essentially no photon
noise left to be incoherent about, so a 10% coherence deficit there cannot be
noise -- it is a phase error, i.e. the two half-stacks are not on the same
raster.  A rigid offset d suppresses the cross-spectrum by cos(2*pi*f*d), which
is ~1 at coarse f and devastating at fine f, so it would masquerade EXACTLY as
"strehl resolves less".

The suspicion has a mechanism.  run_coh.ps1 gives the comparators one shared
alignment pass over all 63 frames and then fuses subsets of it, so their halves
are co-registered BY CONSTRUCTION.  strehl's halves were produced by running
strehl separately on each half-stack, so each half chose its own alignment
reference from its own frames.  That asymmetry hands the comparator an
advantage strehl does not have, and it runs AGAINST strehl -- which is the
direction this lane is least entitled to be careless in, because it is the
direction that produces a false retraction rather than a false win.

METHOD.  Per ROI, plain cross-correlation of the two half-stack crops at full
resolution, then a parabolic fit through the peak and its two neighbours in
each axis for the sub-pixel part.  Cross-correlation, not phase correlation,
for the reason h2.integer_shift documents: whitening promotes the
noise-dominated high frequencies and returns spurious shifts on exactly this
kind of pair.

READING, fixed before the numbers:
    both arms |d| << 0.1 px   ->  cohfree.py's comparison is sound as it stands.
    strehl |d| ~ 0.5-1 px     ->  strehl's coherence is suppressed by geometry,
                                  its C is an UNDERESTIMATE, and the coherent
                                  comparison must be redone with the offset
                                  removed before it means anything.

INVOCATION (rule 47).  Reads:
    strehl      C:\\dev\\strehl-out\\V-H2H2\\lin\\113-{A,B}-g1.tiff
    comparator  C:\\dev\\strehl-out\\V-LINEAR2\\out\\coh-<tag>-{A,B}.tif
Writes nothing.  Prints only.

    python abshift.py [nroi=24]
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import h2                                                        # noqa: E402
import rois                                                      # noqa: E402
from h2h2b import Comp, load, T, PAD                             # noqa: E402
from h2free import FREE                                          # noqa: E402
from cohfree import ARMS, OUT, SCALE                             # noqa: E402


def subpixel_shift(a, b, maxshift=4):
    """(dy, dx) to sub-pixel, by cross-correlation plus a parabolic peak fit."""
    aw = (a - a.mean()) * h2.window(a.shape[0])
    bw = (b - b.mean()) * h2.window(b.shape[0])
    c = np.real(np.fft.ifft2(np.fft.fft2(aw) * np.conj(np.fft.fft2(bw))))
    t = c.shape[0]
    k = maxshift
    win = np.full((2 * k + 1, 2 * k + 1), -np.inf)
    for i in range(-k, k + 1):
        for j in range(-k, k + 1):
            win[i + k, j + k] = c[i % t, j % t]
    iy, ix = np.unravel_index(np.argmax(win), win.shape)
    if iy in (0, 2 * k) or ix in (0, 2 * k):
        return float(iy - k), float(ix - k), False
    def par(m, l, r):
        d = l - 2 * m + r
        return 0.0 if d == 0 else 0.5 * (l - r) / d
    dy = (iy - k) + par(win[iy, ix], win[iy - 1, ix], win[iy + 1, ix])
    dx = (ix - k) + par(win[iy, ix], win[iy, ix - 1], win[iy, ix + 1])
    return float(dy), float(dx), True


def main():
    nroi = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    F1 = load("113-full-g1")
    detail, flat, counts = rois.census(F1, t=T, pad=PAD, flat_frac=0.10)
    rng = np.random.default_rng(11)
    det = [detail[i] for i in rng.permutation(len(detail))[:nroi]]

    print("=" * 92)
    print("HALF-STACK REGISTRATION, per arm")
    print("=" * 92)

    arms = [("strehl 113-A/B", load("113-A-g1"), load("113-B-g1"), 1.0)]
    for tag in ("enfuse", "fs15"):
        _, fa, fb, label = ARMS[tag]
        pa, pb = os.path.join(OUT, fa), os.path.join(OUT, fb)
        if os.path.exists(pa) and os.path.exists(pb):
            W = FREE[tag]["weights"]
            arms.append((label[:28], Comp(dict(path=pa, weights=W)),
                         Comp(dict(path=pb, weights=W)), SCALE[tag]))

    for label, A, B, S in arms:
        TC = int(round(T / S))
        dys, dxs = [], []
        for (y, x) in det:
            y0 = int(round(y / S)); x0 = int(round(x / S))
            ca, na = A.crop(y0, x0, TC)
            cb, nb = B.crop(y0, x0, TC)
            if ca is None or cb is None or na or nb:
                continue
            dy, dx, ok = subpixel_shift(ca, cb)
            if ok:
                dys.append(dy); dxs.append(dx)
        if not dys:
            print(f"  {label:<30} no usable ROIs")
            continue
        dy = np.array(dys); dx = np.array(dxs)
        r = np.hypot(dy, dx)
        print(f"  {label:<30} n={len(dy):3d}  "
              f"dy median {np.median(dy):+7.3f}  dx median {np.median(dx):+7.3f}"
              f"  |d| median {np.median(r):6.3f} px  p90 {np.percentile(r, 90):6.3f}")

    print("\n  A rigid offset d suppresses the cross-spectrum by cos(2*pi*f*d).")
    print("  At the pre-registered band midpoint f = 0.225 cyc/px:")
    for d in (0.1, 0.25, 0.5, 0.75, 1.0):
        print(f"    |d| = {d:4.2f} px  ->  coherence x {np.cos(2 * np.pi * 0.225 * d):6.3f}"
              f"   (0.05-0.10 midpoint f=0.075 -> x {np.cos(2 * np.pi * 0.075 * d):6.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
