"""Graded commissioning: response curves, not single points.

A single pass/fail arm tells you a verdict is reachable. It does not tell you
the RANGE over which the number means anything, which is exactly what is needed
to decide whether a real subject reading 3.9x is inside or outside the
instrument's commissioned regime.
"""
import sys, numpy as np
from scipy.ndimage import gaussian_filter
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-GATHER")
from sharplib import acutance, orig_detail, P
import sharp_commission as SC

def main():
    lat, frames, kstar = SC.build()
    NP, NF = SC.NP, SC.NF
    sharpest = [frames[p][kstar[p]] for p in range(NP)]
    full = [frames[p] for p in range(NP)]
    base_e = SC.score(sharpest, full, acutance)
    base_o = SC.score(sharpest, full, orig_detail)
    print("baseline (master = per-patch sharpest frame, full reference set)")
    print("   E = %.4f    orig = %.4f\n" % (base_e, base_o))

    print("=== AMPLITUDE: master multiplied by a pure gain (nothing is sharper) ===")
    print("%10s %12s %12s" % ("gain", "E", "orig"))
    for g in (1.0, 1.5, 2.0, 4.0, 8.0):
        m = [g * s for s in sharpest]
        print("%10.2f %12.4f %12.4f" % (g, SC.score(m, full, acutance),
                                        SC.score(m, full, orig_detail)))

    print("\n=== DENOMINATOR SUBSAMPLE: keep every Nth reference frame ===")
    print("the master is UNCHANGED in every row. Any movement is pure denominator error.")
    print("%10s %8s %12s %12s" % ("keep 1 in", "n frames", "E", "orig"))
    for st in (1, 2, 3, 4, 6, 12):
        r = [frames[p][::st] for p in range(NP)]
        print("%10d %8d %12.4f %12.4f" % (st, len(r[0]),
              SC.score(sharpest, r, acutance), SC.score(sharpest, r, orig_detail)))

    print("\n=== GRADED IMPROVEMENT: master = latent blurred by sigma (0 = perfect) ===")
    print("%10s %12s %12s" % ("sigma", "E", "orig"))
    for sg in (0.30, 0.24, 0.18, 0.12, 0.0):
        m = [gaussian_filter(L, sg, mode="reflect") if sg > 0 else L for L in lat]
        print("%10.2f %12.4f %12.4f" % (sg, SC.score(m, full, acutance),
                                        SC.score(m, full, orig_detail)))

    print("\n=== GRADED DEFECT: master = sharpest frame blurred by sigma ===")
    print("%10s %12s %12s" % ("sigma", "E", "orig"))
    for sg in (0.3, 0.6, 1.2, 2.4):
        m = [gaussian_filter(s, sg, mode="reflect") for s in sharpest]
        print("%10.2f %12.4f %12.4f" % (sg, SC.score(m, full, acutance),
                                        SC.score(m, full, orig_detail)))

    print("\n=== NOISE ADDED TO THE MASTER ONLY (nothing is sharper) ===")
    rng = np.random.default_rng(5)
    print("%10s %12s %12s" % ("sigma DN", "E", "orig"))
    for nz in (0.0, 12.0, 30.0, 60.0):
        m = [s + rng.normal(0, nz, s.shape) if nz > 0 else s for s in sharpest]
        print("%10.1f %12.4f %12.4f" % (nz, SC.score(m, full, acutance),
                                        SC.score(m, full, orig_detail)))

if __name__ == "__main__":
    main()
