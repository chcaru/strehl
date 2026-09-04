# M138 corrected W1 gate draft

Status: **SECOND REVIEW SEND-BACK UNDER REPAIR; NOT FROZEN.**

This document is a specification, not a campaign result. No corrected-gate
candidate output was generated while repairing it. Commit `7fb925bf` is not a
design seal: independent review rejected that draft. A later commit may change
`corrected-gate-contract.json` from
`DRAFT_PENDING_THIRD_INDEPENDENT_REVIEW` to
`FROZEN_BEFORE_CORRECTED_GATE_OUTCOME_GENERATION` only after a third
independent review, all currently unbound inputs, and the cost benchmark are
present. Until then, `adjudicate.py --result ...` returns
`INSTRUMENT_INVALID`.

I am both the author of the original M138 audit and this replacement
specification. That conflict remains. Source hashes, exact evidence schemas,
executable recomputation, and a required independent review constrain it; they
do not make author self-review independent.

## Evidence tags

- **[VERIFIED]**: read or computed directly in this work.
- **[INHERITED]**: taken from an existing committed source.
- **[VERIFIED—PREREGISTERED]**: fixed here before corrected-gate outcomes; a
  design value, not a measurement.
- **[VERIFIED—ESTIMATE]**: an estimate rather than measured campaign runtime.

A tag on a heading or paragraph applies to every numeric value beneath it.
File line locations, commit identifiers, hashes, schema versions, list
ordinals, and mathematical subscripts are identifiers rather than quantitative
findings.

## Review disposition

The review left the structural rule intact:

- width is diagnostic rather than dispositive;
- calibration and instrument failures cannot refute the merge;
- one globally meaningful admission coordinate is selected on development and
  confirmed once on sealed holdout; and
- a refutation is scoped to the registered implementation and evidence deck.

The first repair changed the unsupported temporal threshold, fixed the hull
stage, specified M135's executable interface, withdrew the unsupported cost
estimate, and removed the premature freeze. The second-review repair closes
four remaining assertion channels: temporal powers, pilot independence,
inflation commissioning, and cost qualification. It also adds mutation
coverage for the two M135 three-state guards that independent execution found
correct but the prior self-test did not exercise.

## Existing behavior and provenance

The existing candidate chooses a raw-energy maximum and forms each
winner-to-frame gap from two plug-in variance terms
(`experiments/PHASE1-DESIGN/measure.py:171-180`). Its legacy comparator changes
soft-power exponent by band
(`experiments/PHASE1-DESIGN/measure.py:129-141`). Candidate and legacy
variance fields are ordinary Gaussian pyramids multiplied by scalar transfer
factors (`experiments/PHASE1-DESIGN/measure.py:235-250`); the corresponding
Rust helper carries variance with the image Gaussian reducer
(`crates/strehl-core/src/pyramid.rs:372-384`).

The withdrawn preregistration applied a per-band/per-ROI width predicate before
rendering (`experiments/PHASE1-DESIGN/PREREGISTRATION.md:167-203`), and its
implementation renders output only after that filter
(`experiments/PHASE1-DESIGN/measure.py:568-575`). The proposal defines width
before output quality (`docs/proposals/2026-09-phase1-design.md:312-316`) and
maps an empty width intersection to `NO_COMMON_K`
(`docs/proposals/2026-09-phase1-design.md:340-350`).

The current calibration fits coarse-band transfer jointly
(`experiments/PHASE1-DESIGN/reference.py:625-633`), records per-frame coverage
but gates pooled coverage
(`experiments/PHASE1-DESIGN/reference.py:666-727`;
`experiments/PHASE1-DESIGN/reference.py:1052-1064`), and exercises its
Poisson–Gaussian control through one pyramid band
(`experiments/PHASE1-DESIGN/reference.py:1080-1134`).

### Why the old temporal constant is withdrawn

**[INHERITED]** The `0.90` number first appears as an authored flat-power
acceptance constant in
`f5658e5d:docs/proposals/2026-09-phase1-design.md:280-286`. The frozen
commissioning later placed its quiet and noisy synthetic powers at `0.70` and
`1.20`, respectively
(`experiments/PHASE1-DESIGN/reference.py:1135-1200`). It therefore tested
direction far from the `0.90` boundary; it did not calibrate that boundary.
Nothing found here shows that `0.90` was selected from `NO_COMMON_K`
survivors, and this repair makes no such accusation.

**[VERIFIED]** `sqrt(0.90)=0.948683298051`, so the old power bar required only a
`5.131670195%` RMS reduction. A `10%` RMS reduction would instead imply a
power ratio of `(1-0.10)^2=0.81`. Those conversions expose the physical
meaning; they do not authorize either effect size.

