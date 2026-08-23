"""M9 analysis: does the noise-optimal merge regulariser width track the focus
measure's spatial support?

Reads the sweep CSVs produced by `m9-support sweep` and computes exactly the
statistics named in PREREGISTRATION.md, in the order that document names them:
controls first, then the treatments, then the decision statistic.

Usage:
    python m9_analyse.py data/sweep-109MSDCF-coupled.csv [more.csv ...]
"""

from __future__ import annotations

import sys
from collections import defaultdict
import csv
import math

TOL = 0.10          # S1: fraction of the improvement left unrealised at the knee
DETAIL_TOL = 0.05   # S4: fraction of peak gradient a usable width may give up
FLOOR_T = 0.02      # S3/S4 severity floor, in ratio units


def load(paths):
    rows = []
    for p in paths:
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                for k in ("support_radius", "support_px", "declared_radius",
                          "declared_px", "width", "radius", "frames",
                          "distinct_winners"):
                    r[k] = int(r[k])
                for k in ("ratio", "stacked_sigma", "single_sigma", "stacked_mean",
                          "speckle", "grad_stacked", "grad_single"):
                    r[k] = float(r[k])
                rows.append(r)
    return rows


def curve(rows, stack, roi, measure, field="ratio"):
    sel = [r for r in rows if r["stack"] == stack and r["roi"] == roi and r["measure"] == measure]
    sel.sort(key=lambda r: r["width"])
    return [r["width"] for r in sel], [r[field] for r in sel]


def knee(widths, values, tol=TOL):
    """S1. Smallest swept width realising 1-tol of the improvement achieved."""
    top = values[0]
    floor = min(values)
    if top <= floor:
        return widths[0]
    target = floor + tol * (top - floor)
    for w, v in zip(widths, values):
        if v <= target:
            return w
    return widths[-1]


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return num / (dx * dy) if dx > 0 and dy > 0 else float("nan")


def perm_p(xs, ys, rho, trials=200000, seed=20260822):
    """Exact-ish two-sided permutation p for Spearman on a small sample."""
    import random
    rnd = random.Random(seed)
    ys = list(ys)
    hits = 0
    for _ in range(trials):
        rnd.shuffle(ys)
        if abs(spearman(xs, ys)) >= abs(rho) - 1e-12:
            hits += 1
    return (hits + 1) / (trials + 1)


