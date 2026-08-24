"""M103b: per-frame placement error, and whether ANY scalar gain can fix the solve.

WHY
---
Every bar M103 has passed so far -- B3's 150.3 -> 2.9 plane px, the 52.4% ->
105.4% recovery, M97's residual, M97b's arm ladder -- is an END-TO-END
measurement between frame 0 and frame 298. `src/curvature.py` has just shown
that end-to-end agreement does not imply per-frame agreement:

    shipped    r(48) = 1.0242 ... r(298) = 0.5239   (CV 21.8%)
    corrected  r(48) = 3.3046 ... r(298) = 1.0544   (CV 37.1%)

The two solves disagree with each other about mid-stack placement by ~3x while
agreeing about the endpoint to within 5%. Both cannot be right, and an
endpoint-only bar cannot tell them apart.

The merge does not care about the endpoint. It gathers each frame at its own
`a_k`, so what reaches the photograph is the PER-FRAME placement error. This
script measures that, in plane px at the corner, which is the unit M97, M86 and
M103's own B3 all quote.

It also answers the orchestrator's actual question -- "ship the gain correction"
-- by testing whether any single multiplier can do the job:

    arm                     definition
    shipped                 as it ships today
    gain-endpoint           shipped * 1/r(298)   -- matches the endpoint exactly
    gain-mean               shipped * 1/mean(r)  -- best uniform fit
    gain-best               shipped * g, with g chosen to MINIMISE mean |error|
                            (a ceiling: no scalar gain can beat this)
    corrected               M103's iterated_wide solve
    truth                   the independent RAW ladder

`gain-best` is the important one. If even the optimally chosen scalar leaves a
large per-frame error, then no gain correction is shippable and the finding is
about the shape of the solve, not its amplitude.

CONTROLS
  PLACEBO   truth vs truth -> 0.00 px at every rung.
  POSITIVE  truth * 0.543 (a genuinely uniform shrinkage) -> `gain-best` MUST
            recover it to ~0 px, proving the gain search works and that a large
            residual on the real solve is a property of the solve rather than of
            the search.
  Per discipline 615 both act on the log-scale track only, downstream of all
  correlation, so neither perturbs the mechanism being measured through.

USAGE
  python placement.py <truth-dense.json> <shipped.txt> <corrected.txt> <out.json>
"""

import json
import math
import struct
import sys

import numpy as np

R_PLANE = 0.5 * float(np.hypot(3516.0, 2344.0))


def read_sidecar(path):
    out = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("strehl-"):
                continue
            p = line.split()
            if len(p) < 6 or p[1] not in ("placed", "held"):
                continue
            try:
                idx = int(p[0])
            except ValueError:
                continue
            a_re = struct.unpack(">d", bytes.fromhex(p[2]))[0]
            a_im = struct.unpack(">d", bytes.fromhex(p[3]))[0]
            m = math.hypot(a_re, a_im)
            if m > 0:
                out[idx] = math.log(m)
    return out


def err_px(track, truth, rungs, gain=1.0):
    """Per-rung |placement error| in plane px at the corner radius."""
    return np.array([abs(track[j] * gain - truth[j]) * R_PLANE
                     for j in rungs if j in track])


def best_gain(track, truth, rungs):
    """Scalar gain minimising MEAN |placement error|. Golden-section on a convex
    piecewise-linear objective; a coarse scan then a refine is ample here."""
    lo, hi = 0.2, 6.0
    best = (None, float("inf"))
    for _ in range(4):
        for g in np.linspace(lo, hi, 241):
            e = err_px(track, truth, rungs, g).mean()
            if e < best[1]:
                best = (float(g), float(e))
        span = (hi - lo) / 24.0
        lo, hi = max(0.01, best[0] - span), best[0] + span
    return best


