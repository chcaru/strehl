r"""Measure the mean_coarse dose-response on one subject.

Every arm is the SEALED SHIP-V4 PIN with one environment variable differing.
Windows are pinned on the mc=0 arm -- which reproduces the shipped master's
merge exactly -- and reused for every other arm, so all arms are scored on
identical pixels.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mottle import (N_TILES, commission, load_lum, measure, boot_ratio,  # noqa: E402
                    pick_detail_tiles, pick_tiles)

BASE = r"C:\dev\strehl-out\V-H2H2\mottle"


def main(argv):
    subject = argv[0]
    levels = [int(v) for v in argv[1:]] or [0, 1, 2, 3]
    rng = np.random.default_rng(20260827)

    print("=" * 100)
    print("SUBJECT %s   mean_coarse dose-response" % subject)
    print("=" * 100)

    ref_path = os.path.join(BASE, "%s--mc%d.tiff" % (subject, levels[0]))
    ref, latt = load_lum(ref_path)
    print("  reference arm mc=%d   lattice %dx%d (READ FROM THE FILE)" % (levels[0], latt[0], latt[1]))

    tiles = pick_tiles(ref, N_TILES)
    dtiles = pick_detail_tiles(ref, N_TILES)
    print("  %d flattest and %d most-textured 900x900 tiles pinned on the reference," % (len(tiles), len(dtiles)))
    print("  reused unchanged for every arm.")
    print("    flat  : %s ..." % ", ".join("(%d,%d)" % t for t in tiles[:5]))
    print("    detail: %s ..." % ", ".join("(%d,%d)" % t for t in dtiles[:5]))
    print()

    ok, verdicts, _ = commission(ref, tiles, dtiles, rng)
    print()
    print("  COMMISSIONED: %s" % ok)
    if not ok:
        print("  REFUSING to report a dose-response on an uncommissioned instrument.")
        return 1
    print()

    base_f = measure(ref, tiles)
    base_d = measure(ref, dtiles)
    print("  ABSOLUTE terms on the reference arm (median over tiles)")
    print("    flat  : blotch %.6f   noise %.6f   sharp %.6f" % tuple(np.median(base_f, axis=0)))
    print("    detail: blotch %.6f   noise %.6f   sharp %.6f" % tuple(np.median(base_d, axis=0)))
    print()
    print("  RATIO TO mc=%d, paired over the same tiles. LOW blotch is GOOD." % levels[0])
    print("  A fall in sharp(flat) or in blotch(detail) alongside it means the image was")
    print("  SOFTENED, not repaired -- that is the cheat the suite is commissioned to catch.")
    print("    %-6s %-21s %-21s %-21s %s"
          % ("arm", "blotch(flat)", "noise(flat)", "sharp(flat)", "blotch(detail)"))
    for mc in levels:
        p = os.path.join(BASE, "%s--mc%d.tiff" % (subject, mc))
        if not os.path.exists(p):
            print("    mc=%-3d  MISSING" % mc)
            continue
        lum, _ = load_lum(p, expect=latt)
        cf = measure(lum, tiles)
        cd = measure(lum, dtiles)
        c = ["%.4f [%.4f,%.4f]" % boot_ratio(base_f[:, i], cf[:, i], rng) for i in range(3)]
        d0 = "%.4f [%.4f,%.4f]" % boot_ratio(base_d[:, 0], cd[:, 0], rng)
        print("    mc=%-3d %-21s %-21s %-21s %s" % (mc, c[0], c[1], c[2], d0))
        del lum
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
