"""Price the confound: could per-subject registration jitter hide a real mote?
Plant a 3% dip at a RANDOM per-master offset and find the jitter at which the
stack stops seeing it. This commissions the term the null depends on."""
import numpy as np, os, glob, tifffile
SHIP=r"C:\dev\strehl-out\acceptance\SHIP-V4"
P=60; FLOOR=800.0
n=2*P+1; gy,gx=np.mgrid[0:n,0:n].astype(np.float64); gy-=P; gx-=P
rr=np.sqrt(gy**2+gx**2); FIT=rr>18
XF=np.stack([np.ones(FIT.sum()),gx[FIT],gy[FIT],gx[FIT]**2,gy[FIT]**2,(gx*gy)[FIT]],1)
XA=np.stack([np.ones(n*n),gx.ravel(),gy.ravel(),gx.ravel()**2,gy.ravel()**2,(gx*gy).ravel()],1)
def detrend(pt):
    if np.median(pt)<FLOOR: return None
    coef,*_=np.linalg.lstsq(XF,pt[FIT].astype(np.float64),rcond=None)
    m=(XA@coef).reshape(pt.shape)
    if m.min()<0.25*np.median(m): return None
    return pt/m-1.0
def score(st):
    S=np.median(np.stack(st),0); c=float(S[rr<=6].min())
    ring=S[rr>25]; sd=float(1.4826*np.median(np.abs(ring-np.median(ring))))
    return c,sd,(c/sd if sd>0 else np.nan)

raw={}
for p in sorted(glob.glob(os.path.join(SHIP,"*--SHIP-V4.tiff"))):
    a=tifffile.imread(p).astype(np.float32)
    L=0.2126*a[:,:,0]+0.7152*a[:,:,1]+0.0722*a[:,:,2]
    for nm,(cx,cy) in {"DUST":(6874,4580),"CTRL":(6874,3000)}.items():
        pt=L[cy-P:cy+P+1,cx-P:cx+P+1]
        if pt.shape==(n,n): raw.setdefault(nm,[]).append(pt.copy())
    del a,L
print("patches held: DUST %d  CTRL %d\n" % (len(raw["DUST"]),len(raw["CTRL"])))

base=[d for d in (detrend(p) for p in raw["CTRL"]) if d is not None]
c0,_,_=score(base)
print("== jitter arm: 3.0%% dip planted at a random per-master offset ==")
print("%10s %12s %12s %10s  %s" % ("jitter px","centre","shift pts","sigma","seen?"))
for J in (0,3,5,10,20,40):
    rng=np.random.default_rng(11); st=[]
    for pt in raw["CTRL"]:
        dx,dy=(0,0) if J==0 else (rng.integers(-J,J+1),rng.integers(-J,J+1))
        q=(pt*(1.0-0.03*np.exp(-(((gx-dx)**2+(gy-dy)**2)/(2*5.0**2))))).astype(np.float32)
        d=detrend(q)
        if d is not None: st.append(d)
    c,sd,z=score(st)
    print("%10d %11.3f%% %11.3f %9.2f  %s" % (J,100*c,100*(c-c0),z,"yes" if (c-c0)<-0.005 else "LOST"))

print("\n== the same jitter applied to a WIDER mote (sigma 15 px) ==")
for J in (0,10,20,40):
    rng=np.random.default_rng(11); st=[]
    for pt in raw["CTRL"]:
        dx,dy=(0,0) if J==0 else (rng.integers(-J,J+1),rng.integers(-J,J+1))
        q=(pt*(1.0-0.03*np.exp(-(((gx-dx)**2+(gy-dy)**2)/(2*15.0**2))))).astype(np.float32)
        d=detrend(q)
        if d is not None: st.append(d)
    c,sd,z=score(st)
    print("   jitter %2d px -> shift %+.3f pts (%.2f sd) %s" % (J,100*(c-c0),z,"yes" if (c-c0)<-0.005 else "LOST"))

print("\n== stacked residual map at the DUST site (percent, 10 px blocks) ==")
st=[d for d in (detrend(p) for p in raw["DUST"]) if d is not None]
S=np.median(np.stack(st),0)*100
b=S[0:110,0:110].reshape(11,10,11,10).mean(axis=(1,3))
print("      "+"".join("%7d"%(x*10-55) for x in range(11)))
for i in range(11):
    print("%5d "%(i*10-55)+"".join("%7.2f"%b[i,j] for j in range(11)))

