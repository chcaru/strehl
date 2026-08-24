"""M107b P5: POST-HOC DIAGNOSTIC. Is the correction's SIGN inverted?

THIS IS NOT A BAR. P1 failed as registered and I am not retuning it. This script
exists to diagnose WHY, and every number it prints is post-hoc by construction
and must be labelled as such wherever it is quoted.

TWO SUSPECTED PROBLEMS, FOUND AFTER THE FACT:

1. My P1 PREDICTION was wrong, not necessarily the instrument. For an edge with
   gradient unit normal n and radial unit vector rhat, if red is magnified by
   (1+eps) relative to green then
        (R - G) / |grad G|  ~=  -eps * r * (rhat . n)
   and projecting on rhat gives a slope of  -eps * <(rhat.n)^2>, with
   <(rhat.n)^2> ~= 0.5 for randomly oriented edges. So for eps_R = -704.5 ppm the
   expected slope is about +352 ppm, POSITIVE. I registered [-1000,-400].
   The measured +141.1 ppm has the sign that derivation predicts.

2. The APPLIED DIRECTION may be inverted, and this is the serious one. The
   correction made the render-domain slope WORSE, 141.1 -> 151.3 ppm (-7.2%
   "reduction"). If red is observed at (1+eps)*u for a scene point u, then
   R_obs(x) = Scene(x/(1+eps)), so recovering Scene(x) requires sampling red at
        q = (1+eps) * x
   whereas p1_preview.py samples at q = x/(1+eps). Those are opposite.

WHAT THIS SCRIPT DOES: applies BOTH directions and reports which one drives the
render-domain radial R-G slope toward zero. Whichever wins, the finding is that
the shipped unit's sign was never tested against a real image.

WHY THE RUST TESTS COULD NOT CATCH THIS. L1 (bitwise no-op), L5 (green
untouched) and L6 (exact composition) are all SIGN-SYMMETRIC: they hold equally
for +eps and -eps. `correction_opposes_the_aberration` does test sign, but it
tests it against `displacement_at`, which is built from the same convention, so
it is circular. A unit test suite can be 9-for-9 green and still ship a global
sign inversion. That is the finding, independent of which way this run lands.
"""
import sys

import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\ORCH-kernel\bee-3-cpl-catmull-rom.tif"
EPS_R = -704.5273607382725e-6
TRANS_PLANE = (0.6294433, -0.4240211)


def resample(chan, scale, trans):
    """output(p) = input(scale*(p - t)), p relative to image centre."""
    h, w = chan.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy = (np.arange(h, dtype=np.float64) - cy)[:, None]
    xx = (np.arange(w, dtype=np.float64) - cx)[None, :]
    qy = scale * (yy - trans[1]) + cy
    qx = scale * (xx - trans[0]) + cx
    y0 = np.clip(np.floor(qy), 0, h - 2).astype(np.int32)
    x0 = np.clip(np.floor(qx), 0, w - 2).astype(np.int32)
    fy = (qy - y0).astype(np.float32)
    fx = (qx - x0).astype(np.float32)
    c = chan
    top = c[y0, x0] * (1 - fx) + c[y0, x0 + 1] * fx
    bot = c[y0 + 1, x0] * (1 - fx) + c[y0 + 1, x0 + 1] * fx
    return (top * (1 - fy) + bot * fy).astype(np.float32)


def main():
    img = tifffile.imread(SRC)
    h, w = img.shape[:2]
    R = img[..., 0].astype(np.float32)
    G = img[..., 1].astype(np.float32)
    del img
    trans = (TRANS_PLANE[0] * 2.0, TRANS_PLANE[1] * 2.0)

    gy, gx = np.gradient(G)
    gmag = np.hypot(gx, gy).astype(np.float32)
    sel = gmag >= float(np.percentile(gmag, 99.0))
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy = (np.arange(h, dtype=np.float32) - cy)[:, None]
    xx = (np.arange(w, dtype=np.float32) - cx)[None, :]
    r = np.sqrt(yy * yy + xx * xx)
    ry = np.broadcast_to(yy / np.maximum(r, 1e-6), (h, w)).copy()
    rx = np.broadcast_to(xx / np.maximum(r, 1e-6), (h, w)).copy()

    ny, nx = gy[sel] / gmag[sel], gx[sel] / gmag[sel]
    proj = ny * ry[sel] + nx * rx[sel]
    print(f"mean (rhat.n)^2 over selected edges = {float(np.mean(proj**2)):.4f} "
          f"(0.5 = randomly oriented)")
    print(f"so a lateral eps of {EPS_R*1e6:.1f} ppm predicts a render-domain")
    print(f"slope of about {-EPS_R*1e6*float(np.mean(proj**2)):+.1f} ppm, "
          f"NOT the [-1000,-400] band I registered.\n")

    rr = r[sel]

    def slope(chan):
        d = (chan[sel] - G[sel]) / gmag[sel]
        radial = d * proj
        lo, hi = np.percentile(radial, [1.0, 99.0])
        k = (radial >= lo) & (radial <= hi)
        a, b = radial[k], rr[k]
        return float(np.sum(b * a) / max(np.sum(b * b), 1e-12)) * 1e6

    s0 = slope(R)
    print(f"BEFORE                         R-G slope {s0:+9.1f} ppm")
    for label, sc in (("as shipped   q = p/(1+eps)", 1.0 / (1.0 + EPS_R)),
                      ("INVERTED     q = p*(1+eps)", 1.0 + EPS_R)):
        s = slope(resample(R, sc, trans))
        print(f"{label}  R-G slope {s:+9.1f} ppm   "
              f"({100.0*(1-abs(s)/abs(s0)):+6.1f}% toward zero)  scale={sc:.9f}")
    print("\nPOST-HOC. Whichever direction wins, the shipped unit's sign was")
    print("never tested against a real image; its 9 green tests are sign-symmetric.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
