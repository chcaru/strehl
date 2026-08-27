"""Dust detector v2.

v1 defect: a Gaussian lowpass cannot follow steep corner vignetting, so its
residual blew up at the frame border and the detector reported 132 'motes' of
which the strongest sat at x=0 and x=3513.  It also failed its null arm with 55
detections on a field containing no dust.  Both are fixed here:

  - detrend by GRAYSCALE CLOSING with a disk larger than any mote.  Closing
    removes dark spots by construction and leaves smooth background alone.
  - exclude a border margin, and say how many px were excluded.
  - the null is a PARAMETRIC radial fit to the real vignetting plus measured
    noise: mote-free by construction, and it never saw a mote.
"""
import numpy as np, cv2, os, json
D = r"C:\dev\strehl-out\V-REVIEW\dust"
RAD  = 40      # closing disk radius, binned px  (= 80 sensor px)
MARG = 60      # border margin excluded, binned px

SE = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2*RAD+1, 2*RAD+1))
def resid(F):
    closed = cv2.morphologyEx(F, cv2.MORPH_CLOSE, SE)
    return F/np.maximum(closed,1e-6) - 1.0

def interior(R):
    m = np.zeros(R.shape, bool); m[MARG:-MARG, MARG:-MARG] = True; return m

def detect(R, thr):
    neg = ((R < -thr) & interior(R)).astype(np.uint8)
    neg = cv2.morphologyEx(neg, cv2.MORPH_OPEN, np.ones((3,3),np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(neg, 8)
    out=[]
    for i in range(1,n):
        if st[i,cv2.CC_STAT_AREA] < 6: continue
        m = lab==i; ys,xs = np.nonzero(m); j = int(np.argmin(R[m]))
        out.append((int(xs[j]), int(ys[j]), float(R[m].min()), int(st[i,cv2.CC_STAT_AREA])))
    return sorted(out, key=lambda t:t[2])

A = np.load(os.path.join(D,"flat_rampA.npy")).astype(np.float32)
B = np.load(os.path.join(D,"flat_rampB.npy")).astype(np.float32)
RA, RB = resid(A), resid(B)
h,w = A.shape
print("binned %dx%d, border margin %d px excluded -> %.2f%% of frame not examined"
      % (w,h,MARG, 100*(1 - (w-2*MARG)*(h-2*MARG)/float(w*h))))
iA = RA[interior(RA)]
sd = float(np.std(iA[np.abs(iA)<0.02]))         # robust: noise core only
THR = 6*sd
print("interior residual noise sd %.5f -> threshold 6sd = %.4f (%.2f%%)\n" % (sd,THR,100*THR))

# ---- parametric mote-free null: radial polynomial fit to the real vignetting
yy,xx = np.mgrid[0:h,0:w].astype(np.float32)
r2 = ((yy-h/2)/(h/2))**2 + ((xx-w/2)/(w/2))**2
X = np.stack([np.ones_like(r2).ravel(), r2.ravel(), (r2**2).ravel(), (r2**3).ravel()],1)
coef,*_ = np.linalg.lstsq(X, A.ravel(), rcond=None)
vign = (X@coef).reshape(h,w).astype(np.float32)
print("radial vignetting fit: residual sd %.5f (fit quality)" % float(np.std(A-vign)))
rng = np.random.default_rng(0)

print("\n== ARM D0  NULL: parametric vignetting + noise, mote-free BY CONSTRUCTION ==")
null = vign*(1.0+rng.normal(0,sd,A.shape).astype(np.float32))
dn = detect(resid(null), THR)
print("   detections: %d   %s" % (len(dn), "PASS" if len(dn)==0 else "FAIL"))

print("\n== ARM D0b NULL on the REAL flat with motes filled in ==")
med = cv2.morphologyEx(A, cv2.MORPH_CLOSE, SE)
dn2 = detect(resid(med*(1.0+rng.normal(0,sd,A.shape).astype(np.float32))), THR)
print("   detections: %d   %s" % (len(dn2), "PASS" if len(dn2)==0 else "FAIL"))

print("\n== ARM D1  PLANT into the null: known depth, known place ==")
plants=[(700,500,0.01,12),(1500,900,0.03,18),(2500,1400,0.10,25),(3000,600,0.003,15),(1000,1800,0.05,30)]
p = null.copy()
for (px,py,dep,rad) in plants:
    p = p*(1.0-dep*np.exp(-(((xx-px)**2+(yy-py)**2)/(2.0*rad**2)))).astype(np.float32)
dp = detect(resid(p), THR)
nmatched=0
for (px,py,dep,rad) in plants:
    hit=[t for t in dp if abs(t[0]-px)<=rad+5 and abs(t[1]-py)<=rad+5]
    if hit:
        nmatched+=1
        print("   plant %5.1f%% r=%2d (%4d,%4d) -> FOUND %5.2f%% at (%4d,%4d)  err %+.2f pts"
              %(100*dep,rad,px,py,-100*hit[0][2],hit[0][0],hit[0][1],-100*hit[0][2]-100*dep))
    else:
        print("   plant %5.1f%% r=%2d (%4d,%4d) -> not detected" %(100*dep,rad,px,py))
print("   spurious (unplanted) detections: %d" % (len(dp)-nmatched))

print("\n== REAL FLAT, both ramps ==")
da,db = detect(RA,THR), detect(RB,THR)
def match(d1,d2,tol=20):
    out=[]
    for (x,y,dep,ar) in d1:
        c=[t for t in d2 if abs(t[0]-x)<=tol and abs(t[1]-y)<=tol]
        if c: out.append((x,y,dep,c[0][2],ar))
    return out
both=match(da,db)
print("rampA %d   rampB %d   in BOTH %d   (A-only %d, B-only %d)"
      % (len(da),len(db),len(both),len(da)-len(both),len(db)-len(both)))
print("\n%6s %6s %9s %9s %9s %9s %7s" % ("bin x","bin y","sensor x","sensor y","depth A","depth B","area"))
for (x,y,dA,dB,ar) in both[:20]:
    print("%6d %6d %9d %9d %8.2f%% %8.2f%% %7d" % (x,y,2*x,2*y,-100*dA,-100*dB,ar))
json.dump([{"bx":x,"by":y,"sx":2*x,"sy":2*y,"depthA":-100*dA,"depthB":-100*dB,"area":ar}
           for (x,y,dA,dB,ar) in both], open(os.path.join(D,"motes.json"),"w"), indent=1)
print("\nwrote motes.json")
