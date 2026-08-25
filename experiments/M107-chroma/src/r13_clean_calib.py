"""R13 -- redo the R11/R12 calibration in the CLEAN measurement space.

R10, R11 and R12 all ran on `--srgb --auto-exposure` renders. The orchestrator
has just established that this space carries two cross-channel operators -- a
non-diagonal colour matrix putting camera green into output red at 27.4% and
camera red into output green at 7.7%, both at ZERO displacement, plus a guided
demosaic whose smoothness assumption a fringe violates. `stack --help` says of
the sRGB render, in the tool's own words: "For looking at, NOT for measuring."
I ignored that warning exactly as the orchestrator did.

This matters for my own conclusions, not just for the shared number. [CORRECTED
2026-08-24, see section 27: the leak percentages above were wrong in the corpus
and are now taken from color.rs; the mechanism stated below is ALSO wrong. The
dominant term is a NEGATIVE coefficient, output red = 1.636 R - 0.449 G, which
SUBTRACTS the reference from the tracked channel and therefore AMPLIFIES the
apparent displacement rather than attenuating it -- R18 E4 measured the
transfer check moving 0.9148 -> 1.4382, away from zero. The original reasoning
is left below because R13's numbers were computed under it.] Matching a
SHIFTED output-red against an output-green that contains an UN-SHIFTED 7.7%
copy of camera red is a reference partially anchored to the thing being tracked.
That biases any displacement estimate toward zero, which is attenuation, and it
would produce a sign-dependent gain -- which is precisely the R11 signature I
attributed to Lucas-Kanade saturation at ~3 px. **That diagnosis may be wrong.**
Iterating against such a reference is also a positive feedback loop, which is a
better candidate for R12's quadratic divergence than the sign error I guessed at.

So: same estimator, same plants, clean space. If it calibrates here, the
instrument was never the problem and section 21's "no calibrated instrument
exists" is too pessimistic and must be narrowed.

## BARS, REGISTERED BEFORE THE RUN

  X1  TRANSFER CHECK (the orchestrator's, adopted). The pipeline applies a
      known compile-time constant, so `applied / eps_r` has a ground truth of
      1.0 and calibrates the whole chain for free. M113 reads 0.9399/0.9813 in
      this space and 1.3073 in sRGB.
        in [0.90, 1.05] -> clean space confirmed on my render too
        ~1.31           -> I am still measuring in a contaminated space

  X2  PLANTED RECOVERY, four points: +/-704.5 and +/-352.2 ppm.
        all four gains in [0.95, 1.05] -> CALIBRATED; R11's failure was the
                                          space, not the estimator
        gains ~0.58/0.30 as in R11      -> the estimator really is the problem
                                          and section 21 stands as written

  X3  TANGENTIAL PLACEBO, matched magnitude, < 10% radial leak.

  X4  Only if X1-X3 pass: report `needed` (the scene's own CA) and the gain
      `needed / 704.5`. M113 reads 529.9 ppm and 1.2496 on this stack. Agreement
      would be independent confirmation from a separately written estimator;
      disagreement is a finding either way. I register 529.9 as the number to
      beat BEFORE running.
"""
import os
import numpy as np
import tifffile
from scipy import ndimage

R13 = r"C:\dev\strehl-out\M107-chroma\r13"
WIN, CORE, STRIDE = 64, 48, 64
SUPPORT_R = 0.788
EPS = -704.5e-6
PAD = (WIN - CORE) // 2
M113_NEEDED_PPM = 529.9


def plant(red, eps, rot=0.0):
    h, w = red.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    s = 1.0 + eps
    ca, sa = np.cos(rot), np.sin(rot)
    sx = s * (ca * dx - sa * dy) + cx
    sy = s * (sa * dx + ca * dy) + cy
    return ndimage.map_coordinates(red, [sy, sx], order=3, mode="nearest").astype(np.float32)


