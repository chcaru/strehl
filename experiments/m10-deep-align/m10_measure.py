"""M10 headline measurement: held-out prediction of trustworthy long edges.

Design
------
The scale-rate ladder (`m10_shrink.py`) and the conservation test
(`m10_conserve.py`) established that short-baseline edges under-report
magnification, and that on the two shallow stacks the ladder converges exactly
onto the directly measured, high-tile-count reference edge.  So long edges with
plenty of surviving tiles are the trustworthy measurement, and they are what a
global solution has to predict.

Every strategy is therefore scored on **one fixed test set** of directly
measured long edges, and no strategy ever sees a test edge.  Because the test
set is identical across rows, the rows are directly comparable - which is not
true of a span-stratified design where the test set moves with the threshold.

Run:  python m10_measure.py
"""

import csv as _csv
import sys

import numpy as np

from m10_lib import (
    RHO,
    corner_err,
    corner_err_parts,
    cycle_consistency,
    graph_stats,
    poly_basis,
    predict,
    read_edges,
    solve_ba,
    solve_fixed,
    solve_hops,
    solve_poly,
    summarise,
)

CASES = {
    "coffee-bean": ("data/coffee-bean-edges.csv", 105, 40, 12),
    "109MSDCF": ("data/shallow-109-edges.csv", 22, 12, 40),
    "119MSDCF": ("data/shallow-119-edges.csv", 33, 16, 40),
}
CFGS = ["m10", "wide64"]


def train_sets(rows, test_keys, n):
    """Named training sets, each guaranteed disjoint from the test set."""
    def keep(pred):
        return [e for e in rows
                if e.ok and (e.i, e.j) not in test_keys and pred(e)]

    sets = {
        "chain (span 1)": keep(lambda e: e.span == 1),
        "span <= 2": keep(lambda e: e.span <= 2),
        "span <= 4": keep(lambda e: e.span <= 4),
        "span <= 8": keep(lambda e: e.span <= 8),
        "span <= 16": keep(lambda e: e.span <= 16),
        "span <= 32": keep(lambda e: e.span <= 32),
        "span <= 32, >= 8": keep(lambda e: 8 <= e.span <= 32),
        "span <= 32, >= 12": keep(lambda e: 12 <= e.span <= 32),
        "span >= 16": keep(lambda e: e.span >= 16),
        "span >= 24": keep(lambda e: e.span >= 24),
        "span >= 32": keep(lambda e: e.span >= 32),
        "all measurable": keep(lambda e: True),
    }
    return {k: v for k, v in sets.items() if v}


def strategies(train, n):
    out = {}
    out["S0-fixed"] = solve_fixed(train, n)
    for M in (1, 8, 16, 32):
        if not any(e.span <= M for e in train):
            continue
        g, _ = solve_hops(train, n, M)
        out[f"S{'1' if M == 1 else '2'}-hops{M}"] = g
    out["S3-ba-invvar"] = solve_ba(train, n, scheme="invvar")
    out["S3-ba-unit"] = solve_ba(train, n, scheme="unit")
    out["S3-ba-count"] = solve_ba(train, n, scheme="count")
    for d in (2, 4, 6):
        r = solve_poly(train, n, deg=d, bdeg=d, scheme="unit")
        if r:
            out[f"S4-poly{d}"] = r[0]
    r = solve_poly(train, n, deg=4, fixed_centre=True, scheme="unit")
    if r:
        out["S5-centre4"] = r[0]
    out["S6-ba-smooth"] = solve_ba(train, n, scheme="unit", smooth=0.02)
    return out


def score(g, test):
    errs, sc, tr, spans = [], [], [], []
    for e in test:
        p = predict(g, e.i, e.j)
        if p is None:
            continue
        errs.append(corner_err(p, e.t()))
        a, b = corner_err_parts(p, e.t())
        sc.append(a)
        tr.append(b)
        spans.append(e.span)
    return (np.array(errs), np.array(sc), np.array(tr), np.array(spans))


def run_case(case, path, n, min_span, min_used, csv_out):
    print("=" * 92)
    print(f"HELD-OUT PREDICTION OF TRUSTWORTHY LONG EDGES - {case}")
    print(f"  test set: every directly measured edge with span >= {min_span} "
          f"and >= {min_used} surviving tiles")
    print("  all errors are plane px at the worst plane corner")
    print("=" * 92)
    for cfg in CFGS:
        rows = read_edges(path, cfg=cfg)
        test = [e for e in rows if e.ok and e.span >= min_span and e.used >= min_used]
        if len(test) < 5:
            print(f"\n  cfg={cfg}: only {len(test)} test edges, skipped")
            continue
        tk = {(e.i, e.j) for e in test}
        print(f"\n  cfg={cfg}: {len(test)} test edges, "
              f"median {np.median([e.used for e in test]):.0f} tiles, "
              f"median rms {np.median([e.rms for e in test]):.2f} px, "
              f"spans {min(e.span for e in test)}-{max(e.span for e in test)}")
        for tname, train in train_sets(rows, tk, n).items():
            st = graph_stats(train, n)
            tree = " TREE" if st["is_tree"] else ""
            print(f"\n    train = {tname}: {len(train)} edges, cycle rank "
                  f"{st['cycle_rank']}, components {st['components']}{tree}")
            sols = strategies(train, n)
            if tname == "all measurable":
                allrows = [e for e in rows if e.ok]
                sols["REF-insample"] = solve_ba(allrows, n, scheme="unit")
            print(f"      {'strategy':>15} {'cover':>8} {'n':>5} {'median':>8} "
                  f"{'p90':>8} {'max':>8} {'mean':>8} {'scale':>8} {'trans':>8}")
            for k in sorted(sols):
                g = sols[k]
                if g is None:
                    continue
                errs, sc, tr, _sp = score(g, test)
                cov = sum(1 for x in g if x is not None)
                if errs.size == 0:
                    print(f"      {k:>15} {cov:>4}/{n:<3}     0"
                          + "        -" * 6)
                    continue
                print(
                    f"      {k:>15} {cov:>4}/{n:<3} {errs.size:>5} "
                    f"{np.median(errs):>8.3f} {np.percentile(errs, 90):>8.3f} "
                    f"{errs.max():>8.3f} {errs.mean():>8.3f} "
                    f"{np.median(sc):>8.3f} {np.median(tr):>8.3f}"
                )
                for q in range(errs.size):
                    csv_out.append((case, cfg, tname, k, int(_sp[q]),
                                    float(errs[q]), float(sc[q]), float(tr[q])))
    print()


