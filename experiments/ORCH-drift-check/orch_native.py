"""Same two crops at NATIVE display scaling. The stretch found the dust; only the
unstretched view can say whether it matters for print. A defect visible only under a
33x linear stretch is a curiosity; one visible at 1:1 is a product failure."""
import numpy as np, tifffile
from PIL import Image

JOBS = [(r"C:\dev\strehl-out\SHIP-V2\coffee-bean--SHIP-V2.tiff", 6000, 900),
        (r"C:\dev\strehl-out\SHIP-V2\flower-bud-alone-cpl--SHIP-V2.tiff", 900, 2400)]
C = 900
for path, x0, y0 in JOBS:
    a = tifffile.imread(path)[y0:y0+C, x0:x0+C, :3]
    v = (a.astype(np.uint32) >> 8).astype(np.uint8)
    name = path.split("\\")[-1].replace(".tiff", f"--native-{x0}x{y0}.png")
    Image.fromarray(v).save(r"C:\dev\strehl-out\ORCH-SMOOTH\\" + name)
    lo, hi = int(a.min()), int(a.max())
    print(f"{name}  range {lo}..{hi} of 65535  ({(hi-lo)/65535*100:.2f}% span)  "
          f"8-bit span {(hi>>8)-(lo>>8)} levels")
