# M144 — reference uncertainty budget

Status: **COMPLETE — DO NOT BUY THE $660 TARGET YET** `[VERIFIED]`

## Executive ruling

The premise needs two corrections.

First, "reference" is not one thing in the scorecard. On the broad and
decision-relevant definition — any value outside the candidate output that is
treated as truth in a pass/fail calculation — the current reference-dependent
set is **M2 through M10** `[VERIFIED]`. M2–M6 and M8 mostly use common input
frames or quantities derived from them; M7 uses traceable target values; M9
requires future M1 truth plus held-out repeats; and M10 uses independently
measured geometric depth. M1 is a prospective tenth member, but v1.7 admits no
M1 computation or numeric bar, so it is not currently scoreable. M11 and M12
use comparator timing, a frozen software baseline, repeated outputs, and input
sizes rather than a truth value
(`docs/proposals/2026-09-sota-scorecard.md:585-588,594-635,646-681,690-717,729-761,774-834,846-892,966-1043,1050-1144`).

On the narrower metrology definition — a separately calibrated physical or
labelled ground truth rather than a common input — the active set is **M7, M9,
and M10** `[VERIFIED]`; M1 joins only after a replacement is registered.
The scorecard's own intermediate taxonomy separately calls out M7's external
target, M10's physical/hidden truth, and M8's exact independently reconstructed
invariant `[VERIFIED]`
(`docs/proposals/2026-09-sota-scorecard.md:150-154`).

The scorecard is also not uniformly silent about uncertainty. It already
defines a site-level bootstrap/Wilson convention, a **0.10%** scale gate, a
**0.02 degree** rotation gate, a **0.10 px** residual gate, an exact M8
floating-point/serialization allowance, and an M10 angle contribution capped
at **2.5% slope error** `[VERIFIED]`
(`docs/proposals/2026-09-sota-scorecard.md:125-129,250-260,861-876,1017-1027`).
The unresolved decision-grade holes are the M7 reference values and seam
population, and the future M1 truth on which M9 depends.

Second, the proposed **$660** item `[VERIFIED]` is not an improved
higher-magnification M1 capture. It is one matte ISA ColorGauge Nano with the
listed calibration-certificate option for M7. The larger **$925** floor
also includes a **$189** Zerene licence and a **$76** meter rental `[VERIFIED]`
(`docs/OWNER-ACTIONS.md:269-289`;
`docs/research/M132-blocker-d-routes.md:406-410,600-649`). The proposed M1
reference is instead a same-subject, converter-on, maximum-reproduction RAW
atlas: three fixed-focus bursts of **32 frames** each `[VERIFIED]`, compared
with independently calibrated bare-lens sweeps at a **1.32x** target and
**1.33x** hard maximum `[VERIFIED]`
(`docs/proposals/2026-09-truth-referenced-detail.md:47-61,98-132,188-226`).

**Purchase verdict:** **do not spend $660 now** `[VERIFIED: budget decision]`.
It changes no current verdict:
M7 has no capture and the vendor has not published the certificate's numerical
uncertainty; M1 is unmeasured for unrelated reasons. Ask ISA for the exact
certificate format and per-patch covariance/expanded uncertainty first, at
**$0** `[ASSUMED: vendor pre-sales request]`. Reject the purchase if any scored
patch or required patch-to-patch difference has `U95 > 0.25 DeltaE00`
`[ASSUMED: procurement ceiling]`; proceed to the remaining preflight only if
each is `<=0.20 DeltaE00` `[ASSUMED: allocation]`.

The largest quantified M7 reference-value term is not sensor noise. Under an
explicit Gaussian screening model applied to ISA's nominal batch statistics,
the worst patch has p95 **2.6445 DeltaE00** and p99 **3.4567 DeltaE00**
`[ASSUMED: distribution; VERIFIED: calculation]`. This is not the uncertainty
of the paid certificate. It demonstrates why nominal values are inadequate and
why the missing certificate number is purchase-critical.

## 1. Scope, tags, and decision convention

The requested tags are used as follows:

- `[VERIFIED]`: read directly from a cited source or recomputed by
  `experiments/M144-reference-uncertainty/analyze.py`.
- `[INHERITED]`: a result taken from earlier repository work. Each such use
  states whether its provenance was checked. "Provenance checked" means the
  cited report was reconciled with its retained JSON/workbook where available;
  it does **not** mean the RAW workload was rerun.
- `[ASSUMED]`: a model, bound, or policy choice introduced here.

Numbers inside the verbatim scorecard quotations below are `[VERIFIED]` as a
whole; changing them to append inline tags would make the quotations
non-verbatim. Elsewhere, a tag at the end of a sentence or table cell applies
to every numerical claim in that sentence or cell.

For a scalar upper-limit rule `q <= b`, define the reported decision margin
`m=b-q_hat`; for a lower-limit rule, `m=q_hat-b`. A reference uncertainty can
flip the observed verdict when its propagated one-sided effect reaches
`|m|`. For percentiles, ratios, and nonlinear colour differences, that effect
must be obtained by rerunning the complete statistic over reference
realizations, not by attaching an error bar after the fact.

This report proposes the following conformity rule:

1. Random terms demonstrated independent may combine by root-sum-square and
   must be nested inside the scorecard's site-level bootstrap `[ASSUMED]`.
2. Systematic terms do not shrink with frame or pixel count. Sweep each over
   its calibrated bound and take the least favourable result; if only signs and
   bounds are known, add those bounds rather than using root-sum-square
   `[ASSUMED]`.
