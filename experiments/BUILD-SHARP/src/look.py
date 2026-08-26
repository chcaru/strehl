"""Look at a render: whole-frame overview plus 1:1 crops at chosen sites.

Written for `flower-bud-alone-cpl`, which V-bestframe scores worst in the corpus
(median merge-to-best-frame 0.82) and which ORCH independently flagged by eye as
the one visibly soft subject of 26. The statistic and the eye agreeing is the
reason this is worth looking at rather than only measuring.

Sites are chosen by gradient rank so the crop is not cherry-picked by hand, and
the overview is included because a "milky veil" is a LOW-frequency complaint
that a 1:1 crop can hide entirely.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

TILE = 320


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: look.py <render.tif> <outdir>")
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    a = tifffile.imread(str(src))
    print(f"{src.name}: {a.shape}, dtype {a.dtype}")
    rgb = a.astype(np.float64) / 65535.0

    # Clipping census first -- ORCH warns this subject's highlight is clipped,
    # and a clipped region is not evidence about sharpness either way.
    for i, ch in enumerate("RGB"):
        c = a[:, :, i]
        print(f"  {ch}: min {c.min():5d}  max {c.max():5d}  "
              f"clipped-high {100.0*np.count_nonzero(c >= 65535)/c.size:.4f}%  "
              f"at-zero {100.0*np.count_nonzero(c == 0)/c.size:.4f}%")

    ov = (rgb[::8, ::8] ** (1 / 1.0) * 255.0 + 0.5).clip(0, 255).astype(np.uint8)
    Image.fromarray(ov).save(out / f"{src.stem}--overview.png")
    print(f"  wrote {src.stem}--overview.png  ({ov.shape[1]}x{ov.shape[0]})")

    g = rgb[:, :, 1]
    h, w = g.shape
    coords, score = [], []
    for y in range(TILE, h - 2 * TILE, TILE):
        for x in range(TILE, w - 2 * TILE, TILE):
            t = g[y:y + TILE, x:x + TILE]
            coords.append((y, x))
            score.append(float(np.abs(np.diff(t, axis=0)).mean()
                               + np.abs(np.diff(t, axis=1)).mean()))
    order = np.argsort(np.asarray(score))
    picks = {
        "sharpest": coords[int(order[-1])],
        "upper-mid": coords[int(order[int(len(order) * 0.75)])],
        "median": coords[int(order[len(order) // 2])],
    }
    for name, (y, x) in picks.items():
        crop = (rgb[y:y + TILE, x:x + TILE] * 255.0 + 0.5).clip(0, 255).astype(np.uint8)
        Image.fromarray(crop).save(out / f"{src.stem}--{name}.png")
        print(f"  wrote {src.stem}--{name}.png  at ({y},{x})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
