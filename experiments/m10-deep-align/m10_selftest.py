"""Numeric controls P2 (positive), P3 (null), P5 (detector null).

These gate the ruling.  If any of them fails, no number measured on real data
may be quoted, because the estimator chain that produced it is not known to
work.  Nothing here touches an image: the edges are constructed algebraically
from a known ground truth, so the solvers and the metrics are being tested and
nothing else.

Run:  python m10_selftest.py
"""

import math
import sys

import numpy as np

from m10_lib import (
    IDENT,
    RHO,
    Edge,
    compose,
    corner_err,
    cycle_consistency,
    graph_stats,
    invert,
    relative,
    solve_ba,
    solve_fixed,
    solve_hops,
    solve_poly,
    summarise,
)

SPANS = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104]
N = 105
FAILS: list[str] = []


def check(name: str, ok: bool, detail: str) -> None:
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {name}: {detail}")
    if not ok:
        FAILS.append(name)


# --------------------------------------------------------------------------
# a known ground-truth camera path
# --------------------------------------------------------------------------


def truth_path(n: int = N, wobble: float = 2.0e-5, seed: int = 11):
    """Magnification sweeping smoothly but *not* polynomially with frame index,
    plus a small non-smooth wobble so that a low-order polynomial cannot be
    exactly right.  A parametric model that scores perfectly here would be
    validated by construction, which is worthless."""
    rng = np.random.default_rng(seed)
    centre = complex(-11.0, -56.0)
    g = []
    for j in range(n):
        t = j / (n - 1)
        s = -0.04575 * (1.0 - math.exp(-1.6 * t)) / (1.0 - math.exp(-1.6))
        rot = 6.0e-5 * t
        a = (1.0 + s) * complex(math.cos(rot), math.sin(rot))
        a += wobble * complex(rng.normal(), rng.normal())
        b = (1.0 - a) * centre + 0.05 * complex(rng.normal(), rng.normal())
        g.append((a, b) if j else IDENT)
    return g


def make_edges(gt, spans=SPANS, direct0=True, sigma_px=0.0, lock_bias=0.0, seed=3,
               drop=(), rms=0.4, used=90):
    """Build exact relative transforms and perturb them in a controlled way.

    ``sigma_px`` is isotropic zero-mean noise at the plane corner.
    ``lock_bias`` is a *coherent* per-step translation bias in plane px, always
    in the same direction: this is the pixel-locking mechanism M3 measured, and
    it is the thing that makes chaining fail while leaving each individual edge
    looking excellent.
    """
    rng = np.random.default_rng(seed)
    pairs = set()
    for s in spans:
        for i in range(len(gt) - s):
            pairs.add((i, i + s))
    if direct0:
        for j in range(1, len(gt)):
            pairs.add((0, j))
    out = []
    for i, j in sorted(pairs):
        if (i, j) in drop:
            continue
        a, b = relative(gt[i], gt[j])
        span = j - i
        if sigma_px:
            a += (sigma_px / RHO) * complex(rng.normal(), rng.normal()) / math.sqrt(2)
            b += sigma_px * complex(rng.normal(), rng.normal()) / math.sqrt(2)
        if lock_bias:
            b += lock_bias * span * complex(1.0, 0.0)
        out.append(
            Edge(i=i, j=j, span=span, ok=True, a=a, b=b, rms=rms, used=used,
                 raw_n=used, total=96, lever=1200.0, peak=0.5, cfg="synthetic",
                 case="p2")
        )
    return out


def gt_error(g, gt, skip_none=True):
    """Absolute corner error against the known truth, gauge-fixed at frame 0."""
    vals = []
    for j in range(len(gt)):
        if g[j] is None:
            if skip_none:
                continue
            return None
        vals.append(corner_err(g[j], gt[j]))
    return vals


# --------------------------------------------------------------------------
# P0 - algebra identities
# --------------------------------------------------------------------------


