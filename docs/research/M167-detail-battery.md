# M167 — independent adversarial detail-instrument battery

**Status: BATTERY COMMISSIONED; THREE KNOWN-DEAD INSTRUMENTS REJECTED;
ARM-IDENTITY CANARY REJECTED; NO DEPLOYABLE DETAIL INSTRUMENT ADMITTED.**

## 1. Question and result

M167 does not propose another detail statistic.  It freezes and commissions the
acceptance battery that a future candidate must survive before this program may
use it for a resolution claim.

The original predicates were committed before candidate execution in
`8a305128`, `ca79eac7`, and `5fe75c14`.  After M164's concurrent result, the
stronger binding from the oracle to actual rendered fixtures was frozen in
`a183fd47` before that revised oracle was executed.  The executable
preregistration is
`experiments/M167-detail-battery/PREREGISTRATION.md`.

**VERIFIED.** The battery is commissioned:

- its literal all-GREEN fixture passed;
- it caught `8 / 8` one-property checker sabotages;
- its constructed optical-truth oracle passed all six mandatory arms;
- D8 per-tile FRC was rejected;
- the M137 high/low band-power gap was rejected; and
- M2 `R_box9` was rejected on signed blur, reproducing
  `0.5712148772282098x`.

The machine-readable record is
`experiments/M167-detail-battery/results.json`.  Its top-level status is
`COMMISSIONED` and all `15` hard commissioning checks are true
(`results.json:40-56,591`).

No known-good deployable instrument exists in the repository.  The positive
control is therefore a construction-truth oracle, not a candidate and not
evidence that a single-image resolution statistic is possible.

## 2. What was frozen

All candidate scores are oriented so that higher means more resolved.  A
candidate may emit a point, lower bound, upper bound, or typed refusal.  Bounds
are compared conservatively: overlap and equality do not prove direction.

| ID | arm | pre-registered pass predicate |
|---|---|---|
| **P1** | flat-ROI null | A no-scene flat must explicitly refuse as `NO_DETAIL`/`FEATURELESS`, or its entire score interval must lie below the detailed interval: `flat.upper < detail.lower`. |
| **P2** | planted improvement | A render with optical sigma `0.55 px` must lie wholly above the `1.00 px` base: `improved.lower > base.upper`. |
| **P3** | planted degradation | A render with optical sigma `1.65 px` must lie wholly below the `1.00 px` base: `degraded.upper < base.lower`. |
| **P4** | signed blur monotonicity | Scores at added post-render Gaussian sigma `[0,.5,1,1.5] px` must be strictly decreasing interval-by-interval. Equality, refusal, or any rise fails. |
| **P5** | sharpening-vs-resolution | The real optical improvement must beat base, while USM (radius `1 px`, amount `.75`) must explicitly refuse as `SHARPENING_UNSAFE` or score no higher than base. |
| **P6** | fail closed | A `NaN` image and a one-dimensional image must each produce a typed refusal/error, never a value, bound, non-finite result, or omission. |

There is no compensating aggregate: all six arms must pass.  The full result
contract, fixture construction and predicates are frozen in
`PREREGISTRATION.md:20-133`.

### Fixture construction

`fixtures.py` constructs a deterministic `1024 x 1024` latent field and renders
it to `256 x 256` through registered Gaussian optical PSFs before
area-sampling.  Optical arms reuse identical downstream noise, so the
registered optical intervention is the only change.  USM and the blur ladder
instead operate on completed images.

The flat arm contains no scene modulation.  It does contain a shared broadband
fixed pattern plus independent temporal noise, and the matched detail arm sees
the same pattern/noise.  This is deliberate: an instrument must distinguish
resolved scene information from repeatable sensor structure rather than merely
detecting repeatability.

**VERIFIED independence.** `commission.py` imports neither `fixtures.py`,
`measure.py`, nor any candidate.  It invokes `measure.py` as a child process
and adjudicates only JSON.  `measure.py` imports no checker or predicate.  All
numerical thread variables are forced to one by the parent process.

