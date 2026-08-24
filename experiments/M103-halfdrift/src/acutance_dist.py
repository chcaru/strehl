"""M103: which tiles produce photo.py's +37%?

photo.py reports, per radius bin,   mean_i(G_i / m_i^2)  for each arm, then the
ratio of those two means. Reproducing it exactly gives 1.3697 in the outer bin,
but the same comparison built from bin MEANS -- mean(G)/mean(m)^2 -- gives
1.1015, and raw gradient energy alone gives 1.0610. Those cannot all describe
the same thing.

The suspect is the 1/m^2 weight. A tile's contribution to mean_i(G_i/m_i^2)
grows without bound as that tile gets darker, so in a bin containing a few very
dark tiles the bin mean is not a property of the bin, it is a property of those
few tiles. Outer tiles on this subject are dark: section 9's own table shows
outer acutance an order of magnitude below the centre.

This script does not argue that. It reports, per bin:

  mean_ratio    photo.py's published statistic
  median_ratio  the same per-tile quantity, robust to a heavy tail
  trimmed       mean of the middle 80% of tiles
  top1_share    fraction of the arm's SUM contributed by its single largest tile
  top5_share    same for the largest five

If the published mean is a tail artifact, median and trimmed will sit near
G_ratio (~1.06) and top1_share will be large. If the effect is broad, the median
will agree with the mean and the +37% survives.

CONTROLS
  PLACEBO   before vs before -- every ratio exactly 1.0.
  POSITIVE  before vs a copy sharpened by a known small amount at ALL radii
            (unsharp mask, 3% amplitude): a genuinely broad change must move the
            median as much as the mean. This proves the median CAN move, so a
            median that fails to move on the real pair is evidence and not just
            an insensitive statistic.

USAGE
  python acutance_dist.py <before.tiff> <after.tiff> <out.json>
"""

import json
import os
import sys

import numpy as np
import tifffile

T = 256
BINS = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]


def acut(g):
    gy, gx = np.gradient(g)
    m = g.mean()
    if m <= 0:
        return np.nan
    return float((gx * gx + gy * gy).mean() / (m * m))


def collect(ga, gb, h, w):
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    rmax = float(np.hypot(cx, cy))
    recs = []
    for y in range(0, h - T + 1, T):
        for x in range(0, w - T + 1, T):
            ta = ga[y:y + T, x:x + T]
            if ta.std() < 1.0:
                continue
            tb = gb[y:y + T, x:x + T]
            r = float(np.hypot(x + T / 2 - cx, y + T / 2 - cy)) / rmax
            recs.append((r, acut(ta), acut(tb), float(ta.mean())))
    return recs


def report(recs, title):
    print(f"\n{title}")
    print(f"  {'r/rmax':>10} {'n':>5} {'mean_ratio':>11} {'median':>9} "
          f"{'trim80':>9} {'top1%':>7} {'top5%':>7}")
    rows = []
    for lo, hi in BINS:
        sel = [t for t in recs if lo <= t[0] < hi]
        if not sel:
            continue
        a = np.array([t[1] for t in sel])
        b = np.array([t[2] for t in sel])
        ok = np.isfinite(a) & np.isfinite(b) & (a > 0)
        a, b = a[ok], b[ok]
        mean_ratio = float(b.mean() / a.mean())
        per = b / a
        median = float(np.median(per))
        k = max(1, int(round(0.1 * len(per))))
        trim = float(np.sort(per)[k:len(per) - k].mean()) if len(per) > 2 * k \
            else float(per.mean())
        srt = np.sort(a)[::-1]
        top1 = float(srt[0] / a.sum())
        top5 = float(srt[:5].sum() / a.sum())
        rows.append({"lo": lo, "hi": hi, "n": int(len(a)),
                     "mean_ratio": mean_ratio, "median_ratio": median,
                     "trimmed80": trim, "top1_share": top1,
                     "top5_share": top5})
        print(f"  {lo:.1f}-{hi:.1f}".ljust(12)
              + f"{len(a):>5} {mean_ratio:>11.4f} {median:>9.4f} "
                f"{trim:>9.4f} {top1 * 100:>6.1f}% {top5 * 100:>6.1f}%")
    return rows


def unsharp(g, amt=0.03):
    from scipy.ndimage import gaussian_filter
    return g + amt * (g - gaussian_filter(g, 1.5))


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    before_p, after_p, out_p = sys.argv[1:4]
    A = tifffile.imread(before_p)
    B = tifffile.imread(after_p)
    h, w = A.shape[:2]
    ga = A[..., 1].astype(np.float64)
    gb = B[..., 1].astype(np.float64)
    print(f"{w}x{h}  before={os.path.basename(before_p)}  "
          f"after={os.path.basename(after_p)}")

    rows_real = report(collect(ga, gb, h, w), "REAL PAIR (shipped -> M103)")
    rows_pl = report(collect(ga, ga, h, w),
                     "PLACEBO (before vs before) -- must be all 1.0000")
    rows_pos = report(collect(ga, unsharp(ga), h, w),
                      "POSITIVE CONTROL (before vs before sharpened 3% at ALL "
                      "radii)")
    print("  ^ a broad, genuine sharpening must move the MEDIAN, not just the "
          "mean.")

    pl_bad = max(abs(r["mean_ratio"] - 1.0) for r in rows_pl)
    print(f"\nPLACEBO max |mean_ratio - 1| = {pl_bad:.2e} "
          f"-- {'PASS' if pl_bad < 1e-9 else 'FAIL'}")

    json.dump({"before": before_p, "after": after_p, "real": rows_real,
               "placebo": rows_pl, "positive_unsharp3pct": rows_pos},
              open(out_p, "w"), indent=1)
    print(f"wrote {out_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
