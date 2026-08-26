"""Put the merged image, the winner field and n_eff side by side at the two patches.

The winner field lives on the plane grid (3520x2344), half the output grid (7040x4688)
in each axis, so it is nearest-neighbour upsampled by 2 -- NOT interpolated, because
interpolation would soften exactly the hard boundaries this is looking for.

Three renderings of the winner field, because one is not enough to judge it:
  * winner index under a cyclic-free colormap, autoscaled to the CROP's own range
    (the whole-plane range is 0..204 and would flatten any local structure)
  * the winner field's own gradient magnitude, which makes a hard seam a bright line
  * n_eff, the number of frames averaged
"""
import argparse
import pathlib

import numpy as np
import tifffile
from PIL import Image
from matplotlib import cm

Image.MAX_IMAGE_PIXELS = None

REF = np.array([18735.0, 19249.0, 18686.0], dtype=np.float32)
CROPS = {"upper-lobe": (2112, 2464), "lower-lobe": (3168, 3872)}
SIDE = 700  # on the full-resolution output grid


def u16(p):
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p} is {a.dtype}, expected uint16"
    return a


def tone(a):
    x = np.clip(a.astype(np.float32) / (REF[None, None, :] / 0.92), 0.0, 1.0)
    return (np.clip(x ** (1 / 2.2), 0, 1) * 255).astype(np.uint8)


def colorise(a, lo=None, hi=None, cmap="turbo"):
    a = a.astype(np.float32)
    lo = float(np.percentile(a, 1)) if lo is None else lo
    hi = float(np.percentile(a, 99)) if hi is None else hi
    if hi <= lo:
        hi = lo + 1.0
    x = np.clip((a - lo) / (hi - lo), 0, 1)
    return (cm.get_cmap(cmap)(x)[..., :3] * 255).astype(np.uint8), lo, hi


def up2(a):
    return np.repeat(np.repeat(a, 2, axis=0), 2, axis=1)


def label(img, text):
    from PIL import ImageDraw
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, len(text) * 7 + 8, 18], fill=(0, 0, 0))
    d.text((4, 4), text, fill=(255, 255, 255))
    return np.asarray(im)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", required=True)
    ap.add_argument("--elect", required=True)
    ap.add_argument("--neff", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--outdir", default=r"C:\dev\strehl-out\BUILD-ELECT\pics")
    args = ap.parse_args()

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    merge = u16(args.merge)
    elect = u16(args.elect)
    neff = u16(args.neff) if args.neff else None
    print(f"merge {merge.shape}  elect {elect.shape}"
          + (f"  neff {neff.shape}" if neff is not None else ""))
    assert merge.shape[0] == 2 * elect.shape[0] and merge.shape[1] == 2 * elect.shape[1], \
        "the election map must be exactly half the output grid in each axis"

    for tag, (cy, cx) in CROPS.items():
        h, w = merge.shape[:2]
        y0 = int(np.clip(cy - SIDE // 2, 0, h - SIDE))
        x0 = int(np.clip(cx - SIDE // 2, 0, w - SIDE))
        py0, px0, pside = y0 // 2, x0 // 2, SIDE // 2

        img = tone(merge[y0:y0 + SIDE, x0:x0 + SIDE])
        e = elect[py0:py0 + pside, px0:px0 + pside].astype(np.float32)
        ec, lo, hi = colorise(e)
        gy, gx = np.gradient(e)
        gm = np.sqrt(gx ** 2 + gy ** 2)
        gc, _, ghi = colorise(gm, lo=0.0, hi=float(np.percentile(gm, 99.5)), cmap="inferno")

        panels = [label(img, "merge"),
                  label(up2(ec), f"winner idx {lo:.0f}-{hi:.0f}"),
                  label(up2(gc), f"|grad winner| 0-{ghi:.1f}")]
        if neff is not None:
            n = neff[py0:py0 + pside, px0:px0 + pside].astype(np.float32)
            nc, nlo, nhi = colorise(n, cmap="viridis")
            panels.append(label(up2(nc), f"n_eff {nlo:.0f}-{nhi:.0f}"))

        dst = outdir / f"{args.out}-{tag}.png"
        Image.fromarray(np.concatenate(panels, axis=1)).save(dst)
        print(f"wrote {dst}")
        print(f"   {tag}: winner idx in crop  min={e.min():.0f} max={e.max():.0f} "
              f"median={np.median(e):.0f}  distinct={len(np.unique(e))}")
        if neff is not None:
            print(f"   {tag}: n_eff in crop  min={n.min():.0f} max={n.max():.0f} "
                  f"median={np.median(n):.0f}")


if __name__ == "__main__":
    main()
