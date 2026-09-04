# Truth-referenced detail: capture decision and conditional instrument

Status: Proposal

Decision: **CAPTURE REQUIRED; CONDITIONAL GO for commissioning; NO-GO for any
score or SOTA claim**

Owner: lane-TRUTH

Scope: M1 detail only. This document designs an instrument and its capture. It
does not take a claim-bearing reading, revise the scorecard, or open the sealed
holdout.

## 0. Decision first

**ARGUED.** Yes, a truth-referenced M1 instrument requires additional physical
data in the incoming session. The current main sweeps, fixed-focus witnesses,
flats and darks do not contain an independently sampled image of the same
nonperiodic subject. Without one, every available candidate must infer detail
from a degraded output, another realization of the same degradation, or a
merge made by the system under test. Those are exactly the families that have
failed or remain uncommissioned.

**ARGUED.** Add **160 frames** after all main sweeps and their fixed-focus
witnesses:

| Block | Frames | Operator instruction |
|---|---:|---|
| `TR-REF-NEAR` | 32 | Same patch, maximum 2.8x reproduction, fixed-focus intersection in the near third |
| `TR-REF-MID` | 32 | Same patch and framing, fixed-focus intersection in the middle third |
| `TR-REF-FAR` | 32 | Same patch and framing, fixed-focus intersection in the far third |
| `TR-FLAT-C` | 32 | Reference-only flat, third diffuser position/orientation |
| `TR-DARK-C` | 32 | Reference-only dark, matching the fixed reference exposure |
| **Total added** | **160** | 96 subject frames plus 64 calibration frames |

**MEASURED.** The FE 100 mm F2.8 Macro GM reaches 1.4x natively and 2.8x with
the SEL20TC; the current session already specifies that lens and 2x
teleconverter (`docs/research/F-camera-lens-optics.md:12-13,61-66`;
`docs/capture-requests/2026-09-319-frame-session.md:223-229`).

**ARGUED.** The subject blocks must be shot as follows:

1. Finish every main sweep and fixed-focus witness first. Do not touch the
   target, target tilt, lighting, polarizers, camera roll, or camera yaw.
2. Only then make the axial camera move needed to reach the lens's maximum
   2.8x reproduction and reframe the **same nonperiodic patch**. Keep at least
   four surrounding grid or fiducial intersections in the frame. Fill as much
   of the sensor as possible with the patch rather than with the periodic grid.
3. Turn focus bracketing off. Set one manual focus position for the near third,
   approach it from the same focus direction every time, lock it, and take 32
   lossless-compressed 14-bit RAWs without moving focus. Repeat independently
   for the middle and far thirds. Each setting needs only a narrow in-focus
   strip through its named third; gaps between strips are expected and are not
   scored. These are three fixed-focus bursts, not one bracket and not an
   interleaved protocol.
4. Use ISO 100, f/5.6, fixed white balance, EFCS, IBIS off, OSS off, the same
   warmed flicker-free light and the same crossed-polarizer state as the main
   blocks. Begin with 1 s. If the axial move changes transmission enough to
   make that exposure unsuitable, select one replacement shutter time before
   the first reference burst, use it unchanged for all 96 reference subject
   frames, and use the same time for `TR-FLAT-C` and `TR-DARK-C`. Do not
   auto-expose the three focus positions separately.
5. After the 96 subject frames, shoot 32 reference-only flats with a diffuser
   position or orientation not used by flat A or B, then 32 warmed darks at the
   reference exposure. Discard the first two darks operationally in the same
   way as the main calibration groups, but retain every RAW in the manifest.
6. Record the reference focus positions, shutter time, lens-reported focus
   state if available, camera-to-stage move, and four fiducial coordinates.
   Do not report "2.8x" from the lens name alone: the analysis must measure the
   actual reference/main subject-sampling ratio from pixels per common grid
   period. Absolute grid pitch is not needed for that ratio.

**MEASURED.** The main request already requires a coplanar nonperiodic patch
beside the grid because a periodic target can carry its own answer
(`docs/capture-requests/2026-09-319-frame-session.md:71-101`). It also requires
IBIS and OSS off, ISO 100, 1 s, f/5.6, fixed white balance and 14-bit
lossless-compressed RAW (`docs/capture-requests/2026-09-319-frame-session.md:220-237`).

**MEASURED.** The A7C II focus bracket drives a complete ladder rather than
allowing two exposures to be interleaved at one focus node. The existing
request therefore added separate fixed-focus witnesses around the independent
sweeps (`docs/STATUS.md:1946-1973`;
`docs/capture-requests/2026-09-319-frame-session.md:138-173`). The reference
protocol above does not require an impossible interleave.

**ARGUED.** Thirty-two frames per focus position are required because they
provide two independently calibrated 16-frame reference halves. The halves
are needed to measure reference noise, shared calibration leakage and transfer
uncertainty without asking the output being scored to validate its own truth.
Three focus positions are required because the target is tilted and depth of
field is smaller at the higher reproduction ratio. A scored site may come from
one fixed-focus average only; no site may cross a seam and no focus-stacking
algorithm may construct the reference.

### 0.1 Reference eligibility and the fallback decision

**ARGUED.** The desired reference/main subject-sampling ratio is at least
`2.0x`. A ratio at or below `1.25x` is an automatic no-go. A ratio between
`1.25x` and `2.0x` is only conditionally usable if a later registrar freezes
and the commissioning battery clears reference-MTF, split-reference SNR and
resampling-uncertainty bars before holdout rendering.

