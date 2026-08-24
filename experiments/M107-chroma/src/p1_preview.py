"""M107b P-series: a LABELLED PREVIEW of the lateral correction on a real render.

WHAT THIS IS AND IS NOT
-----------------------
This applies the M107b lateral profile to the RED channel of an existing render
and measures the result with an instrument that works in the RENDER domain,
independent of the CFA-domain instrument (e2_lateral) that fitted the profile.

IT IS NOT THE SHIPPING PATH. The shipping path composes the correction into the
alignment Similarity and costs no extra interpolation (bar L6, <= 1e-12). This
preview instead RESAMPLES an already-rendered image, which costs a second kernel
application (facts 1373-1374, -0.2360 dex). The preview therefore SLIGHTLY
UNDERSTATES the shipping result's sharpness. It is for looking at, and for
confirming the profile acts in the render domain at all.

ONLY RED IS CORRECTED. eps_B was never measured (E9: 96.6% of bootstrap centres
off-sensor, CI spans zero), and absence is not a measured zero. So blue-side
fringing -- e.g. the cyan on the leaf edge -- is untouched here BY CONSTRUCTION.

BARS, REGISTERED BEFORE THE NUMBERS ARE SEEN
--------------------------------------------
P1  INSTRUMENT AGREEMENT. On the UNCORRECTED render, the fitted slope of radial
    (R-G) displacement against radius must land in [-1000, -400] ppm, i.e. it
    must recover the CFA-domain eps_R = -704.5 ppm to within about +/-40%.
      FALSIFIER: outside that band, or the opposite sign. Then the render-domain
      instrument disagrees with the CFA-domain one and nothing below means
      anything -- I would report that and stop, not retune the band.

P2  EFFECT. After correction, |slope| <= 200 ppm (a >= 70% reduction).
      FALSIFIER: |slope| > 500 ppm.

P3  NULL. Running the identical code path with eps = 0 must return an array that
    is BITWISE identical to the input. Not "within tolerance". Bytes.
      FALSIFIER: any differing element.

P4  CHANNEL-TARGETING CONTROL. Blue is NOT corrected, so the B-G slope must be
    unchanged by the operation, within 10% relative.
      FALSIFIER: the B-G slope moves more than 10%. That would mean the
      resampling is perturbing channels it never touched, and P2's reduction
      could not then be attributed to the profile.

ESTIMATOR. For a channel C against green G, on strong-gradient pixels, the local
sub-pixel misregistration along the gradient direction is estimated by
    s ~= (C - G) / |grad G|
and its RADIAL component by projecting the gradient unit vector on the radial
unit vector. Regressing that radial component on radius gives a slope in ppm
directly comparable to eps. This is a DIFFERENT instrument from e2_lateral,
which measured edge-profile centroids on unresampled CFA planes.
"""
import sys

import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\ORCH-kernel\bee-3-cpl-catmull-rom.tif"
OUT_DIR = r"C:\dev\strehl-out\M107-chroma\preview"

# M107b profile, fitted on CFA planes (3516x2344). The render is exactly 2x that,
# and eps is a RELATIVE magnification so it is scale-free; the translation is in
# plane px and must be doubled.
EPS_R = -704.5273607382725e-6
EPS_B = None                      # never measured -- absent, not zero
import os

TRANS_PLANE = (0.6294433, -0.4240211)
# Ablation switch. The translation term is explicitly UNATTRIBUTED (it is
# degenerate with an optical-centre offset), so being able to zero it and
# re-measure is part of reporting it honestly, not a debugging convenience.
if os.environ.get("M107_NO_TRANS") == "1":
    TRANS_PLANE = (0.0, 0.0)

GRAD_PCT = 99.0
MIN_GRAD = 1e-4