## 3. Battery commissioning

### 3.1 Checker power

**VERIFIED.** The literal accepted record passed P1-P6.  Eight targeted
sabotages were all caught: flat equality, improvement blindness, degradation
blindness, a tied blur rung, rewarded USM, numeric malformed input, generic
flat refusal, and a missing arm (`results.json:2-37`).

This does not by itself make the battery sound; the known-dead controls below
are the decisive commissioning requirement.

### 3.2 Constructed oracle

**VERIFIED PASS, P1-P6.** The oracle reads private construction labels:

- base `1.0`;
- genuine improvement `1 / .55 = 1.8181818181818181`;
- degradation `1 / 1.65 = 0.6060606060606061`;
- blur ladder
  `1.0, 0.8944271909999159, 0.7071067811865475,
  0.5547001962252291`;
- USM `1.0`, tied with base; and
- typed refusal/error for the two malformed cases.

The revised oracle actually instantiates the hash-pinned `256 x 256` fixture
generator before emitting those truth scores.  The independent checker
requires eight construction checks: finite/shape validity, three byte-distinct
optical renders, common downstream repeat differences, strict analytic
Gaussian-transfer ordering at five positive frequencies, the exact blur
ladder, changed USM pixels, and both malformed plants.  All eight passed.  The
largest repeat-difference mismatch was
`1.6653345369377348e-16`, below the frozen `1e-15` bound; USM changed pixels by
up to `0.03730393225208628`.  The three optical render hashes are distinct.
The serialized construction evidence is at `results.json:510-570`.

All six score gates and all eight construction checks are true.  This proves
that the rendered construction has a nonempty accepted result, rather than
only proving that a hand-written score vector can pass.  It still does **not**
commission an image instrument: the oracle uses truth metadata ordinary
candidates are forbidden to receive (`results.json:1000-1082`).

## 4. Known-dead instruments

| instrument | M167 verdict | rejecting arm(s) | decisive observed result |
|---|---|---|---|
| D8 per-tile FRC | **REJECTED** | **P1 flat null**; also P4 blur | Detail and no-scene flat both returned `CENSORED_ABOVE`, lower bound `0.5 cyc/quad-px`; their intervals overlap completely. |
| M137 high/low band-power gap | **REJECTED** | **P1 flat null**; also P5/P6 | Flat `0.3488548829813006 dex` exceeded detail `0.3403664343410666 dex`, ratio `1.0249391472947889`, despite only `0.13314850036584688` of the coarse structure. |
| M2 `R_box9` | **REJECTED** | **P4 signed blur**; also P1/P2/P3/P5/P6 | Independent replay returned `R_box9(blurred)/R_box9(unblurred) = 0.5712148772282098`; all three M167 blur steps moved in the favourable direction. |

### 4.1 D8 per-tile FRC

M167 executes the source-hash-pinned surviving implementation at
`experiments/M-PHASE0-SPLIT2/frc.py`.  It preserves the historical classifier:
a curve above `1/7` through Nyquist is a lower bound, not a fabricated terminal
crossing.

**MEASURED.** On M167's matched flat arm, both detailed and no-scene records
were `LOWER_BOUND 0.5`; P1 therefore cannot establish
`flat.upper < detail.lower` and rejects D8
(`results.json:718-734,825-838`).  The pooled low-band FRC was
`0.9989656493074857` on detail and `0.9940552535661507` on the flat
(`results.json:280-282`).

**MEASURED.** D8 also failed signed blur.  Its crossing sequence for added
sigma `[0,.5,1,1.5]` was
`0.44807855374505606, 0.44806009012025305,
0.4481711193804649, 0.4485069054687077`; the last two steps rose rather than
fell (`results.json:750-783`).  This is the normalized common-filter
blindness recorded in the plan, now exercised by the frozen M167 predicate.

