"""geomwide.py -- is the comparator a CROP of strehl's field, or a DOWNSCALE
of the whole of it?

geomcrop.py assumes -C cropped: it takes the coarse offset from the difference
in raster shapes and sweeps scale over +-6%.  On `bee-1-cpl` that fit failed --
median tile peak 0.06-0.10 against 0.6274 on a planted transform and 0.7686 on
`119MSDCF`, a sweep running to the edge of its range, and two different scales
(1.0510, 1.0560) for two comparators that share a raster by construction.

Before recording "geometry undeterminable" there is a rival hypothesis that
the crop assumption cannot see, and it is suggested by the rasters themselves:

    strehl     7032 x 4688
    comparator 6200 x 4120        7032/6200 = 1.1342,  4688/4120 = 1.1379

Two ratios that agree to 0.3% is what a UNIFORM RESAMPLE looks like.  A crop
has no reason to preserve the aspect ratio at all.  If the comparator is the
whole field at 88% linear scale rather than 88% of the field at full scale,
then the correct offset is ~0 and the correct scale is ~1.134 -- outside every
sweep tried so far, so both fits would fail exactly as observed.

The two hypotheses make OPPOSITE, cheap predictions, which is why this is
worth a run rather than an argument:

    CROP      offset ~ (280, 416) px, scale ~ 1.00, and the wide sweep finds
              nothing better than what geomcrop already reported
    DOWNSCALE offset ~ (0, 0), scale ~ 1.134, and the tile peak JUMPS to the
              0.6-0.8 range that a real geometry match produces here

Usage:  python geomwide.py <key>
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import geom                                                       # noqa: E402
from geomcrop import ROOT, D, COMPARATORS, fit_tiles              # noqa: E402


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    key = sys.argv[1]
    arm = os.path.join(ROOT, key, "arms")
    S = geom.block_mean(geom.load_grey(os.path.join(arm, "strehl-A.tiff")), D)

    for k, (fn, _label) in COMPARATORS.items():
        cp = os.path.join(arm, fn)
        if not os.path.exists(cp):
            continue
        C = geom.block_mean(geom.load_grey(cp), D)
        ry = S.shape[0] / C.shape[0]
        rx = S.shape[1] / C.shape[1]
        print("=" * 92)
        print(f"{key} / {k}:  strehl {S.shape[1] * D}x{S.shape[0] * D}  "
              f"comparator {C.shape[1] * D}x{C.shape[0] * D}")
        print(f"  raster ratios  y {ry:.4f}  x {rx:.4f}  "
              f"(agree to {abs(ry - rx) / rx * 100:.2f}% -> "
              f"{'consistent with a uniform resample' if abs(ry - rx) / rx < 0.01 else 'not a uniform resample'})")

        oy = (S.shape[0] - C.shape[0]) // 2
        ox = (S.shape[1] - C.shape[1]) // 2
        print(f"\n  H1 CROP      offset ({oy * D}, {ox * D}) px, scale swept 0.98-1.06")
        s1, p1, i1, _, _, _ = fit_tiles(S, C, np.arange(0.98, 1.0601, 0.01),
                                        oy, ox, verbose=False)
        print(f"    best scale {s1:.4f}  median tile peak {p1:.4f}")

        print(f"\n  H2 DOWNSCALE offset (0, 0) px, scale swept 1.05-1.22")
        s2, p2, i2, dy2, dx2, sweep = fit_tiles(S, C, np.arange(1.05, 1.2201, 0.01),
                                                0, 0, verbose=False)
        for s, p, ddy, ddx in sweep:
            mark = "  <== best" if abs(s - s2) < 1e-9 else ""
            print(f"    scale {s:.4f}: median tile peak {p:.4f}  "
                  f"residual dy {ddy * D:+5d} dx {ddx * D:+5d} px{mark}")
        print(f"    best scale {s2:.4f}  median tile peak {p2:.4f}  "
              f"interior={i2}  residual dy {dy2:+d} dx {dx2:+d} px")

        win = "H2 DOWNSCALE" if p2 > p1 else "H1 CROP"
        print(f"\n  --> {win} wins: {max(p1, p2):.4f} vs {min(p1, p2):.4f} "
              f"({max(p1, p2) / max(min(p1, p2), 1e-9):.1f}x)")
        print(f"      reference scale for a REAL match on this corpus: "
              f"0.6274 (planted) / 0.7686 (119MSDCF).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
