# Independent results: native green cue

**MEASURED / independently reviewed: REJECT this fixed implementation.** Its
original-green signal is useful in some readouts, but it fails the complete
consumer requirements. No numerical replay, tuning, RAW decode or image metric
execution was performed by this verifier; the review reads the saved rows,
receipts and held source. It does not refute the C12 family or CFA-native cues.

## Complete, live evidence

The result is stage complete:78 stack outputs,72 unique scene/seed/mode tuples
plus6 low-only outputs;89 saved rows in total. There are79 failed bars:
12 mixed noiseless,7 mixed mean-image,48 individual noisy RMSE,6 low-only RMSE
and6 low-only coefficient failures. None is a missing-population or flat-control
failure. The final assertion emitted exit101 after saving measurements; the job
was not terminated by the resource guard.

The literal constant/affine/phase-imbalance/gain controls pass with zero energy.
Both central green impulses give24.5 and the tested vertical neighbors1.5;
R/B give zero. The independent price is exactly3755DN^2, and the affine transport
is4359.802734 against4359.8025. Source support, clipping, padded-origin and the
factor-two price destroyer assertions were reached and passed. The actual-core
invalid-cue fallback matches all3072 f32 values by bits; enabling the deliberately
wrong supported cue changes all3072. Actual scored modes supply valid cue sites
and change144,504 collapsed green samples across the pairs. These are live
consumer witnesses, not an observation of every frame's weight field.

Sharp-source reconstruction also passes. The combined phase-position high-tone
amplitude is .99988–1.00079 of truth; current demosaic Green retains .89889 for
x/y and1.09083 for diagonal, with relative complex errors .10111 and .09084.
Thus .30cycles/native-pixel can survive these readouts. Wrong phases, a native
pixel displacement and manufactured high amplitude fail their literal metric
controls as required. None of this implies a TIFF/tone/ICC or photographic win.

## Benefit and failure are different observations

Flat temporal variance falls from368.755 to300.706DN^2 for phase-position Green
(delta−68.048, paired jackknife SE9.584), and278.824 to219.419DN^2 for reconstructed
Green (delta−59.405, SE7.103). Both fixed95% upper bounds pass. Noisy mean-image
flat RMSE also falls6.738→6.060DN and5.845→5.163DN; paired delta SEs are .125
and .088DN. These are temporal/known-truth quantities, not spatial texture
standard deviations.

The eight-seed-mean high-frequency complex coefficient error improves in every
direction/readout. The reduction is30.09–83.59%, with paired absolute error
changes .1600–.3841 and jackknife SEs .00470–.01127. Every one of the48 individual
noisy readouts also improves its high-tone complex coefficient. The intended
signal benefit is therefore observed; the complete quality gate still fails.

Re-choosing the readout from fitted tone to full image and from mean image to
individual output changes the conclusion:

| Direction/readout | Mean-image RMSE off→cue, DN | Paired mean-image delta ± jackknife SE, DN | Mean individual-output RMSE increase ± paired SE, DN |
| --- | --- | --- | --- |
| x / phases | 19.439→19.860 | +.421 ± .215 | +11.089 ± .162 |
| x / reconstructed Green | 17.393→17.326 | −.068 ± .210 | +9.125 ± .127 |
| y / phases | 19.489→20.614 | +1.125 ± .196 | +10.542 ± .223 |
| y / reconstructed Green | 17.438→18.112 | +.675 ± .166 | +8.808 ± .184 |
| diagonal / phases | 19.107→14.013 | −5.094 ± .064 | +5.937 ± .114 |
| diagonal / reconstructed Green | 15.390→11.299 | −4.091 ± .059 | +6.495 ± .092 |

The last column is independently aggregated from the eight saved paired
single-output RMSE rows; its SE is the sample SD of paired differences divided
by sqrt(8). It is not a new pixel readout. The very small x/reconstructed mean
improvement is unresolved at its SE and reverses sign in every saved
seven-seed leave-one-out mean. The diagonal mean improvement is substantial,
but even that direction loses on every individual noisy output. All48 individual
RMSE ratios lie1.259–1.541, beyond the fixed1.05 limit. The extra seed-dependent
error cannot be dismissed because the flat control improved; behavior on
structured content differs. This record does not isolate which weight/noise
coupling or spatial reconstruction component is responsible.

Noiseless x/y also lose: phase RMSE is about20.07→25.72DN and reconstructed
Green17.76→22.92DN, with both tones' coefficient errors worse. Diagonal alone
improves without noise (phases19.84→14.69DN; reconstructed15.82→12.25DN).
This rules out blaming every failure on the random-noise draw.

Low-only is an independent nuisance re-choice: all six readouts lose RMSE,
by3.769–4.124DN. Low-tone relative error increases .01164–.01193 versus the
allowed .002. The absent high tone is not manufactured more strongly here;
the loss is primarily failure to preserve the real low-frequency content.
A favorable high-frequency coefficient alone would have hidden this failure.

## Post-hoc finite-ensemble decomposition

**DERIVED, not a new acceptance gate.** For the same ROI and truth, the stored
single-output and mean-image RMSE rows give
V = (8/7)*(mean_j(RMSE_j^2) - RMSE(mean image)^2).
This is unbiased per-site temporal output variance averaged over the ROI,
apart from the stored mean image's f32 rounding. No new pixel measurement or
noise-model prediction enters it.

| Direction | Phase-position variance off→cue, DN^2 | Reconstructed-Green variance off→cue, DN^2 |
| --- | --- | --- |
| x | 107.114→779.308 | 89.930→595.131 |
| y | 107.412→707.783 | 90.127→545.594 |
| diagonal | 109.138→633.542 | 91.681→529.053 |

These are the observed eight-draw population's variances, not calibrated
population values. Their individual jackknife SEs cannot be recovered from the
saved delta-only leave-one-out mean RMSE records; no confidence interval is
invented. This decomposition separates increased variability on structured
content from mean-field error, while preserving the diagonal mean-field gain.
It does not identify the particular weight mechanism or transfer to real RAW
noise. The prospective rejection already follows from the measured per-seed
and low-only gates, independently of this post-hoc calculation.


## Provenance and cost

Verified all14 build-manifest source hashes/sizes against disk; the committed
source tree bd7d444e53a8ec399ffc8299e0431c98b20bb2bf has no diff for those paths.
The invocation records earlier HEAD33d87c0382e32ab4711f13bd9482287dffaaf0fe
because the source commit was delayed; the source-file hashes, not that earlier
HEAD label, identify what compiled. Fresh Compiling strehl-core and strehl-cli
lines and successful build-finished are present.

- Test executable: b64a90f9e3dc0554c289404077574eeb5c0641fae8c487af0ff86e639f89882f.
- Independent controls: ecf95bf9173241fdd7035f27c8b4b5fc421cdfa31bdcea94333fc523425e5b14.
- Measurement:465c18ce35ae70bb58536c55f3b4d1d11ae678520c7dc8d8939eb21692289e48,
  103,554bytes; log85e644fd9cd59dc42cddf7d219d6759a57ccef62db228907ae2eb1baa82540e6.

The one numerical job used4.890625 owned CPU seconds,2.890wall seconds and
10,346,496bytes peak job commit, with terminal accounting, no cleanup errors and
no intervention. Retained bytes before completion were108,589. Compilation
separately used99.140wall/191.953125CPU seconds. These are bounded experiment
costs, not production-speed measurements.

The decision remains rejection of this one fixed replacement, with its measured
high-frequency benefit retained in the record. No default promotion, C12
clearance, photographic improvement or SOTA claim is supported.
