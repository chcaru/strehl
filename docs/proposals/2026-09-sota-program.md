# SOTA program — current execution plan

**Owner:** the execution orchestrator, under Chris's 2026-09-06 instruction to
take over and drive the research and implementation program.

**Baseline inspected:** `cba20dae`. This document is the current scheduling
entry point. The August proposal and its amendments remain the design history;
the scorecard remains the claim contract. This plan does not lower a bar,
promote a diagnostic to a score, or release a sealed capture.

## Decision

**ARGUED:** retain the CFA-native stacker and rebase the work queue on completed
evidence. A replacement architecture is not justified by the record. The first
deliverables are a complete systems certificate, usable input/output geometry,
and an evaluation path that can distinguish preserved detail from processing
artifacts. New physics features follow an identified consumer and a test that
can reject them.

There are two distinct acceptance questions. A development experiment can
establish a narrower property and justify the next implementation experiment.
A SOTA claim needs the registered population, comparators, instruments, and
complete production output. Keeping the latter blocked must not turn the
former into an indefinite ban on useful engineering.

## Reconstructed state

**VERIFIED by repository/artifact inspection**, with no new scored capture:

| Item | State at takeover | Consequence |
|---|---|---|
| Scorecard | Zero passed axes; M8 and M12 retain admitted historical failures | No SOTA claim; historical speed comparisons are not a new score |
| D9 / memory | Fixed reduction order `fc2abb49` and bounded recycling `a9727581` are in the measured lineage | Certify these repairs together before further scheduler changes |
| M192 certificate | Explicit abort at `2026-09-05T08:38:16Z`; 35 of 133 registered invocations, no complete certificate | Harden terminal reporting and durable failure diagnostics, then start fresh; the historical failing statement remains unknown |
| M193 geometry | Algorithms precommitted at `dfaa2f63`; proposed blocker-removal edits are unfinished | Do not apply the supplied closure edits; independent review found a denominator-validation defect and unproved deep-stack reach |
| M189 detail | `cba20dae` admits a limited synthetic candidate, not M1 | Test the limits explicitly before assigning capture or comparator work |
| Phase 1 admission merge | The original `NO_COMMON_K` refutation was withdrawn in August-plan Amendment 3 | Status is unvalidated, not refuted and not rescued; the old phase-1 banner is superseded |
| D8 / own decoder / IOCP prefetch subsystem | Specific no-build branches remain supported by their phase-0 reports | Do not revive them as generic improvements; the bounded read/decode channel is a separate surviving mechanism |

Sources: [scorecard](2026-09-sota-scorecard.md),
[M172 closure](../research/M172-m12s-closure.md),
[M192 recovery](../research/M192-campaign-recovery.md),
[M193 review](../research/M193-geometry-review.md),
[M189 candidate](../research/M189-noise-colour-detail.md),
and [August plan Amendments 3 and 7–8](2026-08-sota-path.md).

## Execution order

The frozen systems run is complete. Its remaining measurement work proceeds
alongside geometry/detail development. It does not reserve the host or prohibit
useful work; the registered admission rules decide which observations qualify.

### 1. Finish the systems repair already built

**COMPLETED, overall UNMEASURED:** the fresh campaign finished all 133 invocations
at `2026-09-07T07:30:53Z`. The independent terminal review is
[M192 terminal verification](../research/M192-terminal-verification.md).
The old interrupted directory and the complete new evidence are preserved.

| Registered bar | Result on the frozen repaired lineage | Qualification |
|---|---|---|
| Complete TIFF and canonical pixel byte identity | **PASS** | All 15 fixed-worker six-repeat cells and all five workers at each of N=33/105/299 agree |
| Warm peak process-tree memory, <=6 GiB | **UNMEASURED_SAMPLING_COVERAGE** | Recorded Job peak 2.866577 GiB; two scored runs exceed the 100 ms maximum sampling-gap rule |
| Peak N299 / peak N33, <=1.10 | **UNMEASURED_SAMPLING_COVERAGE** | Recorded conservative ratio 1.000796; the same sampling admission failure applies |
| N-mod-4 per-frame spread, <=2% | **UNMEASURED_HOST_CONTENTION** | Raw-minimum spread 0.355694%; reversal-pair envelope 0.499110%–5.687910%, so the pass rule is not met |

