"""Find the worst-disagreeing tile between two arms and crop it for the eye.

The owner's guard is judged by LOOKING.  But three frozen ROIs can miss a
localised degradation somewhere else in a 7040x4688 frame.  So this does not
score anything -- it only *directs the eye*: it ranks 256px tiles by how much
the two arms disagree and writes a 100% side-by-side of the worst ones.

The statistic decides where to look.  It does not decide the verdict.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
import numpy as np
import tifffile
from PIL import Image

RENDERS = Path(r"C:\dev\strehl-out\BUILD-SHARP\renders")
PICS = Path(r"C:\dev\strehl-out\BUILD-SHARP\pictures")
TILE = 256


def read_linear(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p} is {a.dtype}, expected uint16"
    return a.astype(np.float32)


def develop(lin: np.ndarray, gain: float) -> np.ndarray:
    x = np.clip(lin / 65535.0 * gain, 0.0, 1.0)
    return (np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055) * 255.0).astype(np.uint8)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--before", default="guard-BEFORE")
    ap.add_argument("--after", default="guard-AFTER")
    ap.add_argument("--top", type=int, default=2)
    a = ap.parse_args()

    b = read_linear(RENDERS / a.subject / a.before / "linear.tif")
    c = read_linear(RENDERS / a.subject / a.after / "linear.tif")
    assert b.shape == c.shape, f"shape mismatch {b.shape} vs {c.shape}"

    # Shared display gain from the BEFORE arm only (M20 C3).
    gain = 0.92 / max(np.percentile(b / 65535.0, 99.7), 1e-6)

    d = np.abs(b - c).max(axis=2)
    h, w = d.shape
    ty, tx = h // TILE, w // TILE
    tiles = d[: ty * TILE, : tx * TILE].reshape(ty, TILE, tx, TILE).max(axis=(1, 3))

    print(f"{a.subject}: {b.shape}, gain={gain:.4f}")
    print(f"  whole-frame max |delta| = {d.max():.0f} DN of 65535 "
          f"({100 * d.max() / 65535:.3f}% full scale)")
    print(f"  pixels differing at all  = {100 * (d > 0).mean():.2f}%")
    print(f"  pixels differing > 1% FS = {100 * (d > 655).mean():.3f}%")

    order = np.dstack(np.unravel_index(np.argsort(tiles, axis=None)[::-1], tiles.shape))[0]
    outdir = PICS / a.subject
    outdir.mkdir(parents=True, exist_ok=True)
    for rank in range(a.top):
        j, i = order[rank]
        y0, x0 = int(j) * TILE, int(i) * TILE
        y0 = min(max(y0 + TILE // 2 - 300, 0), h - 600)
        x0 = min(max(x0 + TILE // 2 - 300, 0), w - 600)
        sl = (slice(y0, y0 + 600), slice(x0, x0 + 600))
        pair = np.concatenate(
            [develop(b[sl], gain), np.zeros((600, 12, 3), np.uint8), develop(c[sl], gain)], axis=1)
        p = outdir / f"guard-worst{rank}-PAIR.png"
        Image.fromarray(pair).save(p)
        print(f"  worst#{rank}: tile max |delta| = {tiles[j, i]:.0f} DN at ({x0},{y0}) -> {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
