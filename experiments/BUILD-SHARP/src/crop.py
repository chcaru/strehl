"""Crop a named full-resolution window from a rendered arm, at 100%, no annotations."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np
import tifffile
from PIL import Image

RENDERS = Path(r"C:\dev\strehl-out\BUILD-SHARP\renders")


def develop(lin: np.ndarray, gain: float) -> np.ndarray:
    x = np.clip(lin / 65535.0 * gain, 0.0, 1.0)
    return (np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055) * 255.0).astype(np.uint8)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--arm", default="guard-AFTER")
    ap.add_argument("--box", required=True, help="x,y,w,h in FULL-RES output pixels")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gain", type=float, default=0.0)
    ap.add_argument("--scale", type=int, default=1)
    a = ap.parse_args()

    p = RENDERS / a.subject / a.arm / "linear.tif"
    img = tifffile.imread(str(p))
    assert img.dtype == np.uint16, f"{p} is {img.dtype}"
    lin = img.astype(np.float32)
    gain = a.gain if a.gain > 0 else 0.92 / max(np.percentile(lin / 65535.0, 99.7), 1e-6)

    x, y, w, h = (int(v) for v in a.box.split(","))
    H, W = lin.shape[:2]
    x, y = max(0, min(x, W - w)), max(0, min(y, H - h))
    crop = develop(lin[y:y + h, x:x + w], gain)
    im = Image.fromarray(crop)
    if a.scale != 1:
        im = im.resize((w * a.scale, h * a.scale), Image.NEAREST)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    im.save(a.out)
    print(f"{a.subject}/{a.arm} {W}x{H} gain={gain:.4f} -> {a.out}  box=({x},{y},{w},{h})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