def p0_algebra() -> None:
    print("\nP0  algebra identities")
    rng = np.random.default_rng(5)

    def rnd():
        return (1.0 + 0.03 * complex(rng.normal(), rng.normal()),
                40.0 * complex(rng.normal(), rng.normal()))

    worst_inv = worst_rel = worst_assoc = 0.0
    for _ in range(500):
        t1, t2, t3 = rnd(), rnd(), rnd()
        worst_inv = max(worst_inv, corner_err(compose(t1, invert(t1)), IDENT))
        worst_rel = max(worst_rel, corner_err(compose(t1, relative(t1, t2)), t2))
        worst_assoc = max(
            worst_assoc,
            corner_err(compose(compose(t1, t2), t3), compose(t1, compose(t2, t3))),
        )
    check("compose(T, T^-1) == I", worst_inv < 1e-8, f"worst {worst_inv:.2e} px")
    check("T_i o rel(i,j) == T_j", worst_rel < 1e-8, f"worst {worst_rel:.2e} px")
    check("composition associative", worst_assoc < 1e-8, f"worst {worst_assoc:.2e} px")

    # `corner_err` is the worst corner; the least-squares objective minimises the
    # rms corner.  Both identities are checked, because the report quotes the
    # first and the solver optimises the second.
    from m10_lib import corner_err_rms, corners

    t1, t2 = rnd(), rnd()
    c = corners()
    d = [(t1[0] * p + t1[1]) - (t2[0] * p + t2[1]) for p in c]
    worst = max(abs(z) for z in d)
    rms = math.sqrt(sum(abs(z) ** 2 for z in d) / 4.0)
    check("corner_err == max over 4 corners",
          abs(worst - corner_err(t1, t2)) < 1e-8,
          f"|diff| {abs(worst - corner_err(t1, t2)):.2e} px")
    check("corner_err_rms == rms over 4 corners",
          abs(rms - corner_err_rms(t1, t2)) < 1e-8,
          f"|diff| {abs(rms - corner_err_rms(t1, t2)):.2e} px")
    # the identity the objective rests on
    da, db = t1[0] - t2[0], t1[1] - t2[1]
    ident = math.sqrt((RHO * abs(da)) ** 2 + abs(db) ** 2)
    check("rms corner err == sqrt(rho^2|da|^2 + |db|^2)",
          abs(ident - rms) < 1e-8, f"|diff| {abs(ident - rms):.2e} px")


# --------------------------------------------------------------------------
# P5 - the detector's own null
# --------------------------------------------------------------------------


def p5_detector_null() -> None:
    print("\nP5  detector null - a perfect solution must score zero")
    gt = truth_path()
    edges = make_edges(gt, sigma_px=0.0)
    errs = [corner_err(relative(gt[e.i], gt[e.j]), e.t()) for e in edges]
    check("noiseless edges reproduce truth", max(errs) < 1e-6,
          f"worst held-out corner err {max(errs):.2e} px over {len(edges)} edges")
    cyc = summarise([c["err"] for c in cycle_consistency(edges, max_triples=4000)])
    check("cycle consistency of exact edges", cyc["max"] < 1e-6,
          f"max {cyc['max']:.2e} px over {cyc['n']} triples")
    st = graph_stats(edges, N)
    check("training graph has cycles", not st["is_tree"] and st["cycle_rank"] > 0,
          f"cycle rank {st['cycle_rank']}, components {st['components']}")


# --------------------------------------------------------------------------
# P2 - positive control
# --------------------------------------------------------------------------


def run_all(edges, n=N, tag=""):
    out = {}
    out["S0-fixed"] = solve_fixed(edges, n)
    for M in (1, 8, 32):
        g, _ = solve_hops(edges, n, M)
        out[f"S{1 if M == 1 else 2}-hops{M}"] = g
    out["S3-ba"] = solve_ba(edges, n, scheme="invvar")
    out["S3-ba-unit"] = solve_ba(edges, n, scheme="unit")
    for d in (3, 6):
        r = solve_poly(edges, n, deg=d, bdeg=d)
        if r:
            out[f"S4-poly{d}"] = r[0]
    r = solve_poly(edges, n, deg=6, fixed_centre=True)
    if r:
        out["S5-centre6"] = r[0]
    out["S6-ba-smooth"] = solve_ba(edges, n, scheme="invvar", smooth=0.05)
    return out


def report(sols, gt, title, thresholds=None):
    print(f"\n  {title}")
    print(f"    {'strategy':>14} {'covered':>8} {'median':>9} {'p90':>9} {'max':>9}")
    res = {}
    for k, g in sols.items():
        if g is None:
            print(f"    {k:>14}      -")
            continue
        v = gt_error(g, gt)
        cov = sum(1 for x in g if x is not None)
        res[k] = summarise(v)
        print(f"    {k:>14} {cov:>4}/{len(gt):<3} {np.median(v):>9.3f} "
              f"{np.percentile(v, 90):>9.3f} {max(v):>9.3f}")
    if thresholds:
        for k, (lo, hi) in thresholds.items():
            if k not in res:
                check(f"{title} :: {k} produced a solution", False, "missing")
                continue
            m = res[k]["max"]
            check(f"{title} :: {k} max err in [{lo}, {hi}]", lo <= m <= hi,
                  f"max {m:.3f} px")
    return res


