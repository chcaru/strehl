"""Show the coloured speckles at 100%, so they can be judged as pictures.

speckle_vs_hotmap.py established what they are NOT (persistent hot pixels,
1.06x enrichment over chance -- i.e. chance). This crops the densest cluster of
COLOURED speckles at 1:1 and boosts, so the mechanism can be seen rather than
inferred. Colour is the discriminant: black foam has no coloured detail, so a
single-channel outlier on it cannot be the subject.

Renders side by side if given two images (e.g. demosaic on vs off).

usage:  python speckle_crop.py <a.tif> [b.tif] --out <png>
"""

import argparse

import numpy as np
import tifffile
from PIL import Image


def neighbour_max(a):
    p = np.pad(a, 1, mode="edge")
    out = np.full(a.shape, -np.inf, dtype=np.float32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            out = np.maximum(
                out, p[1 + dy : 1 + dy + a.shape[0], 1 + dx : 1 + dx + a.shape[1]]
            )
    return out


def coloured_speckles(img, excess_dn=250.0, colour_frac=0.35):
    """Isolated outliers where ONE channel is the outlier."""
    hits = np.zeros(img.shape[:2], dtype=bool)
    for c in range(3):
        a = img[:, :, c].astype(np.float32)
        hits |= (a - neighbour_max(a)) >= excess_dn
    v = img.astype(np.float32)
    mx = v.max(axis=2)
    mn = v.min(axis=2)
    coloured = (mx - mn) / np.maximum(mx, 1.0) > colour_frac
    return hits & coloured


def densest_tile(mask, tile):
    """Tile with the most hits. Coarse grid: we want a place to look, not an
    argmax. Choosing the tile by the defect means the crop cannot flatter."""
    H, W = mask.shape
    best, by, bx = -1, 0, 0
    step = tile // 2
    for y in range(0, H - tile, step):
        for x in range(0, W - tile, step):
            n = int(mask[y : y + tile, x : x + tile].sum())
            if n > best:
                best, by, bx = n, y, x
    return by, bx, best


def load(p):
    img = tifffile.imread(p)
    assert img.dtype == np.uint16, f"expected uint16, got {img.dtype}"
    assert img.ndim == 3 and img.shape[2] == 3, f"expected RGB, got {img.shape}"
    return img


def boost(crop, gain):
    return np.clip(crop.astype(np.float32) * gain / 257.0, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b", nargs="?")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tile", type=int, default=420)
    ap.add_argument("--gain", type=float, default=8.0)
    args = ap.parse_args()

    a = load(args.a)
    mask = coloured_speckles(a)
    y, x, n = densest_tile(mask, args.tile)
    print(f"coloured speckles total : {int(mask.sum())}")
    print(f"densest {args.tile}px tile  : ({x},{y}) with {n} of them")

    panels = [("A  " + args.a.rsplit("\\", 1)[-1], boost(a[y:y+args.tile, x:x+args.tile], args.gain))]
    if args.b:
        b = load(args.b)
        if b.shape[:2] != a.shape[:2]:
            # a non-demosaic render is half resolution; map the coords
            sy = b.shape[0] / a.shape[0]
            sx = b.shape[1] / a.shape[1]
            y2, x2 = int(y * sy), int(x * sx)
            t2 = max(8, int(args.tile * sy))
            crop = b[y2:y2+t2, x2:x2+t2]
            crop = np.array(
                Image.fromarray(boost(crop, args.gain)).resize(
                    (args.tile, args.tile), Image.NEAREST
                )
            )
            print(f"B is {b.shape[:2]} vs A {a.shape[:2]}; "
                  f"cropped at ({x2},{y2}) size {t2} and nearest-upscaled")
            panels.append(("B  " + args.b.rsplit("\\", 1)[-1] + "  (nearest x2)", crop))
        else:
            panels.append(("B  " + args.b.rsplit("\\", 1)[-1],
                           boost(b[y:y+args.tile, x:x+args.tile], args.gain)))

    pad = 6
    W = sum(p[1].shape[1] for p in panels) + pad * (len(panels) + 1)
    H = panels[0][1].shape[0] + pad * 2
    sheet = np.full((H, W, 3), 24, dtype=np.uint8)
    cx = pad
    for _, im in panels:
        sheet[pad:pad+im.shape[0], cx:cx+im.shape[1]] = im
        cx += im.shape[1] + pad
    Image.fromarray(sheet).save(args.out)
    print(f"wrote : {args.out}   (gain x{args.gain:g}, 1:1 pixels)")
    for name, _ in panels:
        print(f"        {name}")


if __name__ == "__main__":
    main()
