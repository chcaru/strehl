import rawpy, numpy as np, glob, os
from scipy.ndimage import sobel, uniform_filter
CONT = 16383; R = 2
d  = r"D:\personal\macro\coffee-bubbles"
fs = sorted(glob.glob(os.path.join(d, "*.ARW")))
ys, xs = slice(0,4688,2), slice(1,7028,2)
nclip=None; fmax=None; fmin=None
for f in fs:
    with rawpy.imread(f) as r:
        v = r.raw_image_visible[ys, xs].astype(np.float32)
    if nclip is None: nclip = np.zeros(v.shape, np.uint8)
    nclip += (v>=CONT)
    fm = uniform_filter(np.hypot(sobel(v,axis=1,mode='nearest'), sobel(v,axis=0,mode='nearest')),
                        size=2*R+1, mode='nearest')
    fmax = fm if fmax is None else np.maximum(fmax,fm)
    fmin = fm if fmin is None else np.minimum(fmin,fm)
n=len(fs)
always = nclip==n; never = nclip==0
print("MECHANISM: contrast = (fmax-fmin)/fmax reaches 1.0 only when fmin -> 0.")
for nm,m in (("always clipped",always),("never clipped",never)):
    print(f"  {nm:<16} n={int(m.sum()):>10,}  median fmin={float(np.median(fmin[m])):>10.3f}"
          f"  median fmax={float(np.median(fmax[m])):>10.1f}")
print()
print(f"  fraction of always-clipped pixels with fmin exactly 0.0 : "
      f"{float((fmin[always]==0).mean()):.3f}")
print(f"  fraction of never-clipped  pixels with fmin exactly 0.0 : "
      f"{float((fmin[never]==0).mean()):.6f}")
print()
print("So: in at least one frame the pixel sits INSIDE a uniformly-clipped blob")
print("(gradient identically 0), and in another the blob's edge crosses it")
print("(gradient large). The ratio is then 1.0 -- the metric's maximum -- at a")
print("pixel whose radiometric value is pinned and carries no information.")
