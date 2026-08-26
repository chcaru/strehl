"""1:1 crops from a SHIP master, for judging print-worthiness by eye.

Usage: python pixelpeep.py <master.tiff> <outdir> [--tiles N]

Picks the N most detailed 1:1 tiles by local gradient energy, spaced apart so
they do not all land on the same feature, and writes each at true 1:1 with a
display grade applied.

TONE CURVE RULE (learned the hard way in hullcrop.py): when more than one image
is written for comparison, the curve must be derived ONCE and shared. Here every
tile comes from a single master, so one curve per master is derived from the
whole frame -- never per tile, or tiles become mutually incomparable and a
brightness difference between two regions reads as a grading difference.
"""
import sys
import pathlib
import numpy as np
import tifffile


TILE = 900
MARGIN = 64


def grade(x_lin, lo, hi):
    """Shared display grade: linear DN -> 8-bit sRGB-ish."""
    y = (x_lin.astype(np.float64) - lo) / max(hi - lo, 1.0)
    y = np.clip(y, 0.0, 1.0)
    y = np.where(y <= 0.0031308, y * 12.92, 1.055 * np.power(y, 1 / 2.4) - 0.055)
    return np.clip(y * 255.0 + 0.5, 0, 255).astype(np.uint8)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2])
    ntile = 6
    if "--tiles" in sys.argv:
        ntile = int(sys.argv[sys.argv.index("--tiles") + 1])
    out.mkdir(parents=True, exist_ok=True)

    img = tifffile.imread(str(src))
    assert img.dtype == np.uint16, f"expected uint16, got {img.dtype}"
    assert img.ndim == 3 and img.shape[2] == 3, f"expected HxWx3, got {img.shape}"
    h, w, _ = img.shape
    print(f"{src.name}  {w}x{h}  uint16")

    g = img[:, :, 1].astype(np.float32)

    # one curve for the whole master, from the whole frame
    lo = float(np.percentile(g, 0.5))
    hi = float(np.percentile(g, 99.7))
    print(f"shared display curve: lo={lo:.1f} hi={hi:.1f} DN")

    # detail map on a coarse grid: mean |laplacian| per candidate tile centre
    step = TILE // 2
    lap = np.abs(4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:])
    cand = []
    for y in range(MARGIN, h - TILE - MARGIN, step):
        for x in range(MARGIN, w - TILE - MARGIN, step):
            score = float(lap[y:y + TILE, x:x + TILE].mean())
            cand.append((score, y, x))
    cand.sort(reverse=True)

    picked = []
    for score, y, x in cand:
        if all(abs(y - py) > TILE or abs(x - px) > TILE for _, py, px in picked):
            picked.append((score, y, x))
        if len(picked) >= ntile:
            break

    stem = src.stem
    for i, (score, y, x) in enumerate(picked, 1):
        tile = img[y:y + TILE, x:x + TILE, :]
        rgb = np.dstack([grade(tile[:, :, c], lo, hi) for c in range(3)])
        p = out / f"{stem}--peep{i}-y{y}-x{x}.png"
        try:
            from PIL import Image
            Image.fromarray(rgb).save(str(p))
        except ImportError:
            tifffile.imwrite(str(p.with_suffix(".tif")), rgb)
        print(f"  tile {i}: y={y} x={x} detail={score:.1f} -> {p.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
