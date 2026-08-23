# M57 — a detail metric from first principles: measurements

**Status:** measurement report. Nothing here is folded into `SYNTHESIS.md`;
proposed facts are numbered `P1…` per rule 28 and are proposals, not facts.

**Commission.** M55 refuted `sigpow` (facts 695, 701–708). This milestone was
asked to design, implement and measure candidate replacements from first
principles, to pre-register kill conditions, and to report the finding even if
the finding is that nothing survives.

**Scripts.** `experiments/m57-shape-metric/src/{m57lib,s1_properties,
s2_drift_plant,s3_real,s4_diagnostic,s5_real_nulls,s6_debias,
s7_bias_or_variance,s8_gate_significance}.py`. Logs and JSON under that
experiment's `out/`.
Pre-registrations: `PREREGISTRATION.md` (committed `2b1d9b0` with `src/` empty)
and `PREREGISTRATION-2.md` (committed `a653adf` before `s6` ran).

**Scope note.** The commission was later amended to record that "no candidate
survives" was a pre-registered acceptable outcome and that nothing is gated on
this result. The amendment arrived after the measurements were complete and
changed none of them. Its two working instructions — do not promote a marginal
candidate, and do not trade quality for cost — were applied as an audit of this
document, which found and fixed one error; that audit is `s8_gate_significance`
and the error is recorded in §9.

---

## 0. The finding, in one page

**MEASURED.** A statistic exists that meets requirements 1, 3, 5 and 6 of the
brief exactly or near-exactly, meets requirement 4 far better than `sigpow`, and
**fails requirement 2 on real data by a factor of 3**.

`dsig` — the equivalent-blur difference between two merge configurations,
obtained as the least-squares slope of `log[C₂(f)/C₁(f)]` against `−4π²f²` over
a fixed ring band, reported as `sign(b)·√|b|` in **pixels** —

* recovers a planted Gaussian blur over a 100:1 range with **−0.04% to −0.14%**
  relative error (S1 G0);
* is **exactly degree 0 in photometric gain**, both-sided and one-sided,
  measured at **1e−15** relative and **1e−9 to 1e−6 px** absolute on real
  half-merges at λ = 1.30 — the case fact 701 says actually arises (S1 PR2,
  S3 PR7, S5 N2);
* has split leverage of **0.008–0.36% of a planted 0.10 px signal** across
  every measurable split rule on eight real cells, where fact 705 measured
  `sigpow`'s at **5000%** (S3 PR4);
* reproduces a **ground-truth oracle to ±0.0005 px** on a plant whose two
  half-merges genuinely deliver different latents — the plant class discipline
  340 says did not previously exist (S2);
* **returns `NaN`, not a number**, when a ring's common power goes non-positive,
  where fact 706 records `sigpow` returning a negative reference with an
  undefined sign rule (S3, 17 of 48 real split cells).

And then:

* **it fails its own noise null.** Adding independent noise to both real
  half-merges — an operation whose true equivalent-blur difference is
  **exactly 0 px** on any scene at any level — moves it by up to **0.343 px**,
  which is **3.4× a planted 0.10 px signal** (S5, S6 PR14).
* Removing the logarithm entirely (K6) does **not** fix it: K6's worst reading
  is **0.464 px** (S6). The mechanism I derived was wrong and is reported as
  wrong.
* Repeating the null 24 times shows the failure is **variance, not bias**, on
  62-frame stacks, and that **the jackknife standard error is anti-conservative
  by a median factor of 1.90** (S7 PR19). Every standard error in this report
  and in the family should be read as roughly double what the jackknife says.

**Verdict.** `dsig` is **not a shippable detail metric** and is not offered as
one. It is a *usable resolution contrast* under a stated and measured validity
condition: the two configurations must **share their noise realisation**, or the
contrast must exceed roughly **0.1–0.5 px** depending on stack. Under that
condition it is accurate to 4 decimal places. Outside it, it is accurate to
about one significant figure and its published error bars are wrong.

**The named failure, so the next attempt does not repeat it:** requirement 2
fails as a **variance**, not a bias, and that variance is currently 0.343 px per
512² ROI where the truth is 0. **One specific, cheap experiment would settle
whether that is fatal** — whether the scatter averages down across disjoint
ROIs (§11 item 2, Q-b, costed in S8(b) at 3–17 ROIs). It was not run here.
Naming it does not soften the verdict: as measured, on the evidence that exists,
K1 fails.

**The strategic result is separate and matters more than the metric.**
**MEASURED (S2 PR5b, S3 gate sweeps):** on six of eight real cells and on a
ground-truth plant, the near-selector configuration (`n_eff` 1.4–2.4) delivers
the **sharpest** output — by 0.496–0.740 px against the shipped gate on real
data, at **3.95–17.58σ** on jackknife errors corrected by S7's measured
anti-conservatism factor (≥9.99σ uncorrected), and by 0.556 px on the plant,
where the oracle confirms it. Of the two remaining cells, one is significant the
*other* way and one returns `NaN` and reports nothing.
**A resolution metric cannot defend the estimation thesis, because on
resolution alone the selector wins.** The estimator's claim has to be
*equal or better resolution at lower noise*, which is a two-number claim. No
one-number detail metric can carry it. See §9.

---

## 1. Rejected on sight, and why (requirement: say so rather than measure)

Rejecting without running is legitimate only where a **proof** forecloses the
family. Fact 617 is such a proof and fact 708 widens it: ring FRC is `C/(C+U)`;
a linear post-filter scales `C` and `U` by the same `|H|²`, so the ratio cannot
move (+0.0001), and a ground-truth oracle at one frequency is equally blind
(+0.00003). The blindness belongs to **evaluating at one frequency**.

| Family | Ground for rejection | Label |
| --- | --- | --- |
| Ring FRC/FSC at `f_sig`; any `C/(C+U)`; spectral SNR `C/U`; magnitude-squared coherence; NCC; the SSIM family | Fact 617 — reduces to a normalised correlation at one frequency | DERIVED |
| Oracle FSC against ground truth at one frequency | Fact 708 | DERIVED |
| Phase congruency / phase-only correlation at one ring | Reduces to the above | DERIVED |
| `hp_sd`, `mean_grad`, Tenengrad, Laplacian energy, `ringpow`, `p_ratio`, `sigpow` **as a candidate** | Degree ≥ 1 in photometric gain with no normalisation (facts 701/704); absolute-power statistics cannot separate lost noise from lost signal | DERIVED |
| Slanted-edge / knife-edge MTF, USAF-target resolution, Rayleigh/Sparrow two-point criteria | No edge or point target exists in a macro focus stack; fabricating one is ground truth, which requirement 6 forbids | ARGUED |
| Astronomical Strehl ratio | Needs a point source and a diffraction-limited reference PSF; neither exists here | ARGUED |
| Fourier ring correlation of a *single* image against a noise model (microscopy "decorrelation analysis") | Its resolution estimate is the frequency where a normalised correlation crosses a threshold — fact 617 again, at whichever frequency the crossing lands | DERIVED |

