"""
06-reconcile-targets.py -- why gallery.py and color.rs disagree, decomposed.

THE QUESTION (item 5 of the 10:22 stand-down):
    "gallery.py uses 0.92 and color.rs ships 0.90. One of them is wrong or they
     differ for a reason. SS3 swept five targets, so the answer is probably
     already measured -- find it, state it, and if gallery.py is the odd one
     out say so plainly, since its output is what I have been showing the
     owner."

WHAT I FOUND BEFORE MEASURING, at source:

  1. `experiments/M100-exposure/sweep.py:31` is
     `TARGETS = [0.80, 0.85, 0.90, 0.95, 1.00]`.
     **0.92 IS NOT IN THE GRID.** The answer is NOT already measured. The
     premise of item 5 is false, in the same way the brief's was.

  2. The two rules differ on FOUR axes, not one. `gallery.py:113-131`:
        lin   = srgb_to_linear(tif / 65535)          # H x W x 3
        p999  = np.percentile(lin, 99.9)             # <-- NO axis argument
        gain  = min(TARGET / p999, 64.0)             # TARGET = 0.92
        if clip > 0.005: <30-iteration bisection down>
     versus `color.rs`:
        luma  = BT.709 luminance                     # 0.2126/0.7152/0.0722
        p999  = nearest_rank (numpy "inverted_cdf")
        gain  = 0.90 / p999, bounded +/-6 stops, quantised to 1/100 stop
        (no clipping guard at all)
     So they differ in:
        (a) TARGET      0.92 vs 0.90
        (b) STATISTIC   pooled R,G,B samples vs BT.709 luminance.
                        `np.percentile` with no `axis` FLATTENS, so gallery.py
                        takes the percentile over 3x as many samples drawn from
                        all three channels. M100 swept luminance and
                        max-channel. It never swept this one.
        (c) METHOD      numpy default "linear" (interpolated) vs the
                        nearest-rank `inverted_cdf` that color.rs deliberately
                        matches.
        (d) GUARD       a 30-iteration bisection against a 0.5% clip budget,
                        vs no guard and a quantised fixed-target gain.

  Item 5 asks which is "wrong". A four-axis difference cannot be answered by
  comparing two constants, so this script decomposes it one axis at a time.

PRE-REGISTERED BARS, fixed before the first read:

  POSITIVE CONTROL (must pass first, or nothing below is admissible).
      My reimplementation of the SHIPPED rule must reproduce M100 SS3.4's
      published choices on the two stacks the gallery shares with that table:
      `bee-3-cpl` = +1.54 and `coffee-bean` = -0.18. PASS if both match to
      the 1/100-stop quantum. If this fails I have not reimplemented the
      shipped rule and every decomposition below is void.

  PLACEBO / FIXED POINT.
      Applying the shipped rule's own chosen gain and re-running the shipped
      rule on the result must choose ~0.00 stops. PASS if |stops| <= 0.02
      (two quanta) on every stack. A rule that is not its own fixed point is
      not a rule. This has real power to fail: the quantisation and the
      nearest-rank index could both bite.

  DECOMPOSITION.
      Report each axis's contribution in stops, holding the others at the
      shipped setting. DOMINANT AXIS = the one with the largest median
      absolute contribution across the 7 stacks.

  VERDICT ON gallery.py.
      "ODD ONE OUT" if its total divergence from the shipped rule exceeds
      0.10 stops (10 quanta) on a majority of stacks.
      "COSMETIC" if it is under 0.02 stops on a majority.
      Anything between is reported as "MATERIAL BUT SMALL".
      Registered before looking. I do not move these after.

READ-ONLY on the TIFs. Writes one JSON under C:\\dev\\strehl-out\\M105.
"""

import json
import os
import glob

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M105"
GALLERY = r"C:\dev\strehl-out\ORCH-gallery"

# BT.709 luminance coefficients. From the ITU-R recommendation, NOT from
# color.rs (rule 34: a control must not be handed its answer by the code).
BT709 = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