These are **MEASURED readings with the registered dispositions**, not four
passes. Minimum sampling coverage is 0.990392, but maximum gap is 1163.700 ms;
coverage alone cannot admit the memory readings. The timing disposition names
the protocol's inconclusive category, not a proven physical cause. A transition
within the first mirrored sweep pair is visible in both wall and product CPU
time; its cause remains unresolved.

**Completed follow-through:** [M192b](../research/M192b-verifier.md) implements
the missing execution/evidence bindings; [M192c](../research/M192c-sampler.md)
commissions timestamped phase diagnostics on allocation/null/stall controls;
[M192d](../research/M192d-production-rehearsal.md) verifies observer off/on/placebo
non-perturbation on actual native outputs. Do not dispatch those completed
questions again. None identifies the historical stall or timing-transition cause.

**Next executable systems action:** integrate the commissioned observer and
stricter verifier into a durable prospective campaign runner, with bounded
long-run trace retention, explicit overflow/terminal recovery and the complete
invocation bindings. Freeze the resulting protocol and commission a small
end-to-end run before considering another full campaign. Retain the bounded
timing rehearsal aimed at the unresolved execution-state transition; a small
runner test alone need not exercise it. The existing
[measurement diagnosis](../../experiments/review-m192-measurement/findings.md)
and completed reports define the remaining limits. Do not replace individual
repeats, discard the first pair, relax 100 ms/2%, or reinterpret the old certificate.
No new full campaign has been launched.

This certificate covers the pinned native-RAW merge with prerecorded alignment
sidecars. It does not test the live alignment solver, the comparative common-TIFF
M11 output, or image quality. Preserve the scorecard's historical failing lineage;
this repaired lineage adds one passed bar and three unmeasured bars, not a SOTA
claim. The actual-output geometry adapter in step 2 remains open.

### 2. Make geometry executable before declaring it closed

**COMPLETED within supported-fixture scope:**
[M193b](../research/M193b-geometry-consumer.md) supplies the strict consumer
and bounded path constructor. Independent verification rejected 46 malformed
or untrusted cases, including coherently rehashed denominator substitutions.
The original identity/crop results are unchanged. Actual decoded-array lifetime
fell from twelve to one on the controlled twelve-file fixture. This establishes
the retention property, not native-size memory usage or registration coverage.
The next geometry implementation is a commissioned actual-output adapter and
complementary-focus registration development; neither is closed by this repair.

The completed repair addressed these takeover findings:

M193's review is an acceptance failure for the proposed apparatus. A modified
overlap rectangle can retain the old manifest hash and turn a failing crop
into a passing one. The fix needs consumer-side schema, hash, rectangle, and
binding validation, including tests that recompute a malicious manifest's hash
and therefore defeat superficial checksum-only repairs.

Then replace the all-RGB-in-memory constructor with bounded input processing.
The proposed constructor retains both all input TIFF bytes and all decoded
RGB arrays. At 299 native 7032×4688 RGB16 frames that is a **DERIVED 110.16 GiB
payload lower bound**, before overhead. It cannot be the deep-stack apparatus
for this host. This restriction is independent of the product's CFA working
set.

Finally, commission registration on complementary-focus frames as well as
same-focus transformed textures. The present direct-to-one-reference fit can
refuse even when the planted geometry is exactly identity. Refusal is correct;
it establishes neither false placement nor adequate population coverage.
Use direct multiscale constraints and per-frame held-out placement checks if a
replacement graph is needed; do not chain. Freeze and validate actual program
grid adapters. Only then reconsider blocker `(b)` in the scorecard.

No candidate output may choose the shared denominator. Same-denominator field
of view and correct mapped sites are the consumers being tested; an accurate
endpoint scale alone is insufficient.

### 3. Establish a scoped detail benchmark

M189's v2 result is meaningful on the controls it actually ran: optical
improvement, optical degradation, isotropic post-blur, and isotropic USM. Its
radial-bin noise envelope is not automatically an envelope over every
frequency and orientation. M189b independently changes the scene and filter
to exercise that choice while leaving the frozen candidate untouched.

