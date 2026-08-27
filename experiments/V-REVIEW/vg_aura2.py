"""Two-merge aura comparison on an arbitrary subject/dir.
Self-referenced statistic: depression = median(far field) - median(aura zone), DN.
Prints the DENOMINATOR on every row -- a ratio without its denominator is unreadable.
"""
import os, sys, hashlib
import numpy as np, cv2, tifffile

subj = sys.argv[1]
root = sys.argv[2] if len(sys.argv) > 2 else r"C:\dev\strehl-out\V-REVIEW\geom"

def lum(a): return (0.2126*a[:,:,0] + 0.7152*a[:,:,1] + 0.0722*a[:,:,2]).astype(np.float32)

paths = {m: os.path.join(root, "%s--%s.tiff" % (subj, m)) for m in ("pyramid","estimator")}
for m,p in paths.items():
    print("%-10s %s  sha256 %s" % (m, os.path.basename(p),
          hashlib.sha256(open(p,'rb').read()).hexdigest()[:16]))
arms = {m: lum(tifffile.imread(p).astype(np.float32)) for m,p in paths.items()}
if hashlib.sha256(open(paths['pyramid'],'rb').read()).digest() == \
   hashlib.sha256(open(paths['estimator'],'rb').read()).digest():
    print("FATAL: arms are byte-identical - nothing to compare"); sys.exit(1)

# photometric check: are the two merges in the same space at all?
mp, me = float(np.median(arms['pyramid'])), float(np.median(arms['estimator']))
print("\nphotometric  pyramid median %.1f   estimator median %.1f   level ratio %.4f" % (mp, me, me/mp))

mean = (arms['pyramid'] + arms['estimator']) / 2.0
print("\n%5s %10s %14s %14s %10s   %s" % ("pct","zone(bin)","pyr depress","est depress","est/pyr","note"))
rows=[]
for pct in (20,30,40,50):
    cut = np.percentile(mean, pct)
    sub = (mean <= cut).astype(np.uint8)
    sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, np.ones((25,25), np.uint8))
    d = cv2.distanceTransform(1-sub, cv2.DIST_L2, 5)
    for lo,hi in ((40,100),(80,200)):
        aura = (d>=lo)&(d<=hi); far = (d>400)
        if aura.sum()<20000 or far.sum()<20000:
            print("%5d %14s %14s %14s %10s   too few px" % (pct,"%d-%d"%(lo,hi),"-","-","-")); continue
        dep = {m: float(np.median(arms[m][far]) - np.median(arms[m][aura])) for m in arms}
        r = dep['estimator']/dep['pyramid'] if abs(dep['pyramid'])>1e-9 else float('nan')
        note = "DENOMINATOR NEAR ZERO" if abs(dep['pyramid'])<50 else ""
        rows.append((dep['pyramid'], dep['estimator'], r))
        print("%5d %14s %14.1f %14.1f %10.2f   %s" % (pct,"%d-%d"%(lo,hi),dep['pyramid'],dep['estimator'],r,note))
if rows:
    p=[x[0] for x in rows]; e=[x[1] for x in rows]; rr=[x[2] for x in rows]
    print("\npyramid depression (the DENOMINATOR) spans %+.1f to %+.1f DN" % (min(p),max(p)))
    print("estimator depression            spans %+.1f to %+.1f DN" % (min(e),max(e)))
    print("absolute excess (est-pyr)       spans %+.1f to %+.1f DN" % (min(np.array(e)-np.array(p)),max(np.array(e)-np.array(p))))
    print("ratio                           spans %.2f to %.2f" % (min(rr),max(rr)))
    print("sign of denominator: %s" % ("CROSSES ZERO - ratio undefined near its pole" if min(p)<0<max(p) else "single sign"))
