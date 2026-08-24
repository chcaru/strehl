"""R9b -- are the sign flips noise churn or genuine recolouring?

R9's W3 bar (>90% of falling pixels keep their sign) FAILED at 75.1%, and the
registered verdict is therefore "RECOLOURED, NOT REMOVED". That bar stands.

But the bar cannot distinguish two very different situations:
  (a) sign flips concentrated where |R-Y| was already ~0 -- unavoidable noise
      churn around zero under ANY sub-pixel shift, and harmless;
  (b) sign flips at LARGE |R-Y| -- a genuine recolouring of a strong fringe,
      which is the bad outcome.

This does not move the bar. It qualifies it, and the answer decides whether the
honest headline is "recoloured" or "corrected, with noise-level sign churn".

  Q1  Median |R-Y|_off among sign-FLIPPED near-edge pixels, vs among
      sign-PRESERVED ones. If flipped pixels started far closer to zero, the
      flips are churn.
  Q2  Restrict to pixels with a STRONG initial deviation (|R-Y|_off above its
      90th percentile among near-edge pixels) and recompute the flip rate and
      the mean-|R-Y| change there. This is where a real fringe lives.
"""
import os
import numpy as np
import tifffile
from scipy import ndimage

R7 = r"C:\dev\strehl-out\M107-chroma\r7"


def load(p):
    a = tifffile.imread(p).astype(np.float64) / 65535.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return r, b, y


r0, b0, y0 = load(os.path.join(R7, "off1.tif"))
r1, b1, y1 = load(os.path.join(R7, "on.tif"))

gy, gx = np.gradient(y0)
gm = np.hypot(gx, gy)
edge = gm >= np.quantile(gm, 0.99)
near = ndimage.distance_transform_edt(~edge) <= 3

d0 = (r0 - y0)[near]
d1 = (r1 - y1)[near]
a0 = np.abs(d0)
flip = np.sign(d0) != np.sign(d1)

print("=" * 66)
print("R9b -- are the sign flips churn, or recolouring?")
print("=" * 66)
print(f"\nnear-edge pixels: {a0.size}")
print(f"overall flip rate: {100*flip.mean():.2f}%")

print("\nQ1  where did the flipped pixels START?")
print(f"    median |R-Y|_off, sign-FLIPPED   : {np.median(a0[flip]):.6f}")
print(f"    median |R-Y|_off, sign-PRESERVED : {np.median(a0[~flip]):.6f}")
ratio = np.median(a0[~flip]) / max(np.median(a0[flip]), 1e-12)
print(f"    preserved/flipped ratio          : {ratio:.2f}x")
print(f"    -> {'CHURN: flips are concentrated near zero' if ratio > 2 else 'RECOLOURING: flips occur at comparable magnitude'}")

print("\nQ2  restrict to STRONG initial deviation (top decile of |R-Y|_off)")
thr = np.quantile(a0, 0.90)
strong = a0 >= thr
print(f"    threshold |R-Y|_off >= {thr:.6f}   n={int(strong.sum())}")
print(f"    flip rate among strong pixels    : {100*flip[strong].mean():.2f}%")
print(f"    mean |R-Y| there: off={a0[strong].mean():.6f} "
      f"on={np.abs(d1)[strong].mean():.6f}  "
      f"({100*(np.abs(d1)[strong].mean()-a0[strong].mean())/a0[strong].mean():+.2f}%)")

print("\n    decile profile of |R-Y|_off vs change:")
qs = np.quantile(a0, np.linspace(0, 1, 11))
print("      decile   |R-Y|_off range          mean change   flip%")
for i in range(10):
    m = (a0 >= qs[i]) & (a0 < qs[i + 1]) if i < 9 else (a0 >= qs[i])
    if m.sum() == 0:
        continue
    ch = 100 * (np.abs(d1)[m].mean() - a0[m].mean()) / max(a0[m].mean(), 1e-12)
    print(f"       {i+1:2d}     {qs[i]:.5f}-{qs[i+1]:.5f}   {ch:+8.2f}%   {100*flip[m].mean():5.1f}%")
print("=" * 66)
