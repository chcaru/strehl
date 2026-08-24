"""M111 -- look at the merge's own state where the waxy blobs are.

Four panels at ORCH's two blob locations, plus a textured control ROI:

  1. the merged render (what the owner sees)
  2. best_index   -- pass one's elected frame, per 2x2 CFA quad
  3. n_eff        -- pass two's admitted-frame count at gate 4.0
  4. best_focus   -- the winner's REGULARISED response value

The output grid is 7040x4688 and the plane grid is 3520x2344, so plane
coordinates are output coordinates halved. Every panel is drawn on the plane
grid and the render is downsampled onto it, so the four are pixel-aligned by
construction rather than by eye.

Usage:  python state_panel.py
"""

import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

RENDER = r"C:\dev\strehl-out\M111\render\marker-dump.tif"
STATE = r"C:\dev\strehl-out\M111\render\state-r8"
OUT = r"C:\dev\strehl-out\M111"

# Output-grid ROIs. The first two are ORCH's blobs verbatim; the third is a
# high-texture control chosen from the render before any state plane was looked
# at, and the fourth is the whole frame for orientation.
ROIS = [
    ("blobB-row2", 2048, 1300, 320, 300),
    ("blobA-row4", 4715, 1180, 300, 260),
]


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def norm8(a, lo=None, hi=None, gamma=1.0):
    a = a.astype(np.float32)
    lo = float(np.percentile(a, 0.5)) if lo is None else lo
    hi = float(np.percentile(a, 99.5)) if hi is None else hi
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** gamma
    return (v * 255).astype(np.uint8)


def turbo(a8):
    """A cheap perceptually-ordered colour map so index plateaus are visible."""
    x = a8.astype(np.float32) / 255.0
    r = np.clip(1.5 - np.abs(4 * x - 3), 0, 1)
    g = np.clip(1.5 - np.abs(4 * x - 2), 0, 1)
    b = np.clip(1.5 - np.abs(4 * x - 1), 0, 1)
    return (np.dstack([r, g, b]) * 255).astype(np.uint8)


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 20], fill=(0, 0, 0))
    d.text((5, 4), text, fill=(255, 255, 0))
    return im


def main():
    rgb = tifffile.imread(RENDER)
    bi = np.load(os.path.join(STATE, "best_index.npy"))
    bf = np.load(os.path.join(STATE, "best_focus.npy"))
    ne = np.load(os.path.join(STATE, "n_eff_gate4.00.npy"))
    print(f"render {rgb.shape}  best_index {bi.shape} {bi.dtype}  "
          f"best_focus {bf.shape} {bf.dtype}  n_eff {ne.shape} {ne.dtype}")
    assert rgb.shape[0] == 2 * bi.shape[0] and rgb.shape[1] == 2 * bi.shape[1]

    print("\n--- WHOLE-PLANE STATE (MEASURED) ---")
    print(f"best_index : min {bi.min()} max {bi.max()} median {np.median(bi):.0f}")
    print(f"n_eff      : min {ne.min()} max {ne.max()} mean {ne.mean():.3f} "
          f"median {np.median(ne):.0f}  n_eff==1 {100 * (ne <= 1).mean():.2f}%")
    print(f"best_focus : min {bf.min():.4f} max {bf.max():.4f} "
          f"median {np.median(bf):.4f} p10 {np.percentile(bf, 10):.4f} "
          f"p90 {np.percentile(bf, 90):.4f}")
    # The pure-noise reference: a single frame's regularised response has mean
    # ~0.4330 (Rayleigh scale 0.125*sqrt(12)) and SD FOCUS_NOISE_SD = 0.015214,
    # so the max over 299 draws sits at ~0.4330 + 2.94*0.015214 = 0.4777.
    floor = 0.4330 + 2.94 * 0.015214
    print(f"pure-noise winner ceiling (derived) : {floor:.4f}")
    print(f"fraction of the plane below it      : {100 * (bf < floor).mean():.3f}%")

    y = luma(rgb)
    ydown = 0.25 * (y[0::2, 0::2] + y[1::2, 0::2] + y[0::2, 1::2] + y[1::2, 1::2])

    for name, ox, oy, ow, oh in ROIS:
        px, py, pw, ph = ox // 2, oy // 2, ow // 2, oh // 2
        sl = (slice(py, py + ph), slice(px, px + pw))
        r_bi, r_ne, r_bf, r_y = bi[sl], ne[sl], bf[sl], ydown[sl]
        print(f"\n--- {name}  output({ox},{oy}) {ow}x{oh} = plane({px},{py}) {pw}x{ph} ---")
        print(f"   luma       mean {r_y.mean():9.1f}")
        print(f"   best_index min {r_bi.min():4d} max {r_bi.max():4d} "
              f"unique {len(np.unique(r_bi)):5d}  modal share "
              f"{100 * np.bincount(r_bi.ravel()).max() / r_bi.size:6.2f}%")
        print(f"   n_eff      min {r_ne.min():4d} max {r_ne.max():4d} "
              f"mean {r_ne.mean():8.2f} median {np.median(r_ne):6.1f}  "
              f"n_eff==1 {100 * (r_ne <= 1).mean():6.2f}%")
        print(f"   best_focus min {r_bf.min():8.4f} max {r_bf.max():9.4f} "
              f"median {np.median(r_bf):8.4f}  below noise ceiling "
              f"{100 * (r_bf < floor).mean():6.2f}%")

        z = 3
        panels = [
            label(Image.fromarray(norm8(r_y, gamma=1 / 2.2)).convert("RGB")
                  .resize((pw * z, ph * z), Image.NEAREST), f"{name}  merged luma"),
            label(Image.fromarray(turbo(norm8(r_bi, lo=0, hi=298)))
                  .resize((pw * z, ph * z), Image.NEAREST),
                  f"best_index 0..298 ({r_bi.min()}..{r_bi.max()})"),
            label(Image.fromarray(turbo(norm8(r_ne, lo=1, hi=299)))
                  .resize((pw * z, ph * z), Image.NEAREST),
                  f"n_eff 1..299 ({r_ne.min()}..{r_ne.max()})"),
            label(Image.fromarray(turbo(norm8(np.log10(np.maximum(r_bf, 1e-3)),
                                              lo=-0.4, hi=1.5)))
                  .resize((pw * z, ph * z), Image.NEAREST),
                  f"log10 best_focus ({r_bf.min():.2f}..{r_bf.max():.1f})"),
        ]
        w = sum(p.width + 6 for p in panels)
        sheet = Image.new("RGB", (w, panels[0].height), (30, 30, 30))
        xx = 0
        for p in panels:
            sheet.paste(p, (xx, 0))
            xx += p.width + 6
        sheet.thumbnail((2400, 1200), Image.LANCZOS)
        dst = os.path.join(OUT, f"_STATE-{name}.png")
        sheet.save(dst)
        print(f"   wrote {dst} {sheet.size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
