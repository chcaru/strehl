"""Parent-vs-child isolation of 57e4554, any subject. Byte-frozen linear output."""
import sys
import numpy as np, tifffile
from pathlib import Path
from scipy.ndimage import uniform_filter

OUT = Path(r"C:\dev\strehl-out\V-softness")
SUBJ = sys.argv[1] if len(sys.argv) > 1 else "bee-1-cpl"
PARENT, CHILD = "526c727", "57e4554"

def load(sha):
    a = tifffile.imread(OUT / f"{SUBJ}-{sha}.tif")
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    return a.astype(np.float64).mean(2)

def gradmag2(y):
    gx = np.zeros_like(y); gy = np.zeros_like(y)
    gx[:, :-1] = np.diff(y, axis=1); gy[:-1, :] = np.diff(y, axis=0)
    return gx*gx + gy*gy

def sdmap(y):
    m = uniform_filter(y, 7)
    return np.sqrt(np.maximum(uniform_filter(y*y, 7) - m*m, 0))

print(f"=== {SUBJ}: {PARENT} (shrink ON) -> {CHILD} (shrink DELETED) ===")
yp, yc = load(PARENT), load(CHILD)
d = np.abs(yc - yp)
print(f"pixels changed {100.0*(d>0).mean():.2f}%  mean|d| {d.mean():.1f}  max|d| {d.max():.0f}")

lv = sdmap(yp)**2
qs = np.quantile(lv, np.linspace(0, 1, 6)); qs[0] -= 1; qs[-1] += 1
gp, gc = gradmag2(yp), gradmag2(yc)
sp, sc = sdmap(yp), sdmap(yc)

print("\n bin      gradRMS   noise-sd   (child/parent)")
print(" " + "-"*46)
for i in range(5):
    sel = (lv >= qs[i]) & (lv < qs[i+1])
    tag = "flattest" if i == 0 else ("MOST DETAILED" if i == 4 else "")
    print(f"  {i}     {np.sqrt(gc[sel].mean()/gp[sel].mean()):7.4f}    {sc[sel].mean()/sp[sel].mean():7.4f}   {tag}")

print(f"\nwhole-image gradient RMS ratio : {np.sqrt(gc.mean()/gp.mean()):.4f}")
for q in (0.02, 0.05, 0.10, 0.20):
    bg = lv <= np.quantile(lv, q)
    print(f"background noise sd ratio, flattest {int(q*100):3d}% : "
          f"{sc[bg].mean()/sp[bg].mean():.4f}   (parent {sp[bg].mean():.2f} -> child {sc[bg].mean():.2f})")
print("\nThe commit claimed DELETING the shrink LOWERS background noise")
print("(bee-2-cpl flat patches: 0.878 / 1.005 / 0.996). Ratio >= 1 refutes that here.")
