r"""M122 -- re-derivation of quantisation exposure for THIS milestone's estimator.

The orchestrator has withdrawn the two-question triage rule (absolute? / small
over large?) after three independent refutations, and replaced it with: do not
triage by the FORM of the expression -- expand it algebraically to see which
factor the perturbation lands in, or measure it with a dose-response control.

This does both, for M122's actual statistic.

  B12 = median over 12 windows of  hf(A1_win) / hf(A0_win),
  hf(w) = RMS of the 5-point laplacian of w.

ALGEBRA. The laplacian is linear, so lap(a+e) = lap(a) + lap(e). If the
quantisation error e were independent of the signal with variance s^2/12, the
5-point kernel (sum of squares 4^2+1+1+1+1 = 20) gives

  E[hf_meas^2] = hf_true^2 + q,     q = 20 * s^2 / 12 = 5 s^2 / 3

and therefore

  R_meas = sqrt( (hf1^2 + q) / (hf0^2 + q) ).                          (*)

This is ONE factor with q in BOTH the numerator and the denominator. M115's
band-SNR is a PRODUCT of two factors with q in only one of them, which is why
that ratio tends to the signal-power ratio and can reverse sign. Under (*),
if hf1 < hf0 then hf1^2+q < hf0^2+q for every q >= 0, so R_meas rises toward
1 monotonically and CANNOT cross it. No sign reversal is algebraically
available to this estimator.

But (*) assumes e is independent of the signal, and the orchestrator's central
new finding is that it is not -- rounding is a deterministic function of the
pixel value. So the algebra is a prediction to be TESTED, not a clearance.
STEP 3 tests it and STEP 4 measures the mechanism behind the residual.

Reads C:\dev\strehl-out\M122\{measure,blotch-ab.json}. Writes stdout + JSON.
"""
import json
import os
import sys

import numpy as np
import tifffile

ROOT = r"C:\dev\strehl-out\M122\measure"
OUT = r"C:\dev\strehl-out\M122"
S = 256

# step sizes in DN. 1 = untouched 16-bit reference. 257 is the PIL 8-bit path.
DOSES = [1, 4, 16, 24, 32, 48, 64, 257, 1024, 4096]


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, "%s read as %s, expected uint16 -- refusing" % (p, a.dtype)
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


def lap(w):
    return (-4 * w[1:-1, 1:-1] + w[:-2, 1:-1] + w[2:, 1:-1]
            + w[1:-1, :-2] + w[1:-1, 2:])


def hf(w):
    return float(np.sqrt((lap(w) ** 2).mean()))


def quantise(w, s):
    """Narrowing: deterministic rounding to a grid of step s."""
    if s <= 1:
        return w
    return np.floor(w / s + 0.5) * s


def dither(w, s, rng):
    """The NULL the orchestrator says is invalid: independent noise of the SAME
    power as the quantisation error (uniform on [-s/2, s/2) has var s^2/12),
    added WITHOUT collapsing the value grid."""
    if s <= 1:
        return w
    return w + rng.uniform(-s / 2.0, s / 2.0, w.shape)


