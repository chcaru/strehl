"""Compare the ORCH-HEADCHECK arms as decoded pixels, not as files.

Discipline 32: a file hash answers a question about the container. Every
claim here is made on decoded samples.

Reports, for each pair: fraction of samples differing, mean |delta| in DN,
and the 99.9th percentile of |delta|, plus a self-commissioning identity
check (a file against itself must read exactly 0).
"""
import io
import itertools
import os
import sys

import numpy as np
import tifffile

DIR = r"C:\dev\strehl-out\ORCH-HEADCHECK"

ARMS = {
    "default-k2.0": "leaf-2-cpl--HEAD.tiff",
    "white-k2.0": "leaf-2-cpl--HEAD-white.tiff",
    "measured-k1.29": "leaf-2-cpl--HEAD-k1.29.tiff",
    "measured-k0.9": "leaf-2-cpl--HEAD-k0.9.tiff",
}


def load(name):
    p = os.path.join(DIR, name)
    if not os.path.exists(p):
        return None
    return tifffile.imread(p)


def compare(a, b):
    d = np.abs(a.astype(np.int64) - b.astype(np.int64))
    n = d.size
    moved = int(np.count_nonzero(d))
    return moved / n, float(d.mean()), float(np.percentile(d, 99.9)), int(d.max())


def main() -> int:
    imgs = {}
    for k, v in ARMS.items():
        im = load(v)
        if im is None:
            print("MISSING: %s (%s)" % (k, v))
            continue
        imgs[k] = im
        print("loaded %-16s shape=%s dtype=%s" % (k, im.shape, im.dtype))

    if len(imgs) < 2:
        print("REFUSED: fewer than two arms present")
        return 2

    # Self-commissioning: an arm against itself must read exactly zero.
    first = next(iter(imgs))
    frac, mean, p999, mx = compare(imgs[first], imgs[first])
    if not (frac == 0.0 and mx == 0):
        print("REFUSED: identity check failed -- the comparator is broken")
        return 3
    print("\nidentity control (%s vs itself): frac=%.6f max=%d  OK" % (first, frac, mx))

    print("\n%-32s %10s %10s %10s %8s" % ("pair", "frac moved", "mean |d|", "p99.9 |d|", "max |d|"))
    print("-" * 76)
    for a, b in itertools.combinations(imgs, 2):
        if imgs[a].shape != imgs[b].shape:
            print("%-32s SHAPE MISMATCH" % ("%s vs %s" % (a, b)))
            continue
        frac, mean, p999, mx = compare(imgs[a], imgs[b])
        print("%-32s %10.6f %10.2f %10.1f %8d" % ("%s vs %s" % (a, b), frac, mean, p999, mx))
    return 0


if __name__ == "__main__":
    sys.exit(main())
