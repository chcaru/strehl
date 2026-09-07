# M194d implementation plan: a continuous floor-to-selection transition

2026-09-07. **DESIGN ONLY; implementation and builds await root review.**
Baseline: M194c commit `04128e041dabc0bdb86c64526cd8155dd0a0fd07`.
This is one bounded experiment using the existing known-scene input matrix,
not the withdrawn Phase-1 gate, a calibration result, or a default promotion.

## Prior art and the question that remains

The mechanical command actually run was:

```text
python -X utf8 experiments/ORCH-drift-check/prior_art.py band admission merge variance winner
python -X utf8 experiments/ORCH-drift-check/prior_art.py pedestal weight floor singleton continuity
```

The design read current `SYNTHESIS.md` sections3.1–3.4.2 and the later
floor/selection records, including facts1803,1805,1806,1809,1844,1939,1940.
Its historical architecture table is not a description of every current
consumer: this experiment follows the actual Pyramid code and M194c receipt.
The no-materialization and injected-noise requirements remain binding.

| Source read | Consequence for this experiment |
|---|---|
| `docs/research/ORCH-veiling.md`, `BUILD-HULL.md` | Smooth physical veiling can be inside the input hull; a zero post-clamp violation count is not truth or an occlusion guarantee. M194d has no new occlusion scene. |
| `BUILD-BLEND.md` | The actual component already exists. Its noise and cross-build corrections prohibit inheriting the headline as proof of this operator. The old `blend-truth` component harness is not the production orchestration used here. |
| `V-DILUTE.md` | The measured deep-stack dilution hypothesis was refuted. Do not rebuild an N-dependent selector to fix that alleged defect. Its later interpretation is also constrained by band and width qualification. |
| `V-LINEAR-BANDS.md`, `V-SOFTCHECK-bandqual.md` | An unqualified band, same-band winner selection, gain changes, and develop paths can manufacture a detail result. Use the frozen independently constructed targets, not a new power maximum. |
| `BUILD-TRIAGE.md`, `V-bestframe.md` | Best-source and detail comparisons have documented noise, gain, resampling, and coverage confounds. Frame4 is fixed by the producer's focus geometry, not selected from candidate output. |
| `M70-through-focus-spectrum.md` | A spectral count is not a free harvest or a portable flat-region target; this does not reopen deconvolution or tune an N-eff objective. |
| `M111-waxy-blobs.md` | Its regularizer, excessive-admission, and downstream explanations were refuted. Do not present the present discontinuity as an attribution of all historical waxy blobs. |
| `BUILD-PYRNOISE.md`, `BUILD-PYRNOISE-ADJUDICATION.md`, `experiments/BUILD-PYRNOISE/admission.py` | That `admission` function tests a noise ROI, not frame weights. Its temporal/spatial ratio omitted photometric drift and over-rejected. M194d uses repeated identical scenes for temporal noise; it does not reuse that predicate. |
| `BUILD-SOFTGATE.md`, `experiments/BUILD-SOFTGATE/pyramid-softgate.patch` | The Gaussian winner-relative proposal requires another pass, retains exactly-zero below-floor weights, and has withdrawn width-confounded quality evidence. The report's wiring headline is not authority: later SYNTHESIS records say valid kernels remained inert. Current source is decisive. |
| `M69-focus-noise-sd.md`, `experiments/PHASE1-DESIGN/{reference,measure}.py` | A response uncertainty is not the sensor sigma. The old candidate chooses raw-energy maxima, uses plug-in energy variances, and its Python path does not consume the Rust merge. Neither its calibration nor width gate transfers here. |
| `experiments/M138-w1-gate-audit/corrected-gate-preregistration.md` and `corrected-gate-contract.json` | The contract is schema4, `DRAFT_PENDING_THIRD_INDEPENDENT_REVIEW`; it cannot license output or Phase-1 inference. Width is diagnostic; calibrated winner-conditioned distributions and output evidence are required for that separate gate. |
| `docs/STATUS.md` section2.9.44; roadmap's M143 note | M143 rejected the inherited0.90 threshold and evidence-by-assertion. Its threshold was not shown tuned to survivors; the documented problem was unsupported transfer between different estimands. No standalone M143 report was found: a scoped search found the references in STATUS and the roadmap only. |
| `M194-production-truth.md`, `M194b-known-scene.md`, `M194c-probe-layout.md` | The actual production seam and fixed inputs already exist. The accepted layout repair costs2.538% green flat temporal variance and has a sparse adverse movement104.447 post-WB DN. Keep its probe sequence and every repeat unchanged. |

The second search additionally returned M13, M4, M76c, M-PHASE0-VEIL2 and
M97c. Their title-level matches concern focus windows, physical fixed-pattern
noise, residual floor, base-band pedestal, and clipping. They are not evidence
for the weight transition proposed here; no result from them is imported.