**The opening (DERIVED, and it is the whole design).** A ratio of cross-powers
at **two different frequencies** is not a normalised correlation at one
frequency: a post-filter `H` multiplies the numerator by `|H(f₂)|²` and the
denominator by `|H(f₁)|²`, and those differ. Fact 617's proof does not reach it.
Everything measured below lives in that gap.

**Noise-referenced statistics using `profile.rs` were considered and folded in
rather than run separately.** The calibrated model
(`g = max(iso,100)/436.8`, `σ² = g·S + (RN_e·g)²`, halved on the green quad,
`RN_e` = 1.2392 e⁻ since M48) is used throughout to set the *temporal* sigma
that the noise nulls are denominated in (rule 10 — never a spatial standard
deviation). It is not used to build a candidate, because the quantity a noise
model can supply — the expected noise power — is exactly the quantity a
cross-power of two independent half-merges already suppresses in expectation.
**ARGUED:** a noise-referenced statistic would re-introduce, as a calibration
dependency, information the cross-power gets for free.

---

## 2. The candidates

All are computed from two half-merges of one stack, split by parity of the
depth-sorted frame index (facts 641/702). Write `C_i(f)` for the mean per-mode
real cross-power of ring `f` of configuration `i`'s pair — i.e. canonical
`sigpow` (M46 A.1.10) evaluated at an arbitrary ring instead of only at `f_sig`.

| id | statistic | form | outcome |
| --- | --- | --- | --- |
| K0 | `sigpow` (control only) | `C(f_sig)` | control fired correctly; see §3 |
| **K1** | **`dsig`** | OLS slope of `log[C₂/C₁]` on `−4π²f²`, reported `sign(b)√|b|` px | **kept, with measured validity conditions; fails PR1, PR13/PR14** |
| K2 | `rmtf2` | `[C₂/C₁](f_hi) / [C₂/C₁](f_lo)` | strictly dominated by K1; same failures, less information |
| K3 | `ccent` | `√(Σf²C/ΣC)` over the band, absolute | degree 0 in gain (measured 0.000000) but not pedestal-blind; moves −0.7% to −17% across the PM_M ladder while true MTF falls 0.91→0.002 — **rejected**, it is a monotone-but-uncalibrated scene descriptor |
| K4 | `dsig_ped` | K1 with a white pedestal subtracted | **not implemented.** PR10 measured the white pedestal not binding in the operational range (§6), so the fix had no failure to repair |
| K5 | `gof` | fit-residual model-violation flag | **post-hoc; failed its own PR12** (§7) |
| K6 | `dsig_lin` | linear-domain fit, no logarithm | **post-hoc; failed PR14** (§8) |
| K7 | `dsig_db` | K1 with the Jensen term subtracted | **post-hoc; failed PR14 and PR17** (§8) |

### 2.1 K1's derivation (DERIVED)

For half-merges `A_i`, `B_i` of configuration `i` with independent noise,
`C_i(f) = |H_i(f)|²S(f) + F(f)` where `S` is the common scene power and `F` any
common-mode pedestal. A Gaussian blur of width `σ` has MTF `exp(−2π²σ²f²)`, so
the **cross-power carries `|H|² = exp(−4π²σ²f²)`**. With `F = 0`,

&nbsp;&nbsp;&nbsp;&nbsp;`log[C₂(f)/C₁(f)] = intercept − 4π²(σ₂²−σ₁²)f²`

exactly, at every `f`. The slope is `Δσ²`; `S(f)` cancels; any photometric gain
on any of the four inputs is a constant multiplier absorbed by the **intercept**.
The regressor is `−4π²f²`, not `−2π²f²`, and getting that wrong scales every
reading by √2.

**Sign and range (requirement 5).** Positive = configuration 2 delivers **less**
resolution, by as much as a Gaussian of that σ would cost. Negative = more.
Units are pixels of equivalent Gaussian width; the range is the real line;
`NaN` means "not measurable here" and is returned rather than a number.

---

## 3. The harness is not broken — the controls fired (rule 39)

**MEASURED (S1 PR2).** `sigpow`'s photometric-gain exponent
`d log|m|/d log λ`, on both real ROIs, at λ ∈ {1.30, 3.00}:

| mode | λ | `sigpow` exp | `dsig` move (px) | `rmtf2` exp | `ccent` exp |
| --- | --- | --- | --- | --- | --- |
| both inputs | 1.30 | **2.000000** | +1.2e−15 | −0.000000 | 0.000000 |
| both inputs | 3.00 | **2.000000** | −2.4e−15 | −0.000000 | 0.000000 |
| one input | 1.30 | **1.000000** | +2.8e−15 | −0.000000 | 0.000000 |
| one input | 3.00 | **1.000000** | +1.9e−15 | −0.000000 | 0.000000 |

Facts 704 and 701 require exactly 2.000 and exactly 1.00000. Both reproduce to
six decimal places on an independent re-implementation. **The harness reproduces
the incumbent's known failure, so PR1–PR3 are valid tests.**

**MEASURED (S1 PR1).** On the PM_M ladder at matched `hp_sd`, `sigpow/base` on
the flat ROI reads **1.05147 / 1.13166 / 1.54246 / 2.42212** while true MTF at
`f_sig` falls **0.9102 → 0.6863 → 0.2218 → 0.0024**. It says "up to 142% more
signal" while resolution collapses by a factor of 376. That is fact 703, and
the script's narrow "does it invert?" test returned `False` on this ROI because
the failure here is monotone-in-the-wrong-direction rather than an inversion.
**The test's phrasing was too narrow; the control did fire.** Recorded rather
than re-run with a friendlier predicate.

**MEASURED (S3).** `merge_subset(all frames, gate = 0.5)` reproduces
`m41lib.arm_A` bit-for-bit (`max |diff| = 0.000e+00 DN`) on all four stacks.

---

## 4. G0 — does the instrument recover a known blur, and can it be wrong?

**MEASURED (S1).** Noiseless pair, no FPN, planted Gaussian:

| planted σ (px) | `dsig` (px) | jackknife se | relative error |
| --- | --- | --- | --- |
| 0.020 | +0.01999 | 2.2e−06 | −0.0004 |
| 0.050 | +0.04998 | 5.7e−06 | −0.0004 |
| 0.100 | +0.09996 | 1.2e−05 | −0.0004 |
| 0.200 | +0.19991 | 2.3e−05 | −0.0004 |
| 0.500 | +0.49976 | 5.7e−05 | −0.0005 |
| 1.000 | +0.99934 | 1.1e−04 | −0.0007 |
| 2.000 | +1.99721 | 2.0e−04 | −0.0014 |

