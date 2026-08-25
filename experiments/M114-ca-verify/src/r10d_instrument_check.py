"""M114 R10d -- which polarity instrument is lying?

R8 searched a render-domain radial red scale on the OFF arm and read an
optimum of -704..-830e-6, i.e. the shipped -704.5e-6 is right or slightly
small (UNDER-corrected).  R10c ran the same search on the ON arm and read a
residual of +150..+379e-6, i.e. OVER-corrected by 21-54%.  Those cannot both
be true.  R10c's own P3 was a VACUOUS PASS (`all()` over an empty sequence
after every annulus read UNBRACKETED on a grid that did not reach -704.5e-6).

Decisive control: build a SYNTHETIC ON arm by applying exactly the shipped
-704.5e-6 to the OFF arm in the render domain, where the true residual is
known by construction to be whatever the OFF arm still wanted, and run the
identical ON-arm search on it.

  - If the search returns ~0 (or the small negative r8 predicts), the
    instrument is unbiased and the real ON arm IS over-corrected.
  - If it returns ~+200e-6 on the synthetic too, the reading is instrument
    bias -- the render-domain search cannot invert a plane-domain gather --
    and polarity is UNDECIDABLE by anything built tonight.

Bars, registered before running:
  Q1  the grid must BRACKET every reported minimum; endpoint minima are
      reported UNBRACKETED and never as a value.  (This is the bug that made
      R10c's P3 pass on zero data.)
  Q2  a bar computed over an EMPTY set is a FAIL, not a PASS.  Every gate
      below asserts its own sample count first.
  Q3  POSITIVE CONTROL: plant an extra -300e-6 on the synthetic arm; the
      recovered residual must move by -300e-6 +/- 60e-6 in EVERY annulus.
"""
import json
import sys

import numpy as np
import tifffile
from scipy import ndimage

OFF = r"C:\dev\strehl-out\M114-ca-verify\r1\unset.tif"
ON = r"C:\dev\strehl-out\M114-ca-verify\r1\on.tif"
SHIPPED = -704.5e-6
EDG = [0.0, 0.2, 0.4, 0.6, 0.788, 0.85, 0.92, 1.05]
GRID = np.array([-1400e-6, -1100e-6, -900e-6, -704.5e-6, -500e-6, -300e-6,
                 -150e-6, 0.0, 150e-6, 300e-6, 500e-6, 800e-6])


def load(p):
    return tifffile.imread(p).astype(np.float32) / np.float32(65535.0)


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
y0 = 0.2126 * a0[..., 0] + 0.7152 * a0[..., 1] + 0.0722 * a0[..., 2]
gy, gx = np.gradient(y0)
near = ndimage.distance_transform_edt(~(np.hypot(gx, gy) >= np.quantile(np.hypot(gx, gy), 0.99))) <= 3
yy, xx = np.mgrid[0:H, 0:W]
rad = (np.hypot(xx - W / 2.0, yy - H / 2.0) / np.hypot(W / 2.0, H / 2.0)).astype(np.float32)
del yy, xx
masks = [(rad >= EDG[i]) & (rad < EDG[i + 1]) & near for i in range(len(EDG) - 1)]
names = ["%.2f-%.2f" % (EDG[i], EDG[i + 1]) for i in range(len(EDG) - 1)]