3. A pass is robust only when every capture and the pooled result pass for
   every admitted systematic realization. A fail is robust only when the
   entire uncertainty envelope fails. An envelope crossing a bar is
   `UNMEASURED` `[ASSUMED]`.

Those three points are `[ASSUMED: proposed uncertainty-aware conformity
policy]`. They preserve the scorecard's existing hard-gate, per-capture, and
site-resampling rules:

> 1. Every primary metric is a hard gate. No win compensates for a loss.
> 2. `UNMEASURED`, an uncommissioned checker, an invalid comparator arm, or an
>    under-powered capture blocks a SOTA claim; it is not a pass or a loss.
>
> (`docs/proposals/2026-09-sota-scorecard.md:84-87`)

> 5. Each capture must pass independently, and the pooled one-sided 95% confidence bar
>    must also pass. Pooling may not rescue a failed capture.
> 6. All confidence intervals resample independent physical sites, not pixels:
>    10,000 fixed-seed (`20260902`) hierarchical bootstrap draws by capture, then
>    non-overlapping site. Rates use a Wilson one-sided 95% bound.
>
> (`docs/proposals/2026-09-sota-scorecard.md:125-129`)

## 2. The actual reference-dependent axes

### 2.1 Classification

| Axis | What plays the role of reference | Classification and current consequence |
|---|---|---|
| M1 | No admitted value today. The pending proposal uses an independently calibrated, higher-subject-sampling, fixed-focus RAW atlas of the same physical patch. | Prospective physical reference. Current verdict is `UNMEASURED`; uncertainty cannot flip a verdict until a statistic and bar exist. |
| M2 | The held-out mean of the other **16 frames** `[VERIFIED]`, pairwise temporal-noise estimate, and best qualifying comparator envelope. | Input-derived stochastic reference. |
| M3 | Source plateaus, the per-coordinate source interval, an independently selected far-side source frame, an independently selected sharp source, and comparator p99. | Input-derived reference plus discrete source selection. |
| M4 | Input temporal-noise percentile, **1,000** `[VERIFIED]` convex source blends, source-defined edges, and M3's boundary truth. | Constructed source reference. |
| M5 | The independently elected best and far source frames, or physical target contrast on ruler/grid, plus comparator coverage. | Input/physical reference. |
| M6 | Aligned input samples that define recoverability, the independently selected unsaturated source, and comparator values. | Input-derived reference. |
| M7 | Per-target traceable patch values, true patch-to-patch differences, measured illuminant, frozen ICC, and comparator colour results. | External physical/colorimetric reference. This is the only axis affected by the proposed target purchase. |
| M8 | The exact discrete source support, gathered pre-clamp values, source hull, coordinates, and floating-point/serialization tolerance. | Input-defined numerical reference. |
| M9 | Future independently commissioned M1 truth labels, empirical repeat variance, and a held-out reference. | External label/reference model. It is currently `UNMEASURED` because M1 truth does not exist. |
| M10 | Ruler pitch and independently measured angle, hence `z_true`; measured focus-step conversion; hidden synthetic labels. | External geometric reference. |

M11 is excluded because its values are elapsed times relative to a comparator
and a frozen candidate/default software baseline
(`docs/proposals/2026-09-sota-scorecard.md:1050-1098`). M12 is excluded because
it tests memory, scaling, and byte identity across repeated executions
(`docs/proposals/2026-09-sota-scorecard.md:1107-1144`). They contain comparator
and baseline quantities, but no ground-truth reference value `[VERIFIED]`.

### 2.2 Literal pass/fail rules

#### M1 — not currently scoreable

> **Success.** There is deliberately no active numeric success bar. M1 remains
> **UNMEASURED**, and no detail, matched-information, quality-qualified comparator or
> SOTA claim is licensed until a replacement statistic and numeric bar survive
> commissioning.
>
> (`docs/proposals/2026-09-sota-scorecard.md:585-588`)

#### M2

> **Success.** The proposal says “strictly lower noise” but supplies no practical
> margin (`2026-08-sota-path.md` lines 192–195). **SCORECARD ADDITION:**
> `eta <=1.10` and `UCB95(sigma_strehl / min(sigma_comparator)) <=0.950`.
>
> (`docs/proposals/2026-09-sota-scorecard.md:633-635`)

#### M3

> **Success.** **SCORECARD ADDITION:** median `h_e` and `v_e <=0.01`; p99 of each
> `<=0.05`; affected-edge point rate `<=1%` and Wilson UCB95 `<=2%`; median edge-width
> ratio in `[0.95,1.05]`; median `rho_edge>=0.90`; strehl’s paired p99 is no greater
> than the best comparator’s.
>
> (`docs/proposals/2026-09-sota-scorecard.md:678-681`)

#### M4

> **Success.** **SCORECARD ADDITION:** median `Q_flat<=1.00`; failed-site point rate
> `<=1%`, Wilson UCB95 `<=2%`; strehl’s rate is no greater than the best comparator’s.
>
> (`docs/proposals/2026-09-sota-scorecard.md:716-717`)

#### M5

> **Success.** **SCORECARD ADDITION:** coverage point estimate `>=99%`, Wilson LCB95
> `>=98%`, longest failed run `<=1%` of the sweep dimension, retained FOV `>=99%`, and
> strehl coverage no lower than the best comparator.
>
> (`docs/proposals/2026-09-sota-scorecard.md:759-761`)

#### M6

> **Success.** **SCORECARD ADDITION:** `clip_high<=0.001`,
> `clip_low<=0.001`, highlight-detail retention `>=0.90`, and none of the three values
> is worse than the best comparator.
>
> (`docs/proposals/2026-09-sota-scorecard.md:796-798`)

