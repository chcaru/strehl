"""Why did the 299-frame subjects refuse? Audit the gate on a DEEP stack."""
import os, sys, numpy as np, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sharp_bands as SB, sharp_F2 as S2
for s in ("couch-fibers-cpl", "lavendar-cpl", "119MSDCF"):
    z = dict(SB.build(s))
    A = z["A"].astype(np.float64); M = z["M"].astype(np.float64)
    HA = A[:, :, S2.B_HI].sum(axis=2); LA = A[:, :, S2.B_ANCHOR]
    LM = M[:, S2.B_ANCHOR]
    reg = np.isfinite(HA)
    gn = float(np.nanmedian(np.where(reg, LA / LM[None, :], np.nan)))
    rlo = (LM[None, :] * gn) / LA
    content = reg & (rlo >= S2.GATE_LO) & (rlo <= S2.GATE_HI)
    print("%-18s %d frames %d sites" % (s, A.shape[0], A.shape[1]))
    print("   registered  %5.1f%% of frame-site pairs" % (100 * reg.mean()))
    print("   pass CONTENT %5.1f%%   median frames passing per site %.1f"
          % (100 * content.mean(), float(np.median(content.sum(axis=0)))))
    print("   sites with >=4 content-passing frames: %5.1f%%"
          % (100 * (content.sum(axis=0) >= 4).mean()))
    print("   -> the CONTENT gate rejects a frame whose 0.02-0.05 cyc/px band")
    print("      has collapsed, which on a DEEP stack is exactly what strong")
    print("      defocus does. The gate removes the very frames that prove a")
    print("      single frame has limited depth of field.")
