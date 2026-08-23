"""Descriptive edge-quality tables and the M6 cross-check (no solvers here).

Run:  python m10_edges.py
"""

import sys

import numpy as np

from m10_lib import read_edges


def m6_crosscheck() -> None:
    print("=" * 78)
    print("M6 CROSS-CHECK - fixed reference, M3 estimator verbatim (cfg m3, margin 10)")
    print("=" * 78)
    rows = read_edges("data/coffee-bean-m6-edges.csv")
    d0 = [e for e in rows if e.i == 0 and e.cfg == "m3"]
    ok = [e for e in d0 if e.ok]
    print(f"  direct-to-frame-0 pairs      : {len(d0)}")
    print(f"  no-fit                       : {len(d0) - len(ok)}   (M6 published: 3 of 104)")
    print(f"  median tiles used            : {np.median([e.used for e in ok]):.0f}"
          f"   (M6 published: 18 of 96)")
    print(f"  median tile rms, plane px    : {np.median([e.rms for e in ok]):.2f}"
          f"   (M6 published: 4.61)")
    nofit = sorted(e.j for e in d0 if not e.ok)
    print(f"  frames with no fit           : {nofit}")
    s1 = [e for e in rows if e.span == 1 and e.cfg == "m3"]
    s1ok = [e for e in s1 if e.ok]
    print(f"  span-1 pairs                 : {len(s1)}, no-fit {len(s1) - len(s1ok)}, "
          f"median tiles {np.median([e.used for e in s1ok]):.0f}, "
          f"median rms {np.median([e.rms for e in s1ok]):.3f}")
    print()


SPAN_BUCKETS = [(1, 1), (2, 2), (3, 4), (5, 8), (9, 16), (17, 32), (33, 64), (65, 104)]


def quality_table(case: str, path: str) -> None:
    rows = read_edges(path)
    cfgs = sorted({e.cfg for e in rows})
    print("=" * 78)
    print(f"EDGE QUALITY - {case}")
    print("=" * 78)
    for cfg in cfgs:
        sub = [e for e in rows if e.cfg == cfg]
        tot = len(sub)
        bad = sum(1 for e in sub if not e.ok)
        print(f"\n  cfg={cfg}   {tot} pairs, {bad} no-fit ({100.0 * bad / tot:.1f}%)")
        print(f"  {'span':>9} {'pairs':>6} {'nofit':>6} {'med_used':>9} {'p10_used':>9} "
              f"{'med_rms':>8} {'p90_rms':>8} {'med|g|e-3':>10} {'lever':>7}")
        for lo, hi in SPAN_BUCKETS:
            es = [e for e in sub if lo <= e.span <= hi]
            if not es:
                continue
            ok = [e for e in es if e.ok]
            label = f"{lo}" if lo == hi else f"{lo}-{hi}"
            if not ok:
                print(f"  {label:>9} {len(es):>6} {len(es):>6}" + "        -" * 6)
                continue
            print(
                f"  {label:>9} {len(es):>6} {len(es) - len(ok):>6} "
                f"{np.median([e.used for e in ok]):>9.0f} "
                f"{np.percentile([e.used for e in ok], 10):>9.0f} "
                f"{np.median([e.rms for e in ok]):>8.3f} "
                f"{np.percentile([e.rms for e in ok], 90):>8.3f} "
                f"{1e3 * np.median([abs(e.a - 1.0) for e in ok]):>10.3f} "
                f"{np.median([e.lever for e in ok]):>7.0f}"
            )
    print()


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "m6":
        m6_crosscheck()
        return 0
    m6_crosscheck()
    quality_table("coffee-bean (105 frames)", "data/coffee-bean-edges.csv")
    quality_table("109MSDCF (22 frames)", "data/shallow-109-edges.csv")
    quality_table("119MSDCF (33 frames)", "data/shallow-119-edges.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
