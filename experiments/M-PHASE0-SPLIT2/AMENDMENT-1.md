# M-PHASE0-SPLIT2 amendment 1 — analytically remove translation

**Committed before any real-capture FRC value was retained or inspected.**

The first protocol stopped when pass-1 ISO-50 frames moved by 1–2 quad pixels.
After that STOP was filed, the orchestrator supplied the independently
pre-registered SOTA scorecard (`2026-09-sota-scorecard.md`, commits `90bced75`
and `986c4653`). The scorecard predates this lane's result, names this exact bee
capture as the independent-repeat sentinel, and explicitly permits translation
to be removed analytically as a Fourier phase ramp (§1.5). It also fixes the
bee input to each 32-frame ISO-100 block and caps licensed detail at
0.25 cycles/native pixel (§4 M1).

That external registration changes the interpretation of the gate without
using an FRC outcome: metadata proves repeated fixed-focus exposures, the focus
proxy passed, and direct scale-normalized spatial correlations exceed 0.9978.
The failure is co-registration, not evidence that the subject/focus changed.
The original zero-shift result remains on record; this amendment asks the
narrow original question after the only correction the scorecard licenses.

## Fixed analysis

Primary inputs are the two scorecard-registered ISO-100 runs:

* bright: `DSC00328.ARW`–`DSC00359.ARW`;
* second light: `DSC00584.ARW`–`DSC00615.ARW`.

For each run, estimate every frame's translation relative to frame 0 from a
centred 512x512 quad-green alignment crop. Estimate the peak of low-pass phase
correlation to subpixel precision. Apply the inverse translation only as a
unit-modulus Fourier phase ramp to the 1536x1536 crop; never spatially
interpolate it. The four 256x256 FRC tiles overlapping the alignment crop are
excluded, leaving 32 non-overlapping held-out tiles.

The translation instrument must be commissioned before use against an
analytically evaluated multi-sinusoid image that the estimator/phase-ramp code
did not generate. It must recover a fixed `(1.25,-0.40)`-quad-pixel displacement
within 0.05 pixel, preserve every Fourier magnitude within `1e-12` relative,
and reduce aligned RMS error below 1%. A wrong-sign phase plant must go RED.
Four independently estimated quadrant translations must agree within
0.05 quad pixel (0.10 native pixel) in each real run; otherwise the motion is not a licensed
translation and the amended analysis stops.

Each 32-frame run uses every exposure once:

* held-out reference: index `i mod 4 == 0` (8 frames);
* repeat A: `i mod 4 == 1`, plus `i mod 8 == 3` (12 frames);
* repeat B: the remaining 12 frames.

The reference is retained only to diagnose stable structure; the original
repeat FRC is computed between A and B. The primary temporal null remains the
disjoint ABBA contrast from the preregistration: within every four-frame block,
weights `(+1,-1,-1,+1)` cancel constant and linear light drift; alternating
blocks form D1 and D2.

Primary real-data bars are unchanged:

* pooled ABBA maximum `P_sig/P_noise` over
  `0.10 <= f < 0.2762 cycles/quad-pixel` and its tile-bootstrap upper 95%
  endpoint must both be `<0.25`;
* mean absolute null FRC `<0.05`, three band FRC magnitudes `<0.08`, and maximum
  ring tile `|t| <4`;
* both light runs must pass separately; disagreement is `NOT ROBUST`;
* raw and disjoint-strip photometrically normalized analyses must agree.

The deciding comparison with the closed lane is the pooled real ABBA low-band
FRC against the split-half common-mode adversary `0.972099`, plus the maximum
mid-band SNR against the historic failed `0.438734` and the `0.25` bar.

Report repeat-pair crossings in both cycles/quad-pixel and
cycles/native-pixel (`f_native=f_quad/2`). No value above
0.25 cycles/native-pixel may be quoted; such an outcome is only
`UNLICENSED_GT_0.25`. A crossing is not a scorecard/SOTA result: this lane lacks
the scorecard's frozen common-linear RGB boundary, matched dark/flat floor,
target-locked D statistic, comparator outputs, and holdout site manifest.

## Illumination and verdict

The two light levels are never treated as two observations of one latent.
Every primary pair/null is within one 32-frame fixed-light run. Per-frame
normalization uses only the disjoint left strip and is a sensitivity analysis.
The darker run must independently reproduce the decision; it cannot be pooled
to rescue the bright run.

`REPEAT_FRC_VIABLE` requires both registered runs, both normalization arms, and
every commissioned control to pass. Any null failure, non-translational
motion, censor/fallback, sharpening improvement, or light-level reversal is
`NO_BUILD`. Even a pass licenses only a candidate scorecard instrument, not a
Rust change or a SOTA detail claim.
