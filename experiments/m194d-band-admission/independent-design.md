# M194d independent design and falsifier audit

2026-09-07. Design only: no product edit, build, new capture access or candidate
render. Initial historical objections below were formulated and sent to Curie
before an implementation preregistration was available. The operator-specific
review and independently chosen controls were added after reading Curie's
`implementation-plan.md` and `implementation-preregister.md`, before product
implementation or any candidate result. Root owns release and the final choice.

**ARGUED recommendation:** one explicitly opt-in development experiment is
worth implementing for the now specified `FloorPedestalV1` law. It is not
redundant with the existing significance option, and prior evidence does not
already refute this particular change. Its positive weight at zero excess
removes a mathematical singleton discontinuity; that is not evidence that the
fixed TIFFs improve. The actual reconstructed pixels must decide usefulness.
Keep committed M194c `04128e041dabc0bdb86c64526cd8155dd0a0fd07`, all fixed
inputs, both reference targets and unchanged review triggers.

## Prior-art search and the conclusions that survive it

Command executed before design:

```text
python experiments/ORCH-drift-check/prior_art.py band admission merge
```

Read SYNTHESIS architecture/noise decisions and the current program, then the
following returned records and their relevant corrections. No historical capture
payload was opened or reprocessed.

| Prior work | Consequence for this experiment |
| --- | --- |
| ORCH-veiling; BUILD-HULL | A merge can lose badly to a physically relevant input while staying in the per-pixel input hull. Convexity and a post-clamp hull pass do not certify fidelity. Different reconstructed-band selections also need not form a pointwise convex image before the final clamp. |
| V-DILUTE | Its depth-dilution hypothesis was refuted on the measured subject. Do not justify hard admission by assuming every extra frame dilutes a soft winner. Measured accepted competitors, their actual weights and output noise matter; a generic N-factor argument is insufficient. |
| BUILD-BLEND | Actual multiband reconstruction can change the broad occlusion artifact, but this does not license a universal no-harm claim. The earlier known-scene optics/occlusion gates failed; its executable prints rows before warning rather than enforcing their exclusion. M194b's restricted scene commissioning is the usable present scope. |
| M70-through-focus-spectrum | Informative-frame count is not an optimal admission target. The architectural value of spectral weighting was much smaller than the benefit attributed to admitting more frames. Do not turn a count of available information into a calibrated threshold. |
| V-LINEAR-BANDS; V-SOFTCHECK-bandqual | Fixed frequency bands do not qualify every subject; power ratios can qualify noise through selection or gain. This experiment has known oriented waves and analytic colour, so use those explicit signals rather than a new generic high-frequency energy metric. |
| V-bestframe; BUILD-TRIAGE | Raw best-frame energy can be a noise maximum; source/output develop and gather paths change the comparison. Use the fixed actual original-frame-4 output on its existing common geometry, not a newly picked sharpest/noisiest frame or an unwarped reference. |
| M111-waxy-blobs | Larger admission is not automatically a fix: low effective counts, near ties and relative response dispersion matter, and averaging all frames can remove an artifact by defocusing everything. Several attractive mask-based explanations were withdrawn. Do not define the failure population from the candidate's own response map. |
| PHASE1-DESIGN; M138 audit | The old NO_COMMON_K result tested matching another operator's Kish widths and rendered no Pareto survivors. Its broad refutation was withdrawn, not converted into validation. Its selected-winner uncertainty, coarse per-frame coverage, noncentral term and spatial variance propagation remain uncommissioned for a new consumer. |
| M143 record in STATUS §2.9.44 | The 0.90 ratio was not shown to be outcome-tuned; that accusation was explicitly rejected. It was nevertheless unjustified and moved across estimands. Do not import it as a new temporal-noise acceptance bar. |
| M194b/M194c | There is now an actual software truth/noise benchmark, including adverse sparse pixels. Its scope and known tradeoffs are sufficient to reject an implementation, not to establish real-camera SOTA. |

The relevant Phase-1 source is
`docs/proposals/2026-09-phase1-design.md` and the prototype is
`experiments/PHASE1-DESIGN/reference.py`; neither is a current production
admission implementation. The M138 audit is
`experiments/M138-w1-gate-audit/REPORT.md`. Its corrected contract is still
explicitly draft/unbound in the inspected file. A bounded M194d experiment
must not silently emit PHASE1_GO or claim to complete that physical gate.

