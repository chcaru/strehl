"""M-PHASE0-EDGE / profile — print the median scanline profile of a segment.

Overview/orientation only (rule 48). Shows the vertical structure so ROI bands
and the true blade edge can be chosen by eye rather than by an argmax that has
already been observed to lock onto the bevel boundary instead of the edge.
"""

import argparse

import numpy as np
import rawpy


def read_g1(path):
    with rawpy.imread(str(path)) as raw:
        vis = raw.raw_image_visible.astype(np.float32)
        pattern = raw.raw_pattern.copy()
        black = float(np.mean(raw.black_level_per_channel))
    for r in range(2):
        for c in range(2):
            if pattern[r, c] == 1:
                return np.maximum(vis[r::2, c::2] - black, 0.0), black
    raise SystemExit("no green plane")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("--orient", choices=["h", "v"], default="h")
    ap.add_argument("--x0", type=int, required=True)
    ap.add_argument("--w", type=int, default=256)
    ap.add_argument("--lo", type=int, default=0)
    ap.add_argument("--hi", type=int, default=0)
    ap.add_argument("--step", type=int, default=8)
    args = ap.parse_args()

    g, _ = read_g1(args.frame)
    a = g if args.orient == "h" else np.ascontiguousarray(g.T)
    p = np.median(a[:, args.x0:args.x0 + args.w], axis=1)
    hi = args.hi or len(p)
    top = float(np.percentile(p, 99))
    print(f"segment x {args.x0}..{args.x0 + args.w}, rows {args.lo}..{hi}, "
          f"p99 {top:.0f}")
    for i in range(args.lo, hi, args.step):
        v = float(np.median(p[i:i + args.step]))
        bar = "#" * int(60 * v / max(top, 1))
        print(f"{i:6d} {v:8.0f} {bar}")


if __name__ == "__main__":
    main()
