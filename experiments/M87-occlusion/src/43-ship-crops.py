import numpy as np, pathlib
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
S = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")
b = np.asarray(Image.open(S/"30-SHIP-BEFORE-default.tif"))
a = np.asarray(Image.open(S/"31-SHIP-AFTER-fixhalo.tif"))
def crop(img, y0,y1,x0,x1): return img[y0:y1, x0:x1]
def save(arr, name):
    Image.fromarray((arr.astype(np.float32)/257.0).clip(0,255).astype(np.uint8)).save(S/name)
    print("wrote", name, arr.shape)
# leg / lower-left silhouette, 100% of the demosaiced render
REG = dict(leg=(2400,3100,600,1700), eye=(1500,2100,3400,4200))
for tag,(y0,y1,x0,x1) in REG.items():
    cb, ca = crop(b,y0,y1,x0,x1), crop(a,y0,y1,x0,x1)
    n = {"leg":("32-SHIP-BEFORE-leg.png","33-SHIP-AFTER-leg.png","34-SHIP-side-by-side-leg.png"),
         "eye":("35-SHIP-BEFORE-detail.png","36-SHIP-AFTER-detail.png","37-SHIP-side-by-side-detail.png")}[tag]
    save(cb, n[0]); save(ca, n[1])
    gap = np.zeros((cb.shape[0], 24, 3), cb.dtype)
    save(np.concatenate([cb, gap, ca], axis=1), n[2])
    d = np.abs(ca.astype(np.int32)-cb.astype(np.int32)).max(axis=2)
    print(f"  {tag}: changed {100*(d>0).mean():.2f}%  max |d| {d.max()}  mean |d| {d.mean():.2f}")
