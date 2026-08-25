"""R12 -- an ITERATIVE displacement estimator, calibrated before use.

R11 killed R10's number. The single-step Lucas-Kanade in R10/R11 has a gain of
0.584 for one sign of a planted 704.5 ppm and 0.299 for the other -- an
amplitude-dependent gain, which is what a first-order method does when asked to
measure a ~3 px displacement. Any k derived from it is unreliable, and the bias
INFLATES k, because saturation suppresses the larger (uncorrected) displacement
more than the smaller (corrected) one.

This estimator iterates: shift red by the running estimate and re-solve, so the
residual shift entering the linearisation is driven toward zero, where the
first-order approximation is actually valid.

## BARS, REGISTERED BEFORE THE RUN -- CALIBRATION GATES FIRST

The estimator is not permitted to report a k until it has earned it:

  G1  GAIN. Planted -704.5 ppm must be recovered with ratio in [0.95, 1.05].
  G2  SIGN SYMMETRY. Planted +704.5 ppm must recover with the same magnitude
      to within 10%. R11's single-step estimator failed this at 48.9%.
  G3  LINEARITY. Planted +/-352.25 ppm (half) must ALSO recover at ratio in
      [0.95, 1.05]. Two amplitudes and two signs: four points. A constant gain
      across all four is what "calibrated" means, and is exactly what R11
      lacked.
  G4  TANGENTIAL PLACEBO. A rotation of matched magnitude must leak < 10% into
      the radial channel.

  ONLY IF G1-G4 ALL PASS is the k measurement below meaningful. If they fail,
  the honest output is "no calibrated instrument, no number".

Note on C3 from R11, which was VACUOUS: an identity map_coordinates samples at
the grid knots and returns the input bit-for-bit, so a zero-strength arm does
not exercise the resampler at all -- it read exactly +0.0 ppm drift, which is
the tell. Every arm here is planted through the SAME resampler at a NON-zero
amplitude, and the tangential placebo (G4) is the real resample-matched
control, per the orchestrator's specification.
"""
import os
import numpy as np
import tifffile
from scipy import ndimage

R7 = r"C:\dev\strehl-out\M107-chroma\r7"
WIN = 96          # window fed to the shifter
CORE = 64         # central region actually scored, so shifted edges never count
STRIDE = 128
SUPPORT_R = 0.788
EPS = -704.5e-6
ITERS = 5
PAD = (WIN - CORE) // 2


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
    """Iterative LK. Returns ppm of radial and tangential magnification."""
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
            Rw = r[y:y + WIN, x:x + WIN]
            Gw = g[y:y + WIN, x:x + WIN]
            if Rw.std() < 1e-6 or Gw.std() < 1e-6:
                continue
            Rn = (Rw - Rw.mean()) / Rw.std()
            Gn = (Gw - Gw.mean()) / Gw.std()
            Gc = Gn[PAD:PAD + CORE, PAD:PAD + CORE]
            gy, gx = np.gradient(Gc)
            ux, uy = wx / n, wy / n
            for key, (vx, vy) in (("rad", (ux, uy)), ("tan", (-uy, ux))):
                gu = vx * gx + vy * gy
                den = float((gu * gu).sum())
                if den < 1e-3:
                    continue
                # Iterate: shift red back by the running estimate and re-solve
                # the residual, so the linearisation always sees a small shift.
                total = 0.0
                for _ in range(ITERS):
                    Rs = ndimage.shift(Rn, (-total * vy, -total * vx),
                                       order=3, mode="nearest")
                    Rc = Rs[PAD:PAD + CORE, PAD:PAD + CORE]
                    step = float((gu * (Rc - Gc)).sum()) / den
                    total += step
                    if abs(step) < 1e-4:
                        break
                acc[key][0] += total * den * n
                acc[key][1] += den * n * n
    return {k: (v[0] / v[1] if v[1] > 0 else float("nan")) for k, v in acc.items()}


def main():
    print("=" * 72)
    print(f"R12 -- iterative estimator ({ITERS} iters), calibrated before use")
    print("=" * 72)

    a = tifffile.imread(os.path.join(R7, "off1.tif"))
    red, grn = a[..., 0].astype(np.float32), a[..., 1].astype(np.float32)

    base = estimate(plant(red, 0.0), grn)
    print(f"\nbaseline (scene's own CA): radial {base['rad']*1e6:+.1f} ppm")

    print("\nCALIBRATION GATES")
    gains = []
    for lab, e in (("-704.5", EPS), ("+704.5", -EPS),
                   ("-352.2", EPS / 2), ("+352.2", -EPS / 2)):
        got = estimate(plant(red, e), grn)["rad"] - base["rad"]
        ratio = got / e
        gains.append(ratio)
        print(f"  plant {lab:>8s} ppm -> recovered {got*1e6:+9.1f} ppm   "
              f"gain {ratio:.4f}")

    g1 = 0.95 <= gains[0] <= 1.05
    asym = abs(abs(gains[1]) - abs(gains[0])) / max(abs(gains[0]), 1e-12)
    g2 = asym < 0.10
    g3 = all(0.95 <= g <= 1.05 for g in gains)
    spread = max(gains) - min(gains)
    print(f"\n  G1 gain in [0.95,1.05]        : {'PASS' if g1 else 'FAIL'} ({gains[0]:.4f})")
    print(f"  G2 sign symmetry  < 10%       : {'PASS' if g2 else 'FAIL'} ({100*asym:.1f}%)")
    print(f"  G3 all four amplitudes in band: {'PASS' if g3 else 'FAIL'} "
          f"(spread {spread:.4f})")

    rot = abs(EPS)
    got = estimate(plant(red, 0.0, rot), grn)
    leak = abs(got["rad"] - base["rad"]) / abs(rot)
    g4 = leak < 0.10
    print(f"  G4 tangential leak < 10%      : {'PASS' if g4 else 'FAIL'} "
          f"({100*leak:.1f}%, tangential recovered "
          f"{(got['tan']-base['tan'])*1e6:+.1f} of {rot*1e6:+.1f} ppm)")

    if not (g1 and g2 and g3 and g4):
        print("\n" + "=" * 72)
        print("CALIBRATION FAILED -- no number is reported. The instrument is")
        print("not entitled to an opinion about k.")
        print("=" * 72)
        return

    print("\n" + "-" * 72)
    print("CALIBRATED. Measuring the shipped correction.")
    print("-" * 72)
    b = tifffile.imread(os.path.join(R7, "on.tif"))
    on = estimate(b[..., 0].astype(np.float32), b[..., 1].astype(np.float32))
    off = estimate(red, grn)
    ratio = on["rad"] / off["rad"]
    print(f"  off radial {off['rad']*1e6:+9.1f} ppm")
    print(f"  on  radial {on['rad']*1e6:+9.1f} ppm")
    print(f"  applied    {(on['rad']-off['rad'])*1e6:+9.1f} ppm "
          f"(declared eps_r = {EPS*1e6:+.1f})")
    print(f"  ratio on/off = {ratio:+.4f}   ->  k = {1-ratio:.4f}")
    print(f"  suggested scalar 1/k = {1/(1-ratio):.4f}")
    print("=" * 72)


if __name__ == "__main__":
    main()
