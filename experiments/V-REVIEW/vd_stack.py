"""Residual stacking, v2.  v1 defect: patches in near-black master regions gave
a fitted model close to zero, and dividing by it produced residual noise of
1.7e9 percent, which made every significance read -0.00 sd.  Guarded here:
a patch is USED only if its level and its fitted model stay well clear of zero.
Partition is printed and sums.  Combination is the median, not the mean.
"""
import numpy as np, cv2, os, glob, tifffile
SHIP=r"C:\dev\strehl-out\acceptance\SHIP-V4"
P=60; FLOOR=800.0
SITES={"DUST(6874,4580)":(6874,4580),"ctrl-A(6874,3000)":(6874,3000),
       "ctrl-B(5200,4580)":(5200,4580),"ctrl-C(3500,2344)":(3500,2344),
       "ctrl-D(6300,4200)":(6300,4200),"ctrl-F(2000,4000)":(2000,4000)}
n=2*P+1; gy,gx=np.mgrid[0:n,0:n].astype(np.float64); gy-=P; gx-=P
rr=np.sqrt(gy**2+gx**2); FIT=rr>18
XF=np.stack([np.ones(FIT.sum()),gx[FIT],gy[FIT],gx[FIT]**2,gy[FIT]**2,(gx*gy)[FIT]],1)
XA=np.stack([np.ones(n*n),gx.ravel(),gy.ravel(),gx.ravel()**2,gy.ravel()**2,(gx*gy).ravel()],1)

def detrend(patch):
    if np.median(patch)<FLOOR: return None,"too dark"
    coef,*_=np.linalg.lstsq(XF,patch[FIT].astype(np.float64),rcond=None)
    m=(XA@coef).reshape(patch.shape)
    if m.min() < 0.25*np.median(m): return None,"model near zero"
    return patch/m-1.0, None

paths=sorted(glob.glob(os.path.join(SHIP,"*--SHIP-V4.tiff")))
acc={k:[] for k in SITES}; rej={k:0 for k in SITES}; plant=[]
for p in paths:
    a=tifffile.imread(p).astype(np.float32)
    L=0.2126*a[:,:,0]+0.7152*a[:,:,1]+0.0722*a[:,:,2]
    for name,(cx,cy) in SITES.items():
        pt=L[cy-P:cy+P+1,cx-P:cx+P+1]
        if pt.shape!=(n,n): rej[name]+=1; continue
        d,why=detrend(pt)
        if d is None: rej[name]+=1
        else: acc[name].append(d)
    cx,cy=SITES["ctrl-A(6874,3000)"]
    pt=L[cy-P:cy+P+1,cx-P:cx+P+1]
    if pt.shape==(n,n):
        d,_=detrend((pt*(1.0-0.03*np.exp(-((gx**2+gy**2)/(2*5.0**2))))).astype(np.float32))
        if d is not None: plant.append(d)
    del a,L

def score(st):
    S=np.median(np.stack(st),0)
    c=float(S[rr<=6].min())
    ring=S[rr>25]; sd=float(1.4826*np.median(np.abs(ring-np.median(ring))))
    return c,sd,(c/sd if sd>0 else float('nan')),len(st)

print("%-20s %6s %6s %11s %10s %12s %s" % ("site","used","rej","centre dip","noise sd","significance","verdict"))
for name in SITES:
    c,sd,z,N=score(acc[name])
    print("%-20s %6d %6d %10.3f%% %9.3f%% %9.2f sd %s" % (name,N,rej[name],100*c,100*sd,z,
          "DIP" if z<-5 else "none"))
    assert N+rej[name]==len(paths)
print("\npartition check: used + rejected == %d masters for every site  OK" % len(paths))

c0,_,_,_=score(acc["ctrl-A(6874,3000)"])
c,sd,z,N=score(plant)
print("\n== COMMISSION: 3.0%% dip planted into the SAME patches at ctrl-A ==")
print("   unplanted %.3f%%   planted %.3f%%   shift %+.3f pts   significance %.2f sd   %s"
      % (100*c0,100*c,100*(c-c0),z,"RECOVERED" if z<-5 else "NOT RECOVERED"))
print("\n== detection floor: how deep must a fixed dip be to show here? ==")
for dep in (0.005,0.01,0.02,0.03):
    st=[]
    for pt0 in acc["ctrl-A(6874,3000)"]:
        st.append((1.0+pt0)*(1.0-dep*np.exp(-((gx**2+gy**2)/(2*5.0**2))))-1.0)
    c,sd,z,_=score(st)
    print("   plant %5.2f%% -> centre %7.3f%%  shift %+6.3f pts  %6.2f sd  %s"
          % (100*dep,100*c,100*(c-c0),z,"detected" if z<-5 else "below floor"))
