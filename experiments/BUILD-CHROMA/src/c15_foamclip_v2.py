"""Is foam's corner blue elevation a CLIPPING artifact?  (v2)

V1 OF THIS SCRIPT PRODUCED A FALSE GREEN AND IS THE REASON THIS ONE EXISTS.
It gated on fractions of 65535, but the master's maximum DN is 52239, so every
threshold sat ABOVE the image maximum and the gate removed exactly zero pixels
in all eight rows. It then printed "the elevation survives removal of every
near-clip pixel". The tells were an identical kept-count on every row and a
random control with sd 0.000 over 20 trials -- the controls fired, the verdict
logic simply did not read them. Hence the assertions below.

WHAT THE MASTER ACTUALLY CONTAINS. There is no clipping in it:
no pile-up at the top (>=0.999*max is 0.0000% in every channel) and the
per-channel maxima are far apart (R 42213, G 38921, B 52239) rather than sharing
a ceiling. p99 is ~9,400 against a max of 52,239 -- a long thin highlight tail,
which is the opposite of a clipped histogram.

WHY THAT DOES NOT ACQUIT CLIPPING, AND HOW THE GATE HAD TO CHANGE. ORCH's 0.76%
blown pixels is a RAW/scene statistic. Raw clipping happens before the tone
curve, so its colour error is baked in and then mapped by a monotonic curve into
high-but-unclipped master values. Absence of a plateau therefore proves only that
I cannot find clipping by looking for a ceiling. The correct gate is still on
level, but defined by PERCENTILE of this master -- monotonicity means the top
0.76% of master values is (approximately) the raw-blown set.

CONTROLS, all three of which v1 needed and lacked:
  1. The gate must be PROVEN to remove pixels. Asserted, per threshold.
  2. MATCHED-COUNT RANDOM REMOVAL, which must actually subsample. v1's control
     kept every pixel whenever the requested count equalled the band count.
  3. DILATION, because a pixel adjacent to a blown one is already contaminated
     through the gradient and the colour difference.

ORCH's files are opened read-only and never modified.
"""

import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import binary_dilation

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import dump

ON = r"C:\dev\strehl-out\ORCH-CADEF\foam-caon.tif"
NBANDS = 6
RNG = np.random.default_rng(20260826)


