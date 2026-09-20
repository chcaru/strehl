# Joint RAW reconstruction: bounded prior-art audit

2026-09-19. **Verdict: the exact joint inverse is untried in the searched
record, not empirically killed.** This licenses considering one small solver
test, not assuming that inverse rendering will fix the photographs. Read-only
search: `prior_art.py inverse deconvolution layered radiance`, targeted content
searches, and the reports below. No implementation, tests or RAW reads.

**What actually lost.** M115-deconv-headroom tested **multi-frame**, not
single-frame, Wiener/matched filtering. It found little matched-contrast SNR
headroom, substantial ringing, and a defocus-OTF self-calibration that did not
describe its real spectra. It did not jointly estimate a spatial latent image,
depth and finite-aperture visibility. M41's decisive failure was noise from
diffraction inversion; M20's broad claim was narrowed by M20-VERIFICATION,
including rejection of its circular optical-model gate. These forbid treating
an assumed PSF or inverse-frequency gain as established physics; they do not
test the proposed coupled inverse.

M87-occlusion §§4–5,10 implemented two-layer unmixing: supplied/propagated
foreground depth generated alpha, then each pixel fitted an intercept and slope
across frames. It reconstructed its plant but missed its real-data target;
wrong layer order could catastrophically damage truth while improving the
artifact metric. Textured foreground radiance varying with focus violated the
fixed-slope model. This was not joint spatial radiance/depth fitting. The older
DualFocus attempt in A-prior-corpus F11 used a weighted-mean AIF data term, not
forward defocus. Relative-blur-evidence fitted two already observed images;
its restricted Gaussian family partly transferred at the facet, failed the
dark window, and could not represent every tail within its support. None
reconstructed one latent scene from all original observations.

M79-edof-microscopy-survey records published joint texture/topography and
layered radiance methods, with explicit transfer limits. M194e-joint-pupil
independently commissioned a coupled pupil-ray visibility/radiance **forward
model**; M194f/g fed its CFA fixtures through ordinary merge tests. They did not
invert it. Thus no recorded result specifically kills joint fitting here.

**One practical first model (ARGUED).** Use two ordered opaque depth layers:
two nonnegative camera-linear RGB radiance sheets and a per-pixel foreground
matte, giving a two-valued depth map and explicitly retaining hidden background.
For each fixed pupil ray, intersect both layers, composite visibility and
radiance on that same ray, integrate the sensor cell, then sample the original
CFA through the held source geometry/CA. Do not multiply independently averaged
visibility and radiance. The first small all-frame solve fixes supplied focus
coordinates and a nonzero in-focus PSF; jointly optimize the sheets and matte
with alternating radiance-gradient and depth-label/matte updates. Freeze one
regularizer and work budget. Do not also learn an unconstrained pupil, per-frame
gain or alignment. Real-stack focus/PSF calibration remains an explicit later
requirement, not a camera constant or a frame-index ramp assumed true.

GPU tiles can accumulate forward residuals and adjoint gradients over one
original u16 source at a time, retaining O(image) latent state rather than an
aligned-frame collection. Use the injected noise model in original DN units;
known saturated codes contribute a censored likelihood, not an equality to
white. Unknown clipping authority refuses that likelihood. Fit original CFA,
not MHC RGB; render the reconstructed output once. No inverse-OTF division or
claim to recover diffraction-null information is required. Runtime is unmeasured.

**Decisive first falsifier.** Reuse the independently generated joint-pupil
two-depth crossing: a bright near glint obscures a genuinely fine coloured
far ridge, with unclipped observations of each protected feature and a flat
region. Include its no-glint twin and one fixed chromatic/asymmetric-PSF
mismatch arm generated independently of the solver. Require delivered colour
and ridge truth improvement over the actual canonical stack in the matched
case, without flat-noise or twin damage; mismatch must not erase the ridge or
invent texture. Score only truth visible somewhere in the inputs, separately
from unobservable hidden radiance. Lower training residual, nicer depth, and
out-of-input-hull values alone prove neither success nor failure. A wrong
depth sheet can explain blur by painting false latent texture: this test must
expose that reconstruction error before any real-stack optimization.
