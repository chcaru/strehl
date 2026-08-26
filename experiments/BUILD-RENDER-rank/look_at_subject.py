"""Pull 100%% crops from a master at its own highest-detail site, so the
ordering statistic can be checked against the picture rather than argued about.

Why this exists
---------------
ORCH's brief asserts that `contactsheet.py` ranking `foam` first is "the
instrument rather than the picture", because "a p95 gradient cannot distinguish
fine texture from read noise". That is a hypothesis about foam, and it is
testable in five minutes: crop foam at 100%% where the statistic says its detail
lives, and look. Foam is *literally a field of small bubbles* -- fine texture is
the null hypothesis here, not noise.

Method
------
Tile the linear-light luminance into 512-px tiles. For each tile compute the
same noise-corrected detail the ranking statistic uses:

    detail = sqrt(max(0, mean(|grad L|^2) - sigma^2))

with sigma from Immerkaer's kernel over that tile. Emit the top tile and the
median tile as 100%% PNG crops -- no resampling, no JPEG (the artifacts under
examination are exactly what JPEG eats), no tone curve applied on top of the
master's own.

The written PNG is 8-bit taken as the high byte of the sRGB-encoded uint16
master. That is a faithful view of what the eye would see; it is for LOOKING
only and nothing numeric is ever computed from it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile

# Immerkaer's Laplacian-like kernel: zero response to planes, so its mean
# absolute response over a smooth image estimates the white-noise sigma.
IMMERKAER = np.array([[1.0, -2.0, 1.0], [-2.0, 4.0, -2.0], [1.0, -2.0, 1.0]])

REC709 = np.array([0.2126, 0.7152, 0.0722], dtype=np.float64)


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    """Exact inverse of the sRGB transfer curve. Undone before any measurement
    so the noise arithmetic (E[|grad|^2] = sigma^2 for white noise) holds."""
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def load_linear_luma(path: Path, encoded: str) -> np.ndarray:
    arr = tifffile.imread(str(path))
    if arr.dtype != np.uint16:
        raise SystemExit(f"{path.name}: expected uint16, got {arr.dtype}")
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise SystemExit(f"{path.name}: expected HxWx3, got {arr.shape}")
    f = arr.astype(np.float64) / 65535.0
    if encoded == "srgb":
        f = srgb_to_linear(f)
    return f @ REC709


def conv3_valid(img: np.ndarray, k: np.ndarray) -> np.ndarray:
    """Tiny explicit 3x3 valid convolution; avoids a scipy dependency."""
    out = np.zeros((img.shape[0] - 2, img.shape[1] - 2), dtype=np.float64)
    for dy in range(3):
        for dx in range(3):
            w = k[dy, dx]
            if w != 0.0:
                out += w * img[dy : dy + out.shape[0], dx : dx + out.shape[1]]
    return out


def tile_detail(tile: np.ndarray) -> tuple[float, float, float]:
    """Return (detail, raw_grad_rms, sigma) for one tile, all in linear light."""
    gy, gx = np.gradient(tile)
    grad_sq = float(np.mean(gy * gy + gx * gx))
    resp = conv3_valid(tile, IMMERKAER)
    n = resp.size
    sigma = float(np.sqrt(np.pi / 2.0) / (6.0 * n) * np.sum(np.abs(resp))) if n else 0.0
    detail = float(np.sqrt(max(0.0, grad_sq - sigma * sigma)))
    return detail, float(np.sqrt(grad_sq)), sigma


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("masters", nargs="+", help="master TIFF paths")
    ap.add_argument("--out", required=True)
    ap.add_argument("--encoded", choices=["srgb", "linear"], default="srgb")
    ap.add_argument("--tile", type=int, default=512)
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    import cv2

    for mpath in args.masters:
        p = Path(mpath)
        if not p.exists():
            print(f"MISSING {p}")
            continue
        lum = load_linear_luma(p, args.encoded)
        raw = tifffile.imread(str(p))
        t = args.tile
        ny, nx = lum.shape[0] // t, lum.shape[1] // t

        rows = []
        for iy in range(ny):
            for ix in range(nx):
                sub = lum[iy * t : (iy + 1) * t, ix * t : (ix + 1) * t]
                d, g, s = tile_detail(sub)
                rows.append((d, g, s, float(sub.mean()), iy, ix))
        rows.sort(reverse=True)

        picks = [("top", rows[0]), ("median", rows[len(rows) // 2])]
        for label, (d, g, s, lvl, iy, ix) in picks:
            crop = raw[iy * t : (iy + 1) * t, ix * t : (ix + 1) * t, :]
            eight = (crop >> 8).astype(np.uint8)
            name = f"{p.stem}__{label}__y{iy * t}x{ix * t}.png"
            ok = cv2.imwrite(str(outdir / name), eight[:, :, ::-1])
            if not ok:
                raise SystemExit(f"cv2.imwrite failed for {name}")
            print(
                f"{p.stem:38s} {label:6s} y={iy * t:5d} x={ix * t:5d} "
                f"detail={d:.5f} grad={g:.5f} sigma={s:.6f} level={lvl:.4f} "
                f"noise_frac={(s / g if g else 0):.3f}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
