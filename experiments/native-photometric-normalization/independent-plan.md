# Independent native photometric controls

Pre-run amendment approved by root: only Texture gets the fixed horizontal
background trend `0.12*(x/383-0.5)`, giving a broad bright region potential
support above the noisy raw-luma quantile. Literal Flat remains unchanged;
an unavailable fit there is disclosed. Texture's surrounding window is labeled
low-detail-gradient-surround. Known background is subtracted from truth and
output before texture projection, so preserving its gradient cannot hide
lost vertical texture. Full RGB/green/chroma errors retain the background.
The estimator report also records full-active quantized CFA means by RGGB
phase and their maximum relative drift. The 0.02% diagnostic distinguishes
analytic finite-RGB conservation from sampled/rounded RAW conservation; if
exceeded on broad defocus, a false-gain result cannot solely be attributed to
the estimator. It does not change quality bars or silently count as exact RAW
flux conservation. No measurements preceded this amendment.

Frozen before measurements, 2026-09-25. Root runs the build/tests. The operator
author and separate reviewer read the control choices; this reviewer authors
the generated controls, not the consumer. No RAW or full photographic adapter
is authorized here. No control/data/threshold rescue follows a negative result.

Mechanical prior-art search executed:
`prior_art.py photometric flux gain defocus`. Read M91, M99, M97q, M125 and
their relevant SYNTHESIS records. M91's scalar-model applicability remains
unproved; its spatial-uniformity instruments failed their power controls.
M99's geometric inverse-square gain and offset explanation lost. M97q withdrew
the un-eroded-mask quality headline after a pure-defocus false gain. M125's
auto threshold/domain are not transferred. This tests the approved existing
fixed-window regularized-focus mask, .40/.60 quantiles, erosion16/min1024 and
Flux/PhotometricMap in the actual native consumer. No quadrant/new scalar guard.

Four exact tests, using `STREHL_NATIVE_PHOTOMETRIC_OUT` as an existing fresh
output directory:

1. `independent_identity_and_noise_controls` writes `mechanical.json`. Check
   black-subtracted positive/negative/zero samples and prescribed variances
   through actual `scale_inputs`; gain1 is exact, variance changes by gain².
   A gain-only variance mutant must fail. Off and Unity run the actual native
   consumer with a shared half-quad translation, preserving complete CFA/MHC
   bits and unmodified source bytes. Saved samples and hashes check that the
   consumed pre-scale variance, original beta and source arrays agree on replay.
2. `independent_estimator_discrimination_controls` writes `estimator.json`.
   Two noiseless defocus scenes and exact same-data gain twins use actual
   estimation, never supplied corrector gains. Reference2 has brightness1.
   Both fits must be AVAILABLE, false gain on no-drift data <=0.2%, and fitted
   reference/frame gain relative error <=0.2%. Multiplicative covariance alone
   is arithmetic, not discrimination: the no-drift result must independently
   stay at unity. A finite periodic broad-blur plant conserves full RGB flux
   but extends to radius80 native, beyond the fixed32-native erosion margin.
Selected-region flux conservation is deliberately not assumed.
3. `independent_refusal_controls` writes `refusals.json`. Exercise insufficient
   eroded support, a clipped nonreference source and an implausibly dim source.
   Preserve the existing per-frame refusal behavior and verify full unity
   CFA/MHC identity when all applied gains are1. These guards do not identify
   spatial nonuniformity. Existing clipped-reference semantics are not repaired.
4. `independent_quality_screen` writes `screen.json`, seven fixed cases: noisy
   flat and colored two-depth texture, each without/with uniform illumination
   drift; noiseless broad defocus without/with uniform drift; and noisy texture
   with illumination drift confined to the left half. The untouched right
   detail in the last case must not be sacrificed by a global correction.

Image fixtures use u16 padded active CFA, injected existing ISO100 model,
384x320 native extent, N5/reference2 and fixed supplied identity geometry for
scoring. Noisy fixtures change noiseless signal with illumination **before**
drawing signal-dependent shot/read noise. Noiseless exact scaled twins belong
only to estimator controls. Truth is fixed in the reference brightness gauge.
This validates propagation/consumer behavior, not physical sensor calibration.

Flat cases are scored first. Known-truth RGB/green/chroma RMSE may increase
by at most5% (plus1e-7 roundoff), with at least98% of each already-recovered
bounded true texture component retained. RMSE can reward loss of structure
when noise dominates; template retention guards that direction. Template
energy alone can reward sharpening, so it is never a quality metric by itself.
A brightness0.8 destroyer and added flat-noise destroyer must be rejected.

Uniform noisy texture must be AVAILABLE, baseline RGB RMSE >0.001, both
depths' baseline template recovery >=0.5, non-unity gains and changed pixels.
It must improve RGB RMSE by at least5% on whole interior and each depth, while
all protected windows pass no-harm. No-drift twins and the spatial adversary
must preserve quality; an ordinary unavailable fit is disclosed as such, not
credited as detection of nonuniformity. Broad-defocus no-drift additionally
requires AVAILABLE with <=0.2% false gain. No postfailure waiver.

All four Rust tests must pass mechanical assertions. Scientific negatives
remain in JSON. `screen.json` has schema1, mechanical_pass, quality_pass,
positive_exercised, brightness_destroyer_exercised,
photographic_replay_admitted=false, and cases[7]. `estimator.json` separately
has estimator_pass. Root qualification requires their conjunction, mechanical
and refusal completion, and independent review. A lower disagreement, altered
brightness or unavailable estimator cannot satisfy the positive by itself.