**Rule 39 planted wrong answer.** With truth 0.10000 px, the claim "σ = 0.00"
is rejected at **8706 σ** and the claim "σ = 0.20" at **8713 σ**. A test that
rejects both a lower and an upper wrong answer has power in both directions.
The reference `rings()` geometry and the fast `ring_grid()` label array agree on
ring count, centres and counts.

**On real data (S3), the same planted wrong answers are rejected at
1119–11213 σ** across all eight cells. **DERIVED caveat:** those σ use the
jackknife, which S7 shows is anti-conservative by ≈1.9×; halving them changes
nothing about the conclusion.

---

## 5. PR4 — split leverage, the structural killer (fact 705)

Fact 705 is the reason `sigpow` was unusable: as `|d|`, a 0.05 px blur moved it
0.00719 while changing block-4 for parity moved it 0.35870 — **50× the signal**.

**MEASURED (S3).** With the split held **common to both configurations** and a
0.10 px Gaussian planted on both halves of configuration 2, so truth is 0.100 px
for every row:

| cell | measurable rules | worst error | spread across rules | as % of signal |
| --- | --- | --- | --- | --- |
| 112MSDCF/flat | 2/6 | −0.03% | 0.00001 px | **0.01%** |
| 112MSDCF/detail | 5/6 | −0.06% | 0.00002 px | **0.02%** |
| 113MSDCF/flat | 3/6 | −0.03% | 0.00002 px | **0.02%** |
| 113MSDCF/centre | 5/6 | −0.05% | 0.00002 px | **0.02%** |
| foam/flat | 1/6 | −0.08% | 0.00000 px | **0.00%** |
| foam/centre | 4/6 | +0.01% | 0.00005 px | **0.05%** |
| 109MSDCF/flat | 5/6 | −0.33% | 0.00036 px | **0.36%** |
| 109MSDCF/centre | 6/6 | +0.27% | 0.00030 px | **0.30%** |

**PR4 PASSES on all eight cells, by four orders of magnitude.** Fact 705's 5000%
becomes 0.01–0.36%. **DERIVED mechanism:** `dsig` is a ratio of ratios in which
the split enters both configurations identically and cancels; `sigpow` is an
absolute power in which it does not.

**MEASURED, and it is a usage bound not a pass:** if the *operator* changes the
split rule and nothing else, `dsig` moves **0.07–0.77 px**, i.e. 0.7–7.7× the
planted signal. **S2 measured that this is truth, not error** (§6.2). The rule
is therefore: **`dsig` compares configurations under a fixed split; it does not
compare split rules.**

**MEASURED, and it is the reply to fact 706.** In 17 of 48 real (cell, split)
combinations, at least one ring's common power was non-positive and `dsig`
returned **`NaN` with `ok = False`** — 31 of 48 were measurable. `foam/flat` — one of fact 707's
unexplained flat cells — is measurable under exactly one split rule, and at
gates 0.90/0.99 its FRC at `f_sig` goes negative (−0.0336, −0.0239) and
`sigpow/base` reads **−1.887** and **−1.574**. That is fact 706 reproduced
verbatim. `dsig` declines to report there instead.

---

## 6. PR5 — the latent-drift plant (rule 34 / discipline 340)

Discipline 340: every plant in `m46lib` draws both arms from one latent object,
so latent drift is exactly 0 and swap asymmetry exactly 1 **by construction**.

**Built (S2).** An actual focus stack: a depth map that is a tilt plus a step,
32 frames, per-frame per-pixel blur `σ_k(x) = rate·|z(x) − z_k|` interpolated on
a 25-point sigma grid, plus FPN at the measured `ρ = 0.3094` and shot+read noise
from `profile.rs`. Both halves are then merged by `arm_A`, so **each half elects
its own winners and delivers its own latent.**

**Rule 20 — the plant can express the failure. MEASURED:** the two half-merges'
oracle widths differ by 0.00405 / 0.00426 / 0.01445 / 0.01919 px as the depth
rate goes 0 → 1.5 → 3 → 6 px, their FRC at `f_sig` falls 0.9946 → 0.9613, and
their RMS difference grows 3.84 → 6.08 DN. A fixed-latent plant gives 0 and 1
exactly.

**Oracle (used only as a positive control, never as a metric input).**
`σ_true(M)` = WLS slope of `log[Re⟨M·conj L⟩/⟨|L|²⟩]` on `−2π²f²` — one power of
`H`, because this is a signal-to-truth cross-power. **DERIVED:** since
`C = T_a·T_b·S`, `dsig²` estimates the change in the *pair* width
`(σ_a²+σ_b²)/2`, not one half's. Using one half is measuring a different
quantity, and doing so is what made the first run of S2 look like a failure.

### 6.1 Planted blur under drift

**MEASURED.** At depth rates 1.5 / 3.0 / 6.0 px, planting 0.05 / 0.10 / 0.25 px
on both halves:

| rate | planted 0.05 | planted 0.10 | planted 0.25 |
| --- | --- | --- | --- |
| 1.5 | error **−0.00000 px** | −0.00000 | −0.00001 |
| 3.0 | −0.00000 | −0.00001 | −0.00002 |
| 6.0 | −0.00000 | −0.00001 | −0.00002 |

against the oracle. **PR5 as written PASSES:** with no blur planted, the reading
is 0.00000 px.

### 6.2 The sharper case — the configuration changes the drift

**MEASURED (S2 PR5b).** Gate sweep on the drift plant, `dsig` against the
oracle, where the configuration change itself alters which frames are averaged
and therefore the delivered latent:

| gate | `n_eff` | oracle Δσ (px) | `dsig` (px) | error |
| --- | --- | --- | --- | --- |
| 0.00 | 16.000 | +0.44483 | +0.44685 | +0.00202 |
| 0.25 | 15.423 | +0.41692 | +0.41874 | +0.00182 |
| 0.50 | 12.404 | 0 | 0 | — |
| 0.75 | 7.771 | −0.43178 | −0.41685 | +0.01493 |
| 0.90 | 4.207 | −0.52190 | −0.50470 | +0.01720 |
| 0.99 | 1.453 | −0.55619 | −0.54128 | +0.01491 |

**MEASURED.** A four-way re-pairing — all frames kept, only the pairing changed
— which S3 and PREREGISTRATION §PR6 both assumed was a null, is **not** one:

