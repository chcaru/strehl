"""M15 analysis -- does the focus-measure window optimum survive the merge regulariser?

Reads only files under `experiments/m15-regulariser-window/data`, plus, for Gate A
only, M13's committed `experiments/m13-window-depth/data/edge-*.csv`.

Written independently of `m13_analyse.py`: the regret rule is re-implemented from
the specification in PREREGISTRATION.md section 3 rather than copied, because a
reproduction that shares the analysis code with the thing it reproduces is not a
reproduction. Every table names the stratum it filtered on.

Aggregation rule, used everywhere and stated once:

    cell            = (stack, shape, step)
    E(w, cell, g)   = mean over SEEDS of `excess_dn`, rows filtered to width == g
    regret(w,.,g)   = E(w, cell, g) - min_w' E(w', cell, g)
    meanregret(w,g) = mean of regret over the 30 cells with step > 0
    worstregret(w,g)= max of regret over the same 30 cells
    w*(g)           = argmin_w meanregret(w, g), labelled interior / ENDPOINT

Zero-step cells are the NULL and never enter a decision.
"""

import argparse
import csv
import math
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
M13_DATA = os.path.join(HERE, "..", "m13-window-depth", "data")

STACKS = ("109MSDCF", "119MSDCF")
M13_SEEDS = (20260823, 771117, 4242424)
M13_LADDER = [0, 1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15, 17, 18, 20, 23, 26, 33, 40]

# Gate A targets, quoted from M13-window-depth-measured.md section 3.1 / 3.2 and
# SYNTHESIS fact 60. These are the numbers that must come back before anything
# else in this file is allowed to mean anything.
GATE_A = {
    "step_gt0_argmin": 13,
    "step_gt0_mean": 3.171,
    "step_gt0_worst": 12.111,
    "step_eq0_argmin": 40,
    "step_eq0_mean": 0.000,
}

# Registered thresholds (PREREGISTRATION.md section 5), fixed from M13's own
# published numbers before any M15 result was read.
THRESH_PRIMARY = 0.87      # M13's published w11-w15 basin flatness (w13->w15 gap)
THRESH_SENSITIVITY = 0.29  # M13's w12->w13 gap
THRESH_WORST = 12.111      # M13's published worst-case regret at w13, width 1
M13_SEED_SD = 0.193        # M13's published median seed-to-seed sd of E_excess


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def shape_of(row):
    """`vertical@298` / `bar@298w24` -> `vertical` / `bar`.

    The harness embeds the boundary's tile coordinate in the shape string, and
    that coordinate moves with the tile margin, which moves with the widest
    regulariser in the invocation. Normalising is what makes an M13 run and an
    M15 run comparable at all.
    """
    return row["shape"].split("@")[0]


# The harness writes the DERIVED seed, `base * 1000003 + step (mod 2^64)`, not the
# base seed handed to `--seed`. Invert it by construction rather than by parsing.
ALL_SEEDS = (20260823, 771117, 4242424, 13371337, 90210)
_MASK = (1 << 64) - 1
DERIVED_TO_BASE = {
    (base * 1_000_003 + step) & _MASK: base
    for base in ALL_SEEDS
    for step in (0, 2, 4, 8, 16, 32)
}


def base_seed(row):
    return DERIVED_TO_BASE.get(int(row["seed"]))


def load_edge(files):
    """-> {width: {cell: {window: [excess rows]}}} keyed by seed-preserving lists."""
    out = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for f in files:
        for r in read_csv(f):
            g = int(r["width"])
            cell = (r["stack"], shape_of(r), int(r["step"]))
            out[g][cell][int(r["window"])].append(r)
    return out


def cell_values(bywidth, g, field, seeds=None, reduce_fn=None):
    """{cell: {window: seed-averaged value}} at regulariser width g."""
    out = {}
    for cell, wins in bywidth[g].items():
        d = {}
        for w, rows in wins.items():
            rs = rows if seeds is None else [r for r in rows if base_seed(r) in seeds]
            if not rs:
                continue
            if reduce_fn:
                d[w] = sum(reduce_fn(r) for r in rs) / len(rs)
            else:
                d[w] = sum(float(r[field]) for r in rs) / len(rs)
        if d:
            out[cell] = d
    return out


