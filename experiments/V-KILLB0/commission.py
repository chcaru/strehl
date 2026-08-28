"""Commission bandprobe.py before trusting it.  v2.

An instrument that reads "no change" is indistinguishable from a dead one, so
each control plants a defect whose sign AND magnitude are known in closed form,
and the script fails loudly if the instrument does not report it.

  C0 NULL   same file against itself -> every ratio exactly 1.000000000.
  C1 BLUR   B = gaussian(A, sigma).  Amplitude transfer is exp(-2 pi^2 s^2 f^2)
            in closed form.  Checked bin by bin, but ONLY where the prediction
            is above 1e-3: below that the measurement is the instrument's own
            leakage floor rather than the signal, and asserting on it would be
            asserting on the noise of the assertion.
  C2 NOISE  B = A + N(0,s).  White noise adds a FLAT power spectrum, so the
            predicted amplitude is sqrt(A_bin^2 + Nz_bin^2) with Nz_bin
            measured by running the same estimator on a pure noise field.  This
            is a magnitude test, not a sign test.
  C3 LEVEL  B = A * 1.02 -> every bin reads 1.02.  Documents that this
            instrument does NOT divide out a level change, which is the thing
            contrast_ms.py's median normalisation does do.
  C4 DISCRIMINATION -- THE LOAD-BEARING ONE.  "Grain reduction and blur are not
            distinguishable by a variance metric alone."  So: build two arms
            that a flat-region variance metric CANNOT tell apart, and require
            this instrument to tell them apart at EDGE sites.
              arm DENOISE : default = A + N(0,s), arm = A         (grain only)
              arm BLUR    : default = A,          arm = blur(A)   (real softening)
            Both must read < 1 at FLAT.  Only BLUR may read << 1 at EDGE.
            If this control fails, no verdict below it means anything.
"""
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

import bandprobe as bp

FAIL = []


def check(name, cond, msg):
    if not cond:
        FAIL.append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}: {msg}")


def bands_of(img, idx, nx):
    acc = np.zeros(len(bp.BINS))
    for f in idx:
        ty, tx = divmod(int(f), nx)
        y, x = ty * bp.TILE, tx * bp.TILE
        acc += bp.tile_bands(img[y:y + bp.TILE, x:x + bp.TILE])
    return acc / len(idx)


def main(path):
    a = bp.load(path)
    lum = bp.channels(a)["L"]
    h, w = lum.shape
    y0, x0 = h // 2 - 1024, w // 2 - 1024
    sub = lum[y0:y0 + 2048, x0:x0 + 2048].copy()
    ny, nx = bp.grid(sub.shape)
    idx = np.arange(ny * nx)
    print(f"commissioning on {path}  region 2048x2048 at ({y0},{x0})  "
          f"{ny}x{nx} tiles  mean={sub.mean():.0f}")
    base = bands_of(sub, idx, nx)

    r0 = bands_of(sub.copy(), idx, nx) / base
    check("C0-null", np.all(r0 == 1.0), f"max |ratio-1| = {np.abs(r0-1).max():.3e}")

    for sigma in (0.5, 0.8, 1.5):
        rb = bands_of(gaussian_filter(sub, sigma), idx, nx) / base
        print(f"\nC1 BLUR sigma={sigma}")
        okall, tested = True, 0
        for i, (lo, hi) in enumerate(bp.BINS):
            fc = 0.5 * (lo + hi)
            pred = np.exp(-2.0 * np.pi ** 2 * sigma ** 2 * fc ** 2)
            rel = rb[i] / pred
            live = pred > 1e-3
            ok = (0.6 < rel < 1.7) if live else True
            okall &= ok
            tested += int(live)
            print(f"      {lo:.2f}-{hi:.2f}  measured {rb[i]:.5f}  predicted {pred:.5f}"
                  f"  meas/pred {rel:6.3f}  {'' if live else '(below floor, not asserted)'}"
                  f"{'' if ok else '  <-- OFF'}")
        check(f"C1-blur-s{sigma}", okall and np.all(np.diff(rb) > 0) and tested >= 4,
              f"{tested} bins above floor, all within 0.6-1.7x of closed form, monotone")

    rng = np.random.default_rng(7)
    for s in (100.0, 400.0):
        nz = rng.normal(0, s, sub.shape)
        nz_bands = bands_of(nz, idx, nx)
        rn = bands_of(sub + nz, idx, nx) / base
        pred = np.sqrt(base ** 2 + nz_bands ** 2) / base
        print(f"\nC2 NOISE sigma={s} DN")
        okall = True
        for i, (lo, hi) in enumerate(bp.BINS):
            rel = rn[i] / pred[i]
            ok = 0.995 < rel < 1.005
            okall &= ok
            print(f"      {lo:.2f}-{hi:.2f}  measured {rn[i]:.5f}  predicted {pred[i]:.5f}"
                  f"  meas/pred {rel:6.4f}{'' if ok else '  <-- OFF'}")
        check(f"C2-noise-s{s}", okall and np.all(rn >= 1.0),
              "measured equals sqrt(signal^2 + noise^2) in every bin to 0.5%")

    rl = bands_of(sub * 1.02, idx, nx) / base
    check("C3-level", np.all(np.abs(rl - 1.02) < 1e-9),
          f"every bin reads the planted 1.02 gain, max err {np.abs(rl-1.02).max():.2e}")

    # ---- C4 DISCRIMINATION
    print("\nC4 DISCRIMINATION  (can this instrument tell denoise from blur?)")
    from scipy.ndimage import gaussian_filter as gf
    g = np.hypot(*np.gradient(gf(sub, 2.0)))
    tg = bp.tile_means(g, ny, nx).ravel()
    order = np.argsort(tg)
    flat, edge = order[:8], order[-8:]
    s = 300.0
    noisy = sub + rng.normal(0, s, sub.shape)
    blurred = gf(sub, 0.55)
    rows = []
    for nm, (dflt, arm) in (("DENOISE", (noisy, sub)), ("BLUR", (sub, blurred))):
        rf = bands_of(arm, flat, nx) / bands_of(dflt, flat, nx)
        re = bands_of(arm, edge, nx) / bands_of(dflt, edge, nx)
        rows.append((nm, rf, re))
        print(f"   {nm:8s}  " + "  ".join(
            f"{lo:.2f}-{hi:.2f} F{rf[i]:.3f}/E{re[i]:.3f}"
            for i, (lo, hi) in enumerate(bp.BINS[:4])))
    (_, dnF, dnE), (_, blF, blE) = rows
    check("C4-flat-confound", dnF[0] < 0.95 and blF[0] < 0.95,
          f"both arms drop at FLAT band 0.40-0.50 (denoise {dnF[0]:.3f}, blur {blF[0]:.3f}) "
          "-- a flat-variance metric alone CANNOT separate them")
    check("C4-edge-separates", dnE[0] > 0.97 and blE[0] < 0.90,
          f"at EDGE 0.40-0.50 denoise reads {dnE[0]:.3f} (~1, harmless) while blur "
          f"reads {blE[0]:.3f} (<<1, real softening) -- SEPARATED")
    check("C4-edge-b1-blind", True,
          f"NOTE: in the 0.20-0.25 bin contrast_ms.py uses as its acuity "
          f"criterion, the SAME blur reads {blE[3]:.3f} at EDGE -- much closer to 1 "
          f"than the {blE[0]:.3f} it reads at 0.40-0.50")

    print("\n" + ("ALL CONTROLS PASSED" if not FAIL else f"FAILED: {FAIL}"))
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
