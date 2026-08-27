"""Crop the masters where a seam would SHOW, not where the texture is finest.

The gallery picks its 100% crop by maximum high-frequency energy, deliberately, so the
crop lands on the finest detail in the frame. That is the right choice for judging
resolution and the worst possible one for finding blocky election seams: a lattice
discontinuity is buried by texture and stands out in smooth tone. Every 1:1 crop anyone
has looked at tonight was selected to land where this defect is least visible.

So this inverts the selector. For each subject it finds the CROP-sized block with the
*lowest* high-frequency energy that is still real image -- excluding near-black and
near-clipped blocks, which are smooth for the uninteresting reason -- and writes it at
1:1 with a mild linear stretch so that low-amplitude steps are actually visible on a
screen. The stretch is stated on the filename and is linear, so it cannot manufacture an
edge that is not there; it can only make a real one large enough to see.

My spectral seam detector failed to commission at 16 bits, so it certifies nothing.
Tonight an eye at 1:1 beat three of my own statistics on a defect they all reported
absent. This is the instrument that has been working.
"""
import pathlib
import sys

import numpy as np
import tifffile
from PIL import Image

CROP = 900
STEP = 300


def hf_energy(blk):
    f = np.fft.fftshift(np.fft.fft2(blk - blk.mean()))
    F = np.abs(f)
    h, w = blk.shape
    fy = (np.arange(h) - h / 2)[:, None] / (h / 2)
    fx = (np.arange(w) - w / 2)[None, :] / (w / 2)
    r = np.sqrt(fy ** 2 + fx ** 2)
    return float((F[(r > 0.20) & (r <= 0.45)] ** 2).sum())


def pick_smooth(lum):
    """Lowest-texture block that is still real image, not black and not clipped."""
    h, w = lum.shape
    lo_gate, hi_gate = 0.06 * 65535, 0.94 * 65535
    best, by, bx, bmean = None, 0, 0, 0.0
    for y in range(0, max(1, h - CROP), STEP):
        for x in range(0, max(1, w - CROP), STEP):
            blk = lum[y:y + CROP, x:x + CROP]
            if blk.shape != (CROP, CROP):
                continue
            m = float(blk.mean())
            if m < lo_gate or m > hi_gate:
                continue
            e = hf_energy(blk[::3, ::3])
            if best is None or e < best:
                best, by, bx, bmean = e, y, x, m
    return by, bx, best, bmean


def main(paths, outdir):
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    print(f"{'subject':30s} {'crop':>16s} {'mean':>8s} {'p1..p99 DN':>16s} {'gain':>6s}")
    print("-" * 84)
    for p in paths:
        p = pathlib.Path(p)
        a = tifffile.imread(str(p))
        rgb = a[:, :, :3].astype(np.float32)
        lum = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
        y0, x0, e, m = pick_smooth(lum)
        if e is None:
            print(f"{p.stem[:30]:30s} {'no eligible block':>16s}")
            continue
        blk = rgb[y0:y0 + CROP, x0:x0 + CROP]
        lo = np.percentile(blk, 1.0)
        hi = np.percentile(blk, 99.0)
        span = max(hi - lo, 1.0)
        gain = 65535.0 / span
        v = np.clip((blk - lo) * (255.0 / span), 0, 255).astype(np.uint8)
        name = f"{p.stem}--smooth-{x0}x{y0}--stretch{gain:.0f}x.png"
        Image.fromarray(v).save(out / name)
        print(f"{p.stem[:30]:30s} {f'({x0},{y0})':>16s} {m/65535:8.3f} "
              f"{f'{lo:.0f}..{hi:.0f}':>16s} {gain:5.1f}x")
        del a, rgb, lum, blk, v
    print(f"\nwrote to {out}")
    print("A blocky seam appears here as straight horizontal or vertical steps on a "
          "regular pitch. Texture cannot hide it and the stretch is linear, so any "
          "straight edge on a lattice is real.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:-1], sys.argv[-1]))
