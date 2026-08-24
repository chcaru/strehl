"""Does the MERGE preserve the green detail that binning destroys?

At a G1 or G2 site the MHC demosaic writes `px[1] = known` -- green passes
through untouched (`demosaic.rs:218-231`). So a **linear** `--demosaic` render
(no `--srgb`, hence no colour matrix) carries the merged G1 and G2 estimates
verbatim in its green channel, and the same D instrument runs on it unchanged.

Statistic: rho = var(D) / var(S), the share of green variance in the component
`mean(G1,G2)` annihilates. It is a ratio of two quantities that carry the same
scale factor, so it is directly comparable between a raw frame and a normalised
render without knowing the normalisation.
"""

import json
import os
import sys

import numpy as np
import tifffile

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
REN = r"C:\dev\strehl-out\M95-resolution"
BLACK = 512.0
TILE = 384

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s1_measure import gradmag, planes, vard  # noqa: E402


def render_planes(green, by, bx, dy=0, dx=0):
    """Green channel of a full-res render -> the merged G1/G2 tile."""
    g1 = green[0::2, 1::2][by + dy:by + dy + TILE, bx + dx:bx + dx + TILE].astype(np.float64)
    g2 = green[1::2, 0::2][by + dy:by + dy + TILE, bx + dx:bx + dx + TILE].astype(np.float64)
    return 0.5 * (g1 + g2), 0.5 * (g1 - g2)


def find_offset(a, b, span=12):
    """Integer offset that best aligns b to a. Integer only: sub-pixel
    resampling would add blur to the very quantity being measured."""
    best, bo = -1e18, (0, 0)
    a0 = a - a.mean()
    for dy in range(-span, span + 1):
        for dx in range(-span, span + 1):
            bb = b[span + dy:b.shape[0] - span + dy, span + dx:b.shape[1] - span + dx]
            aa = a0[span:a.shape[0] - span, span:a.shape[1] - span]
            c = float((aa * (bb - bb.mean())).sum())
            if c > best:
                best, bo = c, (dy, dx)
    return bo


def main():
    z = np.load(os.path.join(OUT, "tiles.npz"))
    s1 = json.load(open(os.path.join(OUT, "s1_measure.json"), encoding="utf-8"))
    meta = json.load(open(os.path.join(OUT, "tiles_meta.json"), encoding="utf-8"))
    tiles = meta["tiles"]

    res = {}
    for tag in ("demo-noalign", "demo-align"):
        p = os.path.join(REN, tag + ".tif")
        if not os.path.exists(p):
            print("SKIP %s (not rendered yet)" % tag)
            continue
        img = tifffile.imread(p)
        green = img[:, :, 1]
        print("\n== %s == %s" % (tag, img.shape))
        res[tag] = {}
        for key, (by, bx) in tiles.items():
            i = s1["tiles"][key]["sharp"]["i"]
            s_raw, d_raw = planes(z[key][i])
            # Register the render tile to the raw tile with an integer shift.
            probe_s, _ = render_planes(green, by, bx)
            dy, dx = find_offset(s_raw, probe_s)
            s_r, d_r = render_planes(green, by, bx, dy, dx)
            rho_raw = vard(d_raw) / float(np.var(s_raw))
            rho_ren = vard(d_r) / float(np.var(s_r))
            res[tag][key] = {
                "offset": [dy, dx],
                "rho_raw": rho_raw, "rho_render": rho_ren,
                "keep": rho_ren / rho_raw,
                "grad_raw": gradmag(s_raw), "grad_render": gradmag(s_r),
                "vard_raw": vard(d_raw), "vard_render": vard(d_r),
                "vars_raw": float(np.var(s_raw)), "vars_render": float(np.var(s_r)),
            }
            print("   %s off (%+d,%+d)  rho raw %.5f  render %.5f   kept %.3f"
                  % (key, dy, dx, rho_raw, rho_ren, rho_ren / rho_raw))

    with open(os.path.join(OUT, "s3_merge.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
