"""Why does a real master exceed the ideal-step response 13x?
Hypothesis: an ideal step is NOT the worst case for a negative-lobe kernel.
The worst case is texture whose sign matches the kernel's negative lobes.
Derive PIL's actual weights, compute the provable envelope, then build the
worst-case input and check the instrument approaches it without exceeding it."""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vh_hull as V

scale = 7040.0 / 1400.0


def lanczos3(x):
    x = float(x)
    if x == 0.0:
        return 1.0
    if abs(x) >= 3.0:
        return 0.0
    return (3.0 * np.sin(np.pi * x) * np.sin(np.pi * x / 3.0)) / (np.pi * np.pi * x * x)


def pil_weights(xx, scale, support_units=3.0):
    """PIL ImagingResampleHorizontal, downscale branch."""
    fs = scale
    support = support_units * fs
    center = (xx + 0.5) * scale
    xmin = int(np.ceil(center - support))
    xmax = int(np.floor(center + support))
    w = np.array([lanczos3((i + 0.5 - center) / fs) for i in range(xmin, xmax + 1)])
    return w / w.sum()


ws = [pil_weights(x, scale) for x in range(400, 460)]
Ns = [float(-w[w < 0].sum()) for w in ws]
N = float(np.mean(Ns))
print("PIL Lanczos3 @ scale %.4f : taps %d" % (scale, len(ws[0])))
print("  negative weight mass N (1-D)  mean %.5f  min %.5f  max %.5f" % (N, min(Ns), max(Ns)))
print("  DERIVED 1-D envelope           %.2f DN of a 0..255 range" % (N * 255.0))
neg2d = 2.0 * N * (1.0 + N)
print("  DERIVED 2-D envelope  2N(1+N) = %.5f -> %.2f DN" % (neg2d, neg2d * 255.0))
print("")

# Ideal step, for contrast: only the taps on one side of the edge contribute.
print("  DERIVED ideal-step overshoot   %.2f DN of a 160 DN step"
      % (max(0.0, -np.cumsum(ws[30])[np.argmin(np.cumsum(ws[30]))]) * 160.0))
print("")

# Build the worst case: 2-D input sign-matched to the kernel's negative lobes.
W, H = 7040, 700
w1 = pil_weights(700, scale)
c = (700 + 0.5) * scale
xmin = int(np.ceil(c - 3.0 * scale))
a = np.zeros((H, W), np.float64)
col = np.full(W, 255.0)
for i, wi in enumerate(w1):
    if wi < 0:
        col[xmin + i] = 0.0                      # dark where weight is negative
a[:, :] = col[None, :]
a8 = np.clip(np.round(a), 0, 255).astype(np.uint8)
hi, lo = V.hull_bounds(a8)
print("  sign-matched worst case (1-D pattern):")
for k in ("box", "bilinear", "bicubic", "lanczos"):
    out = V.reduce_f(a8, k)
    s = V.excess_stats(out, hi, lo)
    print("    %-9s max_excess %7.3f  max_deficit %7.3f" % (k, s["max_excess"], s["max_deficit"]))
print("")
print("  MEASURED corpus max was 36.997 DN; envelope above is the provable ceiling.")
