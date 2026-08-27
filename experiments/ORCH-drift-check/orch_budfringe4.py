"""ORCH: is the pink rim on flower-bud-alone real colour, or simultaneous contrast?

The commissioned magenta statistic (orch_budfringe3.py) separates the three reported
specular-fringe subjects from four showcase subjects with a clean gap, and scores
flower-bud-alone at 0.00% -- the LOWEST of all eight -- while a 3x blowup shows an
obvious pink line on the bud silhouette.

Two hypotheses:
  H1  real chroma: pixels on the rim have R>G and B>G by a visible margin.
  H2  perceptual: the rim is a desaturated transition that only LOOKS pink because it
      abuts a strongly green interior (simultaneous contrast). No pixel is actually pink.

H1 and H2 are separated by reading the pixels, which no summary statistic did.
Print raw RGB transects across the boundary at the rows where the rim is visible.
"""
import os
import numpy as np
from PIL import Image

ASSETS = r"C:\dev\strehl-out\VIEW-SHIP\assets"

im = np.asarray(Image.open(
    os.path.join(ASSETS, "flower-bud-alone-cpl--SHIP-V2--1to1.png")
).convert("RGB")).astype(np.int32)

sus = im[20:220, 350:560]
R, G, B = sus[:, :, 0], sus[:, :, 1], sus[:, :, 2]
pink = np.minimum(R - G, B - G)

print(f"suspect region {sus.shape}, pink=min(R-G,B-G)")
print(f"  pink  max={pink.max():4d}  p99.9={np.percentile(pink,99.9):6.1f}  "
      f"p99={np.percentile(pink,99):6.1f}  median={np.median(pink):6.1f}")
n_pos = int((pink > 0).sum())
print(f"  pixels with BOTH R>G and B>G : {n_pos} / {pink.size} ({100*n_pos/pink.size:.2f}%)")

if n_pos:
    ys, xs = np.where(pink == pink.max())
    y, x = int(ys[0]), int(xs[0])
    print(f"  strongest pink pixel at region ({y},{x}) = image ({y+20},{x+350})")
else:
    y, x = 90, 110
    print("  no pixel has both R>G and B>G  ->  H1 already in trouble")

print("\nRAW TRANSECTS across the visible boundary (region coords)")
for row in (40, 60, 90, 120):
    if row >= sus.shape[0]:
        continue
    print(f"\n  row {row}:")
    print("     x    R    G    B   R-G  B-G   pink")
    seg = range(max(0, x - 14), min(sus.shape[1], x + 15))
    for xx in seg:
        r, g, b = int(R[row, xx]), int(G[row, xx]), int(B[row, xx])
        mark = "  <== both above G (PINK)" if (r > g and b > g) else ""
        print(f"   {xx:3d}  {r:3d}  {g:3d}  {b:3d}  {r-g:4d} {b-g:4d}  "
              f"{min(r-g,b-g):5d}{mark}")

print("\nVERDICT INPUTS")
print(f"  H1 (real pink) requires pixels with R>G AND B>G on the rim: found {n_pos}")
print("  H2 (simultaneous contrast) predicts the rim is merely LESS GREEN than the")
print("     interior, i.e. B-G rises toward 0 but never crosses it.")
bgv = (B - G)
print(f"  interior B-G median = {np.median(bgv):.1f}   rim-band max B-G = {bgv.max()}")
