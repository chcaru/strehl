"""Native-resolution, no-resize tiles used to freeze visual site predicates.

This script never computes theta.  It exposes the pixels used for the
content-only selection in PREREGISTRATION §5.4.  Every output panel is at most
400 pixels in either dimension and no source pixel is resized.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import rawpy
import tifffile
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from veil2lib import Similarity, parse_warpmap  # noqa: E402


def grade(a: np.ndarray, lo: float, hi: float) -> np.ndarray:
    x = np.clip((a.astype(np.float32) - lo) / max(hi - lo, 1e-9), 0, 1)
    return np.asarray(np.sqrt(x) * 255.0, dtype=np.uint8)


def master_tiles(master: Path, out: Path, tile: int = 400) -> None:
    a = tifffile.imread(str(master))
    if a.dtype != np.uint16 or a.ndim != 3 or a.shape[2] != 3:
        raise SystemExit(f"unexpected master {a.shape} {a.dtype}")
    g = a[:, :, 1]
    lo, hi = (float(v) for v in np.percentile(g, [0.5, 99.5]))
    out.mkdir(parents=True, exist_ok=True)
    for y in range(0, g.shape[0], tile):
        for x in range(0, g.shape[1], tile):
            z = grade(g[y:min(y + tile, g.shape[0]), x:min(x + tile, g.shape[1])], lo, hi)
            im = Image.fromarray(z).convert("RGB")
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, min(155, im.width - 1), 18], fill=(0, 0, 0))
            d.text((4, 3), f"y={y} x={x} {z.shape[0]}x{z.shape[1]}", fill=(255, 80, 80))
            im.save(out / f"tile-y{y:04d}-x{x:04d}.png")
    print(f"{math.ceil(g.shape[0]/tile) * math.ceil(g.shape[1]/tile)} native tiles -> {out}")


def raw_green(path: Path) -> np.ndarray:
    with rawpy.imread(str(path)) as r:
        v = r.raw_image_visible.astype(np.float32)
        black = float(np.mean(r.black_level_per_channel))
    # Match the merge's two green planes at the binned coordinate without
    # touching either adjacent red or blue sample.
    return 0.5 * (v[0::2, 1::2] + v[1::2, 0::2]) - black


def crop_map(
    src: np.ndarray,
    t: Similarity,
    roi: tuple[int, int, int, int],
) -> np.ndarray:
    y0, y1, x0, x1 = roi
    yy, xx = np.indices((y1 - y0, x1 - x0), dtype=np.float32)
    xx += np.float32(x0)
    yy += np.float32(y0)
    h, w = src.shape
    cx, cy = np.float32(w * 0.5), np.float32(h * 0.5)
    xr, yr = xx - cx, yy - cy
    mx = t.a_re * xr - t.a_im * yr + t.b_re + cx
    my = t.a_im * xr + t.a_re * yr + t.b_im + cy
    return cv2.remap(
        src,
        mx,
        my,
        cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def frame_sheets(
    rawdir: Path,
    warpmap: Path,
    roi: tuple[int, int, int, int],
    coverage: float,
    step: int,
    out: Path,
) -> None:
    meta, warps = parse_warpmap(warpmap)
    files = sorted(rawdir.glob("*.ARW"))
    idxs = list(range(0, len(files), step))
    crops = []
    for i in idxs:
        g = raw_green(files[i])
        crops.append(crop_map(g, warps[i].fitted(coverage), roi))
        print(f"decoded {i:03d}", flush=True)
    allpx = np.concatenate([z.ravel() for z in crops])
    lo, hi = (float(v) for v in np.percentile(allpx, [0.5, 99.5]))
    h, w = crops[0].shape
    if h > 96 or w > 96:
        raise SystemExit("site sheets require <=96x96 native ROIs")
    cols, rows = 4, 4
    out.mkdir(parents=True, exist_ok=True)
    for page, start in enumerate(range(0, len(crops), cols * rows)):
        canvas = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
        d = ImageDraw.Draw(canvas)
        for j, z in enumerate(crops[start:start + cols * rows]):
            r, c = divmod(j, cols)
            q = Image.fromarray(grade(z, lo, hi)).convert("RGB")
            canvas.paste(q, (c * w, r * h))
            d.rectangle([c * w, r * h, c * w + 42, r * h + 14], fill=(0, 0, 0))
            d.text((c * w + 2, r * h + 1), f"f{idxs[start+j]:03d}", fill=(255, 80, 80))
        if canvas.width > 400 or canvas.height > 400:
            raise AssertionError(f"viewer-unsafe panel {canvas.size}")
        canvas.save(out / f"frames-{page:02d}.png")
    print(f"{len(crops)} registered native crops -> {out}")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("tiles")
    p.add_argument("--master", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("frames")
    p.add_argument("--rawdir", type=Path, required=True)
    p.add_argument("--warpmap", type=Path, required=True)
    p.add_argument("--coverage", type=float, required=True)
    p.add_argument("--roi", type=int, nargs=4, required=True)
    p.add_argument("--step", type=int, default=5)
    p.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.cmd == "tiles":
        master_tiles(a.master, a.out)
    else:
        frame_sheets(
            a.rawdir,
            a.warpmap,
            tuple(a.roi),
            a.coverage,
            a.step,
            a.out,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

