import numpy as np, pathlib, json, tifffile
from PIL import Image
S = pathlib.Path(r"C:\dev\strehl-out\M87-before-after")
b = tifffile.imread(S/"30-SHIP-BEFORE-default.tif")
a = tifffile.imread(S/"31-SHIP-AFTER-fixhalo.tif")
print("dtype", b.dtype, "shape", b.shape, "max", b.max())
d = np.abs(a.astype(np.int32)-b.astype(np.int32)).max(axis=2)
print(f"changed {100*(d>0).mean():.3f}%  max |d| {d.max()} / 65535 = {100*d.max()/65535:.1f}%")
# locate the strongest correction to aim the owner crop
dd = d[::8,::8].astype(np.float32)
k = 16
box = np.add.reduceat(np.add.reduceat(dd, np.arange(0,dd.shape[0],k), 0), np.arange(0,dd.shape[1],k), 1)
iy, ix = np.unravel_index(np.argmax(box), box.shape)
cy, cx = int(iy*k*8 + k*4), int(ix*k*8 + k*4)
print("strongest correction near y,x =", cy, cx)
def save(arr, name):
    Image.fromarray((arr.astype(np.float32)/65535*255).clip(0,255).astype(np.uint8)).save(S/name)
def cut(y,x,hh,ww):
    y0=max(0,min(y-hh//2, b.shape[0]-hh)); x0=max(0,min(x-ww//2, b.shape[1]-ww))
    return y0,y0+hh,x0,x0+ww
out={}
y0,y1,x0,x1 = cut(cy,cx,700,1100)
cb,ca = b[y0:y1,x0:x1], a[y0:y1,x0:x1]
save(cb,"32-SHIP-BEFORE-halo.png"); save(ca,"33-SHIP-AFTER-halo.png")
gap = np.zeros((cb.shape[0],24,3), cb.dtype)
save(np.concatenate([cb,gap,ca],1), "34-SHIP-side-by-side-halo.png")
dc = np.abs(ca.astype(np.int32)-cb.astype(np.int32)).max(axis=2)
print(f"HALO crop y{y0}..{y1} x{x0}..{x1}: changed {100*(dc>0).mean():.2f}% max|d| {dc.max()}")
out["halo_crop"]=[y0,y1,x0,x1,float((dc>0).mean()),int(dc.max())]
# fine-detail control: the highest-gradient window that the fix left alone
g = b[:,:,1].astype(np.float32)
gy,gx = np.gradient(g[::4,::4]); mg = np.hypot(gx,gy)
untouched = (d[::4,::4]==0).astype(np.float32)
kk=32
gb = np.add.reduceat(np.add.reduceat(mg*untouched, np.arange(0,mg.shape[0],kk),0), np.arange(0,mg.shape[1],kk),1)
jy,jx = np.unravel_index(np.argmax(gb), gb.shape)
dy,dx = int(jy*kk*4+kk*2), int(jx*kk*4+kk*2)
y0,y1,x0,x1 = cut(dy,dx,600,800)
cb,ca = b[y0:y1,x0:x1], a[y0:y1,x0:x1]
save(cb,"35-SHIP-BEFORE-detail.png"); save(ca,"36-SHIP-AFTER-detail.png")
dc = np.abs(ca.astype(np.int32)-cb.astype(np.int32)).max(axis=2)
gg=cb[:,:,1].astype(np.float32); ggy,ggx=np.gradient(gg)
print(f"DETAIL crop y{y0}..{y1} x{x0}..{x1}: changed {100*(dc>0).mean():.2f}% max|d| {dc.max()} "
      f"mean|grad| {np.hypot(ggx,ggy).mean():.1f} sd {gg.std():.0f} mean {gg.mean():.0f}")
out["detail_crop"]=[y0,y1,x0,x1,float((dc>0).mean()),int(dc.max()),
                    float(np.hypot(ggx,ggy).mean()), float(gg.std())]
out["frame_changed_frac"]=float((d>0).mean()); out["frame_max_delta"]=int(d.max())
json.dump(out, open("data/43-ship-crops.json","w"), indent=1)
