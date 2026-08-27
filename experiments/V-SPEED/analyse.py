"""Aggregate V-SPEED timing records.

Reads C:\\dev\\strehl-out\\V-SPEED\\timings-<tag>.jsonl and reports, per
(subject, stage): the cold run (lowest round index), then median / min / max /
spread over the WARM runs (every later round).

`--compare A B --stage S` prints the shift in stage S's warm median between two
tags, which is how the planted-delay commissioning is read.
"""

import argparse
import json
import os
import statistics
from collections import defaultdict

ROOT = r"C:\dev\strehl-out\V-SPEED"


def load(tag):
    path = os.path.join(ROOT, f"timings-{tag}.jsonl")
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def group(recs):
    g = defaultdict(list)
    for r in recs:
        g[(r["subject"], r.get("mode", "srgb"), r["stage"])].append(r)
    for v in g.values():
        v.sort(key=lambda r: r["round"])
    return g


def summarise(recs, drop_first=True):
    out = {}
    for key, rs in group(recs).items():
        bad = [r for r in rs if r["rc"] != 0]
        cold = rs[0]["wall_s"] if rs else None
        warm = [r["wall_s"] for r in (rs[1:] if drop_first else rs)]
        out[key] = {
            "n_total": len(rs),
            "frames": rs[0]["frames"],
            "cold_s": cold,
            "warm_n": len(warm),
            "warm_median_s": statistics.median(warm) if warm else None,
            "warm_min_s": min(warm) if warm else None,
            "warm_max_s": max(warm) if warm else None,
            "warm_spread_s": (max(warm) - min(warm)) if warm else None,
            "warm_spread_pct": (100.0 * (max(warm) - min(warm)) / statistics.median(warm))
            if warm and statistics.median(warm)
            else None,
            "nonzero_rc": [r["rc"] for r in bad],
            "runs": [(r["round"], round(r["wall_s"], 3), r["rc"]) for r in rs],
        }
    return out


def show(tag, drop_first=True):
    s = summarise(load(tag), drop_first)
    print(f"\n=== {tag} (warm = all rounds after the first) ===")
    hdr = f"{'subject':<14}{'mode':<8}{'stage':<13}{'n':>3}{'cold':>9}{'med':>9}{'min':>9}{'max':>9}{'spread%':>9}  rc"
    print(hdr)
    print("-" * len(hdr))
    for (subj, mode, stage), v in sorted(s.items()):
        print(
            f"{subj:<14}{mode:<8}{stage:<13}{v['n_total']:>3}"
            f"{v['cold_s']:>9.2f}"
            f"{(v['warm_median_s'] or 0):>9.2f}"
            f"{(v['warm_min_s'] or 0):>9.2f}"
            f"{(v['warm_max_s'] or 0):>9.2f}"
            f"{(v['warm_spread_pct'] or 0):>9.1f}"
            f"  {v['nonzero_rc'] if v['nonzero_rc'] else 'ok'}"
        )
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--compare", nargs=2)
    ap.add_argument("--expect", type=float, default=None)
    ap.add_argument("--tol", type=float, default=0.5)
    ap.add_argument("--no-drop-first", action="store_true")
    args = ap.parse_args()

    tables = {t: show(t, not args.no_drop_first) for t in args.tags}

    if args.compare:
        a, b = args.compare
        print(f"\n=== shift {a} -> {b} (warm median) ===")
        keys = sorted(set(tables[a]) | set(tables[b]))
        ok = True
        for k in keys:
            va, vb = tables[a].get(k), tables[b].get(k)
            if not (va and vb):
                continue
            d = vb["warm_median_s"] - va["warm_median_s"]
            verdict = ""
            if args.expect is not None:
                # a stage is EXPECTED to move only if it carried the plant
                pass
            print(f"  {k[0]:<14}{k[1]:<8}{k[2]:<13} {va['warm_median_s']:8.2f} -> {vb['warm_median_s']:8.2f}   delta {d:+8.2f} s {verdict}")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
