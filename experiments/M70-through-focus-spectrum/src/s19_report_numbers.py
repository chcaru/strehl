"""M70 s19 - exact null-sd multiples quoted in the report's section 16.

Every number in section 16.5 that is stated as "N null sd from zero" is computed
here rather than eyeballed from the s16 table.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

nb = json.load(open(os.path.join(OUT, "s16_null_band.json")))
S = json.load(open(os.path.join(OUT, "s15_asym_corpus.json")))["stacks"]

z = {}
print(f"{'stack':<16}{'K':>5}{'obs':>10}{'null sd':>10}{'z':>10}{'powered':>9}")
for st, e in nb.items():
    q = e["A50"]
    z[st] = abs(q["obs"]) / q["null_sd"]
    print(f"{st:<16}{e['K']:>5}{q['obs']:>+10.4f}{q['null_sd']:>10.4f}"
          f"{z[st]:>10.1f}{('YES' if q['outside'] else 'no'):>9}")

pw = [s for s in nb if nb[s]["A50"]["outside"]]
print(f"\npowered stacks n={len(pw)}: z range {min(z[s] for s in pw):.1f} - "
      f"{max(z[s] for s in pw):.1f}")
print("bees      z: " + ", ".join(f"{z[s]:.1f}" for s in ("bee-1", "bee-2", "bee-3")))
print("wrapped   z: " + ", ".join(f"{z[s]:.1f}" for s in
                                  ("wrapped-text-1", "wrapped-text-2")))

ag = [S[s]["agree_A50"] for s in nb]
print(f"\nwithin-stack sign agreement (A50): median {np.median(ag):.4f}  "
      f"range {min(ag):.3f}-{max(ag):.3f}")

a = np.array([S[s]["A50"] for s in nb])
print(f"A50 stack medians: min {a.min():+.4f} max {a.max():+.4f} "
      f"median-of-medians {np.median(a):+.4f}  max|A50| {np.abs(a).max():.4f}")
r = (1 + np.abs(a).max()) / (1 - np.abs(a).max())
print(f"max |A50| = {np.abs(a).max():.4f}  ->  worst half-width ratio "
      f"w_far/w_near = {r:.3f}")
rm = (1 + np.median(np.abs(a))) / (1 - np.median(np.abs(a)))
print(f"med |A50| = {np.median(np.abs(a)):.4f}  ->  typical ratio {rm:.3f}")

sd = np.array([nb[s]["A50"]["null_sd"] for s in nb])
print(f"\nnull sd range {sd.min():.4f} - {sd.max():.4f}  = {sd.max() / sd.min():.0f}x")

json.dump({"z": z, "agree_median": float(np.median(ag)),
           "max_absA50": float(np.abs(a).max()), "worst_ratio": float(r),
           "typ_ratio": float(rm), "nullsd_span": float(sd.max() / sd.min())},
          open(os.path.join(OUT, "s19_report_numbers.json"), "w"), indent=1)
print("\nwrote out/s19_report_numbers.json")