## Review of the actual proposed operator

The agreed experiment retains the current linear-DN luma Laplacian energy and
variance paths, and changes only their per-frame weight:

```text
E = smooth5(L_luma^2)                      DN^2
F = gate * beta_k * max(V_k,0)              DN^2
q = max(E-F,0)                             DN^2
a = q / max(F,1 DN^2)                      dimensionless
r = hypot(a,1) / 64                        dimensionless
w = exp(clamp(p * ln(r), -80,80))           dimensionless, also when q=0
```

The actual three-band exponents remain approximately3.92,2.8,2; the library
cap is8. This is a heuristic weight, not a calibrated admission probability.
There is no selected reference, energy-gap uncertainty, Anscombe transform,
new sensor model, second pass or retained winner array. Historical objections
to those unused mechanisms below do not block this narrower experiment.

**DERIVED, not measured:** these equations identify the falsifiable mechanism
and the limits of what the proposed intervention can establish.

1. **It differs from the previous significance option precisely where the
   singleton discontinuity occurs.** Current `pyramid.rs::select_weight`
   returns zero for `excess <= 0` before its optional `hypot`. For positive
   excess, the proposed law is algebraically the same shape as that function
   with `r_floor=1/64`, before floating-point fast-path differences and clamping.
   The corresponding old significance multiplier would be
   `gate/sqrt(2/NU_SMOOTH)`, about 5.17 at gate 2; it still leaves zero excess at
   zero weight. The saved `experiments/BUILD-SOFTGATE/pyramid-softgate.patch`,
   lines152-164, also keeps that rejection by mapping nonpositive excess to
   negative infinity.
   Neither mode already supplies the proposed positive below-floor baseline.
2. **The singleton mechanism has a closed-form control.** With one positive
   normalized excess a and N-1 zero excesses, write
   `R=(1+a^2)^(p/2)`. The preferred share is `R/(R+N-1)`, tending to1/N as
   a tends to zero. The legacy share is1 whenever its lone weight is positive.
   A component-only placebo that uses the candidate shape but restores the
   zero cutoff must still select that lone frame. This separates below-floor
   participation from above-floor weight softening; a legacy/candidate pair
   alone does not isolate those two changes.
3. **All-zero excess gives a mathematical mean, with a rounding caveat.**
   Equal positive `64^-p` weights normalize to an arithmetic mean. The existing
   all-zero fallback uses different floating arithmetic, so new-mode TIFF
   identity does not follow by algebra. The same caution applies to N=1.
   Require byte identity for the unchanged HardFloor arm; measure rather than
   assume candidate identity in these cases.
4. **High-signal agreement is asymptotic.** For positive excess before the
   clamp, new/old weight is `(1+a^-2)^(p/2)`, not exactly1. At a=10,p=8 it is
   already about1.0406. Distinct floors can change normalized relative weights.
   The strong-detail arm must differ from a mean destroyer, while exact
   high-signal byte identity is not a justified requirement.
5. **Positive tails can introduce dilution.** The preferred frame dominates
   only when R is much larger than N-1. V-DILUTE refuted a particular old
   deep-stack hypothesis; it does not establish safety for newly nonzero
   contributions from every below-floor frame. Noise-off waves and analytic
   colour are therefore decisive, even if flat temporal noise improves.
6. **Units are consistent within a declared numerical convention.** Dividing
   DN^2 by DN^2 makes a dimensionless. The `max(F,1 DN^2)` convention breaks
   global rescaling covariance when the floor crosses1. The baseline already
   has this regularizer. A unit test must state its F>=1 domain and retain an
   explicit below1 counterexample; it cannot claim arbitrary unit invariance.
   The 64 scale cancels in ideal within-band normalization only before the
   exponent cap. At the cap it can affect relative weights.
