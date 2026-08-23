"""M17 analysis: three axes, one decision.

Reads only committed CSVs. Nothing here touches RAW.

The four axes, in the order PREREGISTRATION.md fixed them:
  * GATE 3/4 -- the fork reproduces M13's own `tenengrad-w13` rows.
  * axis 1 -- the blind spot: D = r(defocused) / r(in-focus) on a monotone edge.
  * axis 2 -- quality: mean `excess_dn` over M13's 30 depth-step cells.
  * axis 3 -- noise: N, median over flat ROIs then mean over stacks.
  * axis 4 -- cost.
"""

import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
M13 = os.path.join(HERE, "..", "m13-window-depth", "data")

CANDIDATES = [
    "tenengrad-w13",
    "tgmax-w13",
    "tgp95-w13",
    "tgp99-w13",
    "tgdual-geo-w13",
    "tgdual-sum-w13",
    "tgdual-tie5-w13",
    "tgrad-larger-w1-w13",
    "tgrad-geo-w1-w13",
    "tenengrad-sq-w13",
]
CONTROLS = ["tenengrad-w1", "tenengrad-w3", "tenengrad-w0", "tenengrad-w40"]
STATUS_QUO = "tenengrad-w13"

# Pre-registered thresholds. Both are borrowed from earlier milestones rather
# than chosen here: 0.87 DN is M13's own basin-flatness bar on `excess_dn`, and
# +0.02 ratio units is M9's severity floor on N.
D_MAX = 0.90
DE_MAX = 0.87
DN_MAX = 0.02

OUT = []


def say(s=""):
    print(s)
    OUT.append(s)


def rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fmt(v, n=4):
    return "n/a" if v is None else f"{v:.{n}f}"


def cost_radius_flat(tol=1.25):
    """Does the candidate's window filter hold box_mean's O(1)-in-radius cost?

    The pre-registration states the clause qualitatively ("cost is O(1) in the
    radius"); the numeric bound 1.25x over r = 1..40 is a POST-HOC
    operationalisation.  It is not load-bearing: box_mean measures 1.02x and
    box_max 4.90x, so no candidate lands anywhere near any plausible bar.
    """
    p = os.path.join(DATA, "boxcost.csv")
    ratio = {}
    if os.path.exists(p):
        by = {}
        for r in rows(p):
            by.setdefault(r["filter"], []).append(float(r["ms_per_frame_per_mpx_min"]))
        ratio = {f: max(v) / min(v) for f, v in by.items()}
    p2 = os.path.join(DATA, "boxcost-pct.csv")
    if os.path.exists(p2):
        by = {}
        for r in rows(p2):
            by.setdefault(r["filter"], []).append(float(r["ms_per_frame_per_mpx_min"]))
        for f, v in by.items():
            ratio.setdefault(f, max(v) / min(v))

    def flat(measure):
        if "tgp" in measure:
            return ratio.get("window_p95", 999.0) <= tol
        if "tgmax" in measure or "tgdual" in measure:
            return ratio.get("box_max", 999.0) <= tol
        return ratio.get("box_mean", 999.0) <= tol

    return flat


def sign_test(wins, n):
    """Exact two-sided binomial p under H0: p(win) = 0.5.  No scipy here."""
    def c(a, b):
        r = 1
        for i in range(b):
            r = r * (a - i) // (i + 1)
        return r
    tail = min(wins, n - wins)
    p = 2.0 * sum(c(n, k) for k in range(0, tail + 1)) / (2.0 ** n)
    return min(p, 1.0)


# --------------------------------------------------------------- gate 3 and 4


def gate_edge():
    """Every `tenengrad-w13` and `tenengrad-w40` row must be M13's, exactly."""
    ok = True
    checked = 0
    for stack in ("109MSDCF", "119MSDCF"):
        mine = rows(os.path.join(DATA, f"edge-{stack}.csv"))
        theirs = rows(os.path.join(M13, f"edge-{stack}.csv"))
        key = lambda r: (r["shape"], r["step"], r["seed"], r["measure"], r["width"])
        ref = {key(r): r for r in theirs if r["measure"] in ("tenengrad-w13", "tenengrad-w40")}
        for r in mine:
            if r["measure"] not in ("tenengrad-w13", "tenengrad-w40"):
                continue
            t = ref.get(key(r))
            if t is None:
                say(f"  GATE3 MISSING in M13: {key(r)}")
                ok = False
                continue
            for col in ("excess_dn", "acc", "acc_band", "band_rms", "far_rms", "single_sigma"):
                if r[col] != t[col]:
                    say(f"  GATE3 MISMATCH {key(r)} {col}: {r[col]} vs {t[col]}")
                    ok = False
            checked += 1
    say(f"GATE 3  edge harness reproduces M13 digit-for-digit: "
        f"{'PASS' if ok else 'FAIL'} ({checked} rows compared)")
    return ok


