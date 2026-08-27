"""Determine, by measurement, which gauge the reusable source bundle is on.

The bundle records no render command, so its gauge is unknown until measured.
This lane exists because an unmatched gauge silently turns a ratio into an
exposure measurement, so the bundle is not usable until this returns.

Test: the bundle carries the master's own tile (`mb`). The SHIP-V4 master on
disk is `--srgb --auto-exposure`. Cut the same region out of it and compare. If
`mb` IS the sRGB master the two agree to within resampling dust; if `mb` is a
linear render they cannot agree, and the linear one is far darker.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile

SUBJ = "coffee-bubbles"
BUN = r"C:\dev\strehl-out\V-NEVERWORSE\bundle\%s.npz" % SUBJ
MET = r"C:\dev\strehl-out\V-NEVERWORSE\bundle\%s.json" % SUBJ
SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4\%s--SHIP-V4.tiff" % SUBJ


def main():
    meta = json.load(io.open(MET, encoding="utf-8"))
    z = np.load(BUN)
    mb = z["mb"].astype(np.float64)
    bw = meta["bw"]
    print("bundle mb  : shape %s  mean %.1f  p99 %.1f  max %d"
          % (mb.shape, mb.mean(), np.percentile(mb, 99), mb.max()))

    m = tifffile.imread(SHIP)
    print("SHIP-V4    : shape %s dtype %s  mean %.1f"
          % (m.shape, m.dtype, m.astype(np.float64).mean()))

    h, w = mb.shape[:2]
    # `bw` is the tile origin. Try both orderings rather than assume one.
    cands = {"bw=(x,y)": (bw[1], bw[0]), "bw=(y,x)": (bw[0], bw[1])}
    best = None
    for name, (y, x) in cands.items():
        if y + h > m.shape[0] or x + w > m.shape[1]:
            print("  %-10s out of bounds" % name)
            continue
        t = m[y:y + h, x:x + w].astype(np.float64)
        # scale-invariant agreement, so a pure gain cannot mask a match
        a = (mb - mb.mean()) / (mb.std() + 1e-9)
        b = (t - t.mean()) / (t.std() + 1e-9)
        r = float((a * b).mean())
        ratio = t.mean() / max(mb.mean(), 1e-9)
        print("  %-10s corr %+.4f   ship/bundle mean ratio %.3fx"
              % (name, r, ratio))
        if best is None or r > best[1]:
            best = (name, r, ratio)

    print()
    if best is None:
        print("REFUSED: no candidate tile origin was in bounds")
        return 2
    name, r, ratio = best
    if r > 0.95 and 0.9 < ratio < 1.1:
        print("VERDICT: the bundle IS the sRGB shipping master -- same gauge as "
              "SHIP-V4, NOT linear. A pyramid reimplementation on it would run "
              "on tone-mapped data and is INADMISSIBLE.")
        return 1
    if r > 0.5:
        print("VERDICT: same scene, different transfer (corr %+.4f at %.3fx "
              "mean). The bundle is NOT the sRGB master; consistent with a "
              "linear render." % (r, ratio))
        return 0
    print("VERDICT: the tiles do not even correlate (%+.4f). The recorded "
          "origin is wrong or the bundle is of something else. REFUSED." % r)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("\nREFUSED: gauge probe crashed; the bundle's gauge is UNKNOWN")
        sys.exit(2)
