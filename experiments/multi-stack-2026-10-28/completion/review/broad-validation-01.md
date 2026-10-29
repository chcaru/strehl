# Broad debug validation checkpoint01

MEASURED root-scheduled checks in the isolated multi-stack worktree. No numerical source content was changed. lib.rs mtimes were refreshed solely to force fresh compilation/checking; no release build, RAW decode or renderer was run. Complete command stdout/stderr, immediate exit codes and resource receipts are retained in the three named output directories.

| Check | Result | Evidence |
| --- | --- | --- |
| Full core tests | Exit101. Main library710passed,4ignored; sampler1passed. Registered examples6+17+12passed, then signal commissioning14passed/1failed. Later targets were not reached. | outputs/multi-stack/completion/core-full-validation-01 |
| Strict core clippy, all targets | Exit101,56unique error diagnostics:43unchanged remote-main spans,13new completion diagnostics. | outputs/multi-stack/completion/core-strict-clippy-01 |
| Strict CLI clippy, all targets | Exit101,58unique error diagnostics:30unchanged remote-main spans,1inherited enum-size cause,27new completion diagnostics. | outputs/multi-stack/completion/cli-strict-clippy-01 |

The test log contains fresh Compiling strehl-core. Core clippy contains fresh Checking strehl-core. CLI clippy contains fresh Compiling strehl-cli (its build-script package), fresh Checking dependencies and current CLI compiler-message diagnostics; no strict pass is claimed. Structured JSON diagnostics are deduplicated by code/message/normalized primary spans including columns. Multiple distinct diagnostics on one line remain distinct.

## New failing research control

`experiments/multi-stack-2026-10-28/completion/sr/geometry-signal-commission-controls.rs:354`, test `d01_actual_signal_and_independent_noise_commission_the_fixed_geometry_bar`, failed with:

```text
instrument never supports accurate low-DN placement in at least one color: [0, 10, 1]
```

This is a newly registered completion experiment, not an unchanged private-corpus test. The library's710passed tests do not erase this failed positive commissioning requirement. The failed state and fixture should be diagnosed; a threshold relaxation or removing the test would not establish the missing low-signal capability.

## New lint diagnostics requiring scoped cleanup

Locations are those recorded by the actual compiler invocation, before later concurrent author fixes. They are not inferred from filenames alone.

| Source | Recorded line and lint |
| --- | --- |
| crates/strehl-core/src/mosaic.rs | 367: `needless_range_loop`, 673: `needless_range_loop`, 753: `collapsible_if` |
| crates/strehl-core/src/reconstruction-affine.rs | 65: `needless_range_loop` |
| crates/strehl-core/src/reconstruction-registration.rs | 505: `manual_is_multiple_of` |
| crates/strehl-core/src/reconstruction-registration-graph.rs | 304: `needless_range_loop` |
| crates/strehl-core/src/reconstruction.rs | 346: `needless_range_loop`, 364: `needless_range_loop`, 366: `needless_range_loop`, 563: `needless_range_loop` |
| crates/strehl-core/src/reconstruction-mixture-tests.rs | 56: `needless_range_loop`, 72: `manual_contains` |
| crates/strehl-core/src/reconstruction-tests.rs | 310: `useless_vec` |
| crates/strehl-cli/src/session-alpha-output.rs | 106: `chunks_exact_to_as_chunks`, 291: `chunks_exact_to_as_chunks`, 295: `manual_range_contains`, 295: `manual_range_contains` |
| crates/strehl-cli/src/image_out.rs | 1430: `manual_is_multiple_of`, 1430: `manual_is_multiple_of` |
| crates/strehl-cli/src/session-mosaic-tiles.rs | 550: `drop_non_drop` |
| crates/strehl-cli/src/session-reconstruction-consumer.rs | 184: `needless_range_loop`, 680: `needless_range_loop` |
| crates/strehl-cli/src/session-consumer.rs | 494: `collapsible_if`, 547: `collapsible_if` |
| crates/strehl-cli/src/session-mosaic-scale-features.rs | 79: `needless_range_loop`, 88: `needless_range_loop`, 389: `collapsible_if`, 445: `manual_is_multiple_of`, 196: `items_after_test_module` |
| crates/strehl-cli/src/session-mosaic-grid.rs | 120: `too_many_arguments` |
| crates/strehl-cli/src/session-mosaic-native.rs | 328: `type_complexity` |
| crates/strehl-cli/src/session-mosaic-solve.rs | 232: `type_complexity` |
| crates/strehl-cli/src/session-reconstruction-output.rs | 234: `chunks_exact_to_as_chunks` |
| crates/strehl-cli/src/session-focus.rs | 556: `manual_range_contains`, 554: `manual_range_contains` |
| crates/strehl-cli/src/session-reproducibility.rs | 676: `single_range_in_vec_init`, 682: `single_range_in_vec_init` |
| crates/strehl-cli/src/session-mosaic-match.rs | 311: `manual_is_multiple_of` |
| crates/strehl-cli/src/session-reconstruction-plan.rs | 300: `useless_vec`, 322: `useless_vec` |

## Baseline audit

[audit-validation-lints.py](audit-validation-lints.py) compares current diagnostic source text to both the prior multi-stack checkpointef655050 and remote-mainc149e52834fc1c86c2af0fe022713c39fa25f33c. [validation-lint-audit-01.json](validation-lint-audit-01.json) retains exact messages, primary spans, source SHA256, and matching unchanged diff-block locations. Inherited experimental includes are normalized to their actual experiment paths; no excluded-license dependency source was read.

The CLI enum needs causal inspection beyond its changed enclosing span: its actual largest Stack variant remains542lines exactly equal to both baselines, and its second-largest Align variant and complete align_cmd.rs source are unchanged. The added Session is not the size cause identified in this diagnostic. This single lint is therefore inherited, separately from the30exact unchanged CLI spans. All27new CLI diagnostics and13new core diagnostics occur in the new completion implementation or its controls. The strict lint commands remain failed until these are repaired and the requested checks rerun; unchanged inherited diagnostics must remain explicitly disclosed.

Commands actually run through the receipt helper:

```powershell
cargo test --locked -p strehl-core
cargo clippy --locked -p strehl-core --all-targets --no-deps --message-format=json -- -D warnings
cargo clippy --locked -p strehl-cli --all-targets --no-deps --message-format=json -- -D warnings
```
