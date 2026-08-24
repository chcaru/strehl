"""M97 -- verdicts on the pre-registered angled-ruler bars S1-S5.

Does the arithmetic in one place so the treatment comparison cannot be quoted
without its controls. Three things this file exists to prevent:

  * comparing arms that tracked DIFFERENT tick populations. The arms are
    laterally offset, and one arm finds a graduation at the frame edge that the
    other does not. PREREG3 amendment 1 says that if the ticks do not
    correspond one-to-one the comparison is void; this pairs them by index
    shift and recomputes every statistic on the COMMON set.
  * quoting a bend-plant recovery against amp/sqrt(2) when a straight-line fit
    legitimately absorbs the half-sine's DC term. Uses the instrument's own
    `expected_added_rms_px`.
  * quoting an absolute straightness number as registration error. The ruler's
    manufacturing straightness and the lens's distortion are common to both
    arms; only the paired difference is a claim.
"""

import json
import sys

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import binomtest, wilcoxon

O = r"C:\dev\strehl-out\M97"
TAG = "ang"


def load(name):
    with open(rf"{O}\{TAG}-{name}.json", encoding="utf-8") as f:
        return json.load(f)


def pair_ticks(xa, xb):
    """Pair graduations between arms by index shift, not by position.

    Graduations are identical objects in a fixed order, so the only ambiguity
    is which one each arm's first detection is. Both arms are FOV-matched by
    construction, so the correct pairing is the one that leaves each tick close
    to where the other arm found it -- the criterion is POSITIONAL DISTANCE.

    An earlier version scored candidates by the residual of a linear map fitted
    between the two arms' tick positions, and it silently chose k=-4 with a
    scale of 1.113 -- a four-graduation slip -- because tick spacing varies
    projectively along a tilted ruler, so a slipped-and-rescaled pairing fits a
    line about as well as the true one. It was caught only because the two arms
    had already been MEASURED to agree on pitch to 0.3% (102.48 vs 102.15 px),
    which a scale of 1.113 flatly contradicts. Distance cannot slip like that:
    a one-tick error costs a whole pitch.
    """
    pitch = float(np.median(np.diff(xa)))
    best = None
    for k in range(-4, 5):
        ia = [i for i in range(len(xa)) if 0 <= i + k < len(xb)]
        if len(ia) < 6:
            continue
        a = np.array([xa[i] for i in ia])
        b = np.array([xb[i + k] for i in ia])
        d = float(np.median(np.abs(b - a)))
        if best is None or d < best[0]:
            best = (d, k, ia, a, b)
    if best is None:
        return None
    d, k, ia, a, b = best
    if d > 0.5 * pitch:
        return None
    c = np.polyfit(a, b, 1)
    r = float(np.sqrt(np.mean((b - np.polyval(c, a)) ** 2)))
    return (r, k, ia, float(c[0]), float(c[1]), d, pitch)


def g_stats(t):
    """Projective-in-index residual for a tick-centre sequence."""
    t = np.asarray(t, dtype=np.float64)
    i = np.arange(len(t), dtype=np.float64)

    def resid(p):
        a, b, c = p
        return t - (a * i + b) / (c * i + 1.0)

    p0 = [float(np.polyfit(i, t, 1)[0]), float(t[0]), 0.0]
    sol = least_squares(resid, p0, method="lm", max_nfev=40000)
    r = resid(sol.x)
    d = np.diff(t)
    rms = float(np.sqrt(np.mean(r**2)))
    return rms, rms / float(np.median(d)), float(np.median(d))


def quad(a, b):
    """Component that, added in quadrature to a, gives b. NaN if b < a."""
    v = b * b - a * a
    return float(np.sqrt(v)) if v > 0 else float("nan")


