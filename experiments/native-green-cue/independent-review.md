# Independent review: native green cue

Status: source review and fixed controls ready; no numerical execution by the
verifier. This is a consumer falsifier for one off-default cue, not a completed
C12 commissioning, calibration, photographic improvement or SOTA result.

## Held choices and what can reject them

The actual consumer is the existing BandWorker/load_frame/current three-band
merge/collapse. Its supplied-valid count is paired with an actual collapsed
output change. A separate compact core control passes the same deliberately
wrong energy with all validity bits false or true: false must reproduce the
ordinary accumulator/collapse bit for bit; true must change output. This
commissions fallback and live use without claiming that per-frame weights were
observed. It does not compare the new binary against a held prior revision.

The source model is fixed at gain .25 DN/e and read noise4e (1DN), including
noise-off draws. Original phase samples divide by WB[1.15,1,1,1.65] before u16
storage, with black512 and white15360. The independent generator applies the
literal variance .25*S+1; it does not call the priced cue to choose a sigma.
Standard normals reuse fill_probe_noise at32768/4096, seed
seed_id + frame_index*0x9e3779b9 with wrapping usize arithmetic. Generator and
source clipping are asserted absent. Each nine-frame input is generated once
and cloned for the two modes. This can check the operator against an injected
model; it cannot independently calibrate that model or physical CFA covariance.

Fixed primary population: flat and mixed x/y/diagonal fields, noise-off plus
eight seeds701,709,719,727,733,739,743,751, both modes; three noiseless low-only
directions, both modes. Maximum78 stack outputs. Flat18 outputs run first and
must pass before the sharp-source survival controls and remaining60 outputs.
No original RAW data, TIFF, tone/profile, fresh alignment or parameter search.
A scientific failure is written to measurement.json before the assertion exits;
incomplete populations cannot pass. Hard malformed-input failures remain
assertions with root-owned logs.

Literal controls independently choose:
- Flat, additive green +/-32 and exact integer affine green fields must have
  zero cue response. Exact affine fields with independent1.01/.99 phase gains
  must also vanish; arbitrary quantized slopes are not silently assumed affine.
- An impulse at either central green contributes24.5 for amplitude4; either
  selected vertical neighbor contributes1.5. R/B impulses contribute zero.
  These literal values are independently expanded coefficients, not a copy of
  the author's loop. Constant S3000 must price3755DN^2; doubling the returned
  price must fail that same .001DN^2 gate. This tests unique-source accounting,
  not calibration.
- Nonzero textured padded and packed layouts must agree. Missing original
  support and clipped green support must abstain. Prepared border validity must
  be false after the actual smoothing support requirement.
- An affine variance field has an analytic transported expectation. The fixed
  independent similarity has g=.012, rot=.006, tx=.375, ty=-.25; direct matrix
  arithmetic locates its native quad centre, without apply_at in the oracle.
  Its price must agree within .003DN^2. Omitting the quarter-quad centre changes
  the literal answer by more than1DN^2. This is a coordinate falsifier, not a
  new scored warp population.

## Output metric and nuisance re-choice

The high tone is .30cycles/native-pixel. Each individual green plane aliases
above .25, so the readout retains the two greens at their different native
positions. The second readout assembles the actual collapsed four planes,
reapplies the fixed WB and calls the existing demosaic_row, matching the
reconstruction stage's convention. Its green output is compared on the same
native ROI x[87,187), y[45,145). This establishes only that reconstruction
kernel's behavior, not RGB16 file/tone/ICC behavior.

The reference is the independently evaluated unit-cell integral of the sharp
continuous two-tone field, not the output of a warp or demosaic. Five-term f64
least squares fits constant and both sine/cosine pairs simultaneously, avoiding
finite-window and diagonal-frequency leakage. Complex error includes phase:
amplitude alone could reward sharpening or the wrong alias. Full known-truth
RMSE additionally rejects extra unmodelled content. Noise-off sharp source-only
reconstruction must retain at least50% high-tone amplitude with at most25%
relative complex error in both readouts. No extra stack output is needed.
Swapped green phases on the axis case, a one-native-pixel shifted field, and
+50% manufactured high-tone amplitude must each fail the independent metric
by at least .10 relative-error units. The diagonal green-swap case is not
claimed as a falsifier: its two green positions have equal x+y and swapping
them is intrinsically inert.

Flat uses per-site temporal variance over eight seeds, then an ROI mean; no
spatial standard deviation substitutes for temporal noise. The statistic is a
difference of variances, not the variance of paired image differences. Exact
paired delete-one jackknife yields the variance-difference SE. The candidate
point variance cannot exceed off, and delta+1.96SE must be <=.05*off variance.
Mean-field RMSE cannot worsen. An explicit doubled-noise readout must fail the
same temporal statistic. Small adverse differences can reject this fixed
program without demonstrating visible or statistically resolved degradation.

For every direction and both readouts, noise-off and eight-seed-mean high-tone
complex error and full RMSE must not worsen. Low-tone relative error may rise
by no more than .002; individual noisy seed RMSE may rise by at most5%.
Low-only rows also reject a manufactured high tone. Allowances are only
1e-5DN RMSE and1e-6 relative error. Mean-field RMSE and high complex-error
changes retain paired jackknife SE and delete-one values; every seed is saved
as a metric row. A material result requires at least5% high complex-error
reduction in both readouts for one same direction, with baseline relative error
at least .02. The decision does not pool favorable directions or hide an
adverse extreme.

## Source routing and run review

Source preparation precedes the fullres gather, keeps the original u16 CFA
source and uses the injected NoiseModel. The fixed sums price each squared
filter separately; shared sensels between squared filters do not create a cross
term in this expectation. Positive bilinear transport and actual smooth5 apply
equally to energy and variance, and validity is eroded before the replacement.
The core seam overwrites only supported finest-band weights; old coarse bands,
reconstruction and off/fallback arithmetic remain in the shared path. This is
source evidence, not a measured unchanged-default guarantee.

Root's run.py binds build sources and the test executable before and after one
exact ignored test. It clears inherited experiment environment, fixes two
threads/fullres gather and records invocation, process and completion even when
the scientific assertion fails. It enforces120CPU seconds,120wall seconds,
2GiB job commit and256MiB retained artifacts. No automatic numerical repeat is
authorized. Compilation/source repairs may address code defects before
measurement, not alter the acceptance bars after seeing a result.
