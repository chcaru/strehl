"""LADDER v2. Two defects in v1, both caught by looking at the picture:

  1. The plant was built on the sub=4 grid and upsampled with order-1 zoom, so
     at 9000 DN it showed as 4 px BLOCKS. The eye would have been judging my
     resampling artifact, not a rim. Fixed: the distance field is now computed
     at FULL resolution.
  2. The crop site was the argmax of the plant, which sits in open background.
     A halo is judged AT A BOUNDARY. Fixed: the site must contain both subject
     and rim pixels.

Also adds a BROAD rim (peak 100 px, sigma 40) alongside the narrow one, because
flat-on-ruler-cpl's flagged elevation is at d=80-120 px and a narrow-rim
calibration says nothing about a broad one.
"""
import os, sys
import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, label

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check")
import halo_profile as H

HOST = "pencil-flatter-angle-cpl"
SRC = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful\%s.tiff" % HOST
OUT = r"D:\strehl-out\V-REVIEW\ladder2"
AMPS = [0, 500, 2000, 4500, 9000]
SHAPES = {"narrow": (10.0, 14.0), "broad": (100.0, 40.0)}
SIZE = 460
GAMMA = 2.2
os.makedirs(OUT, exist_ok=True)

img = tifffile.imread(SRC)
yf = H.luma(img)
print("host %s shape=%s" % (HOST, img.shape))
t, subj = H.segment(yf)
print("segmented at full res: subject = %.1f%% of frame" % (100 * subj.mean()))
d = distance_transform_edt(~subj)
bg = ~subj
print("full-res distance field: max %.0f px" % d.max())

for shape, (peak, sig) in SHAPES.items():
    field = np.exp(-((d - peak) ** 2) / (2 * sig ** 2)) * bg
    print("\n=== %s rim: peak %.0f px sigma %.0f ; %d px above 0.5 ==="
          % (shape, peak, sig, int((field > 0.5).sum())))
    for a in AMPS:
        dst = os.path.join(OUT, "%s-%s-A%05d.tiff" % (HOST, shape, a))
        if a == 0 and shape == "narrow":
            out = img.copy()
        elif a == 0:
            continue
        else:
            out = img.astype(np.float32)
            add = (field * a).astype(np.float32)
            for c in range(out.shape[2]):
                out[:, :, c] += add
            out = np.clip(out, 0, 65535).astype(img.dtype)
        tifffile.imwrite(dst, out)
        clip = float((out >= 65535).mean()) * 100
        v, over, bump, pen, farl, bands, why = H.profile(H.luma(out))
        print("  %-6s A=%5d -> %-10s overshoot %9s bump %8s clip %.2f%%"
              % (shape, a, v,
                 ("%.1f" % over) if over is not None else "-",
                 ("%.1f" % bump) if bump is not None else "-", clip))

# --- site that straddles a boundary: subject present AND rim present ---
narrow = np.exp(-((d - 10.0) ** 2) / (2 * 14.0 ** 2)) * bg
best, bxy = -1, None
step = 200
for yy in range(SIZE, img.shape[0] - SIZE, step):
    for xx in range(SIZE, img.shape[1] - SIZE, step):
        s = subj[yy:yy + SIZE, xx:xx + SIZE].mean()
        r = narrow[yy:yy + SIZE, xx:xx + SIZE].mean()
        if 0.25 < s < 0.75:              # a real edge crosses the box
            sc = r
            if sc > best:
                best, bxy = sc, (yy, xx)
y0, x0 = bxy
print("\nboundary crop box (y=%d,x=%d): subject %.0f%% of box, rim energy %.3f"
      % (y0, x0, 100 * subj[y0:y0 + SIZE, x0:x0 + SIZE].mean(), best))

for shape in SHAPES:
    panels = []
    for a in AMPS:
        f = os.path.join(OUT, "%s-%s-A%05d.tiff" % (HOST, shape, a))
        if not os.path.exists(f):
            f = os.path.join(OUT, "%s-narrow-A00000.tiff" % HOST)
        im = tifffile.imread(f)
        c = im[y0:y0 + SIZE, x0:x0 + SIZE, :3].astype(np.float32) / 65535.0
        panels.append((a, (np.clip(c, 0, 1) ** (1 / GAMMA) * 255).astype(np.uint8)))
    sheet = Image.new("RGB", (SIZE * len(panels), SIZE + 26), (16, 16, 16))
    dr = ImageDraw.Draw(sheet)
    for i, (a, p) in enumerate(panels):
        sheet.paste(Image.fromarray(p), (i * SIZE, 26))
        dr.text((i * SIZE + 8, 7), "%s  planted %d DN" % (shape, a), fill=(255, 255, 0))
    o = r"D:\strehl-out\V-REVIEW\halo\crops\LADDER2-%s.jpg" % shape
    sheet.save(o, quality=95)
    print("wrote", o)