7. **Finite weights do not prove finite reconstruction.** For p<=8 and q=0,
   `64^-p >= 2^-48`, well above the smallest normal f32. There is no pedestal
   underflow in that range. Very small a can round `hypot(a,1)` to1, so strict
   monotonicity for every representable increment is not required. Conversely,
   `exp(80)` is finite but multiplying it by a large valid coefficient can
   overflow: a coefficient near32767 gives a product around1.8e39, above f32.
   This upper-end hazard also exists in the legacy accumulator. The proposed
   log path at p1/2 avoids a separate unchecked square; it does not prove an
   arbitrary-N numerator bound. Check the actual fold and collapse on the
   registered fixtures, and disclose an extreme component failure as such.
8. **Noise coupling remains.** Weights use the noisy coefficients they average;
   positive weights do not justify sigma/sqrt(N), unbiasedness or a Kish-based
   variance prediction. The current Gaussian variance levels and scalar probe
   beta remain approximations after gather, especially for heterogeneous signal
   and WB. Matching injected producer/model constants validates this software
   operator, not camera calibration. Green-shared weights also do not observe
   every chromatic component. Those are retained limitations, not new models.

The proposal now explicitly requires SoftPower, positive finite gate,
exponent in(0,8], significance_scale0, BaseBand::Mean, Fallback::Mean,
mean_coarse0 and Hull::InputRange or Unclamped in candidate mode. It rejects
PerLevel hull and mixed-mode absorb. This resolves the interaction ambiguity.
Nonfinite energy/floor inputs fail explicitly; candidate num/den/unweighted
sums are checked after every fold and absorb, resolved coefficients and
collapsed pixels before final hull projection. These checks are part of the
candidate's numeric refusal contract, not an optional observer. They add scans
without new retained arrays; no performance claim follows.

**ARGUED disposition:** the explicit refusal boundary is defensible for this
bounded opt-in experiment. It retains the declared weight law and does not
silently lower its cap or change accumulator precision. Every frozen benchmark
input must still finish with finite intermediates and actual TIFFs; refusal of
one is a recorded candidate/instrument failure, not permission to exclude that
case. A future wider input promise would need its own numeric solution. A
valid negative/clamped variance and an invalid NaN remain different caller
cases and must not be conflated as in M194c's early independent harness.

## Historical objections retained with their original scope

These were the first objections, before the actual narrower proposal arrived.
They apply if a future revived law follows the old proposal:
`E=smooth5(L²)`, `F=beta*v`, `q=max(E-F,0)`, winner=max(E), admission by an
energy gap divided by `sqrt(sigma²_Ew+sigma²_Ei)`, admitted weights proportional
to1/F, and below-floor-winner fallback to an arithmetic mean. M194d does not
implement that law. In particular, objections1-3,5 and8 must not be reported as
failures of its nonexistent winner, Anscombe path or second pass.

1. **A selected maximum is not a fixed pair.** Even when frames carry the same
   true signal, E_w is selected for a positive fluctuation. Its distribution
   changes with N and the frame-specific noise laws. Pairwise uncertainty
   cannot be labelled a confidence level for that winner-conditioned gap
   without separate commissioning. On a flat, max(E-F)>0 is common; it does
   not establish recoverable detail.
2. **Raw E can prefer high-noise frames.** If warp/WB makes F differ across
   frames, argmax(E) can prefer a larger noise floor. Subtracting F only after
   electing the reference does not remove that preference. Changing winner
   semantics would be a different operator and must be fixed before output.
3. **Energy covariance is not one universally transferable scalar nu.** For
   Gaussian band-noise vector n with covariance C and coherent signal s,
   `Var(sum_j a_j(s_j+n_j)^2)` has central term
   `2 sum_jk a_j a_k C_jk²` and noncentral term
   `4 sum_jk a_j a_k s_j C_jk s_k`. The same nu need not represent both.
   M138 already found that central null coverage did not commission noncentral
   signal behavior, and pooled coverage hid bad coarse per-frame coverage.
4. **A variance field is not an image.** Passing v through an ordinary
   Gaussian pyramid and multiplying by a scalar beta is an approximation for
   heterogeneous variance. Exact linear-filter variance needs squared taps
   and covariance. The prototype's spatially varying Poisson signal, gather
   and local CFA/WB all make that distinction relevant. Name the approximation;
   do not present it as an exact noise calculation.
