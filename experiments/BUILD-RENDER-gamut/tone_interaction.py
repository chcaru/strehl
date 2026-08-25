"""What the tone rendering does to the out-of-gamut pixels, and what a
luminance-preserving gamut map would do instead.

Two questions, both of which have to be answered in numbers before touching the
Rust:

  1. The tone stage subtracts a black point IN LINEAR LIGHT, per channel, before
     the clamp. Blue is the channel already sitting closest to zero, so black
     subtraction necessarily pushes more blue pixels below zero. How many more?
     "The fix makes it worse" is a mechanism, not a measurement.

  2. A hard clamp to zero is not a neutral act. It RAISES a negative channel,
     which lightens the pixel and desaturates it by an uncontrolled amount, and
     because the three channels are clamped independently it moves hue. The
     alternative is to desaturate toward the neutral of the SAME luminance --
     the minimum amount needed to bring the triple inside [0, 1]. That preserves
     luminance exactly, preserves hue direction, and is the identity for every
     pixel already inside the gamut. How different are the two, in pixels?

Reports both ends of the range, because a saturated highlight clamped at 1.0 is
the same defect as a saturated shadow clamped at 0.0 and the same map fixes it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from crop_set import A7C2_CAM_TO_SRGB  # noqa: E402

BT709 = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
# Matches image_out.rs.
BLACK_PCT, WHITE_PCT, WHITE_TARGET = 0.1, 99.9, 0.90


def tone_of(srgb: np.ndarray) -> tuple[float, float]:
    lum = srgb @ BT709
    black = float(np.percentile(lum, BLACK_PCT))
    white = black + max(float(np.percentile(lum, WHITE_PCT)) - black, 1e-4) / WHITE_TARGET
    return black, white


def gamut_map(v: np.ndarray) -> np.ndarray:
    """Desaturate toward the neutral of the same luminance, minimally.

    Identical in intent to the Rust this is a rehearsal for. `t` is the smallest
    blend toward grey that brings every channel inside [0, 1]; `t == 0` for an
    in-gamut pixel, so this is exactly the identity where nothing is wrong.
    """
    y = np.clip(v @ BT709, 0.0, 1.0)[..., None]
    t = np.zeros(v.shape[:-1] + (1,), dtype=np.float32)
    below = v < 0.0
    d = np.where(below, y - v, 1.0)
    t = np.maximum(t, np.where(below & (d > 1e-6), -v / np.maximum(d, 1e-6), 0.0).max(-1, keepdims=True))
    above = v > 1.0
    d = np.where(above, v - y, 1.0)
    t = np.maximum(t, np.where(above & (d > 1e-6), (v - 1.0) / np.maximum(d, 1e-6), 0.0).max(-1, keepdims=True))
    t = np.clip(t, 0.0, 1.0)
    return np.clip(v + (y - v) * t, 0.0, 1.0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tiffs", nargs="+", type=Path)
    ap.add_argument("--stride", type=int, default=3)
    a = ap.parse_args()
    m = A7C2_CAM_TO_SRGB.astype(np.float32)

    for t in a.tiffs:
        raw = tifffile.imread(t)
        assert raw.dtype == np.uint16, f"{t} is {raw.dtype}"
        cam = raw[:: a.stride, :: a.stride].astype(np.float32) / 65535.0
        srgb = cam @ m.T
        black, white = tone_of(srgb)
        toned = (srgb - black) / (white - black)

        print(f"{t.stem}   tone black {black:.5f} white {white:.5f}")
        for label, v in (("before tone", srgb), ("after tone ", toned)):
            lo = (v < 0.0).mean(axis=(0, 1)) * 100
            hi = (v > 1.0).mean(axis=(0, 1)) * 100
            print(
                f"   {label}: below 0  R {lo[0]:6.2f}%  G {lo[1]:6.2f}%  B {lo[2]:6.2f}%"
                f"   |   above 1  R {hi[0]:5.2f}%  G {hi[1]:5.2f}%  B {hi[2]:5.2f}%"
            )

        hard = np.clip(toned, 0.0, 1.0)
        soft = gamut_map(toned)
        d = np.abs(hard - soft)
        moved = (d.max(-1) > 1.0 / 65535.0)
        print(
            f"   hard clamp vs luminance-preserving map: {moved.mean()*100:6.2f}% of pixels differ, "
            f"max delta {d.max():.4f}, p99.9 of movers {np.percentile(d.max(-1)[moved], 99.9) if moved.any() else 0:.4f}"
        )
        # The thing a hard clamp actually breaks: it does not preserve luminance.
        yh, ys, y0 = hard @ BT709, soft @ BT709, np.clip(toned @ BT709, 0, 1)
        print(
            f"   luminance error vs the unclamped ideal: hard clamp p99.9 {np.percentile(np.abs(yh-y0),99.9):.5f}, "
            f"map p99.9 {np.percentile(np.abs(ys-y0),99.9):.5f}"
        )
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
