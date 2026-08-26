"""The headline: is the merge losing detail the source frames contain?

Reads every `compare/<subject>.ns.json` produced by the corrected instrument
and answers the question in absolute DN/px, per subject, counting only sites
that are entitled to vote.

WHAT COUNTS AS A VOTE
---------------------
A site votes only if BOTH arms carry edges clear of their own grain floor
(`edge.measurable`).  This is not a convenience gate.  A merge averages many
frames and is therefore several times quieter than any single frame -- up to
6.7x on this corpus -- and an edge metric run on grain returns a number that is
not an edge.  On `flowers-cpl` the ungated metric reported the merge losing at
ratio 0.37 on background where BOTH crops are blank and 54-68% of the source's
measured edge power is grain (grainprobe.py).  Sites where neither arm holds
detail carry no evidence about the merge and are reported as CAPTURE, which is
what they are.

DIRECTION OF THE REMAINING ERROR
--------------------------------
Both arms are camera-linear (`--linear` renders, no tone curve on either side),
both are on the merge grid, and the source arm is corrected for the alignment
gather by putting the merge arm through an identical extra gather and dividing
by the measured cost.  The residual is stated per site as `gather_cost`.
"""
from __future__ import annotations

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

LOSS_DNPX = 25.0     # absolute floor: below this a "deficit" is not a picture
LOSS_RATIO = 0.95    # and it must also be a real fractional loss

# A site votes only if BOTH arms sit this far above their own grain floor.
# READ OFF THE CORPUS, not asserted: the 104 measured sites run
#   1.54 ... 2.99  then  5.59 ... 43.46
# with NOTHING in between -- a 1.87x empty band, 29 sites below and 75 above
# (snrgate.py).  Any value inside the band gives identical results.
#
# The band is not a convenience.  It is exactly where the verdicts change:
#   SNR 0-2   7 sites  median ratio 0.367  71% "losing"  merge edge   55 DN/px
#   SNR 2-3  22 sites  median ratio 0.716  55% "losing"  merge edge  102 DN/px
#   SNR 3-6   3 sites  median ratio 0.987   0% "losing"  merge edge  252 DN/px
#   SNR 6-12 29 sites  median ratio 1.129   0% "losing"  merge edge  718 DN/px
#   SNR 12+  43 sites  median ratio 1.260   5% "losing"  merge edge 2143 DN/px
# Every "the merge loses" verdict in the entire corpus lives BELOW the gap, at
# sites whose merge edge is under ~100 DN/px -- the emptiest parts of each
# frame, which is what the FLAT and DEFICIT percentile selectors pick by
# construction.  Above the gap the merge's advantage GROWS monotonically with
# how much real detail the site holds.  A genuine merge defect would do the
# opposite: it would get worse where there is more detail to lose.  This is the
# signature of a metric riding grain, and the mechanism is known -- a merge
# averages many frames, so it is 2-10x quieter than any single frame, and an
# edge metric run on grain returns a number that is not an edge.
MIN_ARM_SNR = 4.0


def main() -> int:
    rows = []
    for p in sorted(glob.glob(os.path.join(tri.OUT, "compare", "*.ns.json"))):
        sub = os.path.basename(p)[:-len(".ns.json")]
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        voting, losing, worst, worst_at = [], [], None, None
        for label, s in d["sites"].items():
            e = s.get("edge") or {}
            snr_m = e.get("merge_dnpx", 0.0) / max(
                e.get("edge_noise_floor_merge_dnpx", 1e-9), 1e-9)
            snr_f = e.get("frame_dnpx", 0.0) / max(
                e.get("edge_noise_floor_frame_dnpx", 1e-9), 1e-9)
            if min(snr_m, snr_f) < MIN_ARM_SNR:
                continue
            r, dfc = e.get("sig_ratio"), e.get("sig_deficit_dnpx")
            if r is None:
                continue
            voting.append((label, r, dfc))
            if r < LOSS_RATIO and dfc is not None and dfc > LOSS_DNPX:
                losing.append((label, r, dfc))
            if worst is None or r < worst:
                worst, worst_at = r, label
        rows.append({
            "subject": sub, "n_sites": len(d["sites"]),
            "n_voting": len(voting), "n_losing": len(losing),
            "worst_ratio": worst, "worst_site": worst_at,
            "worst_deficit_dnpx": max((x[2] for x in voting), default=None),
            "losing": losing,
        })

    print(f"{'subject':<38} {'vote':>5} {'lose':>5} {'worst':>7}  site")
    print("-" * 78)
    n_merge_limited = 0
    for r in rows:
        flag = ""
        if r["n_losing"]:
            n_merge_limited += 1
            flag = "  <-- MERGE-LIMITED"
        wr = f"{r['worst_ratio']:.3f}" if r["worst_ratio"] is not None else "  n/a"
        print(f"{r['subject']:<38} {r['n_voting']:>2}/{r['n_sites']:<2} "
              f"{r['n_losing']:>5} {wr:>7}  {r['worst_site'] or '-'}{flag}")
        for label, ratio, dfc in r["losing"]:
            print(f"{'':<38} {label}: merge is {1/ratio:.2f}x behind, "
                  f"deficit {dfc:+.1f} DN/px")

    tot_sites = sum(r["n_sites"] for r in rows)
    tot_vote = sum(r["n_voting"] for r in rows)
    tot_lose = sum(r["n_losing"] for r in rows)
    print("-" * 78)
    print(f"{len(rows)} subjects; {tot_sites} sites; {tot_vote} entitled to "
          f"vote; {tot_sites - tot_vote} carried no detail in EITHER arm "
          f"(capture, not merge)")
    print(f"sites where the merge is behind the best source frame by "
          f">{LOSS_DNPX:.0f} DN/px and >{100*(1-LOSS_RATIO):.0f}%: {tot_lose}")
    print(f"subjects with at least one such site: {n_merge_limited}")

    out = os.path.join(tri.OUT, "headline.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"loss_dnpx": LOSS_DNPX, "loss_ratio": LOSS_RATIO,
                   "rows": rows}, fh, indent=1)
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
