import numpy as np, os, inspect
from scipy.ndimage import sobel, uniform_filter
import scipy.ndimage as ndi
print(inspect.getsource(ndi.sobel))
ROOT = r"C:\dev\blog\death-of-software\projects\strehl\experiments"
raw = np.asarray(np.load(os.path.join(ROOT,"m32-posterior","out","cache","raw.npy"), mmap_mode="r"), np.float32)[:9]
R=2
def focus3d(cube):
    gx = sobel(cube, axis=2, mode="nearest"); gy = sobel(cube, axis=1, mode="nearest")
    return uniform_filter(np.hypot(gx,gy), size=(1,2*R+1,2*R+1), mode="nearest")
def focus2d(v):
    gx = sobel(v, axis=1, mode="nearest"); gy = sobel(v, axis=0, mode="nearest")
    return uniform_filter(np.hypot(gx,gy), size=2*R+1, mode="nearest")
f3 = focus3d(raw)
f2 = np.stack([focus2d(raw[i]) for i in range(raw.shape[0])])
print("focus3d[4] / focus2d[4] : median ratio", float(np.median(f3[4]/np.maximum(f2[4],1e-9))))
print("max abs diff f3 vs 4*f2:", float(np.abs(f3[4]-4*f2[4]).max()), " median |.|", float(np.median(np.abs(f3[4]-4*f2[4]))))
# is f3 frame-smoothed?  compare f3[4] against 4*(f2[3]+2*f2[4]+f2[5])/4
blend = (f2[3]+2*f2[4]+f2[5])
print("median |f3[4]-blend|/blend:", float(np.median(np.abs(f3[4]-blend)/np.maximum(blend,1e-9))))
print("median |f3[4]-4*f2[4]|/(4*f2[4]):", float(np.median(np.abs(f3[4]-4*f2[4])/np.maximum(4*f2[4],1e-9))))
