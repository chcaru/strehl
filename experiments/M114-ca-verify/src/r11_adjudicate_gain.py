"""M114 R11 -- adjudicating ORCH's gain 1.444 against M114's 1.260.

ORCH's ca_gain.py reports, on MY renders r1/unset.tif and r1/on.tif:
    applied = R_on - R_off, radial, px:  0.147 0.189 0.224 0.192 0.143 0.108 0.115
M114 r10e measured the SAME quantity on the SAME files, raw before calibration:
    -0.477 -1.135 -1.530 -1.782 (r 0..0.79) and -2.85 -2.41 past support.
Same quantity, same files, 4-16x apart.  One of us is wrong.

Tiebreaker: a third estimator that is neither phase correlation (ORCH) nor a
linear gradient regression (M114).  Per window, brute-force the radial shift
that minimises SSD between R_on and a shifted R_off, cubic, on a fine grid.
No linearisation, no frequency domain.

  PART A  the tiebreaker, with ORCH's own integer-roll positive control.
  PART B  what the profile DECLARES it applies, in px, at each radius --
          neither of us checked our numbers against the coefficient itself.
  PART C  ORCH's `needed` column must be LINEAR in r; that is what "lateral"
          means and ORCH asserts the shape is right.  Check it.
  PART D  ORCH's gain implies the ON arm needs +324e-6 undone; M114's r10d
          measured +207e-6 with a plant recovered to 3.3%.  Score both.

Bars, registered before running:
  T1  CONTROL: an integer roll of R_off by -2..+2 px along x must be recovered
      to within 0.06 px by the SSD searcher, or PART A is not reportable.
  T2  the searcher must return ~0 for R_off against itself.
  T3  PART D must BRACKET its minimum; an endpoint minimum reports UNBRACKETED.
"""
import json

import numpy as np
import tifffile
from scipy import ndimage

OFF = r"C:\dev\strehl-out\M114-ca-verify\r1\unset.tif"
ON = r"C:\dev\strehl-out\M114-ca-verify\r1\on.tif"
NOMINAL = 704.5e-6
a0 = tifffile.imread(OFF).astype(np.float32) / np.float32(65535.0)
a1 = tifffile.imread(ON).astype(np.float32) / np.float32(65535.0)
r_off, r_on = a0[..., 0].copy(), a1[..., 0].copy()
H, W = r_off.shape
RC = np.hypot(W / 2.0, H / 2.0)
y0 = 0.2126 * a0[..., 0] + 0.7152 * a0[..., 1] + 0.0722 * a0[..., 2]
del a0, a1
print("render %dx%d  half-diagonal %.1f px" % (W, H, RC))

WIN = 128
gyl, gxl = np.gradient(y0)
magl = np.hypot(gxl, gyl)
thr = np.quantile(magl, 0.99)


def windows(rlo, rhi, want=200):
    """Window centres in an annulus, kept only if they carry radial edges."""
    out = []
    step = WIN // 2
    for cy in range(WIN, H - WIN, step):
        for cx in range(WIN, W - WIN, step):
            rr = np.hypot(cx - W / 2.0, cy - H / 2.0) / RC
            if not (rlo <= rr < rhi):
                continue
            sl = (slice(cy - WIN // 2, cy + WIN // 2), slice(cx - WIN // 2, cx + WIN // 2))
            if (magl[sl] >= thr).mean() < 0.02:
                continue
            ux, uy = (cx - W / 2.0) / (rr * RC), (cy - H / 2.0) / (rr * RC)
            out.append((sl, ux, uy, rr))
            if len(out) >= want:
                return out
    return out


def shift_img(img, dx, dy):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]].astype(np.float64)
    return ndimage.map_coordinates(img, [yy + dy, xx + dx], order=3, mode="nearest")


def ssd_shift(a, b, ux, uy, lo=-6.0, hi=6.0):
    """radial shift d minimising SSD(a, b shifted by d along (ux,uy))."""
    best, bd = 1e30, 0.0
    for d in np.arange(lo, hi + 1e-9, 0.5):
        v = shift_img(b, d * ux, d * uy)
        e = float(np.mean((a - v) ** 2))
        if e < best:
            best, bd = e, d
    for d in np.arange(bd - 0.5, bd + 0.5 + 1e-9, 0.05):
        v = shift_img(b, d * ux, d * uy)
        e = float(np.mean((a - v) ** 2))
        if e < best:
            best, bd = e, d
    return bd


RINGS = [(0.20, 0.30), (0.30, 0.40), (0.40, 0.50), (0.50, 0.60),
         (0.60, 0.70), (0.70, 0.80), (0.80, 0.90)]
sets = {r: windows(*r, want=60) for r in RINGS}

print()
print("T2 NULL: R_off vs itself")
w = sets[(0.40, 0.50)][:20]
z = [ssd_shift(r_off[sl], r_off[sl], ux, uy) for sl, ux, uy, _ in w]
print("   median %+0.4f px over %d windows -> %s"
      % (np.median(z), len(z), "PASS" if abs(np.median(z)) < 0.06 else "FAIL"))

print()
print("T1 CONTROL: integer roll of R_off (no resampling), recovered by the searcher")
t1ok = True
for k in (-2, -1, 0, 1, 2):
    rolled = np.roll(r_off, k, axis=1)
    got = [ssd_shift(rolled[sl], r_off[sl], 1.0, 0.0) for sl, _, _, _ in w[:12]]
    m = float(np.median(got))
    err = abs(m - k)
    t1ok &= err < 0.06
    print("   planted %+d -> recovered %+7.3f  err %.3f %s" % (k, m, err, "ok" if err < 0.06 else "MISS"))
