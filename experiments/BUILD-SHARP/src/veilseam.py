import numpy as np, tifffile
from PIL import Image
R = r"C:\dev\strehl-out\BUILD-SHARP\veil"; OUT=r"C:\dev\strehl-out\BUILD-SHARP\pictures\veil"
A = tifffile.imread(rf"{R}\coffee-bean\A\linear-srgb.tif").astype(np.float32)
B = tifffile.imread(rf"{R}\coffee-bean\B\linear-srgb.tif").astype(np.float32)
y0,x0,hh,ww = 60, 3200, 1050, 1500
a=A[y0:y0+hh, x0:x0+ww]; b=B[y0:y0+hh, x0:x0+ww]
hi = 65535.0
def tone(x): return (np.clip(x/hi,0,1)**(1/2.2)*255).astype(np.uint8)
clip = (b>=65535).any(axis=2)
bm = tone(b).copy(); bm[clip] = [255,0,0]      # mark clipped pixels red
gap=np.full((hh,12,3),255,np.uint8)
Image.fromarray(np.concatenate([tone(a),gap,tone(b),gap,bm],axis=1)).save(rf"{OUT}\seam-coffee-bean.png")
print("crop clipped frac  A", float((a>=65535).any(axis=2).mean()), " B", float(clip.mean()))
print("crop mean level    A", float(a.mean()), " B", float(b.mean()))
