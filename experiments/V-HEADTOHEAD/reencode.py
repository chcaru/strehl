"""Re-encode the uint8 previews as real PNGs.
NOTE: PIL is used ONLY on uint8 arrays produced in numpy. AGENTS rule about PIL
applies to 16-bit reads; nothing 16-bit passes through PIL here."""
import numpy as np, tifffile, os
from PIL import Image
OUT = r"C:\dev\strehl-out\V-HEADTOHEAD"
for n in ("preview_prior", "preview_prior_clipmap", "preview_strehl"):
    a = tifffile.imread(os.path.join(OUT, n + ".png"))
    assert a.dtype == np.uint8, a.dtype
    Image.fromarray(a).save(os.path.join(OUT, n + "_v.png"))
    print(n, a.shape, a.dtype, "->", n + "_v.png")
