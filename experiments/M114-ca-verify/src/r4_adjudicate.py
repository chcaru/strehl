"""M114 R4 -- adjudicate W3, and test the UNPAIRED distribution.

Q1 UNPAIRED: does the distribution of |R-Y| near edges move down at EVERY
   percentile?  If it does, no population of pixels gained chroma, and the
   paired "+583% in decile 1" is regression to the mean and nothing else.
Q2 W3's disease: is >90%-keep-sign a bar that can tell a correction from a
   perturbation?  Score it on C-wrong (strictly damaging) and C-noise.
   If those also read ~75%, the bar is non-discriminating.
Q3 Are sign flips harmful?  A flip with a SMALLER magnitude is still closer to
   neutral.  Report mean |R-Y| before/after among flipped pixels.
Q4 FLAT regions (far from any edge) -- the population where injected chroma
   would be most visible.  Fixed population, taken from the OFF arm.
Q5 Per-channel mean |on-off| in DN (M107 claimed R 540, G 50, B 54).
"""
import json
import numpy as np
import tifffile
from scipy import ndimage

OFF = r"C:\dev\strehl-out\M114-ca-verify\r1\unset.tif"
ON = r"C:\dev\strehl-out\M114-ca-verify\r1\on.tif"
EPS = -704.5e-6
rng = np.random.default_rng(20260824)
out = {}


def load(p):
    return tifffile.imread(p).astype(np.float32) / np.float32(65535.0)


def yof(r, g, b):
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def radial_scale(chan, eps):
    h, w = chan.shape
    cx, cy = w * 0.5, h * 0.5
    s = 1.0 + eps
    o = np.empty_like(chan)
    xs = (np.arange(w, dtype=np.float64) - cx) * s + cx
    for y0 in range(0, h, 256):
        y1 = min(y0 + 256, h)
        ys = (np.arange(y0, y1, dtype=np.float64) - cy) * s + cy
        yy, xx = np.meshgrid(ys, xs, indexing="ij")
        o[y0:y1] = ndimage.map_coordinates(chan, [yy, xx], order=3,
                                           mode="nearest").astype(np.float32)
    return o


a0 = load(OFF)
a1 = load(ON)
r0, g0, b0 = a0[..., 0], a0[..., 1], a0[..., 2]
r1, g1, b1 = a1[..., 0], a1[..., 1], a1[..., 2]
y0, y1 = yof(r0, g0, b0), yof(r1, g1, b1)

gy, gx = np.gradient(y0)
gm = np.hypot(gx, gy)
edge = gm >= np.quantile(gm, 0.99)
dist = ndimage.distance_transform_edt(~edge)
near = dist <= 3
flat = dist >= 12
print("near px=%d (%.2f%%)   flat px=%d (%.2f%%)"
      % (near.sum(), 100 * near.mean(), flat.sum(), 100 * flat.mean()))

d0 = (r0 - y0)[near].astype(np.float64)
d1 = (r1 - y1)[near].astype(np.float64)
A0, A1 = np.abs(d0), np.abs(d1)

print("\n=== Q1  UNPAIRED percentiles of |R-Y| on the SAME fixed pixel set ===")
print("   pct      off        on      on-off      off_DN   on_DN")
pcts = [1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9]
q1 = []
for p in pcts:
    a, b = np.percentile(A0, p), np.percentile(A1, p)
    q1.append(dict(p=p, off=float(a), on=float(b)))
    print("   %5.1f  %.6f  %.6f  %+.6f   %8.1f %8.1f"
          % (p, a, b, b - a, a * 65535, b * 65535))
mono = all(x["on"] <= x["off"] for x in q1)
print("   every percentile falls: %s" % ("YES" if mono else "NO"))
out["Q1"] = dict(rows=q1, monotone_down=mono)

print("\n=== Q2  can the >90%-keep-sign bar tell correction from damage? ===")


def w3(dref, dtest):
    a, b = np.abs(dref), np.abs(dtest)
    fell = b < a
    same = np.sign(dref) == np.sign(dtest)
    return (float((fell & same).sum() / max(fell.sum(), 1)),
            float(fell.mean()), float((~same).mean()))


rw = radial_scale(r0, -EPS)
yw = yof(rw, g0, b0)
dw = (rw - yw)[near].astype(np.float64)
del rw, yw
rms = float(np.sqrt(np.mean(((r1 - r0)[near]).astype(np.float64) ** 2)))
rms_small = rms * 0.25
rn = r0 + rng.normal(0.0, rms_small, size=r0.shape).astype(np.float32)
yn = yof(rn, g0, b0)
dn = (rn - yn)[near].astype(np.float64)
del rn, yn