def slope(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else float("nan")


def section(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def main(paths):
    rows = load(paths)
    stacks = sorted({r["stack"] for r in rows})
    widths = sorted({r["width"] for r in rows})

    for stack in stacks:
        srows = [r for r in rows if r["stack"] == stack]
        modes = sorted({(r["select_on"], r["evaluate_on"]) for r in srows})
        flat = sorted({r["roi"] for r in srows if r["roi_kind"] == "flat"})
        detail = sorted({r["roi"] for r in srows if r["roi_kind"] == "detail"})
        frames = srows[0]["frames"]
        meta = {r["measure"]: r for r in srows}

        treat = sorted({r["measure"] for r in srows if r["role"] == "treatment"})
        nulls = sorted({r["measure"] for r in srows if r["role"] == "null"},
                       key=lambda m: meta[m]["declared_radius"])
        posit = sorted({r["measure"] for r in srows if r["role"] == "positive"},
                       key=lambda m: meta[m]["support_radius"])

        section(f"STACK {stack} -- {frames} frames, widths {widths}")
        print(f"flat ROIs   : {flat}")
        print(f"detail ROIs : {detail}")
        print(f"modes       : {modes}")

        for mode in modes:
            mrows = [r for r in srows if (r["select_on"], r["evaluate_on"]) == mode]
            tag = "COUPLED (select on luma, evaluate on luma)" if mode == ("luma", "luma") \
                else f"PLACEBO (select on {mode[0]}, evaluate on {mode[1]})"
            section(f"{stack} :: {tag}")

            # ---- reproducibility yardstick s_roi (PREREG section 4) -------------
            fixed = []
            for roi in flat:
                w, c = curve(mrows, stack, roi, "ring-1-3")
                fixed.append(c[w.index(17)])
            n = len(fixed)
            mean_f = sum(fixed) / n
            s_roi = math.sqrt(sum((v - mean_f) ** 2 for v in fixed) / (n - 1)) if n > 1 else float("nan")
            T = max(FLOOR_T, 3.0 * s_roi)
            print(f"s_roi: ring-1-3 at width 17 over {n} flat ROIs = "
                  f"{['%.4f' % v for v in fixed]}, sd {s_roi:.4f}")
            print(f"severity threshold T = max(0.02, 3*s_roi) = {T:.4f} ratio units")

            # ---- per-measure knee, per ROI and pooled ---------------------------
            def knees_for(measures):
                out = {}
                for m in measures:
                    per = []
                    for roi in flat:
                        w, c = curve(mrows, stack, roi, m)
                        per.append(knee(w, c))
                    pooled_w, pooled_c = None, None
                    for roi in flat:
                        w, c = curve(mrows, stack, roi, m)
                        pooled_w = w
                        pooled_c = c if pooled_c is None else [a + b for a, b in zip(pooled_c, c)]
                    pooled_c = [v / len(flat) for v in pooled_c]
                    out[m] = (per, sorted(per)[len(per) // 2], knee(pooled_w, pooled_c),
                              pooled_w, pooled_c)
                return out

            k_null = knees_for(nulls)
            k_pos = knees_for(posit)
            k_tr = knees_for(treat)

            # ---- CONTROLS FIRST -------------------------------------------------
            print()
            print("-- NULL CONTROL: declared support varies, operator identical --")
            print(f"{'measure':<14} {'declared_px':>11} {'real_px':>8} {'W90 per ROI':>24} {'W90 pooled':>11}")
            for m in nulls:
                per, med, pooled, _, _ = k_null[m]
                print(f"{m:<14} {meta[m]['declared_px']:>11} {meta[m]['support_px']:>8} "
                      f"{str(per):>24} {pooled:>11}")
            uniq = {k_null[m][2] for m in nulls}
            print(f"NULL VERDICT: pooled W90 takes {len(uniq)} distinct value(s) {sorted(uniq)} "
                  f"across {len(nulls)} declarations -- "
                  f"{'PASS, statistic ignores the declaration' if len(uniq) == 1 else 'FAIL'}")

            print()
            print("-- POSITIVE CONTROL: support genuinely varies, family fixed --")
            print(f"{'measure':<14} {'support_px':>10} {'W90 per ROI':>24} {'W90 pooled':>11} {'floor':>8} {'top':>8}")
            for m in posit:
                per, med, pooled, pw, pc = k_pos[m]
                print(f"{m:<14} {meta[m]['support_px']:>10} {str(per):>24} {pooled:>11} "
                      f"{min(pc):>8.4f} {pc[0]:>8.4f}")
            pv = [k_pos[m][2] for m in posit]
            px = [meta[m]["support_radius"] for m in posit]
            rho_pos = spearman(px, pv)
            print(f"POSITIVE VERDICT: pooled W90 spans {min(pv)}..{max(pv)} "
                  f"({max(pv) / max(min(pv), 1):.1f}x), Spearman rho vs support = {rho_pos:+.3f} -- "
                  f"{'PASS, the statistic can detect support-driven movement' if min(pv) != max(pv) else 'FAIL, statistic is blind'}")

            # ---- TREATMENTS -----------------------------------------------------
            print()
            print("-- TREATMENTS: 4 families x 4 support radii --")
            print(f"{'measure':<14} {'family':<10} {'sup_px':>6} {'W90 per ROI':>24} {'W90':>5} "
                  f"{'argmin':>7} {'interior':>8} {'floor':>7} {'top':>7} {'Wharm':>6}")
            tw, ts = [], []
            floors, tops, harms = {}, {}, {}
            pooled_curves = {}
            for m in treat:
                per, med, pooled, pw, pc = k_tr[m]
                am = pw[pc.index(min(pc))]
                interior = 0 < pw.index(am) < len(pw) - 1
                harm = 0
                for w, v in zip(pw, pc):
                    if v > pc[0]:
                        harm = w
                harms[m] = harm
                floors[m] = min(pc)
                tops[m] = pc[0]
                pooled_curves[m] = (pw, pc)
                tw.append(pooled)
                ts.append(meta[m]["support_radius"])
                print(f"{m:<14} {meta[m]['family']:<10} {meta[m]['support_px']:>6} {str(per):>24} "
                      f"{pooled:>5} {am:>7} {str(interior):>8} {min(pc):>7.4f} {pc[0]:>7.4f} {harm:>6}")

            # ---- S2 -------------------------------------------------------------
            print()
            rho = spearman(ts, tw)
            p = perm_p(ts, tw, rho, trials=20000)
            print(f"S2  Spearman rho(support_radius, W90) over {len(treat)} treatments = "
                  f"{rho:+.3f}, permutation p = {p:.4f}")

            fams = sorted({meta[m]["family"] for m in treat})
            sups = sorted({meta[m]["support_radius"] for m in treat})
            print()
            print("    W90 grid (rows = family, cols = support radius):")
            hdr = "      " + f"{'family':<10}" + "".join(f"{s:>8}" for s in sups) + f"{'range':>8}"
            print(hdr)
            within = []
            for f in fams:
                vals = []
                for s in sups:
                    got = [k_tr[m][2] for m in treat
                           if meta[m]["family"] == f and meta[m]["support_radius"] == s]
                    vals.append(got[0] if got else float("nan"))
                rng = max(vals) - min(vals)
                within.append(rng)
                print("      " + f"{f:<10}" + "".join(f"{v:>8.0f}" for v in vals) + f"{rng:>8.0f}")
            between = []
            for i, s in enumerate(sups):
                vals = [k_tr[m][2] for m in treat if meta[m]["support_radius"] == s]
                between.append(max(vals) - min(vals))
            print("      " + f"{'range':<10}" + "".join(f"{v:>8.0f}" for v in between))
            wi = sum(within) / len(within)
            be = sum(between) / len(between)
            print(f"    mean within-family range across support = {wi:.1f} px")
            print(f"    mean between-family range at fixed support = {be:.1f} px")
            print(f"    within/between = {wi / be if be else float('inf'):.2f} "
                  f"(PREREG wants >= 2.0 for 'tracks support specifically')")
            for f in fams:
                xs, ys = [], []
                for s in sups:
                    got = [k_tr[m][2] for m in treat
                           if meta[m]["family"] == f and meta[m]["support_radius"] == s]
                    if got:
                        xs.append(math.log2(s))
                        ys.append(got[0])
                print(f"    within-family slope, {f:<10}: dW90/dlog2(support) = {slope(xs, ys):+7.2f} px")

            # ---- S6 the discriminator -------------------------------------------
            print()
            if "dsml-s12" in k_tr and "ring-4-12" in k_tr:
                a, b = k_tr["dsml-s12"][2], k_tr["ring-4-12"][2]
                print(f"S6  discriminator: same declared support_px=25, "
                      f"dsml-s12 (no internal averaging) W90={a}, "
                      f"ring-4-12 (25x25 internal average) W90={b} -- "
                      f"{'DIFFER' if a != b else 'agree'}")

            # ---- S3 one-width regret -------------------------------------------
            print()
            best = None
            print("S3  one-width regret over the treatments (pooled over flat ROIs):")
            print(f"      {'w0':>5} {'regret':>9} {'worst measure':<14}")
            for i, w0 in enumerate(widths):
                worst_m, worst_v = None, -1e9
                for m in treat:
                    pw, pc = pooled_curves[m]
                    v = pc[pw.index(w0)] - floors[m]
                    if v > worst_v:
                        worst_v, worst_m = v, m
                print(f"      {w0:>5} {worst_v:>9.4f} {worst_m:<14}")
                if best is None or worst_v < best[1]:
                    best = (w0, worst_v, worst_m)
            print(f"    R* = {best[1]:.4f} ratio units at w0* = {best[0]} "
                  f"(worst measure {best[2]}), threshold T = {T:.4f}")
            print(f"    S3 verdict: {'EXCEEDS T -- coupling is severe' if best[1] > T else 'BELOW T -- one width serves everything'}")
            print(f"    S3 against the 0.02 floor alone: "
                  f"{'EXCEEDS' if best[1] > FLOOR_T else 'BELOW'}")

            # Supplementary yardstick, disclosed as an addition to the
            # pre-registration: R* is a within-ROI difference across measures,
            # while s_roi is a between-ROI difference of levels. The level
            # offsets largely cancel inside R*, so the reproducibility of R*
            # itself is the better-matched scale. Reported alongside, never
            # instead of, the pre-registered T.
            per_roi_R = []
            for roi in flat:
                rbest = None
                fl = {}
                cv = {}
                for m in treat:
                    w, c = curve(mrows, stack, roi, m)
                    cv[m] = (w, c)
                    fl[m] = min(c)
                for w0 in widths:
                    worst = max(cv[m][1][cv[m][0].index(w0)] - fl[m] for m in treat)
                    if rbest is None or worst < rbest[1]:
                        rbest = (w0, worst)
                per_roi_R.append(rbest)
            vals = [v for _, v in per_roi_R]
            mR = sum(vals) / len(vals)
            sR = math.sqrt(sum((v - mR) ** 2 for v in vals) / (len(vals) - 1)) if len(vals) > 1 else float("nan")
            print(f"    per-ROI R*: {[('w=%d' % w, '%.4f' % v) for w, v in per_roi_R]}")
            print(f"    mean {mR:.4f}, sd {sR:.4f} -> supplementary threshold "
                  f"3*sd = {3 * sR:.4f}; R* {'EXCEEDS' if best[1] > 3 * sR else 'BELOW'} it")

            # ---- S4 usable band --------------------------------------------------
            if detail:
                print()
                droi = detail[0]
                bands = {}
                selfempty = []
                for m in treat:
                    pw, pc = pooled_curves[m]
                    target = min(pc) + TOL * (pc[0] - min(pc))
                    gw, gc = curve(mrows, stack, droi, m, field="grad_stacked")
                    gmax = max(gc)
                    band = {w for w, v, g in zip(pw, pc, gc)
                            if v <= target and g >= (1 - DETAIL_TOL) * gmax}
                    bands[m] = band
                    if not band:
                        selfempty.append(m)
                print(f"S4  usable band per measure (noise within {TOL:.0%} of its floor "
                      f"AND detail within {DETAIL_TOL:.0%} of its peak), detail ROI {droi}:")
                for m in treat:
                    print(f"      {m:<14} {sorted(bands[m])}")
                inter = set(widths)
                for m in treat:
                    inter &= bands[m]
                print(f"    INTERSECTION over all {len(treat)} treatments = {sorted(inter)}")
                print(f"    measures whose own band is empty (no width satisfies THEM, so no "
                      f"support declaration could help either): {selfempty}")
                live = [m for m in treat if bands[m]]
                inter2 = set(widths)
                for m in live:
                    inter2 &= bands[m]
                print(f"    INTERSECTION over the {len(live)} measures with a non-empty band = "
                      f"{sorted(inter2)}")
                print(f"    S4 verdict: {'NON-EMPTY -- one width satisfies every measure on both sides' if inter else 'EMPTY -- no single width works'}")

                # Absolute-tolerance restatement, disclosed as a deviation: the
                # relative 10% rule is undefined in practice on a curve with no
                # improvement to make, and several measures have one.
                bands_abs = {}
                for m in treat:
                    pw, pc = pooled_curves[m]
                    gw, gc = curve(mrows, stack, droi, m, field="grad_stacked")
                    gmax = max(gc)
                    bands_abs[m] = {w for w, v, g in zip(pw, pc, gc)
                                    if v <= min(pc) + FLOOR_T and g >= (1 - DETAIL_TOL) * gmax}
                ia = set(widths)
                for m in treat:
                    ia &= bands_abs[m]
                print(f"    same with an absolute {FLOOR_T} ratio-unit noise tolerance "
                      f"instead of {TOL:.0%} relative: intersection = {sorted(ia)}")

                print()
                print(f"    detail-side gradient, DN/px, on {droi} (peak and value at w0*={best[0]}):")
                print(f"      {'measure':<14} {'g(1)':>8} {'g(peak)':>8} {'w_peak':>7} {'g(w0*)':>8} {'loss':>7}")
                for m in treat:
                    gw, gc = curve(mrows, stack, droi, m, field="grad_stacked")
                    gmax = max(gc)
                    print(f"      {m:<14} {gc[0]:>8.3f} {gmax:>8.3f} {gw[gc.index(gmax)]:>7} "
                          f"{gc[gw.index(best[0])]:>8.3f} "
                          f"{100 * (1 - gc[gw.index(best[0])] / gmax):>6.2f}%")

            # ---- S5 harm zone ----------------------------------------------------
            print()
            hv = [harms[m] for m in treat]
            hs = [meta[m]["support_radius"] for m in treat]
            print(f"S5  harm zone Wharm (widest width worse than no regularisation): "
                  f"{min(hv)}..{max(hv)}, Spearman rho vs support = {spearman(hs, hv):+.3f}")
            print(f"    a blind framework must choose w0 > {max(hv)} to clear every harm zone; "
                  f"w0* = {best[0]}")

            # ---- S7 what knowing support_px() is actually worth -----------------
            # ADDITION to the pre-registration, declared as such in the report.
            # S3 asks what one blind width costs. B3 asks something narrower:
            # what does the framework gain by being *told the support* and
            # nothing else? An oracle that knows only support_px() may pick one
            # width per support class, the same for every family in that class.
            print()

            def regret_partition(keyfn):
                """Best achievable worst-case regret when one width may be chosen
                per class of the given key."""
                classes = defaultdict(list)
                for m in treat:
                    classes[keyfn(m)].append(m)
                worst = 0.0
                picks = {}
                for cls, mem in classes.items():
                    bestw, bestv = None, None
                    for w0 in widths:
                        v = max(pooled_curves[m][1][pooled_curves[m][0].index(w0)] - floors[m]
                                for m in mem)
                        if bestv is None or v < bestv:
                            bestw, bestv = w0, v
                    picks[cls] = (bestw, bestv)
                    worst = max(worst, bestv)
                return worst, picks

            r_blind = best[1]
            r_sup, picks_sup = regret_partition(lambda m: meta[m]["support_radius"])
            r_fam, picks_fam = regret_partition(lambda m: meta[m]["family"])
            r_both, _ = regret_partition(lambda m: (meta[m]["family"], meta[m]["support_radius"]))
            print("S7  worst-case regret against a per-measure oracle, by what the "
                  "framework is allowed to know:")
            print(f"      knows nothing (one width for all)     R = {r_blind:.4f} at w0 = {best[0]}")
            print(f"      knows support_px() only               R = {r_sup:.4f}")
            for cls in sorted(picks_sup):
                print(f"          support radius {cls:>3}: width {picks_sup[cls][0]:>4}, "
                      f"class regret {picks_sup[cls][1]:.4f}")
            print(f"      knows the operator family only        R = {r_fam:.4f}")
            for cls in sorted(picks_fam):
                print(f"          family {cls:<10}: width {picks_fam[cls][0]:>4}, "
                      f"class regret {picks_fam[cls][1]:.4f}")
            print(f"      knows family AND support              R = {r_both:.4f}")
            v_sup = r_blind - r_sup
            print(f"    VALUE OF support_px() = {r_blind:.4f} - {r_sup:.4f} = {v_sup:+.4f} ratio units")
            print(f"    value of family label  = {r_blind - r_fam:+.4f} ratio units")
            print(f"    S7 verdict vs T={T:.4f}: "
                  f"{'support_px() earns its place' if v_sup > T else 'support_px() does not earn its place'}")
            print(f"    S7 verdict vs the {FLOOR_T} floor: "
                  f"{'earns its place' if v_sup > FLOOR_T else 'does not earn its place'}")

            # Leave-one-out: a zero that rests on one unusual measure is not a
            # result. Recompute the whole of S7 with each treatment dropped.
            print("    leave-one-out robustness (drop one treatment, recompute):")
            keep_all = list(treat)
            worst_v_sup = None
            for drop in keep_all:
                sub = [m for m in keep_all if m != drop]

                def partition(keyfn, members):
                    classes = defaultdict(list)
                    for m in members:
                        classes[keyfn(m)].append(m)
                    return max(
                        min(max(pooled_curves[m][1][pooled_curves[m][0].index(w0)] - floors[m]
                                for m in mem) for w0 in widths)
                        for mem in classes.values())

                rb = partition(lambda m: 0, sub)
                rs = partition(lambda m: meta[m]["support_radius"], sub)
                if worst_v_sup is None or rb - rs > worst_v_sup[1]:
                    worst_v_sup = (drop, rb - rs, rb, rs)
                print(f"        without {drop:<14} R_blind {rb:.4f}  R_support {rs:.4f}  "
                      f"value {rb - rs:+.4f}")
            print(f"    worst-case value of support_px() over all leave-one-out subsets = "
                  f"{worst_v_sup[1]:+.4f} (dropping {worst_v_sup[0]})")

            # W_eff: the same knee with an absolute tolerance. Disclosed as a
            # deviation, because the relative rule is undefined in practice on a
            # curve with no improvement to make and several measures have one.
            print()
            print(f"    W_eff (smallest width within {FLOOR_T} ratio units of the measure's own "
                  f"floor), the degeneracy-free restatement of S1:")
            weff = {}
            for m in treat:
                pw, pc = pooled_curves[m]
                tgt = min(pc) + FLOOR_T
                weff[m] = next(w for w, v in zip(pw, pc) if v <= tgt)
            for m in sorted(treat, key=lambda m: weff[m]):
                print(f"        {m:<14} sup_px {meta[m]['support_px']:>3}  W_eff {weff[m]:>4}")
            rho_eff = spearman([meta[m]["support_radius"] for m in treat],
                               [weff[m] for m in treat])
            print(f"      Spearman rho(support_radius, W_eff) = {rho_eff:+.3f}, "
                  f"p = {perm_p([float(meta[m]['support_radius']) for m in treat], [float(weff[m]) for m in treat], rho_eff, trials=20000):.4f}")
            print(f"      W_eff spans {min(weff.values())}..{max(weff.values())}; "
                  f"the single width that satisfies the most measures is "
                  f"{max(widths, key=lambda w: sum(1 for m in treat if pooled_curves[m][1][pooled_curves[m][0].index(w)] <= min(pooled_curves[m][1]) + FLOOR_T))}, "
                  f"satisfying {max(sum(1 for m in treat if pooled_curves[m][1][pooled_curves[m][0].index(w)] <= min(pooled_curves[m][1]) + FLOOR_T) for w in widths)} of {len(treat)}")

            # ---- S8 what the excess DOES track ----------------------------------
            try:
                phi = {}
                phi_src = f"data/sensitivity-{stack}.csv"
                with open(phi_src, newline="", encoding="utf-8") as fh:
                    for r in csv.DictReader(fh):
                        phi[r["measure"]] = float(r["phi"])
            except OSError:
                phi = {}
                phi_src = "(missing)"
            if phi and all(m in phi for m in treat):
                print()
                excess = {m: tops[m] - floors[m] for m in treat}
                xs = [phi[m] for m in treat]
                ys = [excess[m] for m in treat]
                rho_phi = spearman(xs, ys)
                rho_sup_ex = spearman([meta[m]["support_radius"] for m in treat],
                                      [excess[m] for m in treat])
                print("S8  what the naive-argmax noise excess actually tracks "
                      f"(ADDITION, declared in the report); phi from {phi_src}:")
                print(f"      {'measure':<14} {'sup_px':>6} {'taps':>6} {'phi':>8} "
                      f"{'c(1)':>8} {'floor':>8} {'excess':>8}")
                for m in sorted(treat, key=lambda m: -phi[m]):
                    print(f"      {m:<14} {meta[m]['support_px']:>6} {'':>6} {phi[m]:>8.5f} "
                          f"{tops[m]:>8.4f} {floors[m]:>8.4f} {excess[m]:>8.4f}")
                print(f"    Spearman rho(centre-tap fraction phi, argmax excess) = {rho_phi:+.3f}, "
                      f"p = {perm_p(xs, ys, rho_phi, trials=20000):.4f}")
                print(f"    Spearman rho(support radius,        argmax excess) = {rho_sup_ex:+.3f}, "
                      f"p = {perm_p([float(meta[m]['support_radius']) for m in treat], ys, rho_sup_ex, trials=20000):.4f}")

                # Each measure judged at its own best operating point, both
                # sides at once. Rule 9: a noise number never travels alone.
                if detail:
                    print()
                    print("    each measure at its own W_eff -- noise and detail together:")
                    print(f"      {'measure':<14} {'phi':>8} {'W_eff':>6} {'ratio':>8} "
                          f"{'grad DN/px':>11} {'ratio@w=1':>10} {'grad@w=1':>9}")
                    for m in sorted(treat, key=lambda m: -phi[m]):
                        pw, pc = pooled_curves[m]
                        gw, gc = curve(mrows, stack, droi, m, field="grad_stacked")
                        i = pw.index(weff[m])
                        print(f"      {m:<14} {phi[m]:>8.5f} {weff[m]:>6} {pc[i]:>8.4f} "
                              f"{gc[i]:>11.3f} {pc[0]:>10.4f} {gc[0]:>9.3f}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    main(sys.argv[1:])
