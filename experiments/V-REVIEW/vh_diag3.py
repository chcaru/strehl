"""Two questions the fix design hangs on.

Q1. If REGIME GUARD 2 split the far field at its OWN MEDIAN distance instead of
    a fixed 650 px, it would always apply.  What would it then say?  This
    matters because it may fire on flat-on-ruler-cpl, which ORCH's regression
    gate requires to keep reading HALO -- and whose own docstring calls its
    +4477 illumination falloff.  Measure before touching anything.

Q2. 112/113MSDCF have background but never 400 px from the subject (dmax 167,
    181).  An adaptive far field is the only way to reach them.  How much
    error does a CLOSE far field inject?  Calibrated on subjects where both the
    true (400-900) and a truncated window exist, so the bias is measured, not
    assumed.
"""
import glob, os, sys
import numpy as np
from scipy.ndimage import (binary_closing, binary_opening,
                           distance_transform_edt)

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H
CACHE = r"D:\strehl-out\V-REVIEW\halo\cache"


def prep(f):
    y = np.load(f)[::2, ::2]
    t = H.otsu(y.ravel())
    s = binary_opening(y < t, np.ones((3, 3)))
    s = binary_closing(s, np.ones((5, 5)))
    return y, distance_transform_edt(~s) * 4


def stats(y, d, flo, fhi):
    far = (d >= flo) & (d < fhi)
    if int(far.sum()) < 200:
        return None
    fl = float(np.median(y[far]))
    vals = []
    for lo, hi in H.NEAR:
        if hi > flo:
            break
        m = (d >= lo) & (d < hi)
        if int(m.sum()) > 200:
            vals.append(float(np.median(y[m])) - fl)
    if not vals:
        return None
    bump = max((vals[i] - vals[i + 1] for i in range(len(vals) - 1)), default=0.0)
    return max(vals), max(bump, 0.0), fl


def main():
    files = sorted(glob.glob(os.path.join(CACHE, "*.npy")))
    print("Q1. GUARD 2 with the far field split at its own median distance")
    print("%-38s %9s %9s %9s  %s" % ("subject", "n_far", "spread_med", "old", "would guard2 fire?"))
    print("-" * 100)
    for f in files:
        stem = os.path.basename(f)[:-4].replace(".tiff", "")
        y, d = prep(f)
        far = (d >= H.FAR[0]) & (d < H.FAR[1])
        n = int(far.sum())
        if n < 400:
            print("%-38s %9d %9s %9s  (no far field at all)" % (stem, n, "-", "-")); continue
        dv = d[far]; med = float(np.median(dv))
        A = far & (d < med); B = far & (d >= med)
        sp = abs(float(np.median(y[A])) - float(np.median(y[B])))
        mid = (H.FAR[0] + H.FAR[1]) // 2
        a1 = far & (d < mid); a2 = far & (d >= mid)
        old = (abs(float(np.median(y[a1])) - float(np.median(y[a2])))
               if a1.sum() > 200 and a2.sum() > 200 else None)
        print("%-38s %9d %9.0f %9s  %s"
              % (stem, n, sp, "-" if old is None else "%.0f" % old,
                 "*** FIRES ***" if sp > H.BG_UNIFORM else "no"))

    print("\n\nQ2. Bias injected by a CLOSE far field (calibration)")
    print("true far = 400-900.  Test windows emulate what 112/113MSDCF can reach.")
    print("%-30s %11s %11s %11s %11s" % ("subject", "over@400-900", "over@130-180", "delta", "farlevel d"))
    print("-" * 90)
    for f in files:
        stem = os.path.basename(f)[:-4].replace(".tiff", "")
        y, d = prep(f)
        if d.max() < 900:
            continue
        t = stats(y, d, 400, 900)
        c = stats(y, d, 130, 180)
        if t is None or c is None:
            continue
        print("%-30s %+11.1f %+11.1f %+11.1f %11.0f"
              % (stem, t[0], c[0], c[0] - t[0], c[2] - t[2]))


if __name__ == "__main__":
    main()
