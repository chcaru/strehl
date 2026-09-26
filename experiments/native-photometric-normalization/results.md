# Native photometric normalization: generated result

**MEASURED — this fixed recipe did not qualify.** Final `controls-3` completed
four tests and seven image cases, with `quality_pass`, `estimator_pass`,
`positive_exercised` and `candidate_qualified` all false. No photographic replay
is admitted. This is the control-author/instrument report; the separate
[independent review](independent-results.md) evaluates the choices and outcome.

The tested change ports the existing fixed-reference, eroded low-detail mask,
`Flux` and gain-only `PhotometricMap` into the actual native gather/merge path.
It scales CFA samples and luma by the estimated gain, and existing injected
variance by gain squared, retaining beta. It adds no spatial-drift detector,
offset, geometric exposure law or fitted noise model. M91/M99/M125 applicability
limits remain binding; this generated operator test cannot calibrate the sensor
or establish physical brightness drift in photographs.

All five noisy image cases had **zero eligible mask sites**, reported
`UNAVAILABLE`, and applied unity gains. The noiseless Texture estimator twins
were also unavailable. The required noisy Texture positive therefore never
exercised a correction or improved the image. The left-only illumination case
also stayed unchanged: its no-harm result supplies no evidence that an active
scalar correction can safely handle spatially varying illumination.

BroadDefocus alone had usable support: 2,410 sites. Its no-drift false gain was
0.03759%, inside the fixed 0.2% discriminator; the scaled twin's gain error was
0.04520%, also inside that bar. Nevertheless, no-drift flat-surround RGB RMSE
rose from **0.0000297137 to 0.000108708**, failing preservation. These are small
absolute normalized linear errors, not a demonstrated visible photographic
defect. Interior RGB error changed only 0.0157888 to 0.0157962. Under uniform
drift, flat-surround error improved from 0.000944126 to 0.000141688, but interior
error slightly increased. That narrower benefit does not replace the missing
whole-and-both-depth Texture positive.

Full analytic RGB blur conserves flux, but sampled, quantized CFA does not do
so exactly. Maximum full-active phase-mean drift was 0.06478% (R-driven), above
the declared 0.02% diagnostic; the two green phases varied by up to 0.01718%.
Neither quantity is the selected gathered-green mask flux. Sampling/rounding
and selected support remain distinct confounds, so the small false gain cannot
be attributed solely to defocus leakage across that mask.

The completed mechanical checks retain exact Off/Unity CFA and MHC output,
including a half-quad gather; reject the gain-only variance mutant; and preserve
unity on the three existing refusal cases. They validate this implementation,
not image-quality qualification. Final receipts are in
[completion.json](controls-3/completion.json) and `controls-3/output/`.

Two instrument repairs are retained without changing scenes or acceptance bars:

- `controls-1` stopped before scientific reports. Naive final summation crossed
  the fixed 1e-12 blur-flux tolerance (1.02846e-12); independent `math.fsum` on
  the same samples gave 1.25798e-15. Only assertion totals now use compensated
  sums; blur-producing loops and tolerance are unchanged. See
  [fixture-repair.md](fixture-repair.md) and its standalone diagnostic command.
- `controls-2` completed but serialized two no-drift fits as JSON literal null.
  Renaming the local `null` variable to `no_drift_fit` repaired the receipt.
  Run 3's screen, mechanical and refusal files are byte-identical to run 2;
  the final estimator receipt now contains both Fit objects. Run 2 remains an
  incomplete estimator record, not an alternative accepted result.

The fresh [build receipt](build-3/process.json) and log retain `Compiling
strehl-cli`. The executed test command was `build-3/cli-tests.exe
merge_cmd::native_photometric_normalization::independent_controls:: --nocapture
--test-threads=1`; exact paths and environment are in
[process.json](controls-3/process.json) and [invocation.json](controls-3/invocation.json).
No further tuning, full-stack render, default change or photographic claim follows.
