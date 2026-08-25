r"""M125 -- re-derivation of quantisation exposure for M125's OWN estimator and,
more importantly, for M125's DECISION.

The orchestrator withdrew the two-question triage rule (absolute? / small-over-
large?) after three refutations, and replaced it with: do not triage by the FORM
of the expression. Either expand it algebraically and see which factor the
perturbation lands in, or measure it with a dose-response control. This does
both.

M122 already discharged this for B12 (quant_doseresponse.py) and found
compression toward 1 with NO sign reversal algebraically available. That
clearance covers M125's LOSS. It does not cover either of M125's own objects:

  (1) Dpp -- the drift estimator promoted into strehl-core, and
  (2) the DECISION, a threshold crossing at T = 1.8392 %.

(2) is the sharp one. B12 compressing toward 1 is graceful degradation. A
BINARY DECISION HAS NO GRACEFUL DEGRADATION. M125's threshold sits in a gap of
0.3740 pp between bee-2-cpl (1.6522) and lead-1-cpl (2.0262), so a bias of only
~0.19 pp in Dpp reclassifies a stack and changes what the shipped code does.

ALGEBRA (the factor the perturbation lands in).

  L_f = mean over the active G1 area of frame f      (N ~ 10^6 pixels)
  Dpp = 100 * (max_f L_f - min_f L_f) / mean_f L_f

Quantisation with step s maps v -> round(v/s)*s, error e(v), |e| <= s/2, and e
is a DETERMINISTIC function of v (the orchestrator's central finding). So

  L_f_meas = L_f + ebar_f,     ebar_f = mean over the area of e(v_fi)

Write ebar_f = ebar + delta_f, splitting the part common to all frames from the
part that varies. Then

  numerator_meas = (max_f (L_f + delta_f)) - (min_f (L_f + delta_f))
  denominator_meas = mean_f L_f + ebar

THE COMMON PART CANCELS IN THE NUMERATOR. It survives only in the denominator,
where it is divided by a level of ~10^3 DN and is therefore negligible.

This is the OPPOSITE of the hazard the orchestrator warns about, and for the
same reason: Dpp DIFFERENCES ACROSS FRAMES, so the correlated component of
quantisation error is common-mode and cancels. The very correlation that
disables split-half and frame-difference NOISE estimators is PROTECTIVE here.

What is left is delta_f, the frame-to-frame VARIATION in mean rounding error.
delta_f is non-zero exactly when frames have different value histograms -- which
is what drift IS. So delta correlates with the signal being measured, and the
residual exposure is structured, not random. That is a prediction to be TESTED,
not a clearance. STEP 2 tests it.

STEP 3 runs the control the orchestrator says is invalid -- matched-power random
dither -- to confirm, in this estimator's own currency, that it is not a model
of quantisation.

Reads D:\personal\macro (READ-ONLY). Writes C:\dev\strehl-out\M125\quant-*.
"""

import glob
import json
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import rawpy

LIB = r"D:\personal\macro"
OUT = r"C:\dev\strehl-out\M125"
BLACK = 512

# The shipped constant. experiments/../photometric.rs AUTO_DRIFT_THRESHOLD_PCT.
T_SHIP = 1.8392099860712

# Quantisation steps in DN on the 14-bit RAW scale. step 64 is the 16->8 bit
# narrowing that the PIL hazard inflicts (16383/255 ~ 64).
STEPS = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512]

# The decision-critical set: the two stacks that straddle the threshold, the
# stack carrying 104% of the margin, and a high-drift control.
STACKS = ["bee-3-cpl", "bee-2-cpl", "lead-1-cpl", "tweezers-cpl"]

SEED = 20260824


def frame_row(path):
    """Mean G1 level above black at every dose, for one frame.

    The frame is read ONCE and every dose is computed from the same pixels, so
    the ladder is paired and I/O is paid once. Everything is reduced to floats
    inside the `with` (rule 32: no view may outlive the RawPy context).
    """
    with rawpy.imread(path) as rr:
        g = rr.raw_image_visible[0::2, 1::2].astype(np.float64) - BLACK

        quant = []
        levels = []
        for s in STEPS:
            if s == 1:
                q = g
            else:
                q = np.round(g / s) * s
            quant.append(float(q.mean()))
            levels.append(int(np.unique(q).size))

        # Matched-power random dither: same error variance as the rounding at
        # each step (uniform on [-s/2, s/2] has variance s^2/12), but INDEPENDENT
        # of the value. The orchestrator's point is that this is NOT a model of
        # quantisation; measuring it here proves that for THIS estimator.
        rng = np.random.default_rng(SEED + (abs(hash(os.path.basename(path))) % 100000))
        dither = []
        for s in STEPS:
            if s == 1:
                dither.append(float(g.mean()))
            else:
                d = rng.uniform(-s / 2.0, s / 2.0, size=g.shape)
                dither.append(float((g + d).mean()))

        native_levels = int(np.unique(g).size)
    return quant, levels, dither, native_levels