#### M7

> **Success.** **SCORECARD ADDITION:** median DeltaE00 `<=1.0`, p95 `<=2.0`, maximum
> `<=3.0`, boundary-seam p99 `<=1.0`, ICC/300-DPI conformance `100%`, and no summary is
> worse than the best comparator.
>
> (`docs/proposals/2026-09-sota-scorecard.md:832-834`)

#### M8

> **Success.** **PROPOSAL BAR (M8-O):** final-output violation fraction exactly
> `0.0000%`. **SCORECARD ADDITION (M8-R):** resampler violation fraction exactly
> `0.0000%`; the crop/reference identity arm also has zero violations. A missing
> pre-clamp trace is `UNMEASURED`, not a pass.
>
> (`docs/proposals/2026-09-sota-scorecard.md:889-892`)

The prospective v1.5 M8-O replacement retains the exact-zero decision
`[VERIFIED]`:

> - **PASS iff every capture has `V=0` and aggregate `V=0`.**
> - `FAIL iff aggregate V>=1`. `V=40` is a FAIL.
> - Nonzero floor: **none.** *"No empirical or statistical allowance may be
>   introduced after observing the result."*
>
> (`docs/proposals/2026-09-sota-scorecard.md:926-931`)

#### M9

> **Success.** **SCORECARD ADDITION:** false-certification Wilson UCB95 `<=1%`;
> true-band coverage `>=90%`; nominal 95% coverage in `[93%,97%]`; empirical/predicted
> variance ratio in `[0.90,1.10]` for at least 90% of deciles.
>
> (`docs/proposals/2026-09-sota-scorecard.md:997-999`)

#### M10

> **Success.** **SCORECARD ADDITION:** valid target pixels `>=99%`; rank correlation
> `>=0.99`; median absolute error `<=0.5` focus step; p95 `<=1.0` step; ruler slope error
> `<=5%`; flat-null p95 range `<=0.5` step; synthetic layer confusion `<=1%`.
>
> (`docs/proposals/2026-09-sota-scorecard.md:1041-1043`)

## 3. What the physical references are

### 3.1 Proposed M1 atlas

The current proposal calls the atlas a higher-subject-sampling,
fixed-focus RAW view of the exact patch in the scored sweeps, explicitly not a
JPEG, stack, deconvolution, or candidate-derived synthetic target
(`docs/proposals/2026-09-truth-referenced-detail.md:188-195`). Each
**32-frame** burst `[VERIFIED]` is split odd/even; its two **16-frame** halves
`[VERIFIED]` use independent converter-on flat/dark masters, while the scored
bare-lens A/B outputs use disjoint calibration
(`docs/proposals/2026-09-truth-referenced-detail.md:196-214`). Near, middle,
and far fixed-focus strips form an atlas without focus stacking
(`docs/proposals/2026-09-truth-referenced-detail.md:216-226`).

The conservative proposed subject-sampling ratio is **2.0312x** `[VERIFIED]`
at the scored hard maximum; the desired gate is **2.0x** `[VERIFIED]`
(`docs/proposals/2026-09-truth-referenced-detail.md:254-273`). The proposal
correctly calls the atlas a qualified proxy rather than perfect truth and
requires split-reference SNR, focus/transfer, geometry, resampler, clipping,
linearity, and reference-power gates
(`docs/proposals/2026-09-truth-referenced-detail.md:227-239`).

This proposal remains unratified scorecard work. Its exact comparison form is
`lower_95(Delta J) > delta_J` together with an upper bound for every fidelity
departure, but neither `delta_J` nor the fidelity allowances are numeric
(`docs/proposals/2026-09-truth-referenced-detail.md:1084-1116`) `[VERIFIED]`.
Therefore no
numeric M1 verdict-flip budget exists yet.

### 3.2 Proposed M7 target

M7 presently has no target capture. Its registered input requires a tilted
ColorChecker under a measured illuminant, published traceable values, a grey
reference, and darks; at least **24 patches** `[VERIFIED]`, including all
neutrals and at least **12 chromatic patches** `[VERIFIED]`, must survive
(`docs/proposals/2026-09-sota-scorecard.md:781-792`).

The **$660** candidate `[VERIFIED]` is a **30-patch** matte ISA ColorGauge Nano
with a listed NIST-traceable calibration-certificate option. Its body is
**17.463 by 20.638 mm** `[VERIFIED]`, so it fits the calculated macro field.
The base target is **$330** and the certificate option adds **$330**
`[VERIFIED]`
(`docs/research/M132-blocker-d-routes.md:485-515`). The purchase would replace
nominal batch-average colour values with, it is hoped, values measured for the
delivered unit. It would not improve sensor noise, flat-field correction,
registration, illumination measurement, ICC accuracy, tone linearity, or
quantisation.

ISA's retained workbook says its free values are nominal batch measurements,
warns of inter-batch variation, and directs critical users to individual
target calibration
(`docs/research/M132-blocker-d-routes.md:521-544`). The workbook does not state
the paid certificate's uncertainty, coverage factor, geometry, or covariance.
Calling the option "individual" is `[ASSUMED]`, albeit supported by that vendor
wording; it must be confirmed before payment.

## 4. Cross-axis uncertainty budget

The magnitudes below are either measured proxies from existing material or
explicitly marked unknown. A proxy is not silently promoted to the pending
capture.

