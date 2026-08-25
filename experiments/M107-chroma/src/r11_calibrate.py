"""R11 -- calibrate the R10 estimator against a PLANTED magnification.

The orchestrator argues the shipped correction over-corrects by 1.444x, and my
R10 independently read k = 1.374. Both are statements produced by displacement
estimators, and NEITHER estimator has been calibrated. A high r^2 cannot detect
a multiplicative bias, because a scaled version of the truth is still perfectly
linear -- so "r^2 = 0.9969" says nothing about whether Instrument A's ppm is the
right size, and my own k inherits exactly the same doubt.

This plants a KNOWN radial magnification on the red channel of a real render and
asks the R10 estimator to recover it. Recovery ratio 1.00 means the estimator is
calibrated and k = 1.374 stands. Recovery ratio ~1.37 would mean there is no
over-correction at all and the whole effect is my instrument.

## BARS, REGISTERED BEFORE THE RUN

  C1  RECOVERY. Plant eps = -704.5 ppm (the shipped magnitude) on red. The
      estimator must recover it.
        ratio in [0.95, 1.05]  -> calibrated; R10's k = 1.374 stands
        ratio ~ 1.37           -> THE OVER-CORRECTION IS MY INSTRUMENT
        ratio < 0.95           -> attenuating; k is biased LOW, true k larger

  C2  SIGN. Plant +704.5 ppm. Recovery must be equal in magnitude and opposite
      in sign. An estimator that reads the same magnitude for both signs is
      measuring something other than direction.

  C3  RESAMPLE-MATCHED NULL. Plant eps = 0 but STILL RESAMPLE red through the
      identical code path. The orchestrator's own warning: a strength-zero arm
      that short-circuits the resampler is not a control. Recovery must be ~0.
      Anything else is the resampler, not the plant.

  C4  TANGENTIAL PLACEBO. Rotate red by an angle giving the SAME peak
      displacement as C1, a direction the physics forbids. The RADIAL estimator
      must read ~0 and the TANGENTIAL estimator must read the planted value.
      This is the placebo the orchestrator specified: same resampler, same
      magnitude, impossible direction.

All planting is done on off1.tif, which carries the real uncorrected
aberration. The plant ADDS to it, so recovery is measured as a DIFFERENCE
against the eps=0 resampled arm -- that way the scene's own CA cancels and only
the planted increment is scored.
"""
import os
import numpy as np
import tifffile
from scipy import ndimage

R7 = r"C:\dev\strehl-out\M107-chroma\r7"
WIN = 64
STRIDE = 128
SUPPORT_R = 0.788
EPS = -704.5e-6


def plant(red, eps, rot=0.0):
    """Resample red under a similarity about the image centre.

    scale = 1 + eps, plus an optional rotation. Always resamples, including at
    eps = 0 and rot = 0, so the resampler is present in every arm (C3).
    """
    h, w = red.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = xx - cx
    dy = yy - cy
    s = 1.0 + eps
    ca, sa = np.cos(rot), np.sin(rot)
    # Pull: sample the source at the transformed coordinate.
    sx = s * (ca * dx - sa * dy) + cx
    sy = s * (sa * dx + ca * dy) + cy
    return ndimage.map_coordinates(red, [sy, sx], order=3, mode="nearest").astype(np.float32)


def estimate(r, g):
    """Window-weighted radial and tangential R-vs-G displacement."""
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
            R = r[y:y + WIN, x:x + WIN]
            G = g[y:y + WIN, x:x + WIN]
            sr, sg = R.std(), G.std()
            if sr < 1e-6 or sg < 1e-6:
                continue
            Rn = (R - R.mean()) / sr
            Gn = (G - G.mean()) / sg
            gy, gx = np.gradient(Gn)
            d = Rn - Gn
            ux, uy = wx / n, wy / n
            for key, (vx, vy) in (("rad", (ux, uy)), ("tan", (-uy, ux))):
                gu = vx * gx + vy * gy
                den = float((gu * gu).sum())
                if den < 1e-3:
                    continue
                # Slope of displacement vs radius, weighted: accumulate
                # shift*weight*n and weight*n^2 so the ratio is px per px.
                sh = float((gu * d).sum()) / den
                acc[key][0] += sh * den * n
                acc[key][1] += den * n * n
    out = {}
    for key, (num, den) in acc.items():
        out[key] = num / den if den > 0 else float("nan")
    return out


