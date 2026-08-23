"""The scale-rate ladder: is a short-baseline scale estimate biased?

For each frame span `s`, the per-frame magnification rate implied by a directly
measured span-`s` edge is `|a| ** (1/s) - 1`.  If every edge were unbiased this
would be a flat function of `s` (up to the curvature of the true magnification
path, which is second order over the spans compared here).

If it *rises* with `s`, short edges are systematically shrinking the scale
change toward zero, and any strategy built out of short edges - chaining,
hop ladders, or a bundle adjustment weighted toward the numerous short edges -
inherits a coherent multiplicative bias that no amount of averaging removes.

Run:  python m10_shrink.py
"""

import numpy as np

from m10_lib import read_edges

CASES = {
    "coffee-bean (105 fr)": ("data/coffee-bean-edges.csv", 105),
    "109MSDCF (22 fr)": ("data/shallow-109-edges.csv", 22),
    "119MSDCF (33 fr)": ("data/shallow-119-edges.csv", 33),
}
CFGS = ["m10", "wide64"]


def rate_table(case: str, path: str) -> None:
    print("=" * 78)
    print(f"SCALE-RATE LADDER - {case}")
    print("  per-frame magnification rate |a|^(1/s) - 1, in units of 1e-3")
    print("  and the implied differential displacement across the anchor grid,")
    print("  d = |a-1| * lever, in plane px.  Pixel locking cannot be beaten by")
    print("  averaging when d is below about 1 px.")
    print("=" * 78)
    for cfg in CFGS:
        rows = [e for e in read_edges(path, cfg=cfg) if e.ok]
        spans = sorted({e.span for e in rows})
        # Only spans with a decent sample; direct-to-0 contributes 1 edge each.
        spans = [s for s in spans if sum(1 for e in rows if e.span == s) >= 5]
        print(f"\n  cfg={cfg}")
        print(f"    {'span':>5} {'n':>5} {'rate e-3/fr':>12} {'p25':>8} {'p75':>8} "
              f"{'diff disp px':>13} {'med_used':>9} {'med_rms':>8}")
        for s in spans:
            es = [e for e in rows if e.span == s]
            rate = np.array([abs(e.a) ** (1.0 / s) - 1.0 for e in es]) * 1e3
            disp = np.array([abs(e.a - 1.0) * e.lever for e in es])
            print(
                f"    {s:>5} {len(es):>5} {np.median(rate):>12.4f} "
                f"{np.percentile(rate, 25):>8.4f} {np.percentile(rate, 75):>8.4f} "
                f"{np.median(disp):>13.3f} "
                f"{np.median([e.used for e in es]):>9.0f} "
                f"{np.median([e.rms for e in es]):>8.3f}"
            )
        rows_long = [e for e in rows if e.span >= 24]
        if rows_long:
            r1 = np.median([abs(e.a) - 1.0 for e in rows if e.span == 1]) * 1e3
            rl = np.median([abs(e.a) ** (1.0 / e.span) - 1.0 for e in rows_long]) * 1e3
            print(f"    span-1 rate {r1:.4f}e-3/fr vs span>=24 rate {rl:.4f}e-3/fr"
                  f"   -> span-1 shrinkage factor {rl / r1 if r1 else float('nan'):.2f}x")
    print()


def rotation_check(case: str, path: str) -> None:
    """The same ladder for rotation, which has the same lever arm as scale and
    should therefore show the same bias if the mechanism is differential
    displacement falling below the locking scale."""
    print(f"  rotation ladder - {case} (units 1e-6 rad/frame)")
    for cfg in CFGS:
        rows = [e for e in read_edges(path, cfg=cfg) if e.ok]
        spans = [s for s in sorted({e.span for e in rows})
                 if sum(1 for e in rows if e.span == s) >= 5]
        vals = []
        for s in spans:
            es = [e for e in rows if e.span == s]
            vals.append((s, len(es), 1e6 * np.median([np.angle(e.a) / s for e in es])))
        print(f"    cfg={cfg}: " + "  ".join(f"s{s}:{v:+.3f}" for s, _n, v in vals))
    print()


def main() -> int:
    for case, (path, _n) in CASES.items():
        rate_table(case, path)
        rotation_check(case, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
