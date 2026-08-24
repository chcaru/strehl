"""Characterise the 'waxy blob' defect: hard-edged pale patches in flat regions.

Found by eye in `_LOOK-marker.png` (rows 2 and 4): the merged render carries
pale amorphous patches with HARD boundaries in regions where the single-frame
control shows only a smooth defocused gradient. This script asks three
questions, each with the control beside it:

  Q1  Is the boundary actually hard, or is it a soft gradient my eye sharpened?
      -> radial/linear profile across the boundary in BOTH arms.
  Q2  Are the blobs in LOW-TEXTURE regions?
      -> local gradient energy of the CONTROL inside vs outside the blob mask.
  Q3  Does the control show any structure there at all?
      -> side-by-side zoom, per-arm stretch so neither arm is unreadable.

Q2 is the one that matters. If the blobs sit where the control has no texture,
the election has no signal there and the noise-gated mean (fact 19) should have
taken over. That makes "is the gate firing in flat regions?" the next question,
and it is answerable in code.

NOTE ON A FLAW IN THE PARENT SHEET: `look_defects.py` used ONE shared stretch
for both arms to stop brightness masquerading as structure. On `lavendar` that
made the control arm pure black and unreadable. Here each arm gets its own
stretch and the brightness difference is reported as a NUMBER instead.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

OUT = r"C:\dev\strehl-out\ORCH-thennow"
MERGED = os.path.join(OUT, "marker-HEAD-8f46f04.tif")
CTRL = os.path.join(OUT, "CONTROL-singleframe-dry-erase-marker-head-cpl.tif")

# Blob locations read off _LOOK-marker.png row 4 (crop origin 4715,1200) and
# row 2 (crop origin 2048,1300). Written down before measuring.
ZOOMS = [
    ("blobA-row4", 4715, 1180, 300, 260),
    ("blobB-row2", 2048, 1300, 320, 300),
]


def stretch(a):
    a = a.astype(np.float32)
    lo, hi = float(np.percentile(a, 0.5)), float(np.percentile(a, 99.5))
    return np.clip((a - lo) / max(hi - lo, 1e-6), 0, 1)


def to8(a):
    return (stretch(a) ** (1 / 2.2) * 255).astype(np.uint8)


def luma(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def grad_energy(y):
    gy, gx = np.gradient(y)
    return np.sqrt(gx * gx + gy * gy)


def main():
    m = tifffile.imread(MERGED)
    c = tifffile.imread(CTRL)
    h = min(m.shape[0], c.shape[0])
    w = min(m.shape[1], c.shape[1])
    m, c = m[:h, :w], c[:h, :w]

    print(f"merged {m.shape}  control {c.shape}")
    print(f"GLOBAL luma mean: merged {luma(m).mean():.1f}  control {luma(c).mean():.1f}  "
          f"ratio {luma(m).mean() / max(luma(c).mean(), 1e-6):.3f}")
    print()

    tiles = []
    for name, x, y, bw, bh in ZOOMS:
        mm = m[y:y + bh, x:x + bw]
        cc = c[y:y + bh, x:x + bw]
        ym, yc = luma(mm), luma(cc)

        # Q2: blob mask = brightest quartile of the MERGED patch (the blobs are
        # the pale things). Measure the CONTROL's texture inside vs outside.
        thr = np.percentile(ym, 75)
        mask = ym >= thr
        ge_c = grad_energy(yc)
        ge_m = grad_energy(ym)
        inside_c = ge_c[mask].mean()
        outside_c = ge_c[~mask].mean()
        inside_m = ge_m[mask].mean()
        outside_m = ge_m[~mask].mean()

        print(f"[{name}] @({x},{y}) {bw}x{bh}")
        print(f"   luma mean   merged {ym.mean():8.1f}   control {yc.mean():8.1f}")
        print(f"   CONTROL grad energy  inside-blob {inside_c:7.2f}   outside {outside_c:7.2f}"
              f"   ratio {inside_c / max(outside_c, 1e-6):.3f}")
        print(f"   MERGED  grad energy  inside-blob {inside_m:7.2f}   outside {outside_m:7.2f}"
              f"   ratio {inside_m / max(outside_m, 1e-6):.3f}")

        # Q1: how sharp is the blob boundary in each arm? Compare the 99th
        # percentile gradient on the mask BOUNDARY against the patch median.
        from scipy import ndimage
        edge = ndimage.binary_dilation(mask, iterations=2) & ~ndimage.binary_erosion(mask, iterations=2)
        if edge.sum() > 20:
            print(f"   boundary grad p90   merged {np.percentile(ge_m[edge], 90):7.2f}"
                  f"   control {np.percentile(ge_c[edge], 90):7.2f}")
        print()

        z = 3
        mim = Image.fromarray(to8(mm)).resize((bw * z, bh * z), Image.NEAREST)
        cim = Image.fromarray(to8(cc)).resize((bw * z, bh * z), Image.NEAREST)
        for im, t in ((mim, f"STREHL merged  {name}"), (cim, f"single frame   {name}")):
            d = ImageDraw.Draw(im)
            d.rectangle([0, 0, im.width, 22], fill=(0, 0, 0))
            d.text((6, 5), t, fill=(255, 255, 0))
        row = Image.new("RGB", (bw * z * 2 + 8, bh * z), (40, 40, 40))
        row.paste(mim, (0, 0))
        row.paste(cim, (bw * z + 8, 0))
        tiles.append(row)

    sheet = Image.new("RGB", (max(t.width for t in tiles),
                              sum(t.height + 8 for t in tiles)), (40, 40, 40))
    yy = 0
    for t in tiles:
        sheet.paste(t, (0, yy))
        yy += t.height + 8
    sheet.thumbnail((1400, 3600), Image.LANCZOS)
    dst = os.path.join(OUT, "_BLOB-zoom.png")
    sheet.save(dst)
    print(f"wrote {dst} {sheet.size}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