The prior draft copied `0.90` from a spatial shared-green band-power statistic
into a per-CFA temporal-power statistic. Those estimands are not interchangeable.
The copied constant and the prior unchanged-constant defence are withdrawn.

## Corrected merge coordinate

### Width is diagnostic, never dispositive

`n_eff`, singleton fraction, below-floor fraction, and candidate/legacy width
ratios are emitted for every capture, band, ROI, and threshold. They may
diagnose mechanism or collapse. They do not remove an arm from rendering,
change a confidence interval, choose the threshold, or alter a verdict.

The old **[INHERITED] `±5%`** width window remains only as a labelled historical
diagnostic. No adjudicator branch reads it.

### Globally meaningful admission coordinate — [VERIFIED—PREREGISTERED]

For each non-winner frame retain the observed energy gap:

```text
D_i = E_w - E_i
```

Do not treat `D_i / sqrt(sigma2_Ew + sigma2_Ei)` as already pivotal. Build an
independent equal-focus calibration distribution through the complete decision
path: source-level Poisson–Gaussian draws, affine pull, shared-green
construction, variance stabilisation, every Laplacian band, energy smoothing,
and winner selection from the exact stack size.

For the frozen nuisance stratum, with calibration gaps
`D^(1)...D^(M)`, define:

```text
u_i = (1 + count(D^(j) <= D_i)) / (M + 1)
```

Equal scores take the conservative upper rank. The winner is explicitly
admitted. Calibration retains a frame-role row only when that role is not the
selected winner. The below-floor arithmetic-mean fallback remains the one in
`experiments/PHASE1-DESIGN/measure.py:407-422`.

Admit a non-winner iff `u_i <= tau`. `tau` is the sole operating parameter.
Band, stack size, frame warp, gain mode, signal quartile, and positive-signal
stratum index a frozen calibration distribution; they are not independently
selectable thresholds.

The registered threshold grid is:

```text
tau = 0.00, 0.01, 0.02, ..., 1.00
```

The endpoint `0.00` admits only the winner outside fallback, and `1.00` admits
every finite frame. Every arm is rendered. A selectable center and both
immediate `0.01` neighbors must pass; the greatest passing center is selected.

## Standardisation repairs

Every heading marked BLOCKING returns `INSTRUMENT_INVALID` on failure. It does
not return a Phase-1 refutation.

### Pooled-only coverage gating — BLOCKING

**[VERIFIED—PREREGISTERED]** A calibration cell is keyed by manifest hash,
exact stack size, frame ordinal, band, gain mode, input-only signal quartile,
and positive-signal anchor. The positive-signal coordinate
`r=(q_w+q_i)/(F_w+F_i)` uses left-closed bins
`[0,0.25)`, `[0.25,1)`, `[1,4)`, `[4,16)`, and `[16,+infinity)`, represented
by anchors `[0,0.5,2,8,32]`.

Use `4,095` calibration trials and an independent `8,192` validation trials
per cell. At checkpoints
`[0.01,0.05,0.25,0.50,0.75,0.95,0.99]`, the sealed evidence contains every
trial's `u`, not a PASS flag or reported error. The adjudicator counts
`u<=checkpoint` and recomputes each rate. Every cell must have maximum absolute
error `<=0.03`; pooled summaries are not accepted.

The physical static-repeat null separately supplies every registered
session/band/gain cell. Each has at least `256` support-separated sites. A
Bonferroni simultaneous `99%` Wilson interval, with
`alpha_cell=0.01/C` over the complete registered predicate family, must contain
every nominal checkpoint. The interval is recomputed from trial-level physical
`u` values. Session, band, and gain cells cannot rescue one another.

### Positive-`q` commissioning — BLOCKING

**[VERIFIED—PREREGISTERED]** Equal-focus trials carry coherent signal at all
anchors `[0,0.5,2,8,32]`. For every calibration cell, a non-winner receives
focus deficits `[0,1,2,4]` in unselected standard-deviation units while
nuisance variables remain fixed. Recomputed `99%` Wilson intervals for
admission probability must fall strictly and not overlap between adjacent
steps. A calibrated null with no separation power fails.

### All-band Poisson–Gaussian control — BLOCKING

**[VERIFIED—PREREGISTERED]** Generate noise before warp and decision
transforms. Exercise bands `[0,1,2,3,4,5,6]`, both gain modes, all input-only
signal quartiles, all positive-signal anchors, every frame role, and the four
CFA planes `R`, `G1`, `G2`, and `B`. Shared green drives admission; the
per-plane paths remain evidence for noise propagation and output checks. The
current one-band construction cannot stand in for this requirement
(`experiments/PHASE1-DESIGN/reference.py:1080-1134`).

### Approximate variance propagation — BLOCKING