**ARGUED.** Those are proposed capture-eligibility thresholds, not active M1
score bars. The scorecard registrar must ratify or replace them before the
holdout is opened. Sampling ratio alone is not enough: the reference optic
must also show superior object-space transfer in every licensed band. A
higher pixel count with worse reference defocus or aberration is not truth.

**ARGUED.** If the main setup is already at the lens's maximum 2.8x
reproduction, this lens cannot create a higher-sampling truth reference. The
session then needs one of these replacements:

1. a different optical path that gives at least 2x more subject pixels per
   millimetre while keeping the same patch and fiducials; or
2. a traceable, nonperiodic chrome-on-glass or photomask target with a native
   design map, features spanning the licensed main-sensor band, and at least
   256 independent guarded cells, captured with the same A/B repeat,
   fixed-focus and calibration discipline.

**ARGUED.** The existing periodic grid is not that replacement. It is useful
for geometry and scale, but it is predictable. The current capture request
withdrew a certified target under the previous relative-only M1 design
(`docs/capture-requests/2026-09-319-frame-session.md:71-84`). This proposal
changes the premise: if no oversampled same-subject reference is available,
known physical truth becomes necessary.

**ARGUED.** If neither replacement can be shot, the honest result is:
**no admissible truth-referenced detail reading can be taken from this
session**. Preserve the main session for the other axes, but leave M1
`UNMEASURED`.

## 1. Verified starting point

**MEASURED.** The scorecard remains `0/12 MEASURED`; M1 has neither an admitted
statistic nor a numeric bar and blocks several quality claims
(`docs/proposals/2026-09-sota-scorecard.md:473-505,544-577`).

**MEASURED.** Six tested detail statistics do not supply the missing
instrument:

| Candidate | Deciding observation | Result |
|---|---|---|
| `Q25` slant-edge | USM/base `5.560744x`; genuine sigma-1.20 improvement `0.977981x` | Rewards fake sharpening and gives real improvement the wrong sign |
| Three slanted-edge implementations | approximately `+9.9%` after USM | Presentation-sharpness diagnostics only |
| native `S_25` | USM/base `1.028294x` after the 64-site expansion | Outside the unchanged 1% arm |
| candidate 1 | USM/base `1.095732x`, UCB95 `1.129895` | Bounded finite reader rewards accessibility |
| FRC | exact common-filter cancellation | Immune to USM and blind to blur |
| candidate 2 | not run after the ordered FRC stop | Uncommissioned, not empirically dead |

**MEASURED.** The slanted-edge values and sign reversals are recorded in
`docs/research/M-PHASE0-SLANTEDGE.md:202-212,251-278`. Candidate 1's finite
128-moment, ridge-logistic estimator returned `1.095732x` under unclipped USM
even though the population estimand obeys data processing
(`docs/research/M-CAND1.md:38-55`). FRC's exact finite-sample cancellation and
its blur blindness are derived and demonstrated in
`docs/research/M-FRC-VIABILITY.md:215-285`.

**MEASURED.** Candidate 2 is a full-rank, unregularized, full-covariance
Hotelling construction with an ordered arm sequence and exact congruence
conditions (`experiments/M-CAND2/PREREGISTRATION.md:21-94`). It is
uncommissioned because the previous lane stopped when FRC failed, and its
registered clipping arm had no rail hits
(`docs/research/M-CAND2.md:20-45`). This proposal reuses candidate 2's exact
linear-equivariance lesson; it does not present the same algebra as an
independent discovery.

**MEASURED.** Earlier internal truth-reference work is also a warning, not a
free pass. A truth-referenced `0.30-0.40` wedge preferred Hamilton-Adams by
9.7%, while later real-capture evidence found no useful detail and additional
maze artifacts (`docs/research/BUILD-SHARP.md:3945-3955`). M57 likewise found
that a ground-truth oracle FSC at one frequency remained blind to a common
linear filter (`docs/research/M57-detail-metric-from-first-principles.md:98-125`).

## 2. What truth-referencing does and does not solve

### 2.1 A direct fidelity scalar still fails failure mode A

**DERIVED.** Let the physical truth be `x`, the delivered image be
`y = Hx + n`, and a deterministic post-render sharpening operator be `U`.
A squared-error fidelity score compares

```text
E_base = ||Hx + n - x||^2
E_usm  = ||U(Hx + n) - x||^2.
```

There is no ordering theorem that forces `E_usm >= E_base`. If `H` is a blur
and `U` partially approximates its inverse, the bias term
`||(UH - I)x||^2` can shrink by more than the transformed-noise term grows.
The sharpening contains no new scene information, yet the fidelity estimate
improves. SSIM, PSNR, learned perceptual distances and other single-image
fidelity scores have the same logical opening unless a separate proof closes
it.

**ARGUED.** This is the truth-reference version of candidate 1's accessibility
failure. Candidate 1 made information easier for a bounded reader. A direct
fidelity score can make a blurred image easier to match to the reference. The
reference changes what "correct" means, but it does not make every finite
estimator immune to a helpful-looking inverse filter.

**MEASURED.** This repository has already seen a truth-referenced band score
select an algorithm later rejected for artifacts
(`docs/research/BUILD-SHARP.md:3945-3955`). Truth reference is therefore
necessary for the proposed transfer test, but direct fidelity alone is not
sufficient.

