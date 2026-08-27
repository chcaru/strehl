"""Aura comparison with a mask that MATCHES the measured subject, plus an
explicit contamination floor on the aura band.

Defect this fixes: vh2's fixed 20/30/40/50 percentile sweep was built on a
subject occupying 21% of the frame.  Applied to a subject occupying 60%, it
masks half the subject and the 'aura' band lands on unmasked subject, so the
statistic stops measuring ground depression.  Symptom: depression exceeding
the image median.  A configuration whose aura band is not ground is REFUSED,
not scored.
"""
import os, sys, hashlib
import numpy as np, cv2, tifffile

subj = sys.argv[1]
root = sys.argv[2] if len(sys.argv) > 2 else r"C:\dev\strehl-out\V-REVIEW\geom"
def lum(a): return (0.2126*a[:,:,0] + 0.7152*a[:,:,1] + 0.0722*a[:,:,2]).astype(np.float32)

paths = {m: os.path.join(root, "%s--%s.tiff" % (subj,m)) for m in ("pyramid","estimator")}
arms = {m: lum(tifffile.imread(p).astype(np.float32)) for m,p in paths.items()}
h = {m: hashlib.sha256(open(p,'rb').read()).hexdigest()[:12] for m,p in paths.items()}
assert h['pyramid'] != h['estimator'], "arms byte-identical"
mean = (arms['pyramid']+arms['estimator'])/2.0

# subject mask by Otsu -- the same delineation the geometry screen measured
thr,_ = cv2.threshold((np.clip(mean/mean.max(),0,1)*255).astype(np.uint8),0,255,
                      cv2.THRESH_BINARY+cv2.THRESH_OTSU)
base = (mean <= thr/255.0*mean.max())
print("%s   arms %s / %s   otsu subject %.1f%% of frame" % (subj,h['pyramid'],h['estimator'],100*base.mean()))

print("%7s %10s %9s %9s %13s %13s %9s   %s" %
      ("mask%","zone(bin)","aura=grnd","subj%","pyr depress","est depress","est/pyr","status"))
ok=[]; refused=0
for scale in (0.75,1.0,1.25,1.5):
    pct = float(np.clip(100*base.mean()*scale, 2, 90))
    sub = (mean <= np.percentile(mean,pct)).astype(np.uint8)
    sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, np.ones((25,25),np.uint8))
    sub = cv2.morphologyEx(sub, cv2.MORPH_OPEN,  np.ones((9,9),np.uint8))
    d = cv2.distanceTransform(1-sub, cv2.DIST_L2, 5)
    ms = float(np.median(mean[sub>0]))
    for lo,hi in ((40,100),(80,200)):
        aura=(d>=lo)&(d<=hi); far=(d>400)
        if aura.sum()<20000 or far.sum()<20000:
            print("%7.1f %10s %9s %9s %13s %13s %9s   REFUSED too-few-px"%(pct,"%d-%d"%(lo,hi),"-","-","-","-","-")); refused+=1; continue
        mfar=float(np.median(mean[far]))
        # contamination: is the aura band GROUND, or is it still subject?
        mid=(ms+mfar)/2.0
        gfrac=float((mean[aura]>mid).mean())
        dep={m: float(np.median(arms[m][far])-np.median(arms[m][aura])) for m in arms}
        if gfrac < 0.70:
            print("%7.1f %10s %9.2f %8.1f%% %13.1f %13.1f %9s   REFUSED aura-not-ground"
                  %(pct,"%d-%d"%(lo,hi),gfrac,100*sub.mean(),dep['pyramid'],dep['estimator'],"-")); refused+=1; continue
        if abs(dep['pyramid'])<300:
            print("%7.1f %10s %9.2f %8.1f%% %13.1f %13.1f %9s   REFUSED denom<300DN"
                  %(pct,"%d-%d"%(lo,hi),gfrac,100*sub.mean(),dep['pyramid'],dep['estimator'],"-")); refused+=1; continue
        r=dep['estimator']/dep['pyramid']; ok.append((dep['pyramid'],dep['estimator'],r))
        print("%7.1f %10s %9.2f %8.1f%% %13.1f %13.1f %9.3f   ok"
              %(pct,"%d-%d"%(lo,hi),gfrac,100*sub.mean(),dep['pyramid'],dep['estimator'],r))
print("\npartition: measured %d / refused %d / total %d" % (len(ok),refused,len(ok)+refused))
if ok:
    p=np.array([x[0] for x in ok]); e=np.array([x[1] for x in ok]); r=np.array([x[2] for x in ok])
    print("denominator (pyr depress) %+.1f..%+.1f DN   single-sign %s" % (p.min(),p.max(), p.min()*p.max()>0))
    print("absolute excess est-pyr   %+.1f..%+.1f DN" % ((e-p).min(),(e-p).max()))
    print("RATIO                     %.3f..%.3f" % (r.min(),r.max()))
