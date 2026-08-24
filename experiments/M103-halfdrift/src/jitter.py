"""M103 -- is the per-frame placement error e(j) SMOOTH or JITTERY in j?

The orchestrator's question, and it decides between two very different worlds:

  smooth  (increment << 1 px)  the error is a slowly varying geometric warp.
                               Detailed pixels are locally sharp and locally
                               displaced; the artifact lives at election
                               boundaries and the fix is global geometry.
  jittery (increment >= 1 px)  adjacent frames disagree, so any pixel electing
                               across that boundary tears, and the merge is
                               sampling an incoherent field.

Asked because fact 1393 measured n_eff = 1 wherever there is detail: a detailed
output pixel takes exactly ONE frame, so a placement error there cannot blur it,
only displace it. What then matters is not the magnitude of e(j) but its SPREAD
across frames elected by neighbouring pixels -- i.e. |de/dj|.

TWO ROUTES, DELIBERATELY. The first is what was asked; the second needs no truth
data, no fit and no free parameter, so it cannot be wrong in the way an
instrument of mine has already been wrong four times tonight.

  R1  first difference of the ERROR:  de(j) = ds(j) - dt(j)
      Needs the truth ladder, which exists at only 39 of 299 rungs, so the truth
      increment comes from a smooth fit. The fit is a modelling choice and is
      reported with its residual and repeated at three polynomial orders.

  R2  second difference of the SOLVE alone:  s(j+1) - 2s(j) + s(j-1)
      Truth-free, fit-free, parameter-free, and available at all 297 interior
      frames rather than 39.

WHY CURVATURE CANNOT CONTAMINATE R2 -- the key point, DERIVED.
C1 measured the real track departing its own straight chord by 46.1 plane px at
j = 200. For a smooth arc, departure-from-chord d over N frames implies a second
difference of about 8d/N^2 = 8 * 46.1 / 200^2 = **0.0092 px per frame squared**.
So a perfectly smooth track with the REAL breathing curvature contributes under
0.01 px to R2. Any second difference above ~0.01 px is therefore jitter and not
curvature, with two orders of magnitude of headroom. That margin is what makes
R2 trustworthy without a truth ladder, and control C below measures it rather
than assuming it.

GAUGE. Section 16.2 established that per-frame placement numbers are meaningless
without their gauge, because the same track reads 98.2 px referenced at frame 0
and 37.5 px at rung 144. **This statistic needs no gauge.** A whole-graph
constant offset cancels in a first difference and twice over in a second, so
every number below is gauge-invariant. It is the only number in this milestone
free of that caveat, and that is a property of the question, not a virtue of the
instrument.

CONTROLS
  A PLACEBO    a purely LINEAR track                -> exactly 0
  B POSITIVE   planted alternating +-0.5 px jitter  -> 4A = 2.00 px, recovered
  C SPECIFICITY a smooth track carrying the REAL    -> must stay ~0.01 px,
    (the important one)  breathing curvature           NOT be read as jitter
Control C is the analogue of the natural-smooth plant that finally made
`waxy.py` honest: without it, a statistic that reports curvature as jitter would
answer the orchestrator's question backwards, and confidently.

usage:
  python src/jitter.py <truth-dense.json> <solve.txt> <out.json>
"""

import json
import math
import struct
import sys

import numpy as np

R_PLANE = 0.5 * float(np.hypot(3516.0, 2344.0))
REFERENCE = 149  # the gauge bee-3-cpl's merge actually uses


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


def d2_px(track):
    """Second difference in plane px at the corner radius, all interior frames."""
    j = np.array(sorted(track))
    y = np.array([track[k] for k in j])
    contiguous = np.all(np.diff(j) == 1)
    d2 = (y[2:] - 2.0 * y[1:-1] + y[:-2]) * R_PLANE
    return j[1:-1], np.abs(d2), contiguous


def stats(v):
    return {
        "median_px": float(np.median(v)),
        "p90_px": float(np.percentile(v, 90)),
        "p99_px": float(np.percentile(v, 99)),
        "max_px": float(v.max()),
        "frac_ge_0p5": float((v >= 0.5).mean()),
        "frac_ge_1p0": float((v >= 1.0).mean()),
        "n": int(v.size),
    }