### 2.2 The information component escapes failure mode A only structurally

**DERIVED.** For each independent site, let `x_s` be a fixed vector of
reference-side truth features and let `y_s` be the complete linear output
pixel vector for the registered observation support. With centered sample
covariance matrices

```text
S_xx = X'X / (n - 1)
S_yy = Y'Y / (n - 1)
S_xy = X'Y / (n - 1),
```

define squared canonical correlations as the eigenvalues of

```text
K = S_xx^-1 S_xy S_yy^-1 S_yx
```

and define the truth-referenced canonical information functional

```text
J_raw = -0.5 * sum_i log2(1 - rho_i^2).
```

This is a second-order Gaussian information functional, not a claim that the
natural scene is exactly Gaussian and not a learned ideal observer.

**ARGUED.** Finite-sample canonical correlation is upward biased. The reported
information component is therefore

```text
J_TR = J_raw - median_pi J_raw(X_pi, Y),
```

using a registrar-frozen set of block-respecting truth-label permutations
`pi`, shared across algorithms and arms. The correction is not floored at
zero. Each permuted term obeys the same congruence identity as the observed
term, so null correction does not reopen the USM accessibility defect.

**DERIVED.** If a nonsingular linear post-filter `A` is applied to every output
vector, then

```text
S_yy' = A S_yy A'
S_xy' = S_xy A'
```

and therefore

```text
S_xy' S_yy'^-1 S_yx'
  = S_xy A' (A S_yy A')^-1 A S_yx
  = S_xy S_yy^-1 S_yx.
```

Every `rho_i` and `J_TR` is identical on the finite sample. A full-rank USM
cannot buy accessibility because there is no fitted classifier, selected
moment set, capacity limit, ridge penalty or arm-specific optimization to
tighten. The equality is in the computed statistic, not merely in a population
estimand.

**ARGUED.** That protection is conditional and deliberately brittle. The
instrument must refuse rather than add covariance shrinkage, diagonal loading,
PCA truncation, selected moments, outcome-chosen bands, learned embeddings or
any other non-equivariant capacity limit. For the theorem-bearing USM arm, site
extraction happens first and the arm applies an explicitly registered square,
full-rank operator to the complete `y_s` vector with a fixed boundary rule; no
post-filter crop is allowed. A crop from a globally filtered image is not
automatically covered, because outside-support pixels enter the crop. If the
rank and sample-size gates cannot be met without regularization, `J_TR` does
not exist for that run.

**ARGUED.** The battery therefore contains two USM arms. The site-local square
operator tests the exact finite-sample theorem. A second full-frame USM,
followed by the ordinary site extractor and with all scored sites far from the
frame boundary, tests the real rendering path empirically against the frozen
1% recommendation. Failure of either arm kills the candidate. The exact proof
must not be quoted as if it covered an unexamined crop or boundary mode.

**MEASURED.** Candidate 1 failed specifically because its implemented
128-moment map and finite ridge-logistic optimization were not equivariant,
whereas candidate 2 preregistered a full-rank, unregularized covariance
estimator (`docs/research/M-CAND1.md:38-55`;
`experiments/M-CAND2/PREREGISTRATION.md:21-50`). Those are the repository
precedents for the prohibition above.

### 2.3 The same proof reproduces failure mode B

**DERIVED.** The congruence proof does not know that `A` is a sharpening
filter. If a common post-render blur is nonsingular on the finite support, it
also leaves `J_TR` unchanged. Truth-referencing has not repealed the
invariance/blindness tradeoff. It has only made a second, non-normalized
comparison to truth possible.

**DERIVED.** In a scalar stationary mode with pre-noise optical transfer `h`,
truth power `S_x` and independent noise power `N`,

```text
rho^2 = |h|^2 S_x / (|h|^2 S_x + N)
J_raw = 0.5 log2(1 + |h|^2 S_x / N).
```

A genuine optical improvement made **before** sensor noise raises `|h|` and
raises the raw functional. A physical blur made before noise lowers both in
this stationary mode. The reported null-corrected statistic is admitted only
if the frozen optical-direction arms preserve those orderings. A common
post-render filter multiplies signal and already-present noise together and
cancels. This is the desired distinction between registered truth
recoverability and presentation, but it means `J_TR` alone cannot satisfy the
blur arm.

### 2.4 The required escape is a non-compensating certificate

**ARGUED.** The proposed instrument is not one scalar. It is the joint
certificate

```text
TRD = (J_TR, F_TR)
```

where higher `J_TR` means more recoverable truth-referenced information and
`F_TR` is a vector of transfer departures from the independent reference.
`F_TR` may veto or make a result worse. It may never create a detail win.

**DERIVED.** Split the reference burst into independently calibrated halves
`R_1` and `R_2`. For each frozen frequency mode `k` and output repeat `Y`,
estimate the output-to-truth transfer with a cross-fitted ratio

```text
h_hat_k =
    sum_s Y_s,k * conj((R_1,s,k + R_2,s,k) / 2)
    -------------------------------------------------
    sum_s R_1,s,k * conj(R_2,s,k).
```

