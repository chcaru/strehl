"""Is the 0.85 gain caused by LINEAR interpolation in the correlation?
Test a cubic-spline variant against the linear one on the same synthetic data."""
import numpy as np, vc_ca
from scipy.ndimage import gaussian_filter, map_coordinates

N=2000; C=N/2.0
Y,X=np.mgrid[0:N,0:N].astype(np.float32); R=np.hypot(X-C,Y-C)
img0=gaussian_filter((np.sin(R/14.0)*0.5+0.5),1.1); img0=(img0*40000+8000).astype(np.uint16)
img=np.dstack([img0,img0,img0])
def plant(im,ch,eps):
    out=im.copy(); ys=C+(Y-C)/(1.0+eps); xs=C+(X-C)/(1.0+eps)
    out[:,:,ch]=np.clip(map_coordinates(im[:,:,ch].astype(np.float32),[ys,xs],order=3,mode="nearest"),0,65535).astype(np.uint16)
    return out

def shift_cubic(pa,pb):
    da=np.diff(pa.astype(np.float64)); db=np.diff(pb.astype(np.float64))
    if np.std(da)<1e-6 or np.std(db)<1e-6: return None
    da=(da-da.mean())/np.std(da); db=(db-db.mean())/np.std(db)
    t=np.arange(len(da),dtype=np.float64); best,bs=-2.0,None
    for s in vc_ca.LAGS:
        ai=map_coordinates(da,[t+s],order=3,mode="nearest")
        lo=int(np.ceil(max(0,-s))); hi=int(len(t)-np.ceil(max(0,s)))
        if hi-lo < len(t)-8: continue
        aa=ai[lo:hi]-ai[lo:hi].mean(); bb=db[lo:hi]-db[lo:hi].mean()
        den=np.linalg.norm(aa)*np.linalg.norm(bb)
        if den<=0: continue
        c=float(np.dot(aa,bb)/den)
        if c>best: best,bs=c,float(s)
    return None if (bs is None or best<0.90) else bs

S=vc_ca.sites(img[:,:,1],(C,C)); S=S[::max(1,len(S)//200)][:200]
def per_site(im,fn):
    out={}
    for i,(py,px,nx,ny,r,m,a) in enumerate(S):
        pg=vc_ca.profile(im[:,:,1],py,px,nx,ny); pr=vc_ca.profile(im[:,:,0],py,px,nx,ny)
        if pg is None or pr is None: continue
        s=fn(pr,pg)
        if s is None: continue
        out[i]=(s/a)/r*1e6
    return out

for label,fn in (("LINEAR (current)",vc_ca.shift),("CUBIC  (candidate)",shift_cubic)):
    base=per_site(img,fn); rows=[]
    for a_ in (-1000.,-500.,+500.,+1000.):
        p=per_site(plant(img,0,a_*1e-6),fn); common=sorted(set(base)&set(p))
        rows.append((a_,np.median([p[i]-base[i] for i in common])))
    A=np.array([r[0] for r in rows]); D=np.array([r[1] for r in rows])
    sn=np.polyfit(A[A<0],D[A<0],1)[0]; sp=np.polyfit(A[A>0],D[A>0],1)[0]
    print("%-20s  slope NEG %.3f  POS %.3f  asym %.3f   deltas %s" %
          (label,sn,sp,sp/sn,"  ".join("%+.0f" % d for d in D)))
