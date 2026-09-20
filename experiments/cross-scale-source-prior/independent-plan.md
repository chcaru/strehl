# Independent fixed coarse-source screen

Pre-execution choices; root builds and runs. The numerical author does not
verify the operator. This is one generated qualification for a photographic
counterfactual, not a calibrated optics model or a SOTA result.

The exact rule is the author's design.md: normalized finest weights, then
Gaussian reduction; coarse AC weights multiply that prior, while finest/base/
fallback/hull state stays exact. Zero finest support means a literal canonical
bypass. Mixed supports keep the uniform 1/N contribution from unsupported
sites. This is neither the retired radius32 finest-energy pool nor the rejected
categorical whole-AC source field. It can wrongly veto genuine coarse detail
whose focused source lacks fine texture.

Two tests are fixed. The operator test uses an asymmetric odd 17x13 quad field,
three sources, distinct weights and a half-field with no finest support. An
independent literal 25-tap reduction checks all pixels/levels including borders,
phase, uniform unsupported contributions, normalization order and exact bypass.
Wrong normalization-after-reduction and dropping unsupported contributions must
differ. Invalid shape, negative/nonfinite input, overflow and incomplete source
counts refuse. Off/Neutral return canonical fields literally.

The actual-consumer test uses five original-u16 generated 320x288 active arrays
inside sentinel-padded storage with odd decoded origin (7,11), RGGB active-local
phase, fixed warm WB (1.7,1,2.3), injected existing ILCE-7CM2 ISO100/400 noise,
the retained five fractional scale/rotation/translation pulls, and crop
(7,9,145,125) quads. Noise is independently seeded on original sensor samples;
the actual rounded GPU gather/probe/MHC/merge/developer consumes it. This tests
the injected model, not its calibration. No RAW, optical profile or new noise
fit is used. Twelve cases are fixed, flat first at each ISO:

1. Flat neutral 0.25.
2. Broad bright contact: a 32x48-native rectangle [108,116]–[140,164] plus
   genuine coloured sinusoidal texture at 0.075 cycles/native pixel, focused
   at source0. Gaussian sigma .65+3.2k broadens the contact through the stack.
   The rectangle is the separable Gaussian integral; the independent full-plane
   texture has its analytic Gaussian attenuation. Right outside spill window
   [142,118]–[164,162], interior [112,120]–[136,160], edge
   [92,100]–[158,180], and common whole interior are fixed.
3–4. Neutral and chromatic 3-native-pixel glints with area-preserving anisotropic
   blur and a distinct near textured half-plane/depth boundary. These are no-harm
   checks, not a required vitamin-fan repair. Core, extension, depth edge and
   near texture are retained fixed windows. Neutral uses one common glint angle
   and peak; chromatic uses three angles/peaks. The existing blurred near mask
   and premultiplied radiance are composed before sampling.
5. Strong adversary: transparent superposition of a fine near-depth texture
   (frequency .10, focused0) and genuine coarse far-depth colour structure
   (frequency .022, focused4). Their independent channel phases/directions and
   amplitudes are fixed. A joint two-template regression with intercept reports
   the two true components separately, so near detail cannot hide far loss.
6. Genuine coloured thin radial detail focused at source3 (width1.6, length24),
   retained from the previous generated screen. These rays are true structure.

At each ISO separately: flat RGB and R-G/B-G truth-error RMS <=1.05x current.
The broad-contact spill requires <=.95x RGB error. All other named structured
windows and the common whole interior require RGB and chroma error <=1.05x.
Every protected component requires current recovery >=.5 (otherwise UNEXERCISED)
and candidate positive recovery capped at truth >=.98x the current truth-capped
value. An over-contrasted current output is not a reason to reject removal of
manufactured contrast. Contact interior, glint core/near texture, both adversary
components and each radial colour are protected; spill/edge windows use error
rather than claiming their gradients are detail.

The contact positive is exercised only if baseline spill RGB error >2x the
same-ISO flat RGB RMS, baseline signed mean outside excess >flat RMS, and the
known defocused source's noiseless spill error >2x flat RMS. Its actual coarse
weights and output must change and canonical coarse selection must occur.
Otherwise admission refuses; no later window/blur/threshold rescue is allowed.
Glint extension strength is reported, not used as a benefit requirement.

One actual near/far case at each ISO also runs Off, Neutral and a forced wrong
coarse donor0. Off/Neutral must equal the actual baseline exactly, all source
storage/replay hashes and finest weights match, and the private b0/base/usum/
hull accumulator comparison must hold after every actual source. The forced
donor must really change coarse weights/output and fail far-component retention
or the structured error guard; otherwise the destroyer is unexercised and the
screen refuses. This is not a usable argmax source selector.

Metric commissioning passes exact truth, rejects halved true components and
neutralized genuine colour, and explicitly allows 1.4x overcontrast to return
to truth under capped retention. Lower RMS alone can reward smoothing, so
component retention and the live wrong-donor control are mandatory. Template
recovery alone can reward overshoot or miss other errors, so full RGB/chroma
truth error is mandatory too. No gradient energy is a quality metric.

Output: STREHL_CROSS_SCALE_SOURCE_PRIOR_OUT/screen.json, status SCREEN_COMPLETE,
12 cases, per-ISO quality/exercise decisions, photographic_replay_admitted only
when all pass. Rust success means instruments ran, not image admission. Marker
CROSS_SCALE_SOURCE_PRIOR. No full photograph is licensed by structural checks
alone, and all earlier closures remain preserved.