The denominator removes additive reference-noise power in expectation, but
the finite-sample ratio is not itself unbiased. The final estimator must
preserve the split labels, report its ratio bias in the reference uncertainty,
and never reuse one noisy reference as both truth and noise estimate. A later
implementation audit may replace the displayed ratio with an algebraically
equivalent errors-in-variables cross-fit, but not with a self-normalized
output-only correlation.

**ARGUED.** For each preregistered band below `0.25 cyc/native output px`,
`F_TR` reports, separately and without compensation:

```text
attenuation_b = weighted departure of |h_hat| below 1
overshoot_b   = weighted departure of |h_hat| above 1
phase_b       = weighted departure of arg(h_hat) from 0
residual_b    = deterministic output energy not explained by the reference,
                after independently estimated temporal and reference noise
```

No average over these four components or over bands is claim-bearing. The
reference-power weights and bands are fixed before holdout rendering.

**DERIVED.** A frequency-wise common residual can be estimated without
rewarding temporal noise by combining the two main repeats:

```text
C_YY,k       = Re sum_s Y_A,s,k * conj(Y_B,s,k)
C_RR,k       = Re sum_s R_1,s,k * conj(R_2,s,k)
C_YR,k       = (1/4) sum_s [
                   Y_A,s,k * conj(R_1,s,k) +
                   Y_A,s,k * conj(R_2,s,k) +
                   Y_B,s,k * conj(R_1,s,k) +
                   Y_B,s,k * conj(R_2,s,k)]
residual_k   = C_YY,k - |C_YR,k|^2 / C_RR,k.
```

The estimate may be negative from finite-sample variation and is never
clipped into success. A deterministic texture shared by A and B but absent
from the independent reference raises `C_YY` without the corresponding
truth cross-term and is therefore exposed by the residual component. Any mode
whose `C_RR` is nonpositive, phase-inconsistent between reference halves, or
not significantly above its reference-noise uncertainty is refused.

**DERIVED.** Relative to truth:

| Input to the instrument | `J_TR` | `F_TR` | Joint ordering |
|---|---|---|---|
| `Y = X` | maximum for the given noise | all transfer departures zero | truth |
| `Y = B X`, nonidentity low-pass blur | invariant if blur is post-noise; lower if pre-noise | nonzero attenuation and/or phase departure | below truth |
| `Y = U X`, nonidentity USM | invariant if USM is post-noise | nonzero overshoot and/or phase departure | below truth |
| sharper optics before noise | higher | attenuation no worse and normally lower | eligible to be better |
| USM applied to an already blurred output | unchanged | may improve or worsen | never better, because `J_TR` did not rise |

**DERIVED.** The last row is important. A sharpening filter can legitimately
move a biased transfer closer to one. The design does not deny that. It denies
the filter a detail win because transfer fidelity is veto-only and the
information component is exactly unchanged. This is the precise reason the
pair escapes failure mode A without pretending that every fidelity number is
sharpening-monotone.

**DERIVED.** Blur and over-sharpening both rank below truth because
`|b_k - 1| > 0` for any nonidentity blur transfer `b_k` in a licensed mode and
`|u_k - 1| > 0` for any nonidentity sharpening transfer `u_k`. They lie on
opposite sides of one and cannot cancel because attenuation and overshoot are
reported separately. This closes failure mode B for the joint certificate,
not for `J_TR` by itself.

### 2.5 Why no claim-bearing scalar is proposed

**ARGUED.** A weighted scalar such as `J_TR - lambda F_TR` reopens the problem.
For any finite `lambda`, a sufficiently large apparent fidelity improvement
can compensate for zero registered information gain, or an information gain
can hide an arbitrarily bad artifact component. Choosing `lambda` from
observed results would also be outcome-dependent tuning.

**MEASURED.** The scorecard already forbids a composite headline score and
requires joint tuples with no compensation
(`docs/proposals/2026-09-sota-scorecard.md:108-113,1125-1130`). M57 separately
concluded that the defensible stacker claim is two-dimensional rather than a
one-number detail claim (`docs/research/M57-detail-metric-from-first-principles.md:91-94,629-637`).

**ARGUED.** The defensible conclusion is therefore narrower than "no scalar
can exist" as a theorem. It is: **no single scalar is presently justified
against both observed failure modes without adding a model-specific
compensation rule that this program has already ruled inadmissible.** The
joint certificate is the candidate that remains.

## 3. What counts as truth

### 3.1 Higher-magnification same-subject reference: recommended

**ARGUED.** The reference is a higher-subject-sampling, fixed-focus RAW atlas
of the exact patch in the scored main sweeps. It is not a rendered JPEG, not a
focus-stack output, not a deconvolution, and not a synthetic target inferred
from the candidate output.

**ARGUED.** Each 32-frame focus burst is dark/flat corrected with the
reference-only `C` masters and split 16/16. Frames may receive analytic
translation correction before a straight linear mean. Near, middle and far
sites are assigned by a geometry-frozen strip map. Each scored site must lie
fully inside one strip and one focus burst; seam pixels and feathering are
excluded. The atlas is therefore a set of fixed-focus averages, not a fourth
stacker.

**ARGUED.** "Independent" means:

- the reference has more measured subject samples per millimetre;
- it is captured in separate exposures after the main blocks;
- it is made without the algorithm under test or any comparator merger;
- its two 16-frame halves and calibration master are disjoint from main A and
  B;
- its geometry is estimated without looking at a candidate's score; and
- the algorithm under test never receives the reference.

