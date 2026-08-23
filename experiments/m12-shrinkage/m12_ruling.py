"""M12 — the registered ruling, applied mechanically.

Every section number here is the section of `PREREGISTRATION.md` it executes.
Nothing in this file chooses a threshold; the thresholds were fixed before any
ladder was computed and are repeated in the constants below.

Run:  python m12_ruling.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from m12_ladder import RHO, ladder, load_stack, pct
from m12_lib import IDENT, compose, corner_err, corner_err_parts, fit_to_ab

# --- registered constants (PREREGISTRATION.md sections 4 and 5) -------------
K_MATCH = 2.0          # <= 2 sigma_w  -> MATCHING
K_DIFFER = 3.0         # >  3 sigma_w  -> MATERIALLY DIFFERENT
OP_MAX_REL_ERR = 0.10  # corrected out-of-sample relative error ceiling
OP_MIN_GAIN = 0.5      # corrected <= 0.5 x uncorrected

STACKS = [
    ("coffee-bean", "data/m10-coffee-bean-edges.csv", 105),
    ("119MSDCF", "data/m10-shallow-119-edges.csv", 33),
    ("109MSDCF", "data/m10-shallow-109-edges.csv", 22),
    ("112MSDCF", "data/stack-112-edges.csv", 79),
    ("113MSDCF", "data/stack-113-edges.csv", 63),
]

CMP_SPANS = [1, 2, 3, 4, 6, 8, 12]


@dataclass
class WinS:
    stack: str
    start: int
    w: int
    s1: float
    anchor_used: int
    anchor_rms: float


def windows(st, w: int) -> list[WinS]:
    """Every *disjoint* window of length ``w`` that the stack can hold."""
    out = []
    start = 0
    while start + w < st.n:
        ld = ladder(st, start, w)
        if ld is not None and 1 in ld.frac:
            out.append(WinS(st.name, start, w, ld.frac[1], ld.anchor_used, ld.anchor_rms))
        start += w
    return out


def pooled_sd(groups: list[list[float]]) -> tuple[float, int]:
    ss, df = 0.0, 0
    for g in groups:
        if len(g) < 2:
            continue
        m = float(np.mean(g))
        ss += float(sum((x - m) ** 2 for x in g))
        df += len(g) - 1
    return (math.sqrt(ss / df) if df else float("nan")), df


def chain_transforms(st, n: int, k_corr: float = 1.0):
    """Compose the span-1 chain from frame 0, optionally inflating each edge's
    ``log|a|`` by ``k_corr``.  Rotation and translation are left as measured:
    the correction under test is a magnification correction and nothing else."""
    g = [IDENT] + [None] * (n - 1)
    for j in range(1, n):
        e = st.edge(j - 1, j)
        if e is None or g[j - 1] is None:
            g[j] = None
            continue
        la = math.log(abs(e.a))
        a = math.exp(k_corr * la) * complex(math.cos(math.atan2(e.a.imag, e.a.real)),
                                            math.sin(math.atan2(e.a.imag, e.a.real)))
        g[j] = compose(g[j - 1], (a, e.b))
    return g


def main() -> int:  # noqa: PLR0915  (a ruling is a script, not a library)
    sts = {name: load_stack(name, path, n, cfg="m10") for name, path, n in STACKS}
    for name, _p, n in STACKS:
        sts[name].n = n

    print("=" * 78)
    print("SECTION A  -  C5, the within-capture spread of S_24(1)")
    print("  Disjoint 24-frame windows inside one capture.  Same subject, same")
    print("  rig, same sweep, same estimator; only the part of the sweep moves.")
    print("  This is the noise floor the section-4 threshold is built from.")
    print("=" * 78)
    w24: dict[str, list[WinS]] = {}
    for name, _p, n in STACKS:
        w24[name] = windows(sts[name], 24)
        if not w24[name]:
            continue
        print(f"\n  {name}")
        for ws in w24[name]:
            print(f"    window {ws.start:>3}..{ws.start + ws.w:<3}  "
                  f"S_24(1) = {ws.s1:.4f}   1/S = {1.0 / ws.s1:.3f}   "
                  f"(anchor {ws.anchor_used} tiles, rms {ws.anchor_rms:.2f})")
        vals = [w.s1 for w in w24[name]]
        if len(vals) > 1:
            print(f"    mean {np.mean(vals):.4f}   sd {np.std(vals, ddof=1):.4f}   "
                  f"range {max(vals) - min(vals):.4f}")

    reg_groups = [[w.s1 for w in w24["112MSDCF"]], [w.s1 for w in w24["113MSDCF"]]]
    sigma_w, df = pooled_sd(reg_groups)
    print(f"\n  REGISTERED sigma_w (112 and 113 pooled, {df} d.f.): {sigma_w:.4f}")
    all_groups = [[w.s1 for w in w24[k]] for k, _p, _n in STACKS if len(w24[k]) > 1]
    sigma_all, df_all = pooled_sd(all_groups)
    print(f"  (all five stacks pooled, {df_all} d.f., reported not used: {sigma_all:.4f})")

    print()
    print("=" * 78)
    print("SECTION B  -  the registered primary comparison, 112 vs 113")
    print("  Statistic: S_24(1) averaged over each stack's disjoint windows.")
    print(f"  MATCHING if |diff| <= {K_MATCH:.0f} sigma_w, MATERIALLY DIFFERENT if "
          f"> {K_DIFFER:.0f} sigma_w.")
    print("=" * 78)
    m112 = float(np.mean([w.s1 for w in w24["112MSDCF"]]))
    m113 = float(np.mean([w.s1 for w in w24["113MSDCF"]]))
    diff = abs(m112 - m113)
    print(f"    112 mean S_24(1) = {m112:.4f}   (n={len(w24['112MSDCF'])} windows)")
    print(f"    113 mean S_24(1) = {m113:.4f}   (n={len(w24['113MSDCF'])} windows)")
    print(f"    |difference|     = {diff:.4f}  =  {diff / sigma_w:.2f} sigma_w")
    verdict_b = ("MATCHING" if diff <= K_MATCH * sigma_w
                 else "MATERIALLY DIFFERENT" if diff > K_DIFFER * sigma_w
                 else "INDETERMINATE")
    print(f"    -> {verdict_b}")
    mm112 = float(np.mean([w.s1 for w in w24["112MSDCF"] if w.start < 48]))
    print(f"    (robustness: restricting 112 to the two windows 113 also covers "
          f"gives {mm112:.4f}, |diff| = {abs(mm112 - m113):.4f} = "
          f"{abs(mm112 - m113) / sigma_w:.2f} sigma_w)")
    print(f"    ratio-of-ratios Q = rho_shrink(112)/rho_shrink(113) = "
          f"{m113 / m112:.4f}")

    print()
    print("=" * 78)
    print("SECTION C  -  the headline ladder, every stack, W=48 where possible")
    print("  1/S_W(1) is the shrinkage ratio, by the stated rule A_W / T_W(1).")
    print("=" * 78)
    head: dict[str, dict] = {}
    print(f"    {'stack':>12} {'W':>4} {'S_W(1)':>8} {'1/S_W(1)':>9} {'S_W(16)/S_W(1)':>15} "
          f"{'A_W %':>9} {'d_true(1) px':>13} {'anchor tiles':>13}")
    for name, _p, n in STACKS:
        st = sts[name]
        w = 48 if n > 48 else (32 if n > 32 else 16)
        ld = ladder(st, 0, w)
        if ld is None:
            continue
        g = (ld.frac.get(16, float("nan")) / ld.frac[1]) if 16 in ld.frac else float("nan")
        head[name] = dict(w=w, s1=ld.frac[1], g=g, ld=ld)
        print(f"    {name:>12} {w:>4} {ld.frac[1]:>8.4f} {1.0 / ld.frac[1]:>9.3f} "
              f"{g:>15.3f} {pct(ld.anchor):>9.4f} {ld.disp_true(1):>13.3f} "
              f"{ld.anchor_used:>13}")

    print()
    print("  Anchor robustness: the same S_W(1) recomputed against a *second*,")
    print("  disjoint long anchor T_W(W/2) (two edges) instead of the single")
    print("  direct edge (0,W).  Both are disjoint from the span-1 chain.")
    print(f"    {'stack':>12} {'S via (0,W)':>12} {'S via T_W(W/2)':>15} {'ratio':>8}")
    for name in head:
        ld = head[name]["ld"]
        half = ld.w // 2
        if half not in ld.total:
            continue
        alt = ld.total[1] / ld.total[half]
        print(f"    {name:>12} {ld.frac[1]:>12.4f} {alt:>15.4f} "
              f"{alt / ld.frac[1]:>8.4f}")

    print()
    print("=" * 78)
    print("SECTION D  -  the registered parameterisation test (section 2)")
    print("=" * 78)
    print("  H-index vs H-phys on the 112/113 pair is DEGENERATE: m12_premise.py")
    print("  measures rate(112)/rate(113) = 1.004, not the 0.795 that a shared")
    print("  focus interval at two densities requires.  The two captures share a")
    print("  per-frame physical step, so span s is the SAME physical baseline in")
    print("  both and H-index and H-phys make identical predictions here.")
    print("  The registered SSD test is therefore not run: it cannot discriminate.")
    print()
    print("  What CAN be tested is H-disp across all five stacks: fact 45 says the")
    print("  governing variable is the edge's true differential corner displacement")
    print("  d = rho * s * |rate_true|.  If so, S collapses onto one curve in d.")
    print()
    print(f"    {'stack':>12} {'span':>5} {'d_true px':>10} {'S_W(s)':>8}")
    collapse: list[tuple[str, int, float, float]] = []
    for name in head:
        ld = head[name]["ld"]
        for s in CMP_SPANS:
            if s in ld.frac:
                collapse.append((name, s, ld.disp_true(s), ld.frac[s]))
    for row in collapse:
        print(f"    {row[0]:>12} {row[1]:>5} {row[2]:>10.3f} {row[3]:>8.4f}")

    print()
    print("  The decisive pair - matched differential displacement, different stacks:")
    for a, b in [("coffee-bean", "112MSDCF"), ("coffee-bean", "113MSDCF")]:
        if a in head and b in head:
            la, lb = head[a]["ld"], head[b]["ld"]
            print(f"    {a} span 1: d = {la.disp_true(1):.3f} px, S = {la.frac[1]:.4f}")
            print(f"    {b} span 1: d = {lb.disp_true(1):.3f} px, S = {lb.frac[1]:.4f}")
            print(f"      d differs by {100 * abs(la.disp_true(1) / lb.disp_true(1) - 1):.1f}%, "
                  f"S differs by {la.frac[1] / lb.frac[1]:.3f}x")

    print()
    print("=" * 78)
    print("SECTION E  -  C7, the in-sample positive control for the correction")
    print("=" * 78)
    worst = 0.0
    for name in head:
        ld = head[name]["ld"]
        k = 1.0 / ld.frac[1]
        pred = k * ld.total[1]
        err = abs(pred - ld.anchor) / abs(ld.anchor)
        worst = max(worst, err)
        print(f"    {name:>12}  k = {k:.4f}   in-sample rel err = {err:.3e}")
    print(f"    worst {worst:.3e}   {'PASS' if worst < 1e-9 else 'FAIL'} (gate 1e-9)")

    print()
    print("=" * 78)
    print("SECTION F  -  the registered out-of-sample test (section 5)")
    print("  Fit k = 1/S_A,W(1) on stack A; predict stack B's own long anchor")
    print("  from B's span-1 edges alone.  A's edges and B's edges are disjoint;")
    print("  B's span-1 edges and B's anchor edge are disjoint.")
    print(f"  VIABLE iff rel_err_corrected <= {OP_MAX_REL_ERR:.2f} AND "
          f"<= {OP_MIN_GAIN} x uncorrected.")
    print("=" * 78)
    print(f"    {'fit on':>12} -> {'test on':<12} {'k_A':>7} {'uncorr err':>11} "
          f"{'corr err':>10} {'gain':>7} {'cond1':>6} {'cond2':>6}")
    oos: dict[tuple[str, str], dict] = {}
    for a in head:
        for b in head:
            if a == b:
                continue
            ka = 1.0 / head[a]["ld"].frac[1]
            lb = head[b]["ld"]
            unc = abs(lb.total[1] - lb.anchor) / abs(lb.anchor)
            cor = abs(ka * lb.total[1] - lb.anchor) / abs(lb.anchor)
            gain = cor / unc if unc else float("nan")
            c1 = cor <= OP_MAX_REL_ERR
            c2 = gain <= OP_MIN_GAIN
            oos[(a, b)] = dict(k=ka, unc=unc, cor=cor, gain=gain, c1=c1, c2=c2)
            print(f"    {a:>12} -> {b:<12} {ka:>7.3f} {unc:>11.4f} {cor:>10.4f} "
                  f"{gain:>7.3f} {'PASS' if c1 else 'FAIL':>6} "
                  f"{'PASS' if c2 else 'FAIL':>6}")

    pair_ok = all(oos[(a, b)]["c1"] and oos[(a, b)]["c2"]
                  for a, b in [("112MSDCF", "113MSDCF"), ("113MSDCF", "112MSDCF")])
    cross = [(a, b) for a, b in oos
             if not (a in ("112MSDCF", "113MSDCF") and b in ("112MSDCF", "113MSDCF"))]
    cross_ok = sum(1 for k in cross if oos[k]["c1"] and oos[k]["c2"])
    print(f"\n    registered 112<->113 pair passes both directions: {pair_ok}")
    print(f"    cross-scene ordered pairs passing both conditions: "
          f"{cross_ok}/{len(cross)}")
    worst_pair = max(cross, key=lambda k: oos[k]["gain"])
    print(f"    worst cross-scene transfer: {worst_pair[0]} -> {worst_pair[1]}, "
          f"correction makes it {oos[worst_pair]['gain']:.1f}x WORSE "
          f"({oos[worst_pair]['unc']:.4f} -> {oos[worst_pair]['cor']:.4f})")

    print()
    print("=" * 78)
    print("SECTION G  -  C8, what the correction does to a real chain")
    print("  Composed span-1 chain vs the DIRECT (0,j) edges, which are disjoint")
    print("  from every edge in the chain.  Worst plane-px corner error.")
    print("=" * 78)
    for name, _p, n in STACKS:
        st = sts[name]
        if name not in head:
            continue
        k_self = 1.0 / head[name]["ld"].frac[1]
        other = "113MSDCF" if name == "112MSDCF" else "112MSDCF" if name == "113MSDCF" else None
        ks = [("uncorrected", 1.0), ("self-fitted (in-sample)", k_self)]
        if other in head:
            ks.append((f"fitted on {other}", 1.0 / head[other]["ld"].frac[1]))
        print(f"\n  {name}")
        for label, k in ks:
            g = chain_transforms(st, n, k)
            errs, scale_parts = [], []
            for j in range(1, n):
                e = st.edge(0, j)
                if e is None or g[j] is None or e.used < 20:
                    continue
                errs.append(corner_err(g[j], e.t()))
                scale_parts.append(corner_err_parts(g[j], e.t())[0])
            if not errs:
                continue
            print(f"    {label:<26} k={k:.4f}  n={len(errs):>3}  "
                  f"worst {max(errs):>8.2f} px   median {np.median(errs):>7.2f} px   "
                  f"worst scale part {max(scale_parts):>8.2f} px")

    print()
    print("=" * 78)
    print("SECTION H  -  C6, the disjointness audit (SYNTHESIS section 5 item 20)")
    print("=" * 78)
    bad = 0
    for name in head:
        ld = head[name]["ld"]
        anchor_edge = {(0, ld.w)}
        for s in ld.spans:
            edges = {(k, k + s) for k in range(0, ld.w, s)}
            if edges & anchor_edge:
                print(f"    OVERLAP: {name} span {s} contains the anchor edge (0,{ld.w})")
                bad += 1
    print(f"    span rows used in every ruling: s < W only; "
          f"overlaps found: {bad}   {'PASS' if bad == 0 else 'FAIL'}")
    print("    section F: k comes from stack A's edges, the test uses stack B's")
    print("    edges only -> disjoint by construction for every ordered pair.")
    print("    section G: chain uses span-1 edges (k,k+1); truth uses direct")
    print("    edges (0,j) -> disjoint for every j >= 2.")

    print()
    print("=" * 78)
    print("SECTION I  -  the registered outcome grid (section 6)")
    print("=" * 78)
    print(f"    section 4 verdict: {verdict_b}")
    print(f"    section 5 out-of-sample, registered 112<->113 pair: "
          f"{'PASSES' if pair_ok else 'FAILS'}")
    print(f"    cross-scene transfer: {cross_ok}/{len(cross)} ordered pairs pass")
    if verdict_b == "MATCHING" and pair_ok:
        ruling = "VIABLE"
    elif verdict_b == "MATCHING":
        ruling = "PARTIAL/NEGATIVE"
    elif verdict_b == "INDETERMINATE" and pair_ok:
        ruling = "PARTIAL/POSITIVE"
    elif verdict_b == "INDETERMINATE":
        ruling = "NEGATIVE"
    elif pair_ok:
        ruling = "CONTRADICTION"
    else:
        ruling = "REFUTED"
    print(f"\n    RULING (registered grid): {ruling}")
    print("    R2 (section 6): a correction that does not beat doing nothing is")
    print("    not a calibration.  Cross-scene transfer is the case the project")
    print("    would actually ship, and it is reported above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
