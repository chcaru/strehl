"""Is there a hard straight seam in the shipped render?

The worst-kurtosis window of the shipped render did not look like crazy paving.
It looked like a rectangular region of different texture with a hard straight
boundary -- which nature does not produce and a tile-based processing stage
does. This crops a wide area around it and, separately, tests the claim
numerically: a real seam is a step that is CONSTANT along one axis and abrupt
across it.

Instrument: for every candidate column x, compare the mean of the strip to its
left against the strip to its right, and normalise by the local row-to-row
variation. A seam is a column whose left/right step is large and consistent
down the whole height. A texture change with a wandering natural boundary is
not.

Controls:
  N1  the same scan on a single unmerged input frame -- there is no tiling in a
      single frame, so any seam the scan reports there is the scan's own noise.
  N2  a planted seam of known position and known amplitude, to prove the scan
      can see one at all.

Reads only. Writes to C:\\dev\\strehl-out\\ORCH-morning. Never touches D:\\.
"""
import os

import numpy as np
import tifffile
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
OUT = r"C:\dev\strehl-out\ORCH-morning"
SHIPPED = r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif"
SINGLE = r"C:\dev\strehl-out\M93-out\armF-f173.tif"


def lum(p):
    a = tifffile.imread(p)
    if a.dtype != np.uint16:
        raise SystemExit("%s is %s, expected uint16" % (p, a.dtype))
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


def seam_scan(L, w=8, label=""):
    """Return (best_x, z) for the strongest vertical seam in L."""
    H, W = L.shape
    best = (None, 0.0)
    zs = []
    for x in range(w, W - w):
        left = L[:, x - w : x].mean(axis=1)
        right = L[:, x : x + w].mean(axis=1)
        step = right - left
        # A seam is a step that is consistent down the column: large |mean|
        # relative to its own scatter. A wandering natural boundary is not.
        s = step.std()
        z = abs(step.mean()) / (s / np.sqrt(len(step))) if s > 0 else 0.0
        zs.append(z)
        if z > best[1]:
            best = (x, z)
    zs = np.array(zs)
    print("  %-34s strongest seam at x=%s  z=%.1f   (median z over all columns %.1f)"
          % (label, best[0], best[1], np.median(zs)))
    return best, zs


print("SEAM SCAN -- is there a hard straight vertical boundary in the output?\n")

X, Y, N = 586, 2344, 512
Ls = lum(SHIPPED)
crop = Ls[Y : Y + N, X : X + N]

print("N2 positive control (planted seam, amplitude = 0.25 sd):")
plant = crop.copy()
amp = 0.25 * crop.std()
plant[:, N // 2 :] += amp
(bx, bz), _ = seam_scan(plant, label="planted seam at x=256")
if bx is None or abs(bx - N // 2) > 3:
    raise SystemExit("PLANT NOT FOUND at x=256 (got %s) -- the scan cannot see a seam, "
                     "so nothing below means anything" % bx)
print("     plant recovered at x=%d, off by %d px -- scan is live\n" % (bx, abs(bx - N // 2)))

print("N1 negative control (single unmerged input frame, no tiling in its history):")
Lsg = lum(SINGLE)
h, w = Lsg.shape
(_, z_single), zs_single = seam_scan(Lsg[h // 2 - N // 2 : h // 2 + N // 2,
                                         w // 2 - N // 2 : w // 2 + N // 2],
                                     label="single frame centre")
print()

print("THE MEASUREMENT (shipped render, worst-kurtosis window):")
(sx, sz), zs_ship = seam_scan(crop, label="shipped render crop")
print()
print("shipped strongest z = %.1f   single-frame strongest z = %.1f   ratio = %.2fx"
      % (sz, z_single, sz / z_single if z_single else float("nan")))
print("VERDICT: %s" % ("a straight seam is present in the merge and absent from the photograph"
                       if sz > 3 * z_single else
                       "NO seam distinguishable from what a single photograph produces"))

Z, pad, lab = 2, 12, 30
panels = [("shipped render  x=%d..%d y=%d..%d" % (X, X + N, Y, Y + N), crop),
          ("single input frame, same size", Lsg[h // 2 - N // 2 : h // 2 + N // 2,
                                                w // 2 - N // 2 : w // 2 + N // 2])]
sheet = Image.new("L", ((N * Z + pad) * len(panels) - pad, N * Z + lab), 255)
d = ImageDraw.Draw(sheet)
for i, (t, wnd) in enumerate(panels):
    lo, hi = np.percentile(wnd, [0.5, 99.5])
    st = np.clip((wnd - lo) / max(hi - lo, 1e-9), 0, 1) * 255.0
    sheet.paste(Image.fromarray(st.astype(np.uint8)).resize((N * Z, N * Z), Image.NEAREST),
                (i * (N * Z + pad), lab))
    d.text((i * (N * Z + pad) + 8, 9), t, fill=0)
p = os.path.join(OUT, "SEAM-wide.png")
sheet.save(p)
print("wrote %s" % p)