def gate_noise():
    ok = True
    checked = 0
    for stack in ("109MSDCF", "119MSDCF"):
        mine = rows(os.path.join(DATA, f"noise-{stack}.csv"))
        theirs = rows(os.path.join(M13, f"noise-{stack}.csv"))
        key = lambda r: (r["roi"], r["measure"], r["width"])
        ref = {key(r): r for r in theirs}
        for r in mine:
            if r["measure"] not in ("tenengrad-w13", "tenengrad-w0", "tenengrad-w40"):
                continue
            t = ref.get(key(r))
            if t is None:
                continue
            for col in ("ratio", "single_sigma", "stacked_sigma"):
                if r[col] != t[col]:
                    say(f"  GATE4 MISMATCH {key(r)} {col}: {r[col]} vs {t[col]}")
                    ok = False
            checked += 1
    say(f"GATE 4  noise harness reproduces M13 digit-for-digit: "
        f"{'PASS' if ok else 'FAIL'} ({checked} rows compared)")
    return ok


# ------------------------------------------------------------------- axis 1


def blindspot(path, plants, pair, col="edge", label=""):
    """D = r(pair[1]) / r(pair[0]), averaged over seeds within a noise level."""
    data = rows(path)
    names = []
    for r in data:
        if r["measure"] not in names:
            names.append(r["measure"])
    table = {}
    for plant in plants:
        for ns in sorted({r["noise_scale"] for r in data}):
            for m in names:
                sel = [r for r in data
                       if r["plant"] == plant and r["measure"] == m and r["noise_scale"] == ns]
                by_sigma = {}
                for r in sel:
                    by_sigma.setdefault(float(r["sigma"]), []).append(float(r[col]))
                if pair[0] not in by_sigma or pair[1] not in by_sigma:
                    continue
                a = sum(by_sigma[pair[0]]) / len(by_sigma[pair[0]])
                b = sum(by_sigma[pair[1]]) / len(by_sigma[pair[1]])
                table[(plant, ns, m)] = (b / a if a != 0 else float("nan"), a, b)
    return table, names


def null_control(path, plant, sigma, col="edge"):
    """D between two independent noise realisations at the SAME blur."""
    data = rows(path)
    out = {}
    for r in data:
        if r["plant"] != plant or float(r["sigma"]) != sigma or float(r["noise_scale"]) <= 0:
            continue
        out.setdefault(r["measure"], []).append(float(r[col]))
    return {m: (max(v) / min(v) if min(v) else float("nan")) for m, v in out.items() if len(v) > 1}


# ------------------------------------------------------------------- axis 2


def edge_cells():
    """cell = (stack, shape, step); value = mean `excess_dn` over the 3 seeds."""
    acc = {}
    for stack in ("109MSDCF", "119MSDCF"):
        for r in rows(os.path.join(DATA, f"edge-{stack}.csv")):
            if r["width"] != "1":
                continue
            k = (r["measure"], stack, r["shape"], int(r["step"]))
            acc.setdefault(k, []).append(float(r["excess_dn"]))
    return {k: sum(v) / len(v) for k, v in acc.items()}


# ------------------------------------------------------------------- axis 3


def noise_n():
    """N = median over the 4 flat ROIs of a stack, then mean over stacks."""
    per = {}
    for stack in ("109MSDCF", "119MSDCF"):
        by = {}
        for r in rows(os.path.join(DATA, f"noise-{stack}.csv")):
            if r["width"] != "1":
                continue
            by.setdefault(r["measure"], []).append(float(r["ratio"]))
        for m, v in by.items():
            v = sorted(v)
            n = len(v)
            med = v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])
            per.setdefault(m, {})[stack] = med
    return {m: (sum(d.values()) / len(d), d) for m, d in per.items()}


# --------------------------------------------------------------------- main


