"""Stationarity across 26 masters: does a dip sit at a FIXED sensor location?

Self-calibrating: at each candidate site I search a +/-40 px window for the
deepest quadratic-detrended dip and record WHERE it landed. A mote never moves,
so its argmin clusters tightly across subjects. Subject detail moves, so a
control site's argmin scatters. Scatter of the argmin IS the statistic; that
needs no knowledge of the exact master-to-sensor offset.
"""
import numpy as np, cv2, os, glob, json
SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4"
import tifffile

WIN=45; CORE=8; SEARCH=40
def quad_depth(F,x,y,win=WIN,core=CORE):
    h,w=F.shape
    y0,y1=max(0,y-win),min(h,y+win+1); x0,x1=max(0,x-win),min(w,x+win+1)
    sub=F[y0:y1,x0:x1].astype(np.float64)
    gy,gx=np.mgrid[y0:y1,x0:x1]; gy=(gy-y).astype(np.float64); gx=(gx-x).astype(np.float64)
    rr=np.sqrt(gy**2+gx**2); fit=rr>core+6
    if fit.sum()<400: return None
    Xc=np.stack([np.ones(fit.sum()),gx[fit],gy[fit],gx[fit]**2,gy[fit]**2,gx[fit]*gy[fit]],1)
    coef,*_=np.linalg.lstsq(Xc,sub[fit],rcond=None)
    Xa=np.stack([np.ones(sub.size),gx.ravel(),gy.ravel(),gx.ravel()**2,gy.ravel()**2,(gx*gy).ravel()],1)
    model=(Xa@coef).reshape(sub.shape); cm=rr<=core
    md=np.median(model[cm])
    if md<=0: return None
    return float(1.0-sub[cm].min()/md)

# dust site from the flat (binned 3437,2290 -> master ~6874,4580) + controls
SITES = {"DUST (resolved)": (6874,4580),
         "ctrl-A": (6874,3000), "ctrl-B": (5200,4580), "ctrl-C": (3500,2344),
         "ctrl-D": (6300,4200), "ctrl-E": (1500,1500)}

paths = sorted(glob.glob(os.path.join(SHIP,"*--SHIP-V4.tiff")))
res = {k:[] for k in SITES}
print("scanning %d masters..." % len(paths))
for p in paths:
    s=os.path.basename(p).replace("--SHIP-V4.tiff","")
    a=tifffile.imread(p).astype(np.float32)
    L=(0.2126*a[:,:,0]+0.7152*a[:,:,1]+0.0722*a[:,:,2])
    L=cv2.GaussianBlur(L,(0,0),1.5)
    for name,(cx,cy) in SITES.items():
        best=None
        for dy in range(-SEARCH,SEARCH+1,4):
            for dx in range(-SEARCH,SEARCH+1,4):
                d=quad_depth(L,cx+dx,cy+dy,win=40,core=5)
                if d is not None and (best is None or d>best[0]): best=(d,dx,dy)
        if best: res[name].append((s,best[0],best[1],best[2]))
    del a,L

print("\n%-16s %9s %9s %11s %11s %s" % ("site","med depth","max depth","argmin sd x","argmin sd y","interpretation"))
summary={}
for name,rows in res.items():
    d=np.array([r[1] for r in rows]); dx=np.array([r[2] for r in rows]); dy=np.array([r[3] for r in rows])
    sdx,sdy=float(np.std(dx)),float(np.std(dy))
    summary[name]=dict(med=float(np.median(d)),mx=float(d.max()),sdx=sdx,sdy=sdy,n=len(rows))
    print("%-16s %8.2f%% %8.2f%% %11.1f %11.1f %s" % (name,100*np.median(d),100*d.max(),sdx,sdy,
          "STATIONARY" if (sdx<12 and sdy<12) else "scatters"))
json.dump({k:[(r[0],r[1],r[2],r[3]) for r in v] for k,v in res.items()},
          open(r"C:\dev\strehl-out\V-REVIEW\dust\stationarity.json","w"), indent=1)
print("\nuniform-random argmin over a +/-40 grid would give sd ~= %.1f px" % (80/np.sqrt(12)))
