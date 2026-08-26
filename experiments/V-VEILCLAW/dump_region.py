"""Dump a master-coordinate region from N raw frames AND from the master TIFF,
all under ONE shared display curve, so they can be compared honestly.

Usage:
  python dump_region.py --win y0 y1 x0 x1 --frames 1,40,80 --outdir DIR [--tag NAME]

Master coords are full-res. Raw green lattice is half-res in both axes, so the
region is sampled at y0//2:y1//2, x0//2:x1//2 of raw_image_visible[0::2, 1::2]
and then nearest-upsampled 2x for display, keeping raw and master the same size.
"""
import argparse
import pathlib

import numpy as np
import rawpy
import tifffile
from PIL import Image, ImageDraw

RAWDIR = pathlib.Path(r"D:\personal\macro\bee-3-cpl")
MASTER = pathlib.Path(r"C:\dev\strehl-out\SHIP-V1\bee-3-cpl.tiff")


def raw_green(path):
    with rawpy.imread(str(path)) as r:
        return r.raw_image_visible[0::2, 1::2].astype(np.float32)


def grade(a, lo, hi):
    x = np.clip((a - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return (np.power(x, 1.0 / 2.2) * 255.0).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--win", nargs=4, type=int, required=True)
    ap.add_argument("--frames", required=True, help="comma list, or a:b:step")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--tile", type=int, default=440)
    ap.add_argument("--singles", action="store_true", help="also write per-frame PNGs")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--tag", default="win")
    ap.add_argument("--no-master", action="store_true")
    a = ap.parse_args()

    y0, y1, x0, x1 = a.win
    if ":" in a.frames:
        b, e, s = (int(v) for v in a.frames.split(":"))
        idxs = list(range(b, e, s))
    else:
        idxs = [int(v) for v in a.frames.split(",")]
    out = pathlib.Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)

    files = sorted(RAWDIR.glob("*.ARW"))
    print(f"{len(files)} raws; window master y[{y0}:{y1}] x[{x0}:{x1}]")

    crops = {}
    for i in idxs:
        g = raw_green(files[i])
        c = g[y0 // 2:y1 // 2, x0 // 2:x1 // 2]
        crops[f"f{i:03d}_{files[i].stem}"] = np.repeat(np.repeat(c, 2, 0), 2, 1)

    mst = None
    if not a.no_master:
        m = tifffile.imread(str(MASTER))
        mst = m[y0:y1, x0:x1, 1].astype(np.float32)

    # one shared curve over the raw crops (16-bit linear, same sensor scale)
    allpx = np.concatenate([c.ravel() for c in crops.values()])
    lo, hi = np.percentile(allpx, [1.0, 99.7])
    print(f"raw display curve: lo={lo:.0f} hi={hi:.0f}")
    if a.singles:
        for k, c in crops.items():
            Image.fromarray(grade(c, lo, hi)).save(out / f"{a.tag}--{k}.png")

    if mst is not None:
        mlo, mhi = np.percentile(mst, [1.0, 99.7])
        print(f"master display curve: lo={mlo:.0f} hi={mhi:.0f}")
        Image.fromarray(grade(mst, mlo, mhi)).save(out / f"{a.tag}--MASTER.png")

    # contact sheet of the raw frames under the shared curve
    keys = sorted(crops)
    h, w = crops[keys[0]].shape
    cols = min(a.cols, len(keys))
    rows = (len(keys) + cols - 1) // cols
    sc = max(1, int(np.ceil(max(h, w) / a.tile)))
    th, tw = h // sc, w // sc
    sheet = np.full((rows * th, cols * tw), 255, np.uint8)
    for n, k in enumerate(keys):
        img = grade(crops[k], lo, hi)[::sc, ::sc][:th, :tw]
        r, c = divmod(n, cols)
        sheet[r * th:r * th + img.shape[0], c * tw:c * tw + img.shape[1]] = img
    sh = Image.fromarray(sheet).convert("RGB")
    d = ImageDraw.Draw(sh)
    for n, k in enumerate(keys):
        r, c = divmod(n, cols)
        d.rectangle([c * tw, r * th, c * tw + tw - 1, r * th + th - 1], outline=(255, 0, 0))
        d.text((c * tw + 6, r * th + 6), k.split("_")[0], fill=(255, 0, 0))
    sh.save(out / f"{a.tag}--SHEET.png")
    print(f"wrote {len(keys)} crops + sheet to {out}")


if __name__ == "__main__":
    main()
