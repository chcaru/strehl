"""cafitstats.py -- the FitStats fields for the re-fitted eps_r.

carefit.py produces the coefficient. A shipped coefficient also needs the
evidence struct beside it, and the two fields carefit does not produce are
`residual_rms_sensel` and `permutation_p`. Those must be MEASURED, not carried
over from the superseded M107 fit -- a p-value describing a different fit sitting
in the struct of this one is a landmine for the next reader.

permutation null: the tile radial positions are shuffled against the measured
displacements, destroying any radial organisation while preserving both
marginals. If the fitted magnification survives that, it is scatter.

sensel convention: optics.rs states "1.489 sensels, or 2.977 output pixels", so
one sensel is two output pixels. Residuals are converted accordingly.

Usage: python cafitstats.py <master.tiff> [...]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
import tifffile

from caorigin import fit_mag_and_offset
from chromashift import field

N_PERM = 2000
PX_PER_SENSEL = 2.0


def design(px, py):
    n = len(px)
    A = np.zeros((2 * n, 3))
    A[:n, 0] = px
    A[:n, 1] = 1.0
    A[n:, 0] = py
    A[n:, 2] = 1.0
    return A


def rows_to_arrays(rows, ch):
    px, py, dx, dy = [], [], [], []
    for q in rows:
        r = q["r"]
        rad, tan = q[ch + "rad"], q[ch + "tan"]
        vx, vy = q[ch]
        den = vx * vx + vy * vy
        if den < 1e-12:
            continue
        ux = (vx * rad + vy * tan) / den
        uy = (vy * rad - vx * tan) / den
        n = np.hypot(ux, uy)
        if n < 1e-9:
            continue
        px.append(r * ux / n)
        py.append(r * uy / n)
        dx.append(vx)
        dy.append(vy)
    return (np.array(px), np.array(py), np.array(dx), np.array(dy))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--tile", type=int, default=512)
    ap.add_argument("--gradpct", type=float, default=97.0)
    args = ap.parse_args()

    allpx, allpy, alldx, alldy = [], [], [], []
    r2s, ns = [], []
    print(f"{'subject':>20} {'n':>5} {'r2':>7} {'resid rms px':>13} {'sensel':>8}")
    print("-" * 60)
    for path in args.images:
        name = os.path.splitext(os.path.basename(path))[0]
        img = tifffile.imread(path).astype(np.float32)
        rows = field(img, args.tile, args.gradpct)
        px, py, dx, dy = rows_to_arrays(rows, "R")
        fr = fit_mag_and_offset(rows, "R")
        if fr is None:
            print(f"{name:>20}  UNSCORED")
            continue
        m, tx, ty, r2, n = fr
        A = design(px, py)
        b = np.concatenate([dx, dy])
        sol = np.array([m * 1e-6, tx, ty])
        resid = b - A @ sol
        rms = float(np.sqrt((resid ** 2).mean()))
        print(f"{name:>20} {n:5d} {r2:+7.3f} {rms:13.4f} {rms/PX_PER_SENSEL:8.4f}")
        r2s.append(r2)
        ns.append(n)
        allpx.append(px)
        allpy.append(py)
        alldx.append(dx)
        alldy.append(dy)

    px = np.concatenate(allpx)
    py = np.concatenate(allpy)
    dx = np.concatenate(alldx)
    dy = np.concatenate(alldy)
    A = design(px, py)
    b = np.concatenate([dx, dy])
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    resid = b - A @ sol
    rms = float(np.sqrt((resid ** 2).mean()))

    print("\n=== POOLED ===")
    print(f"  tiles (n_regions)      = {sum(ns)}")
    print(f"  mean per-stack r2      = {np.mean(r2s):.4f}")
    print(f"  pooled magnification   = {sol[0]*1e6:+.1f} ppm")
    print(f"  residual rms           = {rms:.4f} output px = "
          f"{rms/PX_PER_SENSEL:.4f} sensel")

    rng = np.random.default_rng(20260224)
    obs = abs(sol[0])
    hits = 0
    n = len(px)
    for _ in range(N_PERM):
        idx = rng.permutation(n)
        Ap = design(px[idx], py[idx])
        s, *_ = np.linalg.lstsq(Ap, b, rcond=None)
        if abs(s[0]) >= obs:
            hits += 1
    p = (hits + 1) / (N_PERM + 1)
    print(f"  permutation null       : {hits}/{N_PERM} >= |observed|  -> p = {p:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
