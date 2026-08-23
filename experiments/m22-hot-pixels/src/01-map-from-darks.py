import numpy as np, rawpy, glob, os, exifread, json
from scipy.ndimage import median_filter
ROOT=r"D:\macro-dark-frames"; BLACK=512
dirs=sorted(glob.glob(os.path.join(ROOT,"*MSDCF")))
def iso_exp(f):
    with open(f,'rb') as fh: t=exifread.process_file(fh, details=False)
    return (str(t.get('EXIF ISOSpeedRatings','?')), str(t.get('EXIF ExposureTime','?')))
print("=== R11 step 1: hot-pixel map from the 242 delivered darks ===\n")
count=None; per=[]
for d in dirs:
    fs=sorted(glob.glob(os.path.join(d,"*.ARW")))[2:]      # owner: first 2 are stabilisation
    iso,exp=iso_exp(fs[0])
    acc=None
    for f in fs:
        with rawpy.imread(f) as rr:
            a=rr.raw_image_visible.astype(np.float32)
        acc = a if acc is None else acc+a
    m=acc/len(fs)-BLACK
    hot=np.zeros(m.shape,bool); exc_all=[]
    for (dy,dx) in ((0,0),(0,1),(1,0),(1,1)):              # four CFA planes, same-colour neighbours
        p=m[dy::2,dx::2]
        exc=p-median_filter(p,3)
        s=1.4826*np.median(np.abs(exc-np.median(exc)))     # robust sigma of the excess
        hot[dy::2,dx::2]=exc>8*s
        exc_all.append(s)
    if count is None: count=np.zeros(m.shape,np.uint8)
    count+=hot
    per.append((os.path.basename(d),iso,exp,len(fs),int(hot.sum()),float(np.mean(exc_all)),float(m.mean())))
    print(f"  {os.path.basename(d)}  ISO {iso:>6}  exp {exp:>8}  n={len(fs)}  "
          f"hot(8sigma)={hot.sum():>7}  sigma_exc={np.mean(exc_all):6.3f} DN  meandark={m.mean():+7.3f} DN")
np.save(os.path.join(r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files","hotcount.npy"),count)
N=count.size
print(f"\n  sensor {count.shape} = {N/1e6:.1f} Mpx, {len(dirs)} ISO groups")
print(f"  flagged in >=1 group : {(count>=1).sum():>8}  ({(count>=1).mean()*100:.4f}%)")
print(f"  flagged in >=6 groups: {(count>=6).sum():>8}  ({(count>=6).mean()*100:.4f}%)")
print(f"  flagged in ALL {len(dirs)}    : {(count==len(dirs)).sum():>8}  ({(count==len(dirs)).mean()*100:.4f}%)")
print("\n  STABILITY: a real hot pixel is a property of the silicon and must recur at every ISO.")
print("  Distribution of how many groups flagged each ever-flagged pixel:")
h=np.bincount(count[count>=1].ravel(),minlength=len(dirs)+1)
for k in range(1,len(dirs)+1): print(f"     in exactly {k:>2} groups: {h[k]:>8}")
json.dump(per,open(os.path.join(r"C:\Users\chris\.copilot\session-state\7a7e4522-18b0-4052-91c4-fc39cb2db6f2\files","darkmeta.json"),"w"),indent=1)
