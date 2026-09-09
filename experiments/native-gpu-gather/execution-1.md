# Native GPU gather — first finite control run

Root authorizes one fresh release compile, then exactly one ignored test:
merge_cmd::tests::native_gpu_gather_controls::independent_gpu_gather_controls.

The independent fixture fixes 18 primary comparisons, 25 literal quantizer operands,
three descriptor destroyers, and the ordinary/observed/placebo CPU hashes.
A wrong phase, coordinate, coverage decision, rounded value or perturbed oracle
must fail; the live destroyers demonstrate that the comparison can reject.

Compile uses the existing bounded builder: 600 wall seconds, 1800 aggregate
child CPU seconds, 8 GiB Job commit, 16 MiB log, two build workers, offline and
locked dependencies. Run uses the existing bounded process: 120 wall seconds,
120 aggregate child CPU seconds, 4 GiB Job commit, 4 MiB log, two Rayon workers.
The device must identify as discrete hardware; initialization failures are
retained. No RAW decode or quality/timing campaign is part of this allocation.

Source is committed first, the build binds source hashes and the executable,
and the runner checks them before and after. All failures and partial receipts
remain. An implementation repair requires a new source revision and fresh
build/run directories; thresholds and the fixed stimulus stay unchanged.
The next decision is actual-consumer integration only after these controls pass.

Build1 stopped before any GPU execution on a Rust json! syntax error in the
failure-report phase expression. Parenthesizing that existing expression is
a syntax-only repair. Build2 uses the same bounds, inputs and criteria; run1
will use its held executable. Original build1 receipts and log are retained.

Build2 exposed two further compile-only test issues: missing Similarity import
and LowerHex unavailable on the current digest return type. Import the existing
type and hex-format individual digest bytes. Build3 and run1 keep every fixed
input/operator/criterion and all bounds; no GPU execution has yet occurred.
