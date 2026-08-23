"""M13 analysis. Reads only files under experiments/m13-window-depth/data.

Every table this prints names the stratum it filtered on, because the M11
post-mortem in the brief records that a previous analysis silently kept the
last row per operator and recovered the opposite correlations. Filtering is
explicit and loud here on purpose.
"""

import csv
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# The M13 window ladder, in numeric order. Derived from the data so a denser
# sweep is picked up automatically and rows never sort lexicographically
# (w11 before w2) by accident.
LADDER = []


def set_ladder(*files):
    global LADDER
    ws = set()
    for f in files:
        for r in rows(f):
            if "window" in r:
                ws.add(int(r["window"]))
    if ws:
        LADDER = sorted(ws)


def rows(name):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return []
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def win(r):
    return int(r["window"])


def med(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return float("nan")
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def turnover(pairs, mode="min"):
    """Report an argmin/argmax and say honestly whether it is an endpoint.

    PREREGISTRATION rule: an endpoint argmin is reported as 'no turnover found
    within the sweep', never as an optimum. This function is the only place
    that decision is made, so it cannot drift between tables.
    """
    pairs = [(w, v) for w, v in pairs if v == v]
    if not pairs:
        return "n/a"
    pairs.sort()
    best = min(pairs, key=lambda p: p[1]) if mode == "min" else max(pairs, key=lambda p: p[1])
    w = best[0]
    if w == pairs[0][0] or w == pairs[-1][0]:
        return f"w{w} (ENDPOINT - no turnover within sweep)"
    return f"w{w} (interior - turns over)"


def sec(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def noise_axis():
    sec("1. N (merged noise / single-frame noise) vs window - flat ROIs, width 1")
    print("stratum: roi_kind='flat', width=1; median over ROIs then mean over stacks")
    per = defaultdict(list)
    for stk in ("109MSDCF", "119MSDCF"):
        by = defaultdict(list)
        for r in rows(f"noise-{stk}.csv"):
            if r["roi_kind"] != "flat" or int(r["width"]) != 1:
                continue
            by[win(r)].append(float(r["ratio"]))
        for w, v in by.items():
            per[w].append(med(v))
    print(f"{'window':>7} {'N':>9}")
    out = []
    for w in LADDER:
        if w in per:
            n = sum(per[w]) / len(per[w])
            out.append((w, n))
            print(f"{w:>7} {n:>9.4f}")
    print("  argmin:", turnover(out, "min"))
    return dict(out)


def phi_axis():
    sec("2. phi (centre-tap fraction) vs window - real texture")
    print("STRATUM WARNING: phi is measured at several probe amplitudes (delta).")
    print("Pooling them silently would average unlike things, so each delta is")
    print("printed separately. M11 A1 quoted the delta=8 stratum.")
    for tag, f in (("pointwise-normalised", "phi-109MSDCF.csv"),
                   ("Norm::None", "phi-109MSDCF-nonorm.csv")):
        rr = rows(f)
        if not rr:
            continue
        for delta in sorted({float(r["delta"]) for r in rr}):
            by = defaultdict(list)
            for r in rr:
                if float(r["delta"]) != delta:
                    continue
                by[win(r)].append(float(r["phi"]))
            print(f"\n  {tag}, delta = {delta:g} DN "
                  f"(reach {rr[0]['reach']} px, aggregated over the probe lattice)")
            print(f"  {'window':>7} {'phi':>10} {'1/(2w+1)^2':>12} {'ratio':>8}")
            out = []
            for w in LADDER:
                if w in by:
                    v = sum(by[w]) / len(by[w])
                    out.append((w, v))
                    an = 1.0 / (2 * w + 1) ** 2
                    print(f"  {w:>7} {v:>10.6f} {an:>12.6f} {v/an:>8.3f}")
            print("  argmax:", turnover(out, "max"))


def planted_axis():
    sec("3. selectivity vs window on CONTINUOUS plants (no depth discontinuity)")
    for tag, suffix in (("M11-matched fronto-parallel", "m11match"), ("tilt sweep", "tilt")):
        agg = defaultdict(lambda: defaultdict(list))
        for stk in ("109MSDCF", "119MSDCF"):
            for r in rows(f"planted-{stk}-{suffix}.csv"):
                if r.get("roi_kind", "detail") != "detail" or int(r["width"]) != 1:
                    continue
                t = int(round(float(r.get("tilt", 0))))
                agg[t][win(r)].append((float(r["acc"]), float(r["mae"])))
        for t in sorted(agg):
            print(f"\n  {tag}: tilt {t} DN-frames/px  (stratum roi_kind='detail', width=1)")
            print(f"  {'window':>7} {'acc':>8} {'mae':>8}")
            a_out, m_out = [], []
            for w in LADDER:
                if w in agg[t]:
                    vs = agg[t][w]
                    a = sum(v[0] for v in vs) / len(vs)
                    m = sum(v[1] for v in vs) / len(vs)
                    a_out.append((w, a))
                    m_out.append((w, m))
                    print(f"  {w:>7} {a:>8.4f} {m:>8.4f}")
            print("    acc argmax:", turnover(a_out, "max"))
            print("    mae argmin:", turnover(m_out, "min"))


def edge_cells(stk):
    """(shape, step) -> window -> list of E_excess, one per seed.

    Strata filtered explicitly: width == 1. The seed axis is kept as a list
    rather than collapsed on read, so the seed-to-seed spread stays visible
    and a two-window tie can be judged against it.
    """
    out = defaultdict(lambda: defaultdict(list))
    for r in rows(f"edge-{stk}.csv"):
        if int(r["width"]) != 1:
            continue
        out[(r["shape"], int(r["step"]))][win(r)].append(r)
    return out


def edge_axis():
    sec("4. EDGE: what a depth discontinuity does to the window trade-off")
    print("stratum: width=1; each row is the mean over the seed repeats")
    for stk in ("109MSDCF", "119MSDCF"):
        cells = edge_cells(stk)
        for (shape, step) in sorted(cells, key=lambda k: (k[0], k[1])):
            sub = cells[(shape, step)]
            nseed = max(len(v) for v in sub.values())
            print(f"\n  {stk} / {shape} / depth step {step} frames  ({nseed} seeds)")
            print(f"  {'window':>7} {'E_excess':>9} {'+-sd':>6} {'E_band':>8} {'floor':>8} "
                  f"{'bleed_bg':>9} {'bleed_fg':>9} {'mis_bg':>8} {'mis_fg':>8} "
                  f"{'dmae_b':>7} {'acc':>7} {'acc_band':>9}")
            ex, mi = [], []
            for w in LADDER:
                if w not in sub:
                    continue
                g = sub[w]
                f = lambda k: sum(float(r[k]) for r in g) / len(g)  # noqa: E731
                e = f("excess_dn")
                es = [float(r["excess_dn"]) for r in g]
                sd = (sum((v - e) ** 2 for v in es) / max(1, len(es) - 1)) ** 0.5
                m = max(f("mis_bg"), f("mis_fg"))
                ex.append((w, e))
                mi.append((w, m))
                print(f"  {w:>7} {e:>9.3f} {sd:>6.2f} {f('band_rms'):>8.2f} "
                      f"{f('floor_rms'):>8.2f} {f('bleed_bg'):>9.2f} {f('bleed_fg'):>9.2f} "
                      f"{f('mis_bg'):>8.2f} {f('mis_fg'):>8.2f} {f('dmae_band'):>7.3f} "
                      f"{f('acc'):>7.4f} {f('acc_band'):>9.4f}")
            print("    E_excess argmin:", turnover(ex, "min"))
            print("    max mis width argmin:", turnover(mi, "min"))
            accs = [(w, sum(float(r["acc"]) for r in sub[w]) / len(sub[w]))
                    for w in LADDER if w in sub]
            accb = [(w, sum(float(r["acc_band"]) for r in sub[w]) / len(sub[w]))
                    for w in LADDER if w in sub]
            print("    acc argmax (M11's metric class):", turnover(accs, "max"))
            print("    acc_band argmax (M11's metric, restricted to the band):",
                  turnover(accb, "max"))


def edge_summary():
    sec("5. HEADLINE: E_excess optimum per (stack, shape, step), seed-averaged")
    print(f"{'stack':>9} {'shape':>16} {'step':>5} {'argmin':>6} {'E@min':>8} "
          f"{'seed sd':>8} {'E@w5':>8} {'E@w11':>8} {'E@w15':>8} {'E@w40':>8} {'interior?':>10}")
    for stk in ("109MSDCF", "119MSDCF"):
        cells = edge_cells(stk)
        for (shape, step) in sorted(cells, key=lambda k: (k[0], k[1])):
            sub = cells[(shape, step)]
            e = {w: sum(float(r["excess_dn"]) for r in g) / len(g) for w, g in sub.items()}
            ws = [w for w in LADDER if w in e]
            bw = min(ws, key=lambda w: e[w])
            g = sub[bw]
            es = [float(r["excess_dn"]) for r in g]
            m = sum(es) / len(es)
            sd = (sum((v - m) ** 2 for v in es) / max(1, len(es) - 1)) ** 0.5
            interior = "interior" if bw not in (ws[0], ws[-1]) else "ENDPOINT"
            print(f"{stk:>9} {shape:>16} {step:>5} {bw:>6} {e[bw]:>8.3f} {sd:>8.3f} "
                  f"{e.get(5, float('nan')):>8.3f} {e.get(11, float('nan')):>8.3f} "
                  f"{e.get(15, float('nan')):>8.3f} {e.get(40, float('nan')):>8.3f} "
                  f"{interior:>10}")


def cost_axis():
    rr = rows("cost-109MSDCF.csv")
    if not rr:
        return
    sec("6. COST vs window (ms/frame/Mpx) - is a wide window free?")
    print("box_mean is O(1) per pixel in the radius, so the prediction is 'flat'.")
    print(f"{'measure':>18} {'window':>7} {'support':>8} {'ms/f/Mpx':>10}")
    vals = []
    for r in rr:
        print(f"{r['measure']:>18} {r['window']:>7} {r['support_radius']:>8} "
              f"{float(r['ms_per_frame_per_mpx']):>10.4f}")
        if r["measure"].startswith("tenengrad-w") and int(r["window"]) > 0:
            vals.append(float(r["ms_per_frame_per_mpx"]))
    if vals:
        lo, hi = min(vals), max(vals)
        print(f"\n  windowed tenengrad w1..w40: min {lo:.4f} max {hi:.4f} "
              f"spread {100*(hi-lo)/lo:.2f}%")
        print("  rule: spread = 100 * (max - min) / min over the windowed rows only.")


def adaptive_axis():
    rr = rows("adaptive-109MSDCF.csv")
    if not rr:
        return
    sec("7. ADAPTIVE: can two windows beat the better single one?")
    print("registered threshold: an oracle gain < 5% of the better fixed arm's")
    print("band RMS means 'recommend a single global window'.")
    print("arms: fixed:<m> | oracle:min-error (reads the answer, upper bound)")
    print("      rule:disagree tau (realisable: use narrow where the two windows")
    print("      disagree by more than tau frames)")
    print()
    print(f"{'narrow':>14} {'wide':>14} {'step':>5} {'E_nar':>8} {'E_wid':>8} "
          f"{'E_orac':>8} {'orac%':>7} {'best rule':>16} {'E_rule':>8} {'rule%':>7} {'verdict':>9}")
    groups = defaultdict(list)
    for r in rr:
        groups[(r["narrow"], r["wide"], int(r["step"]))].append(r)
    for k in sorted(groups, key=lambda k: (k[0], k[1], k[2])):
        g = groups[k]
        nar = next((float(r["rms_band"]) for r in g if r["arm"] == f"fixed:{k[0]}"), float("nan"))
        wid = next((float(r["rms_band"]) for r in g if r["arm"] == f"fixed:{k[1]}"), float("nan"))
        orc = next((float(r["rms_band"]) for r in g if r["arm"] == "oracle:min-error"), float("nan"))
        rules = [(int(r["tau"]), float(r["rms_band"])) for r in g if r["arm"] == "rule:disagree"]
        best_rule = min(rules, key=lambda t: t[1]) if rules else (0, float("nan"))
        base = min(nar, wid)
        og = 100.0 * (base - orc) / base
        rg = 100.0 * (base - best_rule[1]) / base
        verdict = "ADAPTIVE" if og >= 5.0 else "single"
        print(f"{k[0]:>14} {k[1]:>14} {k[2]:>5} {nar:>8.3f} {wid:>8.3f} {orc:>8.3f} "
              f"{og:>7.2f} {'tau='+str(best_rule[0]):>16} {best_rule[1]:>8.3f} "
              f"{rg:>7.2f} {verdict:>9}")
    print()
    print("  rule for orac% : 100 * (min(E_nar, E_wid) - E_oracle) / min(E_nar, E_wid)")
    print("  rule for rule% : same, with the best realisable disagreement gate")


def regret():
    """Pick the single global window that minimises worst-case regret.

    This is the decision the milestone owes the implementation. Regret is
    measured in the halo metric's own units (excess DN over the physical
    floor) so that a cell where NO window can do well does not dominate.
    """
def cell_table(field, reduce_fn=None):
    """(stack, shape, step) -> window -> seed-averaged value of `field`."""
    out = {}
    for stk in ("109MSDCF", "119MSDCF"):
        for k, v in edge_cells(stk).items():
            out[(stk,) + k] = {
                w: (reduce_fn(g) if reduce_fn
                    else sum(float(r[field]) for r in g) / len(g))
                for w, g in v.items()
            }
    return out


def _max_mis(g):
    return sum(max(float(r["mis_bg"]), float(r["mis_fg"])) for r in g) / len(g)


def regret():
    """Pick the single global window that minimises worst-case regret.

    This is the decision the milestone owes the implementation. Regret is
    measured in each metric's own units so that a cell where NO window can do
    well does not dominate. Three objectives are run because a recommendation
    that depends on which of my own metrics I picked is not a recommendation.
    """
    sec("8. DECISION: which single global window minimises regret across cells?")
    objectives = (
        ("E_excess (DN over the physical floor)", cell_table("excess_dn")),
        ("max mis-selection width (px)", cell_table(None, _max_mis)),
        ("dmae in the band (frames)", cell_table("dmae_band")),
    )
    for oname, cells in objectives:
        print()
        print("-" * 78)
        print(f"  objective: {oname}")
        print("-" * 78)
        for label, keep in (("ALL cells incl. step 0", lambda k: True),
                            ("cells WITH a depth step (step > 0)", lambda k: k[2] > 0),
                            ("NULL: step 0 only (no discontinuity)", lambda k: k[2] == 0)):
            sub = {k: v for k, v in cells.items() if keep(k)}
            if not sub:
                continue
            print(f"\n  {label}  ({len(sub)} cells)")
            print(f"  {'window':>7} {'mean regret':>12} {'worst regret':>13} {'worst cell':>32}")
            rank = []
            for w in LADDER:
                regs = []
                for k, v in sub.items():
                    if w not in v:
                        continue
                    best = min(v.values())
                    regs.append((v[w] - best, k))
                if not regs:
                    continue
                mean = sum(r[0] for r in regs) / len(regs)
                worst = max(regs, key=lambda r: r[0])
                rank.append((w, mean, worst[0], worst[1]))
                cell = f"{worst[1][0]}/{worst[1][1]}/s{worst[1][2]}"
                print(f"  {w:>7} {mean:>12.3f} {worst[0]:>13.3f} {cell:>32}")
            if rank:
                bm = min(rank, key=lambda t: t[1])
                bw = min(rank, key=lambda t: t[2])
                em = "ENDPOINT" if bm[0] in (LADDER[0], LADDER[-1]) else "interior"
                ew = "ENDPOINT" if bw[0] in (LADDER[0], LADDER[-1]) else "interior"
                print(f"    min mean regret : w{bm[0]} ({bm[1]:.3f})  [{em}]")
                print(f"    min worst regret: w{bw[0]} ({bw[2]:.3f})  [{ew}]")
            print("    rule: regret(w, cell) = f(w, cell) - min_w' f(w', cell)")


def head_to_head():
    """M11's recommendation against M13's, on every axis, cell by cell.

    A Pareto claim has to be checked cell by cell, not on means. The count of
    cells where the wider window loses is the honest form of the claim.
    """
    sec("9. HEAD TO HEAD: tenengrad-w5 (M11's 11x11) vs the M13 candidates")
    cells = cell_table("excess_dn")
    for cand in (6, 8, 9, 10, 11, 12, 13, 15, 17, 20):
        if cand not in LADDER:
            continue
        wins = sum(1 for v in cells.values() if v.get(cand, 1e9) < v.get(5, 1e9))
        loss = sum(1 for v in cells.values() if v.get(cand, 1e9) > v.get(5, 1e9))
        worst = max(((v.get(cand, 0) - v.get(5, 0), k) for k, v in cells.items()),
                    key=lambda t: t[0])
        print(f"  w{cand:<3} vs w5 on E_excess: better in {wins}/{len(cells)} cells, "
              f"worse in {loss}; worst single-cell loss {max(0.0, worst[0]):.2f} DN "
              f"at {worst[1][0]}/{worst[1][1]}/s{worst[1][2]}")
    print()
    print("  rule: 'better' = strictly lower seed-averaged E_excess in that cell.")


def stability():
    """Is the argmin stable across noise realisations?

    The regret tables average the three seeds before choosing. That hides
    whether the choice survives a different noise draw. Here the whole
    decision is recomputed inside each seed independently, so the spread of
    the argmin is the honest uncertainty on the recommendation.
    """
    sec("10. STABILITY: recompute the decision inside each seed separately")
    per_seed = defaultdict(lambda: defaultdict(dict))
    for stk in ("109MSDCF", "119MSDCF"):
        for r in rows(f"edge-{stk}.csv"):
            if int(r["width"]) != 1:
                continue
            key = (stk, r["shape"], int(r["step"]))
            # The CSV records the per-step derived seed (cli * 1_000_003 + step).
            # Integer division recovers the CLI seed that identifies the repeat.
            per_seed[int(r["seed"]) // 1_000_003][key][win(r)] = float(r["excess_dn"])
    print("objective E_excess, cells with a depth step (step > 0)")
    print(f"{'seed':>12} {'argmin mean regret':>20} {'argmin worst regret':>21}")
    picks = []
    for seed in sorted(per_seed):
        sub = {k: v for k, v in per_seed[seed].items() if k[2] > 0}
        rank = []
        for w in LADDER:
            regs = [v[w] - min(v.values()) for v in sub.values() if w in v]
            if regs:
                rank.append((w, sum(regs) / len(regs), max(regs)))
        bm = min(rank, key=lambda t: t[1])[0]
        bw = min(rank, key=lambda t: t[2])[0]
        picks.append(bm)
        print(f"{seed:>12} {'w' + str(bm):>20} {'w' + str(bw):>21}")
    print(f"\n  argmin across the {len(picks)} seeds: "
          f"{', '.join('w' + str(p) for p in picks)}")
    print("  rule: the full regret table is rebuilt from that seed's rows alone.")

    print("\n  How flat is the basin? mean regret (step>0, seed-averaged) around")
    print("  the argmin, next to the seed-to-seed sd of E_excess itself:")
    cells = cell_table("excess_dn")
    sds = []
    for stk in ("109MSDCF", "119MSDCF"):
        for k, v in edge_cells(stk).items():
            if k[1] == 0:
                continue
            for w, g in v.items():
                es = [float(r["excess_dn"]) for r in g]
                m = sum(es) / len(es)
                sds.append((sum((x - m) ** 2 for x in es) / max(1, len(es) - 1)) ** 0.5)
    print(f"  median seed-to-seed sd of E_excess over all cells: "
          f"{med(sds):.3f} DN  (n = {len(sds)})")
    sub = {k: v for k, v in cells.items() if k[2] > 0}
    for w in LADDER:
        if not (8 <= w <= 23):
            continue
        regs = [v[w] - min(v.values()) for v in sub.values() if w in v]
        print(f"    w{w:<3} mean regret {sum(regs)/len(regs):>7.3f} DN   "
              f"worst {max(regs):>7.3f} DN")


def barwidth():
    """Confound check: does the argmin track the planted feature size?

    The main run planted one bar (24 px wide). If the measured optimum simply
    followed the bar, it would be an artifact of the plant. The bar width is
    swept over an order of magnitude here and the argmin is recomputed inside
    each width.
    """
    rr = rows("barwidth-109MSDCF.csv")
    if not rr:
        return
    sec("11. CONFOUND: does the optimum track the planted bar width?")
    print(f"{'bar width px':>13} {'step':>5} {'argmin':>7} {'E@min':>8} {'E@w13':>8} "
          f"{'interior?':>10}")
    for shape in sorted({r["shape"] for r in rr}):
        for step in sorted({int(r["step"]) for r in rr}):
            sub = {win(r): float(r["excess_dn"])
                   for r in rr if r["shape"] == shape and int(r["step"]) == step}
            if not sub:
                continue
            ws = [w for w in LADDER if w in sub]
            bw = min(ws, key=lambda w: sub[w])
            interior = "interior" if bw not in (ws[0], ws[-1]) else "ENDPOINT"
            # shape label is bar@<row>w<width>
            width_px = shape.split("w")[-1]
            print(f"{width_px:>13} {step:>5} {'w' + str(bw):>7} {sub[bw]:>8.3f} "
                  f"{sub.get(13, float('nan')):>8.3f} {interior:>10}")
    print("\n  If the argmin were an artifact of the plant it would rise with the")
    print("  bar width. rule: argmin over the same 20-point window ladder, one")
    print("  seed, within each (bar width, step) cell.")


def m11_blindness():
    """Can M11's per-pixel selectivity metric see halo damage? Directly tested.

    For each cell, compare the window M11's metric class would pick (argmax of
    per-pixel exact-hit accuracy, both over the whole ROI and restricted to
    the band around the boundary) against the window E_excess picks. If the
    accuracy metric is structurally blind, its argmax will sit at the wide
    endpoint even where E_excess has turned over hard.
    """
    sec("12. Can M11's metric see the damage? acc argmax vs E_excess argmin")
    print(f"{'stack':>9} {'shape':>16} {'step':>5} {'acc argmax':>11} {'accband argmax':>15} "
          f"{'E argmin':>9} {'E@acc-pick':>11} {'E@E-pick':>9} {'penalty DN':>11}")
    pen = []
    dirn = []
    for stk in ("109MSDCF", "119MSDCF"):
        cells = edge_cells(stk)
        for (shape, step) in sorted(cells, key=lambda k: (k[0], k[1])):
            if step == 0:
                continue
            sub = cells[(shape, step)]
            avg = lambda w, k: sum(float(r[k]) for r in sub[w]) / len(sub[w])  # noqa: E731
            ws = [w for w in LADDER if w in sub]
            wa = max(ws, key=lambda w: avg(w, "acc"))
            wb = max(ws, key=lambda w: avg(w, "acc_band"))
            we = min(ws, key=lambda w: avg(w, "excess_dn"))
            p = avg(wa, "excess_dn") - avg(we, "excess_dn")
            pen.append(p)
            dirn.append((wa, we))
            print(f"{stk:>9} {shape:>16} {step:>5} {'w' + str(wa):>11} {'w' + str(wb):>15} "
                  f"{'w' + str(we):>9} {avg(wa, 'excess_dn'):>11.3f} "
                  f"{avg(we, 'excess_dn'):>9.3f} {p:>11.3f}")
    print(f"\n  mean penalty from following the accuracy argmax: {sum(pen)/len(pen):.2f} DN")
    print(f"  worst penalty: {max(pen):.2f} DN   ({len(pen)} depth-step cells)")
    print(f"  cells where the accuracy argmax is STRICTLY WIDER than the E argmin: "
          f"{sum(1 for a, e in dirn if a > e)}/{len(dirn)}")
    print(f"  cells where it is strictly narrower: {sum(1 for a, e in dirn if a < e)}/{len(dirn)}")
    print("  rule: penalty = E_excess at the accuracy-chosen window minus")
    print("        E_excess at its own argmin, inside the same cell.")


def main():
    set_ladder("noise-109MSDCF.csv", "edge-109MSDCF.csv", "planted-109MSDCF-tilt.csv")
    print("window ladder read from the data:", " ".join(f"w{w}" for w in LADDER))
    noise_axis()
    phi_axis()
    planted_axis()
    edge_axis()
    edge_summary()
    cost_axis()
    adaptive_axis()
    regret()
    head_to_head()
    stability()
    barwidth()
    m11_blindness()
    print()
    print("done.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--out":
        with open(sys.argv[2], "w") as f:
            sys.stdout = f
            main()
        sys.stdout = sys.__stdout__
        print(f"wrote {sys.argv[2]}")
    else:
        main()
