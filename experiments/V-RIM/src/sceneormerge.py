"""Is the ring in the SCENE or in the MERGE?

The merged render and a single frame of the same bracket, through the same
pipeline, same binary, same flags. If a single frame shows the same ring then
the merge did not emit it and the mechanism in C2 is wrong whatever the
morphology correlation says.

Both are profiled by the same registered-ray method, and the single frame's
rays are anchored on ITS OWN mask, so neither inherits the other's geometry.
"""
import json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, r"C:\dev\strehl-out\V-RIM")
import vrim_rays

pairs = [
    (r"C:\dev\strehl-out\ORCH-rim\cb-1cacb61-lin.tif", "cb-MERGE"),
    (r"C:\dev\strehl-out\V-RIM\cb-frame52-lin.tif",    "cb-FRAME52"),
]
out = {}
for src, lab in pairs:
    out[lab] = vrim_rays.run(Path(src), lab, r"C:\dev\strehl-out\V-RIM\json3", "G")

print()
print("SCENE-OR-MERGE, coffee-bean")
print("  variant       group        n     edge %far    ring t    ring %")
for lab in out:
    for k in ("all", "straight", "fringed"):
        r = out[lab].get(k)
        if not r:
            continue
        rg = r["ring"]
        print(f"  {lab:12s} {k:9s} {r['n']:6d}  {r['frac1']*100:+9.2f}  "
              f"{(rg['t'] if rg else float('nan')):7.0f}  "
              f"{(rg['frac']*100 if rg else float('nan')):+7.2f}")
