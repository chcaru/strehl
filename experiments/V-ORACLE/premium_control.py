"""Does the selection premium contaminate V-ORACLE's own statistic?

ORCH broadcast (facts 1843-1845): the max-of-N order statistic on a noisy focus
measure manufactures noise power, 24.82x at N=19 and 240.70x at N=79.  My source
arm is

    contrast(b,t) = max_k Var(b,k,t) - quantile_0.25_k Var(b,k,t)

which contains a max over N frames.  So the premium applies to MY instrument and
I have to establish what it does to my published conclusion rather than assume the
common-mode argument covers it.  It does not: common-mode cancellation removes the
noise term's MEAN, it does not remove the upward bias of taking a maximum.

Two questions, opposite consequences:

1. THE RATIO (verdict (a) vs (b)).  The source arm is a max over N frames; the
   merge arm is one image with no max.  So the premium inflates the SOURCE arm
   only, drives the ratio UP, and biases the rule toward (b) -- toward finding a
   merge defect.  I published (a).  The bias is therefore ADVERSE to my
   conclusion and can only have made (a) harder to reach.  This test measures how
   big it is, so the claim is quantified rather than asserted.

2. STUCK% (the corpus ranking).  This one is not obviously safe, so it gets a
   real control.  stuck% counts tiles whose through-focus curve is maximal at a
   BOUNDARY frame.  Under pure noise the argmax location is uniform over the K
   frames, so the null expectation is about 2/K -- 1.1% at K=176, not 58.7%.
   The empirical null is measured here on this subject's own noise-dominated
   tiles, which is stronger than the analytic argument because it uses the real
   noise, the real K and the real band decomposition.

Usage:  python premium_control.py [--subject flowers-cpl] [--band 2]
"""
from __future__ import annotations

import argparse
import os

import numpy as np

import ora


