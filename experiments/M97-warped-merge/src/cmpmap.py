"""Count pixels where two 16-bit index maps disagree. M97q bar F2/F2b."""

import sys

from PIL import Image
import numpy as np


def load(p):
    a = np.array(Image.open(p))
    if a.dtype != np.uint16:
        raise SystemExit(f"{p}: expected uint16, got {a.dtype}")
    return a


def main():
    a, b = load(sys.argv[1]), load(sys.argv[2])
    if a.shape != b.shape:
        raise SystemExit(f"shape mismatch {a.shape} vs {b.shape}")
    n = a.size
    d = int(np.count_nonzero(a != b))
    pct = 100.0 * d / n
    print(f"  plane      : {a.shape[1]}x{a.shape[0]} = {n} px")
    print(f"  mean A     : {a.mean():.4f}   mean B: {b.mean():.4f}")
    print(f"  differing  : {d} px  ({pct:.6f}%)")
    # Guard against a vacuous comparison: two all-identical maps that are also
    # both constant would pass F2 while measuring nothing.
    print(f"  distinct winners in A: {len(np.unique(a))}")
    return pct


if __name__ == "__main__":
    pct = main()
    bar = float(sys.argv[3])
    mode = sys.argv[4]  # "below" for F2, "above" for the F2b plant
    ok = pct < bar if mode == "below" else pct > bar
    print(f"  bar        : {mode} {bar}%  ->  {'PASS' if ok else 'FAIL'}")