Using the same subject and lighting is intentional and is not a dependence
defect. Sharing a flat master, output merger, selected score sites or
score-driven registration would be.

**ARGUED.** The higher-magnification image is a qualified proxy for optical
truth, not perfect ground truth. It licenses only modes for which all of these
later-frozen gates pass:

1. measured reference/main subject-sampling ratio from common fiducials;
2. split-reference signal-to-noise;
3. reference focus and transfer sufficiency at the licensed subject
   frequencies;
4. no clipping or nonlinear RAW transfer;
5. reference-half agreement;
6. geometry and resampler sensitivity; and
7. enough nonperiodic reference power in every claim-bearing band.

A failed gate produces `UNMEASURED`, not a lower score.

### 3.2 Dense focus stack: useful, but not optical truth

**ARGUED.** The 91-frame `sw1` pass may answer one narrower question:
"Does a sparse sweep converge toward the output produced by the same merger
from a denser depth sampling?" It may support depth-sampling adequacy for a
fixed algorithm and fixed rendering contract.

**ARGUED.** It may not license:

- absolute optical detail;
- a comparison between mergers;
- sharpening safety;
- artifact freedom;
- truth fidelity; or
- a SOTA claim.

The dense merge is generated by the same possibly flawed operation as the
sparse merge, so shared blur, hallucination, registration defects and tone can
agree perfectly. Treating it as truth would move the circularity one level
up, not remove it.

**MEASURED.** The incoming request contains a density ladder and independent
repeat passes, but the current scorecard explicitly says the existing burned
grid and development-only high-resolution slide may commission an instrument
and may not supply its scored value
(`docs/proposals/2026-09-sota-scorecard.md:278-285,337-355,551-552`;
`docs/capture-requests/2026-09-319-frame-session.md:104-133`).

### 3.3 Known physical target: valid alternate, not the current grid

**ARGUED.** A certified physical target can replace the higher-magnification
atlas only when its **two-dimensional, nonperiodic geometry** is independently
known at substantially finer sampling than the main sensor. A suitable object
is a random binary microdot or pseudorandom chrome photomask with a traceable
design file, fiducials, features spanning the licensed band and enough
guard-separated cells for cluster inference.

**ARGUED.** A USAF chart, Siemens star or regular microscope grid may help
calibrate geometry and transfer, but none alone is sufficient for a
natural-detail claim. Repetition makes the answer guessable, sparse bars
under-sample artifact behavior, and radial/edge summaries can reward
presentation sharpening.

## 4. Registration and resampling contract

**MEASURED.** Registration is a first-order threat in this repository. A prior
nontranslation residual missed the `0.10 px` gate at `0.107703`; an independent
implementation reproduced `0.105202`, and the battery found wrong-sign and
local-warp failures (`docs/research/M-PHASE0-SPLIT2.md:1-18,148-170`).
A prior down/up resampling path moved one claim band by `77.5%`
(`docs/research/V-HEADTOHEAD3.md:442-453`).

**ARGUED.** The native candidate/comparator output is never resampled. The
common-grid procedure is:

1. Decode and linearize RAW through the frozen product path. Keep the output
   on its native pixel grid.
2. Estimate reference-to-main geometry from grid/fiducial coordinates and
   low-frequency input copies that are disjoint from scored sites. No output
   detail statistic participates.
3. Freeze one reference-side geometry for each of the near, middle and far
   fixed-focus bursts, including any measured focus breathing. Reuse that
   three-map set for all algorithms and all kill arms.
4. Apply scale, rotation, optical-distortion mapping and pixel-footprint
   integration to the **oversampled reference only**.
5. Remove candidate translation analytically. In spectral calculations use a
   unit-modulus Fourier phase ramp; in pixel calculations shift the
   reference-side footprint integrals. Never interpolate the candidate.
6. Restrict every claim mode to `<=0.25 cyc/native output px`, with the
   antialias transition entirely on the reference side.
7. Fit no local warp to improve a score. If the frozen physical mapping leaves
   excessive local residual, refuse the site or the run.

**MEASURED.** The scorecard requires native-output work, analytic translation
handling, scale disagreement `<=0.10%`, rotation `<=0.02 degrees`, and
nontranslation residual `<=0.10 native output px RMS`
(`docs/proposals/2026-09-sota-scorecard.md:225-235`). The head-to-head
verification likewise states that output pixels are never resampled
(`docs/research/V-HEADTOHEAD3.md:296-304,401-404`).

**ARGUED.** Reference resampling is unavoidable because the point of the
capture is a different subject-sampling grid. It is admissible only as a
frozen measurement operator. Before any holdout rendering, the registrar must
freeze:

- the reference pixel-footprint model;
- the antialias filter and support;
- the optical-distortion model;
- two alternate reference-side kernels used only as a sensitivity arm; and
- a maximum allowed change in `J_TR` and every `F_TR` component between them.

If that uncertainty consumes the decision margin, the result is
`UNMEASURED`. The instrument may not select whichever kernel favors Strehl.

## 5. Exact decision relation

**ARGUED.** The claim-bearing result is a paired comparison of Strehl to each
comparator, reported by independent repeat and by band. Let
`Delta J = J_TR(strehl) - J_TR(comparator)` and let each
`Delta F_j = F_TR,j(strehl) - F_TR,j(comparator)`, where lower fidelity
departure is better.

**ARGUED.** The only result allowed to say **BETTER DETAIL** is:

