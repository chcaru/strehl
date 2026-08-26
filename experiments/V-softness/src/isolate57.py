"""Parent-vs-child isolation of 57e4554 on bee-1-cpl.

Measured on the BYTE-FROZEN default output (binned, linear, camera-native),
which is the file this project's corpus is measured on -- not on an --srgb
render, which the CLI help and every RUN.txt forbid measuring.

Reports BOTH sides of the trade the commit claimed:
  detail-bin gradient energy  (what BUILD-RENDER says was lost)
  flat-bin noise sd           (what the commit says was bought)
"""
import sys
import numpy as np
import tifffile
from pathlib import Path
from scipy.ndimage import uniform_filter

OUT = Path(r"C:\dev\strehl-out\V-softness")
PARENT, CHILD = "526c727", "57e4554"

def load(sha):
    a = tifffile.imread(OUT / f"bee-1-cpl-{sha}.tif")
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    print(f"  {sha}: shape={a.shape} dtype={a.dtype} min={a.min()} max={a.max()}")
    return a.astype(np.float64).mean(2)

def gradmag2(y):
    gx = np.zeros_like(y); gy = np.zeros_like(y)
    gx[:, :-1] = np.diff(y, axis=1); gy[:-1, :] = np.diff(y, axis=0)
    return gx*gx + gy*gy

print("loading byte-frozen linear renders:")
yp, yc = load(PARENT), load(CHILD)
assert yp.shape == yc.shape, "shape mismatch"

ident = np.array_equal(yp, yc)
print(f"\nrenders byte-identical: {ident}")
if ident:
    print("  !! the commit changed NOTHING on this subject -- inert on bee-1-cpl")
    sys.exit(0)

d = np.abs(yc - yp)
print(f"  pixels changed: {100.0*(d>0).mean():.3f}%   mean|d| {d.mean():.2f}   max|d| {d.max():.0f}")

# partition on the PARENT only, so the treatment cannot move the bins
m = uniform_filter(yp, 7)
lv = uniform_filter(yp*yp, 7) - m*m
qs = np.quantile(lv, np.linspace(0, 1, 6)); qs[0] -= 1; qs[-1] += 1
gp, gc = gradmag2(yp), gradmag2(yc)

print("\n  bin        n_px    gradRMS ratio   noise-sd ratio   (child/parent)")
print("  " + "-"*62)
for i in range(5):
    sel = (lv >= qs[i]) & (lv < qs[i+1])
    gr = np.sqrt(gc[sel].mean()/gp[sel].mean())
    sp = np.sqrt(np.maximum(uniform_filter(yp*yp,7)-m*m, 0))[sel].mean()
    mc = uniform_filter(yc, 7)
    sc = np.sqrt(np.maximum(uniform_filter(yc*yc,7)-mc*mc, 0))[sel].mean()
    tag = "flattest" if i == 0 else ("MOST DETAILED" if i == 4 else "")
    print(f"  {i}  {int(sel.sum()):10d}       {gr:8.4f}         {sc/sp:8.4f}   {tag}")

whole = np.sqrt(gc.mean()/gp.mean())
print(f"\n  whole-image gradient RMS ratio (child/parent): {whole:.4f}")
print(f"  BUILD-RENDER claims 0.9342 for this commit on couch-fibers-cpl.")

# flattest 2% = the background the commit measured
thr = np.quantile(lv, 0.02)
bg = lv <= thr
mp2 = uniform_filter(yp,7); mc2 = uniform_filter(yc,7)
sdp = np.sqrt(np.maximum(uniform_filter(yp*yp,7)-mp2*mp2,0))[bg].mean()
sdc = np.sqrt(np.maximum(uniform_filter(yc*yc,7)-mc2*mc2,0))[bg].mean()
print(f"\n  background (flattest 2%) noise sd: parent {sdp:.3f} -> child {sdc:.3f}"
      f"  ratio {sdc/sdp:.4f}")
print("  commit 57e4554 claimed deleting the shrink gives 0.878-1.005 background sd")
print("  on bee-2-cpl flat patches. Ratio < 1 here CONFIRMS the commit bought noise.")
