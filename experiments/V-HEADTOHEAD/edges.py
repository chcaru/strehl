"""Locate the bean silhouette (the occluding edge) in PRIOR coordinates and emit
a list of well-conditioned, unclipped edge sites with their outward normals."""
import numpy as np, h2h, tifffile
from scipy import ndimage
P, S = h2h.open_arms()
f = 8
a = np.asarray(P[:, :, 1], np.float32)
h = (a.shape[0]//f)*f; w = (a.shape[1]//f)*f
small = a[:h, :w].reshape(h//f, f, w//f, f).mean(axis=(1,3))
clip = (np.asarray(P[:h:1, :w:1, :], np.float32).max(axis=2) >= 1.0)
csmall = clip[:h, :w].reshape(h//f, f, w//f, f).mean(axis=(1,3))
mask = small < 0.45          # bean is dark, paper is bright
mask = ndimage.binary_opening(mask, np.ones((5,5)))
mask = ndimage.binary_fill_holes(mask)
lbl, n = ndimage.label(mask)
sizes = ndimage.sum(mask, lbl, range(1, n+1))
mask = lbl == (1 + int(np.argmax(sizes)))
print("bean area frac:", float(mask.mean()))
ys, xs = np.where(mask)
print(f"bean bbox in prior px: y {ys.min()*f}-{ys.max()*f}  x {xs.min()*f}-{xs.max()*f}")
# boundary + outward normal from the distance transform gradient
d = ndimage.distance_transform_edt(~mask) - ndimage.distance_transform_edt(mask)
gy, gx = np.gradient(ndimage.gaussian_filter(d, 2.0))
bnd = ndimage.binary_dilation(mask, np.ones((3,3))) & ~ndimage.binary_erosion(mask, np.ones((3,3)))
by, bx = np.where(bnd)
sites = []
for y, x in zip(by, bx):
    ny, nx = gy[y, x], gx[y, x]
    L = np.hypot(ny, nx)
    if L < 1e-3: continue
    ny, nx = ny/L, nx/L
    # require paper OUTSIDE unclipped for 30 coarse px, and inside the frame
    oy = int(round(y + ny*4)); ox = int(round(x + nx*4))
    iy = int(round(y - ny*4)); ix = int(round(x - nx*4))
    if not (0 <= oy < mask.shape[0] and 0 <= ox < mask.shape[1]): continue
    if not (0 <= iy < mask.shape[0] and 0 <= ix < mask.shape[1]): continue
    if mask[oy, ox] or not mask[iy, ix]: continue
    if csmall[max(0,oy-2):oy+3, max(0,ox-2):ox+3].max() > 0.0: continue   # clipped outside
    sites.append((y*f + f//2, x*f + f//2, ny, nx))
sites = np.array(sites)
print("candidate unclipped silhouette sites (coarse):", len(sites))
np.save("edge_sites.npy", sites)
# summarise where they are
if len(sites):
    print("  y range", sites[:,0].min(), sites[:,0].max(), " x range", sites[:,1].min(), sites[:,1].max())
    # print a decimated list
    for s in sites[::max(1, len(sites)//25)]:
        print(f"   y={s[0]:6.0f} x={s[1]:6.0f} n=({s[2]:+.2f},{s[3]:+.2f})")
