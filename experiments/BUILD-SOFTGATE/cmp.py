"""Compare two 16-bit TIFF renders. Reports DIFFERENT/IDENTICAL plus magnitude.

Commissioned before use: a file against itself must report IDENTICAL, and a
known-different pair must report DIFFERENT. A comparator that has not been shown
to see a real change cannot be trusted to report the absence of one.
"""
import sys
import numpy as np
import tifffile


def load(p):
    a = tifffile.imread(p)
    return a.astype(np.int32)


def main(a_path, b_path, label):
    a, b = load(a_path), load(b_path)
    if a.shape != b.shape:
        print(f"{label:<34} SHAPE-MISMATCH {a.shape} vs {b.shape}")
        return
    d = np.abs(a - b)
    n = d.size
    nz = int((d > 0).sum())
    if nz == 0:
        print(f"{label:<34} IDENTICAL      0 px differ of {n}")
        return
    print(
        f"{label:<34} DIFFERENT      {nz} px ({100.0 * nz / n:6.3f}%)  "
        f"maxDN={int(d.max()):5d}  meanDN(all)={d.mean():.6f}  "
        f"meanDN(nz)={d[d > 0].mean():.4f}  p99.9={int(np.percentile(d, 99.9))}"
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
