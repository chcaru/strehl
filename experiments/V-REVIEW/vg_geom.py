"""Does a subject present 'a dark subject on a bright ground'?  MEASURED.

  dark_ratio    = median(far field) / median(subject)   >1 means subject darker
  surround_frac = fraction of the near band that is bright ground
  ground_iqr    = IQR/median of far field; low = a coherent, uniform ground

Boundary note: the subject test is `L <= cut`, not `L < cut`.  Otsu returns the
LOWER mode on a degenerate two-valued histogram, and a strict `<` then excludes
exactly the subject it just found.  See vg_commission.py ARM G0.
"""
import os, sys, glob
import numpy as np, cv2, tifffile

SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4"

def lum(a):
    return (0.2126*a[:,:,0] + 0.7152*a[:,:,1] + 0.0722*a[:,:,2]).astype(np.float32)

def geom(L, scale=2.0):
    thr, _ = cv2.threshold((np.clip(L/L.max(),0,1)*255).astype(np.uint8), 0, 255,
                           cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    sub = (L <= thr/255.0*L.max()).astype(np.uint8)
    sub = cv2.morphologyEx(sub, cv2.MORPH_OPEN, np.ones((15,15), np.uint8))
    sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, np.ones((51,51), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(sub, 8)
    if n <= 1:
        return None
    sub = (lab == 1+int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
    frac = float(sub.mean())
    if frac < 0.01 or frac > 0.75:
        return dict(bad="subject %.0f%% of frame" % (100*frac), frac=frac)
    d = cv2.distanceTransform(1-sub, cv2.DIST_L2, 5)
    far = (d > 400*scale)
    near = (d >= 40*scale) & (d <= 120*scale)
    if far.sum() < 20000 or near.sum() < 20000:
        return dict(bad="no far field", frac=frac)
    mf = float(np.median(L[far])); ms = float(np.median(L[sub > 0]))
    q1, q3 = np.percentile(L[far], [25, 75])
    return dict(frac=frac, dark_ratio=mf/max(ms,1e-9),
                surround=float((L[near] > 0.5*mf).mean()),
                iqr=float((q3-q1)/max(mf,1e-9)), mf=mf, ms=ms, bad=None)

def main():
    names = sys.argv[1:] or None
    paths = sorted(glob.glob(os.path.join(SHIP, "*--SHIP-V4.tiff")))
    if names:
        paths = [p for p in paths if any(n in os.path.basename(p) for n in names)]
    print("%-38s %7s %10s %9s %8s  %s" % ("subject","subj%","dark_ratio","surround","grnd_iqr","note"))
    for p in paths:
        s = os.path.basename(p).replace("--SHIP-V4.tiff","")
        g = geom(lum(tifffile.imread(p).astype(np.float32)))
        if g is None or g.get("bad"):
            print("%-38s %7s %10s %9s %8s  %s" % (s,"-","-","-","-", (g or {}).get("bad","no subject")))
        else:
            print("%-38s %6.1f%% %10.2f %9.2f %8.2f" % (s, 100*g["frac"], g["dark_ratio"], g["surround"], g["iqr"]))

if __name__ == "__main__":
    main()
