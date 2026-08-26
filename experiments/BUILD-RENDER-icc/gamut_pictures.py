"""Where does sRGB actually clip? Show it, do not just score it.

The census says `flower-inner-edge-cpl` loses 9.7-10.7% of its coloured pixels
to the sRGB gamut wall and every other subject loses essentially none. A number
like that is worth nothing until someone has looked at WHICH pixels, because
"10% of pixels clip" is compatible both with "an entire petal is wrong" and with
"a scattering of noise at the black point".

Output, all PNG -- a 100% artifact crop is never JPEG-encoded:
  <subject>-overview.png     downsampled frame, clipped pixels flagged
  <subject>-crop-*.png       true 100% crops at the densest clipping sites
  <subject>-swatches.png     the clipped colours themselves, before and after

Reads camera-native + linear-sRGB pairs with tifffile and asserts uint16.
Display conversion is for LOOKING only; no number in the report comes from it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

GAMUT = Path(r"C:\dev\strehl-out\ICC-AB\gamut")
OUT = Path(r"C:\dev\strehl-out\ICC-AB\gamut-pictures")
CROP = 400


def load(stem: str):
    lin = tifffile.imread(GAMUT / f"{stem}--linear.tiff")
    assert lin.dtype == np.uint16, f"expected uint16, got {lin.dtype}"
    return lin


def to_display(lin16: np.ndarray) -> np.ndarray:
    """Linear sRGB -> 8-bit sRGB. For viewing only."""
    v = lin16.astype(np.float32) / 65535.0
    v = np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.power(np.maximum(v, 0), 1 / 2.4) - 0.055)
    return (np.clip(v, 0, 1) * 255).astype(np.uint8)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    stems = ["flower-inner-edge-cpl", "flowers-cpl", "leaf-2-cpl"]

    for stem in stems:
        lin = load(stem)
        disp = to_display(lin)
        lum = (lin.astype(np.float32) / 65535.0) @ np.array([0.2126, 0.7152, 0.0722],
                                                            dtype=np.float32)
        # A coloured pixel pinned to exactly 0 in some channel is out of gamut.
        clipped = np.any(lin == 0, axis=2) & (lum > 0.005)
        pct = clipped.mean() * 100
        pct_col = clipped.sum() / max((lum > 0.005).sum(), 1) * 100
        print(f"\n{stem}: {clipped.sum():,} clipped px "
              f"({pct:.3f}% of frame, {pct_col:.3f}% of coloured px)")

        # Overview with the clipped pixels flagged.
        ov = disp.copy()
        ov[clipped] = [255, 0, 255]
        h, w, _ = ov.shape
        side = Image.fromarray(disp).resize((w // 4, h // 4), Image.LANCZOS)
        flag = Image.fromarray(ov).resize((w // 4, h // 4), Image.LANCZOS)
        panel = Image.new("RGB", (side.width * 2 + 12, side.height), "black")
        panel.paste(side, (0, 0))
        panel.paste(flag, (side.width + 12, 0))
        d = ImageDraw.Draw(panel)
        d.text((6, 6), f"{stem}  as delivered", fill=(255, 255, 255))
        d.text((side.width + 18, 6),
               f"magenta = clipped by sRGB  ({pct_col:.2f}% of coloured px)",
               fill=(255, 255, 255))
        panel.save(OUT / f"{stem}-overview.png")

        if clipped.sum() == 0:
            print("  no clipping -- no crops emitted (not a pass, just nothing to show)")
            continue

        # Densest clipping sites, at 100%.
        box = 64
        dens = clipped[: (h // box) * box, : (w // box) * box]
        dens = dens.reshape(h // box, box, w // box, box).sum(axis=(1, 3))
        flat = np.argsort(dens.ravel())[::-1]
        placed, sites = [], []
        for f in flat:
            by, bx = divmod(int(f), dens.shape[1])
            cy, cx = by * box + box // 2, bx * box + box // 2
            if any(abs(cy - y) < CROP and abs(cx - x) < CROP for y, x in placed):
                continue
            placed.append((cy, cx))
            sites.append((cy, cx, int(dens[by, bx])))
            if len(placed) == 3:
                break

        for i, (cy, cx, n) in enumerate(sites):
            y = int(np.clip(cy - CROP // 2, 0, h - CROP))
            x = int(np.clip(cx - CROP // 2, 0, w - CROP))
            sub = disp[y:y + CROP, x:x + CROP]
            msk = clipped[y:y + CROP, x:x + CROP]
            a = Image.fromarray(sub)
            b = Image.fromarray(np.where(msk[..., None], [255, 0, 255], sub).astype(np.uint8))
            pair = Image.new("RGB", (CROP * 2 + 8, CROP), "black")
            pair.paste(a, (0, 0))
            pair.paste(b, (CROP + 8, 0))
            pair.save(OUT / f"{stem}-crop{i + 1}-at-{x}-{y}.png")
            print(f"  crop{i + 1} at ({x},{y}) 100%: {msk.sum()} of {CROP * CROP} px clipped "
                  f"({msk.mean() * 100:.1f}%)")

        # The clipped colours themselves.
        ys, xs = np.nonzero(clipped)
        pick = np.random.default_rng(0).choice(len(ys), min(2000, len(ys)), replace=False)
        cols = disp[ys[pick], xs[pick]].astype(np.float32)
        order = np.argsort(cols.sum(axis=1))
        cols = cols[order]
        sw = Image.new("RGB", (600, 120), "black")
        dd = ImageDraw.Draw(sw)
        for i in range(60):
            c = cols[int(i * (len(cols) - 1) / 59)].astype(int)
            dd.rectangle([i * 10, 20, i * 10 + 9, 110], fill=tuple(c))
        dd.text((6, 4), f"{stem}: the colours sRGB clipped (sorted by lightness)",
                fill=(255, 255, 255))
        sw.save(OUT / f"{stem}-swatches.png")
        mean = cols.mean(axis=0)
        print(f"  mean clipped colour (8-bit display): R{mean[0]:.0f} G{mean[1]:.0f} B{mean[2]:.0f}"
              f"  -> {'red/magenta' if mean[0] > mean[1] and mean[0] > mean[2] else 'other'}")

    print(f"\npictures in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