def apply_radial(chan, eps, trans_render):
    """Sample `chan` at q = s*p + t, s = 1 + eps, p relative to image centre.

    This mirrors the REPAIRED `optics.rs::compose`. The original version of this
    script used `s = 1/(1+eps)` and `q = s*(p - t)`, which is the inverted
    convention the P1 preview caught: it made the aberration 7.2 % worse. Under
    warpmap.rs's pull convention (`dst(p) = src(T(p))`) a channel imaged at
    magnification `(1+eps)` records scene point u at `(1+eps)u`, so the pull must
    sample there.

    Returns the input array UNCHANGED (same object) when eps is None or 0.0, so
    the no-op is bitwise by construction rather than by luck (bar P3).
    """
    if eps is None or eps == 0.0:
        return chan
    h, w = chan.shape
    s = 1.0 + eps
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    ty, tx = trans_render[1], trans_render[0]
    yy = (np.arange(h, dtype=np.float64) - cy)[:, None]
    xx = (np.arange(w, dtype=np.float64) - cx)[None, :]
    qy = s * yy + ty + cy
    qx = s * xx + tx + cx
    y0 = np.clip(np.floor(qy), 0, h - 2).astype(np.int32)
    x0 = np.clip(np.floor(qx), 0, w - 2).astype(np.int32)
    fy = (qy - y0).astype(np.float32)
    fx = (qx - x0).astype(np.float32)
    y1, x1 = y0 + 1, x0 + 1
    c = chan.astype(np.float32)
    top = c[y0, x0] * (1 - fx) + c[y0, x1] * fx
    bot = c[y1, x0] * (1 - fx) + c[y1, x1] * fx
    return (top * (1 - fy) + bot * fy).astype(np.float32)


def slope_ppm(chan, g, gy, gx, gmag, r, ry, rx, sel):
    """Fitted slope of radial (chan-G) misregistration against radius, in ppm."""
    d = (chan[sel] - g[sel]) / gmag[sel]
    ny, nx = gy[sel] / gmag[sel], gx[sel] / gmag[sel]
    radial = d * (ny * ry[sel] + nx * rx[sel])
    rr = r[sel]
    ok = np.isfinite(radial) & np.isfinite(rr)
    radial, rr = radial[ok], rr[ok]
    # robust: trim the extreme 2% of the displacement estimate before fitting
    lo, hi = np.percentile(radial, [1.0, 99.0])
    k = (radial >= lo) & (radial <= hi)
    radial, rr = radial[k], rr[k]
    slope = float(np.sum(rr * radial) / max(np.sum(rr * rr), 1e-12))
    return slope * 1e6, int(radial.size)


