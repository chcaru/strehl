#!/usr/bin/env python3
"""Did the window matcher actually find the partner window?

Every cross-arm number in detail.py rests on locating the same content in the
other arm by normalised cross-correlation.  If the match fails, the "damage"
being reported is the difference between two DIFFERENT pieces of scene, and the
number is not about damage at all.

This matters most for the `noalign` arm, whose frames carry 232.7 px of drift
against a search radius of 64 px.  A control that cannot be matched is not a
control, and reporting it as one would be worse than not running it.

Reports, per arm: the median NCC peak, the fraction of sites whose peak sits on
the edge of the search box (a peak against the wall means the true optimum is
outside it), and the median displacement found.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "BUILD-TRIAGE"))
import tri  # noqa: E402
from detail import ncc_offset, pick_sites, SEARCH, TILE  # noqa: E402

ROOT = Path(r"C:\dev\strehl-out\V-DRIFT")


def main() -> None:
    arms = sys.argv[1:] or ["iid2", "walk20", "iid20", "walk60", "noalign"]
    base = tri.luma(tri.load16(str(ROOT / "merge" / "d0.tif")))
    sites = pick_sites(base, 0.9321, 24, TILE)
    print(f"{len(sites)} sites, search radius {SEARCH} px\n")
    print(f"{'arm':10s} {'med NCC':>9s} {'min NCC':>9s} {'at wall':>9s} "
          f"{'med |shift|':>12s} {'max |shift|':>12s}")
    print("-" * 66)
    for arm in arms:
        p = ROOT / "merge" / f"{arm}.tif"
        if not p.exists():
            continue
        img = tri.luma(tri.load16(str(p)))
        sc, sh, wall = [], [], 0
        for (y, x) in sites:
            ref = base[y:y + TILE, x:x + TILE]
            hay = img[y - SEARCH:y + TILE + SEARCH, x - SEARCH:x + TILE + SEARCH]
            dy, dx, s = ncc_offset(ref, hay)
            sc.append(s)
            sh.append(np.hypot(dy - SEARCH, dx - SEARCH))
            if dy in (0, 2 * SEARCH) or dx in (0, 2 * SEARCH):
                wall += 1
        print(f"{arm:10s} {np.median(sc):9.4f} {min(sc):9.4f} "
              f"{wall:5d}/{len(sites):<3d} {np.median(sh):12.1f} {max(sh):12.1f}")
    print("\nA median NCC well below the others, or peaks against the wall, means the\n"
          "partner window was not found and that arm's detail row is not a\n"
          "measurement of damage.")


if __name__ == "__main__":
    main()