| ID | Term and axes | How to estimate cheaply | Magnitude | Random/systematic |
|---|---|---|---|---|
| R1 | Photon and read noise in reference/input samples; M1–M10 where image values define truth | Pairwise frame differences and odd/even means, stratified by signal and channel; use the already required repeats | Using inherited ISO-100 green gain **0.224001 DN/e-** and read noise **1.079 DN** `[INHERITED: provenance checked to M71 and independent camera calibration; RAW not rerun]`, one-frame sigma is **7.71–48.55 DN** `[VERIFIED]` over **260.4–10,515.5 DN** `[INHERITED]`; a **16-frame** mean is **1.93–12.14 DN** and a **32-frame** mean **1.36–8.58 DN** `[VERIFIED]` (`docs/research/M71-flat-fields.md:309-318,427-432,1169-1173`; `docs/research/F-camera-lens-optics.md:120-140`) | Random if exposures are independent; averages as `1/sqrt(N)`. |
| R2 | Finite sites, percentile estimation, Wilson rates; M2–M10 | Existing hierarchical bootstrap and Wilson rules, with the reference nuisance draws nested outside the site draw | At exactly **500 sites** `[ASSUMED: sensitivity example]`, M3/M4 permit at most **4 failures**, M5 at most **4 failures**, and M9 at most **1 false certification** under their combined point/Wilson rules `[VERIFIED]` | Random sampling. More independent sites help; more pixels in one site do not. |
| R3 | Best-comparator envelope and paired comparator measurement; M2–M7 and proposed M1 | Repeat every comparator on the identical inputs; in every bootstrap draw reselect the comparator-favouring mode rather than conditioning on the observed winner | **Unknown** `[VERIFIED: the scorecard says no quality-qualified comparator exists in v1.7, while marking that coupling rule unratified]` (`docs/proposals/2026-09-sota-scorecard.md:88-124`) | Random run/site variation plus systematic version/settings effects; additional runs do not remove mode-selection bias unless selection is nested in inference. |
| S1 | PRNU, DSNU, row/column structure, dust, residual flat error; all image-reference axes | Apply A/B masters separately, then measure held-out flat/dark residual RMS and cross-half/reference-candidate correlation in sensor coordinates | Raw green PRNU is **0.3096% rms** and at least **91.36% of its variance** persisted across changed captures `[INHERITED: provenance checked to retained M71 JSON; RAW not rerun]`. Corrected residual is **unknown** `[VERIFIED: not reported for the proposed chain]` (`docs/research/M71-flat-fields.md:300-306,318-343,1147-1160`) | Systematic within a fixed sensor footprint; does not average away. Independent calibration/footprint can decorrelate it. |
| S2 | Translation, rotation, local warp, chromatic registration; M1–M10 as geometry enters the statistic | Fit from input-only fiducials; cross-validate withheld fiducials; report residual vector fields, not only global RMS; rerun metrics over the residual-warp ensemble | Existing repeat data span **0.064031–0.107703 native px RMS** `[INHERITED: provenance checked to retained alignment JSON]`. At **0.25 cyc/px** `[VERIFIED: scorecard licence]`, that is **0.1006–0.1692 rad phase RMS** and, only under a zero-mean Gaussian-jitter model, **0.50%–1.42% amplitude loss** `[ASSUMED model; VERIFIED arithmetic]` (`docs/research/M-PHASE0-SPLIT2.md:7-14,76-85`) | Mixed. Fit variance is random; lens distortion, local warp, and chromatic residual are systematic. |
| S3 | Magnification ratio and pixel-footprint calibration; especially M1, M7, M10 | Measure common-grid pixels per period in every capture; bootstrap fiducials; hold out grid cells; propagate scale through the exact resampler | A prior ruler fit gave `m=2.7198 +/- 0.0051`, or **0.188%** `[INHERITED: provenance checked to retained M84b JSON; different setup]`. The scorecard geometry gate is **0.10%** `[VERIFIED]`; across a centered **128-px** site this is **0.064 px** edge displacement and an assumed sinc loss of **0.168%** at **0.25 cyc/px** `[ASSUMED model; VERIFIED arithmetic]` (`docs/research/M84b-ruler-metrology.md:273-282`; `docs/proposals/2026-09-sota-scorecard.md:250-260`) | Mostly systematic within a capture; fiducial fit has a random component. |
| S4 | Reference focus position, strip assignment, best/far-frame election; M1, M3, M5, M9, M10 | Fit through-focus transfer at every reference strip; repeat the return-to-focus approach; propagate ambiguous frame election as discrete alternatives | The available independent ruler proxy has median depth uncertainty **8.28 um** and p90 **16.43 um** `[INHERITED: provenance checked to retained depth JSON; not the registered capture]`. Against its mean **42.20 um/focus-step** `[INHERITED]`, these are **0.196** and **0.389 focus step** `[VERIFIED]` (`docs/research/M84b-ruler-metrology.md:16-20,619-622,731-735`) | Mixed. Shot noise in peak fitting is random; backlash, breathing, wrong-strip choice, and reference defocus are systematic. |
| S5 | Tone, linearity, white balance, illuminant and ICC transformation; strongest in M7, also M1/M2/M3/M6/M8 | Capture the registered ramp in the same session; estimate per-channel response and residuals; repeat illuminant SPD; propagate spectral/Lab covariance through the frozen ICC | The current tone sentinel admits slope **0.995–1.005**, offset magnitude **0.001**, and max affine residual **0.002** `[VERIFIED]` (`docs/proposals/2026-09-sota-scorecard.md:201-215`). If all three take their allowed worst sign, the darkest Nano neutral can shift by **1.162 DeltaL-star** `[ASSUMED worst-case alignment; VERIFIED calculation]`. This is a bound, not an expected error. Actual M7 illuminant/ICC uncertainty is **unknown** `[VERIFIED]`. | Predominantly systematic. Repeating the same transform does not reduce it. Meter repeat noise is random. |
| S6 | Quantisation and numeric representation; all serialized-output axes, decisive in M8 | Recompute from exact stored code values and rerun with higher-precision intermediate/output as a sensitivity arm | A **16-bit** half-LSB is **0.0000076295** of range `[VERIFIED]`; on the darkest Nano neutral it is **0.002705 DeltaL-star** `[VERIFIED]`. Quantisation error is correlated across like scene values, not independent dither (`docs/research/M115-deconv-headroom.md:228-231,320-333`). | Deterministic/systematic for a fixed value; it does not average as white noise. |
| S7 | Reference optical transfer, sampling sufficiency, and reference-side resampler kernel; M1 and therefore M9 | Split-reference transfer, a measured edge/random-code MTF, two pre-frozen kernels, and a nuisance sweep through the complete `J_TR/F_TR` calculation | **Unknown** `[VERIFIED: no physical M1 capture exists]`. The M1 proposal explicitly requires the kernel sensitivity to fit inside the decision margin (`docs/proposals/2026-09-truth-referenced-detail.md:1060-1082`) | Systematic. More frames reduce noise, not optical blur or kernel bias. |
| S8 | Unit-specific target value, batch variation, patch homogeneity, aging; M7 | Require serial-linked spectral or Lab values, covariance, geometry, date, coverage factor, and within-patch scans; Monte Carlo through CIEDE2000 | Paid-certificate uncertainty is **unknown** `[VERIFIED]`. As a screening model only, the nominal workbook's component standard deviations imply worst-patch p95 **2.6445 DeltaE00**, p99 **3.4567 DeltaE00**, median-patch p95 **0.5623 DeltaE00**, and **7 of 30 patches** above p95 **1.0 DeltaE00** `[ASSUMED independent Gaussian components; VERIFIED simulation]` (`docs/research/M132-blocker-d-routes.md:521-544`) | Systematic to the purchased chart. It does not average with more photographs. |
| S9 | External ruler angle, pitch, perspective model, and physical focus-step scale; M10 | Independent inclinometer/metrology repeats, two-view projective fit, pitch certificate, and Monte Carlo depth maps | M10 already requires angle uncertainty to contribute at most **2.5% slope error** `[VERIFIED]` (`docs/proposals/2026-09-sota-scorecard.md:1017-1027`). A different existing ruler achieved a depth-scale largest 95% half-width of **0.0441%** `[VERIFIED]`, but that is only an achievable proxy (`docs/research/M84b-ruler-metrology.md:273-282`) | Angle, pitch, and model bias are systematic; repeated tick localisation is random. |
| S10 | Truth-label error and boundary membership; M3–M7, M9, M10 | Blind duplicate annotation, latent-label permutations, strip/boundary erosion sweeps, and adjudication before rendering | **Unknown** `[VERIFIED: no scored manifests exist]`. Count sensitivities in section 6 show that one wrong label can be decisive near several bars. | Usually systematic per site; inter-rater disagreement supplies a random model only if raters are genuinely independent. |