def main():
    say("=" * 78)
    say("M17 -- dual (mean, max) focus response.  Analysis of committed CSVs.")
    say("=" * 78)

    say("\n-- GATES ------------------------------------------------------------")
    g3 = gate_edge()
    g4 = gate_noise()

    say("\n-- AXIS 1: the blind spot -------------------------------------------")
    say("D = r(defocused) / r(in-focus) at the boundary column. 1.0000 = blind.")

    for tag, path in (("normalised (shipped semantics)", "blindspot-norm.csv"),
                      ("un-normalised (operator only)", "blindspot-nonorm.csv")):
        p = os.path.join(DATA, path)
        if not os.path.exists(p):
            continue
        tbl, names = blindspot(p, ["step", "ramp9", "texture-synth", "texture-real"], (0.0, 3.0))
        say(f"\n  B1 {tag}, noiseless (noise_scale=0), sigma 3 vs sigma 0:")
        head = f"    {'measure':<26}" + "".join(f"{p:>16}" for p in
                                                ["step", "ramp9", "texture-synth", "texture-real"])
        say(head)
        for m in names:
            line = f"    {m:<26}"
            for plant in ["step", "ramp9", "texture-synth", "texture-real"]:
                v = tbl.get((plant, "0", m))
                line += f"{fmt(v[0], 4) if v else 'n/a':>16}"
            say(line)

    p = os.path.join(DATA, "blindspot-norm.csv")
    if os.path.exists(p):
        tbl, names = blindspot(p, ["step", "ramp9", "texture-synth", "texture-real"], (0.0, 3.0))
        say("\n  B1 normalised, WITH sensor noise (noise_scale=1, 3 seeds):")
        say(f"    {'measure':<26}" + "".join(f"{q:>16}" for q in
                                             ["step", "ramp9", "texture-synth", "texture-real"]))
        for m in names:
            line = f"    {m:<26}"
            for plant in ["step", "ramp9", "texture-synth", "texture-real"]:
                v = tbl.get((plant, "1", m))
                line += f"{fmt(v[0], 4) if v else 'n/a':>16}"
            say(line)

        nc = null_control(p, "step", 0.0)
        say("\n  NULL CONTROL (sigma 0 vs sigma 0, independent noise draws):")
        say("    worst-case ratio across the 3 seeds; must be ~1.0000")
        for m in names:
            if m in nc:
                say(f"    {m:<26}{nc[m]:>10.4f}")

    p = os.path.join(DATA, "blindspot-edge.csv")
    if os.path.exists(p):
        for ns, tag in (("0", "noiseless"), ("1", "with sensor noise, 3 seeds")):
            tbl, names = blindspot(p, ["edge2"], (20.0, 29.0))
            say(f"\n  B2 realistic compositor ({tag}), frame 29 vs frame 20 "
                f"(= 3.15 sigma of extra blur):")
            for m in names:
                v = tbl.get(("edge2", ns, m))
                if v:
                    say(f"    {m:<26}{v[0]:>10.4f}   (in-focus {v[1]:.3f} -> defocused {v[2]:.3f})")

    say("\n-- AXIS 2: quality on M13's 36 occluding-edge cells ------------------")
    cells = edge_cells()
    if cells:
        measures = sorted({k[0] for k in cells})
        keys = sorted({k[1:] for k in cells})
        step_cells = [k for k in keys if k[2] > 0]
        zero_cells = [k for k in keys if k[2] == 0]
        say(f"  {len(keys)} cells ({len(step_cells)} with a depth step, "
            f"{len(zero_cells)} zero-step)")
        base = None
        say(f"\n    {'measure':<26}{'mean excess_dn':>16}{'delta vs w13':>14}"
            f"{'worst cell':>12}{'zero-step':>12}")
        table = {}
        for m in measures:
            vals = [cells[(m,) + k] for k in step_cells]
            zvals = [cells[(m,) + k] for k in zero_cells]
            mean = sum(vals) / len(vals)
            table[m] = mean
            if m == STATUS_QUO:
                base = mean
        for m in [STATUS_QUO] + [x for x in measures if x != STATUS_QUO]:
            vals = [cells[(m,) + k] for k in step_cells]
            zvals = [cells[(m,) + k] for k in zero_cells]
            mean = sum(vals) / len(vals)
            say(f"    {m:<26}{mean:>16.4f}{mean - base:>+14.4f}"
                f"{max(vals):>12.4f}{sum(zvals) / len(zvals):>12.4f}")

    say("\n-- AXIS 2b: paired per-cell comparison vs the shipped operator -------")
    if cells:
        say("  sign test over the 30 depth-step cells; a mean is worthless if it")
        say("  is carried by two cells.  win = candidate's excess_dn is LOWER.")
        say(f"\n    {'measure':<26}{'wins/30':>9}{'median d':>11}{'worst reg':>11}"
            f"{'best gain':>11}{'p(two-sided)':>14}")
        for m in [x for x in measures if x != STATUS_QUO]:
            d = [cells[(m,) + k] - cells[(STATUS_QUO,) + k] for k in step_cells]
            wins = sum(1 for x in d if x < 0)
            d_sorted = sorted(d)
            nn = len(d_sorted)
            med = (d_sorted[nn // 2] if nn % 2
                   else 0.5 * (d_sorted[nn // 2 - 1] + d_sorted[nn // 2]))
            say(f"    {m:<26}{wins:>6}/{nn:<3}{med:>+11.4f}{max(d):>+11.4f}"
                f"{min(d):>+11.4f}{sign_test(wins, nn):>14.5f}")
        say("\n  winner, split by stack and shape (mean excess_dn delta vs w13):")
        win = "tenengrad-sq-w13"
        if any(k[0] == win for k in cells):
            for stack in sorted({k[0] for k in step_cells}):
                for shape in sorted({k[1] for k in step_cells if k[0] == stack}):
                    sel = [k for k in step_cells if k[0] == stack and k[1] == shape]
                    d = [cells[(win,) + k] - cells[(STATUS_QUO,) + k] for k in sel]
                    say(f"    {stack:<12}{shape:<12}{sum(d) / len(d):>+10.4f}"
                        f"   ({sum(1 for x in d if x < 0)}/{len(d)} cells improved)")

    say("\n-- AXIS 1b: is the shipped D>1 real, or pixel-side junk? -------------")
    p = os.path.join(DATA, "blindspot-norm.csv")
    if os.path.exists(p):
        say("  D read at the bright-side boundary column x0 and at the dark-side")
        say("  column x0-1.  If the sign flips, D>1 is a normalisation artefact")
        say("  that varies with which pixel you ask, not a preference for defocus.")
        b_hi, names = blindspot(p, ["step"], (0.0, 3.0), col="edge")
        b_lo, _ = blindspot(p, ["step"], (0.0, 3.0), col="edge_dark")
        say(f"\n    {'measure':<26}{'D at x0':>12}{'D at x0-1':>12}{'verdict':>22}")
        for m in names:
            a = b_hi.get(("step", "0", m))
            b = b_lo.get(("step", "0", m))
            if not a or not b:
                continue
            flip = (a[0] - 1.0) * (b[0] - 1.0) < 0
            say(f"    {m:<26}{a[0]:>12.4f}{b[0]:>12.4f}"
                f"{('SIGN FLIPS' if flip else 'same side of 1'):>22}")
        pn = os.path.join(DATA, "blindspot-nonorm.csv")
        if os.path.exists(pn):
            n_hi, nnames = blindspot(pn, ["step"], (0.0, 3.0), col="edge")
            n_lo, _ = blindspot(pn, ["step"], (0.0, 3.0), col="edge_dark")
            say("\n  same check on the UN-NORMALISED operator (no sigma divide):")
            say(f"    {'measure':<26}{'D at x0':>12}{'D at x0-1':>12}")
            for m in nnames:
                a = n_hi.get(("step", "0", m))
                b = n_lo.get(("step", "0", m))
                if a and b:
                    say(f"    {m:<26}{a[0]:>12.7f}{b[0]:>12.7f}")

    say("\n-- AXIS 3: merged noise on flat ROIs ---------------------------------")
    n = noise_n()
    if n:
        base = n[STATUS_QUO][0]
        say(f"    {'measure':<26}{'N pooled':>10}{'delta N':>10}"
            f"{'109MSDCF':>12}{'119MSDCF':>12}")
        for m in [STATUS_QUO] + [x for x in sorted(n) if x != STATUS_QUO]:
            v, d = n[m]
            say(f"    {m:<26}{v:>10.5f}{v - base:>+10.5f}"
                f"{d.get('109MSDCF', float('nan')):>12.5f}"
                f"{d.get('119MSDCF', float('nan')):>12.5f}")

    say("\n-- AXIS 4: cost ------------------------------------------------------")
    p = os.path.join(DATA, "boxcost.csv")
    if os.path.exists(p):
        by = {}
        for r in rows(p):
            by.setdefault(r["filter"], []).append((int(r["radius"]),
                                                   float(r["ms_per_frame_per_mpx_min"]),
                                                   float(r["spread_pct"])))
        say("    per-setting MINIMUM over alternating-direction passes, "
            "ms/frame/Mpx")
        radii = sorted({x[0] for v in by.values() for x in v})
        say(f"    {'filter':<14}" + "".join(f"{('r=' + str(r)):>10}" for r in radii)
            + f"{'max/min':>10}")
        for f, v in by.items():
            d = {r: t for r, t, _ in v}
            lo = min(d.values())
            hi = max(d.values())
            say(f"    {f:<14}" + "".join(f"{d[r]:>10.4f}" for r in radii)
                + f"{hi / lo:>10.2f}x")
        say("    worst within-setting spread (max/min over passes): "
            + ", ".join(f"{f} +{max(s for _, _, s in v):.1f}%" for f, v in by.items()))

    p = os.path.join(DATA, "boxcost-pct.csv")
    if os.path.exists(p):
        by = {}
        for r in rows(p):
            by.setdefault(r["filter"], []).append((int(r["radius"]),
                                                   float(r["ms_per_frame_per_mpx_min"])))
        say("\n    exact windowed percentile, auxiliary run (CONTAMINATED: this")
        say("    run overlapped the edge sweep, spreads to +127%; the growth is")
        say("    3 orders of magnitude so the ordering is not in doubt):")
        radii = sorted({x[0] for v in by.values() for x in v})
        say(f"    {'filter':<14}" + "".join(f"{('r=' + str(r)):>12}" for r in radii)
            + f"{'max/min':>10}")
        for f, v in by.items():
            d = {r: t for r, t in v}
            say(f"    {f:<14}" + "".join(f"{d[r]:>12.2f}" for r in radii)
                + f"{max(d.values()) / min(d.values()):>9.0f}x")

    p = os.path.join(DATA, "cost-measures.csv")
    if os.path.exists(p):
        say("\n    whole-measure cost, ms/frame/Mpx (min over alternating passes):")
        rs = rows(p)
        base = next((float(r["ms_per_frame_per_mpx_min"]) for r in rs
                     if r["measure"] == STATUS_QUO), None)
        for r in rs:
            v = float(r["ms_per_frame_per_mpx_min"])
            say(f"    {r['measure']:<26}{v:>10.4f}{v / base:>10.2f}x"
                f"   (pass spread +{float(r['spread_pct']):.1f}%)")

    say("\n-- DECISION ----------------------------------------------------------")
    say(f"  pre-registered: SHIP iff D <= {D_MAX} and dE <= +{DE_MAX} DN "
        f"and dN <= +{DN_MAX} and cost is O(1) in radius.")
    p = os.path.join(DATA, "blindspot-norm.csv")
    if cells and n and os.path.exists(p):
        tbl, names = blindspot(p, ["step"], (0.0, 3.0))
        base_e = None
        for m in [STATUS_QUO] + [x for x in CANDIDATES if x != STATUS_QUO]:
            keys = sorted({k[1:] for k in cells if k[0] == m})
            step_cells = [k for k in keys if k[2] > 0]
            if not step_cells:
                continue
            e = sum(cells[(m,) + k] for k in step_cells) / len(step_cells)
            if m == STATUS_QUO:
                base_e = e
        say(f"\n    {'candidate':<26}{'D (step)':>10}{'dE (DN)':>10}{'dN':>10}"
            f"{'r-flat?':>9}{'verdict':>16}")
        cost_flat = cost_radius_flat()
        for m in [STATUS_QUO] + [x for x in CANDIDATES if x != STATUS_QUO]:
            d = tbl.get(("step", "0", m))
            keys = sorted({k[1:] for k in cells if k[0] == m})
            step_cells = [k for k in keys if k[2] > 0]
            e = (sum(cells[(m,) + k] for k in step_cells) / len(step_cells)
                 if step_cells else None)
            de = None if e is None else e - base_e
            dn = None if m not in n else n[m][0] - n[STATUS_QUO][0]
            if d is None or de is None or dn is None:
                say(f"    {m:<26}{'?':>10}{'?':>10}{'?':>10}{'?':>9}{'incomplete':>16}")
                continue
            flat = cost_flat(m)
            passes = [d[0] <= D_MAX, de <= DE_MAX, dn <= DN_MAX]
            if all(passes) and flat:
                v = "SHIP"
            elif all(passes) and not flat:
                v = "NO (cost)"
            elif passes[0] and sum(passes) == 2:
                over_e = de > DE_MAX and de < 2 * DE_MAX
                over_n = dn > DN_MAX and dn < 2 * DN_MAX
                v = "FLAG" if (over_e or over_n) else "NO"
            else:
                v = "NO"
            say(f"    {m:<26}{d[0]:>10.4f}{de:>+10.4f}{dn:>+10.5f}"
                f"{('yes' if flat else 'NO'):>9}{v:>16}")

    with open(os.path.join(DATA, "m17-analysis.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(OUT) + "\n")
    return 0 if (g3 and g4) else 1


if __name__ == "__main__":
    sys.exit(main())