| depth rate | `dsig` (px) | jackknife se | **oracle truth** | error |
| --- | --- | --- | --- | --- |
| 0.0 | −0.00548 | 1.3e−03 | −0.00051 | −0.00497 |
| 1.5 | −0.00752 | 2.2e−03 | +0.00414 | −0.01167 |
| 3.0 | +0.04033 | 3.8e−03 | +0.03982 | **+0.00051** |
| 6.0 | +0.06221 | 4.5e−03 | +0.06186 | **+0.00035** |

Truth genuinely moves, and `dsig` reports it to 0.0005 px. **P-note: PR6's null
was mis-specified in the pre-registration, and its failure on real data (§7)
must not be read as estimator error.**

**Rule 39, and it caught me.** My first replacement "true null" was the same
merge pair transposed. It returned **exactly 0.00000 with `se = nan`** because
transposing both images transposes the whole spectrum and the ring bins are
isotropic, so the ring sums are bit-identical. A test that cannot fail has not
passed; it was discarded, not reported.

---

## 7. PR1, PR8, PR10, PR12 — where K1 breaks

### 7.1 PR1 — the PM_M ladder. **K1 FAILS.**

PM_M destroys resolution by `σ_b` **and** injects a fixed high-frequency texture
**common to both half-merges**, at an amplitude solved so `hp_sd` returns to
baseline. **MEASURED:** the `honest` and `PM_M` columns are one paired run (S4,
same seed, directly comparable); `sigpow/base` is S1's matched-`hp_sd` ladder at
the same four true-MTF rungs.

| ROI | true MTF | honest-blur `dsig` | PM_M `dsig` | `sigpow/base` |
| --- | --- | --- | --- | --- |
| flat | 0.9102 | +0.218 | **+0.106** | 1.051 |
| flat | 0.6863 | +0.441 | **+0.142** | 1.132 |
| flat | 0.2218 | +0.752 | **−0.268** | 1.542 |
| flat | 0.0024 | +0.589 | **−0.842** | 2.422 |
| detail | 0.9102 | +0.246 | +0.196 | 0.923 |
| detail | 0.6863 | +0.493 | +0.368 | 0.793 |
| detail | 0.2218 | +0.958 | +0.479 | 0.914 |
| detail | 0.0024 | +1.198 | **−0.623** | 1.555 |

`dsig` inverts at true MTF 0.22 on the flat ROI and 0.0024 on the detail ROI.
**PR1 as pre-registered is FAILED and K1 is not monotone in true resolution
against this adversary.** It is strictly better than `sigpow`, which says "more
signal" at every rung — but "better" was not the kill condition.

**Note the honest column is itself non-monotone on the flat ROI at 2.0 px**
(+0.752 → +0.589), with no adversary present. That is §7.2's mechanism, not
PM_M's: at `σ_b` = 2.0 px the Gaussian MTF at `f_hi` = 0.2762 is
`exp(−2π²·2.0²·0.2762²)` = 0.0024, so the top of the band carries no common
power to fit and the estimate degrades. **`dsig` has an upper measurement range,
and it is set by the band, not by the adversary.**

**DERIVED, and it generalises past this adversary.** `C(f)` is *common* power.
From a half-merge pair alone, **nothing can distinguish resolved scene detail
from any other structure common to both halves** — FPN, PRNU, a shared guide
frame, aliased content, a shared hallucinating prior. This is a property of the
information available, not of `dsig`.

**DERIVED, and it bounds the damage.** For a merge that is a **weighted average
of aligned frames** — which is what `strehl` ships — each half is
`Σ_k w_k H_k L + Σ_k w_k N_k`, and the common part is
`(Σw H)_a (Σw H)_b* S`. **There is no term that introduces high-frequency
structure not present in `L`.** PM_M is therefore unreachable by any convex
merge of the same frames; it requires a merge that *injects*. That does not
rescue PR1, but it says which failures are live: FPN and PRNU (calibratable
from darks and flats), aliasing (not calibratable), and any future learned or
deconvolving merge (which would make the metric invalid, not merely noisy).

### 7.2 PR8 — real defocus with contrast reversals. **K1 fails past the first OTF zero, on a boundary that is derivable in advance.**

**MEASURED (S1).** Pillbox OTF `2J₁(2πrf)/(2πrf)`:

| r (px) | zeros in band | flat `dsig` | detail `dsig` |
| --- | --- | --- | --- |
| 0.25 | 0 | +0.114 | +0.124 |
| 0.50 | 0 | +0.229 | +0.250 |
| 1.00 | 0 | +0.456 | +0.510 |
| 2.00 | 0 | +0.824 | +1.112 |
| 3.00 | 1 | **+0.767** | +1.213 |
| 5.00 | 2 | **−0.451** | **+0.816** |

**DERIVED bound, stated before looking at which rung broke:** the first zero of
a radius-`r` pillbox is at `f = 0.6098/r`; it enters the band when
`r ≥ 0.6098/f_hi = 2.208 px`. **MEASURED:** monotone at every `r < 2.208`,
non-monotone at `r = 3` (flat) and `r = 5` (both). The bound is correct and
conservative. This is a stated validity condition, and M46 §9 item 5 listed it
as unmeasured.

### 7.3 PR10 — the pedestal floor. **PASSES.**

**MEASURED (S1).** A white common-mode pedestal at planted ρ, against truth:

| ROI | ρ | pedestal/`C(f_sig)` | 0.05 px | 0.20 px | 0.50 px | 1.00 px | 2.00 px |
| --- | --- | --- | --- | --- | --- | --- | --- |
| flat | 0.3094 (real) | 0.224 | 0.0456 | 0.1818 | 0.4424 | 0.7554 | 0.5967 |
| flat | 1.0000 | 0.491 | 0.0388 | 0.1537 | 0.3612 | 0.5423 | −0.2366 |
| detail | 0.3094 (real) | 0.031 | 0.0496 | 0.1984 | 0.4945 | 0.9623 | 1.1960 |
| detail | 1.0000 | 0.093 | 0.0487 | 0.1944 | 0.4815 | 0.8942 | 0.9362 |

PR10's kill was "departure from truth by 2× below 0.5 px equivalent". Worst in
range is −11.5% (flat, real ρ, 0.50 px). **PR10 PASSES**, and the bias is
**downward** — the pedestal makes `dsig` *under*-report blur, never claim
resolution it does not have. K4 was therefore not built: it had no failure to
repair.

### 7.4 PR12 — the post-hoc `gof` diagnostic. **FAILS.**

`gof` = fit-residual RMS ÷ the log-ratio sweep the fitted Gaussian accounts for.
Designed **after** PR1 failed, with its kill condition written before it ran:
useful only if `gof` ≥ 3× the honest-blur value at every rung where K1's sign is
wrong.