SHIPPED_TARGET = 0.90       # color.rs AUTO_EXPOSURE_TARGET
SHIPPED_PCT = 99.9          # color.rs AUTO_EXPOSURE_PERCENTILE
SHIPPED_MAX_STOPS = 6.0     # color.rs AUTO_EXPOSURE_MAX_STOPS
SHIPPED_QUANTUM = 100.0     # color.rs AUTO_EXPOSURE_STEPS_PER_STOP

GALLERY_TARGET = 0.92       # gallery.py TARGET
GALLERY_CLIP_BUDGET = 0.005  # gallery.py CLIP_BUDGET

# M100 SS3.4's published choices, for the positive control. Read from the
# report, not recomputed here.
M100_PUBLISHED = {"bee-3-cpl": 1.54, "coffee-bean": -0.18}


def srgb_to_linear(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4).astype(np.float32)


def quantise(stops):
    s = float(np.clip(stops, -SHIPPED_MAX_STOPS, SHIPPED_MAX_STOPS))
    return float(np.round(s * SHIPPED_QUANTUM) / SHIPPED_QUANTUM)


def stat(lin, statistic, method):
    """The percentile, under each candidate reading of 'the bright end'."""
    if statistic == "luminance":
        samples = lin @ BT709
    elif statistic == "pooled":
        samples = lin          # np.percentile flattens: gallery.py's behaviour
    elif statistic == "maxch":
        samples = lin.max(axis=2)
    else:
        raise ValueError(statistic)
    return float(np.percentile(samples, SHIPPED_PCT, method=method))


def clip_fraction(mx, gain):
    """Fraction of pixels with any channel over 1.0 after `gain`."""
    return float((mx > (1.0 / gain)).mean())


def bisect_to_budget(mx, gain):
    """gallery.py's guard, reimplemented exactly: 30 halvings toward 1.0."""
    if clip_fraction(mx, gain) <= GALLERY_CLIP_BUDGET:
        return gain
    lo, hi = 1.0, gain
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if clip_fraction(mx, mid) > GALLERY_CLIP_BUDGET:
            hi = mid
        else:
            lo = mid
    return lo


