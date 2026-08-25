#!/usr/bin/env python
"""Magnify a small window of each arm side by side, for by-eye adjudication.

`sheet.py` answers "how do these renders compare" at 1:1. It cannot answer
"does lanczos3 ring", because ringing is a one-to-three pixel over/undershoot
hugging a hard edge and 1:1 is too coarse to see it. This magnifies NEAREST so
no interpolation of mine is ever mistaken for the renderer's.

Usage:
  python zoom.py --subject bee-3-cpl --x 300 --y 4300 --w 180 --zoom 5

The luminance profile printed alongside is here to confirm or refute what my
eye reports on the same pixels -- it is not offered as an independent metric.
M113-kernel-verify owns the metric-side attack on this claim and I have not
looked at its work.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

OUT_ROOT = Path(r"C:\dev\strehl-out\M110-sheet")
ARMS = ["default", "lanczos3"]


def load8(p: Path) -> np.ndarray:
    a = tifffile.imread(p)
    return (a >> 8).astype(np.uint8) if a.dtype == np.uint16 else a.astype(np.uint8)


def font(size: int):
    for name in ("consola.ttf", "arial.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--x", type=int, required=True)
    ap.add_argument("--y", type=int, required=True)
    ap.add_argument("--w", type=int, default=180)
    ap.add_argument("--zoom", type=int, default=5)
    ap.add_argument("--row", type=int, default=None,
                    help="row within the window to profile; default = middle")
    ap.add_argument("--tag", default="zoom")
    ap.add_argument("--arm", action="append",
                    help="arms to place side by side; repeatable. Default: the two "
                         "kernel arms this script was written for.")
    ap.add_argument("--chroma", type=float, default=0.0,
                    help="also emit a row showing SIGNED R-Y amplified by this gain, "
                         "mapped red-positive / cyan-negative. Lateral CA is a red/cyan "
                         "pair and at 1:1 an 8-bit level of it is near the edge of "
                         "visibility, so the amplified row is how you SEE which way a "
                         "fringe went. It is a viewing aid and is labelled as one: every "
                         "verdict in the report is quoted from the unamplified row.")
    a = ap.parse_args()
    arms = a.arm or ARMS

    d = OUT_ROOT / a.subject
    tiles, profiles, chroma = [], {}, {}
    for arm in arms:
        img = load8(d / f"{arm}.tif")
        win = img[a.y:a.y + a.w, a.x:a.x + a.w]
        tiles.append((arm, win))
        lum = win.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
        profiles[arm] = lum[a.row if a.row is not None else a.w // 2]
        if a.chroma > 0:
            f = win.astype(np.float32)
            ry = f[:, :, 0] - (0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1]
                               + 0.0722 * f[:, :, 2])
            v = np.clip(ry * a.chroma, -128, 128)
            g = np.full_like(v, 128.0)
            chroma[arm] = np.dstack([g + v, g - v * 0.5, g - v]).clip(0, 255).astype(np.uint8)

    z, pad, head = a.zoom, 12, 34
    tw = a.w * z
    rows = 2 if a.chroma > 0 else 1
    W = pad + (tw + pad) * len(tiles)
    H = head + (tw + head) * rows + pad - head + head
    sheet = Image.new("RGB", (W, H), (16, 16, 16))
    dr = ImageDraw.Draw(sheet)
    dr.text((pad, 8), f"{a.subject}  @({a.x},{a.y})  {a.w}px window  x{z} NEAREST"
                      f"  -- no resize/sharpen/tone change", font=font(15), fill=(235, 235, 235))
    for i, (arm, win) in enumerate(tiles):
        x0 = pad + i * (tw + pad)
        sheet.paste(Image.fromarray(win).resize((tw, tw), Image.NEAREST), (x0, head))
        dr.text((x0, head - 15), arm + ("   <- SHIPPED DEFAULT" if arm == "default" else ""),
                font=font(13), fill=(255, 210, 90))
        if a.chroma > 0:
            y1 = head + tw + head
            sheet.paste(Image.fromarray(chroma[arm]).resize((tw, tw), Image.NEAREST), (x0, y1))
            dr.text((x0, y1 - 15), f"{arm}  SIGNED R-Y x{a.chroma:g}  (red +, cyan -) "
                                   f"VIEWING AID, NOT THE MEASUREMENT",
                    font=font(13), fill=(120, 200, 255))
    out = d / f"ZOOM-{a.subject}-{a.tag}-{a.x}x{a.y}.png"
    sheet.save(out)
    print(f"wrote {out}  {sheet.size}")

    # Overshoot readout on the identical row, to check my eye against the pixels.
    print(f"\nluminance profile, row {a.row if a.row is not None else a.w // 2} of window")
    for arm in arms:
        p = profiles[arm]
        lo, hi = float(p.min()), float(p.max())
        # local extrema relative to a monotone edge: the signature of ringing is
        # excursion BEYOND the flat levels on either side of the edge.
        left, right = float(np.median(p[:12])), float(np.median(p[-12:]))
        flat_lo, flat_hi = min(left, right), max(left, right)
        under = max(0.0, flat_lo - lo)
        over = max(0.0, hi - flat_hi)
        print(f"  {arm:<10} plateaus {left:6.1f} .. {right:6.1f}   "
              f"min {lo:6.1f} max {hi:6.1f}   undershoot {under:5.2f}  overshoot {over:5.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
