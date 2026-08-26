"""Does the 'presentation' grade do what its note claims?

The note claims three operations: a percentile black point, a filmic
S-curve, and a saturation lift. My first probe measured only p99-p1 of
luma, which is blind to the S-curve (it moves MIDTONE slope, not the
endpoints) and totally blind to saturation. Three statistics, one per
claimed operation, each shown able to fire on a plant before use.
"""
import os, glob
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

def measure(a):
    a = a.astype(np.float64)
    y = 0.2126*a[...,0] + 0.7152*a[...,1] + 0.0722*a[...,2]
    blk = np.percentile(y, 1)                       # black point
    mid = np.percentile(y,75) - np.percentile(y,25) # midtone slope proxy
    mx = a.max(axis=2); mn = a.min(axis=2)
    sat = np.where(mx > 8, (mx-mn)/np.maximum(mx,1e-9), np.nan)
    return blk, mid, np.nanmean(sat)

def commission():
    rng = np.random.default_rng(7)
    base = (rng.random((256,256,3))*0.5 + 0.25)
    b0,m0,s0 = measure((base*255).astype(np.uint8))
    # plant 1: raise black point
    p1 = np.clip((base-0.10)/0.90, 0, 1)
    b1,m1,s1 = measure((p1*255).astype(np.uint8))
    # plant 2: S-curve (increases midtone slope)
    p2 = np.clip(base + 0.6*(base-0.5)*(1-np.abs(2*base-1)), 0, 1)
    b2,m2,s2 = measure((p2*255).astype(np.uint8))
    # plant 3: saturation lift only
    g = base.mean(axis=2, keepdims=True)
    p3 = np.clip(g + (base-g)*1.8, 0, 1)
    b3,m3,s3 = measure((p3*255).astype(np.uint8))
    print("== commissioning ==")
    print(f"  black-point plant : blk {b0:6.2f} -> {b1:6.2f}   {'OK' if b1 < b0-3 else 'FAIL'}")
    print(f"  S-curve plant     : mid {m0:6.2f} -> {m2:6.2f}   {'OK' if m2 > m0*1.10 else 'FAIL'}")
    print(f"  saturation plant  : sat {s0:6.4f} -> {s3:6.4f}   {'OK' if s3 > s0*1.20 else 'FAIL'}")
    print(f"  cross-talk: S-curve moved sat {s0:.4f}->{s2:.4f}, sat plant moved mid {m0:.2f}->{m3:.2f}")
    ok = (b1 < b0-3) and (m2 > m0*1.10) and (s3 > s0*1.20)
    if not ok:
        print("COMMISSIONING FAILED"); raise SystemExit(2)
    print("  all three axes fire on their own plant\n")

commission()
base = r"C:\dev\strehl-out\SHIP-V2-ICC"
fa = {os.path.basename(p).split("--")[0]: p for p in glob.glob(os.path.join(base,"_faithful","*.jpg"))}
pr = {os.path.basename(p).split("--")[0]: p for p in glob.glob(os.path.join(base,"_presentation","*.jpg"))}
keys = sorted(set(fa)&set(pr))
print(f"{'subject':<36} {'blk f':>6} {'blk p':>6} | {'mid f':>6} {'mid p':>6} {'x':>5} | {'sat f':>6} {'sat p':>6} {'x':>5}")
print("-"*100)
db=[]; dmm=[]; ds=[]
for k in keys:
    bf,mf,sf = measure(np.asarray(Image.open(fa[k]).convert("RGB")))
    bp,mp,sp = measure(np.asarray(Image.open(pr[k]).convert("RGB")))
    db.append(bp-bf); dmm.append(mp/mf if mf>0 else np.nan); ds.append(sp/sf if sf>0 else np.nan)
    print(f"{k[:35]:<36} {bf:6.1f} {bp:6.1f} | {mf:6.1f} {mp:6.1f} {dmm[-1]:5.2f} | {sf:6.4f} {sp:6.4f} {ds[-1]:5.2f}")
print("-"*100)
print(f"black point : median {np.median(db):+.1f} of 255")
print(f"midtone     : median {np.nanmedian(dmm):.3f}x")
print(f"saturation  : median {np.nanmedian(ds):.3f}x")
