# Quality path after the September 14 RAW experiments

This is the current quality implementation queue, replacing the immediate
quality actions in 2026-09-sota-program.md and the older SOTA proposal. Read
the measured decision record in docs/research/SYNTHESIS.md before architectural
changes; this plan does not promote any experimental default.

Current September19 execution checkpoint: complete Helicon B/C comparisons
are committed at e250ddc2. B reduces the known vitamin-C glint fans, while
Strehl green-match has cleaner smooth fields. This evidence changes the next
priority to the fixed donor-consistency counterfactual. Its complete70-frame
RAW triplet passes mechanical controls and reproduces baseline pixels exactly.
Independent photographic review finds a partial facet gain but a persistent
dark-inclusion tail: close that exact recipe as an incomplete repair. The
automatic assignment design stays conditional while an immutable coefficient
observer isolates the remaining reconstruction loss. This is an oracle
diagnostic, not a product feature. See experiments/donor-consistency. The
passing complete-periodic all-CFA controls are retained at48276660; their
boundary/noise-probe continuation is deferred behind this visible defect.

The owner's priority is photographic quality on the A7C II macro captures.
The existing program has not established SOTA quality. Further speed-only work
is deferred; retain the already measured experimental GPU improvements.

The new capture regime is electronic shutter, IBIS off, a delayed tripod start,
manual white balance and polarized KL 1500 LCD lighting. The optical path is
the Sony 100mm Macro GM, Viltrox 2x teleconverter and X4 CPL. Use these captures
as the current development population, recording which originals each test
actually consumes. Camera metadata, sensor noise, clipping and colour headroom
remain part of the RAW model. Do not infer unmeasured optics from the gear name.

## What changes the direction

Committed evidence at `a0febf209ce9f38649e40fc39a6f7cf3abf4a243`, particularly
experiments/quality-september14/results.md, supports a narrower route than more
single-frame interpolation variants. Several alternatives clean up the chip's
rail appearance while destroying genuine coloured detail in independent tests.
A direct multi-frame CFA inverse preserves those test signals but adds colour
noise and periodic artifacts to the actual photograph. Even four prescribed
updates from a cleaner mean do not give a clear photographic benefit. Close
these tested variants for this crop; do not use more parameter sweeps to rescue them.

The useful intervention is local placement. With the same eight observations,
a translation fitted on one part of a green-only patch and checked on another
improves rail continuity and ladder separation in the mean. Blur-only and
wrong-sign controls can reject the fit. This does not yet show an improvement
in the complete product, new resolved detail, or validity on an entire frame.

## Immediate implementation question

Carry the correction through the actual gather, injected variance, band merge
and developer before building a general refinement system. The first adapter
reuses saved original CFA data and an explicitly cropped domain. Its available
context supports four Laplacian levels, so it cannot reproduce the seven-band
whole-image result. Require complete source support and exact invariance to
unsupported-buffer filler. Both image arms keep current lens colour correction,
the same frame membership and the same reference. See
experiments/quality-september14/local-placement-consumer-decision.md for the
pre-execution scope and stopping conditions.

That diagnostic is now positive: both reviewers see clearer ladder separation
and crossings through the actual consumer, with no obvious lost structure in
the selected native view. Complete source-support checks and black/white
unsupported-buffer invariance pass. The four-level/eight-frame limitation
remains. This justifies the next full-context placement test; it does not
justify a default change. Exact commands, costs and output hashes are in
experiments/quality-september14/results.md, final section.

If that diagnostic is useful, the next acceptance result must use full context
and the real merge on at least one other scene. A local fit may guide a spatial
correction only where supported; it must not overwrite a whole-image sidecar.
The runtime correction needs an unchanged-map fallback in ambiguous or
defocused regions. It must demonstrate that it does not convert blur or an
occlusion into motion. These are implementation requirements to test, not
claims that a suitable general algorithm has already shipped.

## September 19 full-context decision