The authoritative standardisation is the independently validated empirical
rank of the complete selected gap. Analytic `sigma2_E` may be emitted only as
`sigma2_E_approx`; it cannot choose a stratum or enter a verdict. Passing each
draw through the actual warp, transform, pyramid, and energy operator carries
filter covariance and spatially varying noise into the reference distribution.

An analytic covariance-aware predictor is advisable for product cost, but it
is not load-bearing until a new preregistration proves the same per-cell
coverage.

### Selected-winner and stack-size calibration — BLOCKING

Every trial creates the exact manifest stack, applies the production winner
tie-break, and forms gaps only after selecting that maximum. Banks are indexed
by exact stack size. Interpolation or reuse from another stack size is
forbidden. This addresses the maximum-over-stack dependence documented at
`crates/strehl-core/src/merge.rs:421-427`.

## Output-quality instruments

### Capture roles

Withdrawn-W1 captures may provide diagnostics only. Development requires a
disposable physical M135 rehearsal family and an independent static-repeat
family. Holdout requires fresh subject/session families for both roles. A
pre-output amendment must bind exact capture IDs, role membership, temporal
site IDs, transforms, exclusions, and artifact hashes. Development and holdout
families must be disjoint.

### M135 executable interface

The gate does not invent another detail statistic. M135's estimator requires
two independent references and two independent outputs
(`experiments/M135-detail-instrument/PREREGISTRATION.md:26-53`), returns
eligibility, information, transfer, unexplained-repeatability, and noise
coordinates (`experiments/M135-detail-instrument/instrument.py:207-260`), and
already requires both a blur defect and planted optical improvement
(`experiments/M135-detail-instrument/PREREGISTRATION.md:127-149`).

The existing M135 scope is synthetic and does not qualify a physical path
(`experiments/M135-detail-instrument/PREREGISTRATION.md:7-12`). The M138
contract therefore remains `UNBOUND`.

Before any candidate render, M135 must provide and M138 must bind all of:

1. `physical_preregistration`: path and SHA-256;
2. `checker_entrypoint`: executable Python path and SHA-256;
3. `checker_bundle_manifest`: path and SHA-256 covering every transitive source
   and calibration dependency;
4. `environment_manifest`: Python and dependency versions, path and SHA-256;
5. `comparison_rule`: the exact candidate-versus-legacy rule, path and SHA-256;
6. `commissioning_request`: raw physical control artifacts, path and SHA-256;
   and
7. exact development and holdout detail-capture IDs.

The checker interface schema is `m135-m138-checker/v1`. M138 invokes:

```text
python -I CHECKER --m138-commission REQUEST
python -I CHECKER --m138-evaluate REQUEST
```

An evaluation request has this required envelope:

```json
{
  "schema": "m135-m138-evaluate-request/v1",
  "capture_ids": ["..."],
  "artifacts": [{"path": "...", "sha256": "..."}],
  "binding_hashes": {
    "checker_bundle_manifest_sha256": "...",
    "environment_manifest_sha256": "...",
    "physical_preregistration_sha256": "...",
    "comparison_rule_sha256": "..."
  },
  "comparisons": ["M135-defined raw capture bundles"]
}
```

A commissioning request uses schema
`m135-m138-commission-request/v1` and the same artifact-reference form. Its
payload supplies the physical null, pre-noise blur, pre-noise optical
improvement, missing-flat, and hash-mutation cases defined by M135's own
physical preregistration.

The adjudicator opens and verifies each request artifact before execution. The
checker emits exactly one JSON object to standard output:

```json
{
  "schema": "m135-m138-checker/v1",
  "checker_sha256": "...",
  "checker_bundle_manifest_sha256": "...",
  "environment_manifest_sha256": "...",
  "physical_preregistration_sha256": "...",
  "comparison_rule_sha256": "...",
  "request_sha256": "...",
  "detail_state_by_capture": {"capture-id": "DETAIL_PASS"},
  "detail_pass_by_capture": {"capture-id": true}
}
```

Commissioning replaces the evaluation state and Boolean maps with a `controls`
object whose keys exactly equal the required control list in
`corrected-gate-contract.json`. A nonzero process exit, extra/missing capture,
missing artifact, hash mismatch, wrong schema, or missing control is
`INSTRUMENT_INVALID`. The checker-bundle manifest itself is opened, and every
transitive source listed in it is hash-verified. The bound checker must reject
an environment that differs from its environment manifest. Cached or
campaign-supplied `detail_pass` values are forbidden.

Evaluation is explicitly three-state:

- `DETAIL_PASS` requires a matching Boolean `true`;
- `DETAIL_FAIL` requires a matching Boolean `false`; and
- `INSTRUMENT_INVALID` requires that capture to be absent from the Boolean
  map.

