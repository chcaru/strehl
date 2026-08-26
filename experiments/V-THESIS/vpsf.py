"""Measure the system PSF from real edges, so that '1.2-1.8x on resolved
detail' can be converted into the units this verification measures in.

Slanted-edge, ISO-12233 in spirit: find patches whose structure tensor says
'one dominant orientation, strong gradient', project every pixel onto the edge
normal, bin sub-pixel to build the edge spread function, differentiate to the
line spread function, fit a Gaussian. Camera-linear green plane throughout.

If the merge's PSF were 1.2x narrower than the argmax arm's, the difference in
quadrature would be sigma_argmax * sqrt(1 - 1/1.2^2) = 0.553 * sigma_argmax
pixels of equivalent Gaussian blur. That is the number the headline has to be
able to exclude.
"""
import pathlib, sys
import numpy as np, tifffile
V = pathlib.Path("experiments/V-THESIS").resolve(); sys.path.insert(0, str(V))
from vplant import gauss_exact   # noqa: E402

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
P = 64


def esf_sigma(patch):
    a = patch.astype(np.float64)
    gy, gx = np.gradient(a)
    Jxx, Jyy, Jxy = (gx*gx).sum(), (gy*gy).sum(), (gx*gy).sum()
    tr, det = Jxx+Jyy, Jxx*Jyy-Jxy*Jxy
    disc = max(tr*tr/4-det, 0.0)
    l1, l2 = tr/2+np.sqrt(disc), tr/2-np.sqrt(disc)
    if l1 <= 0: return None
    coh = (l1-l2)/l1
    if coh < 0.90 or l1 < 1e4: return None
    th = 0.5*np.arctan2(2*Jxy, Jxx-Jyy)
    nx, ny = np.cos(th), np.sin(th)
    ang = np.degrees(np.arctan2(ny, nx)) % 90.0
    if ang < 3 or ang > 87: return None          # need a slant for sub-pixel binning
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    d = (xx-w/2)*nx + (yy-h/2)*ny
    lo, hi = np.percentile(a, 5), np.percentile(a, 95)
    if hi-lo < 200: return None
    order = np.argsort(d.ravel()); dv = d.ravel()[order]; av = a.ravel()[order]
    edges = np.arange(-8, 8.001, 0.25)
    idx = np.digitize(dv, edges)-1
    ok = (idx >= 0) & (idx < len(edges)-1)
    prof = np.array([np.median(av[ok][idx[ok]==i]) if (idx[ok]==i).any() else np.nan
                     for i in range(len(edges)-1)])
    if np.isnan(prof).any(): return None
    c = 0.5*(edges[:-1]+edges[1:])
    lsf = np.gradient(prof, c)
    if np.abs(lsf).max() < 1e-9: return None
    lsf = np.abs(lsf); lsf = lsf/lsf.sum()
    m = (lsf*c).sum(); var = (lsf*(c-m)**2).sum()
    if var <= 0: return None
    return float(np.sqrt(var))


for subj in ("flat-on-ruler-cpl","tweezers-cpl","bee-3-cpl"):
    for arm in ("merge","argmax"):
        g = tifffile.imread(str(R/subj/f"{arm}.tif"))[:,:,1].astype(np.float64)
        sig = []
        H, W = g.shape
        for y in range(200, H-P-200, 48):
            for x in range(200, W-P-200, 48):
                s = esf_sigma(g[y:y+P, x:x+P])
                if s is not None and 0.1 < s < 4.0: sig.append(s)
        if sig:
            sig = np.array(sig)
            k50 = np.sqrt(2*np.log(2))/(2*np.pi*np.median(sig))
            print(f"{subj:<20}{arm:<8} n_edges={len(sig):>5}  "
                  f"PSF sigma median {np.median(sig):.3f} px  p25 {np.percentile(sig,25):.3f}  "
                  f"MTF50 ~ {k50:.3f} cyc/px (period {1/k50:.2f} px)")
        else:
            print(f"{subj:<20}{arm:<8} no usable edges")

print("\nSANITY: plant a known extra blur on the argmax arm and re-measure the PSF")
g = tifffile.imread(str(R/"flat-on-ruler-cpl"/"argmax.tif"))[:,:,1].astype(np.float64)
sub = g[800:1600, 1200:2000]
for extra in (0.0, 0.5, 1.0):
    b = gauss_exact(sub, extra) if extra else sub
    sig = []
    for y in range(0, 800-P, 32):
        for x in range(0, 800-P, 32):
            s = esf_sigma(b[y:y+P, x:x+P])
            if s is not None and 0.1 < s < 5.0: sig.append(s)
    if sig:
        print(f"   planted +{extra:.1f} px -> PSF sigma {np.median(sig):.3f} px "
              f"(expected {np.sqrt(np.median(sig)**2) if extra==0 else '~'+format(np.sqrt(0.0),'')}) n={len(sig)}")
