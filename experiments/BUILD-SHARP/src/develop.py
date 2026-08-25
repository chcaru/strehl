"""Develop linear-sRGB renders to viewable PNGs, identically across arms.

The exposure is computed ONCE from a stated reference arm and then applied
unchanged to every other arm. This is the whole point of the script. Several of
the treatments under test here (photometric correction, Wiener restoration)
change image brightness or contrast, so any per-arm auto-exposure would partly
normalise away the difference being judged, and the comparison would understate
or invert the effect. Fixing the develop outside the render makes the arms
differ only by the treatment.

The exposure rule matches the project's own `--auto-exposure` (M100): put the
99.9th percentile of linear-sRGB luminance at 0.90.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image


def read16(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    if a.dtype != np.uint16:
        raise SystemExit(f"{path}: expected uint16, got {a.dtype}")
    return a


def srgb(lin: np.ndarray) -> np.ndarray:
    """IEC 61966-2-1 transfer curve."""
    a = 0.055
    return np.where(lin <= 0.0031308, 12.92 * lin,
                    (1 + a) * np.power(np.maximum(lin, 0.0), 1 / 2.4) - a)


def exposure_for(rgb: np.ndarray) -> float:
    f = rgb.astype(np.float64) / 65535.0
    y = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
    p = np.percentile(y, 99.9)
    if p <= 0:
        return 1.0
    return float(0.90 / p)


def develop(rgb: np.ndarray, gain: float) -> Image.Image:
    f = rgb.astype(np.float64) / 65535.0 * gain
    return Image.fromarray((np.clip(srgb(f), 0, 1) * 255 + 0.5).astype(np.uint8))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ref", required=True, help="arm that sets the exposure")
    p.add_argument("--arms", nargs="+", required=True, help="NAME=PATH ...")
    p.add_argument("--outdir", required=True)
    p.add_argument("--width", type=int, default=1600, help="full-frame width")
    p.add_argument("--crops", default="", help="NAME:X,Y,W,H;... at 100%")
    a = p.parse_args()

    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    gain = exposure_for(read16(Path(a.ref)))
    print(f"exposure gain {gain:.5f}  ({np.log2(gain):+.3f} stops), from {a.ref}")

    boxes = []
    for spec in filter(None, a.crops.split(";")):
        name, rest = spec.split(":")
        boxes.append((name, *[int(v) for v in rest.split(",")]))

    meta = {"gain": gain, "ref": a.ref, "arms": {}}
    for spec in a.arms:
        name, path = spec.split("=", 1)
        rgb = read16(Path(path))
        img = develop(rgb, gain)
        full = out / f"full-{name}.png"
        img.resize((a.width, round(a.width * img.height / img.width)),
                   Image.LANCZOS).save(full)
        meta["arms"][name] = {"src": path, "full": str(full), "size": img.size}
        for (bn, x, y, w, h) in boxes:
            img.crop((x, y, x + w, y + h)).save(out / f"crop-{bn}-{name}.png")
        print(f"  {name:<12} {img.size} -> {full.name}")

    (out / "develop.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
