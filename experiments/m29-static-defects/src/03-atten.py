"""
M29 / 03 -- What does the static-map pipeline actually do to a planted shadow?

Script 02 used ATTEN = 0.274, the map-domain trough script 01 recovered from a
4.0% frame-domain plant. Writing down the analytic response of the pipeline
afterwards gives a different number, and the two must be reconciled before any
detection limit quoted in these units means anything.

The pipeline is  m = mean_k[ g_k / blur24(g_k) ] - 1,  then  m <- m - blur24(m).
For a plant  g -> g*(1 - A*s)  with s a sigma-6 Gaussian:

  blur24(s) at the centre  = 36/(36+576) = 0.0588
  the ratio step keeps      (1 - A) / (1 - 0.0588 A)   ~=  1 - 0.941 A
  the highpass step keeps   0.941 A * (1 - 0.0588)     ~=  0.885 A

so the predicted map-domain trough is  -0.885 A, i.e. -3.54% for A = 4%. Script
01 measured -1.096%. A factor of 3.2 is not a rounding disagreement; one of the
two is wrong, and if it is the analytic one then my model of my own instrument
is wrong, which matters more than the dust question.

Three measurements, all on real data through the exact code path of script 01:

  A. single frame, plant swept over depth and radius -- is the response linear
     in depth, and does the radius dependence follow the blur24 geometry?
  B. the same, but reading the trough at the planted CENTRE rather than as the
     minimum over a window. Script 02's plant was read as a window minimum,
     which is an extremum over 3600 correlated pixels and therefore pinned by
     the scene, not by the plant. If A and B disagree, that is the defect.
  C. the multi-frame path, to check that averaging over frames does not itself
     attenuate a static plant (it must not: the plant is identical in every
     frame, so the mean of the ratio is the ratio).
"""
import glob, os, json
import numpy as np
import rawpy
from scipy.ndimage import gaussian_filter

BLACK, SIG = 512.0, 24.0
FOLDER = r"D:\personal\macro\109MSDCF"
PY, PX = 900, 1200
OUT = os.path.join(os.path.dirname(__file__), "..", "out")


def green(path):
    with rawpy.imread(path) as r:
        return r.raw_image_visible[0::2, 1::2].astype(np.float32) - BLACK


def mapify(frames):
    acc = None
    for g in frames:
        r = g / np.maximum(gaussian_filter(g, SIG), 1.0)
        acc = r if acc is None else acc + r
    m = acc / len(frames) - 1.0
    return (m - gaussian_filter(m, SIG)).astype(np.float32)


files = sorted(glob.glob(os.path.join(FOLDER, "*.ARW")))
g0 = green(files[0])
h, w = g0.shape
yy, xx = np.mgrid[0:h, 0:w]
d2 = ((yy - PY) ** 2 + (xx - PX) ** 2).astype(np.float32)
del yy, xx
print(f"frame {h}x{w}   local level at plant "
      f"{gaussian_filter(g0, SIG)[PY, PX]:.1f} DN")

base1 = mapify([g0])
rows = []
print(f"\nA/B  single frame, response read two ways")
print(f"{'depth':>7s} {'sigma':>6s} {'centre':>10s} {'win min':>10s} "
      f"{'centre/A':>9s} {'winmin/A':>9s}")
for r_ in (3.0, 6.0, 12.0):
    shape = np.exp(-d2 / (2 * r_ ** 2))
    for A in (0.01, 0.04, 0.16):
        m = mapify([g0 * (1.0 - A * shape)])
        d = m - base1
        sl = (slice(PY - 30, PY + 30), slice(PX - 30, PX + 30))
        c, wm = float(d[PY, PX]), float(d[sl].min())
        rows.append(dict(kind="single", r=r_, A=A, centre=c, winmin=wm))
        print(f"{100*A:6.1f}% {r_:6.1f} {100*c:9.3f}% {100*wm:9.3f}% "
              f"{-c/A:9.3f} {-wm/A:9.3f}")

print(f"\nC  multi-frame path (static plant, 8 frames)")
gs = [green(f) for f in files[::max(1, len(files) // 8)][:8]]
base8 = mapify(gs)
shape = np.exp(-d2 / (2 * 6.0 ** 2))
for A in (0.04, 0.16):
    m = mapify([g * (1.0 - A * shape) for g in gs])
    d = m - base8
    c = float(d[PY, PX])
    rows.append(dict(kind="multi8", r=6.0, A=A, centre=c, winmin=None))
    print(f"{100*A:6.1f}%    6.0 {100*c:9.3f}%            {-c/A:9.3f}")

pred = 0.885
got = [-x["centre"] / x["A"] for x in rows if x["r"] == 6.0 and x["kind"] == "single"]
print(f"\npredicted attenuation at sigma 6 {pred:.3f}   "
      f"measured at centre {np.mean(got):.3f}   "
      f"script-01 window-min figure 0.274")
with open(os.path.join(OUT, "03-atten.json"), "w") as fh:
    json.dump(dict(rows=rows, predicted=pred), fh, indent=1)
