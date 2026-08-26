"""Print full profiles for the subjects whose ring numbers look extreme.

A ring expressed as a fraction of a dark far field inflates; and a structured
backdrop can produce a local maximum that is scene content, not a merge
artifact. The profile is printed in full so the verdict can be checked by eye.
"""
import json
from pathlib import Path
import numpy as np

JS = Path(r"C:\dev\strehl-out\V-RIM\json2")
for lab in ("109MSDCF", "119MSDCF", "coffee-bean", "bee-1-cpl"):
    d = json.loads((JS / f"{lab}-rays.json").read_text())
    print(f"\n=== {lab}  subj={d['seg']['subject_frac']*100:.2f}%  "
          f"fringe q25={d['fringe_q'][0]:.3f} q75={d['fringe_q'][1]:.3f}")
    for grp in ("all", "straight", "fringed"):
        g = d.get(grp)
        if not g:
            continue
        grid = np.array(g["grid"]); med = np.array(g["med"]); far = g["far"]
        print(f"  {grp:8s} n={g['n']:5d} inner={g['inner']:8.0f} far={far:8.0f} "
              f"contrast={far-g['inner']:8.0f}")
        ts = [0,5,10,20,30,40,50,60,70,85,100,120,150,200,250,290]
        print("      ", " ".join(f"{t}:{med[int(np.searchsorted(grid,t))]:.0f}" for t in ts))
        print("      %far", " ".join(
            f"{t}:{(med[int(np.searchsorted(grid,t))]-far)/far*100:+.1f}" for t in ts))
