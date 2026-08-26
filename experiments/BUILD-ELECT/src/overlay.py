"""Overlay the winner field's discontinuities on the merged image, at a chosen zoom.

The question this answers is registration, not existence: does a seam in the winner
field land ON the boundary of the patch the eye sees? Two panels are emitted per crop --
the plain image and the image with seams painted -- so the seams can be judged against an
unpainted reference rather than against memory.

A "seam" is a pixel whose 4-neighbour winner index differs by more than --jump frames.
"""
import argparse
import pathlib

import numpy as np
import tifffile
from PIL import Image, ImageDraw
from matplotlib import colormaps

Image.MAX_IMAGE_PIXELS = None
REF = np.array([18735.0, 19249.0, 18686.0], dtype=np.float32)


def u16(p):
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p} is {a.dtype}, expected uint16"
    return a


def tone(a):
    x = np.clip(a.astype(np.float32) / (REF[None, None, :] / 0.92), 0.0, 1.0)
    return (np.clip(x ** (1 / 2.2), 0, 1) * 255).astype(np.uint8)


def colorise(a, cmap="turbo", lo=None, hi=None):
    a = a.astype(np.float32)
    lo = float(a.min()) if lo is None else lo
    hi = float(a.max()) if hi is None else hi
    if hi <= lo:
        hi = lo + 1.0
    x = np.clip((a - lo) / (hi - lo), 0, 1)
    return (colormaps[cmap](x)[..., :3] * 255).astype(np.uint8), lo, hi


def up2(a):
    return np.repeat(np.repeat(a, 2, axis=0), 2, axis=1)


def label(img, text):
    im = Image.fromarray(np.ascontiguousarray(img))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, len(text) * 7 + 8, 18], fill=(0, 0, 0))
    d.text((4, 4), text, fill=(255, 255, 255))
    return np.asarray(im)


def seams(e, jump):
    d = np.zeros(e.shape, bool)
    d[:-1, :] |= np.abs(np.diff(e.astype(np.int32), axis=0)) > jump
    d[:, :-1] |= np.abs(np.diff(e.astype(np.int32), axis=1)) > jump
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", required=True)
    ap.add_argument("--elect", required=True)
    ap.add_argument("--cy", type=int, required=True)
    ap.add_argument("--cx", type=int, required=True)
    ap.add_argument("--side", type=int, default=400, help="on the full-res output grid")
    ap.add_argument("--jump", type=int, default=8, help="winner-index step counted as a seam")
    ap.add_argument("--zoom", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--outdir", default=r"C:\dev\strehl-out\BUILD-ELECT\pics")
    args = ap.parse_args()

    merge, elect = u16(args.merge), u16(args.elect)
    h, w = merge.shape[:2]
    side = args.side
    y0 = int(np.clip(args.cy - side // 2, 0, h - side))
    x0 = int(np.clip(args.cx - side // 2, 0, w - side))
    py0, px0, pside = y0 // 2, x0 // 2, side // 2

    img = tone(merge[y0:y0 + side, x0:x0 + side])
    e = elect[py0:py0 + pside, px0:px0 + pside]
    ec, lo, hi = colorise(e)

    s = up2(seams(e, args.jump))
    painted = img.copy()
    painted[s] = np.array([255, 0, 0], np.uint8)

    z = args.zoom
    def Z(a):
        return np.repeat(np.repeat(a, z, axis=0), z, axis=1) if z > 1 else a

    panels = [label(Z(img), f"merge  y{y0} x{x0} {side}px"),
              label(Z(painted), f"seams |d idx|>{args.jump} in red"),
              label(Z(up2(ec)), f"winner idx {lo:.0f}-{hi:.0f}")]
    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    dst = outdir / f"{args.out}.png"
    Image.fromarray(np.concatenate(panels, axis=1)).save(dst)
    print(f"wrote {dst}")
    print(f"  winner idx: min={e.min()} max={e.max()} distinct={len(np.unique(e))} "
          f"median={np.median(e):.0f}")
    print(f"  seam pixels (plane grid): {int(seams(e, args.jump).sum())} of {e.size} "
          f"({100.0 * seams(e, args.jump).mean():.3f}%)")


if __name__ == "__main__":
    main()
