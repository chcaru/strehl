"""magdose.py -- commission the RADIAL SLOPE statistic with a planted magnification.

WHY THIS EXISTS
---------------
`chromashift.py` commissions itself with a planted *translation* (`--plant n`), and
its own source says so at the plant site:

    # For planted/null arms report the raw mean displacement, not the radial
    # decomposition: a uniform translation is not radial and must not be
    # scored as if it were.

So the commissioned statistic is the MEAN DISPLACEMENT, while every ppm number
this lane has quoted is the RADIAL SLOPE. Those are different statistics and the
slope has never had a dose. Worse, the plant arm builds R as `np.roll(G)` -- an
exact copy of green -- which removes the independent per-channel content that
causes regression dilution in the first place. A plant that deletes the error
mechanism cannot measure it. That is why it recovered 1.0003.

This tool plants a known MAGNIFICATION on the REAL red plane, keeping real R-vs-G
content differences intact, and asks the slope statistic for the dose back. This
is the same design as BUILD-CHROMA's `c4_attenuation.py` (report S15).

    recovery a(D) = (slope_dosed - slope_base) / D

If a < 1 the statistic under-reads (regression dilution). If a > 1 it over-reads,
which dilution cannot cause and which would indicate a gain defect.

READ THIS BEFORE QUOTING THIS TOOL'S NUMBER
-------------------------------------------
This tool measures a = 0.775-0.794, and **that figure must NOT be used to
de-attenuate a measurement of the shipped correction.** The plant here resamples
an ALREADY-DEMOSAICED red plane, which adds a second interpolation that the real
correction explicitly does not have ("the correction rides the gather's existing
interpolation and adds no second resampling pass" -- optics.rs). That extra blur
decorrelates R from G and is itself most of the measured shortfall.

The controlled figure is 0.996: the SAME estimator reading the dose the CODE
applies, on a single-frame CA-on/CA-off pair, where no extra resample occurs
(caorigin.py). `magtruth.py` separately proves the plant geometry is honest to
0.7%, so the gap is the blur and not the dose. See BUILD-CROP.md S15.2, which is
also why BUILD-CHROMA S15's de-attenuation does not transfer to a
gradient-regression estimator.

What this tool IS good for: the null and specificity arms below, and detecting a
gain defect, where only the RATIO between arms matters.

ARMS
----
  base       undosed, gives slope_base
  dose D     R resampled to carry an extra outward radial displacement of D*r
  null       D = 0 run through the identical resample path (isolates the
             interpolator's own contribution from the dose's)
  noise      R perturbed by zero-mean noise at the measured R-G residual scale,
             NO displacement. Specificity: the slope must NOT move. Sensitivity
             without specificity is what invalidated corpus_scan.py.

Usage:
  python magdose.py <master.tiff> [--tile 512] [--gradpct 97]
                    [--doses 200,400,704.5,1000]
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
import tifffile
from scipy.ndimage import affine_transform

from chromashift import solve_tile


def magnify(plane, ppm):
    """Return `plane` resampled so a feature at radius r moves OUTWARD by ppm*r.

    dst(p) = src(c + (p - c)*(1 - d)), so the feature that sat at radius r0 in
    src appears at r0/(1-d) ~ r0*(1+d) in dst: displaced outward by d*r0.
    """
    d = ppm * 1e-6
    h, w = plane.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    s = 1.0 - d
    matrix = np.array([[s, 0.0], [0.0, s]], dtype=np.float64)
    offset = np.array([cy * d, cx * d], dtype=np.float64)
    return affine_transform(
        plane, matrix, offset=offset, order=3, mode="nearest", prefilter=True
    )


def build_geometry(img, tile, gradpct):
    """Replicate field()'s tile/mask geometry EXACTLY, once, so every arm below
    is scored by the same statistic on the same pixels."""
    g = img[:, :, 1]
    gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy)
    thr = np.percentile(mag, gradpct)
    h, w = g.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    tiles = []
    for ty in range(0, h - tile + 1, tile):
        for tx in range(0, w - tile + 1, tile):
            sl = (slice(ty, ty + tile), slice(tx, tx + tile))
            m = mag[sl] >= thr
            if m.sum() < 200:
                continue
            ty_c, tx_c = ty + tile / 2.0 - cy, tx + tile / 2.0 - cx
            r = float(np.hypot(tx_c, ty_c))
            if r < 1e-6:
                continue
            tiles.append(
                {
                    "sl": sl,
                    "m": m,
                    "r": r,
                    "ux": tx_c / r,
                    "uy": ty_c / r,
                    "gx": gx[sl][m],
                    "gy": gy[sl][m],
                    "gv": g[sl][m],
                }
            )
    return tiles


def slope_of(tiles, rplane):
    """Radial slope of R-G, identical formula to chromashift.report()."""
    rs, rads = [], []
    for t in tiles:
        dc = rplane[t["sl"]][t["m"]] - t["gv"]
        dx, dy, _, _ = solve_tile(dc, t["gx"], t["gy"])
        rs.append(t["r"])
        rads.append(dx * t["ux"] + dy * t["uy"])
    r = np.array(rs)
    rad = np.array(rads)
    slope = float((r * rad).sum() / max((r * r).sum(), 1e-30))
    pred = slope * r
    ss = float(((rad - pred) ** 2).sum())
    st = float(((rad - rad.mean()) ** 2).sum())
    return slope, 1.0 - ss / max(st, 1e-30), len(r)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--tile", type=int, default=512)
    ap.add_argument("--gradpct", type=float, default=97.0)
    ap.add_argument("--doses", default="200,400,704.5,1000")
    args = ap.parse_args()

    img = tifffile.imread(args.image).astype(np.float32)
    if img.ndim != 3 or img.shape[2] < 3:
        print("need an RGB image")
        return 2
    print(f"image : {args.image}  {img.shape[1]}x{img.shape[0]}")

    tiles = build_geometry(img, args.tile, args.gradpct)
    print(f"tiles : {len(tiles)}  (tile={args.tile} gradpct={args.gradpct})")
    if len(tiles) < 8:
        print("TOO FEW TILES -> UNSCORED")
        return 3

    r0 = img[:, :, 0]
    base, r2b, n = slope_of(tiles, r0)
    print(f"\nbase       slope = {base*1e6:+9.1f} ppm   r2={r2b:+.3f}  n={n}")

    # NULL: dose 0 through the identical resample path.
    z, r2z, _ = slope_of(tiles, magnify(r0, 0.0))
    print(f"null(D=0)  slope = {z*1e6:+9.1f} ppm   r2={r2z:+.3f}   "
          f"delta from base = {(z-base)*1e6:+.2f} ppm  <- interpolator floor")

    # SPECIFICITY: noise at the real R-G residual scale, no displacement.
    resid = float(np.std(r0[::7, ::7] - img[::7, ::7, 1]))
    rng = np.random.default_rng(12345)
    noisy = r0 + rng.normal(0.0, resid, size=r0.shape).astype(np.float32)
    sn, r2n, _ = slope_of(tiles, noisy)
    print(f"noise arm  slope = {sn*1e6:+9.1f} ppm   r2={r2n:+.3f}   "
          f"delta from base = {(sn-base)*1e6:+.2f} ppm  (sd={resid:.1f} DN, no shift)")

    print("\n  dose      measured delta      recovery a")
    print("  ------------------------------------------")
    recs = []
    for tok in args.doses.split(","):
        D = float(tok)
        s, r2d, _ = slope_of(tiles, magnify(r0, D))
        delta = (s - base) * 1e6
        a = delta / D
        recs.append((D, delta, a))
        print(f"  {D:+8.1f}   {delta:+9.1f} ppm     {a:.4f}    (r2={r2d:+.3f})")

    if recs:
        amean = float(np.mean([a for _, _, a in recs]))
        print(f"\nmean recovery a = {amean:.4f}")
        print(f"de-attenuated base = {base*1e6/amean:+.1f} ppm "
              f"(base {base*1e6:+.1f} / {amean:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
