import tifffile, numpy as np
from pathlib import Path
for g in (r"C:\dev\strehl-out\GALLERY-FIXED-SRGB", r"C:\dev\strehl-out\SHIP-V1"):
    p = sorted(Path(g).glob("*.tiff"))[0]
    with tifffile.TiffFile(p) as tf:
        s = tf.series[0]
        pg = tf.pages[0]
        print(f"{Path(g).name:24s} {p.name:14s} shape={s.shape} dtype={s.dtype} "
              f"compression={pg.compression} photometric={pg.photometric}")
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"NOT uint16: {a.dtype}"
    print(f"{'':24s} uint16 OK  min={a.min()} max={a.max()} "
          f"ptp={np.ptp(a)} mean={a.mean():.1f}")