def analyse(path, name):
    a = tifffile.imread(path).astype(np.float32) / 65535.0
    lin = srgb_to_linear(a)
    del a
    mx = lin.max(axis=2)

    # The shipped rule, end to end.
    p_ship = stat(lin, "luminance", "inverted_cdf")
    ship_stops = quantise(np.log2(SHIPPED_TARGET / max(p_ship, 1e-6)))

    # gallery.py, end to end.
    p_gal = stat(lin, "pooled", "linear")
    gal_gain_raw = min(GALLERY_TARGET / max(p_gal, 1e-6), 64.0)
    gal_gain = bisect_to_budget(mx, gal_gain_raw)
    gal_stops = float(np.log2(gal_gain))

    # One axis at a time, everything else at the shipped setting.
    axis_target = quantise(np.log2(GALLERY_TARGET / max(p_ship, 1e-6))) - ship_stops
    axis_stat = quantise(np.log2(SHIPPED_TARGET /
                                 max(stat(lin, "pooled", "inverted_cdf"), 1e-6))) - ship_stops
    axis_method = quantise(np.log2(SHIPPED_TARGET /
                                   max(stat(lin, "luminance", "linear"), 1e-6))) - ship_stops
    guard_gain = bisect_to_budget(mx, float(2.0 ** ship_stops))
    axis_guard = float(np.log2(guard_gain)) - ship_stops

    # Fixed point: apply the shipped gain, re-run the shipped rule.
    re_p = stat(np.clip(lin * (2.0 ** ship_stops), 0.0, 1.0), "luminance", "inverted_cdf")
    fixed_point_stops = quantise(np.log2(SHIPPED_TARGET / max(re_p, 1e-6)))

    out = {
        "stack": name,
        "shipped_p999_luma": round(p_ship, 6),
        "shipped_stops": ship_stops,
        "shipped_clip_pct": round(100.0 * clip_fraction(mx, 2.0 ** ship_stops), 4),
        "gallery_p999_pooled": round(p_gal, 6),
        "gallery_stops": round(gal_stops, 4),
        "gallery_bisected": gal_gain < gal_gain_raw - 1e-9,
        "gallery_clip_pct": round(100.0 * clip_fraction(mx, gal_gain), 4),
        "total_divergence_stops": round(gal_stops - ship_stops, 4),
        "axis_target_stops": round(axis_target, 4),
        "axis_statistic_stops": round(axis_stat, 4),
        "axis_method_stops": round(axis_method, 4),
        "axis_guard_stops": round(axis_guard, 4),
        "fixed_point_stops": fixed_point_stops,
    }
    del lin, mx
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for p in sorted(glob.glob(os.path.join(GALLERY, "*-srgb.tif"))):
        name = os.path.basename(p)[: -len("-srgb.tif")]
        rows.append(analyse(p, name))
        print("done %s" % name)

    pos = {}
    for k, v in M100_PUBLISHED.items():
        r = next((x for x in rows if x["stack"] == k), None)
        if r is not None:
            pos[k] = {"mine": r["shipped_stops"], "M100": v,
                      "delta": round(abs(r["shipped_stops"] - v), 4)}
    pos_pass = bool(pos) and all(v["delta"] <= 0.01 for v in pos.values())

    fp = [abs(r["fixed_point_stops"]) for r in rows]
    placebo_pass = bool(fp) and all(x <= 0.02 for x in fp)

    med = {a: float(np.median([abs(r["axis_%s_stops" % a]) for r in rows]))
           for a in ("target", "statistic", "method", "guard")}
    dominant = max(med, key=med.get)

    tot = [abs(r["total_divergence_stops"]) for r in rows]
    n_big = sum(1 for x in tot if x > 0.10)
    n_small = sum(1 for x in tot if x < 0.02)
    if n_big > len(tot) / 2:
        verdict = "ODD ONE OUT"
    elif n_small > len(tot) / 2:
        verdict = "COSMETIC"
    else:
        verdict = "MATERIAL BUT SMALL"

    result = {
        "note_0_92_was_never_swept": "sweep.py:31 TARGETS = [0.80, 0.85, 0.90, 0.95, 1.00]",
        "POSITIVE_CONTROL": {"reading": "PASS" if pos_pass else "FAIL", "detail": pos},
        "PLACEBO_fixed_point": {
            "reading": "PASS" if placebo_pass else "FAIL",
            "max_abs_stops": round(max(fp), 4) if fp else None,
        },
        "median_abs_contribution_stops": {k: round(v, 4) for k, v in med.items()},
        "DOMINANT_AXIS": dominant,
        "VERDICT_on_gallery_py": verdict,
        "n_stacks": len(rows),
        "n_diverging_over_0_10_stops": n_big,
        "rows": rows,
    }

    dst = os.path.join(OUT, "06-reconcile-targets.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print("")
    print("%-24s %8s %8s %8s %9s %9s %9s %9s %8s"
          % ("stack", "ship", "gallery", "diverge", "d:target", "d:stat",
             "d:method", "d:guard", "fixpt"))
    for r in rows:
        print("%-24s %+8.2f %+8.3f %+8.3f %+9.3f %+9.3f %+9.3f %+9.3f %+8.2f"
              % (r["stack"], r["shipped_stops"], r["gallery_stops"],
                 r["total_divergence_stops"], r["axis_target_stops"],
                 r["axis_statistic_stops"], r["axis_method_stops"],
                 r["axis_guard_stops"], r["fixed_point_stops"]))
    print("")
    print(json.dumps({k: result[k] for k in
                      ("POSITIVE_CONTROL", "PLACEBO_fixed_point",
                       "median_abs_contribution_stops", "DOMINANT_AXIS",
                       "VERDICT_on_gallery_py")}, indent=2))
    print("wrote " + dst)


if __name__ == "__main__":
    main()
