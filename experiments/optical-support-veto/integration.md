# Root-owned include and execution instructions

UNEXECUTED. Author changed only this experiment directory. Include these two
modules after root releases shared-source freeze:

In `crates/strehl-core/src/pyramid.rs`, beside the existing diagnostic modules:

```rust
#[cfg(feature = "native-correction-variance")]
pub mod optical_support_veto_diagnostic {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/optical-support-veto/core-bridge.rs"));
}
```

In `crates/strehl-cli/src/merge_cmd.rs`, beside the existing generated modules:

```rust
#[cfg(all(test, feature = "native-correction-variance", feature = "native-gpu-gather", feature = "native-direct-planes"))]
mod optical_support_veto {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/optical-support-veto/implementation.rs"));
}
```

There are no other production edits. The core module only compares held state;
existing diagnostic canonical_fields/add_fields expose the unchanged actual
weight and accumulation code. The identity map exercises the actual rounded GPU
gather and green probe. All-one output equality commissions the adapter against
actual BandWorker, not a second reimplementation. Support sets traverse actual
reduce/expand operations on bit indicators. Exported impulse support permits a
separately authored index/phase/border check.

The two Rust tests are `merge_cmd::optical_support_veto::footprint_and_fallback_mechanics`
and `merge_cmd::optical_support_veto::generated_consumer_screen`. The first checks
impulse coefficient footprints only; all-no-clean fallback/output identity is
checked by the complete consumer plus independent saved-weight review. Always
use `--include-ignored --test-threads=1` with this existing process-global
GPU/developer framework. The generated screen is explicitly ignored during
unconfigured general CLI tests; the bounded runner opts it in.

`prepare.py` calls the independent Python `prepare_controls(prep,pupil,tables)`
immediately after table construction and before CUDA fields are made. Prepare
input support files retain native96x96 bitsets:1 near,2 far,4 unsupported. Truth
and per-component arrays are96x96x3 row-major f32, black-subtracted and normalized
by14848. Consumer RGB arrays are64x64x3 in the same units after actual MHC; their
matching original truth is native `[16:80,16:80]`. Consumer CFA is4x32x32 DN.
Every source/band weight and Q is exported at32x32 and16x16. `operator_support`
in result.json describes input-major uint8 matrices from actual impulse operators.

Root separately runs independent scoring after successful consumer execution.
Successful instrumentation does not admit a photographic replay; even an oracle
generated pass needs a separate scene-relevant decision.
