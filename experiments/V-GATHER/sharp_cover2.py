import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands as SB, sharp_F2 as S2
print("%-20s %6s %7s %8s %8s %8s %8s" % ("subject","sites","frames","regOK%","contOK%","measured","med resp"))
print("-"*72)
for subj in sys.argv[1:]:
    z = SB.build(subj); r = S2.evaluate(z); s = S2.summarise(r)
    A = z["A"].astype(np.float64)
    reg = np.isfinite(A[:, :, 0]); tot = A.shape[0]*A.shape[1]
    HM = z["M"].astype(np.float64)[:, S2.B_ANCHOR]
    LA = np.where(reg, A[:, :, S2.B_ANCHOR], np.nan)
    rlo = HM[None, :]/LA
    cont = reg & (rlo >= S2.GATE_LO) & (rlo <= S2.GATE_HI)
    print("%-20s %6d %7d %7.1f%% %7.1f%% %8s %8.2f"
          % (subj, r["nsites"], r["nframes"], 100.0*reg.sum()/tot, 100.0*cont.sum()/tot,
             (s[3] if s else 0), float(np.nanmedian(r["resp"]))))