def search(red, g, b, label):
    tab = np.zeros((len(GRID), len(masks)))
    for k, e in enumerate(GRID):
        rr = radial_scale(red, e)
        yv = 0.2126 * rr + 0.7152 * g + 0.0722 * b
        d = np.abs(hp(rr - yv))
        for j, m in enumerate(masks):
            tab[k, j] = d[m].mean()
        del rr, yv, d
    res = []
    print("\n  %s" % label)
    print("  %-12s %9s %14s   %s" % ("annulus", "n", "residual e-6", "reading"))
    for j in range(len(masks)):
        col = tab[:, j]
        k = int(np.argmin(col))
        n = int(masks[j].sum())
        if k == 0 or k == len(GRID) - 1:
            res.append((names[j], n, None))
            print("  %-12s %9d %14s   Q1 UNBRACKETED" % (names[j], n, "-"))
            continue
        x = GRID[k - 1:k + 2] * 1e6
        yv = col[k - 1:k + 2]
        den = yv[0] - 2 * yv[1] + yv[2]
        xo = float(x[1] - 0.5 * (x[2] - x[0]) * (yv[2] - yv[0]) / (4 * den)) if den > 0 else float(x[1])
        res.append((names[j], n, xo))
        tag = ("at target" if abs(xo) < 60 else
               ("UNDER-corrected" if xo < 0 else "*** OVER-corrected ***"))
        print("  %-12s %9d %+14.1f   %s%s" % (names[j], n, xo, tag,
                                              "   PAST SUPPORT" if float(names[j].split("-")[0]) >= 0.788 else ""))
    return res


def gate(name, vals, pred, tol):
    """Q2: an empty sample is a FAIL, never a vacuous pass."""
    vals = [v for v in vals if v is not None]
    if not vals:
        print("  %s -> FAIL (no bracketed annuli; the bar had NOTHING to test)" % name)
        return False
    ok = all(abs(v - pred) <= tol for v in vals)
    print("  %s -> %s  (n=%d annuli, want %+.1f +/- %.1f, got %s)"
          % (name, "PASS" if ok else "FAIL", len(vals), pred, tol,
             " ".join("%+.0f" % v for v in vals)))
    return ok


print("=== the real ON arm ===")
real = search(a1[..., 0], a1[..., 1], a1[..., 2], "ON arm (shipped correction, plane-domain)")

print()
print("=== the SYNTHETIC ON arm: OFF + exactly the shipped -704.5e-6, render-domain ===")
synth_r = radial_scale(a0[..., 0], SHIPPED)
syn = search(synth_r, a0[..., 1], a0[..., 2], "synthetic ON (residual known to be ~0 to -126e-6)")

print()
print("  Q3 POSITIVE CONTROL: synthetic ON with an extra planted -300e-6")
pl = search(radial_scale(synth_r, -300e-6), a0[..., 1], a0[..., 2], "  synthetic + plant(-300e-6)")
moved = [b - a for (_, _, a), (_, _, b) in zip(syn, pl) if a is not None and b is not None]
q3 = gate("Q3", moved, -300.0, 60.0)

print()
print("=== ADJUDICATION ===")
sv = [v for _, _, v in syn if v is not None]
rv = [v for _, _, v in real if v is not None]
if not sv or not rv:
    print("  UNDECIDABLE: not enough bracketed annuli to compare.")
    sys.exit(0)
bias = float(np.mean(sv))
print("  synthetic-arm reading (should be ~0 to -126e-6): mean %+.1fe-6 over %d annuli"
      % (bias, len(sv)))
print("  real ON-arm reading:                             mean %+.1fe-6 over %d annuli"
      % (float(np.mean(rv)), len(rv)))
if abs(bias) < 60:
    print("  -> instrument is UNBIASED. The real ON arm's reading stands.")
else:
    print("  -> instrument carries a %+.1fe-6 BIAS it invents on an arm whose residual is"
          % bias)
    print("     known to be near zero. The render-domain search CANNOT invert a")
    print("     plane-domain gather, so R10c's over-correction verdict is NOT")
    print("     REPORTABLE, and R8's OFF-arm optimum inherits the same doubt.")
    print("  -> POLARITY PAST r=0.788 IS UNDECIDABLE with anything built tonight.")
    print("  bias-corrected real reading: %+.1fe-6" % (float(np.mean(rv)) - bias))
with open(r"C:\dev\strehl-out\M114-ca-verify\r10d.json", "w") as fh:
    json.dump(dict(real=real, synth=syn, bias=bias, q3=q3), fh, indent=2)
print("\nwrote r10d.json")