The state map must contain every requested capture. The Boolean map must
contain exactly the internally valid pass/fail captures. Any null, refusal,
unknown state, missing state, state/Boolean disagreement, or Boolean supplied
for an internally invalid capture returns `INSTRUMENT_INVALID`. Only a valid
`DETAIL_FAIL` may participate in the scientific output-quality verdict. The
adjudicator never coerces an invalid state to `false`
(`experiments/M138-w1-gate-audit/adjudicate.py:829-896`).

Physical commissioning must execute and pass:

- a physical null;
- a pre-noise blur that lowers the information coordinate;
- a pre-noise optical improvement that raises it;
- missing-flat-control refusal; and
- artifact-hash-mutation refusal.

The positive plant is therefore an executable obligation, not prose. Its
magnitude and decision rule belong to M135's physical preregistration and may
not be chosen after Phase-1 output exists. Until every binding exists and the
adjudicator executes both checker modes, the only detail verdict is
`BLOCKED_DETAIL_INSTRUMENT`.

### Temporal noise: paired-repeat power — [VERIFIED—PREREGISTERED]

For mode `m`, site `s`, and CFA plane `c`, use two independently captured
static-repeat outputs:

```text
P_m,s,c = 0.5 * mean((Y_m,1 - Y_m,2)^2)
R_c     = mean_s(P_candidate,s,c) / mean_s(P_legacy,s,c)
theta_c = log(R_c)
```

The scene cancels in the repeat difference. This is temporal output power, not
spatial band energy. The independent arithmetic rationale is in
`docs/research/M62-sqrt-n.md:32-45`; its physical branch was not run
(`docs/research/M62-sqrt-n.md:64-70`), so it supplies arithmetic rather than
physical qualification.

#### Hash-bound extraction and independence — [VERIFIED—PREREGISTERED]

The temporal instrument is not bound until these three references exist in the
contract and verify by SHA-256: `extractor_entrypoint`,
`extractor_bundle_manifest`, and `extractor_environment_manifest`. The bundle
uses schema `m138-temporal-extractor-bundle/v1`, lists every transitive source
file, and must include the exact entrypoint
(`experiments/M138-w1-gate-audit/adjudicate.py:898-933`).

For scored output, M138 invokes exactly:

```text
python -I EXTRACTOR --m138-scored REQUEST --capture-id CAPTURE
```

`REQUEST` uses schema `m138-temporal-extraction-request/v3`. It contains no
power, ratio, confidence bound, or PASS field. For each registered capture it
contains only:

- the frozen `site_ids` and hash-bound site manifest;
- exactly two distinct source-capture identities and two hash-distinct source
  artifacts, in repeat order;
- exactly two candidate-output references and two legacy-output references,
  in the same repeat order.

All four output paths must differ. Within each mode, the two repeat artifacts
must also have different hashes. Candidate and legacy hashes for the same
repeat are allowed to be equal: exact equality is a valid scientific
no-improvement outcome, not an instrument error. The ordered output role
inherits the ordered source-capture identity; an implementation may not choose
or swap the pair after inspecting output. Source identities, source hashes, and
output paths may not be reused by another capture in the same evidence deck.

The executed extractor emits schema `m138-temporal-extractor/v1`, mode
`SCORED`, its own SHA-256, the request SHA-256, capture ID, exact site ledger,
and one sufficient-statistic row per CFA plane and mode:

```json
{
  "squared_difference_sum": ["one finite positive value per site"],
  "sample_count": ["one positive integer per site"]
}
```

The extractor may not emit site powers. The adjudicator computes
`P=0.5*squared_difference_sum/sample_count`, then computes ratios, bootstrap
bounds, and verdicts. Thus replacing a referenced output changes the
hash-verified extractor input; changing a power assertion is impossible
because the request has no such field
(`experiments/M138-w1-gate-audit/adjudicate.py:935-1156`).

For the pilot, M138 invokes:

```text
python -I EXTRACTOR --m138-pilot REQUEST --capture-id CAPTURE
```

The request schema is `m138-temporal-pilot-request/v2`. Every pilot capture
contains one target scored-capture ID, the frozen site ledger, four unique
source-capture identities, and four path- and hash-distinct output artifacts.
The order is frozen: `(1,2)` is pair A and `(3,4)` is pair B. The extractor
emits squared-difference sums and counts for those two pairs; the adjudicator
derives `P_A` and `P_B`. A copied file under another path is rejected by its
duplicate hash, including reuse across pilot targets. Candidate and legacy
renders of the same acquisition are
paired measurements, not independent acquisitions; the repeat captures inside
each temporal pair are the units that must be independent
(`experiments/M138-w1-gate-audit/adjudicate.py:1228-1370`).

#### No replacement effect-size constant

