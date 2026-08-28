"""carefit.py -- re-fit native lateral CA from the DELIVERED (CA-on) masters.

METHOD, AND WHY IT NEEDS NO NEW RENDERS
--------------------------------------
Every delivered master already carries a known, exactly-applied dose: the
shipping correction itself, +704.5 ppm outward on red and -174.4 ppm on blue.
So the native coefficient is recoverable from the residual alone:

    native = measured_residual - applied_push

This is BUILD-CHROMA's dose-ladder logic with the dose delivered by the pipeline
instead of by a resampler, which matters: a synthetic plant made by resampling an
already-demosaiced plane adds a second interpolation that the real correction
explicitly does not have ("the correction rides the gather's existing
interpolation and adds no second resampling pass", optics.rs). That extra blur
attenuates a GRADIENT-REGRESSION estimator. Measured here: a synthetic +704.5 ppm
plant reads back at 0.775-0.794 of nominal, while the SAME estimator reads the
code's own +704.5 ppm at 0.996 on a controlled single-frame pair.

The fit is magnification AND uniform translation jointly. Fitting a radial slope
through the origin -- as chromashift.py does -- conflates the two and inflates the
magnification whenever the tile distribution is asymmetric. BUILD-CHROMA S14.1
records the mirror-image trap.

GATE: report r2 and n and refuse to score a subject that fails the gate, rather
than reporting a number the data does not support.

Usage: python carefit.py <master.tiff> [<master.tiff> ...] [--tile 512]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import tifffile

from caorigin import fit_mag_and_offset
from chromashift import field

APPLIED_R = +704.5   # ppm of outward push the shipped profile applies to red
APPLIED_B = -174.4   # ppm applied to blue (eps_b = +174.4e-6 -> inward)
R2_MIN = 0.30

# BUILD-CHROMA S14, raw and de-attenuated, for comparison.
BC = {
    "tweezers-cpl":     (-650.8, -661.8),
    "bee-3-cpl":        (-519.9, -593.8),
    "coffee-bean":      (-653.2, -655.6),
    "lavendar-cpl":     (-552.0, -600.6),
    "couch-fibers-cpl": (-654.5, -700.7),
    "bee-2-cpl":        (-548.4, -676.1),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--tile", type=int, default=512)
    ap.add_argument("--gradpct", type=float, default=97.0)
    args = ap.parse_args()

    print(f"applied push: R {APPLIED_R:+.1f} ppm   B {APPLIED_B:+.1f} ppm")
    print(f"gate: r2 >= {R2_MIN}\n")
    hdr = (f"{'subject':>20} {'n':>4} {'R resid':>9} {'R r2':>6} "
           f"{'R native':>9} | {'BC raw':>8} {'BC deatt':>9} | "
           f"{'B resid':>9} {'B native':>9}")
    print(hdr)
    print("-" * len(hdr))

    natives = {}
    for path in args.images:
        name = os.path.splitext(os.path.basename(path))[0]
        img = tifffile.imread(path).astype(np.float32)
        rows = field(img, args.tile, args.gradpct)
        fr = fit_mag_and_offset(rows, "R")
        fb = fit_mag_and_offset(rows, "B")
        if fr is None:
            print(f"{name:>20}  UNSCORED (too few tiles)")
            continue
        mr, _, _, r2r, n = fr
        nat_r = mr - APPLIED_R
        bcr, bcd = BC.get(name, (float("nan"), float("nan")))
        if fb is not None:
            mb, _, _, r2b, _ = fb
            nat_b = mb - APPLIED_B
        else:
            mb = nat_b = float("nan")
        flag = "" if r2r >= R2_MIN else "  <- FAILS GATE, UNSCORED"
        print(f"{name:>20} {n:4d} {mr:+9.1f} {r2r:+6.3f} {nat_r:+9.1f} | "
              f"{bcr:+8.1f} {bcd:+9.1f} | {mb:+9.1f} {nat_b:+9.1f}{flag}")
        if r2r >= R2_MIN:
            natives[name] = nat_r

    if len(natives) >= 2:
        vals = np.array(list(natives.values()))
        print(f"\nscored {len(natives)} subject(s)")
        print(f"  mean   {vals.mean():+.1f} ppm")
        print(f"  median {np.median(vals):+.1f} ppm")
        print(f"  range  {vals.min():+.1f} .. {vals.max():+.1f} ppm")
        print("\nleave-one-out median (each subject predicted by the OTHER five):")
        loo = []
        for k in natives:
            others = [v for kk, v in natives.items() if kk != k]
            m = float(np.median(others))
            err = natives[k] - m
            loo.append(abs(err))
            print(f"  {k:>20}  LOO median {m:+8.1f}  own {natives[k]:+8.1f}"
                  f"  err {err:+7.1f} ppm")
        print(f"  mean |LOO error| = {np.mean(loo):.1f} ppm")
        print(f"\nshipped is {APPLIED_R:+.1f}; "
              f"scored median says {np.median(vals):+.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
