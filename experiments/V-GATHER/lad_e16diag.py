r"""Why does the e16 arm appear to have MOVED, and is its huge excess a number?

lad_audit.py flagged 15 sites as displaced between the default arm and e16, with
shifts as large as (350, -356). Every arm merges ONE source set into ONE
reference grid, so a 350 px rigid displacement is not physically available. Two
hypotheses:

  (a) the arm really is displaced -- which would invalidate measuring it at the
      frozen coordinates, and

  (b) the cross-correlation cannot LOCALISE, because near-argmax selection at
      exponent 16 fills the image with high-frequency content uncorrelated with
      the default arm's, leaving a flat correlation surface whose argmax is
      arbitrary.

These make opposite predictions under a low-pass. Under (a) the displacement is
rigid and survives blurring: a low-passed e16 still correlates at the same large
offset. Under (b) the coarse structure is shared, so a low-passed pair locks at
(0, 0) while the full-band pair does not. The peak confidence est_shift already
returns separates them a second way.

WHY IT MATTERS EVEN THOUGH THE MEASUREMENT DOES NOT USE THE SHIFT. measure_array
reads the FROZEN coordinates and applies no shift, so nothing here changes a
ladder number. What is at stake is the INTERPRETATION: under (b) the flag is
itself evidence that exponent 16 has decorrelated the fine structure from the
shipping arm, which is the manufactured-detail claim showing up in a second,
independent quantity.
"""
import os
import subprocess
import sys
import time

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import certmeasure as cm                                           # noqa: E402
import lad_measure as lm                                           # noqa: E402

SUB = "coffee-bubbles"
HALF = 384


def render(sub, out, exponent, sharpen):
    env = dict(os.environ)
    env["STREHL_CACHE_DIR"] = os.path.join(lm.LAD, "cache-" + sub)
    for v in ("STREHL_FIX_CA", "STREHL_EDGE_AWARE", "STREHL_EDGE_TAU",
              "STREHL_EDGE_CONF", "STREHL_ONLY_FRAME"):
        env.pop(v, None)
    cmd = [cm.EXE, "stack", os.path.join(cm.RAW, sub), "--out", out,
           "--linear-srgb", "--demosaic"]
    if exponent is not None:
        cmd += ["--pyramid-exponent", str(exponent), "--pyramid-sharpen", str(sharpen)]
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if p.returncode != 0 or not os.path.exists(out):
        raise SystemExit("render failed: %s" % p.stderr[-300:])
    return out


def main():
    cm.check_binary()
    sites, _ = lm.frozen_sites(SUB)
    pd = os.path.join(lm.LAD, "diag-default.tiff")
    p16 = os.path.join(lm.LAD, "diag-e16.tiff")
    p8 = os.path.join(lm.LAD, "diag-e8.tiff")
    for p, e, s in ((pd, None, None), (p16, 16, 1.0), (p8, 8, 1.0)):
        if not os.path.exists(p):
            render(SUB, p, e, s)
    ld, _ = lm.load_lum(pd)
    l16, _ = lm.load_lum(p16)
    l8, _ = lm.load_lum(p8)

    print("=== full-band vs low-passed correlation, default -> arm ===")
    print("  %-18s %-22s %-22s" % ("site", "full band (dy,dx,conf)", "low-pass s=8 (dy,dx,conf)"))
    for arm, la in (("e8", l8), ("e16", l16)):
        print("  -- arm %s" % arm)
        nfull0 = nlow0 = 0
        for s in sites:
            cy, cx = s["y"] + lm.WIN // 2, s["x"] + lm.WIN // 2
            a = ld[cy - HALF:cy + HALF, cx - HALF:cx + HALF]
            b = la[cy - HALF:cy + HALF, cx - HALF:cx + HALF]
            if a.shape != b.shape:
                continue
            dy, dx, cf = cm.est_shift(a, b)
            ga = ndimage.gaussian_filter(a, 8.0)
            gb = ndimage.gaussian_filter(b, 8.0)
            ly, lx, lc = cm.est_shift(ga, gb)
            nfull0 += (dy == 0 and dx == 0)
            nlow0 += (ly == 0 and lx == 0)
            print("    (%4d,%4d)  %6d %6d %7.2f      %6d %6d %7.2f"
                  % (s["y"], s["x"], dy, dx, cf, ly, lx, lc))
        print("    locked at (0,0): full band %d/%d   low-pass %d/%d"
              % (nfull0, len(sites), nlow0, len(sites)))

    print("\n=== is the e16 excess a real number? raw bands at the worst sites ===")
    rows16 = lm.measure_array(l16, sites)
    rowsd = lm.measure_array(ld, sites)
    order = sorted(range(len(sites)),
                   key=lambda i: -(rows16[i].get("excess") or -9))
    print("  %-14s %12s %12s %12s %12s"
          % ("site", "ceiling", "default band", "e16 band", "e16 excess"))
    for i in order[:5]:
        s = sites[i]
        print("  (%4d,%4d) %12.6f %12.6f %12.6f %11.2f%%"
              % (s["y"], s["x"], s["ceiling"], rowsd[i]["master"],
                 rows16[i]["master"], 100 * rows16[i]["excess"]))
    print("  all finite: e16 %s  default %s"
          % (all(lm.finite(r.get("excess")) for r in rows16),
             all(lm.finite(r.get("excess")) for r in rowsd)))
    for p in (pd, p16, p8):
        os.remove(p)


if __name__ == "__main__":
    main()