**[VERIFIED—PREREGISTERED]** The temporal decision boundary is `1.0`, the
estimand's natural no-improvement null. For one arm, resample paired site
indices within each capture, using the same resample for all four CFA planes.
For bootstrap replicate `b` and capture-plane cell `j`, compute
`e_bj=theta_bj-theta_j`. Let `q` be the `95th` percentile of
`max_j(e_bj)` over `8,192` deterministic replicates. Then:

```text
U_j = exp(theta_j + q)
```

The arm passes temporal noise iff every `U_j < 1.0`. This is a simultaneous
one-sided `95%` family bound across all registered captures and all four
planes. Report the physically interpretable guaranteed RMS reduction:

```text
delta_guaranteed = 1 - sqrt(max_j(U_j))
```

No positive magnitude is claimed beyond that lower bound. This is a strict
Pareto-superiority test, not a disguised `0.90` replacement.
The resampler is NumPy `default_rng`/PCG64 with seed `138138` mixed with the
arm label by SHA-256; quantiles use method `higher`.

#### Power and site-count binding

The old `64`-site minimum is withdrawn as an assumption of adequacy. It remains
the lowest admissible count, but it has no demonstrated power for this
estimand or for the four-plane/all-capture conjunction.

Before freeze, acquire a candidate-independent pilot with four independent
legacy repeat bursts per matched capture condition. The two disjoint burst
pairs provide `P_A` and `P_B` under the null. The pilot must expose at least
`64` support-separated sites so the old proposal can be evaluated rather than
presumed.

An owner-approved effect requirement must state the smallest RMS reduction
worth detecting, `delta_required`, before candidate output. The requirement
schema is `m138-noise-effect-requirement/v1`; it must contain the physical claim
text, `authority=OWNER_APPROVED_REQUIREMENT`, and a hash-bound approval
artifact. A bare number in the contract is invalid. The corresponding planted
power shift is derived, not authored:

```text
R_required = (1 - delta_required)^2
log_shift  = 2 * log(1 - delta_required)
```

Using the same max-statistic resampling and the complete development or
holdout capture-by-plane conjunction, estimate the probability that all
simultaneous upper bounds fall below `1.0`. The familywise type-I budget is
`alpha=0.05`. Because a false refutation is no less serious than a false GO,
the type-II budget is set symmetrically to `beta=0.05`, hence required power
`0.95`. The one-sided `95%` Wilson lower bound on simulated power, not its
point estimate, must be `>=0.95`.

The power artifact must report power at exactly `64` sites and at the selected
site count. The selected count is frozen into every site ledger and must meet
the power rule for both the full development conjunction and the full holdout
conjunction. If no available count meets it, or if `delta_required` has no
external provenance, the result is `INSTRUMENT_INVALID`; a convenient effect
or threshold may not be invented.

At this draft's authoring, the temporal extractor binding,
`delta_required`, the physical pilot, and the power-qualified site count do not
exist. The temporal instrument is therefore intentionally `UNBOUND`.

### Hull: PRE-CLAMP reconstruction

The old implementation collapses the pyramid and immediately clips it to the
aligned-input hull (`experiments/PHASE1-DESIGN/measure.py:443-460`). A
post-clamp check would therefore be nearly tautological.

**[VERIFIED—PREREGISTERED]** The corrected stage measures the quantized
linear-DN reconstruction before the aligned-input clamp:

```text
z_q = output_quantize_without_hull_or_sensor_clamp(collapse(levels))
d_hull = max(lo - z_q, 0, z_q - hi)
max(d_hull) <= 1 DN
```

The ordering is explicit: collapse, apply the delivered format's rounding in
floating storage, measure against independently recomputed aligned-input
minimum/maximum, then apply the production clamp. Evidence labelled
`POST_CLAMP` is `INSTRUMENT_INVALID`. The interpretation is a bound on
unconstrained reconstruction overshoot; it cannot be passed merely because the
shipping output was clipped. The **[INHERITED] `1 DN`** tolerance retains its comparator-independent
provenance from the original design
(`docs/proposals/2026-09-phase1-design.md:226-230`).

## Raw sealed evidence contract

The governing rule is:

> No submitted scalar, array, or status string may carry a verdict. Every
> quantity the gate scores must be recomputed by the adjudicator from a
> hash-bound artifact, and every artifact reference that is required to be
> independent must be verified distinct.

“Submitted” here means copied into a result or control manifest as an already
interpreted score. Trial-level observations and extractor sufficient
statistics may live in hash-bound artifacts, but the adjudicator performs the
registered arithmetic and decision itself.

The top-level `m138-result/v3` file contains only the exact contract hash and
hash-bound references to standardisation, commissioning, development, and
optional holdout artifacts. Every reference is `{path, sha256}`. Paths are
relative and must remain inside the sealed result tree.

The adjudicator itself:

- opens every referenced artifact and verifies SHA-256 before use;
- recomputes every standardisation checkpoint rate from trial-level
  compatibility values;
