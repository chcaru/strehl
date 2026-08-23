#!/usr/bin/env python3
"""M42 -- argmin uncertainty, and the null-control breakdown.

Written as a SEPARATE script on purpose. `m42_analyse.py` has already produced
results that are reported, and rule 15 forbids modifying it. Its argmin-uncertainty
block produced NO output (it matched on the input seed, but the CSV's `seed` column
carries a per-cell derived seed, not the input), so nothing from it was ever reported.
This file supplies that block instead.

Replicates are recovered structurally: within a (stack, shape, step) cell there are
exactly 3 distinct derived seeds, one per input seed, and sorting them gives a stable
replicate index. Verified below before use.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
LADDER = [0, 1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15, 17, 18, 20, 23, 26, 33, 40]
STACKS = ("109MSDCF", "119MSDCF")
BASIN_DN = 0.87
OUT = []


def say(s=""):
    print(s)
    OUT.append(s)


def rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load(stack, prefix):
    """-> {(shape, step): {replicate: {window: excess_dn}}}, replicate in 0..2"""
    raw = {}
    for r in rows(os.path.join(DATA, f"edge-{stack}.csv")):
        if r["width"] != "1" or int(r["step"]) == 0:
            continue
        m = r["measure"]
        if not m.startswith(prefix):
            continue
        tail = m[len(prefix):]
        if not tail.startswith("w") or not tail[1:].isdigit():
            continue
        raw.setdefault((r["shape"], r["step"]), {}) \
           .setdefault(r["seed"], {})[int(tail[1:])] = float(r["excess_dn"])
    out = {}
    for cell, by_seed in raw.items():
        seeds = sorted(by_seed)
        if len(seeds) != 3:
            say(f"  !! {stack} {cell} has {len(seeds)} seeds, expected 3 -- ABORT")
            sys.exit(2)
        out[cell] = {i: by_seed[s] for i, s in enumerate(seeds)}
    return out


def argmin_of(subset):
    """subset: list of {window: excess_dn}. Regret pooled inside the subset only."""
    per = []
    for d in subset:
        if len(d) != len(LADDER):
            continue
        best = min(d.values())
        per.append({w: d[w] - best for w in LADDER})
    if not per:
        return None, None, None
    mean = {w: sum(p[w] for p in per) / len(per) for w in LADDER}
    a = min(mean, key=lambda k: mean[k])
    lo = mean[a]
    band = sorted(w for w in LADDER if mean[w] - lo <= BASIN_DN)
    return a, mean, band


def main():
    say("=" * 82)
    say("M42 -- argmin uncertainty: 6 independent (stack x replicate) subsets")
    say("Regret is recomputed inside each subset, so the subsets really are independent.")
    say("=" * 82)

    for prefix, label in (("tenengrad-", "magnitude (shipped)"),
                          ("tenengrad-sq-", "squared (M17's recommendation)")):
        say(f"\n-- {label}")
        allargs = []
        for stack in STACKS:
            cells = load(stack, prefix)
            for rep in range(3):
                sub = [cells[c][rep] for c in cells]
                a, mean, band = argmin_of(sub)
                if a is None:
                    continue
                allargs.append(a)
                say(f"   {stack}  replicate {rep + 1}   argmin w{a:<3} "
                    f"({len(sub)} cells)   basin w{band[0]}..w{band[-1]}")
        if allargs:
            say(f"   -> 6-subset argmin spread: w{min(allargs)} .. w{max(allargs)}  "
                f"({sorted(set(allargs))})")

        # per-stack pooled (3 replicates together), the level fact 60 reports at
        for stack in STACKS:
            cells = load(stack, prefix)
            sub = []
            for c in cells:
                d = {w: sum(cells[c][r][w] for r in range(3)) / 3.0 for w in LADDER}
                sub.append(d)
            a, mean, band = argmin_of(sub)
            say(f"   {stack} pooled over 3 replicates: argmin w{a}, "
                f"basin w{band[0]}..w{band[-1]}, regret(w13)-regret(min) = "
                f"{mean[13] - mean[a]:+.4f} DN")

    # ---- the null control, per arm, so the worst case is attributable
    say("\n-- NULL CONTROL breakdown (sigma 0 vs sigma 0, independent noise draws)")
    p = os.path.join(DATA, "blindspot-nonorm.csv")
    if os.path.exists(p):
        nc = {}
        for r in rows(p):
            if r["plant"] != "step" or float(r["sigma"]) != 0.0 or float(r["noise_scale"]) <= 0:
                continue
            nc.setdefault(r["measure"], []).append(float(r["edge"]))
        nc = {m: max(v) / min(v) for m, v in nc.items() if len(v) > 1 and min(v)}
        worst = sorted(nc.items(), key=lambda kv: -kv[1])[:5]
        say("   worst 5 arms (a null ratio far from 1.0 would mean the ladder can")
        say("   manufacture discrimination out of noise alone):")
        for m, v in worst:
            say(f"     {m:<30}{v:.4f}")
        big = [m for m, v in nc.items() if v > 1.02]
        say(f"   arms with null ratio > 1.02: {len(big)} of {len(nc)}"
            + (f"  -> {', '.join(sorted(big))}" if big else ""))

    # ---- cost, flat bound excluding w0 (w0 skips the box entirely)
    say("\n-- COST: the flat bound, stated without w0")
    p = os.path.join(DATA, "cost-measures.csv")
    if os.path.exists(p):
        for prefix, label in (("tenengrad-", "magnitude"), ("tenengrad-sq-", "squared")):
            t = {}
            for r in rows(p):
                m = r["measure"]
                if not m.startswith(prefix):
                    continue
                tail = m[len(prefix):]
                if not tail.startswith("w") or not tail[1:].isdigit():
                    continue
                t[int(tail[1:])] = float(r["ms_per_frame_per_mpx_min"])
            nz = {w: v for w, v in t.items() if w > 0}
            if nz:
                say(f"   {label:<12} w1..w40: {min(nz.values()):.3f}..{max(nz.values()):.3f}"
                    f" ms/frame/Mpx  -> <= {max(nz.values()) / min(nz.values()):.3f}x  (a BOUND)")
                say(f"   {'':<12} w0 alone: {t.get(0, float('nan')):.3f}"
                    f"  (w0 skips the box entirely, which is why the with-w0 ratio is ~1.75x)")
        mg = next((float(r["ms_per_frame_per_mpx_min"]) for r in rows(p)
                   if r["measure"] == "tenengrad-w13"), None)
        sq11 = next((float(r["ms_per_frame_per_mpx_min"]) for r in rows(p)
                     if r["measure"] == "tenengrad-sq-w11"), None)
        sq13 = next((float(r["ms_per_frame_per_mpx_min"]) for r in rows(p)
                     if r["measure"] == "tenengrad-sq-w13"), None)
        if mg and sq11 and sq13:
            say(f"\n   COMBINED cost of the recommendation vs the shipped operator:")
            say(f"     tenengrad-w13    (shipped)  {mg:.3f} ms/frame/Mpx   1.000x")
            say(f"     tenengrad-sq-w13            {sq13:.3f}              {sq13 / mg:.3f}x")
            say(f"     tenengrad-sq-w11 (new opt)  {sq11:.3f}              {sq11 / mg:.3f}x")

    with open(os.path.join(DATA, "m42-uncertainty.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(OUT) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