def regret_table(cells, ladder):
    """-> [(w, mean regret, worst regret, worst cell)] over the given cells."""
    rank = []
    for w in ladder:
        regs = []
        for cell, d in cells.items():
            if w not in d:
                continue
            regs.append((d[w] - min(d.values()), cell))
        if not regs:
            continue
        mean = sum(x[0] for x in regs) / len(regs)
        worst = max(regs, key=lambda x: x[0])
        rank.append((w, mean, worst[0], worst[1]))
    return rank


def label(w, ladder):
    return "ENDPOINT" if w in (ladder[0], ladder[-1]) else "interior"


def argmins(rank, ladder):
    bm = min(rank, key=lambda t: t[1])
    bw = min(rank, key=lambda t: t[2])
    return (bm[0], bm[1], label(bm[0], ladder)), (bw[0], bw[2], label(bw[0], ladder))


def sec(t):
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def med(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return float("nan")
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def sd(xs):
    n = len(xs)
    if n < 2:
        return float("nan")
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def ols(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return float("nan"), float("nan")
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return b, my - b * mx


# --------------------------------------------------------------- Gate A


def gate_a():
    sec("GATE A -- reproduce M13 at regulariser width 1 before extending it")
    print("SYNTHESIS section 5 item 15. If this fails, nothing below is valid.")
    print()

    arms = (
        ("M13's own committed CSVs",
         [os.path.join(M13_DATA, f"edge-{s}.csv") for s in STACKS]),
        ("M15's replication run (repro-edge-*.csv)",
         [os.path.join(DATA, f"repro-edge-{s}.csv") for s in STACKS]),
    )
    ok_all = True
    for name, files in arms:
        if not all(os.path.exists(f) for f in files):
            print(f"  {name}: MISSING -- skipped")
            continue
        bw = load_edge(files)
        if 1 not in bw:
            print(f"  {name}: no width==1 rows")
            ok_all = False
            continue
        ladder = sorted({w for c in bw[1].values() for w in c})
        cells = cell_values(bw, 1, "excess_dn")
        gt0 = {k: v for k, v in cells.items() if k[2] > 0}
        eq0 = {k: v for k, v in cells.items() if k[2] == 0}
        rm, rw = argmins(regret_table(gt0, ladder), ladder)
        zm, _ = argmins(regret_table(eq0, ladder), ladder)
        print(f"  {name}")
        print(f"    ladder            : {len(ladder)} windows, w{ladder[0]}..w{ladder[-1]}")
        print(f"    cells step>0 / =0 : {len(gt0)} / {len(eq0)}")
        print(f"    argmin mean regret (step>0)  : w{rm[0]} {rm[1]:.3f} DN  [{rm[2]}]"
              f"   target w{GATE_A['step_gt0_argmin']} {GATE_A['step_gt0_mean']:.3f}")
        print(f"    argmin worst regret (step>0) : w{rw[0]} {rw[1]:.3f} DN  [{rw[2]}]"
              f"   target w{GATE_A['step_gt0_argmin']} {GATE_A['step_gt0_worst']:.3f}")
        print(f"    argmin mean regret (step=0)  : w{zm[0]} {zm[1]:.3f} DN  [{zm[2]}]"
              f"   target w{GATE_A['step_eq0_argmin']} ENDPOINT {GATE_A['step_eq0_mean']:.3f}")
        ok = (rm[0] == GATE_A["step_gt0_argmin"]
              and abs(rm[1] - GATE_A["step_gt0_mean"]) < 5e-4
              and rw[0] == GATE_A["step_gt0_argmin"]
              and abs(rw[1] - GATE_A["step_gt0_worst"]) < 5e-4
              and zm[0] == GATE_A["step_eq0_argmin"] and zm[2] == "ENDPOINT"
              and abs(zm[1] - GATE_A["step_eq0_mean"]) < 5e-4)
        print(f"    ==> {'PASS' if ok else 'FAIL'}")
        ok_all = ok_all and ok
    print()
    print("  stratum: width == 1; cell = (stack, shape-without-coordinate, step);")
    print("  value   = mean of excess_dn over the 3 seeds; regret vs the per-cell min.")
    return ok_all


def gate_a_byte_identity():
    sec("GATE A1 -- is the replication byte-identical to M13's committed CSV?")
    import hashlib
    for s in STACKS:
        a = os.path.join(M13_DATA, f"edge-{s}.csv")
        b = os.path.join(DATA, f"repro-edge-{s}.csv")
        if not (os.path.exists(a) and os.path.exists(b)):
            print(f"  {s}: missing")
            continue
        ha = hashlib.sha256(open(a, "rb").read()).hexdigest()
        hb = hashlib.sha256(open(b, "rb").read()).hexdigest()
        # Line-ending normalised comparison as well: the replication is written
        # by PowerShell Set-Content, which is CRLF on this box.
        la = open(a, newline=None).read().splitlines()
        lb = open(b, newline=None).read().splitlines()
        same_lines = la == lb
        ndiff = sum(1 for x, y in zip(la, lb) if x != y) + abs(len(la) - len(lb))
        print(f"  {s}: sha256 M13 {ha[:16]}  M15 {hb[:16]}  "
              f"raw-identical={ha == hb}  line-identical={same_lines}  differing lines={ndiff}")


# --------------------------------------------------------------- the surface


def surface(seeds=None, ladder_filter=None, tag=""):
    sec(f"1. THE SURFACE -- argmin over windows at each regulariser width{tag}")
    files = [os.path.join(DATA, f"edge-{s}.csv") for s in STACKS]
    bw = load_edge(files)
    widths = sorted(bw)
    if not widths:
        print("  no data")
        return None
    out = {}
    for name, keep, is_decision, expect in (
            ("cells WITH a depth step (step > 0) -- THE DECISION",
             lambda k: k[2] > 0, True, None),
            ("NULL: step == 0 cells (no discontinuity)",
             lambda k: k[2] == 0, False, "ENDPOINT")):
        print()
        print("-" * 78)
        print(f"  {name}")
        print("-" * 78)
        print(f"  {'width':>6} {'radius':>7} {'cells':>6} {'w*(mean)':>9} {'label':>9} "
              f"{'meanreg':>9} {'w*(worst)':>10} {'label':>9} {'worstreg':>9} "
              f"{'reg@w13':>9} {'Delta13':>9}")
        for g in widths:
            cells = cell_values(bw, g, "excess_dn", seeds=seeds)
            cells = {k: v for k, v in cells.items() if keep(k)}
            if not cells:
                continue
            ladder = sorted({w for d in cells.values() for w in d})
            if ladder_filter:
                ladder = [w for w in ladder if w in ladder_filter]
                cells = {k: {w: v for w, v in d.items() if w in ladder}
                         for k, d in cells.items()}
            rank = regret_table(cells, ladder)
            rm, rw = argmins(rank, ladder)
            r13 = next((t for t in rank if t[0] == 13), None)
            d13 = (r13[1] - rm[1]) if r13 else float("nan")
            print(f"  {g:>6} {(g - 1) // 2:>7} {len(cells):>6} {rm[0]:>9} {rm[2]:>9} "
                  f"{rm[1]:>9.3f} {rw[0]:>10} {rw[2]:>9} {rw[1]:>9.3f} "
                  f"{(r13[1] if r13 else float('nan')):>9.3f} {d13:>9.3f}")
            if is_decision:
                out[g] = dict(wstar=rm[0], lab=rm[2], mean=rm[1],
                              wstar_worst=rw[0], lab_worst=rw[2], worst=rw[1],
                              reg13=r13[1] if r13 else float("nan"),
                              worst13=r13[2] if r13 else float("nan"),
                              delta13=d13, rank=rank, ladder=ladder)
        if expect == "ENDPOINT":
            print("    registered null: every zero-step argmin must be an ENDPOINT (fact 61).")
    print()
    print("  stratum: rows filtered to `width == g`; cell = (stack, shape, step);")
    print("  value = mean of excess_dn over seeds; regret vs the per-cell min AT THAT g.")
    print("  Delta13 = meanregret(w13, g) - meanregret(w*(g), g): the DN penalty the")
    print("  project pays by shipping M13's w13 at that regulariser width.")
    return out


def full_ladder_dump():
    sec("2. THE WHOLE SURFACE -- mean regret (DN) for every (window, regulariser width)")
    print("stratum: 30 cells with step > 0, all seeds, E_excess.")
    files = [os.path.join(DATA, f"edge-{s}.csv") for s in STACKS]
    bw = load_edge(files)
    widths = sorted(bw)
    tab = {}
    ladder = None
    for g in widths:
        cells = {k: v for k, v in cell_values(bw, g, "excess_dn").items() if k[2] > 0}
        ladder = sorted({w for d in cells.values() for w in d})
        for w, m, _, _ in regret_table(cells, ladder):
            tab[(w, g)] = m
    print()
    print("   w  | " + " ".join(f"{('g=' + str(g)):>8}" for g in widths))
    print("  ----+" + "-" * (9 * len(widths)))
    for w in ladder:
        row = " ".join(f"{tab.get((w, g), float('nan')):>8.2f}" for g in widths)
        print(f"  {w:>3} | {row}")
    print()
    print("  Each column is an independent regret table: the per-cell minimum is taken")
    print("  within that column, so columns are NOT comparable to each other in level.")
    return tab, widths, ladder


def joint_surface():
    sec("3. JOINT (window, regulariser) regret -- the pair the project would ship")
    print("stratum: 30 cells with step > 0, all seeds. Per cell the minimum is taken")
    print("over ALL (w, g) pairs at once, so this table IS comparable in level.")
    files = [os.path.join(DATA, f"edge-{s}.csv") for s in STACKS]
    bw = load_edge(files)
    widths = sorted(bw)
    joint = defaultdict(dict)
    for g in widths:
        for cell, d in cell_values(bw, g, "excess_dn").items():
            if cell[2] <= 0:
                continue
            for w, v in d.items():
                joint[cell][(w, g)] = v
    rank = []
    keys = sorted({k for d in joint.values() for k in d})
    for k in keys:
        regs = [(d[k] - min(d.values()), cell) for cell, d in joint.items() if k in d]
        if not regs:
            continue
        rank.append((k, sum(x[0] for x in regs) / len(regs),
                     max(regs, key=lambda x: x[0])[0]))
    rank.sort(key=lambda t: t[1])
    print()
    print(f"  {'rank':>4} {'window':>7} {'width':>6} {'mean regret':>12} {'worst regret':>13}")
    for i, (k, m, wst) in enumerate(rank[:20], 1):
        print(f"  {i:>4} {k[0]:>7} {k[1]:>6} {m:>12.3f} {wst:>13.3f}")
    print("  ...")
    for i, (k, m, wst) in enumerate(rank[-3:], len(rank) - 2):
        print(f"  {i:>4} {k[0]:>7} {k[1]:>6} {m:>12.3f} {wst:>13.3f}")
    print()
    best_by_g = {}
    for (w, g), m, wst in rank:
        if g not in best_by_g or m < best_by_g[g][1]:
            best_by_g[g] = ((w, g), m, wst)
    print(f"  best window at each regulariser width, on the JOINT scale:")
    print(f"  {'width':>6} {'best w':>7} {'mean regret':>12} {'w13 mean regret':>16} {'penalty':>9}")
    for g in widths:
        k, m, _ = best_by_g[g]
        m13 = next((x[1] for x in rank if x[0] == (13, g)), float("nan"))
        print(f"  {g:>6} {k[0]:>7} {m:>12.3f} {m13:>16.3f} {m13 - m:>9.3f}")
    return rank


def substitution_rate(surf):
    sec("4. SUBSTITUTION RATE -- do the window and the regulariser trade off 1:1?")
    if not surf:
        return
    print("H_sub  (perfect substitution): w*(g) = w*(1) - (g-1)/2, slope s = 1")
    print("H_none (no substitution)     : w*(g) = w*(1),           slope s = 0")
    print()
    gs = sorted(surf)
    rs = [(g - 1) / 2 for g in gs]
    ws = [surf[g]["wstar"] for g in gs]
    b, a = ols(rs, ws)
    print(f"  OLS of w*(g) on regulariser radius r over all {len(gs)} widths:")
    print(f"    w* = {a:.3f} + {b:.4f} * r     =>  substitution rate s = {-b:.4f}")
    if 17 in surf and 1 in surf:
        s17 = (surf[1]["wstar"] - surf[17]["wstar"]) / 8.0
        print(f"  endpoint contrast (g=1 vs g=17, r=0 vs r=8): "
              f"s = ({surf[1]['wstar']} - {surf[17]['wstar']}) / 8 = {s17:.4f}")
    print()
    print(f"  {'width':>6} {'radius r':>9} {'w*(g)':>7} {'H_sub predicts':>15} {'residual':>9}")
    for g in gs:
        pred = max(0, surf[1]["wstar"] - (g - 1) // 2)
        print(f"  {g:>6} {(g - 1) // 2:>9} {surf[g]['wstar']:>7} {pred:>15} "
              f"{surf[g]['wstar'] - pred:>9}")


def decision(surf):
    sec("5. DECISION -- the registered rule, applied")
    if not surf:
        return
    print(f"  registered primary   : Delta(g) <= {THRESH_PRIMARY} DN  "
          f"(M13's own published w11-w15 basin flatness)")
    print(f"  registered sensitivity: Delta(g) <= {THRESH_SENSITIVITY} DN "
          f"(M13's w12->w13 gap)")
    print(f"  registered worst-case : worstregret(w13, g) <= {THRESH_WORST} DN "
          f"(M13's published worst case at w13)")
    print()
    print(f"  {'width':>6} {'w*(g)':>6} {'Delta13':>9} {'primary':>9} {'sens':>7} "
          f"{'worst@w13':>10} {'worst gate':>11}")
    for g in sorted(surf):
        d = surf[g]["delta13"]
        w13w = surf[g]["worst13"]
        print(f"  {g:>6} {surf[g]['wstar']:>6} {d:>9.3f} "
              f"{('PASS' if d <= THRESH_PRIMARY else 'FAIL'):>9} "
              f"{('PASS' if d <= THRESH_SENSITIVITY else 'FAIL'):>7} "
              f"{w13w:>10.3f} {('PASS' if w13w <= THRESH_WORST else 'FAIL'):>11}")
    print()
    if 17 in surf:
        d = surf[17]["delta13"]
        print(f"  HEADLINE at the project's reference regulariser width 17: "
              f"Delta = {d:.3f} DN -> "
              f"{'w13 SURVIVES' if d <= THRESH_PRIMARY else 'w13 DOES NOT SURVIVE'}")
    fails = [g for g in sorted(surf) if surf[g]["delta13"] > THRESH_PRIMARY]
    print(f"  widths at which w13 fails the primary threshold: "
          f"{fails if fails else 'none'}")


def basin(surf):
    sec("6. THE BASIN at each regulariser width -- how flat, and how wide")
    if not surf:
        return
    for g in sorted(surf):
        rank = surf[g]["rank"]
        best = min(t[1] for t in rank)
        inbasin = [t[0] for t in rank if t[1] - best <= THRESH_PRIMARY]
        print(f"  g={g:>3}  w*={surf[g]['wstar']:>3}  "
              f"windows within {THRESH_PRIMARY} DN of the best: "
              f"{'w' + str(min(inbasin))}..{'w' + str(max(inbasin))}  "
              f"({len(inbasin)} of {len(rank)})  members {inbasin}")


def seed_floor():
    sec("7. THE SEED NOISE FLOOR -- measured, not assumed")
    files = [os.path.join(DATA, f"edge-{s}.csv") for s in STACKS]
    bw = load_edge(files)
    for g in sorted(bw):
        sds, n, nseed = [], 0, 0
        for cell, wins in bw[g].items():
            if cell[2] <= 0:
                continue
            for w, rows in wins.items():
                xs = [float(r["excess_dn"]) for r in rows]
                nseed = max(nseed, len(xs))
                if len(xs) > 1:
                    sds.append(sd(xs))
                    n += 1
        print(f"  g={g:>3}  median seed-to-seed sd of E_excess = {med(sds):>6.3f} DN  "
              f"(over {n} (cell, window) groups, {nseed} seeds each)")
    print(f"  M13 published, at g=1 with 3 seeds: {M13_SEED_SD} DN")
    print()
    print("  standard error of a 30-cell mean regret, from the measured sd:")
    for g in (1, 17):
        if g not in bw:
            continue
        sds = [sd([float(r["excess_dn"]) for r in rows])
               for cell, wins in bw[g].items() if cell[2] > 0
               for w, rows in wins.items() if len(rows) > 1]
        nseed = max(len(rows) for wins in bw[g].values() for rows in wins.values())
        s = med(sds)
        print(f"    g={g:>3}: sd {s:.3f} / sqrt({nseed} seeds) / sqrt(30 cells) = "
              f"{s / math.sqrt(nseed) / math.sqrt(30):.4f} DN")


def placebo():
    sec("8. GATE D -- placebo: how far does w* move when NOTHING changes?")
    print("Disjoint seed halves at a FIXED regulariser width. Any shift here is")
    print("the null distribution of the treatment shift.")
    files = [os.path.join(DATA, f"edge-{s}.csv") for s in STACKS]
    bw = load_edge(files)
    halves = ({20260823, 771117}, {4242424, 13371337, 90210})
    print()
    print(f"  {'width':>6} {'w* half A':>10} {'w* half B':>10} {'|shift|':>8} "
          f"{'w* all':>7} {'per-seed w*':>28}")
    shifts = []
    for g in sorted(bw):
        ws = []
        for h in halves:
            cells = {k: v for k, v in cell_values(bw, g, "excess_dn", seeds=h).items()
                     if k[2] > 0}
            ladder = sorted({w for d in cells.values() for w in d})
            rm, _ = argmins(regret_table(cells, ladder), ladder)
            ws.append(rm[0])
        cells = {k: v for k, v in cell_values(bw, g, "excess_dn").items() if k[2] > 0}
        ladder = sorted({w for d in cells.values() for w in d})
        rall, _ = argmins(regret_table(cells, ladder), ladder)
        per = []
        for sd_ in sorted({base_seed(r) for wins in bw[g].values()
                           for rows in wins.values() for r in rows}):
            c1 = {k: v for k, v in cell_values(bw, g, "excess_dn", seeds={sd_}).items()
                  if k[2] > 0}
            l1 = sorted({w for d in c1.values() for w in d})
            r1, _ = argmins(regret_table(c1, l1), l1)
            per.append(r1[0])
        shifts.append(abs(ws[0] - ws[1]))
        print(f"  {g:>6} {ws[0]:>10} {ws[1]:>10} {abs(ws[0] - ws[1]):>8} "
              f"{rall[0]:>7}   {str(per):>26}")
    print()
    print(f"  placebo shift (disjoint seed halves, same width): "
          f"max {max(shifts)} window steps, median {med(shifts)}")


def secondary():
    sec("9. SECONDARY OBJECTIVES -- does the ruling depend on which metric I picked?")
    files = [os.path.join(DATA, f"edge-{s}.csv") for s in STACKS]
    bw = load_edge(files)
    objs = (
        ("E_excess (DN over the floor)", "excess_dn", None),
        ("max mis-selection width (px)", None,
         lambda r: max(float(r["mis_bg"]), float(r["mis_fg"]))),
        ("dmae in the band (frames)", "dmae_band", None),
        ("far_rms (DN, DISJOINT pixel set from the band)", "far_rms", None),
    )
    for name, field, fn in objs:
        print()
        print(f"  objective: {name}")
        print(f"  {'width':>6} {'w* step>0':>10} {'label':>9} {'w* step=0':>10} {'label':>9}")
        for g in sorted(bw):
            cells = cell_values(bw, g, field, reduce_fn=fn)
            gt0 = {k: v for k, v in cells.items() if k[2] > 0}
            eq0 = {k: v for k, v in cells.items() if k[2] == 0}
            ladder = sorted({w for d in cells.values() for w in d})
            rm, _ = argmins(regret_table(gt0, ladder), ladder)
            zm, _ = argmins(regret_table(eq0, ladder), ladder)
            print(f"  {g:>6} {rm[0]:>10} {rm[2]:>9} {zm[0]:>10} {zm[2]:>9}")
    print()
    print("  NOTE: `acc` and `acc_band` are NESTED sets and are never quoted as")
    print("  agreeing (M13 section 2.5 item 5). `far_rms` and `band_rms` are disjoint,")
    print("  so far_rms may be compared with the band objective.")


def blind_spot():
    sec("10. GATE C -- W_bleed's blind spot, asserted on real M15 data")
    print("M13 section 2.5 item 1: W_bleed cannot see a selector that elects a")
    print("COMPROMISE frame between two layers. Registered as a control, not a caveat")
    print("(SYNTHESIS section 5 item 26). Here it is searched for in M15's own rows.")
    files = [os.path.join(DATA, f"edge-{s}.csv") for s in STACKS]
    bw = load_edge(files)
    hits = []
    for g in sorted(bw):
        for cell, wins in bw[g].items():
            if cell[2] <= 0:
                continue
            ws = sorted(wins)
            vals = {w: (sum(float(r["bleed_fg"]) for r in wins[w]) / len(wins[w]),
                        sum(float(r["excess_dn"]) for r in wins[w]) / len(wins[w]))
                    for w in ws}
            for i in range(len(ws)):
                for j in range(i + 1, len(ws)):
                    a, b = vals[ws[i]], vals[ws[j]]
                    if a[0] - b[0] > 5.0 and b[1] - a[1] > 2.0:
                        hits.append((g, cell, ws[i], ws[j], a, b))
    hits.sort(key=lambda h: -(h[4][0] - h[5][0]))
    print()
    print(f"  found {len(hits)} (width, cell, w_narrow, w_wide) pairs where bleed_fg")
    print(f"  COLLAPSES while E_excess RISES. Top 8 by bleed collapse:")
    print(f"  {'width':>6} {'cell':>34} {'w_a':>4} {'w_b':>4} "
          f"{'bleed_a':>8} {'bleed_b':>8} {'exc_a':>8} {'exc_b':>8}")
    for g, cell, wa, wbb, a, b in hits[:8]:
        c = f"{cell[0]}/{cell[1]}/s{cell[2]}"
        print(f"  {g:>6} {c:>34} {wa:>4} {wbb:>4} {a[0]:>8.2f} {b[0]:>8.2f} "
              f"{a[1]:>8.2f} {b[1]:>8.2f}")
    print()
    print("  rule: bleed_fg drop > 5 px AND excess_dn rise > 2 DN, seed-averaged.")
    print("  Reading W_bleed alone would call the wider window nearly halo-free.")
    print("  Only the oracle-referenced E_excess sees through it.")


def noise_ladder():
    sec("11. GATE B2 -- the regulariser IS switched on: N vs regulariser width")
    for stk in STACKS:
        rr = read_csv(os.path.join(DATA, f"noise-{stk}.csv"))
        if not rr:
            continue
        print()
        print(f"  {stk}  (stratum: roi_kind == flat, select_on == luma; "
              f"median over the 4 committed ROIs)")
        by = defaultdict(lambda: defaultdict(list))
        for r in rr:
            if r["roi_kind"] != "flat" or r["select_on"] != "luma":
                continue
            by[r["measure"]][int(r["width"])].append(float(r["ratio"]))
        widths = sorted({w for m in by.values() for w in m})
        print("    measure          " + " ".join(f"{('g=' + str(g)):>8}" for g in widths))
        for m in sorted(by):
            print(f"    {m:<16} " + " ".join(f"{med(by[m][g]):>8.4f}" for g in widths))
        sig = med([float(r["single_sigma"]) for r in rr if r["roi_kind"] == "flat"])
        print(f"    median single_sigma over these ROIs = {sig:.2f} DN "
              f"(flat ROI discriminator: 28-30 DN)")


def per_cell(surf):
    sec("12. PER-CELL argmin at g=1 and g=17 -- is the shift uniform or cell-driven?")
    files = [os.path.join(DATA, f"edge-{s}.csv") for s in STACKS]
    bw = load_edge(files)
    if 1 not in bw or 17 not in bw:
        return
    c1 = {k: v for k, v in cell_values(bw, 1, "excess_dn").items() if k[2] > 0}
    c17 = {k: v for k, v in cell_values(bw, 17, "excess_dn").items() if k[2] > 0}
    print(f"  {'cell':>34} {'w* g=1':>7} {'w* g=17':>8} {'shift':>6} "
          f"{'E@min g=1':>10} {'E@min g=17':>11}")
    shifts = []
    for cell in sorted(c1):
        a = min(c1[cell], key=lambda w: c1[cell][w])
        b = min(c17[cell], key=lambda w: c17[cell][w])
        shifts.append(b - a)
        print(f"  {cell[0] + '/' + cell[1] + '/s' + str(cell[2]):>34} {a:>7} {b:>8} "
              f"{b - a:>6} {c1[cell][a]:>10.2f} {c17[cell][b]:>11.2f}")
    print(f"  median per-cell shift w*(17) - w*(1) = {med(shifts)}, "
          f"mean {sum(shifts) / len(shifts):.2f}, "
          f"narrower in {sum(1 for s in shifts if s < 0)}/{len(shifts)}, "
          f"wider in {sum(1 for s in shifts if s > 0)}, "
          f"unchanged in {sum(1 for s in shifts if s == 0)}")


def w13_vs_w14():
    sec("13. w13 vs w14 and w16 -- the windows M13's ladder could not see")
    files = [os.path.join(DATA, f"edge-{s}.csv") for s in STACKS]
    bw = load_edge(files)
    print(f"  {'width':>6} " + " ".join(f"{('w' + str(w)):>8}" for w in
                                        (11, 12, 13, 14, 15, 16, 17)))
    for g in sorted(bw):
        cells = {k: v for k, v in cell_values(bw, g, "excess_dn").items() if k[2] > 0}
        ladder = sorted({w for d in cells.values() for w in d})
        rank = {t[0]: t[1] for t in regret_table(cells, ladder)}
        print(f"  {g:>6} " + " ".join(f"{rank.get(w, float('nan')):>8.3f}"
                                      for w in (11, 12, 13, 14, 15, 16, 17)))
    print("  mean regret (DN), 30 step>0 cells, all seeds.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    args = ap.parse_args()
    stream = open(args.out, "w") if args.out else None
    old = sys.stdout
    if stream:
        sys.stdout = _Tee(old, stream)
    try:
        print("M15 -- regulariser vs focus window. Analysis of committed CSVs only.")
        ok = gate_a()
        gate_a_byte_identity()
        if not ok:
            print("\n*** GATE A FAILED -- everything below is reported but NOT valid "
                  "as a comparison with M13. ***")
        surf = surface()
        surface(seeds=set(M13_SEEDS), tag="  [M13's 3 seeds only]")
        surface(ladder_filter=set(M13_LADDER), tag="  [M13's 20-window ladder only]")
        full_ladder_dump()
        joint_surface()
        substitution_rate(surf)
        decision(surf)
        basin(surf)
        w13_vs_w14()
        per_cell(surf)
        seed_floor()
        placebo()
        secondary()
        blind_spot()
        noise_ladder()
    finally:
        sys.stdout = old
        if stream:
            stream.close()


class _Tee:
    def __init__(self, *ss):
        self.ss = ss

    def write(self, d):
        for s in self.ss:
            s.write(d)

    def flush(self):
        for s in self.ss:
            s.flush()


if __name__ == "__main__":
    main()
