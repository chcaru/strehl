"""M114 R10c -- polarity, on an instrument that passes its controls.

R10b's linearised shift estimator (R-Y ~ d * dY/dr) FAILED its own planted
control (C1: under-read a known +500e-6 plant by 32-88%, worsening with
radius) and failed C2.  Its "REVERSED" verdicts are therefore NOT REPORTABLE.
They also appeared at EVERY radius including the innermost, which is the
signature of estimator bias rather than of an over-extrapolated radial term.

Replace it with a search on the real objective, which needs no linearisation:
take the ON arm and apply an ADDITIONAL render-domain radial red scale over a
grid.  If the shipped correction OVER-shoots past r = 0.788, the residual that
minimises edge chroma there will be POSITIVE (undoing part of it).  If it
UNDER-shoots, the residual will be NEGATIVE (asking for more).  If it is right,
the residual will be ~0.  One signed number per annulus, and the sign is the
whole answer.

Also: split M107's W1 fringe area at r = 0.788 on its EXACT whole-frame
definition (r10b split the near-edge-restricted variant, a different
population).

Bars, registered before running:
  P1  the objective must be a BOWL with an interior minimum in every annulus
      (endpoint minima mean the grid does not bracket the answer -> report
      UNBRACKETED, never a clipped value).
  P2  POSITIVE CONTROL: plant a known extra -300e-6 on the ON arm; every
      annulus's recovered residual must move by -300e-6 +/- 20%.  A search
      that cannot see a planted shift cannot see a real one.
  P3  NULL CONTROL: run the identical search on the OFF arm; it must recover
      the shipped -704.5e-6 to within 20%, since that is what OFF is missing.
"""
import json

import numpy as np
import tifffile
from scipy import ndimage

OFF = r"C:\dev\strehl-out\M114-ca-verify\r1\unset.tif"
ON = r"C:\dev\strehl-out\M114-ca-verify\r1\on.tif"
SUP = 0.788
SHIPPED = -704.5e-6
EDG = [0.0, 0.2, 0.4, 0.6, 0.788, 0.85, 0.92, 1.05]
out = {}


def load(p):
    return tifffile.imread(p).astype(np.float32) / np.float32(65535.0)