def load(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    assert a.ndim == 3 and a.shape[2] == 3, f"expected HxWx3, got {a.shape}"
    return a


def bands(bg, rad, rmax, mask):
    out = []
    for i in range(NBANDS):
        lo, hi = i / NBANDS * rmax, (i + 1) / NBANDS * rmax
        m = mask & (rad >= lo) & (rad < hi)
        n = int(m.sum())
        out.append((n, float(bg[m].mean()) if n else float("nan")))
    return out


def main():
    a = load(ON)
    f = a.astype(np.float32)
    g, b = f[..., 1], f[..., 2]
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w]
    rad = np.hypot(yy - (h - 1) / 2.0, xx - (w - 1) / 2.0)
    rmax = rad.max()

    gy, gx = np.gradient(g)
    strong = np.hypot(gx, gy) >= np.percentile(np.hypot(gx, gy), 99.0)
    bg = np.abs(b - g) / np.maximum(g, 1.0)
    lum = f.max(axis=2)

    print("=" * 94)
    print("BASELINE -- ORCH's ungated band table (CA-ON arm), reproduced")
    print("=" * 94)
    base = bands(bg, rad, rmax, strong)
    for i, (n, v) in enumerate(base):
        tag = "   <- centre" if i == 0 else ("   <- corner" if i == NBANDS - 1 else "")
        print(f"  band {i}  edges {n:>8,}  |B-G|/G {v:.4f}{tag}")
    base_ratio = base[-1][1] / base[0][1]
    print(f"  corner/centre = {base_ratio:.3f}   (ORCH reported 1.88)")

    print()
    print("=" * 94)
    print("LEVEL GATE -- by PERCENTILE of this master, with the gate PROVEN to bite")
    print("=" * 94)
    print(f"  {'drop top':>9} {'DN':>7} {'dil':>4} {'kept':>9} {'removed':>9} "
          f"{'centre':>8} {'corner':>8} {'ratio':>7}")
    results = []
    n_base = int(strong.sum())
    for pct in (0.76, 2.0, 5.0, 10.0, 25.0):
        thr = float(np.percentile(lum, 100 - pct))
        for dil in (0, 3):
            hot = lum >= thr
            if dil:
                hot = binary_dilation(hot, iterations=dil)
            m = strong & ~hot
            removed = n_base - int(m.sum())
            # CONTROL 1: the gate must actually do something.
            assert removed > 0, (
                f"GATE INERT at pct={pct} dil={dil}: removed 0 of {n_base} edge "
                f"pixels. This is the v1 failure; refusing to report it as a pass.")
            bb = bands(bg, rad, rmax, m)
            if any(n == 0 for n, _ in bb):
                print(f"  {pct:9.2f} {thr:7.0f} {dil:4d}   band emptied -- not interpretable")
                continue
            ratio = bb[-1][1] / bb[0][1]
            results.append({"pct": pct, "thr": thr, "dilate": dil,
                            "kept": int(m.sum()), "removed": removed,
                            "centre": bb[0][1], "corner": bb[-1][1], "ratio": ratio})
            print(f"  {pct:9.2f} {thr:7.0f} {dil:4d} {int(m.sum()):9,} {removed:9,} "
                  f"{bb[0][1]:8.4f} {bb[-1][1]:8.4f} {ratio:7.3f}")

    strict = results[-1]
    print()
    print("=" * 94)
    print("CONTROL 2 -- matched-count RANDOM removal (level, or merely sample size?)")
    print("=" * 94)
    hot = binary_dilation(lum >= float(np.percentile(lum, 100 - strict["pct"])),
                          iterations=strict["dilate"])
    lg = strong & ~hot
    ratios = []
    for _ in range(20):
        keep = np.zeros_like(strong)
        for i in range(NBANDS):
            lo, hi = i / NBANDS * rmax, (i + 1) / NBANDS * rmax
            inband = strong & (rad >= lo) & (rad < hi)
            idx = np.flatnonzero(inband.ravel())
            want = int((lg & (rad >= lo) & (rad < hi)).sum())
            # CONTROL 2 must actually subsample, which v1's did not.
            assert want < idx.size, "random control degenerate: nothing to drop"
            sel = RNG.choice(idx, want, replace=False)
            keep.ravel()[sel] = True
        bb = bands(bg, rad, rmax, keep)
        ratios.append(bb[-1][1] / bb[0][1])
    ratios = np.array(ratios)
    sd = ratios.std(ddof=1)
    assert sd > 0, "random control frozen: sd == 0, the v1 signature"
    print(f"  random removal of the SAME COUNT: mean {ratios.mean():.3f}  sd {sd:.4f}  "
          f"range [{ratios.min():.3f}, {ratios.max():.3f}]")
    print(f"  level-gated                     : {strict['ratio']:.3f}")
    print(f"  separation                      : {abs(strict['ratio'] - ratios.mean()) / sd:.1f} sd")

    print()
    print("=" * 94)
    print("VERDICT")
    print("=" * 94)
    print(f"  ungated {base_ratio:.3f}  ->  level-gated {strict['ratio']:.3f} "
          f"(top {strict['pct']}% of luminance and its shoulder removed, "
          f"{strict['removed']:,} edge pixels dropped)")
    if strict["ratio"] > 1.4:
        print("  CLIPPING IS NOT THE EXPLANATION. The corner blue elevation survives")
        print("  removing the entire bright tail that raw clipping maps into.")
    else:
        print("  CLIPPING EXPLAINS IT -- channel-asymmetric clipping defect, a build task.")

    dump("c15_foamclip", {"baseline_ratio": base_ratio, "gates": results,
                          "rand_mean": float(ratios.mean()), "rand_sd": float(sd)})


if __name__ == "__main__":
    main()
