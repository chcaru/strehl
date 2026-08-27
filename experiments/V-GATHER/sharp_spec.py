"""Why do E and orig disagree by 15x on coffee-bubbles? Look at the spectra.

E = HI/LO band energy. It is amplitude-invariant, which is what made it survive
commissioning. But amplitude-invariance says nothing about whether the HI band
holds DETAIL or NOISE, and on a smooth subject the high band of a single frame
is mostly read noise while the master has averaged that noise down. If that is
what is happening, E is reading noise suppression as softness -- the same class
of error as a ringing statistic that actually measures aliasing.
"""
import os, sys, glob, numpy as np, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma, acutance, P, SEARCH
import sharp_diag as SD

ROOT = r"C:\dev\strehl-out\V-GATHER\sharp"
BANDS = [(0.02,0.06),(0.06,0.10),(0.10,0.15),(0.15,0.20),(0.20,0.25),
         (0.25,0.30),(0.30,0.35),(0.35,0.42),(0.42,0.50)]


def radial(y):
    n = y.shape[0]
    w = np.outer(np.hanning(n), np.hanning(n))
    pw = np.abs(np.fft.fft2((y - y.mean()) * w)) ** 2
    fy = np.fft.fftfreq(n)[:, None]; fx = np.fft.fftfreq(n)[None, :]
    rf = np.sqrt(fy*fy + fx*fx)
    return [float(pw[(rf >= a) & (rf < b)].mean()) for a, b in BANDS]


def main(subj="coffee-bubbles"):
    r = SD.cached(subj)
    sites = r["sites"]; A = r["A"]; M = r["M"]; C = r["C"]; SH = r["SH"]
    frames = [str(f) for f in r["frames"]]
    nreg = np.isfinite(A).sum(axis=0)
    amax = np.where(nreg >= 3, np.nanmax(np.where(np.isfinite(A), A, -np.inf), axis=0), np.nan)
    bestk = np.where(nreg >= 3, np.nanargmax(np.where(np.isfinite(A), A, -np.inf), axis=0), -1)
    rat = M / amax
    ok = np.isfinite(rat) & (nreg >= 3)
    idx = np.where(ok)[0]
    worst = idx[np.argsort(rat[idx])][:4]
    best = idx[np.argsort(rat[idx])][-4:]

    my = luma(tifffile.imread(os.path.join(ROOT, subj, "MASTER.tiff"))[..., :3].astype(np.float32))
    cache = {}
    def fy(k):
        if k not in cache:
            cache[k] = luma(tifffile.imread(os.path.join(ROOT, subj, frames[k]))[..., :3].astype(np.float32))
        return cache[k]

    hdr = "  ".join("%.2f-%.2f" % b for b in BANDS)
    for tag, sel in (("LOWEST master/best", worst), ("HIGHEST master/best", best)):
        print("\n########## %s ##########" % tag)
        for si in sel:
            y, x = sites[si]; k = int(bestk[si])
            dy, dx = SH[k, si]
            mp = my[y:y+P, x:x+P]
            fp = fy(k)[y+dy:y+dy+P, x+dx:x+dx+P]
            rm, rf_ = radial(mp), radial(fp)
            print("\nsite(%d,%d) ratio=%.4f  best=%s corr=%.3f shift=(%d,%d)"
                  % (y, x, rat[si], frames[k], C[k, si], dy, dx))
            print("  mean DN  master %8.1f  frame %8.1f   std  master %7.1f  frame %7.1f"
                  % (mp.mean(), fp.mean(), mp.std(), fp.std()))
            print("  band          " + hdr)
            print("  master   " + "  ".join("%9.3e" % v for v in rm))
            print("  frame    " + "  ".join("%9.3e" % v for v in rf_))
            print("  M/F      " + "  ".join("%9.3f" % (a/b if b else np.nan) for a, b in zip(rm, rf_)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles")
