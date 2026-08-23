"""M23 gate (c) - the only gate that matters.

Does re-admitting metacalibrated short edges beat the 6.758 px held-out
baseline?  Registered PASS margin: 0.40 px, i.e. E* <= 6.36 px, because the
runner-up spread in M10's own table is about 0.4 px and anything inside that is
noise.

FAILURE DIRECTION (registered, PREREGISTRATION section 2c): held-out corner
error fails UPWARD - bigger is worse - and it is a median over a fixed test set,
so it cannot be gamed by dropping hard edges.  The test set is IDENTICAL in
every arm here (span >= 40, >= 12 tiles), and the correction only ever touches
edges of span <= 2, so no test edge is modified by any arm.  That is the point
of the design: the correction cannot reach the thing it is scored on.

Reuse (discipline 34): `train_sets`, `strategies` and `score` are imported from
`experiments/m10-deep-align/m10_measure.py` and the solvers from `m10_lib.py`,
unmodified, and the M10 baseline is recomputed here rather than quoted.  That
is a CONSISTENCY CHECK, not independent evidence: the same code reproducing its
own number proves the plumbing, not the physics.

Run:  python m23_heldout.py > out\\heldout.txt
"""

from __future__ import annotations

import math
import os
import sys
import time
from dataclasses import replace

import numpy as np

_M10 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "m10-deep-align")
sys.path.insert(0, _M10)

from m10_lib import graph_stats, read_edges  # noqa: E402
from m10_measure import score, strategies, train_sets  # noqa: E402

from m23_mc import PRIMARY_DELTA, by_delta, by_span, read_metacal  # noqa: E402

EDGES = "data/m10-coffee-bean-edges.csv"
MC = "data/coffee-bean-metacal.csv"
N = 105
MIN_SPAN, MIN_USED = 40, 12
CFG = "m10"
DELTAS = [1e-4, 2e-4, 4e-4, 8e-4, 1.6e-3]
BASELINE = 6.758
MARGIN = 0.40

SHORT_SETS = ["span <= 2", "span <= 4", "span <= 8", "span <= 16",
              "span <= 32", "all measurable"]
KEY_SETS = SHORT_SETS + ["span >= 32", "chain (span 1)"]


def rmap_for(mc, delta, spans=(1, 2)):
    out = {}
    for s in spans:
        for r in by_delta(by_span(mc, s), delta):
            out[(r.i, r.j)] = r.r_two
    return out


def apply_corr(rows, rmap, floor=0.0):
    """`log|a| -> log|a| / R`, phase untouched, translation untouched."""
    out, hit = [], 0
    for e in rows:
        r = rmap.get((e.i, e.j))
        if not e.ok or r is None or not math.isfinite(r):
            out.append(e)
            continue
        if floor > 0.0:
            r = math.copysign(max(abs(r), floor), r if r != 0 else 1.0)
        if r == 0.0:
            out.append(e)
            continue
        m = abs(e.a)
        if m <= 0:
            out.append(e)
            continue
        out.append(replace(e, a=e.a * (math.exp(math.log(m) / r) / m)))
        hit += 1
    return out, hit


def shuffle_map(rmap, seed):
    rng = np.random.default_rng(seed)
    k = list(rmap)
    v = np.array([rmap[x] for x in k])
    rng.shuffle(v)
    return dict(zip(k, v))


def const_map(rmap):
    m = float(np.median(list(rmap.values())))
    return {k: m for k in rmap}, m


TREES: set[str] = set()
SHORT_FRAC: dict[str, float] = {}


def evaluate(rows, test, tk, only=None, label=""):
    """Every (train set, strategy) row; returns the non-degenerate full-coverage
    candidates with M10's robust E*."""
    spans = np.array([e.span for e in test])
    qcut = float(np.percentile(spans, 75))
    cand = []
    for tname, train in train_sets(rows, tk, N).items():
        if only is not None and tname not in only:
            continue
        st = graph_stats(train, N)
        SHORT_FRAC[tname] = (sum(1 for e in train if e.span <= 2) / len(train)
                             if train else 0.0)
        if st["is_tree"]:
            TREES.add(tname)
            continue
        for k, g in strategies(train, N).items():
            if g is None:
                continue
            errs, sc, tr, sp = score(g, test)
            cov = sum(1 for x in g if x is not None)
            if errs.size == 0 or cov < N:
                continue
            at_q = errs[sp >= qcut]
            cand.append(dict(
                arm=label, train=tname, strat=k, n=int(errs.size),
                cover=cov, e_q=float(np.median(at_q)), k_q=int(at_q.size),
                med=float(np.median(errs)), p90=float(np.percentile(errs, 90)),
                mx=float(errs.max()),
                e_top=float(np.median(errs[sp == sp.max()])),
                scale=float(np.median(sc)), trans=float(np.median(tr)),
            ))
    return cand


