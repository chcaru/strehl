"""Header/geometry inspection of the two head-to-head arms. Read-only."""
import numpy as np, tifffile, json, sys

PRIOR = r"C:\dev\macro\out\coffee-bean\stack.tif"
STREHL = r"C:\dev\strehl-out\SHIP-V2\coffee-bean--SHIP-V2.tiff"

for name, path in (("PRIOR ", PRIOR), ("STREHL", STREHL)):
    print("=" * 70)
    print(name, path)
    with tifffile.TiffFile(path) as tf:
        p = tf.pages[0]
        print("  pages      :", len(tf.pages))
        print("  shape      :", p.shape, "dtype", p.dtype)
        print("  photometric:", p.photometric, " planarconfig:", p.planarconfig)
        print("  compression:", p.compression)
        print("  bits       :", p.bitspersample, " sampleformat:", p.sampleformat)
        print("  tilewidth  :", p.tilewidth, " rowsperstrip:", getattr(p, "rowsperstrip", None))
        for tag in p.tags:
            v = tag.value
            if isinstance(v, bytes):
                v = v[:400]
            s = str(v)
            if len(s) > 600:
                s = s[:600] + " ...[trunc]"
            print(f"    tag {tag.code:>6} {tag.name:<24} = {s}")
