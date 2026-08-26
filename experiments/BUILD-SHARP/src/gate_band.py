"""Did lowering the pyramid noise gate actually sharpen the picture?

The hypothesis under test is that on this high-key subject the local band power
falls under the gate, no frame is allowed to win, and the merge falls back to
averaging 205 frames of differing focus -- which is exactly the shape of a
merge that is SOFTER than its own best frame.

Two rules from earlier sections are load-bearing here and are enforced rather
than remembered:

  s33.5  A number is only valid on the subject population it was measured on.
         So tiles are ranked ONCE, by the REFERENCE arm, and reported as three
         separate populations. An arm may not choose its own tiles.

  s31    Measuring in the right band is necessary but not sufficient -- the
         stimulus must exist in the real data too. A gain in the FLATTEST
         population is not detail recovery, it is manufactured texture or
         admitted noise, and on this subject the flat population is the large
         white field. If flat gains as much as sharp, the gate change is not
         buying detail and it must be rejected exactly as Hamilton-Adams was.

Frequencies are cycles per OUTPUT pixel (f_out), the convention used throughout
this report, so the 0.20-0.40 band is directly comparable to the head-to-head
deficit once converted.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

TILE = 256
BANDS = [(0.05, 0.10), (0.10, 0.20), (0.20, 0.30), (0.30, 0.40), (0.40, 0.48)]


def luma(p: Path) -> np.ndarray:
    a = tifffile.imread(p).astype(np.float64)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def tiles(h: int, w: int):
    for y in range(TILE, h - 2 * TILE, TILE):
        for x in range(TILE, w - 2 * TILE, TILE):
            yield y, x


def band_power(t: np.ndarray, masks) -> np.ndarray:
    win = np.outer(np.hanning(TILE), np.hanning(TILE))
    f = np.fft.fftshift(np.fft.fft2((t - t.mean()) * win))
    p = (f.real ** 2 + f.imag ** 2)
    return np.array([p[m].mean() for m in masks])


def main() -> int:
    paths = [Path(a) for a in sys.argv[1:]]
    if len(paths) < 2:
        raise SystemExit("usage: gate_band.py <reference.tif> <arm.tif> [arm2.tif ...]")

    fy = np.fft.fftshift(np.fft.fftfreq(TILE))[:, None]
    fx = np.fft.fftshift(np.fft.fftfreq(TILE))[None, :]
    r = np.hypot(fy, fx)
    masks = [(r >= lo) & (r < hi) for lo, hi in BANDS]

    ref = luma(paths[0])
    h, w = ref.shape
    coords = list(tiles(h, w))

    # Rank tiles ONCE, on the reference arm, by mean gradient magnitude.
    sharp = []
    for y, x in coords:
        t = ref[y:y + TILE, x:x + TILE]
        gy, gx = np.gradient(t)
        sharp.append(np.hypot(gy, gx).mean())
    order = np.argsort(sharp)
    n = len(order)
    pops = {
        "flattest 5%": order[: max(1, n // 20)],
        "median 10%": order[n // 2 - n // 20: n // 2 + n // 20],
        "sharpest 5%": order[-max(1, n // 20):],
    }
    print(f"{n} tiles of {TILE}px, ranked once on {paths[0].name}")

    per_arm = {}
    for p in paths:
        img = luma(p)
        acc = np.zeros((n, len(BANDS)))
        for i, (y, x) in enumerate(coords):
            acc[i] = band_power(img[y:y + TILE, x:x + TILE], masks)
        per_arm[p.name] = acc

    base = per_arm[paths[0].name]
    for name in list(per_arm)[1:]:
        print(f"\n  {name}  /  {paths[0].name}")
        hdr = "".join(f"{f'{lo:.2f}-{hi:.2f}':>12s}" for lo, hi in BANDS)
        print(f"    {'population':>14s}{hdr}")
        for label, idx in pops.items():
            ratio = per_arm[name][idx].mean(axis=0) / base[idx].mean(axis=0)
            row = "".join(f"{v:12.4f}" for v in ratio)
            print(f"    {label:>14s}{row}")
        flat = (per_arm[name][pops["flattest 5%"]].mean(axis=0)
                / base[pops["flattest 5%"]].mean(axis=0))
        shp = (per_arm[name][pops["sharpest 5%"]].mean(axis=0)
               / base[pops["sharpest 5%"]].mean(axis=0))
        b = 2  # the 0.20-0.30 band, the head-to-head deficit band
        verdict = ("DETAIL" if shp[b] > flat[b] * 1.05 else
                   "NOT DETAIL -- flat gains as much as sharp (s31 rule)")
        print(f"    0.20-0.30: sharp {shp[b]:.4f} vs flat {flat[b]:.4f}  -> {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
