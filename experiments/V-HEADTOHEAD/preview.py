"""Downsampled previews of both arms, plus a clipping map for the prior arm."""
import numpy as np, tifffile, os
OUT = r"C:\dev\strehl-out\V-HEADTOHEAD"
os.makedirs(OUT, exist_ok=True)
PRIOR = r"C:\dev\macro\out\coffee-bean\stack.tif"
STREHL = r"C:\dev\strehl-out\SHIP-V2\coffee-bean--SHIP-V2.tiff"

def srgb_encode(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.power(v, 1/2.4) - 0.055)

f = 6
a = tifffile.memmap(PRIOR, mode="r")
h = (a.shape[0]//f)*f; w = (a.shape[1]//f)*f
p = np.asarray(a[:h,:w,:]).astype(np.float32).reshape(h//f,f,w//f,f,3).mean(axis=(1,3))
clip = (np.asarray(a[:h,:w,:]) >= 1.0).any(axis=2).reshape(h//f,f,w//f,f).mean(axis=(1,3))
del a
tifffile.imwrite(os.path.join(OUT,"preview_prior.png"), (srgb_encode(p)*255).astype(np.uint8))
# clip overlay: red where clipped
ov = (srgb_encode(p)*255).astype(np.uint8).copy()
m = clip > 0.5
ov[m] = np.array([255,0,255], np.uint8)
tifffile.imwrite(os.path.join(OUT,"preview_prior_clipmap.png"), ov)
print("prior clipped-any-channel fraction:", float((clip>0.5).mean()))

b = tifffile.memmap(STREHL, mode="r")
h2=(b.shape[0]//f)*f; w2=(b.shape[1]//f)*f
s = np.asarray(b[:h2,:w2,:]).astype(np.float32).reshape(h2//f,f,w2//f,f,3).mean(axis=(1,3))/65535.0
del b
tifffile.imwrite(os.path.join(OUT,"preview_strehl.png"), (np.clip(s,0,1)*255).astype(np.uint8))
print("wrote previews to", OUT, p.shape, s.shape)
