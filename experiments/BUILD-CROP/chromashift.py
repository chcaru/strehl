"""Estimate the R-vs-G and B-vs-G displacement field of a single image.

WHY A DISPLACEMENT AND NOT A COLOUR DIFFERENCE. A raw "mean R-G near edges"
statistic conflates three unrelated things: a genuine colour, a channel gain
error, and a geometric displacement of one channel against another. Only the
third produces magenta on one side of an edge and cyan on the other, which is
the signature under investigation. So this measures the displacement directly
and reports it in PIXELS, which is a physical quantity with a ground truth that
can be planted and recovered.

THE ESTIMATOR. If R is a copy of G displaced by d, then R(x) = G(x - d), so to
first order R - G = -d . grad G. Regressing the observed (R - G) on grad G over
the strong-gradient pixels of a tile solves for d in closed form (a 2x2 normal
system). Flat pixels carry no information about d and are excluded by the
gradient threshold rather than being allowed to dilute the fit.

WHAT DISCRIMINATES OPTICS FROM MERGE. Lateral chromatic aberration is a
property of the lens: the displacement is RADIAL about the optical axis and
grows with radius, vanishing at the centre. A merge or demosaic defect has no
reason to know where the optical axis is. So the per-tile displacement is
decomposed into radial and tangential components about the frame centre, and
the tangential component -- which lateral CA cannot produce -- is reported
alongside the radial one. A large radial term with a small tangential term is
optics; comparable terms are not.

COMMISSIONING. --null replaces R and B by G, so the true displacement is
exactly zero and the estimator must say so. --plant N rolls R by N pixels in x
and B by N pixels in y, so the true displacement is known and must be
recovered. Both print the error against ground truth, in pixels.

Usage:
    python chromashift.py <image.tiff> [--tile 512] [--null] [--plant N]
                          [--gradpct 97] [--quiet]
"""

import argparse

import numpy as np
import tifffile


def solve_tile(dc, gx, gy):
    """Least-squares d minimising sum((dc + d.grad)^2). Returns (dx, dy, n, cond)."""
    a11 = float((gx * gx).sum())
    a12 = float((gx * gy).sum())
    a22 = float((gy * gy).sum())
    b1 = -float((dc * gx).sum())
    b2 = -float((dc * gy).sum())
    det = a11 * a22 - a12 * a12
    if det <= 0:
        return 0.0, 0.0, dc.size, 0.0
    dx = (a22 * b1 - a12 * b2) / det
    dy = (a11 * b2 - a12 * b1) / det
    tr = a11 + a22
    cond = det / max(tr * tr, 1e-30)   # 0.25 is perfectly conditioned
    return dx, dy, dc.size, cond


def field(img, tile, gradpct):
    g = img[:, :, 1]
    gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy)
    thr = np.percentile(mag, gradpct)
    h, w = g.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    rows = []
    for ty in range(0, h - tile + 1, tile):
        for tx in range(0, w - tile + 1, tile):
            sl = (slice(ty, ty + tile), slice(tx, tx + tile))
            m = mag[sl] >= thr
            if m.sum() < 200:
                continue
            sgx, sgy = gx[sl][m], gy[sl][m]
            out = []
            for c in (0, 2):
                dc = img[sl][:, :, c][m] - g[sl][m]
                out.append(solve_tile(dc, sgx, sgy))
            ty_c, tx_c = ty + tile / 2.0 - cy, tx + tile / 2.0 - cx
            r = np.hypot(tx_c, ty_c)
            if r < 1e-6:
                continue
            ux, uy = tx_c / r, ty_c / r
            rec = {"r": r, "n": int(m.sum()), "cond": min(out[0][3], out[1][3])}
            for name, (dx, dy, _, _) in (("R", out[0]), ("B", out[1])):
                rec[name] = (dx, dy)
                rec[name + "rad"] = dx * ux + dy * uy
                rec[name + "tan"] = -dx * uy + dy * ux
            rows.append(rec)
    return rows