print("   T1 -> %s" % ("PASS" if t1ok else "FAIL"))

print()
print("=== PART A/B  applied displacement: three numbers per ring ===")
print("   %-12s %4s %11s %11s %11s   %s"
      % ("ring", "n", "M114 SSD", "ORCH phase", "DECLARED", "SSD/declared"))
orch_applied = {0.25: 0.147, 0.35: 0.189, 0.45: 0.224, 0.55: 0.192,
                0.65: 0.143, 0.75: 0.108, 0.85: 0.115}
rows = []
for rlo, rhi in RINGS:
    ws = sets[(rlo, rhi)]
    if len(ws) < 8:
        print("   %.2f-%.2f  n=%d (too few)" % (rlo, rhi, len(ws)))
        continue
    ds = [ssd_shift(r_on[sl], r_off[sl], ux, uy) for sl, ux, uy, _ in ws]
    med = float(np.median(ds))
    rmid = (rlo + rhi) / 2.0
    decl = -NOMINAL * rmid * RC
    key = round(rmid, 2)
    oa = orch_applied.get(key, float("nan"))
    rows.append(dict(rlo=rlo, rhi=rhi, n=len(ws), ssd=med, orch=oa, declared=decl))
    print("   %.2f-%.2f %5d %+11.3f %+11.3f %+11.3f   %.3f"
          % (rlo, rhi, len(ws), med, -oa, decl, med / decl))

print()
print("=== PART C  is ORCH's `needed` column linear in r?  (lateral CA must be) ===")
rr = np.array([0.250, 0.350, 0.450, 0.550, 0.650, 0.750, 0.830])
need = np.array([0.100, 0.129, 0.155, 0.133, 0.100, 0.072, 0.083])
A = np.vstack([rr, np.zeros_like(rr)]).T
sol, *_ = np.linalg.lstsq(A, need, rcond=None)
pred = A @ sol
r2 = 1 - np.sum((need - pred) ** 2) / np.sum((need - need.mean()) ** 2)
print("   through-origin slope %.4f px per unit r   R^2 = %.4f" % (sol[0], r2))
print("   needed peaks at r=%.2f and FALLS %.0f%% by r=0.83"
      % (rr[int(np.argmax(need))], 100 * (1 - need[-1] / need.max())))
print("   -> %s" % ("linear" if r2 > 0.9
                    else "NOT LINEAR: the `needed` profile is not the lateral-CA shape;"
                         " the estimator is losing sensitivity with radius"))

print()
print("=== PART D  ORCH's gain implies +324e-6 to undo; r10d measured +207e-6 ===")


def radial_scale(chan, eps):
    h, w = chan.shape
    cx, cy = w * 0.5, h * 0.5
    s = 1.0 + eps
    o = np.empty_like(chan)
    xs = (np.arange(w, dtype=np.float64) - cx) * s + cx
    for q0 in range(0, h, 512):
        q1 = min(q0 + 512, h)
        ys = (np.arange(q0, q1, dtype=np.float64) - cy) * s + cy
        my, mx = np.meshgrid(ys, xs, indexing="ij")
        o[q0:q1] = ndimage.map_coordinates(chan, [my, mx], order=3,
                                           mode="nearest").astype(np.float32)
    return o


def hp(x):
    return x - ndimage.uniform_filter(x, 31, mode="nearest")


a1f = tifffile.imread(ON).astype(np.float32) / np.float32(65535.0)
near = ndimage.distance_transform_edt(~(magl >= thr)) <= 3
GRID = np.array([0.0, 100e-6, 150e-6, 207e-6, 260e-6, 324e-6, 400e-6, 500e-6])
obj = []
for e in GRID:
    rr2 = radial_scale(a1f[..., 0], e)
    yv = 0.2126 * rr2 + 0.7152 * a1f[..., 1] + 0.0722 * a1f[..., 2]
    obj.append(float(np.abs(hp(rr2 - yv))[near].mean()))
    del rr2, yv
k = int(np.argmin(obj))
print("   residual applied   mean |hp(R-Y)| near edges")
for e, o in zip(GRID, obj):
    tag = ""
    if abs(e - 207e-6) < 1e-9:
        tag = "   <- M114 r10d"
    if abs(e - 324e-6) < 1e-9:
        tag = "   <- ORCH gain 1.444 implies this"
    print("   %+8.1fe-6        %.6f%s%s" % (e * 1e6, o, "  MIN" if o == obj[k] else "", tag))
t3 = 0 < k < len(GRID) - 1
print("   T3 bracketed: %s" % ("PASS" if t3 else "FAIL (UNBRACKETED)"))
i207, i324 = list(GRID).index(207e-6), list(GRID).index(324e-6)
print("   objective at +324e-6 is %+.3f%% vs at +207e-6"
      % (100 * (obj[i324] - obj[i207]) / obj[i207]))
with open(r"C:\dev\strehl-out\M114-ca-verify\r11.json", "w") as fh:
    json.dump(dict(rows=rows, grid=list(GRID), obj=obj, need_r2=float(r2)), fh, indent=2)
print("\nwrote r11.json")