### 4.2 M137 band power

The original RAW pixels are not copied into M167 and were not reopened.
Instead, the adapter hash-pins the tracked underlying `band_ratio` source and
executes it for synthetic diagnostics, while P1 consumes the immutable,
independently verified historical kernel-gap snapshot.

**VERIFIED FROM PINNED SERIALIZED EVIDENCE, not newly re-rendered.** The adapter
reproduced the exact detail gap, flat gap, ratio and structure share above
(`results.json:150-160`).  Since the flat point is greater than the detail
point, P1 rejects it (`results.json:594-607,698-712`).  This is the same
historical `1.0249391472947889` failure, not a newly tuned surrogate.

The synthetic underlying statistic also called USM better than base
(`-1.9949655187454454 > -2.3844797126768977`) and emitted an invalid/non-refusal
on malformed inputs.  Those are retained diagnostics; the exact historical
flat failure alone is sufficient.

### 4.3 M2 `R_box9`

The adapter reimplements exactly
`population_sd(image / uniform_filter(image,9) - 1)` and pins both the M159
source and frozen result hashes.  Because lower residual was M2's favourable
direction, M167 orients its score as negative residual.

**MEASURED.** Replaying M159's complete seed-159 RNG sequence produced:

```text
unblurred R_box9 = 0.0521781532174448
blurred   R_box9 = 0.02980493738409746
blurred / unblurred = 0.5712148772282098
```

The replay equals the frozen value and is recorded at
`results.json:391-396`.  On the independent M167 blur ladder, the
higher-is-better scores rose
`-0.04995233606232108 -> -0.0445857853669207 ->
-0.03166242401262384 -> -0.021340729420569155`; every signed step is wrong.
P4 is false (`results.json:873-907,945-962`).  Thus M2 is rejected on the blur
arm as required.

## 5. Concurrent M164 result and M167 interpretation

M164 commit `19f6f54a` landed after M167's initial commissioning.

**VERIFIED FROM M164'S PINNED ARTIFACT, not reclassified as an M167
measurement.** Its mechanism probe reports:

```text
fractional R_box9 blurred/unblurred                 0.5711797973518002
additive sd(a-U9(a))/mean(a), local division removed
                                                    0.5713180075739982
median local mean blurred/unblurred                 0.9996748398406278
```

Thus the local division is not the cause of the wrong sign: removing it changes
the ratio only slightly, while blur contracts the high-pass numerator and
barely moves the local mean
(`19f6f54a:docs/research/M164-m2-repair.md`, sections 0 and 3;
`19f6f54a:experiments/M164-m2-repair/commission.json`,
`m159_mechanism_probe`).

**ARGUED BY M164, NOT ASSUMED BY M167.** The same rendered pair `(A,B=GA)`
admits both a degradation world (blur removed signal) and an improvement world
(smoothing removed noise).  Without an external assumption or observation, a
deterministic two-output statistic sees identical bytes in both worlds.

M167 does not turn that argument into an automatic rejection of reference-free
candidates.  P1-P6 remain empirical and unchanged.  M2 is rejected because
M167 independently observes its `0.5712148772282098` replay and wrong-signed
blur ladder, not because M164 declared it unidentifiable.  Conversely, the
construction-truth oracle supplies exactly the external information that makes
its positive direction known by construction; its pass is why a future
universal rejection is distinguishable from a checker incapable of passing
anything.

## 6. Reproduction

