"""Lateral-CA correction, judged on pictures at fixed coordinates.

The corpus already establishes the physics (SYNTHESIS fact 1414: a clean
one-parameter radial magnification error of -704.5 ppm in red, R^2 = 0.9969,
worth ~3 output pixels at the corner) and that the correction is implemented and
selected by STREHL_FIX_CA. What was never checked is the thing that decides:
does turning it on make the owner's photographs look better?

Lateral CA is zero at the optical centre and grows with radius, so a comparison
that crops the middle of the frame is guaranteed to show nothing. The ROIs here
are therefore fixed FRACTIONS of the frame, weighted to the corners, and they
are stated in the output so two runs are comparable. They are not chosen by
searching for a flattering tile.

The scalar is deliberately secondary. Project rule: if the pictures and the
number disagree, the pictures are right. It is reported per radial band, because
a correction can reduce fringing at one radius while over-correcting at another,
and a single frame-wide mean hides exactly that.

usage:
  python ca_ab.py --off <off.tif> --on <on.tif> --out <dir> --label <name>
"""

import argparse
import pathlib

import numpy as np
import tifffile
from PIL import Image, ImageDraw

# fixed fractional ROI centres: four corners, two mid-field, one centre control.
ROIS = [
    ("corner TL", 0.075, 0.075),
    ("corner TR", 0.925, 0.075),
    ("corner BL", 0.075, 0.925),
    ("corner BR", 0.925, 0.925),
    ("mid L", 0.250, 0.500),
    ("CENTRE (control: CA is ~0 here)", 0.500, 0.500),
]


def load(p):
    img = tifffile.imread(p)
    assert img.dtype == np.uint16, f"expected uint16, got {img.dtype} in {p}"
    assert img.ndim == 3 and img.shape[2] == 3, f"expected RGB, got {img.shape}"
    return img


def fringe_by_radius(img, bands=6):
    """Mean |R-G| and |B-G| at strong edges, per radial band, normalised.

    Chroma at an edge that is achromatic in the subject is the fringe. Measured
    only where the green gradient is strong, because that is where a lateral
    displacement between channels can express itself at all.
    """
    g = img[:, :, 1].astype(np.float32)
    r = img[:, :, 0].astype(np.float32)
    b = img[:, :, 2].astype(np.float32)
    gy, gx = np.gradient(g)
    grad = np.hypot(gy, gx)
    thr = np.percentile(grad, 99.0)
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    cy, cx = (H - 1) / 2.0, (W - 1) / 2.0
    rad = np.hypot(yy - cy, xx - cx)
    rad /= rad.max()
    strong = grad >= thr
    lum = np.maximum(g, 1.0)
    out = []
    for i in range(bands):
        lo, hi = i / bands, (i + 1) / bands
        m = strong & (rad >= lo) & (rad < hi)
        n = int(m.sum())
        if n < 200:
            out.append((lo, hi, n, float("nan"), float("nan")))
            continue
        rg = float(np.mean(np.abs(r[m] - g[m]) / lum[m]))
        bg = float(np.mean(np.abs(b[m] - g[m]) / lum[m]))
        out.append((lo, hi, n, rg, bg))
    return out


def crop(img, fx, fy, size):
    H, W = img.shape[:2]
    cx, cy = int(fx * W), int(fy * H)
    x = max(0, min(W - size, cx - size // 2))
    y = max(0, min(H - size, cy - size // 2))
    return img[y : y + size, x : x + size], x, y


def to8(a, gain):
    return np.clip(a.astype(np.float32) * gain / 257.0, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--off", required=True)
    ap.add_argument("--on", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--size", type=int, default=340)
    ap.add_argument("--gain", type=float, default=3.0)
    args = ap.parse_args()

    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    off = load(args.off)
    on = load(args.on)
    assert off.shape == on.shape, f"shape mismatch {off.shape} vs {on.shape}"
    H, W = off.shape[:2]
    print(f"subject : {args.label}   {W}x{H}")

    print()
    print("fringe at strong edges, normalised by local green, per radial band")
    print(f'{"band":>12s} {"n":>9s} {"|R-G| off":>10s} {"|R-G| on":>10s} '
          f'{"|B-G| off":>10s} {"|B-G| on":>10s}   verdict')
    fo = fringe_by_radius(off)
    fn = fringe_by_radius(on)
    lines = []
    for (lo, hi, n0, rg0, bg0), (_, _, n1, rg1, bg1) in zip(fo, fn):
        if np.isnan(rg0) or np.isnan(rg1):
            v = "too few edges"
        elif rg1 < rg0 * 0.98:
            v = "R fringe DOWN"
        elif rg1 > rg0 * 1.02:
            v = "R fringe UP (over-correction?)"
        else:
            v = "unchanged"
        line = (f"{lo:.2f}-{hi:.2f}".rjust(12) + f" {n0:9d} {rg0:10.5f} {rg1:10.5f} "
                f"{bg0:10.5f} {bg1:10.5f}   {v}")
        print(line)
        lines.append(line)

    pad, hdr = 8, 26
    tiles = []
    for name, fx, fy in ROIS:
        a, x, y = crop(off, fx, fy, args.size)
        b, _, _ = crop(on, fx, fy, args.size)
        tiles.append((name, x, y, to8(a, args.gain), to8(b, args.gain)))

    sheet_w = args.size * 2 + pad * 3
    sheet_h = (args.size + hdr + pad) * len(tiles) + pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    yy = pad
    for name, x, y, a8, b8 in tiles:
        d.text((pad, yy), f"{name}   at ({x},{y}) {args.size}px 1:1   "
                          f"LEFT = CA off    RIGHT = CA on", fill=(235, 235, 235))
        yy += hdr
        sheet.paste(Image.fromarray(a8), (pad, yy))
        sheet.paste(Image.fromarray(b8), (pad * 2 + args.size, yy))
        yy += args.size + pad

    p = outdir / f"ca-{args.label}.png"
    sheet.save(p)
    print()
    print(f"wrote : {p}   (gain x{args.gain:g}, 1:1 pixels, fixed fractional ROIs)")
    (outdir / f"ca-{args.label}.txt").write_text(
        f"{args.label}  {W}x{H}\noff={args.off}\non={args.on}\n\n" + "\n".join(lines) + "\n"
    )


if __name__ == "__main__":
    main()
