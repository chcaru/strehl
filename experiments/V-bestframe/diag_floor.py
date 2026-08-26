"""Inspect the fixed-pattern control per subject. The floor F is what every SNR
and every ratio is measured against, so a collapsed or NaN floor silently
rewrites the ranking. Print the inputs to F, not just F."""
import numpy as np, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME")
GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB")
DISP_MIN = 20.0
print(f"{'subject':36s} {'gap':>8} {'dispMin':>8} {'dispMed':>8} {'dispMax':>8} "
      f"{'nTile>=20':>9} {'sqrtZmed':>9} {'nFiniteZ':>9}")
print("-"*106)
for s in sorted(p.stem for p in GAL.glob("*.tiff")):
    fp = sorted(OUT.glob(f"{s}__fpn_k*.npz"))[0]
    f = np.load(fp)
    d, Z = f["disp"], f["Z"]
    m = d >= DISP_MIN
    sel = np.where(m, np.maximum(Z, 0.0), np.nan)
    nf = int(np.sum(np.isfinite(sel)))
    zz = np.nanmedian(sel) if nf else np.nan
    print(f"{s:36s} {fp.name.split('__')[1][4:-4]:>8} {np.nanmin(d):8.1f} "
          f"{np.nanmedian(d):8.1f} {np.nanmax(d):8.1f} {int(m.sum()):9d} "
          f"{np.sqrt(zz) if np.isfinite(zz) else float('nan'):9.2f} {nf:9d}")
