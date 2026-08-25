"""Rule 7: go and look at the blue fringe before recommending a coefficient.

Section 19.1 asks for one literal in optics.rs on the strength of a chroma
statistic. The standing rule for this build phase is that if the pictures and the
number disagree, the pictures are right -- so the number does not get to stand
unless someone has looked. This crops the worst-blue-fringe neighbourhood out of
the corner of the off render and the blue-corrected render and writes them side
by side, magnified, with no annotation.

WHERE IT LOOKS. Lateral CA is zero on axis and grows with radius, so the crop is
chosen in the outer field: among tiles in the top decile of luma gradient beyond
0.75 of the corner radius, the one with the highest blue-minus-green chroma. That
is where the effect must be if it is real, and choosing the location by GREEN
gradient and B-G chroma on the OFF arm keeps the choice independent of whether
the correction helps.

WHAT WOULD FALSIFY THE RECOMMENDATION. A blue-magenta fringe on one side of a
structure and yellow on the other in the off crop, visibly reduced in the
corrected crop, confirms it. If the off crop shows no blue fringe at all, or if
the corrected crop looks the same or worse, section 19.1 is wrong and the chroma
statistic was measuring something else.
"""

import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import sobel, uniform_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import c3_chroma as c3

CROP = 110          # plane px of the crop window
ZOOM = 6


def to_srgb8(a):
    """Linear-sRGB float -> 8-bit sRGB, for LOOKING at only."""
    x = np.clip(a, 0, 1)
    y = np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055)
    return (y * 255 + 0.5).astype(np.uint8)


def main():
    stack = sys.argv[1] if len(sys.argv) > 1 else "coffee-bean"
    off = c3.read16(os.path.join(c3.REND, f"{stack}-off.tif")).astype(np.float32)

    with open(os.path.join(common.OUT, "json",
                           f"c1_lateral_{stack}.json")) as fh:
        import json
        h = json.load(fh)["headline"]
    eps_b = h["B"]["eps_null_corrected"]
    fixed = c3.apply_eps(off, 0.0, eps_b)

    a = off / max(off.max(), 1.0)
    g = c3.LUMA[0] * a[:, :, 0] + c3.LUMA[1] * a[:, :, 1] + c3.LUMA[2] * a[:, :, 2]
    grad = np.hypot(sobel(g, 0, mode="nearest"), sobel(g, 1, mode="nearest"))

    # Blue-minus-green excursion, as a local swing rather than a local mean: a
    # fringe is a SIGNED alternation across a structure, so the thing to find is
    # where B-G varies most, not where it is largest.
    bg = (a[:, :, 2] - a[:, :, 1])
    sw = uniform_filter(bg.astype(np.float32) ** 2, 9) - \
        uniform_filter(bg.astype(np.float32), 9) ** 2

    h_, w_ = g.shape
    yy, xx = np.mgrid[0:h_, 0:w_]
    r = np.hypot(yy - (h_ - 1) / 2, xx - (w_ - 1) / 2)
    rmax = r.max()

    score = np.where((r > 0.75 * rmax) &
                     (grad > np.quantile(grad, 0.90)), sw, 0.0)
    score[:CROP, :] = 0; score[-CROP:, :] = 0
    score[:, :CROP] = 0; score[:, -CROP:] = 0
    cy, cx = np.unravel_index(np.argmax(score), score.shape)
    print(f"{stack}: crop centred at (y={cy}, x={cx}), "
          f"r={r[cy,cx]:.0f} = {r[cy,cx]/rmax:.2f} of corner")
    print(f"  eps_b applied {eps_b*1e6:+.1f} ppm  -> corner shift "
          f"{abs(eps_b)*2112:.2f} plane px, here {abs(eps_b)*r[cy,cx]:.2f} px")

    s = (slice(cy - CROP // 2, cy + CROP // 2),
         slice(cx - CROP // 2, cx + CROP // 2))
    # One shared exposure for both panels, from the off arm, so the only
    # difference a reader can see is the correction.
    k = 0.9 / max(np.quantile(off[s][:, :, 1], 0.999) / 65535.0, 1e-6)
    panels = [to_srgb8(off[s] / 65535.0 * k), to_srgb8(fixed[s] / 65535.0 * k)]
    panels = [np.repeat(np.repeat(p, ZOOM, 0), ZOOM, 1) for p in panels]
    gap = np.full((panels[0].shape[0], 8, 3), 255, np.uint8)
    outimg = np.concatenate([panels[0], gap, panels[1]], axis=1)

    d = os.path.join(common.OUT, "look")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, f"blue_{stack}.png")
    tifffile.imwrite(p.replace(".png", ".tif"), outimg)
    try:
        from PIL import Image
        Image.fromarray(outimg).save(p)   # 8-bit RGB: PIL is safe here (rule 1
        #                                   forbids PIL for 16-bit TIFF READS)
        print(f"  wrote {p}")
    except ImportError:
        print(f"  wrote {p.replace('.png', '.tif')}")

    # The number that goes with the picture.
    for name, img in (("off", off[s]), ("blue-corrected", fixed[s])):
        c = c3.chroma(img)
        bgl = (img[:, :, 2] - img[:, :, 1]) / np.maximum(img[:, :, 1], 1)
        print(f"  {name:>15}  mean chroma {c.mean():.4f}   "
              f"B-G swing sd {bgl.std():.4f}")


if __name__ == "__main__":
    main()
