"""Build a 1:1 detail gallery across every delivered master.

A contact sheet answers "did it stack". It cannot answer "is this print-worthy",
because print quality lives at the pixel level and a 300 px thumbnail has thrown
that away before you look at it. This emits one true 1:1 tile per subject at
native resolution -- what a print actually shows -- plus a navigation sheet that
is explicitly labelled as reduced so nobody mistakes it for the evidence.

Usage: python detailgallery.py <masterdir> <outdir> [--tile 800]

Per master:
  - one display curve, derived once from the whole frame, shared by every tile
    from that master. Never per-tile: a brightness difference between two
    regions of the subject would otherwise read as a grading difference.
  - the tile is chosen by mean |laplacian| on a coarse grid, i.e. the subject's
    own best-resolved site. This flatters every subject equally, which is the
    point -- it asks "at its best, is this a print?" and compares like with
    like.

The per-subject number reported is mean |laplacian| INSIDE the chosen tile, in
linear DN. It is not comparable across subjects with different exposure or
albedo and is printed only to order the sheet; the images are the evidence.
"""
import sys
import pathlib
import numpy as np
import tifffile
from PIL import Image, ImageDraw


def grade(x_lin, lo, hi):
    y = (x_lin.astype(np.float64) - lo) / max(hi - lo, 1.0)
    y = np.clip(y, 0.0, 1.0)
    y = np.where(y <= 0.0031308, y * 12.92, 1.055 * np.power(y, 1 / 2.4) - 0.055)
    return np.clip(y * 255.0 + 0.5, 0, 255).astype(np.uint8)


def best_tile(g, tile, margin=64):
    h, w = g.shape
    lap = np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])
    step = max(tile // 2, 1)
    best = (-1.0, margin, margin)
    for y in range(margin, max(h - tile - margin, margin + 1), step):
        for x in range(margin, max(w - tile - margin, margin + 1), step):
            s = float(lap[y:y + tile, x:x + tile].mean())
            if s > best[0]:
                best = (s, y, x)
    return best


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    srcdir = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2])
    tile = int(sys.argv[sys.argv.index("--tile") + 1]) if "--tile" in sys.argv else 800
    out.mkdir(parents=True, exist_ok=True)
    (out / "detail").mkdir(exist_ok=True)

    masters = sorted(srcdir.glob("*.tiff"))
    if not masters:
        print(f"no .tiff in {srcdir}")
        return 2
    print(f"{len(masters)} masters, tile {tile}x{tile} at 1:1")

    rows = []
    for i, m in enumerate(masters, 1):
        img = tifffile.imread(str(m))
        if img.dtype != np.uint16 or img.ndim != 3:
            print(f"  SKIP {m.name}: dtype={img.dtype} shape={img.shape}")
            continue
        g = img[:, :, 1].astype(np.float32)
        lo = float(np.percentile(g, 0.5))
        hi = float(np.percentile(g, 99.7))
        score, y, x = best_tile(g, tile)
        t = img[y:y + tile, x:x + tile, :]
        rgb = np.dstack([grade(t[:, :, c], lo, hi) for c in range(3)])
        p = out / "detail" / f"{m.stem}.png"
        Image.fromarray(rgb).save(str(p))
        rows.append((score, m.stem, y, x, p))
        print(f"  [{i:2d}/{len(masters)}] {m.stem:<32} detail={score:8.1f}  y={y} x={x}")

    rows.sort(reverse=True)

    # navigation sheet -- reduced, and labelled as such
    cols, thumb, pad, cap = 5, 300, 14, 30
    n = len(rows)
    nrow = (n + cols - 1) // cols
    W = cols * (thumb + pad) + pad
    H = nrow * (thumb + pad + cap) + 70
    sheet = Image.new("RGB", (W, H), (22, 22, 24))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 16), "strehl -- 1:1 DETAIL, one tile per subject at its own best-resolved site.",
           fill=(232, 232, 232))
    d.text((pad, 34), f"THIS SHEET IS REDUCED {thumb}/{tile} -- judge print quality in detail\\, not here.",
           fill=(168, 168, 172))
    for k, (score, name, y, x, p) in enumerate(rows):
        r, c = divmod(k, cols)
        ox = pad + c * (thumb + pad)
        oy = 70 + r * (thumb + pad + cap)
        sheet.paste(Image.open(p).resize((thumb, thumb), Image.LANCZOS), (ox, oy))
        d.text((ox, oy + thumb + 4), f"#{k + 1} {name}", fill=(228, 228, 228))
        d.text((ox, oy + thumb + 17), f"detail {score:.0f} DN  y={y} x={x}", fill=(150, 150, 154))
    sp = out / "detail-sheet.png"
    sheet.save(str(sp))
    print(f"\nwrote {sp}")
    print(f"wrote {n} 1:1 tiles to {out / 'detail'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