- checks every manifest/frame/band/gain/signal/positive-signal cell;
- recomputes physical-null intervals and focus-power ordering;
- executes the exact hash-bound temporal extractor on each scored request,
  accepts only per-site squared-difference sums and integer sample counts, and
  computes every temporal power as `0.5*sumsq/count`;
- rejects repeated source-capture identities, repeated independent source
  hashes, repeated output paths, and repeated within-mode repeat hashes;
- executes the same extractor on the four-burst pilot, requires four unique
  source-capture identities and four path- and hash-distinct artifacts, and
  forms disjoint pairs `(1,2)` and `(3,4)` itself;
- reads pre-clamp reconstruction and input-hull arrays and recomputes maximum
  excess;
- verifies candidate and legacy postprocess bundle hashes are identical;
- executes the bound M135 checker on hash-verified raw requests; and
- opens the hash-bound cost benchmark, runner bundle, environment, and workload
  manifest; validates finite positive warm measurements; and recomputes both
  wall-clock totals
  (`experiments/M138-w1-gate-audit/adjudicate.py:1483-1622`); and
- rejects old-style supplied conclusions such as `seal_valid`, `detail_pass`,
  `candidate_site_power`, `pair_a_site_power`,
  `noise_power_upper95_by_capture`, and
  `maximum_hull_excess_dn_by_capture`.

A missing required artifact, hash mismatch, malformed array, omitted
capture/plane/cell, duplicated independent reference, post-clamp hull record,
stale checker/extractor hash, non-finite benchmark measurement, or extra
supplied conclusion returns `INSTRUMENT_INVALID`. It can never become a
quality failure or a GO.

`--check` has two modes. A draft receives structural/source/document checks and
is reported explicitly as not frozen. A contract claiming the frozen status
must additionally open and hash-verify the independent review, all M135
bindings, the temporal extractor bundle/environment/effect/pilot, both
complete disjoint capture ledgers, and every cost artifact; it also recomputes
pilot power and benchmark totals. A malformed review object, an unbound M135
adapter, a null ledger, a missing extractor, or null benchmark measurements
therefore makes `--check` exit nonzero
(`experiments/M138-w1-gate-audit/adjudicate.py:1624-1656`).

## Pass/fail rule

### Freeze order

1. Commit this repaired draft.
2. Obtain the third independent review.
3. Bind the temporal extractor, transitive bundle, and environment.
4. Bind the external temporal effect requirement and four-burst pilot.
5. Bind the power-qualified temporal site count.
6. Bind the physical M135 checker, dependency bundle, rule, environment, and
   bidirectional commissioning request.
7. Bind disjoint development/holdout role and site ledgers.
8. Run and record the representative cost benchmark.
9. Change the contract to
   `FROZEN_BEFORE_CORRECTED_GATE_OUTCOME_GENERATION`, bind the review artifact
   and frozen commit, and commit that activation without candidate output.
10. Commission the standardisation and output instruments from raw evidence.
11. Render and score every development `tau` arm.
12. Select and commit the one global `tau`.
13. Open holdout once and render only legacy plus that selected candidate.

No candidate output may exist before the activation commit. No holdout output
may exist before selection.

### Development — [VERIFIED—PREREGISTERED]

For one `tau`, `OUTPUT_PASS(tau)` is true iff, on every registered development
capture:

1. the freshly executed, hash-bound M135 checker passes detail;
2. every recomputed simultaneous temporal-power upper bound is `<1.0`;
3. every recomputed pre-clamp hull excess is `<=1 DN`;
4. all raw evidence values are finite; and
5. candidate and legacy use byte-identical postprocess bundles and no
   arm-specific postfilter.

There is no averaging across captures, planes, or criteria. A robust center
requires `OUTPUT_PASS` at itself and its immediate `±0.01` neighbors. Select
the greatest robust center. The endpoints are controls and cannot be centers.

### Holdout

Render only the selected global `tau`. The same `OUTPUT_PASS` rule applies to
the exact sealed holdout ledger. A changed threshold, site, exclusion, checker,
pipeline, or artifact hash returns `INSTRUMENT_INVALID`.

### Deterministic verdicts

| Condition | Verdict | Meaning |
|---|---|---|
| Draft contract, absent artifact, hash mismatch, failed standardisation, failed bidirectional commissioning, unsupported temporal power, or unsupported cost | `INSTRUMENT_INVALID` | No Phase-1 inference |
| Physical M135 binding absent | `BLOCKED_DETAIL_INSTRUMENT` | No Phase-1 inference |
| Valid instruments; no robust development center | `PHASE1_REFUTED_NO_GLOBAL_OUTPUT_OPERATING_POINT` | Frozen Phase-1 candidate family refuted |
| Robust center selected; holdout unopened | `AWAITING_HOLDOUT` | No final verdict |
| Selected center fails any holdout output requirement | `PHASE1_REFUTED_HOLDOUT` | Frozen Phase-1 version refuted |
| Selected center passes every holdout output requirement | `PHASE1_GO` | Phase-1 may proceed to integration |

