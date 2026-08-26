"""Is the C13 blur-ladder inversion a border artifact? Diagnose before fixing.

C13 asserts a known blur reduces HF monotonically.  It failed on two subjects,
BOTH at rungs 2<->3:

    flowers-cpl  0.0607 > 0.0360 > 0.0361 > 0.0169   (2.5e-3 inversion)
    119MSDCF     0.1728 > 0.1460 > 0.1496 > 0.0776   (2.5% inversion)

The first was explained as a plant on bokeh and fixed by richest_window().  The
second has a HIGH-signal window (0.1728), so that explanation does not reach it,
and two subjects failing at the SAME rung points at the ladder, not the subjects.

HYPOTHESIS.  blur() uses np.convolve(..., "same"), which ZERO-PADS.  A window of
real pixel values ~1000 DN padded with 0 has an enormous artificial step at its
border, and that step injects high-frequency energy which GROWS with kernel
radius:  r = int(max(1, round(3*s))) gives r = 2, 3, 6 for s = 0.5, 1.0, 2.0.
So every rung is measured under a DIFFERENT amount of border contamination --
the ladder compares rungs across a transformation that is not held fixed, which
is this project's most expensive recurring error in miniature.

PREDICTION.  Measuring hf_rel on the INTERIOR only, with a margin wider than the
largest kernel radius and IDENTICAL for every rung, should restore monotonicity
without touching the subjects.  If it does not, the hypothesis is wrong and the
inversion is a real property of the content.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sitescan as SS  # noqa: E402
import tri  # noqa: E402


def blur(a, s):
    if s <= 0:
        return a
    r = int(max(1, round(3 * s)))
    x = np.arange(-r, r + 1, dtype=np.float64)
    k = np.exp(-x * x / (2 * s * s))
    k /= k.sum()
    out = np.apply_along_axis(lambda m: np.convolve(m, k, "same"), 0, a)
    return np.apply_along_axis(lambda m: np.convolve(m, k, "same"), 1, out)


def floor_diag(sub: str) -> None:
    """Why did C15 estimate a floor of exactly 0?

    noise_floor() takes the 2nd percentile of noise-subtracted focus scores over
    a 16x16 tiling.  focus_score clamps at 0, so a floor of exactly 0 means >=2%
    of tiles have LESS variance than the noise model predicts for their level.
    The suspect is clipping: a saturated tile's variance is suppressed by the
    sensor's own nonlinearity, so it is not a valid sample of "empty content" --
    it is a sample taken on the far side of a transformation the noise model does
    not know about.  Print the evidence instead of assuming it.
    """
    d = os.path.join(tri.RAW, sub)
    seen: dict[str, str] = {}
    for f in os.listdir(d):
        if f.lower().endswith(".arw"):
            seen.setdefault(os.path.normcase(f), f)
    files = sorted(seen.values())
    g = SS.green_plane(os.path.join(d, files[len(files) // 2]))
    a, b = SS.noise_model(g)
    h, w = g.shape
    th, tw = h // 16, w // 16
    hi = float(np.percentile(g, 99.99))
    rows = []
    for r in range(16):
        for c in range(16):
            t = g[r * th:(r + 1) * th, c * tw:(c + 1) * tw]
            if t.shape[0] > 4 and t.shape[1] > 4:
                rows.append((SS.focus_score(t, a, b), float(t.mean()),
                             float((t >= hi * 0.995).mean())))
    zero = [x for x in rows if x[0] <= 0.0]
    print(f"\n{sub}: floor diagnostic")
    print(f"  tiles={len(rows)}  zero-score tiles={len(zero)} "
          f"({100.0 * len(zero) / len(rows):.1f}%)   "
          f"2nd pct = {np.percentile([x[0] for x in rows], 2):.4f}")
    if zero:
        print(f"  zero-score tiles: mean level {np.mean([x[1] for x in zero]):.0f} DN, "
              f"near-max pixels {100.0 * np.mean([x[2] for x in zero]):.1f}%")
    nz = [x for x in rows if x[0] > 0.0]
    if nz:
        print(f"  scoring tiles:    mean level {np.mean([x[1] for x in nz]):.0f} DN, "
              f"near-max pixels {100.0 * np.mean([x[2] for x in nz]):.1f}%")
        print(f"  2nd pct of NON-zero tiles = "
              f"{np.percentile([x[0] for x in nz], 2):.4f}")


def main():
    if "--floor" in sys.argv:
        for sub in [a for a in sys.argv[1:] if not a.startswith("--")] or ["119MSDCF"]:
            floor_diag(sub)
        return 0
    subs = [a for a in sys.argv[1:] if not a.startswith("--")] or [
        "119MSDCF", "flowers-cpl", "bee-3-cpl"]
    sigmas = (0.0, 0.5, 1.0, 2.0)
    print(f"{'subject':<20} {'margin':>7}  " + "  ".join(f"s={s:<5}" for s in sigmas)
          + "   monotone?")
    print("-" * 78)
    for sub in subs:
        d = os.path.join(tri.RAW, sub)
        seen: dict[str, str] = {}
        for f in os.listdir(d):      # Windows globs are case-insensitive: dedupe
            if f.lower().endswith(".arw"):
                seen.setdefault(os.path.normcase(f), f)
        files = sorted(seen.values())
        g = SS.green_plane(os.path.join(d, files[len(files) // 2]))
        win = SS.richest_window(g, 64)
        for margin in (0, 10):
            vals = []
            for s in sigmas:
                b = blur(win, s)
                if margin:
                    b = b[margin:-margin, margin:-margin]
                vals.append(SS.hf_rel(b))
            mono = all(vals[i] > vals[i + 1] for i in range(len(vals) - 1))
            cells = "  ".join(f"{v:<7.4f}" for v in vals)
            print(f"{sub:<20} {margin:>7}  {cells}   "
                  f"{'YES' if mono else 'NO  <-- inverted'}")
    print("\nIf margin=0 inverts and margin=10 does not, the inversion is the")
    print("zero-padded border, not the content, and C13 must measure the interior.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
