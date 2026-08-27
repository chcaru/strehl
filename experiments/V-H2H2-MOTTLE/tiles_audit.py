r"""Interrogate the tiles the dose-response was scored on, and the band count.

Two ways this experiment could be reporting numbers for pixels that are not
image: a warp border (near-black, so `band/mean` explodes on a tiny denominator)
and a tile that is uniform fill (no content at all). Both produce well-formed
numbers. This asks for the evidence rather than assuming.
"""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mottle import N_TILES, TILE, load_lum, pick_detail_tiles, pick_tiles, terms  # noqa: E402

BASE = r"C:\dev\strehl-out\V-H2H2\mottle"


def main(argv):
    subject = argv[0] if argv else "coffee-bubbles"
    ref, latt = load_lum(os.path.join(BASE, "%s--mc0.tiff" % subject))
    gmean = float(np.mean(ref))
    print("subject %s   lattice %dx%d   global mean %.1f DN" % (subject, latt[0], latt[1], gmean))
    print()
    for label, tiles in (("FLAT", pick_tiles(ref, N_TILES)),
                         ("DETAIL", pick_detail_tiles(ref, N_TILES))):
        print("%s tiles" % label)
        print("  %-14s %10s %10s %10s %10s %8s" % ("origin", "mean", "min", "max", "std", "blotch"))
        bad = 0
        for (y, x) in tiles:
            blk = ref[y:y + TILE, x:x + TILE]
            m = float(np.mean(blk))
            b = terms(blk)[0]
            flag = ""
            if m < 0.02 * gmean:
                flag, bad = "  <-- NEAR-BLACK", bad + 1
            if float(np.std(blk)) < 1e-6:
                flag, bad = "  <-- UNIFORM FILL", bad + 1
            print("  (%5d,%5d) %10.1f %10.1f %10.1f %10.1f %8.4f%s"
                  % (y, x, m, float(np.min(blk)), float(np.max(blk)),
                     float(np.std(blk)), b, flag))
        print("  degenerate tiles: %d of %d" % (bad, len(tiles)))
        if bad:
            print("  REFUSED: a tile that is not image cannot carry a measurement.")
            return 1
        print()

    print("BAND COUNT, read from each arm's own render log (not inferred):")
    pat = re.compile(r"(?i)(band|level|octave|pyramid)[^\n]*?(\d+)")
    for mc in (0, 8, 16):
        p = os.path.join(BASE, "%s--mc%d.log" % (subject, mc))
        if not os.path.exists(p):
            continue
        txt = open(p, "r", encoding="utf-8", errors="replace").read()
        hits = [ln.strip() for ln in txt.splitlines()
                if re.search(r"(?i)\b(bands?|levels?|octaves?|mean_coarse|pyramid)\b", ln)]
        print("  mc=%-3d %s" % (mc, hits[:4] if hits else "(no band line in log)"))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
