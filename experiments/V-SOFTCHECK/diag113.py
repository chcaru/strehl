import numpy as np, softcheck as S, hcoh as HC
d=r"C:\dev\strehl-out\V-SOFTCHECK\hcoh\113MSDCF"
A=S.load_luma(rf"{d}\N062-A.tiff","srgb"); B=S.load_luma(rf"{d}\N062-B.tiff","srgb")
ok,o=HC.commission(A,B); b0=o["BASE"]
for k,v in o.items(): print(f"  {k:32s} {v:.8f}")
deg=[o[f"DEGRADE_{a}"] for a in (0.01,0.03,0.10)]
for n,p in [("floor>2",o["FLOOR_GATE_ratio"]>2.0),("identity",o["IDENTITY"]<1e-6),
            ("offset",abs(o["NULL_OFFSET"]-b0)<1e-6),("gain",abs(o["NULL_GAIN"]-b0)<1e-6),
            ("shiftboth",abs(o["NULL_SHIFT_BOTH"]-b0)<5e-3),
            ("noise",abs(o["NOISE_NULL"]-o["NOISE_NULL_predicted"])<0.02),
            ("deg monotone",deg[0]<deg[1]<deg[2]),("deg>base",deg[0]>b0),
            ("improve",o["IMPROVE"]<0.25*b0)]:
    print(f"  {n:16s} {'pass' if p else 'FAIL'}")