def estimate(r, g):
    h, w = r.shape
    cy, cx = h / 2.0, w / 2.0
    rmax = float(np.hypot(cx, cy))
    acc = {"rad": [0.0, 0.0], "tan": [0.0, 0.0]}
    for y in range(0, h - WIN, STRIDE):
        for x in range(0, w - WIN, STRIDE):
            wy, wx = y + WIN / 2.0 - cy, x + WIN / 2.0 - cx
            n = np.hypot(wx, wy)
            if n / rmax > SUPPORT_R or n < 1.0:
                continue
            Rw, Gw = r[y:y + WIN, x:x + WIN], g[y:y + WIN, x:x + WIN]
            if Rw.std() < 1e-6 or Gw.std() < 1e-6:
                continue
            Rn = (Rw - Rw.mean()) / Rw.std()
            Gn = (Gw - Gw.mean()) / Gw.std()
            Rc = Rn[PAD:PAD + CORE, PAD:PAD + CORE]
            Gc = Gn[PAD:PAD + CORE, PAD:PAD + CORE]
            gy, gx = np.gradient(Gc)
            d = Rc - Gc
            ux, uy = wx / n, wy / n
            for key, (vx, vy) in (("rad", (ux, uy)), ("tan", (-uy, ux))):
                gu = vx * gx + vy * gy
                den = float((gu * gu).sum())
                if den < 1e-3:
                    continue
                sh = float((gu * d).sum()) / den
                acc[key][0] += sh * den * n
                acc[key][1] += den * n * n
    return {k: (v[0] / v[1] if v[1] > 0 else float("nan")) for k, v in acc.items()}


def main():
    print("=" * 70)
    print("R13 -- calibration in the CLEAN binned-linear space")
    print("=" * 70)
    off = tifffile.imread(os.path.join(R13, "off.tif"))
    on = tifffile.imread(os.path.join(R13, "on.tif"))
    ro, go = off[..., 0].astype(np.float32), off[..., 1].astype(np.float32)
    rn, gn = on[..., 0].astype(np.float32), on[..., 1].astype(np.float32)
    print(f"\nimage {ro.shape[1]}x{ro.shape[0]}  (binned: one pixel = one quad)")

    e_off = estimate(ro, go)
    e_on = estimate(rn, gn)
    applied = e_on["rad"] - e_off["rad"]
    tr = applied / EPS
    print("\nX1  TRANSFER CHECK -- applied / eps_r, ground truth 1.0")
    print(f"    off {e_off['rad']*1e6:+9.1f} ppm   on {e_on['rad']*1e6:+9.1f} ppm")
    print(f"    applied {applied*1e6:+9.1f} ppm   eps_r {EPS*1e6:+.1f} ppm")
    print(f"    applied/eps_r = {tr:.4f}   (M113: 0.9399/0.9813 clean, 1.3073 sRGB)")
    x1 = 0.90 <= tr <= 1.05
    print(f"    X1 {'PASS -- clean space confirmed' if x1 else 'FAIL -- still contaminated'}")

    print("\nX2  PLANTED RECOVERY")
    base = estimate(plant(ro, 0.0), go)["rad"]
    gains = []
    for lab, e in (("-704.5", EPS), ("+704.5", -EPS),
                   ("-352.2", EPS / 2), ("+352.2", -EPS / 2)):
        got = estimate(plant(ro, e), go)["rad"] - base
        gains.append(got / e)
        print(f"    plant {lab:>8s} -> recovered {got*1e6:+9.1f} ppm   gain {got/e:.4f}")
    x2 = all(0.95 <= g <= 1.05 for g in gains)
    asym = abs(abs(gains[1]) - abs(gains[0])) / max(abs(gains[0]), 1e-12)
    print(f"    spread {max(gains)-min(gains):.4f}   sign asymmetry {100*asym:.1f}%"
          f"   (R11 in sRGB: 0.584/0.299, 48.9%)")
    print(f"    X2 {'PASS -- CALIBRATED' if x2 else 'FAIL -- estimator is the problem'}")

    rot = abs(EPS)
    got = estimate(plant(ro, 0.0, rot), go)
    leak = abs(got["rad"] - base) / abs(rot)
    x3 = leak < 0.10
    print(f"\nX3  TANGENTIAL PLACEBO -- radial leak {100*leak:.1f}%   "
          f"{'PASS' if x3 else 'FAIL'}")

    print("\n" + "=" * 70)
    if not (x1 and x2 and x3):
        print("GATES FAILED -- no number reported.")
        print("=" * 70)
        return
    needed = -e_off["rad"]
    print("X4  CALIBRATED. The scene's own lateral CA:")
    print(f"    needed  {needed*1e6:9.1f} ppm     (M113 registered: {M113_NEEDED_PPM})")
    print(f"    shipped {abs(EPS)*1e6:9.1f} ppm")
    print(f"    gain needed/shipped = {abs(EPS)/needed if needed else float('nan'):.4f}"
          f"   (M113: 1.2496)")
    print(f"    residual after correction: {e_on['rad']*1e6:+.1f} ppm "
          f"({'SIGN FLIPPED -- over-corrected' if e_on['rad']*e_off['rad'] < 0 else 'same sign'})")
    print(f"    agreement with M113 on `needed`: "
          f"{100*abs(needed*1e6-M113_NEEDED_PPM)/M113_NEEDED_PPM:.1f}% apart")
    print("=" * 70)


if __name__ == "__main__":
    main()
