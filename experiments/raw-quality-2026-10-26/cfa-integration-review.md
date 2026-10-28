# Independent direct-CFA integration source review

2026-10-26. Source-only independent review; no Cargo or numerical jobs were run while the full299-source baseline was active. This does not validate photographic benefit, noise calibration, speed, current compile success or exact disabled replay.

## Blocking findings in the reviewed snapshot

1. **Alignment aliases silently bypass the candidate.** `direct_cfa::preflight` rejects only literal STREHL_ALIGN=0. `align_cmd::align_enabled` additionally disables on trimmed case-insensitive off/false/no. Those values pass preflight, then `alignment_for_observed` returnsNone and `load_frame_impl_observed` never calls the sampler. Use the existing align_enabled predicate; do not duplicate its parser.
2. **Enabled environment does not prove a resolved map.** `load_or_solve_observed` deliberately returnsNone for a named tilted subject. Require resolved alignmentSome before announcing/running the direct candidate, and check the effective map kernel, not merely the requested CLI resampler. Direct warp rejects non-CatmullRom only when the first warp is reached. Prefer a clear refusal before source processing.
3. **Crop support requires the composed candidate geometry.** Existing cover_scale tests only base similarity corners with margin3quad=6native, excluding CFA phase and per-channel CA. Direct4x4 interpolation can reach almost4native pixels from its query, rather than3. Six native margin is often sufficient, but the source phase displacement and CA can use the remainder. Validate all placed sources and four phase pulls over the delivered crop with a conservative4native active-boundary envelope, or count actual missing support inside the analysis crop and refuse it. Sampling just the four corners with sample_checked is not a universal proof: exact-zero taps permit integer boundary corners that can conceal unsupported adjacent fractional sites. Changing the photograph's crop to hide support failures would break the matched comparison and must be explicit.

Findings1/2 are candidate-activation blockers; finding3 is a candidate border/support acceptance requirement. All were sent immediately to root. They do not require changing the shared legacy baseline path.

## Source-consistent parts

- Coordinates are active-area native pixel centers. The integration evaluates the existing centered quad pull at px+dx/2,py+dy/2, then doubles to native coordinates. This agrees with the baseline fullres path's site offsets and center convention.
- CA composition uses the same OpticalProfile::compose(ca,channel,t) before applying the pull. It applies in source coordinates, preserving the existing ordering; no second resample is introduced.
- R lattice x/2,y/2 and B lattice(x-1)/2,(y-1)/2 map to their measured phases. Green u=(x+y-1)/2,v=(x-y-1)/2 and inverse x=u+v+1,y=u-v correctly include both original green phases. Negative v is valid; physical bounds are checked after inverse mapping. The core view uses active_x/active_y only for storage indexing, not CFA parity.
- ActiveCfa validates storage extents and checked indexing. Padding is excluded. Its extent bound leaves room for signed lattice arithmetic. The integration's even active extent matches the existing whole-quad convention.
- The one source clone remains u16 and immutable while all four sinks update frame.data. In particular, G2 cannot consume already-warped G1. This is one original-frame copy, not an aligned-frame volume.
- GREEN_ONLY skips R/B writes but uses the same two green samples, original clone, gains, pull and sink. `gatefloor::Probe::run_gather_impl` follows warp_probe_greens_in_place into the same branch, then extracts both greens and builds their average. The probe's pre-warp sigma-squared/2 denominator remains a reference normalization; actual postwarp green covariance enters its measured numerator. No private new sensor-noise model is introduced.
- When direct mode is absent/off, preflight returns immediately and the new branch does not touch pixel arithmetic. This supports an exact-off hypothesis, but only an executed same-build replay establishes exact equality.
- Feature-absent on and invalid direct values are rejected. Active GPU, temporal, spatial-floor, direct-plane and local-placement settings are refused by preflight; research lens pull/test CA override is refused at the dispatch. A public experiment should also bind the full environment and explicitly show measured gatefloor enabled.

## Minimum meaningful execution checks for root

Use the actual fullres routing and writeback, not only ActiveCfa unit tests. Retain a nonzero active-buffer origin and colored padding. An arbitrary nonperiodic u16 fixture at integer identity should preserve all measured phase values after sink; fractional translation plus rotation/nonunit scale should match an independently enumerated source stencil and literal pull. Give G1/G2 deliberately different patterns so in-place contamination is exposed. Compare true GREEN_ONLY green outputs and beta readout against the same source under the full-output dispatch. An identity-only image cannot validate fractional support or the physical site conversion.

Exercise every alignment-off alias, a no-map/tilted refusal, feature-disabled on, incompatible kernel/map and one CA-expanded boundary foil. Wrong phase and wrong pull sign must fail. A suitable support-positive uses an interior crop; a boundary-negative must be refused before publishing a photo. Keep integer measured-boundary support valid in the core sampler while the production conservative envelope may intentionally be stricter.

