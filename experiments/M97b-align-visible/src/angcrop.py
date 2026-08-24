"""Full-resolution crops of the angled ruler, both arms, for looking at.

Co-location is legitimate here because both arms come from the same
fit_to_cover scale (STREHL_ALIGN=zoom discards registration but keeps FOV), and
angthumb.py asserted identical shapes. Discipline 606 bans fixed-coordinate
comparison only across arms whose field of view differs, which is ALIGN=0.

Usage: angcrop.py            -- writes the default survey
"""

import sys

import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

OUT = r"C:\dev\strehl-out\M97"
ARMS = {"A": rf"{OUT}\angruler-ALIGNED.tif", "Z": rf"{OUT}\angruler-ZOOMNULL.tif"}

# (name, x0, y0, size) in full-resolution pixels, read off the 1/8 thumbnail.
BOXES = [
    ("leftedge-hi", 3040, 640, 640),
    ("leftedge-lo", 3040, 2880, 640),
    ("rightedge", 4560, 960, 640),
    ("ticks", 3680, 2560, 640),
]


def luma(a):
    return a.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])


def main():
    imgs = {k: luma(tifffile.imread(v)) for k, v in ARMS.items()}
    for name, x0, y0, n in BOXES:
        pair = []
        for k in ("A", "Z"):
            c = imgs[k][y0 : y0 + n, x0 : x0 + n]
            pair.append(c)
        lo = min(np.percentile(c, 0.5) for c in pair)
        hi = max(np.percentile(c, 99.5) for c in pair)
        strip = np.concatenate([pair[0], np.full((n, 12), hi), pair[1]], axis=1)
        v = np.clip((strip - lo) / max(hi - lo, 1e-9), 0, 1)
        p = rf"{OUT}\angcrop-{name}.png"
        Image.fromarray((v * 255).astype(np.uint8)).save(p)
        d = np.abs(pair[0] - pair[1])
        print(f"{name:12s} x={x0} y={y0}  |A-Z| mean={d.mean():7.1f} p99={np.percentile(d, 99):8.1f}")
    print("wrote angcrop-*.png  (left half ALIGNED, right half ZOOMNULL)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
