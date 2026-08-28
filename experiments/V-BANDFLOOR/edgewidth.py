r"""Per-arm EDGE WIDTH and STEP at the identical selected edges.

WHY THIS EXISTS. The rim statistic max(q[+2..+7])-1 falls when overshoot is
removed AND when the edge is simply blurred -- a wide edge has not reached its
plateau by +7 px, so it reads lower with nothing fixed. rimv6's own docstring
records that its v3 predecessor read +14.85% on a smoothed image and was
declared inadmissible for exactly this confusion. A rim REDUCTION is therefore
only evidence of less halo if the edge did not get wider at the same time.

Selection is reproduced bit for bit from rimab.run: same mean-of-arms
reference, same cut sweep, same seed.
"""
import argparse
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "V-H2H2-RIMCLIP")))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "V-GATHER")))
import rimv6                                                       # noqa: E402
import rimaxis                                                     # noqa: E402
import rimab                                                       # noqa: E402


def widths(gA, gB, cm, label_a="A", label_b="B"):
    gm = 0.5 * (gA + gB)
    rois = rimaxis.pick_rois(gm, cm, n=rimab.NTILE)
    ref = ndimage.gaussian_filter(gm, rimab.SMOOTH).astype(np.float32)
    best = rimab.choose(ref, cm, rois)
    if best is None:
        print("  REFUSED: no cut")
        return
    sel = best[2]
    out = {}
    for name, g in ((label_a, gA), (label_b, gB)):
        e = rimv6.measure(g, sel, rimab.T)
        w = rimv6.edge_width(e)
        s = rimv6.stats(e, nmin=rimab.NMIN)
        # bootstrap the width by resampling edges
        rng = np.random.default_rng(77)
        idx = rng.integers(0, len(e["prof"]), size=(600, len(e["prof"])))
        ws = []
        for row in idx:
            q = np.median(e["prof"][row], axis=0)
            sl = 0.5 * (q[rimv6.R + 1] - q[rimv6.R - 1])
            ws.append(0.8 / sl if sl > 1e-9 else np.nan)
        ws = np.array(ws)
        out[name] = (w, float(np.percentile(ws, 2.5)),
                     float(np.percentile(ws, 97.5)), s["step_median"],
                     s["bright"], s["n"])
        print("  %-10s edge 10-90 width %6.3f px [%6.3f, %6.3f]   median step "
              "%9.1f DN   bright %+7.3f%%   n=%d"
              % (name, out[name][0], out[name][1], out[name][2], out[name][3],
                 100 * out[name][4], out[name][5]))
    dw = out[label_b][0] - out[label_a][0]
    print("  WIDTH CHANGE B-A %+.4f px  (%+.3f%%)  -- POSITIVE means B's edges "
          "are SOFTER" % (dw, 100 * dw / out[label_a][0]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--tag", default="")
    ap.add_argument("--commission", action="store_true")
    args = ap.parse_args()
    gA, cmA, clipA = rimab.load(args.a)
    gB, cmB, clipB = rimab.load(args.b)
    print("%s   A clip %.4f%%  B clip %.4f%%" % (args.tag, 100 * clipA, 100 * clipB))
    if args.commission:
        print("  COMMISSIONING: the width column must RISE on a blurred arm and")
        print("  must NOT rise on a pure-halo arm (USM raises rim, sharpens edge).")
        widths(gA, ndimage.gaussian_filter(gA, 1.0), cmA, "as-is", "blur s=1.0")
        widths(gA, rimab.usm(gA, 0.5, 2.0), cmA, "as-is", "USM 0.5 r2")
        return 0
    widths(gA, gB, cmA | cmB)
    return 0


if __name__ == "__main__":
    sys.exit(main())