Run no-feature baseline and new-feature direct-off with identical full-stack inputs/map/resolved development; inspect decoded RGB16/ICC exactness and disclose container-stamp differences separately. Then direct-on can proceed through the same complete299-source workflow. All sharpness/color claims still need flat-first and structural falsifiers plus complete independent photographic review; sparse red/blue interpolation may lose genuine achromatic high frequencies that MHC borrowed from green. The source review cannot waive that risk.

## Reviewed identities

The files were actively being edited; hashes below identify this review snapshot, not a frozen final implementation. Recheck the blocking symbols after root repairs them.

| File | SHA256 |
| --- | --- |
| `crates/strehl-cli/src/direct-cfa-gather.rs` | `dc6005a1cb918aad35454fad194b3a60c4662dc0473be4c4277b8ff0522ff819` |
| `crates/strehl-cli/src/align_cmd.rs` | `e76707ba8dbcaf922b079d80d82920d8211639f62375b8c30b8a9e0fe62fc56a` |
| `crates/strehl-cli/src/merge_cmd.rs` | `041d9924bd9c721f265412a0b1ae784d400b0fbcc4a7acb05e53ca7d0770e8db` |
| `crates/strehl-core/src/cfa-lattice.rs` | `d94cbebcf5c4654a2ec7c4fe9f417333d8e468fc7ae846eeadc43bfd3bda9440` |

## Recheck and executable integration controls

2026-10-26. **VERIFIED by source inspection:** the three blocking requirements above have been addressed in the current experiment branch. `preflight` now uses `align_enabled()` for the complete existing alias behavior. The prepared merge invokes `validate_domain` before buffer work; this requires a resolved map, Catmull-Rom kernel, matching source count and a placed transform for every frame. It checks all four phase offsets and the composed per-channel CA transform at the delivered rectangle corners, using a conservative four-native-pixel envelope. Exact integer corner samples therefore cannot hide a fractional support gap elsewhere on that affine edge. This is source verification, not execution of the environment aliases or the metadata lookup.

**PREPARED / UNEXECUTED by the independent reviewer:** `cfa-integration-controls.rs` is registered as `align_cmd::cfa_integration_tests`. The root schedules compilation and execution. It constructs a generated 96-by-80-native-sensel `Frame`, active origin `(5,3)`, stride113, buffer height91, phase-colored large padding, black512, white16383, WB `[2,1,4,NaN]`, and nonperiodic distinct CFA-phase readings including below-black values. It does not decode a file, alter a capture, mutate the process environment, or claim calibrated noise/photographic benefit.

The three tests exercise the actual `direct_cfa::warp` and `writeback_fullres_site` together:

1. Integer identity must preserve every original u16 sample and padding bit, cover every phase, and deliver more than500 negative black-subtracted values before the sink. This catches clipping to black and treating buffer origin as active CFA parity.
2. A fractional centered similarity with rotation, nonunit scale and translation plus injected nonzero red/blue CA must match an independent f64 oracle enumerating physical source sensels with a continuous Keys basis. Every sample's coverage and pre-sink DN are checked, allowing0.05DN for f32 arithmetic; integer writeback allows1DN at a half-DN rounding boundary. Actual GREEN_ONLY greens must equal the full-path greens exactly while R/B stay unchanged. Distinct G1/G2 inputs expose in-place source contamination. Reversed translation and omitted phase are required to fail by more than100DN at more than900 interior locations each, so identity or a repeated texture cannot satisfy the control accidentally.
3. The actual domain guard must accept an interior identity crop and reject no map, wrong kernel, count mismatch, unplaced frame, and unsupported boundary. An injected expanded red CA profile makes an actual warp lose red support at the accepted base corner; an equivalent expanded map must fail the actual support guard. **Limitation:** this is not execution of the guard's file-to-profile CA lookup branch. That branch and its composition remain source-reviewed; no helper was extracted solely to enlarge tests for a quality-rejected sampler.

Suggested root execution, with `STREHL_FIX_CA` unset/off and `STREHL_WARP_WRITEBACK` unset/serial/parallel in the launching process:

```powershell
cargo test --locked -p strehl-cli --bin strehl --features direct-cfa-gather cfa_integration_tests -- --nocapture --test-threads=1
$integrationExit = $LASTEXITCODE
if ($integrationExit -ne 0) { throw "CFA integration controls failed: $integrationExit" }
```

The tests never set environment variables and therefore add no environment-mutation races. The scheduler must still bind the clean process environment because production writeback selection and domain CA resolution read it. The independent reviewer ran only `rustfmt --edition 2024 experiments/raw-quality-2026-10-26/cfa-integration-controls.rs` successfully; no Cargo jobs were launched. `git diff --check -- experiments/raw-quality-2026-10-26/cfa-integration-controls.rs` failed with exit128 because the sandbox could not access the linked worktree Git common-directory, not because it found a content defect.

The first cubic per-color sampler remains quality-rejected by the independently executed neutral-detail controls reported elsewhere. Correct mechanical integration would not reverse that result. These tests retain a checkable route for a successor. Complete direct-off equality replay, runtime alias/feature-absent refusals, actual gatefloor beta equivalence and any complete candidate photographic gain remain **UNVERIFIED** here. Do not promote this review or these synthetic fixtures as a quality improvement.