**Source finding, not a new measurement:**
`pyramid.rs::select_weight` returns0 on `excess <= 0` before the optional
significance `hypot`. `BandMerge::finish` uses the all-frame mean only when
the total selected weight is zero. Thus one arbitrarily small positive weight
can replace the mean with one frame. The existing significance option's own
documentation identifies this singleton case as unreachable by its weighting
change. The saved Gaussian patch retains the same early rejection.

This leaves a defensible, narrower experiment: remove that discontinuity by
giving every frame a positive baseline weight. It does not require claiming
the present operator is the cause of every M194c excursion. The component and
delivered-output checks must establish those separate statements.

## The single proposed operator

For frame i and Laplacian band k, retain the current production quantities:

```text
E = smooth5(L_luma²)                   [DN²]
V = existing Gaussian variance level   [DN²]
beta = existing per-frame transfer      [dimensionless]
F = gate * beta * max(V,0)              [DN²]
q = max(E-F,0)                         [DN²]
a = q / max(F,1 DN²)                   [dimensionless]
p = existing exponent_at(k,bands)
r = hypot(a,1) / 64
w = exp(clamp(p * ln(r), -80, 80))
```

Apply this weight to **every** frame, including q=0. Its numerator, denominator,
unweighted sums, base mean, hull, collapse and writer are the existing ones.
The constant1 is a **fixed heuristic baseline on the current floor scale**;
it is not a confidence level, measured degree of freedom or calibrated optimum.
64 is the existing dynamic-range reference. There is one candidate and no
multiplier, gate, exponent, epsilon or probe-seed sweep.

At q=0 all frames receive the same `64^-p` weight, irrespective of their F.
Ignoring floating-point rounding, their coefficient is the arithmetic mean.
For a small a, the relative weight is
`(1+a²)^(p/2) = 1 + p*a²/2 + O(a⁴)`: a lone near-crossing frame no longer
receives the whole coefficient. For large a, candidate/legacy weight tends to
`(1+a^-2)^(p/2)`, hence1. The high-signal preference asymptote is retained
until the existing numeric cap binds. The candidate does **not** hard-reject
a frame; the high-contrast control must show strong relative suppression of
losers, not claim an exact zero.

All weights still depend on the same noisy image being averaged. Positivity,
continuity, or a large Kish participation count does not prove independent
averaging, unbiased output, or sigma/sqrt(N). A low but nonzero contribution
from many blurred frames may dilute real detail; inverse floor normalization
may still favor a particular warp/noise level. These are central falsifiers.

This changes no noise physics. In particular, an A1 energy-gap test would need
sigma_E in DN²: `Var(E)` has DN⁴ units, with both a pure-noise term and a
signal–noise cross term. The old plug-in form
`(2*F0² + 4*F0*q)/nu` illustrates those dimensions, but correlations and
winner conditioning prevent treating it as calibrated. A coefficient sigma
in DN, or a zero-signal constant alone, cannot substitute. M194d does not
form that statistic, call NU_SMOOTH, perform Anscombe stabilization, or infer
an admission probability from beta.

For the fixed three-band consumer, the exponent schedule remains approximately
3.92,2.8,2; the library cap remains8. The candidate uses the log/clamp form
also at p=1 and2 to avoid an unchecked squared-ratio overflow. HardFloor keeps
the current fast paths byte-for-byte. `hypot` avoids squaring a huge ratio.
`exp(-80)` and `exp(80)` are finite positive f32 values; at q=0 and p<=8 the
baseline weight is at least64^-8, well above the subnormal range. This is a
weight bound, **not** a proof against every possible numerator overflow at
arbitrary frame counts. At the cap, `exp(80)*10000 DN` already exceeds f32's
maximum. The experiment keeps the fixed law/cap and **refuses unsupported
numeric accumulation**, rather than claiming all finite inputs are safe or
silently introducing a lower, potentially blur-producing weight ceiling.
For FloorPedestalV1 only, check the weighted numerator, denominator and
unweighted sums after each frame fold and after each absorb; require finite
resolved coefficients and finite collapsed pixels before the final hull
projection. Failure is an explicit error/panic before an image can be written.
These scans add no retained arrays and are not claimed free in time. Inputs
that overflow this guarded path are outside its supported numeric range.
Check the complete registered workload and the separately fixed extreme
component. Invalid candidate configuration or nonfinite energy/floor inputs
also fail explicitly rather than emitting a misleading finite weight.

## Proposed compiler inputs and explicit option

No source changes have been made under this plan. On approval, own only the
following product/test integration (root may narrow it further):