def main():
    global TAG
    if len(sys.argv) > 1:
        TAG = sys.argv[1]
    A, Z = load("ALIGNED"), load("ZOOMNULL")
    P = load("PLACEBO")
    S3 = load("SHIFT3")
    BA2, BA4, BZ4 = load("BENDA2"), load("BENDA4"), load("BENDZ4")

    print("=" * 72)
    print("S4 -- CONTROLS. None of S1-S3 is admissible unless these pass.")
    print("=" * 72)

    ok_placebo = (
        P["S_rms_median_px"] == A["S_rms_median_px"]
        and P["S_resid_p99_abs"] == A["S_resid_p99_abs"]
        and P["n_ticks"] == A["n_ticks"]
    )
    print(f"placebo (ALIGNED measured twice)")
    print(f"   S_rms_median  {A['S_rms_median_px']:.6f} vs {P['S_rms_median_px']:.6f}")
    print(f"   verdict: {'PASS (bit-identical)' if ok_placebo else 'FAIL'}")

    d = np.median(np.array(S3["fit_mid_x"]) - np.array(A["fit_mid_x"][: len(S3["fit_mid_x"])]))
    gain = float(-d / 3.0)
    ok_shift = abs(gain - 1.0) < 0.05
    print(f"\ntranslation gain (planted +3.0 px)")
    print(f"   median tick displacement {d:+.4f} px  ->  gain {gain:.4f}")
    print(f"   residual unchanged: {S3['S_rms_median_px']:.6f} vs {A['S_rms_median_px']:.6f}")
    print(f"   verdict: {'PASS' if ok_shift else 'FAIL'} (a translation must move ticks at gain 1")
    print(f"            and must NOT change straightness -- it is absorbed by the intercept)")

    print(f"\nbend response (does the metric see a planted bend?)")
    rec = {}
    for tag, B, base in (("2.0 px on ALIGNED", BA2, A), ("4.0 px on ALIGNED", BA4, A),
                         ("4.0 px on ZOOMNULL", BZ4, Z)):
        add = quad(base["S_rms_median_px"], B["S_rms_median_px"])
        exp = B["expected_added_rms_px"]
        rec[tag] = add / exp if exp else float("nan")
        print(f"   {tag:22s} {base['S_rms_median_px']:.4f} -> {B['S_rms_median_px']:.4f}"
              f"   added {add:.4f}  expected {exp:.4f}  recovery {rec[tag] * 100:.0f}%")
    ok_bend = all(0.5 < v < 2.0 for v in rec.values() if v == v)
    print(f"   verdict: {'PASS' if ok_bend else 'FAIL'} (bar: recovery within 0.5x-2.0x of the")
    print(f"            post-fit expectation, for every plant)")

    ok_dir = BZ4["S_rms_median_px"] > Z["S_rms_median_px"] and BA4["S_rms_median_px"] > A["S_rms_median_px"]
    print(f"\ndirection: a planted bend must make an arm WORSE, never better")
    print(f"   ALIGNED  {A['S_rms_median_px']:.4f} -> {BA4['S_rms_median_px']:.4f}")
    print(f"   ZOOMNULL {Z['S_rms_median_px']:.4f} -> {BZ4['S_rms_median_px']:.4f}")
    print(f"   verdict: {'PASS' if ok_dir else 'FAIL'}")

    controls_ok = ok_placebo and ok_shift and ok_bend and ok_dir
    print(f"\nCONTROLS OVERALL: {'PASS' if controls_ok else 'FAIL'}")

    print("\n" + "=" * 72)
    print("TICK CORRESPONDENCE -- prerequisite for any paired comparison")
    print("=" * 72)
    got = pair_ticks(A["tick_x"], Z["tick_x"])
    if got is None:
        print("could not pair within half a pitch; comparison VOID")
        return 1
    r, k, ia, slope, icpt, mdist, pitch = got
    print(f"   ALIGNED ticks {A['n_ticks']}   ZOOMNULL ticks {Z['n_ticks']}")
    print(f"   pitch {pitch:.1f} px; best index shift k={k}, {len(ia)} paired")
    print(f"   median |x_null - x_aligned| = {mdist:.2f} px  ({mdist / pitch * 100:.1f}% of a pitch)")
    print(f"   map  x_null = {slope:.6f} * x_aligned + {icpt:.2f}  (linear-map residual {r:.3f} px)")
    if k != 0:
        print(f"   NOTE: k != 0 means one arm found a graduation the other did not.")
    print(f"   pitch agreement: aligned {A['G_median_spacing_px']:.2f} px, "
          f"null {Z['G_median_spacing_px']:.2f} px "
          f"({abs(A['G_median_spacing_px'] / Z['G_median_spacing_px'] - 1) * 100:.2f}% apart)")

    # Plant on the pairing itself. A pairing that reports k=0 is a null, and a
    # null is worth nothing unless the same wiring can report a non-zero k when
    # one genuinely exists (discipline 598). Drop the null arm's first
    # graduation and the correct answer becomes k=-1 with the SAME physical
    # pairs; anything else means the criterion cannot see a slip at all.
    slipped = pair_ticks(A["tick_x"], Z["tick_x"][1:])
    if slipped is None:
        print("   PAIRING PLANT: FAIL -- a one-tick slip could not be paired at all")
        ok_pair = False
    else:
        ok_pair = slipped[1] == -1
        print(f"   PAIRING PLANT: dropped one graduation from the null arm -> "
              f"k={slipped[1]:+d}, median dist {slipped[5]:.2f} px  "
              f"{'PASS' if ok_pair else 'FAIL (expected k=-1)'}")
    controls_ok = controls_ok and ok_pair

    ra = np.array([A["S_rms_per_tick"][i] for i in ia])
    rz = np.array([Z["S_rms_per_tick"][i + k] for i in ia])
    ta = [A["tick_x"][i] for i in ia]
    tz = [Z["tick_x"][i + k] for i in ia]

    print("\n" + "=" * 72)
    print("S1 -- STRAIGHTNESS, on the common tick set. Paired difference only.")
    print("=" * 72)
    print(f"   {'tick':>6} {'x_aln':>8} {'RMS_aln':>9} {'RMS_null':>9} {'null-aln':>9}")
    for j in range(len(ia)):
        print(f"   {j:>6d} {ta[j]:>8.0f} {ra[j]:>9.4f} {rz[j]:>9.4f} {rz[j] - ra[j]:>+9.4f}")
    dif = rz - ra
    print(f"\n   median RMS   aligned {np.median(ra):.4f}   null {np.median(rz):.4f}")
    print(f"   paired difference (null - aligned): median {np.median(dif):+.4f} px")
    nb = int((dif > 0).sum())
    print(f"   ticks where aligned is straighter: {nb}/{len(dif)}")

    # A 6/14 split is not a defeat and a 12/14 split is not a rounding error.
    # Both look identical in a median, so test them.
    bt = binomtest(nb, len(dif), 0.5)
    try:
        wp = float(wilcoxon(dif).pvalue)
    except ValueError:
        wp = float("nan")
    rng = np.random.default_rng(97)
    boot = np.array([np.median(rng.choice(dif, len(dif), replace=True)) for _ in range(20000)])
    ci = (float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5)))
    print(f"   sign test p = {bt.pvalue:.4f}   Wilcoxon p = {wp:.4f}")
    print(f"   bootstrap 95% CI on the paired median: [{ci[0]:+.4f}, {ci[1]:+.4f}] px")
    sig = bt.pvalue < 0.05
    print(f"   -> the difference is {'SIGNIFICANT' if sig else 'NOT significant'} at p<0.05;"
          f" {'a direction can be claimed' if sig else 'this is a NULL, not a defeat'}")

    s1 = np.median(ra) < np.median(rz)
    print(f"   S1 VERDICT: {'PASS' if s1 else 'FAIL'}  (pre-registered FAIL if rms_aligned >= rms_null)")

    print("\n" + "=" * 72)
    print("S2 -- STEP STRUCTURE")
    print("=" * 72)
    print(f"   step median  aligned {A['S2_step_median_px']:.4f}   null {Z['S2_step_median_px']:.4f}")
    print(f"   step p90     aligned {A['S2_step_p90_px']:.4f}   null {Z['S2_step_p90_px']:.4f}")
    s2 = Z["S2_step_median_px"] > A["S2_step_median_px"]
    print(f"   S2 VERDICT: {'PASS' if s2 else 'FAIL'}")

    print("\n" + "=" * 72)
    print("S3 -- TICK SPACING, recomputed on the common set in real units")
    print("=" * 72)
    ga = g_stats(ta)
    gz = g_stats(tz)
    print(f"   aligned : projective residual {ga[0]:.4f} px = {ga[1] * 100:.3f}% of pitch"
          f"   (pitch {ga[2]:.2f} px = 1 mm)")
    print(f"   null    : projective residual {gz[0]:.4f} px = {gz[1] * 100:.3f}% of pitch"
          f"   (pitch {gz[2]:.2f} px = 1 mm)")
    s3 = ga[1] < gz[1]
    print(f"   S3 VERDICT: {'PASS' if s3 else 'FAIL'}")

    print("\n" + "=" * 72)
    print(f"OVERALL: controls {'PASS' if controls_ok else 'FAIL'} | "
          f"S1 {'PASS' if s1 else 'FAIL'} | S2 {'PASS' if s2 else 'FAIL'} | "
          f"S3 {'PASS' if s3 else 'FAIL'}")
    print("=" * 72)

    out = {
        "controls": {"placebo": ok_placebo, "shift_gain": gain, "bend_recovery": rec,
                     "direction": ok_dir, "overall": controls_ok},
        "pairing": {"k": k, "n": len(ia), "resid_px": r, "scale": slope, "offset": icpt,
                    "median_dist_px": mdist, "pitch_px": pitch},
        "S1": {"rms_aligned": float(np.median(ra)), "rms_null": float(np.median(rz)),
               "paired_median_diff": float(np.median(dif)),
               "n_aligned_better": nb, "n": len(dif),
               "sign_p": float(bt.pvalue), "wilcoxon_p": wp,
               "boot_ci": list(ci), "significant": bool(sig), "pass": bool(s1)},
        "S2": {"aligned": A["S2_step_median_px"], "null": Z["S2_step_median_px"], "pass": bool(s2)},
        "S3": {"aligned_frac": ga[1], "null_frac": gz[1], "pitch_px": ga[2], "pass": bool(s3)},
    }
    with open(rf"{O}\{TAG}-VERDICT.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