5. **The generalized-Anscombe path has a different noise transfer.** Current
   Probe beta measures linear-DN white noise through gather and a Laplacian
   pyramid. Applying it to a nonlinear transformed decision field is not
   automatically calibrated, especially at low signal or with varying gain.
   Reusing it may define a heuristic experiment; it does not inherit a
   standardized probability or justify adding B6 unnoticed.
6. **Data-dependent weights invalidate the simple output-variance promise.**
   `sum(w_i² Var_i)/(sum w_i)²` is not generally the actual temporal variance
   when the weights are chosen from the same noisy coefficients. Conditioning
   on those weights changes the noise distribution. Kish n_eff is useful
   arithmetic, not an independent measurement of noise reduction. The actual
   eight-repeat output variance is the present instrument.
7. **Shared-green admission does not observe all colour structure.** A red/blue
   contrast mode may have little green signal; averaging it can lose colour
   detail while green noise improves. The fixed analytic colour and colour-null
   fixtures are mandatory. Their absence would make this assumption untested.
8. **More passes create an input contract, not merely a performance cost.**
   Both passes must consume identical decoded values, masks, geometry, WB,
   noise, stable original ordinals and probe seeds. A reindexed single-input
   comparator keeps its already declared local-zero seed; do not silently
   make it a different comparison. Reset FrameWorkspace before every new
   frame; M194c's independent harness demonstrated the failure when omitted.

No proposed rule gets a universal “never noisier than a single frame” guarantee
from positivity, inverse variance weighting, the input hull, or the presence of
an averaging fallback. The fixed flat/noise inputs can falsify such a claim but
cannot prove it over all cameras/scenes.

## Primary readout must keep the existing failures visible

Use the committed M194c full20-case/40-output matrix as the immediate baseline;
M194b remains historical context. Run all40 HardFloor outputs as byte controls
and all40 FloorPedestalV1 outputs without a proxy prefilter. Read every TIFF with
the versioned M194d adapter over the unchanged numerical scorer, retaining
the strict CameraLinear normalization, shape, crop, frame-4 gauge,
all eight fixed noise repeats, and both full-nine and single-input arms.

M194c's measured flat green temporal variance increased2.538%; one red flat
pixel moved104.447 post-WB DN adversely inside the scored ROI. Whole-ROI
noise/error means therefore cannot substitute for the sparse-error record.
The fixed plane already demonstrates that lower noise and error to the optical
observation can accompany greater error to the ideal latent target. Earlier
full-stack noise-off analytic colour RMSE was38.347 DN versus34.143 DN single;
the achromatic component was29.472 versus19.371 DN. These green summaries do
not replace per-channel data.

Re-use unchanged engineering review triggers: any channel RMSE increase>1 DN,
flat/plane temporal-variance increase>2%, or noise-off plane-wave amplitude
loss>1 DN requires explicit disposition. These are review triggers, not SOTA
acceptance or calibrated equivalence margins. Smaller changes remain reported;
the inherited finite numerical-accuracy rule still prevents unsupported rankings.

Independent complementary instruments I recommend, fixed before new output:

* Per repeat/channel, retain the maximum signed and absolute truth residual,
  its canonical coordinate and baseline/candidate values, plus the existing
  complete error and temporal rows. Report adverse truth-error change as well
  as absolute cross-version movement; a large beneficial repair is different
  from a large new error. Do not select only M194c's previously worst coordinate.
* Retain p99 and p99.9 absolute truth error as descriptive summaries alongside
  the maximum, never as a replacement. A single bad pixel can evade both
  quantiles. Root/Socrates own exact sparse-summary implementation and freeze;
  these are supplemental diagnostics, not revised benchmark bars.
* Keep the known oriented-wave complex response: amplitude and phase, to both
  existing targets, with no fitted gain/offset or new registration. Less noisy
  MSE can reward blur; amplitude alone can reward sharpening or miss phase loss.
* Colour and colour-null outputs must retain per-channel errors and the known
  analytic chromatic response. A pooled RGB score could hide opposite signs.
* Uncertainty remains paired by whole independent input-noise repeat. Pixels,
  CFA phases, pyramid bands and two deterministic reruns are not new independent
  physical replicates. Eight repeats give finite development evidence, not a
  precise rare-failure probability certificate.

## Independently rejectable commissioning controls

