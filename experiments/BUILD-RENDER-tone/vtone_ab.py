"""Judge the V-TONE chromaticity fix by looking at pictures.

Emits, per subject, one panel:
    row 1  full frame   before | after
    row 2  100% crop    before | after      (crop chosen where the defect was worst)
    row 3  same crop x6 before | after      (V-TONE's boost, to reveal shadow structure)

The crop is chosen automatically as the tile with the most channel-zeroed pixels in
the BEFORE arm. That is the place the defect actually lived, so it is the honest
place to look, and it is reproducible from the images alone.

These are --srgb viewing renders. Measuring here is legitimate and required: the
question is a property of the deliverable image (is a channel destroyed on the way
to the file), not a question about merge or sharpness quality. Nothing in this
script is used to judge the stack.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw

AB = Path(r"C:\dev\strehl-out\vtone-ab")
OUT = AB / "panels"
CROP = 560
BOOST = 6.0


def read16(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p} is {a.dtype}, expected uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{p} shape {a.shape}"
    return a


def stats(a: np.ndarray) -> dict:
    f = a.astype(np.float32) / 65535.0
    lum = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
    n = f[..., 0].size
    d = {"medLum": float(np.median(lum))}
    for i, c in enumerate("RGB"):
        d[f"zero{c}%"] = 100.0 * float((a[..., i] == 0).sum()) / n
        d[f"blown{c}%"] = 100.0 * float((a[..., i] >= 65535).sum()) / n
    d["blownAny%"] = 100.0 * float((a >= 65535).any(axis=2).sum()) / n
    d["blownAll%"] = 100.0 * float((a >= 65535).all(axis=2).sum()) / n
    return d


def worst_tile(before: np.ndarray) -> tuple[int, int]:
    """Tile origin with the most channel-zeroed pixels in the before arm."""
    zero = (before == 0).any(axis=2)
    h, w = zero.shape
    best, by, bx = -1, h // 2 - CROP // 2, w // 2 - CROP // 2
    for y in range(0, h - CROP, CROP):
        for x in range(0, w - CROP, CROP):
            c = int(zero[y:y + CROP, x:x + CROP].sum())
            if c > best:
                best, by, bx = c, y, x
    if best <= 0:  # no defect to find: fall back to the frame centre
        return h // 2 - CROP // 2, w // 2 - CROP // 2
    return by, bx


def to8(a: np.ndarray, boost: float = 1.0) -> Image.Image:
    f = a.astype(np.float32) * boost
    return Image.fromarray(np.clip(f / 257.0, 0, 255).astype(np.uint8))


def label(im: Image.Image, text: str) -> Image.Image:
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 8 * len(text) + 10, 22], fill=(0, 0, 0))
    d.text((5, 6), text, fill=(255, 255, 0))
    return im


def panel(subject: str) -> str:
    b = read16(AB / f"{subject}-before.tif")
    a = read16(AB / f"{subject}-after.tif")
    assert b.shape == a.shape, f"{subject}: shapes differ {b.shape} {a.shape}"
    sb, sa = stats(b), stats(a)
    y, x = worst_tile(b)

    cb, ca = b[y:y + CROP, x:x + CROP], a[y:y + CROP, x:x + CROP]
    view_w = CROP * 2
    fb = to8(b).resize((view_w, int(view_w * b.shape[0] / b.shape[1])), Image.LANCZOS)
    fa = to8(a).resize((view_w, int(view_w * a.shape[0] / a.shape[1])), Image.LANCZOS)

    rows = [
        (label(fb, "FULL before"), label(fa, "FULL after")),
        (label(to8(cb), f"100% before @{x},{y}"), label(to8(ca), "100% after")),
        (label(to8(cb, BOOST), f"x{BOOST:g} before"), label(to8(ca, BOOST), f"x{BOOST:g} after")),
    ]
    w = max(l.width + r.width for l, r in rows) + 12
    h = sum(max(l.height, r.height) for l, r in rows) + 8 * len(rows)
    out = Image.new("RGB", (w, h), (24, 24, 24))
    yy = 0
    for l, r in rows:
        out.paste(l, (0, yy))
        out.paste(r, (l.width + 8, yy))
        yy += max(l.height, r.height) + 8
    OUT.mkdir(parents=True, exist_ok=True)
    out.save(OUT / f"{subject}.png")

    keys = ["zeroR%", "zeroG%", "zeroB%", "medLum", "blownR%", "blownG%", "blownB%", "blownAll%"]
    return "  ".join([f"{subject:<24}"] + [f"{k}={sb[k]:.4f}->{sa[k]:.4f}" for k in keys])


if __name__ == "__main__":
    subs = sys.argv[1:] or [p.name[: -len("-before.tif")]
                            for p in sorted(AB.glob("*-before.tif"))]
    for s in subs:
        if not (AB / f"{s}-after.tif").exists():
            print(f"{s:<24} after arm missing, skipped")
            continue
        print(panel(s), flush=True)
    print(f"\npanels -> {OUT}")
