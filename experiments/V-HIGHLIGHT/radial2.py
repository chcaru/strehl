import numpy as np, tifffile
from scipy.ndimage import uniform_filter, sobel

def analyse(path, label):
    a = tifffile.imread(path).astype(np.float32)
    H, W, _ = a.shape
    R, G, B = a[:,:,0], a[:,:,1], a[:,:,2]
    lum = (R + 2*G + B) * 0.25
    # SCALE-INVARIANT chroma: a pure intensity edge at constant chromaticity gives 0.
    m = ((R + B) * 0.5 - G) / np.maximum(lum, 256.0)
    exc = m - uniform_filter(m, size=31)
    lums = uniform_filter(lum, size=3)
    gy, gx = sobel(lums, axis=0), sobel(lums, axis=1)
    gmag = np.hypot(gx, gy)
    cy, cx = (H-1)/2.0, (W-1)/2.0
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ry, rx = yy-cy, xx-cx
    rad = np.hypot(ry, rx); rn = np.maximum(rad, 1e-6)
    dot = (gx*rx + gy*ry) / rn
    edge = gmag > np.percentile(gmag, 99.5)

    print("=== %s ===" % label)
    # CONFOUND CHECK: does chroma track luminance at all? (would fake antisymmetry)
    s = np.random.default_rng(0).choice(edge.sum(), 60000, replace=False)
    cc = np.corrcoef(lums[edge][s], m[edge][s])[0,1]
    print("  confound check: corr(normalised chroma, luminance) on edges = %+.4f" % cc)
    o, i = edge & (dot > 0), edge & (dot < 0)
    mo, mi = exc[o].mean(), exc[i].mean()
    print("  T1 ANTISYMMETRY  outward %+.5f  inward %+.5f  separation %+.5f  [%s]"
          % (mo, mi, mo-mi, "OPPOSITE SIGN = CA-like" if mo*mi < 0 else "same sign"))
    rmax = rad.max(); seps=[]
    print("  T2 RADIAL")
    for k in range(6):
        band = edge & (rad >= k*rmax/8) & (rad < (k+1)*rmax/8)
        bo, bi = band & (dot>0), band & (dot<0)
        if bo.sum()>200 and bi.sum()>200:
            sp = exc[bo].mean()-exc[bi].mean(); seps.append(sp)
            print("     r %.2f-%.2f : %+.5f" % (k/8,(k+1)/8,sp))
    if len(seps)>=4:
        sl = np.polyfit(np.arange(len(seps),dtype=float), np.array(seps),1)[0]
        print("     trend %+.5f/octile -> %s" % (sl,
              "GROWS with radius = CA" if sl*np.sign(np.mean(seps))>0 else "flat/shrinks"))
    print("  T3 LEVEL (mean |excess| by luminance quintile)")
    lv, ex = lums[edge], np.abs(exc[edge])
    qs = np.percentile(lv,[0,20,40,60,80,100])
    vals=[]
    for k in range(5):
        sel=(lv>=qs[k])&(lv<=qs[k+1]); vals.append(ex[sel].mean())
        print("     lum %5.0f-%5.0f : %.5f" % (qs[k],qs[k+1],vals[-1]))
    print("     brightest quintile is %s the peak -> %s\n"
          % ("BELOW" if vals[-1]<max(vals) else "AT",
             "NOT monotonic in level = NOT clipping asymmetry" if vals[-1]<max(vals) else "level-driven"))

analyse(r"C:\dev\strehl-out\V-HIGHLIGHT\fba-srgb-default.tiff", "flower-bud CA CORRECTING (ships), knee default")
analyse(r"C:\dev\strehl-out\V-HIGHLIGHT\fba-srgb-CAoff.tiff",   "flower-bud CA OFF, knee default")
