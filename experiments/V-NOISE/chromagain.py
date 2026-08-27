"""IS THE CHROMAGAIN GUARD ITSELF CIRCULAR?

noisefree.py's CHROMAGAIN arm withdrew this lane's headline: enfuse's 1.74x /
1.77x chroma noise excess is 110% / 69% "explained" by a coarse chroma gain
difference.  Before accepting that, the guard has to survive the obvious
objection to it.

THE OBJECTION.  CHROMAGAIN measures scene chroma as the spread of 4x4-block-
averaged chroma.  Block averaging attenuates noise sigma by 4x, but it does not
remove it, and these FLAT tiles are dark (median luma 0.0146) with chroma sigma
0.062-0.152.  If the residual noise after 4x4 averaging is comparable to the
real scene chroma spread, then a NOISIER arm automatically shows a higher
"gain", the guard is measuring noise a second time, and it has no authority to
withdraw anything.  A guard that fails circularly is worse than no guard.

TWO NON-CIRCULAR ESTIMATORS, both immune to the objection:

  DC     the per-tile MEAN of signed chroma.  Zero-mean noise cancels in the
         mean, so this is scene chroma with no noise contribution to remove.
         It measures a colour/saturation difference directly.

  HALF   scene chroma variance = var(coarse(mean)) - var(coarse(half-diff)),
         using the A/B half-stacks.  The subtracted term is a MEASURED noise
         variance at the same block size, so whatever noise survives 4x4
         averaging is removed rather than assumed negligible.

If both agree with CHROMAGAIN, the withdrawal stands.  If both say the arms
have equal scene chroma, CHROMAGAIN was circular and the withdrawal is void.

INVOCATION (rule 47).  Reads the same arms plus the A/B half-stacks and
census.npz.  Prints only.

    python chromagain.py [nboot=2000]
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from noisefree import (Arm, LIN, CACHE, opponent, boot, coarse4,   # noqa: E402
                       FREE)

OUT = r"C:\dev\strehl-out\V-LINEAR2\out"
HALF = {
    "strehl": (rf"{LIN}\113-A-g1.tiff", rf"{LIN}\113-B-g1.tiff", 1.0, 16),
    "enfuse": (rf"{OUT}\coh-enfuse-A.tif", rf"{OUT}\coh-enfuse-B.tif",
               1.0050, 16),
    "fs15": (rf"{OUT}\coh-fs15-A.tif", rf"{OUT}\coh-fs15-B.tif", 1.0050, 8),
}


def main():
    nboot = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    z = np.load(CACHE)
    cells = [tuple(c) for c in z["cells"][z["flat"]]]
    rng = np.random.default_rng(31)

    arms = {"strehl": Arm(rf"{LIN}\113-full-g1.tiff", 1.0, 16, "strehl")}
    for tag in ("enfuse", "fs15"):
        arms[tag] = Arm(FREE[tag]["path"], FREE[tag]["scale"],
                        FREE[tag]["bits"], FREE[tag]["label"])

    print("=" * 100)
    print("Is the CHROMAGAIN guard circular?  Two noise-immune estimators.")
    print("=" * 100)

    # ---- DC: per-tile mean of signed chroma.  Noise cancels in the mean. ----
    dc = {}
    for k, a in arms.items():
        rows = []
        for (y, x) in cells:
            b = a.rgb(y, x)
            if b is None:
                rows.append([np.nan] * 3)
                continue
            Y, c1, c2 = opponent(b)
            lv = float(Y.mean())
            rows.append([float(c1.mean()) / lv, float(c2.mean()) / lv, lv])
        dc[k] = np.array(rows)
    ok = np.ones(len(cells), bool)
    for k in dc:
        ok &= np.all(np.isfinite(dc[k]), axis=1)

    print(f"\n--- DC chroma, per-tile mean signed chroma / luma (n={int(ok.sum())}) ---")
    print("  noise has zero mean, so nothing needs to be subtracted here")
    print(f"{'arm':10s} {'mean R-Y':>12s} {'mean B-Y':>12s}")
    for k in dc:
        print(f"{k:10s} {np.median(dc[k][ok, 0]):12.5f} "
              f"{np.median(dc[k][ok, 1]):12.5f}")
    print(f"\n{'ratio vs strehl -- |DC| magnitude':50s}")
    for k in dc:
        if k == "strehl":
            continue
        row = f"{k:10s} "
        for i, nm in ((0, "R-Y"), (1, "B-Y")):
            m, lo, hi, _ = boot(np.abs(dc[k][ok, i]),
                                np.abs(dc["strehl"][ok, i]), nboot, rng)
            row += f"  {nm} {m:6.3f} [{lo:6.3f},{hi:6.3f}]"
        print(row)

    # ---- HALF: coarse scene chroma variance with MEASURED noise removed ----
    print("\n--- HALF: coarse chroma variance, measured noise subtracted ---")
    print("  scene_var = var(coarse((A+B)/2)) - var(coarse((A-B)/2))")
    sc = {}
    for k, (pa, pb, s, bits) in HALF.items():
        if not (os.path.exists(pa) and os.path.exists(pb)):
            print(f"  MISSING half-stacks for {k}")
            continue
        A, B = Arm(pa, s, bits, k), Arm(pb, s, bits, k)
        rows = []
        for (y, x) in cells:
            ca, cb = A.rgb(y, x), B.rgb(y, x)
            if ca is None or cb is None or ca.shape != cb.shape:
                rows.append([np.nan] * 2)
                continue
            Ya, a1, a2 = opponent(ca)
            Yb, b1, b2 = opponent(cb)
            lv = float(0.5 * (Ya.mean() + Yb.mean()))
            out = []
            for u, v in ((a1, b1), (a2, b2)):
                tot = float(coarse4(0.5 * (u + v)).var())
                nz = float(coarse4(0.5 * (u - v)).var())
                out.append(max(tot - nz, 0.0) ** 0.5 / lv if lv > 1e-6
                           else np.nan)
            rows.append(out)
        sc[k] = np.array(rows)
    ok2 = np.ones(len(cells), bool)
    for k in sc:
        ok2 &= np.all(np.isfinite(sc[k]), axis=1)
    print(f"{'arm':10s} {'scene R-Y':>12s} {'scene B-Y':>12s}   "
          f"(n={int(ok2.sum())})")
    for k in sc:
        print(f"{k:10s} {np.median(sc[k][ok2, 0]):12.5f} "
              f"{np.median(sc[k][ok2, 1]):12.5f}")
    print(f"\n{'ratio vs strehl -- noise-free scene chroma':50s}")
    for k in sc:
        if k == "strehl":
            continue
        row = f"{k:10s} "
        for i, nm in ((0, "R-Y"), (1, "B-Y")):
            m, lo, hi, _ = boot(sc[k][ok2, i], sc["strehl"][ok2, i],
                                nboot, rng)
            row += f"  {nm} {m:6.3f} [{lo:6.3f},{hi:6.3f}]"
        print(row)

    print("\n" + "=" * 100)
    print("READ THIS AS: if both estimators show the comparators carrying")
    print("MORE scene chroma than strehl, CHROMAGAIN was not circular and the")
    print("withdrawal of the chroma noise headline stands.  If both show the")
    print("arms level on scene chroma, CHROMAGAIN was re-measuring noise and")
    print("the withdrawal is void.")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
