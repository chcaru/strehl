"""M23 gate (a) - conservation / telescoping under the per-edge correction,
with the registered nulls.

The identity (M12's, unchanged).  For a window ``start .. start+W``::

    T_W(1) = sum_k log|a_{k,k+1}|          A_W = log|a_{start,start+W}|
    1/S_W(1) = A_W / T_W(1)

Every span estimates the same physical quantity, so an unbiased estimator gives
1.000.  ``coffee-bean`` reads 3.260 (M12) / 3.222 (orchestrator's independent
recomputation).

The correction replaces each ``log|a|`` by ``log|a| / R``.

FAILURE DIRECTION OF THIS METRIC (registered, PREREGISTRATION section 2):
1/S -> 1 is manufactured by ANY operation that inflates the magnitude of
span-1 log-scales.  ``E[1/R] > 1/E[R]`` for any R with variance, so dividing by
a NOISY R inflates even when R carries no information.  The metric cannot tell a
correct per-edge correction from an undirected inflation, so it is scored only
jointly with N1 (shuffled R) and N2 (constant R).

Run:  python m23_conserve.py > out\\conservation.txt
"""

from __future__ import annotations

import math

import numpy as np

from m23_lib import read_edges
from m23_mc import PRIMARY_DELTA, by_delta, by_span, read_metacal

DELTAS = [1e-4, 2e-4, 4e-4, 8e-4, 1.6e-3]
NSHUF = 400

CASES = [
    ("coffee-bean", "data/coffee-bean-metacal.csv", "data/m10-coffee-bean-edges.csv", 105, 48),
    ("112MSDCF", "data/stack-112-metacal.csv", "data/m12-stack-112-edges.csv", 79, 48),
]


def pct(x: float) -> float:
    return 100.0 * (math.exp(x) - 1.0)


def load(mc_path, edge_path, cfg="m10"):
    mc = read_metacal(mc_path, cfg=cfg)
    emap = {}
    for e in read_edges(edge_path, cfg=cfg):
        if not e.ok:
            continue
        k = (e.i, e.j)
        if k not in emap or e.used > emap[k].used:
            emap[k] = e
    return mc, emap


def repro_gate(name, mc, emap):
    """G0: does this milestone's own base fit reproduce the committed edge CSV?

    Same estimator, same frames, same config, so the answer must be 'exactly'.
    Anything else means the harness moved between M10/M12 and M23.
    """
    d = []
    for r in by_delta(by_span(mc, 1), DELTAS[0]):
        e = emap.get((r.i, r.j))
        if e is None:
            continue
        d.append(r.l0 - math.log(abs(e.a)))
    d = np.array(d)
    print(f"\n  {name}: {d.size} span-1 edges compared with the committed CSV")
    print(f"    max |l0(M23) - log|a|(committed)| = {np.abs(d).max():.3e}   "
          f"median {np.median(np.abs(d)):.3e}")
    print(f"    G0 {'PASS' if np.abs(d).max() < 1e-7 else 'FAIL'} "
          f"(threshold 1e-7; the two are the same deterministic computation)")


def one_over_s(l_by_edge, anchor, start, w):
    t = 0.0
    for k in range(start, start + w):
        v = l_by_edge.get((k, k + 1))
        if v is None or not math.isfinite(v):
            return float("nan")
        t += v
    return anchor / t if t else float("nan")


