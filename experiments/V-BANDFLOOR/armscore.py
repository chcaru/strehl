"""Score arbitrary arms on the directed primary axis, with both guards.

Prints, per arm: the N-SCALING ratio (deep/shallow) for flat and for detail --
the directed criterion is flat <= 1.0000 -- and the ABSOLUTE ratio against
A-unset at each N, which is what a viewer actually receives. Guard 2 (a global
softening must not buy the flat win) is enforced by printing the detail column
beside every flat column and never quoting one alone.
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
    ap.add_argument("--arms", required=True)
    ap.add_argument("--tile", type=int, default=128)
    ap.add_argument("--pct", type=float, default=25.0)
    ap.add_argument("--bands", default="0,1,2")
    a = ap.parse_args()
    bm.TILE = a.tile
    arms = a.arms.split(",")
    bands = [int(x) for x in a.bands.split(",")]

    imgs, cm, clips = {}, None, {}
    for arm in arms:
        for lbl, n in (("deep", a.deep), ("shallow", a.shallow)):
            p = os.path.join(OUT, "%s__N%d__%s.tiff" % (a.subject, n, arm))
            g, c, cf = ns.load64(p)
            imgs[(arm, lbl)] = g
            clips["%s/N%d" % (arm, n)] = cf
            cm = c if cm is None else (cm | c)

    g0 = imgs[(arms[0], "deep")]
    y0, x0, ty, tx = bm.tile_grid(g0.shape)
    cl = bm.tile_rms(cm.astype(np.float32), ty, tx, y0, x0)
    ok = (cl == 0.0)
    t, _ = ns.classify([imgs[k] for k in imgs], y0, x0, ty, tx)
    fthr = np.percentile(t[ok], a.pct)
    tthr = np.percentile(t[ok], 100 - a.pct)
    flat = ok & (t <= fthr)
    tex = ok & (t >= tthr)

    prof = {k: bm.band_profile(g, y0, x0, ty, tx) for k, g in imgs.items()}

    def col(k, b, sel):
        return bm.group(prof[k][0], prof[k][1], (b,))[sel]

    print("%s  deep N=%d  shallow N=%d   tile=%d   flattest/most-textured %g%%  (%d/%d tiles)"
          % (a.subject, a.deep, a.shallow, a.tile, a.pct, int(flat.sum()), int(tex.sum())))
    print("  clip: " + "  ".join("%s %.4f%%" % (k, 100 * v) for k, v in clips.items()))
    for b in bands:
        print("\n  === BAND %d (%d-%d px)  --- N-SCALING deep/shallow, criterion FLAT <= 1.0000"
              % (b, 2 ** (b + 1), 2 ** (b + 2)))
        print("      %-10s %-26s %-26s" % ("arm", "FLAT grain", "DETAIL sharp"))
        base = None
        for arm in arms:
            f = ns.ratio(col((arm, "shallow"), b, flat), col((arm, "deep"), b, flat))
            x = ns.ratio(col((arm, "shallow"), b, tex), col((arm, "deep"), b, tex))
            if base is None:
                base = f[0]
            print("      %-10s x%.4f [%.4f,%.4f]   x%.4f [%.4f,%.4f]   %s"
                  % (arm, f[0], f[1], f[2], x[0], x[1], x[2],
                     "" if arm == arms[0] else "dFLAT %+.4f" % (f[0] - base)))
        print("      --- ABSOLUTE vs %s at fixed N (what is actually delivered)" % arms[0])
        for arm in arms[1:]:
            for lbl in ("deep", "shallow"):
                f = ns.ratio(col((arms[0], lbl), b, flat), col((arm, lbl), b, flat))
                x = ns.ratio(col((arms[0], lbl), b, tex), col((arm, lbl), b, tex))
                print("      %-10s %-7s grain x%.4f [%.4f,%.4f]   sharp x%.4f [%.4f,%.4f]"
                      % (arm, lbl, f[0], f[1], f[2], x[0], x[1], x[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
