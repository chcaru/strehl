# Shared SNR guide: root handoff

Source prepared and independently reviewed, not numerically executed by the author. Root owns registration, fresh build, resource limits and execution. No RAW originals were opened by this lane.

## Test registration and invocation

Add this test-only module to `crates/strehl-cli/src/merge_cmd.rs`:

```rust
#[cfg(all(
    test,
    feature = "native-direct-planes",
    feature = "native-correction-variance",
    feature = "native-gpu-gather"
))]
mod insect_color {
    include!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../experiments/raw-quality-2026-10-26/insect-color/implementation.rs"
    ));
}
```

Build the current library tests, not the historical binary test target:

```powershell
cargo test --locked --release -p strehl-cli --lib --no-run --features native-direct-planes,native-correction-variance,native-gpu-gather --jobs 8 --message-format=json-render-diagnostics
```

Capture the native exit immediately and require `Compiling strehl-cli`. Select the emitted library-test executable from Cargo JSON, freeze its bytes, and bind all five local Rust sources plus retained dependencies and current engine source. The exact filter is:

```text
merge_cmd::insect_color::controls::fixed_shared_snr_actual_consumer_screen
```

Pass `--exact --nocapture --test-threads=1`. The root runner must start from its usual cleaned experiment environment. Required settings:

| Variable | Value |
| --- | --- |
| RAYON_NUM_THREADS | 2, or the root's recorded allocation |
| STREHL_PYRAMID_WORKERS | 2 |
| STREHL_ALIGN | 1 |
| STREHL_FULLRES_GATHER | 1 |
| STREHL_DIRECT_PLANES | rounded |
| STREHL_PROBE_GATHER | green |
| STREHL_WARP_WRITEBACK | parallel |
| STREHL_GPU_GATHER | on |
| STREHL_GPU_GATHER_LOG | off |
| STREHL_GPU_SCHEDULE | device |
| STREHL_DEFECT | off |
| STREHL_FINE_SUPPORT | off |
| STREHL_FIX_CA | off |
| STREHL_INSECT_COLOR_OUT | Fresh absent output directory, whose parent exists |

Keep `STREHL_GATE_FLOOR` unset/default, with no floor scale, local placement, directional demosaic, hull/fallback/significance overrides. The synthetic supplied similarities and sentinel-padded original-u16 buffers are created internally; there is no alignment solve, RAW corpus input or capture sidecar.

An exit0 means execution mechanics succeeded. Read `screen.json`: `FLAT_REFUSAL` is an expected scientific negative and terminates before structured fixtures; `SCREEN_COMPLETE` may still carry strict admission=false. The independent noiseless companion cannot replace that flag. Whole generated camera-RGB float32 outputs are saved for all five arms; these are synthetic controls, not photographic masters or improvements. Every claimed future photograph still requires complete native and comparator presentation.

## Actual operator cost and one complete observation

The present generated helper deliberately refuses real paths and dimensions above512. Do not weaken those guards to point it at originals. Only after the fixed screen and root's decision, prepare a separate full adapter with explicit input-order/map/master hashes, observed capture profile, complete crop and fixed source count299. Reuse the same guide arithmetic and paired original-source draws; retain current native Laplacian synthesis, mean terminal, hull and final MHC. Preserve canonical reduction chunk order, complete coverage and input hashes. Full writes must include the entire CFA/linear result and full-resolution developed master using the baseline's fixed display/development transform. Native baseline and full Helicon B remain required references.

**DERIVED cost:** this floor requires16 additional actual GPU gathers per original source:4784 for299 originals, plus normal signal and canonical green-floor work. It also makes48 channel Laplacian transforms per source for those16 draws, followed by three signal-channel transforms and energy/floor filtering. These are current-source buffers; no aligned-frame volume or dense per-source RGB volume is allocated. Runtime is unmeasured. Historical full-wavelet timing is not transferable to this shallower transform.

One fixed original-source checkpoint must execute the identical full-sized floor/guide/fold, reconstruction and writes before root permits the full299 run. Measure source-phase time, finish/write time and process peak commit under the intended CPU/GPU allocation. Project `299 * source_phase_seconds + finish_write_seconds` and add the root's operational margin; compare with the root's declared wall/CPU/commit limits. This checkpoint must not alter the probe count or change the estimator. If it is impractical, stop that full adapter and report the cost; a cheaper propagated floor is a separate, explicitly compared mechanism.

**DERIVED storage lower bound:** the current6896×4596 native crop corresponds to3448×2298 quad pixels. Seven AC levels plus terminal contain10,565,468 scalar sites. For four planes with default SoftPower/mean/input-range settings, current `BandMerge::planning_accumulator_floats` gives633,908,976 bytes and `FrameWorkspace::planning_floats` gives443,762,912 bytes per arm. A baseline-plus-joint full adapter therefore starts above2,155,343,776 bytes from these legacy terms alone. They explicitly omit some actual buffers and are not a peak estimate. Original CFA copies, probe variance, two probe member guide sets, signal/floor/weight arrays, warp scratch, GPU memory and development add material overhead. Measure peak; do not claim that lower bound as practical memory use. Keep only baseline and joint full accumulators, not the five-arm synthetic comparison, and stream one original plus one probe pair at a time.

The synthetic four-band ladder is[5.488,3.92,2.8,2]; seven-band full reaches[8,8,7.6832,5.488,3.92,2.8,2]. This unchanged production schedule is a full-observation risk: the screen does not certify the stronger fine-band selection. Preserve it and disclose the difference rather than secretly softening full weights.

## Preparation checks

Author ran only `rustfmt --edition 2024 --config skip_children=true` followed by the same command with `--check` on guide-fields.rs, implementation.rs, fixtures.rs and controls.rs: both exit0. Independent reviewer separately formatted independent-controls.rs with exit0 and reviewed the final control routing. No compilation, numerical screen, RAW decode or photographic claim occurred in this lane. The root run must record fresh build, hashes, actual environment, worker count, host load, limits and measured outcomes separately.