def main():
    import os
    os.makedirs(OUT_DIR, exist_ok=True)
    img = tifffile.imread(SRC)
    print(f"src {SRC}")
    print(f"    {img.shape[1]}x{img.shape[0]} {img.dtype}")
    h, w = img.shape[:2]
    trans_render = (TRANS_PLANE[0] * 2.0, TRANS_PLANE[1] * 2.0)
    print(f"    eps_R {EPS_R*1e6:.1f} ppm   eps_B {EPS_B}   "
          f"translation(render px) ({trans_render[0]:.4f}, {trans_render[1]:.4f})")

    R = img[..., 0].astype(np.float32)
    G = img[..., 1].astype(np.float32)
    B = img[..., 2].astype(np.float32)
    del img

    # P3 NULL first, before anything else can be believed.
    z = apply_radial(R, 0.0, trans_render)
    n_diff = int(np.count_nonzero(z.view(np.uint32) != R.view(np.uint32))) if z is not R else 0
    print(f"P3 NULL eps=0: identical object={z is R}, differing elements={n_diff} "
          f"-> {'PASS' if n_diff == 0 else 'FAIL'}")
    del z

    gy, gx = np.gradient(G)
    gmag = np.hypot(gx, gy).astype(np.float32)
    thr = float(np.percentile(gmag, GRAD_PCT))
    sel = (gmag >= thr) & (gmag > MIN_GRAD)
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy = (np.arange(h, dtype=np.float32) - cy)[:, None]
    xx = (np.arange(w, dtype=np.float32) - cx)[None, :]
    r = np.sqrt(yy * yy + xx * xx)
    half_diag = float(np.hypot(cy, cx))
    ry, rx = (yy / np.maximum(r, 1e-6)), (xx / np.maximum(r, 1e-6))
    ry = np.broadcast_to(ry, (h, w)).copy()
    rx = np.broadcast_to(rx, (h, w)).copy()
    print(f"    edge pixels {int(sel.sum())} at grad p{GRAD_PCT} = {thr:.5f}; "
          f"half-diagonal {half_diag:.1f} px")

    sr0, n0 = slope_ppm(R, G, gy, gx, gmag, r, ry, rx, sel)
    sb0, _ = slope_ppm(B, G, gy, gx, gmag, r, ry, rx, sel)
    print(f"BEFORE  R-G slope {sr0:9.1f} ppm  (n={n0})")
    print(f"BEFORE  B-G slope {sb0:9.1f} ppm")

    p1 = -1000.0 <= sr0 <= -400.0
    print(f"P1 instrument agreement: expect [-1000,-400] ppm vs CFA-domain "
          f"-704.5 -> {'PASS' if p1 else 'FAIL'}")

    Rc = apply_radial(R, EPS_R, trans_render)
    Bc = apply_radial(B, EPS_B, trans_render)
    print(f"    blue corrected? {Bc is not B}  (eps_B is {EPS_B})")

    sr1, _ = slope_ppm(Rc, G, gy, gx, gmag, r, ry, rx, sel)
    sb1, _ = slope_ppm(Bc, G, gy, gx, gmag, r, ry, rx, sel)
    print(f"AFTER   R-G slope {sr1:9.1f} ppm   "
          f"({100.0*(1-abs(sr1)/max(abs(sr0),1e-9)):.1f}% reduction)")
    print(f"AFTER   B-G slope {sb1:9.1f} ppm")

    p2 = abs(sr1) <= 200.0
    p4 = abs(sb1 - sb0) <= 0.10 * max(abs(sb0), 1e-9)
    print(f"P2 effect     |slope| <= 200 ppm -> {'PASS' if p2 else 'FAIL'}")
    print(f"P4 targeting  B-G unchanged within 10% -> {'PASS' if p4 else 'FAIL'} "
          f"(moved {100.0*abs(sb1-sb0)/max(abs(sb0),1e-9):.2f}%)")

    # ---- crops for looking at: the highest-edge-density tile in the outer band
    T = 420
    band = (r > 0.62 * half_diag) & sel
    best, bxy = -1, (0, 0)
    for y in range(0, h - T, T):
        for x in range(0, w - T, T):
            c = int(band[y:y + T, x:x + T].sum())
            if c > best:
                best, bxy = c, (y, x)
    y, x = bxy
    rad = float(r[y + T // 2, x + T // 2]) / half_diag
    print(f"    crop at ({x},{y}) {T}x{T}, {best} band-edge px, r={rad:.2f} of half-diagonal")
    print(f"    predicted red shift there: {abs(EPS_R)*float(r[y+T//2,x+T//2]):.2f} render px")

    def stack8(rr, gg, bb):
        a = np.stack([rr[y:y + T, x:x + T], gg[y:y + T, x:x + T], bb[y:y + T, x:x + T]], -1)
        return np.clip(a / 257.0, 0, 255).astype(np.uint8)

    before = stack8(R, G, B)
    after = stack8(Rc, G, Bc)
    gap = np.full((T, 12, 3), 255, np.uint8)
    tifffile.imwrite(rf"{OUT_DIR}\bee3-lateral-BEFORE-AFTER.png",
                     np.concatenate([before, gap, after], axis=1))
    diff = np.abs(after.astype(np.int16) - before.astype(np.int16))
    amp = np.clip(diff * 8, 0, 255).astype(np.uint8)
    tifffile.imwrite(rf"{OUT_DIR}\bee3-lateral-DIFF-x8.png", amp)
    print(f"    wrote BEFORE-AFTER and DIFF-x8 to {OUT_DIR}")
    print(f"    max |change| in crop: {int(diff.max())} DN of 255; "
          f"mean {diff.mean():.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
