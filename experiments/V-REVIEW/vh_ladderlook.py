"""Cut the SAME fixed box from every ladder rung and tile them, so the only
difference between panels is the planted amplitude.

crop1to1.py ranks sites per image; on a ladder the ranking can move when the
plant changes the gradient, which would compare different places and call it a
difference in amplitude. A fixed box cannot do that. Fixed gamma, no autoscale,
no per-panel normalisation -- the tone difference IS the measurement.
"""
import os
import numpy as np
import tifffile
from PIL import Image, ImageDraw

LAD = r"D:\strehl-out\V-REVIEW\ladder"
HOST = "pencil-flatter-angle-cpl"
AMPS = [0, 500, 2000, 4500, 9000]
SIZE = 460
GAMMA = 2.2

# Locate a boundary site from the unplanted rung, then reuse it for all rungs.
base = tifffile.imread(os.path.join(LAD, "%s-A00000.tiff" % HOST))
plant = tifffile.imread(os.path.join(LAD, "%s-A09000.tiff" % HOST)).astype(np.int32)
delta = (plant - base.astype(np.int32))[:, :, 1]
# strongest planted rim, away from the frame edge
d = delta.copy()
m = SIZE
d[:m, :] = 0; d[-m:, :] = 0; d[:, :m] = 0; d[:, -m:] = 0
iy, ix = np.unravel_index(int(np.argmax(d)), d.shape)
y0, x0 = iy - SIZE // 2, ix - SIZE // 2
print("fixed crop box at (y=%d,x=%d) size %d; planted delta there = %d DN"
      % (y0, x0, SIZE, int(delta[iy, ix])))

panels = []
for a in AMPS:
    img = tifffile.imread(os.path.join(LAD, "%s-A%05d.tiff" % (HOST, a)))
    c = img[y0:y0 + SIZE, x0:x0 + SIZE, :3].astype(np.float32) / 65535.0
    c = np.clip(c, 0, 1) ** (1.0 / GAMMA)
    panels.append((a, (c * 255).astype(np.uint8)))

W = SIZE * len(panels)
sheet = Image.new("RGB", (W, SIZE + 26), (16, 16, 16))
dr = ImageDraw.Draw(sheet)
for i, (a, p) in enumerate(panels):
    sheet.paste(Image.fromarray(p), (i * SIZE, 26))
    dr.text((i * SIZE + 8, 7), "planted %d DN" % a, fill=(255, 255, 0))
out = r"D:\strehl-out\V-REVIEW\halo\crops\LADDER-fixedbox.jpg"
sheet.save(out, quality=95)
print("wrote", out, sheet.size)

# What the planted amplitude does to the measured tone in that very box.
print("\n%-8s %-12s %-12s" % ("planted", "box median", "delta vs A=0"))
b0 = None
for a, p in panels:
    img = tifffile.imread(os.path.join(LAD, "%s-A%05d.tiff" % (HOST, a)))
    reg = img[y0:y0 + SIZE, x0:x0 + SIZE, 1].astype(np.float32)
    med = float(np.median(reg))
    if b0 is None:
        b0 = med
    print("%-8d %-12.1f %-12.1f" % (a, med, med - b0))
