"""M87 orientation pass (declared, pre-registration): look at the A/B captures.

This script does NOT compute the halo metric. It exists to answer three
questions needed to write the pre-registration:
  1. Are the flower-bud A/B captures visually comparable (framing, exposure)?
  2. What does the "alone" background actually contain?
  3. How long does one rawpy decode take, so the measurement plan is feasible?

Rule 32: rawpy's raw_image_visible is a view into LibRaw's buffer. Copy inside
the `with`.
"""

import sys
import time
from pathlib import Path

import numpy as np
import rawpy
from PIL import Image

OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(parents=True, exist_ok=True)

STACKS = {
    "bee-3-cpl": r"D:\personal\macro\bee-3-cpl",
    "flower-bud-alone-cpl": r"D:\personal\macro\flower-bud-alone-cpl",
    "flower-bud-with-background-fern-cpl": r"D:\personal\macro\flower-bud-with-background-fern-cpl",
}


def frames(d):
    return sorted(Path(d).glob("*.ARW"))


def green_bin(path):
    """Decode one RAW, return (G1+G2)/2 binned to one value per 2x2 quad."""
    t0 = time.time()
    with rawpy.imread(str(path)) as raw:
        vis = raw.raw_image_visible.astype(np.float32)  # copy inside the with
        pat = raw.raw_pattern.copy()
        black = float(np.mean(raw.black_level_per_channel))
        white = float(raw.white_level)
    dt = time.time() - t0
    h, w = vis.shape
    h -= h % 2
    w -= w % 2
    vis = vis[:h, :w]
    # raw_pattern gives the colour index of each of the 2x2 positions.
    # colour index 1 and 3 are the two greens for a Bayer sensor.
    g = np.zeros((h // 2, w // 2), np.float32)
    ng = 0
    for dy in (0, 1):
        for dx in (0, 1):
            if pat[dy, dx] in (1, 3):
                g += vis[dy::2, dx::2]
                ng += 1
    g /= ng
    return g - black, dt, black, white, pat, (h, w)


def main():
    for name, d in STACKS.items():
        fs = frames(d)
        if not fs:
            print(f"{name}: NO FRAMES", flush=True)
            continue
        picks = [0, len(fs) // 2, len(fs) - 1]
        print(f"\n=== {name}: {len(fs)} frames ===", flush=True)
        for i in picks:
            g, dt, black, white, pat, shape = green_bin(fs[i])
            print(
                f"  frame {i:3d} {fs[i].name}  decode {dt:5.2f}s  active {shape}  "
                f"black {black:.1f} white {white:.0f}  "
                f"g-mean {g.mean():8.1f} p1 {np.percentile(g, 1):8.1f} "
                f"p99 {np.percentile(g, 99):8.1f} pat {pat.tolist()}",
                flush=True,
            )
            if i == picks[1]:
                v = np.clip(g / max(np.percentile(g, 99.5), 1.0), 0, 1) ** (1 / 2.2)
                small = (v[::4, ::4] * 255).astype(np.uint8)
                Image.fromarray(small).save(OUT / f"00-{name}-mid.png")
                print(f"    preview -> 00-{name}-mid.png  {small.shape}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