1. `crates/strehl-core/src/pyramid.rs`: add
   `AdmissionMode::{HardFloor, FloorPedestalV1}` and
   `MergeConfig.admission`, defaulting to HardFloor. Introduce private
   `pedestal_weight` and dispatch inside the existing
   `BandMerge::add_frame_with_gain` weight loop. Do not copy or change the
   accumulator, reduction or reconstruction. Candidate mode requires SoftPower,
   positive finite gate/exponent, significance_scale0, BaseBand::Mean,
   Fallback::Mean and mean_coarse0; Hull::InputRange and Hull::Unclamped are
   supported, while PerLevel is refused in this bounded revision so a partial
   clamp cannot conceal an intermediate numeric failure. Reject incompatible
   modes rather than inventing interactions. `absorb`
   must reject mixing admission modes rather than reducing incompatible sums.
2. `crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs`: factor only the
   private test-local configuration/plan/render entry as needed to share its
   strict manifest loader, frame source and production call. The original
   `m194b_known_scene_consumer` keeps its entry, environment and v1 receipt
   structure. New candidate receipts must not masquerade as unchanged v1.
3. `crates/strehl-cli/src/merge_cmd/band-admission-benchmark.rs`: new cfg(test)
   child nested under `known_scene_benchmark` so it can reuse private helpers.
   Ignored entry:
   `merge_cmd::known_scene_benchmark::band_admission_benchmark::m194d_known_scene_consumer`.
4. `experiments/m194d-band-admission/*-tests.rs`: author and independent
   component/integration test includes, explicitly bound as compiler inputs.
   No external dependency or Cargo feature is required.
5. `crates/strehl-cli/src/merge_cmd.rs`: candidate-only diagnostic wording.
   The existing `averaged_fraction` counts den<=0, which is a zero-weight
   fallback count, not the amount of averaging under positive weights. Keep
   the legacy banner unchanged; describe the candidate value as zero-weight
   fallback and explicitly deny an averaging-fraction interpretation. No new
   statistic, observer, image buffer or arithmetic path is introduced.

The test-local option is required and exact:
`STREHL_M194D_ADMISSION=hard-floor|floor-pedestal-v1`.
Missing/unknown values refuse. There is no shipping CLI option and no changed
default. M194d plan/receipt schemas are `m194d-consumer-plan-v1` and
`m194d-consumer-receipt-v1`; `config.admission` records the actual enum, with
all other resolved settings. `config.admission_formula` is exactly
`hard-floor-v1` for HardFloor or
`floor-pedestal-v1: q=max(E-F,0); w=(hypot(q/max(F,1),1)/64)^p`
for FloorPedestalV1; the registered numeric clamp remains part of that version.
Existing `STREHL_M194B_*` input/control keys remain in the new adapter and the
admission key is an additional render/plan key; the build needs no such key.
A plan made for one mode
cannot render the other, even with identical dimensions and rehashed fields.
Trust remains the test-local external manifest/plan/source digests.

The previous tentative compile-feature suggestion is superseded by this
explicit configuration field. Root owns new versioned Python driver/runner/
scorer adapters. Frozen M194b/M194c scripts and evidence are read-only.
Cargo argv, environment, test entry, source closure, plan/config differences
and the actual compiler artifact/copy hashes must all be bound prospectively.

## Streaming and execution boundary

The actual path remains
`run_pyramid_prepared -> BandWorker::fold -> FrameWorkspace::next_frame ->
BandMerge::add_frame_with_gain -> canonical absorb -> finish -> TIFF writer`.
RAW prologue, registration solving and defect preflight are bypassed only as
already declared by the known-scene seam; the fold, injected model, measured
probe, gather and output are real production consumers.

No reference/winner field, second pass, aligned frame, focus volume or new
image array is required. The only new persistent value is the mode in the
existing per-worker config. Storage remains u16; arithmetic remains f32.
Source/layout tests count retained arrays and unchanged per-frame decode
counts as a structural bound, not an RSS certificate or speed claim.

Root runs the fixed20 cases/40 outputs twice in the new adapter: HardFloor
and FloorPedestalV1. Every HardFloor TIFF must reproduce the corresponding
M194c candidate2 TIFF exactly. Direct tests must also assert that
`MergeConfig::default` and the original M194b `options` resolve HardFloor
before any override. One additional plane/noise-off/full9 run through the
original M194b entry proves that entry is live and retains its TIFF bytes;
the explicitly selected forty-off matrix alone does not prove default behavior.
Every candidate output is then scored; no width
or other proxy may prune an arm. Use the same producer bytes, eight noise
seeds, curved frame4 gauge, Crop, model, WB, targets and ROI. M194c's changes
are accepted inputs to this experiment, not knobs to reverse.

Implementation is warranted only for this bounded falsifiable question.
Failure on truth/noise or failure to retain high-contrast preference rejects
this one candidate; it neither refutes all admission methods nor justifies
another coefficient search inside M194d.
