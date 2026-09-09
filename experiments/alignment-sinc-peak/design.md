# Fixed generated peak-interpolation comparison

2026-09-09. Independent prospective design, frozen before numerical execution. This is a small current-NCC consumer test, not native alignment or photographic evidence. The author implements; root executes; the independent verifier owns the literal controls and reviews the actual choices. No original capture or full solve is released.

## One field family, 48 actual consumer rows

Reuse the continuous sinusoid construction in `experiments/m78-blur-eq/src/field.rs` and its existing xorshift64*/BoxMuller RNG. Fix64 components, radial frequencies log-uniform from1/40 to1/2.6 cycles per plane pixel, amplitudes proportional to1/frequency, and the existing normalization sum(amplitude²/2)=1. Field F1 seed is0x78F1E1D0; independent F2 seed is F1seed XOR0x9e3779b97f4a7c15. No field, frequency or seed selection after looking at errors. A thin reuse of these formulas is enough; do not copy the retired alignment implementation or create another renderer.

All images are256x256 f32 planes. The fixed128x128 reference tile starts(64,64), centred at c=(128,128), with search radius6 and the current deep config's contrast/peak thresholds. Each field evaluation is direct at the requested continuous coordinate, including analytic Gaussian attenuation exp(-2*pi²*sigma²*frequency²) before sampling. There is no raster warp in the generator. Mean is3500DN; signal scale is250DN. This is an alignment software field, not a RAW/photon-calibration fixture.

Six residual displacements in reference-plane pixels, in this order:

| case | dx | dy |
|---|---:|---:|
|0|+.0625|-.3125|
|1|-.0625|+.3125|
|2|+.1875|+.4375|
|3|-.1875|-.4375|
|4|+.375|-.125|
|5|-.375|+.125|

Four fixed content blocks:

- Same focus:3500+250*F1, sigma .35 in both images, no noise.
- Unequal blur: the same field, reference sigma .35 and moving sigma1.4, no noise.
- Mixed-depth challenge:3500+(250/sqrt2)*(F1+F2); reference sigmas(.35,1.4), moving sigmas(1.4,.35), no noise. This additive two-depth construction changes content without one shared blur kernel. It is not an opaque-surface/shared-pupil renderer or a physical occlusion claim.
- Noisy same focus: the first block plus independent16DN Gaussian image noise, using the existing M78 row schedule. Reference seed0x51C00000+i and moving seed0x51D00000+i for case i. These six fixed pairs are a noise challenge, not a temporal calibration or confidence-interval population.

Run every block/case through BOTH actual current paths, with identical arrays for old and candidate:

1. `ncc_tile`: T(p)=p+delta, predicted displacement zero.
2. `ncc_tile_warped`: A=1.008*R(.004 radians), T(p)=c+A*(p-c)+A*delta. Supply the seed linear part A, predicted displacement zero. Moving(q) evaluates its declared blurred field at T^-1(q); blur sigma is in reference-plane units. The actual warped path's bilinear sampling remains part of the tested consumer, unchanged in both modes.

Thus48 paired rows require96 actual NCC calls before controls/timing. The expected returned displacement is delta for the first path and A*delta for the second. Score the Euclidean reference-plane error after independently applying literal A^-1 to the warped return. Derive truth from the declared matrix/constants, never from an estimated fit or the production coordinate helper. This tests a fixed local scale/rotation seed, not recovery of a nonlinear breathing track. The separate39-rung M103 RAW ladder remains deferred.

## Fixed candidate and integration boundary

Use normalized separable Lanczos-windowed sinc, radius4, only on the existing NCC score grid. The union of support over the +/-0.5 cell is9x9: each noninteger evaluation has8x8 nonzero samples, and its tap indices change with floor(position). Do not use one asymmetric fixed8x8 block, pad missing scores, wrap or clamp them. The author's bounded Newton/backtracking implementation uses analytic derivatives, at most80 evaluations, step tolerance1e-4, a negative-definite Hessian and a strict interior maximum. Its exact arithmetic/constants must be held before execution; no optimizer comparison follows. Subtracting a scalar score baseline is allowed only as the algebraically equivalent normalized-interpolant calculation, and gets a constant-offset control.

