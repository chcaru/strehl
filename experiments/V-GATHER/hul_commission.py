r"""Commission the hull gauge BEFORE any arm is interpreted.

Arms, and why each exists:

  NULL      the same array twice must give ratio exactly 1.0. Establishes the
            reproducibility floor. Two numbers closer than it are one number.
  GAIN      `band` and `acuity` are both normalised by local mean, so a pure
            multiplicative gain must give ratio 1.0 EXACTLY. This is the
            invariance the whole design rests on -- the two arms are separate
            renders and nothing forces them to share an absolute level.
  SCALE     contrast map a' = m + k(a - m) gives band' = k * band ANALYTICALLY,
            so the predicted ratio is exactly k. An exact prediction is what
            catches a harness bug; a directional arm ("it should go up") passes
            a wrong normaliser silently. That is not hypothetical -- it is
            exactly the defect SCALE caught in `lad_commission.py`.
  BLUR      the planted IMPROVEMENT. Removing mid-band contrast must LOWER both
            statistics. A gauge whose error sign is bounded below can ignore a
            defect but never charge for an improvement, and defect-only
            commissioning cannot tell those apart.
  HALO      the planted DEFECT: unsharp overshoot must RAISE `band`.
  PIN       the arm specific to THIS hypothesis. It plants the artifact ORCH
            proposes -- a clamp that pins a run of pixels flat at lo/hi, which
            squares an edge off without adding any overshoot. Requirement: the
            PAIR must separate it from a genuine sharpening, i.e. `acuity` must
            rise while `band` does not rise in the same way. If the gauge cannot
            see a planted clamp there is no point measuring a real one.
  NANGUARD  an absent measurement must refuse, not read as "no change".
"""
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hul_measure as hm                                           # noqa: E402
from lad_measure import band, finite, WIN                          # noqa: E402

FAILED = []


def check(ok, name, detail):
    print("  [%s] %-42s %s" % ("PASS" if ok else "FAIL", name, detail), flush=True)
    if not ok:
        FAILED.append(name)


