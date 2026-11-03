"""List runs of consecutive RAW files sharing one ISO (EXIF read via tifffile)."""
import glob
import os
import sys
import tifffile

fs = sorted(glob.glob(os.path.join(sys.argv[1], "*.ARW")))
groups, prev, start = [], None, 0
for i, f in enumerate(fs):
    with tifffile.TiffFile(f) as t:
        ex = t.pages[0].tags.get("ExifTag")
        iso = ex.value.get("ISOSpeedRatings") if ex else None
    if iso != prev:
        if prev is not None:
            groups.append((prev, start, i - 1))
        prev, start = iso, i
groups.append((prev, start, len(fs) - 1))
for iso, a, b in groups:
    print(iso, os.path.basename(fs[a]), os.path.basename(fs[b]), b - a + 1)
