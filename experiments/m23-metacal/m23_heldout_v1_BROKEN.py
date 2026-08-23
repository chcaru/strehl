"""M23 gate (c) - *** SUPERSEDED, THIS VERSION'S RESULT WAS WRONG ***

KEPT DELIBERATELY.  This is the FIRST version of `m23_heldout.py`, committed
unchanged so the diff against the working version is in the record.

WHAT IT GOT WRONG.  It scored gate (c) as "the minimum E* over every
non-degenerate full-coverage row", which is M10's own decision rule and is
correct for M10.  Applied here it reported 6.758 px for ALL FOUR ARMS -
baseline, metacalibrated, N1 shuffled, N2 constant - and it is tempting to read
that as "the correction is inert".

It IS inert, but this table could not have shown it.  The winning row is
`S4-poly6` trained on 'span >= 32', a training set that contains NO span <= 2
edge, so the correction cannot reach it.  All four arms were identical BY
CONSTRUCTION and the comparison had ZERO POWER.  A comparison whose optimum is
set by a row the treatment cannot touch is not a null result, it is a broken
instrument.

THE FIX (see `m23_heldout.py`): add a PAIRED table restricted to training sets
that actually contain corrected edges, joined on (train set, strategy) so the
same strategy is compared with and without the correction.  That table is what
exposed the real finding - on 'span <= 2' the correction improves E* by 11.25 px
and BOTH NULLS IMPROVE IT MORE (30.931 and 31.245 against 32.426), i.e. the gain
is undirected inflation and a random assignment of responses beats the measured
ones.  The broken version could not have found that.

Do not run this for a result.  Run `m23_heldout.py`.

--- original docstring follows ---

Does re-admitting metacalibrated short edges beat the 6.758 px held-out
baseline?  Registered PASS margin: 0.40 px, i.e. E* <= 6.36 px, because the
runner-up spread in M10's own table is about 0.4 px and anything inside that is
noise.

FAILURE DIRECTION (registered, PREREGISTRATION section 2c): held-out corner
error fails UPWARD - bigger is worse - and it is a median over a fixed test set,
so it cannot be gamed by dropping hard edges.  The test set is IDENTICAL in
every arm here (span >= 40, >= 12 tiles), and the correction only ever touches
edges of span <= 2, so no test edge is modified by any arm.

Reuse (discipline 34): `train_sets`, `strategies` and `score` are imported from
`experiments/m10-deep-align/m10_measure.py` and the solvers from `m10_lib.py`,
unmodified, and the M10 baseline is recomputed here rather than quoted.  That
is a CONSISTENCY CHECK, not independent evidence.
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

KEY_SETS = ["chain (span 1)", "span <= 2", "span <= 4", "all measurable",
            "span >= 32"]


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
        if st["is_tree"]:
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
    print("GATE (c) HEADLINE")
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

    print("\n" + "=" * 100)
    print("DELTA SWEEP (rule 16: near-flat rows are a BOUND, not a value; the")
    print("argmin over a swept grid is never reported as an optimum)")
    print("=" * 100)
    print(f"  {'delta':>9} {'med R':>7} {'metacal E*':>11} {'N1 shuf E*':>11} "
          f"{'N2 const E*':>12}  best strategy / train (metacal arm)")
    for dd in DELTAS:
        rr = rmap_for(mc, dd)
        if not rr:
            continue
        cr, _ = apply_corr(rows, rr)
        m = best(evaluate(cr, test, tk, only=KEY_SETS, label="m"))
        s = best(evaluate(apply_corr(rows, shuffle_map(rr, 7))[0], test, tk,
                          only=KEY_SETS, label="s"))
        cmm, mvv = const_map(rr)
        k = best(evaluate(apply_corr(rows, cmm)[0], test, tk,
                          only=KEY_SETS, label="k"))
        print(f"  {dd:>9.1e} {mvv:>7.4f} {m['e_q']:>11.3f} {s['e_q']:>11.3f} "
              f"{k['e_q']:>12.3f}  {m['strat']} '{m['train']}'")

    print(f"\n  total wall clock {time.time() - t_all:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
