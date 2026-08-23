"""Control P7 - the mechanism test.

A known extra similarity `W` is planted on the moving frame of a **real**
defocus-mismatched pair, and the estimator is asked to recover the increment.
The defocus mismatch, the tile dropout and the content overlap are identical in
the two fits that form the increment, so they cancel.

Ratio 1.000 means the estimator responds correctly to a small geometric change
at that span.  A ratio below 1 at short span means the estimator itself is
shrinking small scale changes, and no strategy built out of short edges can
recover the loss.

Run:  python m10_increment.py
"""

import csv
import sys
from collections import defaultdict

import numpy as np


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "data/coffee-bean-increment.csv"
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r["ratio"]:
                continue
            rows.append(dict(cfg=r["cfg"], base=int(r["base"]), span=int(r["span"]),
                             g_plant=float(r["g_plant"]), ratio=float(r["ratio"]),
                             used0=int(r["used0"]), rms0=float(r["rms0"])))
    print("=" * 78)
    print("P7  KNOWN-INCREMENT RECOVERY ON REAL DEFOCUS-MISMATCHED PAIRS")
    print("  ratio = recovered increment / planted increment.")
    print("  Held fixed across the two fits: the pair, its defocus mismatch,")
    print("  its tile dropout, its content overlap.  Only the geometry changes.")
    print("=" * 78)
    for cfg in sorted({r["cfg"] for r in rows}):
        print(f"\n  cfg={cfg}")
        mags = sorted({abs(r["g_plant"]) for r in rows})
        print(f"    {'span':>5} {'med_used':>9} " +
              "".join(f"{f'|g|={m:.0e}':>13}" for m in mags))
        for s in sorted({r["span"] for r in rows if r["cfg"] == cfg}):
            cells = []
            for m in mags:
                v = [r["ratio"] for r in rows
                     if r["cfg"] == cfg and r["span"] == s and abs(abs(r["g_plant"]) - m) < 1e-9]
                cells.append(np.median(v) if v else float("nan"))
            used = [r["used0"] for r in rows if r["cfg"] == cfg and r["span"] == s]
            print(f"    {s:>5} {np.median(used):>9.0f} " +
                  "".join(f"{c:>13.3f}" for c in cells))
    print()
    print("  same, split by sign of the planted increment (cfg=m10):")
    by = defaultdict(list)
    for r in rows:
        if r["cfg"] != "m10":
            continue
        by[(r["span"], r["g_plant"] > 0)].append(r["ratio"])
    spans = sorted({s for s, _ in by})
    print(f"    {'span':>5} {'g>0':>10} {'g<0':>10}")
    for s in spans:
        p = np.median(by.get((s, True), [float("nan")]))
        n = np.median(by.get((s, False), [float("nan")]))
        print(f"    {s:>5} {p:>10.3f} {n:>10.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
