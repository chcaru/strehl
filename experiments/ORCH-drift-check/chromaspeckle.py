"""Chroma speckle: a chroma excursion WITHOUT a matching luma excursion.

TWO INSTRUMENTS DIED BEFORE THIS ONE, and both deaths are the point.

V1 asked "is this pixel magenta". Negative arm: an achromatic ramp. It passed,
then reported 109MSDCF as 11.76% magenta with 84.21% of saturated pixels
affected -- a catastrophic-looking defect in a gate-PASSED master. 109MSDCF is
a photograph of PINK FABRIC. The arm only proved the detector ignores grey; it
never asked whether the detector ignores a legitimately coloured subject.

V2 asked "is this pixel magenta while its neighbourhood is not", and added the
pink patch as arm N2. It passed N2 -- by going BLIND inside coloured regions.
Arm P2 (a planted defect INSIDE the pink patch) caught it: SPECKLE 0.0000%,
fired=False, on a defect that was certainly there. N2 was passed by detecting
nothing, which is how every negative arm can be passed.

V3, here, works on the CONTINUOUS chroma signal instead of a thresholded mask:

    c  = (R - G) + (B - G)        magenta-green opponent axis, continuous
    dc = c - boxmean(c, 5)        chroma excursion from the neighbourhood
    dy = |G - boxmean(G, 5)|      luma excursion from the neighbourhood

    speckle = (dc > CHROMA_DN) AND (dy < LUMA_DN)

The physics: green is sampled at twice the density of red and blue in a Bayer
CFA, so luma is well sampled and chroma is interpolated. Demosaic chroma error
is therefore predominantly chroma-only. A real edge, a real coloured object,
and chromatic aberration all move luma too, and are excluded by the dy term.

  - a uniformly pink subject has dc ~ 0 everywhere: not a defect, not detected
  - the boundary between a pink object and a grey one has large dc AND large
    dy: a real edge, excluded by construction, and arm N3 proves it
  - an isolated interpolated chroma error has large dc and small dy: detected

FIVE ARMS. N3 and P2 are the ones that killed the previous two versions.
"""
import os
import sys

import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
K = 5
CHROMA_DN = 2000.0   # absolute, in 16-bit DN. NOT derived from the data's own
                     # spread: a threshold set from the data it thresholds
                     # cancels the amplitude and measures only tail shape,
                     # which is how overshoot_frac came to read backwards.
LUMA_DN = 1500.0
FIRE = 1e-4          # 0.01% of frame


def box_mean(x, k):
    p = k // 2
    a = np.pad(x, p, mode="edge").astype(np.float64)
    c = np.cumsum(np.cumsum(a, axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0)))
    h, w = x.shape
    return ((c[k:k + h, k:k + w] - c[0:h, k:k + w]
             - c[k:k + h, 0:w] + c[0:h, 0:w]) / float(k * k)).astype(np.float32)


def speckle(a):
    r = a[..., 0].astype(np.float32)
    g = a[..., 1].astype(np.float32)
    b = a[..., 2].astype(np.float32)
    c = (r - g) + (b - g)
    dc = c - box_mean(c, K)
    dy = np.abs(g - box_mean(g, K))
    hit = (dc > CHROMA_DN) & (dy < LUMA_DN)
    return float(hit.mean()), float(dc[hit].mean()) if hit.any() else 0.0


def arm(a, label, expect, ok_acc):
    f, mag = speckle(a)
    fired = f > FIRE
    good = (fired == expect)
    print("  %-38s speckle %8.4f%%  mean dc %7.0f  fired=%-5s %s"
          % (label, f * 100, mag, fired, "OK" if good else "*** FAILED ***"))
    return ok_acc and good


def commission():
    print("=== COMMISSIONING (5 arms) ===")
    rng = np.random.default_rng(20260824)
    ceil = 65535
    ok = True

    ramp = np.zeros((512, 512, 3), dtype=np.uint16)
    v = np.linspace(0, ceil, 512).astype(np.uint16)
    for ch in range(3):
        ramp[..., ch] = v[None, :]
    ok = arm(ramp, "N1 achromatic ramp", False, ok)

    def noisy(base, sd=400):
        return np.clip(base.astype(np.int32)
                       + rng.normal(0, sd, base.shape).astype(np.int32),
                       0, ceil).astype(np.uint16)

    pink = np.zeros((512, 512, 3), dtype=np.uint16)
    # the MEASURED channel medians of 109MSDCF, the subject V1 falsely convicted
    pink[..., 0], pink[..., 1], pink[..., 2] = 63231, 22081, 26574
    pink = noisy(pink)
    ok = arm(pink, "N2 saturated pink subject", False, ok)

    edge = pink.copy()
    edge[:, 256:, 0] = 20000
    edge[:, 256:, 1] = 20000
    edge[:, 256:, 2] = 20000
    edge = noisy(edge)
    ok = arm(edge, "N3 pink/grey EDGE (large dc AND dy)", False, ok)

    def plant(base):
        """Chroma-ONLY plant: R and B move, G does not. This is the shape of
        real demosaic chroma error, because G is sampled twice as densely."""
        out = base.copy().astype(np.int32)
        ys, xs = rng.integers(3, 509, 900), rng.integers(3, 509, 900)
        out[ys, xs, 0] += 5000
        out[ys, xs, 2] += 5000
        return np.clip(out, 0, ceil).astype(np.uint16)

    grey = noisy(np.full((512, 512, 3), 20000, dtype=np.uint16))
    ok = arm(plant(grey), "P1 chroma speckle on neutral", True, ok)
    ok = arm(plant(pink), "P2 chroma speckle INSIDE the pink subject", True, ok)

    print("=== COMMISSIONING %s ===\n" % ("PASSED" if ok else "FAILED"))
    return ok


def main():
    if not commission():
        print("Instrument is not trustworthy. No corpus number is reported.")
        return 1
    names = sys.argv[1:] or sorted(
        set(f.split("--")[0] for f in os.listdir(SRC) if f.endswith(".tiff")))
    print("=== CORPUS ===")
    rows, missing = [], []
    for name in names:
        p = None
        for cand in sorted(os.listdir(SRC)):
            if cand.startswith(name) and cand.endswith(".tiff"):
                p = os.path.join(SRC, cand)
                break
        if p is None:
            missing.append(name)
            continue
        a = tifffile.imread(p)
        if a.ndim != 3:
            missing.append(name)
            continue
        f, mag = speckle(a)
        rows.append((name, f, mag))
    rows.sort(key=lambda r: -r[1])
    for name, f, mag in rows:
        print("  %-30s speckle %8.4f%%   mean dc %7.0f DN" % (name, f * 100, mag))
    for name in missing:
        print("  %-30s NOT EXAMINED" % name)
    print("\n  examined %d   not examined %d   total %d"
          % (len(rows), len(missing), len(rows) + len(missing)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
