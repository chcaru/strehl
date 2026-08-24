import numpy as np, pathlib
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
S = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")
b = np.asarray(Image.open(S/"30-SHIP-BEFORE-default.tif"))
print("dtype", b.dtype, "shape", b.shape, "min", b.min(), "max", b.max(), "mean", b.mean())
g = b[:,:,1].astype(np.float32)
print("green: p1 %.0f p50 %.0f p99 %.0f" % tuple(np.percentile(g,[1,50,99])))
# thumbnail to locate content
th = g[::16,::16]
print("thumb min/max/mean", th.min(), th.max(), th.mean())
Image.fromarray((th/max(th.max(),1)*255).astype(np.uint8)).save(S/"38-THUMB-before.png")
d = np.load("cache/ship-delta.npy").astype(np.float32)
dt = d[::16,::16]
ys,xs = np.nonzero(dt > np.percentile(dt,99.9))
print("top-delta thumb rows", ys.min()*16, ys.max()*16, "cols", xs.min()*16, xs.max()*16)
# brightest-gradient window search on a coarse grid for a fine-detail control
print("global mean level of green:", g.mean())