### 4.1 Two terms that need special treatment

**M3 plateau normalization.** At the minimum eligible source step of
**10 sigma** `[VERIFIED]`, a normal-noise approximation for the two source
medians gives `U95` **8.43% of a unit step** for each **17-sample** narrow
plateau and **3.86%** for each **81-sample** broad plateau
`[ASSUMED normal independent samples; VERIFIED arithmetic]`. Those values are
larger than the M3 median halo/veil bar of **1%** `[VERIFIED]`, and the narrow
value is larger than the p99 bar of **5%** `[VERIFIED]`. Correlation and median
filtering can change the exact values. The cheap answer is to estimate them
from the actual plateau covariance and bootstrap the entire normalized
profile; a bare `10*sigma` eligibility floor is not an uncertainty budget.

**M7 patch-image random terms.** For the darkest nominal Nano neutral, a
conservative one-frame, **20%-eroded**, **484 by 484 px** patch model with a
**16-pixel** correlation area gives patch-median `U95` **0.00515
DeltaL-star** `[ASSUMED correlation model; VERIFIED arithmetic]`. Treating the
measured white PRNU as spatially white gives **0.000803 DeltaL-star**
`[ASSUMED transferability and whiteness; VERIFIED arithmetic]`. Both are tiny
beside the nominal target-value term, but neither covers low-frequency
illumination, flat residual, patch nonuniformity, ICC bias, or certificate
uncertainty.

## 5. Axis-by-axis propagation

### M1 — proposed atlas, no active flip threshold

Uncertain quantities are reference photon/read noise, residual FPN, atlas
focus, subject-sampling ratio, distortion/registration, reference optical
transfer, reference-half covariance, tone inversion, and reference-side
resampling. The proposed decision has the right propagation form:

```text
lower_95(Delta J) > delta_J
AND
upper_95(Delta F_j) <= delta_F_j for every j
```

A reference-induced decrease or interval widening of at least
`lower_95(Delta J)-delta_J` flips `BETTER DETAIL`; a fidelity increase of at
least `delta_F_j-upper_95(Delta F_j)` flips the corresponding veto
`[VERIFIED: algebra]`. But the numeric deltas and the physical readings do not
exist, so **M1 has no numeric uncertainty threshold** `[VERIFIED]`.

