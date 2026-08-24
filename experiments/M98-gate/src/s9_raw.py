"""M98 -- per-tercile RAW A_hf (M85's own instrument, no noise subtraction).

Kept separate from s7 so that the noise-subtracted headline and M85's raw
quantity are never confused for one another.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m98lib as M98  # noqa: E402

d = json.load(open(os.path.join(M98.OUT, "s4_bee-3-cpl.json")))
hp = np.array(d["hp_sd"], float)
th = np.array_split(np.argsort(hp), 3)

print("bee-3-cpl gate 4 / gate 0, band f in [0.15, 0.2762] cyc/px")
print("  raw   = M85's quantity: single-render band amplitude, noise included")
print("  clean = the same after subtracting the measured above-cutoff floor")
for arm in ("ALN", "ZOOM"):
    A = d["arms"][arm]["per_gate"]
    print(f"\n  --- {arm} ---")
    for nm, idx in zip(("LOW", "MID", "HIGH"), th):
        r = np.array([A["4"][k]["raw_ratio"] for k in idx], float)
        c = np.array([A["4"][k]["clean_ratio"] for k in idx], float)
        print(f"    {nm:>4} hp_sd {hp[idx].min():.0f}-{hp[idx].max():.0f}   "
              f"raw {r.mean():.4f} +/- {r.std(ddof=1) / np.sqrt(r.size):.4f}"
              f"   clean {c.mean():.4f} "
              f"+/- {c.std(ddof=1) / np.sqrt(c.size):.4f}")
    k = int(np.argmax(hp))
    row = A["4"][k]
    print(f"    single sharpest ROI #{k} (hp_sd {hp[k]:.0f}): "
          f"raw {row['raw_ratio']:.4f}  clean {row['clean_ratio']:.4f}  "
          f"dsig {row['dsig']:+.4f} px")
    for g in ("0.5", "1", "2", "4"):
        rr = A[g][k]
        print(f"      gate {g:>3}  raw {rr['raw_ratio']:.4f}  "
              f"clean {rr['clean_ratio']:.4f}  dsig {rr['dsig']:+.4f} px  "
              f"noise {np.sqrt(rr['floor_ratio']):.4f}x")
