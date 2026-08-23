import numpy as np, os, time
from scipy.ndimage import sobel, uniform_filter
ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
raw = np.asarray(np.load(os.path.join(ROOT,"m32-posterior","out","cache","raw.npy"), mmap_mode="r"), np.float32)
t0=time.time()
foc = np.empty_like(raw)
for i in range(raw.shape[0]):
    gx = sobel(raw[i], axis=1, mode="nearest"); gy = sobel(raw[i], axis=0, mode="nearest")
    foc[i] = uniform_filter(np.hypot(gx,gy), size=5, mode="nearest")
print("focus rebuild", time.time()-t0, "s")
t0=time.time()
fmax = foc.max(0)
tail = np.concatenate([foc[:6], foc[-6:]],0)
d2 = tail[2:]-2*tail[1:-1]+tail[:-2]
sf = np.sqrt(np.maximum(d2.var(0),1e-12)/6.0).astype(np.float32)
d = (fmax[None]-foc)/np.maximum(sf,1e-6)[None]
lp = -0.5*d.astype(np.float64)**2
lp -= lp.max(0); p = np.exp(lp); p/=p.sum(0)
c2 = np.exp(-(p*np.log(np.maximum(p,1e-300))).sum(0)).astype(np.float32)
print("C2", time.time()-t0, "s")
