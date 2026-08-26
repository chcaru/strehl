"""Diagnose why some subjects report 0 detail tiles and why the shallow stacks
rank worst. Prints the floor and SNR machinery per subject so an instrument
failure cannot hide behind a low score."""
import numpy as np, warnings
from pathlib import Path
from curve import arms, DISP_MIN
from peaks import peaks_for

warnings.filterwarnings("ignore")
GAL = Path(r"C:\dev\strehl-out\GALLERY-FIXED-SRGB")
OUT = Path(r"C:\dev\strehl-out\V-BESTFRAME")
subs = sorted(p.stem for p in GAL.glob("*.tiff"))
print(f"{'subject':36s} {'np':>3} {'gt':>3} {'pkMed':>6} {'Ffloor':>7} {'Fm':>8} "
      f"{'sqrtEm50':>8} {'snr50':>6} {'snr95':>6} {'empty':>6} {'fpnFile':>14}")
print("-"*118)
for s in subs:
    try:
        a = arms(s, peak_min=0.80)
    except Exception as e:
        print(f"{s:36s}  ERROR {type(e).__name__}: {e}"); continue
    pk = peaks_for(s, a["z"]["anchors"])
    fn = sorted(OUT.glob(f"{s}__fpn_k*.npz"))[0].name.split("__")[1][:-4]
    emp = float(np.mean(a["snr"] < 0.5) * 100)
    print(f"{s:36s} {a['na']:3d} {a['ngate']:3d} {np.nanmedian(pk):6.3f} "
          f"{np.sqrt(np.nanmedian(a['F'])):7.2f} {np.sqrt(a['Fm']):8.2f} "
          f"{np.sqrt(np.nanmedian(a['Em'])):8.2f} {np.nanmedian(a['snr']):6.2f} "
          f"{np.nanpercentile(a['snr'],95):6.2f} {emp:5.1f}% {fn:>14}")
