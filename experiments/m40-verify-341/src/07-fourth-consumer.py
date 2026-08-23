"""M40 verification, script 07 -- the FOURTH consumer, and Jensen.

The change under review enumerates three consumers of `predicted_sigma`: the detail
metric's noise term, confidence channel C1, and `sigma_cut`.  There is a fourth, and it is
the one that PRINTS the defect fact 341 named.

crates/strehl-cli/src/merge_cmd.rs:912 prints a column headed

    "pred sigma gain 1/sqrt(n)"

whose value is `1.0 / mean_n_eff().sqrt()` -- computed from the mean acceptance-set size
alone, never calling `predicted_sigma`.  So after the repair the tool asserts in code that
the gate-0 predicted sigma is 1.074x a single frame, and prints in its own report that the
gate-0 predicted-sigma gain is 1.0000x.  Measured directly from the two binaries in
out/05-*.txt: that column is byte-identical in both arms.

Two separate errors live in that one column and this script separates them.

  (a) THE INFLATION IS MISSING.  The column does not go through `predicted_sigma`.
  (b) JENSEN.  Even without any inflation, `1/sqrt(mean n)` is not the mean gain.  The
      gain per pixel is `1/sqrt(n_i)`; 1/sqrt(.) is convex, so
      `mean(1/sqrt(n)) >= 1/sqrt(mean n)` with equality only when n is constant.  The
      column therefore reports a gain BETTER than the merge achieves, by an amount that
      grows with the spread of n.

RULE 20 -- WHAT WOULD MAKE THIS FAIL.  If the acceptance-set size were near-constant
across the plane the Jensen gap would vanish and (b) would be a pedantic non-finding.  The
CLI itself reports 41.66% of pixels at n_eff = 1 while mean n_eff = 1.884 at gate 1.00 on
109MSDCF, so n is very far from constant; a measured gap of under 1% would still refute
(b) as material.  For (a): if the three ratios below coincide, there is no fourth consumer
and no inconsistency.

Measured on the two flat ROIs of 109MSDCF only.  The ROI is a sample of the plane, not the
plane; the CLI's own whole-plane n_eff=1 share is quoted beside it for scale.

Outputs: out/07-fourth-consumer.txt
"""

import glob
import json
import os
import sys

import numpy as np
import rawpy

BLACK, GAIN_DIV, RN_E_LOW, SIGMA_EPS = 512.0, 436.8, 4.20, 1e-3
WINDOW_RADIUS, REG_RADIUS, MARGIN = 13, 8, 24
FOCUS_NOISE_SD = 0.015214
SELECTION_INFLATION = 1.074
GATES = [0.0, 0.5, 1.0, 2.0, 4.0]
PATH, ISO = r"C:\dev\macro\test\109MSDCF", 160.0
ROIS = {"flat-M2 2272,1344": (2272, 1344), "flat-M11 2352,1408": (2352, 1408)}


def sigma_luma(S, g, rd):
    return np.sqrt(0.5 * (g * np.maximum(S, 0.0) + rd * rd))


def box_mean(a, r):
    H, W = a.shape
    c = np.pad(np.cumsum(np.cumsum(a, 0), 1), ((1, 0), (1, 0)))
    y0, y1 = np.maximum(np.arange(H) - r, 0), np.minimum(np.arange(H) + r, H - 1)
    x0, x1 = np.maximum(np.arange(W) - r, 0), np.minimum(np.arange(W) + r, W - 1)
    s = (c[np.ix_(y1 + 1, x1 + 1)] - c[np.ix_(y0, x1 + 1)]
         - c[np.ix_(y1 + 1, x0)] + c[np.ix_(y0, x0)])
    return s / np.outer(y1 - y0 + 1, x1 - x0 + 1)


def sobel_mag(a):
    p = np.pad(a, 1, mode="edge")
    gx = (p[:-2, 2:] + 2 * p[1:-1, 2:] + p[2:, 2:]
          - p[:-2, :-2] - 2 * p[1:-1, :-2] - p[2:, :-2]) * 0.125
    gy = (p[2:, :-2] + 2 * p[2:, 1:-1] + p[2:, 2:]
          - p[:-2, :-2] - 2 * p[:-2, 1:-1] - p[:-2, 2:]) * 0.125
    return np.hypot(gx, gy)