**MEASURED (S4).** Flat ROI: gof/honest = 9.82 / 42.97 / 15.57 / **0.47**. The
worst rung is 0.47. **PR12 FAILS.** The rule-39 planted wrong answer — "gof
cannot tell PM_M from honest blur" — **SURVIVES on both ROIs**, because the
honest range [0.036, 0.823] overlaps the PM_M range [0.383, 1.727].

**MEASURED restriction, which is post-hoc and must not be trusted yet:** within
the operational range (rungs 0.25 and 0.50 px), gof separates by 8–43×. That
restriction was chosen after seeing the data and is offered as a lead, not a
result.

**Bug recorded rather than silently fixed:** the first run of S4 reported a PM_M
amplitude of 0.0000 in every row, because it reused M55 `e5`'s `solve_sb`, which
bisects a *decreasing* function, on `hp_sd`, which increases with texture
amplitude. Both directions now exist under separate names.

---

## 8. PR13 / PR14 — the noise null, and what actually killed it

### 8.1 The null, and why it is the right one

PR6's four-way re-pairing was **not** a null (§6.2). Two real-data operations
have truth known **exactly**, with no ground truth about the scene:

* **N1** — add independent noise to each half-merge. The common transfer is
  untouched, so the true equivalent-blur difference is **exactly 0 px**.
* **N2** — scale one half. Fact 701 measures `P_a/P_b` = 1.30 on real
  half-merges; truth is **exactly 0 px**.

**MEASURED (S5). N2 passes everywhere**, on all eight cells, at λ ∈ {1.10, 1.30,
3.00}, one-sided and both-sided: worst move **1.9e−06 px**, typical **1e−08 px**.
Requirement 3 is met, on real data, in the case that actually arises.

**MEASURED (S5, S6). N1 fails everywhere.** At 3× the merged temporal sigma:

| cell | K1 `dsig` (px) | jackknife se | vs 0.10 px signal |
| --- | --- | --- | --- |
| 112MSDCF/flat | −0.11639 | 3.0e−02 | 116% |
| 112MSDCF/detail | +0.05964 | 1.5e−02 | 60% |
| 113MSDCF/flat | −0.06440 | 4.6e−02 | 64% |
| 113MSDCF/centre | +0.05437 | 1.6e−02 | 54% |
| foam/flat | +0.03241 | 2.5e−02 | 32% |
| foam/centre | +0.01585 | 1.7e−02 | 16% |
| 109MSDCF/flat | `NaN` | — | — |
| 109MSDCF/centre | −0.29126 | 4.4e−02 | **291%** |

Pre-registered threshold 0.02 px. **PR13 FAILED.**

For scale: on `112MSDCF/flat`, 3× noise moves `hp_sd` by **+17.67%** while a
0.10 px blur moves it by **−0.62%**. Requirement 2 — separate true detail from
noise smoothing — is precisely this axis, and `dsig` does not clear it.

### 8.2 A derivation, pre-registered — and refuted

`PREREGISTRATION-2.md` (committed `a653adf` before any of it ran) derived the
cause as a Jensen bias: `E[log Ĉ] = log E[C] − Var(Ĉ)/(2E[C]²)`, a term that
grows towards `f_hi` where `E[C]` falls, and therefore has the *shape* of a
blur. Two fixes were pre-registered with no tunable constants: **K6** fits in
the linear domain with no logarithm at all; **K7** subtracts the Jensen term.

**MEASURED (S6), across all eight cells:**

| candidate | PR14 worst \|null\| | PR15 worst signal err | PR16 worst gain move | PR17 worst split spread |
| --- | --- | --- | --- | --- |
| K1 `dsig` | 0.34310 px | 0.08% | 9.97e−07 px | 0.357% |
| K7 `dsig_db` | 0.34118 px | 0.05% | 9.71e−07 px | 24.850% |
| K6 `dsig_lin` | **0.46420 px** | 0.16% | 1.14e−06 px | 0.244% |

**All three FAIL PR14. K6, which contains no logarithm, failed worst.**
**My derived mechanism is refuted and is reported as refuted.** PR16 passed for
all three, including K6 — the loss of gain invariance I predicted in
`PREREGISTRATION-2.md` §5 did not happen.

### 8.3 PR19 — bias or variance, with the null's own standard error

S5 and S6 each reported **one** draw. Rule 39 asks for the null's standard
error. **MEASURED (S7), 24 independent noise draws per level:**

| cell | candidate | ×σ | mean (px) | se(mean) | sd(draws) | median jack se | sd/jack |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 109/centre | K1 | 1 | **+0.05487** | 0.01680 | 0.08230 | 0.06385 | 1.29 |
| 109/centre | K1 | 2 | +0.03205 | 0.03341 | 0.16370 | 0.09236 | 1.77 |
| 109/centre | K1 | 3 | +0.13440 | 0.05224 | 0.25592 | 0.14955 | 1.71 |
| 109/centre | K6 | 1 | +0.02028 | 0.01443 | 0.07068 | 0.03806 | 1.86 |
| 109/centre | K6 | 3 | −0.01815 | 0.03213 | 0.15740 | 0.09506 | 1.66 |
| 112/flat | K1 | 1 | +0.00017 | 0.01192 | 0.05841 | 0.02314 | 2.52 |
| 112/flat | K1 | 3 | +0.00259 | 0.01843 | 0.09029 | 0.05856 | 1.54 |
| 112/flat | K6 | 3 | −0.01597 | 0.01417 | 0.06942 | 0.04794 | 1.45 |
| 112/detail | K1 | 1 | +0.00352 | 0.00623 | 0.03054 | 0.01372 | 2.23 |
| 112/detail | K1 | 2 | +0.00621 | 0.00885 | 0.04334 | 0.01401 | **3.09** |
| 112/detail | K1 | 3 | −0.00335 | 0.01000 | 0.04898 | 0.02063 | 2.37 |
| 112/detail | K6 | 3 | −0.00523 | 0.00681 | 0.03338 | 0.01712 | 1.95 |

**PR19's pre-registered rule returns BIAS**, because 1 of 18 combinations has
`|mean| > 3·se(mean)`. **I report that verdict as written.** Disaggregated, the
picture is narrower and I report the disaggregation *as well*, not instead:

* **MEASURED.** On the 62-frame stack, both candidates' means are consistent
  with zero at every level (|mean| ≤ 0.018 px, ≤ 2.1 se). There is **no bias**
  there.
* **MEASURED.** The single BIAS flag is K1 on the 22-frame stack at 1× noise
  (+0.0549, 3.3 se). K6 on the same cell reads +0.0203 ± 0.0144 (1.4 se). So the
  Jensen derivation was *directionally* right on the one cell that had a bias,
  and S6's "K6 is worse" was a single unlucky draw.
