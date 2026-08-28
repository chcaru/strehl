"""caorigin.py -- does the CA correction scale about the ORIGIN or the CENTRE?

`optics.rs::compose` scales about the coordinate ORIGIN and states a precondition:

    **This function scales about the coordinate ORIGIN, not about the plane
    centre.** `z` must already be plane-centre-relative. Feeding it absolute
    warpmap coordinates would introduce a uniform red offset of order
    `eps * half_diagonal` ~ 1.5 sensels. Nothing in this crate calls `compose`
    yet; a wiring commit must satisfy that precondition.

That last sentence is stale: align_cmd.rs calls it at L1929 and L2095. If the
precondition is NOT met, the delivered field is

    magnification about the centre  +  a UNIFORM offset of eps * centre

The uniform term is the falsifier. A correct wiring predicts a zero change in the
uniform term between CA-on and CA-off; a violated precondition predicts a change
of eps*(cx, cy) full-res px, which for eps = 704.5 ppm on a 7040x4688 plane is
about (+2.48, +1.65) px -- enormous and unmistakable.

chromashift's slope fits through the ORIGIN with no translation term, so it
cannot separate these two. BUILD-CHROMA S14.1 records falling into the same trap
from the other side ("a spurious 1/r term from the fitted translation ...
manufactured a convincing" artifact). This tool fits BOTH terms.

COMMISSIONING (always runs first): a planted magnification and a planted uniform
offset are recovered separately, proving the fit can tell them apart. If the
commissioning arm cannot separate them, no measurement below means anything.

Usage:  python caorigin.py <ca_off.tiff> <ca_on.tiff> [--tile 512] [--gradpct 97]
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import tifffile

from chromashift import field

W_FULL, H_FULL = 7040, 4688


def fit_mag_and_offset(rows, ch):
    """Least squares for d(p) = m*(p - c) + t0.  Returns m (ppm), t0x, t0y, r2.

    Tile centres are already centre-relative in chromashift's `field` (it stores
    r and the unit radial vector about the plane centre), so we rebuild the
    centre-relative position from r and the unit vector.
    """
    px, py, dx, dy = [], [], [], []
    for q in rows:
        r = q["r"]
        rad, tan = q[ch + "rad"], q[ch + "tan"]
        ux, uy = None, None
        # recover the tile's unit radial vector from (rad, tan) and (dx, dy)
        vx, vy = q[ch]
        # rad = vx*ux + vy*uy ; tan = -vx*uy + vy*ux  ->  solve for (ux, uy)
        den = vx * vx + vy * vy
        if den < 1e-12:
            continue
        ux = (vx * rad + vy * tan) / den
        uy = (vy * rad - vx * tan) / den
        n = np.hypot(ux, uy)
        if n < 1e-9:
            continue
        ux, uy = ux / n, uy / n
        px.append(r * ux)
        py.append(r * uy)
        dx.append(vx)
        dy.append(vy)
    px, py = np.array(px), np.array(py)
    dx, dy = np.array(dx), np.array(dy)
    n = len(px)
    if n < 8:
        return None
    # stack x and y equations: dx = m*px + t0x ; dy = m*py + t0y
    A = np.zeros((2 * n, 3))
    A[:n, 0] = px
    A[:n, 1] = 1.0
    A[n:, 0] = py
    A[n:, 2] = 1.0
    b = np.concatenate([dx, dy])
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    m, t0x, t0y = sol
    pred = A @ sol
    ss = float(((b - pred) ** 2).sum())
    st = float(((b - b.mean()) ** 2).sum())
    return m * 1e6, t0x, t0y, 1.0 - ss / max(st, 1e-30), n


def commission():
    print("=== COMMISSIONING: can the fit separate magnification from offset? ===")
    rng = np.random.default_rng(7)
    n = 200
    r = rng.uniform(200, 4000, n)
    th = rng.uniform(0, 2 * np.pi, n)
    px, py = r * np.cos(th), r * np.sin(th)
    for (m_true, tx_true, ty_true) in [
        (700e-6, 0.0, 0.0),
        (0.0, 2.48, 1.65),
        (700e-6, 2.48, 1.65),
        (0.0, 0.0, 0.0),
    ]:
        dx = m_true * px + tx_true + rng.normal(0, 0.05, n)
        dy = m_true * py + ty_true + rng.normal(0, 0.05, n)
        A = np.zeros((2 * n, 3))
        A[:n, 0] = px
        A[:n, 1] = 1.0
        A[n:, 0] = py
        A[n:, 2] = 1.0
        sol, *_ = np.linalg.lstsq(A, np.concatenate([dx, dy]), rcond=None)
        print(f"  planted m={m_true*1e6:+7.1f}ppm t0=({tx_true:+.3f},{ty_true:+.3f})"
              f"  ->  recovered m={sol[0]*1e6:+7.1f}ppm "
              f"t0=({sol[1]:+.3f},{sol[2]:+.3f})")
    print()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ca_off")
    ap.add_argument("ca_on")
    ap.add_argument("--tile", type=int, default=512)
    ap.add_argument("--gradpct", type=float, default=97.0)
    args = ap.parse_args()

    commission()

    res = {}
    for label, path in (("CA-OFF", args.ca_off), ("CA-ON ", args.ca_on)):
        img = tifffile.imread(path).astype(np.float32)
        rows = field(img, args.tile, args.gradpct)
        print(f"{label}  {path}   tiles={len(rows)}")
        res[label] = {}
        for ch in ("R", "B"):
            out = fit_mag_and_offset(rows, ch)
            if out is None:
                print(f"    {ch}: too few tiles -> UNSCORED")
                continue
            m, tx, ty, r2, n = out
            res[label][ch] = (m, tx, ty)
            print(f"    {ch}-G  mag={m:+9.1f} ppm   uniform offset="
                  f"({tx:+.4f}, {ty:+.4f}) px   r2={r2:+.3f}  n={n}")
        print()

    cx, cy = (W_FULL - 1) / 2.0, (H_FULL - 1) / 2.0
    print("=== THE TEST ===")
    for ch, eps in (("R", -704.5e-6), ("B", +174.4e-6)):
        if ch not in res["CA-OFF"] or ch not in res["CA-ON "]:
            continue
        m0, tx0, ty0 = res["CA-OFF"][ch]
        m1, tx1, ty1 = res["CA-ON "][ch]
        dtx, dty = tx1 - tx0, ty1 - ty0
        pred_x, pred_y = -eps * cx, -eps * cy
        print(f"  {ch}:  magnification change = {m1-m0:+9.1f} ppm "
              f"(nominal applied {-eps*1e6:+.1f})")
        print(f"      uniform offset change = ({dtx:+.4f}, {dty:+.4f}) px")
        print(f"      predicted if ORIGIN-scaled = ({pred_x:+.4f}, {pred_y:+.4f}) px")
        print(f"      predicted if CENTRE-scaled = ( 0.0000,  0.0000) px")
        mag = np.hypot(dtx, dty)
        pmag = np.hypot(pred_x, pred_y)
        print(f"      |observed| = {mag:.4f} px   |origin-prediction| = {pmag:.4f} px"
              f"   ratio = {mag/pmag if pmag else float('nan'):.3f}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