def main():
    os.makedirs("out", exist_ok=True)
    out = open("out/07-fourth-consumer.txt", "w", encoding="utf-8")

    def emit(s=""):
        print(s, flush=True)
        out.write(s + "\n")

    frames = sorted(glob.glob(os.path.join(PATH, "*.ARW")))
    g, rd = ISO / GAIN_DIV, RN_E_LOW * ISO / GAIN_DIV
    acc = {k: dict(L=[], reg=[]) for k in ROIS}
    for p in frames:
        r = rawpy.imread(p)
        a = r.raw_image_visible
        for k, (x, y) in ROIS.items():
            cx, cy, cw, ch = x - MARGIN, y - MARGIN, 256 + 2 * MARGIN, 256 + 2 * MARGIN
            sub = a[2 * cy: 2 * (cy + ch), 2 * cx: 2 * (cx + cw)].astype(np.float64)
            g1, g2 = sub[0::2, 1::2], sub[1::2, 0::2]
            lf = 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))
            focus = box_mean(sobel_mag(lf), WINDOW_RADIUS) / np.maximum(
                sigma_luma(lf, g, rd), SIGMA_EPS)
            acc[k]["reg"].append(box_mean(focus, REG_RADIUS).astype(np.float32))
            acc[k]["L"].append((0.5 * (g1 + g2) - BLACK).astype(np.float32))
        del r, a
    sl = (slice(MARGIN, MARGIN + 256), slice(MARGIN, MARGIN + 256))

    emit("=" * 100)
    emit("M40 script 07 -- 'pred sigma gain' is a fourth consumer, and it is not a mean")
    emit("=" * 100)
    emit("  CLI column   = 1/sqrt(mean n)                     [merge_cmd.rs:912, no inflation]")
    emit("  true gain    = mean( 1/sqrt(n) )                  [Jensen-correct, no inflation]")
    emit("  shipped gain = mean( infl(n)/sqrt(n) )            [what predicted_sigma now implies]")
    emit("  sigma-wtd    = mean(sigma*infl/sqrt(n)) / mean(sigma)   [the ratio C1 actually forms]")
    emit("")
    res = {}
    for k in ROIS:
        L = np.stack(acc[k]["L"])[:, sl[0], sl[1]].astype(np.float64)
        R = np.stack(acc[k]["reg"])[:, sl[0], sl[1]]
        best, win = R.max(axis=0), R.argmax(axis=0)
        h = w = 256
        emit(f"  --- ROI {k} ---")
        emit("     gate   mean n   n=1 %   CLI column   true gain  shipped gain   sigma-wtd"
             "   CLI vs true")
        rows = {}
        for gate in GATES:
            tol = gate * np.sqrt(2.0) * FOCUS_NOISE_SD
            admit = best[None] - R <= tol
            admit[win, np.arange(h)[:, None], np.arange(w)[None, :]] = True
            n = admit.sum(axis=0).astype(np.float64)
            merged = (L * admit).sum(axis=0) / n
            sg = sigma_luma(merged, g, rd)
            infl = np.where(n <= 1, SELECTION_INFLATION, 1.0)
            cli = 1.0 / np.sqrt(n.mean())
            true = float((1.0 / np.sqrt(n)).mean())
            ship = float((infl / np.sqrt(n)).mean())
            swt = float((sg * infl / np.sqrt(n)).mean() / sg.mean())
            emit(f"     {gate:4.2f} {n.mean():8.4f} {100 * (n <= 1).mean():6.2f}% "
                 f"{cli:12.4f}x {true:11.4f}x {ship:13.4f}x {swt:11.4f}x "
                 f"{100 * (cli / true - 1):+9.2f}%")
            rows[gate] = dict(mean_n=float(n.mean()), n1=float((n <= 1).mean()),
                              cli=float(cli), true=true, shipped=ship, sigma_wtd=swt)
        res[k] = rows
        emit("")
    json.dump(res, open("out/07-fourth-consumer.json", "w"), indent=1)
    emit("  For scale, the CLI's own WHOLE-PLANE reading on this stack (out/05-*.txt):")
    emit("    gate 0.00 : mean n_eff 1.000, n_eff=1 100.00%, column 1.0000x  (both arms)")
    emit("    gate 1.00 : mean n_eff 1.884, n_eff=1  41.66%, column 0.7285x  (both arms)")
    out.close()


if __name__ == "__main__":
    sys.exit(main())