* **MEASURED, and it is the most consequential number in this report.**
  `sd(draws) / jackknife se` = **1.29 min, 1.90 median, 3.09 max**. The rule-39
  planted wrong answer "the jackknife standard error is honest" is **REJECTED**.
  **Every jackknife standard error in this report, and in this family, is
  anti-conservative by roughly a factor of two.**

### 8.4 What the noise failure actually is (DERIVED, from the above)

The dominant term is **variance, not bias**. Adding independent noise gives
`C₂ = C₁ + ε(f)` with `E[ε] = 0` but `sd(ε) ∝ √((P_aσ_b² + P_bσ_a² +
σ_a²σ_b²)/count)`, roughly flat in `f`, against an `E[C]` that falls steeply
towards `f_hi`. A single realisation therefore delivers a random slope error of
**0.023–0.256 px per 512² ROI** at real merged SNR.

This resolves the whole report into one rule:

* **When the two configurations share their noise realisation** — configuration
  2 is configuration 1 post-processed (blur, gain, linear filter, planted
  perturbation) — `ε` cancels and `dsig` is accurate to **1e−4 px** (§4, §5).
* **When they have independent noise** — different gate, different frame subset,
  different split rule — `dsig` carries **0.023–0.256 px** of scatter per 512²
  ROI, and its jackknife under-states that by ≈1.9×.

**DERIVED, not measured:** scatter falls as `1/√(independent ROIs)`, so reaching
0.02 px on `112MSDCF/detail` at 1× noise (sd 0.0305) needs ≈2.3 independent
512² ROIs and 0.01 px needs ≈9. **ARGUED:** ROI independence is assumed, not
measured, and a macro stack's ROIs are not obviously independent.

---

## 9. The gate sweep — the result the project should act on

**MEASURED (S3), `dsig` relative to the shipped gate 0.50; negative = sharper:**

| cell | gate 0.00 | 0.25 | 0.75 | 0.90 | 0.99 | `n_eff` at 0.99 |
| --- | --- | --- | --- | --- | --- | --- |
| 112/flat | +0.291 | +0.430 | −0.528 | −0.681 | **−0.690** | 1.81 |
| 112/detail | +0.705 | +0.478 | −0.386 | −0.466 | **−0.496** | 1.43 |
| 113/flat | +0.382 | +0.434 | −0.605 | −0.742 | **−0.740** | 1.85 |
| 113/centre | +0.567 | +0.451 | −0.503 | −0.620 | **−0.629** | 1.46 |
| foam/flat | +0.214 | +0.138 | +0.357 | `NaN` | `NaN` | 2.40 |
| foam/centre | +0.607 | +0.390 | −0.438 | −0.496 | **−0.496** | 2.00 |
| 109/flat | −0.081 | −0.026 | +0.040 | +0.043 | +0.041 | 10.82 |
| 109/centre | +0.468 | +0.231 | −0.345 | −0.520 | **−0.538** | 5.11 |

**In 6 of 8 cells the near-selector is the sharpest configuration, by
0.496–0.740 px.** Rule 39 requires an error bar on each, not on one of them.
**MEASURED**, contrast against gate 0.50 at gate 0.99, with the sector jackknife
`se` corrected by the anti-conservatism factor S7 measured — each cell's own
factor where S7 covered it, the median 1.904 otherwise:

| cell | `dsig`(0.99) | jack `se` | factor | corrected `se` | σ | source |
| --- | --- | --- | --- | --- | --- | --- |
| 112/flat | −0.690 | 0.0691 | 2.52 | 0.1745 | **3.95** | own |
| 112/detail | −0.496 | 0.0127 | 2.23 | 0.0282 | **17.58** | own |
| 113/flat | −0.740 | 0.0699 | 1.90 | 0.1331 | **5.56** | median |
| 113/centre | −0.629 | 0.0291 | 1.90 | 0.0553 | **11.37** | median |
| foam/centre | −0.496 | 0.0260 | 1.90 | 0.0496 | **10.01** | median |
| 109/centre | −0.538 | 0.0385 | 1.29 | 0.0496 | **10.85** | own |
| 109/flat | **+0.041** | 0.0081 | 1.90 | 0.0155 | 2.64 *wrong way* | median |
| foam/flat | `NaN` | — | — | — | — | refuses to report |

**All six clear 2σ, at 3.95–17.58σ.** `109/flat` is significant in the *opposite*
direction — the shipped gate is very slightly sharper — which is consistent with
its `n_eff` barely moving across the sweep (11.0 → 10.8). `foam/flat` returns
`NaN` and reports nothing, which is the designed behaviour, not a pass.

**The conclusion does not depend on the correction.** At the raw, uncorrected
jackknife every one of the six reads ≥ 9.99σ; the correction moves the weakest
from 9.99σ to 3.95σ and changes no verdict. The correction factor itself is
**MEASURED** (S7, 24 draws); its transfer from a re-drawn-noise perturbation to
a gate-change perturbation is **ARGUED**, and is the reason the raw figure is
given alongside.

**Correction to an earlier draft of this section (recorded rather than silently
fixed).** An earlier version disqualified `112/flat` as unbelievable, citing a
jackknife `se` of 0.26 px. That number is the `se` of the gate **0.00** row, not
the gate 0.99 row that the contrast actually uses; the correct value is 0.0691.
`112/flat` survives at 3.95σ. **The error was conservative — it discarded a real
result — but it was an error, and the six-of-eight count was right for the wrong
reason on that row.**

**MEASURED (S2 PR5b), with ground truth:** on the drift plant the oracle agrees
— gate 0.99 (`n_eff` 1.45) really is 0.556 px sharper than gate 0.50.

**DERIVED, and it is the strategic finding.** A selector wins on resolution
because it takes the best-focused frame at every pixel; an estimator averages in
less-focused frames and pays for it in MTF. It buys back noise. **Therefore no
one-number "detail metric" can defend the estimation thesis**, and the search
this milestone was commissioned to run was for a number that cannot exist in the
form requested. The defensible claim is two-dimensional: *equal or better
equivalent resolution at strictly lower noise*, with `dsig` supplying the first
axis under §8.4's validity condition and the calibrated `profile.rs` model
supplying the second.

**ARGUED:** this also re-frames fact 707. `foam/flat` is measurable under one
split rule out of six and goes non-positive at high gates; `109/flat`'s gate
axis is flat. Both are cells where the *common power at `f_hi` is close to the
pedestal*, which is a stated boundary of this family rather than a new mystery.
It does not explain fact 707, and it is not offered as an explanation.

---

## 10. Pre-registrations and outcomes

