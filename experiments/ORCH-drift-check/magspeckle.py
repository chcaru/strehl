"""Magenta SPECKLE, not magenta. The first version of this could not tell a
defect from a pink subject, and reported a pink subject as a defect.

WHAT WENT WRONG THE FIRST TIME. The statistic was "R-G > t AND B-G > t", and
its negative arm was an achromatic ramp (R=G=B). That arm only ever proved the
detector ignores GREY. It never asked whether the detector ignores a
legitimately COLOURED subject. Run on the corpus it reported 109MSDCF as
11.76% magenta, 84.21% of saturated pixels, rising monotonically with luma --
a catastrophic-looking highlight defect in a gate-PASSED master.

109MSDCF is a photograph of pink fabric. The channel medians refuted the
clipping story before the picture did: R 63231, G 22081, B 26574, with 0.0% of
EVERY channel at the ceiling. Nothing was clipping. The subject was pink.

THE DISCRIMINATOR. Subject colour is spatially COHERENT: a pink object is pink
over large contiguous regions. Demosaic chroma noise is ISOLATED: single pixels
and tiny clusters surrounded by neighbours of a different colour. So do not ask
"is this pixel magenta". Ask "is this pixel magenta while its neighbourhood is
not". That question a pink subject answers no.

COMMISSIONING, four arms, and the third is the one that killed version one:
  N1 achromatic ramp            must not fire   (grey is not magenta)
  N2 SATURATED PINK PATCH       must not fire   (a coloured subject is not a defect)
  P1 isolated magenta speckle   must fire       (this is the actual defect)
  P2 speckle ON the pink patch  must fire       (a defect inside a coloured
                                                 subject must still be found;
                                                 else N2 was passed by going blind)
P2 exists because the cheap way to pass N2 is to stop detecting anything in
coloured regions, which would pass every negative arm and find nothing real.
"""
import os
import sys

import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
MAG_DN = 1200.0    # how far R and B must both exceed G, in 16-bit DN
NB = 5             # neighbourhood half-window is NB//2
ISO_MAX = 0.25     # magenta fraction of the neighbourhood, above which it is
                   # a coherent region (subject) rather than a speckle (defect)


def box_mean(x, k):
    p = k // 2
    a = np.pad(x, p, mode="edge")
    c = np.cumsum(np.cumsum(a, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = x.shape
    return (c[k:k + h, k:k + w] - c[0:h, k:k + w]
            - c[k:k + h, 0:w] + c[0:h, 0:w]) / float(k * k)


def speckle(a):
    """Returns (magenta_frac, speckle_frac). speckle_frac is the defect."""
    r = a[..., 0].astype(np.float32)
    g = a[..., 1].astype(np.float32)
    b = a[..., 2].astype(np.float32)
    m = ((r - g > MAG_DN) & (b - g > MAG_DN)).astype(np.float32)
    if m.sum() == 0:
        return 0.0, 0.0
    local = box_mean(m, NB)
    # isolated: this pixel is magenta but its neighbourhood mostly is not
    iso = (m > 0) & (local <= ISO_MAX)
    return float(m.mean()), float(iso.mean())


def arm(a, label, expect_fire, thresh=1e-4):
    mf, sf = speckle(a)
    fired = sf > thresh
    ok = (fired == expect_fire)
    print("  %-32s magenta %7.4f%%  SPECKLE %7.4f%%  fired=%-5s  %s"
          % (label, mf * 100, sf * 100, fired, "OK" if ok else "*** FAILED ***"))
    return ok


def commission():
    print("=== COMMISSIONING ===")
    rng = np.random.default_rng(20260824)
    ceil = 65535
    ok = True

    ramp = np.zeros((512, 512, 3), dtype=np.uint16)
    v = np.linspace(0, ceil, 512).astype(np.uint16)
    for c in range(3):
        ramp[..., c] = v[None, :]
    ok &= arm(ramp, "N1 achromatic ramp", False)

    # a saturated pink patch with the MEASURED channel ratios of 109MSDCF
    pink = np.zeros((512, 512, 3), dtype=np.uint16)
    pink[..., 0] = 63231
    pink[..., 1] = 22081
    pink[..., 2] = 26574
    pink = np.clip(pink.astype(np.int32)
                   + rng.normal(0, 400, pink.shape).astype(np.int32), 0, ceil).astype(np.uint16)
    ok &= arm(pink, "N2 saturated pink subject", False)

    def plant(base):
        out = base.copy().astype(np.int32)
        ys = rng.integers(2, 510, 900)
        xs = rng.integers(2, 510, 900)
        out[ys, xs, 0] += 6000
        out[ys, xs, 2] += 6000
        out[ys, xs, 1] -= 3000
        return np.clip(out, 0, ceil).astype(np.uint16)

    grey = np.full((512, 512, 3), 20000, dtype=np.uint16)
    grey = np.clip(grey.astype(np.int32)
                   + rng.normal(0, 400, grey.shape).astype(np.int32), 0, ceil).astype(np.uint16)
    ok &= arm(plant(grey), "P1 speckle on neutral", True)
    ok &= arm(plant(pink), "P2 speckle INSIDE the pink subject", True)

    print("=== COMMISSIONING %s ===\n" % ("PASSED" if ok else "FAILED"))
    return ok


def main():
    if not commission():
        print("Instrument is not trustworthy. No corpus number is reported.")
        return 1
    names = sys.argv[1:] or sorted(
        set(f.split("--")[0] for f in os.listdir(SRC) if f.endswith(".tiff")))
    print("=== CORPUS (speckle %% is the defect; magenta %% is not) ===")
    rows = []
    for name in names:
        p = None
        for cand in sorted(os.listdir(SRC)):
            if cand.startswith(name) and cand.endswith(".tiff"):
                p = os.path.join(SRC, cand)
                break
        if p is None:
            rows.append((name, None, None))
            continue
        a = tifffile.imread(p)
        if a.ndim != 3:
            rows.append((name, None, None))
            continue
        mf, sf = speckle(a)
        rows.append((name, mf, sf))
    rows.sort(key=lambda r: (-1 if r[2] is None else -r[2]))
    n_ex = 0
    for name, mf, sf in rows:
        if sf is None:
            print("  %-30s NOT EXAMINED" % name)
            continue
        n_ex += 1
        print("  %-30s magenta %8.4f%%   SPECKLE %8.4f%%" % (name, mf * 100, sf * 100))
    print("\n  examined %d, not examined %d, total %d"
          % (n_ex, len(rows) - n_ex, len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
