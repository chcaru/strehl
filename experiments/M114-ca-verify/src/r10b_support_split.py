"""M114 R10b -- ORCH item 5, sharpened: split at r = 0.788, and test POLARITY.

Three questions ORCH raised that nobody has answered:

 B  Split every one of M107's headline statistics at the support boundary
    r = 0.788.  A -54% top decile produced by extrapolated coefficients is a
    different and weaker claim than the same number produced inside the fit.

 C  Does the fringe REVERSE polarity past r = 0.788 (over-correction), merely
    shrink (under-correction), or vanish (correct extrapolation)?
    Instrument: lateral CA is a radial displacement of red relative to luma.
    For a small shift d,  R - Y  ~  d * dY/dr.  So a weighted least-squares
    d = <hp(R-Y) * dY/dr> / <(dY/dr)^2> recovers the SIGNED displacement in
    pixels, per annulus, for each arm.  d_off should grow linearly with r
    (that is what "lateral" means).  d_on ~ 0 is correct; same sign as d_off
    is under-correction; OPPOSITE sign is over-correction, i.e. reversal.
    Positive control: plant a known radial red scale on the OFF arm and check
    the estimator returns it.

 D  Is W3's sign-flip population concentrated at high radius?  If so the
    aggregate failure becomes a precise statement about the extrapolation.

Bars, registered before running:
  B1  the inside/outside split must reconstruct the whole-frame numbers.
  C1  POSITIVE CONTROL: on a planted radial red scale of +500e-6 the estimator
      must return d within 15% of the predicted +500e-6 * r_px, at every
      annulus, or the polarity result is not reportable.
  C2  d_off must grow monotonically with r (the lateral-CA signature) or the
      instrument is not measuring lateral CA.
"""
import json

import numpy as np
import tifffile
from scipy import ndimage

OFF = r"C:\dev\strehl-out\M114-ca-verify\r1\unset.tif"
ON = r"C:\dev\strehl-out\M114-ca-verify\r1\on.tif"
SUP = 0.788
EPS_SHIPPED = 704.5e-6
out = {}

a0 = tifffile.imread(OFF).astype(np.float32) / np.float32(65535.0)
a1 = tifffile.imread(ON).astype(np.float32) / np.float32(65535.0)
H, W, _ = a0.shape
RC = np.hypot(W / 2.0, H / 2.0)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
dxr = xx - W / 2.0
dyr = yy - H / 2.0
rpx = np.hypot(dxr, dyr)
rad = rpx / RC
del yy, xx


