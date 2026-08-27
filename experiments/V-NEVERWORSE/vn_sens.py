r"""V-NEVERWORSE / SENSITIVITY -- how much does the source-set size decide the answer?

The sharpness lane's reference used 10 frames out of a 299-frame stack and
thinning alone moved its readings 1.05x-1.56x and across unity. `min` and `max`
over N draws are extrema and are biased in N BY CONSTRUCTION: more frames can
only lower the min and raise the max. So the free parameter is measured here
rather than chosen and forgotten.

Two subjects, deep-sampled, then the ratio recomputed on nested subsamples of
the SAME measured frames -- so the ladder isolates N and nothing else (no
re-render, no re-registration, no rng).

  python vn_sens.py [--n 61] [subject ...]
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L                                            # noqa: E402
import vn_run as RUN                                          # noqa: E402

# One deep stack and one shallow one, so the ladder covers both regimes.
SUBJ = ["lead-1-cpl", "foam"]
DEEP = 61


def ladder(rec, key):
    """N-dependence of the order statistics, on the SAME measured frames.

    NOT by linspace. A linspace subsample always retains both endpoints, and
    on these subjects the argmin IS an endpoint, so a linspace ladder reports
    `vs_min` frozen across N and certifies a stability the estimator does not
    have. That is commissioning arm S2's defect, and it was reproduced here
    once before this ladder was rewritten to draw random subsets.
    """
    rows = [r for r in rec["rows"] if L.admits(r, key) and r.get(key) is not None]
    rows.sort(key=lambda r: r["frame"])
    m = rec["master"][key]
    rng = np.random.default_rng(20260827)
    out = []
    for n in (3, 5, 9, 13, 21, 31, 41, len(rows)):
        if n > len(rows):
            continue
        if n == len(rows):
            draws = [np.arange(len(rows))]
        else:
            draws = [rng.choice(len(rows), n, replace=False) for _ in range(200)]
        vmin, vmed, vmax = [], [], []
        for idx in draws:
            sub = [rows[i] for i in idx]
            o = L.order_stats(sub, key)
            vmin.append(m / o["min"]); vmed.append(m / o["med"])
            vmax.append(m / o["max"])
        out.append(dict(n=n, draws=len(draws),
                        vs_min=float(np.median(vmin)),
                        vs_min_lo=float(min(vmin)), vs_min_hi=float(max(vmin)),
                        vs_med=float(np.median(vmed)),
                        vs_max=float(np.median(vmax)),
                        frac_above1=float(np.mean([v > 1.0 for v in vmin]))))
    return out


def main(argv):
    n, want = DEEP, []
    i = 0
    while i < len(argv):
        if argv[i] == "--n":
            n = int(argv[i + 1]); i += 2
        else:
            want.append(argv[i]); i += 1
    subs = want or SUBJ
    res = {}
    for s in subs:
        print("deep sample %s at N=%d" % (s, n))
        rec = RUN.measure(s, n, tag="--sens%d" % n)
        res[s] = {}
        for key in ("blotch", "chroma"):
            lad = ladder(rec, key)
            res[s][key] = lad
            print("  %-7s  N  draws   vs_min   [ lo .. hi ]      vs_med    vs_max   P(>1)"
                  % key)
            for r in lad:
                print("           %3d %5d %8.4f  [%.4f..%.4f] %8.4f  %8.4f  %5.2f"
                      % (r["n"], r["draws"], r["vs_min"], r["vs_min_lo"],
                         r["vs_min_hi"], r["vs_med"], r["vs_max"],
                         r["frac_above1"]))
            lo = min(r["vs_min_lo"] for r in lad)
            hi = max(r["vs_min_hi"] for r in lad)
            crossed = lo < 1.0 < hi
            print("           vs_min spans %.3fx over all N and all draws "
                  "(%.4f..%.4f)%s"
                  % (hi / lo, lo, hi,
                     "  -- AND CROSSES UNITY: N decides the verdict" if crossed
                     else "  -- does not cross unity: the verdict survives N"))
            full = lad[-1]
            print("           at the deepest sample (N=%d) vs_min %.4f ; at N=21 "
                  "median %.4f -- subsampling can only RAISE the min, so N=21 is "
                  "a LOWER bound on vs_min"
                  % (full["n"], full["vs_min"],
                     next((r["vs_min"] for r in lad if r["n"] == 21), float("nan"))))
    L.jdump(res, os.path.join(L.OUT, "sens", "sens.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
