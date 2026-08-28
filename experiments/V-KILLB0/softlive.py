"""V-KILLB0 softlive.py -- is STREHL_SOFT_GATE live in the pixels?

Compares pixel ARRAYS, never file hashes: TIFF ImageDescription carries the
tool's own parameters, so two byte-different files can be pixel-identical and
two pixel-different files can hash-differ for irrelevant reasons.
"""
import sys, numpy as np, tifffile

def stats(a):
    x = a.astype(np.float64)
    return dict(median=float(np.median(x)),
                clip=100.0*float(np.mean(a >= 65535)),
                black=100.0*float(np.mean(a <= 0)))

def cmp(tag, pa, pb):
    A = tifffile.imread(pa); B = tifffile.imread(pb)
    if A.shape != B.shape:
        raise SystemExit("FATAL shape mismatch %s %s vs %s" % (tag, A.shape, B.shape))
    d = A.astype(np.int64) - B.astype(np.int64)
    nz = int(np.count_nonzero(d)); tot = int(d.size)
    sa, sb = stats(A), stats(B)
    print("%-34s n_diff=%10d / %10d  (%7.4f%%)  maxabs=%6d  meanabs=%.6f"
          % (tag, nz, tot, 100.0*nz/tot, int(np.abs(d).max()), float(np.abs(d).mean())))
    print("%-34s   A: median=%9.1f clip=%.4f%% black=%.4f%%   B: median=%9.1f clip=%.4f%% black=%.4f%%"
          % ("", sa['median'], sa['clip'], sa['black'], sb['median'], sb['clip'], sb['black']))
    return nz

D = r"D:\strehl-out\V-KILLB0\softgate"
print("=== PYRAMID (the SHIPPING default backend) ===")
n_pyr = cmp("gaussian vs unset [pyramid]", D+r"\gauss_default.tiff", D+r"\unset_default.tiff")
print()
print("=== ESTIMATOR (--merge estimator, NOT the default) ===")
n_est = cmp("gaussian vs unset [estimator]", D+r"\gauss_est.tiff", D+r"\unset_est.tiff")
n_exp = cmp("exponential vs unset [estimator]", D+r"\expo_est.tiff", D+r"\unset_est.tiff")
n_ge  = cmp("gaussian vs exponential [est]", D+r"\gauss_est.tiff", D+r"\expo_est.tiff")

print()
print("--- COMMISSIONING: the comparator must be able to see a difference at all ---")
A = tifffile.imread(D+r"\unset_est.tiff")
B = A.copy(); B[100, 100, 0] = 0 if A[100,100,0] != 0 else 1
d = int(np.count_nonzero(A.astype(np.int64)-B.astype(np.int64)))
print("planted 1-sample defect -> comparator reports n_diff=%d (must be 1)" % d)
if d != 1: raise SystemExit("FATAL comparator is dead")
dn = int(np.count_nonzero(A.astype(np.int64)-A.astype(np.int64)))
print("NULL same-array-vs-itself   -> n_diff=%d (must be 0)" % dn)
if dn != 0: raise SystemExit("FATAL null failed")

print()
print("VERDICT: soft gate on PYRAMID(default) moved %d samples; on ESTIMATOR moved %d samples." % (n_pyr, n_est))
if n_pyr == 0 and n_est > 0:
    print("=> STREHL_SOFT_GATE is INERT on the shipping merge and LIVE only on --merge estimator.")
