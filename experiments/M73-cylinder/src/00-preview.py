"""M73 step 00 — look at the subject before designing anything against it.

Reads a handful of frames from each `wrapped-text` stack READ-ONLY, decodes the
green plane the way `green_luma_with_clip` does (G1/G2 mean of the RGGB quad),
downsamples, and writes 8-bit PNG previews plus a per-frame level summary.

Rule 32: `raw_image_visible` is a view into LibRaw's buffer. Every read here
copies inside the `with` block on the same line.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import rawpy
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
CORPUS = pathlib.Path(r"D:\personal\macro")
STACKS = ["wrapped-text-1", "wrapped-text-2"]


def green_luma(path: pathlib.Path) -> tuple[np.ndarray, int, int]:
    """(G1 + G2) / 2 on the RGGB quad grid, plus black/white levels."""
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float32)
        black = int(np.max(raw.black_level_per_channel))
        white = int(raw.white_level)
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    g1 = cfa[0:h:2, 1:w:2]
    g2 = cfa[1:h:2, 0:w:2]
    return 0.5 * (g1 + g2) - black, black, white


def to_png(plane: np.ndarray, path: pathlib.Path, step: int = 4) -> None:
    small = plane[::step, ::step]
    lo, hi = np.percentile(small, [0.5, 99.5])
    img = np.clip((small - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    Image.fromarray((img * 255).astype(np.uint8)).save(path)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for stack in STACKS:
        d = CORPUS / stack
        frames = sorted(d.glob("*.ARW"))
        if not frames:
            print(f"FATAL: {d} holds no ARW files", file=sys.stderr)
            return 2
        print(f"{stack}: {len(frames)} frames")
        picks = [0, len(frames) // 4, len(frames) // 2, 3 * len(frames) // 4, len(frames) - 1]
        for i in picks:
            plane, black, white = green_luma(frames[i])
            to_png(plane, OUT / f"preview-{stack}-f{i:03d}.png")
            print(
                f"  f{i:03d} {frames[i].name}: plane {plane.shape[1]}x{plane.shape[0]} "
                f"black={black} white={white} "
                f"mean={plane.mean():.1f} p01={np.percentile(plane, 1):.1f} "
                f"p99={np.percentile(plane, 99):.1f} max={plane.max():.1f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
