"""Does a rendered master RECORD which env-var-controlled merge mode produced it?

Motivation: STREHL_HULL (new, uncommitted, V-SPEED) joins STREHL_GATE_FLOOR_SCALE
and STREHL_PYRAMID_WEIGHT_DUMP as ambient switches that change merge behaviour.
CLI flags land in the TIFF ImageDescription. If env vars do NOT, then two masters
with byte-identical provenance strings can have been rendered under different
merge maths, and no downstream lane can tell them apart.
"""
import glob, os, sys, tifffile

ENVS = ["STREHL_HULL", "STREHL_GATE_FLOOR_SCALE", "STREHL_PYRAMID_WEIGHT_DUMP",
        "STREHL_MEAN_COARSE", "STREHL_"]

roots = [r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful",
         r"C:\dev\strehl-out\acceptance\SHIP-V3"]
shown = 0
for root in roots:
    if not os.path.isdir(root):
        print(f"MISSING {root}")
        continue
    tifs = sorted(glob.glob(os.path.join(root, "*.tif*")))
    print(f"\n=== {root}  ({len(tifs)} tif) ===")
    for t in tifs[:2]:
        with tifffile.TiffFile(t) as tf:
            d = tf.pages[0].tags.get("ImageDescription")
            desc = d.value if d is not None else ""
        print(f"\n--- {os.path.basename(t)}  desc={len(desc)} chars ---")
        print(desc[:1400])
        for e in ENVS:
            print(f"  contains {e!r}: {e in desc}")
        shown += 1
if shown == 0:
    sys.exit("no masters found")
