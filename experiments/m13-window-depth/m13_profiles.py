"""Turn the committed distance profiles into the two figures the report cites.

Reads only data/edgeprof-*.csv. Prints an ASCII profile of mis-selection and
of reconstruction error against distance from the occluding boundary, for
M11's recommended window, M13's, and the wide endpoint.
"""

import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def load(stk):
    with open(os.path.join(DATA, f"edgeprof-{stk}.csv"), newline="") as f:
        return list(csv.DictReader(f))


def bar(v, lo, hi, width=44):
    if hi <= lo:
        return ""
    n = int(round(width * (v - lo) / (hi - lo)))
    return "#" * max(0, min(width, n))


def main():
    for stk in ("109MSDCF", "119MSDCF"):
        rr = load(stk)
        for step in sorted({int(r["step"]) for r in rr}):
            print()
            print("=" * 78)
            print(f"{stk} / vertical occluding boundary / depth step {step} frames")
            print("d < 0 is the near (occluding) layer, d >= 0 the far layer.")
            print("=" * 78)
            by = defaultdict(dict)
            for r in rr:
                if int(r["step"]) != step:
                    continue
                by[int(r["window"])][int(r["d"])] = r
            wins = sorted(by)
            ds = [d for d in sorted(by[wins[0]]) if -64 <= d <= 64 and d % 4 == 0]
            print(f"{'d':>5} " + " ".join(f"{'w' + str(w) + ' mis':>10}" for w in wins)
                  + " " + " ".join(f"{'w' + str(w) + ' err':>10}" for w in wins))
            for d in ds:
                cells = []
                for w in wins:
                    cells.append(f"{float(by[w][d]['mis']):>10.3f}")
                for w in wins:
                    cells.append(f"{float(by[w][d]['e_merged']):>10.1f}")
                print(f"{d:>5} " + " ".join(cells))
            print()
            print("  reconstruction error vs the ideal, by distance (DN):")
            allv = [float(by[w][d]["e_merged"]) for w in wins for d in ds]
            lo, hi = min(allv), max(allv)
            for w in wins:
                print(f"    w{w}")
                for d in ds:
                    v = float(by[w][d]["e_merged"])
                    o = float(by[w][d]["e_oracle"])
                    print(f"      d={d:>4} {v:>8.1f} (floor {o:>7.1f}) {bar(v, lo, hi)}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--out":
        with open(sys.argv[2], "w") as f:
            sys.stdout = f
            main()
        sys.stdout = sys.__stdout__
        print(f"wrote {sys.argv[2]}")
    else:
        main()