def yof(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def hp(x):
    return x - ndimage.uniform_filter(x, 31, mode="nearest")


y0, y1 = yof(a0), yof(a1)
gy, gx = np.gradient(y0)
mag = np.hypot(gx, gy)
edge = mag >= np.quantile(mag, 0.99)
near = ndimage.distance_transform_edt(~edge) <= 3
ry0 = a0[..., 0] - y0
ry1 = a1[..., 0] - y1
by0 = a0[..., 2] - y0
by1 = a1[..., 2] - y1

rn = rad[near]
inside = rn <= SUP
outside = ~inside
print("near-edge px %d   inside 0.788: %d (%.2f%%)   outside: %d (%.2f%%)"
      % (near.sum(), inside.sum(), 100 * inside.mean(),
         outside.sum(), 100 * outside.mean()))

print()
print("=== B  M107's headline statistics, split at the support boundary ===")


def pct(a, b):
    return 100.0 * (b - a) / a


s0, s1 = np.abs(ry0[near]), np.abs(ry1[near])
b0, b1 = np.abs(by0[near]), np.abs(by1[near])
rows = {}
for tag, m in (("WHOLE", np.ones_like(inside)), ("inside<=0.788", inside),
               ("outside>0.788", outside)):
    fa0 = int((s0[m] > 0.06).sum())
    fa1 = int((s1[m] > 0.06).sum())
    rows[tag] = dict(n=int(m.sum()), area_off=fa0, area_on=fa1,
                     area_pct=pct(fa0, fa1) if fa0 else float("nan"),
                     ry_off=float(s0[m].mean()), ry_on=float(s1[m].mean()),
                     ry_pct=float(pct(s0[m].mean(), s1[m].mean())),
                     by_pct=float(pct(b0[m].mean(), b1[m].mean())))
    print("  %-14s n=%8d   W1 area %7d -> %7d (%+7.2f%%)   W3 |R-Y| %+7.2f%%   W4 |B-Y| %+7.2f%%"
          % (tag, m.sum(), fa0, fa1, rows[tag]["area_pct"],
             rows[tag]["ry_pct"], rows[tag]["by_pct"]))
b1ok = (rows["inside<=0.788"]["area_off"] + rows["outside>0.788"]["area_off"]
        == rows["WHOLE"]["area_off"])
print("  B1 split reconstructs the whole: %s" % ("PASS" if b1ok else "FAIL"))
print("  share of the TOTAL fringe-area reduction contributed outside 0.788: %.1f%%"
      % (100.0 * (rows["outside>0.788"]["area_off"] - rows["outside>0.788"]["area_on"])
         / (rows["WHOLE"]["area_off"] - rows["WHOLE"]["area_on"])))

print()
print("  top decile of |R-Y|_off -- ORCH asks whether -54.08%% is an extrapolation artefact")
thr = np.quantile(s0, 0.9)
d10 = s0 >= thr
print("    WHOLE-frame decile 10: %+.2f%%   (M107 reports -54.08%%)"
      % pct(s0[d10].mean(), s1[d10].mean()))
print("    radial composition of decile 10: %.2f%% of it lies outside 0.788 "
      "(vs %.2f%% of all near-edge px)"
      % (100 * outside[d10].mean(), 100 * outside.mean()))
for tag, m in (("inside<=0.788", inside), ("outside>0.788", outside)):
    t = np.quantile(s0[m], 0.9)
    dd = m & (s0 >= t)
    print("    decile 10 computed WITHIN %-14s: %+.2f%%   (n=%d)"
          % (tag, pct(s0[dd].mean(), s1[dd].mean()), dd.sum()))
out["B"] = rows

print()
print("=== C  POLARITY: signed radial displacement of red vs luma, per annulus ===")
gyr, gxr = np.gradient(y0)
dydr = (gxr * dxr + gyr * dyr) / np.maximum(rpx, 1e-6)
gyr1, gxr1 = np.gradient(y1)
dydr1 = (gxr1 * dxr + gyr1 * dyr) / np.maximum(rpx, 1e-6)
# use edges whose gradient is substantially radial; that is where a radial
# displacement is observable at all.
usable = near & (np.abs(dydr) >= 0.5 * mag) & (mag > np.quantile(mag, 0.99))
print("  usable radial-edge px: %d (%.3f%% of frame)" % (usable.sum(), 100 * usable.mean()))

hr0 = hp(ry0)
hr1 = hp(ry1)


def shift(num_field, den_field, m):
    n = float(np.sum(num_field[m] * den_field[m]))
    d = float(np.sum(den_field[m] * den_field[m]))
    return n / d if d > 0 else float("nan")


# C1 positive control: plant a known radial red scale on the OFF arm.
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


PLANT = 500e-6
rp = radial_scale(a0[..., 0], PLANT)
yp = 0.2126 * rp + 0.7152 * a0[..., 1] + 0.0722 * a0[..., 2]
hrp = hp(rp - yp)

EDG = [0.0, 0.2, 0.4, 0.6, 0.788, 0.85, 0.92, 1.05]
print()
print("  %-12s %8s   %9s %9s %9s   %10s   %s"
      % ("annulus", "n", "d_off px", "d_on px", "d_plant", "eps_off", "verdict"))
c1_ok, c2_seq, res = True, [], []
for i in range(len(EDG) - 1):
    m = usable & (rad >= EDG[i]) & (rad < EDG[i + 1])
    if m.sum() < 300:
        print("  %.2f-%.2f  n=%d (too few)" % (EDG[i], EDG[i + 1], m.sum()))
        continue
    d_off = shift(hr0, dydr, m)
    d_on = shift(hr1, dydr1, m)
    d_pl = shift(hrp, dydr, m) - d_off
    rmid = float(rpx[m].mean())
    pred = PLANT * rmid
    err = abs(d_pl - pred) / abs(pred)
    if err > 0.15:
        c1_ok = False
    c2_seq.append(d_off)
    if abs(d_on) < 0.15 * abs(d_off):
        v = "NULLED"
    elif np.sign(d_on) == np.sign(d_off):
        v = "under-corrected"
    else:
        v = "*** REVERSED (over) ***"
    eps_off = d_off / rmid
    res.append(dict(lo=EDG[i], hi=EDG[i + 1], n=int(m.sum()), d_off=d_off,
                    d_on=d_on, eps_off=float(eps_off), verdict=v))
    print("  %.2f-%.2f %9d   %+9.4f %+9.4f %+9.4f   %+9.1fe-6   %s%s"
          % (EDG[i], EDG[i + 1], m.sum(), d_off, d_on, d_pl, eps_off * 1e6, v,
             "   PAST SUPPORT" if EDG[i] >= SUP else ""))
print("  control predicted plant %+0.1fe-6 * r_px; measured within 15%% everywhere: %s"
      % (PLANT * 1e6, "C1 PASS" if c1_ok else "C1 FAIL"))
mono = all(c2_seq[i] <= c2_seq[i + 1] for i in range(len(c2_seq) - 1)) or \
       all(c2_seq[i] >= c2_seq[i + 1] for i in range(len(c2_seq) - 1))
print("  d_off monotone in r (the lateral-CA signature): %s" % ("C2 PASS" if mono else "C2 FAIL"))
print("  shipped coefficient is %.1fe-6; eps_off is what the image says it should be."
      % (EPS_SHIPPED * 1e6))
out["C"] = res

print()
print("=== D  W3's sign flips -- are they concentrated past the support? ===")
flip = (np.sign(ry0[near]) != np.sign(ry1[near]))
print("  whole-frame keep-sign %.1f%%  (M107 reports 75.1%%)" % (100 * (~flip).mean()))
print("  keep-sign inside  <=0.788: %.1f%%" % (100 * (~flip[inside]).mean()))
print("  keep-sign outside  >0.788: %.1f%%" % (100 * (~flip[outside]).mean()))
print("  share of ALL flipped px lying outside 0.788: %.2f%%  "
      "(outside is %.2f%% of near-edge px)"
      % (100 * outside[flip].mean(), 100 * outside.mean()))
print()
print("  %-12s %9s %10s   %s" % ("annulus", "n", "keep-sign", "mean |R-Y| of flipped px, DN"))
for i in range(len(EDG) - 1):
    m = (rn >= EDG[i]) & (rn < EDG[i + 1])
    if m.sum() < 300:
        continue
    f = flip & m
    print("  %.2f-%.2f %9d %9.1f%%   %8.1f -> %8.1f  (%+.2f%%)%s"
          % (EDG[i], EDG[i + 1], m.sum(), 100 * (~flip[m]).mean(),
             s0[f].mean() * 65535, s1[f].mean() * 65535,
             pct(s0[f].mean(), s1[f].mean()),
             "   PAST SUPPORT" if EDG[i] >= SUP else ""))

with open(r"C:\dev\strehl-out\M114-ca-verify\r10b.json", "w") as fh:
    json.dump(out, fh, indent=2)
print("\nwrote r10b.json")
