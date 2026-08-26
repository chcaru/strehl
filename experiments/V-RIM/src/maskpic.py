"""Overlay the two masks so the 7.3 point area disagreement is visible.

grey  = both methods call it subject
red   = ORCH only
blue  = V-RIM only
"""
import gc, sys
from pathlib import Path
import numpy as np
from scipy import ndimage
import tifffile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
from vrimlib import load_lum, segment

SRC = r"C:\dev\strehl-out\ORCH-rim\cb-1cacb61-lin.tif"
a = tifffile.imread(SRC)
mean_ch = a.astype(np.float32).mean(axis=2)
del a; gc.collect()
lo, hi = np.percentile(mean_ch, 5), np.percentile(mean_ch, 95)
dark = mean_ch < 0.5 * (lo + hi)
lab, n = ndimage.label(dark)
sizes = ndimage.sum(dark, lab, range(1, n + 1))
orch = ndimage.binary_fill_holes(lab == (int(np.argmax(sizes)) + 1))
del lab, dark; gc.collect()

shape, lum = load_lum(Path(SRC), "G")
mine, backdrop, diag = segment(lum)

s = 6
o = orch[::s, ::s]; m = mine[::s, ::s]
img = np.zeros(o.shape + (3,), np.float32)
base = np.clip(lum[::s, ::s] / 65535.0, 0, 1) ** 0.45
for c in range(3):
    img[..., c] = base * 0.55
img[o & m] = [0.62, 0.62, 0.62]
img[o & ~m] = [0.95, 0.15, 0.15]
img[~o & m] = [0.20, 0.45, 0.98]

fig, ax = plt.subplots(1, 2, figsize=(15, 7.2), dpi=110)
ax[0].imshow(base, cmap="gray"); ax[0].set_title(
    "coffee-bean merged render (display gamma only, for orientation)", fontsize=11)
ax[1].imshow(img); ax[1].set_title(
    f"grey = both ({(o&m).mean()*100:.1f}%)   red = ORCH only "
    f"({(o&~m).mean()*100:.1f}%)   blue = V-RIM only ({(~o&m).mean()*100:.1f}%)",
    fontsize=11)
for x in ax:
    x.set_xticks([]); x.set_yticks([])
fig.tight_layout()
out = r"C:\dev\strehl-out\V-RIM\pics\mask-disagreement.png"
fig.savefig(out)
print("wrote", out)
print(f"ORCH filled {orch.mean()*100:.2f}%   V-RIM {mine.mean()*100:.2f}%")
print(f"both {(orch&mine).mean()*100:.2f}%  ORCH-only {(orch&~mine).mean()*100:.2f}%  "
      f"V-RIM-only {(~orch&mine).mean()*100:.2f}%")
lbl, nn = ndimage.label(~orch & mine)
sz = ndimage.sum(~orch & mine, lbl, range(1, nn + 1))
print(f"V-RIM-only region: {nn} components, largest holds "
      f"{sz.max()/sz.sum()*100:.1f}% of the disagreement")
ys, xs = np.nonzero(lbl == 1 + int(np.argmax(sz)))
print(f"  largest component bbox y {ys.min()}-{ys.max()}  x {xs.min()}-{xs.max()}")
print(f"  its median green DN = {np.median(lum[ys, xs]):.0f}, "
      f"far field = {np.median(lum[backdrop]):.0f}")
