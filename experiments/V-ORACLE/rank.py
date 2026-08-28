#!/usr/bin/env python3
"""Deliverable 4: rank all delivered masters by the merge-defect signature.

THE SIGNATURE BEING RANKED is 'tiles where the best available source frame
clearly beats the merge': tiles that (i) carry measurable resolvable structure
in the bracket, and (ii) where the merge delivered materially less of it than
the best single frame did, under BOTH resampling conventions.  A subject with
many such tiles had information and lost it.  A subject with none either merged
well or never captured the detail in the first place -- and those two are told
apart by the second column, which is the fraction of detail tiles whose focus
curve is still at its peak on a boundary frame.

TWO DETAIL DEFINITIONS ARE REPORTED, NOT ONE.  A ranking that depends on where
the detail threshold is drawn is a ranking of the threshold.
  'decile'  top 10% of the subject's own through-focus contrast (relative:
            adapts to subject contrast, but by construction always selects
            10% of tiles even on a subject with no detail anywhere).
  'null'    contrast > 10x the subject's own p10 contrast, which estimates the
            no-structure null for that subject (absolute: can legitimately
            select zero tiles, or most of them).
The headline uses 'null'; both are printed and disagreement is flagged.

EVERY SUBJECT IS COUNTED.  Subjects with no stage A or no stage B result are
listed under their own outcome and included in the total, so a subject that
could not be measured can never be read as a subject that passed.

Usage:  python rank.py [--band 2] [--thresh 1.25]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402


def analyse(subj, b, thresh):
    pA = os.path.join(ora.OUT, "stageA", subj + ".npz")
    pB = os.path.join(ora.OUT, "stageB", subj + ".npz")
    if not os.path.exists(pA):
        return "NO-STAGEA", None
    A = np.load(pA)
    con, var_k, ks = A["contrast"], A["var_k"], A["frames"]
    nr, nc = int(A["nr"]), int(A["nc"])
    c = con[b]
    p10 = float(np.nanquantile(c, 0.10))
    det = {"decile": c >= np.nanquantile(c, 0.90),
           "null": c > 10.0 * max(p10, 1e-9)}
    # Tiles with NO detail at all.  These are the drift control: whatever
    # fraction of THEM reads 'stuck' is what the criterion manufactures on this
    # subject from a whole-frame trend across the sweep (illumination or level
    # drift), with no focus signal available to produce it.
    flat = c <= max(p10, 1e-9) * 2.0

    # fraction of detail tiles whose focus curve never turned over inside the
    # bracket -- the capture-gap signature, measured independently of the merge
    cur = var_k[:, b]                       # (K, nr, nc)
    kpk = np.argmax(cur, axis=0)
    floor = np.quantile(cur, 0.25, axis=0)
    pk = np.max(cur, axis=0)
    K = cur.shape[0]
    endi = np.where(kpk <= (K - 1 - kpk), 0, K - 1)
    vend = np.take_along_axis(cur, endi[None], 0)[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        rise = (pk - vend) / np.maximum(pk - floor, 1e-9)

    if not os.path.exists(pB):
        return "NO-STAGEB", None
    B = np.load(pB)
    if "reg_ok" in B.files and not bool(B["reg_ok"]):
        # The master could not be put on the frames' grid.  A ratio map built on
        # a failed lock measures the misregistration, and it fails in the
        # direction of INVENTING a merge defect, so such a subject is refused a
        # rank rather than given a flattering or damning number.
        return "UNREGISTERED", None
    modes = [str(m) for m in B["modes"]]
    rats = [con[b] / np.maximum(B[f"{m}_sig"][b], 1e-9) for m in modes]
    both = np.all([r > thresh for r in rats], axis=0)
    # A tile can only "lose" if the merge actually has measurable signal there:
    # dividing by a merge signal that has been floored to ~0 produces ratios of
    # 1e14, which are a division artefact and not a merge defect.
    msig = np.max([B[f"{m}_sig"][b] for m in modes], axis=0)
    measurable = msig > 10.0 * max(p10, 1e-9)
    both &= measurable
    # The same guard MUST also gate the reported 'worst' and 'median' ratios.
    # It originally gated only the lose count, so a tile excluded from the
    # count as a division artefact could still supply the headline worst-case
    # number -- which is how dry-erase-marker-head-cpl reported a worst ratio
    # of 4.5e14.  A number that is excluded from the count as untrustworthy
    # cannot be trusted as the headline either.
    interior = np.zeros((nr, nc), bool)
    interior[1:-1, 1:-1] = True

    out = {"nr": nr, "nc": nc, "ntile": nr * nc, "nframes": int(A["nframes"]),
           "nused": len(ks), "reg": True}
    for name, d in det.items():
        n = int(d.sum())
        lose = d & both & interior
        r0 = np.where(d & interior & measurable, np.max(rats, axis=0), np.nan)
        out[name] = {
            "ndetail": n,
            "nlose": int(lose.sum()),
            "pct": 100.0 * lose.sum() / max(n, 1),
            "worst": float(np.nanmax(r0)) if np.isfinite(r0).any() else np.nan,
            "median": float(np.nanmedian(r0)) if np.isfinite(r0).any() else np.nan,
            "stuck": (100.0 * float(np.nanmean(rise[d] < 0.10))
                      if n else float("nan")),
        }
    out["edge_lose"] = int((both & ~interior & det["null"]).sum())
    out["stuck_flat"] = (100.0 * float(np.nanmean(rise[flat] < 0.10))
                         if flat.any() else float("nan"))
    out["nflat"] = int(flat.sum())
    return "OK", out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--band", type=int, default=2)
    ap.add_argument("--thresh", type=float, default=1.25)
    ap.add_argument("--minn", type=int, default=20,
                    help="minimum detail tiles before a subject may be ranked "
                         "on lose%%; below this the percentage is dominated by "
                         "its own denominator")
    args = ap.parse_args()
    subs = sorted(f[:-5] for f in os.listdir(ora.MASTERS) if f.endswith(".tiff"))

    rows, bad = [], []
    for s in subs:
        st, r = analyse(s, args.band, args.thresh)
        if st != "OK":
            bad.append((s, st))
        elif r["null"]["ndetail"] < args.minn:
            bad.append((s, "TOO-LITTLE-DETAIL"))
        else:
            rows.append((s, r))

    # ---------------------------------------------------------------- TABLE 1
    # The headline ranking uses stuck%, which is measured ENTIRELY on the frame
    # side.  It needs no master, no resampling convention, no cross-domain gain
    # and no registration, so none of those choices can move it.  It answers the
    # product question directly: RESHOOT-THIS (the sweep ran out before focus
    # did) versus RETOUCH-THIS.
    # Ranked by EXCESS, not by raw stuck%.  Raw stuck% is confounded: the
    # criterion also fires on tiles with no detail at all, on some subjects for
    # more than half of them, because a whole-frame trend across the sweep makes
    # the boundary frame the maximum without any focus signal being involved.
    # Subtracting each subject's own no-detail rate removes a confound that is
    # per-subject and cannot be removed by any global threshold.
    rows.sort(key=lambda t: -(t[1]["null"]["stuck"] - t[1]["stuck_flat"]))
    print(f"=== DELIVERABLE 4a: all {len(subs)} delivered masters ranked by the "
          f"CAPTURE-GAP signature (band {args.band}) ===")
    print("stuck%% = detail tiles whose through-focus curve is still AT ITS "
          "MAXIMUM on a\n         boundary frame, i.e. the bracket ended while "
          "the tile was still getting\n         sharper.  Frame-side only: no "
          "master, no registration, no resampling\n         choice enters it, "
          "so no such choice can move the ranking.")
    print("flat%%  = the same criterion on tiles with NO detail: what this "
          "subject's own\n         sweep-wide trend manufactures with no focus "
          "signal present.\nexcess = stuck%% - flat%%, the drift-controlled "
          "statistic.  THIS IS THE RANKING.\n")
    hd = (f"{'#':<3}{'subject':<38}{'frames':>9}{'detail':>8}{'stuck%':>9}"
          f"{'flat%':>8}{'excess':>9}")
    print(hd)
    print("-" * len(hd))
    for i, (s, r) in enumerate(rows):
        ex = r["null"]["stuck"] - r["stuck_flat"]
        print(f"{i + 1:<3}{s:<38}{r['nused']:>5}/{r['nframes']:<3}"
              f"{r['null']['ndetail']:>8}{r['null']['stuck']:>9.1f}"
              f"{r['stuck_flat']:>8.1f}{ex:>9.1f}")
    st_n = np.array([r["null"]["stuck"] for _, r in rows])
    st_d = np.array([r["decile"]["stuck"] for _, r in rows])
    ex_a = np.array([r["null"]["stuck"] - r["stuck_flat"] for _, r in rows])
    print(f"\ncorpus stuck%: median {np.median(st_n):.1f}, "
          f"max {st_n.max():.1f}")
    print(f"corpus excess: median {np.median(ex_a):.1f}, "
          f"max {ex_a.max():.1f} ({rows[0][0]})")
    npos = int((ex_a > 5.0).sum())
    print(f"subjects with excess > 5 points: {npos} of {len(rows)}")
    print(f"agreement between the two detail definitions: "
          f"r = {np.corrcoef(st_n, st_d)[0, 1]:.3f}")

    # ---------------------------------------------------------------- TABLE 2
    rows.sort(key=lambda t: -t[1]["null"]["pct"])
    print(f"\n=== DELIVERABLE 4b: the same masters ranked by the MERGE-DEFECT "
          f"signature (threshold {args.thresh}x) ===")
    print("lose%% = interior detail tiles where the best source frame beats the "
          "merge by more\n        than the threshold under BOTH resampling "
          "conventions, counting only tiles\n        where the merge itself has "
          "measurable signal.")
    print("'edge' = losing tiles on the outer tile ring, excluded from lose%% "
          "because the\n         master's crop and the frame's active area do "
          "not cover the same scene there.\n")
    hd = (f"{'#':<3}{'subject':<38}{'detail':>8}{'lose':>6}{'lose%':>8}"
          f"{'worst':>8}{'med':>7}{'edge':>6}{'decile lose%':>14}")
    print(hd)
    print("-" * len(hd))
    for i, (s, r) in enumerate(rows):
        n, d = r["null"], r["decile"]
        print(f"{i + 1:<3}{s:<38}{n['ndetail']:>8}{n['nlose']:>6}"
              f"{n['pct']:>8.2f}{n['worst']:>8.2f}{n['median']:>7.2f}"
              f"{r['edge_lose']:>6}{d['pct']:>14.2f}")
    pn = np.array([r["null"]["pct"] for _, r in rows])
    pd_ = np.array([r["decile"]["pct"] for _, r in rows])
    rc = float(np.corrcoef(pn, pd_)[0, 1])
    print(f"\ncorpus lose%: median {np.median(pn):.2f}, max {pn.max():.2f} "
          f"({rows[0][0]})")
    print(f"agreement between the two detail definitions: r = {rc:.3f}")
    if rc < 0.8:
        print("  !! THIS RANKING IS PARTLY A RANKING OF THE THRESHOLD.  The two\n"
              "     detail definitions disagree, so 4b must not be read as an\n"
              "     ordering of merge quality.  4a, which has no such\n"
              "     dependence, is the ranking to use.")

    # -------------------------------------------------------------- PARTITION
    print("\n-- outcome partition over all delivered masters --")
    counts = {"RANKED": len(rows)}
    for s, st in bad:
        counts[st] = counts.get(st, 0) + 1
    tot = 0
    for k in sorted(counts):
        print(f"  {k:20s} {counts[k]}")
        tot += counts[k]
    print(f"  {'TOTAL':20s} {tot}")
    for s, st in sorted(bad, key=lambda t: t[1]):
        print(f"    {st}: {s}")
    assert tot == len(subs), f"{tot} != {len(subs)}"
    print(f"partition check OK: {tot} == {len(subs)} masters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
