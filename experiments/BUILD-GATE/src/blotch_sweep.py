"""The two-column admission sweep: blotch and sharpness, on the same pixels.

ORCH: "A row with only the left column is inadmissible." So every row carries
both, and both bands are stated:

  blotch     sigma_mid, 20-60 px, ORCH's `orch_eye_check` statistic, imported.
  sharp/flat band 0.20-0.25 cyc/px on THE SAME FLAT PIXELS the blotch is read
             on. This is the column that catches "cleaned it by blurring it".
  sharp/tex  band 0.20-0.25 cyc/px on the textured sites, i.e. where the
             product's sharpness actually lives. Reported because a knob that
             is harmless on flat sky and ruinous on an eye is not harmless.

Everything is a RATIO against the shipped arm. The absolute sigma_mid on any
crop contains subject structure; the ratio does not, because every arm is the
same subject, same frames, one pinned binary, differing only in k.
"""
import os
import sys
import json

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blotch as bl                                               # noqa: E402
import bandceiling as bc                                          # noqa: E402
from orch_sharp1to1 import luma                                   # noqa: E402
from ceiling import pick_sites                                    # noqa: E402
import tifffile                                                   # noqa: E402


def fine_on(c):
    return float(np.mean(bc.tile_bands(luma(c * 257.0))[..., 1]))


def run(subject):
    """Cached: the sweep re-reads 7 full masters per subject, which is slow."""
    cp = os.path.join(bl.SWEEP, "..", "blotch_rows_%s.json" % subject)
    if os.path.exists(cp):
        with open(cp) as f:
            d = json.load(f)
        return ({k: tuple(v) for k, v in d["rows"].items()},
                [tuple(s) for s in d["flat"]], [tuple(s) for s in d["tex"]],
                d["rej"], d["ncand"])
    ref = os.path.join(bl.SWEEP, "WHITE200", subject + ".tiff")
    flat, rej, ncand = bl.pick_flat_sites(ref)
    tex, _ = pick_sites(tifffile.imread(ref)[..., :3].astype(np.float64))
    rows = {}
    for arm in bl.ARMS:
        p = os.path.join(bl.SWEEP, arm, subject + ".tiff")
        if not os.path.exists(p):
            continue
        mid, hp, ff, ft = [], [], [], []
        for (y, x) in flat:
            c = bl.codes(p, y, x)
            mid.append(np.mean([bl.sigma_mid(c[..., k]) for k in range(3)]))
            hp.append(np.mean([bl.sigma_hp(c[..., k]) for k in range(3)]))
            ff.append(fine_on(c))
        for (y, x) in tex:
            ft.append(fine_on(bl.codes(p, y, x)))
        rows[arm] = (float(np.mean(mid)), float(np.mean(hp)),
                     float(np.mean(ff)), float(np.mean(ft)))
    with open(cp, "w") as f:
        json.dump({"rows": rows, "flat": [list(s) for s in flat],
                   "tex": [list(s) for s in tex], "rej": rej,
                   "ncand": ncand}, f)
    return rows, flat, tex, rej, ncand


def main():
    print("Two-column admission sweep. Ratios vs WHITE200, the SHIPPED arm.")
    print("blotch = sigma_mid 20-60px (lower better). sharp = band 0.20-0.25 "
          "cyc/px (higher better).")
    best = {}
    for s in sys.argv[1:]:
        rows, flat, tex, rej, ncand = run(s)
        b = rows["WHITE200"]
        print("\n%s  N=%d frames   flat sites %r (of %d, rejected %r)"
              % (s, bl.NFRAMES[s], flat, ncand, rej))
        print("  %-9s %6s %11s %11s %11s %11s" %
              ("arm", "k", "blotch x", "grain x", "sharp/flat", "sharp/tex"))
        for arm in bl.ARMS:
            if arm not in rows:
                continue
            r = rows[arm]
            k = bl.KS[arm]
            print("  %-9s %6s %11.4f %11.4f %11.4f %11.4f"
                  % (arm, "ship" if k is None else "%.1f" % k,
                     r[0] / b[0], r[1] / b[1], r[2] / b[2], r[3] / b[3]))
        # The knee: the largest blotch reduction costing no measurable sharpness.
        cand = [(rows[a][0] / b[0], a) for a in bl.ARMS if a in rows
                and rows[a][3] / b[3] >= 0.99 and rows[a][2] / b[2] >= 0.99]
        best[s] = min(cand) if cand else None
        print("  KNEE (blotch min with sharp/tex >= 0.99 and sharp/flat >= 0.99): %s"
              % ("%s at %.4f x blotch" % (best[s][1], best[s][0]) if best[s]
                 else "NONE -- every blotch reduction costs measurable sharpness"))
    print("\nN-DEPENDENCE OF THE OPTIMUM")
    print("%-22s %6s %s" % ("subject", "N", "knee"))
    for s in sys.argv[1:]:
        print("%-22s %6d %s" % (s, bl.NFRAMES[s],
                                best[s][1] if best[s] else "none"))


if __name__ == "__main__":
    main()
