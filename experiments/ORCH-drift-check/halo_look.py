"""Render flower-bud-alone-cpl with the M87 halo correction ON, and put it
beside the OFF render gallery2 already produced.

M87's module header says the correction cuts the halo metric 79.8% while
raising RMSE against truth 254.6%, and 558.4% on a region with no occluding
edge at all -- it fires on silhouettes, not occlusions. That is a strong
argument for leaving it off, and it is an argument about a NUMBER. The owner
judges pictures. Before I carry M87's verdict to him I want to see what the
two images actually look like, because "measurably more wrong" and "looks
worse" are different claims and only the first one has been measured.

Emits matched crops at the silhouette, chosen on the OFF render and applied
to BOTH at identical coordinates -- picking the crop on either image
separately would be choosing where to look.
"""
import os
import subprocess
import time
import numpy as np
import tifffile
from PIL import Image

NAME = "flower-bud-alone-cpl"
SRC = r"D:\personal\macro\%s" % NAME
OFF = r"C:\dev\strehl-out\ORCH-gallery2\%s-auto.tif" % NAME
OUT = r"C:\dev\strehl-out\ORCH-halo"
EXE = r".cargo-target-orch\release\strehl.exe"
os.makedirs(OUT, exist_ok=True)

on_tif = os.path.join(OUT, "%s-halofix.tif" % NAME)
if not os.path.exists(on_tif):
    env = dict(os.environ)
    env["STREHL_FIX_HALO"] = "1"
    print("rendering with STREHL_FIX_HALO=1 ...", flush=True)
    t0 = time.time()
    r = subprocess.run(
        [EXE, "stack", SRC, "--out", on_tif, "--srgb", "--auto-exposure"],
        capture_output=True, text=True, env=env)
    print("  rc=%d in %.1f s" % (r.returncode, time.time() - t0))
    for line in (r.stderr or "").splitlines():
        if "halo" in line.lower() or "exposure" in line.lower():
            print("  | " + line.rstrip())
    if r.returncode != 0:
        raise SystemExit((r.stderr or "")[-3000:])

a = tifffile.imread(OFF).astype(np.float32) / 65535.0
b = tifffile.imread(on_tif).astype(np.float32) / 65535.0
assert a.shape == b.shape, (a.shape, b.shape)

d = np.abs(a - b).max(axis=2)
print()
print("pixels changed by the correction : %.4f%%" % (100 * (d > 1 / 65535).mean()))
print("max abs difference               : %.4f" % d.max())
print("RMS difference over changed px   : %.5f"
      % float(np.sqrt((d[d > 1 / 65535] ** 2).mean())) if (d > 1 / 65535).any() else 0.0)

# Crop where the correction actually did the most work -- that is where the
# claim lives. Found on the DIFFERENCE, so neither render chooses the view.
s = 8
ds = d[::s, ::s]
k = 900 // (2 * s)
c = np.zeros((ds.shape[0] + 1, ds.shape[1] + 1))
np.cumsum(np.cumsum(ds.astype(np.float64), 0), 1, out=c[1:, 1:])
H, W = ds.shape
y0 = np.clip(np.arange(H) - k, 0, H); y1 = np.clip(np.arange(H) + k, 0, H)
x0 = np.clip(np.arange(W) - k, 0, W); x1 = np.clip(np.arange(W) + k, 0, W)
tot = (c[np.ix_(y1, x1)] - c[np.ix_(y0, x1)]
       - c[np.ix_(y1, x0)] + c[np.ix_(y0, x0)])
iy, ix = np.unravel_index(int(np.argmax(tot)), tot.shape)
cy, cx = iy * s, ix * s
N = 900
y = int(np.clip(cy - N // 2, 0, a.shape[0] - N))
x = int(np.clip(cx - N // 2, 0, a.shape[1] - N))
print("crop at y=%d x=%d (max of the difference, so neither render picked it)" % (y, x))

ca = (a[y:y + N, x:x + N] * 255).astype(np.uint8)
cb = (b[y:y + N, x:x + N] * 255).astype(np.uint8)
bar = np.full((N, 6, 3), 255, np.uint8)
Image.fromarray(np.concatenate([ca, bar, cb], axis=1)).save(
    os.path.join(OUT, "SBS-halo-OFF-left-ON-right.png"))

# Whole-frame previews for the overall impression.
Image.fromarray((a[::6, ::6] * 255).astype(np.uint8)).save(
    os.path.join(OUT, "full-OFF.png"))
Image.fromarray((b[::6, ::6] * 255).astype(np.uint8)).save(
    os.path.join(OUT, "full-ON.png"))
print("wrote %s" % OUT)
