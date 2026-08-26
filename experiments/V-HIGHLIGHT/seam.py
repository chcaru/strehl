import sys, numpy as np, tifffile
from PIL import Image
a = tifffile.imread(sys.argv[1]).astype(np.float64)
b = tifffile.imread(sys.argv[2]).astype(np.float64)
tag = sys.argv[3]
moved = np.any(a != b, axis=2)
# find a 400x400 window with the most knee-CROSSING content: both moved and
# unmoved-but-bright pixels present, so any seam has to show.
lvl = a.max(axis=2)
near = moved & (lvl < 50000)          # gently-corrected, where a seam would live
H, W = moved.shape
best, bxy = -1, (0,0)
S = 400
for y in range(0, H-S, 100):
    for x in range(0, W-S, 100):
        w = near[y:y+S, x:x+S]
        u = ((lvl[y:y+S, x:x+S] > 40000) & ~moved[y:y+S, x:x+S])
        score = min(w.sum(), u.sum())
        if score > best:
            best, bxy = score, (y, x)
y, x = bxy
print("%s window y=%d x=%d  gently-moved=%d  bright-unmoved=%d" % (tag, y, x, near[y:y+S,x:x+S].sum(), best))
def png(arr, path):
    v = np.clip(arr/65535.0, 0, 1) ** (1/2.2)
    Image.fromarray((v*255).astype(np.uint8)).save(path)
ca, cb = a[y:y+S, x:x+S], b[y:y+S, x:x+S]
png(ca, "seam-%s-OFF.png" % tag); png(cb, "seam-%s-DEF.png" % tag)
d = np.abs(cb-ca).max(axis=2)
print("crop max|d| %d ; moved %.2f%%" % (d.max(), 100.0*(d>0).mean()))
# amplified difference map, and a mask of exactly which pixels moved
Image.fromarray((np.clip(d/max(d.max(),1)*255*4,0,255)).astype(np.uint8)).save("seam-%s-DIFF.png" % tag)
Image.fromarray(((d>0)*255).astype(np.uint8)).save("seam-%s-MASK.png" % tag)
sbs = np.concatenate([np.clip(ca/65535,0,1)**(1/2.2), np.clip(cb/65535,0,1)**(1/2.2)], axis=1)
Image.fromarray((sbs*255).astype(np.uint8)).save("seam-%s-SBS.png" % tag)
