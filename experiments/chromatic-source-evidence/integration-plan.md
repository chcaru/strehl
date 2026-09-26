# Root integration and independent controls

Generated-only implementation is ready for an early compile review; tests are
owned by trace_review. No full adapter or RAW route exists.
No shared source has been edited by this lane.

After the currently bound run completes, root may add this one CLI test module
beside the existing experimental modules in `crates/strehl-cli/src/merge_cmd.rs`:

```rust
#[cfg(all(test, feature = "native-direct-planes", feature = "native-correction-variance", feature = "native-gpu-gather"))]
pub(crate) mod chromatic_source_evidence {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/chromatic-source-evidence/implementation.rs"));
}
```

No new core hook is required. Existing cfg-gated core bridges supply ordinary
energy/smoothing, canonical fields, weight construction, accumulation and held
state checks. Do not modify those helpers or weaken an old receipt gate.

Pure independently testable APIs in `operator.rs`:

- `project_co_sited(packed12, wb) -> [Vec<f32>;2]`, slot table `CO_SITED_RGB`.
- `projected_bands`, `joint_energy` and `PairedNoiseEnergy::{new,add_pair,finish}`.
- `AdmissionUnion::{new,add,complete,apply}`; `Mode::{Off,Chromatic,NoChroma}`.

Actual generated consumer API:

- `compare_generated(frames,transforms,crop,noise,cfg,mode)` returns the same
  baseline/candidate plane and final-MHC RGB fields as band-source-agreement.
- `compare_generated_forced(...,mode,forced_source)` supplies a commissioning
  destroyer, never a candidate. `Comparison::forced_source` distinguishes it.
- `gather_packed_verified(...,known4)` and `projected_noise` expose the actual
  phase/rounding/noise route for independent controls.

Evidence retains original hashes, first-four/whole-twelve hashes, projected
signal hashes, sixteen content-derived seeds, every projected noise-draw hash,
E/F/weight hashes, supported/fallback counts and exact second-pass replay.
`verified_probe_draws` must equal16 per source per pass. `admission.supported`
holds only the per-band stack-wide union, not an N-frame image volume.

The independent child module is included at the end of `implementation.rs`:

```rust
mod independent_controls {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/chromatic-source-evidence/independent-controls.rs"));
}
```

Runner source binding must cover all new files, shared CLI/core sources and
reused `phase-packed-rgb`, `rb-own-guide`, `boundary-cfa-wavelet`,
`native-correction-variance`, `cross-scale-source-prior` and `shared-source-field`
helpers. Preserve the existing build/run resource controls, fresh compile
evidence and explicit screen refusals. No performance claim precedes a timed
run; any eventual full sixteen-probe route needs a separate cost decision.

`run.py` reuses the band-source-agreement job helper and inherited source
inventory. It supports `build --out <new-build>` and
`controls --build <retained-build> --out <new-controls>` only. A retained shared
build is accepted only if this lane's runner/design/control files and actual
helpers were already bound before compilation and remain exact. Its saved
successful process, fresh CLI compile line and test-executable hash are checked.
It never retroactively adds bindings or rescans the broad experiment inventory
when accepting a retained build. Shared runners must explicitly bind this
lane's Python/Markdown files; the inherited inventory already includes Rust.

The runner requires frozen independent control files before its own build.
The first compile precedes independent test execution, with no admission until
the controls and their fixed design are reviewed. Root runs all
compilation/tests; this author has run none.

The agreed filter is `merge_cmd::chromatic_source_evidence::independent_controls::`
with four tests: projection, paired floor, admission union and the eight-case
quality screen. `STREHL_CHROMATIC_SOURCE_EVIDENCE_OUT` names the new output
directory. The runner retains separate quality, positive-exercise and wrong-
source-destroyer decisions; a completed instrument may have failed quality.
The independent fixture copy is explicitly required and bound alongside its
controls and plan. There is no full-image subcommand.