def summarise(name, e):
    return {"arm": name, "mean_px": float(e.mean()), "max_px": float(e.max()),
            "median_px": float(np.median(e)), "rms_px": float(np.sqrt((e ** 2).mean()))}


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    truth_p, ship_p, corr_p, out_p = sys.argv[1:5]
    td = json.load(open(truth_p))
    ladder = {int(k): v for k, v in td["ladder"].items()}
    truth = {j: ladder[j]["ln"] for j in ladder}
    rungs = sorted(truth)
    ship = read_sidecar(ship_p)
    corr = read_sidecar(corr_p)

    r_end = ship[rungs[-1]] / truth[rungs[-1]]
    rs = [ship[j] / truth[j] for j in rungs if abs(truth[j]) >= 0.01]
    r_mean = float(np.mean(rs))

    g_ship, e_ship = best_gain(ship, truth, rungs)
    g_corr, e_corr = best_gain(corr, truth, rungs)

    arms = [
        ("shipped", err_px(ship, truth, rungs)),
        (f"gain-endpoint (x{1 / r_end:.3f})", err_px(ship, truth, rungs, 1 / r_end)),
        (f"gain-mean (x{1 / r_mean:.3f})", err_px(ship, truth, rungs, 1 / r_mean)),
        (f"gain-best (x{g_ship:.3f})", err_px(ship, truth, rungs, g_ship)),
        ("corrected (iterated_wide)", err_px(corr, truth, rungs)),
        (f"corrected + gain-best (x{g_corr:.3f})",
         err_px(corr, truth, rungs, g_corr)),
    ]

    print("Per-frame placement error against the independent RAW ladder,")
    print(f"plane px at the corner (R_PLANE = {R_PLANE:.1f} px), {len(rungs)} rungs.")
    print("The merge gathers each frame at its own a_k, so THIS is what reaches")
    print("the photograph -- not the end-to-end number every bar so far has used.")
    print()
    print(f"  {'arm':<32} {'mean':>8} {'median':>8} {'max':>8} {'rms':>8}")
    rows = []
    for name, e in arms:
        s = summarise(name, e)
        rows.append(s)
        print(f"  {name:<32} {s['mean_px']:>8.1f} {s['median_px']:>8.1f} "
              f"{s['max_px']:>8.1f} {s['rms_px']:>8.1f}")

    print()
    print("Per-rung detail (plane px):")
    print(f"  {'j':>5} {'truth_px':>9} {'shipped':>9} {'gain-best':>10} "
          f"{'corrected':>10}")
    for j in rungs:
        if j % 24 and j != rungs[-1]:
            continue
        tp = truth[j] * R_PLANE
        print(f"  {j:>5} {tp:>9.1f} "
              f"{(ship[j] - truth[j]) * R_PLANE:>+9.1f} "
              f"{(ship[j] * g_ship - truth[j]) * R_PLANE:>+10.1f} "
              f"{(corr[j] - truth[j]) * R_PLANE:>+10.1f}")

    # ---- controls --------------------------------------------------------
    e_pl = err_px(dict(truth), truth, rungs)
    pl_ok = e_pl.max() < 1e-9
    print(f"\nPLACEBO  truth vs truth: max {e_pl.max():.2e} px -> "
          f"{'PASS' if pl_ok else 'FAIL'}")

    uni = {j: truth[j] * 0.543 for j in rungs}
    g_uni, e_uni = best_gain(uni, truth, rungs)
    pos_ok = e_uni < 0.5
    print(f"POSITIVE truth x0.543: gain-best finds x{g_uni:.4f} "
          f"(true 1/0.543 = {1 / 0.543:.4f}), residual {e_uni:.3f} px -> "
          f"{'PASS' if pos_ok else 'FAIL'}")
    print("     (so the gain search CAN null a genuinely uniform shrinkage;")
    print("      a large gain-best residual on the real solve is the solve's")
    print("      shape, not the search failing)")

    json.dump({"R_PLANE": R_PLANE, "arms": rows,
               "best_gain_shipped": g_ship, "best_gain_corrected": g_corr,
               "control_placebo_max_px": float(e_pl.max()),
               "control_positive_gain": g_uni,
               "control_positive_residual_px": e_uni},
              open(out_p, "w"), indent=1)
    print(f"\nwrote {out_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