A genuine refutation exists only after all instruments, power, evidence,
hashes, cost benchmark, and freeze are valid, and then either no
three-adjacent development interval passes or the selected threshold fails
holdout.

## Why this is not a weaker bar

Removing the **[INHERITED] `0.90`** value does not silently replace it with a
friendlier number. The
repaired gate asks the exact Pareto question: whether temporal power is
strictly lower while independently referenced detail and pre-clamp integrity
survive. The simultaneous upper bound must clear the natural null in every
capture and CFA plane. The guaranteed RMS reduction is reported rather than
hidden behind a power ratio.

The gate cannot refute Phase 1 unless a separately justified RMS target is
shown detectable at the frozen site count. It cannot return GO unless the
observed improvement itself clears the simultaneous no-improvement boundary.
A stronger product claim, such as a specified minimum RMS reduction, requires
its own external requirement and cannot be inferred from this GO.

Average-everything remains exposed to M135's detail/transfer veto.
Winner-take-all remains exposed to the temporal superiority test. Width removes
no arm. The physically commissioned detail instrument is stricter than the
withdrawn synthetic cross-power test
(`experiments/PHASE1-DESIGN/reference.py:1135-1200`).

## Commissioning in both directions

### Standardisation — [VERIFIED—PREREGISTERED]

- Null evidence must satisfy every recomputed checkpoint.
- A wrong-stack bank and an omitted-warp-correlation bank must each push at
  least one cell beyond absolute error `0.03`.
- The repaired bank's score
  `S_cal=0.03-maximum_absolute_admission_error` must exceed both defective
  scores and be nonnegative.
- The focus-deficit ladder `[0,1,2,4]` must show ordered separation.

### M135

The adjudicator runs `--m138-commission` and requires the physical null, blur
defect, optical improvement, missing-flat refusal, and hash-mutation refusal.
Both directions are mandatory. No cached PASS field is read.

### Temporal noise — [VERIFIED—PREREGISTERED]

Define `S_noise=-max_j(log(R_j))`, so larger is better.

- One hash-bound base request is extracted once. The campaign may not submit
  four transformed power arrays or four PASS labels.
- The adjudicator applies the registered transforms to the recomputed
  candidate repeat-difference power:
  `IDENTITY`,
  `(1+delta_required)^2`,
  `(1-delta_required)^2`, and the identity induced by adding the same scene
  term to both repeats. The legacy power is unchanged.
- The null and common-scene placebo must have simultaneous two-sided `95%`
  intervals containing `1.0` in every cell, and their recomputed power arrays
  must be exactly equal.
- The inflation plant must lower `S_noise` **and**
  `passes_superiority` must be false.
- The improvement plant must raise `S_noise` and pass superiority at the
  commissioned site count.
- Suppressing the improvement evidence, deleting any artifact, mutating a
  hash, or relabelling post-clamp hull values as pre-clamp must make the
  adjudicator refuse.

The transform application and the explicit inflation-superiority refusal are
implemented at
`experiments/M138-w1-gate-audit/adjudicate.py:1832-1947`.

`python experiments\M138-w1-gate-audit\adjudicate.py --self-test` executes
non-campaign null, defect, improvement, missing-artifact, hash-mutation,
duplicate-output, duplicate-pilot, supplied-power, supplied-Boolean, M135
`DETAIL_FAIL`, M135 internally invalid, M135 invalid-plus-Boolean, M135
unknown-plus-Boolean, post-clamp, malformed-freeze, null-cost, refutation,
holdout, and width-irrelevance controls. The M135 null-state plants must return
`INSTRUMENT_INVALID`; the valid `DETAIL_FAIL` plant must remain a scientific
failure rather than an instrument failure.

### Guard mutation commissioning — [VERIFIED]

In a disposable scratch copy under this experiment directory, exact
single-match source deletions produced:

- removing the internally-invalid-plus-Boolean rejection: exit `1`;
- removing the unknown/null-state rejection: exit `1`; and
- an inert comment-only edit: exit `0`.

The scratch tree was deleted after the checks. These mutations establish that
the permanent self-test now exercises both guards; they do not qualify M135's
still-unbound physical instrument.

## Cost

Status: **UNSUPPORTED.**

The old width-only run took **[VERIFIED] `263.6871026000008` seconds** over
**[VERIFIED] `161` frames**, but rendered no Pareto output
(`experiments/PHASE1-DESIGN/results/gate.json:1`;
`experiments/PHASE1-DESIGN/results/run.json:1`). It cannot support the prior
**[INHERITED] `10/4/2`-hour** allocation, which is withdrawn.

