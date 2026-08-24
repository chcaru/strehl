"""Is the halo's outer boundary a step or a ramp?

A veil from defocused foreground is a smooth optical falloff. A piecewise
constant winner field produces a discontinuity. These are distinguishable by
the profile across the boundary, and they imply different fixes, so measure
rather than eyeball -- fact 1250 is what eyeballing costs.

Method: walk scanlines across the halo's outer contour in the background,
away from the subject. Compare the largest |first difference| on the contour
against the same statistic on matched background scanlines that do not cross
it. A step gives a spike; a ramp does not.
"""
import os
import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif"
a = tifffile.imread(SRC).astype(np.float32).mean(axis=2)
H, W = a.shape

# Two bands: one crossing the halo contour below the left leg, one in clean
# background far from any silhouette, same size, same nominal brightness.
BANDS = {
    "crosses-halo-contour": (760, 3980, 420, 1),   # x0, y0, length, +x
    "crosses-halo-contour-2": (700, 3760, 420, 1),
    "clean-background-A": (5900, 700, 420, 1),
    "clean-background-B": (6100, 3900, 420, 1),
}
NROWS = 96  # average this many adjacent scanlines to kill photon noise


def profile(x0, y0, ln):
    blk = a[y0:y0 + NROWS, x0:x0 + ln]
    return blk.mean(axis=0)


print("%-24s %8s %8s %8s %8s" % ("band", "range", "max|d|", "med|d|", "ratio"))
res = {}
for name, (x0, y0, ln, _) in BANDS.items():
    p = profile(x0, y0, ln)
    d = np.abs(np.diff(p))
    mx, md = float(d.max()), float(np.median(d))
    res[name] = (mx, md)
    print("%-24s %8.1f %8.2f %8.3f %8.1f"
          % (name, float(p.max() - p.min()), mx, md, mx / max(md, 1e-9)))

hb = max(res["crosses-halo-contour"][0], res["crosses-halo-contour-2"][0])
cb = max(res["clean-background-A"][0], res["clean-background-B"][0])
print()
print("largest single-pixel step on the halo contour : %.2f DN" % hb)
print("largest single-pixel step in clean background : %.2f DN" % cb)
print("contour / background                          : %.2fx" % (hb / max(cb, 1e-9)))
print()
if hb > 3.0 * cb:
    print("VERDICT: the outer boundary is a STEP. Piecewise-constant admission.")
else:
    print("VERDICT: no step above background. The halo is a smooth optical veil.")

# Where exactly is the step, and how wide? Report the profile around it.
p = profile(*BANDS["crosses-halo-contour"][:3])
i = int(np.argmax(np.abs(np.diff(p))))
lo = max(0, i - 6); hi = min(len(p), i + 8)
print()
print("profile across the step (DN), index %d..%d:" % (lo, hi - 1))
print("  " + "  ".join("%.1f" % v for v in p[lo:hi]))
