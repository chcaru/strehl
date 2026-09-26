# Root integration and execution

Prepared only; no build or original-file job run by this author. Root decides
the harmonic contingency before the full observation. No old experiment file
is changed. Add these two includes with the surrounding experiment hooks:

In `crates/strehl-core/src/pyramid.rs`:

```rust
#[cfg(feature = "native-correction-variance")]
pub mod chip_shared_source_observation_diagnostic {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/chip-shared-source-observation/core-bridge.rs"));
}
```

In `crates/strehl-cli/src/merge_cmd.rs`:

```rust
#[cfg(all(test, feature = "native-direct-planes", feature = "native-correction-variance", feature = "native-gpu-gather"))]
mod chip_shared_source_observation {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/chip-shared-source-observation/implementation.rs"));
}
```

Use the existing Python3.12 runtime, with `-I -B -X faulthandler`, for each
sequential command below. All output directories must be new.

```text
experiments/chip-shared-source-observation/run.py build --out experiments/chip-shared-source-observation/build-1
experiments/chip-shared-source-observation/run.py controls --build experiments/chip-shared-source-observation/build-1 --out experiments/chip-shared-source-observation/controls-1
experiments/chip-shared-source-observation/run.py full --build experiments/chip-shared-source-observation/build-1 --controls experiments/chip-shared-source-observation/controls-1 --execute-approved-observation --out experiments/chip-shared-source-observation/run-1
experiments/chip-shared-source-observation/run.py views --run experiments/chip-shared-source-observation/run-1 --out experiments/chip-shared-source-observation/views-1
```

The three capacity controls and two unchanged historical controls must complete.
The latter screen stays rejected; if current numeric consumers change its
historical JSON, the runner preserves both complete screens and differing paths
and stops for root review. The capacity copy audit is separate from that test.

Full execution uses all299 frames and the exact held production recipe, with
32GiB/1800seconds process limits. Whole baseline RGB16/ICC identity, a literal
pinned baseline rewrite, matching pass1/pass2 gathers and all four cache-plane
hashes are enforced. Review the complete outputs and all25 fixed native pairs;
the prior generated harm cannot be removed by a favorable chip observation.
