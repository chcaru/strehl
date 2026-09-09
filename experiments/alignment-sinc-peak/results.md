# Sinc peak implementation: not admitted

2026-09-09. **MEASURED:** the fixed radius4/f32/Newton implementation fails its independent analytic controls, including after one compensated-sum arithmetic repair. Status is CONTROL_FAILED. No generated48-row comparison, candidate timing, original RAW ladder or photographic evaluation ran. This does not reject windowed-sinc interpolation as a family or establish that the current production aligner is accurate.

The original sourcee22ba5c15ac6c063fdb57ac401458a255a52c2f9 compiled with a fresh strehl-core build. Its literal test declined a required positive peak, but the first assertion lacked case context. One unchanged-input, context-only repeat at a957c89b067809b1810bdbe8e4e3416fd56723b9 identified kind2 crossed Gaussian, shift(0.1875,-0.3125), outcome(None,10,line-search). This means the bounded refinement declined a known valid positive. The record does not reconstruct its trial coordinates or uniquely establish numerical cancellation as the cause.

One prospective repair at cc7c9ed3ed7351f27f5b3d9b0f89d7ec9c0c6e55 replaced only the normalization and interpolant reductions with Neumaier f32 sums. Kernel, products, optimizer, tolerances, support, inputs and acceptance tests stayed unchanged. The same literal suite then failed at "reflection lost peak": a positive had been accepted, but its x-reflection was declined. That message does not identify its kind/shift. Do not infer that the original crossed-peak failure was fixed or that the repaired suite progressed farther.

Both failed variants and the diagnostic repeat are preserved. All three numerical children terminated normally with testexit101, no process-limit intervention or cleanup error. Their summed childCPU was0.046875s and summed wall0.405s. The three core-only builds took35.672/31.672/32.188wall seconds. These are execution costs, not alignment-speed comparisons. The control suite stopped early, so unvisited positive, ringing and refusal checks are not passes.

## Default path and disposition

All32 existing align::tests:: regressions pass on the freshly built source, covering current matching/refusal, planted fits, global graph placement and resampling. The ordinary public NCC wrappers remain parabolic; only explicit feature-gated diagnostic calls can select sinc. The regression run took0.078wall/0.03125childCPU seconds, bringing the current numerical allocation to0.078125childCPU seconds. This is a scoped library regression result, not a complete native-output byte guarantee or non-feature compile certificate.

Close this implementation and its one-repair allocation. Keep the experimental source and independently chosen controls for the record; do not enable a runtime/default path, run the deferred population, enlarge the support or start an optimizer/precision sweep. A future different proposal would need a distinct reason and explicit allocation. The larger alignment and photographic-quality goals remain unresolved.

Commands run by root:
- python -I -B experiments/alignment-sinc-peak/build.py
- python -I -B experiments/alignment-sinc-peak/run.py
- python -I -B experiments/alignment-sinc-peak/build.py --diagnostic
- build2/core-tests.exe --exact align::sinc_peak_diagnostic::tests::sinc_peak_literal_controls --ignored --nocapture --test-threads=1, through the existing bounded helper; see diagnostic-1/invocation.json
- python -I -B experiments/alignment-sinc-peak/build.py --compensated
- python -I -B experiments/alignment-sinc-peak/run.py --compensated
- build3/core-tests.exe align::tests:: --nocapture --test-threads=1, through the existing bounded helper; see default-regression-1/invocation.json

Actual artifact directories are build-1/build-2/build-3, run-1, diagnostic-1, compensated-1 and default-regression-1. The final held executable is build-3/core-tests.exe, SHA256edcaa1c7c574c396b4fcd5004a72378b4929432743e958945f90b2bd887cfe27. Independent interpretation is in independent-results.md. Scientific and performance bars were not relaxed.
