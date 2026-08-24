"""M84 step 00 - RECONNAISSANCE. Look at the two ruler stacks before designing anything.

This runs BEFORE the pre-registration is frozen and is declared as such in
`PREREGISTRATION.md` section 0. It measures nothing that the pre-registration
commits to; it exists to answer "are graduations visible at all, and at what
spacing", which is design input for the method and for the accuracy bars.

Reads READ-ONLY from `D:\\personal\\macro`. Rule 32: `raw_image_visible` is a view
into LibRaw's buffer, so every read copies inside the `with` block on the same line.
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
STACKS = ["flat-on-ruler-cpl", "highly-angled-ruler-mm-cpl"]


def green_luma(path: pathlib.Path) -> tuple[np.ndarray, int, int]:
    """(G1 + G2) / 2 on the RGGB quad grid, black-subtracted, plus levels."""
    with rawpy.imread(str(path)) as raw:
        cfa = raw.raw_image_visible.astype(np.float32)
        black = int(np.max(raw.black_level_per_channel))
        white = int(raw.white_level)
        pattern = raw.raw_pattern.copy()
    h, w = cfa.shape
    h -= h % 2
    w -= w % 2
    g1 = cfa[0:h:2, 1:w:2]
    g2 = cfa[1:h:2, 0:w:2]
    del pattern
    return 0.5 * (g1 + g2) - black, black, white


def to_png(plane: np.ndarray, path: pathlib.Path, step: int = 4) -> None:
    small = plane[::step, ::step]
    lo, hi = np.percentile(small, [0.5, 99.5])
    img = np.clip((small - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    Image.fromarray((img * 255).astype(np.uint8)).save(path)


def crop_png(plane: np.ndarray, path: pathlib.Path, box: tuple[int, int, int, int]) -> None:
    y0, y1, x0, x1 = box
    sub = plane[y0:y1, x0:x1]
    lo, hi = np.percentile(sub, [0.5, 99.5])
    img = np.clip((sub - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
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
            ph, pw = plane.shape
            crop_png(
                plane,
                OUT / f"crop-{stack}-f{i:03d}.png",
                (ph // 2 - 300, ph // 2 + 300, pw // 2 - 400, pw // 2 + 400),
            )
            print(
                f"  f{i:03d} {frames[i].name}: plane {pw}x{ph} "
                f"black={black} white={white} "
                f"mean={plane.mean():.1f} p01={np.percentile(plane, 1):.1f} "
                f"p99={np.percentile(plane, 99):.1f} max={plane.max():.1f}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
