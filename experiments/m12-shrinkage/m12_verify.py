"""Verify the derived numbers quoted in the M12 report.

Anything in the report that is a ratio of two measured numbers, or a
whole-stack figure not printed verbatim by an earlier script, is recomputed
here so the report cannot drift from the data.

Run:  python m12_verify.py
"""

from __future__ import annotations

import numpy as np

from m12_ladder import load_stack, pct
from m12_lib import read_edges

STACKS = [("coffee-bean", "data/m10-coffee-bean-edges.csv", 105),
          ("119MSDCF", "data/m10-shallow-119-edges.csv", 33),
          ("109MSDCF", "data/m10-shallow-109-edges.csv", 22),
          ("112MSDCF", "data/stack-112-edges.csv", 79),
          ("113MSDCF", "data/stack-113-edges.csv", 63)]


def main() -> int:
    print("=" * 78)
    print("FULL-STACK CHAIN RECOVERY - telescope every span-1 edge, compare with")
    print("  the longest direct edge (0, j) the stack provides.  Disjoint.")
    print("=" * 78)
    print(f"    {'stack':>12} {'j':>4} {'chain %':>10} {'direct %':>10} "
          f"{'recovery':>9} {'tiles':>6}")
    for name, path, n in STACKS:
        st = load_stack(name, path, n, cfg="m10")
        chain = 0.0
        ok = True
        for k in range(n - 1):
            e = st.edge(k, k + 1)
            if e is None:
                ok = False
                break
            chain += np.log(abs(e.a))
        if not ok:
            print(f"    {name:>12}   span-1 chain incomplete")
            continue
        direct = [e for e in read_edges(path, cfg="m10")
                  if e.ok and e.i == 0 and e.j == n - 1]
        if not direct:
            cands = [e for e in read_edges(path, cfg="m10") if e.ok and e.i == 0]
            direct = [max(cands, key=lambda e: e.j)]
        d = direct[0]
        part = 0.0
        for k in range(d.j):
            part += np.log(abs(st.edge(k, k + 1).a))
        print(f"    {name:>12} {d.j:>4} {pct(part):>10.4f} "
              f"{pct(np.log(abs(d.a))):>10.4f} "
              f"{part / np.log(abs(d.a)):>9.4f} {d.used:>6}")

    print()
    print("=" * 78)
    print("DERIVED RATIOS QUOTED IN THE REPORT")
    print("=" * 78)
    checks = [
        ("oracle coffee-bean chain vs M10 global solve", 13.92 / 6.76, "2.06x"),
        ("oracle coffee-bean chain vs T_usable 4.0 px", 13.92 / 4.0, "3.5x"),
        ("worst cross-scene transfer 0.0261 -> 2.1753", 2.1753 / 0.0261, "83.4x"),
        ("coffee-bean vs 112 shrinkage 3.260 / 1.048", 3.260 / 1.048, "3.11x"),
        ("112 uncorrected -> self-fitted worst px", 5.66 / 5.27, "1.07x worse"),
        ("fact 43 span16/span1 on coffee-bean", 5.8891 / 1.6876, "3.49x"),
        ("wide64 anchor rms vs m10, 112", 8.44 / 3.23, "2.6x"),
        ("wide64 anchor rms vs m10, 113", 7.33 / 3.04, "2.4x"),
    ]
    for lab, v, said in checks:
        print(f"    {lab:>48} = {v:8.4f}   report says {said}")

    print()
    print("=" * 78)
    print("C1 SPOT CHECK - the estimator control, worst scale error in plane px")
    print("=" * 78)
    for tag in ("112", "113"):
        with open(f"out/c1-estimator-{tag}.txt", encoding="utf-8") as fh:
            for line in fh:
                if "worst" in line.lower() or "PASS" in line or "FAIL" in line:
                    print(f"    [{tag}] {line.rstrip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
