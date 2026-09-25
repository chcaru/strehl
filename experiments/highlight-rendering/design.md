# Fixed highlight rendering factorial

Test-only, root-executed, display-only experiment. Four output arms consume the
same complete merged f32 CFA object: current; existing sensor chroma roll-off
disabled while pinned-sensor clipping remains; a post-tone luminance shoulder;
and both changes. No alignment, focus measure, merge, optical correction,
white balance, exposure, crop or source count changes. No production default.

The shoulder is fixed before results. For y<=0.75, f(y)=y. Above 0.75,
f(y)=0.75+0.25*(1-exp(-(y-0.75)/0.25)). The implementation uses expm1 for
accuracy close to the knee. This is continuous with slope one at the knee,
strictly increasing in real arithmetic and asymptotic to one. Floating output
can round to one at extreme inputs; no claim of arbitrary highlight recovery.
One gain f(y)/y multiplies all three linear sRGB channels after current tone
placement/exposure and before the existing gamut map. This preserves their
ratios before gamut, not perceptual hue through every subsequent operation.
The upper-quarter knee is a deliberately simple fixed diagnostic allocation
of highlight headroom, not a measured optimum or camera constant.

The sensor-off arm calls the actual Render::clip_highlights and matrix, omitting
only highlight::desaturate. It must not resurrect the pinned-neutral magenta
defect by bypassing pin protection. Existing sRGB encoding and display-space
S-curve remain identical. Both interventions are pointwise; neither can claim
to correct spatial ghosting, resolve added detail or remove an occlusion halo.

Tone is measured through the existing tone_from_mosaic and current
Render::develop for every arm. The pixel override does not affect that path.
Actual resolved Tone/exposure/matrix/ceiling f32 bit patterns are recorded once
per write and must match across the complete factorial. Thus disabling sensor
desaturation is not confounded with remeasuring tone on a new color distribution.
The cache's exact exposure value is replayed through actual write_merged,
including its upstream scaling and explicit post-tone exposure handling.
No decimal reconstruction from rounded render logs is permitted.

The shared cache reader belongs to full-stack-source-prior. Its frozen
CacheMetadata getters expose the literal complete collapsed f32 object and
metadata. A Current pass goes through actual write_merged and must exactly
match every RGB16 sample and ICC of the declared retained full master before
any candidate arm runs. An observer-disabled and Current-observer pair must
also produce byte-identical complete TIFF files. Cache metadata/binary,
retained input image and all merged plane hashes remain unchanged.

The independent author supplies four control tests and a separate plan.
Successful tests commission the experiment, not photographic improvement.
Whole-image pairs and full-resolution masters are mandatory; native inspection
uses the independently frozen regions at <=400-pixel unresampled extent.
White-count reductions and global dimming are not quality claims. Protect real
colored highlights, visible grains/facets, fine hairs/petals and dark texture.
A null or damaging fixed arm closes rather than triggering a parameter sweep.

Prior evidence constrains this interpretation. M109-highlights.md established
the pinned-neutral defect and pre-matrix clipping remedy; that protection is
retained. BUILD-HIGHLIGHT.md and its independent V-HIGHLIGHT.md verified the
sensor chroma roll-off, including its below-knee null and real colored-highlight
risk. V-HIGHLIGHT's later flower-bud prediction was refuted: its fringe stayed
byte-identical because the pixels did not reach the sensor knee. BUILD-OUTPUT
section 2 likewise found the old flowers-cpl knee .60/.45/.30 sweep inert when
the gamut boundary arose downstream in tone. This factorial changes no knee:
it isolates the existing desaturation factor, then tests a distinct downstream
luminance shoulder. M97c-clip-mass.md provides weighted clip evidence for the
legacy estimator; that producer is not present in these cached pyramid planes.
The cache cannot retrospectively supply per-contributor clipping provenance.
No output-channel ceiling count is labelled RAW clipping or physical glare.

Implementation author writes source only; root builds/runs and independent
reviewers judge source, controls and photographs. The minimal driver consumes
a shared fresh build and has controls/replay/views phases. Replay allows 240
seconds wall, 1200 seconds CPU and 8 GiB process-tree committed memory. These
are bounds, not measured speed or memory claims. One merged object is replayed,
not a stored aligned-frame volume; no RAW source is opened by the replay.
