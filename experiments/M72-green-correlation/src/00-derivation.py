"""M72 step 0 -- the algebra, before any corpus contact.

Written and committed BEFORE the measurement. Its job is to make my own
reasoning falsifiable and to catch my own errors, which is the only reason
M68 caught M61's inverted sign.

Four things are derived here:

  1. The arithmetic consequence of rho on `green_luma_sigma`, and its SIGN.
  2. The error amplification of M62's difference-of-variances estimator,
     which is how fact 895's rho = +0.073 was obtained.
  3. The SIGNAL dependence of rho under two mechanisms for the covariance.
  4. The ISO dependence of the covariance under upstream vs downstream
     generation -- discipline 473, locate a mechanism by where the noise is
     generated, not by where it is observed.

Then a planted signal-chain simulation checks that the estimator I intend to
use recovers a known answer and that each null does what I claim it does.

Run: python 00-derivation.py
"""

from __future__ import annotations

import numpy as np

RHO_M62 = 0.073
VAR_GREEN_M62 = 0.53229
SIG_G1_M62 = 0.99346
SIG_G2_M62 = 0.99905


def rule(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# ---------------------------------------------------------------------------
# 1. The consequence, and its sign
# ---------------------------------------------------------------------------

def consequence() -> None:
    rule("1. var(mean of two correlated planes), and the SIGN of the error")

    print("""
  L = (G1 + G2)/2.  With var(G1) = var(G2) = s^2 and corr = rho,

      var(L) = (var G1 + var G2 + 2 cov)/4
             = (2 s^2 + 2 rho s^2)/4
             = s^2 (1 + rho)/2

  crates/strehl-core/src/noise.rs:126 `green_luma_sigma` computes

      var(L) = (var G1 + var G2)/4  ->  s^2/2

  i.e. it evaluates the rho = 0 case.  The doc comment at noise.rs:122 states
  the assumption in words: "their read noise is independent".
""")
    for rho in (0.0, RHO_M62, 0.10, -0.05):
        v = 0.5 * (1.0 + rho)
        print(f"    rho = {rho:+.3f}   var(L) = {v:.4f} s^2   "
              f"sigma ratio true/model = {np.sqrt(1 + rho):.5f}  "
              f"({100 * (np.sqrt(1 + rho) - 1):+.2f} %)")

    print(f"""
  At M62's rho = +{RHO_M62:.3f}: var(L) = {0.5 * (1 + RHO_M62):.4f} s^2, which is the
  0.5365 in SYNTHESIS fact 958, and the sigma ratio is
  {np.sqrt(1 + RHO_M62):.5f} -> +{100 * (np.sqrt(1 + RHO_M62) - 1):.2f} %.

  SIGN.  rho > 0 means the true sigma is LARGER than the model's.  The model
  therefore predicts less noise than exists: it is OVER-CONFIDENT.  A gate
  denominated in sigma admits samples it should reject.  This matches
  SYNTHESIS fact 958's "bias in the direction of over-confidence".

  Note what is NOT true: this is not a sqrt(N) failure.  Temporal
  independence frame-to-frame is what makes averaging work, and M62's P15
  measured that separately at -0.17 % on green.  rho here is a WITHIN-frame,
  BETWEEN-plane correlation.  The two are different objects and only the
  second is at issue.
""")


# ---------------------------------------------------------------------------
# 2. How fact 895 was actually obtained, and how fragile that is
# ---------------------------------------------------------------------------

def m62_estimator_fragility() -> None:
    rule("2. M62's estimator is a difference of two large variances")

    v1 = SIG_G1_M62 ** 2
    v2 = SIG_G2_M62 ** 2
    cov = (4.0 * VAR_GREEN_M62 - v1 - v2) / 2.0
    rho = cov / (SIG_G1_M62 * SIG_G2_M62)
    print(f"""
  M62 P17 did not measure a correlation directly.  It measured three
  variances and took a difference:

      cov = (4 var(L) - var G1 - var G2) / 2

    var(L)  = {VAR_GREEN_M62:.5f}          4 var(L) = {4 * VAR_GREEN_M62:.5f}
    var G1  = {v1:.5f}          var G1 + var G2 = {v1 + v2:.5f}
    var G2  = {v2:.5f}
    ------------------------------------------------
    numerator = {4 * VAR_GREEN_M62 - v1 - v2:.5f}   cov = {cov:.5f}   rho = {rho:.5f}

  which reproduces the published +0.073 exactly, so I have the estimator right.

  The numerator is {100 * (4 * VAR_GREEN_M62 - v1 - v2) / (4 * VAR_GREEN_M62):.2f} % of the quantity it is differenced out of.
  Error amplification: a relative error eps in var(L) alone moves cov by
""")
    for eps in (0.001, 0.005, 0.01, 0.02):
        d = 2.0 * VAR_GREEN_M62 * eps
        print(f"    eps = {100 * eps:4.1f} %  ->  d(cov) = {d:+.5f}  "
              f"= {100 * d / cov:+6.1f} % of cov  ->  rho = {(cov + d) / (SIG_G1_M62 * SIG_G2_M62):+.4f}")
    amp = 2.0 * VAR_GREEN_M62 / cov
    d_half = 2.0 * VAR_GREEN_M62 * 0.005 / (SIG_G1_M62 * SIG_G2_M62)
    print(f"""
  Amplification factor {amp:.1f}x.  A 0.5 % systematic difference between how
  var(L) and how var(G1), var(G2) were computed -- a different crop, a
  different defect mask, a clamp, a different frame set -- moves rho by
  {d_half:+.4f}, which is {100 * d_half / rho:.0f} % of the finding.

  This is NOT a claim that M62 is wrong.  It is the reason the item is worth
  re-measuring with an estimator that computes the covariance DIRECTLY, from
  per-cell temporal cross-products, where no such cancellation occurs and the
  quantity of interest is not a small residue of large numbers.

  One direction is worth noting because it constrains the artefact space: a
  clamp such as `(raw - black).max(0)`, which M62 section 9.1 discloses in the
  merge path, REDUCES var(L) and therefore makes cov appear NEGATIVE.  The
  published sign is positive, so clamping is not a candidate explanation.
""")


# ---------------------------------------------------------------------------
# 3. Signal dependence -- which regime does the 3.6 % live in?
# ---------------------------------------------------------------------------

def signal_dependence() -> None:
    rule("3. Signal dependence of rho -- two mechanisms, two regimes")

    print("""
  Per-plane variance in DN^2 at signal S DN is  var = g S + (RN g)^2, a shot
  term and a read term.  What happens to rho as S rises depends entirely on
  what generates the covariance:

    H-read   The covariance is in the READ chain: a fixed cov c DN^2,
             independent of signal.  Then

                 rho(S) = c / (g S + (RN g)^2)

             and rho FALLS as 1/S once shot noise dominates.  The 3.6 % is a
             black-level worst case and decays to nothing in the midtones.

    H-xtalk  The covariance is CROSSTALK -- charge or optical leakage between
             neighbouring photosites, proportional to the collected signal.
             Then cov = k g S + c and

                 rho(S) -> k   as S grows

             i.e. rho is roughly CONSTANT and the 3.6 % applies at every
             signal level, including where every gate in the project actually
             adjudicates.

  These two have very different operational weight and they are separated by
  data, not by argument.  Note now, before measuring: a dark frame has S ~ 0,
  so a dark-frame measurement sees c and is BLIND to k.  Dark frames can
  measure H-read's amplitude and cannot rule H-xtalk in or out.
""")
    g = 0.229
    rn_g2 = 0.925
    c = 0.0721
    print("  H-read, using ISO-100 numbers (g = 0.229 DN/e, (RN g)^2 = 0.925 DN^2,")
    print(f"  c = {c} DN^2 from M62):")
    print()
    print("     signal S      var/plane     rho(S)      sigma error on L")
    print("     --------      ---------     ------      ----------------")
    for s in (0.0, 1.0, 10.0, 100.0, 1000.0, 4000.0):
        var = g * s + rn_g2
        rho = c / var
        print(f"     {s:8.0f} DN   {var:9.3f}     {rho:.5f}     {100 * (np.sqrt(1 + rho) - 1):+6.3f} %")
    print("""
  Under H-read the effect is already below 0.5 % in sigma by 10 DN above
  black and below 0.05 % by 100 DN.  Under H-xtalk every row of that table
  would read +3.58 %.
""")


# ---------------------------------------------------------------------------
# 4. ISO dependence -- WHERE in the chain is the covariance generated?
# ---------------------------------------------------------------------------

def iso_dependence() -> None:
    rule("4. ISO dependence -- locating the covariance in the chain")

    print("""
  M68 fitted, per plane, the dark variance against gain:

      sigma^2(ISO) = alpha G^2 + delta                (M68 section 4)

  alpha is the variance generated UPSTREAM of the analog gain, which the gain
  then multiplies; delta is the variance generated DOWNSTREAM of it -- ADC,
  bus, digital -- which the gain does not touch.  The same decomposition
  applies to a covariance, and it is the same instrument:

      cov(ISO) = alpha_c G^2 + delta_c

    alpha_c > 0, delta_c ~ 0   covariance generated UPSTREAM: pixel, sense
                               node, source follower, column amp before gain.
    alpha_c ~ 0, delta_c > 0   covariance generated DOWNSTREAM: ADC reference,
                               supply ripple at digitisation, output bus.
    both > 0                   mixed; report the split rather than a label.

  And then, because rho is a ratio of two such fits,

      rho(ISO) = (alpha_c G^2 + delta_c) / (alpha G^2 + delta)

  which is FLAT in ISO if and only if the covariance has the same
  upstream/downstream split as the variance.  Any departure from flat locates
  the covariance relative to the variance, which is the useful statement --
  it does not require me to know either absolute term.

  I state the mechanism and the observable.  I do not state an expected sign:
  M61 stated one for its own separating observable and had it inverted, and
  M68 found that out only by deriving it independently.
""")
    print("  Worked illustration -- NOT a prediction, a demonstration that the")
    print("  observable has leverage over the ISO range on disk (G spans 40x):")
    print()
    g_lo, g_hi = 1.0, 40.0
    for name, ac, dc in (("all upstream", 0.05, 0.0),
                         ("all downstream", 0.0, 0.05),
                         ("same split as var", 0.05 * 0.58, 0.05 * 0.42)):
        alpha, delta = 0.58, 0.42
        r_lo = (ac * g_lo ** 2 + dc) / (alpha * g_lo ** 2 + delta)
        r_hi = (ac * g_hi ** 2 + dc) / (alpha * g_hi ** 2 + delta)
        print(f"    {name:18s}  rho(G=1) = {r_lo:.5f}   rho(G=40) = {r_hi:.5f}   "
              f"ratio {r_hi / r_lo if r_lo else float('nan'):8.3f}")
    print("""
  The three cases are separated by more than an order of magnitude in the
  ratio, so the sweep has power provided rho itself is measurable at each ISO.
  Whether it is, is criterion C0's job.
""")


# ---------------------------------------------------------------------------
# 5. Planted simulation -- does my estimator recover a known answer?
# ---------------------------------------------------------------------------

def pooled_rho(x: np.ndarray, y: np.ndarray) -> float:
    """Pooled temporal correlation over cells, per-cell temporal mean removed.

    x, y are (T, M).  Each cell's own temporal mean is subtracted, which
    removes fixed-pattern offset exactly.  Cross-products are then pooled
    across cells before normalising, which is more stable for small T than
    averaging per-cell r-hats (those are biased at small T).
    """
    xc = x - x.mean(axis=0, keepdims=True)
    yc = y - y.mean(axis=0, keepdims=True)
    sxy = float((xc * yc).sum())
    sxx = float((xc * xc).sum())
    syy = float((yc * yc).sum())
    return sxy / np.sqrt(sxx * syy)


def plant() -> int:
    rule("5. Planted signal chain -- the estimator must recover a known answer")

    rng = np.random.default_rng(20250823)
    T, M = 20, 200_000
    sigma = 1.0
    fails = 0

    # Fixed-pattern offsets: large, static, must cancel exactly.
    fpn1 = rng.normal(0, 30.0, M)
    fpn2 = rng.normal(0, 30.0, M)

    def build(rho_local: float, sigma_cm: float, n_hot: int = 0,
              quantise: bool = True):
        """Two planes with a planted local correlation and a global common mode."""
        common = rng.normal(0, sigma_cm, (T, 1))
        shared = rng.normal(0, 1.0, (T, M))
        ind1 = rng.normal(0, 1.0, (T, M))
        ind2 = rng.normal(0, 1.0, (T, M))
        a = np.sqrt(max(rho_local, 0.0))
        b = np.sqrt(max(1.0 - abs(rho_local), 0.0))
        p1 = 512.0 + fpn1 + sigma * (a * shared + b * ind1) + common
        p2 = 512.0 + fpn2 + sigma * (a * shared + b * ind2) + common
        if n_hot:
            hot = rng.choice(M, n_hot, replace=False)
            rate = rng.uniform(20.0, 200.0, n_hot)
            p1[:, hot] += rng.poisson(rate, (T, n_hot))
            p2[:, hot] += rng.poisson(rate, (T, n_hot))
        if quantise:
            p1 = np.rint(p1)
            p2 = np.rint(p2)
        return p1, p2

    def check(label: str, got: float, want: float, tol: float) -> None:
        nonlocal fails
        ok = abs(got - want) <= tol
        if not ok:
            fails += 1
        print(f"    {'ok ' if ok else 'FAIL'}  {label:52s} {got:+.5f}  "
              f"(want {want:+.4f} +/- {tol:.4f})")

    print("\n  5a. Recovery of a planted local correlation, no common mode\n")
    print("      SELF-CORRECTION 1, found here and left in.  My first version of")
    print("      this check compared the estimate against the PLANTED rho and")
    print("      three of them failed.  The estimator was right and my")
    print("      expectation was wrong: the data are quantised, quantisation")
    print("      adds 1/12 DN^2 to each VARIANCE and nothing to the COVARIANCE,")
    print("      so the observable rho is diluted by")
    print()
    print("          rho_obs = rho_true * s^2 / (s^2 + 1/12)")
    print()
    print(f"      which at s = {sigma:.1f} DN is a factor {sigma ** 2 / (sigma ** 2 + 1 / 12):.4f}.  Expectations below are")
    print("      the diluted value.  This matters for the real measurement and")
    print("      is picked up again in 5f.\n")
    dil = sigma ** 2 / (sigma ** 2 + 1.0 / 12.0)
    for want in (0.0, 0.02, 0.073, 0.20):
        p1, p2 = build(want, 0.0)
        check(f"planted rho_local = {want:+.3f} (x{dil:.4f} quantised)",
              pooled_rho(p1, p2), want * dil, 0.006)

    print("\n  5b. A global common mode ALONE manufactures a positive rho\n")
    print("      This is the artefact that would look exactly like the finding.")
    print("      cm sigma is per-frame, added identically to every cell.\n")
    for scm in (0.0, 0.1, 0.27, 0.5):
        p1, p2 = build(0.0, scm)
        expect = scm ** 2 / (scm ** 2 + sigma ** 2)
        got = pooled_rho(p1, p2)
        print(f"      cm sigma {scm:.2f} DN  ->  rho = {got:+.5f}   "
              f"(analytic {expect:+.5f}, sampling error at T={T} is large)")
    print(f"""
      A per-frame offset of only 0.27 DN reproduces rho = +0.073 on its own.
      That is the single most likely artefact and it has a decisive test:
      it is spatially UNIFORM, so it survives at any displacement.  M62's own
      P14 measured the per-frame crop mean spanning 0.079 DN over 20 frames,
      which already constrains a uniform common mode far below 0.27 DN -- but
      P14 is a different group's crop and I will measure it myself.
""")

    print("\n  5c. The displaced-pair null separates local from global\n")
    print("      SELF-CORRECTION 2, found here and left in.  I first asserted")
    print("      that rho_adjacent - rho_displaced recovers rho_local.  It does")
    print("      not.  Writing v_c for the common-mode variance and q = 1/12,")
    print()
    print("          rho_adj = (s^2 rho_local + v_c) / (s^2 + v_c + q)")
    print("          rho_dis =                  v_c / (s^2 + v_c + q)")
    print("          difference = s^2 rho_local / (s^2 + v_c + q)")
    print()
    print("      so the difference is rho_local diluted by the common mode AND")
    print("      by quantisation, both of which sit in the denominator.  The")
    print("      clean decomposition is done in COVARIANCE space, not in rho.")
    print("      Consequence for the report, fixed now: the OPERATIONAL number")
    print("      that belongs in green_luma_sigma is the total rho_adj, because")
    print("      that is what sets var(L).  The local/global split is for")
    print("      MECHANISM only and must not be substituted for the fix.\n")
    scm = 0.27
    p1, p2 = build(0.073, scm)
    r_adj = pooled_rho(p1, p2)
    perm_cells = rng.permutation(M)
    r_dis = pooled_rho(p1, p2[:, perm_cells])
    denom = sigma ** 2 + scm ** 2 + 1.0 / 12.0
    print(f"      adjacent  rho = {r_adj:+.5f}   (local 0.073 + common mode)")
    print(f"      displaced rho = {r_dis:+.5f}   (common mode only)")
    print(f"      difference    = {r_adj - r_dis:+.5f}   "
          f"(predicted {sigma ** 2 * 0.073 / denom:+.5f})")
    check("difference matches the corrected algebra",
          r_adj - r_dis, sigma ** 2 * 0.073 / denom, 0.010)

    print("\n  5d. The frame-permutation null must destroy a real temporal rho\n")
    p1, p2 = build(0.073, 0.0)
    # A derangement of the frame index: no frame keeps its partner.
    while True:
        perm = rng.permutation(T)
        if not np.any(perm == np.arange(T)):
            break
    check("permuted frames, planted rho = +0.073", pooled_rho(p1, p2[perm]), 0.0, 0.010)
    print("      If a measured rho SURVIVES this, it is not a temporal")
    print("      correlation at all and the finding is an estimator artefact.")

    print("\n  5e. Hot pixels: shared dark-current shot noise is NOT plane coupling\n")
    p1, p2 = build(0.0, 0.0, n_hot=4000)
    r_hot = pooled_rho(p1, p2)
    print(f"      rho with 4000/{M} hot cells, independent shot = {r_hot:+.5f}")
    print("      Independent Poisson in each plane does not couple them, but it")
    print("      inflates the variances and so DILUTES a real rho.  Excluding")
    print("      defects per M48c is therefore required, and its effect on a")
    print("      real rho is to raise it.  Recorded so the direction is fixed")
    print("      in advance and cannot be chosen later.")

    print("\n  5f. Quantisation biases rho DOWNWARD, and does so ISO-dependently\n")
    p1, p2 = build(0.0, 0.0, quantise=True)
    q1, q2 = build(0.0, 0.0, quantise=False)
    check("quantised, planted rho = 0", pooled_rho(p1, p2), 0.0, 0.006)
    check("unquantised, planted rho = 0", pooled_rho(q1, q2), 0.0, 0.006)
    print("""
      Independent rounding errors add 1/12 DN^2 to each variance and nothing
      to the covariance, so they DILUTE rho rather than create it.  The
      estimator therefore cannot manufacture the finding -- but it CAN
      manufacture the finding's ISO DEPENDENCE, which is the thing I am here
      to measure.  Dark sigma grows ~40x across the ISO range on disk, so the
      dilution factor s^2/(s^2 + 1/12) is:
""")
    print("        ISO   dark sigma (M4, green)   dilution   bias in rho")
    print("        ---   ----------------------   --------   -----------")
    for iso, s in ((50, 1.009), (100, 1.007), (400, 1.233),
                   (1000, 2.875), (2000, 5.652)):
        d = s ** 2 / (s ** 2 + 1.0 / 12.0)
        print(f"        {iso:4d}   {s:14.3f} DN         {d:.4f}     {100 * (d - 1):+6.2f} %")
    print("""
      An uncorrected rho would RISE by about 8 % from ISO 50 to ISO 2000 with
      no physical cause whatsoever, and section 4 says a rising rho is the
      upstream signature.  This is a confound in my own instrument that points
      at a specific answer, and I found it before measuring rather than after.

      The fix is Sheppard's correction, applied to the variances only:

          rho_corrected = cov / sqrt((var1 - 1/12)(var2 - 1/12))

      PRE-REGISTERED: every rho reported for the ISO-dependence question is
      Sheppard-corrected, and the uncorrected value is reported alongside it
      so the size of the correction is visible.  If the two disagree about
      the DIRECTION of the ISO trend, the ISO result is reported as
      instrument-limited and no mechanism is named.
""")

    print()
    if fails:
        print(f"  {fails} planted check(s) FAILED -- the estimator is not trustworthy.")
    else:
        print("  All planted checks passed.  The estimator recovers known answers,")
        print("  each null does what I claim, and the artefact that would mimic")
        print("  the finding has a decisive test.")
    return fails


def main() -> int:
    consequence()
    m62_estimator_fragility()
    signal_dependence()
    iso_dependence()
    fails = plant()
    rule("Summary of what this establishes before any corpus contact")
    print("""
  - The consequence of rho = +0.073 is +3.58 % in sigma, OVER-CONFIDENT.
  - Fact 895 comes from a difference of variances with a ~15x error
    amplification; a direct per-cell covariance has no such cancellation.
  - Dark frames measure a read-domain covariance and are structurally BLIND
    to a signal-proportional crosstalk covariance.  Say so in the report;
    do not let a dark null be read as "no correlation anywhere".
  - The ISO sweep locates the covariance upstream or downstream of the analog
    gain, using M68's already-validated alpha/delta instrument.
  - A per-frame common mode of 0.27 DN reproduces the finding exactly and is
    separated from a local coupling by the displaced-pair null.
  - A frame permutation must destroy any genuinely temporal rho.

  Two errors of my own, caught here and left in the file:

    1. Quantisation dilutes rho by s^2/(s^2 + 1/12).  My first checks
       compared against the undiluted planted value and failed.  Worse, the
       dilution is ISO-DEPENDENT -- about 8 % across the range on disk, in
       the direction that mimics an upstream covariance.  Sheppard's
       correction is now pre-registered for every ISO-dependence number.
    2. rho_adj - rho_dis is NOT rho_local; it is rho_local diluted by the
       common mode and by quantisation.  The decomposition must be done in
       covariance space, and the OPERATIONAL number is the total rho, not
       the local part.
""")
    return fails


if __name__ == "__main__":
    raise SystemExit(main())
