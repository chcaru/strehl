# Independent source and execution-contract review

2026-10-27. **VERIFIED by read-only source inspection:** no remaining source blocker for the first bounded generated falsifier. This is implementation review, not numerical verification, physical-model admission or photographic improvement. No model import, fit, RAW read, build or numerical job was run by this reviewer.

Frozen model SHA256: `659da66d343908564b16262482dc55e3220dd15f8318bf49623a7b2d8d8106cc`.

Frozen root `run-bounded.py` SHA256: `9e387adc0baa8f9bd650f24ef5b463af1f7056f55807890655d9d580ba61e68f`.

The independent control file remains its reviewer's separately frozen source; the root runner binds its actual execution version. This audit read its analytic generator, known-X controls, calibration split and decision path.

## Resolved source checks

The observation operator maps quadrature nodes from the original sensel square before Lanczos evaluation and literal R/G1/G2/B selection. It validates phase against original integer coordinates and rejects missing Gaussian/Lanczos support. It does not interpolate an observed RGB source. Delivery integrates the reference unit cell once from the pre-integration latent. The known-X scale/rotation challenge uses the predeclared central64 query subset because the full96 transformed corners exceed the fixed apron; full96 remains the fit/output panel and complete display. Independent analytic source-square integration and the wrong reference-footprint foil challenge the intended distinction.

Noise coefficients remain injected per phase. The NLL uses signal DN, supplied shot/read terms and quantization variance; no private variance estimate, fitted gain or white balance enters the fit. Original codes stay u16 on host/GPU; only the current observation converts to f32. Each source recomputes its latent graph and immediately accumulates backward gradients. Objective and image arithmetic remain f32 with TF32 disabled by the control entry before forward tests and by the fit entry.

The prior retains the physical-DN matrix-Cauchy expression but prospectively normalizes its summed edge terms by observed96x96 area. This resolves dilution from averaging over the larger free apron. It is explicitly a changed normalization, not an exact replay of the old whole-latent mean prior.

Five training views alone drive radiance, initialization and stopping. The other two View objects contain calibration-cell codes only; their scored cells are absent. Calibration freezes X. Returned-parameter localization is distinguished from shrinking a search interval and from identification. Known compatible acceptance and component/color guards prevent refusal-all from passing; numerical failure does not count as successful physical-mismatch detection. Annular blur is an explicit adverse case. Spatially changing least-blur ordering is deferred and cannot be silently credited to the global mixed-frequency test.

The root wrapper binds its own/model/control/design files, bounded-process helper, m12 harness, Python executable and retained helper-source files before/after. It checks terminal process accounting and records scientific status from `observations.json`, including negative outcomes. Limits are120seconds/4GiB host committed memory; the controls separately cap the CUDA allocator at4GiB. Package versions are runtime provenance, not a claim that every dependency binary is hashed. Host/device observations are not competitive timing evidence.

## Remaining interpretation limits

All240x240x3 radiance parameters remain free:172800 scalars, including145152 apron scalars, against46080 joint-training sensels. Counts alone do not prove rank, but central64 scoring does not remove blur-mediated apron inference. Direct-query support is labelled pre-blur coverage, not observability or a prior-only mask. Seven small sparse query matrices are cached; production query streaming is unimplemented. Full-size L-BFGS history alone would occupy approximately7.7GB before other buffers.

The1e-6 maximum-gradient stop is parameterization-dependent. For X=D softplus(z), dX/dz=D(1-exp(-X/D)), approximately1900 near2048DN; the same threshold has different meanings near black and for sigmoid blur parameters near a bound. A finite iterate can contain useful diagnostics without satisfying that stop. Preserve the frozen criterion and separate numerical refusal from optical-model rejection; do not launch a tolerance or solver-repair sweep.

**No complete-photo release follows this job.** Successful generated behavior would not establish Sony PSFs, source30's least-blurred status, automatic insect depth/visibility handling, or image-quality improvement. The deferred guard, practical full-size cost and complete photographic comparisons remain outstanding.

## Independent receipt review: first two executions

**VERIFIED from root receipts, not a reviewer rerun.** `raw-blur-controls-1` exited1 after7.453seconds during JSON serialization of a NumPy float32, before a fit or valid commission record. All processes terminated normally, without a Job kill; preservation records sources unchanged. The repaired control SHA `fe9428750e557cfd8839c6be2e0a7cbaaea905d8bd3760e3aca21fdc07705b9f` differs only by the NumPy-scalar JSON fallback. Removing those two serialization edits exactly reproduces the run1 source hash `edcaf5869ccc88c3ae82608437c472d90ffeae0297b01f32f22f96949bf4e7b9`. No stimulus, operator or guard changed.

`raw-blur-controls-2` exited0 after8.172seconds with `NUMERICAL_REFUSAL`; only flat-neutral fitted. Peak Job committed memory was3,536,044,032bytes; recorded CUDA peak allocated/reserved were555,328,512/727,711,744bytes. There was no termination attempt. All four completion-listed report hashes/lengths and both fitted NPZ hashes independently match. These checks use file bytes/JSON only, without array decoding or model execution. Source preservation and original-u16 preservation are recorded true.

The commissioned forward tests passed: DC error0.001953DN; continuous-source prediction RMS errors0.0680/0.1141/0.0220 injected sigma at variances0/.35/2.3; wrong footprint and wrong map were live. Reference integration, all-phase directional gradient and erased-far/overcontrast guard controls passed. This supports the tested observation wiring, not real Sony blur or unknown-field recovery.

Flat fitting reached64 optimizer iterations and71 complete objective evaluations. Maximum parameter gradient fell from0.01573 to0.00052035 but missed the unchanged1e-6 bar. Total objective fell4.09017→3.36270, mostly through prior reduction0.69096→0.03188; data NLL fell3.39921→3.33082. The last optimizer steps still reduce the objective by about1e-4, well above its f32 quantization increment. This is not evidence of a roundoff floor.

The finite diagnostic output passed flat noise protections: RGB/chroma error3.977/5.544DN versus7.737/10.245DN for the declared same-data flat mean. Held-source RMS was0.9890/1.0082 sigma and both guards passed. These are generated flat diagnostics, not recovered detail or photographic gains. Training variances fell near0.06–0.08 while calibration chose about55/109; flat data do not identify blur, so these values cannot calibrate optics. The first calibration also correctly records that its chosen value lies outside its localized final search interval.

**ARGUED next step:** one separately authorized, unchanged fixed-work continuation on coloured-flat and compatible structure is more informative than changing the already-passing discretization or starting a solver campaign. Preserve64 iterations, objective, source identities, guards, numerical refusal and unconditional no-admission. Observe complete finite outputs; stop on failed image/held protections. This changes scheduling only. A failure of that finite iterate would reject this fixed-work reconstruction, not establish infeasibility of the optical model. No continuation was executed by this reviewer.