def analyse(subject: str, b: int):
    """Return (K, detail stuck%, flat stuck%, ndetail, nflat) for one subject."""
    p = os.path.join(ora.OUT, "stageA", subject + ".npz")
    if not os.path.exists(p):
        return None
    A = np.load(p)
    con, var_k, ks = A["contrast"], A["var_k"], A["frames"]
    K = len(ks)
    cb = con[b]
    p10 = float(np.nanquantile(cb, 0.10))
    detail = cb > 10.0 * max(p10, 1e-9)
    flat = cb <= max(p10, 1e-9) * 2.0
    cur = var_k[:, b].astype(float)
    kpk = np.argmax(cur, axis=0)
    floor = np.quantile(cur, 0.25, axis=0)
    pk = np.max(cur, axis=0)
    endi = np.where(kpk <= (K - 1 - kpk), 0, K - 1)
    vend = np.take_along_axis(cur, endi[None], 0)[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        rise = (pk - vend) / np.maximum(pk - floor, 1e-9)
    stuck = rise < 0.10
    sd = 100.0 * float(stuck[detail].mean()) if detail.any() else float("nan")
    sf = 100.0 * float(stuck[flat].mean()) if flat.any() else float("nan")
    return K, sd, sf, int(detail.sum()), int(flat.sum())


def run_all(b: int) -> int:
    """The decisive control for deliverable 4a.

    stuck% fires on 38% of flowers-cpl's NO-DETAIL tiles.  Two explanations:
      (i)  flowers-cpl carries a whole-frame monotone trend (illumination or
           level drift across the sweep) that makes every tile read 'stuck',
           in which case its headline 58.7% is inflated by that trend and the
           ranking is partly measuring drift, not capture gap;
      (ii) the flat-tile null is high on every subject, in which case it is a
           property of the criterion and the DIFFERENCE between subjects still
           carries the signal.
    Only the corpus can tell these apart, so the corpus is what gets measured.
    'excess' = detail stuck% - flat stuck%, the drift-controlled statistic.
    """
    subs = sorted(x[:-4] for x in os.listdir(os.path.join(ora.OUT, "stageA"))
                  if x.endswith(".npz") and "__" not in x)
    rows = []
    for s in subs:
        r = analyse(s, b)
        if r is not None:
            rows.append((s, *r))
    rows.sort(key=lambda t: -(t[2] - t[3]))
    hd = (f"{'subject':<38}{'K':>5}{'detail%':>9}{'flat%':>8}{'excess':>9}"
          f"{'ndet':>7}{'nflat':>7}")
    print(f"=== flat-tile null for stuck%, all subjects, band {b} ===")
    print("'flat%' is stuck% measured on tiles with NO detail.  A subject whose")
    print("flat% is high has a whole-frame trend across the sweep, and that trend")
    print("inflates its detail% too.  'excess' subtracts it.\n")
    print(hd)
    print("-" * len(hd))
    for s, K, sd, sf, nd, nf in rows:
        print(f"{s:<38}{K:>5}{sd:>9.1f}{sf:>8.1f}{sd - sf:>9.1f}{nd:>7}{nf:>7}")
    fl = np.array([r[3] for r in rows], float)
    print(f"\ncorpus flat% : median {np.nanmedian(fl):.1f}, max {np.nanmax(fl):.1f}")
    print(f"subjects counted: {len(rows)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="flowers-cpl")
    ap.add_argument("--band", type=int, default=2)
    ap.add_argument("--all", action="store_true",
                    help="flat-tile null across every subject")
    args = ap.parse_args()
    if args.all:
        return run_all(args.band)
    b = args.band

    A = np.load(os.path.join(ora.OUT, "stageA", args.subject + ".npz"))
    con, var_k, ks = A["contrast"], A["var_k"], A["frames"]
    K = len(ks)
    cb = con[b]

    # detail = the absolute (null-referenced) definition used by the report
    p10 = float(np.nanquantile(cb, 0.10))
    detail = cb > 10.0 * max(p10, 1e-9)
    flat = cb <= max(p10, 1e-9) * 2.0

    print(f"=== selection-premium control :: {args.subject} band {b} ===")
    print(f"K = {K} frames; {detail.sum()} detail tiles, {flat.sum()} "
          f"noise-dominated tiles, {cb.size} total\n")

    # ---- Q2: is stuck% a premium artefact? --------------------------------
    # This MUST use the statistic the ranking actually ships (rise < 0.10), not
    # a proxy.  My first version of this control tested raw argmax-at-boundary,
    # which is a weaker and different quantity, and it would have condemned the
    # ranking for a property the ranking does not use.  Testing a proxy for the
    # shipped statistic is the same error as testing a report for the presence
    # of a word instead of the claim it certifies.
    cur = var_k[:, b].astype(float)                 # (K, nr, nc)
    kpk = np.argmax(cur, axis=0)
    floor = np.quantile(cur, 0.25, axis=0)
    pk = np.max(cur, axis=0)
    endi = np.where(kpk <= (K - 1 - kpk), 0, K - 1)
    vend = np.take_along_axis(cur, endi[None], 0)[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        rise = (pk - vend) / np.maximum(pk - floor, 1e-9)
    at_edge = rise < 0.10                            # the shipped criterion
    argmax_edge = (kpk == 0) | (kpk == K - 1)        # the weaker proxy, for contrast

    null_expect = 100.0 * 2.0 / K
    s_detail = 100.0 * float(at_edge[detail].mean()) if detail.any() else np.nan
    s_flat = 100.0 * float(at_edge[flat].mean()) if flat.any() else np.nan
    p_detail = 100.0 * float(argmax_edge[detail].mean()) if detail.any() else np.nan
    p_flat = 100.0 * float(argmax_edge[flat].mean()) if flat.any() else np.nan

    print("Q2  stuck% vs its empirical noise null   [shipped criterion: rise<0.10]")
    print(f"  analytic null (argmax uniform over K):      {null_expect:6.2f}%")
    print(f"  measured on noise-dominated tiles:          {s_flat:6.2f}%   "
          f"<- the empirical null, real noise and real K")
    print(f"  measured on detail tiles (the published #): {s_detail:6.2f}%")
    if np.isfinite(s_flat) and s_flat > 0:
        print(f"  separation: detail is {s_detail / s_flat:.1f}x the empirical "
              f"null")
    else:
        print("  separation: the empirical null is 0.00% -- no noise-dominated "
              "tile satisfies the shipped criterion at all")
    print(f"  [weaker proxy argmax-at-boundary, NOT used by the ranking: "
          f"detail {p_detail:.2f}% vs flat {p_flat:.2f}%]")
    safe = (s_detail > 5 * max(s_flat, null_expect)) if np.isfinite(s_detail) else False
    verdict2 = ("SAFE: stuck% on detail tiles is far above what the premium "
                "can manufacture" if safe
                else "NOT SAFE: stuck% is within reach of the noise null")
    print(f"  -> {verdict2}\n")

    # ---- Q1: how much does the max inflate the source arm? ----------------
    # Split the frames into two independent halves.  The premium is the excess of
    # a max taken over N frames relative to a max taken over N/2, on the same
    # scene: the scene content is identical, only the number of draws differs.
    h1, h2 = cur[0::2], cur[1::2]
    def contrast_of(c):
        return np.max(c, axis=0) - np.quantile(c, 0.25, axis=0)
    full = contrast_of(cur)
    half = 0.5 * (contrast_of(h1) + contrast_of(h2))
    with np.errstate(divide="ignore", invalid="ignore"):
        infl = full / np.maximum(half, 1e-9)

    print(f"Q1  premium inflation of the SOURCE arm, N={K} vs N={K // 2}")
    for name, msk in (("detail tiles", detail), ("noise-dominated tiles", flat)):
        if not msk.any():
            continue
        v = infl[msk]
        print(f"  {name:<24} median {np.median(v):.3f}  p90 {np.percentile(v, 90):.3f}"
              f"  max {v.max():.3f}")
    print("  direction: this inflates the SOURCE arm only (the merge arm has no")
    print("  max over frames), so it pushes the ratio UP, toward verdict (b).")
    print("  The published verdict is (a), reached DESPITE this bias.\n")

    print("CONCLUSION")
    print("  The premium is present in my statistic and its sign is adverse to")
    print("  my own conclusion: it can only have made a merge defect easier to")
    print("  declare, and none was declared.")
    if np.isfinite(s_flat) and s_flat > 0:
        print(f"  stuck%, which carries the corpus ranking, sits "
              f"{s_detail / s_flat:.0f}x above its empirical noise null.")
    else:
        print("  stuck%, which carries the corpus ranking, has an empirical")
        print("  noise null of 0.00%: no noise-dominated tile reaches the")
        print("  shipped criterion, so it cannot be manufactured by the premium.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
