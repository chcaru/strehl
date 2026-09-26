# Independent review: native photometric normalization

**MEASURED / VERIFIED — stop this fixed recipe after the generated screen.**
The final `controls-3` run executes all four tests and seven image cases, but
`quality_pass`, `estimator_pass`, `positive_exercised` and
`candidate_qualified` are false. No photographic replay is admitted. This
review changes no source, mask, scene, threshold or setting.

The retained command is `build-3/cli-tests.exe
merge_cmd::native_photometric_normalization::independent_controls:: --nocapture
--test-threads=1`, with the exact consumer environment recorded in
`controls-3/invocation.json`. The fresh build has a `Compiling strehl-cli` line;
the test log records four passes. Those passes certify completed mechanical
checks, not scientific qualification. Off/Unity preserve full CFA and MHC
output, including the half-quad gather control. The gain-only variance mutant
is rejected; variance is transformed by gain squared with the original beta.
Insufficient-support, clipped-source and implausibly-dim-source refusals retain
the prescribed unity behavior. These are operator checks, not independent
sensor-noise calibration.

The decisive limitation is support. Both noisy Flat cases and all three noisy
Texture cases have zero eroded mask sites and apply unity gains. The noiseless
Texture estimator twins also have no support. Uniform Texture therefore keeps
the same interior RGB error, **0.00558429**, and cannot deliver the required
5% whole-and-both-depth improvement. The left-only illumination case also stays
unchanged. Its no-harm result does **not** demonstrate detection of spatial
nonuniformity or the safety of an active global correction. This is a measured
availability failure of the prescribed mask, not proof that scalar exposure
normalization can never help.

Broad defocus is the only active image family, with 2,410 mask sites. Its
no-drift false correction is **0.03759%**, within the frozen 0.2% estimator
bar. Nevertheless, the flat-surround RGB error rises from **0.0000297137 to
0.000108708** in normalized RGB units and fails no-harm. These are small
absolute errors; the relative ratio alone would exaggerate the practical
magnitude. Interior RGB error changes only **0.0157888 to 0.0157962**. With
uniform illumination drift, flat-surround RGB error improves from
**0.000944126 to 0.000141688**, while interior error changes
**0.0157456 to 0.0157994**. This limited flat-region benefit is not the required
colored-detail positive. The exact scaled broad twins recover gains within
**0.04520%** of their prescribed values, but scaling covariance alone does not
establish discrimination against defocus.

Analytic full-RGB flux conservation must not be confused with RAW conservation.
The measured maximum full-active CFA phase drift is **0.06478%** for broad
defocus, above the predeclared 0.02% diagnostic. That statistic is also not
the selected gathered-green flux consumed by the estimator. Sampling and
rounding remain a confound; the small false correction cannot be attributed
solely to leakage through the mask. None of these generated measurements
establishes physical brightness drift in the user's photographs.

Two instrumentation defects remain visible in history. `controls-1` stopped
at a naive floating-point sum assertion before completing scientific reports;
the compensated-sum repair retained the blur-producing loops and the 1e-12
tolerance.
`controls-2` completed the tests but omitted both no-drift Fit objects through
a JSON literal/variable mistake. Its apparent completion receipt is not a
complete estimator record. I verified that final mechanical, refusal and
screen files are byte-identical between runs 2 and 3; estimator JSON differs
only by replacing those two nulls with objects. The repaired broad no-drift
object equals the already-retained quality-screen Fit exactly.

Final screen SHA-256:
`1a6e7944de93df55f501b3eea400aba6031675aee87f4d198b5a1f4e82b7a71f`.
Final estimator SHA-256:
`475a2dd5ab4a366190895ae13b0624edf8f9b808bebdf96d9b8211ba1d1f657a`.
There is no full-stack candidate or photographic improvement to show from
this trial. The saved result does not authorize another mask, erosion, gain
or scene sweep.