def report(rows, label, quiet=False):
    if not rows:
        print(f"{label}: NO USABLE TILES -> UNSCORED")
        return None
    r = np.array([q["r"] for q in rows])
    res = {}
    for ch in ("R", "B"):
        rad = np.array([q[ch + "rad"] for q in rows])
        tan = np.array([q[ch + "tan"] for q in rows])
        # radial slope through the origin: CA grows linearly with radius
        slope = float((r * rad).sum() / max((r * r).sum(), 1e-30))
        pred = slope * r
        ss = float(((rad - pred) ** 2).sum())
        st = float(((rad - rad.mean()) ** 2).sum())
        res[ch] = {
            "slope": slope,
            "corner": slope * float(r.max()),
            "rad_rms": float(np.sqrt((rad ** 2).mean())),
            "tan_rms": float(np.sqrt((tan ** 2).mean())),
            "r2": 1.0 - ss / max(st, 1e-30),
        }
        if not quiet:
            print(f"  {ch}-G  radial slope={slope:+.3e} px/px -> "
                  f"{res[ch]['corner']:+.3f} px at corner   "
                  f"rad_rms={res[ch]['rad_rms']:.4f}  tan_rms={res[ch]['tan_rms']:.4f}  "
                  f"r2={res[ch]['r2']:+.3f}")
    if not quiet:
        print(f"  tiles={len(rows)}  median n={int(np.median([q['n'] for q in rows]))}")
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--tile", type=int, default=512)
    ap.add_argument("--gradpct", type=float, default=97.0)
    ap.add_argument("--null", action="store_true")
    ap.add_argument("--plant", type=int, default=0)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    img = np.asarray(tifffile.imread(args.image)).astype(np.float64)
    if img.ndim == 2:
        img = np.dstack([img] * 3)
    img = img[:, :, :3]

    truth = None
    if args.null:
        img[:, :, 0] = img[:, :, 1]
        img[:, :, 2] = img[:, :, 1]
        truth = (0.0, 0.0)
        print(f"NULL arm: R and B replaced by G, true displacement = (0, 0)")
    if args.plant:
        n = args.plant
        img[:, :, 0] = np.roll(img[:, :, 1], n, axis=1)   # R shifted +n in x
        img[:, :, 2] = np.roll(img[:, :, 1], n, axis=0)   # B shifted +n in y
        truth = float(n)
        print(f"PLANTED: R = G rolled {n}px in x, B = G rolled {n}px in y")

    print(f"image : {args.image}  {img.shape[1]}x{img.shape[0]}")
    rows = field(img, args.tile, args.gradpct)

    if truth is not None:
        # For planted/null arms report the raw mean displacement, not the radial
        # decomposition: a uniform translation is not radial and must not be
        # scored as if it were.
        for ch, idx in (("R", "R"), ("B", "B")):
            dxs = np.array([q[idx][0] for q in rows])
            dys = np.array([q[idx][1] for q in rows])
            print(f"  {ch}: mean dx={dxs.mean():+.4f} dy={dys.mean():+.4f}  "
                  f"(median dx={np.median(dxs):+.4f} dy={np.median(dys):+.4f})  "
                  f"sd=({dxs.std():.4f},{dys.std():.4f})  tiles={len(dxs)}")
        if args.null:
            allv = np.array([abs(q[c][k]) for q in rows for c in ("R", "B") for k in (0, 1)])
            print(f"  NULL max |d| over all tiles/axes = {allv.max():.3e} px")
        else:
            dxs = np.array([q["R"][0] for q in rows])
            dys = np.array([q["B"][1] for q in rows])
            print(f"  RECOVERY: R dx err={np.median(dxs) - truth:+.4f} px, "
                  f"B dy err={np.median(dys) - truth:+.4f} px")
        return 0

    report(rows, args.image, args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
