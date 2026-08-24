import os
import numpy as np
import tifffile
from PIL import Image

OUT = r"C:\dev\strehl-out\ORCH-look"
D = r"C:\dev\strehl-out\M86-align"

a = tifffile.imread(os.path.join(D, "bee-3-ALIGNED.tif"))
z = tifffile.imread(os.path.join(D, "bee3-zoomnull.tif"))

# FOV- and resampler-matched pair. Any visible difference here is registration
# and nothing else. The UNALIGNED render is NOT usable for a visual comparison
# because fit_to_cover gives it a ~7% larger field of view, so at a matched
# output size it renders smaller -- which reads as "softer" for reasons that
# have nothing to do with alignment. I fell for exactly that a moment ago.
for name, x in [("aligned", a), ("zoomnull", z)]:
    im = Image.fromarray(np.clip(x / 257.0, 0, 255).astype(np.uint8))
    im.thumbnail((1400, 1400), Image.LANCZOS)
    im.save(os.path.join(OUT, "fair-%s.png" % name))

# Difference image, amplified, to show WHERE registration changed the render.
d = np.abs(a.astype(np.float32) - z.astype(np.float32)).mean(axis=2)
print("mean abs diff (16-bit DN): %.1f" % d.mean())
print("frac pixels differing >1 DN: %.4f%%" % (100 * (d > 257).mean()))
p99 = float(np.percentile(d, 99))
print("p99 abs diff: %.1f DN" % p99)
dv = np.clip(d / max(p99, 1.0) * 255.0, 0, 255).astype(np.uint8)
im = Image.fromarray(dv)
im.thumbnail((1400, 1400), Image.LANCZOS)
im.save(os.path.join(OUT, "fair-diff.png"))
print("wrote fair-aligned.png / fair-zoomnull.png / fair-diff.png")
