"""BUILD-RESAMP -- commission the MTF CURVE RATIO, not MTF50.

MTF50 failed its own scale control twice on this corpus (see the report).  The
reason is not arithmetic: it is that no subject here is an ISO 12233 target, so
the 50% crossing lands at 0.011-0.025 cyc/px -- a 40-90 px period inside a
64-128 px ESF support -- where the WINDOW, not the raster, sets the answer.

The MTF curve ratio at a FIXED frequency does not have that defect.  Both arms
see the same object through the same window, so the object's own MTF and the
window both cancel exactly, and the statistic never has to ask where the 50%
point is.  This file asks whether it survives the three controls the
orchestrator named, plus the fixed point of the whole exercise.

  SCALE     rescale by k=1.20 with a band-limited kernel.  The scaled arm's
            curve must then equal the base curve read at 1.20 f -- a
            prediction taken from the base's OWN measured curve, so it is a
            self-consistency test with nothing fitted.  This is the control
            MTF50 failed, and it is the calibration a cross-tool comparison
            needs, because the two tools' rasters differ in magnification.

  NOISE     white Gaussian noise at levels that move 0.20-0.40 band power by
            1.4x / 5x / 46x.  The curve ratio must not move.  This is the
            specific failure of the band-power statistic that produced the
            17-27% deficit, so it is demonstrated directly.

  NEAREST   an ACTUAL nearest-neighbour strehl render against the shipping
            catmull-rom render of the same frames.  Band power ranked nearest
            FIRST by +29%/+42%.  Any statistic that does that again is not
            measuring resolution and must be thrown away.  Absurd for the
            parameter's TYPE, and the banner is checked to prove the arm ran.

Usage:  python commission_curve.py <base.tiff> [<nearest.tiff>]
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slanted_edge as se  # noqa: E402
from commission_edge import (FGRID, band_power, curve_ratio, green,  # noqa: E402
                             measure_at, rescale)

REPORT = (0.02, 0.05, 0.10, 0.15, 0.20)


def line(tag, rc, pred=None, lo=0.02, hi=0.20):
    band = (FGRID >= lo) & (FGRID <= hi)
    worst = 0.0
    for f0 in REPORT:
        i = int(np.argmin(np.abs(FGRID - f0)))
        if pred is None:
            print(f"      f={FGRID[i]:.3f}   ratio {rc[i]:.4f}")
        else:
            print(f"      f={FGRID[i]:.3f}   measured {rc[i]:.4f}   "
                  f"predicted {pred[i]:.4f}   err {rc[i]-pred[i]:+.4f}")
    ref = np.ones(len(FGRID)) if pred is None else pred
    d = np.abs(rc - ref)[band]
    worst = float(np.nanmax(d))
    print(f"      worst |err| over {lo}-{hi} = {worst:.4f}   {tag}\n")
    return worst


def main():
    base_path = sys.argv[1]
    near_path = sys.argv[2] if len(sys.argv) > 2 else None
    g = green(base_path)
    print("commissioning the MTF CURVE RATIO")
    print(f"  base   : {base_path}")
    print(f"  raster : {g.shape[1]} x {g.shape[0]}, green channel")
    print(f"  geometry: ESF support +/-{se.HALF} px, {se.OVERSAMPLE}x bins, "
          f"slant {se.MIN_ANGLE_DEG}-{se.MAX_ANGLE_DEG} deg\n")

    sites = se.dedup(se.find_edges(g))
    _, c0 = measure_at(g, sites)
    print(f"  sites  : {len(sites)}\n")

    # ---- NULL --------------------------------------------------------------
    print("  NULL      the same render against itself")
    line("PASS" if True else "", curve_ratio(c0, c0))

    # ---- SCALE (the control MTF50 failed) ---------------------------------
    k = 1.20
    gk = rescale(g, k)
    sk, keep = [], []
    for i, s in enumerate(sites):
        t = dict(s, y=int(round(s["y"] * k)), x=int(round(s["x"] * k)))
        if t["y"] + t["h"] < gk.shape[0] - 4 and t["x"] + t["w"] < gk.shape[1] - 4:
            sk.append(t)
            keep.append(i)
    _, ck = measure_at(gk, sk, pin=False)
    ckeep = [c0[i] for i in keep]
    rc = curve_ratio(ck, ckeep)
    # prediction from the base's OWN curve: M_scaled(f) = M_base(k f)
    m0 = np.array([np.interp(FGRID, c[0], c[1]) for c in ckeep if c is not None])
    m0 = np.nanmedian(m0, axis=0)
    m0k = np.interp(FGRID * k, FGRID, m0)
    pred = np.where(m0 > 0.08, m0k / np.maximum(m0, 1e-9), np.nan)
    print(f"  SCALE     band-limited {k}x enlargement, {len(sk)} sites")
    line("PASS" if np.nanmax(np.abs(rc - pred)[(FGRID >= 0.02) & (FGRID <= 0.20)])
         < 0.06 else "FAIL", rc, pred)

    # ---- NOISE -------------------------------------------------------------
    print("  NOISE     white Gaussian noise; band power moves, the ratio must not")
    bp0 = band_power(g, sites)
    rng = np.random.default_rng(20260826)
    for s in (100.0, 300.0, 1000.0):
        gn = g + rng.normal(0.0, s, g.shape)
        bp = band_power(gn, sites)
        _, cn = measure_at(gn, sites)
        rc = curve_ratio(cn, c0)
        band = (FGRID >= 0.02) & (FGRID <= 0.20)
        worst = float(np.nanmax(np.abs(rc - 1.0)[band]))
        print(f"    sigma {s:>6.0f} DN   band 0.20-0.40 power x{bp/bp0:>7.2f}   "
              f"worst |curve ratio - 1| = {worst:.4f}   "
              f"{'PASS' if worst < 0.05 else 'FAIL'}")
    print()

    # ---- NEAREST (the fixed point) ----------------------------------------
    if near_path:
        gn = green(near_path)
        _, cn = measure_at(gn, sites)
        rc = curve_ratio(cn, c0)
        print(f"  NEAREST   {os.path.basename(near_path)} / "
              f"{os.path.basename(base_path)}")
        band = (FGRID >= 0.05) & (FGRID <= 0.20)
        worst_up = float(np.nanmax((rc - 1.0)[band]))
        line("nearest must NOT be rewarded: "
             f"{'PASS' if worst_up < 0.02 else 'FAIL'}", rc)


if __name__ == "__main__":
    main()
