#!/usr/bin/env python3
"""Print the ladder: verdict, site placement and per-site numbers per rung."""
import json
import os
import sys

BT = r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-TRIAGE"
sys.path.insert(0, BT)
import tri  # noqa: E402
import triage  # noqa: E402

ROOT = r"C:\dev\strehl-out\V-TRIAGE-POTENCY"


def main() -> int:
    sub = sys.argv[1]
    rungs = sys.argv[2:]
    print(f"{'rung':<8} {'sigma':>6} {'verdict':<16} {'worst_blur':>10} "
          f"{'worst_site':<12} {'ratio_min':>9}   per-site (block) blur/ratio")
    for tag in rungs:
        root = os.path.join(ROOT, tag)
        tri.OUT = root
        tri.LIN = os.path.join(root, "lin")
        ev = triage.load(sub)
        if "compare" not in ev:
            print(f"{tag:<8} (no compare json)")
            continue
        r = triage.classify(sub, ev)
        e = r["evidence"]
        sig = tag[1:]
        sites = ev["compare"]["sites"]
        detail = "  ".join(
            f"{k}({v['block'][0]},{v['block'][1]};f{v['best_frame']})="
            f"{v['edge']['blur_equiv_px']:.2f}/{v['edge']['ratio']:.3f}"
            for k, v in sites.items())
        wb = e.get("worst_blur_px")
        print(f"{tag:<8} {sig:>6} {r['verdict']:<16} "
              f"{(wb if wb is not None else float('nan')):>10.3f} "
              f"{str(e.get('worst_site')):<12} "
              f"{(e.get('edge_ratio_min') or float('nan')):>9.4f}   {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
