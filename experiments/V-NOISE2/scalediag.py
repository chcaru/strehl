"""scalediag -- the reproducer for fullhp DEFECTS 1 and 2.

`fullhp`'s SCALE arm was pre-registered to return 1.000: strehl-full read
against ITSELF through the geometry the comparator gets.  It returned 0.8867.
An 11.3% loss is far too large to be the 0.8% annulus bin-count difference
between a 255-px and a 256-px tile, so this isolates the things that path
changes, one at a time, against the same baseline.

It carries its OWN copy of the defective placement bounds test, because
`fullhp.Placer` has since been repaired and a reproducer that imports the fix
reproduces nothing.  `BuggyPlacer` below is the code as committed at 91150f56.

WHAT IT ESTABLISHED, and both findings are recorded in fullhp's header:

  DEFECT 1  the placement search ON at s = 1.0000 returned correlation peak
            exactly 1.0000 and offset exactly 0/0 on every surviving tile --
            the identical pixels the baseline read -- and yet S moved 12%.
            Identical pixels cannot give a different answer, so the tile
            POPULATION had to have changed.  The bounds test crossed its axes:
            `xb + b > mb.shape[0]` tests an x index against a row count, which
            with rb.shape = (1172, 1758) rejects every tile with x > 4432 in a
            7032-px-wide frame.
  DEFECT 2  tile size alone, no placement search, moves S by +4.5% at t = 255
            and +10.0% at t = 250.  The annulus is a discrete bin set and its
            membership is not stable under tile size, so matching the scene AREA
            between two arms of different content scale silently reads them on
            two different instruments.

    python scalediag.py [key=119]
"""
import os
import sys

import numpy as np
from scipy.ndimage import zoom

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
from h2h2b import Comp, T                                        # noqa: E402

import hd2                                                       # noqa: E402
from fullhp import (REG_D, REG_WIN, W, Placer, bandpower,        # noqa: E402
                    block_mean)


class BuggyPlacer:
    """fullhp.Placer as committed at 91150f56, crossed axes intact."""

    def __init__(self, ref, mov, scale):
        self.s = float(scale)
        self.rb = block_mean(ref.g, REG_D)
        mb = block_mean(mov.g, REG_D)
        self.mb = zoom(mb, self.s, order=3) if abs(self.s - 1.0) > 1e-9 else mb

    def place(self, y, x, t):
        s = self.s
        ts = int(round(t / s))
        b = t // REG_D
        yb, xb = y // REG_D, x // REG_D
        if (yb + b > self.rb.shape[0] or xb + b > self.mb.shape[0]
                or xb + b > self.rb.shape[1] or yb + b > self.mb.shape[1]):
            return None
        R = self.rb[yb:yb + b, xb:xb + b]
        R = R - R.mean()
        best, bdy, bdx = -2.0, 0, 0
        rn = np.sqrt((R * R).sum())
        if rn <= 0:
            return None
        for dy in range(-REG_WIN, REG_WIN + 1):
            for dx in range(-REG_WIN, REG_WIN + 1):
                ay, ax = yb + dy, xb + dx
                if (ay < 0 or ax < 0 or ay + b > self.mb.shape[0]
                        or ax + b > self.mb.shape[1]):
                    continue
                M = self.mb[ay:ay + b, ax:ax + b]
                M = M - M.mean()
                mn = np.sqrt((M * M).sum())
                if mn <= 0:
                    continue
                c = float((R * M).sum()) / (rn * mn)
                if c > best:
                    best, bdy, bdx = c, dy, dx
        return (int(round((y + bdy * REG_D) / s)),
                int(round((x + bdx * REG_D) / s)), ts, best,
                bdy * REG_D, bdx * REG_D)


def med_bp(comp, cells, placer=None, t=T):
    """The v1 population estimator: median band power, no level matching."""
    v = []
    for (y, x) in cells:
        if placer is None:
            y0, x0, ts = int(y), int(x), t
        else:
            pl = placer.place(int(y), int(x), T)
            if pl is None:
                continue
            # BuggyPlacer returns (y0, x0, ts) -- the SCALED tile size, which is
            # DEFECT 2 itself and must be preserved to reproduce it.  The
            # repaired Placer returns (y0, x0, peak, dy, dx) and reads both arms
            # at the same fixed t, which is the repair.  Cropping int(pl[2]) for
            # both took the repaired placer's correlation PEAK as a tile size
            # and cropped 1 px.
            y0, x0 = int(pl[0]), int(pl[1])
            ts = int(pl[2]) if len(pl) == 3 else t
        c, nc = comp.crop(y0, x0, ts)
        if c is None or nc:
            continue
        b = bandpower(c)
        if b is not None and np.isfinite(b):
            v.append(b)
    return np.array(v)


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "119"
    arm = os.path.join(hd2.ROOT, key, "arms")
    S = Comp(dict(path=os.path.join(arm, "strehl-full.tiff"), weights=W))
    z = np.load(os.path.join(hd2.ROOT, key, "census.npz"))
    cells, emax = z["cells"], z["emax"]
    flat = [int(i) for i in z["flat"]]
    det = [int(i) for i in np.argsort(emax)[-len(flat):]]
    DET = [tuple(cells[i]) for i in det]
    FLAT = [tuple(cells[i]) for i in flat]

    bD, bF = med_bp(S, DET), med_bp(S, FLAT)
    base = float(np.median(bD) - np.median(bF))
    print("=" * 96)
    print(f"SCALEDIAG -- reproducer for fullhp DEFECTS 1 and 2, {key}")
    print("=" * 96)
    print(f"  baseline (no placer, t={T}, {len(bD)} DETAIL / {len(bF)} FLAT "
          f"tiles): S {base:.4e}")

    print("\n  DEFECT 2 -- tile size alone, native position, no placement:")
    for ts in (256, 255, 254, 250, 240, 128):
        aD, aF = med_bp(S, DET, t=ts), med_bp(S, FLAT, t=ts)
        aS = float(np.median(aD) - np.median(aF))
        print(f"    t={ts:3d}  S {aS:.4e}  amplitude ratio to t=256 "
              f"{np.sqrt(aS/base):.4f}  ({len(aD)} tiles)")

    print("\n  DEFECT 1 -- the placement search, buggy bounds vs repaired:")
    for name, cls in (("BUGGY", BuggyPlacer), ("FIXED", Placer)):
        for s in (1.0000, 1.0040):
            P = cls(S, S, s)
            pD, pF = med_bp(S, DET, placer=P), med_bp(S, FLAT, placer=P)
            pS = float(np.median(pD) - np.median(pF))
            drop = [x for (y, x) in DET if P.place(int(y), int(x), T) is None]
            keptx = [x for (y, x) in DET if P.place(int(y), int(x), T) is not None]
            r = np.sqrt(pS / base) if pS > 0 else float("nan")
            print(f"    {name:6s} s={s:.4f}  S {pS:.4e}  ratio {r:.4f}  "
                  f"kept {len(pD)}/{len(DET)} DETAIL tiles")
            if drop:
                print(f"           {len(drop)} dropped, x in "
                      f"[{min(drop)}, {max(drop)}]; kept x max "
                      f"{max(keptx) if keptx else 0}; frame is {S.w} px wide")
    return 0


if __name__ == "__main__":
    sys.exit(main())
