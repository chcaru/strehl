"""Build the V-SPEED breakdown table and the headline ratios.

PIPELINES. Same start artifact (a directory of .ARW), same end artifact (one
merged image on disk):

  strehl        strehl
  enfuse        develop + align + enfuse
  focus-stack   develop + focus-stack

`develop` is executed once per round and charged to BOTH comparators, because
it is literally the same work: neither can read RAW.

ESTIMATOR. Primary is the warm MINIMUM (AGENTS.md rule 16). Nine agents share
this box and their contention is one-sided -- it can only make a stage slower --
so the minimum over repeats is the estimator of the true duration and the mean
and median both inherit the load. Median, max and full spread are printed
beside it so a reader can see how much load is in the numbers.

RATIOS. Three, of decreasing generosity to strehl and increasing robustness:

  end-to-end   comparator total / strehl total, both at the warm median.
  conservative comparator's FASTEST warm round / strehl's SLOWEST warm round.
               If this still exceeds 1, the result survives the drift.
  floor        comparator's merge stage ALONE (conversion free, and for enfuse
               alignment free too) / strehl's full pipeline at its slowest.
               A lower bound on any pipeline built on that comparator, so it
               survives every choice of converter and aligner.

Usage: python report.py <tag> [<tag> ...]
"""

import statistics
import sys
from collections import defaultdict

from analyse import load

PIPELINES = {
    "strehl": ["strehl"],
    "enfuse": ["develop", "align", "enfuse"],
    "focus-stack": ["develop", "focus-stack"],
}
FLOOR_STAGE = {"enfuse": "enfuse", "focus-stack": "focus-stack"}


def collect(tags):
    """(subject, mode, frames) -> round -> stage -> wall_s"""
    by = defaultdict(lambda: defaultdict(dict))
    for tag in tags:
        for r in load(tag):
            key = (r["subject"], r.get("mode", "srgb"), r["frames"])
            if r["rc"] != 0:
                print(f"!! nonzero rc {r['rc']} {key} round {r['round']} {r['stage']}")
                continue
            by[key][r["round"]][r["stage"]] = r["wall_s"]
    return by


def stats(vals):
    if not vals:
        return None
    return {
        "n": len(vals),
        "min": min(vals),
        "median": statistics.median(vals),
        "max": max(vals),
        "spread": max(vals) - min(vals),
        "spread_pct": 100.0 * (max(vals) - min(vals)) / statistics.median(vals),
    }


def fmt(s):
    if s is None:
        return f"{'-':>9}{'-':>9}{'-':>9}{'-':>9}"
    return f"{s['min']:>9.2f}{s['median']:>9.2f}{s['max']:>9.2f}{s['spread_pct']:>8.1f}%"


