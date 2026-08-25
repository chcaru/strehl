"""Crop a render at 100% -- one output pixel per sensor pixel, no resampling.

A downsampled full frame hides exactly the defects a texture guard exists to
catch. Shrinking an image is a low-pass filter, so per-pixel noise, ringing on
fine detail, and a window that shrank too far all average away and the picture
looks fine. `couch-fibers-cpl` is a guard against precisely those, so it has to
be judged where they live.

No resampling at all here: an integer crop, the plan's own display gain, and a
straight 16 -> 8 bit conversion. Anything that appears in the output appears in
the render.
"""

import argparse
import json
import pathlib

import numpy as np
import tifffile
from PIL import Image

PLAN = pathlib.Path(r"C:\dev\strehl-out\roi-plan.json")


def gain_for(subject: str) -> float:
    if not PLAN.exists():
        return 1.0
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    for entry in plan if isinstance(plan, list) else plan.get("subjects", []):
        if entry.get("subject") == subject or entry.get("name") == subject:
            return float(entry.get("display_gain", 1.0))
    return 1.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--subject", default="")
    ap.add_argument("--size", type=int, default=900)
    # Fraction of the frame, so the same crop lands on the same content in any
    # arm of the same subject. Arms of one subject share a pixel grid; single
    # frames do NOT, and this tool must not be pointed at those.
    ap.add_argument("--cx", type=float, default=0.5)
    ap.add_argument("--cy", type=float, default=0.5)
    ap.add_argument("--gain", type=float, default=0.0)
    a = ap.parse_args()

    img = tifffile.imread(a.src)
    assert img.dtype == np.uint16, f"expected uint16, got {img.dtype}"
    assert img.ndim == 3 and img.shape[2] == 3, f"expected RGB, got {img.shape}"

    h, w, _ = img.shape
    n = a.size
    x0 = int(round(a.cx * w)) - n // 2
    y0 = int(round(a.cy * h)) - n // 2
    x0 = max(0, min(w - n, x0))
    y0 = max(0, min(h - n, y0))
    crop = img[y0 : y0 + n, x0 : x0 + n, :].astype(np.float32)

    g = a.gain if a.gain > 0 else gain_for(a.subject or pathlib.Path(a.src).stem)
    out = np.clip(crop * g / 65535.0, 0.0, 1.0)
    eight = (out * 255.0 + 0.5).astype(np.uint8)

    dst = pathlib.Path(a.out)
    # tifffile.imwrite ignores the extension and writes TIFF regardless, which
    # has already produced a "PNG" that was not one in this build.
    Image.fromarray(eight, mode="RGB").save(dst)
    magic = dst.read_bytes()[:4]
    assert magic == b"\x89PNG", f"not a PNG: {magic!r}"
    print(f"wrote {dst}  {n}x{n} at 100% from ({x0},{y0})  gain {g:.4f}")


if __name__ == "__main__":
    main()