for lab, dv in [("REAL correction", d1),
                ("C-wrong  (+eps, strictly damaging)", dw),
                ("C-noise  (rms/4 white noise)", dn)]:
    k, f, fl = w3(d0, dv)
    print("   %-36s keep-sign=%5.1f%%  fell=%5.1f%%  flip=%5.2f%%"
          % (lab, 100 * k, 100 * f, 100 * fl))
    out.setdefault("Q2", {})[lab] = dict(keep=k, fell=f, flip=fl)

print("\n   keep-sign by decile of |R-Y|_off (REAL correction)")
qs = np.quantile(A0, np.linspace(0, 1, 11))
rows = []
for i in range(10):
    m = (A0 >= qs[i]) & (A0 < qs[i + 1]) if i < 9 else (A0 >= qs[i])
    fell = A1[m] < A0[m]
    same = np.sign(d0[m]) == np.sign(d1[m])
    k = float((fell & same).sum() / max(fell.sum(), 1))
    rows.append(dict(decile=i + 1, keep=k))
    print("     decile %2d  keep-sign=%5.1f%%   (bar was >90%%)  %s"
          % (i + 1, 100 * k, "PASS" if k > 0.90 else "fail"))
out["Q2_decile"] = rows

print("\n=== Q3  are the sign flips harmful? ===")
flip = np.sign(d0) != np.sign(d1)
print("   flipped pixels n=%d (%.2f%%)" % (flip.sum(), 100 * flip.mean()))
print("   among FLIPPED: mean |R-Y| off=%.6f (%.1f DN) -> on=%.6f (%.1f DN)  %+.2f%%"
      % (A0[flip].mean(), A0[flip].mean() * 65535, A1[flip].mean(),
         A1[flip].mean() * 65535,
         100 * (A1[flip].mean() - A0[flip].mean()) / A0[flip].mean()))
print("   among KEPT   : mean |R-Y| off=%.6f -> on=%.6f  %+.2f%%"
      % (A0[~flip].mean(), A1[~flip].mean(),
         100 * (A1[~flip].mean() - A0[~flip].mean()) / A0[~flip].mean()))
out["Q3"] = dict(flip_rate=float(flip.mean()),
                 flipped_off=float(A0[flip].mean()), flipped_on=float(A1[flip].mean()),
                 kept_off=float(A0[~flip].mean()), kept_on=float(A1[~flip].mean()))

print("\n=== Q4  FLAT regions (>=12 px from any strong edge) ===")
f0 = np.abs((r0 - y0)[flat]).astype(np.float64)
f1 = np.abs((r1 - y1)[flat]).astype(np.float64)
fb0 = np.abs((b0 - y0)[flat]).astype(np.float64)
fb1 = np.abs((b1 - y1)[flat]).astype(np.float64)
print("   mean |R-Y| flat  off=%.6f (%.1f DN)  on=%.6f (%.1f DN)  %+.3f%%"
      % (f0.mean(), f0.mean() * 65535, f1.mean(), f1.mean() * 65535,
         100 * (f1.mean() - f0.mean()) / f0.mean()))
print("   mean |B-Y| flat  off=%.6f  on=%.6f  %+.3f%%"
      % (fb0.mean(), fb1.mean(), 100 * (fb1.mean() - fb0.mean()) / fb0.mean()))
print("   flat percentiles of |R-Y|:")
for p in [50, 90, 99, 99.9]:
    a, b = np.percentile(f0, p), np.percentile(f1, p)
    print("     P%-5.1f off=%.6f (%6.1f DN)  on=%.6f (%6.1f DN)  %+.6f"
          % (p, a, a * 65535, b, b * 65535, b - a))
out["Q4"] = dict(r_off=float(f0.mean()), r_on=float(f1.mean()),
                 b_off=float(fb0.mean()), b_on=float(fb1.mean()))

print("\n=== Q5  per-channel mean |on - off| over the whole frame, in 16-bit DN ===")
for name, u, v in [("R", r0, r1), ("G", g0, g1), ("B", b0, b1)]:
    m = float(np.mean(np.abs(u.astype(np.float64) - v.astype(np.float64))) * 65535)
    p999 = float(np.percentile(np.abs(u - v), 99.9) * 65535)
    print("   %s  mean|on-off| = %8.1f DN   P99.9 = %8.1f DN" % (name, m, p999))
    out.setdefault("Q5", {})[name] = dict(mean_dn=m, p999_dn=p999)

with open(r"C:\dev\strehl-out\M114-ca-verify\r4.json", "w") as fh:
    json.dump(out, fh, indent=2)
print("\nwrote r4.json")