def main():
    print("=" * 72)
    print("R11 -- is the R10 estimator calibrated?")
    print(f"      planted eps = {EPS*1e6:+.1f} ppm    window={WIN} stride={STRIDE}")
    print("=" * 72)

    a = tifffile.imread(os.path.join(R7, "off1.tif"))
    red = a[..., 0].astype(np.float32)
    grn = a[..., 1].astype(np.float32)
    h, w = red.shape
    rmax = float(np.hypot(w / 2.0, h / 2.0))
    # Rotation giving the same peak displacement at the support edge as EPS.
    rot = abs(EPS)
    print(f"\nimage {w}x{h}  half-diagonal {rmax:.1f} px")
    print(f"tangential placebo angle {rot*1e6:.1f} urad "
          f"(peak displacement matched to |eps|)")

    arms = {
        "zero  (C3 null)": (0.0, 0.0),
        "minus (C1)": (EPS, 0.0),
        "plus  (C2)": (-EPS, 0.0),
        "rot   (C4)": (0.0, rot),
    }
    res = {}
    for label, (e, rr) in arms.items():
        rp = plant(red, e, rr)
        res[label] = estimate(rp, grn)
        print(f"  {label:16s} radial={res[label]['rad']*1e6:+9.1f} ppm   "
              f"tangential={res[label]['tan']*1e6:+9.1f} ppm")

    base = res["zero  (C3 null)"]
    print("\n" + "-" * 72)
    print("Recovery measured as a DIFFERENCE against the resampled zero arm,")
    print("so the scene's own aberration cancels and only the plant is scored.")
    print("-" * 72)

    def rec(label, key="rad"):
        return res[label][key] - base[key]

    print("\nC1  RECOVERY of a planted -704.5 ppm")
    r1 = rec("minus (C1)")
    ratio = r1 / EPS
    print(f"    recovered {r1*1e6:+.1f} ppm   planted {EPS*1e6:+.1f} ppm"
          f"   ratio {ratio:.4f}")
    if 0.95 <= ratio <= 1.05:
        v = "PASS -- estimator is calibrated; R10's k = 1.374 stands"
    elif ratio > 1.2:
        v = f"FAIL -- estimator INFLATES by {ratio:.3f}x; the over-correction may be the instrument"
    else:
        v = f"ATTENUATING at {ratio:.3f}x -- k is biased LOW, true k is LARGER"
    print(f"    C1 {v}")

    print("\nC2  SIGN symmetry")
    r2 = rec("plus  (C2)")
    print(f"    recovered {r2*1e6:+.1f} ppm   planted {-EPS*1e6:+.1f} ppm"
          f"   ratio {r2/(-EPS):.4f}")
    asym = abs(abs(r2) - abs(r1)) / max(abs(r1), 1e-12)
    print(f"    magnitude asymmetry {100*asym:.1f}%   "
          f"{'PASS' if np.sign(r2) != np.sign(r1) and asym < 0.15 else 'FAIL'}")

    print("\nC3  RESAMPLE-MATCHED NULL (zero arm vs the raw unresampled image)")
    raw = estimate(red, grn)
    print(f"    raw radial      {raw['rad']*1e6:+9.1f} ppm")
    print(f"    resampled zero  {base['rad']*1e6:+9.1f} ppm")
    drift = base["rad"] - raw["rad"]
    print(f"    resampler drift {drift*1e6:+9.1f} ppm  "
          f"({100*abs(drift/max(abs(EPS),1e-12)):.1f}% of the plant)")
    print(f"    C3 {'PASS -- resampling alone does not manufacture radial displacement' if abs(drift) < 0.15*abs(EPS) else 'FAIL -- the resampler itself moves red radially'}")

    print("\nC4  TANGENTIAL PLACEBO (physics forbids this direction)")
    print(f"    radial read     {rec('rot   (C4)', 'rad')*1e6:+9.1f} ppm  (must be ~0)")
    print(f"    tangential read {rec('rot   (C4)', 'tan')*1e6:+9.1f} ppm  "
          f"(planted {rot*1e6:+.1f})")
    leak = abs(rec("rot   (C4)", "rad")) / abs(rot)
    print(f"    radial leakage {100*leak:.1f}%   "
          f"{'PASS' if leak < 0.25 else 'FAIL -- radial channel is contaminated by tangential motion'}")

    print("\n" + "=" * 72)
    print(f"BOTTOM LINE: estimator gain = {ratio:.4f}")
    print(f"  R10 measured k = 1.374 -> gain-corrected k = {1 + (1.374-1)/ratio:.4f}")
    print("=" * 72)


if __name__ == "__main__":
    main()
