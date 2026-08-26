"""Review sheet for a single render: full frame plus a UNIFORM 3x3 grid of 100%
crops.

The grid is uniform on purpose. Section 28 records a reversal caused by choosing
crops by edge density: every crop landed on a silhouette, the halo was correctly
judged absent, and a large black crush elsewhere in the same frame went unseen
for hours. A uniform grid has no feature preference, so it cannot be blind to a
feature. It will often be boring. Boring is the point.

Input is expected to be the tool's sRGB output. If given camera-linear data the
sheet will look black and that is the correct behaviour -- it is not this
script's job to invent a tone curve, because a tone curve I invent would be a
confound in every judgement made from the picture.
"""
import numpy as np, tifffile, os, sys
from PIL import Image

CROP = 520          # px at 100%
GRID = 3


def to8(a):
    """16-bit -> 8-bit. No tone mapping: the render already carries its curve."""
    if a.dtype == np.uint16:
        return (a >> 8).astype(np.uint8)
    if a.dtype == np.uint8:
        return a
    return np.clip(a / 256.0, 0, 255).astype(np.uint8)


def label(img, text):
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 8 * len(text) + 10, 18], fill=(0, 0, 0))
    d.text((5, 4), text, fill=(255, 220, 60))
    return img


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: preview.py <render.tiff> <outdir> [maxdim]")
        raise SystemExit(2)
    src, outdir = sys.argv[1], sys.argv[2]
    maxdim = int(sys.argv[3]) if len(sys.argv) > 3 else 2000
    os.makedirs(outdir, exist_ok=True)
    name = os.path.splitext(os.path.basename(src))[0]

    a = tifffile.imread(src)
    if a.ndim != 3:
        raise SystemExit(f"expected RGB, got shape {a.shape}")
    h, w = a.shape[:2]
    u8 = to8(a)

    # A render that is almost entirely black is far more likely to be linear data
    # opened as if it were tone-mapped than a genuinely black photograph. Say so
    # rather than silently emitting a black sheet that looks like a failed stack.
    med = float(np.median(u8))
    note = "" if med > 12 else "  [WARNING: median 8-bit level %.1f -- is this camera-linear rather than sRGB?]" % med

    full = Image.fromarray(u8)
    sc = min(maxdim / w, maxdim / h, 1.0)
    full_s = full.resize((int(w * sc), int(h * sc)), Image.LANCZOS)
    label(full_s, f"{name}  {w}x{h}  fit {sc*100:.0f}%")
    fp = os.path.join(outdir, f"{name}--full.jpg")
    full_s.save(fp, quality=92)

    # Uniform grid, inset from the border so the frame edge does not dominate.
    inset = 300
    ys = np.linspace(inset, h - CROP - inset, GRID).astype(int)
    xs = np.linspace(inset, w - CROP - inset, GRID).astype(int)
    tiles = []
    for gy, y in enumerate(ys):
        row = []
        for gx, x in enumerate(xs):
            t = Image.fromarray(u8[y:y + CROP, x:x + CROP])
            label(t, f"{gy},{gx} @ y{y} x{x}")
            row.append(np.asarray(t))
        tiles.append(np.concatenate([np.pad(r, ((0, 0), (0, 6), (0, 0)),
                                            constant_values=40) for r in row], axis=1))
    sheet = np.concatenate([np.pad(t, ((0, 6), (0, 0), (0, 0)),
                                   constant_values=40) for t in tiles], axis=0)
    gp = os.path.join(outdir, f"{name}--grid100.jpg")
    Image.fromarray(sheet).save(gp, quality=95)

    print(f"{name}: {w}x{h}  median8={med:.1f}{note}")
    print(f"  {fp}")
    print(f"  {gp}   (uniform {GRID}x{GRID} at 100%, {CROP}px each)")
