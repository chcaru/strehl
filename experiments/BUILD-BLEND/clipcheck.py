"""Did the hull clamp remove the mid-tone clip, and what did it cost?

Reports the same statistics as ORCH's `experiments/ORCH-drift-check/zeros.py`
(exact-zero pixels, luma<500, median DN, per-channel zero counts) so the numbers
are directly comparable to ORCH-veiling section 29.1, plus the Jaccard overlap
between two arms' zero masks.

The pair that matters is interventional: the SAME binary, the SAME stack, one
flag apart. Anything that differs between them is the clamp and nothing else.

Usage:  python clipcheck.py <label:path.tiff> [<label:path.tiff> ...]
"""

import sys

import numpy as np
import tifffile


def load(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, not uint16 -- refusing to guess"
    return a.astype(np.float64)


def luma(a):
    if a.ndim == 2:
        return a
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    arms = {}
    print(
        f"{'arm':16s} {'exact0 px':>12s} {'exact0 %':>9s} {'lum<500 %':>10s} "
        f"{'med DN':>9s} {'R zero':>9s} {'G zero':>9s} {'B zero':>9s}"
    )
    print("-" * 92)
    for spec in argv:
        label, path = spec.split(":", 1)
        a = load(path)
        z = (a <= 0).all(axis=2) if a.ndim == 3 else (a <= 0)
        y = luma(a)
        per = [int((a[:, :, c] <= 0).sum()) for c in range(3)] if a.ndim == 3 else [0, 0, 0]
        arms[label] = z
        print(
            f"{label:16s} {int(z.sum()):12,} {100 * z.mean():8.3f}% "
            f"{100 * (y < 500).mean():9.3f}% {np.median(y):9.1f} "
            f"{per[0]:9,} {per[1]:9,} {per[2]:9,}"
        )

    keys = list(arms)
    if len(keys) >= 2:
        print()
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a, b = arms[keys[i]], arms[keys[j]]
                inter, union = int((a & b).sum()), int((a | b).sum())
                jac = inter / union if union else float("nan")
                print(
                    f"{keys[i]} vs {keys[j]}: shared zeros {inter:,}  "
                    f"union {union:,}  Jaccard {jac:.4f}"
                )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
