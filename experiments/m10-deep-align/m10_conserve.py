"""Is the scale-rate ladder a real bias, or a median-versus-mean artefact?

If the true per-frame magnification rate varies a lot with frame index, then a
span-`s` edge measures the *mean* rate over a window of `s` frames while a
span-1 edge measures a single frame's rate.  Taking the **median** over edges
then compares the median of single values against the median of window means,
and for a skewed distribution those differ - producing a rising ladder with no
estimator bias anywhere.

That confound has to be killed before the ladder can be read as shrinkage.  The
test is a conservation identity: the span-1 edges must sum to the total drift.

    sum_j (log a_{j, j+1})  ==  log a_{0, 104}

is exact for any consistent set of transforms.  It involves no median, no
weighting and no solver, so it cannot be fooled by skew.

Run:  python m10_conserve.py
"""

import numpy as np

from m10_lib import read_edges

CASES = {
    "coffee-bean (105 fr)": ("data/coffee-bean-edges.csv", 105),
    "109MSDCF (22 fr)": ("data/shallow-109-edges.csv", 22),
    "119MSDCF (33 fr)": ("data/shallow-119-edges.csv", 33),
}
CFGS = ["m10", "wide64"]


def main() -> int:
    print("=" * 78)
    print("CONSERVATION TEST - do short edges add up to the long-edge total?")
    print("  Each row telescopes edges of one span across the whole stack and")
    print("  reports the total log-magnification that implies.  Every row")
    print("  measures the same physical quantity, so any trend is bias.")
    print("=" * 78)
    for case, (path, n) in CASES.items():
        print(f"\n{case}")
        for cfg in CFGS:
            rows = [e for e in read_edges(path, cfg=cfg) if e.ok]
            emap = {(e.i, e.j): e for e in rows}
            print(f"\n  cfg={cfg}")
            print(f"    {'span':>5} {'links':>6} {'covered':>8} {'total scale %':>14} "
                  f"{'per-frame e-3':>14} {'mean rate e-3':>14}")
            for s in [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 56, 64]:
                links, cov = [], 0
                k = 0
                while k + s < n:
                    e = emap.get((k, k + s))
                    if e is None:
                        break
                    links.append(np.log(e.a))
                    cov += s
                    k += s
                if not links or cov < n - s:
                    continue
                tot = sum(links)
                # extrapolate the covered part to the whole stack
                full = tot * (n - 1) / cov
                pct = 100.0 * (np.exp(full.real) - 1.0)
                per = 1e3 * (np.exp(full.real / (n - 1)) - 1.0)
                # mean (not median) per-frame rate over every span-s edge
                es = [e for e in rows if e.span == s]
                mean_rate = 1e3 * np.mean([np.log(abs(e.a)) / s for e in es])
                mean_rate = 1e3 * (np.exp(mean_rate / 1e3) - 1.0)
                print(f"    {s:>5} {len(links):>6} {cov:>4}/{n - 1:<3} {pct:>14.4f} "
                      f"{per:>14.4f} {mean_rate:>14.4f}")
            for a, b in [(0, n - 1)]:
                e = emap.get((a, b))
                if e is not None:
                    pct = 100.0 * (abs(e.a) - 1.0)
                    print(f"    {'direct':>5} {1:>6} {n - 1:>4}/{n - 1:<3} {pct:>14.4f} "
                          f"{1e3 * (abs(e.a) ** (1.0 / (n - 1)) - 1):>14.4f}"
                          f"{'':>15}  <- single edge 0->{b}, {e.used} tiles, "
                          f"rms {e.rms:.2f}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
