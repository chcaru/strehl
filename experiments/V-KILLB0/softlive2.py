"""V-KILLB0 softlive2.py -- close the subject confound on the pyramid arm."""
import numpy as np, tifffile
D = r"D:\strehl-out\V-KILLB0\softgate"

def cmp(tag, pa, pb):
    A = tifffile.imread(pa); B = tifffile.imread(pb)
    if A.shape != B.shape: raise SystemExit("FATAL shape mismatch "+tag)
    d = A.astype(np.int64) - B.astype(np.int64)
    nz = int(np.count_nonzero(d))
    print("%-46s n_diff=%9d / %9d (%7.4f%%) maxabs=%5d  median=%8.1f clip=%.4f%% black=%.4f%%"
          % (tag, nz, d.size, 100.0*nz/d.size, int(np.abs(d).max()),
             float(np.median(A)), 100.0*float(np.mean(A>=65535)), 100.0*float(np.mean(A<=0))))
    return nz

print("=== PYRAMID default backend, SAME SUBJECT as the estimator arm ===")
a = cmp("112MSDCF  gaussian vs unset   [pyramid]", D+r"\g_pyr_112.tiff", D+r"\u_pyr_112.tiff")
print()
print("=== PYRAMID default backend, ASSIGNED SUBJECT bee-1-cpl --srgb ===")
b = cmp("bee-1-cpl exponential vs unset [pyramid,srgb]", D+r"\e_pyr_bee.tiff", D+r"\u_pyr_bee.tiff")
print()
print("=== reference: ESTIMATOR backend, same 112MSDCF frames ===")
c = cmp("112MSDCF  gaussian vs unset   [estimator]", D+r"\gauss_est.tiff", D+r"\unset_est.tiff")
print()
print("PYRAMID moved %d and %d samples; ESTIMATOR moved %d." % (a,b,c))
print("CONCLUSION: %s" % ("soft gate INERT on shipping merge, LIVE on estimator only"
      if (a==0 and b==0 and c>0) else "MIXED -- re-examine"))
