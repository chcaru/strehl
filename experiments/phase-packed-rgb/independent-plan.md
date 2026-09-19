# Independent screen fixed before execution

This is one test-only screen, then at most one paired photographic replay.
It does not change the default or claim universal metric dominance. The
implementation author does not choose or verify the acceptance numbers.

## What is and is not new

The candidate retains all three RGB values already reconstructed by the
existing MHC/Catmull source gather at each of four native CFA phases. Twelve
quad-scale planes carry these values through the existing green-driven merge,
then reassemble co-sited native RGB without the second MHC operation.

This differs from September14's rejected single-frame demosaic replacements
and joint CFA inverse reconstruction. It changes the actual merge's retained
representation, not the initial demosaic or inverse solver. BUILD-DEMOSAIC
already compared a one-demosaic reference at the single-frame warp stage and
found a tradeoff: better true-colour error but worse flat-noise and some neutral
error. It did not implement this twelve-plane focus merge. V-GATHER's old
chroma-high-pass increase was not proof of a double-demosaic defect; that metric
can reward correlated R/B errors. M95's binned colour co-siting is a different
geometry and does not justify combining four native phases into one pixel.

## Frozen generated inputs

Use five original u16 CFA frames, native active extent 320x288, unequal row
stride, odd decoded active origin, and plane crop (7,9,145,125). This reaches a
small actual pyramid whose attained band count must be recorded, never called
a full seven-band render. Source observations come from direct evaluation of
analytic continuous scenes through independently inverted source transforms;
no resampler generates the planted motion. Original source storage stays u16.

There are two map sets: all coincident identity and fixed fractional motion.
The latter has source-native translations (-0.46,0.32), (0.37,-0.21), (0,0),
(0.23,0.44), (-0.18,-0.39), with small fixed scale/rotation changes about frame
two. Test noise at ISO100 and ISO400, using the injected existing profile to
draw seeded independent sensor noise. This validates the consumer, not the
camera calibration; sharing a noise constant cannot validate that constant.

At each noise level and map set, run flat radiance first, then neutral waves
and independently coloured waves at native frequencies 0.08 and 0.18, a
neutral 0.30 diagnostic, and an independently coloured spatial-defocus field.
The defocus field has different positions sharp in different frames, so it can
express failure from spatially varying selection; a fronto-parallel target
cannot. Underlying colour components remain independently specified. The
same fixed radiance/noise realization is supplied to both actual consumers.

An explicit synthetic nonzero CA control compares all gathered channels at
all four native positions with the existing full-frame MHC/Catmull oracle.
Each output colour needs that colour's CA pull at the destination phase;
using the site's original CFA colour for every channel is incorrect.

## Structural requirements

The four known-site gathered planes and collapsed outputs must be bit-exact
between arms. Original CFA data must remain unchanged. Green luma, injected
variance, probe beta, merge configuration, frame order and weighting path must
be shared. All twelve channels must be finite and placed at their actual native
positions. Explicit channel/phase swaps must disagree on a colour fixture.
Unsupported source stencils must refuse rather than silently synthesize data.

## Quality admission for one replay

Report per-case RGB and true-chroma RMSE in linear camera units, and recovered
in-phase amplitudes of independently specified true colour components. Truth
RMSE can reward blur, hence the component-preservation requirement; component
amplitude can reward added artifacts, hence the truth-error and flat controls.
No gradient or chroma-high-pass magnitude counts as quality evidence.

For each tested noise level separately, at least one genuine-colour case must
improve RGB or true-chroma RMSE by at least 5%. No genuine-colour component that
the baseline recovers at least halfway may lose more than 10% of its baseline
recovered in-phase amplitude. Recovered amplitude is capped at the true
amplitude in both arms: contrast above truth is not extra recovered signal.
Flat RGB and chroma RMS may rise by at most 25%, assessed
separately at each noise level and map set. Report neutral regressions openly;
they do not automatically reject a mixed but potentially useful tradeoff.

These are the root-approved bounds for one photographic replay, not final
promotion. Do not pool away a failure at one noise level. No parameter sweep,
demosaic replacement, new noise fit, or threshold adjustment follows a failure.
A passing screen still needs an identifiable photographic gain and preservation
of genuine colour in independently reviewed matched native views. Full images
and the RGB16 master must accompany any reported photographic improvement.

Pre-run amendment, before any numerical execution: root identified that a raw
baseline-relative amplitude bar would penalize removal of baseline contrast
above truth. The recovered-signal cap above repairs that failure direction.
All fixtures, the 10% recovered-component bound, and the RGB/chroma/noise
thresholds remain fixed. Raw in-phase and quadrature amplitudes are still
reported, so the cap does not hide overshoot.

## Full-source adapter extension, before its first execution

The admitted photographic adapter adds a full-source MHC gather, so it needs
a separate structural check; passing the saved-patch implementation alone is
insufficient. Reuse the existing generated colour fixture with its odd active
origin and unequal row stride. Require all twelve full-source planes to equal
the saved-patch gather in the supported interior, and its missing-eight mode
to equal slots 4 through 11 exactly. Independently compare all twelve phases
with the existing CPU oracle at a near-sensor-edge crop, using fractional
placement and nonzero colour CA; the retained-patch route must refuse this
crop because its stencil policy is deliberately stricter than the real sensor
edge policy. Source CFA storage must remain bit-identical.

Exercise the all-channel support decision with a fixed blue expansion whose
known B site remains covered while a missing B phase leaves support. The
existing oracle must witness both facts, and the full-source predicate and
gather must refuse the twelve-plane crop. Also check finite placement refusal
and the exact inclusive sampler support boundary. This can fail if only the
old four sites are checked, if CA follows the destination CFA instead of the
output channel, if sensor edges receive retained-patch filler, or if active
coordinates are confused with the decoded buffer origin.

Inspect and, where exposed, exercise paired canonical chunk reduction: the
four-plane baseline determines both arms' chunk ranges and absorption order.
Do not let the twelve-plane allocation change floating-point reduction groups.
The photographic pair must share levels, white balance, current map bits,
crop, full pyramid sizes, tone settings and the actual output developer.
These are structural extensions, not a second quality sweep or changed gate.
