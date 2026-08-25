"""Profile the bimodality detector against distance from the silhouette.

This is the same instrument that settled the halo mechanism: a dose-response
ladder, not a single number. It exists because the first two readings of this
detector were both wrong in instructive ways.

  1. A plain `r2 / r1` prominence fired on 54% of clean defocused ground, and
     at any fixed false-positive rate the near-silhouette pixels fired 3-4x
     LESS than clean ground. On featureless background *neither* peak is real,
     so the ratio tends to 1 by noise alone -- it measured the absence of a
     dominant peak, not the presence of two.

  2. Stratifying by the fix's own `blend` coverage is circular and noisy: the
     coverage is derived from the guide, which is itself haloed, and the
     "treated" population is mostly foreground interior that is genuinely
     unimodal.

Distance from a depth step in the guide is neither. It is an external axis, it
is the axis the halo itself lives on, and it lets the obvious confound be
tested rather than argued: if the second mode only looked strong near edges
because there is *more contrast* near edges, then the FIRST mode would rise
there too. It does not -- it falls.
"""

import argparse
import os

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, grey_dilation, grey_erosion

BANDS = ((0, 2), (2, 4), (4, 6), (6, 9), (9, 13), (13, 18), (18, 26), (26, 40),
         (40, 80), (80, 400))


def read(d, name, scale):
    a = tifffile.imread(os.path.join(d, name))
    assert a.dtype == np.uint16, f"{name} is {a.dtype}, refusing to guess"
    return a.astype(np.float32) / scale


def profile(dump, step_mult=2.0):
    z1 = read(dump, "bimodal-first-mode-z.tif", 6553.5)
    z2 = read(dump, "bimodal-second-mode-z.tif", 6553.5)
    sep = read(dump, "bimodal-separation.tif", 256.0)
    g = read(dump, "guide-winner.tif", 64.0)

    # A silhouette is a real depth step in the guide, sized against the
    # bracket's own scale rather than a constant that would not transfer.
    span = np.percentile(g, 97.5) - np.percentile(g, 2.5)
    tau = span / 8.0
    step = grey_dilation(g, size=(5, 5)) - grey_erosion(g, size=(5, 5))
    sil = step > step_mult * tau
    if sil.sum() < 1000:
        return None
    dist = distance_transform_edt(~sil)
    # Background side only: the halo is background rendered from the
    # foreground's frame, so foreground interior is not the population.
    bg = ~(g < np.median(g) - tau)

    rows = []
    for lo, hi in BANDS:
        m = (dist >= lo) & (dist < hi) & bg
        if m.sum() < 500:
            continue
        s = sep[m][sep[m] > 0]
        rows.append((lo, hi, int(m.sum()), z1[m].mean(), z2[m].mean(),
                     s.mean() if s.size else 0.0))
    return tau, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dumps", nargs="+", required=True)
    args = ap.parse_args()
    for dump in args.dumps:
        name = os.path.basename(dump.rstrip("\\/"))
        out = profile(dump)
        if out is None:
            print(f"\n{name}: no silhouettes found, skipped")
            continue
        tau, rows = out
        print(f"\n{name}   (tau = {tau:.1f} frames)")
        print("   dist(px)     n      z1(first)  z2(second)   z2/z1   sep(frames)")
        for lo, hi, n, a, b, s in rows:
            print(f"   {lo:3d}-{hi:3d}  {n:9d}     {a:6.2f}     {b:6.2f}    {b / a:6.3f}   {s:7.1f}")
        near, far = rows[0], rows[-1]
        print(f"   RIM vs FAR:  z1 {near[3]:.2f} -> {far[3]:.2f} (RISES with distance, "
              f"so this is not just 'more contrast at edges')")
        print(f"                z2 {near[4]:.2f} -> {far[4]:.2f}   "
              f"ratio {near[4] / near[3]:.3f} -> {far[4] / far[3]:.3f} "
              f"({(near[4] / near[3]) / (far[4] / far[3]):.1f}x swing)")


if __name__ == "__main__":
    main()