The local chip gain now survives the complete 299-frame, seven-band RAW render.
Both reviewers see modestly cleaner existing rail cores and crossings, with no
obvious seam in the frozen transition views. Strong colour stipple remains.
The default-off consumer validates stack/map identity, reconstructs a small
supported original-CFA patch, and applies a tapered source displacement before
existing colour geometry. Actual inputs and the noise probe share the hook.
Independent affine, textured-noise, constant, CFA-phase and refusal controls
pass. The disabled baseline reproduces the earlier baseline's pixels exactly.

The new star-sand stack supplies the counterexample needed to limit this
direction: all eight local fits improve held-out guide prediction, yet neither
reviewer can identify a clearer feature in the complete 259-frame result.
Do not treat that residual improvement as an image-quality gain, and do not
expand the proposed multi-region correction before locating the remaining
loss. The matched source/gathered/merged comparison now shows that the selected
frames 125/129/133 are softer than the merged porous-grain patch. The first
transfer therefore tested a weak detail-bearing window. Locate and visually
confirm the focused originals before repeating the same fixed correction;
the global alignment reference is not a guarantee of local focus. If a focused
source retains a feature that the merge loses, target that actual consumer
behavior. Do not infer a capture limit from three defocused originals.

That follow-up is complete: a bounded full-stack locator and native review
identify a detail-bearing neighbourhood at frames 116–124, with local anchor
120 and unchanged global reference 129. The same fixed correction improves
held-out guide prediction but still yields no identifiable feature improvement
in the complete render. Close this specific star-region intervention and
defer the four-region extension. Preserve the targeted chip gain; automatic
general refinement has not earned promotion. Further work must address an
identified photographic deficit, including persistent colour artifacts and a
matched comparison with strong external outputs, rather than another sweep of
the same translation fit.

Evidence and commands: experiments/full-context-placement/results.md and
experiments/quality-september19/results.md. The new crystallized-vitamin-C
stack is inventoried but has not been RAW-rendered in this work.

September 19 continuation: the complete 70-frame vitamin-C RAW baseline is now
rendered, with its full image retained alongside chip/star outputs. The next
fixed intervention preserves reconstructed RGB through the current quad-scale
pyramid by carrying twelve colour/site planes instead of four CFA planes.
The original four planes and green decisions must remain exact. It omits the
final MHC operation; it changes neither the source demosaicer nor the geometry.
BUILD-DEMOSAIC already measured a mixed single-frame tradeoff, so this is a
testable candidate, not a presumed colour fix. Independent known-scene and
flat-noise controls must admit it before a photographic replay. See
experiments/phase-packed-rgb/charter.md and independent-plan.md. A complete
vitamin-C comparison with the available MIT fork is now complete;
historical commercial outputs do not cover these new captures. Independent
native review finds fewer long chromatic highlight spokes in the fork, paid
for by broader granular highlights and grainier low-detail fields. Neither
arm clearly recovers an additional facet. This establishes an actionable
tradeoff rather than a blanket competitor win. The twelve-plane candidate
passes its fixed generated-scene screen: fractional true-colour truth improves,
known-site values remain exact, and the measured flat chroma penalty is modest.
One complete paired photographic replay is justified; no default promotion or
SOTA conclusion follows from that generated screen.

The complete photographic replay is now negative: both reviewers see the same
highlight fans, no newly resolved facet or inclusion, and slight local
comb-like colour structure in one candidate cluster. All 70 frames and all
seven bands were exercised with exact known-site values and admission. Keep
this twelve-plane implementation experimental; no default promotion, speed
optimization or setting sweep is earned. The next bounded diagnosis uses the
already-developed original frames to locate where those exact highlight
structures enter, before choosing another change. Evidence and complete
paired images: experiments/phase-packed-rgb/results.md and full-1.

