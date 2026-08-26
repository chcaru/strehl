"""Is the gate-lowering gain additive noise, or is any of it real detail?

The ratio table alone cannot answer this. A uniform additive noise floor raises
every tile's band power by the SAME ABSOLUTE amount, which reads as a huge
ratio in a flat tile and a small ratio in a sharp one -- exactly the shape of
the observed 10.16x / 1.27x split. Recovered detail is different in kind: it is
proportional to the detail already present, so it raises the sharp population
by a LARGER absolute amount than the flat one.

So the discriminator is absolute delta power, not ratio:

  delta constant across populations  -> additive noise, gate change rejected
  delta grows with tile sharpness    -> real recovered detail, worth pursuing

This is the same instrument-discipline point as s31: the ratio is measured in
the right band, but the right band is not sufficient. The quantity has to be
one the two hypotheses actually disagree about.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

TILE = 256
BANDS = [(0.20, 0.30), (0.30, 0.40)]


def luma(p: Path) -> np.ndarray:
    a = tifffile.imread(p).astype(np.float64)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def main() -> int:
    ref_p, arm_p = Path(sys.argv[1]), Path(sys.argv[2])
    fy = np.fft.fftshift(np.fft.fftfreq(TILE))[:, None]
    fx = np.fft.fftshift(np.fft.fftfreq(TILE))[None, :]
    r = np.hypot(fy, fx)
    masks = [(r >= lo) & (r < hi) for lo, hi in BANDS]
    win = np.outer(np.hanning(TILE), np.hanning(TILE))

    ref, arm = luma(ref_p), luma(arm_p)
    h, w = ref.shape
    coords = [(y, x) for y in range(TILE, h - 2 * TILE, TILE)
              for x in range(TILE, w - 2 * TILE, TILE)]

    def power(t):
        f = np.fft.fftshift(np.fft.fft2((t - t.mean()) * win))
        p = f.real ** 2 + f.imag ** 2
        return np.array([p[m].mean() for m in masks])

    sharp, pr, pa = [], [], []
    for y, x in coords:
        t = ref[y:y + TILE, x:x + TILE]
        gy, gx = np.gradient(t)
        sharp.append(np.hypot(gy, gx).mean())
        pr.append(power(t))
        pa.append(power(arm[y:y + TILE, x:x + TILE]))
    sharp = np.asarray(sharp)
    pr, pa = np.asarray(pr), np.asarray(pa)
    order = np.argsort(sharp)
    n = len(order)

    print(f"{arm_p.name}  minus  {ref_p.name}")
    print(f"{n} tiles, ranked on the reference arm\n")
    pops = [
        ("flattest 20%", order[: n // 5]),
        ("2nd quintile", order[n // 5: 2 * n // 5]),
        ("3rd quintile", order[2 * n // 5: 3 * n // 5]),
        ("4th quintile", order[3 * n // 5: 4 * n // 5]),
        ("sharpest 20%", order[4 * n // 5:]),
    ]
    for bi, (lo, hi) in enumerate(BANDS):
        print(f"  band {lo:.2f}-{hi:.2f} cyc/px_out")
        print(f"    {'population':>14s} {'ref power':>14s} {'ABS delta':>14s} {'ratio':>8s}")
        deltas = []
        for label, idx in pops:
            rp = pr[idx, bi].mean()
            ap = pa[idx, bi].mean()
            deltas.append(ap - rp)
            print(f"    {label:>14s} {rp:14.1f} {ap - rp:14.1f} {ap / rp:8.3f}")
        d = np.array(deltas)
        spread = d.max() / max(d.min(), 1e-9)
        trend = "GROWS with sharpness" if d[-1] > d[0] * 1.5 else (
            "FLAT across populations" if spread < 2.0 else "falls with sharpness")
        print(f"    absolute delta {trend};  max/min = {spread:.2f}")
        if spread < 2.0:
            print("    -> ADDITIVE NOISE. Constant power added regardless of content.")
        elif d[-1] > d[0] * 1.5:
            print("    -> content-proportional: consistent with real recovered detail.")
        else:
            print("    -> anti-correlated with detail: not detail recovery.")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
