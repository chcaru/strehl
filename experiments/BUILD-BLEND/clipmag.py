"""How much did the hull clamp actually move, and where?

`clamped_fraction` counts pixels; it does not say by how much. A clamp binding
on 10% of pixels is alarming or inert depending entirely on the size of the
moves, and the count cannot distinguish those. This reports the distribution.

The pair must be one binary, one stack, one flag apart, or the difference is not
the clamp.

Usage:  python clipmag.py <unclamped.tiff> <clamped.tiff>
"""

import sys

import numpy as np
import tifffile


def load(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, not uint16 -- refusing to guess"
    return a.astype(np.float64)


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    u, c = load(argv[0]), load(argv[1])
    assert u.shape == c.shape, f"shape mismatch {u.shape} vs {c.shape}"
    d = c - u
    moved = np.abs(d) > 1.0

    print(f"{'statistic':34s} {'value':>14s}")
    print("-" * 50)
    print(f"{'pixels moved > 1 DN':34s} {100 * moved.mean():13.3f}%")
    print(f"{'  of those, moved UP (clamped to lo)':34s} {100 * (d[moved] > 0).mean():13.3f}%")
    print(f"{'median |move| over moved px':34s} {np.median(np.abs(d[moved])):14.1f}")
    print(f"{'p95 |move| over moved px':34s} {np.percentile(np.abs(d[moved]), 95):14.1f}")
    print(f"{'p99.9 |move| over moved px':34s} {np.percentile(np.abs(d[moved]), 99.9):14.1f}")
    print(f"{'max |move|':34s} {np.abs(d).max():14.1f}")
    print(f"{'mean level, unclamped':34s} {u.mean():14.1f}")
    print(f"{'mean level, clamped':34s} {c.mean():14.1f}")
    print(f"{'global level shift':34s} {c.mean() - u.mean():+14.2f}")
    print(f"{'  as fraction of level':34s} {100 * (c.mean() - u.mean()) / u.mean():+13.4f}%")

    # Where the excursions are, by input brightness. ORCH's mechanism says the
    # damage concentrates in the dark, where the hull sits near zero.
    y = u.mean(axis=2) if u.ndim == 3 else u
    edges = [0, 1000, 4000, 12000, 30000, 70000]
    print(f"\n{'input luma band':>22s} {'px':>12s} {'moved %':>10s} {'med |move|':>12s}")
    print("-" * 60)
    for lo, hi in zip(edges, edges[1:]):
        m = (y >= lo) & (y < hi)
        sel = m[..., None] & moved if u.ndim == 3 else m & moved
        n = int(sel.sum())
        med = np.median(np.abs(d[sel])) if n else float("nan")
        tot = int(m.sum()) * (u.shape[2] if u.ndim == 3 else 1)
        print(
            f"{f'{lo:,}-{hi:,}':>22s} {tot:12,} "
            f"{100 * n / max(tot, 1):9.3f}% {med:12.1f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
