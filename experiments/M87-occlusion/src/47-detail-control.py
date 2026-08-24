import numpy as np, pathlib, json, tifffile
from PIL import Image
S = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")
b = tifffile.imread(S/"30-SHIP-BEFORE-default.tif"); a = tifffile.imread(S/"31-SHIP-AFTER-fixhalo.tif")
d = np.abs(a.astype(np.int32)-b.astype(np.int32)).max(axis=2)
g = b[:,:,1].astype(np.float32)
gy,gx = np.gradient(g); mg = np.hypot(gx,gy)
B = 100
H,W = (d.shape[0]//B)*B, (d.shape[1]//B)*B
dm = d[:H,:W].reshape(H//B,B,W//B,B).max(axis=(1,3))     # per-block max change
gm = mg[:H,:W].reshape(H//B,B,W//B,B).mean(axis=(1,3))   # per-block detail
hb, wb = 6, 8   # 600 x 800 window
best=None
for y in range(dm.shape[0]-hb+1):
    for x in range(dm.shape[1]-wb+1):
        if dm[y:y+hb, x:x+wb].max() != 0: continue
        s = gm[y:y+hb, x:x+wb].mean()
        if best is None or s > best[0]: best=(s,y,x)
assert best is not None, "no completely untouched 600x800 window exists"
s,y,x = best
y0,x0 = y*B, x*B; y1,x1 = y0+hb*B, x0+wb*B
cb, ca = b[y0:y1,x0:x1], a[y0:y1,x0:x1]
dc = np.abs(ca.astype(np.int32)-cb.astype(np.int32))
gg = cb[:,:,1].astype(np.float32); ggy,ggx = np.gradient(gg)
halo = mg[866:1566,1050:2150].mean()
print(f"DETAIL CONTROL y{y0}..{y1} x{x0}..{x1}")
print(f"  max |delta|      : {dc.max()} DN   (changed pixels: {100*(dc.max(axis=2)>0).mean():.4f}%)")
print(f"  mean |grad|      : {np.hypot(ggx,ggy).mean():.1f}   vs {halo:.1f} in the halo crop")
print(f"  sd / mean level  : {gg.std():.0f} / {gg.mean():.0f}")
def save(arr,n): Image.fromarray((arr.astype(np.float32)/65535*255).clip(0,255).astype(np.uint8)).save(S/n)
save(cb,"35-SHIP-BEFORE-detail.png"); save(ca,"36-SHIP-AFTER-detail.png")
gap=np.zeros((cb.shape[0],24,3),cb.dtype); save(np.concatenate([cb,gap,ca],1),"37-SHIP-side-by-side-detail.png")
json.dump({"roi":[y0,y1,x0,x1],"max_delta":int(dc.max()),
           "changed_frac":float((dc.max(axis=2)>0).mean()),
           "mean_grad_detail":float(np.hypot(ggx,ggy).mean()),
           "mean_grad_halo_crop":float(halo),"sd":float(gg.std()),"mean":float(gg.mean())},
          open("data/44-detail-control.json","w"), indent=1)
