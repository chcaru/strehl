"""Read a per-tile displacement dump and separate the candidate mechanisms.

Reports, for one pair:

  * the least-squares similarity the tiles imply, and its scale;
  * the same fit through the **origin in lever arm** (radial slope), which is
    the scale on its own;
  * the distribution of the fractional parts of the measured displacements,
    which is what pixel-locking shows up in;
  * the radial displacement binned by lever arm, so a field that is not linear
    in lever arm is visible rather than inferred.

usage: python tiles.py <tiles.csv> [label]
"""

import csv
import math
import sys

import numpy as np


def main():
    path = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else path
    with open(path, "r", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["status"] == "Ok"]

    ux = np.array([float(r["ux"]) for r in rows])
    uy = np.array([float(r["uy"]) for r in rows])
    dx = np.array([float(r["dx"]) for r in rows])
    dy = np.array([float(r["dy"]) for r in rows])
    peak = np.array([float(r["peak"]) for r in rows])

    # dx = ax + g*ux - rot*uy ; dy = ay + rot*ux + g*uy
    n = len(rows)
    A = np.zeros((2 * n, 4))
    b = np.zeros(2 * n)
    A[0::2, 0] = 1.0
    A[0::2, 2] = ux
    A[0::2, 3] = -uy
    A[1::2, 1] = 1.0
    A[1::2, 2] = uy
    A[1::2, 3] = ux
    b[0::2] = dx
    b[1::2] = dy
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    ax, ay, g, rot = sol
    scale = math.hypot(1.0 + g, rot)

    res = b - A @ sol
    rms = float(np.sqrt(np.mean(res**2)))

    # Radial slope: project displacement onto the outward radial direction and
    # regress on lever arm. This is the scale with translation removed by
    # construction rather than by fit, so a translation error cannot leak in.
    lev = np.hypot(ux, uy)
    good = lev > 1e-6
    rad = ((dx[good] - ax) * ux[good] + (dy[good] - ay) * uy[good]) / lev[good]
    slope = float(np.sum(rad * lev[good]) / np.sum(lev[good] ** 2))

    print(f"=== {label} ===")
    print(f"tiles ok {n}   mean peak {peak.mean():.4f}")
    print(f"  fit    ax {ax:+8.4f}  ay {ay:+8.4f}  g {g:+.6e}  rot {rot:+.6e}")
    print(f"  scale  {scale:.8f}   ln {math.log(scale):+.6e}   rms {rms:.4f} px")
    print(f"  radial slope (g by projection) {slope:+.6e}")

    # Pixel locking: the fractional part of a measured displacement should be
    # uniform on [-0.5, 0.5) if the sub-pixel estimator is unbiased. Locking
    # piles it up at zero.
    fr = np.concatenate([dx - np.round(dx), dy - np.round(dy)])
    hist, edges = np.histogram(fr, bins=10, range=(-0.5, 0.5))
    print(f"  |frac| mean {np.abs(fr).mean():.4f}  (uniform would be 0.2500)")
    print("  frac histogram " + " ".join(f"{h:>3}" for h in hist))

    # Is the field linear in lever arm? Bin the radial displacement.
    print(f"  {'lever bin':>12} {'n':>3} {'radial px':>10} {'implied g':>12}")
    lv = lev[good]
    qs = np.quantile(lv, [0.0, 0.25, 0.5, 0.75, 1.0])
    for k in range(4):
        m = (lv >= qs[k]) & (lv <= qs[k + 1])
        if m.sum() == 0:
            continue
        print(
            f"  {qs[k]:>5.0f}-{qs[k + 1]:>5.0f} {m.sum():>3} "
            f"{rad[m].mean():>10.4f} {rad[m].mean() / lv[m].mean():>12.4e}"
        )


if __name__ == "__main__":
    main()
