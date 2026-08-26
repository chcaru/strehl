"""PART 2, sharpened: is the flux ramp magnification, or is it gain?

Several subjects show a large, smooth, monotonic rise in camera-linear flux
across the bracket -- up to +0.54 stops -- with essentially no frame-to-frame
flicker and with EXIF that says the exposure never changed.  Read naively that
is a half-stop of unexplained gain drift, and it would mis-weight the merge's
noise gate on a third of the corpus.

There is a competing explanation that costs nothing to test.  Focus breathing
changes MAGNIFICATION.  A magnified image spreads the same photons over m^2
more pixels, so mean flux per pixel goes as 1/m^2.  That gives a prediction
with NO free parameter:

    ln(flux_b / flux_a)  ==  -2 * ln(scale_ab)

analyse.py tests this on the bracket total, but only by extrapolating a median
per-frame scale rate over the whole bracket, which assumes the rate is
constant.  It is not: magnification change per focus step depends on where in
the focus range you are.  This script removes that assumption entirely by
testing the prediction PAIRWISE, on exactly the frame pairs whose scale was
actually measured.  No extrapolation, no fitting.

The two sides are independent.  The left comes from exposure.py: per-frame
decile statistics of the camera-linear green plane.  The right comes from
sweep.py: a similarity fitted to tile correlation displacements, computed for
an entirely different purpose (measuring motion) before this hypothesis
existed.  They share no code beyond the RAW decoder.

CONTROLS (rule 2: never let a plant or a control go unverified)

  N1  permutation null.  Both flux and scale drift monotonically with frame
      index, so "they correlate" is a weak claim -- anything monotonic
      correlates with anything else monotonic.  Re-pair each measured flux
      change with the predicted scale of a DIFFERENT randomly chosen pair from
      the same subject.  That preserves both marginal distributions and
      destroys only the pairing.  If the slope survives, the agreement is an
      artifact of shared monotonicity; if it collapses, the pairing carries
      real information.

  N2  the slope is the test, not the correlation.  The prediction fixes the
      slope at exactly 1.0.  A shared-trend artifact would produce some
      arbitrary slope; only the real mechanism produces 1.0.  Reported with a
      bootstrap CI so a hostile reader can see whether 1.0 is inside it.

USAGE
    python experiments/BUILD-GHOST/magtest.py
"""
from __future__ import annotations

import json
import os

import numpy as np

OUT = r"C:\dev\strehl-out\BUILD-GHOST"
DATA = os.path.join(OUT, "data")

# A similarity fitted from very few tiles carries a very noisy scale.  This is
# a trust bar on the INPUT, declared before looking at the answer, and the
# census below reports how many pairs it removes.
MIN_TILES_FOR_SCALE = 20
LN2 = float(np.log(2.0))

# POWER GATE, applied per SUBJECT rather than per pair.  A subject can only
# test the prediction if the effect the prediction predicts is bigger than the
# noise on the measurement of it.  The predicted effect is |-2 ln s|; the noise
# is that subject's own frame-to-frame flicker, measured by exposure.py as a
# MAD and independent of both sides of this test.
#
# Gating per SUBJECT rather than per PAIR matters: a per-pair gate keeps a
# ragged handful of pairs from otherwise-untestable subjects, which is the
# worst of both worlds -- too few pairs to fit, but enough variance to
# dominate a pooled fit.
#
# Both criteria are computed from the PREDICTOR and from independently
# measured noise/clipping, never from the residual or the slope, so neither
# can select for agreement.  Subjects that fail are "UNTESTABLE", which is a
# third outcome distinct from "agrees" and "disagrees", and they are counted.
POWER_K = 3.0
# Clipped pixels destroy a flux measurement outright: a saturated sensel does
# not get brighter.  This is a property of the input frames.
MAX_SAT = 0.01
# A slope needs enough pairs to mean anything.
MIN_PAIRS_FOR_SLOPE = 5


