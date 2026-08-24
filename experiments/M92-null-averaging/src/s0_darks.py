import glob
import os

import exifread

root = r"D:\macro-dark-frames"
for d in sorted(os.listdir(root)):
    p = os.path.join(root, d)
    if not os.path.isdir(p):
        continue
    fs = sorted(glob.glob(os.path.join(p, "*.ARW")))
    if not fs:
        continue
    with open(fs[0], "rb") as fh:
        t = exifread.process_file(fh, details=False, stop_tag="ISOSpeedRatings")
    iso = t.get("EXIF ISOSpeedRatings")
    exp = t.get("EXIF ExposureTime")
    print(f"{d:16s} n={len(fs):4d} ISO={iso} exp={exp}")