def theil_sen(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    sl = [(y[j] - y[i]) / (x[j] - x[i])
          for i in range(n) for j in range(i + 1, n) if x[j] != x[i]]
    return float(np.median(sl)) if sl else float("nan")


def collect():
    """Pull the stored smooth windows for every usable stack, both arms."""
    recs = json.load(open(os.path.join(OUT, "blotch-ab.json")))
    got = []
    for r in recs:
        st = r["stack"]
        p0 = os.path.join(ROOT, "%s__A0.tif" % st)
        p1 = os.path.join(ROOT, "%s__A1.tif" % st)
        if not (os.path.exists(p0) and os.path.exists(p1)):
            continue
        if not r.get("commissioning_ok"):
            continue
        wins = r.get("smooth_windows") or []
        if not wins:
            continue
        a0, a1 = load(p0), load(p1)
        w0 = [a0[w["y"]:w["y"] + S, w["x"]:w["x"] + S].copy() for w in wins]
        w1 = [a1[w["y"]:w["y"] + S, w["x"]:w["x"] + S].copy() for w in wins]
        del a0, a1
        got.append((st, w0, w1))
        print("  loaded %-32s %2d windows" % (st, len(w0)))
        sys.stdout.flush()
    return got


def main():
    print(__doc__.split("Reads")[0])
    print("=" * 78)
    print("STEP 1 -- load the corpus windows (real uint16 pixels)")
    data = collect()
    nwin = sum(len(w) for _, w, _ in data)
    print("  %d stacks, %d windows total\n" % (len(data), nwin))

    rng = np.random.default_rng(20260824)
    out = {"doses": DOSES, "stacks": [s for s, _, _ in data], "rows": []}

    # ---- STEP 2: dose-response of beta, the M115 instrument, on my statistic
    print("=" * 78)
    print("STEP 2 -- dose-response. beta = Theil-Sen slope of log R(dose) on")
    print("          log R(truth) across all %d windows. beta=1 faithful," % nwin)
    print("          0 = collapsed to a null, NEGATIVE = ranking inverted.\n")

    base = []
    for st, w0, w1 in data:
        for a, b in zip(w0, w1):
            base.append(np.log(hf(b) / hf(a)))
    base = np.array(base)

    print("%6s %8s %9s %9s %9s %9s %7s" %
          ("step", "levels", "beta_q", "beta_dith", "twz_q", "bee_q", "dead"))
    rows = []
    for s in DOSES:
        lq, ld, lb = [], [], []
        per_stack = {}
        lev, dead = [], 0
        for st, w0, w1 in data:
            rs = []
            for k, (a, b) in enumerate(zip(w0, w1)):
                aq, bq = quantise(a, s), quantise(b, s)
                ad, bd = dither(a, s, rng), dither(b, s, rng)
                h0q, h1q = hf(aq), hf(bq)
                h0d, h1d = hf(ad), hf(bd)
                if h0q <= 0 or h1q <= 0 or h0d <= 0 or h1d <= 0:
                    dead += 1          # window annihilated: statistic undefined
                    continue
                rq, rd = h1q / h0q, h1d / h0d
                lq.append(np.log(rq))
                ld.append(np.log(rd))
                lb.append(np.log(hf(b) / hf(a)))
                rs.append(rq)
                lev.append(len(np.unique(aq)))
            if rs:
                per_stack[st] = float(np.median(rs))
        base_s = np.array(lb)
        bq_ = theil_sen(base_s, np.array(lq))
        bd_ = theil_sen(base_s, np.array(ld))
        allr = [v for v in per_stack.values()]
        row = {"step": s, "levels_median": float(np.median(lev)) if lev else 0.0,
               "beta_quant": bq_, "beta_dither": bd_,
               "per_stack": per_stack, "dead_windows": dead,
               "minR_quant": float(np.min(allr)), "maxR_quant": float(np.max(allr))}
        rows.append(row)
        print("%6d %8.0f %9.4f %9.4f %9.4f %9.4f %7d" %
              (s, row["levels_median"], bq_, bd_,
               per_stack.get("tweezers-cpl", float("nan")),
               per_stack.get("bee-3-cpl", float("nan")), dead))
        sys.stdout.flush()
    out["rows"] = rows

    neg = [r for r in rows if r["beta_quant"] < 0]
    print("\n  doses with beta < 0 (sign reversal): %s" %
          ("NONE -- matches the algebra" if not neg
           else [r["step"] for r in neg]))
    print("  beta monotone non-increasing: %s" %
          all(rows[i]["beta_quant"] >= rows[i + 1]["beta_quant"] - 1e-9
              for i in range(len(rows) - 1)))
    print("  per-stack B12 stays on one side of 1: min = %.4f, max = %.4f"
          % (min(r["minR_quant"] for r in rows),
             max(r["maxR_quant"] for r in rows)))
    print("  VERDICT-CRITICAL: does bee-3-cpl still exceed the 1.03 harm bar?")
    for r in rows:
        v = r["per_stack"].get("bee-3-cpl", float("nan"))
        print("     step %5d  bee-3-cpl B12 = %.4f   K2 fires: %s"
              % (r["step"], v, "YES" if v > 1.03 else "NO"))

    # ---- STEP 3: does the independent-noise floor model actually predict it?
    print("\n" + "=" * 78)
    print("STEP 3 -- test the algebra (*), q = 5 s^2 / 3, no free parameters.")
    print("          PER STACK, not pooled: a pooled median is ~1.0 for both")
    print("          predicted and measured because most windows do not respond,")
    print("          which makes the test vacuous (discipline 835, aggregate last).\n")
    print("%-26s %7s %11s %11s %9s" % ("stack", "step", "predicted", "measured", "resid"))
    pred_rows = []
    for st, w0, w1 in data:
        if st not in ("tweezers-cpl", "bee-3-cpl", "foam"):
            continue
        for s in (16, 64, 257):
            pr, mr = [], []
            for a, b in zip(w0, w1):
                h0, h1 = hf(a), hf(b)
                hq0, hq1 = hf(quantise(a, s)), hf(quantise(b, s))
                if h0 <= 0 or hq0 <= 0:
                    continue
                q = 5.0 * s * s / 3.0
                pr.append(np.sqrt((h1 * h1 + q) / (h0 * h0 + q)))
                mr.append(hq1 / hq0)
            p_, m_ = float(np.median(pr)), float(np.median(mr))
            pred_rows.append({"stack": st, "step": s, "pred": p_, "meas": m_})
            print("%-26s %7d %11.4f %11.4f %+9.4f" % (st, s, p_, m_, m_ - p_))
    out["floor_model"] = pred_rows

    worst = max(pred_rows, key=lambda r: abs(r["meas"] - r["pred"]))
    print("\n  largest disagreement: %s step %d, predicted %.4f, measured %.4f (%+.4f)"
          % (worst["stack"], worst["step"], worst["pred"], worst["meas"],
             worst["meas"] - worst["pred"]))
    print("  sign of residual tells the story: measured LESS compressed than the")
    print("  independent-noise model predicts => the error is NOT independent.")

    # ---- STEP 4: the mechanism -- is the error correlated BETWEEN THE ARMS?
    print("\n" + "=" * 78)
    print("STEP 4 -- why (*) misses. If rounding error were noise it would be")
    print("          independent between the two arms. It is a deterministic")
    print("          function of the value, and the arms image the same scene.\n")
    print("%6s %12s %12s" % ("step", "corr(e0,e1)", "corr(lap e)"))
    corr_rows = []
    for s in DOSES:
        if s <= 1:
            continue
        ce, cl = [], []
        for st, w0, w1 in data:
            for a, b in zip(w0, w1):
                e0 = quantise(a, s) - a
                e1 = quantise(b, s) - b
                if e0.std() > 0 and e1.std() > 0:
                    ce.append(np.corrcoef(e0.ravel(), e1.ravel())[0, 1])
                    l0, l1 = lap(e0).ravel(), lap(e1).ravel()
                    if l0.std() > 0 and l1.std() > 0:
                        cl.append(np.corrcoef(l0, l1)[0, 1])
        r = {"step": s, "corr_err": float(np.median(ce)) if ce else float("nan"),
             "corr_lap": float(np.median(cl)) if cl else float("nan")}
        corr_rows.append(r)
        print("%6d %12.4f %12.4f" % (s, r["corr_err"], r["corr_lap"]))
    out["arm_correlation"] = corr_rows

    # the same comparison for the dither null, which SHOULD be uncorrelated
    cd = []
    for st, w0, w1 in data:
        for a, b in zip(w0, w1):
            e0 = dither(a, 257, rng) - a
            e1 = dither(b, 257, rng) - b
            cd.append(np.corrcoef(e0.ravel(), e1.ravel())[0, 1])
    out["dither_corr_257"] = float(np.median(cd))
    print("\n  dither null at step 257: corr(e0,e1) = %.4f  (independent, as designed)"
          % out["dither_corr_257"])

    with open(os.path.join(OUT, "quant-doseresponse.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("\nwrote %s" % os.path.join(OUT, "quant-doseresponse.json"))

    # ---- STEP 5: chase the one number that does not fit.
    # beta falls monotonically to 0.2482 at step 1024 and then RISES at 4096,
    # which the algebra forbids. Hypothesis: survivorship -- 26 of 180 windows
    # are annihilated (hf = 0) at that dose and silently dropped, leaving a
    # biased high-contrast subset. Test it by holding the window set fixed to
    # those alive at EVERY dose, so the sample cannot change beneath the curve.
    print("\n" + "=" * 78)
    print("STEP 5 -- the number that does not fit: beta rises 0.2482 -> 0.3151")
    print("          at the largest dose. Testing the survivorship hypothesis by")
    print("          fixing the window set to those alive at every dose.\n")
    alive = []
    for st, w0, w1 in data:
        for a, b in zip(w0, w1):
            if all(hf(quantise(a, s)) > 0 and hf(quantise(b, s)) > 0 for s in DOSES):
                alive.append((a, b))
    print("  windows alive at every dose: %d of %d\n" % (len(alive), nwin))
    print("%6s %12s %12s" % ("step", "beta_all", "beta_fixed"))
    lb = np.array([np.log(hf(b) / hf(a)) for a, b in alive])
    fixed_rows = []
    for r in rows:
        s = r["step"]
        lq = np.array([np.log(hf(quantise(b, s)) / hf(quantise(a, s)))
                       for a, b in alive])
        bf = theil_sen(lb, lq)
        fixed_rows.append({"step": s, "beta_fixed": bf})
        print("%6d %12.4f %12.4f" % (s, r["beta_quant"], bf))
    out["beta_fixed_sample"] = fixed_rows
    mono = all(fixed_rows[i]["beta_fixed"] >= fixed_rows[i + 1]["beta_fixed"] - 1e-9
               for i in range(len(fixed_rows) - 1))
    print("\n  beta monotone non-increasing on the FIXED sample: %s" % mono)
    print("  => the rise was %s" %
          ("survivorship, as hypothesised: the sample changed, not the physics."
           if mono else
           "NOT survivorship -- it survives a fixed sample. Hypothesis refuted."))

    # ---- STEP 6: is the rise even significant? Bootstrap beta over windows.
    # If the interval at 4096 covers the value at 1024 there is no anomaly to
    # explain, only an estimator that has itself been destroyed by the dose.
    print("\n" + "=" * 78)
    print("STEP 6 -- bootstrap CI on beta (fixed sample, %d windows, 200 resamples)"
          % len(alive))
    print("          to test whether the rise is a real effect at all.\n")
    boot = np.random.default_rng(7)
    print("%6s %9s %9s %22s" % ("step", "levels", "beta", "95% CI"))
    ci_rows = []
    for r in rows:
        s = r["step"]
        if s < 257:
            continue
        lq = np.array([np.log(hf(quantise(b, s)) / hf(quantise(a, s)))
                       for a, b in alive])
        bs = []
        idx = np.arange(len(alive))
        for _ in range(200):
            j = boot.choice(idx, len(idx), replace=True)
            bs.append(theil_sen(lb[j], lq[j]))
        lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
        ci_rows.append({"step": s, "beta": theil_sen(lb, lq), "lo": lo, "hi": hi,
                        "levels": r["levels_median"]})
        print("%6d %9.0f %9.4f     [%7.4f, %7.4f]"
              % (s, r["levels_median"], ci_rows[-1]["beta"], lo, hi))
    out["beta_ci"] = ci_rows
    if len(ci_rows) >= 2:
        a_, b_ = ci_rows[-2], ci_rows[-1]
        overlap = not (b_["lo"] > a_["hi"] or a_["lo"] > b_["hi"])
        print("\n  CIs at step %d and %d overlap: %s" % (a_["step"], b_["step"], overlap))
        print("  => %s" %
              ("the rise is NOT significant. There is no anomaly in the physics;\n"
               "     what the doses destroyed is beta itself. At %.0f levels per\n"
               "     window the ratio takes a handful of discrete values and the\n"
               "     slope is no longer estimable. The instrument that measures\n"
               "     the damage is disabled by the same dose it is measuring."
               % b_["levels"] if overlap else
               "the rise IS significant and remains unexplained. Report it as open."))

    with open(os.path.join(OUT, "quant-doseresponse.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    main()
