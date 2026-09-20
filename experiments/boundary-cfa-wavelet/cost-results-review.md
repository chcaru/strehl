# Independent cost/failure decision

**Close this full-size CPU-transform/eight-pair recipe. Do not run the70-frame
photographic pair, even if the numerical failure is repaired.** Review is
read-only; no new RAW, experiment, build or sweep was run by this reviewer.

Root invoked build-3/cli-tests.exe, exact ignored test
merge_cmd::boundary_cfa_wavelet::full_stack::vitamin_c_observational_pair,
with cost phase. The process exited101 after33.141 wall seconds and40.953
job CPU seconds, reporting `nonfinite inverse input`. Peak job committed
memory was7,101,923,328 bytes (about6.61GiB), not an RSS measurement.
Only source35's one-source baseline TIFF, started receipt and source receipt
exist. No candidate photograph or successful finish/cost receipt exists.

Source35's retained frame time is31.708082s: signal transform1.565031s,
eight-pair probe28.734747s, weighting0.392635s and baseline fold0.644651s.
The frozen resource projection already gives
70*31.708082+120 =2339.56574s before any finish allowance, exceeding the
1500s admission bar. This is the declared one-source cost projection, not a
measured70-frame duration or a claim that every source costs the same.
Memory alone is below the12GiB cost bar; that does not rescue runtime or
the failed finish. The prior fractional quality rejection also remains intact.

## Narrow numerical assessment

**STRONGLY SUPPORTED INFERENCE, not a retained coefficient diagnosis:**
overflow of the unnormalized f32 weighted coefficient is the likely cause.
The source fold finished after checking finite signal transform, smoothed
energy/floor and each individual weight. With one source and disjoint AC
packing, the denominator and unweighted mean remain finite. The shared fold
then performs `sums += weight * wave` without checking that product; finish
divides these numerators before the inverse's finite-input check fails.
The log does not retain the offending band, coefficient or weight, so none
can be reported as measured.

The inherited select_weight exponential arm permits exp(80), about5.54e34.
A finite weight of that size multiplied by a component above roughly6142DN
exceeds f32 capacity. Complete orthonormal coefficients can be much larger
than individual sensor samples. Bounding the weight or denominator alone
therefore does not bound the numerator. Tiny positive probe variances are
recorded, but no evidence identifies them as the cause; select_weight also
uses floor.max(1), and changing that floor is not licensed by this failure.

The production Laplacian BandMerge has the same arithmetic vulnerability:
pyramid.rs::accumulate_level uses f32 `num += w*lv`, while its named
long-stack overflow test checks only the weight sum. Different coefficient
scales and weights mean this cost failure does **not** prove the delivered
baseline overflowed. No production fix is made here. A future numerical
repair would need a direct finite-numerator/normalized-result control, not
another denominator-only test or an unexplained smaller clamp.

Preserve the useful original-u16 gather/covariance controls and failed result.
Move quality work toward an automatic shared source/support field feeding
the fast native CFA consumer, retaining noise-gated averaging and one shared
colour decision. The manual donor and commercial-image witnesses motivate
that direction, not an automatic ownership claim. Closed peak/concentration,
naive argmax smoothing and unconstrained blur routes stay closed; this cost
result does not rehabilitate them or justify another expensive replay.

Bindings: source-35.json SHA256
2e09d7cab2dc5b4c8710ff132e174fa00099c1a48bb07ee7c62fdb8917edbfae;
process.json42acb740eb40ea072211220f8d8b1f134f04b9e7575ee83ad61a60e706d6642c;
process.logcef971d550f92cb2c007fef56ce0dee3a6c5f3d2713c1112c6bd5aa738d1a480.