The current instruction forbids RAW decoding and build workloads, so no
representative render benchmark was run. Before activation, benchmark:

- one complete calibration cell at a frozen production stack size;
- one full-resolution disposable, non-scored legacy/candidate render pair;
  and
- one complete M135/noise/pre-clamp-hull scoring arm.

Use alternating order and the repository timing rule, record warm repetitions
and uncertainty, then scale only by the exact bound counts of calibration
cells, candidate render arms, legacy render arms, and scoring arms.

### Evidence-derived cost contract — [VERIFIED—PREREGISTERED]

The binding contains a hash-bound benchmark artifact plus four further
hash-bound references: workload manifest, runner entrypoint, runner bundle,
and environment manifest. The workload schema `m138-cost-workload/v1`
contains four nonempty unique unit-ID ledgers: calibration cells, candidate
render arms, legacy render arms, and scoring arms. The adjudicator derives each
count as the ledger length; the manifest cannot submit count scalars.
The benchmark schema `m138-cost-benchmark/v1` binds the hashes of that workload,
runner, bundle, and environment; records both `candidate-first` and
`legacy-first` orders; and carries at least two finite positive warm samples
for each of:

- `calibration_cell_seconds`;
- `candidate_render_arm_seconds`;
- `legacy_render_arm_seconds`;
- `scoring_arm_seconds`; and
- `contention_multiplier`.

The adjudicator takes each timing median, multiplies it by the corresponding
frozen workload count, sums the first four products for exclusive seconds, and
multiplies by the maximum measured contention multiplier for shared-host
seconds. It verifies any displayed wall-clock totals against those recomputed
values to relative and absolute tolerance `1e-12`. A `BENCHMARKED` status
string has no meaning and is not part of the schema. Null, non-finite,
non-positive, incomplete, unhashed, or arithmetically inconsistent
measurements return `INSTRUMENT_INVALID`.

Until all five references and derived totals are bound,
`cost.binding_state` remains `UNBOUND`, no wall-clock estimate is claimed, and
the adjudicator refuses campaign results.

## Could not determine — [VERIFIED]

1. The smallest RMS improvement the program intends Phase 1 to claim. No
   external requirement was available, so `delta_required` remains unbound.
2. The power at `64` sites or the required site count. No qualifying four-burst
   physical pilot exists in the reviewed inputs.
3. Whether M135's physical path, positive improvement plant, and comparison
   checker will commission.
4. Exact development and holdout capture/site ledgers.
5. Campaign wall-clock and contention. The only existing timing omitted the
   work this gate now requires.
6. Whether any global `tau` passes. No campaign was run.

## Source-anchor checklist

The reference checker verifies these ranges against pinned bytes:

- `f5658e5d:docs/proposals/2026-09-phase1-design.md:280-286`
- `experiments/PHASE1-DESIGN/measure.py:29-31`
- `experiments/PHASE1-DESIGN/measure.py:129-141`
- `experiments/PHASE1-DESIGN/measure.py:171-180`
- `experiments/PHASE1-DESIGN/measure.py:235-250`
- `experiments/PHASE1-DESIGN/measure.py:407-422`
- `experiments/PHASE1-DESIGN/measure.py:443-460`
- `experiments/PHASE1-DESIGN/measure.py:568-575`
- `experiments/PHASE1-DESIGN/reference.py:625-633`
- `experiments/PHASE1-DESIGN/reference.py:666-727`
- `experiments/PHASE1-DESIGN/reference.py:1052-1064`
- `experiments/PHASE1-DESIGN/reference.py:1080-1134`
- `experiments/PHASE1-DESIGN/reference.py:1135-1200`
- `crates/strehl-core/src/pyramid.rs:372-384`
- `crates/strehl-core/src/merge.rs:421-427`
- `experiments/M135-detail-instrument/PREREGISTRATION.md:7-12`
- `experiments/M135-detail-instrument/PREREGISTRATION.md:26-53`
- `experiments/M135-detail-instrument/PREREGISTRATION.md:127-149`
- `experiments/M135-detail-instrument/instrument.py:207-260`
- `docs/research/M62-sqrt-n.md:32-45`
- `docs/research/M62-sqrt-n.md:64-70`
- `docs/proposals/2026-09-phase1-design.md:226-230`
- `docs/proposals/2026-09-phase1-design.md:312-316`
- `docs/proposals/2026-09-phase1-design.md:340-350`
- `experiments/PHASE1-DESIGN/PREREGISTRATION.md:167-203`
- `experiments/PHASE1-DESIGN/results/gate.json:1-1`
- `experiments/PHASE1-DESIGN/results/run.json:1-1`