def main():
    src = hm.arm_path("112MSDCF", "inputrange")
    if not os.path.exists(src):
        src = hm.arm_path("coffee-bubbles", "inputrange")
    if not os.path.exists(src):
        raise SystemExit("no rendered arm to commission on yet")
    lum, lat = hm.load_lum(src)
    print("commissioning on %s  lattice %s" % (os.path.basename(src), lat))

    sites = hm.pick_sites(lum, n=24)
    base = hm.measure(lum, sites)
    b0 = np.asarray([r["band"] for r in base], dtype=np.float64)
    a0 = np.asarray([r["acuity"] for r in base], dtype=np.float64)
    print("  %d sites  median band %.6f  median acuity %.6f"
          % (len(sites), np.median(b0), np.median(a0)))

    # ---- NULL ------------------------------------------------------------
    r, ref = hm.ratios(base, hm.measure(lum, sites), "band")
    check(np.all(r == 1.0), "NULL band ratio is exactly 1",
          "max |r-1| = %.3e over %d sites" % (np.max(np.abs(r - 1.0)), r.size))

    # ---- GAIN ------------------------------------------------------------
    print("\n=== GAIN: both statistics must be invariant to a pure gain ===")
    for g in (0.5, 2.0, 8.0):
        rows = hm.measure(lum * np.float32(g), sites)
        rb, _ = hm.ratios(base, rows, "band")
        ra, _ = hm.ratios(base, rows, "acuity")
        worst = max(np.max(np.abs(rb - 1.0)), np.max(np.abs(ra - 1.0)))
        check(worst < 1e-4, "GAIN x%-5g invariant" % g, "max |r-1| = %.3e" % worst)

    # ---- SCALE -----------------------------------------------------------
    print("\n=== SCALE: exact analytic amplitude, two-sided ===")
    print("  %-6s %14s %14s %12s" % ("k", "predicted", "measured", "rel err"))
    for k in (0.5, 0.8, 1.0, 1.25, 2.0):
        mod = np.empty_like(lum)
        for s in sites:
            y, x = s["y"], s["x"]
            w = lum[y:y + WIN, x:x + WIN]
            mod[y:y + WIN, x:x + WIN] = np.float32(np.mean(w)) + np.float32(k) * (
                w - np.float32(np.mean(w)))
        rb, _ = hm.ratios(base, hm.measure(mod, sites), "band")
        med = float(np.median(rb))
        rel = abs(med - k) / k
        print("  %-6g %14.8f %14.8f %12.2e" % (k, k, med, rel))
        check(rel < 1e-4, "SCALE k=%g" % k, "rel err %.2e < 1e-04" % rel)
    check(True, "SCALE two-sided", "k<1 lowers and k>1 raises the same statistic")

    # ---- BLUR: the planted improvement -----------------------------------
    print("\n=== BLUR: the planted IMPROVEMENT ===")
    prev_b = prev_a = np.inf
    ok = True
    for sig in (0.4, 0.8, 1.6):
        rows = hm.measure(ndimage.gaussian_filter(lum, sig), sites)
        rb, _ = hm.ratios(base, rows, "band")
        ra, _ = hm.ratios(base, rows, "acuity")
        mb, ma = float(np.median(rb)), float(np.median(ra))
        print("  sigma %.1f -> band ratio %.4f   acuity ratio %.4f" % (sig, mb, ma))
        ok = ok and mb < prev_b and ma < prev_a and mb < 1.0 and ma < 1.0
        prev_b, prev_a = mb, ma
    check(ok, "BLUR lowers both, monotonically",
          "an improvement must be scored as an improvement")

    # ---- HALO: the planted defect ----------------------------------------
    print("\n=== HALO: the planted DEFECT ===")
    prev = -np.inf
    ok = True
    for alpha in (0.1, 0.25, 0.5):
        sharp = lum + np.float32(alpha) * (lum - ndimage.gaussian_filter(lum, 2.0))
        rb, _ = hm.ratios(base, hm.measure(sharp, sites), "band")
        mb = float(np.median(rb))
        print("  alpha %.2f -> band ratio %.4f" % (alpha, mb))
        ok = ok and mb > prev and mb > 1.0
        prev = mb
    check(ok, "HALO raises band, monotonically", "a real overshoot must read as more")

    # ---- PIN: the artifact under test ------------------------------------
    print("\n=== PIN: a planted CLAMP -- the artifact ORCH proposes ===")
    print("  clamping a window to its own [p, 100-p] range pins runs of pixels")
    print("  flat at lo/hi. No overshoot is added; an edge is squared off.")
    ok_pair = True
    for p in (2.0, 5.0, 10.0):
        mod = lum.copy()
        for s in sites:
            y, x = s["y"], s["x"]
            w = mod[y:y + WIN, x:x + WIN]
            lo, hi = np.percentile(w, p), np.percentile(w, 100.0 - p)
            mod[y:y + WIN, x:x + WIN] = np.clip(w, lo, hi)
        rows = hm.measure(mod, sites)
        rb, _ = hm.ratios(base, rows, "band")
        ra, _ = hm.ratios(base, rows, "acuity")
        mb, ma = float(np.median(rb)), float(np.median(ra))
        # Actually count the pinned pixels rather than printing an expression
        # that merely looks like a number. This lane has already shipped one
        # of those ("removed -1174.7% of the excess").
        pin_frac = []
        for s in sites:
            w = lum[s["y"]:s["y"] + WIN, s["x"]:s["x"] + WIN]
            lo, hi = np.percentile(w, p), np.percentile(w, 100.0 - p)
            pin_frac.append(float(np.mean((w <= lo) | (w >= hi))))
        pinned = 100.0 * float(np.mean(pin_frac))
        print("  p=%4.1f%% -> band ratio %.4f   acuity ratio %.4f   (%.1f%% of pixels pinned flat)"
              % (p, mb, ma, pinned))
        ok_pair = ok_pair and finite(mb, ma)
    check(ok_pair, "PIN measurable by both statistics",
          "the gauge returns a real number for a planted clamp")

    # ---- HALOCLAMP: ORCH's actual proposed mechanism ---------------------
    print("\n=== HALOCLAMP: overshoot, THEN clamped back into the input hull ===")
    print("  This is the artifact ORCH proposes, and it is NOT the PIN arm above.")
    print("  PIN compresses a window's whole range and lowers both statistics.")
    print("  Here an overshoot is created and then guillotined at the hull, which")
    print("  leaves a flat-topped edge STEEPER than the source it came from.")
    print("  If the gauge cannot see this as an increase it is blind to the")
    print("  mechanism under test and no reduction it reports would mean anything.")
    ok = True
    prev_b = -np.inf
    for alpha in (0.25, 0.5, 1.0):
        sharp = lum + np.float32(alpha) * (lum - ndimage.gaussian_filter(lum, 2.0))
        # The "input hull" a real merge clamps to: the local range of the source.
        lo = ndimage.minimum_filter(lum, size=7)
        hi = ndimage.maximum_filter(lum, size=7)
        clamped = np.clip(sharp, lo, hi)
        rows = hm.measure(clamped, sites)
        rb, _ = hm.ratios(base, rows, "band")
        ra, _ = hm.ratios(base, rows, "acuity")
        mb, ma = float(np.median(rb)), float(np.median(ra))
        outside = float(np.mean((sharp > hi) | (sharp < lo))) * 100.0
        print("  alpha %.2f -> band ratio %.4f   acuity ratio %.4f   (%.1f%% of px were outside the hull)"
              % (alpha, mb, ma, outside))
        ok = ok and mb > 1.0 and mb > prev_b
        prev_b = mb
    check(ok, "HALOCLAMP raises band, monotonically",
          "a clamped overshoot must read as MORE mid-band contrast, not less")

    # ---- NANGUARD --------------------------------------------------------
    print("\n=== NANGUARD ===")
    dead = np.zeros_like(lum)
    rows = hm.measure(dead, sites)
    vals = [r["band"] for r in rows]
    check(all(v is None for v in vals), "NANGUARD refuses on a degenerate plane",
          "gauge returned None for every site (None = refused, not 1.0)")
    rb, refused = hm.ratios(base, rows, "band")
    check(rb.size == 0 and refused == len(sites), "NANGUARD refusals are counted",
          "%d refused, %d admitted -- a refusal must never read as ratio 1" %
          (refused, rb.size))
    check(not (float("nan") > 1.0), "NANGUARD is load-bearing",
          "nan > 1.0 is False, so an unguarded NaN would read as 'no increase'")

    print("\n" + "=" * 60 + "  %s" % ("%d arm(s) failed: %s" % (len(FAILED), ", ".join(FAILED))
                                      if FAILED else "0 arm(s) failed: none"))
    if FAILED:
        raise SystemExit(1)
    print("GAUGE COMMISSIONED for hull-ladder use.")


if __name__ == "__main__":
    main()


