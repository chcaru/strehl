"""(a) Fine map of the mote region on the flat -- resolves the '25-quad offset'.
   (b) Per-subject reading at the dust site vs controls in the masters --
       tests whether -13.28% on one subject is dust or subject detail."""
import numpy as np, cv2, os, glob, tifffile
D=r"C:\dev\strehl-out\V-REVIEW\dust"
A=np.load(os.path.join(D,"flat_rampA.npy")).astype(np.float32)
B=np.load(os.path.join(D,"flat_rampB.npy")).astype(np.float32)
h,w=A.shape

def qdetrend(F,x0,x1,y0,y1,pad=70):
    ys,ye=max(0,y0-pad),min(h,y1+pad); xs,xe=max(0,x0-pad),min(w,x1+pad)
    sub=F[ys:ye,xs:xe].astype(np.float64)
    gy,gx=np.mgrid[ys:ye,xs:xe].astype(np.float64)
    gy-=(y0+y1)/2.0; gx-=(x0+x1)/2.0
    inner=(gx>=x0-(x0+x1)/2.0)&(gx<=x1-(x0+x1)/2.0)&(gy>=y0-(y0+y1)/2.0)&(gy<=y1-(y0+y1)/2.0)
    fit=~inner
    X=lambda a,b: np.stack([np.ones(a.size),a.ravel(),b.ravel(),a.ravel()**2,b.ravel()**2,(a*b).ravel()],1)
    coef,*_=np.linalg.lstsq(X(gx[fit],gy[fit]),sub[fit],rcond=None)
    m=(X(gx,gy)@coef).reshape(sub.shape)
    r=(sub/np.maximum(m,1e-6)-1.0)
    return r[(y0-ys):(y1-ys),(x0-xs):(x1-xs)]

print("=== flat, quadratic-detrended, 5x5 blocks, percent (negative = darker) ===")
x0,x1,y0,y1=3390,3470,2255,2335
for tag,F in (("rampA",A),("rampB",B)):
    r=qdetrend(cv2.GaussianBlur(F,(0,0),1.5),x0,x1,y0,y1)*100
    bh,bw=r.shape[0]//5,r.shape[1]//5
    red=r[:bh*5,:bw*5].reshape(bh,5,bw,5).mean(axis=(1,3))
    print("\n%s  (columns = binned x, rows = binned y)" % tag)
    print("      "+"".join("%7d"%(x0+5*j+2) for j in range(bw)))
    for i in range(bh):
        print("%5d "%(y0+5*i+2)+"".join("%7.2f"%red[i,j] for j in range(bw)))
    ij=np.unravel_index(np.argmin(r),r.shape)
    print("   deepest %.2f%% at binned (%d,%d) = sensor (%d,%d)"
          % (r.min(), x0+ij[1], y0+ij[0], 2*(x0+ij[1]), 2*(y0+ij[0])))

print("\n\n=== masters: per-subject reading at the dust site and at controls ===")
P=60; n=2*P+1
gy,gx=np.mgrid[0:n,0:n].astype(np.float64); gy-=P; gx-=P
rr=np.sqrt(gy**2+gx**2); FIT=rr>18
XF=np.stack([np.ones(FIT.sum()),gx[FIT],gy[FIT],gx[FIT]**2,gy[FIT]**2,(gx*gy)[FIT]],1)
XA=np.stack([np.ones(n*n),gx.ravel(),gy.ravel(),gx.ravel()**2,gy.ravel()**2,(gx*gy).ravel()],1)
def depth(pt):
    if pt.shape!=(n,n) or np.median(pt)<800: return None
    coef,*_=np.linalg.lstsq(XF,pt[FIT].astype(np.float64),rcond=None)
    m=(XA@coef).reshape(pt.shape)
    if m.min()<0.25*np.median(m): return None
    return float(1.0-pt[rr<=6].min()/np.median(m[rr<=6]))
SITES={"DUST":(6874,4580),"c1":(6874,3000),"c2":(5200,4580),"c3":(3500,2344),"c4":(6300,4200),"c5":(2000,4000)}
print("%-34s %9s %9s %9s %9s %9s %9s  %s" % ("subject","DUST","c1","c2","c3","c4","c5","dust worst?"))
nworst=0; tot=0
for p in sorted(glob.glob(r"C:\dev\strehl-out\acceptance\SHIP-V4\*--SHIP-V4.tiff")):
    s=os.path.basename(p).replace("--SHIP-V4.tiff","")
    a=tifffile.imread(p).astype(np.float32)
    L=0.2126*a[:,:,0]+0.7152*a[:,:,1]+0.0722*a[:,:,2]
    vals={k:depth(L[cy-P:cy+P+1,cx-P:cx+P+1]) for k,(cx,cy) in SITES.items()}
    del a,L
    ok=[v for v in vals.values() if v is not None]
    if vals["DUST"] is None or len(ok)<4: continue
    tot+=1
    worst = vals["DUST"] >= max(v for k,v in vals.items() if v is not None and k!="DUST")
    nworst += 1 if worst else 0
    print("%-34s %8s %8s %8s %8s %8s %8s  %s" % (s,
        *[("%.2f%%"%(100*vals[k])) if vals[k] is not None else "  -  " for k in ["DUST","c1","c2","c3","c4","c5"]],
        "YES" if worst else ""))
print("\ndust site was the deepest of the six in %d of %d subjects (chance would be about %.1f)"
      % (nworst, tot, tot/6.0))