| ID | Condition | Outcome |
| --- | --- | --- |
| G0 | Recover a known blur; reject planted wrong answers | **PASS** — −0.04% over 100:1; wrong answers rejected at 8700σ |
| PR1 | Monotone in true resolution on the PM_M ladder | **FAIL** — K1 inverts at true MTF 0.22 (flat) and 0.0024 (detail) |
| PR2 | Photometric gain | **PASS, exactly** — 1e−15 relative, both-sided and one-sided |
| PR3 | Separation at matched cost, with its null | **PASS on the plant** — `d_blur` 3782σ / 13384σ; `d_smooth` 0.4σ / 0.9σ; null 0.4σ / 0.3σ; no `S` reported |
| PR4 | Split leverage < planted signal | **PASS** — 0.01–0.36% of signal on 8 cells (fact 705: 5000%) |
| PR5 | Latent drift, no planted blur | **PASS** — 0.00000 px; and tracks a ground-truth oracle to ±0.0005 px where the drift is real |
| PR6 | Real planted blur ±30%, four-way re-pairing null within 2 se | **SIGNAL PASSES** (±0.33% on 8 cells); **NULL FAILS** (0.19–0.54 px, 3.6–12.8 se) — **but the null was mis-specified**: S2's oracle shows its truth is non-zero |
| PR7 | Planted wrong answer must be rejected both ways | **PASS** — 1119–11213 σ on real data, 8706σ on the plant |
| PR8 | Real defocus, no sign inversion across an OTF zero | **FAIL past `r` = 2.208 px**, which is derivable in advance and now a stated validity condition |
| PR9 | Flat ROI first | **HELD** — every real cell, flat before detail, reported whether convenient |
| PR10 | Pedestal floor not binding below 0.5 px | **PASS** — worst −11.5% at 0.50 px, bias downward |
| PR11 | Tuning hygiene | **HELD** — band `[0.05, 0.2762]`, `nbin` 64, `n` 512, `N_SECT` 16 fixed in `m57lib` before any stack was scored; never re-chosen |
| PR12 | Post-hoc `gof` ≥ 3× honest at every fooled rung | **FAIL** — worst 0.47; the planted wrong answer survives |
| PR13/PR14 | Noise null ≤ 0.02 px | **FAIL** — K1 0.343, K7 0.341, K6 0.464 px |
| PR15 | Signal survives the fix | **PASS** — ≤ 0.16% error for all three |
| PR16 | Gain invariance survives the fix | **PASS** — ≤ 1.14e−06 px; my prediction that K6 would lose it was **wrong** |
| PR17 | Split spread < 5% of signal after the fix | **PASS** K1 0.357%, K6 0.244%; **FAIL** K7 24.85% |
| PR18 | No held-out cell for K6/K7 | **HELD as declared** — K6/K7 results are provisional |
| PR19 | Bias vs variance, with the null's own se | **Rule as written: BIAS.** Disaggregated: no bias on 62-frame stacks; one flagged combination on the 22-frame stack; **the jackknife se is rejected as anti-conservative (median 1.90×)** |

**Things I predicted and got wrong**, recorded because the pre-registration
exists to make that visible: (a) I expected K1 to pass PR1 and it does not;
(b) I derived the noise failure as a Jensen bias and K6, which has no logarithm,
failed worse — the derivation is refuted; (c) I predicted K6 would lose gain
invariance and it did not; (d) I wrote PR6's null believing its truth was
exactly zero and S2's oracle shows it is not; (e) my first "true null" was a
transpose, which is bit-identical by construction and could not fail.

---

## 11. What is still unmeasured

1. **PR18's held-out confirmation.** K6 and K7 were designed against a failure
   observed on all eight cells. No stack outside {112, 113, foam, 109} has been
   run. `119MSDCF`, `coffee-bean`, `coffee-bubbles`, `129`–`136MSDCF` exist and
   were not touched.
2. **Whether the §8.4 scatter really falls as `1/√(ROIs)`.** Asserted from the
   variance decomposition, never measured. Multi-ROI aggregation is the obvious
   route to a usable threshold and it is untested. **It is also cheap, and
   S8(b) costs it:** at the measured per-ROI scatter, a 0.02 px threshold needs
   3 / 9 / 17 disjoint 512² ROIs on `112/detail` / `112/flat` / `109/centre`,
   and a 6000×4000 frame holds ≈91 such tiles. Under fact 644 this is one to
   two frames' worth of area. **The premise, not the cost, is what is
   unmeasured** — if ROIs share scene structure or fixed-pattern noise the
   scatter will not average down, and that is exactly what the experiment would
   find out.
3. **A correct standard error.** S7 shows the sector jackknife is
   anti-conservative by 1.29–3.09×. No replacement estimator was built. Every
   `se` in this report needs roughly doubling and none of them has been
   validated by coverage.
4. **PRNU (question 111).** `C(f)` cannot separate scene from any common
   structure (§7.1). FPN was modelled at the measured `ρ` = 0.3094; PRNU was
   not, because no flat fields exist yet. When they do, PRNU's contribution to
   `C(f)` at `f_hi` is directly measurable and is the single most useful
   follow-up.
5. **Aliasing.** Common to both halves by construction and not calibratable
   from darks or flats. Its share of `C(f_hi)` is unmeasured.
6. **Fact 707 remains unexplained.** §9 notes that the failing flat cells are
   the ones with the least common power at `f_hi`; that is a correlation, not
   the mechanism, and no `K`-window experiment was run here.
7. **`gof`'s restricted claim** (§7.4) was chosen after seeing the data. Its
   8–43× separation inside the operational range has no held-out confirmation.
8. **The noise axis of the two-number claim in §9.** This milestone measured
   resolution only. The matching noise statistic — presumably a residual
   temporal variance referenced to `profile.rs` — was neither designed nor
   measured.
9. **Non-Gaussian, non-pillbox degradations.** Motion, misregistration and
   tilt-induced anisotropy were not tested. The ring band is isotropic and the
   sector jackknife would not see a purely directional loss.
10. **Whether any of this survives a merge that is not a weighted average.**
    §7.1's protective derivation assumes a convex merge. It does not hold for
    deconvolution, sharpening or a learned prior, and `strehl` may ship one.
11. **The upper end of `dsig`'s measurement range was bounded, not mapped.**
    §7.1 and §7.2 show two separate ceilings — a Gaussian one near `σ_b` ≈ 2 px
    where `exp(−2π²σ_b²f_hi²)` reaches 0.0024, and a pillbox one at
    `r` = 0.6098/`f_hi`. Both were observed at a handful of rungs. The blur at
    which the reading first departs by more than 1% was never located, and it
    is the number an operator would need.

---