Separate component controls from the scored forty outputs. The independent
choices below were fixed after the operator was specified, before any candidate
execution. They rechoose the author's nine-frame checkerboard in frame count,
spatial pattern, amplitude, base level, active ordinal and threshold placement.

Use five80x64 f32 component frames, background4096, with alternating-row
stripes only in frame3. The others are constant. One Laplacian band uses p2;
within x[16,64),y[16,48), the period-two zero-DC stripe is killed by the
binomial lowpass, so its band coefficient is the stripe and its smoothed
energy is A^2. Start with A10 and three prospectively fixed floor values
99.9375,100,100.0625 (gate2, beta1, supplied variance F/2). These are fixed
input numbers, not a fit to a measured energy. They place the same signal
just above, exactly on, and just below the threshold. Assert that these three
cases actually occur on the consumer's energy plane. No result is evidence
if the fixture has not exercised them.

At F99.9375, a=0.0625/99.9375 and the preferred share is
`(1+a^2)/(5+a^2)`, approximately1/5. Its candidate stripe is approximately2
DN against legacy10 DN. At the other two floors the candidate mean remains
approximately2 DN. A component-only zero-cutoff placebo must still give10 DN
at the first floor and the fallback mean at the other two. Compare actual
BandMerge output to these independently derived values with0.004 DN absolute
tolerance at background4096; require at least5 DN discrimination between
candidate and the first-floor placebo. This is a powered software component
control, not a physical noisy-image sample or calibration relation.

Keep the same N, geometry and first floor for a separate A96 strong-signal
arm. Its predicted preferred share exceeds0.999; require >0.999, agreement
with the formula within the same0.004 DN output tolerance, and an output
closer to the selected96-DN stripe than to the19.2-DN mean. This is an
analytically chosen counterexample to an all-mean implementation, not an
amplitude search. Product three-band output is tested by the fixed matrix;
the one-band control does not pretend to commission the complete optics.

No component source has been written or run under this design. If actual API
constraints make a registered check invalid, preserve the failed attempt and
prospectively correct only that fixture, with the reason and source lineage.
Minimum useful additional checks and failure directions:

For the numeric refusal control, independently choose two80x64 frames with
alternating-row amplitude16384 at background24576, p8, F1. Their samples are
8192 or40960, within u16 range, and ideal band energy is2^28. The capped
positive weight times16384 exceeds f32; require explicit refusal before the
writer. This is a component stress input, not a newly rendered physical scene.
Also inject two individually finite partial numerator states at three-quarters
of f32::MAX into absorb: their sum must refuse. A deliberately nonfinite
resolved/collapsed value must fail before the hull could make it look finite.
These last two are labelled fault-injection checks, not reachable-noise claims.

