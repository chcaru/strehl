# Frozen source-preparation interface

2026-10-27. No execution. Root registers `merge_cmd::dual_tree_cfa` by including
`implementation.rs`; that file includes `transform.rs`. Root owns child module
registration for `controls.rs` and `full-adapter.rs`.

```rust
Plan::new(width: usize, height: usize) -> Result<Plan> // seven levels
// public fields: input_width, input_height, padded_width, padded_height, levels
forward_phase(input: &[f32], plan: &Plan) -> Result<Coefficients>
inverse_phase(coeff: &Coefficients, plan: &Plan) -> Result<Vec<f32>>
// Coefficients { bands: Vec<ComplexBand>, low: [Vec<f32>; 4] }
// ComplexBand { level, direction, width, height, values: Vec<Complex> }
// level-major directions: LH+, LH-, HL+, HL-, HH+, HH-
// Complex { re: f32, im: f32 }; fields public for independent one-sided foil

Accumulator::new(plan: Plan, cfg: MergeConfig, wb: [f32; 4]) -> Result<Accumulator>
Accumulator::add_source(&mut self, frame: &Frame, source_id: usize,
  known4: &[Vec<f32>], noise: &NoiseModel,
  gather: impl Fn(&Frame) -> Result<Vec<Vec<f32>>>) -> Result<serde_json::Value>
Accumulator::finish(self) -> Result<Finished>
// Finished public fields: planes4, pre_hull_planes4, uniform_planes4,
// mean_planes4: Vec<Vec<f32>>; evidence: serde_json::Value

compare_generated(frames: &[Frame], transforms: &[Similarity], crop: align_cmd::CropRect,
  noise: &NoiseModel, cfg: MergeConfig) -> Result<Comparison>
// Comparison: canonical, candidate, uniform, gathered_source0: Arm;
// pre_hull_planes4, mean_planes4: Vec<Vec<f32>>;
// native_width, native_height: usize; evidence: serde_json::Value
// Arm { planes4: Vec<Vec<f32>>, rgb: Vec<f32> }
camera_rgb(planes4: &[Vec<f32>], width: usize, height: usize,
  levels: Levels, wb: [f32; 4]) -> Result<Vec<f32>>
```

Children can `use super::*` for these APIs and the parent's Frame, Similarity,
Levels, MergeConfig, NoiseModel, Result, serde_json::Value/json imports.
Controls use fresh `STREHL_DUAL_TREE_CFA_CONTROL_OUT`; full adapter owns strict config and
tests `weevil_source149_cost` / `weevil299_complete`.

`add_source` performs exactly sixteen original-u16 probe gathers. The full
adapter supplies its held actual gather closure and original ordinal. Source
noise helpers are reused from `boundary_cfa_wavelet`; the transform is new.
Only one gathered probe is resident. Retain the full coefficient map of pair
A, then transform pair B one phase at a time. The signal energy is analyzed
once before probes and the signal is analyzed again for weighted accumulation
after the floor is available: two signal transforms per phase, explicitly
counted in stage receipts. This avoids simultaneously retaining the full
signal and pair-A maps. No repeated hidden probe gathers.

`uniform_planes4` exercises forward/inverse on the actual gathered spatial
mean before hull. `pre_hull_planes4` preserves the candidate before InputRange;
`planes4` is the delivered hull result. Source149 singleton hull may be exact
while its inverse is approximate: do not conflate these contracts.

Root cost contract: four CPU workers, one complete source plus eight pairs,
300 s wall and 14 GiB peak host commit. CPU full299 is not admitted unless
`299*source_seconds + finish_seconds + 120 <= 1200` and the memory gate passes.
Otherwise stop and allocate the literal GPU port; do not reduce probes.

Source checkpoint: `transform.rs` and `implementation.rs` are prepared and
rustfmt-parsed only. Full adapter supplies the held CPU/remosaic gather
closure; no direct-plane mode is imposed by `add_source`. Generated comparison
uses the same CPU `warp_frame_in_place` plus `extract_planes` path as the full
adapter, checking its output against canonical gathered planes bitwise before
using it for probes. DIRECT_PLANES and GPU_GATHER are off for both arms.
Source receipt keys include `source_index`, `probe_pairs`, `probe_draws`,
`signal_analyses_per_phase`, `probe_analyses_per_phase`, `source_seconds` and
four timed substages. Original ordinals are never renumbered (cost149 uses
source_id149). `Finished.evidence.finish_seconds` includes uniform and
candidate inverse work and the hull.
