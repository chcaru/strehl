"""Independent re-check of M15's headline numbers.

Deliberately NOT sharing code with m15_analyse.py: different CSV reader,
different grouping, different regret loop. If this disagrees with
data/analysis.txt, one of the two is wrong and the report is not safe.

    python verify_headline.py
"""
import csv
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def excess_by(paths):
    """(width, stack, geom, step, window) -> [excess_dn per seed]"""
    acc = defaultdict(list)
    for p in paths:
        for r in load(p):
            geom = re.split(r"[@]", r["shape"])[0]
            win = int(re.match(r"tenengrad-w(\d+)$", r["measure"]).group(1))
            key = (int(r["width"]), r["stack"], geom, int(r["step"]), win)
            acc[key].append(float(r["excess_dn"]))
    return acc


def mean(xs):
    return sum(xs) / len(xs)


def main():
    data = os.path.join(HERE, "data")
    m13 = os.path.join(HERE, "..", "m13-window-depth", "data")
    fails = []

    def check(name, got, want, tol=5e-4):
        ok = abs(got - want) <= tol if isinstance(want, float) else got == want
        print(f"  {'OK ' if ok else 'BAD'}  {name:<52} got {got!r:>12}  want {want!r}")
        if not ok:
            fails.append(name)

    # ---- Gate A, straight off M13's committed bytes -----------------------
    print("Gate A on M13's committed CSVs (width 1, its 20-window ladder, its 3 seeds)")
    M13_LADDER = {0, 1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13, 15, 17, 18, 20, 23, 26, 33, 40}
    acc = excess_by([os.path.join(m13, f"edge-{s}.csv") for s in ("109MSDCF", "119MSDCF")])
    for tag, keep, want_w, want_mean, want_worst in (
            ("step>0", lambda st: st > 0, 13, 3.171, 12.111),
            ("step=0", lambda st: st == 0, 40, 0.000, 0.000)):
        cells = defaultdict(dict)
        for (g, stack, geom, step, win), vs in acc.items():
            if g != 1 or win not in M13_LADDER or not keep(step):
                continue
            cells[(stack, geom, step)][win] = mean(vs)
        per_w_mean, per_w_worst = defaultdict(list), defaultdict(list)
        for c, d in cells.items():
            lo = min(d.values())
            for w, v in d.items():
                per_w_mean[w].append(v - lo)
                per_w_worst[w].append(v - lo)
        bm = min(per_w_mean, key=lambda w: mean(per_w_mean[w]))
        bw = min(per_w_worst, key=lambda w: max(per_w_worst[w]))
        check(f"{tag}: n cells", len(cells), 30 if tag == "step>0" else 6)
        check(f"{tag}: argmin mean regret window", bm, want_w)
        check(f"{tag}: argmin mean regret value", round(mean(per_w_mean[bm]), 3), want_mean)
        if tag == "step>0":
            check(f"{tag}: argmin worst regret window", bw, want_w)
            check(f"{tag}: argmin worst regret value", round(max(per_w_worst[bw]), 3), want_worst)

    # ---- the M15 headline -------------------------------------------------
    print("\nM15 surface headline (24-window ladder, 5 seeds, 30 step>0 cells)")
    acc = excess_by([os.path.join(data, f"edge-{s}.csv") for s in ("109MSDCF", "119MSDCF")])
    check("total measurements", sum(len(v) for v in acc.values()), 38880)
    want_wstar = {1: 13, 3: 14, 5: 13, 9: 13, 13: 14, 17: 14, 25: 13, 33: 14, 49: 8}
    want_d13 = {1: 0.000, 3: 0.033, 5: 0.000, 9: 0.000, 13: 0.080,
                17: 0.050, 25: 0.000, 33: 0.121, 49: 0.551}
    for g in sorted(want_wstar):
        cells = defaultdict(dict)
        for (gg, stack, geom, step, win), vs in acc.items():
            if gg == g and step > 0:
                cells[(stack, geom, step)][win] = mean(vs)
        per_w = defaultdict(list)
        for d in cells.values():
            lo = min(d.values())
            for w, v in d.items():
                per_w[w].append(v - lo)
        bm = min(per_w, key=lambda w: mean(per_w[w]))
        d13 = mean(per_w[13]) - mean(per_w[bm])
        check(f"g={g}: n cells", len(cells), 30)
        check(f"g={g}: w*", bm, want_wstar[g])
        check(f"g={g}: Delta13", round(d13, 3), want_d13[g])

    # ---- the null stratum is a plateau, not a turnover --------------------
    print("\nNull stratum: regret at the w40 endpoint (must stay ~0 at every width)")
    for g in sorted(want_wstar):
        cells = defaultdict(dict)
        for (gg, stack, geom, step, win), vs in acc.items():
            if gg == g and step == 0:
                cells[(stack, geom, step)][win] = mean(vs)
        regs = [d[40] - min(d.values()) for d in cells.values()]
        check(f"g={g}: mean regret at w40 (step=0) < 0.01 DN",
              round(mean(regs), 4) < 0.01, True)

    print()
    if fails:
        print(f"*** {len(fails)} DISAGREEMENTS: {fails}")
        sys.exit(1)
    print("all headline numbers reproduce through a disjoint code path.")


if __name__ == "__main__":
    main()