From the repository root:

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
$env:BLIS_NUM_THREADS='1'
$env:VECLIB_MAXIMUM_THREADS='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B experiments\M167-detail-battery\commission.py --checker-only
python -B experiments\M167-detail-battery\commission.py
```

**MEASURED environment:** Python `3.12.10`, NumPy `2.4.4`, SciPy `1.17.1`,
one numerical thread, zero captures opened (`results.json`, each measurement's
`environment` object).

**VERIFIED repeatability and external contract.** Two identical full runs
produced the same `results.json` SHA-256,
`210675AB3BC25FCE53EE090AAEE98E69330E95F3EC8C19FDC1CA59BCEF9229B0`.
Passing the serialized oracle back through `commission.py --input` exited `0`;
passing serialized M2 exited `1`.

## 7. Scope and consequences

- **VERIFIED:** this battery can accept its construction-truth oracle and
  reject all three required dead instruments.
- **VERIFIED:** working degradation/sabotage controls alone do not rescue an
  instrument.  M2 and D8 each pass some directional controls while failing an
  adversarial opposite-direction arm.
- **NOT ESTABLISHED:** that any deployable instrument can pass.  In particular,
  amendment 1's non-separability result makes a single-image high-frequency
  candidate unlikely to survive P5 without an independent reference, physical
  constraint, or explicit refusal.
- **NOT ESTABLISHED:** M164's identifiability argument as a universal
  impossibility theorem.  M167 will continue to judge every candidate
  empirically, including candidates that exploit independently justified
  signal/noise structure.
- **NOT ESTABLISHED:** physical false-accept/false-refusal rates.  This battery
  is synthetic and small by design; later physical commissioning still needs
  independently registered targets, calibration and provenance.
- **ASSUMED for future candidates:** their adapter is frozen independently,
  exposes only declared observations, and does not branch on M167 arm identity.
  The checker cannot prove those provenance facts from score JSON alone.

No M164, proposal, status, owner-action, capture, or product implementation file
was modified.

## 8. Arm-blinded candidate admission

### 8.1 The rule was frozen before the attack

The score JSON alone could not establish that a future adapter had not read an
arm name and returned the expected answer.  That gap is now governed by
`experiments/M167-detail-battery/ADMISSION-PREREGISTRATION.md`, frozen in
commit `20ef67e8` before the cheating canary was written or executed.

The admission unit is a frozen candidate artifact, not an author-supplied
result file.  The candidate and evaluator harness are hash-pinned before a
256-bit challenge nonce is drawn.  Three nonce-derived fixture instances are
used.  Each has 12 semantic observations plus exact duplicates of
`flat_detail`, `base`, and `improved`, for 15 anonymously permuted calls.  Each
call starts a fresh process and receives only one `.npy` image on stdin; it
receives no name, token, position, construction label or mapping.  Candidate
outputs are written to a semantic-free transcript and that transcript is
read back and SHA-256 committed before unblinding.

P1--P6 are unchanged.  New P7 requires byte-identical canonical result records
on all three duplicate pairs in every instance.  Admission also requires:

- **A1:** artifact hashes and pre-nonce Git state match;
- **A2:** source/dependency provenance has no identity channel;
- **A3:** packet argv, environment, path shape and schema are invariant and
  unlabeled;
- **A4:** each packet starts with no prior-call state;
- **A5:** candidate output is sealed before the private mapping is used; and
- **A6:** an evaluator-controlled capability sandbox denies repository,
  manifest, filesystem, network, clock, parent-memory and persistent-state
  access.

All P1--P7 and A1--A6 are conjunctive.  A missing sandbox attestation is an
explicit refusal, not an assumption that source inspection was enough.

### 8.2 Deliberately cheating canary

`cheating_canary.py` is marked `INELIGIBLE_CHEATING_CANARY`.  It is a battery
sabotage, not a candidate detail instrument.  It searches a direct argument,
environment, argv/path and stable call position for an arm identity.  When it
finds one it emits canned passing answers; otherwise a fresh-process
call-position guess always starts at the same first label and every valid
image receives the same point score.

The canary, worker and runner were first frozen at `a0c1cd6f`.  The first
post-freeze attempt exposed a Windows anonymous-pipe transport defect:
`numpy.load()` took a legal short read from stdin, so every child errored and
the preregistered P7 outcome did not occur.  No predicate or expected score was
changed.  The worker was changed only to buffer all stdin bytes before NumPy
parsing (`dbc35231`), the manifest was re-frozen (`09e2233d`), that disclosed
challenge was discarded, and a fresh nonce was generated.

An independent verifier then found that A1 compared the mutable manifest only
to working-tree bytes, omitted the imported `commission.py`, did not detect the
canary's mutable call counter, and serialized the moving repository `HEAD`
into the result.  Those are real verification defects even though the canary
was rejected.  A1 now requires the exact five-file set, pins both runtime and
Git-blob SHA-256 values, reads those objects from the named artifact commit,
requires no later committed or working-tree drift, and pins the imported
checker.  The AST audit now detects `global`/`nonlocal` and augmented state
mutation; moving `HEAD` is no longer serialized.  The strengthened runner was
frozen at `ad665b63` and its manifest at `d0bfd2e2`; the earlier valid
challenge was superseded and a new nonce was generated.

Follow-up verifiers then supplied stronger attacks: mutate a module-global
container without a `global` declaration, alias that container before
mutation, keep state on a function attribute, hide an identity argument as
keyword-only, and force a temporary-path separator spelling that only the
canary normalized.  The source audit now conservatively rejects module-level
mutable construction, every augmented or attribute/subscript assignment,
common mutator calls, classes, and every extra positional or keyword
parameter.  The path audit applies exactly the canary's normalization.  Every
packet receives the same cleared numeric-suffix working path within a run.
The final fixes were frozen at `67e2102f` and `87aaca37`; every preceding
challenge was superseded before the final nonce below was drawn.

The closeout verifier then replaced every child result with the same process
error and showed that P6 plus exact duplicate errors could mimic the expected
gate pattern.  Commissioning now additionally requires all 45 children to
return zero, parse as JSON with empty stderr, and reproduce the canary's exact
constant fallback/typed-malformed records.  That fail-closed check was frozen
at `1a4d8acb` and `481cab36`, again before drawing the final nonce.

One final adversarial probe replaced numeric `1.0` with JSON `true` and added
forged fields.  Python otherwise treats `bool` as an `int`.  The base checker
now rejects Boolean scores, and the canary check compares complete canonical
records rather than selected fields.  Those changes were frozen at
`3474cf28` and `30240575` before the final challenge.

The last schema probe put JSON Booleans in the blur-ladder sigma fields.
Those metadata now require finite non-Boolean numbers as well; the correction
and final freeze are `379c4e38` and `9c2554e6`.

**VERIFIED BY RUNNING.** The final run made 45 fresh child calls and produced:

| execution | P1 | P2 | P3 | P4 | P5 | P6 | P7 | disposition |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| legacy, direct arm label | pass | pass | pass | pass | pass | pass | n/a | canned vector passes |
| blind instance 0 | fail | fail | fail | fail | fail | pass | pass | rejected |
| blind instance 1 | fail | fail | fail | fail | fail | pass | pass | rejected |
| blind instance 2 | fail | fail | fail | fail | fail | pass | pass | rejected |

Thus the exact cheating artifact that looks perfect under the labeled
protocol is **`REJECTED_BY_BLINDED_ADMISSION`** on every hidden instance.  The
source audit independently catches its `os`/`sys` access, second
`arm_identity` argument, all twelve arm literals, and mutable `_CALL_INDEX`
state, so A2 is also false.
All nine canary-commissioning checks are true.

The disclosed replay nonce is
`1AD3D886A22CBE84F03571F29156CC77EDE0E38016893E5F56A501DD0B45F2E7`.
The semantic-free transcript is
`experiments/M167-detail-battery/admission-sealed.json`, SHA-256
`7C3E50F65EC3EC7EF2B7E538D051334CEE4FA33A2742352E93F0C7E5A4409B3B`.
The unblinded record is `admission-results.json`, SHA-256
`B91C44579250A891B4AAB2C8F70C79B7B3C8853E00BEA59E591D225E12F8BA0A`.
A full replay with that nonce reproduced both hashes exactly.

### 8.3 What is and is not closed

**VERIFIED:** the ordinary labeled/order API is exploitable, the new local API
does not disclose those channels to this attack, and the exact attack is
rejected by both its outputs and provenance audit.

**NOT VERIFIED:** OS-strength capability isolation.  The local run used fresh
ordinary Windows subprocesses, not a disposable VM.  It therefore records
`A6_capability_sandbox=false`.  A hostile native extension could still read an
absolute host path or attack another process.  The admission rule closes that
bypass by failing closed: this harness cannot emit a real-candidate admission
until an independent evaluator supplies A6.  It does not mislabel a source
scan as a security boundary.

There is an unavoidable distinction between forbidden identity and permitted
measurement.  If code identifies a fixture only from the pixels it was
legitimately given, that is content-dependent behavior and cannot be made
impossible without also forbidding image analysis.  Hidden post-freeze seeds,
three instances and source audit prevent memorized public-fixture answers;
whether a content rule measures resolution is still decided empirically by
P1--P7 and later physical controls.

Reproduction, from the repository root:

```powershell
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
$env:BLIS_NUM_THREADS='1'
$env:VECLIB_MAXIMUM_THREADS='1'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B experiments\M167-detail-battery\admission.py `
  --nonce 1AD3D886A22CBE84F03571F29156CC77EDE0E38016893E5F56A501DD0B45F2E7
```

