#!/usr/bin/env python3
"""Is the noise gate genuinely two-sided, and what does it cost?

Re-runs the SHIPPED classifier three ways over BUILD-TRIAGE's own evidence:
  as shipped        - both arms must clear 4x noise before a site may say "loss"
  merge-only gate   - the pre-fix behaviour the commit says was reversed
  no gate at all    - every reliable non-FLAT site votes
"""
from __future__ import annotations

import json
import os
import sys

BT = r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-TRIAGE"
sys.path.insert(0, BT)
import tri  # noqa: E402
import triage  # noqa: E402

tri.OUT = r"C:\dev\strehl-out\BUILD-TRIAGE"
SNR = 4.0


def gate(v, mode):
    """True = drop this site."""
    e = v.get("edge") or {}
    m, f = e.get("merge_dnpx", 0.0), e.get("frame_corr_dnpx", 0.0)
    nm, nf = e.get("noise_merge_dn", 0.0), e.get("noise_frame_dn", 0.0)
    if mode == "none":
        return False
    if nm > 0 and m < SNR * nm:
        return True
    if mode == "shipped" and e.get("ratio", 1.0) < 1.0 and nf > 0 and f < SNR * nf:
        return True
    return False


def worst(sub, mode):
    with open(os.path.join(tri.OUT, "compare", sub + ".json"), encoding="utf-8") as fh:
        c = json.load(fh)
    keep = {k: v for k, v in c["sites"].items()
            if k != "FLAT" and v.get("reliable", True) and not gate(v, mode)}
    if not keep:
        return None, None
    b = {k: v["edge"]["blur_equiv_px"] for k, v in keep.items()}
    k = max(b, key=b.get)
    return b[k], k


def main() -> int:
    print(f"{'subject':<36} {'shipped':>18} {'merge-only gate':>22} {'no gate':>18}")
    flips = {"shipped": [], "merge": [], "none": []}
    for s in tri.SUBJECTS:
        row = []
        for mode in ("shipped", "merge", "none"):
            w, site = worst(s, mode)
            row.append((w, site))
            if w is not None and w >= triage.BLUR_BAD_PX:
                flips[mode].append(s)
        print(f"{s:<36} "
              + " ".join(f"{('n/a' if w is None else f'{w:.2f}'):>8} @{str(k):<12}"
                         for w, k in row))
    print()
    print(f"threshold {triage.BLUR_BAD_PX} px -- sites exceeding it, per gate "
          f"(before the motion/coverage adjudication that runs first):")
    for mode in ("shipped", "merge", "none"):
        print(f"  {mode:<12} {len(flips[mode]):>2}  {', '.join(flips[mode]) or '-'}")
    print()
    print("full classifier verdicts under the pre-fix MERGE-ONLY gate")
    print("(patched into triage.classify via its own module globals):")
    ev = {s: triage.load(s) for s in tri.SUBJECTS}
    base = {s: triage.classify(s, ev[s])["verdict"] for s in tri.SUBJECTS}
    for s in tri.SUBJECTS:
        w_ship, _ = worst(s, "shipped")
        w_merge, site = worst(s, "merge")
        if (w_merge or 0) >= triage.BLUR_BAD_PX and (w_ship or 0) < triage.BLUR_BAD_PX:
            print(f"  {s:<36} shipped={base[s]:<32} merge-only would raise "
                  f"{w_merge:.2f} px at {site}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