```text
lower_95(Delta J) > delta_J
AND
upper_95(Delta F_j) <= delta_F_j for every fidelity component j
AND
every provenance, geometry, rank, tone, clipping and reference gate passes.
```

`delta_J` is a strictly positive information margin. Each `delta_F_j` is a
noninferiority allowance set from reference repeat uncertainty, geometry
uncertainty and arm-blind development power. No fidelity improvement may
substitute for `Delta J <= delta_J`.

**ARGUED.** Other outcomes are:

| Outcome | Rule |
|---|---|
| `WORSE` | information is significantly lower, or a fidelity component is significantly worse without a qualifying information gain |
| `EQUIVALENT` | information and all fidelity components lie inside their frozen equivalence regions |
| `MIXED` | information rises but any fidelity component regresses, or components disagree across bands |
| `UNMEASURED` | any input, reference, rank, transfer, geometry, tone, clipping, power or provenance gate fails |

**ARGUED.** `MIXED` and `UNMEASURED` do not satisfy M1 and cannot be rounded
into a win. Results are reported for Strehl versus Zerene and Strehl versus
Helicon separately. There is no average-comparator victory.

## 6. Estimator and sample contract

**ARGUED.** The commissioning implementation must use all of the following:

- at least 64 independent macro-sites, with uncertainty resampled at the
  macro-site level;
- enough disjoint micro-sites inside those macro-sites to meet a preregistered
  `n / max(p, q) >= 1.5` full-rank covariance gate for output dimension `p`
  and truth dimension `q`;
- a complete linear green or luminance output support window with a frozen
  site-local boundary rule for theorem-bearing filter arms;
- a fixed reference feature basis using only modes at or below
  `0.25 cyc/native output px`;
- no ridge, shrinkage, pseudo-inverse, PCA, learned embedding, selected
  moment, score-driven feature deletion or outcome-driven band choice;
- separate A and B readings before any summary;
- reference halves 1 and 2 retained through the calculation;
- cluster bootstrap or an independently justified cluster interval, with
  seeds and site manifest frozen; and
- exact refusal on covariance rank failure or an inadmissible condition
  number, rather than a regularized number.

**ARGUED.** The reference basis may reduce the truth dimension because it
defines the licensed task. The output observation may not be reduced in a way
that destroys full-rank post-filter equivariance. The implementation must
demonstrate algebraically and with a finite random matrix self-test that its
actual centering, support, channel transform and covariance code preserve
`J_TR(Y) == J_TR(AY)` before any image arm is run.

**ARGUED.** The congruence guarantee covers nonsingular **linear** output
operators only. `J_TR` is still a finite second-order reader and can change
under an arbitrary nonlinear remapping. Gamma, logistic tone, clipping and
quantization therefore do not receive a theorem: the linear-output provenance
gate and their dedicated kill arms must refuse them. A learned hallucinating
restorer outside the frozen comparator envelope is also out of scope and
produces `UNMEASURED`, not an information claim.

**ARGUED.** The A and B main passes are not pooled as if they were twice as
many independent subjects. Each pass produces a complete paired comparison.
Agreement is a reproducibility gate; the subject and uninterrupted session
remain the holdout unit.

### 6.1 Commissioning data before the holdout

**ARGUED.** The sealed same-session reference is not commissioning data. The
implementation must reach a frozen, auditable state before those RAWs are
rendered:

| Commissioning need | Allowed development source |
|---|---|
| Congruence, null bias, blur/improvement direction, USM, tone, clipping and hallucination plants | Synthetic forward models with complete latent truth and frozen seeds |
| Reference split, transfer ratio, residual and reference-side resampler code | Existing development-only high-resolution slide plus synthetic pixel-footprint plants |
| Wrong-sign, fractional shift, scale, rotation and local-warp refusal | Existing phase-0 registration development captures and planted transforms |
| Rank, conditioning, site count and cluster interval | Existing development images with truth labels permuted, plus arm-blind power simulation |
| End-to-end physical rehearsal | Prefer a disposable-subject rehearsal using the same reference protocol; if omitted, all unexercised physical-reference branches remain automatic holdout refusal conditions |

**MEASURED.** The scorecard permits the burned grid and development-only
high-resolution slide to commission a new instrument but bars them from its
scored value (`docs/proposals/2026-09-sota-scorecard.md:551-552`). Their known
IBIS geometry defect makes them useful for failure and rejection paths, not
evidence that the final native-geometry success path will pass
(`docs/capture-requests/2026-09-319-frame-session.md:36-55`).

**ARGUED.** A disposable-subject rehearsal is strongly preferred because it
is the only way to exercise the full cross-magnification success path without
spending the holdout. It need not use the irreplaceable subject and does not
supply any M1 score. If no such rehearsal is made, the first unseen physical
condition that requires a code, mapping or threshold change burns the
holdout; the lane may only refuse and reshoot.

## 7. Ordered commissioning battery

**ARGUED.** The following arms and death conditions are frozen conceptually
by this proposal. A later scorecard registrar must freeze numerical
tolerances, powers, nuisance values and exact seeds on development data before
the sealed session is rendered. Arm order is binding: stop at the first death
and do not use later arms to rehabilitate the statistic.

