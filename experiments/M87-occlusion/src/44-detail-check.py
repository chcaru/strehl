import numpy as np, pathlib
from PIL import Image
S = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")
for n in ("32-SHIP-BEFORE-leg.png","35-SHIP-BEFORE-detail.png"):
    g = np.asarray(Image.open(S/n)).astype(np.float32)[:,:,1]
    gy, gx = np.gradient(g)
    m = np.hypot(gx,gy)
    print(f"{n:34s} mean|grad| {m.mean():7.3f}  p99 {np.percentile(m,99):7.2f}  "
          f"sd {g.std():7.2f}  mean level {g.mean():6.1f}")
