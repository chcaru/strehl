"""M114 R8 -- (a) a fairer chroma control, (b) is the radial model right PAST
the fit support?

(a) M107's W4 control is mean |B-Y|, which on this subject is dominated by the
    SCENE's own colour (a warm cream wing), not by fringing: flat |B-Y| is
    0.0429 against 0.0600 near edges.  High-pass the chroma with a 31-px box
    first, so the statistic measures the FRINGE and not the subject.

(b) An independent estimate of eps(r) that does not use M107's fit at all.
    Take the CA-OFF render, apply a render-domain radial scale of eps to RED
    only, and find the eps that MINIMISES high-passed |R-Y| near edges, in each
    radial annulus.  If lateral CA really is a linear radial magnification, the
    minimising eps is CONSTANT in r.  If |eps_opt| grows with r, the shipped
    linear model UNDER-corrects the corner; if it shrinks, it OVER-corrects
    exactly where there was no data.
    The shipped coefficient is -704.5e-6.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage

OFF = r"C:\dev\strehl-out\M114-ca-verify\r1\unset.tif"
ON = r"C:\dev\strehl-out\M114-ca-verify\r1\on.tif"
EPS_SHIPPED = -704.5e-6
BOX = 31
out = {}


def load(p):
    return tifffile.imread(p).astype(np.float32) / np.float32(65535.0)


def yof(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def hp(x):
    return x - ndimage.uniform_filter(x, BOX, mode="nearest")


def radial_scale(chan, eps):
    h, w = chan.shape
    cx, cy = w * 0.5, h * 0.5
    s = 1.0 + eps
    o = np.empty_like(chan)
    xs = (np.arange(w, dtype=np.float64) - cx) * s + cx
    for y0 in range(0, h, 512):
        y1 = min(y0 + 512, h)
        ys = (np.arange(y0, y1, dtype=np.float64) - cy) * s + cy
        yy, xx = np.meshgrid(ys, xs, indexing="ij")
        o[y0:y1] = ndimage.map_coordinates(chan, [yy, xx], order=3,
                                           mode="nearest").astype(np.float32)
    return o


a0 = load(OFF)
a1 = load(ON)
H, W, _ = a0.shape
y0 = yof(a0)
gy, gx = np.gradient(y0)
edge = np.hypot(gx, gy) >= np.quantile(np.hypot(gx, gy), 0.99)
near = ndimage.distance_transform_edt(~edge) <= 3
cy_, cx_ = H * 0.5, W * 0.5
yy, xx = np.mgrid[0:H, 0:W]
rad = (np.hypot(xx - cx_, yy - cy_) / np.hypot(cx_, cy_)).astype(np.float32)
del yy, xx
rn = rad[near].astype(np.float64)
del rad

print("=== (a) high-passed chroma near edges (31px box), fixed pixel set ===")
r_off = hp((a0[..., 0] - y0))[near].astype(np.float64)
b_off = hp((a0[..., 2] - y0))[near].astype(np.float64)
y1 = yof(a1)
r_on = hp((a1[..., 0] - y1))[near].astype(np.float64)
b_on = hp((a1[..., 2] - y1))[near].astype(np.float64)
print("   mean |hp(R-Y)| off=%.6f (%.1f DN)  on=%.6f (%.1f DN)  %+.2f%%"
      % (np.abs(r_off).mean(), np.abs(r_off).mean() * 65535,
         np.abs(r_on).mean(), np.abs(r_on).mean() * 65535,
         100 * (np.abs(r_on).mean() - np.abs(r_off).mean()) / np.abs(r_off).mean()))
print("   mean |hp(B-Y)| off=%.6f (%.1f DN)  on=%.6f (%.1f DN)  %+.2f%%"
      % (np.abs(b_off).mean(), np.abs(b_off).mean() * 65535,
         np.abs(b_on).mean(), np.abs(b_on).mean() * 65535,
         100 * (np.abs(b_on).mean() - np.abs(b_off).mean()) / np.abs(b_off).mean()))
print("   red/blue fringe ratio  off=%.3f  on=%.3f"
      % (np.abs(r_off).mean() / np.abs(b_off).mean(),
         np.abs(r_on).mean() / np.abs(b_on).mean()))
out["hp"] = dict(r_off=float(np.abs(r_off).mean()), r_on=float(np.abs(r_on).mean()),
                 b_off=float(np.abs(b_off).mean()), b_on=float(np.abs(b_on).mean()))
del r_on, b_on, y1, a1

print("\n=== (b) eps that minimises high-passed |R-Y|, per annulus ===")
grid = np.array([0.0, -200e-6, -400e-6, -550e-6, -704.5e-6, -850e-6,
                 -1000e-6, -1200e-6, -1500e-6])
edges = [0.0, 0.2, 0.4, 0.6, 0.7, 0.788, 0.85, 0.92, 1.05]
masks = [(rn >= edges[i]) & (rn < edges[i + 1]) for i in range(len(edges) - 1)]
table = np.zeros((len(grid), len(masks)))
g0c, b0c = a0[..., 1], a0[..., 2]
for k, e in enumerate(grid):
    rr = radial_scale(a0[..., 0], e)
    yy2 = 0.2126 * rr + 0.7152 * g0c + 0.0722 * b0c
    d = np.abs(hp(rr - yy2))[near].astype(np.float64)
    for j, m in enumerate(masks):
        table[k, j] = d[m].mean()
    print("   eps=%+9.1fe-6  " % (e * 1e6)
          + " ".join("%.5f" % table[k, j] for j in range(len(masks))), flush=True)
    del rr, yy2, d

print("\n   annulus        n        eps_opt(e-6)   min|hp(R-Y)|   at shipped   support")
res_rows = []
for j, m in enumerate(masks):
    col = table[:, j]
    k = int(np.argmin(col))
    # parabolic refinement on the three points around the minimum
    if 0 < k < len(grid) - 1:
        x = grid[k - 1:k + 2] * 1e6
        yv = col[k - 1:k + 2]
        den = (yv[0] - 2 * yv[1] + yv[2])
        xo = x[1] - 0.5 * (x[2] - x[0]) * (yv[2] - yv[0]) / (4 * den) if den > 0 else x[1]
    else:
        xo = grid[k] * 1e6
    ship = col[list(grid).index(EPS_SHIPPED)]
    tag = "in" if edges[j + 1] <= 0.788 else "PAST"
    res_rows.append(dict(lo=edges[j], hi=edges[j + 1], n=int(m.sum()),
                         eps_opt=float(xo), fmin=float(col[k]), f_ship=float(ship)))
    print("   %.2f-%.2f %9d      %+8.1f       %.6f      %.6f    %s"
          % (edges[j], edges[j + 1], m.sum(), xo, col[k], ship, tag))
out["eps_opt"] = res_rows
out["grid"] = list(grid)
out["table"] = table.tolist()
with open(r"C:\dev\strehl-out\M114-ca-verify\r8.json", "w") as fh:
    json.dump(out, fh, indent=2)
print("\nwrote r8.json")
