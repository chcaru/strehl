"""Side-by-side crops of the restoration's sigma^2 arms, for LOOKING at.

s31 is the reason this file exists. There the statistic said +50% HF power and
the picture said maze artifact, and the picture was right. ORCH's standing
instruction since: "any arm that improves the band statistic must be looked at
at 1:1 before you recommend it."

SITE SELECTION IS FROM THE OFF ARM ONLY, so an arm under test cannot choose the
crop that flatters it. Three sites, each answering a different question:

  flat   -- a defocused tile. There is no detail here to recover, so anything
            the arm adds is noise or ringing. This is where s31's maze showed.
  sharp  -- the highest-gradient tile. This is where a real restoration must
            show its gain, and if it does not, the arm is buying nothing.
  edge   -- the tile with the strongest single step. Gibbs overshoot lives on
            exactly this geometry and is visible as a bright rim.

Both arms of a pair are stretched with the SAME window, taken from the OFF arm,
so a difference on screen is a difference in the pixels and not in the display.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

TILE = 224
ZOOM = 2


def green(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    return a[:, :, 1].astype(np.float64)


def sites(g: np.ndarray) -> dict[str, tuple[int, int]]:
    h, w = g.shape
    coords, sharp, step = [], [], []
    for y in range(TILE, h - 2 * TILE, TILE):
        for x in range(TILE, w - 2 * TILE, TILE):
            t = g[y:y + TILE, x:x + TILE]
            coords.append((y, x))
            sharp.append(float(np.abs(np.diff(t, axis=0)).mean()
                               + np.abs(np.diff(t, axis=1)).mean()))
            step.append(float(np.abs(np.diff(t, axis=1)).max()))
    sharp = np.asarray(sharp)
    order = np.argsort(sharp)
    # ~2.5th percentile rather than the minimum: the true minimum is often
    # clipped black, where every arm is identical and the crop says nothing.
    return {
        "flat": coords[int(order[len(order) // 40])],
        "sharp": coords[int(order[-1])],
        "edge": coords[int(np.argmax(np.asarray(step)))],
    }


def panel(off: np.ndarray, arm: np.ndarray, y: int, x: int) -> np.ndarray:
    ta = off[y:y + TILE, x:x + TILE]
    tb = arm[y:y + TILE, x:x + TILE]
    lo, hi = float(ta.min()), float(ta.max())
    if hi <= lo:
        hi = lo + 1.0
    sa = np.clip((ta - lo) / (hi - lo), 0, 1)
    sb = np.clip((tb - lo) / (hi - lo), 0, 1)
    rule = np.ones((TILE, 6))
    joined = np.concatenate([sa, rule, sb], axis=1)
    return np.repeat(np.repeat(joined, ZOOM, axis=0), ZOOM, axis=1)


def main() -> int:
    if len(sys.argv) < 4:
        raise SystemExit("usage: restore_crops.py <outdir> <off.tif> <arm.tif> ...")
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    poff = Path(sys.argv[2])
    off = green(poff)
    where = sites(off)
    print(f"sites chosen from {poff.name} (the OFF arm):")
    for k, (y, x) in where.items():
        print(f"  {k:6s} at ({y},{x})")
    for a in sys.argv[3:]:
        pa = Path(a)
        arm = green(pa)
        d = float(np.abs(arm - off).max())
        print(f"\n{pa.stem}: max|arm - off| on green = {d:.1f} DN")
        if d == 0.0:
            print("  arms identical -- crops would be vacuous, skipped")
            continue
        for k, (y, x) in where.items():
            img = panel(off, arm, y, x)
            dst = out / f"{pa.stem}--{k}.png"
            Image.fromarray((img * 255.0 + 0.5).astype(np.uint8)).save(dst)
            print(f"  wrote {dst.name}   left = OFF, right = {pa.stem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
