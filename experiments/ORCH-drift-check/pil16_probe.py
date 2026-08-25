"""Does PIL silently downconvert 16-bit RGB TIFFs?

Controlled test on a file whose contents we choose, so the answer cannot be a
property of somebody else's export. Also tests 16-bit GREYSCALE, because the two
paths differ in PIL and the corpus uses both.

If this holds, every measurement in the corpus that read a 16-bit TIFF through
PIL was working on 8 bits and lost a factor of 256 in level resolution, with no
warning printed anywhere.
"""
import os
import tempfile

import numpy as np
import tifffile
from PIL import Image

tmp = tempfile.mkdtemp(prefix="tifprobe-")
rng = np.random.default_rng(7)

# A ramp with 1-LSB steps: survives 16-bit exactly, collapses under 8-bit.
H = W = 64
base = np.arange(H * W, dtype=np.uint16).reshape(H, W) % 4096 + 30000

cases = {
    "rgb16": np.stack([base, base + 1, base + 2], axis=2).astype(np.uint16),
    "grey16": base.astype(np.uint16),
}

print("%-8s %-22s %-10s %-10s %10s %10s" % ("case", "reader", "dtype", "shape", "min", "max"))
verdict = {}
for name, arr in cases.items():
    p = os.path.join(tmp, name + ".tif")
    tifffile.imwrite(p, arr)

    rt = tifffile.imread(p)
    print("%-8s %-22s %-10s %-10s %10d %10d" % (name, "tifffile", rt.dtype, str(rt.shape), rt.min(), rt.max()))

    im = Image.open(p)
    rp = np.asarray(im)
    print("%-8s %-22s %-10s %-10s %10d %10d" % ("", "PIL (mode=%s)" % im.mode, rp.dtype, str(rp.shape), rp.min(), rp.max()))

    exact = rt.dtype == arr.dtype and np.array_equal(rt, arr)
    pil_exact = rp.dtype == arr.dtype and rp.shape == arr.shape and np.array_equal(rp, arr)
    verdict[name] = (exact, pil_exact, rp.dtype, im.mode)
    print("%-8s %-22s tifffile exact=%s   PIL exact=%s" % ("", "", exact, pil_exact))

    # How many distinct levels survive each reader?
    print("%-8s %-22s distinct levels: source=%d tifffile=%d PIL=%d"
          % ("", "", len(np.unique(arr)), len(np.unique(rt)), len(np.unique(rp))))
    print()

print("=" * 78)
for name, (ex, pex, dt, mode) in verdict.items():
    if ex and not pex:
        print("CONFIRMED  %-7s PIL returns %s (mode %s) where the file holds uint16." % (name, dt, mode))
    elif ex and pex:
        print("REFUTED    %-7s PIL round-trips uint16 exactly. No hazard for this case." % name)
    else:
        print("INCONCLUSIVE %-5s tifffile did not round-trip either; the probe is broken." % name)
print("=" * 78)
print("temp dir:", tmp)
