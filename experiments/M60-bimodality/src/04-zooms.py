"""M60 step 4 — full-resolution zooms of candidate regions, for hand labelling.

Green sublattice is 2344 x 3514 (rows x cols). Coordinates below are in that space.
Nothing here reads the focus volume: the frames are shown as captured.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.abspath(os.path.join(HERE, "..", "fig"))

# (name, y0, y1, x0, x1) in green-sublattice coordinates
REGIONS = [
    ("A-antenna-head", 1000, 1900, 2300, 3050),
    ("B-eye-antenna", 1350, 2050, 1850, 2600),
    ("C-leg-body", 1050, 1850, 1150, 2050),
    ("D-wing-thorax", 100, 800, 500, 1600),
    ("E-leg-bg", 1150, 2050, 150, 1050),
    ("F-legs-lower", 1500, 2300, 700, 1800),
]


def render_strip(stack, region, ks, out):
    from PIL import Image
    name, y0, y1, x0, x1 = region
    tiles = []
    fs = L.frames(stack)
    for k in ks:
        g = L.load_green(fs[k], (y0, y1, x0, x1))
        tiles.append(g)
    allv = np.concatenate([t.ravel() for t in tiles])
    lo, hi = 0.0, float(np.percentile(allv, 99.7))
    imgs = []
    for g in tiles:
        v = np.clip((g - lo) / max(hi - lo, 1e-6), 0, 1) ** (1 / 2.2)
        imgs.append((v * 255).astype(np.uint8))
    sep = np.full((imgs[0].shape[0], 6), 255, np.uint8)
    strip = imgs[0]
    for im in imgs[1:]:
        strip = np.concatenate([strip, sep, im], axis=1)
    Image.fromarray(strip).save(out)
    return strip.shape


if __name__ == "__main__":
    ks = [int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])] if len(sys.argv) > 3 else [60, 104, 194]
    stack = sys.argv[4] if len(sys.argv) > 4 else "bee-3"
    for r in REGIONS:
        out = os.path.join(FIG, "04-%s-%s-k%s.png" % (stack, r[0], "-".join(str(k) for k in ks)))
        sh = render_strip(stack, r, ks, out)
        print("wrote %s  %s" % (out, sh))
