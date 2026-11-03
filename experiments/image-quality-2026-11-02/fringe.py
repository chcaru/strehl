"""Colour fringing on a neutral target. usage: fringe.py LIN.tif [LIN.tif ...]
Per-channel gains from bright flat pixels make the target grey; then, in the band
of strongest luma gradient (top 3%), report mean |R'-G| and |B'-G| as a share of the
local bright level, and the per-channel high-pass energy ratios R'/G and B'/G."""
import sys, numpy as np, tifffile
from scipy.ndimage import sobel, uniform_filter, maximum_filter, laplace
for p in sys.argv[1:]:
    a = tifffile.imread(p).astype(np.float32)[..., :3]
    H, W, _ = a.shape; a = a[H//8:-H//8, W//8:-W//8]  # central region
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    gm = np.hypot(sobel(G, 0), sobel(G, 1))
    flat = (gm < np.percentile(gm, 40)) & (G > np.percentile(G, 70))
    gR = np.median(R[flat] / G[flat]); gB = np.median(B[flat] / G[flat])
    Rn, Bn = R / gR, B / gB
    edge = gm > np.percentile(gm, 97)
    ref = maximum_filter(G, 15)
    fr = (np.abs(Rn - G) / ref)[edge].mean(); fb = (np.abs(Bn - G) / ref)[edge].mean()
    hp = lambda c: (laplace(c) ** 2)[edge].mean()
    print(f"{p.split('/')[-1]:14s} fringe R {fr*100:.3f}%  B {fb*100:.3f}%   hp R/G {hp(Rn)/hp(G):.4f}  B/G {hp(Bn)/hp(G):.4f}")
