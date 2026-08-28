"""Commission `bleedband.py`: plant a known border error and require detection.

Usage:
    python plantcheck.py <scale.tiff> <crop.tiff> <k> <x0> <y0> <W> <H>

A ratio detector that reads 1.14 at the border is only worth believing if it
reads 1.00 when there is nothing there and reads 1.02 when exactly 2% has been
planted. This does both, on the real renders, and reports the detection floor.

Arm NULL   : crop compared against ITSELF through the same mapping. Any
             departure from 1.000 is the tool's own error -- resampling bias,
             mapping error, band bookkeeping -- and bounds what it can resolve.
Arm PLANT  : a known multiplicative error applied to the crop render inside a
             known border width. The detector must recover it.

The null arm is the important one. It shares every step with the real
measurement except the effect under test, so whatever it reports is noise.
"""

import subprocess
import sys
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent


def bands(crop, scale, k, x0, y0, W, H):
    """mean(crop)/mean(scale mapped to crop grid) in bands from the border."""
    cx, cy = W * 0.5, H * 0.5
    ch, cw = crop.shape[0], crop.shape[1]
    RX, RY = np.meshgrid(np.arange(cw, dtype=np.float64), np.arange(ch, dtype=np.float64))
    PX = np.clip(cx + (RX + x0 - cx) / k, 0.0, scale.shape[1] - 1.001)
    PY = np.clip(cy + (RY + y0 - cy) / k, 0.0, scale.shape[0] - 1.001)
    ix, iy = np.floor(PX).astype(np.int64), np.floor(PY).astype(np.int64)
    fx, fy = (PX - ix)[..., None], (PY - iy)[..., None]
    a, b = scale[iy, ix], scale[iy, ix + 1]
    c, d = scale[iy + 1, ix], scale[iy + 1, ix + 1]
    pred = (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
    dist = np.minimum(np.minimum(RX, cw - 1 - RX), np.minimum(RY, ch - 1 - RY))
    out = []
    for lo, hi in [(0, 2), (4, 8), (16, 32), (64, 128), (128, 10**9)]:
        m = (dist >= lo) & (dist < hi)
        out.append((lo, hi, crop[..., 1][m].mean() / pred[..., 1][m].mean()))
    return out


def show(tag, rows):
    txt = "  ".join(f"{lo}-{hi if hi < 10**8 else ''}:{r:.6f}" for lo, hi, r in rows)
    print(f"{tag:<26} {txt}")


def main() -> int:
    s = np.asarray(tifffile.imread(sys.argv[1])).astype(np.float64)
    c = np.asarray(tifffile.imread(sys.argv[2])).astype(np.float64)
    k = float(sys.argv[3])
    x0, y0, W, H = (int(v) for v in sys.argv[4:8])

    print("== REAL (crop vs scale)")
    show("real", bands(c, s, k, x0, y0, W, H))

    # NULL: compare crop against a unity-scale copy of itself, mapped the same
    # way. k=1 with the crop placed back at its own origin is the identity.
    print("\n== NULL (crop vs itself through the same mapping; must read 1.000000)")
    selfscale = np.zeros_like(s)
    selfscale[y0 : y0 + c.shape[0], x0 : x0 + c.shape[1]] = c
    show("null k=1", bands(c, selfscale, 1.0, x0, y0, W, H))

    print("\n== PLANT (known error in the outer 8 px of crop; detector must recover it)")
    ch, cw = c.shape[0], c.shape[1]
    RX, RY = np.meshgrid(np.arange(cw), np.arange(ch))
    dist = np.minimum(np.minimum(RX, cw - 1 - RX), np.minimum(RY, ch - 1 - RY))
    edge = (dist < 8)[..., None]
    for g in (1.10, 1.02, 1.005, 1.001):
        planted = np.where(edge, c * g, c)
        rows = bands(planted, selfscale, 1.0, x0, y0, W, H)
        got = rows[0][2]
        ok = "PASS" if abs(got - g) < 0.0005 else "MISS"
        show(f"plant x{g:.3f} -> {got:.6f} {ok}", rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
