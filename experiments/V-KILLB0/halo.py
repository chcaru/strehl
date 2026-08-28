"""V-KILLB0 halo / rim instrument.  Independent of ORCH-drift-check/orch_halo.py.

The owner's loudest standing complaint is HALOS, so this is the axis that can
kill the default flip on its own.

WHAT IT MEASURES.  At each of the K strongest step edges it builds an edge
spread function by projecting every pixel of a patch onto the patch's dominant
gradient direction, then reads:

  overshoot  = (max ESF within 1..10 px on the BRIGHT side - bright far field)
               / step height
  undershoot = (dark far field - min ESF within 1..10 px on the DARK side)
               / step height

Far field is 14..30 px, so the "plateau" is measured outside the ring the halo
lives in.  Both are dimensionless, so an arm that merely shifts level cannot
move them.

COMMISSIONING.  --commission plants a halo with an unsharp mask of known
amount on arm B and requires the instrument to report it going UP; and runs
arm A against itself, which must read exactly 0 difference.
"""
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, maximum_filter

import bandprobe as bp

PATCH = 72
HALF = PATCH // 2
NEAR = (1.0, 10.0)
FAR = (14.0, 30.0)


def find_edges(lum, k=40, minsep=200):
    g = gaussian_filter(lum, 1.5)
    gy, gx = np.gradient(g)
    mag = np.hypot(gy, gx)
    m = gaussian_filter(mag, 3.0)
    m[:HALF + 4, :] = 0
    m[-(HALF + 4):, :] = 0
    m[:, :HALF + 4] = 0
    m[:, -(HALF + 4):] = 0
    peaks = (m == maximum_filter(m, minsep)) & (m > 0)
    ys, xs = np.nonzero(peaks)
    vals = m[ys, xs]
    order = np.argsort(vals)[::-1][:k]
    return list(zip(ys[order].tolist(), xs[order].tolist()))


def esf(patch):
    """Project the patch onto its dominant gradient direction; return
    (distance, value) with distance signed so + is the bright side."""
    gy, gx = np.gradient(gaussian_filter(patch, 1.0))
    # dominant direction by the structure tensor's principal axis, sign taken
    # from the mean gradient so + points uphill
    vy, vx = gy.mean(), gx.mean()
    n = np.hypot(vy, vx)
    if n < 1e-9:
        return None
    vy, vx = vy / n, vx / n
    yy, xx = np.mgrid[0:PATCH, 0:PATCH]
    d = (yy - HALF) * vy + (xx - HALF) * vx
    return d.ravel(), patch.ravel()


def profile(d, v, step=0.5):
    lo, hi = -30.0, 30.0
    nb = int((hi - lo) / step)
    idx = np.clip(((d - lo) / step).astype(int), 0, nb - 1)
    s = np.bincount(idx, weights=v, minlength=nb)
    c = np.bincount(idx, minlength=nb)
    ok = c >= 4
    centres = lo + (np.arange(nb) + 0.5) * step
    return centres[ok], s[ok] / c[ok]


def site_halo(patch):
    r = esf(patch)
    if r is None:
        return None
    c, p = profile(*r)
    far_hi = p[(c >= FAR[0]) & (c <= FAR[1])]
    far_lo = p[(c <= -FAR[0]) & (c >= -FAR[1])]
    near_hi = p[(c >= NEAR[0]) & (c <= NEAR[1])]
    near_lo = p[(c <= -NEAR[0]) & (c >= -NEAR[1])]
    if min(len(far_hi), len(far_lo), len(near_hi), len(near_lo)) < 4:
        return None
    hi, lo = far_hi.mean(), far_lo.mean()
    step = hi - lo
    if step < 500.0:            # too shallow to be an occluding edge
        return None
    return {
        "step": float(step),
        "over": float((near_hi.max() - hi) / step),
        "under": float((lo - near_lo.min()) / step),
    }


def run(lumA, lumB, sites):
    rows = []
    for (y, x) in sites:
        pa = lumA[y - HALF:y + HALF, x - HALF:x + HALF]
        pb = lumB[y - HALF:y + HALF, x - HALF:x + HALF]
        ha, hb = site_halo(pa), site_halo(pb)
        if ha is None or hb is None:
            continue
        rows.append((y, x, ha, hb))
    return rows


def summarise(rows, label):
    if not rows:
        return f"  {label}: NO ADMITTED SITES"
    oa = np.array([r[2]["over"] for r in rows])
    ob = np.array([r[3]["over"] for r in rows])
    ua = np.array([r[2]["under"] for r in rows])
    ub = np.array([r[3]["under"] for r in rows])
    worst = int(np.argmax(ob - oa))
    return (
        f"  {label}  n={len(rows)}\n"
        f"    overshoot  A mean {oa.mean():+.4f} max {oa.max():+.4f}   "
        f"B mean {ob.mean():+.4f} max {ob.max():+.4f}   "
        f"delta mean {(ob-oa).mean():+.4f}  worst site {(ob-oa)[worst]:+.4f} "
        f"@ y={rows[worst][0]} x={rows[worst][1]}\n"
        f"    undershoot A mean {ua.mean():+.4f} max {ua.max():+.4f}   "
        f"B mean {ub.mean():+.4f} max {ub.max():+.4f}   "
        f"delta mean {(ub-ua).mean():+.4f}"
    )


def main():
    A, B = sys.argv[1], sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else ""
    lumA = bp.channels(bp.load(A))["L"]
    lumB = bp.channels(bp.load(B))["L"]
    assert lumA.shape == lumB.shape
    sites = find_edges(lumA)
    print(f"== HALO {label}   {len(sites)} candidate edges")

    # ---- commissioning, every run, never optional
    rows_null = run(lumA, lumA, sites)
    o = np.array([r[3]["over"] - r[2]["over"] for r in rows_null])
    u = np.array([r[3]["under"] - r[2]["under"] for r in rows_null])
    null_ok = (np.abs(o).max() if len(o) else 1.0) == 0.0 and \
              (np.abs(u).max() if len(u) else 1.0) == 0.0
    print(f"  [C0 NULL] A vs A: max |d overshoot| = "
          f"{np.abs(o).max() if len(o) else float('nan'):.3e}  "
          f"{'PASS' if null_ok else 'FAIL'}")

    planted = lumA + 1.0 * (lumA - gaussian_filter(lumA, 3.0))
    rows_p = run(lumA, planted, sites)
    dp = np.array([r[3]["over"] - r[2]["over"] for r in rows_p])
    plant_ok = len(dp) > 0 and dp.mean() > 0.01
    print(f"  [C1 PLANT] unsharp amount=1.0 sigma=3: mean d overshoot "
          f"{dp.mean() if len(dp) else float('nan'):+.4f}  "
          f"{'PASS' if plant_ok else 'FAIL'}")
    if not (null_ok and plant_ok):
        print("  INSTRUMENT NOT COMMISSIONED -- results below are void")

    rows = run(lumA, lumB, sites)
    print(summarise(rows, "A=default  B=arm"))
    # the tail matters more than the mean for halos
    if rows:
        d = np.array([r[3]["over"] - r[2]["over"] for r in rows])
        print(f"    d-overshoot percentiles: p50 {np.percentile(d,50):+.4f}  "
              f"p90 {np.percentile(d,90):+.4f}  p100 {d.max():+.4f}  "
              f"sites worse {(d>0).sum()}/{len(d)}")


if __name__ == "__main__":
    main()
