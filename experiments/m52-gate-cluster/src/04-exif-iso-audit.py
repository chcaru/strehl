import collections
import pathlib

import exifread

for name in ["119MSDCF", "109MSDCF", "113MSDCF", "112MSDCF", "coffee-bean"]:
    d = pathlib.Path(r"D:\personal\macro") / name
    isos, exps, models = collections.Counter(), collections.Counter(), collections.Counter()
    for p in sorted(d.glob("*.ARW")):
        with open(p, "rb") as f:
            t = exifread.process_file(f, details=False, stop_tag="EXIF ExposureTime")
        isos[str(t.get("EXIF ISOSpeedRatings"))] += 1
        exps[str(t.get("EXIF ExposureTime"))] += 1
        models[str(t.get("Image Model"))] += 1
    print(name, "ISO", dict(isos), "model", dict(models))
    print(" " * len(name), "exposure", dict(exps))
