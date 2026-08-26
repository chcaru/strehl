import numpy as np, tifffile
from PIL import Image
p = r"C:\dev\strehl-out\GALLERY-NOW\flower-bud-alone-cpl.tif"
a = tifffile.imread(p)
x0, y0 = 3200, 800
c = a[y0:y0+800, x0:x0+800].astype(np.float32)
R, G, B = c[:,:,0], c[:,:,1], c[:,:,2]
mg = ((R - G) + (B - G)) / 2.0
lvl = c.max(axis=2)
# where is the white background in this crop?
white = (lvl > 55000) & (np.abs(mg) < 3000)
print("white-ish background pixels in crop: %.2f%%" % (100.0*white.mean()))
for name, sl in [("upper-right 200x200", (slice(0,200), slice(600,800))),
                 ("lower-left 200x200",  (slice(600,800), slice(0,200)))]:
    q = c[sl]
    print("  %-20s level median %.0f max %.0f   mg median %.0f" % (
        name, np.median(q.max(axis=2)), q.max(), np.median(((q[:,:,0]-q[:,:,1])+(q[:,:,2]-q[:,:,1]))/2)))
# visualise: magenta positive = red overlay, negative(green) = ignored
vis = np.clip(c/65535.0,0,1)**(1/2.2)
heat = np.clip(mg/4000.0, 0, 1)
ov = vis.copy(); ov[:,:,0] = np.maximum(ov[:,:,0], heat); ov[:,:,1] *= (1-heat*0.7); ov[:,:,2] = np.maximum(ov[:,:,2], heat)
Image.fromarray((np.concatenate([vis,ov],axis=1)*255).astype(np.uint8)).save("fba-orch-magentamap.png")
# the strongest magenta run, as a tight zoom
th = 2500
ys, xs = np.where(mg >= th)
print("pixels with mg >= %d : %d" % (th, len(xs)))
if len(xs):
    print("  bbox crop x %d..%d y %d..%d  centroid (%.0f,%.0f)" % (xs.min(),xs.max(),ys.min(),ys.max(),xs.mean(),ys.mean()))
    cx, cy = int(xs.mean()), int(ys.mean())
    zx, zy = max(0,cx-100), max(0,cy-100)
    z = vis[zy:zy+200, zx:zx+200]
    Image.fromarray((np.kron(z, np.ones((2,2,1)))*255).astype(np.uint8)).save("fba-orch-zoom.png")
    print("  zoom crop-origin (%d,%d) -> full (%d,%d)" % (zx,zy,x0+zx,y0+zy))
