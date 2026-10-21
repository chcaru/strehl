# Spatial Adaptive development

The previous Balance implementation changed global sliders. The user rejected
the resulting insect photograph because the stronger treatment brightened the
whole scene. Its earlier reviewer acceptance does not override that feedback.
This revision replaces that Balance path with image-specific spatial curves;
the separate regional **Balance highlights** operation remains available.

## Research and scope

Adobe describes Adaptive as a learned system trained on photographer-edited
photographs. It combines position-and-brightness-dependent tone curves with
global and semantic color tables. Its profile does not need to move the ordinary
sliders. This supports the user's distinction between a spatial treatment and a
global exposure suggestion. Strehl does not possess that model or its training
targets and does not claim equivalent rendering.
[Adobe Adaptive Profile, Kainz, Levoy and Jebe](https://blog.adobe.com/en/publish/2024/10/14/the-adobe-adaptive-profile).

The [HDRNet project](https://groups.csail.mit.edu/graphics/hdrnet/) predicts a
compact bilateral transform from a low-resolution image and applies it at full
resolution. The [official implementation](https://github.com/google/hdrnet) is
Apache-2.0, but is archived, uses a legacy TensorFlow/Python environment and
custom GPU slicing, and documents special preprocessing for its HDR+ checkpoint.
Its existing weights do not establish suitable macro-photograph or scene-linear
HDR behavior. The original [bilateral-grid paper and project](https://groups.csail.mit.edu/graphics/bilagrid/)
also demonstrate the useful separation of compact edge-aware processing from
full-resolution image evaluation. No implementation source was copied.

[Image-Adaptive 3D LUT](https://github.com/HuiZeng/Image-Adaptive-3DLUT) provides
an Apache-2.0 implementation and released models. Its small network combines
basis LUTs into an image-dependent global color transform; that core operator
does not independently treat identical RGB values at different locations. Its
documented FiveK training uses reduced-resolution photographs and SDR targets.
Code licensing alone does not establish redistribution rights for every dataset
or checkpoint. The original FiveK [Adobe license](https://data.csail.mit.edu/graphics/fivek/legal/LicenseAdobe.txt)
and [Adobe/MIT license](https://data.csail.mit.edu/graphics/fivek/legal/LicenseAdobeMIT.txt)
explicitly restrict image use to research and exclude commercial advantage.
That is not the permissive project license. This review has not established a
clear release basis for those trained weights, nor macro/HDR generalization.

A 5090 can accelerate training, but does not supply desired photographic targets.
A defensible learned follow-up would first collect consented before/after pairs,
split them by capture rather than crop, and compare a compact coefficient
predictor against this deterministic operator on held-out complete photographs.
Paired RAW-derived linear inputs, highlight-safe targets, flat/noise controls,
and target-domain color handling are necessary. No model download or training
has been represented as completed, and this implementation is not marketed as
AI, semantic recognition, Adobe compatibility, or missing-detail recovery.

## Implemented representation

Balance leaves manual controls unchanged. Bounded stratified samples build a
small lattice of local log-light statistics. Nearby brightness values share
support; remote brightness bands remain separated. Local and broader spatial
statistics produce restrained tonal redistribution and locally supported color
enrichment. A sampled centering constraint removes an overall working-light
increase. This constraint controls exposure placement, not photographic merit.

The frozen recipe stores at most 20 × 20 spatial cells, each with 33 tone-gain
samples over input log luminance. Original fields use one chroma multiplier per
cell; tone-selective fields also sample chroma over the same luminance axis.
Full-resolution
evaluation interpolates those coefficients using original image coordinates
and the current pixel's light. It does not blur or replace the source pixels.
Dark noise-floor values, near-delivery-white channels, neutral pixels and already
saturated colors receive separate protection. The same operation is consumed
by native viewport patches, overview rendering and export.
Coefficient arrays use compact, exact float-bit strings on disk, retaining even
interpolated Amount coefficients without lossy re-quantization. Six maximum
lattices plus 128 maximum-length ordinary text annotations fit the existing
2 MiB sidecar bound in the serialization control. This is not a claim that every
combination of maximum-length escaped text and maximum-vertex polygons fits;
the application must still report a size refusal rather than silently lose edits.

For a scene-linear master the ceiling follows the HDR target; imported SDR uses
its stored range. Above-white light is not automatically classified as clipped.
This is still RGB development after stack reconstruction and camera conversion,
not a camera-RAW demosaic or recovery of channels absent from an SDR TIFF.

`AdaptiveParameters` stores portable intent controls. `SpatialTreatment` stores
photo-specific coefficients and Amount. Reusable presets retain parameters and
recompute coefficients for the destination photograph; they do not transplant a
measured spatial field. Regional treatments reference an existing annotation,
leaving its shape, feather and source constraint intact. Disabled regions do not
apply their field. Validation rejects fields whose region no longer exists;
deleting an annotation clears its addressed field too.

Amount blends against the frozen base; zero returns that base exactly. A new
analysis replaces only its addressed scope. `gain_ev_at(uv, luminance)` exposes
the raw coefficient correction for diagnostic visualization; that value precedes
Amount, mask feather, black-floor and highlight protection and must be labelled
accordingly.

## Photographic controls

The photo pane calls this **Spatial light & color**. Choose a starting treatment,
then **Analyze** builds the field for the photograph or selected region in a
worker. **Natural** retains the original treatment. **Deep background** reduces
light balancing and protects dark areas; **Texture contrast** concentrates local
tonal separation in midtones; **Gentle highlights** concentrates its treatment in
bright areas and adds a soft highlight shoulder. Texture contrast does not
sharpen, reconstruct detail or establish optical resolution.

**Shape treatment** exposes Light balance, Local contrast, Color, a tone range,
Protect shadows and Soften highlights. Those choices are drafts until
**Recalculate** is pressed, so dragging a parameter does not enqueue repeated
image analyses. Ordinary Light/Color sliders remain independent.

Tone ranges overlap smoothly rather than cutting a hard brightness mask. They
select both local tone and color changes. Protect shadows progressively removes
those changes in deep values; its maximum leaves values at or below 1/64 of
working diffuse white unchanged. The light-placement constraint acts only
through the selected tones, so it cannot compensate by lifting a protected
background. Soften highlights is a separate, monotone shoulder with a knee at
55% of the delivery ceiling, sampled into the curves after that constraint.
It does not add a compensating
exposure lift elsewhere. Imported SDR and scene-linear HDR use their respective
delivery ceilings. This shoulder changes existing light; it cannot restore
texture or color absent from clipped input.

The new controls default to All light, no added shadow protection and no added
highlight shoulder. These defaults retain the original coefficient format and
rendering. Tone-selective fields use version 2 of the portable recipe, with
continuous Amount interpolation across the two versions. Presets carry the
intent and remeasure the destination image, rather than copying measured curves.

The persisted field has an absolute Amount control, including after reopening a
photograph without a cached analysis. Zero disables that addressed field while
retaining its curves for instant restoration. The shared control handles numeric
entry, dragging and double-click reset. The separate Balance highlights action
still edits regional highlights and reports the limitations of clipped input.

**Where it changes** optionally shows a bounded sampled effect map. A worker
compares actual developed pixels with and without the addressed field, including
baseline placement, other edits, region feathering and highlight protection.
Warm tint indicates lifted light, cool tint deeper light, and violet color change.
These tints are amplified for visibility; they are not a contribution map or a
detail-recovery score. The existing thumbnail stays in place during a refresh,
and replies for a different image or scope are discarded. The map has no effect
on rendering or saved pixels.

## Original treatment verification

**VERIFIED, October 21, 2026:** the fresh core build passed 52 tests, including
14 Adaptive and five spatial controls. Controls include
equal RGB under different neighborhoods, flat/noise/black controls, hard-edge
halo detection, bright channels, monotonic light order, regional support,
full-image versus native-region coordinates, recipe round trips, exact Amount
zero, retained effective Amount when recapturing a preset, missing-region
refusal, and bounded serialized size. The initial size test failed at 2,429,663
bytes; compact exact coefficient serialization corrected that real defect. A
native-patch test initially compared an SDR gamma round trip with direct linear
samples and differed by one float ULP. The corrected exact test uses the same
scene-linear operation at native resolution, while existing SDR controls check
the actual byte output. The original failed log is retained.

```powershell
$env:CARGO_BUILD_JOBS = '4'
$env:CARGO_TARGET_DIR = 'target/progressive-photo'
cargo test -p strehl-edit --offline
cargo build --release -p strehl-edit --example adaptive-review
$env:RAYON_NUM_THREADS = '4'
$tool = 'target/progressive-photo/release/examples/adaptive-review.exe'
& $tool outputs/feature-validation/insect-run/result.tiff outputs/adaptive-spatial-review/insect
& $tool outputs/quality-october20-slide/repair/linear-master.tiff outputs/adaptive-spatial-review/slide
& $tool ../strehl-1792368598430-22840-1/result.tiff outputs/adaptive-spatial-review/garnet
python outputs/adaptive-spatial-review/prepare-views.py
python outputs/adaptive-spatial-review/measure-output.py
```

The three existing photographs are 7032 × 4688. Insect and garnet are imported
SDR outputs; the slide is an existing scene-linear master. The slide's earlier
source-repair experiment was rejected as a stacking-quality improvement; using
it here evaluates development of fixed pixels, not that repair. Originals were
read only. Every complete before/Amount-zero TIFF pair has the same SHA-256.

**MEASURED:** one analysis observation per photograph was 13.79 ms, 18.87 ms and
13.70 ms respectively, sampling 16,328 pixels. These single observations exclude
import, rendering, GPU submission and UI latency; they are not a performance
benchmark. Typical serialized recipes were about 72 kB.

| Photograph | Complete SDR display-linear mean, after / before | Encoded max-channel change, 90th percentile, 8-bit scale |
| --- | ---: | ---: |
| Insect | 0.999917 | 3.73 |
| Slide | 0.999623 | 2.05 |
| Garnet | 1.000137 | 0.46 |

These are behavioral measurements: the mean checks broad light placement, and
the difference measures change. Neither can establish photographic improvement;
more difference can be worse, and a constant mean can conceal damaged regions.

An independent reviewer viewed all six complete before/after images before
crops. They found stronger insect cellular/plate separation without broad
brightening, a substantially stable slide, and a subtler garnet change with its
dark setting retained. Existing glare remains visible. No broad new bright-edge
halo was apparent at that viewing scale. This is a restrained treatment, not a
transformative result or Adobe parity. The same independent reviewer then chose
four 800 × 800 native crops: insect plate junction and relatively flat green
texture, garnet glare/dark boundary, and a calibration-chart edge. They found no
conspicuous new edge bands or granular/sharpened pattern in those regions. The
garnet glare remained clipped. This limited inspection does not establish a
universal no-halo or no-noise guarantee. User preference remains a separate
acceptance decision. The earlier global-treatment reviews are historical, not
acceptance of this operator.

The [delivery verification](spatial-export-verification.md) records final native
Edit/Export screenshots, live MCP pixel/Undo controls, preset and persistence
regressions, and bounded worker timings on the optimized executable.

## Tone-selective options verification

**VERIFIED, October 21, 2026:** a fresh core build passed all 57 tests. Five new
option controls exercise selective light placement with a deliberately incorrect
offset as the failing arm, exact dark/color exclusions, flat-noise and hard-edge
plants, monotone hue-preserving highlight compression, unchanged default wire
format, native-region/full-image agreement, and continuous interpolation between
old and new field versions. Uniform bright input can be compressed but remains
uniform. The pre-existing sidecar-size control now uses six maximum version-2
fields. Strict all-target edit Clippy passed after removing one redundant default
initializer from the review example; the first failed lint log is retained.

The full-photograph run uses the same three inputs described above and renders
all four UI choices. Every Natural RGB16 output is pixel-exact to the earlier
Natural output. For all twelve image/option combinations, Amount zero returns
the exact base recipe and every complete RGB16 pixel unchanged. These are
compatibility controls, not evidence of photographic superiority.

```powershell
$env:CARGO_BUILD_JOBS = '4'
$env:CARGO_TARGET_DIR = 'target/progressive-photo'
cargo test -p strehl-edit --offline
cargo clippy -p strehl-edit --all-targets --offline -- -D warnings
cargo build -p strehl-edit --release --example adaptive-options-review --offline
$env:RAYON_NUM_THREADS = '4'
$tool = 'target/progressive-photo/release/examples/adaptive-options-review.exe'
& $tool outputs/feature-validation/insect-run/result.tiff outputs/adaptive-spatial-review/options-insect
& $tool outputs/quality-october20-slide/repair/linear-master.tiff outputs/adaptive-spatial-review/options-slide
& $tool ../strehl-1792368598430-22840-1/result.tiff outputs/adaptive-spatial-review/options-garnet
python outputs/adaptive-spatial-review/prepare-option-views.py
```

**MEASURED:** the example warms each option once, then runs four alternating
forward/reverse sweeps. Each analysis uses 16,328 stratified samples. The table
reports the minimum through maximum of four observations, in milliseconds,
with four worker threads. It measures analysis only, excluding TIFF import,
full-resolution development, upload, rendering and interaction latency. The
small differences between options are a cost bound on this machine, not a
general speed ranking, quality score or frame-rate claim.

| Photograph | Natural | Deep background | Texture contrast | Gentle highlights |
| --- | ---: | ---: | ---: | ---: |
| Insect | 12.97–13.31 | 13.75–13.99 | 13.71–14.29 | 13.50–13.68 |
| Slide | 17.02–17.16 | 17.41–17.57 | 17.64–17.71 | 17.28–17.44 |
| Garnet | 12.82–13.02 | 13.22–13.36 | 13.25–13.35 | 13.15–13.29 |

Local receipts are retained in `outputs/adaptive-spatial-review/options-summary.json`
and each option folder, with the exact parameters, complete output hashes,
timings and zero-Amount controls. The source photographs were read only.

An independent reviewer viewed all fifteen complete before/options photographs
before choosing native-resolution crops: insect bright border, plate seam and
low-detail green area; garnet reflection and black background; slide flat ramp
and high-contrast boundary. They found no obvious new bright edge outline,
broad background lift or color damage in those views. Gentle highlights modestly
dims the garnet reflection while its clipped center remains textureless. Its
insect effect is subtle and the chart remains essentially stable. Texture
contrast adds restrained insect plate separation. The reviewer accepted these
as optional, restrained treatments, not a transformative correction, recovered
detail, solved glare/occlusion artifacts or demonstrated quality superiority.
This supports visual non-regression for the inspected scenes and regions only.
The independently chosen crop coordinates and images are retained beside the
receipts in `independent-option-crops.py` and `independent-option-crops/`.
