# M194d implementation and author checks

2026-09-07. This records the implementation lane, not the independently owned
quality adjudication. The fixed candidate remains experimental and opt-in.
The production baseline is M194c commit
`04128e041dabc0bdb86c64526cd8155dd0a0fd07`; the prospective design was committed
at `5f55c9ee7dc15d47e04ded53cd11eea929e28fc2` before root released product edits.
No RAW/capture access, source-noise redraw, seed search, parameter sweep,
performance measurement, calibration claim or default promotion occurred here.

## Implemented path and limits

`strehl_core::pyramid::AdmissionMode` and `MergeConfig.admission` add an explicit
choice with `HardFloor` as the default. `BandMerge::add_frame_with_gain` retains
the existing HardFloor `select_weight` call and arithmetic. Its candidate
branch invokes `pedestal_weight(E,F,p)` for every Laplacian coefficient,
including zero excess:

```text
F = gate * beta_k * max(V_k,0)
q = max(E_k-F,0)
w = exp(clamp(p_k * ln(hypot(q/max(F,1),1)/64), -80, 80))
```

E and F have squared-DN units. This is a heuristic normalization, not an
energy standard error, selected-winner confidence or calibrated admission
probability. Finite negative component variances retain the registered
`max(V,0)` behavior; nonfinite variance refuses. No floor seed, measured beta,
noise physics, coefficient denominator or existing power/ramp constant changes.
There is no new selected-reference field or per-frame image retention.

The candidate accepts only SoftPower, finite positive gate/exponent/ramp,
exponent at most8, significance0, mean base and fallback, mean_coarse0, and
InputRange or Unclamped hull. `BandMerge::new` refuses other combinations.
`pedestal_weight` rejects invalid raw E/F/p before the max could hide NaN.
`assert_pedestal_accumulators_finite` checks num/den/usum after fold/absorb and
again at finish; resolved coefficients and reconstruction are checked before
the final hull. Mixed-admission absorb refuses. The cap makes a weight finite,
but does not make weight-times-coefficient finite: finite u16-range component
samples can deliberately trigger the explicit refusal. These checks add scans,
so unchanged asymptotic retained storage is not a performance or M12 claim.

The CLI's shared `run_pyramid_prepared` body and actual TIFF writer remain the
consumer. Candidate diagnostic text says `weight fallback`: zero denominator
does not count positive equal-weight averaging. The old diagnostic text is
retained for HardFloor. `known-scene-benchmark.rs` adds optional admission to
the existing plan and rendering wrappers, preserving the original M194b
entry/schema. The new child test is
`merge_cmd::known_scene_benchmark::band_admission_benchmark::m194d_known_scene_consumer`.
It requires exact `STREHL_M194D_ADMISSION=hard-floor|floor-pedestal-v1`, uses
new M194d plan/receipt schemas and records the resolved mode/formula. Original
M194b strict source, geometry, noise and external-plan bindings remain active.
The white-floor diagnostic is excluded from the new entry.

This is a test-local trusted synthetic-input consumer, not a general output
geometry/authenticity adapter. Actual camera decoding, alignment and optics
calibration are outside these software plants.

## Author controls and compilation

The commands actually run, with raw logs and command/environment/source records:

| Command / evidence | Result and scope |
|---|---|
| `python -X utf8 experiments/m194d-band-admission/run-author-controls.py --output experiments/m194d-band-admission/author-run-1` | 4 author core tests and1 default/option test passed; visible core and CLI compilation. Preserves the first independent consumer include before its counter observer commission. |
| `python -X utf8 experiments/m194d-band-admission/run-checks.py --output experiments/m194d-band-admission/checks-1` | Core559 passed; CLI138 passed,3 ignored; visible `Compiling strehl-core` and `Compiling strehl-cli`. Clippy exited0 but lacked the separately required `Checking strehl-cli` proof and found3 new test-only modulo style warnings. Its original record remains unchanged. |
| `python -X utf8 experiments/m194d-band-admission/run-checks.py --output experiments/m194d-band-admission/checks-2 --lint-only` | Warm Clippy exited0 with explicit Checking of both core and CLI. The3 equivalent modulo expressions were cleaned; no new owned-code warning remains. Inherited warnings remain; this is not a warning-free repository claim. |
| `python -X utf8 experiments/m194d-band-admission/format-owned.py` | Zero required formatting changes in owned chunks. The report explicitly lists inherited full-file formatting differences; no broad style rewrite. |
| `python -X utf8 experiments/m194d-band-admission/run-author-controls.py --output experiments/m194d-band-admission/author-run-2` | Final4 author core controls and1 actual-default/parser control passed after the equivalent test lint cleanup. Visible new core and CLI compilation; source bytes unchanged across build/run. |
| `python -X utf8 experiments/m194d-band-admission/consumer-run.py build --build-record experiments/m194d-band-admission/author-run-2/versioned-cli-build.json` | Final compatible CLI pin via root's frozen versioned driver. Visible Compiling in the raw build log; original artifact and copied executable hash/size match. Both independent lanes used this pin before root's later image build. |

Author controls test the near-zero singleton discontinuity against actual
BandMerge output, high-signal preference against a mean destroyer, heterogeneous
below-floor equal weighting, fixed allocation capacity through17 frames,
scalar weight arithmetic against f64 arithmetic, and overflow/refusal before
hull. The component floor is arranged from its analytic energy; it cannot
validate sensor calibration. The independent controls deliberately re-choose
stripe geometry, N, floors, amplitudes and invalid states; the author unit
counts above are not independent verification.

The only post-first-run Rust changes were the independent counter observer
on/off/placebo controls and equivalent test modulo lint cleanup. No candidate
formula, data, parameter or production arithmetic was changed after seeing
component output. No scored matrix had run when those edits were made.

Final author core build record SHA-256:
`930f82d7bd19f6dfcc61b4fd0cbf24a54de093971f791aa934f680827200d5e3`.
Final compatible CLI build record SHA-256:
`973a0fb48edb88d52b9a6e1037e0fc75e58c495af1aa0e1e9f8e74ca8f2005b0`.
Each build record contains exact command, environment, times, raw-log hash,
source maps, original Cargo artifact and pinned copy. The latter CLI executable
hash is `8fe0f83b263424338c704388dfe20219a6ae77ac607ad1e12300d5d4a3bbe46c`.
Root later compiled the separately recorded image artifact; the author target
path therefore no longer denotes the old pin, while its copied binary remains
unchanged. This is explicitly retained in the next control's failed preflight.

## Original unselected entry byte control

`original-entry-control.py` invokes the original ignored M194b test name on the
new pinned CLI with no M194d environment key, using the existing plane,
noise-off, full9 bundle and saved M194c candidate2 comparator. It does not
rebuild the original target or count an additional noise repeat.

The first preflight refused because root's final experiment build had replaced
the original compiler artifact path after the independent lanes had finished.
The copied author executable still matched its old record. The same preflight
refusal was reproduced into
`original-entry-preflight-refusal-1/preflight.log` with exact command and script
snapshot. Root authorized use of its fresh `experiment-1/build.json` pin;
no assertion was relaxed and no source was changed to bypass the refusal.

The actual rendering command was:

```text
python -X utf8 experiments/m194d-band-admission/original-entry-control.py --build-record experiments/m194d-band-admission/experiment-1/build.json --build-sha256 7e3567a176e66dd7b8db3ebb16f2e4d2d5774216e0c3530b990df80a15fd7559 --output experiments/m194d-band-admission/original-entry-1
```