The test-only helper returns offset/evaluation-count/reason. Actual mode wrappers expose the helper outcome without changing ordinary public calls, which stay parabolic. Every unsupported, nonfinite, flat/ambiguous, curvature, boundary, convergence or budget case returns the original parabolic result through the unchanged caller arithmetic. Preserve the integer winning location, original integer peak score, contrast and TileStatus. A fallback is not a candidate success. In particular, the old NCC matcher has no general periodic-texture uniqueness guarantee; exact fallback preserves that limitation rather than claiming the matcher now rejects all ambiguous images.

## Literal controls before the field comparison

The verifier independently supplies score grids not generated by the candidate interpolator: an analytic rotated peak with known stationary point, a displaced peak of reversed sign, a flat plateau, separated equal maxima, nonfinite support, insufficient support, a boundary maximum and a nonconcave/ringing challenge. Include symmetry/axis swap and positive score-gain/constant-offset invariance. The field truth must not be obtained by interpolating a discrete array with the same kernel. Literal controls commission arithmetic and refusals only; they cannot license the RAW ladder without the actual48 rows.

Actual flat planes must preserve LowContrast refusal; an independently specified periodic ambiguous image must retain the old status/result when the refinement declines it. Show live accepted, fallback and default-off paths, exact default/old relevant result bits, unchanged source arrays, finite evaluation counts<=80 and preserved integer peak metadata. An all-fallback result is insufficient. Every requested fixed row remains in the report, including refusal/failure. Wrong signs, swapped axes or omission of A on warped returned displacement must make their independent checks fail.

## Frozen engineering bars

Report every signed estimate, reference-plane vector error, mode status and fallback reason, then RMS Euclidean error and literal maximum separately for each of the8 content/path blocks. These finite-case statistics have no sensor/noise CI interpretation.

- Same-focus blocks: if old RMS<.005px, classify the gap as INCONCLUSIVE. Otherwise require candidate RMS<=.80*old RMS, candidate max<=.075px, and candidate max<=old max+.005px in EACH path.
- Unequal-blur, mixed-depth and noisy blocks, EACH path: candidate RMS<=old RMS+.005px, candidate max<=old max+.02px, and candidate max<=.25px.
- All48 actual rows must retain the old successful TileStatus and integer-peak metadata. At least4/6 rows in EVERY block must use an accepted sinc offset, and each block must contain a changed offset. Missing liveness or insufficient baseline error is INCONCLUSIVE; a resolved accuracy/control violation is REJECT. Retain all flags if conditions overlap. A reduced fractional-offset pile-up alone never passes a bar.

The RMS can conceal one bad fraction, hence the maximum guard. A symmetric average can conceal a sign error, hence signed rows and independent sign controls. These masks/cases are not selected from measured NCC confidence. The candidate can fail by sinc ringing, by following a different continuous maximum, by finite-support truncation, or by unequal-depth content bias that a finer interpolation cannot fix. Same-focus exact recovery cannot establish defocus robustness; the challenge blocks are binding. No covariance/noise constant is estimated or fitted from these errors.

## Timing and stopping

Reuse the already generated same-focus case2 arrays. For EACH actual path, run one unmeasured warm-up per mode, followed by fixed old/new/new/old blocks of16 calls each, preserving exact inputs and collecting the actual NCC result. Report completed block elapsed time and the minimum per mode; require candidate/old<=1.10. This is local NCC-call timing, not a full pair solve, full stack or GPU benchmark. Keep timing separate from correctness and retain cap/failure records. No repetition extension or alternative field/settings follows a noisy timing bound.

Root allocation is120 aggregate child CPU seconds,2GiB job commit and256MiB retained artifacts for controls,48 rows and this timing together. A generated PASS only permits root to consider the separately allocated real ladder. It does not change defaults or establish general photographic improvement. No width, optimizer, radius, noise, seed or threshold sweep follows a rejection/inconclusive result.
