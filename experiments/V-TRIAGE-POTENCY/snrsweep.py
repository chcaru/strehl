#!/usr/bin/env python3
"""How close is MERGE-LIMITED = 0 to the SNR_MIN = 4.0 gate constant?

Motion and coverage-gap are adjudicated before the blur test and do not consult
the gate, so their verdicts are taken from the shipped table; only subjects that
actually reach step 3 can flip.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

BT = r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-TRIAGE"
sys.path.insert(0, BT)
import tri  # noqa: E402
import triage  # noqa: E402

tri.OUT = r"C:\dev\strehl-out\BUILD-TRIAGE"


def main() -> int:
    ev = {s: triage.load(s) for s in tri.SUBJECTS}
    shipped = {s: triage.classify(s, ev[s])["verdict"] for s in tri.SUBJECTS}
    reach = [s for s in tri.SUBJECTS
             if not shipped[s].startswith("CAPTURE-LIMITED")]
    print(f"subjects that reach the merge-loss test at all: {len(reach)} of 26")
    print()
    print(f"{'SNR_MIN':>8} {'MERGE-LIMITED':>14}  subjects")
    for snr in (2.0, 3.0, 3.5, 3.7, 3.8, 3.9, 4.0, 4.5, 5.0, 6.0):
        ml = []
        for s in reach:
            with open(os.path.join(tri.OUT, "compare", s + ".json"), encoding="utf-8") as fh:
                c = json.load(fh)
            keep = {}
            for k, v in c["sites"].items():
                if k == "FLAT" or not v.get("reliable", True):
                    continue
                e = v["edge"]
                nm, nf = e["noise_merge_dn"], e["noise_frame_dn"]
                if nm > 0 and e["merge_dnpx"] < snr * nm:
                    continue
                if e["ratio"] < 1.0 and nf > 0 and e["frame_corr_dnpx"] < snr * nf:
                    continue
                keep[k] = e["blur_equiv_px"]
            if keep and max(keep.values()) >= triage.BLUR_BAD_PX:
                ml.append(f"{s}({max(keep.values()):.2f})")
        print(f"{snr:>8.1f} {len(ml):>14}  {', '.join(ml) or '-'}")

    print()
    print("TILE STATISTICS FOR THE BOUNDARY SITES (does the gate drop real content?)")
    print(f"{'subject.site':<40} {'arm':<6} {'mean':>9} {'sd':>8} {'sd/mean':>8} "
          f"{'edge p99.5':>11} {'noise':>8} {'SNR':>6}")
    for s, k in (("109MSDCF", "SOURCE-BEST"), ("109MSDCF", "DEFICIT"),
                 ("lead-1-cpl", "DEFICIT"), ("bee-2-cpl", "DEFICIT"),
                 ("flowers-cpl", "DEFICIT"), ("bee-3-cpl", "DETAIL")):
        p = os.path.join(tri.OUT, "tiles", f"{s}.{k}.npz")
        if not os.path.exists(p):
            print(f"{s}.{k}: MISSING")
            continue
        z = np.load(p)
        for arm in ("merge", "frame"):
            t = z[arm].astype(np.float32)
            e = tri.edge_slope(t)
            n = tri.pixel_noise(t)
            print(f"{s + '.' + k:<40} {arm:<6} {t.mean():>9.1f} {t.std():>8.1f} "
                  f"{t.std() / max(t.mean(), 1e-9):>8.4f} {e:>11.1f} {n:>8.1f} "
                  f"{e / max(n, 1e-9):>6.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
