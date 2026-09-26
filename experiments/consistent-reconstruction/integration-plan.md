# Root integration: generated-only reconstruction

No shared source is changed by this lane. After currently bound runs finish,
root adds one CLI test module beside existing experimental consumers:

```rust
#[cfg(all(test, feature = "native-direct-planes", feature = "native-correction-variance", feature = "native-gpu-gather"))]
pub(crate) mod consistent_reconstruction {
    include!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../experiments/consistent-reconstruction/implementation.rs"));
}
```

No new core hook is expected. Existing donor-consistency and
real-source-contributions core bridges expose canonical coefficients and the
held hull; rb-own-guide exposes actual canonical fields for receipts only.
The real BandWorker performs one fold per source. Nothing reweights or replays
the merge. Exact all-state hashes cover every reached denominator, scaled
numerator, fallback sum, resolved target and input hull.

Source inventory must bind this directory's implementation.rs, operator.rs,
design.md, integration-plan.md, independent-controls.rs, independent-plan.md
and any independent fixture file. Also bind the existing donor-consistency,
real-source-contributions, rb-own-guide, phase-packed-rgb and shared-source-field
helpers and shared CLI/core source via the current include inventory. Root
owns the bounded runner/build, compile evidence and all test execution.

Four expected independent tests under
`merge_cmd::consistent_reconstruction::independent_controls::`:
independent_adjoint_dense_controls, independent_solver_controls,
independent_refusal_controls, independent_quality_screen. The reviewer will
freeze exact screen marker/fields before execution. No test success by itself
authorizes photographs or changes a prior quality decision.

Consumer API: compare_generated(frames, transforms, crop, noise, cfg, Mode),
where Mode is Off or Consistent. Comparison retains canonical/pre-hull images,
final-MHC RGB, per-source coefficients/E/F/weight/gather/noise hashes, target
hashes, before/after accumulator and hull hashes, all per-plane Solve records,
coefficient inconsistency and pre/post-hull deltas. `candidate_valid=false`
means every candidate image is an explicit baseline placeholder for receipt
continuity and MUST NOT be scored as a reconstructed output.
