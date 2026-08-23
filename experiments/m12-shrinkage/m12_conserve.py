"""C2 — reproduce M10's published ladder before trusting anything of my own.

SYNTHESIS §5 item 15: *"When re-analysing someone else's data, reproduce one of
their published numbers first."*  M10's `out/conservation.txt` publishes, for
`coffee-bean` at `cfg=m10`, a span-1 total of **-1.6876%** and a span-16 total of
**-5.8891%**.  This script recomputes those from M10's own committed edge CSV
using M10's own coverage-extrapolated rule, re-implemented here from the
definition rather than imported, and fails loudly if they do not come back.

It then prints the same quantity under M12's *windowed* rule (identical frame
range and endpoints for every span, no extrapolation), so the difference between
the two rules is visible rather than assumed.

Run:  python m12_conserve.py
"""

from __future__ import annotations

import math
import sys

import numpy as np

from m12_ladder import ladder, load_stack, pct, print_ladder

M10_PUBLISHED = {1: -1.6876, 16: -5.8891}
TOL = 0.0002

CASES = [
    ("coffee-bean", "data/m10-coffee-bean-edges.csv", 105),
    ("119MSDCF", "data/m10-shallow-119-edges.csv", 33),
    ("109MSDCF", "data/m10-shallow-109-edges.csv", 22),
    ("112MSDCF", "data/stack-112-edges.csv", 79),
    ("113MSDCF", "data/stack-113-edges.csv", 63),
]


def m10_rule(st, n: int, s: int):
    """M10's coverage-extrapolated telescoping total, re-implemented from the
    definition in `m10_conserve.py`'s docstring: telescope span-`s` edges from
    frame 0 until one is missing, then rescale the covered part to the whole
    stack."""
    links, cov, k = [], 0, 0
    while k + s < n:
        e = st.edge(k, k + s)
        if e is None:
            break
        links.append(math.log(abs(e.a)))
        cov += s
        k += s
    if not links or cov < n - s:
        return None, 0, 0
    full = sum(links) * (n - 1) / cov
    return 100.0 * (math.exp(full) - 1.0), len(links), cov


def main() -> int:
    print("=" * 78)
    print("C2  REPRODUCTION GATE - M10's published coffee-bean ladder")
    print("  SYNTHESIS section 5 item 15.  Recomputed from M10's committed CSV")
    print("  with M10's own coverage-extrapolated rule, re-implemented here.")
    print("=" * 78)
    cb = load_stack("coffee-bean", "data/m10-coffee-bean-edges.csv", 105, cfg="m10")
    bad = 0
    for s, want in M10_PUBLISHED.items():
        got, links, cov = m10_rule(cb, 105, s)
        ok = got is not None and abs(got - want) <= TOL
        bad += 0 if ok else 1
        print(f"    span {s:>2}: published {want:>9.4f}%   recomputed "
              f"{got:>9.4f}%   ({links} links, {cov}/104)   "
              f"{'PASS' if ok else 'FAIL'}")
    if bad:
        print("\n  C2 FAILED - the reader or the rule is wrong. Nothing below is believed.")
        return 1
    print("\n  C2 PASS - the reader and the algebra agree with M10.")

    print()
    print("=" * 78)
    print("M10's RULE vs M12's WINDOWED RULE, coffee-bean, cfg=m10")
    print("  M10 extrapolates each span's partial coverage to the whole stack.")
    print("  M12 fixes the window so every span shares endpoints exactly.")
    print("=" * 78)
    ld = ladder(cb, 0, 48)
    print(f"    {'span':>5} {'M10 rule (0..104)':>20} {'M12 rule (0..48)':>19} "
          f"{'M12 S_48(s)':>13}")
    for s in ld.spans:
        m10v, _, _ = m10_rule(cb, 105, s)
        m10s = f"{m10v:>19.4f}%" if m10v is not None else f"{'n/a':>20}"
        print(f"    {s:>5} {m10s} {pct(ld.total[s]):>18.4f}% {ld.frac[s]:>13.4f}")

    print()
    print("=" * 78)
    print("WINDOWED CONSERVATION LADDER - every stack, cfg=m10, W=48")
    print("  S_W(s) = T_W(s) / A_W.  1.0000 == unbiased.  1/S is the shrinkage.")
    print("  A_W is the single direct edge (0,W); no T_W(s<W) contains it.")
    print("=" * 78)
    for name, path, n in CASES:
        st = load_stack(name, path, n, cfg="m10")
        print(f"\n  {name} ({n} frames)")
        for w in (48, 32, 24, 16):
            if w >= n:
                continue
            ld = ladder(st, 0, w)
            if ld is None or len(ld.spans) < 3:
                continue
            print_ladder(ld)
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
