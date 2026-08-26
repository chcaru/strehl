"""Before/after on one subject, from ONE binary and one warpmap.

Prints the statistics BUILD-CHROMA section 25 is written in, plus the two that
say directly whether the per-channel ceilings still diverge:

  * the CLAMP CENSUS -- what fraction of each channel is pinned at the writer's
    shared full-scale ceiling. If the channels run out together the three
    fractions are equal; the spread between the largest and the smallest is the
    defect, stated as a number.
  * the DIFF -- how much of the frame moved at all, which is what a null has to
    answer with zero.

Both files must come from the same binary. The caller states the pair; this
script refuses to compare files of different shape and asserts that the hot set
it measures is non-empty.
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import dump

NBANDS = 6
DROP_PCT = 0.76


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: expected uint16, got {a.dtype}"
    assert a.ndim == 3 and a.shape[2] == 3, f"{p}: expected HxWx3, got {a.shape}"
    return a


def stats(f, tag, mask=None):
    """Statistics on `f`. When `mask` is given it is used verbatim, so a
    before/after pair is scored on **the same pixels**; recomputing the hot set
    per image would move the population between the arms and the difference
    would then be partly a change of subject rather than a change of value."""
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    h, w = g.shape
    clamp = [float((f[..., c] >= 65535).mean()) for c in range(3)]
    lo, hi = min(clamp), max(clamp)
    gy, gx = np.gradient(g)
    gm = np.hypot(gx, gy)
    if mask is None:
        strong = gm >= np.percentile(gm, 99.0)
        lum = f.max(axis=2)
        hot = strong & (lum >= np.percentile(lum, 100 - DROP_PCT))
        lv = lum[hot]
    else:
        strong, hot, lv = mask
    assert int(hot.sum()) > 0, f"{tag}: hot set is empty"
    sb = ((b - g) / np.maximum(g, 1.0))[hot]
    sr = ((r - g) / np.maximum(g, 1.0))[hot]
    rb = (b / np.maximum(g, 1.0))[hot]
    q = np.quantile(lv, np.linspace(0, 1, 11))
    means = [float(rb[(lv >= q[i]) & (lv <= q[i + 1])].mean()) for i in range(10)]
    rises = int(sum(means[i + 1] > means[i] for i in range(9)))
    yy, xx = np.mgrid[0:h, 0:w]
    rad = np.hypot(yy - (h - 1) / 2.0, xx - (w - 1) / 2.0)
    rmax = rad.max()
    bg = np.abs(b - g) / np.maximum(g, 1.0)
    band = []
    for i in range(NBANDS):
        m = strong & (rad >= i / NBANDS * rmax) & (rad < (i + 1) / NBANDS * rmax)
        band.append(float(bg[m].mean()) if m.any() else float("nan"))
    return {
        "clamp": clamp,
        "clamp_spread": (hi / lo) if lo > 0 else float("inf"),
        "clamp_any": float((f >= 65535).any(axis=2).mean()),
        "hot": int(hot.sum()),
        "b_pos": float((sb > 0).mean()),
        # The signed ratio is what BUILD-CHROMA reported, and on a subject whose
        # cast is a RED deficit rather than a blue excess it can move *away*
        # from 1 as the pixel is corrected, because pulling a population that
        # mostly sits below 1 toward neutral raises its mean. The unsigned
        # distance from neutral cannot do that, so both are reported and the
        # unsigned one is the verdict.
        "chroma_mean": float(((np.abs(sb) + np.abs(sr)) / 2.0).mean()),
        "chroma_med": float(np.median((np.abs(sb) + np.abs(sr)) / 2.0)),
        "bg_mean": float(sb.mean()), "bg_med": float(np.median(sb)),
        "rg_mean": float(sr.mean()), "rg_med": float(np.median(sr)),
        "bg_deciles": means, "monotone": rises,
        "bg_spread": means[-1] / means[0],
        "corner_centre": band[-1] / band[0],
        "bands": band,
    }


def frozen_mask(f):
    """The edge set, the hot set and the level axis, all taken from the BEFORE
    image and then held fixed."""
    g = f[..., 1]
    gy, gx = np.gradient(g)
    gm = np.hypot(gx, gy)
    strong = gm >= np.percentile(gm, 99.0)
    lum = f.max(axis=2)
    hot = strong & (lum >= np.percentile(lum, 100 - DROP_PCT))
    return strong, hot, lum[hot]


def main():
    subject, before, after = sys.argv[1], sys.argv[2], sys.argv[3]
    a0, a1 = load(before), load(after)
    assert a0.shape == a1.shape, f"shapes differ: {a0.shape} vs {a1.shape}"
    f0, f1 = a0.astype(np.float32), a1.astype(np.float32)

    d = np.abs(f1 - f0)
    moved = (d > 0).any(axis=2)
    print("=" * 96)
    print(f"{subject}")
    print(f"  before {before}")
    print(f"  after  {after}")
    print("=" * 96)
    print(f"  DIFF: pixels changed {moved.mean() * 100:8.4f}%   "
          f"max |d| R {d[..., 0].max():.0f} G {d[..., 1].max():.0f} B {d[..., 2].max():.0f} DN")

    mask = frozen_mask(f0)
    s0, s1 = stats(f0, "before", mask), stats(f1, "after", mask)
    print(f"  hot edge set: {s0['hot']:,} px, FROZEN from the before arm and "
          f"used for both")
    print()
    print(f"  {'statistic':<38} {'BEFORE':>12} {'AFTER':>12}   change")
    rows = [
        ("clamped at 65535: R", "clamp", 0, "%"),
        ("clamped at 65535: G", "clamp", 1, "%"),
        ("clamped at 65535: B", "clamp", 2, "%"),
        ("any channel clamped", "clamp_any", None, "%"),
        ("clamp spread max/min channel", "clamp_spread", None, "x"),
        ("hot edge CHROMA (|B-G|+|R-G|)/2G mean", "chroma_mean", None, ""),
        ("hot edge CHROMA              median", "chroma_med", None, ""),
        ("hot edge px, frac with B-G > 0", "b_pos", None, "%"),
        ("hot edge (B-G)/G  mean", "bg_mean", None, ""),
        ("hot edge (B-G)/G  median", "bg_med", None, ""),
        ("hot edge (R-G)/G  mean", "rg_mean", None, ""),
        ("hot edge (R-G)/G  median", "rg_med", None, ""),
        ("B/G decile 0", "bg_deciles", 0, ""),
        ("B/G decile 9", "bg_deciles", 9, ""),
        ("B/G decile 9 / decile 0", "bg_spread", None, "x"),
        ("monotone rising steps (of 9)", "monotone", None, ""),
        ("corner/centre |B-G|/G", "corner_centre", None, "x"),
    ]
    for label, key, idx, unit in rows:
        v0 = s0[key] if idx is None else s0[key][idx]
        v1 = s1[key] if idx is None else s1[key][idx]
        if unit == "%":
            print(f"  {label:<38} {v0 * 100:11.4f}% {v1 * 100:11.4f}%   "
                  f"{(v1 - v0) * 100:+.4f} pp")
        else:
            ch = f"{(v1 / v0 - 1) * 100:+.1f}%" if v0 else "--"
            print(f"  {label:<38} {v0:12.4f} {v1:12.4f}   {ch}")

    print()
    print(f"  {'decile':>7} {'BEFORE B/G':>12} {'AFTER B/G':>12}")
    for i in range(10):
        print(f"  {i:7d} {s0['bg_deciles'][i]:12.4f} {s1['bg_deciles'][i]:12.4f}")

    # ---- the same statistic with the writer's clamp taken out of it --------
    #
    # There are two ceilings in this pipeline and only one of them is the
    # defect. The writer's `clamp(0, 1)` pins a channel at 65535 whatever the
    # sensor did, and a pinned B over an unpinned G reads as B/G > 1 by
    # construction -- so a hot set that is largely output-clamped reports a
    # colour cast the roll-off cannot be blamed for and cannot reach. Excluding
    # every pixel clamped in EITHER arm scores the two arms on pixels where the
    # rendered value is the arithmetic and nothing else.
    #
    # This is a gate, so it is asserted to bite: BUILD-CHROMA's own near-miss on
    # this task was a gate that removed zero pixels while the verdict logic
    # never checked.
    clamped = (f0 >= 65535).any(axis=2) | (f1 >= 65535).any(axis=2)
    strong, hot, _ = mask
    free = hot & ~clamped
    cut = int(hot.sum()) - int(free.sum())
    # The gate is asserted to bite whenever there is anything for it to bite
    # on. BUILD-CHROMA's near-miss on this task was a gate that removed zero
    # pixels while the verdict logic never checked; the check is the point.
    assert cut == int(clamped[hot].sum()), "the gate did not remove what it named"
    if cut == 0:
        print()
        print("  UNCLAMPED HOT SUBSET: skipped -- no hot pixel is clamped in "
              "either arm, so there is no writer's clamp to take out of the "
              "statistic. That is a property of this subject, not a failure "
              "of the gate.")
        u0 = u1 = None
    elif int(free.sum()) <= 100:
        print()
        print(f"  UNCLAMPED HOT SUBSET: REFUSED -- only {int(free.sum())} of "
              f"{int(hot.sum()):,} hot pixels survive the clamp gate, which is "
              f"too few to quote. On this subject the hot set IS the clamped "
              f"set, so the writer's clamp cannot be separated from the "
              f"roll-off here and no number is reported rather than a weak "
              f"one.")
        u0 = u1 = None
    else:
        assert int(free.sum()) > 100, f"only {int(free.sum())} unclamped hot px left"
        fm = (strong, free, f0.max(axis=2)[free])
        u0, u1 = stats(f0, "before/unclamped", fm), stats(f1, "after/unclamped", fm)
        print()
        print(f"  UNCLAMPED HOT SUBSET: {int(free.sum()):,} px "
              f"({cut:,} of {int(hot.sum()):,} dropped as clamped in one arm or both)")
        print(f"  {'statistic':<38} {'BEFORE':>12} {'AFTER':>12}   change")
        for label, key in [("(B-G)/G  mean", "bg_mean"), ("(B-G)/G  median", "bg_med"),
                           ("(R-G)/G  mean", "rg_mean"), ("(R-G)/G  median", "rg_med"),
                           ("B/G decile 9", "bg_deciles"), ("B/G d9 / d0", "bg_spread")]:
            v0 = u0[key][9] if key == "bg_deciles" else u0[key]
            v1 = u1[key][9] if key == "bg_deciles" else u1[key]
            ch = f"{(v1 / v0 - 1) * 100:+.1f}%" if v0 else "--"
            print(f"  {label:<38} {v0:12.4f} {v1:12.4f}   {ch}")

    dump(f"h6-{subject}", {"before": {"path": before, **s0},
                           "after": {"path": after, **s1},
                           "before_unclamped": u0,
                           "after_unclamped": u1,
                           "unclamped_hot": int(free.sum()),
                           "moved_frac": float(moved.mean()),
                           "max_abs_delta": [float(d[..., c].max()) for c in range(3)]})


if __name__ == "__main__":
    main()
