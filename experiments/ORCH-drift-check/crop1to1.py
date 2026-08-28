"""Cut true 1:1 crops from a single master and tile them into one viewable sheet.

Everything else in this directory is an A/B instrument. This one exists because
a ratio cannot tell you whether an image is print-worthy, and because I have
twice read a 1:1 crop backwards in this project -- grain reads to the eye as
"deeper blacks" and smoothness reads as "veiling". So: no comparison, no
rescaling, no tone mapping beyond a fixed gamma. Native pixels, at size.

Sites are chosen by gradient energy so the crops land on structure rather than
on empty background, with a minimum separation so they do not all pile onto the
same feature. A second mode targets subject/background BOUNDARIES specifically,
which is where a halo lives and where this project's worst artifact was found.

Usage:
    python crop1to1.py <master.tiff> <out.jpg> [--sites N] [--size PX] [--mode edge|halo]
"""

import argparse
import sys

import numpy as np
import tifffile
from PIL import Image


def to_luma(a: np.ndarray) -> np.ndarray:
    if a.ndim == 2:
        return a.astype(np.float32)
    a = a[:, :, :3].astype(np.float32)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def box(a: np.ndarray, r: int) -> np.ndarray:
    """Separable box blur via cumulative sums; O(1) per pixel in the radius."""
    pad = np.pad(a, r + 1, mode="edge")
    c = pad.cumsum(0).cumsum(1)
    w = 2 * r + 1
    s = c[w:, w:] - c[:-w, w:] - c[w:, :-w] + c[:-w, :-w]
    return s[: a.shape[0], : a.shape[1]] / (w * w)


def pick_sites(luma, n, size, mode, stride=8):
    """Return (y, x) top-left corners of crops, ranked and separated."""
    small = luma[::stride, ::stride]
    gy, gx = np.gradient(small)
    grad = np.hypot(gy, gx)

    if mode == "halo":
        # A halo lives where a subject boundary separates two large regions of
        # very different level. Rank by local level RANGE over a wide window,
        # not by gradient: fine texture has huge gradient and no halo, while a
        # subject edge against a bright ground has a big low-frequency step.
        lo = box(small, 12)
        hi = box(small, 40)
        score = np.abs(hi - lo) * grad
    else:
        score = box(grad, 6)

    half = size // (2 * stride)
    score[:half, :] = 0
    score[-half:, :] = 0
    score[:, :half] = 0
    score[:, -half:] = 0

    order = np.argsort(score, axis=None)[::-1]
    sep = max(size // stride, 24)
    out, taken = [], []
    for idx in order:
        if len(out) >= n:
            break
        sy, sx = np.unravel_index(idx, score.shape)
        if any(abs(sy - ty) < sep and abs(sx - tx) < sep for ty, tx in taken):
            continue
        taken.append((sy, sx))
        y = int(sy * stride) - size // 2
        x = int(sx * stride) - size // 2
        y = max(0, min(luma.shape[0] - size, y))
        x = max(0, min(luma.shape[1] - size, x))
        out.append((y, x, float(score[sy, sx])))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("master")
    ap.add_argument("out")
    ap.add_argument("--sites", type=int, default=6)
    ap.add_argument("--size", type=int, default=520)
    ap.add_argument("--mode", choices=["edge", "halo"], default="edge")
    ap.add_argument("--cols", type=int, default=3)
    args = ap.parse_args()

    a = tifffile.imread(args.master)
    if a.ndim == 2:
        a = np.dstack([a] * 3)
    a = a[:, :, :3]
    print(f"master  : {args.master}")
    print(f"shape   : {a.shape}  dtype={a.dtype}")

    luma = to_luma(a)
    sites = pick_sites(luma, args.sites, args.size, args.mode)
    if not sites:
        print("no sites found", file=sys.stderr)
        return 2

    # Fixed display transform, identical for every crop: scale by the master's
    # own 99.9th percentile then sRGB-ish gamma. No per-crop autoscaling, which
    # would make a flat crop and a contrasty crop look equally contrasty.
    p999 = float(np.percentile(luma, 99.9))
    scale = 1.0 / max(p999, 1.0)

    tiles = []
    for i, (y, x, sc) in enumerate(sites):
        crop = a[y : y + args.size, x : x + args.size].astype(np.float32) * scale
        crop = np.clip(crop, 0.0, 1.0) ** (1.0 / 2.2)
        tiles.append((crop * 255.0 + 0.5).astype(np.uint8))
        print(f"site {i}: y={y:5d} x={x:5d}  score={sc:12.1f}")

    cols = min(args.cols, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    gap = 8
    sheet = np.full(
        (rows * args.size + (rows + 1) * gap, cols * args.size + (cols + 1) * gap, 3),
        32,
        np.uint8,
    )
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        yy = gap + r * (args.size + gap)
        xx = gap + c * (args.size + gap)
        sheet[yy : yy + args.size, xx : xx + args.size] = t

    Image.fromarray(sheet).save(args.out, quality=95)
    print(f"wrote   : {args.out}  ({sheet.shape[1]}x{sheet.shape[0]}, {len(tiles)} crops @ 1:1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
