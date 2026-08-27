"""Why the single-frame reduction factor is invalid: the high-pass estimator counts SCENE DETAIL as noise.
Two estimators, same images, same tiles. half-diff cancels scene; high-pass cannot."""
import numpy as np, tifffile
from scipy.ndimage import uniform_filter
CEN = np.load(r"C:\dev\strehl-out\V-NOISE\census.npz", allow_pickle=True)
CELLS, FLAT, T = CEN["cells"], CEN["flat"], int(CEN["T"])
TILES = [tuple(CELLS[i]) for i in FLAT]; R = 3; CH = ("Y","R-Y","B-Y")

def raw_pad(p):
    a = tifffile.imread(p)
    if a.ndim==3 and a.shape[2]>=4: a=a[:,:,:3]
    o=np.empty((len(TILES),T+2*R,T+2*R,3),a.dtype)
    for i,(y,x) in enumerate(TILES): o[i]=a[y-R:y+T+R,x-R:x+T+R,:3]
    del a; return o
def opp(u):
    f=u.astype(np.float64)/(255.0 if u.dtype==np.uint8 else 65535.0)
    Y=0.2126*f[...,0]+0.7152*f[...,1]+0.0722*f[...,2]
    return np.stack([Y,f[...,0]-Y,f[...,2]-Y],-1)
def halfdiff(A,B):
    c=slice(R,R+T); m=A[:,c,c,0].mean(axis=(1,2)); n=A.shape[0]
    best=np.full(n,np.inf); bd=np.zeros((n,2),int)
    for dy in range(-R,R+1):
        for dx in range(-R,R+1):
            d=A[:,c,c,0]-B[:,R+dy:R+dy+T,R+dx:R+dx+T,0]
            v=(d**2).mean(axis=(1,2))-d.mean(axis=(1,2))**2
            w=v<best; best[w]=v[w]; bd[w]=(dy,dx)
    out=np.empty((n,3))
    for i in range(n):
        dy,dx=bd[i]; d=A[i,c,c,:]-B[i,R+dy:R+dy+T,R+dx:R+dx+T,:]
        v=(d**2).mean(axis=(0,1))-d.mean(axis=(0,1))**2
        out[i]=np.sqrt(0.5*v)/m[i]
    return out
def hp(X):
    c=slice(R,R+T); m=X[:,c,c,0].mean(axis=(1,2)); n=X.shape[0]; out=np.empty((n,3))
    for i in range(n):
        for ch in range(3):
            t=X[i,c,c,ch]; out[i,ch]=(t-uniform_filter(t,9,mode="reflect")).std()
        out[i]/=m[i]
    return out

arms={"strehl":(r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff", r"C:\dev\strehl-out\V-H2H2\lin\113-B-g1.tiff"),
      "enfuse":(r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-A.tif", r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-B.tif"),
      "focus-stack":(r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-A.tif", r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-B.tif")}
print("="*92)
print("MECHANISM: high-pass vs scene-cancelled half-difference, SAME image, SAME tiles")
print("="*92)
print("\n  sigma x1000.  If the high-pass estimator measured noise, the two would agree.\n")
print("  %-13s %-8s %10s %10s %10s" % ("arm","estim","Y","R-Y","B-Y"))
res={}
for k,(a,b) in arms.items():
    A,B=raw_pad(a),raw_pad(b)
    h=halfdiff(opp(A),opp(B)); g=hp(opp(A)); del B
    res[k]=(h,g)
    print("  %-13s %-8s %10.4f %10.4f %10.4f" % (k,"half-diff",*[1000*np.median(h[:,i]) for i in range(3)]))
    print("  %-13s %-8s %10.4f %10.4f %10.4f" % ("","high-pass",*[1000*np.median(g[:,i]) for i in range(3)]))
    print("  %-13s %-8s %10.2fx %9.2fx %9.2fx" % ("","INFLATION",*[np.median(g[:,i])/np.median(h[:,i]) for i in range(3)]))
    del A
print("\n  INFLATION = how much SCENE CONTENT the high-pass estimator mistakes for noise.")
print("  It is largest on the sharpest arm, which is the signature of detail, not of noise.")
print("\n  CONSEQUENCE: the input frame carries little in-focus detail in these tiles while every")
print("  merge carries a lot, so sigma_in/sigma_out on the high-pass estimator measures DETAIL GAINED,")
print("  not NOISE REMOVED. The Part 2 'reduction factors' are WITHDRAWN.")