def row(name, v):
    s = stats(v)
    return ("  %-34s %8.4f %8.4f %8.4f %9.4f %8.3f %8.3f"
            % (name, s["median_px"], s["p90_px"], s["p99_px"], s["max_px"],
               s["frac_ge_0p5"], s["frac_ge_1p0"]))


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    truth_p, solve_p, out_p = sys.argv[1:4]
    td = json.load(open(truth_p))
    ladder = {int(k): v["ln"] for k, v in td["ladder"].items()}
    rungs = np.array(sorted(ladder))
    tv = np.array([ladder[j] for j in rungs])
    s = read_sidecar(solve_p)
    js, d2s, contiguous = d2_px(s)
    print("solve %s: %d frames, contiguous=%s" % (solve_p, len(s), contiguous))
    print("truth ladder: %d rungs, j %d..%d" % (len(rungs), rungs[0], rungs[-1]))

    hdr = ("  %-34s %8s %8s %8s %9s %8s %8s"
           % ("", "median", "p90", "p99", "max", ">=0.5px", ">=1px"))

    # ---------------- controls ----------------
    print("\nCONTROLS  (all in plane px at the corner radius)")
    print(hdr)
    n = max(s) + 1
    jj = np.arange(n, dtype=float)

    lin = {int(k): float(v) for k, v in
           zip(jj, -1.54154e-1 * jj / 298.0)}
    _, a_v, _ = d2_px(lin)
    print(row("A PLACEBO  linear track", a_v))
    a_ok = bool(a_v.max() < 1e-9)

    # a smooth curve carrying the REAL breathing curvature, from the ladder
    coef = np.polyfit(rungs.astype(float), tv, 4)
    smooth = {int(k): float(np.polyval(coef, float(k))) for k in range(n)}
    fit_res = np.abs(np.polyval(coef, rungs.astype(float)) - tv) * R_PLANE
    _, c_v, _ = d2_px(smooth)
    print(row("C SPECIFICITY real curvature, smooth", c_v))
    print("     (quartic fit to the ladder, residual at the 39 rungs: "
          "median %.3f px, max %.3f px)"
          % (float(np.median(fit_res)), float(fit_res.max())))
    print("     DERIVED ceiling from C1's 46.1 px chord departure: 0.0092 px")
    c_ok = bool(c_v.max() < 0.05)

    amp = 0.5 / R_PLANE
    plant = {k: v + amp * (1.0 if k % 2 == 0 else -1.0) for k, v in smooth.items()}
    _, b_v, _ = d2_px(plant)
    got, want = float(np.median(b_v)), 4.0 * 0.5
    print(row("B POSITIVE +-0.5 px alternating", b_v))
    print("     expected 4A = %.2f px, recovered %.4f px (%.1f%%)"
          % (want, got, 100.0 * got / want))
    b_ok = bool(abs(got - want) / want < 0.02)

    ok = bool(a_ok and b_ok and c_ok)
    print("  -> controls %s   (A %s, B %s, C %s)"
          % ("PASS" if ok else "FAIL",
             "ok" if a_ok else "FAIL", "ok" if b_ok else "FAIL",
             "ok" if c_ok else "FAIL"))

    # ---------------- R2: the truth-free answer ----------------
    print("\nR2  SECOND DIFFERENCE OF THE SOLVE  (truth-free, fit-free, gauge-free)")
    print(hdr)
    print(row("the shipped solve, all frames", d2s))
    near = d2s[np.abs(js - REFERENCE) <= 50]
    far = d2s[np.abs(js - REFERENCE) > 100]
    print(row("  near reference (|j-149| <= 50)", near))
    print(row("  far from reference (> 100)", far))

    # ---------------- R1: as asked ----------------
    print("\nR1  FIRST DIFFERENCE OF THE ERROR  e(j) = s(j) - t_hat(j)")
    print(hdr)
    r1 = {}
    for deg in (3, 4, 6):
        c = np.polyfit(rungs.astype(float), tv, deg)
        e = {k: s[k] - float(np.polyval(c, float(k))) for k in sorted(s)}
        ks = np.array(sorted(e))
        ev = np.array([e[k] for k in ks])
        v = np.abs(np.diff(ev)) * R_PLANE
        res = float(np.median(np.abs(np.polyval(c, rungs.astype(float)) - tv))
                    * R_PLANE)
        print(row("truth fit degree %d (resid %.2f px)" % (deg, res), v))
        r1["deg%d" % deg] = stats(v)

    # ---------------- R3: disagreement at election lag ----------------
    # Fact 1411's mechanism needs the placement difference between the frames
    # that ADJACENT PIXELS elect, which is a lag-1 quantity only if adjacent
    # pixels elect adjacent frames. M96 measured a 25.247% disconnected
    # competitive set on this stack, so elections jump and the relevant lag is
    # not always 1. This prices the hypothesis across the range.
    print("\nR3  DISAGREEMENT AT ELECTION LAG L  (truth-free: s(j+L) - 2s(j) + s(j-L))")
    print("  %-12s %8s %8s %9s %8s | %9s %8s"
          % ("", "median", "p90", "max", ">=1px", "curv-ceil", "ratio"))
    ks = np.array(sorted(s))
    yv = np.array([s[k] for k in ks])
    r3 = {}
    for L in (1, 2, 4, 8, 16, 32, 64):
        v = np.abs(yv[2 * L:] - 2.0 * yv[L:-L] + yv[:-2 * L]) * R_PLANE
        # DERIVED: a smooth arc with this stack's measured curvature contributes
        # f'' * L^2 to a second difference at spacing L, with f'' = 8d/N^2 from
        # C1's 46.1 px chord departure. Beyond the lag where the ceiling
        # approaches the signal, this statistic can no longer separate real
        # disagreement from the breathing curve itself, and says so.
        ceil = 0.0092 * L * L
        st = stats(v)
        st["curvature_ceiling_px"] = ceil
        st["ratio_to_ceiling"] = st["median_px"] / ceil
        r3["L%d" % L] = st
        print("  L = %-8d %8.4f %8.4f %9.4f %8.3f | %9.4f %7.1fx"
              % (L, st["median_px"], st["p90_px"], st["max_px"],
                 st["frac_ge_1p0"], ceil, st["ratio_to_ceiling"]))
    lag_ok = bool(r3["L1"]["ratio_to_ceiling"] > 10.0)
    print("  -> trustworthy while ratio >> 1; curvature dominates beyond that")
    print("  -> lag readout %s at L=1 (%.0fx headroom)"
          % ("PASS" if lag_ok else "FAIL", r3["L1"]["ratio_to_ceiling"]))

    out = {"controls": {"placebo_linear": stats(a_v),
                        "positive_planted": stats(b_v),
                        "specificity_curvature": stats(c_v),
                        "positive_recovery_pct": 100.0 * got / want,
                        "pass": ok},
           "R2_all": stats(d2s), "R2_near": stats(near), "R2_far": stats(far),
           "R1": r1, "R3_lag": r3, "R3_lag_control_pass": lag_ok,
           "fit_residual_px": {"median": float(np.median(fit_res)),
                               "max": float(fit_res.max())}}
    json.dump(out, open(out_p, "w"), indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
