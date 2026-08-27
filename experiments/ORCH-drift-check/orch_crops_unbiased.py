"""ORCH-owned. Unbiased crop sampling — the companion to orch_crops.py.

orch_crops.py picks the highest-gradient window, which is the site where the
stack most likely SUCCEEDED. A verdict from it is selection-biased by
construction: it answers "how good is the best part" and I read it as "how good
is the image". This draws sites without reference to the outcome.

Modes:
  random  -- N sites from a fixed seed, no reference to content at all
  worst   -- the lowest-gradient window that is NOT background (background is
             genuinely featureless and proves nothing); i.e. the softest place
             that still has something in it
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
GRID = 24
SEED = 20260824


def energy(g: np.ndarray) -> np.ndarray:
    h, w = g.shape
    return np.abs(np.diff(g, axis=0))[:, : w - 1] + np.abs(np.diff(g, axis=1))[: h - 1, :]


def windows(e: np.ndarray, crop: int):
    h, w = e.shape
    ys = np.linspace(0, max(0, h - crop - 1), GRID).astype(int)
    xs = np.linspace(0, max(0, w - crop - 1), GRID).astype(int)
    for y in ys:
        for x in xs:
            yield int(y), int(x), float(e[y : y + crop, x : x + crop].mean())


def main(mode: str, names: list[str]) -> int:
    rng = np.random.default_rng(SEED)
    for name in names:
        p = SRC / f"{name}.png"
        if not p.exists():
            print(f"MISSING {p}")
            return 2
        im = Image.open(p)
        a = np.asarray(im)
        g = a[..., :3].astype(np.float32).mean(axis=2) if a.ndim == 3 else a.astype(np.float32)
        m = int(min(g.shape) * 0.05)
        sub = g[m:-m, m:-m]

        if mode == "random":
            H, W = sub.shape
            for i in range(3):
                y = int(rng.integers(0, H - CROP))
                x = int(rng.integers(0, W - CROP))
                out = DST / f"{name}__RAND{i}_{x+m}_{y+m}.png"
                im.crop((x + m, y + m, x + m + CROP, y + m + CROP)).save(out)
                print(f"{name} rand{i}: ({x+m},{y+m}) -> {out.name}")
        elif mode == "worst":
            e = energy(sub)
            ws = sorted(windows(e, CROP), key=lambda t: t[2])
            # skip genuinely featureless background: a flat backdrop proves
            # nothing about stacking. 20% was too low on subjects with large
            # clean backdrops (bee-1, tweezers both landed on empty backdrop),
            # so require the window to sit in the upper half of energy.
            floor = np.percentile([t[2] for t in ws], 55)
            pick = next(t for t in ws if t[2] >= floor)
            y, x, v = pick
            out = DST / f"{name}__WORST_{x+m}_{y+m}.png"
            im.crop((x + m, y + m, x + m + CROP, y + m + CROP)).save(out)
            print(f"{name} worst: ({x+m},{y+m}) energy={v:.3f} -> {out.name}")
        else:
            print(f"unknown mode {mode}")
            return 2
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: orch_crops_unbiased.py <random|worst> <name> [<name>...]")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2:]))
