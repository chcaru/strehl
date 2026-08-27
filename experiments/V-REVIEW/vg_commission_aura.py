"""Commission the AURA statistic on THIS configuration.  Both directions,
plus the far-field term the verdict divides by.  Substrate: bee-2-cpl."""
import os, numpy as np, cv2, tifffile

R = r"C:\dev\strehl-out\V-REVIEW\geom"
def lum(a): return (0.2126*a[:,:,0]+0.7152*a[:,:,1]+0.0722*a[:,:,2]).astype(np.float32)
P = lum(tifffile.imread(os.path.join(R,"bee-2-cpl--pyramid.tiff")).astype(np.float32))
E = lum(tifffile.imread(os.path.join(R,"bee-2-cpl--estimator.tiff")).astype(np.float32))
mean=(P+E)/2.0
sub=(mean<=np.percentile(mean,48.0)).astype(np.uint8)
sub=cv2.morphologyEx(sub,cv2.MORPH_CLOSE,np.ones((25,25),np.uint8))
sub=cv2.morphologyEx(sub,cv2.MORPH_OPEN,np.ones((9,9),np.uint8))
d=cv2.distanceTransform(1-sub,cv2.DIST_L2,5)
AURA=(d>=40)&(d<=100); FAR=(d>400)

def dep(a): return float(np.median(a[FAR])-np.median(a[AURA]))
def report(tag,p,e,pred=None):
    dp,de=dep(p),dep(e); r=de/dp if abs(dp)>1e-9 else float('nan')
    s="%-42s pyr %8.1f  est %8.1f  excess %+8.1f  ratio %7.3f"%(tag,dp,de,de-dp,r)
    if pred is not None: s+="   predicted excess %+.1f  err %+.1f DN"%(pred,(de-dp)-pred)
    print(s)
    return de-dp

print("== ARM A0  identity: both arms the SAME file.  excess MUST be 0.000, ratio 1.000 ==")
report("A0 pyramid vs pyramid", P, P.copy())

print("\n== baseline ==")
base=report("A1 real pyramid vs real estimator", P, E)

print("\n== ARM A2  plant a DEPRESSION into the estimator aura band ==")
print("   (deeper aura = the defect being alleged; excess MUST rise by the planted amount)")
for amt in (100.0,400.0,1600.0):
    e2=E.copy(); e2[AURA]-=amt
    report("A2 plant -%.0f DN in est aura"%amt, P, e2, pred=base+amt)

print("\n== ARM A3  plant an IMPROVEMENT: LIFT the estimator aura band ==")
print("   (a fix, not a defect; excess MUST fall, and must go NEGATIVE when over-corrected)")
for amt in (400.0,1600.0):
    e2=E.copy(); e2[AURA]+=amt
    report("A3 lift +%.0f DN in est aura"%amt, P, e2, pred=base-amt)

print("\n== ARM A4  DENOMINATOR arm: perturb the FAR FIELD only, not the aura ==")
print("   (the statistic is a difference FROM the far field; it must track it 1:1)")
for amt in (-800.0,-200.0,200.0,800.0):
    e2=E.copy(); e2[FAR]+=amt
    report("A4 far field %+.0f DN (est only)"%amt, P, e2, pred=base+amt)

print("\n== ARM A5  common-mode: shift BOTH arms' far field equally.  excess MUST NOT move ==")
for amt in (500.0,2000.0):
    p2=P.copy(); e2=E.copy(); p2[FAR]+=amt; e2[FAR]+=amt
    report("A5 both far fields %+.0f DN"%amt, p2, e2, pred=base)

print("\n== ARM A6  scale: multiply BOTH arms by 2.  a DIFFERENCE statistic must double ==")
report("A6 both arms x2", P*2.0, E*2.0, pred=base*2.0)
