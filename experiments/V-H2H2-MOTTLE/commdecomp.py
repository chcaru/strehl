"""Commission decomplib on synthetic pairs, where the true answer is known.

Seven arms. The ones that matter most are 1, 2 and 7.

  1 QUANTITATIVE NOISE RECOVERY. The predicted value is derived from the FILTER
    GEOMETRY, not from the image code path. For a difference of two box means of
    side m1 < m2 the kernel's sum of squares is 1/m1^2 - 1/m2^2, because the
    smaller box sits inside the larger, so white noise of sd s emerges from the
    band with sd s*sqrt(1/m1^2 - 1/m2^2). If the tool agrees with a number
    computed from arithmetic on the two radii, it is measuring what it claims.

  2 THE IDENTITY CONTROL IS A PREDICTION, NOT A SHORT-CIRCUIT. Identical arms
    give noise exactly 0 -- a suspiciously round number, and this project has now
    twice shipped a control that returned a round number because it returned
    early rather than because it computed one. So the round number is never the
    test. The test is a LADDER of near-identities at s, 2s, 4s, 8s: the recovered
    noise must come back in the ratio 1:2:4:8. A short-circuit returns a constant
    and fails this; only a live computation tracks the plant.

  7 SCENE INVARIANCE UNDER ADDED NOISE. Add independent noise to BOTH arms and
    the SCENE term must not move. This is the arm that separates a decomposition
    from a variance measurement: total variance rises with added noise, and a
    tool that reported it as scene would be a noise meter wearing a scene label.
    It is the one arm no naive statistic can pass.

and the two failure modes relayed from other lanes tonight, planted here so this
tool has to survive them rather than be asserted immune:

  5 MIXED BANDWIDTH. One term band-limited, the other not. Another lane's
    decomposition was degenerate on 3 of 3 arms and still printed a verdict. Here
    it must raise Degenerate.
  6 CORRELATED ARMS. If the two arms share frames their noise is common, the
    half-difference cancels it, and it is reported as SCENE -- an error in the
    flattering direction. Not detectable from the images, so this arm measures
    the size of the error and names the guard that prevents it.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bandlib  # noqa: E402
import decomplib  # noqa: E402

LO, HI = 20, 60
RNG = np.random.default_rng(20260824)
FAIL = []


def check(name, ok, detail):
    print("  %-4s %-34s %s" % ("PASS" if ok else "FAIL", name, detail))
    if not ok:
        FAIL.append(name)


def lv(a, b):
    """Certify a pair's gains. In commissioning the synthetic arrays ARE the whole
    arms, so this is the same call the ladder makes on full renders."""
    return decomplib.check_pair_levels(a, b)


def dec(a, b, lo=LO, hi=HI):
    return decomplib.decompose(a, b, lo, hi, lv(a, b))


def scene_field(h=512, w=512):
    """A scene with structure at many scales, and no noise in it."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float64)
    s = 40.0 * np.sin(x / 7.0) * np.cos(y / 11.0)
    s += 25.0 * np.sin((x + y) / 31.0)
    s += 30.0 * ((x // 37 + y // 41) % 2)
    return s + 128.0


def band_gain(lo, hi):
    """sqrt of the band filter's white-noise variance gain, from geometry alone."""
    m1, m2 = 2 * (lo // 2) + 1, 2 * (hi // 2) + 1
    return float(np.sqrt(1.0 / m1**2 - 1.0 / m2**2))


print("commissioning decomplib  band %d-%d px" % (LO, HI))
S = scene_field()

# ---- 1. quantitative noise recovery against an analytic prediction ------------
print("\n1. noise recovery vs the filter's analytic white-noise gain")
g = band_gain(LO, HI)
for sigma in (2.0, 8.0):
    a = S + RNG.normal(0, sigma, S.shape)
    b = S + RNG.normal(0, sigma, S.shape)
    _, nse = dec(a, b)
    want = sigma * g
    err = abs(nse - want) / want
    check("sigma=%.0f" % sigma, err < 0.03,
          "recovered %.4f  predicted %.4f (= %.1f x %.6f)  err %.2f%%"
          % (nse, want, sigma, g, 100 * err))

# ---- 2. the identity control, and proof it is not a short-circuit -------------
print("\n2. identity, then a ladder proving the identity value is computed")
a = S.copy()
sc0, nse0 = dec(a, a.copy())
check("identical arms -> noise 0", nse0 == 0.0, "noise %.6g, scene %.4f" % (nse0, sc0))
base = None
ratios = []
for k, mult in enumerate((1, 2, 4, 8)):
    s = 0.35 * mult
    b = a + RNG.normal(0, s, S.shape)
    _, nse = dec(a, b)
    if base is None:
        base = nse
    ratios.append(nse / base)
    print("      s = %.2f -> noise %.5f  (ratio to first %.4f, want %d)"
          % (s, nse, nse / base, mult))
worst = max(abs(r - m) / m for r, m in zip(ratios, (1, 2, 4, 8)))
check("noise tracks the plant 1:2:4:8", worst < 0.05,
      "worst deviation %.2f%%; a short-circuit returns a constant and reads 87.5%% here"
      % (100 * worst))

# ---- 3/4. a degradation and an improvement, in both directions ---------------
# The first attempt planted a boxblur of radius 3 and the tool scored it 0.9584,
# below the 0.75 the arm demanded. Measuring the plant itself settled who was at
# fault: r=3 moves the 20-60 px band by 4%, r=15 by 52%. The PLANT was under-
# powered, not the tool -- a defect outside the band under test is not a defect
# this band should report, and an arm that demanded otherwise was asking the
# statistic to respond to something it is designed to ignore. Both plants are now
# built at the band's own scale.
print("\n3/4. scene term must FALL on blur and RISE on sharpening (plants at band scale)")
sigma = 3.0
na, nb = RNG.normal(0, sigma, S.shape), RNG.normal(0, sigma, S.shape)
sc_ref, nse_ref = dec(S + na, S + nb)
Sb = bandlib.boxblur(S, 15)
sc_bl, _ = dec(Sb + na, Sb + nb)
check("blur lowers scene", sc_bl < 0.75 * sc_ref,
      "scene %.4f -> %.4f  (x%.4f)" % (sc_ref, sc_bl, sc_bl / sc_ref))
Ss = S + 0.8 * (S - bandlib.boxblur(S, 15))
sc_sh, _ = dec(Ss + na, Ss + nb)
check("sharpening raises scene", sc_sh > 1.15 * sc_ref,
      "scene %.4f -> %.4f  (x%.4f)" % (sc_ref, sc_sh, sc_sh / sc_ref))

# ---- 5. bandwidth mixing: where the guard fires, and where it cannot ----------
print("\n5. planted defect: one term band-limited, the other full-band")
# 5a. The loud case -- a flat, noise-dominated region, which is precisely the
# content another lane's decomposition was degenerate on. Here the unfiltered
# term dwarfs the band-limited one and the impossibility is visible.
flat = np.full_like(S, 128.0)
fa, fb = flat + RNG.normal(0, sigma, S.shape), flat + RNG.normal(0, sigma, S.shape)
v_tot_f = float(np.var(decomplib.bandpass((fa + fb) / 2.0, LO, HI)))
v_nse_f = float(np.var((fa - fb) / 2.0))
check("5a loud case is caught", v_nse_f > v_tot_f,
      "flat ROI: full-band half-diff var %.4g exceeds band-limited half-sum var %.4g "
      "by %.0fx -- impossible for additive noise" % (v_nse_f, v_tot_f, v_nse_f / v_tot_f))
# 5b. The quiet case -- scene-dominated content. The guard stays silent and the
# answer is merely WRONG, by about a percent. Reported as a limitation because it
# is one: the real defence is structural, not this check.
v_tot_q = float(np.var(decomplib.bandpass((S + na + S + nb) / 2.0, LO, HI)))
v_nse_q = float(np.var(((S + na) - (S + nb)) / 2.0))
quiet_err = abs(np.sqrt(max(v_tot_q - v_nse_q, 0.0)) - sc_ref) / sc_ref
check("5b quiet case is a stated blind spot", v_nse_q < v_tot_q and quiet_err < 0.05,
      "scene-dominated ROI: guard silent, scene biased %.2f%%. decompose() builds "
      "both terms from ONE filter argument and exposes no way to pass two, which is "
      "what actually prevents this." % (100 * quiet_err))
# 5c. A construction that genuinely violates the inequality, to prove the guard
# in decompose() is live rather than unreachable.
anti = 2.0 * float(np.mean(S)) - (S + na)
try:
    dec(S + nb, anti)
    raised = False
    why = "NO exception -- the guard is unreachable"
except decomplib.Degenerate as e:
    raised = True
    why = str(e)[:96]
check("5c decompose() raises when violated", raised, why)
# The guard was loosened to a significance test after it refused a real flat ROI
# whose scene really is zero. These two arms are what stop that loosening from
# being a quiet disabling: a true-zero scene must be ADMITTED and reported as
# zero, and the loud violation above must still fire.
pure_a, pure_b = 128.0 + RNG.normal(0, 3.0, S.shape), 128.0 + RNG.normal(0, 3.0, S.shape)
try:
    sc_zero, ns_zero = dec(pure_a, pure_b)
    admitted, why3 = True, ("scene %.5f, noise %.5f -- a scene of zero is reported as "
                            "zero, not refused" % (sc_zero, ns_zero))
except decomplib.Degenerate as e:
    admitted, why3 = False, "REFUSED a true-zero scene: " + str(e)[:80]
check("5e zero scene admitted, not refused", admitted, why3)

# ---- 5d. the gain mismatch the variance guard provably cannot see -------------
print("\n5d. gain mismatch: measured blind to the variance guard, so guarded apart")
# The band filter's own arithmetic, which is why this guard tests spread and not
# level: an additive offset cannot reach any number reported here, a gain can.
t = S[:256, :256]
b_off = float(np.std(decomplib.bandpass(t + 10.0, LO, HI)))
b_gai = float(np.std(decomplib.bandpass(t * 1.04, LO, HI)))
b_ref = float(np.std(decomplib.bandpass(t, LO, HI)))
check("offset is invisible, gain is not", abs(b_off - b_ref) < 1e-9
      and abs(b_gai / b_ref - 1.04) < 1e-6,
      "band sd %.6f -> %.6f under +10 offset, -> %.6f under x1.04 gain (x%.4f)"
      % (b_ref, b_off, b_gai, b_gai / b_ref))
big = (S + nb) * 40.0
v_hs = float(np.var(decomplib.bandpass((S + na + big) / 2.0, LO, HI)))
v_hd = float(np.var(decomplib.bandpass((S + na - big) / 2.0, LO, HI)))
check("variance guard is blind to 40x gain", v_hd < v_hs,
      "half-sum var %.4g vs half-diff var %.4g, ratio %.4f -- both dominated by the "
      "scaled arm, so the inequality holds and nothing fires" % (v_hs, v_hd, v_hs / v_hd))
try:
    dec(S + na, big)
    caught_gain, why = False, "NO exception -- an exposure mismatch would print a number"
except decomplib.Degenerate as e:
    caught_gain, why = True, str(e)[:110]
check("level guard catches it", caught_gain, why)
# The guard must not be always-on, and with a significance threshold the right
# way to show that is a two-sided calibration against its own measured floor
# rather than against a fixed percentage. The previous version of this arm
# planted 0.5% and demanded admission; the significance-based guard correctly
# REFUSED it, because on a synthetic pair the floor is far below 0.5% and a 0.5%
# gain really is detectable there. The arm's premise was obsolete, not the guard
# -- so the plant is now sized in units of the floor the guard reports.
tok_cal = lv(S + na, S + nb)
half, twice = 1.0 + tok_cal.bound / 2.0, 1.0 + tok_cal.bound * 2.0
try:
    dec(S + na, (S + nb) * half)
    admits_below = True
except decomplib.Degenerate:
    admits_below = False
try:
    dec(S + na, (S + nb) * twice)
    refuses_above = False
except decomplib.Degenerate:
    refuses_above = True
check("guard is calibrated, not always-on", admits_below and refuses_above,
      "floor %.3f%%: a gain of half the floor (%.3f%%) is admitted=%s, twice the floor "
      "(%.3f%%) is refused=%s" % (100 * tok_cal.bound, 100 * (half - 1), admits_below,
                                  100 * (twice - 1), refuses_above))
# The misfire this guard was rebuilt for: same scene, same exposure, noise so
# large that the arms' sample means separate by more than the flat tolerance.
loud_a = S + RNG.normal(0, 800.0, S.shape)
loud_b = S + RNG.normal(0, 800.0, S.shape)
try:
    dec(loud_a, loud_b)
    no_misfire = True
    detail = "same-scene arms at noise sd 800 (relative level gap %.2f%%) are admitted" \
             % (100 * abs(np.mean(loud_a) - np.mean(loud_b)) / np.mean(loud_a))
except decomplib.Degenerate as e:
    no_misfire, detail = False, "MISFIRE: " + str(e)[:90]
check("no misfire on loud identical-exposure arms", no_misfire, detail)
# A pure additive offset must be ADMITTED: it cannot reach any reported number,
# and refusing it threw away a real measurement once already.
try:
    dec(S + na, S + nb + 12.0)
    off_ok, why4 = True, "an arm offset by +12 codes is admitted (the band filter " \
                         "removes it exactly)"
except decomplib.Degenerate as e:
    off_ok, why4 = False, "REFUSED a harmless offset: " + str(e)[:80]
check("additive offset admitted", off_ok, why4)
# ...and the arm that proves the significance test did not simply disable it.
try:
    dec(S + na, (S + nb) * 1.03)
    still_fires, why2 = False, "a 3% gain mismatch at realistic noise was ADMITTED -- " \
                               "the z test neutered the guard"
except decomplib.Degenerate as e:
    still_fires, why2 = True, str(e)[:104]
check("still catches 3% gain at real noise", still_fires, why2)

# ---- 5f. the gain the guard CANNOT rule out, and what it costs ----------------
# The guard has a measured floor, so a residual gain always survives it. Reporting
# a noise number without saying what that residual could have done to it is the
# same omission as reporting a noise number without a sharpness number. The bound
# is eps^2 * r^2 / 4 and it is only worth printing if it PREDICTS: so a gain of
# exactly the certified floor is planted, the resulting bias is measured, and the
# bound must sit above it without being absurdly above it.
print("\n5f. the residual gain the guard cannot see is bounded, and the bound predicts")
lv_ref = lv(S + na, S + nb)
eps = lv_ref.bound
# A single draw is not enough to test a bound: the noise estimate has its own
# scatter, and the first version of this arm needed a 1.35x slack factor to admit
# a measured +0.86% against a 0.75% bound. A slack factor chosen to make an arm
# pass is not a test. The bias is a property of the expectation, so it is measured
# as one, over draws, and compared to the bound with its own standard error.
NDRAW = 24
for r_target, noise_sd in (("low", 60.0), ("high", 6.0)):
    biases, rs, bounds, floors = [], [], [], []
    for _ in range(NDRAW):
        ca = S + RNG.normal(0, noise_sd, S.shape)
        cb = S + RNG.normal(0, noise_sd, S.shape)
        tok = lv(ca, cb)
        s_c, n_c = decomplib.decompose(ca, cb, LO, HI, tok)
        # the same pair carrying the largest gain the guard would have admitted
        _, n_g = decomplib.decompose(ca, cb * (1.0 + tok.bound), LO, HI, tok)
        biases.append(n_g / n_c - 1.0)
        rs.append(s_c / n_c)
        bounds.append(decomplib.noise_bias(tok, s_c, n_c))
        floors.append(tok.bound)
    mb = float(np.mean(biases))
    se = float(np.std(biases, ddof=1)) / np.sqrt(NDRAW)
    bd = float(np.mean(bounds))
    check("5f bound holds (%s r)" % r_target, 0.0 <= mb <= bd + 2.0 * se,
          "r %6.1f, floor %.3f%%: measured bias %+.3f%% +- %.3f%% over %d draws, "
          "bound %.3f%%  (%s)"
          % (float(np.mean(rs)), 100 * float(np.mean(floors)), 100 * mb, 100 * se,
             NDRAW, 100 * bd,
             "bound holds" if mb <= bd else "EXCEEDED by %.2f se" % ((mb - bd) / se)))
check("5f bound rises with r", True,
      "eps %.4f%%; the same certified pair bounds the noise term to %.2f%% at r=1 and "
      "%.1f%% at r=100 -- one pair, two verdicts, which is why a flat tolerance cannot "
      "express this" % (100 * eps, 100 * (eps / 2 + eps ** 2 / 4),
                        100 * (eps / 2 + eps ** 2 * 1e4 / 4)))

# ---- 6. correlated arms: the error this tool cannot see from the images -------
print("\n6. blind spot: arms sharing noise (guarded in staging, not here)")
sc_ok, nse_ok = dec(S + na, S + nb)
sc_bad, nse_bad = dec(S + na, S + na)
check("shared noise inflates scene", sc_bad > sc_ok and nse_bad == 0.0,
      "disjoint: scene %.4f noise %.4f | shared: scene %.4f noise %.4f -- noise is "
      "reported as scene, inflating it %.2f%%. stage_ladder.ps1 asserts the arms are "
      "disjoint; that assertion is this tool's only defence."
      % (sc_ok, nse_ok, sc_bad, nse_bad, 100 * (sc_bad / sc_ok - 1)))

# ---- 7. THE arm: is the scene term ACCURATE, not merely stable ---------------
# Two earlier versions of this arm were wrong in opposite directions. The first
# planted noise too small to move the foil, so a plain variance meter passed it
# and the arm proved nothing. The second planted noise large enough to bite and
# then demanded 2% stability, which at a band noise-to-scene variance ratio of
# 2.7 is beyond what any unbiased estimator can deliver -- subtracting two large
# numbers to leave a small one carries sampling error, and that is statistics,
# not a defect.
#
# The scene is synthetic, so its true band content is KNOWN. That makes the right
# question accuracy rather than stability: averaged over independent draws, does
# the estimate land on the truth? Bias is the property that would invalidate the
# ladder; scatter is a quantified cost, reported rather than hidden.
#
# A THIRD VERSION, because the second read -5.10% at sigma 800 and 8 draws and
# called it a bias. It was not. At 96 draws the same configuration reads -0.440%
# with z = 0.28. Eight draws could not resolve a 5% bias -- per-draw scatter is
# 15.7% there -- so the arm was comparing an unresolved number against a fixed
# threshold, which is once more an absolute tolerance on a quantity whose
# uncertainty varies. The arm now tests bias against its OWN standard error and
# prints the smallest bias it could have detected, so a verdict of "unbiased"
# carries the precision it was reached at.
print("\n7. scene accuracy against known truth (a variance meter must FAIL this)")
REPS = 64
truth = float(np.var(decomplib.bandpass(S, LO, HI)))
print("      true band variance of the scene: %.4f (sd %.4f), %d draws per plant"
      % (truth, np.sqrt(truth), REPS))
worst_z, worst_naive, worst_limit = 0.0, 0.0, 0.0
for sigma in (2.0, 200.0, 800.0):
    ests, naives = [], []
    for _ in range(REPS):
        a = S + RNG.normal(0, sigma, S.shape)
        b = S + RNG.normal(0, sigma, S.shape)
        sc, _ = dec(a, b)
        if sc <= 0.0:
            check("sigma=%.0f no clipped draw" % sigma, False, "a draw clipped to zero")
        ests.append(sc ** 2)
        naives.append(float(np.var(decomplib.bandpass((a + b) / 2.0, LO, HI))))
    bias = float(np.mean(ests)) / truth - 1.0
    se = float(np.std(ests, ddof=1)) / np.sqrt(REPS) / truth
    z = abs(bias) / max(se, 1e-12)
    nbias = float(np.mean(naives)) / truth - 1.0
    worst_z, worst_naive = max(worst_z, z), max(worst_naive, abs(nbias))
    worst_limit = max(worst_limit, 3 * se)
    print("      sigma %6.1f -> bias %+7.3f%% +- %.3f%% (z %.2f), detects a bias down "
          "to %.2f%%  |  variance meter %+8.1f%%"
          % (sigma, 100 * bias, 100 * se, z, 300 * se, 100 * nbias))
check("the foil actually fails", worst_naive > 0.30,
      "the variance meter's bias reaches %.0f%% (must exceed 30%% or this arm is "
      "inert and its verdict means nothing)" % (100 * worst_naive))
check("scene unbiased across 400x noise", worst_z < 3.0,
      "worst |bias| is %.2f standard errors from zero; the arm would have caught any "
      "bias above %.2f%%, against the meter's %.0f%%"
      % (worst_z, 100 * worst_limit, 100 * worst_naive))

print("\n%s  (%d arm(s) failed)" % ("GREEN" if not FAIL else "RED: " + ", ".join(FAIL),
                                    len(FAIL)))
sys.exit(1 if FAIL else 0)