September19 source diagnosis and fixed support experiment: long coloured fans
already occur in defocused source frames. The actual native finest-band
observer reproduces the whole baseline hash and shows a95.67% weight share
for the final frame at one fan point. A fixed65x65-quad energy/floor pool
changes both measured fan nominations toward compact-source frames, but also
borrows focus from a visibly softer neighbouring structure. Its finest-only
implementation is now **rejected** by independent generated controls: at
ISO100 fan error rises12.56% and true glint-core recovery loses58–59%.
Coarse/base accumulators remain exact; this is a selection failure, not an
unintended wider code change. No full candidate RAW replay or default promotion
is justified. See experiments/fine-support-guidance/results.md and the
independent control report. The next bounded question is whether source point
spread measurements can separate the highlight from neighbouring surfaces;
generic spatial pooling and unvalidated guided smoothing are not the next step.

## What counts as progress

September19 continuation: source-profile inspection distinguishes coherent
focus-dependent spread at the facet from mixed extended structure at the dark
feature. It does not identify a transferable point-spread function; no optical
kernel is fitted from those profiles. Evidence is in
experiments/highlight-spread/results.md (commit93c08ce7). The actual comparison
stacker also reconstructs complete source-colour tuples against a fused grey
target. A separate RAW-native variant now has a positive generated screen:
match source green to the current collapsed green within one fixed injected
variance threshold, retain complete colour tuples, average matches and preserve
the baseline where none match. It is a heuristic with explicit equal-green
colour ambiguity and no clipping repair. Genuine-colour truth errors improve
at both tested ISOs while component/flat controls pass. This admits exactly
one complete vitamin-C paired RAW replay, not promotion. See
experiments/green-match-rgb/results.md and full-plan.md.

That complete replay is now finished. Both reviewers see reduced fine grain
in low-detail backgrounds, but the targeted coloured fans persist and some
fine crystal texture looks smoother. Preserve the complete paired images and
keep this mode experimental. Do not promote it, optimize it, or sweep its
threshold on this evidence. Native RGB preservation and subsequent source
colour projection have both failed to repair the target by themselves; the
next bounded prior-work audit concerns the directional complex-wavelet source
selection used by the comparison stacker. Existing source evidence does not
justify the separately considered parent-band weight multiplier as a full
render. Evidence: experiments/green-match-rgb/results.md and its independent
photographic review.

The first native complex-wavelet screen is now complete and rejected
(fbe8bbcb). Its transform and identity variance checks pass, but green-only
directional evidence loses real red/blue detail under spatially varying focus.
Flat-field gains do not compensate for that loss. The exact failed rule is
closed. The next fixed test uses energy from all four original CFA planes,
shared colour weights, two decomposition levels and exact composed sensor-noise
propagation. It retains independent truth/detail controls and adds a weak-colour
test under the warm capture WB. No RAW replay or promotion is yet admitted;
see experiments/all-cfa-wavelet/charter.md.

That two-level screen has now completed and remains rejected: fine/colour/noise
guards pass, but genuine coarse structure is attenuated to about0.528 of truth.
Independent filter analysis predicts0.528616 from structure left in the mean
base. The separately scoped next operator decomposes geometrically to terminal
DC, first on a fixed periodic generated domain with no image padding. Natural
boundaries and fractional noise remain subsequent questions, not assumptions.
See all-cfa-wavelet/results-review.md and complete-cfa-wavelet/charter.md.

The complete periodic candidate now passes all32 fixed scene/ISO/phase cases,
including coarse recovery near truth and the weak-red focused-source guard.
This admits a boundary/composed-gather check, not a photographic claim. The
comparison changes transform, actual depth, exponent ramp and boundaries;
seven requested baseline bands reach four on the fixed128-square domain.
See complete-cfa-wavelet/results.md and its independent results review.
In parallel, Helicon8.3.11 trial B/C have produced complete70-frame vitamin-C
outputs from the retained RGB16 inputs. RAW loading requires an absent Adobe
DNG converter; these are prepared-TIFF whole-workflow comparisons with
unmatched development/alignment, not native-RAW or speed benchmarks.

