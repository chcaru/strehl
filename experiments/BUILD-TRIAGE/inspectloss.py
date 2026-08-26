"""Inspect the sites that the headline calls merge-limited, in absolute DN."""
from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

with open(os.path.join(tri.OUT, "headline.json"), encoding="utf-8") as fh:
    H = json.load(fh)

print(f"{'subject':<36} {'site':<12} {'merge':>7} {'frame':>7} "
      f"{'noiseM':>7} {'noiseF':>7} {'floorM':>7} {'floorF':>7} {'ratio':>6} "
      f"{'frameSNR':>8}")
print("-" * 118)
for r in H["rows"]:
    if not r["losing"]:
        continue
    p = os.path.join(tri.OUT, "compare", r["subject"] + ".ns.json")
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    for label, ratio, dfc in r["losing"]:
        s = d["sites"][label]
        e = s["edge"]
        # How far above its own grain floor does each arm actually sit?
        snr_f = e["frame_dnpx"] / max(e["edge_noise_floor_frame_dnpx"], 1e-9)
        print(f"{r['subject']:<36} {label:<12} {e['merge_dnpx']:>7.1f} "
              f"{e['frame_dnpx']:>7.1f} {e['noise_merge_dn']:>7.1f} "
              f"{e['noise_frame_dn']:>7.1f} "
              f"{e['edge_noise_floor_merge_dnpx']:>7.1f} "
              f"{e['edge_noise_floor_frame_dnpx']:>7.1f} {ratio:>6.3f} "
              f"{snr_f:>8.2f}   @({s['x']},{s['y']}) f{s.get('best_frame')}")
