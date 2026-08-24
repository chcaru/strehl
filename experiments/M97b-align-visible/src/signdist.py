"""Inspect the per-tile radius ratios from signcheck.py.

D4 was pre-registered as max-minus-min < 0.005, which a single bad tile
destroys. This prints the whole distribution so the failure can be attributed:
genuine spatial heterogeneity between the arms, or one unmatchable tile.
"""

import json

import numpy as np

d = json.load(open(r"C:\dev\strehl-out\M97\signcheck.json", encoding="utf-8"))
t = d["TREATMENT null"]["tiles"]
r = np.array([x["ratio"] for x in t])
n = np.array([x["ncc"] for x in t])
rad = np.array([x["r_aligned"] for x in t])
dy = np.array([x["dy"] for x in t])
dx = np.array([x["dx"] for x in t])

print("  ncc    ratio   r_aligned      dy      dx   radial_disp_px")
for i in np.argsort(r):
    # component of the displacement along the radius: the part a pure scale
    # would produce. A global scale shows up here and nowhere else.
    ur = np.array([dy[i], dx[i]])
    print(f"{n[i]:6.3f}  {r[i]:8.5f}  {rad[i]:9.1f}  {dy[i]:+7.2f} {dx[i]:+7.2f}"
          f"   {(r[i] - 1.0) * rad[i]:+8.2f}")

print()
print(f"n = {len(r)}   median {np.median(r):.5f}   "
      f"IQR {np.percentile(r, 75) - np.percentile(r, 25):.5f}   "
      f"max-min {r.max() - r.min():.5f}")
for thr in (0.7, 0.8, 0.9):
    g = n > thr
    if g.sum() >= 4:
        print(f"ncc>{thr}: n={int(g.sum())}  median {np.median(r[g]):.5f}  "
              f"IQR {np.percentile(r[g], 75) - np.percentile(r[g], 25):.5f}  "
              f"max-min {r[g].max() - r[g].min():.5f}")

print()
print("self-check D1 exact value:", d["D1 self"]["median_radius_ratio"])
print("D1 spread:", d["D1 self"]["spread"])
