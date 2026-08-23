import rawpy, numpy as np, glob, os
from scipy.ndimage import sobel, uniform_filter
BLACK, CONT = 512, 16383
R = 2   # M21: fine scale; the shipped R=13 window destroys fine structure

d  = r"D:\personal\macro\coffee-bubbles"
fs = sorted(glob.glob(os.path.join(d, "*.ARW")))
ys, xs = slice(0,4688,2), slice(1,7028,2)

nclip = None; ssum = None; fmax = None; fmin = None
for i, f in enumerate(fs):
    with rawpy.imread(f) as r:
        v = r.raw_image_visible[ys, xs].astype(np.float32)
    if nclip is None:
        nclip = np.zeros(v.shape, np.uint8); ssum = np.zeros(v.shape, np.float64)
    nclip += (v >= CONT); ssum += v
    gx = sobel(v, axis=1, mode='nearest'); gy = sobel(v, axis=0, mode='nearest')
    fm = uniform_filter(np.hypot(gx, gy), size=2*R+1, mode='nearest')
    fmax = fm if fmax is None else np.maximum(fmax, fm)
    fmin = fm if fmin is None else np.minimum(fmin, fm)
n = len(fs); mean = (ssum/n).astype(np.float32)

# discipline 29's quantity: contrast of the focus peak across the stack
contrast = (fmax - fmin) / np.maximum(fmax, 1e-6)

never = nclip == 0
some  = (nclip > 0) & (nclip < n)
always= nclip == n
print(f"frames={n}   never-clipped={int(never.sum()):,}  sometimes={int(some.sum()):,}  always={int(always.sum()):,}")
print()
print("cross-frame focus contrast (discipline 29's confidence quantity)")
print(f"{'group':<34}{'n':>12}{'median':>10}{'mean':>10}")
for nm, m in (("never clipped", never), ("SOMETIMES clipped", some), ("always clipped", always)):
    if m.sum() < 20: 
        print(f"{nm:<34}{int(m.sum()):>12,}{'--':>10}{'--':>10}"); continue
    print(f"{nm:<34}{int(m.sum()):>12,}{float(np.median(contrast[m])):>10.4f}{float(contrast[m].mean()):>10.4f}")

print()
print("MATCHED control: both groups restricted to the same mean-level bin,")
print("so brightness cannot explain a difference.")
print(f"{'bin (mean DN)':>20}{'never n':>10}{'never med':>11}{'some n':>9}{'some med':>10}{'ratio':>8}")
for lo,hi in [(8000,12000),(12000,14000),(14000,15360),(15360,16383)]:
    b = (mean>=lo)&(mean<hi)
    a, c = never&b, some&b
    if a.sum()<50 or c.sum()<50:
        print(f"{f'[{lo},{hi})':>20}{int(a.sum()):>10,}{'--':>11}{int(c.sum()):>9,}{'--':>10}{'--':>8}"); continue
    ma, mc = float(np.median(contrast[a])), float(np.median(contrast[c]))
    print(f"{f'[{lo},{hi})':>20}{int(a.sum()):>10,}{ma:>11.4f}{int(c.sum()):>9,}{mc:>10.4f}{mc/ma:>8.3f}")
