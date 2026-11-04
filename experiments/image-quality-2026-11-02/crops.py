"""Side-by-side native crops of two or more renders with one display transform.

usage: crops.py OUT_PREFIX y x size A.tif B.tif [C.tif ...]
       crops.py OUT_PREFIX overview A.tif

Each crop is copied 1:1 from the 16-bit sRGB TIFFs, converted to 8 bit by the
same >> 8 for every arm, and nearest-neighbour enlarged by an integer factor so
no resampling filter can soften or sharpen one arm relative to the other.
"""
import sys
import numpy as np
import tifffile
from PIL import Image


def main():
    out = sys.argv[1]
    if sys.argv[2] == "overview":
        a = tifffile.imread(sys.argv[3])
        h, w, _ = a.shape
        step = max(1, w // 1600)
        small = (a[::step, ::step] >> 8).astype(np.uint8)
        Image.fromarray(small).save(out + "-overview.png")
        print(f"overview step {step}: {small.shape}")
        return
    y, x, size = (int(v) for v in sys.argv[2:5])
    paths = sys.argv[5:]
    zoom = max(1, 512 // size)
    tiles = []
    for p in paths:
        a = tifffile.imread(p)[y:y + size, x:x + size]
        t = (a >> 8).astype(np.uint8)
        t = np.repeat(np.repeat(t, zoom, 0), zoom, 1)
        tiles.append(t)
        tiles.append(np.full((t.shape[0], 6, 3), 255, np.uint8))
    Image.fromarray(np.concatenate(tiles[:-1], 1)).save(f"{out}-{y}-{x}-{size}.png")
    print(f"crop origin ({y},{x}) size {size} zoom {zoom}x nearest -> {out}-{y}-{x}-{size}.png")


if __name__ == "__main__":
    main()