def run_case(name, mc_path, edge_path, n, w):
    print("=" * 100)
    print(f"GATE (a)  CONSERVATION UNDER THE PER-EDGE CORRECTION - {name}")
    print(f"  window 0..{w},  1/S_W(1) = A_W / T_W(1).   PASS |1/S - 1| <= 0.15, "
          f"PARTIAL <= 2.13, else FAIL")
    print("=" * 100)
    mc, emap = load(mc_path, edge_path)
    repro_gate(name, mc, emap)

    anchor_e = emap.get((0, w))
    anchor = math.log(abs(anchor_e.a))
    print(f"\n  anchor A_{w} = {pct(anchor):+.4f}%  ({anchor_e.used} tiles, "
          f"rms {anchor_e.rms:.2f})")

    raw = {(r.i, r.j): r.l0 for r in by_delta(by_span(mc, 1), DELTAS[0])}
    base = one_over_s(raw, anchor, 0, w)
    print(f"  UNCORRECTED 1/S_{w}(1) = {base:.4f}   "
          f"(M12 published 3.260 on coffee-bean; orchestrator 3.222)")

    print(f"\n  {'delta':>9} {'measured R':>11} {'N1 shuffled':>27} {'N2 const=med':>13} "
          f"{'|R| floor 0.2':>14}")
    print(f"  {'':>9} {'1/S':>11} {'median [p05,p95] of 1/S':>27} {'1/S':>13} {'1/S':>14}")
    rows_out = []
    for d in DELTAS:
        rs = by_delta(by_span(mc, 1), d)
        keys = [(r.i, r.j) for r in rs]
        rvals = np.array([r.r_two for r in rs])
        l0 = np.array([r.l0 for r in rs])

        corr = {k: l / r if r != 0 else np.nan for k, l, r in zip(keys, l0, rvals)}
        v_meas = one_over_s(corr, anchor, 0, w)

        rng = np.random.default_rng(20230823)
        shuf = []
        for _ in range(NSHUF):
            p = rng.permutation(rvals)
            cs = {k: l / rr if rr != 0 else np.nan for k, l, rr in zip(keys, l0, p)}
            shuf.append(one_over_s(cs, anchor, 0, w))
        shuf = np.array([x for x in shuf if math.isfinite(x)])

        med = float(np.median(rvals))
        cc = {k: l / med for k, l in zip(keys, l0)}
        v_const = one_over_s(cc, anchor, 0, w)

        fl = np.where(np.abs(rvals) < 0.2, np.copysign(0.2, rvals), rvals)
        cf = {k: l / rr for k, l, rr in zip(keys, l0, fl)}
        v_floor = one_over_s(cf, anchor, 0, w)

        print(f"  {d:>9.1e} {v_meas:>11.4f}   {np.median(shuf):>8.4f} "
              f"[{np.percentile(shuf, 5):>7.4f},{np.percentile(shuf, 95):>7.4f}] "
              f"{v_const:>13.4f} {v_floor:>14.4f}")
        rows_out.append((d, v_meas, float(np.median(shuf)), v_const))

    print("\n  VERDICT at the registered primary delta = "
          f"{PRIMARY_DELTA:.0e}:")
    for d, v, s, c in rows_out:
        if abs(d - PRIMARY_DELTA) < 1e-12:
            verdict = "PASS" if abs(v - 1) <= 0.15 else ("PARTIAL" if v <= 2.13 else "FAIL")
            print(f"    measured-R 1/S = {v:.4f} -> gate (a) {verdict}")
            print(f"    N1 shuffled-R  = {s:.4f}   "
                  f"({100 * (base - s) / (base - v) if base != v else float('nan'):.1f}% of the "
                  f"measured correction's movement, with ZERO per-edge information)")
            print(f"    N2 constant-R  = {c:.4f}   "
                  f"(this is the scalar M12 refuted, on this code path)")

    # inflation decomposition - how much of the movement is Jensen, not signal
    print("\n  WHERE THE MOVEMENT COMES FROM (the rule-17 shared path)")
    print(f"    {'delta':>9} {'mean 1/R':>10} {'1/mean R':>10} {'Jensen ratio':>13} "
          f"{'corr(R, l0)':>12} {'corr(R, used)':>14} {'corr(R, rms)':>13}")
    for d in DELTAS:
        rs = by_delta(by_span(mc, 1), d)
        r = np.array([x.r_two for x in rs])
        l = np.array([x.l0 for x in rs])
        u = np.array([float(x.used0) for x in rs])
        q = np.array([x.rms0 for x in rs])
        print(f"    {d:>9.1e} {np.mean(1 / r):>10.4f} {1 / np.mean(r):>10.4f} "
              f"{np.mean(1 / r) * np.mean(r):>13.4f} {np.corrcoef(r, l)[0, 1]:>12.4f} "
              f"{np.corrcoef(r, u)[0, 1]:>14.4f} {np.corrcoef(r, q)[0, 1]:>13.4f}")

    # every width-w window, not one hand-matched one (M12's verification lesson)
    print(f"\n  EVERY width-{w} WINDOW AT EVERY OFFSET "
          f"(M12's verification found a single window is where selection hides)")
    print(f"    {'delta':>9} {'n win':>6} {'1/S med':>9} {'min':>9} {'max':>9}  "
          f"{'uncorrected med':>16}")
    unc = []
    for st in range(0, n - w):
        ae = emap.get((st, st + w))
        if ae is None:
            continue
        a = math.log(abs(ae.a))
        unc.append(one_over_s(raw, a, st, w))
    unc = np.array([x for x in unc if math.isfinite(x)])
    for d in DELTAS:
        rs = by_delta(by_span(mc, 1), d)
        corr = {(r.i, r.j): (r.l0 / r.r_two if r.r_two else np.nan) for r in rs}
        vals = []
        for st in range(0, n - w):
            ae = emap.get((st, st + w))
            if ae is None:
                continue
            a = math.log(abs(ae.a))
            vals.append(one_over_s(corr, a, st, w))
        vals = np.array([x for x in vals if math.isfinite(x)])
        print(f"    {d:>9.1e} {vals.size:>6} {np.median(vals):>9.4f} {vals.min():>9.4f} "
              f"{vals.max():>9.4f}  {np.median(unc):>16.4f}")

    # local telescoping: 103 independent instances instead of one aggregate
    print("\n  GATE (a2)  LOCAL TELESCOPING, PER TRIPLE "
          "(103 instances, not one aggregate)")
    print("    rho_k = l(k,k+2) / [l(k,k+1) + l(k+1,k+2)].  Unbiased => 1.000.")
    print("    FAILURE DIRECTION: rho is a ratio of small noisy sums; it is undefined")
    print("    where the denominator crosses zero, so the MEDIAN is quoted, never the mean.")
    print(f"    {'delta':>9} {'rho med (uncorr)':>17} {'rho med (corr)':>15} "
          f"{'med R span1':>12} {'med R span2':>12}")
    for d in DELTAS:
        r1 = {(r.i, r.j): r for r in by_delta(by_span(mc, 1), d)}
        r2 = {(r.i, r.j): r for r in by_delta(by_span(mc, 2), d)}
        u, c = [], []
        for (i, j), e2 in r2.items():
            a = r1.get((i, i + 1))
            b = r1.get((i + 1, i + 2))
            if a is None or b is None:
                continue
            den = a.l0 + b.l0
            if abs(den) < 1e-6:
                continue
            u.append(e2.l0 / den)
            denc = a.l0 / a.r_two + b.l0 / b.r_two
            if abs(denc) < 1e-6:
                continue
            c.append((e2.l0 / e2.r_two) / denc)
        print(f"    {d:>9.1e} {np.median(u):>17.4f} {np.median(c):>15.4f} "
              f"{np.median([x.r_two for x in r1.values()]):>12.4f} "
              f"{np.median([x.r_two for x in r2.values()]):>12.4f}")
    print()


def main() -> int:
    for name, mc, ed, n, w in CASES:
        run_case(name, mc, ed, n, w)

    print("=" * 100)
    print("GATE (b) SECOND CLAUSE - does the correction move 112MSDCF's 1/S by < 0.10?")
    print("  A correction that 'fixes' a stack with no defocus asymmetry to fix is")
    print("  measuring something else.  Numbers are in the 112MSDCF block above.")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
