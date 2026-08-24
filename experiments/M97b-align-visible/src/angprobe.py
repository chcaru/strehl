"""Probe the graduation geometry: how wide is a tick, how wide is the gap?

Written because the plant in angrun.ps1 recovered only ~18% of a known 2.0 px
bend. The suspected cause is that both the tracking window (HALF_WIN=9, so 19
px) and the background median (BG_MED=61) were sized for a thin line, while
these graduations are engraved bars. If a tick is wider than the window, the
centroid is pinned by the window edges rather than the tick, and the tracker
goes nearly blind to displacement. Measure it rather than assume it.
"""

import numpy as np
import tifffile
from scipy.ndimage import median_filter

P = r"C:\dev\strehl-out\M97\angruler-ALIGNED.tif"
ROI_Y0, ROI_Y1, ROI_X0, ROI_X1 = 3000, 4600, 3250, 4900

a = tifffile.imread(P)
img = a.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
roi = img[ROI_Y0:ROI_Y1, ROI_X0:ROI_X1]

row = roi[800]
print("row 800 of ROI, x 0..400:")
for w in (61, 121, 201, 301):
    bg = median_filter(roi[800:801], size=(1, w), mode="nearest")[0]
    d = np.maximum(bg - row, 0)
    print(f"  BG_MED={w:4d}  bg med={np.median(bg):8.1f}  depth p99={np.percentile(d, 99):8.1f}"
          f"  frac depth>0.5*max={float((d > 0.5 * d.max()).mean()):.3f}")

# Tick width at half depth, from a generous background.
bg = median_filter(roi, size=(1, 401), mode="nearest")
depth = np.maximum(bg - roi, 0.0)
prof = depth[700:900].mean(axis=0)
half = 0.5 * np.percentile(prof, 99)
on = prof > half
runs = []
i = 0
while i < len(on):
    if on[i]:
        j = i
        while j < len(on) and on[j]:
            j += 1
        runs.append((i, j - i))
        i = j
    else:
        i += 1
widths = [n for _, n in runs if n >= 4]
print(f"\nticks found: {len(widths)}")
print(f"tick width at half depth: median={np.median(widths):.1f} px  min={min(widths)} max={max(widths)}")
starts = [s for s, n in runs if n >= 4]
print(f"tick pitch: median={np.median(np.diff(starts)):.1f} px")
print(f"duty cycle: {np.median(widths) / np.median(np.diff(starts)):.3f}")