def yof(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def hp(x):
    return x - ndimage.uniform_filter(x, 31, mode="nearest")


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


a0 = load(OFF)
a1 = load(ON)
H, W, _ = a0.shape
y0 = yof(a0)
gy, gx = np.gradient(y0)
mag = np.hypot(gx, gy)
near = ndimage.distance_transform_edt(~(mag >= np.quantile(mag, 0.99))) <= 3
yy, xx = np.mgrid[0:H, 0:W]
rad = (np.hypot(xx - W / 2.0, yy - H / 2.0) / np.hypot(W / 2.0, H / 2.0)).astype(np.float32)
del yy, xx

print("=== W1 fringe area on M107's EXACT whole-frame definition, split at 0.788 ===")
f0 = np.abs(a0[..., 0] - y0) > 0.06
f1 = np.abs(a1[..., 0] - yof(a1)) > 0.06
ins = rad <= SUP
for tag, m in (("WHOLE", np.ones_like(ins)), ("inside<=0.788", ins), ("outside>0.788", ~ins)):
    c0, c1 = int((f0 & m).sum()), int((f1 & m).sum())
    print("  %-14s  %8d -> %8d   %+7.2f%%" % (tag, c0, c1, 100.0 * (c1 - c0) / c0))
tot = int(f0.sum()) - int(f1.sum())
print("  share of the -10.20%% whole-frame reduction contributed outside 0.788: %.1f%%"
      % (100.0 * (int((f0 & ~ins).sum()) - int((f1 & ~ins).sum())) / tot))
print("  fraction of ALL fringe-area pixels (off arm) lying outside 0.788: %.2f%%"
      % (100.0 * (f0 & ~ins).sum() / f0.sum()))
del f0, f1, ins

GRID = np.array([-600e-6, -400e-6, -250e-6, -125e-6, 0.0,
                 125e-6, 250e-6, 400e-6, 600e-6])
masks = [(rad >= EDG[i]) & (rad < EDG[i + 1]) & near for i in range(len(EDG) - 1)]
names = ["%.2f-%.2f" % (EDG[i], EDG[i + 1]) for i in range(len(EDG) - 1)]


def search(arm, label, plant=0.0):
    base = arm[..., 0]
    if plant:
        base = radial_scale(base, plant)
    g, b = arm[..., 1], arm[..., 2]
    tab = np.zeros((len(GRID), len(masks)))
    for k, e in enumerate(GRID):
        rr = radial_scale(base, e)
        yv = 0.2126 * rr + 0.7152 * g + 0.0722 * b
        d = np.abs(hp(rr - yv))
        for j, m in enumerate(masks):
            tab[k, j] = d[m].mean()
        del rr, yv, d
    res = []
    for j in range(len(masks)):
        col = tab[:, j]
        k = int(np.argmin(col))
        n = int(masks[j].sum())
        if n < 3000:
            res.append((names[j], n, float("nan"), "TOO FEW"))
            continue
        if k == 0 or k == len(GRID) - 1:
            res.append((names[j], n, float("nan"), "UNBRACKETED"))
            continue
        x = GRID[k - 1:k + 2] * 1e6
        yv = col[k - 1:k + 2]
        den = yv[0] - 2 * yv[1] + yv[2]
        xo = x[1] - 0.5 * (x[2] - x[0]) * (yv[2] - yv[0]) / (4 * den) if den > 0 else x[1]
        res.append((names[j], n, float(xo), "bowl"))
    print("\n  %s" % label)
    print("  %-12s %9s %14s   %s" % ("annulus", "n", "residual e-6", "reading"))
    for nm, n, xo, st in res:
        if st != "bowl":
            print("  %-12s %9d %14s   %s" % (nm, n, "-", st))
            continue
        if abs(xo) < 60:
            verdict = "at target"
        elif xo < 0:
            verdict = "UNDER-corrected (wants more)"
        else:
            verdict = "*** OVER-corrected (wants it undone) ***"
        print("  %-12s %9d %+14.1f   %s%s"
              % (nm, n, xo, verdict,
                 "   PAST SUPPORT" if float(nm.split("-")[0]) >= SUP else ""))
    return res


print()
print("=== POLARITY: what residual radial red scale does each arm still want? ===")
on_res = search(a1, "ON arm  (shipped correction applied)")
print()
print("  P2 POSITIVE CONTROL: ON arm with a planted extra -300e-6")
pl = search(a1, "  ON arm + plant(-300e-6)", plant=-300e-6)
ok2 = True
for (n0, _, x0, s0), (n1, _, x1, s1) in zip(on_res, pl):
    if s0 == "bowl" and s1 == "bowl":
        d = x1 - x0
        good = abs(d - 300.0) <= 60.0
        ok2 &= good
        print("     %-12s  moved %+8.1f e-6 (want +300 +/- 60)  %s"
              % (n0, d, "ok" if good else "MISS"))
print("  P2 -> %s" % ("PASS" if ok2 else "FAIL"))

print()
print("  P3 NULL CONTROL: the OFF arm must ask for the shipped -704.5e-6")
off_res = search(a0, "  OFF arm (no correction)")
ok3 = all(abs(x - SHIPPED * 1e6) <= 0.2 * abs(SHIPPED * 1e6)
          for _, _, x, s in off_res if s == "bowl")
print("  P3 -> %s (bar: within 20%% of %.1fe-6)" % ("PASS" if ok3 else "FAIL", SHIPPED * 1e6))

out["on"] = on_res
out["off"] = off_res
with open(r"C:\dev\strehl-out\M114-ca-verify\r10c.json", "w") as fh:
    json.dump(out, fh, indent=2)
print("\nwrote r10c.json")
