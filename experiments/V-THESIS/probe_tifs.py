import sys, json, glob, os
import numpy as np, tifffile

R = r"C:\dev\strehl-out\BUILD-THESIS\renders"
subs = ["bee-3-cpl","bee-1-cpl","leaf-2-cpl","flowers-cpl","tweezers-cpl","flat-on-ruler-cpl"]
for s in subs:
    for a in ("merge","argmax"):
        p = os.path.join(R,s,a+".tif")
        with tifffile.TiffFile(p) as tf:
            pg = tf.pages[0]
            desc = pg.tags.get("ImageDescription")
            desc = desc.value if desc else None
            sw = pg.tags.get("Software")
            sw = sw.value if sw else None
            icc = "ICCProfile" in pg.tags
            arr = pg.asarray()
        g = arr[:,:,1].astype(np.float64)
        print(f"{s:20s} {a:7s} shape={arr.shape} dtype={arr.dtype} icc={icc}")
        print(f"    G min={g.min():.0f} max={g.max():.0f} mean={g.mean():.1f} med={np.median(g):.0f} p99={np.percentile(g,99):.0f}")
        print(f"    Software={sw!r}")
        if desc: print("    Desc=" + repr(desc)[:400])
