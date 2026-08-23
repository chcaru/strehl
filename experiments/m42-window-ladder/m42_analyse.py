#!/usr/bin/env python3
"""M42 -- the window ladder for `tenengrad-sq`.  Owner question Q1.

Reads only committed CSVs in data/.  No RAW access.  Writes data/m42-analysis.txt.

Statistic, per the pre-registration section 1: regret against the per-cell best
*within an operator's own ladder*, exactly as fact 60 defines it.  Mixing the two
operators into one regret pool would let one operator's bad windows flatter the
other's, so the pools are kept separate and the operators are compared on
absolute excess_dn instead.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
M13 = os.path.join(HERE, "..", "m13-window-depth", "data")

LADDER = [0, 1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15, 17, 18, 20, 23, 26, 33, 40]
SEEDS = ("20260823", "771117", "4242424")
STACKS = ("109MSDCF", "119MSDCF")
# 0.87 DN is M13's own pre-registered basin-flatness threshold, re-used by M15
# (facts 81, 60).  It is BORROWED, not invented here.
BASIN_DN = 0.87
SHIPPED_W = 13

OUT = []


def say(s=""):
    print(s)
    OUT.append(s)


def rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def cells(stack_files, prefix):
    """cell = (stack, shape, step) -> {window: mean excess_dn over the 3 seeds}."""
    acc = {}
    for stack, path in stack_files:
        if not os.path.exists(path):
            continue
        for r in rows(path):
            if r["width"] != "1":
                continue
            m = r["measure"]
            if not m.startswith(prefix):
                continue
            tail = m[len(prefix):]
            if not tail.startswith("w") or not tail[1:].isdigit():
                continue
            w = int(tail[1:])
            k = (stack, r["shape"], int(r["step"]))
            acc.setdefault(k, {}).setdefault(w, []).append(float(r["excess_dn"]))
    return {k: {w: sum(v) / len(v) for w, v in d.items()} for k, d in acc.items()}


def regret_table(cell_map, keys):
    """mean and worst regret per window, over `keys`, pooled within this operator."""
    windows = sorted({w for k in keys for w in cell_map[k]})
    per_cell = {}
    for k in keys:
        d = cell_map[k]
        if len(d) != len(windows):
            continue
        best = min(d.values())
        per_cell[k] = {w: d[w] - best for w in windows}
    if not per_cell:
        return {}, {}, 0
    mean = {w: sum(per_cell[k][w] for k in per_cell) / len(per_cell) for w in windows}
    worst = {w: max(per_cell[k][w] for k in per_cell) for w in windows}
    return mean, worst, len(per_cell)


def argmin_label(table):
    w = min(table, key=lambda k: table[k])
    lo, hi = min(table), max(table)
    tag = "ENDPOINT (no turnover found within the sweep)" if w in (lo, hi) else "interior"
    return w, table[w], tag


def basin(table, bar):
    lo = min(table.values())
    return sorted(w for w in table if table[w] - lo <= bar)


def fmt_ladder(table, width=8, prec=3):
    return "".join(f"{table[w]:>{width}.{prec}f}" if w in table else f"{'-':>{width}}"
                   for w in LADDER)


def header_ladder(width=8):
    return "".join(f"{('w' + str(w)):>{width}}" for w in LADDER)


# ------------------------------------------------------------------ gate 1


def gate1():
    """M13's own ladder must come back out of MY harness: w13 / 3.171 / 12.111,
    and the zero-step stratum at the w40 endpoint (facts 60, 61)."""
    cm = cells([(s, os.path.join(DATA, f"edge-{s}.csv")) for s in STACKS], "tenengrad-")
    if not cm:
        say("GATE 1  no data yet")
        return False
    step_keys = [k for k in cm if k[2] > 0]
    zero_keys = [k for k in cm if k[2] == 0]
    mean, worst, n = regret_table(cm, step_keys)
    zmean, _, zn = regret_table(cm, zero_keys)
    w, v, tag = argmin_label(mean)
    zw, zv, ztag = argmin_label(zmean)
    ok = (w == 13 and abs(v - 3.171) < 0.01 and abs(max(worst.values()) * 0 + worst[w] - 12.111) < 0.01
          and zw == 40 and zv < 0.01)
    say(f"GATE 1  M13's ladder reproduces from MY harness: {'PASS' if ok else 'CHECK'}")
    say(f"        {n} depth-step cells -> argmin w{w} ({tag}), mean regret {v:.4f}, "
        f"worst at that window {worst[w]:.4f}")
    say(f"        fact 60 says:            argmin w13,           mean regret 3.171,   "
        f"worst 12.111")
    say(f"        {zn} zero-step cells   -> argmin w{zw} ({ztag}), mean regret {zv:.4f}")
    say(f"        fact 61 says:            argmin w40 ENDPOINT,  regret 0.000")
    return ok


# ------------------------------------------------------------------- main


def main():
    say("=" * 86)
    say("M42 -- the window ladder for `tenengrad-sq`.  Owner question Q1.")
    say("Regret is pooled WITHIN an operator (pre-registration section 1).")
    say("=" * 86)

    say("\n-- GATE 1 -----------------------------------------------------------------")
    g1 = gate1()

    ops = [("tenengrad-", "magnitude  (M13/M15's operator, SHIPPED in focus.rs)"),
           ("tenengrad-sq-", "squared    (M17's recommendation, NOT yet in focus.rs)")]
    summary = {}

    for prefix, label in ops:
        cm = cells([(s, os.path.join(DATA, f"edge-{s}.csv")) for s in STACKS], prefix)
        if not cm:
            continue
        step_keys = [k for k in cm if k[2] > 0]
        zero_keys = [k for k in cm if k[2] == 0]
        mean, worst, n = regret_table(cm, step_keys)
        zmean, _, zn = regret_table(cm, zero_keys)
        absmean = {w: sum(cm[k][w] for k in step_keys) / len(step_keys)
                   for w in sorted({w for k in step_keys for w in cm[k]})}

        say(f"\n-- AXIS 1: quality vs window -- {label}")
        say(f"   {n} depth-step cells, regret in DN (lower is better)")
        say(f"          {header_ladder()}")
        say(f"   mean   {fmt_ladder(mean)}")
        say(f"   worst  {fmt_ladder(worst)}")
        say(f"   abs    {fmt_ladder(absmean, prec=2)}")
        w, v, tag = argmin_label(mean)
        ww, wv, wtag = argmin_label(worst)
        b = basin(mean, BASIN_DN)
        say(f"\n   mean-regret  argmin w{w} ({tag}) at {v:.4f} DN")
        say(f"   worst-regret argmin w{ww} ({wtag}) at {wv:.4f} DN")
        say(f"   basin (within {BASIN_DN} DN of the minimum): "
            f"{'w' + ', w'.join(str(x) for x in b)}")
        say(f"   is the shipped w{SHIPPED_W} inside the basin?  "
            f"{'YES' if SHIPPED_W in b else 'NO'}   "
            f"(regret at w{SHIPPED_W} = {mean.get(SHIPPED_W, float('nan')):.4f}, "
            f"excess over the min = {mean.get(SHIPPED_W, float('nan')) - min(mean.values()):+.4f} DN)")
        zw, zv, ztag = argmin_label(zmean)
        say(f"   NULL STRATUM ({zn} zero-step cells): argmin w{zw} ({ztag}) at {zv:.4f} DN"
            f"   -- fact 61 predicts an endpoint, and a depth signal without a depth step"
            f" would be the failure")
        summary[prefix] = dict(mean=mean, worst=worst, absmean=absmean, basin=b,
                               argmin=w, argmin_val=v, tag=tag, zero=zw)

        say(f"\n   ARGMIN UNCERTAINTY -- 6 independent argmins (2 stacks x 3 seeds),")
        say(f"   regret recomputed inside each subset so they really are independent:")
        per = []
        for stack in STACKS:
            path = os.path.join(DATA, f"edge-{stack}.csv")
            if not os.path.exists(path):
                continue
            for seed in SEEDS:
                acc = {}
                for r in rows(path):
                    if r["width"] != "1" or r["seed"][:len(seed)] != seed:
                        continue
                    m = r["measure"]
                    if not m.startswith(prefix):
                        continue
                    tail = m[len(prefix):]
                    if not tail.startswith("w") or not tail[1:].isdigit():
                        continue
                    if int(r["step"]) == 0:
                        continue
                    acc.setdefault((r["shape"], r["step"]), {})[int(tail[1:])] = \
                        float(r["excess_dn"])
                if not acc:
                    continue
                mn, _, cnt = regret_table(acc, list(acc))
                if not mn:
                    continue
                a = min(mn, key=lambda k: mn[k])
                per.append((stack, seed, a, mn[a], cnt))
        for stack, seed, a, val, cnt in per:
            say(f"     {stack}  seed {seed:<10}  argmin w{a:<3}  ({cnt} cells)")
        if per:
            aa = [x[2] for x in per]
            say(f"     spread: w{min(aa)} .. w{max(aa)}   "
                f"({len(set(aa))} distinct argmins across {len(aa)} independent subsets)")

    # --------------------------------------------------------------- axis 2
    say("\n-- AXIS 2: merged noise N vs window ----------------------------------------")
    say("   median over the 4 committed flat ROIs of a stack, then mean over stacks")
    for prefix, label in ops:
        per = {}
        for stack in STACKS:
            p = os.path.join(DATA, f"noise-{stack}.csv")
            if not os.path.exists(p):
                continue
            by = {}
            for r in rows(p):
                if r["width"] != "1":
                    continue
                m = r["measure"]
                if not m.startswith(prefix):
                    continue
                tail = m[len(prefix):]
                if not tail.startswith("w") or not tail[1:].isdigit():
                    continue
                by.setdefault(int(tail[1:]), []).append(float(r["ratio"]))
            for w, v in by.items():
                v = sorted(v)
                nn = len(v)
                med = v[nn // 2] if nn % 2 else 0.5 * (v[nn // 2 - 1] + v[nn // 2])
                per.setdefault(w, []).append(med)
        if per:
            n = {w: sum(v) / len(v) for w, v in per.items()}
            say(f"   {label[:10]}")
            say(f"          {header_ladder()}")
            say(f"   N      {fmt_ladder(n, prec=4)}")
            bw, bv, btag = argmin_label(n)
            say(f"   argmin w{bw} ({btag}) at N = {bv:.5f};  "
                f"N(w{SHIPPED_W}) = {n.get(SHIPPED_W, float('nan')):.5f}")

    # --------------------------------------------------------------- axis 3
    say("\n-- AXIS 3: is the blind-spot cure radius-dependent? -------------------------")
    say("   D = response(sigma 3) / response(sigma 0) on the boundary column.")
    say("   1.0000 = totally blind.  This is the whole reason tenengrad-sq won M17.")
    p = os.path.join(DATA, "blindspot-nonorm.csv")
    if os.path.exists(p):
        data = rows(p)
        for prefix, label in ops:
            for plant in ("step", "ramp9"):
                d = {}
                for r in data:
                    if r["plant"] != plant or float(r["noise_scale"]) != 0:
                        continue
                    m = r["measure"]
                    if not m.endswith("-nonorm") or not m.startswith(prefix):
                        continue
                    tail = m[len(prefix):-len("-nonorm")]
                    if not tail.startswith("w") or not tail[1:].isdigit():
                        continue
                    d.setdefault(int(tail[1:]), {})[float(r["sigma"])] = float(r["edge"])
                t = {w: v[3.0] / v[0.0] for w, v in d.items() if 0.0 in v and 3.0 in v and v[0.0]}
                if t:
                    say(f"   {label[:10]}  plant={plant}")
                    say(f"          {header_ladder()}")
                    say(f"   D      {fmt_ladder(t, prec=4)}")
        # controls
        nc = {}
        for r in data:
            if r["plant"] != "step" or float(r["sigma"]) != 0.0 or float(r["noise_scale"]) <= 0:
                continue
            nc.setdefault(r["measure"], []).append(float(r["edge"]))
        nc = {m: max(v) / min(v) for m, v in nc.items() if len(v) > 1 and min(v)}
        if nc:
            say(f"\n   NULL CONTROL (sigma 0 vs sigma 0, independent noise): worst ratio over "
                f"all {len(nc)} arms = {max(nc.values()):.4f}  (must be ~1.0000)")
        pc = {}
        for r in data:
            if r["plant"] != "texture-real" or float(r["noise_scale"]) != 0:
                continue
            pc.setdefault(r["measure"], {})[float(r["sigma"])] = float(r["edge"])
        pc = {m: v[3.0] / v[0.0] for m, v in pc.items() if 0.0 in v and 3.0 in v and v[0.0]}
        if pc:
            say(f"   POSITIVE CONTROL (real corpus texture, same ladder): worst D over "
                f"all {len(pc)} arms = {max(pc.values()):.4f}  (must be << 1)")

    # --------------------------------------------------------------- axis 4
    say("\n-- AXIS 4: cost vs window ---------------------------------------------------")
    p = os.path.join(DATA, "cost-measures.csv")
    if os.path.exists(p):
        for prefix, label in ops:
            t = {}
            sp = {}
            for r in rows(p):
                m = r["measure"]
                if not m.startswith(prefix):
                    continue
                tail = m[len(prefix):]
                if not tail.startswith("w") or not tail[1:].isdigit():
                    continue
                t[int(tail[1:])] = float(r["ms_per_frame_per_mpx_min"])
                sp[int(tail[1:])] = float(r["spread_pct"])
            if t:
                say(f"   {label[:10]}  ms/frame/Mpx, min over alternating passes")
                say(f"          {header_ladder()}")
                say(f"   cost   {fmt_ladder(t, prec=3)}")
                say(f"   max/min over the ladder = {max(t.values()) / min(t.values()):.3f}x"
                    f"   (worst within-setting pass spread +{max(sp.values()):.1f}%)")

    # ------------------------------------------------------------- decision
    say("\n-- DECISION ------------------------------------------------------------------")
    sq = summary.get("tenengrad-sq-")
    mg = summary.get("tenengrad-")
    if sq and mg:
        inb = SHIPPED_W in sq["basin"]
        gap = sq["mean"][SHIPPED_W] - min(sq["mean"].values())
        say(f"   pre-registered: 13 SURVIVES iff 13 is inside tenengrad-sq's "
            f"{BASIN_DN} DN mean-regret basin.")
        say(f"   tenengrad-sq basin: w{', w'.join(str(x) for x in sq['basin'])}")
        say(f"   w13 regret excess over the ladder minimum: {gap:+.4f} DN")
        say(f"   VERDICT: WINDOW_RADIUS = 13 {'SURVIVES' if inb else 'IS OUTSIDE THE BASIN'}"
            f" the operator change.")
        say(f"   (magnitude argmin w{mg['argmin']}, squared argmin w{sq['argmin']})")

    with open(os.path.join(DATA, "m42-analysis.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(OUT) + "\n")
    return 0 if g1 else 1


if __name__ == "__main__":
    sys.exit(main())
