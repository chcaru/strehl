"""DENOMINATOR COMMISSIONING ON REAL DATA.

Three subjects were rendered with COMPLETE frame enumeration -- every source
frame in D:\personal\macro is present as a same-pipeline arm. On those the
denominator is the true per-site best frame, not a subsample of it.

Thinning that complete denominator by a known factor tells us, on real pixels,
how much a subsampled denominator inflates the statistic. That number then
prices the subjects that could only be rendered at 1-in-3 to 1-in-9.

This is the arm orch_sharp1to1 does not have: it perturbs the REFERENCE.
'''"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands as SB
from sharp_F2 import evaluate
COMPLETE = ["coffee-bubbles", "109MSDCF", "119MSDCF"]
print("%-16s %5s %8s %7s %7s %8s" % ("subject", "keep", "frames", "sites", "F med", "inflation"))
for s in COMPLETE:
    z = dict(SB.build(s))
    base = None
    for k in (1, 2, 3, 4, 6):
        r = evaluate(z, refkeep=k)
        f = r["F"][r["ok"]]; f = f[np.isfinite(f)]
        if len(f) < 10:
            print("%-16s %5d %8d %7d %7s %8s" % (s, k, 0, len(f), "-", "refused"))
            continue
        m = float(np.median(f))
        if k == 1: base = m
        print("%-16s %5d %8d %7d %7.4f %8.3fx"
              % (s, k, int(np.ceil(z["A"].shape[0] / k)), len(f), m, m / base))
    print()