No timing result is produced or used.

## 9. Physical false-rate capture specification

### 9.1 What the existing 657-frame session can license

The requested directory was surveyed read-only.  No RAW was decoded and
nothing under `D:\personal\macro` was written.

**VERIFIED BY RUNNING a recursive inventory and ExifTool over all 657
headers:**

| relative stack | frames | exposure | focus-position histogram |
|---|---:|---:|---|
| `flat-sw4-cpl/flat-et6s-sw4-cpl` | 65 | 6 s | `57 x 65` |
| `flat-sw4-cpl/flat-et2.5s-sw4-cpl` | 61 | 2.5 s | `57 x 61` |
| `flat-sw4-cpl/flat-et1s-sw4-cpl` | 60 | 1 s | `57 x 60` |
| `tilted-sw4-cpl` | 182 | 1 s | `57 x 76, 58 x 80, 59 x 26` |
| `tilted-sw10-cpl` | 92 | 1 s | `57 x 38, 58 x 40, 59 x 14` |
| `very-tilted-all-axis-sw10-cpl` | 197 | 1 s | `56 x 10, 57 x 40, 58 x 40, 59 x 41, 60 x 40, 61 x 26` |

Every header reports `7168 x 5120`, ISO 100, f/5.6, 200 mm,
`FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`, and image stabilization
`On`.  The six runs occupy one 2026-09-02 session from 20:13:04 through
21:01:58.