One eligibility sensitivity is already computable: the conservative proposed
ratio **2.0312x** is only **0.0312x** above **2.0x**, or **1.54% relative**
`[VERIFIED]`. A downward scale uncertainty exceeding that amount crosses the
desired sampling gate. This changes eligibility, not today's M1 verdict.

### M2 — held-out mean reference

The uncertain quantities are both **16-frame** means, pairwise `sigma_1`,
bandpass residuals, ROI eligibility, geometry, tone, and the comparator
envelope `[VERIFIED]`. For `eta`, the reference-noise realization is part of the measurand,
while uncertainty in its variance estimate and the ROI population belongs in
the confidence interval. Residual FPN shared by output and reference can
artificially lower `sigma_res`; disjoint calibration and a held-out residual
correlation arm are mandatory.

The flip sensitivities are:

- `U95(eta) >= |1.10-eta_hat|` `[VERIFIED]`;
- `U95(ratio) >= |0.950-ratio_hat|` `[VERIFIED]`;
- any reference-driven eligibility or geometry change that makes the arm
  invalid `[VERIFIED]`.

All three are `[VERIFIED: direct distance to the registered bars]`. There is no
numeric `eta_hat` or comparator ratio today, and v1.7 has no
quality-qualified comparator mode, so M2 remains unmeasured independently of
the $660 purchase
(`docs/proposals/2026-09-sota-scorecard.md:615-635`).

### M3 — source interval, plateaus, and selected frames

The uncertain quantities are source medians, source interval endpoints,
temporal sigma and the `10*sigma` eligibility label, edge normal/position,
far/sharp frame selection, registration, and comparator p99. Propagate them by
bootstrapping frames inside each site, then sites inside each capture, while
rerunning the discrete reference-frame election `[VERIFIED: scorecard inputs;
ASSUMED: propagation method]`.

Continuous arms flip when propagated uncertainty reaches the distance to
their bars:

- `|0.01-median(h)|`, `|0.01-median(v)|`,
  `|0.05-p99(h)|`, or `|0.05-p99(v)|` `[VERIFIED]`;
- distance of width ratio to `[0.95,1.05]` `[VERIFIED]`;
- `|rho_edge-0.90|` `[VERIFIED]`;
- distance between Strehl and the comparator p99 `[VERIFIED]`.

These four expressions are `[VERIFIED]`. At exactly **500 eligible edges**
`[ASSUMED: minimum-size sensitivity]`, at most **4 affected edges**
`[VERIFIED]` satisfy both the point and one-sided Wilson bars; if the observed
count is **4** `[ASSUMED: boundary case]`, one reference-label change flips
the rate verdict. The plateau calculation above shows that a minimally
eligible edge can already have enough reference normalization uncertainty to
cross the continuous bars.

### M4 — synthetic/source blend reference

The uncertain quantities are temporal-noise p99, finite **1,000-blend**
`B99`, flat/edge eligibility, edge location, `Q_flat` denominator floor, and
the inherited M3 label. Regenerate the Dirichlet blend ensemble under frozen
seeds and bootstrap source frames and sites; separately sweep systematic
registration and flat-field residual `[VERIFIED: scorecard inputs; ASSUMED:
propagation method]`.

The continuous flip threshold is `U95(Q_median) >= |1.00-Q_median_hat|`.
Individual site status flips when uncertainty in `Q_flat` reaches
`|1.25-Q_flat_hat|`, in `g_ghost` reaches `|0.10-g_hat|`, or an M3 boundary
classification flips `[VERIFIED]`. At exactly **500 sites** `[ASSUMED:
minimum-size sensitivity]`, at most **4 failures** `[VERIFIED]` satisfy the
point/Wilson pair; one wrong reference classification flips a boundary result
at that count.

### M5 — best-source and far-source election

The uncertain quantities are input-band power, best/far frame identity,
source-signal ratio and its lower confidence bound, coherence, focus-step
position, target contrast, and connected-run geometry. Frame election must be
rerun in each reference bootstrap; conditioning on the initially selected
frame would omit the largest discrete uncertainty.

The per-tile flip thresholds are
`U95(rho_best) >= |rho_best_hat-0.90|` and
`U95(rho_best-rho_far) >= |margin_hat-0.05|` `[VERIFIED]`. At exactly **500
eligible tiles** `[ASSUMED: minimum-size sensitivity]`, at most **4 failures**
`[VERIFIED]` pass both coverage constraints; one label change flips a result
at that boundary. A run-length or field-of-view result flips when its
reference-coordinate uncertainty crosses its distance to **1%** or **99%**
respectively `[VERIFIED]`.

### M6 — input-defined recoverability

The uncertain quantities are each aligned input value around the high/low
eligibility thresholds, output code values around the rails, population
membership, unsaturated-source election, and highlight coherence. Evaluate
recoverability probabilistically from repeated source samples, but make the
final conservative classification before looking at outputs.

For `N` recoverable pixels, the count arm flips when uncertain membership or
rail classification can move the count across `floor(0.001*N)`. At the
required minimum **10,000 pixels** `[VERIFIED]`, **10 clipped pixels** pass and
**11 fail** `[VERIFIED]`; one classification is therefore decisive at the
boundary. The coherence arm flips at
`U95(rho) >= |rho_hat-0.90|` `[VERIFIED]`. Single-frame reference noise reaches
about **0.306% of active range** at the bright end of the inherited ISO-100
range `[VERIFIED]`, so threshold-near pixels cannot be treated as exact.

### M7 — colour target

Every quantity in the colour decision carries uncertainty except the
byte-identity and tag-presence checks:

