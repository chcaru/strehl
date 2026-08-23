import numpy as np, rawpy, glob, os, exifread
from scipy.ndimage import median_filter
S=r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files"
BLACK=512; count=np.load(os.path.join(S,"hotcount.npy"))
print("=== R11 step 3: exposure mismatch, the severe tail, and dead pixels ===\n")
print("  Exposure time of every real stack vs the darks (dark current scales with TIME):")
for n,p in (("109MSDCF",r"C:\dev\macro\test\109MSDCF"),("119MSDCF",r"C:\dev\macro\test\119MSDCF"),
            ("coffee-bean",r"C:\dev\macro\test\coffee-bean"),("112MSDCF",r"D:\personal\macro\112MSDCF"),
            ("113MSDCF",r"D:\personal\macro\113MSDCF"),("coffee-bubbles",r"D:\personal\macro\coffee-bubbles")):
    f=sorted(glob.glob(os.path.join(p,"*.ARW")))[0]
    with open(f,'rb') as fh: t=exifread.process_file(fh,details=False)
    e=t.get('EXIF ExposureTime'); i=t.get('EXIF ISOSpeedRatings')
    try: ev=eval(str(e).replace('/','/'))
    except Exception: ev=float('nan')
    print(f"    {n:>14}  ISO {str(i):>5}  exposure {str(e):>8} = {ev:7.3f} s   -> {ev*100:6.1f}x the darks' 1/100 s")

# severe tail: rank the ALWAYS-hot pixels by their dark excess, test the worst in light frames
d=sorted(glob.glob(os.path.join(r"D:\macro-dark-frames","*MSDCF")))
fs=sorted(glob.glob(os.path.join(d[3],"*.ARW")))[2:]   # 121MSDCF ISO 1600
acc=None
for f in fs:
    with rawpy.imread(f) as rr: a=rr.raw_image_visible.astype(np.float32)
    acc=a if acc is None else acc+a
m=acc/len(fs)-BLACK
exc=np.zeros_like(m)
for (dy,dx) in ((0,0),(0,1),(1,0),(1,1)):
    pl=m[dy::2,dx::2]; exc[dy::2,dx::2]=pl-median_filter(pl,3)
always=count>=11
print(f"\n  DEAD/COLD pixels (excess far BELOW local median, ISO1600 dark): "
      f"{(exc < -8*1.4826*np.median(np.abs(exc-np.median(exc)))).sum()} px flagged -- untested for recurrence")
for label,sel in (("always-hot (11/11)",always),("severe: always-hot AND >100 DN dark excess", always&(exc>100))):
    print(f"\n  --- {label}: {sel.sum()} px ---")
    if sel.sum()<10: print("    too few to test"); continue
    rng=np.random.default_rng(11); ctrl=np.zeros_like(sel)
    ctrl.ravel()[rng.choice(sel.size, sel.sum()*20, replace=False)]=True; ctrl&=~sel
    hs=[];cs=[]
    for f in sorted(glob.glob(os.path.join(r"C:\dev\macro\test\109MSDCF","*.ARW")))[:6]:
        with rawpy.imread(f) as rr: a=rr.raw_image_visible.astype(np.float32)-BLACK
        e2=np.zeros_like(a)
        for (dy,dx) in ((0,0),(0,1),(1,0),(1,1)):
            pl=a[dy::2,dx::2]; e2[dy::2,dx::2]=pl-median_filter(pl,3)
        hs.append(e2[sel]); cs.append(e2[ctrl])
    hs=np.concatenate(hs); cs=np.concatenate(cs)
    print(f"    light-frame residual: hot mean {hs.mean():+8.2f} median {np.median(hs):+7.1f} p90 {np.percentile(hs,90):+8.1f} DN")
    print(f"                       control mean {cs.mean():+8.2f} median {np.median(cs):+7.1f} p90 {np.percentile(cs,90):+8.1f} DN")
    print(f"    EXCESS: mean {hs.mean()-cs.mean():+.2f} DN   vs the ISO160 read-noise floor of ~5.2-29.8 DN/px")