def p2_positive() -> None:
    print("\nP2  positive control - recover a planted camera path")
    gt = truth_path()

    e0 = make_edges(gt, sigma_px=0.0)
    sols = run_all(e0)
    report(sols, gt, "P2a noiseless edges",
           {"S3-ba": (0, 1e-6), "S1-hops1": (0, 1e-6), "S0-fixed": (0, 1e-6)})

    e1 = make_edges(gt, sigma_px=0.5, seed=17)
    sols = run_all(e1)
    r = report(sols, gt, "P2b iid edge noise, 0.5 px at the corner")
    check("P2b BA beats the adjacent chain",
          r["S3-ba"]["max"] < r["S1-hops1"]["max"],
          f"BA {r['S3-ba']['max']:.3f} px vs chain {r['S1-hops1']['max']:.3f} px")
    check("P2b BA beats the fixed reference",
          r["S3-ba"]["max"] < r["S0-fixed"]["max"],
          f"BA {r['S3-ba']['max']:.3f} px vs fixed {r['S0-fixed']['max']:.3f} px")

    # The mechanism that killed chaining in M3: a coherent per-step bias.
    e2 = make_edges(gt, sigma_px=0.2, lock_bias=0.02, seed=23)
    sols = run_all(e2)
    r = report(sols, gt, "P2c coherent per-step lock bias, 0.02 px/frame")
    check("P2c the planted chain failure is detected",
          r["S1-hops1"]["max"] > 1.5,
          f"chain max {r['S1-hops1']['max']:.3f} px (planted 0.02*104 = 2.08 px)")
    check("P2c hop ladder reduces the accumulated bias",
          r["S2-hops32"]["max"] < r["S1-hops1"]["max"],
          f"hops32 {r['S2-hops32']['max']:.3f} px vs chain {r['S1-hops1']['max']:.3f} px")

    # Deep-stack topology: long edges missing exactly where coffee-bean loses them.
    drop = {(i, j) for i in range(N) for j in range(N) if j - i > 40}
    e3 = make_edges(gt, sigma_px=0.5, seed=29, drop=drop)
    st = graph_stats([e for e in e3 if e.ok], N)
    print(f"    dropped every span > 40: {len(e3)} edges, cycle rank {st['cycle_rank']}")
    sols = run_all(e3)
    r = report(sols, gt, "P2d no edge longer than span 40")
    check("P2d fixed reference loses coverage",
          sum(1 for x in sols["S0-fixed"] if x is not None) < N,
          f"covered {sum(1 for x in sols['S0-fixed'] if x is not None)}/{N}")
    check("P2d BA still covers every frame",
          all(x is not None for x in sols["S3-ba"]), "105/105")
    check("P2d BA stays under 1 px", r["S3-ba"]["max"] < 1.0,
          f"max {r['S3-ba']['max']:.3f} px")


# --------------------------------------------------------------------------
# P3 - null
# --------------------------------------------------------------------------


def p3_null() -> None:
    print("\nP3  null - edges carrying no geometry must not be solvable")
    gt = truth_path()
    edges = make_edges(gt, sigma_px=0.0)
    rng = np.random.default_rng(101)
    shuffled = []
    for e in edges:
        k, m = rng.integers(0, N), rng.integers(0, N)
        a, b = relative(gt[int(k)], gt[int(m)])
        shuffled.append(Edge(**{**e.__dict__, "a": a, "b": b}))
    sols = run_all(shuffled)
    r = report(sols, gt, "P3 randomised edge payloads")
    check("P3 BA fails on scrambled edges", r["S3-ba"]["max"] > 5.0,
          f"max {r['S3-ba']['max']:.3f} px")
    cyc = summarise([c["err"] for c in cycle_consistency(shuffled, max_triples=4000)])
    check("P3 cycle consistency detects the scramble", cyc["median"] > 5.0,
          f"median cycle err {cyc['median']:.3f} px")


def main() -> int:
    print("=" * 78)
    print("M10 NUMERIC CONTROLS  (P0 algebra, P5 detector null, P2 positive, P3 null)")
    print("=" * 78)
    p0_algebra()
    p5_detector_null()
    p2_positive()
    p3_null()
    print("\n" + "=" * 78)
    if FAILS:
        print(f"CONTROLS FAILED ({len(FAILS)}): " + "; ".join(FAILS))
        print("Per PREREGISTRATION section 5, no real-data number may be quoted.")
        return 1
    print("ALL CONTROLS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
