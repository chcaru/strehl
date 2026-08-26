"""Where does the corpus itself put the boundary between evidence and grain?

`compare.py` reports an edge slope for both arms at every site.  A site is only
entitled to an opinion about the merge if BOTH arms actually carry edges --
otherwise the metric is comparing two grain fields, and since a merge averages
many frames and a single frame does not, the merge is up to 10x quieter and
loses automatically.

Rather than assert a signal-to-grain gate, read one off the measured
distribution, the way GAP_DETAIL_PCT was read off the coverage rates.
"""
from __future__ import annotations
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

rows = []
for p in sorted(glob.glob(os.path.join(tri.OUT, "compare", "*.ns.json"))):
    sub = os.path.basename(p)[:-len(".ns.json")]
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
    for label, s in d["sites"].items():
        e = s.get("edge") or {}
        if not e.get("sig_ratio"):
            continue
        fm = max(e["edge_noise_floor_merge_dnpx"], 1e-9)
        ff = max(e["edge_noise_floor_frame_dnpx"], 1e-9)
        rows.append({
            "subject": sub, "site": label,
            "snr_merge": e["merge_dnpx"] / fm,
            "snr_frame": e["frame_dnpx"] / ff,
            "min_snr": min(e["merge_dnpx"] / fm, e["frame_dnpx"] / ff),
            "merge_dnpx": e["merge_dnpx"],
            "ratio": e["sig_ratio"],
        })

v = np.array(sorted(r["min_snr"] for r in rows))
print(f"{len(rows)} sites; min(arm SNR to its own grain floor)")
print("  sorted:", "  ".join(f"{x:.2f}" for x in v))
gaps = np.diff(v)
i = int(np.argmax(gaps))
print(f"\nlargest gap in the distribution: {v[i]:.2f} -> {v[i+1]:.2f} "
      f"(x{v[i+1]/max(v[i],1e-9):.2f}, {gaps[i]:.2f} wide)")
print(f"{int((v <= v[i]).sum())} sites at or below, "
      f"{int((v > v[i]).sum())} above")

print("\nratio vs SNR -- if low ratios live only at low SNR the 'losses' are "
      "grain:")
for lo, hi in ((0, 2), (2, 3), (3, 6), (6, 12), (12, 1e9)):
    sel = [r for r in rows if lo <= r["min_snr"] < hi]
    if not sel:
        continue
    rr = np.array([r["ratio"] for r in sel])
    below = int((rr < 0.95).sum())
    print(f"  SNR {lo:>2}-{hi if hi < 1e9 else 'inf':>3}: {len(sel):>3} sites, "
          f"median ratio {np.median(rr):.3f}, "
          f"{below} below 0.95 ({100*below/len(sel):.0f}%), "
          f"median merge edge {np.median([r['merge_dnpx'] for r in sel]):.0f} DN/px")
