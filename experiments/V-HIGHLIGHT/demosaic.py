import numpy as np, tifffile
from scipy.ndimage import uniform_filter, sobel
from PIL import Image

def edgechroma(path, label, scale):
    a = tifffile.imread(path).astype(np.float32)
    H, W, _ = a.shape
    R, G, B = a[:,:,0], a[:,:,1], a[:,:,2]
    lum = (R + 2*G + B) * 0.25
    m = ((R + B)*0.5 - G) / np.maximum(lum, 256.0)
    w = max(3, int(round(31/scale)))
    exc = np.abs(m - uniform_filter(m, size=w))
    ls = uniform_filter(lum, size=3)
    g = np.hypot(sobel(ls,axis=0), sobel(ls,axis=1))
    edge = g > np.percentile(g, 99.5)
    print("%-46s  %dx%d  mean|chroma excess| at edges = %.5f   p99 = %.5f   frac>0.10 = %.3f%%"
          % (label, W, H, exc[edge].mean(), np.percentile(exc[edge],99), 100.0*(exc[edge]>0.10).mean()))
    return exc[edge].mean()

print("--- same binary 471D50DA, same subject, same --merge pyramid --pyramid-gate 4.5 ---")
d = edgechroma(r"C:\dev\strehl-out\V-HIGHLIGHT\fba-srgb-default.tiff", "--srgb   (Malvar-He-Cutler DEMOSAIC, 7040px)", 1.0)
b = edgechroma(r"C:\dev\strehl-out\V-HIGHLIGHT\fba-lin-default.tiff",  "--linear-srgb (BINNED, NO demosaic, 3520px)", 2.0)
print("\ndemosaiced arm carries %.2fx the edge chroma of the binned arm" % (d/b))

# visual: ORCH crop region, my two arms side by side
X0,Y0,S = 3200,800,800
for tag,p in [("MINE-CAon", r"C:\dev\strehl-out\V-HIGHLIGHT\fba-srgb-default.tiff"),
              ("MINE-CAoff",r"C:\dev\strehl-out\V-HIGHLIGHT\fba-srgb-CAoff.tiff")]:
    c = tifffile.imread(p)[Y0:Y0+S, X0:X0+S]
    Image.fromarray(np.clip(c/257,0,255).astype(np.uint8)).save("fba-%s.png"%tag)
print("wrote crops fba-MINE-CAon.png / fba-MINE-CAoff.png")