def p2p(v):
    v = np.asarray(v, dtype=np.float64)
    return float((v.max() - v.min()) / v.mean() * 100.0)


def measure(name, workers=8):
    fs = sorted(glob.glob(os.path.join(LIB, name, "*.ARW")))
    if not fs:
        return None
    with ProcessPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(frame_row, fs))
    quant = np.array([r[0] for r in res], dtype=np.float64)      # (nframes, ndose)
    levels = np.array([r[1] for r in res], dtype=np.int64)
    dither = np.array([r[2] for r in res], dtype=np.float64)
    native = int(np.median([r[3] for r in res]))
    return quant, levels, dither, native, len(fs)


def main():
    os.makedirs(OUT, exist_ok=True)
    out = {"steps": STEPS, "T_ship": T_SHIP, "stacks": {}}

    print(__doc__.split("Reads")[0])
    print("=" * 78)
    print("STEP 1 -- level census. V-M113 puts immunity loss near 12 distinct")
    print("          levels per fitted window and sign inversion at 2.")
    print()

    for name in STACKS:
        m = measure(name)
        if m is None:
            print("  %-14s NOT FOUND" % name)
            continue
        quant, levels, dither, native, nf = m
        med_lv = np.median(levels, axis=0).astype(int)
        dpp = np.array([p2p(quant[:, i]) for i in range(len(STEPS))])
        dpp_d = np.array([p2p(dither[:, i]) for i in range(len(STEPS))])
        out["stacks"][name] = {
            "frames": nf,
            "native_levels": native,
            "levels": med_lv.tolist(),
            "dpp": dpp.tolist(),
            "dpp_dither": dpp_d.tolist(),
        }
        print("  %-14s %3d frames, native distinct G1 levels = %d"
              % (name, nf, native))

    print()
    print("=" * 78)
    print("STEP 2 -- dose-response on Dpp, and on the DECISION.")
    print("          bias is in percentage POINTS; the decision gap is 0.3740 pp.")
    print()
    hdr = ("  %-14s %6s %8s %9s %9s %8s  %s"
           % ("stack", "step", "levels", "Dpp", "bias pp", "ratio", "decision"))
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    flips = []
    worst_bias = 0.0
    for name, d in out["stacks"].items():
        base = d["dpp"][0]
        base_dec = base >= T_SHIP
        for i, s in enumerate(STEPS):
            v = d["dpp"][i]
            bias = v - base
            dec = v >= T_SHIP
            mark = ""
            if dec != base_dec:
                mark = "  <== FLIPPED"
                flips.append((name, s, d["levels"][i], base, v))
            worst_bias = max(worst_bias, abs(bias))
            print("  %-14s %6d %8d %9.4f %+9.4f %8.4f  %s%s"
                  % (name, s, d["levels"][i], v, bias, v / base,
                     "ON " if dec else "OFF", mark))
        print()

    print("=" * 78)
    print("STEP 3 -- the control the orchestrator says is invalid.")
    print("          Matched-power RANDOM dither vs real rounding, same estimator.")
    print()
    print("  %-14s %6s %10s %10s %10s"
          % ("stack", "step", "Dpp quant", "Dpp dither", "ratio"))
    print("  " + "-" * 54)
    for name, d in out["stacks"].items():
        for i, s in enumerate(STEPS):
            if s in (1, 16, 64, 256, 512):
                q, dd = d["dpp"][i], d["dpp_dither"][i]
                print("  %-14s %6d %10.4f %10.4f %10.4f"
                      % (name, s, q, dd, (dd / q) if q else float("nan")))
        print()

    out["flips"] = flips
    out["worst_abs_bias_pp"] = worst_bias
    with open(os.path.join(OUT, "quant-doseresponse.json"), "w") as fh:
        json.dump(out, fh, indent=1)

    print("=" * 78)
    print("VERDICT")
    print()
    print("  worst |bias| in Dpp across every dose and stack : %.4f pp" % worst_bias)
    print("  decision gap the threshold sits in              : 0.3740 pp")
    print("  decision flips                                  : %d" % len(flips))
    if flips:
        for nm, s, lv, b, v in flips:
            print("    %s at step %d (%d levels): %.4f -> %.4f"
                  % (nm, s, lv, b, v))
    print()
    print("wrote %s" % os.path.join(OUT, "quant-doseresponse.json"))


if __name__ == "__main__":
    main()
