"""Resolve the three disputed coordinates by MEASUREMENT.

Depth here is annulus-referenced, not closing-referenced: the closing detrend
under-measures large motes (commissioned: a 10% r=25 plant read 8.20%).
    depth = 1 - median(disk r<=R1) / median(annulus R2<=r<=R3)
Commissioned below against plants of known depth.
"""
import numpy as np, os, json
D = r"C:\dev\strehl-out\V-REVIEW\dust"
A = np.load(os.path.join(D,"flat_rampA.npy")).astype(np.float32)
B = np.load(os.path.join(D,"flat_rampB.npy")).astype(np.float32)
h,w = A.shape
yy,xx = np.mgrid[0:h,0:w]
R1,R2,R3 = 14,30,55

def depth_at(F,x,y):
    if not (R3 <= x < w-R3 and R3 <= y < h-R3): return None
    sl = (slice(y-R3,y+R3+1), slice(x-R3,x+R3+1))
    sub = F[sl]; ly,lx = np.mgrid[0:sub.shape[0],0:sub.shape[1]]
    rr = np.sqrt((ly-R3)**2+(lx-R3)**2)
    disk = rr<=R1; ann=(rr>=R2)&(rr<=R3)
    return float(1.0 - np.median(sub[disk])/np.median(sub[ann]))

# --- commission the annulus statistic ---
print("== commission annulus depth: plant known, read back ==")
rng=np.random.default_rng(1)
base = np.ones((h,w),np.float32)
for (px,py,dep,rad) in [(700,500,0.01,12),(1500,900,0.03,18),(2500,1400,0.10,25),(1000,1800,0.05,30),(2000,600,0.1328,20)]:
    t = base*(1.0-dep*np.exp(-(((xx-px)**2+(yy-py)**2)/(2.0*rad**2)))).astype(np.float32)
    t = t*(1.0+rng.normal(0,0.00187,(h,w)).astype(np.float32))
    m = depth_at(t,px,py)
    print("   plant %6.2f%% r=%2d -> read %6.2f%%   err %+.2f pts" % (100*dep,rad,100*m,100*m-100*dep))
print("   NOTE: a Gaussian mote's annulus-referenced depth under-reads its peak for large r.")
print("   ARM: flat with NO plant ->  read %+.3f%% (must be ~0)" % (100*depth_at(base*(1.0+rng.normal(0,0.00187,(h,w)).astype(np.float32)),1700,1200)))

print("\n== the three disputed coordinates, every plausible reading ==")
claims = [
    ("LaneA (3434,2305) read as BINNED/quad", 3434, 2305),
    ("LaneA (3434,2305) read as SENSOR",      3434//2, 2305//2),
    ("LaneB cite (7008,4450) read as SENSOR", 7008//2, 4450//2),
    ("LaneB cite (7008,4450) read as BINNED", 7008, 4450),
    ("LaneB file 6776_4322 read as SENSOR",   6776//2, 4322//2),
    ("LaneB file 6776_4322 read as BINNED",   6776, 4322),
]
print("%-42s %7s %7s %10s %10s  %s" % ("interpretation","bin x","bin y","depth A","depth B","in frame"))
for (tag,bx,by) in claims:
    inb = (0<=bx<w and 0<=by<h)
    dA = depth_at(A,bx,by) if inb else None
    dB = depth_at(B,bx,by) if inb else None
    print("%-42s %7d %7d %10s %10s  %s" % (tag,bx,by,
          ("%.2f%%"%(100*dA)) if dA is not None else "-",
          ("%.2f%%"%(100*dB)) if dB is not None else "-",
          "yes" if inb else "NO - outside sensor"))

print("\n== my own strongest reproducible motes, annulus-referenced ==")
motes = json.load(open(os.path.join(D,"motes.json")))
print("%7s %7s %9s %9s %10s %10s" % ("bin x","bin y","sensor x","sensor y","depth A","depth B"))
for m in motes:
    dA,dB = depth_at(A,m["bx"],m["by"]), depth_at(B,m["bx"],m["by"])
    print("%7d %7d %9d %9d %9.2f%% %9.2f%%" % (m["bx"],m["by"],m["sx"],m["sy"],
          100*dA if dA is not None else float('nan'), 100*dB if dB is not None else float('nan')))