| Control | What must be demonstrated; failure direction |
| --- | --- |
| Identity/no-op, N=1, equal frames | All40 HardFloor outputs must exactly reproduce M194c bytes. An additional original M194b entry render must demonstrate the unselected default, because explicit HardFloor is not that execution. Candidate single-frame/equal-frame output is checked within declared numerical semantics and actual byte differences reported. A reused frame0 cache can fake invariance: call next_frame before each add, use genuinely distinct frames, and retain a deliberate missing-reset component as a negative control. |
| Threshold participation and cutoff placebo | The five-frame stripe test above must establish actual q>0, q=0 and q clamped to0. Every valid candidate weight is positive; there is no rejected nonwinner or winner tie to commission. Require actual normalized output, not only helper weights. The zero-cutoff placebo isolates the discontinuity claim. |
| Flat/noisy null | Score the unchanged eight flat repeats first, including frame-specific beta/warp effects. The constant mean can appear good while rare coefficients fail. Whole-ROI temporal variance, truth-error tails and fixed-single comparison remain separate readouts; shared noise constants do not validate calibration. |
| Coupling attribution boundary | Removing the zero cutoff proves a component mechanism. Better actual flat pixels do not by themselves prove every old excursion was caused by that mechanism. No independent decision-replay observer is currently added; broad selection-noise attribution therefore remains unmeasured. A future replay would need its own prospective input and on/off/placebo proof. |
| Known signal and known destroyers | Deliberately distort exact truth by a known amplitude/phase change or blur: the truth error or known complex-wave discrepancy must increase. Known flat temporal-noise inflation must raise temporal power. Replay the existing scorer commissioning instead of calling duplicated code independent confirmation. |
| Heterogeneous noise/model law | With equal positive energy and different finite floors above1, weights must follow the declared formula and ordering. Equal q=0 has equal baseline weight even with different F. A wrong model must change a powered actual output. Use a factor3 DN rescaling (variance/floor factor9) for F>=1; separately retain F0.25 versus scaled2.25 as an expected failure of global scale invariance from max(F,1). Nonfinite input refusal is distinct from valid zero/clamped variance. These checks do not calibrate the common physical constant. |
| Numerics beyond weight positivity | Exercise p1,2,8 and the actual3.92/2.8 schedule, tiny a that can round to zero response difference, and a deliberately clamped large ratio. Require nondecreasing weights, not impossible strict increments. Inspect actual numerator/denominator and collapsed output separately. A finite helper with an infinite numerator is an instrument/product boundary failure, not a finite-output pass. No arbitrary-N safety inference follows. |
| Colour blindness | Fixed analytic colour versus its achromatic null, plus a separately labelled component stimulus with green-constant red/blue structure if needed to test the assumption directly. Do not change the scored colour target or claim this is physical chromatic defocus. |
| Hull/clamp | Any hull claim needs actual pre-clamp reconstruction against the exact gathered source envelope. A post-clamp pass is guaranteed by the clamp. Delivered truth error must still be read, because an in-hull result can be bad. |
| Storage/source/order | Reuse M194c's established equivalent padding/origin/odd-tail representations in candidate mode, with a powered actual active-site change. One streaming pass remains; count source reads and preserve stable ordinals. There is no second pass to test. Thread scheduling may not alter canonical arithmetic grouping; invalid input/order/map bindings must refuse before plausible TIFFs. |
| Observer | If a new diagnostic is introduced, actual on/off/placebo TIFF equality is required with proof the diagnostic ran. Estimator stats flags are inert on the prepared Pyramid path and cannot supply this proof. |

A null control is not sufficient if the proposed failure cannot occur in it.
Keep every failed commissioning attempt. The lifecycle and caller-boundary
errors in M194c are specific reasons to inspect the actual consuming API rather
than assuming a standalone helper reproduces production semantics.

## Conditions before implementation can be reviewed

Curie's inspected preregistration names the actual decision domain, formula,
heuristic constant, fixed gate/exponent, base/hull, invalid-input contract and
streaming state. It distinguishes this operator from Phase1 and requires
SoftPower with significance_scale0. No unresolved calibration claim prevents
this narrow test. No parameter is selected from width survivors or benchmark
outcomes. Root must preserve these choices in the compiled implementation.

The smallest useful implementation keeps gather, output, base-band, colour,
photometry, injected noise and M194c probe sequence unchanged. It uses the actual
`PyramidFrameSource`/`PreparedPyramid` consumer and the normal TIFF writer. No
new image arrays, reference state or second pass are necessary. Count actual
frame reads and inspect retained storage; never retain an N-frame aligned/RGB
cube. Existing M12 certification is not inherited by source inspection or a
cheap synthetic timing.

The explicit core enum is `AdmissionMode::{HardFloor, FloorPedestalV1}` and
`MergeConfig.admission` defaults to HardFloor. The test-local option
`STREHL_M194D_ADMISSION` is required with exactly `hard-floor` or
`floor-pedestal-v1`; no shipping CLI flag or compile feature is added. Preserve
M194b's original entry/receipt contract, and bind the new enum and formula to
the versioned M194d plan, receipt, child command and actual source configuration.
Missing, unknown or mismatched modes must refuse. All external Rust test files
are compiler inputs and must be in the source/build closure. Socrates owns the
independent controller and pixel-comparison checks; this audit owns component
power and actual consumer semantics.

There is no remaining design blocker to this bounded experiment under the
numeric/refusal and mode restrictions above. Root must freeze this one
implementation plan before product edits or build. Independent controls then
review the new consumer and binding; Socrates owns the complementary
actual-output comparison. If the
experiment loses detail, colour, temporal noise or sparse truth fidelity, keep
the result and identify the failed claim. Do not rescue it by selecting seeds,
changing the probe, shifting the ROI, or quietly promoting a different target.
