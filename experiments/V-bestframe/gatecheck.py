"""Gated vs ungated, side by side. The gate must be shown to matter or not matter."""
import numpy as np
from curve import arms, curve

for g in (0.0, 0.80):
    print("=" * 78)
    print(f"REGISTRATION PEAK GATE = {g:.2f}" + ("  (no gate)" if g == 0 else ""))
    for s in ("bee-1-cpl", "flowers-cpl"):
        a = arms(s, peak_min=g)
        real = a["snr"] >= 3.0
        cand = real & (a["ratio"] < 0.80)
        print(f"  {s:14s} {a['na']:2d} pairs used, {a['ngate']} gated out")
        print(f"    real-detail tiles (SNR>=3)          {int(real.sum()):3d}/352 = "
              f"{100*real.mean():5.1f}%")
        print(f"    merge >= best frame on those        {100*np.mean(a['ratio'][real] >= 1.0):5.1f}%"
              f"   median ratio {np.nanmedian(a['ratio'][real]):.3f}")
        print(f"    H2 candidates (ratio<0.80)          {int(cand.sum()):3d} = "
              f"{100*cand.sum()/max(real.sum(),1):4.1f}% of real-detail tiles")
print("=" * 78)
for s in ("bee-1-cpl", "flowers-cpl"):
    curve(s, a=arms(s, peak_min=0.80), label=f"{s}  [peak gate 0.80]")
