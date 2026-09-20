# A separate in-focus output question, not a repaired pinhole result

READ-ONLY ASSESSMENT. The original design explicitly returns and scores
`P=alpha*N+(1-alpha)*F` before the supplied common optical-floor PSF. Every
original-CFA prediction applies that floor. Thus the current pinhole question
does ask the inverse to remove the common in-focus blur as well as defocus.
The user's stacking objective does not by itself require recovering an
unblurred pinhole image. A separate output `O=B(P)` is defensible as an ideal
all-in-focus image retaining the supplied optical floor. It is not a physically
simultaneous exposure at both depths, nor a calibrated A7C II optical target.
The Gaussian sigma.7 is supplied fixture data, not measured camera knowledge.

Use exactly the existing normalized separable PSF, sigma.7, radiusceil(4*sigma)=3.
Compose the pinhole first, then filter; blurring sheets before composition is
different. Apply once to every retained fitted latent pinhole, original-Huber
included, and once to the same latent truth and truth-component templates.
Filter full96x96 arrays before scoring the unchanged supported16:80 domain
and existing local boxes. Their PSF aprons fit inside the full arrays. No
cropped-region filtering, fitted sigma, sharpening, colour rescaling or refit.
This is a saved-output consumer comparison with separately declared bars;
all previous pinhole rejections remain rejections.

**Do not double-blur observed comparators.** The original mean and oracle
exports are bilinearly developed sensor observations, already carrying the
optical floor and their source defocus. They are not pinhole estimates. If used
against the new B(truth) target, retain these delivered images unchanged and
label their origin. Applying B again would unfairly handicap them. The existing
oracle source choices were made against the old target and remain frozen;
it is not an optimal bound for the new estimand. A normal production focus
stack also already contains captured optical blur; this proposal is not an
instruction to blur the actual stacker's delivered photograph a second time.

The decisive mechanics are a constant field and a one-layer source at its
supplied focus: with zero pupil shift, its forward RGB must agree with B(P)
on supported pixels. Verify the same kernel, phase, support and single
application for all latent arms. Independent truth-component projections must
use B(template) and B(absent truth), so retained colour/ridge components remain
measurable in the new target's units rather than being rewarded or punished for
expected optical attenuation.

The decisive quality destroyers are (1) remove half of a genuine coloured
filament/glint component before the fixed PSF, and (2) apply a second identical
PSF to the otherwise exact new target. The first must fail true-detail/colour
retention; the second must expose oversmoothing wherever the fixture has
transmitted detail. A colour-swap or chromatic perturbation that survives the
PSF should still fail chroma error. Commission these against the new target
before reading candidate scores; if the tests cannot reject those losses,
lower noise alone cannot admit a candidate. Retain flat first, actual RGB and
chroma errors, component undershoot/overshoot and whole native scene views.

Filtering can hide high-frequency reconstruction errors and attenuate genuine
detail simultaneously. Equal filtering of target and fitted arms makes the new
question honest, but not automatically useful: it deliberately stops testing
frequencies beyond the chosen in-focus transfer. A pass would concern this
discrete known-optics/known-alpha consumer only. It would neither validate the
old latent estimates nor solve the failed pupil-resolution check, unknown
visibility, native real-RAW comparator or SOTA evidence requirements.
