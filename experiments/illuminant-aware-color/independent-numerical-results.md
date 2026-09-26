# Independent numerical and identity interpretation

2026-09-25. **VERIFIED from retained execution receipts:** the bounded color
operator controls and complete cached writer comparison completed. This is
an arithmetic/identity result, not an image-quality verdict. I authored the
controls, not the operator; the operator author separately reviewed the
control choices. Root compiled and ran them. This review performs no new
build, numerical run, RAW decode or render and does not judge the images.

## Executed evidence

`build-1` retains the E0284 compile failure; `build-2` explicitly compiled
`strehl-cli` and exited zero. The only control repair was the explicit
`noise: [f64; 3]` type annotation. `controls-1/process.json` records the actual
command:

```
build-2/cli-tests.exe merge_cmd::illuminant_aware_color::independent_controls:: --nocapture --test-threads=1
```

All four exact tests passed: D65 equivalence, warm color/flat covariance,
interpolation, and metadata refusal. Their assertions cover actual Render
application, externally prescribed colored XYZ patches, and live transpose,
missing-WB-undo and appended-adaptation destroyers. This validates the tested
algebra and refusal cases; it does not calibrate the Sony sensor.

**MEASURED on the synthetic flat control**, candidate/baseline RGB variance
ratios were **1.169059, 1.358060, 1.858054**. Relative discrepancies between
actual Render variance and the independent propagated expectation were
**6.319218e-6, 6.389215e-6, 2.646976e-6**, respectively. These are variances,
not standard deviations. The larger variance is a real response to the new
matrix on this prescribed input covariance, not a propagation failure. The
synthetic camera and draws are not the actual captures' RAW noise, so neither
an actual photographic noise penalty nor a noise improvement follows.
See `controls-1/flat-propagation.json`; no photographic gate is encoded there.

## Metadata establishes availability, not physical calibration

`metadata-1` passed its one `metadata_pair` test. Exactly two originals were
decoded: opal103 `DSC00046.ARW` and marigold4 `DSC00021.ARW`. Both returned
ILCE-7CM2, ISO 100, exact A and D65 matrices, zero direct matrix, and the same
consumed WB bits `[1071144960, 1065353216, 1075924992]`. Their WB, selected
D65 bits and levels agree with their retained complete caches. Original file
hashes/stamps were held before and after, and active-u16 hashes were recorded.

Those active hashes identify these decodes; they are **not an independent
second-decoder validation**. This new route did not decode all 155/488 frames
or independently verify every frame's warm calibration. WB reciprocal is the
same consumed WB expressed differently, not a second white measurement.
Separate AnalogBalance/CameraCalibration/ForwardMatrix are not exposed by
the wrapper. The native-coordinate interpretation remains the stated model
assumption, not something proved by available matrix labels.

Both selections used the declared 3000 K coordinate, warm fraction
**0.9144210526315789**, and derived source white
**[1.0489465443842318, 1, 0.37826042356889616]**. The common matrix follows from
the common calibration/WB metadata. Neither equality nor neutral preservation
measures the filtered light spectrum, actual CCT or off-neutral physical color.

## Complete cached writer identity

`cached-1` passed its one `cached_pair` test, with zero RAW reads. It used the
held complete 155-source opal cache and corrected 488-source marigold cache.
Both Current replays and pinned rewrites exactly reproduce their original
full RGB16 pixels and ICC at **6792x4528** and **6268x4176**. Current and pinned
files also share file hashes within this run; their files need not equal the
older masters byte-for-byte to satisfy the explicitly checked pixel/ICC
identity. Cache binary and four-plane hashes remain unchanged.

For each candidate the full resolved development record differs only in
`matrix_bits`: exposure, sensor ceilings/top and tone parameters are identical.
Both candidate RGB hashes differ from Current, proving the arm was live, not
that its result is better. The existing matrix-dependent rolloff neutral target,
tone gain and gamut decisions can respond differently to the changed matrix;
holding their implementation and settings does not freeze those pixel results.

**No numerical or identity blocker found in this bounded review.** Receipts
explicitly leave `physical_color_calibration_established=false` and the image
verdict null. Complete-image/native-color review belongs to the independent
photographic reviewer. This evidence cannot establish glare recovery, removal
of spatial ghosting, absolute color fidelity or general quality acceptance.
