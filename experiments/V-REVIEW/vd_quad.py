"""Local quadratic detrend -- the reference that survives a steep gradient.

Every reference I tried before failed in the corner: a spatial annulus, an
iso-radial ring and a morphological closing each read 1.7-11.9% at sites where
a 20x20 block map shows a smooth monotone gradient and no dip at all. The
iso-radial arm read 8.88% at a corner control where nobody claims a mote.
Cause: they were all commissioned on a FLAT synthetic background, which is the
one background that cannot expose a gradient-following failure.

Here: fit a 2-D quadratic over a window, subtract it, measure the residual dip.
A quadratic absorbs any smooth vignetting including steep corner falloff.
Commissioned ON THE REAL CORNER, not on a flat field.
"""
import numpy as np, cv2, os
D = r"C:\dev\strehl-out\V-REVIEW\dust"
A = np.load(os.path.join(D,"flat_rampA.npy")).astype(np.float32)
B = np.load(os.path.join(D,"flat_rampB.npy")).astype(np.float32)
h,w = A.shape
SA = cv2.GaussianBlur(A,(0,0),2.0); SB = cv2.GaussianBlur(B,(0,0),2.0)

WIN=45; CORE=8
def quad_depth(F,x,y,win=WIN,core=CORE):
    y0,y1=max(0,y-win),min(h,y+win+1); x0,x1=max(0,x-win),min(w,x+win+1)
    sub=F[y0:y1,x0:x1].astype(np.float64)
    gy,gx=np.mgrid[y0:y1,x0:x1]; gy=(gy-y).astype(np.float64); gx=(gx-x).astype(np.float64)
    rr=np.sqrt(gy**2+gx**2)
    fit=(rr>core+6)                      # fit the surround only, never the core
    if fit.sum()<400: return None
    Xc=np.stack([np.ones(fit.sum()),gx[fit],gy[fit],gx[fit]**2,gy[fit]**2,gx[fit]*gy[fit]],1)
    coef,*_=np.linalg.lstsq(Xc,sub[fit],rcond=None)
    Xa=np.stack([np.ones(sub.size),gx.ravel(),gy.ravel(),gx.ravel()**2,gy.ravel()**2,(gx*gy).ravel()],1)
    model=(Xa@coef).reshape(sub.shape)
    core_m=rr<=core
    return float(1.0-sub[core_m].min()/np.median(model[core_m]))

print("== COMMISSION ON THE REAL CORNER GRADIENT (bin 3434,2305) ==")
yy,xx=np.mgrid[0:h,0:w]
rng=np.random.default_rng(4)
for site,(bx,by) in {"corner(3434,2305)":(3434,2305),"corner(3400,2300)":(3400,2300),"mid(1717,1152)":(1717,1152)}.items():
    print("  site %s   unplanted read %+.2f%%" % (site, 100*quad_depth(SA,bx,by)))
    for dep in (0.02,0.05,0.1328):
        t=A*(1.0-dep*np.exp(-(((xx-bx)**2+(yy-by)**2)/(2.0*5.0**2)))).astype(np.float32)
        d=quad_depth(cv2.GaussianBlur(t,(0,0),2.0),bx,by)
        print("      plant %6.2f%% -> read %6.2f%%   err %+.2f pts" % (100*dep,100*d,100*d-100*dep))
print("  ARM wrong-sign: plant a BRIGHT +5%% spot at the corner ->", end=" ")
t=A*(1.0+0.05*np.exp(-(((xx-3434)**2+(yy-2305)**2)/(2.0*5.0**2)))).astype(np.float32)
print("read %+.2f%%" % (100*quad_depth(cv2.GaussianBlur(t,(0,0),2.0),3434,2305)))

print("\n== DISPUTED COORDINATES, quadratic-detrended ==")
sites=[("LaneA (3434,2305) as BINNED",3434,2305),
       ("LaneA (3434,2305) as SENSOR",1717,1152),
       ("LaneB (7008,4450) as SENSOR",3504,2225),
       ("LaneB 6776_4322 as SENSOR",3388,2161),
       ("my detected mote",3440,2282),
       ("corner control (no claim)",3400,2300),
       ("mid-frame control",1200,800)]
print("%-34s %7s %7s %10s %10s" % ("site","bin x","bin y","depth A","depth B"))
for (tag,bx,by) in sites:
    dA=quad_depth(SA,bx,by); dB=quad_depth(SB,bx,by)
    print("%-34s %7d %7d %9s %9s" % (tag,bx,by,
        ("%+.2f%%"%(100*dA)) if dA is not None else "-",
        ("%+.2f%%"%(100*dB)) if dB is not None else "-"))

print("\n== worst quadratic-detrended dip anywhere (grid scan, 25 px step) ==")
best=[]
for by in range(60,h-60,25):
    for bx in range(60,w-60,25):
        d=quad_depth(SA,bx,by,win=40,core=6)
        if d is not None: best.append((d,bx,by))
best.sort(reverse=True)
print("%10s %7s %7s %9s %10s" % ("depth A","bin x","bin y","sensor","depth B"))
for (d,bx,by) in best[:10]:
    print("%9.2f%% %7d %7d %4d,%4d %9.2f%%" % (100*d,bx,by,2*bx,2*by,100*quad_depth(SB,bx,by,win=40,core=6)))
