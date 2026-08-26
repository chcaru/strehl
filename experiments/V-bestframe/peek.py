"""Early targeted look at the crux subjects, before the full survey finishes.
Same curve.arms(), reloaded per gallery. No floor-family gate here because it
needs the whole gallery to define the family; raw numbers only."""
import os, importlib, warnings, sys
import numpy as np
warnings.filterwarnings("ignore")
GALS = {"GAL": (r"C:\dev\strehl-out\GALLERY-FIXED-SRGB", r"C:\dev\strehl-out\V-BESTFRAME"),
        "SHIP": (r"C:\dev\strehl-out\SHIP-V1", r"C:\dev\strehl-out\V-BESTFRAME-SHIP")}
subs = sys.argv[1:]
print(f"{'subject':24s} {'gallery':5s} {'floor':>7} {'mfloor':>8} {'detail':>7} "
      f"{'merge>=frm':>10} {'medR':>6} {'p05':>6} {'<0.8':>5}")
print("-" * 88)
for s in subs:
    for tag, (g, o) in GALS.items():
        os.environ["VBF_GAL"] = g; os.environ["VBF_OUT"] = o
        import paircov, peaks, curve
        importlib.reload(paircov); importlib.reload(peaks); importlib.reload(curve)
        try:
            a = curve.arms(s, peak_min=0.80)
        except Exception as e:
            print(f"{s:24s} {tag:5s} arms() raised {type(e).__name__}: {e}"); continue
        fl = float(np.sqrt(np.nanmedian(a["F"])))
        fm = float(np.sqrt(a["Fm"]))
        real = np.isfinite(a["snr"]) & (a["snr"] >= 3.0)
        Smt = np.maximum(a["Em"] - np.minimum(a["Fm"], a["F"]), 0.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            rc = np.sqrt(Smt) / np.sqrt(np.maximum(a["Sft"], 1e-12))
        r = rc[real]
        print(f"{s:24s} {tag:5s} {fl:7.2f} {fm:8.2f} {int(real.sum()):3d}/352 "
              f"{np.mean(r >= 1.0)*100:9.1f}% {np.nanmedian(r):6.2f} "
              f"{np.nanpercentile(r,5):6.3f} {int(np.sum(r < 0.80)):5d}")
    print()