def best(cand):
    return min(cand, key=lambda c: c["e_q"]) if cand else None


def show(title, cand, k=6):
    print(f"\n  {title}")
    if not cand:
        print("    (no non-degenerate full-coverage row)")
        return
    print(f"    {'E* robust':>10} {'med':>8} {'p90':>8} {'max':>8} "
          f"{'scale':>8} {'trans':>8}  strategy / train set")
    for c in sorted(cand, key=lambda x: x["e_q"])[:k]:
        print(f"    {c['e_q']:>10.3f} {c['med']:>8.3f} {c['p90']:>8.3f} "
              f"{c['mx']:>8.3f} {c['scale']:>8.3f} {c['trans']:>8.3f}  "
              f"{c['strat']:<14} '{c['train']}'")


def main() -> int:
    t_all = time.time()
    rows = read_edges(EDGES, cfg=CFG)
    test = [e for e in rows if e.ok and e.span >= MIN_SPAN and e.used >= MIN_USED]
    tk = {(e.i, e.j) for e in test}
    mc = read_metacal(MC, cfg=CFG)

    print("=" * 100)
    print("GATE (c)  HELD-OUT PREDICTION OF TRUSTWORTHY LONG EDGES - coffee-bean")
    print(f"  test set: {len(test)} direct edges, span >= {MIN_SPAN}, "
          f">= {MIN_USED} tiles, spans "
          f"{min(e.span for e in test)}-{max(e.span for e in test)}")
    print(f"  correction touches span <= 2 ONLY; 0 test edges are modified in any arm")
    print(f"  registered PASS: E* <= {BASELINE - MARGIN:.2f} px "
          f"(baseline {BASELINE:.3f} px, margin {MARGIN:.2f} px)")
    print("  FAILURE DIRECTION: larger E* is worse.")
    print("=" * 100)

    n_touch = sum(1 for e in test if e.span <= 2)
    print(f"\n  sanity: test edges with span <= 2 = {n_touch} (must be 0)")

    t0 = time.time()
    base = evaluate(rows, test, tk, label="baseline")
    print(f"\n  [{time.time() - t0:.1f} s]")
    show("ARM 0 - BASELINE, uncorrected (reproduces M10)", base)
    b = best(base)
    print(f"\n    reproduction gate: best E* = {b['e_q']:.3f} px vs M10's published "
          f"{BASELINE:.3f} px -> "
          f"{'PASS' if abs(b['e_q'] - BASELINE) < 0.01 else 'MISMATCH'}")
    print(f"    ({b['strat']} trained on '{b['train']}', {b['k_q']} test edges "
          f"at span >= p75)")

    d = PRIMARY_DELTA
    rm = rmap_for(mc, d)
    corr, hit = apply_corr(rows, rm)
    print(f"\n  primary delta {d:.0e}: {len(rm)} responses, "
          f"{hit} of {len(rows)} edges corrected")
    med_r = float(np.median(list(rm.values())))
    print(f"    median R = {med_r:.4f}, "
          f"IQR [{np.percentile(list(rm.values()), 25):.4f}, "
          f"{np.percentile(list(rm.values()), 75):.4f}]")

    t0 = time.time()
    ca = evaluate(corr, test, tk, label="metacal")
    print(f"\n  [{time.time() - t0:.1f} s]")
    show(f"ARM 1 - METACALIBRATED spans 1-2, delta={d:.0e}", ca)
    c1 = best(ca)

    sm = shuffle_map(rm, 20230823)
    sc_rows, _ = apply_corr(rows, sm)
    n1 = evaluate(sc_rows, test, tk, only=KEY_SETS, label="N1")
    cm, mv = const_map(rm)
    cn_rows, _ = apply_corr(rows, cm)
    n2 = evaluate(cn_rows, test, tk, only=KEY_SETS, label="N2")
    show(f"NULL N1 - R SHUFFLED across edges (seed 20230823), delta={d:.0e}", n1, 4)
    show(f"NULL N2 - R constant = median {mv:.4f} (this IS M12's refuted scalar)",
         n2, 4)

    print("\n" + "=" * 100)
    print("GATE (c) HEADLINE - global best over every non-degenerate full-coverage row")
    print("=" * 100)
    print(f"  {'arm':<34} {'best E*':>9} {'delta vs base':>14} {'verdict':>9}")
    print(f"  {'ARM 0 uncorrected (baseline)':<34} {b['e_q']:>9.3f} "
          f"{0.0:>14.3f} {'-':>9}")
    for lab, cc in [("ARM 1 metacal spans 1-2", c1),
                    ("N1 shuffled R", best(n1)),
                    ("N2 constant R (= M12 scalar)", best(n2))]:
        if cc is None:
            continue
        dv = cc["e_q"] - b["e_q"]
        v = "PASS" if cc["e_q"] <= BASELINE - MARGIN else "FAIL"
        print(f"  {lab:<34} {cc['e_q']:>9.3f} {dv:>+14.3f} {v:>9}")

    print("\n  NOTE - the global best is set by a training set that contains NO")
    print("  corrected edges ('span >= 32'), so it is unchanged BY CONSTRUCTION.")
    print("  The informative comparison is the paired one below, restricted to")
    print("  training sets that actually contain span <= 2 edges.")

    print("\n" + "=" * 100)
    print("GATE (c) PAIRED - only training sets that CONTAIN corrected edges")
    print(f"  same test set, same strategy, delta={d:.0e}.  Negative delta = the")
    print("  correction helped.  Registered PASS needs an absolute E* <= "
          f"{BASELINE - MARGIN:.2f} px.")
    print("=" * 100)
    bmap = {(c["train"], c["strat"]): c for c in base}
    cmap = {(c["train"], c["strat"]): c for c in ca}
    n1m = {(c["train"], c["strat"]): c for c in n1}
    n2m = {(c["train"], c["strat"]): c for c in n2}
    print(f"  {'train set':<20} {'%sp<=2':>7} {'strategy':>14} {'uncorr':>8} "
          f"{'metacal':>8} {'delta':>8} {'N1 shuf':>8} {'N2 const':>9}")
    seen = set()
    for key in sorted(bmap, key=lambda k: bmap[k]["e_q"]):
        tname, strat = key
        f = SHORT_FRAC.get(tname, 0.0)
        if f <= 0.0 or key not in cmap:
            continue
        if tname in seen:
            continue
        seen.add(tname)
        bq, cq = bmap[key]["e_q"], cmap[key]["e_q"]
        s1 = n1m[key]["e_q"] if key in n1m else float("nan")
        s2 = n2m[key]["e_q"] if key in n2m else float("nan")
        print(f"  {tname:<20} {100 * f:>6.1f}% {strat:>14} {bq:>8.3f} "
              f"{cq:>8.3f} {cq - bq:>+8.3f} {s1:>8.3f} {s2:>9.3f}")
    print("\n  best strategy within each short-edge-inclusive training set:")
    print(f"  {'train set':<20} {'%sp<=2':>7} {'uncorr best':>12} "
          f"{'metacal best':>13} {'delta':>8}  strategy")
    for tname in sorted({k[0] for k in bmap}):
        f = SHORT_FRAC.get(tname, 0.0)
        if f <= 0.0:
            continue
        bs = min((c for c in base if c["train"] == tname), key=lambda x: x["e_q"])
        cs = min((c for c in ca if c["train"] == tname), key=lambda x: x["e_q"])
        print(f"  {tname:<20} {100 * f:>6.1f}% {bs['e_q']:>12.3f} "
              f"{cs['e_q']:>13.3f} {cs['e_q'] - bs['e_q']:>+8.3f}  "
              f"{bs['strat']} -> {cs['strat']}")
    if TREES:
        print(f"\n  training sets excluded as TREE (a solve over a tree is chaining "
              f"in disguise): {sorted(TREES)}")

    print("\n" + "=" * 100)
    print("DELTA SWEEP over SHORT-EDGE-INCLUSIVE training sets only")
    print("  (rule 16: near-flat rows are a BOUND, not a value; the argmin over a")
    print("  swept grid is never reported as an optimum)")
    print("=" * 100)
    b_short = best([c for c in base if c["train"] in SHORT_SETS])
    print(f"  uncorrected best over these sets: {b_short['e_q']:.3f} px "
          f"({b_short['strat']} '{b_short['train']}')")
    print(f"  {'delta':>9} {'med R':>7} {'metacal E*':>11} {'N1 shuf E*':>11} "
          f"{'N2 const E*':>12}  best strategy / train (metacal arm)")
    for dd in DELTAS:
        rr = rmap_for(mc, dd)
        if not rr:
            continue
        cr, _ = apply_corr(rows, rr)
        m = best(evaluate(cr, test, tk, only=SHORT_SETS, label="m"))
        s = best(evaluate(apply_corr(rows, shuffle_map(rr, 7))[0], test, tk,
                          only=SHORT_SETS, label="s"))
        cmm, mvv = const_map(rr)
        k = best(evaluate(apply_corr(rows, cmm)[0], test, tk,
                          only=SHORT_SETS, label="k"))
        print(f"  {dd:>9.1e} {mvv:>7.4f} {m['e_q']:>11.3f} {s['e_q']:>11.3f} "
              f"{k['e_q']:>12.3f}  {m['strat']} '{m['train']}'")

    print(f"\n  total wall clock {time.time() - t_all:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
