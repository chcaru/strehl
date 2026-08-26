import numpy as np, tifffile
from scipy.ndimage import uniform_filter, sobel

def analyse(path, label):
    a = tifffile.imread(path).astype(np.float32)
    H, W, _ = a.shape
    R, G, B = a[:,:,0], a[:,:,1], a[:,:,2]
    m = (R + B) * 0.5 - G                       # magenta(+) / green(-) index
    exc = m - uniform_filter(m, size=31)        # LOCAL excess: cancels subject colour
    lum = uniform_filter((R + 2*G + B) * 0.25, size=3)
    gy, gx = sobel(lum, axis=0), sobel(lum, axis=1)
    gmag = np.hypot(gx, gy)

    cy, cx = (H - 1) / 2.0, (W - 1) / 2.0       # optical centre
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ry, rx = yy - cy, xx - cx
    rad = np.hypot(ry, rx)
    rn = np.maximum(rad, 1e-6)
    dot = (gx * rx + gy * ry) / rn              # +ve: brightens OUTWARD

    edge = gmag > np.percentile(gmag, 99.5)     # strong edges only
    print("=== %s ===" % label)
    print("edge population: %d px (top 0.5%% gradient)" % edge.sum())

    # TEST 1 - ANTISYMMETRY. Lateral CA reverses hue across a feature.
    out_, in_ = edge & (dot > 0), edge & (dot < 0)
    mo, mi = exc[out_].mean(), exc[in_].mean()
    print("T1 ANTISYMMETRY  outward-brightening edges: %+8.1f   inward: %+8.1f   separation %+8.1f"
          % (mo, mi, mo - mi))
    print("   signs %s  -> %s" % (("OPPOSITE" if mo*mi < 0 else "SAME"),
          "CA-like" if mo*mi < 0 else "NOT the antisymmetry CA requires"))

    # TEST 2 - RADIAL GROWTH. Lateral CA grows with distance from centre.
    rmax = rad.max()
    print("T2 RADIAL GROWTH (separation by radius octile)")
    seps = []
    for k in range(8):
        band = edge & (rad >= k*rmax/8) & (rad < (k+1)*rmax/8)
        bo, bi = band & (dot > 0), band & (dot < 0)
        if bo.sum() > 200 and bi.sum() > 200:
            s = exc[bo].mean() - exc[bi].mean(); seps.append((k, s))
            print("     r %.2f-%.2f : separation %+8.1f  (n=%d)"
                  % (k/8, (k+1)/8, s, band.sum()))
    if len(seps) >= 4:
        ks = np.array([s[0] for s in seps], float); vs = np.array([s[1] for s in seps])
        slope = np.polyfit(ks, vs, 1)[0]
        print("     linear trend vs radius: %+.1f per octile -> %s"
              % (slope, "grows outward (CA-like)" if abs(slope) > 20 and slope*np.sign(vs.mean()) > 0
                 else "FLAT / no radial growth -> NOT lateral CA"))

    # TEST 3 - LEVEL DEPENDENCE. Clipping asymmetry depends on level only.
    print("T3 LEVEL DEPENDENCE (|excess| by luminance quintile of edge px)")
    lv = lum[edge]; ex = np.abs(exc[edge])
    qs = np.percentile(lv, [0,20,40,60,80,100])
    for k in range(5):
        sel = (lv >= qs[k]) & (lv <= qs[k+1])
        print("     lum %5.0f-%5.0f : mean|excess| %8.1f" % (qs[k], qs[k+1], ex[sel].mean()))
    print()

analyse(r"C:\dev\strehl-out\V-HIGHLIGHT\fba-srgb-default.tiff", "flower-bud, MY render, CA correcting (ships), knee default")
analyse(r"C:\dev\strehl-out\V-HIGHLIGHT\fba-srgb-CAoff.tiff",   "flower-bud, MY render, CA OFF, knee default")
