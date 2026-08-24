"""M87 / 62 -- what is actually in bee3-full.tif, the image the owner judged.

Pure inspection, no claims. Establishes dimensions, dtype, dynamic range and
polarity before any halo statistic is registered against it.
"""
import json
import os
import sys

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\M87-bee"
os.makedirs(OUT, exist_ok=True)

CANDIDATES = [
    r"C:\dev\strehl-out\bee3-full.tif",
    r"C:\dev\strehl-out\bee3-g0.tif",
    r"C:\dev\strehl-out\bee3-g1.tif",
    r"C:\dev\strehl-out\M86-align\bee-3-ALIGNED.tif",
    r"C:\dev\strehl-out\M86-align\bee3-zoomnull.tif",
    r"C:\dev\strehl-out\ORCH-gallery\bee-3-cpl-exposed.tif",
    r"C:\dev\strehl-out\ORCH-gallery\bee-3-cpl-srgb.tif",
]

rep = {}
for p in CANDIDATES:
    if not os.path.exists(p):
        rep[p] = {"exists": False}
        continue
    with tifffile.TiffFile(p) as tf:
        pages = len(tf.pages)
        a = tf.asarray()
    f = a.astype(np.float64)
    ent = {
        "exists": True,
        "shape": list(a.shape),
        "dtype": str(a.dtype),
        "pages": pages,
        "megapixels": round(a.shape[0] * a.shape[1] / 1e6, 4),
        "min": float(f.min()),
        "max": float(f.max()),
        "mean": float(f.mean()),
        "p01": float(np.percentile(f, 1)),
        "p50": float(np.percentile(f, 50)),
        "p99": float(np.percentile(f, 99)),
        "p999": float(np.percentile(f, 99.9)),
    }
    if a.ndim == 3:
        ent["clipped_pct_per_chan"] = [
            round(float((a[..., c] >= np.iinfo(a.dtype).max).mean() * 100), 6)
            for c in range(a.shape[2])
        ]
        ent["chan_means"] = [round(float(f[..., c].mean()), 2) for c in range(a.shape[2])]
    rep[p] = ent
    print(f"{os.path.basename(p):32s} {str(a.shape):22s} {a.dtype}  "
          f"MP={ent['megapixels']:.3f}  p50={ent['p50']:.1f}  p999={ent['p999']:.1f}")
    sys.stdout.flush()

with open(os.path.join(OUT, "62-probe.json"), "w", encoding="utf-8") as fh:
    json.dump(rep, fh, indent=1)
print("\nwrote", os.path.join(OUT, "62-probe.json"))
