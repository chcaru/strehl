"""ORCH-owned. Extract 1:1 crops from delivered masters at the highest-detail site.

A verdict on sharpness is only valid at 1:1. This picks the crop location by
measured local gradient energy rather than by my guess, so I cannot unconsciously
steer the crop toward a flattering patch.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

SRC = Path(r"C:\dev\strehl-out\DELIVER-V5\full-resolution")
DST = Path(r"C:\dev\strehl-out\ORCH-crops")
DST.mkdir(parents=True, exist_ok=True)

CROP = 400
GRID = 24  # coarse search grid


def best_site(g: np.ndarray, crop: int) -> tuple[int, int]:
    """Return (y, x) of the crop window with the most gradient energy."""
    h, w = g.shape
    gy = np.abs(np.diff(g, axis=0))[:, : w - 1]
    gx = np.abs(np.diff(g, axis=1))[: h - 1, :]
    e = gy + gx
    best, by, bx = -1.0, 0, 0
    ys = np.linspace(0, max(0, h - crop - 1), GRID).astype(int)
    xs = np.linspace(0, max(0, w - crop - 1), GRID).astype(int)
    for y in ys:
        for x in xs:
            v = float(e[y : y + crop, x : x + crop].mean())
            if v > best:
                best, by, bx = v, int(y), int(x)
    return by, bx


def main(names: list[str]) -> int:
    for name in names:
        p = SRC / f"{name}.png"
        if not p.exists():
            print(f"MISSING {p}")
            return 2
        im = Image.open(p)
        a = np.asarray(im)
        g = a[..., :3].astype(np.float32).mean(axis=2) if a.ndim == 3 else a.astype(np.float32)
        # ignore a 5% border: alignment crop edges are not representative
        m = int(min(g.shape) * 0.05)
        y, x = best_site(g[m:-m, m:-m], CROP)
        y += m
        x += m
        out = DST / f"{name}__1to1_{x}_{y}.png"
        im.crop((x, y, x + CROP, y + CROP)).save(out)
        print(f"{name}: {a.shape[1]}x{a.shape[0]} bitdepth={a.dtype} -> ({x},{y}) -> {out.name}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: orch_crops.py <name> [<name>...]")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1:]))