**MEASURED:** the original unselected entry produces the exact saved whole TIFF
and decoded pixels:284×212 RGBu16,361851 bytes, whole TIFF SHA-256
`c260d5943de5b7d2127e763541a428c8bdfea7f01cc9284ae308e3520c0eb65f`,
pixel SHA-256 `329755283fe504888822daa94e3d0bebc80909ccc8a76ad319b687222f355a00`.
All9 frames decode once; source and original TIFF bindings remain unchanged.

An extra whole-plan equality assertion failed solely on its correctly changing
build stamp (`444eb759be03-dirty` → `5f55c9ee7dc1-dirty`); every other plan field,
schema and actual output field matched. The original false result remains at
`original-entry-1/result.json`. The separate command
`python -X utf8 experiments/m194d-band-admission/original-entry-recheck.py`
reads the same bound receipt/TIFF, permits exactly those recorded stamp values
and no other difference, and passes. It performs no render. Recheck SHA-256:
`a87bf3ea603a9c2ad13901913ea97ff3366e62c3c66316aa27afc3e9b9031c54`.
This was an author measurement assumption failure, not an output defect.

This one original-entry render plus direct default resolution tests establishes
the observed unselected-default control. Root's40 explicit HardFloor outputs
are a separate matrix control, not40 observations of an unselected option.

## Final product source binding

| Actual compiler input | SHA-256 |
|---|---|
| `crates/strehl-core/src/pyramid.rs` | `848b485271abc48ee496ee69d70a1e01f45074bfbccde7a7ca076ded90f77d9e` |
| `crates/strehl-cli/src/merge_cmd.rs` | `ca829e45c7021c5c5df7b51da85859e3763a9a95d01d302a91ab7cd0687b2dcf` |
| `crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs` | `92febefaaae87849d689ac59390e8c0170a409f5ecf31f3f4102b5288537b5f7` |
| `crates/strehl-cli/src/merge_cmd/band-admission-benchmark.rs` | `d275b189d374117de2f6d5d9aa163417d675adba1820d96f42e9dfe0d322c2c3` |

Complete source/include maps live in the build receipts; the independently owned
includes at freeze are core `89718084f205e087819fb7aa7d8073ca9977d2182fe246e9833e720133d060ae`
and consumer `1942370ba982c6a5bf07e99fd6eda3af28830b63a06dbafa75b24d20fb4248f1`.
The M194c gatefloor source remains unchanged. Production scope is exactly the
four paths above; no Cargo/dependency changes. Diff deletions are replacement
imports, the weight-loop branch, existing adapter wrappers/schema expressions,
the diagnostic text wrapper and nearby formatting; no historical block or
test was removed. The new child is additive. Root owns Git scope and commit.

## Read-only numerical coverage audit after freeze

Source and executed controls cover all three new numerical boundaries: the
weight's E/F/p domain; accumulated num/den/usum after fold/absorb; and resolved
coefficients/reconstruction before hull. Independent faults distinguish finite
product overflow, individually finite partial sums overflowing absorb, explicit
nonfinite accumulator fields, finite-state division overflow, and finite
coefficient collapse overflow. Each has a candidate-specific refusal message.
The independently retained missing-reset failure prevents cached-frame source
inertness from masquerading as spectral evidence.

The numeric contract remains bounded. Candidate asserts/panics do not promise
recoverability of a partially folded in-memory merge. No universal arbitrary-N,
arbitrary-shape, invalid-buffer, externally corrupted hull or allocator-failure
guarantee is made. Zero-band tiny images have no Laplacian admission to evaluate
and use the inherited mean base; the current fixed matrix has3 bands. Very
small positive ramp values can resolve an exponent to zero by underflow and
then refuse at the helper; they are outside the fixed matrix and have not been
separately exercised. Source inspection alone is not new measured coverage.
The scans introduce no arrays but can cost time; no timing claim follows.

The fixed matrix and independent readers, including sparse flat excursions,
remain necessary to decide whether the heuristic is useful. This report makes
no quality finding from continuity, positive weights, hull membership or tests.
