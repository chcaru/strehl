"""Which apertures are actually in band? Read the guard, do not guess.

knee_model_fit's `above_reach` flag is the out-of-band detector M5's commissioning
validated at 36/36 with no false alarms, and floor_flatness is explicitly recorded
there as NOT working for this job. So this asks the validated guard.

It matters because ladder.py's measured means cluster: f/5.6 0.2771, f/8 0.2955,
f/11 0.2946, then f/14 0.2753 and f/18 0.2311. Three apertures reporting nearly the
same cutoff is what saturation against the lattice reach looks like, not what
diffraction looks like.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
TAGS = ["f5.6", "f8", "f11", "f14", "f18"]

d = json.load(open(os.path.join(OUT, "ladder.json"), encoding="utf-8"))
cells = d["cells"]

print("the out-of-band guard, per aperture")
print("=" * 74)
print(f"  {'ap':>6} {'above_reach':>12} {'fit ok':>7} {'knee f_c':>9} "
      f"{'fit f_c':>9} {'dyn range':>10} {'floor slope':>12}")
rows = []
for t in TAGS:
    r = [x for x in cells if x["aperture"] == t]
    ar = sum(1 for x in r if x["above_reach"])
    ok = sum(1 for x in r if x["fit_ok"])
    kf = float(np.mean([x["f_c"] for x in r]))
    ff = [x["fit_f_c"] for x in r if x["fit_f_c"] is not None]
    dy = float(np.median([x["dyn"] for x in r]))
    fs = [x["floor_slope"] for x in r if x["floor_slope"] is not None]
    rows.append({"tag": t, "above_reach": ar, "n": len(r), "knee_fc": kf,
                 "fit_fc": float(np.mean(ff)) if ff else None,
                 "dyn": dy, "floor_slope": float(np.mean(fs)) if fs else None})
    print(f"  {t:>6} {str(ar) + '/' + str(len(r)):>12} {ok:>7} {kf:9.4f} "
          f"{(np.mean(ff) if ff else float('nan')):9.4f} {dy:10.1f} "
          f"{(np.mean(fs) if fs else float('nan')):12.3f}")

print()
print("  above_reach means the physical fit put the cutoff beyond the highest")
print("  frequency the lattice can measure. Where it fires, the crossing estimator")
print("  is not reporting a diffraction cutoff -- it is reporting where the")
print("  subject's own texture ran out of contrast, which is a property of the")
print("  fabric and not of the aperture.")

with open(os.path.join(OUT, "reach-guard.json"), "w", encoding="utf-8") as fh:
    json.dump(rows, fh, indent=1)
print("\nwrote out/reach-guard.json")
