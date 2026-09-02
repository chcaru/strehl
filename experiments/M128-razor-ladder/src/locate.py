"""M-PHASE0-EDGE / locate — where is the blade edge, and which segments are clean?

Prints, for a single frame, the coarse edge position along the scan axis and a
per-segment census: crossing row, local contrast, and a flatness score for the
strip either side of the edge. Used to choose ROIs before any measurement.
Overview only (rule 48): no defect claim rests on this output.
"""

import argparse
from pathlib import Path

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
    ap.add_argument("--seg", type=int, default=128, help="segment width along the edge")
    args = ap.parse_args()

    g, black = read_g1(args.frame)
    a = g if args.orient == "h" else np.ascontiguousarray(g.T)
    H, W = a.shape
    print(f"green plane {g.shape}  black {black:.1f}  scan axis len {H}  edge axis len {W}")
    print(f"frame min {a.min():.0f} max {a.max():.0f}  (container ceiling {16383 - black:.0f})")

    prof = np.median(a, axis=1)
    d = np.diff(prof)
    row = int(np.argmin(d))
    print(f"global median profile: steepest fall at row {row}  "
          f"({prof[max(row-8,0)]:.0f} -> {prof[min(row+8,H-1)]:.0f})")
    print(f"  bright plateau (rows {max(row-200,0)}..{row-20}): "
          f"{np.median(prof[max(row-200,0):row-20]):.0f}")
    print(f"  dark plateau  (rows {row+20}..{min(row+200,H)}): "
          f"{np.median(prof[row+20:min(row+200,H)]):.0f}")

    print(f"\nper-segment census, {args.seg}-px segments along the edge:")
    print(f"{'x0':>6} {'cross':>7} {'hi':>7} {'lo':>7} {'contr':>7} "
          f"{'brightRMS%':>10} {'darkRMS%':>9}")
    for x0 in range(0, W - args.seg + 1, args.seg):
        sl = a[:, x0:x0 + args.seg]
        p = np.median(sl, axis=1)
        lo_win = max(row - 250, 0)
        hi_win = min(row + 250, H)
        seg = p[lo_win:hi_win]
        dd = np.diff(seg)
        k = int(np.argmin(dd))
        cross = k + lo_win
        hi = float(np.median(p[max(cross - 160, 0):max(cross - 30, 1)]))
        lo = float(np.median(p[cross + 30:min(cross + 160, H)]))
        bs = sl[max(cross - 160, 0):max(cross - 30, 1), :]
        ds = sl[cross + 30:min(cross + 160, H), :]
        brms = 100.0 * float(np.std(bs)) / max(hi, 1.0)
        drms = 100.0 * float(np.std(ds)) / max(hi, 1.0)
        print(f"{x0:6d} {cross:7d} {hi:7.0f} {lo:7.0f} {hi - lo:7.0f} "
              f"{brms:10.2f} {drms:9.2f}")


if __name__ == "__main__":
    main()
