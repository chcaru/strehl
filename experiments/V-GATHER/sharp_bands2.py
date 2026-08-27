"""Band cache v2. ONE change from sharp_bands: DEFOCUS-ROBUST REGISTRATION.

v1 correlated the master patch against the frame patch directly. On a DEEP
stack a frame whose focus plane is far from site i is massively defocused
there, correlation falls below 0.60, and the frame is dropped as
"unregistered". Measured on couch-fibers-cpl: only 9.9% of frame-site pairs
survived, and the subject refused.

That is backwards. A frame that is too defocused to correlate is not
unmeasurable -- it is the single most informative observation there is, because
it is a DIRECT MEASUREMENT that this frame does not cover this site. Dropping
it deletes exactly the evidence that a single frame has limited depth of field,
which is the quantity the coverage statistic exists to measure.

Fix: find the shift on a LOW-PASSED copy. Defocus is a low-pass, so it
preserves the 0.02-0.05 cyc/px structure the shift is recovered from, while
destroying the detail band the shift was previously recovered from.

This is safe for the measurement because BAND POWER IS TRANSLATION-INVARIANT --
|FFT| does not depend on phase. Registration here is not aligning phase, it is
only guaranteeing that both patches show the SAME CONTENT. A few px of residual
error is therefore free; 50 px is not.
"""
import os, sys, glob, numpy as np, tifffile
from scipy.ndimage import gaussian_filter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma, register, P, SEARCH
from sharp_bands import BANDS, bandpow, STRIDE, MARGIN, CLIP_MAX, BLACK_MAX, STD_FLOOR, ROOT

CACHE2 = r"C:\dev\strehl-out\V-GATHER\bandcache2"
LP_SIGMA = 4.0        # kills 0.15-0.30 cyc/px, keeps 0.02-0.05
LPCORR_MIN = 0.50     # on the low-passed pair, where defocus is not a penalty


def build(subject, force=False):
    os.makedirs(CACHE2, exist_ok=True)
    p = os.path.join(CACHE2, subject + ".npz")
    if os.path.exists(p) and not force:
        return dict(np.load(p, allow_pickle=True))
    d = os.path.join(ROOT, subject)
    mrgb = tifffile.imread(os.path.join(d, "MASTER.tiff"))[..., :3]
    my = luma(mrgb.astype(np.float32))
    h, w = my.shape
    sites = []
    for y in range(MARGIN, h - MARGIN - P, STRIDE):
        for x in range(MARGIN, w - MARGIN - P, STRIDE):
            b = my[y:y+P, x:x+P]
            if float((mrgb[y:y+P, x:x+P] >= 64000).mean()) > CLIP_MAX: continue
            if float((b <= 200).mean()) > BLACK_MAX: continue
            if float(b.std()) < STD_FLOOR: continue
            sites.append((y, x))
    del mrgb
    sites = np.array(sites)
    M = np.array([bandpow(my[y:y+P, x:x+P]) for y, x in sites])
    mlp = gaussian_filter(my, LP_SIGMA)
    frames = sorted(glob.glob(os.path.join(d, "f[0-9]*.tiff")))
    nf, ns, nb = len(frames), len(sites), len(BANDS)
    A = np.full((nf, ns, nb), np.nan)
    C = np.zeros((nf, ns)); CL = np.zeros((nf, ns))
    for fi, fp in enumerate(frames):
        fy = luma(tifffile.imread(fp)[..., :3].astype(np.float32))
        flp = gaussian_filter(fy, LP_SIGMA)
        for si, (y, x) in enumerate(sites):
            dy, dx, c = register(mlp[y:y+P, x:x+P],
                                 flp[y-SEARCH:y+P+SEARCH, x-SEARCH:x+P+SEARCH])
            CL[fi, si] = c
            if c < LPCORR_MIN:
                continue
            crop = fy[y+dy:y+dy+P, x+dx:x+dx+P]
            if crop.shape != (P, P) or float((crop <= 200).mean()) > BLACK_MAX:
                continue
            A[fi, si] = bandpow(crop)
            r = my[y:y+P, x:x+P]
            C[fi, si] = float(np.corrcoef(r.ravel(), crop.ravel())[0, 1])
        del fy, flp
        if fi % 25 == 0 or fi == nf-1:
            print("   %s %d/%d  lp-registered %.0f%%"
                  % (subject, fi+1, nf, 100*(CL[fi] >= LPCORR_MIN).mean()), flush=True)
    np.savez_compressed(p, sites=sites, M=M, A=A, C=C, CL=CL,
                        frames=np.array([os.path.basename(f) for f in frames]))
    return dict(np.load(p, allow_pickle=True))
