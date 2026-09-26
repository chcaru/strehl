# Root-owned integration

The author owns only this experiment directory and has neither built nor opened
original RAWs. All calls below are read-only observers. Add these two includes:

```rust
// crates/strehl-core/src/pyramid.rs; same guard as rb_own_guide_diagnostic
#[cfg(feature = "native-correction-variance")]
pub mod real_source_contributions {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/real-source-contributions/core-bridge.rs"));
}

// crates/strehl-cli/src/merge_cmd.rs; same cfg(test)+three-feature guard as
// full_stack_source_prior.
mod real_source_contributions {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/real-source-contributions/observer.rs"));
}
```

In `experiments/full-stack-source-prior/adapter.rs::run_complete`:

1. After `std::fs::create_dir(&config.out_dir)?;`, add:

```rust
let mut real_trace = real_source_contributions::Session::start(
    &config.out_dir, &sizes, count, plan.per_chunk)?;
```

2. In the first pass, after `fields=core::canonical_fields(...)` and its
`sum.add(...)`, add:

```rust
if let Some(trace) = real_trace.as_mut() {
    trace.source(i, &base.merge, &base.fws, &fields, &base.planes)?;
}
```

3. Immediately after `let baseline=pool.install(||base_total.finish(...));`,
and before output writing/drop, add:

```rust
if let Some(trace) = real_trace.take() { trace.finish(&base_total, &baseline)?; }
```

The observer has an explicit on/off switch `STREHL_REAL_SOURCE_TRACE`. It refuses
non488-source, non3134x2088, non122-source-chunk runs when on. Off does not inspect
or write anything. Existing corrected-current route remains the full execution
driver. Bind all `.rs/.py/.md/.json` source/control files in this directory in the
new build manifest. Run `merge_cmd::real_source_contributions::sparse_footprint_controls`
and independent controls first; then exactly one on and one off corrected-current
run, same executable/settings. Each full run is bounded to900 wall seconds,
6000 CPU seconds and12 GiB, using the existing281.609s complete marigold operation
as a resource reference, not a speed claim. Keep complete candidate master/cache
hashes; require byte-identical TIFF and all four merged planes on/off before
interpreting the observer. No source subset or new cost-framework run is needed.

The trace writes beneath the normal run's `output/source-trace`. After the pair:

```powershell
python -I -B -X faulthandler experiments/real-source-contributions/run.py build --out experiments/real-source-contributions/build-1
python -I -B -X faulthandler experiments/real-source-contributions/run.py controls --build experiments/real-source-contributions/build-1 --out experiments/real-source-contributions/controls-1
python -I -B -X faulthandler experiments/real-source-contributions/run.py on --build experiments/real-source-contributions/build-1 --controls experiments/real-source-contributions/controls-1 --out experiments/real-source-contributions/on-1
python -I -B -X faulthandler experiments/real-source-contributions/run.py off --build experiments/real-source-contributions/build-1 --controls experiments/real-source-contributions/controls-1 --out experiments/real-source-contributions/off-1
python -I -B -X faulthandler experiments/real-source-contributions/run.py compare --on experiments/real-source-contributions/on-1 --off experiments/real-source-contributions/off-1 --out experiments/real-source-contributions/comparison-1
python -I -B -X faulthandler experiments/real-source-contributions/analyze.py --trace <on-run>/output/source-trace --out <fresh-analysis-directory>
```

No photographic treatment is implemented or admitted here. The independent
fixed-profile plan decides whether this output identifies an actionable loss.
