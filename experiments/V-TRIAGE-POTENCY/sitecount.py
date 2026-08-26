#!/usr/bin/env python3
"""Count the sites the headline rests on, and the per-site gather cost spread."""
from __future__ import annotations

import json
import os
import sys

BT = r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-TRIAGE"
sys.path.insert(0, BT)
import tri  # noqa: E402
import triage  # noqa: E402

tri.OUT = r"C:\dev\strehl-out\BUILD-TRIAGE"


def weak(v):
    if any("not clear of" in c for c in v.get("caution", [])):
        return True
    e = v.get("edge") or {}
    m, f = e.get("merge_dnpx", 0.0), e.get("frame_corr_dnpx", 0.0)
    nm, nf = e.get("noise_merge_dn", 0.0), e.get("noise_frame_dn", 0.0)
    if nm > 0 and m < 4.0 * nm:
        return True
    if e.get("ratio", 1.0) < 1.0 and nf > 0 and f < 4.0 * nf:
        return True
    return False


def main() -> int:
    tot = kept = 0
    kept_distinct = set()
    all_distinct = set()
    costs = []
    dup_labels = 0
    for s in tri.SUBJECTS:
        p = os.path.join(tri.OUT, "compare", s + ".json")
        with open(p, encoding="utf-8") as fh:
            c = json.load(fh)
        blocks_kept = set()
        for k, v in c["sites"].items():
            tot += 1
            all_distinct.add((s, tuple(v["block"])))
            costs.append((s, k, v["edge"]["gather_cost"], v["high"]["gather_cost"],
                          v["high"]["cost_shift"], v["high"]["cost_scale"]))
            if k != "FLAT" and v.get("reliable", True) and not weak(v):
                kept += 1
                if tuple(v["block"]) in blocks_kept:
                    dup_labels += 1
                blocks_kept.add(tuple(v["block"]))
                kept_distinct.add((s, tuple(v["block"])))
    print(f"sites measured (all labels, all subjects)      : {tot}")
    print(f"sites kept by the gate (what the headline uses): {kept}")
    print(f"  of which DISTINCT (subject, block)           : {len(kept_distinct)}")
    print(f"  duplicate labels on the same block           : {dup_labels}")
    print(f"distinct (subject, block) measured at all      : {len(all_distinct)}")
    print()
    ec = [c[2] for c in costs]
    hc = [c[3] for c in costs]
    print(f"EDGE gather cost per site  : n={len(ec)} min={min(ec):.4f} "
          f"max={max(ec):.4f} mean={sum(ec)/len(ec):.4f}")
    print(f"  distinct values          : {len(set(ec))}  (a fitted-once constant "
          f"would show 1)")
    print(f"  above 1.0 (unphysical for a blur): "
          f"{sum(1 for x in ec if x > 1.0)} of {len(ec)}, max {max(ec):.4f}")
    print(f"BAND gather cost per site  : min={min(hc):.4f} max={max(hc):.4f}")
    print()
    print("the 10 sites with the largest edge-cost departure from 1.0:")
    for s, k, e, h, cs, csc in sorted(costs, key=lambda r: -abs(1 - r[2]))[:10]:
        print(f"   {s:<36} {k:<12} edge_cost={e:.4f}  band_cost={h:.4f} "
              f"(shift {cs:.4f} / scale {csc:.4f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