| Order | Arm | Required result | Candidate dies if |
|---:|---|---|---|
| 0 | Provenance and potency | Every transform changes the intended samples; hashes and lineage are complete | The arm is a no-op, touches the wrong stage, or uses scored data to choose a parameter |
| 1 | Identity and permutation nulls | Identity is equivalent; shuffled truth gives no detail evidence | Null is significant, negative estimates are clipped into success, or the shuffled reference scores |
| 2 | Finite-matrix congruence self-test | `J_TR(Y) == J_TR(AY)` to numerical tolerance for random full-rank `A` | Actual code is not equivariant |
| 3a | Site-local information-free USM after all noise | Exact finite-sample `J_TR` equality; the joint verdict is never `BETTER` | Equality fails or fidelity alone promotes the arm |
| 3b | Full-frame information-free USM after all noise | Empirical `J_TR` equivalence on ordinary extracted sites | Recommended one-sided UCB for the ratio exceeds `1.01` |
| 4 | Common post-render Gaussian blur | `J_TR` remains equivalent and `F_TR` ranks blur below truth | Blur is called better/equivalent to truth or the fidelity channel is blind |
| 5 | Truth-sided filter pair | Exact truth beats both a low-pass copy and an over-sharpened copy | Either side is not worse than truth |
| 6 | Pre-sensor blur ladder | `J_TR` decreases monotonically and attenuation worsens | Any blur rung rises, or the effect is underpowered |
| 7 | Genuine optical improvement | `J_TR` rises and no fidelity component regresses | The sigma-1.20 improvement does not beat its blurrier control |
| 8 | Gamma-3 and logistic tone | Transfer sentinel refuses the run before a claim number | Either nonlinear arm produces a higher valid detail result |
| 9 | Clipping and quantization | A potent arm lowers the result or is refused | The arm raises a valid result; a rail-free "clipping" arm is invalid |
| 10 | Added independent noise | `J_TR` falls; fidelity cannot rescue it | Noise raises information or creates a win |
| 11 | Common-mode A/B plant absent from reference | No information gain; residual fidelity worsens | A repeated hallucination or FPN pattern is rewarded |
| 12 | Flat/no-target ROI | No detail evidence and no transferable truth band | A flat produces a positive claim |
| 13 | Shared-master and reference-leakage plants | Deliberate sharing is detected or worsens the result | Shared calibration correlation raises the certificate |
| 14 | Geometry plants | Integer/no-op, fractional shift, wrong sign, scale, rotation and local warp behave as preregistered | Wrong sign passes, candidate pixels are resampled, or local warp is fitted away |
| 15 | Reference-resampler pair | Both frozen reference-side kernels agree inside the uncertainty allowance | Kernel choice changes the verdict |
| 16 | Rank/regularization sentinel | Rank failure refuses; hidden ridge and PCA are detected | Any regularized fallback emits a claim number |
| 17 | Edge-angle and orientation ladder | No orientation creates a win from the same transfer | Result depends materially on edge angle |
| 18 | Dense-stack pseudo-truth trap | Lineage gate rejects a merger-produced reference for optical M1 | A dense merge is accepted as physical truth |
| 19 | Reference corruption | Blurred, sharpened, misfocused and wrong-strip references fail eligibility or widen uncertainty | A compromised reference silently changes the winner |

**MEASURED.** These arms incorporate the current scorecard's mandatory null,
pre-sensor blur, genuine improvement, USM, gamma, logistic, noise, edge-angle,
common-mode, flat and 64-site controls
(`docs/proposals/2026-09-sota-scorecard.md:563-577`). The `1.01` USM
recommendation preserves the scale used to kill candidate 1, but it is not an
active M1 bar until the registrar ratifies it in a later scorecard revision.

**MEASURED.** A clipping arm must prove it reached a rail. Candidate 2's
registered clipping arm had `0/2,088,960` rail hits and therefore did not test
clipping (`docs/research/M-CAND2.md:20-32`). Tone stability also cannot
substitute for optical-direction arms: `Q25` was nearly invariant to affine,
gamma and logistic tone and still rewarded USM and reversed genuine optical
improvement (`docs/research/M-PHASE0-SLANTEDGE.md:202-212`).

## 8. Leakage firewall and authority

**ARGUED.** Roles are separated as follows:

| Role | May do | May not do |
|---|---|---|
| lane-TRUTH | Define the estimand, capture, algebra, arm families and death semantics | Render the holdout, choose result-favouring nuisance values, set the final numeric bar, or take the claim reading |
| scorecard registrar | Freeze dimensions, bands, minimum effects, uncertainty allowances, arm values and status rules in a numbered pre-results revision | Run the claim-bearing analysis or revise a bar after seeing it |
| implementation auditor | Re-derive the finite estimator and inspect code/data lineage independently of the stacker | Tune the production stacker from reference outcomes |
| measurement lane | Run the frozen battery and comparator analysis on the sealed session | Change code, sites, bars, reference mapping or exclusions after unsealing |
| independent verifier | Re-run from RAW, re-choose preregistered nuisance branches and adjudicate discrepancies | Know or optimize for the desired winner |

**MEASURED.** The current scorecard says challenge outcomes and numeric
admission bars must be frozen in a later revision before score data are read
(`docs/proposals/2026-09-sota-scorecard.md:568-577`). It also bars the current
session from development and treats subject plus uninterrupted session as the
holdout unit (`docs/proposals/2026-09-sota-scorecard.md:276-295`;
`docs/capture-requests/2026-09-319-frame-session.md:36-55`).