def cycle_table(case, path, n):
    print("=" * 92)
    print(f"M1  CYCLE CONSISTENCY OF THE RAW EDGES - {case}")
    print("  Data only, no solver.  T(i->k) against T(j->k) o T(i->j).")
    print("=" * 92)
    for cfg in CFGS:
        rows = read_edges(path, cfg=cfg)
        trip = cycle_consistency(rows, max_triples=40000)
        if not trip:
            continue
        errs = np.array([t["err"] for t in trip])
        shortest = np.array([min(t["span_ij"], t["span_jk"]) for t in trip])
        print(f"\n  cfg={cfg}: {len(trip)} triples")
        print(f"    {'shortest leg':>14} {'n':>7} {'median':>9} {'p90':>9} {'max':>9}")
        for lo, hi in [(1, 1), (2, 3), (4, 7), (8, 15), (16, 31), (32, 104)]:
            m = (shortest >= lo) & (shortest <= hi)
            if not m.any():
                continue
            v = errs[m]
            print(f"    {f'{lo}-{hi}':>14} {v.size:>7} {np.median(v):>9.3f} "
                  f"{np.percentile(v, 90):>9.3f} {v.max():>9.3f}")
    print()


def smoothness(case, path, n, min_span=12, max_span=32):
    """Candidate (c): are the parameters smooth, low-order functions of index?

    Fitted against the reference solution, which is the bundle adjustment over
    the medium band the ladder says is unbiased."""
    print("=" * 92)
    print(f"CANDIDATE (c) - IS THE PARAMETER PATH LOW-ORDER IN FRAME INDEX?  {case}")
    print(f"  reference = BA over edges of span {min_span}-{max_span}")
    print("  corner error, plane px, of a degree-d polynomial through it")
    print("=" * 92)
    for cfg in CFGS:
        rows = [e for e in read_edges(path, cfg=cfg)
                if e.ok and min_span <= e.span <= max_span]
        g = solve_ba(rows, n, scheme="unit")
        if g is None or any(x is None for x in g):
            print(f"  cfg={cfg}: incomplete solution, skipped")
            continue
        A = np.array([g[j][0] for j in range(n)])
        B = np.array([g[j][1] for j in range(n)])
        print(f"\n  cfg={cfg}   total scale {100 * (abs(A[-1]) - 1):.4f}%, "
              f"rotation {np.angle(A[-1]) * 1e3:.4f} mrad, |B_end| {abs(B[-1]):.1f} px")
        print(f"    {'deg':>4} {'A part':>10} {'B part':>10} {'joint max':>11} "
              f"{'joint med':>11}")
        for d in range(1, 9):
            M = np.array([poly_basis(j, d, n) for j in range(n)])
            ca, *_ = np.linalg.lstsq(M, np.log(A), rcond=None)
            cb, *_ = np.linalg.lstsq(M, B, rcond=None)
            Ah, Bh = np.exp(M @ ca), M @ cb
            ea = RHO * np.abs(Ah - A)
            eb = np.abs(Bh - B)
            joint = np.array([corner_err((Ah[j], Bh[j]), (A[j], B[j])) for j in range(n)])
            print(f"    {d:>4} {ea.max():>10.3f} {eb.max():>10.3f} "
                  f"{joint.max():>11.3f} {np.median(joint):>11.3f}")
    print()


def main() -> int:
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    csv_out: list = []
    for case, (path, n, ms, mu) in CASES.items():
        run_case(case, path, n, ms, mu, csv_out)
    if what == "all":
        for case, (path, n, _ms, _mu) in CASES.items():
            cycle_table(case, path, n)
        smoothness("coffee-bean", "data/coffee-bean-edges.csv", 105)
        smoothness("119MSDCF", "data/shallow-119-edges.csv", 33, 8, 32)
    if csv_out:
        with open("data/heldout.csv", "w", newline="", encoding="utf-8") as f:
            w = _csv.writer(f)
            w.writerow(["case", "cfg", "train_set", "strategy", "span",
                        "corner_err", "scale_part", "trans_part"])
            w.writerows(csv_out)
        print(f"wrote data/heldout.csv ({len(csv_out)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