- the delivered target's spectral/Lab values and their covariance;
- spatial nonuniformity, aging, contamination, angle, and measurement
  geometry;
- illuminant SPD and spatial uniformity;
- patch segmentation/erosion and chromatic registration;
- camera noise and residual flat-field/PRNU;
- exposure, white balance, tone linearity, and frozen ICC;
- CIEDE2000 computation and output quantisation;
- focus-boundary membership and the covariance of the two patch references in
  the seam subtraction;
- finite patch/boundary populations and percentile convention.

This list is `[VERIFIED: scorecard chain plus identified nuisance terms]`.

The scorecard does not define a seam population, minimum count,
empty-population rule, or p99 convention
`[VERIFIED]` (`docs/research/M133-blocker-audit.md:850-875`). That protocol hole
must be closed before uncertainty can be propagated to the seam verdict.

For each patch, draw jointly from certificate covariance, illuminant repeats,
ICC/tone calibration, patch pixels, and registration. Recompute all patch
DeltaE00 values and all seam residuals per draw. The summary flips whenever
the resulting one-sided envelope crosses **1.0** (median), **2.0** (p95),
**3.0** (maximum), or **1.0** (seam p99) `[VERIFIED]`. In shorthand, the
required uncertainty is the corresponding absolute distance from the
observed summary to its bar; no single pre-capture scalar can replace those
four margins.

For procurement, before a measured score exists, this report allocates:

| Component | Proposed ceiling |
|---|---:|
| Per-patch certificate contribution and every required patch-difference contribution | `U95 <= 0.20 DeltaE00` `[ASSUMED]` |
| Total reference chain for a patch or seam truth value | `U95 <= 0.25 DeltaE00` `[ASSUMED]` |
| Remaining independent-random root-sum-square capacity | `U95 <= 0.15 DeltaE00` `[VERIFIED arithmetic from assumed ceilings]` |

The **0.25 DeltaE00** ceiling `[ASSUMED]` reserves three quarters of the
tightest **1.0 DeltaE00** bar `[VERIFIED]` for the measured system. The
**0.15 DeltaE00** remainder `[VERIFIED]` may be used only by demonstrated
independent random terms. Systematic terms must be swept and fit inside the
actual decision margin. If ISA reports only independent equal per-patch
locally linear uncertainties, each must be at most **0.1414 DeltaE00**
`[VERIFIED]` for their root-sum-square difference to meet the **0.20
DeltaE00** patch-difference screen `[ASSUMED]`; covariance and CIEDE2000
nonlinearity can make the true requirement better or worse.

### M8 — exact source hull

The reference values are the discrete source samples and coordinates actually
used. Sensor noise is already inside those observed samples and the scorecard
explicitly forbids adding a temporal-noise allowance
(`docs/proposals/2026-09-sota-scorecard.md:861-876`) `[VERIFIED]`. The uncertainty terms are
therefore coordinate reproduction, support indexing, floating-point ULP, and
serialized half-LSB. These are deterministic and tested by an independent
implementation.

At unit scale, `tau_R` is **0.000000953674** and the combined serialized
tolerance is **0.00000858319** `[VERIFIED]`. The historical positive M8-O
excess is **431 times** that tolerance and the largest absolute excess is
**122,237 times** it `[VERIFIED]`
(`docs/research/M8-overshoot.md:18-48`). Thus numerical reference uncertainty
cannot rescue the historical M8 failure. For the active exact-zero rule, one
classification change is sufficient to flip pass/fail; the answer is stronger
than a generic budget because every accepted uncertainty is already in the
pointwise tolerance.

### M9 — future M1 truth and held-out repeat

The uncertain quantities are M1 truth-valid labels, band boundaries,
registration, reference transfer/noise, claimed-valid membership, empirical
repeat variance, predicted variance, and held-out interval coverage. Because
the scorecard states that truth is the future M1 condition and then says M9 is
`UNMEASURED` without M1, no amount of improved M7 colour reference can change
M9 (`docs/proposals/2026-09-sota-scorecard.md:978-1005`) `[VERIFIED]`.

At exactly **500 claimed-valid cells** `[ASSUMED: minimum-size sensitivity]`,
at most **1 false certification** `[VERIFIED]` passes the one-sided Wilson
bar; one truth-label error flips a boundary result from **1** to **2**
`[ASSUMED: boundary case; VERIFIED count effect]`. With exactly **500
truth-valid cells** `[ASSUMED]`, a point coverage of **90%** permits **50**
misses and the next changed label flips it `[VERIFIED]`. The interval and
variance arms flip when propagated uncertainty reaches the nearest edge of
`[93%,97%]` or `[0.90,1.10]` respectively `[VERIFIED]`.

### M10 — geometric depth truth

The uncertain quantities are ruler pitch, independent angle, origin,
perspective/distortion model, pixel coordinates, focus-step conversion,
registration, target validity, and synthetic labels. The scorecard already
contains a partial budget: external-angle uncertainty may contribute no more
than **2.5% slope error** `[VERIFIED]`, against a total slope-error bar of
**5%** `[VERIFIED]`.

For a measured slope error `e`, truth uncertainty flips the slope arm at
`U95 >= |5%-e|`. Depth truth flips the median or p95 arm when its propagated
uncertainty reaches `|0.5-median_error|` or `|1.0-p95_error|` focus step
`[VERIFIED]`. The existing, non-registered ruler's median and p90 truth
uncertainties are **0.196** and **0.389 focus step** `[VERIFIED]`; those are
large enough to consume **39.2%** of the median-error bar and **38.9%** of the
p95-error bar `[VERIFIED]`, but cannot be assigned to the future M10 capture.
At the minimum **10,000 valid pixels** `[VERIFIED]`, the valid-fraction and
synthetic-confusion limits each change side after **100** allowed failures;
the **101st** flips the point rule `[VERIFIED]`.