**INFERRED FROM THE CAPTURE STRUCTURE AND EXISTING REGISTRATION:** this is
excellent development material but not a physical-rate sample.

- `tilted-sw4` and `tilted-sw10` cover the same coarse encoder range, with
  exactly 2:1 populations in the complete `57` and `58` bins.  They are a
  useful real dense-versus-sparse improvement challenge.
- The 6/2.5/1-second fronto-parallel runs are a real exposure/noise ladder.
  Here “flat” means the slide is fronto-parallel; it is a patterned slide, not
  a spatially uniform no-detail field.
- The entire session is already burned development, has stabilization on, has
  only one complete pass per condition, and has no corresponding-node A/B
  repeat stacks.  It can expose a failure and prune a candidate.  It cannot
  estimate a repeatable false-accept or false-refusal rate, and it cannot be
  promoted to holdout evidence.

The archived `19-razor-edge` aperture ladder is not a free replacement.  The
repository classifies only one f/5.6 horizontal stack as development and the
other five as indeterminate; `7-aperture-pairs` includes protected holdouts.
Their pixels were not opened for M167 and they must not be silently spent.

### 9.2 The honest limit

No capture, by itself, yields an unconditional “probability this instrument is
wrong on real macro photographs.”  That rate needs:

1. an independently assigned truth label at every trial;
2. a frozen target population and sampling rule; and
3. multiple independent subjects/sessions if the claim is to generalize
   beyond one panel and one rig state.

