r"""Can this instrument EXPRESS the other lane's x1.1697, or is it looking in
the wrong place? Sweeps the two choices that could hide such an effect:

  1. HOW FLAT is "flat". My default splits tiles at the median texture, so my
     "flat" class is the flatter HALF of the frame, which on a busy subject
     still contains real structure that dilutes a grain change. The other lane
     hand-picked three flat SITES. This sweeps the flat percentile down to the
     flattest 5%.
  2. WHICH BAND. My FINE group is bands 0-1 (2-8 px). The other lane quotes a
     "5-15 band" separately from "grain", so their grain band is finer than my
     group and a fine-only effect could be diluted by band 1. This reports
     EVERY band separately.

If the effect is real and I am merely mis-aimed, some (percentile, band) cell
will show it. If no cell shows it, the instrument is not the reason.
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bandmetrics as bm                                           # noqa: E402
import nscale as ns                                                # noqa: E402

OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--deep", type=int, required=True)
    ap.add_argument("--shallow", type=int, required=True)
    ap.add_argument("--tile", type=int, default=128)
    a = ap.parse_args()
    bm.TILE = a.tile

    imgs, cm = {}, None
    for arm in ("A-unset", "B-coarse8"):
        for lbl, n in (("deep", a.deep), ("shallow", a.shallow)):
            g, c, cf = ns.load64(os.path.join(
                OUT, "%s__N%d__%s.tiff" % (a.subject, n, arm)))
            imgs[(arm, lbl)] = g
            cm = c if cm is None else (cm | c)

    y0, x0, ty, tx = bm.tile_grid(imgs[("A-unset", "deep")].shape)
    cl = bm.tile_rms(cm.astype(np.float32), ty, tx, y0, x0)
    ok = (cl == 0.0)
    t, _ = ns.classify([imgs[k] for k in imgs], y0, x0, ty, tx)

    prof = {}
    for k, g in imgs.items():
        p, lvl = bm.band_profile(g, y0, x0, ty, tx)
        prof[k] = (p, lvl)

    print("%s  deep N=%d shallow N=%d   tile=%d   %d usable tiles"
          % (a.subject, a.deep, a.shallow, a.tile, int(ok.sum())))
    print("N-SCALING deep/shallow by band and by how strictly 'flat' is defined.")
    print("A value >1 means the DEEPER stack has MORE contrast in that band.")
    for pct in (50, 25, 10, 5):
        thr = np.percentile(t[ok], pct)
        sel = ok & (t <= thr)
        print("\n  --- flattest %d%% of tiles  (n=%d) ---" % (pct, int(sel.sum())))
        print("      band  scale       A-unset               B-coarse8            B vs A")
        for b in range(bm.NBANDS):
            row = {}
            for arm in ("A-unset", "B-coarse8"):
                d = bm.group(prof[(arm, "deep")][0], prof[(arm, "deep")][1], (b,))[sel]
                s = bm.group(prof[(arm, "shallow")][0], prof[(arm, "shallow")][1], (b,))[sel]
                row[arm] = ns.ratio(s, d)
            print("      %-5d %-11s x%.4f [%.4f,%.4f]  x%.4f [%.4f,%.4f]  %+.4f"
                  % (b, "%d-%d px" % (2 ** (b + 1), 2 ** (b + 2)),
                     row["A-unset"][0], row["A-unset"][1], row["A-unset"][2],
                     row["B-coarse8"][0], row["B-coarse8"][1], row["B-coarse8"][2],
                     row["B-coarse8"][0] - row["A-unset"][0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
