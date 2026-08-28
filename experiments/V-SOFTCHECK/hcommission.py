import sys, numpy as np, softcheck as S, hcoh as HC
d=r"C:\dev\strehl-out\V-SOFTCHECK\hcoh\119MSDCF"
A=S.load_luma(rf"{d}\N032-A.tiff","srgb"); B=S.load_luma(rf"{d}\N032-B.tiff","srgb")
print(f"ring bin counts per band: {HC.MBINS}")
print(f"primary band 0.20-0.25 has {HC.MBINS[HC.PRIMARY]} bins\n")
ok,o=HC.commission(A,B)
for k,v in o.items(): print(f"  {k:24s} {v:.6f}")
print(f"\n  COMMISSIONING {'PASSED' if ok else 'FAILED'}")
