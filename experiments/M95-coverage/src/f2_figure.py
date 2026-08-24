"""Deliverable figure: what the proposed fix does to a real crop, next to what
actually costs the sharpness.

Five panels on one 100% crop of bee-3-cpl, all from the same unresampled strehl
decode, all through one Catmull-Rom gather except where stated:

  SOURCE   no gather at all -- the ceiling
  NOW      real frame warp + coverage scale, shipped geometry
  FIX      real frame warp, coverage scale removed (the proposal)
  SNAP     translation rounded to integer, unit scale (geometry floor)
  LANCZOS3 shipped geometry, better kernel (arm 4's patch)

No sharpness number is printed on any panel. The numbers live in the report,
measured on a band-matched spectral axis, and printing them here would invite
reading them as a per-panel measurement they are not.
"""
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import m95cov as M

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
MAP = Path(r"D:\personal\macro\bee-3-cpl\warpmap.txt")
OUT = Path(r"C:\dev\strehl-out\M95-coverage\M95-coverage-fix.png")

CROP = 420
K_COVER = 0.9315


def f64(h):
    return struct.unpack(">d", bytes.fromhex(h))[0]


def pick_frame():
    """A frame with a strongly non-integer offset -- the common case."""
    best = None
    for line in MAP.read_text(encoding="utf-8").splitlines():
        p = line.strip().split()
        if len(p) >= 6 and p[1] == "placed":
            a_re, a_im, b_re, b_im = (f64(p[2]), f64(p[3]), f64(p[4]), f64(p[5]))
            fx = (b_re * 2.0) % 1.0
            d = min(fx, 1 - fx)
            if best is None or d > best[0]:
                best = (d, int(p[0]), np.hypot(a_re, a_im), b_re * 2.0, b_im * 2.0)
    return best


def render(img, ci, cj, a, by, bx, step, kernel="catmull-rom", snap=False):
    """Gather the SAME scene span through the stated geometry.

    Every panel covers the identical CROP source pixels, so the eye compares
    like with like. Only the sampling step and the sub-pixel phase change. An
    arm whose step is s produces CROP/s output pixels for that span, which is
    exactly the smaller file the coverage fix would emit; it is shown at that
    size rather than stretched, because stretching it back is the very
    operation under test.
    """
    if snap:
        a, by, bx = 1.0, 0.0, 0.0
    s = a * step
    n = int(round(CROP / s))
    phase_y, phase_x = by - np.floor(by), bx - np.floor(bx)
    pad = CROP + 64
    y0, x0 = ci - pad // 2, cj - pad // 2
    reg = img[y0 : y0 + pad, x0 : x0 + pad]
    start_y = (ci - CROP / 2.0) - y0 + phase_y
    start_x = (cj - CROP / 2.0) - x0 + phase_x
    i = np.arange(n, dtype=np.float64)
    t = M.gather_1d(reg, start_y + i * s, 0, kernel)
    return M.gather_1d(t, start_x + i * s, 1, kernel)


def norm(a, lo, hi):
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)
    return (np.power(v, 1 / 2.2) * 255).astype(np.uint8)


def main():
    img = M.load_luma(B0)
    tiles = M.pick_tiles(img, n=6, tile=CROP, pad=CROP + 64)
    ty, tx = tiles[0]
    cy, cx = ty + CROP // 2, tx + CROP // 2
    d, idx, a, bx, by = pick_frame()
    print(f"crop centre  : ({cx}, {cy}) -- sharpest {CROP}px region of the frame")
    print(f"frame chosen : {idx}, scale {a:.6f}, offset ({bx:+.3f}, {by:+.3f}) "
          f"render px, {d:.3f} px from the nearest integer")

    ci, cj = cy, cx
    panels = [("SOURCE  no gather",
               img[ci - CROP // 2 : ci + CROP // 2, cj - CROP // 2 : cj + CROP // 2])]
    for name, kw in (
        ("NOW  warp + coverage scale", dict(step=K_COVER)),
        ("FIX  coverage scale removed", dict(step=1.0)),
        ("SNAP  integer offset, unit scale", dict(step=1.0, snap=True)),
        ("LANCZOS3  shipped geometry", dict(step=K_COVER, kernel="lanczos3")),
    ):
        panels.append((name, render(img, ci, cj, a, by, bx, **kw)))

    allv = np.concatenate([p.ravel() for _, p in panels])
    lo, hi = np.percentile(allv, 1.0), np.percentile(allv, 99.5)

    box = max(p.shape[0] for _, p in panels)
    pad, lab = 12, 34
    W = len(panels) * (box + pad) + pad
    H = box + lab + 2 * pad + 40
    canvas = Image.new("RGB", (W, H), (18, 18, 18))
    dr = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("consola.ttf", 13)
        small = ImageFont.truetype("consola.ttf", 11)
    except OSError:
        font = small = ImageFont.load_default()

    for i, (name, p) in enumerate(panels):
        x = pad + i * (box + pad)
        n = p.shape[0]
        oy, ox = (box - n) // 2, (box - n) // 2
        canvas.paste(Image.fromarray(norm(p, lo, hi)).convert("RGB"),
                     (x + ox, pad + lab + oy))
        dr.text((x, pad + 8), name, fill=(235, 235, 235), font=font)
        dr.rectangle([x + ox - 1, pad + lab + oy - 1, x + ox + n, pad + lab + oy + n],
                     outline=(70, 70, 70))
        dr.text((x, pad + lab + box + 6), f"{n} x {n} px for the same scene",
                fill=(130, 130, 130), font=small)

    dr.text((pad, H - 20),
            "bee-3-cpl, frame %d (offset %+.3f, %+.3f render px). Every panel "
            "covers the IDENTICAL scene span from the same unresampled decode, "
            "same tone map, no display resampling. No sharpness figure is "
            "printed per panel: the numbers are measured on a band-matched "
            "spectral axis, not on these pixels." % (idx, bx, by),
            fill=(150, 150, 150), font=small)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT)
    print(f"\nwrote {OUT}  ({W}x{H})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