**MEASURED scope check (M189b):** a common horizontal three-tap sharpening
filter raises the frozen candidate's score to `1.49879x` the untreated arm,
with SEM `0.01165` across eight independent batches. No adaptive denoising or
fresh re-noising is involved. This confirms the anisotropy exclusion already
present in M189 Amendment 1; it does not retract the isotropic experiment.
See [M189b](../research/M189b-directional-detail.md) for the exact command,
independent population calculation, flat-first controls, and limits.

**Decision taken:** retain v2 as a restricted diagnostic and use known scene
truth for the production development comparison. M194 commissions the actual
CFA-to-TIFF seam; M194b establishes its first scoped baseline; M194c corrects
probe storage dependence; M194d measures one positive-weight candidate. Do not
advertise tested isotropic safety as a general common-LSI guarantee.

Physical-reference work remains governed by M135/M164/M166 and the current
owner sheet. No new photograph is requested by this takeover. First finish
software commissioning on development inputs. A new reference must validate
its information advantage; a sharper-looking edge alone is not truth.

**M194e complete within its fixed geometric scope:** the fourth fifteen-image
run passed independent whole-image/edge/refinement limits, then all15360 actual
CFA samples passed separate exact conversion/provenance verification. The three
earlier full-run refusals and four prospective numerical amendments remain in
[M194e's record](../research/M194e-joint-pupil.md). Worst scalar discrepancy is
0.00012419946 electrons against the unchanged0.004 limit; this commissions the
fixed numerical model, not measured physical optics or merge quality.

**M194f complete:** all eleven fresh TIFFs pass the independent actual-file
reader after consuming admitted CFA through the prepared production Pyramid
and writer. Crop/colour values, observer/confidence byte identity, rank encoding
and the amended observed-channel WB control pass. The unsupported exposure arm
and instrument failures remain in the [M194f report](../research/M194f-production-bridge.md).
The small fixture has one Laplacian band plus a base. **Current next: M194g**
commissions the larger numerical boundary fixture, starting with geometry-only
cost and coverage checks. Its amended full count independently passes all15
rows and1152000 cells within the prospectively chosen180CPU/240wall allowance.
The original60-second refusal and stopped profiling instrument are retained.
The first author component/observer batch completed its331 calls and60 normal
observer frames. The separate reference attempted all300 rows but refused28
near-tangent evaluations on quadrature warnings. All145 independent private
payload/resource/entry controls now pass. The96-call diagnostic preserves the
original numerical signatures in off/count/placebo and locates all28 warnings
on endpoint intervals5–16 binary64 steps wide. The separately released
normalized-interval reference now returns all300 values and passes66 producer
checks; the complete author rerun passes511. The refreshed193 controls passed,
then the complete reader exposed a Markdown-versus-JSON entry bug. The narrow
repair and197 powered controls now pass, followed by the complete independent
component/observer comparison under unchanged accuracy bars. All25 complete
expected arrays and their independent full-image/refinement comparisons now
pass, after79 private controls. The largest external absolute discrepancy is
1.0743797247414477e-5 expected electrons against the unchanged .004 bar.
The fixed numerical population and specified software-noise law are admitted.
All90 saved sensor files now pass their independent reader and37 controls;
69 quality/TIFF instruments and the separate ten-cell ideal-target check pass.
The larger three-band bridge compiles after a retained two-return repair.
Current work runs its private/intended production commissioning before the
registered38-output quality comparison. See the
[M194g record](../research/M194g-larger-pupil.md). Its [prospective protocol](../../experiments/m194g-larger-pupil/preregister.md)
keeps later noise-law admission and the fixed M194d comparison on actual
three-band production output separate from expected-image generation.
The one-plane M194b/M194d evidence cannot express depth-boundary dilution.
The new mathematical model will not clear M25's failed physical/optics gates.
Any later production bridge, noise population and quality comparison need an
explicit versioned contract and independently checked scope. A real-output
adapter must separately observe its noise/transfer law (M189 §4.2–4.4);
applying a RAW scalar PTC gain to adaptive demosaiced output is insufficient.
The development benchmark can improve code while physical-reference work is
pending; it cannot license a real-capture SOTA claim.

The [current comparator refresh](../../experiments/review-current-comparators/findings.md)
retains learned stack-fusion methods as candidates for later development
comparisons. It supplies no substitute for actual-output commissioning and no
formal comparator substitution.

### 4. Ship one measured quality change at a time

**First scoped comparison complete:** M194d measures reconstructed production
pixels against known scene truth and repeated flat-noise controls. Its candidate
remains experimental, with small detail costs and sparse adverse errors retained.
The next depth-boundary comparison depends on M194e and a separately commissioned
production bridge and noise population. Compare one candidate with one pinned
production baseline. Pair detail fidelity with flat-region noise, known
blur/sharpening controls, occlusion-boundary error and clipping. Keep an untreated
control and an independent verifier. Avoid bundling admission, base-band,
photometric, depth and output changes into one result.

If a candidate passes development controls, freeze its binary and settings
before the registered holdout. If it fails, record which input falsified it
and move to the next mechanism. Do not tune it to imitate the legacy
selector's per-band width: that was the defective old W1 gate.

### 5. Optimize the accepted production path

Measure the accepted path with the corrected scheduler and output settings.
Pursue fold parallelism/SIMD only where a profile identifies work that matters,
using fixed arithmetic grouping and unchanged-output checks. Do not inherit
the August proposal's hardware-floor multiplier as a measured promise.
GPU, super-resolution, chromatic diversity, and capture automation stay
conditional on their own surviving gates and an actual consuming feature.

## Operating record

Every update here must name a completed artifact or the next executable action.
`docs/STATUS.md` remains historical context, not proof that an agent or process
is still running. Check explicit completion/abort records and process identity.
Keep unrelated dirty files intact; commit only this program's named paths.

### Current campaign

**COMPLETE; integrity verified, M12 overall UNMEASURED:** launched
`2026-09-06T23:32:53Z`, PID `22556`, and completed `2026-09-07T07:30:53Z`, under
`experiments/M192-m12-certify/recovery-20260906-163253/`. The complete command,
process start identity, file hashes, and redirected log paths are in
`launch-receipt.json`. Runner repair: `3b05ed2d`; measured product lineage:
`e93f0bde695961d53cbd66587a060a41552b4a63`. The old interrupted `work/` is intact.

The root independently ran `test-recovery.py` (nine tests) and the unchanged
`verify.py --self-test` (nine defects caught plus inert control). It also
reproduced and then verified the actual-descriptor shutdown failure that the
first mocked-stream tests missed. See the recovery report; none is an M12 score.

The hourly task follow-up, `strehl-systems-certificate`, is paused after terminal
verification and recording this outcome. The evidence is in the campaign's
`results/`, with independent checks in `experiments/review-m192-completed/` and
measurement diagnosis in `experiments/review-m192-measurement/`. The next code
work has progressed to the independently verified repairs and next actions
recorded below.

### Autonomous continuation, 2026-09-07

The owner explicitly requested continued work while asleep, moving to the next
task after each result. The hourly `strehl-sota-program` task follow-up is active
for that continuation; the old single-campaign monitor stays paused. Inspect
live work before dispatching duplicates and surface substantive outcomes.

**M192c complete and independently verified on synthetic controls:**
[phase diagnostics](../research/M192c-sampler.md) passed the amended 64-arm
commission, retaining its initial launch-confounded failure. An independent
shorter allocation plant, unlabelled waiting/CPU-active stalls, final-memory
delay, output placebo/mutation and bounded overflow checks also passed. This
permits a bounded production rehearsal, not a retrospective change to M192.

**M192b complete and independently verified:** the
[stricter artifact verifier](../research/M192b-verifier.md) rejects 24 author
mutations and 12 independently chosen contradictions with hashes recomputed.
It accepts valid controls and a correctly recorded product failure. Its
baseline retains one PASS and three UNMEASURED bars.

**M194 complete and independently verified:** the
[production-path audit](../../experiments/review-production-truth/audit.md)
identified reusable scene renderers but no complete synthetic CFA-to-production
Pyramid-to-TIFF path among the inspected executables. The private decoded-CFA
source now feeds one shared production gather, fold, confidence and writer body.
Independent controls re-choose scene dimensions, CFA/crop addresses, source
errors and confidence rereads. The final source passes both synthetic suites
and preserves complete native TIFF bytes with alignment off, pinned alignment,
and full-resolution linear-sRGB development. See the
[M194 report](../research/M194-production-truth.md) for the checked scope and
retained build/lint failures. This commissions a source path, not scene truth.

**M194b complete within its fixed registered layout:** the
[forward-model brief](../../experiments/review-production-truth/forward-model-plan.md)
led to forty actual production TIFFs on flat, single textured plane and analytic
colour fixtures, with fixed curved geometry, crop and synthetic noise. Independent
reference calculations and actual TIFF reads confirm a detail/noise tradeoff:
the stack is quieter and closer to the specified optical observation, but farther
from the ideal plane and less accurate on the analytic colour component. Keep
both targets and the single-frame comparator distinct. See the
[M194b report](../research/M194b-known-scene.md) and its retained controls/failures.

**M194c completed as a storage correction with a measured cost:** identical image
data now give identical probe floors and TIFFs across unused-storage layouts.
The RNG law and merge settings are unchanged. On the fixed benchmark, flat
green temporal variance rises 2.538%, and a sparse adverse movement reaches
104.447 post-WB DN inside the scored window. The review trigger remains fired;
this is an accepted correctness tradeoff, not a quality improvement. See the
[M194c report](../research/M194c-probe-layout.md) for paired uncertainty,
whole-image extremes, independent controls and retained failures.

**M194d complete as a promising experimental tradeoff:** one fixed positive
band-weight baseline reduces flat temporal variance by 54.21%/68.70%/53.53%
in R/G/B on the eight-repeat software fixture. All40 off-mode TIFFs reproduce
M194c exactly. The noise-off plane becomes slightly less accurate against both
targets; its maximum wave-amplitude loss is0.008669 DN. No registered engineering
trigger fires, but individual truth errors still worsen, up to33.451259 DN
inside the fixed ROI. Independent readers verify all120 TIFFs and retain the
sparse costs. See [M194d](../research/M194d-band-admission.md). Keep the new
weighting experimental, with HardFloor still the default. This is not calibrated
statistical admission, Phase-1 clearance or a SOTA result. No seed/gate tuning.

**M194e starts the next quality prerequisite:** commission a small geometric
two-layer renderer that evaluates foreground visibility and background radiance
at the same pupil sample. Separate blurred-layer means can miss that coupling.
The existing one-plane benchmark cannot express depth-boundary dilution, and
M25's failed physical-occlusion/optics gates remain failed. Independently check
analytic limits, wrong-order controls, coordinate/cell integration and numerical
convergence before producing a new comparison population. Diffraction, real
camera calibration and capture-based validation remain outside this step. The
[charter](../../experiments/m194e-joint-pupil/charter.md) fixes that boundary;
no default change, full quality matrix or historical artifact edit follows from
the generator commission alone.

**M192d complete and independently verified:** the
[native observer rehearsal](../research/M192d-production-rehearsal.md) ran all
seven registered N33/worker8 invocations on the frozen M192 executable. Complete
TIFF and pixel hashes match the archived M192 output in every arm, including
diagnostics off/on/placebo. All seven sampling observations pass; maximum
complete interval is 42.4173 ms. The independent reviewer parsed the actual TIFF
strips separately and re-chose metadata/pixel and telemetry mutations. No long
stall occurred, so this neither identifies the historical cause nor admits a
new full M12 result. Durable observer integration and a frozen prospective
protocol remain systems work; no full rerun has been launched.

The [output adapter audit](../../experiments/review-output-adapter/audit.md)
locates a native pre-render plan and writer contract as the next geometry seam.
M130 already applies Crop before Pyramid analysis. M165's one-frame common-TIFF
consumer is not a full rendered common-TIFF stack, and M193b's valid descriptors
do not yet authenticate actual output mapping. Use the new M194 source seam to
commission that mapping, including same-size false translations and nonzero
crop origins, before claiming adapter coverage.
