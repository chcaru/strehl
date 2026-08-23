"""M33 step 1: build a DENSE focus volume -- all 105 frames of coffee-bean.

M32's cube used every second frame, which is the operational sampling. This one
keeps all of them, so the x2 decimation that produced M32's stack can be scored
against a focus axis sampled twice as finely. The dense grid is the only ground
truth available for a sub-frame quantity without a rail, and it is honest ground
truth only for questions about the x2 grid -- it is itself sampled, and says
nothing about structure finer than its own step.
"""
import rawpy, numpy as np, glob, os, time, json
from scipy.ndimage import sobel, uniform_filter

OUT = os.path.join(os.path.dirname(__file__), "..", "out")
CACHE = os.path.join(OUT, "cache")
SRC = r"C:\dev\macro\test\coffee-bean"
BLACK, R = 512, 2
CY, CX, H = 1172, 1757, 512

files = sorted(glob.glob(os.path.join(SRC, "*.ARW")))
n = len(files)
ys, xs = slice(0, 4688, 2), slice(1, 7028, 2)

t0 = time.time()
vol = np.empty((n, 2 * H, 2 * H), np.float32)
for i, f in enumerate(files):
    with rawpy.imread(f) as r:
        v = r.raw_image_visible[ys, xs][CY - H:CY + H, CX - H:CX + H].astype(np.float32) - BLACK
    gx = sobel(v, axis=1, mode="nearest")
    gy = sobel(v, axis=0, mode="nearest")
    vol[i] = uniform_filter(np.hypot(gx, gy), size=2 * R + 1, mode="nearest")
print(f"dense focus volume {vol.shape}  {vol.nbytes/1e6:.0f} MB  in {time.time()-t0:.0f}s")
np.save(os.path.join(CACHE, "dense_focus.npy"), vol)

am = vol.argmax(0)
with open(os.path.join(OUT, "01-dense.json"), "w") as fh:
    json.dump(dict(n_frames=n, crop=[2 * H, 2 * H], box_radius=R,
                   argmax_p05=int(np.percentile(am, 5)),
                   argmax_median=int(np.median(am)),
                   argmax_p95=int(np.percentile(am, 95)),
                   frames_holding_1pct=int((np.bincount(am.ravel(), minlength=n)
                                            > 0.01 * am.size).sum())), fh, indent=2)
print(open(os.path.join(OUT, "01-dense.json")).read())
