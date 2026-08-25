"""Draw the frozen silhouette on the picture, so the profile can be believed.

A radial profile is meaningless if the mask's boundary is not where you think
it is.  This build has already been bitten twice by exactly that: a mask cannot
exclude what its own input has already mislabelled.  If the segmentation
swallows the bright rim, then "distance 0" is the OUTER edge of the halo rather
than the silhouette, and every number in the profile is displaced by the width
of the thing being measured.

So: render the mask boundary as a 1 px contour over the developed image and
LOOK.  If the pictures and the number disagree, the pictures are right.
"""

import argparse
import pathlib

import numpy as np
import tifffile
from PIL import Image

import radial


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="the arm the mask is built from")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gain", type=float, default=3.0)
    ap.add_argument("--width", type=int, default=1400)
    args = ap.parse_args()

    a = tifffile.imread(args.src)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    luma = radial.read_linear(pathlib.Path(args.src))
    mask, bg, sd = radial.subject_mask(luma)
    print(f"subject {100*mask.mean():.2f}% of plane, backdrop {bg:.1f} DN, sd {sd:.2f} DN")

    # 1 px contour: a mask pixel with a background 4-neighbour.
    from scipy import ndimage
    edge = mask & ~ndimage.binary_erosion(mask, np.ones((3, 3)))
    # Thicken so it survives the downsample to viewing size.
    edge = ndimage.binary_dilation(edge, np.ones((5, 5)))

    rgb = a.astype(np.float32) / 65535.0 * args.gain
    rgb = np.clip(rgb, 0.0, 1.0)
    # sRGB transfer, for looking at only.
    srgb = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * rgb ** (1 / 2.4) - 0.055)
    srgb[edge] = [1.0, 0.0, 0.0]

    img = Image.fromarray((srgb * 255 + 0.5).astype(np.uint8), "RGB")
    h = round(img.height * args.width / img.width)
    img = img.resize((args.width, h), Image.LANCZOS)
    out = pathlib.Path(args.out)
    img.save(out)
    assert out.read_bytes()[:4] == b"\x89PNG", f"{out} is not a PNG"
    print(f"wrote {out}  {args.width}x{h}  (red contour = the frozen silhouette)")


if __name__ == "__main__":
    main()
