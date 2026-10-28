# Build2 cleanup failure and bounded cached recovery

Source/evidence review only,2026-10-27. No build, executable, numerical job,
RAW operation or source mutation was run for this review.

## Observed evidence

`outputs/raw-quality-2026-10-27/insect-blur-phase-build-2/process.log`
(SHA054e9d9797738950648117f1c986ee292706c3e371e74a9f63fb9c29d4ad0230)
contains `Compiling strehl-cli`, a test-library `compiler-artifact` with
`fresh:false`, `build-finished` with `success:true`, and Cargo's reported
`Finished ... in 4m 49s`. Its executable is
`target/release/deps/strehl_cli-c448e02639c86feb.exe` with the requested three
features. These establish fresh compilation output, not a clean whole-job run
or an independently usable build-performance measurement.

`process.json` (SHAa47ca58935e5d805578fa9e6c63e12e7b918f8bc915e711119036e962f8fefb6)
records direct exit0 and pipe EOF, but post-exit accounting retained one active
owned process. The900-second wall bound fired; the harness terminated its owned
job and subsequently observed zero active processes. Cleanup errors were empty.
No descendant identity is present, and this review makes no claim about it.

The caller `insect-placement-observer/run.py::observed_run` correctly rejects
`error != None` even with exit0. Its bounded-process helper deliberately waits
for whole-job termination after direct exit/EOF, and correctly records the
wall-bound failure. The normal build wrapper consequently never reached its
executable copy, post-build source verification or success receipt. Do not
retroactively mark build2 successful or retain its interrupted job as a timing
benchmark. No photograph or numerical experiment was run in that build.

## Prospective root recovery

The proposed one clean cached Cargo replay is justified; no further forced
recompilation is required solely to recover this failed cleanup step.

1. Preserve build2 as failed. Bind its invocation, process receipt/log and
   `rust-sources.json` (1416entries, SHAe725e00aeefcd0c4c06325cc17f73eaeee53b7cda91f03f302b573535d03142a).
   Recompute the entire current Rust/Cargo inventory and require the same paths,
   sizes and content hashes, with no added/deleted entries. This review has not
   performed that1416-file verification.
2. Hash/stat the currently emitted target executable before retry. Build2's
   Cargo log records its path, not its SHA at compilation completion: describe
   this as the artifact observed at recovery start, not a historical exit hash.
3. Run the exact recorded `cargo test --locked --offline --release -p strehl-cli
   --lib --no-run --features native-direct-planes,native-correction-variance,native-gpu-gather
   --jobs 4 --message-format=json-render-diagnostics` from the same workspace,
   with the same cleaned environment, `CARGO_INCREMENTAL=0` and
   `CARGO_BUILD_JOBS=4`. Root bounds the new owned job at120seconds. Do not weaken
   the harness's whole-job completion test or ignore another lingering process.
4. Require exit0, no harness/cleanup error, direct exit and EOF, normally
   completed post-exit drain, zero terminal active processes and no termination
   attempt. Require successful Cargo completion and exactly one matching
   strehl_cli test artifact with the same target/features/path. Cached
   `fresh:true` is expected; absence of a new `Compiling` line is intentional in
   this recovery, not new compilation evidence.
5. Recheck the1416 source bindings and the target executable's hash/size against
   recovery-start values. Copy it into the fresh build3 directory, independently
   compare copy bytes/hash, and save a build3 executable binding plus an explicit
   recovery receipt linking the failed build2 evidence and clean replay.

A changed inventory/artifact, unexpected recompile or another failed cleanup
invalidates this narrow recovery; preserve the result for a new root decision.
Do not silently expand its bound, change source/mtimes or adopt different bytes.
Build3 would certify clean cached recovery of the unchanged build2 artifact;
fresh-compilation provenance remains build2. Neither job supplies photographic
quality or numerical-test evidence. The native graph controls, exact observer
map replay and later complete baseline/render parity gates still must run.