## 12. Proposed facts (rule 28 — proposals, not facts, numbered `P`)

* **P1 (MEASURED).** The equivalent-blur difference `dsig` — the OLS slope of
  `log[C₂(f)/C₁(f)]` on `−4π²f²` over `[0.05, 0.2762]` cyc/px — is **degree 0
  in photometric gain**, one-sided and two-sided, at 1e−15 relative on plants
  and 1e−9 to 1e−6 px absolute on eight real cells at λ = 1.30. Requirement 3
  is achievable exactly, not approximately. (S1 PR2, S3 PR7, S5 N2.)
* **P2 (MEASURED).** With the split held common to both configurations, `dsig`'s
  spread across measurable split rules is **0.01–0.36% of a planted 0.10 px
  blur** on eight real cells. Fact 705's 50× leverage is a property of absolute
  power statistics, not of half-merge splitting. (S3 PR4.)
* **P3 (MEASURED).** `dsig` reproduces a ground-truth oracle to **±0.0005 px**
  on a focus-stack plant whose two half-merges deliver genuinely different
  latents (oracle widths differing by up to 0.019 px, inter-half FRC 0.961).
  Discipline 340's objection is answerable. (S2.)
* **P4 (MEASURED).** A four-way re-pairing of one stack is **not a null**: on a
  drift plant, truth moves +0.0398 and +0.0622 px at depth rates 3 and 6, and
  `dsig` reports it to 0.0005 px. Any milestone using re-pairing as a null is
  measuring a real effect. (S2.)
* **P5 (MEASURED).** Adding independent noise to both real half-merges — truth
  **exactly 0 px** — moves `dsig` by up to **0.343 px**, 3.4× a planted 0.10 px
  signal. Removing the logarithm (K6) does not fix it (0.464 px). (S5, S6.)
* **P6 (MEASURED).** The failure in P5 is **variance, not bias**, on 62-frame
  stacks: over 24 draws the mean is within 2.1 se of zero at every level, with
  `sd(draws)` = 0.023–0.090 px. (S7.)
* **P7 (MEASURED).** **The leave-one-angular-sector-out jackknife standard error
  is anti-conservative by 1.29–3.09× (median 1.90).** Any milestone in this
  corpus reporting a sector-jackknife se should double it. (S7.)
* **P8 (DERIVED, MEASURED at its boundary).** `dsig` is monotone under real
  pillbox defocus while the first OTF zero `0.6098/r` stays above `f_hi` — i.e.
  `r < 2.208 px` — and non-monotone beyond. Measured monotone at every `r` below
  the bound and non-monotone above it. (S1 PR8.)
* **P9 (DERIVED).** From a half-merge pair alone, **no statistic can distinguish
  resolved scene detail from any other structure common to both halves.**
  However, a merge that is a weighted average of aligned frames cannot introduce
  high-frequency structure absent from the latent, so the live confounds are
  FPN, PRNU and aliasing — not arbitrary injection. (§7.1.)
* **P10 (MEASURED).** A white common-mode pedestal biases `dsig` **downward**,
  by at most 11.5% at 0.50 px at the measured real `ρ` = 0.3094. It cannot cause
  `dsig` to over-report resolution. (S1 PR10.)
* **P11 (MEASURED).** On 6 of 8 real cells and on a ground-truth plant, the
  near-selector configuration (`n_eff` 1.4–2.4) delivers the **sharpest** output,
  by 0.496–0.740 px against gate 0.50 on real data and 0.556 px on the plant.
  Every cell carries an error bar: **3.95–17.58σ** on corrected standard errors,
  9.98–39.14σ uncorrected, verdict identical either way. Of the remaining two,
  `109/flat` is significant in the opposite direction and `foam/flat` returns
  `NaN`. **A resolution metric alone cannot defend the estimation thesis.**
  (S3, S2 PR5b, S8.)
* **P12 (MEASURED).** `dsig` returns `NaN` rather than a number in 17 of 48 real
  (cell, split) combinations, where fact 706 records `sigpow` returning a
  negative reference with an undefined sign rule. A defined refusal is available
  in this family. (S3.)

## 13. Proposed disciplines

* **D-a.** A null must be one whose truth is known **exactly** and which
  **can** fail. Transposing an isotropically-binned spectrum is bit-identical and
  is not a test. Re-pairing a focus stack has non-zero truth and is not a null.
  The two nulls that qualify here are *add independent noise* and *scale one
  input*.
* **D-b.** Report the null's standard error from **repetition**, not from a
  jackknife, until the jackknife's coverage has been validated. P7 measures it
  failing by a median factor of 1.9.
* **D-c.** When a candidate is a **pair** statistic, its ground-truth oracle
  must be the **pair** quantity `(σ_a²+σ_b²)/2`. Using one arm measures a
  different thing and manufactures an apparent failure. (§6.)
* **D-d.** Before proposing a fix derived from a mechanism, pre-register a
  candidate that removes the mechanism **entirely** rather than correcting it.
  K6 contains no logarithm; its failing worse than K1 refuted the derivation in
  one run, which a correction term alone would not have done.
* **D-e.** Rule 39 binds **per cell**, not per claim. An earlier draft of §9
  supported an eight-cell finding with one error bar, and that one was read off
  the wrong row of its own table — the `se` of a different gate. Both errors
  survive casual reading because the conclusion did not change. **When a claim
  is a count over cells, tabulate every cell's null and `se` explicitly, and
  state the sigma for each.** The count is the claim; the cells are the
  evidence. (§9, S8.)

## 14. Proposed questions

* **Q-a.** What is the PRNU contribution to `C(f_hi)` once flat fields exist,
  and does subtracting it move `dsig` on the cells that currently return `NaN`?
* **Q-b.** Does the §8.4 scatter fall as `1/√(ROIs)`? **This is the single
  cheapest experiment that could revive K1**, and S8(b) costs it at 3–17
  disjoint 512² ROIs for a 0.02 px threshold — one to two frames' worth of
  area, negligible under fact 644. It was not run here and it should be run
  first. If the scatter averages down, K1's noise null moves from 0.343 px to
  roughly 0.343/√N and requirement 2 comes back into reach; if it does not, the
  variance is structural and this whole family is finished.
* **Q-c.** What is the correct standard error for a ring-band slope statistic on
  a Hermitian FFT with correlated rings, given that the sector jackknife is
  anti-conservative by ≈1.9×?
* **Q-d.** Given P11 — the selector is sharper — what is the matching *noise*
  statistic, and what is the exchange rate between equivalent-blur pixels and
  noise electrons at which the estimation thesis is defensible?
* **Q-e.** Is aliasing's share of `C(f_hi)` large enough to matter, and can a
  sub-pixel-dithered capture separate it from scene detail?
