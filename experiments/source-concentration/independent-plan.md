# Independent controls for the fixed concentration locator

This is a display-space nomination/refusal diagnostic. Root runs the controls;
the locator author does not verify them. No RAW, new stack render, camera noise
fit, source radiance estimate or automatic correction is authorized here.
The existing automatic-design.md thresholds remain fixed. A failed known case
closes this exact discriminator; no radius, contrast fraction or frame sweep.

Use only the actual pure locator API. Generated normalized RGB supplies its
own known shapes and noise amplitudes, so these controls can test coordinate
assignment, feature identity and nomination, not camera calibration. Real
source TIFFs receive no quality/noise claim from passing these controls.
Every generated image includes the complete radius64 filter margin outside
the radius64 measurement support. Missing support is refused, never padded.
Local contrast's returned64-pixel crop changes the source origin explicitly.

Eight groups, fixed before results:

1. **Nulls first.** Constant RGB, independent seeded noise at amplitudes0.0002
   and0.002, and an unchanging bright narrow Gaussian point across31 frames.
   No stable nomination is permitted. The noise is supplied synthetic noise,
   not an estimate. The persistent point exercises the contraction condition;
   a separate single-pixel component exercises singular covariance refusal.
2. **Coordinates and true pixels.** Independently compute a nonidentity
   similarity inverse with nonzero sensor pivot, source crop origin and output
   offset. Check original pixel centres, half-open2-native maximum bins and
   fixed seed ordering. A known elliptical source-pixel field tests weighted
   mass/centroid/covariance against literal selected source pixels in reference
   coordinates; no interpolated image is created. Translation/rotation/scale,
   axis or phase mistakes must fail. Copy/hash source arrays for immutability.
3. **Compact glint versus late fan.** A conserved-mass Gaussian has its compact
   focus at frame10 of31; sigma=2*(1+0.065*abs(index-10)). A long off-centre fan
   appears later. The admitted compact track must nominate10 within one frame,
   and reversing the sequence must transform that label. A rule that elects
   the brightest late off-centre ray fails. The planted isolated contraction
   is a required positive witness, not an allowed universal abstention.
4. **Genuine coloured thin detail.** Independently focused R-only and B-only
   elongated Gaussian features lie beside the glint, with focus20 and fixed
   intrinsic axes8 and1; true blur sigma=.7+.19*abs(index-20), with analytic
   flux-preserving convolution. Later fan support approaches/crosses the thin
   feature. Its track must retain its own focus within one frame or explicitly
   refuse; it may never borrow10. Include a one-frame sharp opportunity with
   defocused immediate neighbours: abstention is valid, silent replacement is
   not. Require measured component size/covariance change to show a live thin
   fixture, rather than crediting a missing track.
5. **Competing identity.** Two disconnected bright peaks within the8-native
   search disk, plus a connected crossing-depth example, must trigger the
   documented ambiguity or other explicit geometric refusal when identity is
   unresolved. Transfer brightness between neighbours; do not permit a label
   based merely on following whichever peak becomes brightest. A perfectly
   separated/known component is not used to demand impossible ambiguity.
6. **Flux and clipping sabotage.** Replace a defocused source by a faint compact
   remnant, below the frozen mass/peak eligibility fractions. Its small radius
   must not win; record its explicit ineligibility. A bright component with
   display-ceiling contact must be unknown/ineligible. This does not identify
   original RAW clipping. Controls distinguish excluded damaged frames from
   whole-track refusal where no intact stable contraction remains.
7. **Genuinely sharp late radial structure.** A fixed three-direction thin
   radial feature is blurred through focus, genuinely sharp at20 of31. Its
   late nomination and reversed label are required positive witnesses; a rule
   that categorically rejects radial shape or late focus fails. Keep its real
   long-axis structure, not a point relabelled radial. If the frozen rule cannot
   express the known focused feature, report that failure, not improved noise
   or a reason to shorten the feature after viewing results.
8. **Track mechanics.** Literal measured records test minimum end distance5,
   neighbour/plus-minus5 conditions, an interior contiguous minimum plateau
   using the lower middle tie convention, separated equal minima refusal, and
   constant-size refusal. These are arithmetic controls, distinct from the
   image-driven quality/identity tests above.

All outputs retain every decision and refusal reason used by the controls.
No sharpness/gradient, source-selection-map smoothness or low-radius value alone
is a quality gate. Apparent concentration can be fooled by flux loss, clipping,
component breakup and identity transfer; those are explicit destroyers above.
The real-data runner must additionally retain every seed/track and test whether
the frozen core/fan pair belongs to the same observed footprint. Successful
controls license only that locator scan, not a merge or an image-quality claim.

Implementation details fixed before the first run: images are336x288 with
background0.18, glint centre(144,144), thin centre(194,144). Glint peak at focus
is0.35 with channel factors[1,.8,.65]. The later fan is an elliptical Gaussian
centred(166,144), axes15 and1.3, peak0.12, channel factors[.5,.8,1], introduced
linearly from frames15 to20 and then held. Thin features use peak coefficient
0.32 and analytic convolution normalization8/(sigma_major*sigma_minor). The
one-frame opportunity has blur2.6 elsewhere. The genuine radial stimulus sums
three such thin features at angles0,60 and120 degrees with equal thirds and
channel factors[1,.65,.8]. Its feature extent is preserved; there is no endpoint
or parameter search. The faint remnant is at22, sigma0.7 and peak0.025. Ceiling
contact uses a peak1.4 Gaussian clipped at1 before contrast calculation.

The isolated thin feature at15 and20 must produce measured covariance/radius
change greater than10%; that commissions its changing minor width separately
from legitimate geometric refusal when the fan crosses it. For non-null image
controls, all seed locations are retained and only seeds within8native of the
known planted target are measured across frames; a missing or multiple such
seed fails. Null controls measure every seed. This target association is a
known-answer control convenience, not permission for the real scan to discard
other tracks. Reversal reuses the measured image records in reverse source
order, with indices replaced; no second seed-field order or image warp is needed
because its maximum field is order-independent.

Command for root: `python -X faulthandler experiments/source-concentration/independent-controls.py --output experiments/source-concentration/controls-1/output`.
The script writes every tested decision and any harness exception, executes
nulls first, and refuses real-scan admission if any group fails or is unexercised.
