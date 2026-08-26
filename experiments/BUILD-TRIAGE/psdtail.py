"""Empirical look at the radial PSD tail: is the excess in the source arm
noise (flat to Nyquist) or detail (rolling off)?"""
import numpy as np, tri, os, sys

for lab in ("DETAIL", "SOURCE-BEST"):
    f = os.path.join(tri.OUT, "tiles", f"119MSDCF.{lab}.npz")
    if not os.path.exists(f): continue
    z = np.load(f)
    A, B, ka = z["merge"], z["frame"], float(z["ka"])
    rA, pA = tri.spectrum(A); rB, pB = tri.spectrum(B)
    print(f"\n=== 119MSDCF {lab}   ka={ka:.4f}  (radii in c/OUTPUT-sample) ===")
    print(f"{'f_out':>7} {'f_sensor':>9} {'merge DN':>10} {'frame DN':>10} {'m/f':>7}")
    for lo in np.arange(0.10, 0.50, 0.025):
        m = (rA >= lo) & (rA < lo + 0.025)
        if not m.any(): continue
        a = float(np.sqrt(pA[m].mean())); b = float(np.sqrt(pB[m].mean()))
        print(f"{lo+0.0125:7.3f} {(lo+0.0125)/ka:9.3f} {a:10.3f} {b:10.3f} {a/b:7.3f}")
    # noise proxy: power right at Nyquist, where the brief says MTF ~ 0
    for nm, (lo, hi) in (("0.46-0.50", (0.46, 0.50)),):
        m = (rA >= lo) & (rA < hi)
        print(f"  Nyquist band {nm}: merge={np.sqrt(pA[m].mean()):.3f} DN  "
              f"frame={np.sqrt(pB[m].mean()):.3f} DN")
