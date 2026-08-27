"""Audit every gate. A refusal rate of 164/238 on TEXT is not a property of the
subject, it is a defect in the gate. Find which gate and why.
"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands as SB, sharp_F as SF

print("%-20s %6s %7s %7s %7s %7s %7s %8s %8s" % ("subject","sites","frames",
      "corrOK%","loOK%","nzOK%","allOK%","medSA","medSM"))
print("-"*96)
for subj in sys.argv[1:]:
    z = SB.build(subj)
    M = z["M"].astype(np.float64); A = z["A"].astype(np.float64); C = z["C"]
    nf, ns = A.shape[0], A.shape[1]
    nfM = SF.nfloor(M); DM, sM = SF.detail(M, nfM)
    LM = M[:, SF.B_LO]
    corr_ok = np.isfinite(A[:, :, 0])
    LA = np.where(corr_ok, A[:, :, SF.B_LO], np.nan)
    rlo = LM[None, :] / LA
    lo_ok = corr_ok & (rlo >= SF.GATE_LO) & (rlo <= SF.GATE_HI)
    sA = np.full((nf, ns), np.nan)
    for k in range(nf):
        ok = corr_ok[k]
        if ok.sum() < 5: continue
        _, s = SF.detail(A[k], SF.nfloor(A[k][ok]))
        sA[k][ok] = s[ok]
    nz_ok = lo_ok & (sA >= SF.NOISE_MAX)
    tot = nf * ns
    print("%-20s %6d %7d %6.1f%% %6.1f%% %6.1f%% %6.1f%% %8.3f %8.3f"
          % (subj, ns, nf, 100.0*corr_ok.sum()/tot, 100.0*lo_ok.sum()/tot,
             100.0*nz_ok.sum()/tot, 100.0*nz_ok.sum()/tot,
             float(np.nanmedian(sA)), float(np.nanmedian(sM))))
print()
print("corrOK% = registered above 0.60. loOK% = also passes the content gate.")
print("nzOK%   = also has a signal-dominated detail band.")
print("medSA/medSM = median signal fraction of the detail band, frames / master.")
print("A signal fraction near 0 on a TEXTURED subject means the noise estimator")
print("is over-subtracting, not that the subject has no detail.")