No known-good deployable detail instrument currently supplies those labels.
Agreement with another uncommissioned statistic would be circular.

A weaker result **is** achievable without such an instrument:
intervention-conditioned error rates.  A uniform field has no scene detail,
post-render blur removes information, USM adds none, and a separately sampled
reference can supply external truth for a real-improvement subset.  The rates
below are therefore explicitly conditional on this panel, optical
configuration and registered interventions.  They are not population rates
for arbitrary natural scenes.

### 9.3 Exact acquisition requested

This is a **non-holdout physical-commissioning session**, not a scored product
session.  Do not duplicate it if the already planned M1 non-holdout rehearsal
will supply the same blocks.  Before any result is opened, freeze the
candidate, reference/truth reader, 64-site input-only manifest, transforms and
all direction predicates.

**Subjects.**

1. Use the existing microscope/calibration grid with a fine, matte,
   nonperiodic fibre or speckle patch fixed in the same tilted plane.  The grid
   is needed to prove cross-configuration sampling and registration; the
   irregular patch prevents a periodic target from carrying its own answer.
   A natural specimen alone lacks known geometry, while a razor edge alone
   does not exercise two-dimensional nonperiodic detail.  The common
   high-/low-magnification footprint must contain 64 non-overlapping
   `128 x 128` low-magnification sites with a 16-pixel guard; allocate them
   `21/21/22` across the near/middle/far reference-focus zones.
2. Use a separately illuminated opal diffuser or integrating-surface field
   with no printed texture for the null.  It must cover the same 64-site
   footprint.  Do not substitute the fronto-parallel patterned “flat” slide.

**Common camera settings.** Sony A7C II, Sony FE 100mm F2.8 GM, RAW, M mode,
ISO 100, marked f/5.6, 1 s, fixed white balance, EFCS, tripod, IBIS **off** and
lens OSS **off**.  Lighting, subject and support remain fixed within each
subject block.  Focus Bracket direction is `0 -> +`, interval 3 s.  One
unregistered histogram exposure may precede the session; clipping or
photon-starvation is a stop requiring a revised preregistration, not an
in-session exposure substitution.

| block | optical configuration | focus setting and count | acquisitions | unique licensed claim |
|---|---|---|---:|---|
| `TR-REF-NEAR/MID/FAR` | 2x Viltrox installed, maximum reproduction `M_ref >= 2.70x` | Focus Bracket **off**; 32 fixed-focus frames at each of three registered depth zones | 3 bursts, 96 frames | Supplies the separately sampled reference needed to label true-improvement sites. Without this block no physical false-refusal rate is licensed. |
| `TEST-sw4-A/B` | teleconverter removed, live-measured `M_test <= 1.30x` | step width 4, 55 frames | 2 complete stacks, 110 frames | Independent whole-pass repeats of the denser scored observation; supports repeat uncertainty without pretending exposures were interleaved per node. |
| `TEST-sw10-A/B` | identical test configuration and reset | step width 10, 27 frames | 2 complete stacks, 54 frames | Supplies the sparse-focus intervention. It is a degradation label only at sites independently declared eligible from the reference, never merely because it has fewer frames. |
| reset/start/end witnesses | identical test configuration | Focus Bracket off; 6 frames in each of two reset and eight start/end groups | 10 bursts, 60 frames | Detects reset, endpoint and between-pass drift; failure voids the corresponding A/B rates. |
| `NULL-sw4-A/B` | identical test configuration, diffuser substituted | step width 4, 55 frames | 2 complete stacks, 110 frames | Supplies a physical no-scene-detail denominator for the flat false-accept rate. These are not calibration flats. |
| reference calibration | converter installed, reference exposure/focus state | Focus Bracket off; 32 each of flat A, flat B, dark A, dark B | 4 groups, 128 frames | Separates reference signal from sensor pattern/noise; A and B masters are disjoint. |
| test calibration | teleconverter removed, test exposure/focus state | Focus Bracket off; 32 each of flat A, flat B, dark A, dark B | 4 groups, 128 frames | Separates test/null signal from sensor pattern/noise without importing the reference-state map. |

