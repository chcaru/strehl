# Independent generated guide screen

Frozen prospectively on September 26; root executes. Four tests commission the
actual transform, paired-floor path, scoring and then eight image cases. No RAW
file, full photograph, parameter sweep, camera calibration or quality admission.

The original-u16 fixture/gather geometry and original-site noise draw are reused
from rb-own-guide/chromatic-source-evidence: five RGGB frames, active320x288 at
origin(7,11), stride349, outside sentinel64999, black512/white15360, current warm
WB bits, crop(7,9,145,125)quads and five small fractional similarities. Scene
radiance is sampled analytically through the inverse known geometry before
independent original-site Gaussian shot/read draws and u16 rounding. All active
codes must remain strictly within the known black/white interval. The injected
noise model is shared with the operator: this does not validate its calibration,
Poisson tails, PRNU, actual PSF, clipping or a 299/488-frame selection population.

At each ISO100 and400 the order is Flat, Veil, BrightRidge, WeakColour. Flat is
constant neutral .25. Veil exactly retains the prior unclipped additive scene:
neutral glint peak.65, centre(122,120), angle.70, widths(1.8+8k,1.8+.15k) with
conserved analytic flux; coloured far texture at native frequency.06, direction
(.8,.6), phase.37, amplitudes(.065,.025,-.050), focus4 and sigma .65+1.1|k-4|.
The all-focus truth sums the independently focused components. This is a
rejectable bright-spread model, not a measurement of mineral glare physics.
BrightRidge protects a genuine neutral peak.65 over base.08, centre(148,138),
angle.70, Gaussian axes30 and1.4, focus2; convolution adds the same defocus sigma
in quadrature and preserves analytic flux. WeakColour has base.18, focus3,
frequency.09, red amplitude.035 along x/phase.31, blue amplitude.030 along(.6,.8)
with phase.7, and green amplitude.010 of each carrier. No fixture is selected
from an observed candidate output.

Four arms come from the actual consumer: canonical, canonical-field identity,
matched Monte Carlo linear guide, and fixed transformed guide. All are compared
after actual linear-CFA collapse/hull and MHC. Require original and independently
regathered known-four hashes, unique source/draw seeds, exact linear terminal
base and original gathered-input hull, and bit-exact canonical identity. One
Veil/ISO100 diagnostics-off call must preserve all four CFA/RGB output hashes.
No aligned-source volume is stored; independent regathers retain only extrema.

Fixed native windows are interior[38,42,280,244], Veil spill[138,133,171,167],
adjacent texture[180,96,224,192], core[112,110,133,132], and bright ridge
[120,110,178,166]. Pixel coordinates never move. Error means RGB, green and
R-G/B-G truth RMSE, with signed RGB bias also retained. For nomination every
window, including the flats, must be at most1.10 times both canonical and matched
linear error. Protected ridge, weak-colour, adjacent and core full-template
recovery must be at least90% of each reference's recovery capped to[0,1]; every
protected reference component must itself be>=.5. Lower reference recovery is
unexercised protection and cannot nominate. These historical nomination bars
were directed by root before any execution; no later relaxation is permitted.

In the Veil core, an additional independent choice separates texture and glint:
joint per-channel regression on intercept plus the two exact known truth
components. Record signed coefficients, template correlation, relative
determinant, rank and standardized two-template condition. Relative determinant
must exceed.05; both components receive the same90%/reference>=.5 rule. This
prevents a preserved glint from hiding lost texture. RMSE can reward smoothing,
coefficients can reward aligned false detail, and the intercept can hide a bias;
the absolute errors, separate true-bright case and both component guards therefore
remain binding together. No coefficient above one is credited as extra detail.

The positive is ISO100 Veil spill: at least5% lower RGB error versus BOTH
references, baseline errors>2 times their flat errors, positive baseline spill
bias>their flat error, actual changed source weights and changed candidate image.
ISO400 Veil is retained for preservation and its eligibility reported; the prior
same scene was unexercised at that ISO, so it is not manufactured into a second
positive. This restricted nomination does not claim high-ISO glare improvement.
No win from switching the floor estimator alone can pass the matched-linear bar.

Arithmetic controls independently choose unequal green gains .5/1.5 and read
noise2e, yielding a=.5, b=2.5, pedestal2.59375. Check the equivalent f64 centered
square-root expression, H(0), negative clamp, monotonicity, derivative1 at2000,
nonfinite refusal and live wrong-pedestal/transform-before-green-average
destroyers. Actual guide bands are checked against production Pyramid from
independently formed mean green. Eight paired floors on an odd89x73 grid are
checked against explicit differences/divisor16 and a separate clamped2D binomial
convolution; dark/bright halves make omitted-H floors wrong. Opposite green
perturbations must cancel before H. Wrong divisor, seven/ninth pair and nonfinite
inputs reject. These check arithmetic, not distributional variance stabilization.
The mean-G pedestal remains approximate after correlated MHC/gather; actual
conditional floors use the same nonlinear transform and all16 original-noise
draws, never a scalar white-probe beta. Quantization, clamping, noisy conditioning
and unchanged floor.max(1) in transformed units remain limitations.

Score commissioning rejects zero output, half detail, added colour noise, and
half texture with the glint held exact. Exact truth recovers both joint
coefficients as one. These are scorer destroyers, not extra image-render arms.

Four exact test suffixes in variance_stabilized_guide::independent_controls:
independent_transform_controls, independent_paired_floor_controls,
independent_metric_controls, independent_quality_screen. Root runs the first
three before the image screen. Outputenv STREHL_VARIANCE_STABILIZED_GUIDE_OUT;
screen.json status SCREEN_COMPLETE; marker VARIANCE_STABILIZED_GUIDE. Scientific
negatives remain structured results, not test panics. candidate_nominated is the
conjunction of quality_pass, positive_pass and positive_exercised;
photographic_replay_admitted remains false. A nomination permits consideration of
a separately authorized whole photograph/cost check, never default or SOTA status.
All sources freeze before the first compilation/execution.
