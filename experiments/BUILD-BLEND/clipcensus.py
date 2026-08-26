"""Whole-frame clip census for a single linear TIFF, with location.

ORCH reports solid black blocks at one named site.  That site is clean in both
binaries at HEAD, so the question becomes whether the blocks exist anywhere in
the frame -- and if they do, where, so a crop can be taken there instead of
arguing about the one coordinate that happened to be quoted.

Reports, per channel: the exact-zero count, the threshold ramp that
distinguishes a clamp spike from a dark scene, and the centroid plus bounding
box of the zero mass so the next crop can be aimed rather than guessed.
"""

import sys

import numpy as np
import tifffile

THRESH = (0, 1, 16, 64, 256, 1024)
CH = ("R", "G", "B")


def main():
    p = sys.argv[1]
    img = tifffile.imread(p)
    h, w = img.shape[:2]
    n = h * w
    print(f"{p}\n{img.shape} {img.dtype}\n")
    print(f"{'ch':<3} {'min':>7} " + " ".join(f"{'<=' + str(t):>9}" for t in THRESH))
    for c in range(img.shape[2]):
        v = img[:, :, c]
        row = " ".join(f"{100.0 * float((v <= t).sum()) / n:>8.4f}%" for t in THRESH)
        print(f"{CH[c]:<3} {int(v.min()):>7} {row}")

    mask = (img == 0).any(axis=2)
    z = int(mask.sum())
    print(f"\npixels with ANY channel exactly 0 : {z:,} ({100.0 * z / n:.4f}%)")
    if z == 0:
        print("no clipped pixels anywhere in the frame")
        return

    ys, xs = np.nonzero(mask)
    print(f"  centroid      : ({int(xs.mean())}, {int(ys.mean())})")
    print(f"  bounding box  : x {xs.min()}..{xs.max()}   y {ys.min()}..{ys.max()}")

    # Densest 256 px tile, so the next crop can be aimed at the worst spot.
    ts = 256
    ny, nx = h // ts, w // ts
    m = mask[: ny * ts, : nx * ts].reshape(ny, ts, nx, ts).swapaxes(1, 2)
    dens = m.reshape(ny * nx, ts, ts).mean(axis=(1, 2))
    k = int(np.argmax(dens))
    cy, cx = (k // nx) * ts + ts // 2, (k % nx) * ts + ts // 2
    print(f"  densest tile  : ({cx}, {cy}) at {100 * dens[k]:.2f}% clipped")


if __name__ == "__main__":
    main()
