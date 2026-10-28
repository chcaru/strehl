# Full-flat diagnostic adapter

2026-10-27. Source preparation only; root owns build and execution. The new
`full-adapter.rs` is nested under `merge_cmd::reconstruction_restart::photo_observation`.
It copies the completed native-pixel adapter's source identity, actual rounded
GPU gather/probes, four canonical15-source chunks, held map/CA-on, first-source
WB, exact tone and ordinary MHC/developer path. Only candidate synthesis changes.

Tests: `flat_source30_checkpoint` and `flat60_complete_observation`.
`STREHL_RECONSTRUCTION_PHOTO_CONFIG` points to strict JSON with `schema:1`,
absolute fresh `out_dir` beneath workspace outputs, and
`expected_test_executable_sha256`. The existing four-worker native environment
is required. No registration or old source was edited by this lane.

The frozen restart operator SHA256 is
`2ef0ef4237be81ad3febc06140cd36e1469a9d73f3beee567f2f336fdf790a0b`.
All four planes use its unchanged32-step, restart-after8 reconstruction. This
experiment's brief explicitly permits the last finite iterate as a diagnostic;
the historical operator's admission policy and comments remain untouched.
No baseline replacement occurs for a refused plane. Any nonfinite value,
invalid image, objective increase, or refusal other than iteration-cap stops
before image development. Every scalar/trace and f64 bit pattern is retained.

Before/after extraction and synthesis, the adapter checks complete canonical
finish equality plus coefficient, accumulator/weight and hull hashes. It saves
fresh `canonical-coefficients.f32/.json` and `canonical-input-hull.f32` from this
actual merge. The candidate receives the actual InputRange hull. A one-source
checkpoint requires both canonical and candidate post-hull CFA to equal the
actual gathered source30 tuple, plus ordinary/fixed-writer payload parity.

Full output names are `baseline-master.tiff`, `candidate-master.tiff`, their
`-linear.tiff` siblings and complete signed CFA `-sensor.f32le/.json` files.
Both arms are6932x4620. Baseline decoded RGB16/float pixels must equal the held
complete flat baseline; ICC, descriptions including DisplayBaseline, and
material TIFF tags must also match. Software build provenance is recorded
separately and is not forged to match the historical binary.

Complete status is `COMPLETE60_FINITE_RECONSTRUCTION_DIAGNOSTIC`; checkpoint
status remains `SOURCE30_CHECKPOINT_EXACT`. Receipt always has `admission:false`
and `quality_claim:false`, with all four `solver_results`,
`observer_nonperturbation_exact`, `actual_input_hull_applied`,
`baseline_material_metadata_golden_exact`, `pair_material_metadata_exact`,
source before/after integrity, target-cache bindings and file/pixel hashes.
The source-derived RMS bound is not described as an interval enclosure of
arbitrary f32 error. No old generated quality failure is reversed.

Validation so far: rustfmt parse of the new file only. No Cargo, numerical
solver, original RAW read or photographic render was executed by this agent.
