"""M-PHASE0-EDGE / crop — render a 1:1 green-plane crop as PNG.

Orientation and inspection only (rule 48). No defect claim rests on a rendered
image; every claim in this lane comes from a number in `out/`. The stretch
bounds and the exact source region are printed so the render is reproducible.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import geom  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("--out", required=True)
    ap.add_argument("--which", choices=["G1", "G2"], default="G1")
    ap.add_argument("--y0", type=int, required=True)
    ap.add_argument("--y1", type=int, required=True)
    ap.add_argument("--x0", type=int, required=True)
    ap.add_argument("--x1", type=int, required=True)
    ap.add_argument("--zoom", type=int, default=1)
    ap.add_argument("--lo", type=float, default=None)
    ap.add_argument("--hi", type=float, default=None)
    ap.add_argument("--gamma", type=float, default=1.0)
    args = ap.parse_args()

    g1, g2, black = geom.read_greens(args.frame)
    g = g1 if args.which == "G1" else g2
    sub = g[args.y0:args.y1, args.x0:args.x1].astype(np.float64)
    lo = args.lo if args.lo is not None else float(np.percentile(sub, 0.5))
    hi = args.hi if args.hi is not None else float(np.percentile(sub, 99.5))
    print(f"green plane {g.shape} ({args.which}), black {black:.0f}")
    print(f"crop rows {args.y0}..{args.y1} cols {args.x0}..{args.x1} "
          f"= {sub.shape[1]}x{sub.shape[0]} green px")
    print(f"stretch {lo:.1f}..{hi:.1f} DN, gamma {args.gamma}, zoom {args.zoom}x")
    n = np.clip((sub - lo) / max(hi - lo, 1e-9), 0, 1) ** (1.0 / args.gamma)
    img = Image.fromarray((n * 255).astype(np.uint8), "L")
    if args.zoom != 1:
        img = img.resize((img.width * args.zoom, img.height * args.zoom),
                         Image.NEAREST)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print(f"wrote {args.out} ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
