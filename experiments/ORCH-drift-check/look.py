import io, json, os, sys
import numpy as np
import tifffile
from PIL import Image

OUT = r"C:\dev\strehl-out\ORCH-look"
os.makedirs(OUT, exist_ok=True)
D = r"C:\dev\strehl-out\M86-align"

A = os.path.join(D, "bee-3-ALIGNED.tif")
U = os.path.join(D, "bee-3-UNALIGNED.tif")
Z = os.path.join(D, "bee3-zoomnull.tif")

def load(p):
    a = tifffile.imread(p)
    return a

for name, p in [("ALIGNED", A), ("UNALIGNED", U), ("ZOOMNULL", Z)]:
    a = load(p)
    print(name, a.shape, a.dtype, "min", int(a.min()), "max", int(a.max()),
          "mean", round(float(a.mean()), 1))

a = load(A).astype(np.float32)
u = load(U).astype(np.float32)

H, W = a.shape[0], a.shape[1]
print("dims", H, W)

# how much pure black is in each? M86 claimed 0.001% after fit_to_cover.
def blackfrac(x):
    lum = x.mean(axis=2) if x.ndim == 3 else x
    return float((lum <= 1.0).mean())

print("black frac ALIGNED  ", "%.6f%%" % (100 * blackfrac(a)))
print("black frac UNALIGNED", "%.6f%%" % (100 * blackfrac(u)))

def to8(x):
    # already sRGB-encoded per --srgb; just scale 16->8
    return np.clip(x / 257.0, 0, 255).astype(np.uint8)

# full-frame downsampled contact sheets so I can see composition + artefacts
for name, x in [("aligned", a), ("unaligned", u)]:
    im = Image.fromarray(to8(x))
    im.thumbnail((1400, 1400), Image.LANCZOS)
    im.save(os.path.join(OUT, "full-%s.png" % name))
    print("wrote full-%s.png" % name, im.size)

json.dump({"H": H, "W": W}, io.open(os.path.join(OUT, "dims.json"), "w"))
