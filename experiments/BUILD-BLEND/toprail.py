import numpy as np, tifffile
from pathlib import Path
F = [("pyramid  linear", r"C:\dev\strehl-out\BUILD-BLEND\clip\fb-clamped.tiff"),
     ("pyramid  flip",   r"C:\dev\strehl-out\BUILD-BLEND\flip\flower-bud-alone-cpl--pyramid.tiff"),
     ("estimator flip",  r"C:\dev\strehl-out\BUILD-BLEND\flip\flower-bud-alone-cpl--estimator.tiff")]
print(f"{'arm':<18}{'ch':<3}{'==65535':>12}{'pct':>9}{'>=65000':>12}{'pct':>9}")
print("-"*63)
res={}
for lab,p in F:
    a = tifffile.imread(p); h,w,_ = a.shape; t=h*w
    for ci,cn in enumerate("RGB"):
        ch=a[:,:,ci]; s=int((ch==65535).sum()); n=int((ch>=65000).sum())
        res[(lab,cn)]=100*s/t
        print(f"{lab:<18}{cn:<3}{s:>12,}{100*s/t:>8.3f}%{n:>12,}{100*n/t:>8.3f}%")
    print()
print("="*63); print("TOP-RAIL DELTA, pyramid - estimator (percentage points)")
for cn in "RGB":
    d = res[("pyramid  flip",cn)] - res[("estimator flip",cn)]
    flag = "  <-- REAL, in the merge" if abs(d)>1.0 else ""
    print(f"  {cn}: {d:+7.3f} pt{flag}")