Show the owner the complete stack output whenever presenting an improvement,
including the complete before image for comparisons and a link to the RGB16
master. Native crops remain diagnostic evidence, never the sole presentation.
This is the owner's explicit September 19 instruction.

The complete fixed-donor vitamin-C trials are now closed as insufficient.
Coefficient masking improves one facet locally but retains the dark coloured
tail; actual signed reconstruction accounting identifies retained coarse AC.
Moving the same masks after full AC reconstruction still leaves that tail,
despite removing baseline AC inside full-weight support. The accounting was
correct but did not establish a sufficient repair. Baseline pixels remain
exact and all four independent mechanical controls pass. The next cheap
consumer witness must show actual gathered donor content/placement, retained
base, taper and hull separately before any new reconstruction change. An
automatic concentration diagnostic is being controlled in parallel, without
presuming it repairs images. See donor-consistency/spatial-results.md and
the independent photographic decision; no SOTA/default promotion is earned.

The actual-source witness now identifies a target annotation error: the
visible long dark-field streak was sampled at a location with mask0.010998,
while the originally named fan point was fully covered. Actual donor33 is
compact at the missed streak. The separately labelled corrected-address
oracle changes only that endpoint; all six controls pass and the complete
render changes4271 pixels within the declared dark-field rectangle, with
every other pixel exactly unchanged relative to the preceding spatial trial.
Its full photographs and independent verdict live in donor-consistency/
corrected-results.md. This remains a manual diagnostic, not automatic repair.

The proposed automatic concentration rule is closed: a real extended radial
truth control defeats its radius ordering, and an unchanged read-only scan
of124 real tracks makes zero nominations. Preserve both results rather than
tuning thresholds. Unconstrained positive blur fitting likewise cannot prove
ownership, because a compact core can encode an unrelated positive object in
its fitted kernel. Further ownership work is deferred. The next automatic
whole-image candidate resumes the positive complete all-CFA wavelet operator
with the fixed natural-boundary and actual-GPU-gather noise test in
complete-cfa-wavelet/next-design.md, implemented under boundary-cfa-wavelet.
No photographic admission follows until that small independent screen passes.

An image-quality change must retain or restore an identifiable feature in
matched native views, preserve genuine colour, and survive independent review.
Use known-scene truth and flat-noise controls alongside photographs. A lower
registration residual, stronger gradient or better synthetic score alone does
not justify promotion. A local crop improvement cannot establish a full-stack
or competitive SOTA result.

The boundary/actual-rounded-gather screen is now committed at4eced9b4. Its
structural, propagated-noise and observer controls pass, but the frozen
photographic admission remains false: fractional weak-red retention is about
88.73% of the focused source against90%, and the separate5% RGB-error benefit
is absent. The same candidate recovers about2.58 times the baseline's weak-red
component and passes every baseline-relative RGB/edge/corner guard. Do not
confuse failed admission with demonstrated general harm.

Root has separately scoped one observational full-image pair, contingent on
new full-domain/CA mechanical checks and a measured one-source cost checkpoint.
This does not change the failed screen or promote the method. Retain fixed
geometry, colour, tone, eight source-noise pairs, canonical baseline pixels,
one worker and resource caps. See boundary-cfa-wavelet/observational-plan.md.
An independent priority review retains a shared categorical source-field
approach as the next distinct hypothesis for the real streaks; do not mix it
into the wavelet trial or open another parameter sweep.

That one-source checkpoint has now refused the full wavelet route. Mechanical
and unchanged generated checks pass, but source35 takes31.708s and candidate
reconstruction refuses nonfinite input. The incomplete70-source extrapolation
already exceeds the frozen resource bar; no candidate photograph exists.
Weighted-numerator overflow is a strongly supported source-level explanation,
not a measured offending coefficient. Preserve the failure in
boundary-cfa-wavelet/cost-results.md and its independent review. Do not spend a
full render on this exact CPU/eight-pair implementation. The next authorized
quality experiment is shared-source-field: one fixed categorical spatial
regularizer and soft full-AC replay, with independent flat/detail/depth controls
before any complete photograph.

