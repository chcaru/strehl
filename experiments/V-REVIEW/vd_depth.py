"""Peak-depth measurement, aperture-matched to the motes and edge-aware.

Earlier defect: an R1=14 disk averaged a ~3 px-radius mote over 615 px and
diluted its depth about 20-fold, and a 55 px annulus could not seat within
39 px of the frame edge -- which is exactly where the disputed coordinates are.
Here: light smoothing to beat noise, peak (minimum) in a small window, annulus
reference computed only over pixels that exist.
"""
import numpy as np, cv2, os, json
D = r"C:\dev\strehl-out\V-REVIEW\dust"
A = np.load(os.path.join(D,"flat_rampA.npy")).astype(np.float32)
B = np.load(os.path.join(D,"flat_rampB.npy")).astype(np.float32)
h,w = A.shape
SA = cv2.GaussianBlur(A,(0,0),2.0); SB = cv2.GaussianBlur(B,(0,0),2.0)
yy,xx = np.mgrid[0:h,0:w]

def peak_depth(F, x, y, win=10, R2=25, R3=50):
    y0,y1 = max(0,y-R3), min(h,y+R3+1); x0,x1 = max(0,x-R3), min(w,x+R3+1)
    sub = F[y0:y1, x0:x1]
    ly,lx = np.mgrid[y0:y1, x0:x1]
    rr = np.sqrt((ly-y)**2.0+(lx-x)**2.0)
    ann = (rr>=R2)&(rr<=R3)
    if ann.sum() < 200: return None, None, ann.sum()
    ref = float(np.median(sub[ann]))
    near = rr<=win
    pk = float(sub[near].min())
    return 1.0-pk/ref, ref, int(ann.sum())

print("== commission: plant known peak depth, read it back ==")
rng=np.random.default_rng(2)
for (px,py,dep,rad) in [(700,500,0.01,4),(1500,900,0.03,4),(2500,1400,0.10,4),(1700,1200,0.1328,6),(1200,700,0.05,10)]:
    t = (np.ones((h,w),np.float32)*(1.0-dep*np.exp(-(((xx-px)**2+(yy-py)**2)/(2.0*rad**2)))).astype(np.float32))
    t *= (1.0+rng.normal(0,0.00187,(h,w)).astype(np.float32))
    d,_,_ = peak_depth(cv2.GaussianBlur(t,(0,0),2.0),px,py)
    print("   plant %6.2f%% sigma=%2d -> read %6.2f%%  err %+.2f pts" % (100*dep,rad,100*d,100*d-100*dep))
t = np.ones((h,w),np.float32)*(1.0+rng.normal(0,0.00187,(h,w)).astype(np.float32))
d,_,_ = peak_depth(cv2.GaussianBlur(t,(0,0),2.0),1700,1200)
print("   NO plant (null)            -> read %+.3f%%  (must be ~0)" % (100*d))
print("   ARM: a BRIGHT spot (wrong sign) must not read as depth:")
t = np.ones((h,w),np.float32)*(1.0+0.05*np.exp(-(((xx-1700)**2+(yy-1200)**2)/(2.0*6**2)))).astype(np.float32)
d,_,_ = peak_depth(cv2.GaussianBlur(t,(0,0),2.0),1700,1200)
print("      planted +5%% bright spot  -> read %+.3f%%" % (100*d))

print("\n== disputed coordinates, measured on the flat ==")
claims = [("LaneA (3434,2305) as BINNED",3434,2305),
          ("LaneA (3434,2305) as SENSOR ->bin",1717,1152),
          ("LaneB (7008,4450) as SENSOR ->bin",3504,2225),
          ("LaneB 6776_4322 as SENSOR ->bin",3388,2161),
          ("my deepest mote",3440,2282)]
print("%-38s %7s %7s %10s %10s %8s" % ("interpretation","bin x","bin y","depth A","depth B","ann px"))
for (tag,bx,by) in claims:
    dA,_,nA = peak_depth(SA,bx,by); dB,_,_ = peak_depth(SB,bx,by)
    print("%-38s %7d %7d %9s %9s %8d" % (tag,bx,by,
          ("%.2f%%"%(100*dA)) if dA is not None else "no ref",
          ("%.2f%%"%(100*dB)) if dB is not None else "no ref", nA))

print("\n== all reproducible motes, peak depth ==")
motes = json.load(open(os.path.join(D,"motes.json")))
print("%7s %7s %9s %9s %10s %10s" % ("bin x","bin y","sensor x","sensor y","depth A","depth B"))
for m in motes:
    dA,_,_ = peak_depth(SA,m["bx"],m["by"]); dB,_,_ = peak_depth(SB,m["bx"],m["by"])
    print("%7d %7d %9d %9d %9.2f%% %9.2f%%" % (m["bx"],m["by"],m["sx"],m["sy"],100*dA,100*dB))

print("\n== worst depression ANYWHERE in the interior, both ramps ==")
for tag,S in (("rampA",SA),("rampB",SB)):
    cl = cv2.morphologyEx(S, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(81,81)))
    r = S/np.maximum(cl,1e-6)-1.0
    m = np.zeros(r.shape,bool); m[60:-60,60:-60]=True
    rr = np.where(m, r, 0)
    ij = np.unravel_index(np.argmin(rr), rr.shape)
    print("   %s worst %.2f%% at binned (%d,%d) = sensor (%d,%d)"
          % (tag, -100*rr.min(), ij[1], ij[0], 2*ij[1], 2*ij[0]))