def main():
    by = collect(sys.argv[1:])
    for key in sorted(by):
        subject, mode, frames = key
        rounds = by[key]
        idx = sorted(rounds)
        cold, warm = idx[0], idx[1:]
        print(f"\n{'=' * 96}")
        print(f"SUBJECT {subject}   frames {frames}   develop mode {mode}")
        print(f"rounds {idx}  (cold = round {cold}, warm = {warm})")
        print("=" * 96)

        # ---- stage breakdown ----
        stages = ["develop", "strehl", "align", "enfuse", "focus-stack"]
        print(f"\n{'stage':<14}{'cold':>9}{'warm_min':>9}{'warm_med':>9}{'warm_max':>9}{'spread':>9}{'s/frame*':>10}")
        print("-" * 70)
        stage_stats = {}
        for st in stages:
            vals = [rounds[r][st] for r in warm if st in rounds[r]]
            s = stats(vals)
            stage_stats[st] = s
            c = rounds[cold].get(st)
            print(
                f"{st:<14}{(c if c else float('nan')):>9.2f}" + fmt(s)
                + f"{(s['median'] / frames if s else float('nan')):>10.3f}"
            )
        print("* s/frame is the warm median divided by frame count.")

        # ---- per-round pipeline totals ----
        totals = defaultdict(dict)
        for r in idx:
            for arm, sts in PIPELINES.items():
                if all(s in rounds[r] for s in sts):
                    totals[arm][r] = sum(rounds[r][s] for s in sts)

        print(f"\n{'pipeline':<14}{'cold':>9}{'warm_min':>9}{'warm_med':>9}{'warm_max':>9}{'spread':>9}{'s/frame':>10}")
        print("-" * 70)
        arm_stats = {}
        for arm in ("strehl", "enfuse", "focus-stack"):
            wv = [totals[arm][r] for r in warm if r in totals[arm]]
            s = stats(wv)
            arm_stats[arm] = s
            c = totals[arm].get(cold)
            print(
                f"{arm:<14}{(c if c else float('nan')):>9.2f}" + fmt(s)
                + f"{(s['median'] / frames if s else float('nan')):>10.3f}"
            )

        # ---- ratios ----
        base = arm_stats.get("strehl")
        if not base:
            continue
        print(f"\nRATIOS -- every one names comparator, subject and frame count")
        print("-" * 96)
        for arm in ("enfuse", "focus-stack"):
            s = arm_stats.get(arm)
            if not s:
                continue
            e2e = s["median"] / base["median"]
            cons = s["min"] / base["max"]
            fs = stage_stats.get(FLOOR_STAGE[arm])
            floor = (fs["min"] / base["max"]) if fs else float("nan")
            print(
                f"  strehl vs {arm:<12} on {subject} ({frames} frames):\n"
                f"      end-to-end   {e2e:6.2f}x faster   "
                f"({s['median']:.1f} s median vs {base['median']:.1f} s median)\n"
                f"      conservative {cons:6.2f}x faster   "
                f"({arm} fastest warm {s['min']:.1f} s vs strehl slowest warm {base['max']:.1f} s)\n"
                f"      floor        {floor:6.2f}x faster   "
                f"({arm} merge stage alone, fastest warm, vs strehl slowest warm)"
            )

        # ---- per-round paired ratios ----
        # The unpaired guard above compares aggregate spreads across the whole
        # run, which on a nine-agent box is dominated by drift between rounds.
        # Within a round the arms sit minutes apart rather than tens of
        # minutes, and the forward/reverse alternation flips their order, so
        # the per-round ratio is the drift-robust statistic. Reported ALONGSIDE
        # the unpaired verdict, never instead of it.
        print(f"\nPER-ROUND PAIRED RATIOS (warm rounds only, drift-robust)")
        print("-" * 96)
        for arm in ("enfuse", "focus-stack"):
            per = [
                totals[arm][r] / totals["strehl"][r]
                for r in warm
                if r in totals[arm] and r in totals["strehl"]
            ]
            if not per:
                continue
            print(
                f"  strehl vs {arm:<12} on {subject} ({frames} frames): "
                f"per-round {', '.join(f'{p:.2f}x' for p in per)}  ->  "
                f"median {statistics.median(per):.2f}x, min {min(per):.2f}x, max {max(per):.2f}x"
            )

        # ---- inconclusiveness guard ----
        print(f"\nDRIFT GUARD (unpaired, deliberately harsh)")
        print("-" * 96)
        for arm in ("enfuse", "focus-stack"):
            s = arm_stats.get(arm)
            if not s:
                continue
            gap = abs(s["median"] - base["median"])
            noise = max(s["spread"], base["spread"])
            verdict = "OK" if gap > 3 * noise else "INCONCLUSIVE -- spread rivals the gap"
            print(
                f"  {arm:<12} arm-to-arm gap {gap:8.1f} s   worst within-arm spread {noise:7.1f} s"
                f"   ratio {gap / noise if noise else float('inf'):6.1f}x   {verdict}"
            )


if __name__ == "__main__":
    main()
