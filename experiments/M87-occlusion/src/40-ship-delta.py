import numpy as np, pathlib, json
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
S = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")
b = np.asarray(Image.open(S/"30-SHIP-BEFORE-default.tif")).astype(np.int32)
a = np.asarray(Image.open(S/"31-SHIP-AFTER-fixhalo.tif")).astype(np.int32)
print("shapes", b.shape, a.shape)
d = np.abs(a-b).max(axis=2)
n = d.size
ch = int((d>0).sum())
print(f"pixels changed : {ch} / {n} = {100.0*ch/n:.3f}%")
print(f"max |delta|    : {d.max()} of 65535")
ys, xs = np.nonzero(d>0)
if ch:
    print(f"changed bbox   : y {ys.min()}..{ys.max()}  x {xs.min()}..{xs.max()}")
np.save("cache/ship-delta.npy", d.astype(np.uint16))
json.dump({"changed_px": ch, "total_px": int(n), "frac": ch/n, "max_delta": int(d.max())},
          open("data/41-ship-delta.json","w"), indent=1)
