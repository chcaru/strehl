r"""M75 -- are M68's R+B vertical gradient and M72's R decoupling one phenomenon?

PRE-REGISTRATION.  Committed before any M75 measurement is run.  Nothing in this
file has been executed against the dark corpus at the time of commit.  The
derivation below is algebra and planted simulation only.

=============================================================================
0.  WHAT IS ALREADY MEASURED (rule 40; not re-derived here)
=============================================================================

M68 (docs/research/M68-b-plane-mechanism.md), gate E1, SYNTHESIS fact 995:
  Fitting alpha_high in 32 row bands and taking PLANE RATIOS, the linear trend
  over the full sensor height is
      R/G1  -0.0659, r = -0.911
      B/G2  -0.0625, r = -0.896
      G2/G1 +0.0028, r = +0.082
  M68 read this as "both chroma planes drift by ~6.5% in alpha against green,
  top to bottom" and recorded the mechanism as ENTIRELY OPEN and unallocated.
  Grouping implied: {R,B} vs {G1,G2} -- the (row+col) even/odd sublattice.

M72 (docs/research/M72-green-plane-correlation.md), the correlation field:
  Pooled temporal correlation between planes at ISO 100
      G1-G2 +0.0826   G1-B +0.0651   G2-B +0.0600
      R-G2  +0.0090   R-B  +0.0096   R-G1 ~0
  and P1/P2 split the covariance by separation: |d|=1 pairs are UPSTREAM
  (ISO-scaling, share of variance tracking alpha*G^2), |d|>=sqrt(2) pairs are
  DOWNSTREAM (flat in DN).  Grouping implied: {G1,G2,B} vs {R}.

M68 fact 992: alpha_B/alpha_G2 = 0.85235 +/- 0.00316, excluded from BOTH
  conversion gain (1.000) and analog attenuation ahead of the read noise
  (0.705), 0 of 32 row bands in either.

THE TWO GROUPINGS ARE DIFFERENT PARTITIONS OF THE SAME FOUR PLANES.
{R,B}|{G1,G2} is not {G1,G2,B}|{R}.  That is the starting observation and it is
NOT by itself an answer: the two statistics measure different objects (a scale
versus a covariance) and one mechanism can in principle express differently in
each.  It is evidence, and the gates below are what decide.

=============================================================================
1.  DERIVATION -- what each hypothesis predicts, from first principles
=============================================================================

MODEL.  Per plane p, the temporal variance of a dark frame at ISO I, in DN^2,
decomposes as

    var_p(I) = alpha_p * G(I)^2 + delta_p                               (1)

with G(I) the electron->DN gain from profile.rs, alpha_p an input-referred
read-noise power in e^2 (UPSTREAM: it is amplified by the ISO gain), and
delta_p a DN-domain constant (DOWNSTREAM: quantisation plus anything after the
gain stage).  This is the decomposition built and validated in M72 section 9.

1.1  WHAT A RATIO CANNOT SEE -- and this is the gap M68 left.

M68 measured r(b) = alpha_B(b)/alpha_G2(b) over row bands b and found it falls
~6.5%.  Writing alpha_p(b) = alpha_p(0) * (1 + m_p * b),

    r(b) = r(0) * (1 + m_B*b) / (1 + m_G2*b) ~ r(0) * (1 + (m_B - m_G2)*b)  (2)

A RATIO MEASURES ONLY THE DIFFERENCE OF SLOPES.  r falling admits all of:
    (i)   m_B < 0, m_G2 = 0   -- something attenuates the chroma sublattice
                                 more towards the bottom;
    (ii)  m_B = 0, m_G2 > 0   -- something ADDS read noise to the green
                                 sublattice towards the bottom;
    (iii) both negative, m_B steeper;
    (iv)  both positive, m_G2 steeper.
These are different mechanisms and (i) and (ii) are opposite in sign.  M68's
prose ("both chroma planes drift against green") asserts (i) or (iii).  THAT IS
NOT ESTABLISHED BY A RATIO.  Observable O1 below fits alpha_p(b) ABSOLUTELY per
plane and separates them.  I flag in advance that this may overturn M68's own
description of its finding while leaving its numbers untouched.

1.2  WHAT "ONE PHENOMENON" REQUIRES.

M72 located the inter-plane covariance in two components: an upstream part that
scales with G(I)^2 and a downstream part flat in DN.  The gradient of section
1.1 lives in ALPHA -- i.e. it is upstream by construction, since alpha is the
G^2-scaling coefficient of (1).

Let the shared mechanism, if there is one, inject a common fluctuation c into
some set S of planes, with a row-dependent strength:

    x_p(t, b) = n_p(t,b) + s_p(b) * c(t,b),   p in S                    (3)

with n_p independent.  Then for p,q in S,

    cov_pq(b) = s_p(b) s_q(b) var(c),   var_p(b) = var(n_p) + s_p(b)^2 var(c)

so a row-dependent s(b) produces a row-dependent covariance AND a row-dependent
variance, in the SAME planes, with the covariance trend the stronger of the two
(it is first order in each s, the variance contribution second order in one).

    PREDICTION UNDER H1 (ONE PHENOMENON).  The planes carrying the alpha
    gradient must be the planes carrying the covariance, and the covariance
    must carry a row trend at least as pronounced, in the UPSTREAM (|d|=1)
    component.  Concretely: if the gradient is an {R,B} phenomenon then
    cov(R,B) must be non-negligible and must vary with row band.  M72 measured
    cov(R,B) POOLED as the WEAKEST inter-plane pair in the field (rho +0.0096)
    -- but pooled, so a sign-changing gradient could hide in it.  That is
    exactly what gate K3 tests.

    PREDICTION UNDER H2 (TWO PHENOMENA).  No systematic relation: the plane set
    carrying the alpha gradient and the plane set carrying the covariance
    differ, and the covariance's row profile is consistent with its noise floor.

    PREDICTION UNDER H3 (COMMON UPSTREAM CAUSE, DIFFERENT EXPRESSION).
    Groupings differ but BOTH statistics carry a row profile with a common
    shape (correlated across bands) even though they group planes differently.
    Distinguished from H2 by K3's cross-statistic band correlation, not by
    grouping.

    H4 (ARTEFACT).  One or both is manufactured by the estimator or by the
    exclusion rules.  Gates A1 and A2 are built to detect this and can kill
    M68's E1 as well as my own result.

    H5 (THE GRADIENT IS NOT A CHROMA PROPERTY).  Case (ii) of section 1.1: the
    GREENS move and R and B are flat.  Tested by O1.  If H5 holds, the entire
    framing inherited from M68 -- and the orchestrator's framing of M75 as an
    "R-and-B versus green asymmetry" -- is wrong at the root.

=============================================================================
2.  OBSERVABLES
=============================================================================

O1  ABSOLUTE alpha_p(b) and delta_p(b), fitted per plane per row band across
    all 11 ISOs.  NEW; M68 fitted ratios only.  Separates 1.1(i)-(iv).
O2  M68's E1 ratios reproduced with M68's own estimator (alpha_high ratio,
    32 row bands, same exclusion arm).  A reproduction check, not a new result.
O3  rho_pq(b) for all six inter-plane pairs across 32 row bands.  NEW.
O4  The upstream/downstream split of the band-resolved covariance, using M72's
    P1/P2 discriminator: does any band trend sit in the |d|=1 (upstream) or the
    |d|>=sqrt(2) (downstream) component?
O5  Column bands for O1-O3.  M68's E2 saw "column-band means barely moved";
    a row-only effect and a row+column effect have different mechanisms.
O6  Cross-statistic correlation across bands: corr_b(alpha profile, rho profile)
    for each (plane, pair) assignment implied by each hypothesis.

=============================================================================
3.  ESTIMATORS -- named here so that every band in section 5 is attached to one
=============================================================================

E_alpha   fit_alpha_delta from M72 src/02-criteria.py, imported by path.  Fits
          var(I) = alpha_low*G^2 (mode 0) / alpha_high*G^2 (mode 1) + delta by
          least squares over the 11 ISOs.  Reported quantity for the gradient
          arm is alpha_high, BECAUSE THAT IS WHAT M68 USED and O2 must match it.
E_rho     Sheppard-corrected pooled temporal correlation from M72
          src/01-green-correlation.py (rho_from with sheppard=True), computed
          per band.  Sheppard subtracts 1/12 DN^2 from each variance; it does
          not touch the covariance.
E_trend   Ordinary least squares slope of the per-band statistic against band
          index, reported as slope * NBAND (i.e. the change over the full
          sensor height), with Pearson r.  Same convention as M68's E1 so the
          numbers are directly comparable.
E_defect  M72 defect_flags at k = 6 (the r6 arm), the M72/M68 primary.

=============================================================================
4.  NULLS -- and THE STATISTIC EACH ONE IS NULL FOR
=============================================================================

Discipline: fact 1034 corrected fact 996 because a null was used outside the
statistic it is null for.  Each null below states its scope explicitly.

N_gain    The G2/G1 alpha ratio.  NULL FOR: per-plane gain and scale
          differences.  The two greens are electrically equivalent photosites,
          so their alpha ratio is 1 by construction.  VALID for the alpha arm
          (K1, K5).  *** NOT VALID as an independence null: M72 measured
          rho(G1,G2) = +0.0826, so the green pair is a GAIN null and NOT an
          INDEPENDENCE null (SYNTHESIS fact 1034). ***  It is therefore not
          used anywhere in the rho arm.
N_indep   Bias-corrected frame-permutation null (derangement of the temporal
          index, with the analytic -1/(T-1) correction, M72 facts 6-7).
          NULL FOR: temporal covariance.  Destroys temporal pairing, preserves
          per-pixel spatial structure and every exclusion rule.  Used in the
          rho arm.
N_grad    Band-label shuffle: permute the band index AFTER the per-band
          statistics are computed.  NULL FOR: spatial trend.  Any E_trend
          measured on shuffled labels is pure sampling noise, so its
          distribution is the trend estimator's noise floor for that arm.
          THIS IS THE ADVERSARIAL NULL (discipline 496): it is chosen to fire
          against a gradient claim, including my own and M68's.

=============================================================================
5.  GATES.  Each states its estimator, its band, and BOTH branches.
=============================================================================

A criterion with one branch is not a criterion (my own M72 error-log item 6).
Every gate below carries a consequence on both sides.

--- INSTRUMENT GATES (must pass before anything else is interpretable) -------

K0  NOISE FLOOR.  Estimator E_trend on N_grad, 200 shuffles, every arm.
    BAND: a measured trend counts as real only if |trend| > 3 * sd(N_grad
    trends) for that same arm.  This band is DERIVED FROM THE NULL, not
    guessed, and is fixed here before any measurement.
    IF the N_grad sd exceeds 1/3 of M68's reported -0.0659 (i.e. 0.0220) on the
    alpha arm, my instrument cannot resolve M68's own effect: I report that and
    the gradient arm is VOID.
    ELSE the gradient arm proceeds with the 3-sigma band as stated.

A1  ADVERSARIAL: DOES THE ESTIMATOR MANUFACTURE A GRADIENT FROM A PURE SCALE?
    This is the gate that can kill M68's E1 and my own reproduction of it.
    Motivation: G2/G1 flat is a CONFIRMING control -- it fires in M68's favour
    and was never scrutinised (discipline 496).  It compares two planes with
    EQUAL alpha.  The signal ratios B/G2 and R/G1 compare planes with UNEQUAL
    alpha (0.85).  An estimator bias that cancels at ratio 1 but not at ratio
    0.85 would make the control flat BY CONSTRUCTION and the signal sloped BY
    CONSTRUCTION, with no physical gradient at all.
    Estimator E_alpha on planted data: two synthetic planes with a KNOWN alpha
    ratio of 0.85, NO gradient, matched pedestal, quantised to integers, with
    the real ISO set and the real per-band pixel counts.
    BAND: |E_trend of the planted 0.85 ratio| must be < 0.0220 (one third of
    M68's effect).
    IF NOT MET, M68's E1 and my O2 are both artefacts of the estimator, I
    report that as the headline, and no gradient claim survives from either
    milestone.
    IF MET, the estimator is clean at the ratio that matters and the gradient
    arm proceeds.

A2  ADVERSARIAL: DOES A ROW-DEPENDENT DEFECT DENSITY MANUFACTURE BOTH?
    Motivation, per discipline 497 -- plant against the bias that FLATTERS.
    H1 is flattered by any mechanism that gives both statistics a common row
    profile.  M68's E3 found the per-row-band dark mean is U-shaped with hot
    edges; hot pixels inflate both variance and covariance.  If the surviving
    defect density varies with row, both statistics acquire a spurious shared
    row profile and H1 is manufactured.
    Estimator: the realised per-band surviving-pixel fraction under E_defect,
    measured on the real frames; and E_trend of alpha and of rho recomputed
    under exclusion arms k = 3, 6, 9 and none.
    BAND: the alpha trend must not move by more than 0.0220 across arms, and
    the rho trend not by more than 3 * its own N_grad sd.
    IF NOT MET, any shared row profile is attributed to the defect layer, H1 is
    not supported by this data, and I say the observable cannot separate.
    IF MET, arm-independence is established as M68's E4 established it for its
    own arm, and the shared-profile test in K3 is interpretable.

--- REPRODUCTION ------------------------------------------------------------

K1  Estimator E_alpha, E_trend, 32 row bands, arm r6 (E_defect k=6).
    BAND: my R/G1 trend within +/-0.0200 of M68's -0.0659 and my B/G2 within
    +/-0.0200 of -0.0625, with both Pearson |r| > 0.70.
    IF NOT MET I have not reproduced M68 on the same frames with the same
    estimator, the cross-milestone comparison is VOID, and I report the
    discrepancy as the result instead of proceeding.
    IF MET, M68's E1 is independently reproduced and O2 is settled.

--- THE SUBSTANTIVE GATES ---------------------------------------------------

K2  GROUPING.  Estimator: E_trend on the four ABSOLUTE alpha_p(b) profiles (O1)
    and the six pooled rho_pq (O3), same frames, same arm.
    TEST: under each statistic separately, is R grouped with B, or with the
    greens?  For the alpha arm, group by sign and magnitude of the absolute
    trend.  For the rho arm, group by which planes share covariance.
    BAND: the two statistics agree only if the SAME bipartition of {R,G1,G2,B}
    is selected by both.
    IF THE PARTITIONS DIFFER, H1 loses its simplest form and K3 becomes the
    decisive test rather than a confirmation.
    IF THE PARTITIONS AGREE, H1 is supported and K3 tests it quantitatively.
    NOTE: this gate is deliberately NOT decisive on its own.  Different
    statistics can group differently under one mechanism; see section 1.2.

K3  DECISIVE: SHARED SPATIAL SIGNATURE.  Estimator E_rho per band (O3),
    E_trend, and Pearson correlation across the 32 bands between the rho
    profile and the alpha profile (O6).
    BAND: H1 requires (a) rho(R,B) to carry a band trend exceeding its K0 3-
    sigma floor, AND (b) |corr across bands| > 0.70 between the covariance
    profile of the implicated pair and the alpha-ratio profile of the same
    planes -- the same 0.70 M68 used in its own E3 contamination gate.
    IF BOTH MET, the two findings share a spatial signature and I report them
    as one phenomenon, with the mechanism located by O4.
    IF NEITHER MET, and K0/A1/A2 passed and the power condition K4 is
    satisfied, I report them as TWO PHENOMENA and name the statistic that
    separates them.
    IF EXACTLY ONE MET, I report the observable as NOT SEPARATING and say so
    rather than picking the nearer option.

K4  POWER -- the guard against concluding "unrelated" from a weak test.
    Discipline 497 in the other direction: H2 is the hypothesis flattered by
    noise, since two noisy profiles look uncorrelated whatever the truth.
    Estimator: the N_grad sd for the rho arm, propagated to the band
    correlation of K3(b).
    BAND: the 32-band correlation must be able to resolve 0.70 at 3 sigma, i.e.
    the N_grad sd of that correlation must be below 0.233.
    IF NOT MET, I MAY NOT CONCLUDE H2.  The result is reported as UNDERPOWERED
    and the honest statement is that the observable cannot separate them.
    IF MET, a null result in K3 is interpretable as evidence for H2.

K5  H5 CHECK -- WHICH PLANES ACTUALLY MOVE.  Estimator E_trend on the absolute
    alpha_p(b) of O1, normalised to each plane's own alpha (so the trend is a
    fractional drift and the four planes are comparable).
    BAND: a plane is "moving" if its normalised trend exceeds its own K0 3-
    sigma floor.
    IF the greens move and R and B do not, H5 holds, M68's description of its
    own finding is wrong in sign (its numbers are not), and I report that.
    IF R and B move and the greens do not, M68's description is confirmed.
    IF ALL FOUR move, the ratio effect is a difference of slopes on a common
    background and I report the common-mode drift separately, since a common
    drift is a different object from a sublattice asymmetry.

=============================================================================
6.  NON-BLINDNESS -- what I knew before writing this
=============================================================================

I am M68 and M72.  I therefore already know: M68's E1 numbers; M72's pooled rho
field, in which R-B is the weakest inter-plane pair; and that the two groupings
are different partitions.  I have NOT computed any band-resolved rho, any
absolute per-band alpha, or any cross-statistic band correlation.  Those are
the three observables the gates turn on and none exists yet, in this repository
or in my head.

My prior, stated so it can be held against me: I expect K2 to find different
partitions and K3 to fail both limbs, i.e. H2.  The gates most likely to
embarrass that prior are K4 (an underpowered null is not evidence) and K5
(which may show the whole R-vs-green framing is inverted).  A1 is the gate that
can take M68 down with it.

=============================================================================
7.  WHAT THIS MILESTONE CANNOT SETTLE, DECLARED IN ADVANCE
=============================================================================

- Dark frames only.  Any mechanism that requires photocurrent to express is
  invisible here.  M68's B-plane scale was measured in darks and M71 is
  measuring flats; this milestone does not touch flats and must not claim to
  bear on anything that needs them.
- A shared spatial signature is evidence of a shared LOCATION, not of a shared
  mechanism.  Two different circuits in the same physical region would produce
  it.  I will not upgrade co-location to identity.
- The absolute alpha of a plane is fitted through profile.rs's G(I).  If G(I)
  is itself wrong per-plane -- which is precisely M68's open question -- then
  alpha_p absorbs that error.  RATIOS between planes are affected; the ROW
  PROFILE of a ratio is not, unless the error is itself row-dependent, which is
  the effect under study.  I flag the circularity rather than assume past it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
M72SRC = HERE.parent.parent / "M72-green-correlation" / "src"
DATA = HERE.parent / "data"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


m72 = _load("m72", M72SRC / "01-green-correlation.py")
m72c = _load("m72c", M72SRC / "02-criteria.py")

NBAND = 32
ISOS = [50, 100, 200, 250, 400, 500, 640, 800, 1000, 1600, 2000]
SHUFFLES = 200
SEED = 20250917


def bands(n: int, k: int) -> list[slice]:
    edge = np.linspace(0, n, k + 1).astype(int)
    return [slice(edge[i], edge[i + 1]) for i in range(k)]


def trend(y: np.ndarray) -> tuple[float, float]:
    """E_trend: OLS slope * NBAND (change over full height) and Pearson r."""
    x = np.arange(len(y), dtype=float)
    sl = np.polyfit(x, y, 1)[0]
    r = float(np.corrcoef(x, y)[0, 1])
    return float(sl * len(y)), r


def ngrad_floor(y: np.ndarray, shuffles: int, rng: np.random.Generator) -> float:
    """N_grad: shuffle band labels, recompute E_trend, return the sd."""
    out = np.empty(shuffles)
    for i in range(shuffles):
        out[i] = trend(rng.permutation(y))[0]
    return float(out.std(ddof=1))


# ---------------------------------------------------------------------------
# A1 rehearsal on planted data.  Run here, before any real frame is touched,
# so that the gate's own machinery is proven against a known answer.
# ---------------------------------------------------------------------------


def plant_ratio_no_gradient(ratio: float, npix: int, rng) -> dict:
    """Two planes, alpha ratio `ratio`, NO gradient, quantised, real ISO set.

    Returns the fitted alpha_high ratio per band and its E_trend.  The truth is
    a flat profile at `ratio`; any trend the estimator reports is manufactured.
    """
    g = np.array([m72c.gain(i) for i in ISOS])
    md = np.array([m72c.mode(i) for i in ISOS])
    alpha_a, delta = 4.20 ** 2, 1.0 / 12.0
    alpha_b = alpha_a * ratio
    prof = np.empty(NBAND)
    for b in range(NBAND):
        va, vb = [], []
        for k in range(len(ISOS)):
            sa = np.sqrt(alpha_a * g[k] ** 2 + delta)
            sb = np.sqrt(alpha_b * g[k] ** 2 + delta)
            xa = np.rint(512.0 + rng.normal(0.0, sa, size=(20, npix)))
            xb = np.rint(512.0 + rng.normal(0.0, sb, size=(20, npix)))
            va.append(xa.var(axis=0, ddof=1).mean())
            vb.append(xb.var(axis=0, ddof=1).mean())
        fa = m72c.fit_alpha_delta(g, md, np.array(va))["alpha_high"]
        fb = m72c.fit_alpha_delta(g, md, np.array(vb))["alpha_high"]
        prof[b] = fb / fa
    tr, r = trend(prof)
    return {"mean": float(prof.mean()), "trend": tr, "r": r,
            "spread": float(prof.max() - prof.min())}


def main() -> int:
    rng = np.random.default_rng(SEED)
    out = []

    def say(s=""):
        print(s)
        out.append(s)

    say("M75 pre-registration self-test -- planted data only, no dark frames.")
    say(f"numpy {np.__version__}")
    say("")

    say("=== derivation check: a ratio measures a DIFFERENCE of slopes ===")
    b = np.arange(NBAND, dtype=float)
    for name, (ma, mb) in [("(i)  m_B<0, m_G=0 ", (-0.002, 0.0)),
                           ("(ii) m_B=0, m_G>0 ", (0.0, +0.002)),
                           ("(iii) both<0      ", (-0.004, -0.002)),
                           ("(iv) both>0       ", (+0.002, +0.004))]:
        r = (1 + ma * b) / (1 + mb * b)
        say(f"  {name} ratio trend {trend(r)[0]:+.4f}  "
            f"absolute plane trends B {ma * NBAND:+.4f} G {mb * NBAND:+.4f}")
    say("  All four give the SAME ratio trend from DIFFERENT physics. O1 is")
    say("  the observable that separates them; M68 did not have it.")
    say("")

    say("=== N_grad estimator sanity: trend of pure noise, 32 bands ===")
    for sd in (0.001, 0.01):
        y = rng.normal(0.0, sd, NBAND)
        say(f"  sd={sd}: one draw trend {trend(y)[0]:+.5f}, "
            f"N_grad floor {ngrad_floor(y, SHUFFLES, rng):.5f}")
    say("  N_grad floor scales with the per-band scatter, as it must.")
    say("")

    say("=== A1 rehearsal: planted alpha ratio 0.85, NO gradient ===")
    say("  Band: |trend| < 0.0220 (one third of M68's -0.0659).")
    for npix in (2000, 20000):
        res = plant_ratio_no_gradient(0.85, npix, rng)
        ok = "PASS" if abs(res["trend"]) < 0.0220 else "FAIL"
        say(f"  npix/band={npix:6d}  mean {res['mean']:.5f}  "
            f"trend {res['trend']:+.5f}  r {res['r']:+.3f}  "
            f"spread {res['spread']:.5f}  [{ok}]")
    say("  A negative control on the control: plant a REAL gradient and check")
    say("  the same estimator recovers it, so that A1 passing is not merely")
    say("  the estimator being insensitive.")
    g = np.array([m72c.gain(i) for i in ISOS])
    md = np.array([m72c.mode(i) for i in ISOS])
    prof = np.empty(NBAND)
    for bi in range(NBAND):
        ratio = 0.88 * (1.0 - 0.065 * bi / (NBAND - 1) / 0.88)
        va, vb = [], []
        for k in range(len(ISOS)):
            sa = np.sqrt(4.20 ** 2 * g[k] ** 2 + 1 / 12)
            sb = np.sqrt(4.20 ** 2 * ratio * g[k] ** 2 + 1 / 12)
            va.append(np.rint(512 + rng.normal(0, sa, (20, 20000))).var(0, ddof=1).mean())
            vb.append(np.rint(512 + rng.normal(0, sb, (20, 20000))).var(0, ddof=1).mean())
        prof[bi] = (m72c.fit_alpha_delta(g, md, np.array(vb))["alpha_high"]
                    / m72c.fit_alpha_delta(g, md, np.array(va))["alpha_high"])
    tr, r = trend(prof)
    say(f"  planted gradient -0.0650: recovered {tr:+.5f}, r {r:+.3f}  "
        f"[{'PASS' if abs(tr + 0.065) < 0.022 else 'FAIL'}]")
    say("")
    say("Pre-registration self-test complete.  No dark frame was read.")

    DATA.mkdir(exist_ok=True)
    (DATA / "01-preregistration.txt").write_text("\n".join(out) + "\n",
                                                 encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
