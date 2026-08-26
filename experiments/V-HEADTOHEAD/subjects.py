"""Identify candidate SECOND SUBJECTS by rendering tiny previews.  Region/strided
reads only -- these are 375 MB files."""
import numpy as np, tifffile, os
from PIL import Image
OUT = r"C:\dev\strehl-out\V-HEADTOHEAD\subjects"
os.makedirs(OUT, exist_ok=True)
CAND = [r"C:\dev\macro\out\stack_v3.tif",
        r"C:\dev\macro\out\stack_test2_rec2020.tif"]
for n in ("109MSDCF", "112MSDCF", "113MSDCF", "119MSDCF", "dry-erase-marker-head-cpl",
          "wrapped-text-1", "flat-on-ruler-cpl"):
    CAND.append(rf"C:\dev\strehl-out\SHIP-V2\{n}--SHIP-V2.tiff")
for p in CAND:
    if not os.path.exists(p):
        print("missing", p); continue
    try:
        with tifffile.TiffFile(p) as tf:
            pg = tf.pages[0]
            a = pg.asarray()[::16, ::16]
    except Exception as ex:
        print("FAIL", p, ex); continue
    a = np.asarray(a, np.float32)
    if a.ndim == 2: a = np.dstack([a]*3)
    a = a[:, :, :3]
    lo, hi = np.percentile(a, 0.5), np.percentile(a, 99.5)
    v = np.clip((a - lo)/(hi - lo + 1e-9), 0, 1)
    if a.max() > 1.5:        # uint16 display-encoded already
        v = np.clip(a/65535.0, 0, 1)
    else:
        v = v ** (1/2.2)
    name = os.path.splitext(os.path.basename(p))[0] + "_v.png"
    Image.fromarray((v*255).astype(np.uint8)).save(os.path.join(OUT, name))
    print(f"{os.path.basename(p):<45} {pg.shape} {pg.dtype} -> {name}")
