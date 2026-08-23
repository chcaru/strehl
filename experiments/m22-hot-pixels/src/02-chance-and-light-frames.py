import numpy as np, rawpy, glob, os, exifread, json
from scipy.ndimage import median_filter
S=r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files"
BLACK=512
count=np.load(os.path.join(S,"hotcount.npy")); meta=json.load(open(os.path.join(S,"darkmeta.json")))
tot=sum(m[4] for m in meta); NG=len(meta); N=count.size
p=tot/(N*NG)
print("=== R11 step 2: are the recurring flags real, and do they matter in LIGHT frames? ===\n")
print(f"  per-group flag rate p = {p:.6f}; under INDEPENDENCE the recurrence counts would be Binomial({NG},p)")
from math import comb
print(f"  {'k groups':>9} {'observed':>9} {'expected if chance':>20}")
for k in (1,2,3,6,11):
    e=comb(NG,k)*p**k*(1-p)**(NG-k)*N
    print(f"  {k:>9} {(count==k).sum():>9} {e:>20.3g}")
print("\n  Recurrence is therefore NOT chance beyond k=2. The >=6 set is the defensible hot-pixel map.")
stable = count>=6
print(f"  STABLE SET: {stable.sum()} px = {stable.mean()*100:.4f}% of the sensor "
      f"({stable.sum()/ (N/1e6):.0f} per Mpx)\n")

# --- how BIG is the defect, in the darks? ---
d=sorted(glob.glob(os.path.join(r"D:\macro-dark-frames","*MSDCF")))
for dd in (d[0], d[-1]):
    fs=sorted(glob.glob(os.path.join(dd,"*.ARW")))[2:]
    acc=None
    for f in fs:
        with rawpy.imread(f) as rr: a=rr.raw_image_visible.astype(np.float32)
        acc=a if acc is None else acc+a
    m=acc/len(fs)-BLACK
    exc=np.zeros_like(m)
    for (dy,dx) in ((0,0),(0,1),(1,0),(1,1)):
        pl=m[dy::2,dx::2]; exc[dy::2,dx::2]=pl-median_filter(pl,3)
    iso=meta[d.index(dd)][1]
    q=np.percentile(exc[stable],[50,90,99,100])
    print(f"  dark excess of the stable set at ISO {iso:>5}: median {q[0]:6.2f}  p90 {q[1]:6.2f} "
          f" p99 {q[2]:7.2f}  max {q[3]:8.1f} DN   (frame sigma_exc {meta[d.index(dd)][5]:.3f})")

# --- THE TEST THAT MATTERS: do they misbehave in real LIGHT frames? ---
print("\n  --- light-frame test on 109MSDCF (real capture) ---")
fs=sorted(glob.glob(os.path.join(r"C:\dev\macro\test\109MSDCF","*.ARW")))
with open(fs[0],'rb') as fh: t=exifread.process_file(fh,details=False)
print(f"  capture: ISO {t.get('EXIF ISOSpeedRatings')}  exposure {t.get('EXIF ExposureTime')}  "
      f"(darks were 1/100 s -- dark current scales with TIME)")
rng=np.random.default_rng(7)
ctrl=np.zeros_like(stable); idx=rng.choice(N, stable.sum(), replace=False)
ctrl.ravel()[idx]=True; ctrl &= ~stable
hs=[];cs=[]
for f in fs[:6]:
    with rawpy.imread(f) as rr: a=rr.raw_image_visible.astype(np.float32)-BLACK
    exc=np.zeros_like(a)
    for (dy,dx) in ((0,0),(0,1),(1,0),(1,1)):
        pl=a[dy::2,dx::2]; exc[dy::2,dx::2]=pl-median_filter(pl,3)
    hs.append(exc[stable]); cs.append(exc[ctrl])
hs=np.concatenate(hs); cs=np.concatenate(cs)
print(f"  residual vs same-colour local median, over 6 real frames:")
print(f"     STABLE-HOT pixels: mean {hs.mean():+8.3f}  median {np.median(hs):+8.3f}  p99 {np.percentile(hs,99):+9.2f} DN")
print(f"     random CONTROL  : mean {cs.mean():+8.3f}  median {np.median(cs):+8.3f}  p99 {np.percentile(cs,99):+9.2f} DN")
print(f"     EXCESS attributable to the map: mean {hs.mean()-cs.mean():+.3f} DN, "
      f"median {np.median(hs)-np.median(cs):+.3f} DN")
for thr in (20,50,100):
    print(f"     |residual| > {thr:>3} DN:  hot {np.mean(np.abs(hs)>thr)*100:6.3f}%   "
          f"control {np.mean(np.abs(cs)>thr)*100:6.3f}%   ratio {np.mean(np.abs(hs)>thr)/max(np.mean(np.abs(cs)>thr),1e-12):7.2f}x")
