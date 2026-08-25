"""Does "a ratio of two arms on the same data" actually confer protection?

ORCH's refinement #2 states that a ratio of two arms on the same data is largely
protected by cancellation (measured: -1.0% under a planted narrowing), listing it
separately from the small-over-large hazard.

M111's boundary-hardness statistic is a ratio of two arms on the same data --
merged p90 over control p90 -- and it moved -8.7%, not -1.0%. So either the
protection has a boundary or one of the two measurements is wrong.

HYPOTHESIS: cancellation protects only when the two arms are COMPARABLE IN
MAGNITUDE. Quantisation adds a roughly constant absolute floor to both arms, so
it is a similar FRACTION of each only when they are similar in size. M111's two
arms differ by 6.1x (1384 against 227), which makes the statistic simultaneously
"a ratio of two arms" and "small over large". The two triage questions are not
independent, and the protective one can clear a statistic the hazardous one
condemns.

PRE-REGISTERED, before the numbers exist:

  If ORCH's rule holds as stated (protection is a property of being a two-arm
  ratio), |shift| is ~1% at ALL disparities and shows no trend in D.

  If the hypothesis holds, |shift| -> 0 as D -> 1 and grows monotonically with D,
  passing through roughly 8% near D = 6 where M111's statistic sits.

  If neither, |shift| is unrelated to D and both explanations are wrong.

Discriminator: Spearman correlation between D and |shift| across tiles, plus the
binned means. The hypothesis requires rho > 0.5 and a low-D bin under 2%.

RUN 1 RESULT (stride 384, 181 tiles): PRE-REGISTERED GATE FAILED.
  rho = +0.503 (passes), low-D mean |shift| = 2.92% (FAILS the <2% bar).
  Binned means were monotone across a 29x range: 2.42 3.42 5.84 17.67 19.72
  41.45 71.47. Binned medians: 1.13 0.68 2.87 5.99 6.76 7.02 8.17.

  The mean was the wrong choice and that is a design error I own. A ratio of
  two gradient statistics is heavy-tailed by construction -- a tile where the
  denominator arm is near zero throws an unbounded shift -- and the top bin's
  mean (71%) against its median (8%) shows the tail dominating. That is
  knowable a priori, not from the answer. The lowest bin also had n=4, too few
  to bound anything.

RUN 2, PRE-REGISTERED HERE BEFORE IT WAS RUN (stride 128, ~10x the tiles),
because switching to medians post hoc on run 1 would be worthless:

  (a) with n >= 50 in the lowest-disparity bin, MEDIAN |shift| for D < 1.25
      will be BELOW 2%;
  (b) the median will rise monotonically with D and exceed 6% for D > 5;
  (c) the MEAN will exceed the median in every bin, and the lowest bin's mean
      will still exceed 2% -- i.e. run 1's failure will reproduce and is a
      property of the statistic, not of the sample size.

  If (a) or (b) fails, the disparity hypothesis is wrong and ORCH's rule stands
  as stated. If (c) fails, run 1's failure was small-sample noise rather than a
  tail, and my account of my own error is wrong.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile
from PIL import Image

OUT = r"C:\dev\strehl-out\M111-pil-audit"
ORCHDIR = r"C:\dev\strehl-out\ORCH-thennow"
MERGED = os.path.join(ORCHDIR, "marker-HEAD-8f46f04.tif")
CTRL = os.path.join(ORCHDIR, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif")
TILE = 256
STRIDE = int(os.environ.get("M111_STRIDE", "384"))
TAG = os.environ.get("M111_TAG", "run1")


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def gp90(y):
    gy, gx = np.gradient(y)
    return float(np.percentile(np.sqrt(gx * gx + gy * gy), 90))


def main():
    os.makedirs(OUT, exist_ok=True)
    mt, ct = tifffile.imread(MERGED), tifffile.imread(CTRL)
    mp, cp = np.asarray(Image.open(MERGED)), np.asarray(Image.open(CTRL))
    assert mt.dtype == np.uint16 and ct.dtype == np.uint16, "inputs are not 16-bit"
    assert mp.dtype == np.uint8 and cp.dtype == np.uint8, "PIL did not narrow; hazard absent"
    h = min(mt.shape[0], ct.shape[0])
    w = min(mt.shape[1], ct.shape[1])
    print("common crop %dx%d   tile %d stride %d" % (h, w, TILE, STRIDE))

    rows = []
    for y0 in range(200, h - TILE - 200, STRIDE):
        for x0 in range(200, w - TILE - 200, STRIDE):
            sy, sx = slice(y0, y0 + TILE), slice(x0, x0 + TILE)
            m_t, c_t = gp90(luma(mt[sy, sx])), gp90(luma(ct[sy, sx]))
            m_p, c_p = gp90(luma(mp[sy, sx])), gp90(luma(cp[sy, sx]))
            if min(m_t, c_t) < 1e-6 or min(m_p, c_p) < 1e-6:
                continue
            r_t, r_p = m_t / c_t, m_p / c_p
            rows.append({
                "y": y0, "x": x0,
                "disparity": max(m_t, c_t) / min(m_t, c_t),
                "shift_pct": 100.0 * (r_p - r_t) / r_t,
                "m_t": m_t, "c_t": c_t,
            })
    print("tiles: %d" % len(rows))

    D = np.array([r["disparity"] for r in rows])
    S = np.abs(np.array([r["shift_pct"] for r in rows]))

    def rank(a):
        o = np.argsort(a)
        rk = np.empty(len(a), float)
        rk[o] = np.arange(len(a), dtype=float)
        return rk

    rd, rs = rank(D), rank(S)
    rho = float(np.corrcoef(rd, rs)[0, 1])

    edges = [1.0, 1.25, 1.5, 2.0, 3.0, 5.0, 8.0, np.inf]
    print("\n%-14s %6s %10s %10s %10s" % ("disparity D", "n", "mean|shift|", "median", "p90"))
    print("-" * 54)
    bins = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (D >= lo) & (D < hi)
        if sel.sum() < 3:
            continue
        b = {"lo": lo, "hi": None if np.isinf(hi) else hi, "n": int(sel.sum()),
             "mean_abs_shift_pct": float(S[sel].mean()),
             "median_abs_shift_pct": float(np.median(S[sel])),
             "p90_abs_shift_pct": float(np.percentile(S[sel], 90))}
        bins.append(b)
        print("%-14s %6d %10.2f %10.2f %10.2f"
              % ("[%.2f,%s)" % (lo, "inf" if np.isinf(hi) else "%.2f" % hi),
                 b["n"], b["mean_abs_shift_pct"], b["median_abs_shift_pct"],
                 b["p90_abs_shift_pct"]))

    low = [b for b in bins if b["lo"] < 1.5]
    lowmean = float(np.mean([b["mean_abs_shift_pct"] for b in low])) if low else float("nan")
    monotone = all(bins[i]["mean_abs_shift_pct"] <= bins[i + 1]["mean_abs_shift_pct"] + 0.5
                   for i in range(len(bins) - 1))
    verdict = ("HYPOTHESIS SUPPORTED" if (rho > 0.5 and lowmean < 2.0)
               else "HYPOTHESIS NOT SUPPORTED")
    print("\n[run-1 gate, mean-based]  Spearman rho(D, |shift|) = %+.3f   "
          "low-D (<1.5) mean |shift| = %.2f%%   binned means monotone: %s"
          % (rho, lowmean, monotone))
    print("[run-1 gate] %s  (needs rho > 0.5 and low-D mean < 2%%)" % verdict)

    # --- run-2 gate, registered in the docstring before run 2 existed --------
    b0 = next((b for b in bins if b["lo"] == 1.0), None)
    med = [b["median_abs_shift_pct"] for b in bins]
    a_ok = bool(b0 and b0["n"] >= 50 and b0["median_abs_shift_pct"] < 2.0)
    hi = [b for b in bins if b["lo"] >= 5.0]
    b_ok = bool(hi and all(med[i] <= med[i + 1] + 0.5 for i in range(len(med) - 1))
                and max(b["median_abs_shift_pct"] for b in hi) > 6.0)
    c_ok = bool(all(b["mean_abs_shift_pct"] >= b["median_abs_shift_pct"] for b in bins)
                and b0 and b0["mean_abs_shift_pct"] > 2.0)
    print("\n[run-2 gate, median-based, pre-registered]")
    print("  (a) lowest bin n>=50 and median < 2%%          : %s  (n=%s, median=%s)"
          % ("PASS" if a_ok else "FAIL",
             b0["n"] if b0 else "-",
             ("%.2f%%" % b0["median_abs_shift_pct"]) if b0 else "-"))
    print("  (b) medians monotone and exceed 6%% at D>5     : %s" % ("PASS" if b_ok else "FAIL"))
    print("  (c) mean > median in every bin, low bin mean>2%%: %s" % ("PASS" if c_ok else "FAIL"))
    run2 = ("DISPARITY HYPOTHESIS SUPPORTED" if (a_ok and b_ok)
            else "DISPARITY HYPOTHESIS NOT SUPPORTED")
    print("  verdict: %s%s" % (run2, "" if c_ok else "   [c FAILED: tail account is wrong]"))

    doc = {"tag": TAG, "stride": STRIDE, "n_tiles": len(rows), "spearman_rho": rho,
           "low_D_mean_abs_shift_pct": lowmean, "binned_monotone": bool(monotone),
           "run1_verdict": verdict,
           "run2_gate": {"a_low_bin_median_under_2": a_ok, "b_monotone_and_over_6": b_ok,
                         "c_mean_exceeds_median": c_ok, "verdict": run2},
           "bins": bins, "m111_statistic": {"disparity": 6.105, "shift_pct": -8.7},
           "orch_reported": {"shift_pct": -1.0}}
    dst = os.path.join(OUT, "twoarm_cancellation-%s.json" % TAG)
    io.open(dst, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, indent=1))
    print("wrote %s" % dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
