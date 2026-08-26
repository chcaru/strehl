"""Drive BUILD-THESIS's OWN invert() with an infinitesimal difference.

If a 1-part-in-10^6 difference inverts to ~0.4 px, then the +-0.34..0.49 px
cluster in the headline table and the +-0.2..0.5 px "noise null" beside it are
the same floor artifact, and their equality is not evidence of anything.

Imports blureq.invert and stats.STATS unmodified -- this is THEIR code.
"""
import pathlib, sys
import numpy as np, tifffile
sys.path.insert(0, str(pathlib.Path("experiments/BUILD-THESIS").resolve()))
from stats import STATS                 # BUILD-THESIS's statistics, unmodified
from blureq import invert, LADDER       # BUILD-THESIS's inversion, unmodified

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
t = tifffile.imread(str(R/"leaf-2-cpl"/"merge.tif"))[900:1700,1400:2200,1].astype(np.float64)

print("LADDER[:10] =", LADDER[:10])
print("\nWhat does the ladder actually do to each statistic?")
print(f"{'sigma':>7}" + "".join(f"{k:>14}" for k in STATS))
from scipy.ndimage import gaussian_filter
base = {k: fn(t) for k, fn in STATS.items()}
for s in (0.0,0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.45,0.50,0.60):
    tb = gaussian_filter(t, s) if s > 0 else t
    print(f"{s:>7.2f}" + "".join(f"{STATS[k](tb)/base[k]:>14.6f}" for k in STATS))

print("\nINVERT() DRIVEN BY AN INFINITESIMAL TARGET (correct answer ~ 0.000)")
print(f"{'relative deficit':>18}" + "".join(f"{k:>14}" for k in STATS))
for eps in (1e-6, 1e-4, 1e-3, 3e-3, 1e-2, 3e-2, 1e-1):
    row = {}
    for k, fn in STATS.items():
        row[k] = invert(t, base[k]*(1.0-eps), fn)
    print(f"{eps:>18.0e}" + "".join(f"{row[k]:>14.3f}" for k in STATS))
