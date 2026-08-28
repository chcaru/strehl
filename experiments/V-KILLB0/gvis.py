"""V-KILLB0 gvis.py -- the visual ground-truth panel.  REAL FRAME | default | b0x4.

ground.py and ground2.py both went void on their own controls (K1 marginal, K2
0.553 -- focus moves so fast on leaf-2 that a 5-frame average is already
defocused), so no NUMBER from them is usable.  What survives is the picture: for
a structured tile there is a source frame in which that tile is genuinely in
focus, and that frame shows what the scene actually contains.  If default shows
the same texture the real frame shows and b0x4 does not, default is right.  If
the real frame is smooth where default is busy, default is manufacturing mottle
and the whole leaf-2 finding collapses.

No stretch is shared between panels: each is scaled by its own 0.5/99.5
percentiles, because the develop is linear and dark and the masters are sRGB.
Sharing a stretch across a tone mismatch would be the misleading choice here.
The develop is shown at the SINGLE peak-focus frame, not an average.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-HEADTOHEAD2")
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-LINEAR2")
import h2                                    # noqa: E402
import bandsignal as BS                      # noqa: E402

T, MARGIN, NY, NX = BS.T, BS.MARGIN, 10, 13
DEV = r"C:\dev\strehl-out\V-NOISE2\leaf\lintiff"
OUT = r"C:\dev\strehl-out\V-KILLB0"
KEY = "leaf-2-cpl"
WIN, SEARCH = 512, 48


def radial(img, f0, f1):
    a = np.fft.rfft2(img.astype(np.float64))
    h, w = img.shape
    r = np.hypot(np.fft.fftfreq(h)[:, None], np.fft.rfftfreq(w)[None, :])
    a *= ((r >= f0) & (r < f1))
    return np.fft.irfft2(a, s=img.shape)


def best_shift(ref, arm):
    c = WIN // 2
    r = ref[c-T//2:c+T//2, c-T//2:c+T//2]; r = r - r.mean()
    er = np.sqrt((r*r).mean()); bb, sh = -2.0, (0, 0)
    for dy in range(-SEARCH, SEARCH+1, 2):
        for dx in range(-SEARCH, SEARCH+1, 2):
            a = arm[c+dy-T//2:c+dy+T//2, c+dx-T//2:c+dx+T//2]
            a = a - a.mean(); ea = np.sqrt((a*a).mean())
            if ea == 0:
                continue
            v = (r*a).mean()/(er*ea)
            if v > bb:
                bb, sh = v, (dy, dx)
    return sh


def st(a):
    lo, hi = np.percentile(a, 0.5), np.percentile(a, 99.5)
    return np.clip((a-lo)/max(hi-lo, 1e-9), 0, 1)


files = sorted(f for f in os.listdir(DEV) if f.lower().endswith(".tif"))
step = max(1, round(len(files)/80))
selp = np.load(os.path.join(OUT, f"{KEY}-selp.npy"))
mm = tifffile.memmap(os.path.join(DEV, files[0]), mode="r"); H, W = mm.shape[0], mm.shape[1]; del mm
ys = np.linspace(MARGIN, H-MARGIN-T, NY).astype(int)
xs = np.linspace(MARGIN, W-MARGIN-T, NX).astype(int)
pos = [(int(y), int(x)) for y in ys for x in xs]
ma = h2.luma709(tifffile.imread(os.path.join(OUT, "default", KEY+".tiff"))[..., :3].astype(np.float64))
mb = h2.luma709(tifffile.imread(os.path.join(OUT, "b0x4", KEY+".tiff"))[..., :3].astype(np.float64))

panels = []
for t in [int(x) for x in sys.argv[1:]] or [73, 33]:
    y, x = pos[t]
    fi = int(np.nanargmax(selp[:, t])*step)
    cy, cx = y+T//2, x+T//2
    sy, sx = slice(cy-WIN//2, cy+WIN//2), slice(cx-WIN//2, cx+WIN//2)
    dev = h2.luma709(np.asarray(tifffile.memmap(os.path.join(DEV, files[fi]), mode="r")[sy, sx, :3], np.float64))
    dvb = radial(dev, 0.05, 0.14)
    sha = best_shift(dvb, radial(ma[sy, sx], 0.05, 0.14))
    shb = best_shift(dvb, radial(mb[sy, sx], 0.05, 0.14))
    c = WIN//2
    pr = st(dev[c-T//2:c+T//2, c-T//2:c+T//2])
    pa = st(ma[sy, sx][c+sha[0]-T//2:c+sha[0]+T//2, c+sha[1]-T//2:c+sha[1]+T//2])
    pb = st(mb[sy, sx][c+shb[0]-T//2:c+shb[0]+T//2, c+shb[1]-T//2:c+shb[1]+T//2])
    print(f"tile {t} y={y} x={x} in-focus frame={files[fi]} shift default={sha} b0x4={shb}")
    panels.append(np.concatenate([pr, np.ones((T, 6)), pa, np.ones((T, 6)), pb], axis=1))

img = np.concatenate([p for pair in zip(panels, [np.ones((6, panels[0].shape[1]))]*len(panels))
                      for p in pair][:-1], axis=0)
p = os.path.join(OUT, "crops", f"{KEY}-gvis.png")
Image.fromarray((img*255).astype(np.uint8)).resize(
    (img.shape[1]*3, img.shape[0]*3), Image.NEAREST).save(p)
print(f"wrote {p}   columns: [ REAL IN-FOCUS FRAME | default | b0x4 ]")