def main() -> int:
    sweep = json.load(open(os.path.join(DATA, "sweep.json")))

    rows = []          # (subject, k, measured_ln, predicted_ln)
    n_pairs_total = n_no_flux = n_too_few = n_used = 0
    per_subject = {}
    untestable = {}    # subject -> reason

    for rec in sweep["subjects"]:
        name = rec["subject"]
        fp = os.path.join(DATA, f"exposure_{name}.json")
        if not os.path.exists(fp):
            continue
        expo = json.load(open(fp))
        # Join on FILENAME, not on index: exposure.py may have used a stride.
        stops = {f["file"]: f["stops"] for f in expo["per_frame"]}
        # Independent noise level for this subject, in ln units.
        noise_ln = float(expo.get("flicker_mad_stops") or 0.0) * LN2
        sat = float(expo.get("sat_frac_max") or 0.0)

        mine = []
        for p in rec.get("pairs", []):
            if not p.get("ok"):
                continue
            n_pairs_total += 1
            a, b = p.get("a"), p.get("b")
            if a not in stops or b not in stops:
                n_no_flux += 1
                continue
            if p.get("n", 0) < MIN_TILES_FOR_SCALE:
                n_too_few += 1
                continue
            s = p.get("sim_scale_minus_one")
            if s is None:
                n_too_few += 1
                continue
            mine.append(((stops[b] - stops[a]) * LN2,
                         -2.0 * float(np.log1p(s)), p["k"]))
        if not mine:
            continue
        arr = np.array([(m, q) for m, q, _ in mine], dtype=float)

        # --- subject-level gates, all on inputs ---
        # Power for an n-point slope goes as the standard error of the mean,
        # sigma/sqrt(n), NOT as sigma: comparing a per-pair effect against
        # single-measurement noise understates the power of an n-pair fit.
        eff = float(np.median(np.abs(arr[:, 1])))
        se = noise_ln / max(np.sqrt(len(arr)), 1.0)
        if sat > MAX_SAT:
            untestable[name] = (f"clipping {sat * 100:.1f}% > {MAX_SAT * 100:g}%", len(arr))
        elif eff < POWER_K * se:
            untestable[name] = (
                f"no power: median |pred| {eff / LN2:.5f} st < {POWER_K:g}x SE "
                f"{se / LN2:.5f} st", len(arr))
        elif len(arr) < MIN_PAIRS_FOR_SLOPE:
            untestable[name] = (f"only {len(arr)} pairs", len(arr))
        else:
            per_subject[name] = arr
            for m, q, k in mine:
                rows.append((name, k, m, q))
            n_used += len(arr)
            continue
        n_too_few += len(arr)

    print("=" * 96)
    print("PART 2 CONTROL  pairwise magnification test:  ln(flux_b/flux_a) == -2 ln(scale_ab)")
    print("=" * 96)
    print(f"pairs in sweep (ok)          {n_pairs_total}")
    print(f"  dropped, no flux record    {n_no_flux}")
    print(f"  dropped, untestable subject or <{MIN_TILES_FOR_SCALE} tiles  {n_too_few}")
    print(f"  USED                       {n_used}")
    print(f"  (sums to {n_no_flux + n_too_few + n_used} of {n_pairs_total})")
    assert n_no_flux + n_too_few + n_used == n_pairs_total
    print(f"\nsubjects TESTABLE {len(per_subject)}   UNTESTABLE {len(untestable)}   "
          f"(sums to {len(per_subject) + len(untestable)})")
    for nm, (why, npair) in sorted(untestable.items()):
        print(f"    {nm:38s} {npair:3d} pairs   {why}")
    if n_used < 30:
        print("\nTOO FEW PAIRS TO CONCLUDE ANYTHING.")
        return 1

    meas = np.array([r[2] for r in rows])
    pred = np.array([r[3] for r in rows])

    slope, r2, inter = fit(pred, meas)
    lo, hi = boot(pred, meas)

    # The headline statistic is PER SUBJECT, then combined.  An unweighted
    # pooled fit lets whichever subject happens to have the largest flux
    # variance set the answer for all of them, which is not a property of the
    # hypothesis under test.
    subj_slopes = np.array([fit(a[:, 1], a[:, 0])[0] for a in per_subject.values()])
    subj_ratio = np.array([
        float(np.sqrt(np.mean(a[:, 0] ** 2))) /
        max(float(np.sqrt(np.mean((a[:, 0] - a[:, 1]) ** 2))), 1e-12)
        for a in per_subject.values()])
    med_slope = float(np.median(subj_slopes))
    print(f"\nHEADLINE  per-subject slopes, {len(subj_slopes)} testable subjects")
    print(f"  median slope     {med_slope:+.4f}   (prediction says exactly 1.0)")
    print(f"  quartiles        {np.percentile(subj_slopes, 25):+.4f} .. "
          f"{np.percentile(subj_slopes, 75):+.4f}")
    print(f"  subjects whose RMS flux error the prediction REDUCES (ratio>1): "
          f"{int(np.sum(subj_ratio > 1.0))}/{len(subj_ratio)}")
    print(f"  subjects where it more than halves it (ratio>2):               "
          f"{int(np.sum(subj_ratio > 2.0))}/{len(subj_ratio)}")
    print(f"  median RMS reduction factor   {float(np.median(subj_ratio)):.2f}x "
          "with ZERO fitted parameters")

    print(f"\nsecondary: all pairs pooled, n={n_used}")
    print(f"  slope            {slope:+.4f}")
    print(f"  bootstrap 95% CI [{lo:+.4f}, {hi:+.4f}]   "
          f"{'CONTAINS 1.0' if lo <= 1.0 <= hi else 'EXCLUDES 1.0'}")
    print(f"  intercept        {inter:+.6f} ln  ({inter / LN2:+.4f} stops)")
    print(f"  R^2              {r2:.4f}")

    # How much of the observed flux variation does a zero-parameter prediction
    # remove?  This is the number that decides whether the ramps are geometry.
    rms_before = float(np.sqrt(np.mean(meas ** 2))) / LN2
    rms_after = float(np.sqrt(np.mean((meas - pred) ** 2))) / LN2
    print(f"  RMS flux change            {rms_before:.4f} stops")
    print(f"  RMS residual after -2ln s  {rms_after:.4f} stops   "
          f"({rms_before / max(rms_after, 1e-9):.2f}x reduction, no fitted parameter)")

    # ---- N1 permutation null -------------------------------------------
    # Judged on the SAME statistic as the headline (median per-subject slope),
    # drawn from the SAME gated pairs, so if the gates manufactured agreement
    # the null would show it too.
    rng = np.random.default_rng(20260826)
    slopes = []
    for _ in range(400):
        s = []
        for arr in per_subject.values():
            idx = rng.permutation(len(arr))
            s.append(fit(arr[idx, 1], arr[:, 0])[0])
        slopes.append(float(np.median(s)))
    slopes = np.array(slopes)
    print(f"\nN1 permutation null (re-pair within subject, 400 draws)")
    print(f"  median per-subject slope {np.mean(slopes):+.4f} +- {np.std(slopes):.4f}   "
          f"range [{slopes.min():+.4f}, {slopes.max():+.4f}]")
    beats = int(np.sum(slopes >= med_slope))
    print(f"  draws reaching the true median slope {med_slope:+.4f}: "
          f"{beats}/{len(slopes)}   (p = {(beats + 1) / (len(slopes) + 1):.4f})")
    n1 = beats == 0
    print(f"  -> {'PASS' if n1 else 'FAIL'}  "
          "(the pairing must carry information the marginals do not)")
    print("  NOTE: the null is drawn from the SAME gated pairs, so if the")
    print("  gates themselves manufactured agreement the null would show it too.")

    # ---- per subject ----------------------------------------------------
    print(f"\n{'subject':38s} {'n':>4s} {'slope':>8s} {'R^2':>6s} "
          f"{'RMSmeas':>8s} {'RMSresid':>9s} {'ratio':>6s}")
    tab = {}
    for name, arr in sorted(per_subject.items(),
                            key=lambda kv: -np.sqrt(np.mean(kv[1][:, 0] ** 2))):
        if len(arr) < 4:
            print(f"{name:38s} {len(arr):4d}   (too few pairs to fit)")
            continue
        sl, rr, _ = fit(arr[:, 1], arr[:, 0])
        b = float(np.sqrt(np.mean(arr[:, 0] ** 2))) / LN2
        a_ = float(np.sqrt(np.mean((arr[:, 0] - arr[:, 1]) ** 2))) / LN2
        print(f"{name:38s} {len(arr):4d} {sl:+8.3f} {rr:6.3f} "
              f"{b:8.4f} {a_:9.4f} {b / max(a_, 1e-9):6.2f}")
        tab[name] = {"n": len(arr), "slope": sl, "r2": rr,
                     "rms_meas_stops": b, "rms_resid_stops": a_}

    json.dump({"n_used": n_used, "median_subject_slope": med_slope,
               "subject_slopes": {k: float(fit(a[:, 1], a[:, 0])[0])
                                  for k, a in per_subject.items()},
               "n_testable": len(per_subject),
               "untestable": {k: v[0] for k, v in untestable.items()},
               "pooled_slope": slope, "ci": [lo, hi], "r2": r2,
               "intercept_ln": inter,
               "rms_meas_stops": rms_before, "rms_resid_stops": rms_after,
               "median_rms_reduction": float(np.median(subj_ratio)),
               "null_slope_mean": float(np.mean(slopes)),
               "null_slope_sd": float(np.std(slopes)),
               "null_p": (beats + 1) / (len(slopes) + 1),
               "null_passed": bool(n1),
               "min_tiles_for_scale": MIN_TILES_FOR_SCALE,
               "power_k": POWER_K, "max_sat": MAX_SAT,
               "per_subject": tab},
              open(os.path.join(DATA, "magtest.json"), "w"), indent=2, default=float)
    print(f"\nwrote {os.path.join(DATA, 'magtest.json')}")
    return 0


def fit(x, y):
    """Least squares y = slope*x + intercept, plus R^2."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    A = np.stack([x, np.ones_like(x)], axis=1)
    (sl, inter), *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - (sl * x + inter)
    ss = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum(resid ** 2)) / ss if ss > 0 else float("nan")
    return float(sl), r2, float(inter)


def boot(x, y, n=2000, seed=7):
    rng = np.random.default_rng(seed)
    n_obs = len(x)
    out = np.empty(n)
    for i in range(n):
        idx = rng.integers(0, n_obs, n_obs)
        out[i] = fit(x[idx], y[idx])[0]
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


if __name__ == "__main__":
    raise SystemExit(main())
