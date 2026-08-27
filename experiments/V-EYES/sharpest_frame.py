"""Did any frame in the bracket resolve what the master renders soft?

This is the defect that matters most and is hardest to find: softness in the
delivered master at a place where some source frame WAS sharp. If no frame
resolved it, the softness is capture physics -- diffraction, subject motion, or
a focus step too coarse to land on that plane -- and not the stacker's fault.
If a frame did resolve it, the merge threw away detail it was handed, and that
is a bug worth an implementer's time.

Ranking uses the raw green CFA plane, not a demosaic. Demosaicing is
interpolation, and rawpy's kernel is not the tool's Malvar-He-Cutler, so
comparing through two different reconstructions partly measures the
reconstructions. The green plane is real sensor samples: two sites per Bayer
quad, the densest true sampling the sensor offers.

The sharpness metric is Tenengrad (mean squared Sobel gradient magnitude)
computed AFTER a Gaussian blur of sigma 1.5. The blur is the entire point. A
previous version of this measurement ranked frames by std(Laplacian) with no
pre-blur and chose a frame that is visibly defocused across most of the tile,
because shot noise is per-pixel independent and therefore has enormous
Laplacian energy. Defocus blur operates at a much coarser scale than one pixel,
so a sigma 1.5 pre-blur removes most of the noise while leaving the difference
between focused and defocused structure almost untouched.

Frames shift during a focus bracket -- focus breathing changes magnification --
so the tile is searched over a neighbourhood rather than assumed to sit at the
same coordinates in every frame. The best offset per frame is reported; a large
spread across frames is itself informative about how much the aligner had to do.

Only the top few frames are demosaiced, since postprocess on a 33 MP raw is the
expensive step and ranking does not need it.

Usage:
  python sharpest_frame.py <subjectdir> <master.tiff> <x> <y> <size> <outdir>
                           [stride] [search]
"""

import sys
import pathlib
import numpy as np
import tifffile
import cv2
from PIL import Image


def green_plane(path):
    import rawpy

    with rawpy.imread(str(path)) as raw:
        v = raw.raw_image_visible.astype(np.float32).copy()  # view dies with the handle
    g0 = v[0::2, 1::2]
    g1 = v[1::2, 0::2]
    ny, nx = min(g0.shape[0], g1.shape[0]), min(g0.shape[1], g1.shape[1])
    return (g0[:ny, :nx] + g1[:ny, :nx]) * 0.5


def tenengrad(a):
    b = cv2.GaussianBlur(a.astype(np.float32), (0, 0), 1.5)
    gx = cv2.Sobel(b, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(b, cv2.CV_32F, 0, 1, ksize=3)
    return float((gx * gx + gy * gy).mean())


def main():
    subjdir = pathlib.Path(sys.argv[1])
    master = sys.argv[2]
    x, y, size = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    outdir = pathlib.Path(sys.argv[6])
    stride = int(sys.argv[7]) if len(sys.argv) > 7 else 8
    search = int(sys.argv[8]) if len(sys.argv) > 8 else 48
    outdir.mkdir(parents=True, exist_ok=True)

    frames = sorted(subjdir.glob("*.ARW"))
    sel = frames[::stride]
    subject = subjdir.name
    print(f"{subject}: {len(frames)} frames, ranking {len(sel)} (stride {stride})")
    print(f"master tile ({x},{y}) {size}x{size}; green-plane tile "
          f"({x // 2},{y // 2}) {size // 2}x{size // 2}, searched +/-{search // 2} px")

    gx0, gy0, gs = x // 2, y // 2, size // 2
    pad = search // 2
    rows = []
    for p in sel:
        g = green_plane(p)
        best = (-1.0, 0, 0)
        for dy in range(-pad, pad + 1, 8):
            for dx in range(-pad, pad + 1, 8):
                yy, xx = gy0 + dy, gx0 + dx
                if yy < 0 or xx < 0 or yy + gs > g.shape[0] or xx + gs > g.shape[1]:
                    continue
                s = tenengrad(g[yy : yy + gs, xx : xx + gs])
                if s > best[0]:
                    best = (s, dx, dy)
        rows.append((best[0], p, best[1], best[2]))
        print(f"  {p.name}  ten={best[0]:>12.1f}  best offset ({best[1]:+d},{best[2]:+d})")

    rows.sort(key=lambda r: -r[0])
    print()
    print("ranked (noise-suppressed Tenengrad on raw green plane):")
    for s, p, dx, dy in rows[:6]:
        print(f"  {p.name:<16} {s:>12.1f}  offset ({dx:+d},{dy:+d})")
    print(f"  ... worst: {rows[-1][1].name} {rows[-1][0]:.1f}")
    print(f"  sharpest/softest ratio = {rows[0][0] / max(rows[-1][0], 1e-9):.2f}")

    m = tifffile.imread(master)
    mt = (m[y : y + size, x : x + size] / 257.0).round().clip(0, 255).astype(np.uint8)
    mp = outdir / f"{subject}-{x}-{y}-MASTER.png"
    Image.fromarray(mt).save(mp)
    print(f"\nwrote {mp}")

    import rawpy

    for rank, (s, p, dx, dy) in enumerate(rows[:2], 1):
        with rawpy.imread(str(p)) as raw:
            rgb = raw.postprocess(output_bps=8, no_auto_bright=True, use_camera_wb=True)
        yy, xx = y + dy * 2, x + dx * 2
        t = rgb[yy : yy + size, xx : xx + size]
        fp = outdir / f"{subject}-{x}-{y}-FRAME{rank}-{p.stem}.png"
        Image.fromarray(t).save(fp)
        print(f"wrote {fp}  (rawpy demosaic, offset {dx * 2:+d},{dy * 2:+d}, ten={s:.1f})")


if __name__ == "__main__":
    main()
