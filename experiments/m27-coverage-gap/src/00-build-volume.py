"""M27 step 0: build a dense focus volume from coffee-bean (105 frames)."""
import rawpy, numpy as np, glob, os, time
from scipy.ndimage import sobel, uniform_filter

R = 2
SESS = r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files"
d = r"C:\dev\macro\test\coffee-bean"
fs = sorted(glob.glob(os.path.join(d, "*.ARW")))[::2]   # every 2nd of 105 -- still dense
ys, xs = slice(0, 4688, 2), slice(1, 7028, 2)
CY, CX, H = 1172, 1757, 750                             # centred 1500x1500 crop of the G plane

t0 = time.time()
vol = []
for f in fs:
    with rawpy.imread(f) as r:
        v = r.raw_image_visible[ys, xs][CY - H:CY + H, CX - H:CX + H].astype(np.float32)
    gx = sobel(v, axis=1, mode="nearest")
    gy = sobel(v, axis=0, mode="nearest")
    vol.append(uniform_filter(np.hypot(gx, gy), size=2 * R + 1, mode="nearest"))
vol = np.stack(vol)
n = vol.shape[0]
print(f"focus volume {vol.shape}  {vol.nbytes/1e6:.0f} MB  decoded in {time.time()-t0:.0f}s")
np.save(os.path.join(SESS, "cb_vol.npy"), vol)

am = vol.argmax(0)
h = np.bincount(am.ravel(), minlength=n)
print("argmax histogram over frames (thousands of pixels):")
print("  " + " ".join(f"{c/1000:.0f}" for c in h))
print(f"frames holding >1% of pixels as argmax: {int((h > 0.01*am.size).sum())} of {n}")
