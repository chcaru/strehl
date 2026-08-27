"""Side-by-side 100% crops of two masters at the places a defect would show.

Not an instrument. Every number in this project is measured elsewhere by a
commissioned gauge; this exists because the owner's acceptance test is
"print worthy", which is an eye test, and an eye test needs pixels at 1:1
rather than a downsampled thumbnail that hides exactly the 20-60 px mottle
plateaus and edge rims under question.

Sites are chosen by local gradient on the FIRST image and reused verbatim on
the second, so the two panels are the same pixels of the same scene. Choosing
sites per image would compare a defect in one against a different location in
the other, which is the visual equivalent of an unmatched population.

Usage:
    python crop_ab.py A.tiff B.tiff out_dir [--label-a ...] [--label-b ...]
                      [--size 480] [--sites 6]
"""
import argparse
import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None


def to_u8(a):
    if a.dtype == np.uint16:
        return (a // 257).astype(np.uint8)
    if a.dtype == np.uint8:
        return a
    return (np.clip(a, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def load(p):
    a = tifffile.imread(p)
    if a.ndim == 2:
        a = np.dstack([a] * 3)
    return a[:, :, :3]


def pick_sites(gray, size, n):
    """Highest-gradient, spatially separated sites.

    Greedy with exclusion rather than top-n: the top-n of a gradient map are
    all neighbours of one another on a single strong edge, which would produce
    six views of the same defect and call it six samples.
    """
    gy, gx = np.gradient(gray.astype(np.float32))
    mag = np.abs(gx) + np.abs(gy)
    h, w = mag.shape
    step = size
    # Block-reduce to candidate cells so the search is cheap and each cell is
    # already a crop-sized region.
    bh, bw = h // step, w // step
    if bh < 2 or bw < 2:
        return [(max(0, (h - size) // 2), max(0, (w - size) // 2))]
    cells = mag[: bh * step, : bw * step].reshape(bh, step, bw, step).mean(axis=(1, 3))
    order = np.argsort(cells, axis=None)[::-1]
    taken, sites = [], []
    for idx in order:
        r, c = divmod(int(idx), bw)
        if any(abs(r - rr) < 2 and abs(c - cc) < 2 for rr, cc in taken):
            continue
        taken.append((r, c))
        sites.append((r * step, c * step))
        if len(sites) >= n:
            break
    return sites


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("out")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--size", type=int, default=480)
    ap.add_argument("--sites", type=int, default=6)
    args = ap.parse_args()

    A, B = load(args.a), load(args.b)
    if A.shape != B.shape:
        raise SystemExit("shape mismatch %s vs %s -- not the same scene" % (A.shape, B.shape))
    os.makedirs(args.out, exist_ok=True)

    gray = A.astype(np.float32).mean(axis=2)
    sites = pick_sites(gray, args.size, args.sites)

    s = args.size
    pad, hdr = 10, 20
    for i, (y, x) in enumerate(sites, 1):
        ca = Image.fromarray(to_u8(A[y : y + s, x : x + s]), "RGB")
        cb = Image.fromarray(to_u8(B[y : y + s, x : x + s]), "RGB")
        canvas = Image.new("RGB", (2 * s + 3 * pad, s + hdr + 2 * pad), (20, 20, 20))
        canvas.paste(ca, (pad, hdr + pad))
        canvas.paste(cb, (2 * pad + s, hdr + pad))
        d = ImageDraw.Draw(canvas)
        d.text((pad, 5), "%s   @ (%d,%d) 1:1" % (args.label_a, x, y), fill=(230, 230, 230))
        d.text((2 * pad + s, 5), "%s   @ (%d,%d) 1:1" % (args.label_b, x, y), fill=(230, 230, 230))
        p = os.path.join(args.out, "crop%02d_y%d_x%d.jpg" % (i, y, x))
        canvas.save(p, "JPEG", quality=95, subsampling=0)
        # Mean absolute difference over the crop, in 16-bit DN, so a visually
        # identical pair is not silently presented as a comparison.
        dn = float(np.abs(A[y : y + s, x : x + s].astype(np.int32)
                          - B[y : y + s, x : x + s].astype(np.int32)).mean())
        print("%s  mean|delta| = %.2f DN" % (p, dn), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
