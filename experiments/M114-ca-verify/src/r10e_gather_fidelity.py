"""M114 R10e -- does the gather apply the 704.5e-6 it claims?  Same-channel test.

R10d showed the render-domain search is unbiased ON RENDER-DOMAIN SHIFTS: a
synthetic arm built by scaling the OFF arm's red by exactly -704.5e-6 read a
residual of -25.6e-6, and a planted -300e-6 moved the reading by +300e-6 to
within 3.3% in all seven annuli.  On that instrument the REAL ON arm reads
+207e-6, as if it had received ~937e-6 rather than 704.5e-6.

But that control validates the search against its own operator.  The shipped
correction is applied in the CFA PLANE BEFORE DEMOSAIC; the search scales the
DEMOSAICED red.  Those are different operators, so the +207e-6 may be
cross-domain incommensurability rather than an over-applied gather.

Settle it with a measurement that involves no chroma and no second domain:
measure the geometric displacement between the two arms' RED channels
directly.  Same channel, same content, pure shift:

    d = <(R_on - R_off) * dR_off/dr> / <(dR_off/dr)^2>

and calibrate the estimator's response with planted scales of known size, so
any under-read is measured rather than assumed.

  If d(r) tracks 704.5e-6 * r_px  -> the gather applies exactly what it says,
     and R10d's +207e-6 is an artefact of the objective, not an over-correction.
  If d(r) tracks ~937e-6 * r_px   -> the gather really over-applies by ~1.33x
     and that is a shipping defect.

Bars, registered before running:
  E1  CALIBRATION: planted scales of -300/-500/-704.5/-900e-6 must give a
      response slope; the slope is MEASURED and divided out, not assumed to
      be 1.  Report the slope so the correction is auditable.
  E2  NULL: R_off against itself must read |d| < 0.02 px in every annulus.
  E3  the calibration must be linear (R^2 > 0.99) or the divide-out is invalid.
"""
import json

import numpy as np
import tifffile
from scipy import ndimage

OFF = r"C:\dev\strehl-out\M114-ca-verify\r1\unset.tif"
ON = r"C:\dev\strehl-out\M114-ca-verify\r1\on.tif"
NOMINAL = 704.5e-6
EDG = [0.0, 0.2, 0.4, 0.6, 0.788, 0.85, 0.92, 1.05]


def load_red(p):
    return (tifffile.imread(p)[..., 0].astype(np.float32) / np.float32(65535.0),
            tifffile.imread(p).astype(np.float32) / np.float32(65535.0))


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


a0 = tifffile.imread(OFF).astype(np.float32) / np.float32(65535.0)
a1 = tifffile.imread(ON).astype(np.float32) / np.float32(65535.0)
r_off, r_on = a0[..., 0], a1[..., 0]
H, W = r_off.shape
y0 = 0.2126 * a0[..., 0] + 0.7152 * a0[..., 1] + 0.0722 * a0[..., 2]
del a0, a1

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
dxr, dyr = xx - W / 2.0, yy - H / 2.0
rpx = np.hypot(dxr, dyr)
rad = rpx / np.hypot(W / 2.0, H / 2.0)
del yy, xx

gy, gx = np.gradient(r_off)
mag = np.hypot(gx, gy)
dRdr = (gx * dxr + gy * dyr) / np.maximum(rpx, 1e-6)
gyl, gxl = np.gradient(y0)
magl = np.hypot(gxl, gyl)
# strong, substantially RADIAL edges: that is where a radial shift is visible.
use = (magl >= np.quantile(magl, 0.99)) & (np.abs(dRdr) >= 0.5 * mag) & (mag > 0)
print("usable radial-edge px: %d (%.3f%% of frame)" % (use.sum(), 100 * use.mean()))
masks = [(rad >= EDG[i]) & (rad < EDG[i + 1]) & use for i in range(len(EDG) - 1)]
names = ["%.2f-%.2f" % (EDG[i], EDG[i + 1]) for i in range(len(EDG) - 1)]
den = {j: float(np.sum(dRdr[m] * dRdr[m])) for j, m in enumerate(masks)}
rmid = {j: float(rpx[m].mean()) for j, m in enumerate(masks)}


def disp(img):
    d = img - r_off
    return {j: (float(np.sum(d[m] * dRdr[m])) / den[j] if den[j] > 0 else float("nan"))
            for j, m in enumerate(masks)}


print()
print("E2 NULL: R_off vs itself")
z = disp(r_off)
e2 = all(abs(v) < 0.02 for v in z.values())
print("   %s  -> %s" % (" ".join("%+.4f" % v for v in z.values()),
                        "PASS" if e2 else "FAIL"))

print()
print("E1/E3 CALIBRATION: planted radial scales on R_off")
PLANTS = [-300e-6, -500e-6, -704.5e-6, -900e-6]
cal = {}
for p in PLANTS:
    cal[p] = disp(radial_scale(r_off, p))
    print("   plant %+8.1fe-6 -> measured px " % (p * 1e6)
          + " ".join("%+7.4f" % cal[p][j] for j in range(len(masks))))

slopes = {}
print()
print("   %-12s %10s %10s   %s" % ("annulus", "slope", "R^2", "note"))
for j in range(len(masks)):
    x = np.array([p * rmid[j] for p in PLANTS])   # predicted px
    yv = np.array([cal[p][j] for p in PLANTS])
    A = np.vstack([x, np.ones_like(x)]).T
    sol, *_ = np.linalg.lstsq(A, yv, rcond=None)
    pred = A @ sol
    ss = 1 - np.sum((yv - pred) ** 2) / max(np.sum((yv - yv.mean()) ** 2), 1e-30)
    slopes[j] = float(sol[0])
    print("   %-12s %10.4f %10.5f   %s"
          % (names[j], sol[0], ss, "OK" if ss > 0.99 else "E3 FAIL: nonlinear"))

print()
print("=== the real ON arm, calibration divided out ===")
meas = disp(r_on)
print("   %-12s %9s %11s %11s %13s   %s"
      % ("annulus", "n", "raw px", "corrected", "implied eps", "vs nominal 704.5e-6"))
rows = []
for j in range(len(masks)):
    corr = meas[j] / slopes[j]
    eps = corr / rmid[j]
    ratio = eps / -NOMINAL
    rows.append(dict(annulus=names[j], n=int(masks[j].sum()), raw=meas[j],
                     corrected=float(corr), eps=float(eps), ratio=float(ratio)))
    print("   %-12s %9d %+11.4f %+11.4f %+13.1fe-6   %.3fx%s"
          % (names[j], masks[j].sum(), meas[j], corr, eps * 1e6, ratio,
             "   PAST SUPPORT" if float(names[j].split("-")[0]) >= 0.788 else ""))

rs = [r["ratio"] for r in rows]
print()
print("   mean applied/nominal ratio = %.3fx   (1.000 = the gather applies exactly"
      " what the profile declares)" % float(np.mean(rs)))
if abs(np.mean(rs) - 1.0) < 0.10:
    print("   -> THE GATHER IS FAITHFUL. R10d's +207e-6 is a property of the")
    print("      chroma objective, not an over-applied correction.")
else:
    print("   -> THE GATHER DEVIATES from its declared coefficient by %.2fx." % np.mean(rs))
with open(r"C:\dev\strehl-out\M114-ca-verify\r10e.json", "w") as fh:
    json.dump(dict(rows=rows, slopes={str(k): v for k, v in slopes.items()}), fh, indent=2)
print("\nwrote r10e.json")
