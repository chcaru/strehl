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

**Next executable systems action:** commission timestamped sampling-gap and
per-query latency diagnostics on controlled allocation/null/stall plants,
including a short child allocation that must be detected. Observe scheduling
and frequency alongside a separate timing rehearsal. The present aggregates
cannot locate the gap or attribute the timing transition. Determine whether
instrumentation or the execution arrangement needs a prospective change before
funding another full run. Compare observer overhead and output hashes with
diagnostics on/off, including the placebo. The
[measurement diagnosis](../../experiments/review-m192-measurement/findings.md)
defines the phase-delay, child-lifetime, and timing controls. Any change must be
frozen and independently verified;
do not replace individual repeats, discard the first pair, relax 100 ms/2%, or
reinterpret this certificate after the result. No new full campaign is launched.
Carry the independent review's command, worker-environment, campaign-ID, and
manifest-binding checks into the automated verifier before the next campaign.
The review checked those bindings in this package; the generic validator's
missing checks are hardening work, not an observed inconsistency here.

This certificate covers the pinned native-RAW merge with prerecorded alignment
sidecars. It does not test the live alignment solver, the comparative common-TIFF
M11 output, or image quality. Preserve the scorecard's historical failing lineage;
this repaired lineage adds one passed bar and three unmeasured bars, not a SOTA
claim. Geometry consumer repair in step 2 remains the next product-facing work.

### 2. Make geometry executable before declaring it closed

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

The decision is whether this can be a restricted diagnostic, whether an
externally anchored transfer estimate can be commissioned for actual outputs,
or whether the truth-reference route is required. Do not treat a theoretical
or tested limitation as proof that every useful scope is impossible; equally,
do not advertise tested isotropic safety as a general common-LSI guarantee.

Physical-reference work remains governed by M135/M164/M166 and the current
owner sheet. No new photograph is requested by this takeover. First finish
software commissioning on development inputs. A new reference must validate
its information advantage; a sharper-looking edge alone is not truth.

**Exit and next implementation experiment:** M189b closes the directional-safety
question for v2; do not fund another general guarantee from this radial score.
Keep it as a scoped research diagnostic. The next development benchmark must
run the actual production merge on a known latent scene with independently
rendered defocus, curved per-frame geometry, occlusion boundaries, and injected
sensor noise, reporting reconstruction error and flat-region temporal noise.
Reuse the project's existing scene renderers after a prior-art audit; do not
call a duplicate plant independent evidence. Freeze the scene/noise controls
before testing a single admission change. A real-output adapter must separately
observe its noise/transfer law (M189 §4.2–4.4); applying a RAW scalar PTC gain
to an adaptive demosaiced output is not that observation. The development
benchmark can reject and improve code while the physical reference route is
being commissioned; it cannot itself license a real-capture SOTA claim.

### 4. Ship one measured quality change at a time

After the evaluation path and geometry have an explicit supported scope,
return to the admission merge's actual consumer: reconstructed pixels. Compare
one candidate with one pinned production baseline on existing development
stacks. Pair detail fidelity with flat-region noise, known blur/sharpening
controls, occlusion-boundary error, and clipping. Keep an untreated control
and an independent verifier. Avoid bundling admission, base-band, photometric,
depth, and output changes into one result.

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
work remains geometry consumer validation and the bounded constructor in step 2;
systems measurement commissioning follows the bounded action in step 1.