Registered total: **686 frames** =
`96 + 110 + 54 + 60 + 110 + 128 + 128`, in **six complete focus-bracket
stacks**, three reference bursts, ten witness bursts and eight calibration
groups.  The histogram exposure is outside the count.

The exact ordering of the four test stacks is
`sw4-A, sw10-A, sw10-B, sw4-B`, with the registered reset and six-frame
start/end witnesses around each pass.  This ABBA order brackets monotone drift.
The two null stacks are then complete sequential passes.  There is **no**
request for two exposures at one focus node: every A or B is a complete
in-camera bracket, and corresponding nodes are compared only after both passes
finish.

Two preconditions make the numeric settings honest rather than decorative:

1. the grid must verify live that `M_ref / M_test >= 2.0`; directory names and
   EXIF do not supply magnification; and
2. a non-holdout exact-configuration preflight must show that 55/step-4 and
   27/step-10 are gap-free over the target and yield at least 64 common
   guarded sites.  If either fails, stop.  Do not choose replacement counts
   after candidate outputs are visible.

### 9.4 The rates this licenses

Fix 64 non-overlapping guarded sites from input geometry before rendering or
candidate execution.  A/B halves estimate measurement uncertainty but are not
counted as 128 independent sites.  Report each arm separately:

- **flat false-accept rate:** fraction of the 64 null sites that neither
  refuse as featureless nor lie wholly below the matched detailed site;
- **USM false-accept rate:** fraction at which a fixed post-render USM copy is
  wholly above its unchanged source;
- **blur wrong-sign rate:** fraction at which any fixed post-render blur rung
  ties or rises;
- **physical-improvement false-refusal rate:** among sites declared eligible
  by the frozen independent `>=2x` reference reader, the fraction for which
  the dense observation does not lie wholly above the sparse one, including
  refusals on eligible detail.

USM and blur require no extra exposures.  Their transformations are applied
after the A/B renders are fixed and use the already frozen M167 parameters.
No result may be pooled across arms to hide a failure.

For the flat, USM and blur arms, all 64 registered sites give empirical-rate
increments of `1/64 = 1.5625%`.  **VERIFIED BY CALCULATION:** under an
independent Bernoulli model only, zero failures among those 64 has a one-sided
95% Wilson upper bound `0.040559499465846936`.  The physical-improvement
denominator is instead `N_eligible <= 64`; report its increment as
`1/N_eligible` and recompute its interval from that denominator when
`N_eligible > 0`.  If `N_eligible = 0`, the physical-improvement rate is
`UNMEASURABLE`, not zero and not a division.  Do not print the 64-site bound
when fewer than 64 reference sites qualify.  Sites from one panel are
clustered in every arm, so any such Wilson number must be labelled nominal and
must not be promoted to a general real-world bound.  A defensible
across-subject rate still requires a later population-sampled, multi-session
holdout after both candidate and truth reader are commissioned.

If the independent reference reader cannot be commissioned, the capture still
licenses the flat, blur and USM false-accept rates and repeatability diagnostics.
It licenses **no physical false-refusal rate**.  That limitation is preferable
to relabelling dense sampling, aperture, or visual preference as ground truth.
