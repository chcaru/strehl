# Independent review of the signed-black candidate

2026-09-09. Source review and finite test proposal only; no candidate execution or calibration result. The implementation author owns `implementation.rs`; this note does not verify that author's future numerical result.

The proposed extraction change is a defensible opt-in experiment. Keep u16 storage, injected noise coefficients and default behavior unchanged. The completed sensor-transfer result motivates the question but does not identify a gain/beta correction; its paper block failed the motion premise. A synthetic result below tests the operator, not the camera calibration.

## Actual consumers and limits

Source-read `merge_cmd.rs::extract_planes`, `load_frame`, `BandWorker::fold`, `Merged::{value,green_mean}` and `write_merged`; `align_cmd.rs::{warp_frame_in_place_plane,warp_frame_in_place_fullres}`; `noise.rs::{PlaneNoise::variance,NoiseModel::green_luma_sigma}`; the accumulation/final InputRange portions of `pyramid.rs`; and the production demosaic stencils. Consulted SYNTHESIS introduction and architecture decisions, the new charter and existing `production-truth.rs` / `known-scene-benchmark.rs` entry points. The charter records the prior-art query; this review does not repeat it or claim global absence.

* Extraction currently computes `max(f32(raw)-black,0)`. This is the rectification seam the option must actually reach. Count negative extracted samples and retain a negative minimum in the signed run; counting only negative source expectations cannot prove traversal.
* The full-resolution gather subtracts black without a zero clamp, applies WB/MHC/resampling, restores the pedestal, then rounds/clamps to the u16 container. Below-black values remain representable. The plane gather interpolates pedestal-bearing u16 values. Both have container clipping and uncovered-site black fill; a sign-preserving extraction cannot recover information already lost there. Initial fixtures can use no-map; a later placed-path claim needs its own visited consumer evidence.
* `PlaneNoise::variance` already clamps its signal operand to zero while retaining the read-noise floor. Keep that function and the existing green sigma-then-square path unchanged. Signed green luma changes the **data-dependent variance operand** compared with averaging separately clipped greens; unchanged coefficients do not mean unchanged per-pixel variance or gate decisions.
* Pyramid Laplacians, accumulation and InputRange can carry signed values. InputRange is a bound from actual inputs, not an implicit zero floor. Weight/excess/variance clamps have different purposes and must remain.
* The existing writer boundary is `Merged::value` (individual CFA clamp) and `green_mean` (clamp after averaging two greens). Preserve their distinct semantics. Retain collapsed signed f32 as well as the existing native-linear writer output: final clipping can hide a negative result, and lower output variance alone can reward lost detail.

## Small discriminating comparison

Prefer the existing decoded-frame `PyramidFrameSource` / `BandWorker` / native writer route over the M194 manifest machinery. M194's path fixture is explicitly not a physical defocus-quality oracle; do not reinterpret its commissioning outcome as one. Compile the minimal seam and one smoke case before expanding the fixture code. Proposed maximum is six fixed cases, each baseline plus signed: twelve consumer calls, not a parameter sweep. Implementation must freeze geometry, spatial recipe, masks and accepted tolerances before these calls.

1. Zero flat, five spatially constant frame offsets `[-4,-2,0,2,4]` DN. With mean base/fallback and zero Laplacians, the independently derived collapsed means are baseline **1.2 DN**, signed **0 DN**. Require actual negative signed inputs and finite values. A surviving early zero clamp must fail the signed expectation.
2. Dim flat with true value **1 DN**, same offsets. Independently derived means are baseline **1.8 DN**, signed **1 DN**. This rejects a change that merely forces the black output to zero. These two cases isolate rectification; spatially constant offsets are not independent sensor noise or a gate-selection test.
3. Noiseless dim-1 flat. Baseline and signed collapsed bits and complete TIFF bytes agree; the literal mean is one. No output rescaling or general offset correction can hide here.
4. Entirely nonnegative structured/depth fixture. Baseline/signed collapsed bits and TIFF bytes agree. Record texture amplitude and the planted depth transition so a constant null cannot masquerade as coverage.
5. Zero flat with a fixed spatially varying, temporally balanced perturbation. Record bias, RMSE and negative population in actual extracted and collapsed values plus the final output. Do not demand the variance of an unclipped input equal the final clipped writer's variance.
6. Low-signal textured/depth fixture with the same fixed perturbation family. Score against the independently planted target in disjoint flat, textured interior and depth-boundary masks. Report bias, RMSE and maximum absolute error in native DN; a blur or all-zero output can reduce noise and must fail the known texture/depth comparison. No gradient-energy quality score, adaptive mask or after-the-fact tolerance.

For cases 5/6 a seed and a formula are part of the fixture, not a fitted calibration. A nonnegative/noiseless target should be scored at the corresponding final writer convention; keep CFA and demosaiced comparisons distinct. Report any worse fidelity rather than rescue it by changing gain, beta, registration or crop. A reduction in flat bias with worse texture/depth error supports only the narrower claim.

No new runner, registry, source archive, corpus traversal or decoder is needed. Root releases execution and owns its cost record. This lane will check the concrete fixture/flag source and report discrepancies before treating this proposal as implemented coverage.

## Concrete source handoff

Read the initial 5,700-byte `implementation.rs` and the feature/extraction diff: no blocker to the early two-process smoke compile. Its two cases per process reach three actual folds each, including consumed negative samples and signed -8 through `finish`; `Merged` then returns zero. Its positive8 companion checks unchanged numeric transport. The saved `collapsed_constant` is the expected value backed by an assertion, not a separately computed observation; TIFF creation alone is not a paired byte-equality result. Future comparison receipts should retain actual summaries/hashes.

For the structured comparison, adopt two fixed best-focus indices1/3 with per-surface box-blur radius `abs(frame-best)`. Blur each latent surface before the fixed left/right composite. Freeze edge extension, quantization and perturbations. Assert that the source contains distinct best frames and nonzero blur error. This is a two-surface software fixture, not a physical occlusion simulator. The twelve-call ceiling must explicitly include or exclude the four consumer calls in the initial two-process smoke; root owns that allocation. No result is inferred from source review.
