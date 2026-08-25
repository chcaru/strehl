"""M97e -- price ORCH's PIL 16-bit hazard on my own reported metric.

election_crops.py has a SILENT FALLBACK:

    try: import tifffile
    except ImportError: tifffile = None
    ...
    a = tifffile.imread(p) if tifffile is not None else np.array(Image.open(p))

If tifffile were absent, every number I reported would have been computed on
8-bit data and NOTHING would have said so. That is precisely the defect class
ORCH described, sitting in my own file. So: do not reason about which branch
ran. Run both readers on the real files and print both numbers.

The metric at risk is `changed_pixel_fraction` -- the fraction of output pixels
whose value differs between the OFF and SOFT arms. It is a SMALL-SIGNAL metric,
which ORCH flags as most suspect: 8-bit quantisation puts a ~128-count floor (in
16-bit units) under every difference, so a genuine small change reads as a clean
null.

I reported trap 6.874% and plant 0.314% against in-process counters of 7.3723%
and 0.3431% -- a ~7% shortfall in BOTH arms that I attributed to frame swaps
that happen to produce the same value. Quantisation is an equally good
explanation for a shortfall in that direction, and I did not distinguish them.
This script distinguishes them.
"""

import numpy as np
from PIL import Image

try:
    import tifffile
    HAVE_TIFFFILE = True
except ImportError:
    tifffile = None
    HAVE_TIFFFILE = False

OUT = r"C:\dev\strehl-out\M97e"

PAIRS = [
    ("trap coffee-bean", rf"{OUT}\coffee-bean-off.tif",
     rf"{OUT}\coffee-bean-soft-paired.tif", 7.3723),
    ("plant foam", rf"{OUT}\foam-off100.tif",
     rf"{OUT}\foam-soft100-paired.tif", 0.3431),
]

print(f"tifffile importable: {HAVE_TIFFFILE}")
print()

probe = PAIRS[0][1]
pil = Image.open(probe)
print(f"probe file            : {probe}")
print(f"PIL mode              : {pil.mode}")
print(f"PIL array dtype       : {np.asarray(pil).dtype}")
if HAVE_TIFFFILE:
    tf = tifffile.imread(probe)
    print(f"tifffile dtype/shape  : {tf.dtype} {tf.shape}")
    print(f"tifffile min/max      : {tf.min()} {tf.max()}")
    print(f"distinct levels tiff  : {len(np.unique(tf[::8, ::8]))}")
print(f"distinct levels PIL   : {len(np.unique(np.asarray(pil)[::8, ::8]))}")
print()

hdr = f"{'pair':<20}{'reader':<10}{'dtype':<9}{'changed %':>11}{'maxdiff':>10}{'counter %':>11}{'ratio':>8}"
print(hdr)
print("-" * len(hdr))

for name, a_path, b_path, counter in PAIRS:
    for reader in ("tifffile", "PIL"):
        if reader == "tifffile":
            if not HAVE_TIFFFILE:
                continue
            a = tifffile.imread(a_path).astype(np.float64)
            b = tifffile.imread(b_path).astype(np.float64)
            dt = tifffile.imread(a_path).dtype
        else:
            a = np.asarray(Image.open(a_path)).astype(np.float64)
            b = np.asarray(Image.open(b_path)).astype(np.float64)
            dt = np.asarray(Image.open(a_path)).dtype
        d = np.abs(b - a)
        changed = float((d.max(axis=2) > 0).mean()) * 100.0
        print(f"{name:<20}{reader:<10}{str(dt):<9}{changed:>11.4f}"
              f"{d.max():>10.0f}{counter:>11.4f}{changed / counter:>8.3f}")
    print()