**ARGUED.** Existing captures, synthetic forward models and a separately
declared development reference may commission the code. The incoming
high-magnification reference is part of the sealed holdout. It may be checked
for file integrity, EXIF, gross clipping and manifest completeness on arrival,
but no detail output, site selection, band choice, geometry tuning or
threshold choice may be made from it.

## 9. Prior art and scope

**MEASURED.** The repository prior-art tool passed its three commissioning
checks and was searched for `truth reference sharpening detail` during this
design. Its relevant matches included M46, M55b, M57, V-bestframe, M39, M80,
M95, BUILD-DEMOSAIC and BUILD-SHARP. Their disposition is not "superseded":

| Prior work | Result retained here | Why it is not the present instrument |
|---|---|---|
| M46 / M55b / M57 | A detail candidate needs a conjunctive, executable battery; output-only cross-power families have severe noise, gain and monotonicity limits | None had an independently sampled same-subject truth atlas and the accepted one-number result did not survive later verification (`docs/research/M46-detail-metric-measured.md:29-55`; `docs/research/M55-acceptance-spec.md:1-35`; `docs/research/M55-sigpow-verification.md:1-15`; `docs/research/M57-detail-metric-from-first-principles.md:29-81`) |
| V-bestframe | Native-grid, no-resample comparison and cross-repeat covariance can separate signal from temporal noise | It compares a merge to input frames from the same degraded capture and explicitly found raw band energy ranking noise (`docs/research/V-bestframe.md:1-31,55-100`) |
| M39 / M80 | Noise corrections need flat/no-target controls and must not clamp noise into detail | M39 measured a flat credited with `+35.5%` detail; M80 repaired a selector invariant by returning `NO TARGET`, not by forcing a number (`docs/research/M39-verify-detail-metric.md:1-35`; `docs/research/M80-invariant-repair.md:1-20`) |
| M95 / BUILD-DEMOSAIC | Known truth can separate scene-correlated transfer from fabricated output and can reveal defects invisible to power statistics | Both are synthetic or demosaic-specific truth instruments, not a same-subject focus-stack score (`docs/research/M95-demosaic.md:1-75`; `docs/research/BUILD-DEMOSAIC.md:1-75`) |
| BUILD-SHARP | Correct-band truth reference is necessary but can still select an artifact-bearing method | Its wedge is the direct warning against a fidelity-only promotion rule (`docs/research/BUILD-SHARP.md:3945-3955`) |

**ARGUED.** This proposal claims no novelty for canonical correlation, task
information, NEQ, split-reference transfer, truth/residual decomposition or
non-compensating scorecards. Its contribution is the specific conjunction,
capture lineage and refusal boundary required by the current M1 deadlock.

**MEASURED.** The project's DOI ledger resolved the relevant data-processing,
ideal-observer, Fisher-information, task-NEQ, FRC and Gaussian-copula
references on 2026-09-03
(`docs/proposals/2026-09-detail-instrument-investigation.md:376-395`).
The most relevant external foundations are:

- Cover and Thomas, data processing,
  [DOI 10.1002/047174882X](https://doi.org/10.1002/047174882X);
- Barrett, objective task image quality,
  [DOI 10.1364/JOSAA.7.001266](https://doi.org/10.1364/JOSAA.7.001266);
- Barrett et al., Fisher information and task performance,
  [DOI 10.1364/JOSAA.12.000834](https://doi.org/10.1364/JOSAA.12.000834);
- Wagner and Brown, task-based NEQ,
  [DOI 10.1088/0031-9155/30/6/001](https://doi.org/10.1088/0031-9155/30/6/001);
  and
- Nieuwenhuizen et al., FRC resolution measurement,
  [DOI 10.1038/nmeth.2448](https://doi.org/10.1038/nmeth.2448).

**ARGUED.** The name "information" in `J_TR` is scoped to its explicitly
declared Gaussian canonical functional. A successful commissioning would
license a comparative statement about recoverable, truth-referenced linear
information in the registered band and capture regime. It would not establish
general mutual information, perceptual quality, artifact freedom outside
`F_TR`, or universal optical resolution.

## 10. Final ruling

**ARGUED.** Truth-referencing does not by itself solve the detail problem. A
direct fidelity statistic can reward information-free sharpening, and a
structurally post-filter-invariant information statistic is blind to
post-render blur. The hypothesis survives only as a **joint,
non-compensating certificate**:

```text
more recoverable truth information
AND
no regression in transfer fidelity to independent physical truth.
```

**ARGUED.** That certificate has a structural answer to both known failure
modes, an independently sampled reference, a native-output geometry contract
and arms that can kill it. It is therefore worth commissioning. It is not yet
an admitted M1 instrument.

**ARGUED.** The operational decision is:

- **GO:** shoot the 160-frame higher-magnification reference block in the same
  session and seal it with the main holdout;
- **CONDITIONAL GO:** commission `TRD = (J_TR, F_TR)` on development data under
  the ordered battery, then require a registrar revision and independent
  implementation audit;
- **NO-GO:** do not use the dense stack, current grid, development-only
  high-resolution slide, direct MSE/PSNR/SSIM, learned perceptual score, FRC or
  any weighted information/fidelity scalar as the M1 truth instrument; and
- **CURRENT STATUS:** M1 remains `UNMEASURED`, and no detail-qualified SOTA
  claim is licensed.