Keep subagent work bounded: one implementation, one independent choice review,
and photographic review when there is a new image. Reuse retained samples and
fixed settings. Each negative result closes its proposed intervention; it is
not a reason for another open-ended sweep. Once a product-level photographic
gain is established, measure its full-workflow cost and compare complete
outputs with the retained external baselines. Quality decides which changes
deserve optimization.

The fixed shared-source-field screen has now completed and rejected the
candidate before any full RAW replay. At ISO100, fan truth error is1.1085x
baseline and core error1.8607x, despite retained template amplitude; the thin
near feature also fails its error guard. Flat/noise and mechanical controls
pass. ISO400 additionally lacks the required fan/noise separation. Preserve
the distinction between increased error and erasure, and between successful
test execution and quality admission. See shared-source-field/results.md and
its independent review. No penalty sweep or complete render of this rule is
authorized by its result.

The separately scoped parallel complete-CFA wavelet repair is also now
photographically closed. Exact transform controls and a scaled accumulator
remove the execution blockers without changing the old quality decisions.
The complete70-source vitamin-C pair finishes in1253.844s with exact baseline
pixels, but independent full/native review finds broader coloured highlight
smears and worse dark-core contamination. No compensating real-detail gain
earns promotion. Both complete images and masters were shown to the owner.
See parallel-cfa-wavelet/results.md and photographic-review.md. Preserve the
reusable numerical work; do not spend another render or optimization campaign
on this fixed image operator. The next intervention must address source
evidence and the observed through-focus relationship, not merely substitute
another transform or larger spatial prior.

The bounded relative-blur check has now passed its generated algebra/adequacy
controls and completed six fixed actual-source transfer fits. It has not
provided automatic ownership or photographic admission. Facet prediction
improves a held residual, but dark-core fitting reaches its finite blur bound
and nearby real-structure continuation worsens in three planes. Numerical
refusal is unknown, not evidence for the reverse direction; the finite kernel
also cannot rule out broader physical spread. Preserve the exact source
witnesses and separate target-holdout scope in relative-blur-evidence/results.md.
Do not spend a full render on these compatibility scores alone.

The next bounded consumer test is core-lineage: transport existing focus
weights from persistent source cores only across unambiguous observed branches,
with exact baseline fallback at crossings, contested support and clipping.
Original-code checks around the vitamin-C highlights reach16383 in four
independently decoded inputs; the broad boxes do not identify exact branch
stencils, but clipping refusal must remain explicit. Independent actual-consumer
truth controls must demonstrate useful coverage and preserve radial/coloured
and different-depth detail before any photographic replay is considered.

That core-lineage screen is now closed without a full render: it activates no
quads on any through-focus truth scene, including the required glint case.
Its safe fallback and refusal controls do not constitute useful repair. Source
reversal additionally changes existing probe floors, so it cannot isolate
lineage ordering. Preserve core-lineage/results.md and independent review;
do not tune this rule. The next bounded colour investigation changes the
information used for R/B election in the existing Laplacian merge, with their
own propagated RAW noise and both greens held fixed. Historical axial offsets
do not justify a fixed source shift or explain current fans. Actual colour,
neutral-edge, flat-noise and competing-depth controls decide admission.

The R/B own-guide screen now demonstrates live colour-information headroom but
fails full-render admission. RGB truth errors on colour-offset/colour-only
plants fall to0.190/0.437 of canonical at ISO100 and also beat the matched-noise
green control. Flat RGB error rises to1.465 of canonical, while final MHC changes
green despite exact collapsed green CFA samples; its green guard fails. ISO400
repeats both effects. Preserve rb-own-guide/results.md and independent review.
No full render or default change is earned. The next design must control noisy
R/B updates and make the delivered-green preservation contract explicit, without
claiming that these generated focus offsets explain the photographic fans.