## 6. Purchase decision

### What the $660 changes

It buys the physical small target and a promised traceable calibration
certificate. Relative to ISA's free nominal workbook, the useful change is
potentially from batch-average values with material target-to-target spread to
values tied to the delivered target. That can reduce S8, the M7
unit-specific-value term. It changes none of R1, S1–S7, S9, or S10, and it
does not create the M1 atlas `[VERIFIED: dependency map]`.

### Why it is not justified now

1. M7 is currently `UNMEASURED` because the required capture is absent
   `[VERIFIED]`; buying the target is necessary for the proposed route but is
   not itself a pass.
2. The paid certificate's uncertainty and covariance are unknown
   `[VERIFIED]`. Traceability without a fit-for-purpose uncertainty does not
   answer the scorecard.
3. Nominal batch values are demonstrably too uncertain for safe substitution:
   worst-patch p95 **2.6445 DeltaE00** `[ASSUMED model; VERIFIED calculation]`
   exceeds both **1.0 DeltaE00** tight bars and the **2.0 DeltaE00** p95 bar
   `[VERIFIED]`.
4. The scorecard's allowed tone envelope can itself create up to **1.162
   DeltaL-star** `[ASSUMED worst case; VERIFIED calculation]` on the darkest
   neutral, while actual illuminant/ICC and low-frequency flat residual remain
   unmeasured. The purchase does not reduce those terms.
5. The seam rule lacks a defined population and percentile implementation
   `[VERIFIED]`, so no certificate can yet guarantee that arm.

### Falsifiable gate

Before purchase, obtain from ISA at **$0** `[ASSUMED]`:

1. a sample of the exact certificate supplied with the matte Nano option;
2. confirmation that it is serial-linked to the delivered unit;
3. per-patch spectral covariance or D50/two-degree Lab covariance, measurement
   geometry and specular condition, coverage factor, date, and expanded
   uncertainty;
4. covariance sufficient to calculate every required patch-to-patch
   difference.

Those requested fields are `[ASSUMED: procurement acceptance information]`.

Then apply this predeclared decision:

- **Reject** if any patch or required difference has `U95 > 0.25 DeltaE00`,
  if covariance cannot be propagated, or if the certificate is not tied to
  the unit `[ASSUMED policy]`.
- **Continue, but do not yet call the purchase sufficient**, if every patch and
  difference is `U95 <=0.20 DeltaE00` `[ASSUMED policy]`.
- Before the return window closes, capture the registered ramp, grey/target
  repeats, illuminant repeats, flats/darks, and boundary geometry. **Keep**
  only if the complete M7 reference chain is `U95 <=0.25 DeltaE00` and the
  systematic nuisance sweep leaves non-zero margin to every M7 bar
  `[ASSUMED policy]`.

This makes the recommendation falsifiable. A conforming certificate and
preflight reverse "do not buy"; a missing or larger uncertainty confirms it.
Today the answer is **no**.

## 7. Limits

- No scored M1, M2, M3, M4, M5, M6, M7, M9, or M10 capture exists in a form
  that permits a current verdict-margin calculation `[VERIFIED]`. For those
  axes this report gives the exact flip formula and boundary sensitivities,
  not invented observed margins.
- The ISA certificate uncertainty is unknown `[VERIFIED]`. The
  **2.6445 DeltaE00** p95 screen `[ASSUMED model; VERIFIED calculation]` uses
  independent Gaussian Lab components from nominal batch statistics. Real
  covariance, bounded distributions, within-sheet variation, and aging can
  change it. It must not be reported as certificate uncertainty.
- The M7 tone result is an aligned worst-case of the permitted sentinel
  deviations, not a measured output error `[ASSUMED]`.
- The M7 patch-noise and PRNU estimates assume an eroded patch size and
  correlation area from the planned geometry `[ASSUMED]`. Low-frequency
  illumination and corrected flat residual are excluded.
- The registration-to-transfer calculation assumes Gaussian jitter and a
  sinusoid at the licence edge `[ASSUMED]`; real local warps require direct
  image-domain reruns.
- M84b depth and magnification results are proxies from a different capture
  `[INHERITED: provenance checked]`. They demonstrate achievable scale, not
  the uncertainty of future M1 or M10 data.
- No RAW was decoded and no Cargo workload was run `[VERIFIED]`. Existing
  reports and retained numerical artifacts were read; their acquisition
  pipelines were not re-executed.
- This report does not ratify the pending M1 proposal, its sampling gate, or
  the M7 `U95` policy. Those are registrar/owner decisions. It supplies the
  missing quantities and a pre-results rule with explicit assumptions.

## 8. Reproduction

Run:

```powershell
python experiments\M144-reference-uncertainty\analyze.py
```

The script performs the CIEDE2000 self-check, reads the retained ISA workbook,
simulates the stated nominal-batch model, computes camera-noise, registration,
tone, quantisation, count-threshold, M8, and M10 sensitivities, extracts the
scorecard success paragraphs, hashes every input, and writes
`experiments/M144-reference-uncertainty/results.json` `[VERIFIED]`.

The final read-only inventory matched the initial file counts, byte counts,
timestamps, paths, and SHA-256 digests for both protected capture trees
`[VERIFIED]`; the exact check is recorded in
`experiments/M144-reference-uncertainty/read-only-tree-verification.json`.
