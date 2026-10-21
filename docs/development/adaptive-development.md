# Adaptive development

Adaptive is an original, deterministic photographic starting point. It proposes
ordinary editable controls rather than introducing another hidden rendering
pipeline. It does not use a learned model, reproduce Adobe's AI profiles, infer
the subject, invent texture, or automatically change the default stack rendering.

`analyze_adaptive(image, recipe)` returns the frozen base recipe, a suggested
recipe, sampled before/after statistics, explanations for each changed control,
and limitations. `analyze_adaptive_region(image, recipe, region_id, intent)`
targets an existing region, with either `Balance` or `RestoreHighlights` intent.
The UI calls the latter **Balance highlights** because it compresses existing
light, without promising reconstruction. `suggestion.recipe_at(amount)` blends from that frozen base at
amounts from 0 to 1. Amount zero returns the original recipe exactly. Moving the
slider does not reanalyze the photograph or accumulate previous slider changes.
Analysis belongs on a worker; applying a cached amount is inexpensive.
Magic selection and Adaptive use action order: Adaptive cannot start while Magic
is pending, and a newer Magic action invalidates an older Adaptive reply even
when Magic is subsequently cancelled. Neither action fabricates a recipe change
merely to invalidate the other.

## Metering and treatment

At most 16,384 pixels are sampled in a deterministic, spatially stratified,
jittered pattern. Small images use all their pixels. Metering includes the
recorded display placement and existing global controls, while excluding painted
local adjustments. Local regions, source constraints, HDR settings, temperature,
tint, saturation and black-point controls remain intact.

The suggestion uses the central luminance distribution to decide whether there
is room for a small exposure correction, restrained contrast, or a limited shadow
lift. A predominantly dark background, bright-key composition, or strongly
separated dark/bright composition retains its exposure placement. The last case
prevents a black/white calibration target from being mistaken for underexposure
merely because its median falls in the dark part. Nearly uniform or nearly black
images receive no suggestion.
Interleaved sample sets flag unstable metering. This guard is useful but does not
prove that bounded samples represent every tiny subject.

Color adjustment uses at most 24 points of the existing vibrance control.
It requires at least 5% of non-dark samples to have relative chroma between
0.10 and 0.95 and a linear channel span of at least 0.035. The amount scales with
the square root of that measured support. The rendering operator attenuates the
lift per pixel as saturation rises; a second scene-wide suppression no longer
reduces already modest color edits to nearly zero. Neutral pixels remain
neutral, and a few colored outliers do not trigger a boost. No gray-world or
automatic white-balance assumption is made.

Highlight treatment is delivery-aware. For a scene-linear master, the linear
ceiling is the chosen HDR peak divided by reference white; for an imported SDR
photograph it is 1.0. Headroom above diffuse white is therefore not mistaken for
SDR clipping. Compression starts near the selected ceiling and does not clamp
the master. Inspect on an HDR display or in the HDR export; SDR presentation may
clip retained headroom. This is a tone choice, not recovery of sensor-clipped
detail.

Before returning the candidate, the implementation checks its actual operators
on the sampled RGB values and a logarithmic neutral ramp. It first fits bounded
highlight compression to protect the sampled delivery ceiling, preserving useful
midtone and shadow changes. It reduces or declines the whole suggestion only if
that protection cannot avoid additional sampled above-ceiling channels or if it
reverses neutral light order. Counts are working-space linear channel checks,
not a calibrated quality score or a measurement of final AVIF gamut clipping.

The policy constants are deliberately conservative creative choices, not fitted
camera constants or universally optimal photographic settings. The result is a
reviewable suggestion, not an automatic quality verdict.

## Regional treatment

The regional analyzer meters stratified pixels inside the annotation's bounding
box where feather weight is at least one half. The actual recipe, including the
selected feather and other overlapping edits, participates in analysis. Only
the selected region's tone controls change: its shape, feather, name, source
range, other regions, global controls and HDR settings stay intact. Disabled,
missing or subpixel regions fail explicitly. This is an instant photo adjustment,
independent of the separate source-repair operation that requires another stack.

Balance highlights fits the existing Highlights control toward a lower bright
95th percentile. It changes neither exposure nor color controls. A diagnosis
reports current bright/above-delivery support, the fraction of SDR pixels with a
channel at or near stored white, and unedited source luminance variation at the
currently bright locations. Measuring variation on the unedited source prevents
a feathered exposure gradient from masquerading as recorded detail. This is not
a sensor clipping test: an SDR TIFF cannot establish what the RAW once contained.
Truly clipped values remain missing after brightness is reduced. The diagnosis
appears beside the regional treatment, not only inside a disclosure.

Amount blends the targeted controls against a frozen base. Changing selection,
photograph, pixel identity or edits invalidates pending work; changing intent
cannot reuse the other operation's cached suggestion. Applying any amount exits
the Before display state. Whole-photo treatment remains opt-in.

## Checks and full-photograph review

```console
cargo test -p strehl-edit --test adaptive
cargo run --release -p strehl-edit --example adaptive-review -- input.tiff new-review-directory
```

Controls include uniform and dark fields, a small subject on black, bright-key
and saturated-color images, preserved annotations and source constraints, an
exact amount-zero full-pixel placebo, HDR point lights, monotonic light order,
sample-phase disagreement, bounded sample counts and malformed inputs.

The review example writes full-resolution before, after and amount-zero TIFFs,
the suggested recipe and explanations, and a compact receipt. It refuses to
replace an existing directory. The original master and captured sources remain
unchanged. Complete photographs must be reviewed before any cropped detail;
numerical checks establish behavior, not an aesthetic improvement.

## Earlier conservative review: October 20, 2026

This section records the earlier policy and is superseded by the visible
treatment revision below. Its small-control table is historical evidence, not
the current treatment.

**VERIFIED:** Nine adaptive control tests passed with a fresh `Compiling
strehl-edit` line. They include a negative control with small absolute channel
differences that fools a relative-only chroma detector, a positive image with
exactly one-quarter meaningful color support, a strongly separated black/white
scene, and different scene-linear versus SDR treatment of identical above-white
samples.

The final `cargo test -p strehl-edit --all-targets` run rebuilt the crate and
passed all 35 tests, including independently authored odd-sized viewport,
off-center annotation, and invalid-baseline controls. The review examples also
compiled.

**MEASURED:** Three existing complete 7032 × 4688 photographs were developed:
the current 299-frame insect output (imported SDR), a calibration-slide
scene-linear master, and a previously stacked garnet (imported SDR). No RAW
capture was changed and no new stack was required. For each, the full before and
amount-zero TIFFs have identical SHA-256 hashes. The final suggested controls:

| Photograph | Exposure (EV) | Shadows | Highlights | Vibrance |
| --- | ---: | ---: | ---: | ---: |
| Insect | +0.08509 | +1.92388 | −0.12521 | +0.13747 |
| Slide | 0 | 0 | 0 | +1.46885 |
| Garnet | 0 | 0 | 0 | +2.01805 |

All other global controls, regions, source constraints, and HDR target settings
are unchanged. Analysis used 16,328 spatial samples per photograph. One observed
analysis call per case took 5.27 ms, 6.98 ms, and 2.94 ms respectively on the test
machine; these are single observations, not a performance benchmark or a UI
frame-rate claim.

The original candidate was **rejected** after author and independent whole-photo
review: raising the slide's dark median also moved its bright gray steps toward
white. The final policy preserves separated light/dark exposure placement and
scales color treatment with actual color support. Whole-photo review of the
final outputs shows the slide's gray-step arrangement intact, a restrained
insect treatment, and no obvious garnet background or hue shift. The independent
reviewer inspected all six complete final before/after images and reached the
same limited assessment. This is limited
photographic review of these examples, not a general image-quality improvement
claim or permission to make Adaptive the default.

The local receipts, full-resolution pairs, complete-scene viewing PNGs, and
hashes are under `outputs/adaptive-review-final/{insect,slide,garnet}`.
They are review artifacts rather than release assets. The original rejected
comparison remains under `outputs/adaptive-review/slide`. Commands used:

```powershell
$env:CARGO_TARGET_DIR = 'outputs/quality-october20-target'
$env:CARGO_BUILD_JOBS = '4'
cargo test -p strehl-edit --test adaptive
cargo build --release -p strehl-edit --example adaptive-review
$env:RAYON_NUM_THREADS = '4'
$tool = 'outputs/quality-october20-target/release/examples/adaptive-review.exe'
New-Item -ItemType Directory outputs/adaptive-review-final
& $tool outputs/feature-validation/insect-run/result.tiff outputs/adaptive-review-final/insect
& $tool outputs/quality-october20-slide/repair/linear-master.tiff outputs/adaptive-review-final/slide
& $tool ../strehl-1792368598430-22840-1/result.tiff outputs/adaptive-review-final/garnet
```

## Visible treatment revision: October 20, 2026

The preceding version was operational but too weak on the insect photograph:
its saved receipt shows that the clipping guard scaled the entire suggestion to
25%, leaving +0.085 EV, +1.92 Shadows and +0.14 Vibrance. This explained the
reported near-invisible effect; it was not evidence that stronger treatment would
necessarily be better. The revision fits highlight protection separately and
removes duplicate saturation suppression. Ordinary midtones below 0.16 may gain
up to 0.65 EV, with a bounded shadow lift. Flat, dark, high-key and separated
black/white controls retain the earlier safeguards.

**VERIFIED:** A fresh `cargo test -p strehl-edit --all-targets` rebuilt the crate
and passed 40 tests, including 14 Adaptive controls. The added bright-color
outlier control requires a measurable middle-tone correction without new sampled
clipping. Other controls test selected-region pixel support, exact zero amount,
cached strength, tiny-region metering, disabled/missing regions, already-white
texturelessness, and the feather-gradient diagnosis trap.

**MEASURED:** New complete 7032 × 4688 TIFF comparisons were produced from the
same three existing inputs, plus a documented ellipse around the garnet's bright
right-hand reflection. All four before/zero TIFF pairs have identical SHA-256
hashes. Global suggested controls:

| Photograph | Exposure (EV) | Shadows | Highlights | Vibrance |
| --- | ---: | ---: | ---: | ---: |
| Insect | +0.65 | +14.61 | −49.82 | +19.77 |
| Slide | 0 | 0 | 0 | +9.20 |
| Garnet | 0 | 0 | −4.63 | +19.24 |

The garnet regional operation changes only Highlights to −22.50. On its complete
33 MP result, 331,635 pixels changed inside the ellipse and **zero** pixels changed
outside it. This establishes support behavior, not image quality. Its diagnosis
finds 7.3% of sampled pixels at or near stored SDR channel white; the central
reflection remains textureless.

An independent reviewer viewed all three global before/after whole photographs,
then the regional whole photograph and native-resolution reflection, surrounding
red facet and dark boundary. The insect's color/structure became more legible;
the slide retained tonal separation; the garnet retained its dark setting with
richer red. The regional reflection was less glaring without an obvious boundary
seam, while its clipped center remained flat. These are limited acceptance of
editable starting points on these photographs, not recovery, sharpness, general
quality superiority, or a new automatic default.

Artifacts are under `outputs/adaptive-visible-review/{insect,slide,garnet,garnet-region}`.
The final diagnosis refinement was rendered again under
`outputs/adaptive-visible-final`: every before/after/zero TIFF matched the
independently reviewed version byte for byte. This is a direct non-interference
control for the extra diagnosis, including the amount-zero placebo.
The example's optional recipe and region arguments make the local treatment
reproducible:

```powershell
$env:CARGO_TARGET_DIR = 'outputs/quality-october20-target'
$env:CARGO_BUILD_JOBS = '4'
cargo test -p strehl-edit --all-targets
cargo build --release -p strehl-edit --example adaptive-review
$env:RAYON_NUM_THREADS = '4'
$tool = 'outputs/quality-october20-target/release/examples/adaptive-review.exe'
& $tool outputs/feature-validation/insect-run/result.tiff outputs/adaptive-visible-review/insect
& $tool outputs/quality-october20-slide/repair/linear-master.tiff outputs/adaptive-visible-review/slide
& $tool ../strehl-1792368598430-22840-1/result.tiff outputs/adaptive-visible-review/garnet
& $tool ../strehl-1792368598430-22840-1/result.tiff outputs/adaptive-visible-review/garnet-region outputs/adaptive-visible-review/garnet-reflection-recipe.json reflection highlights
```

`adaptive-benchmark` separately measures bounded worker analysis and cached Amount
interpolation. It uses alternating forward/reverse sweeps, writes every observed
duration, and excludes import, preview creation, rendering and interaction
latency. Its 1600-pixel preview arm is a different input because area averaging
changes highlight samples; production continues to sample the master directly.

One four-sweep forward/reverse run on the 7032 × 4688 garnet measured:

| Analysis arm | Minimum (ms) | Observed range (ms) | Samples |
| --- | ---: | ---: | ---: |
| Master balance | 9.79 | 9.79–11.90 | 16,328 |
| 1600 × 1067 preview balance | 9.27 | 9.27–10.43 | 16,328 |
| Master regional highlights | 8.97 | 8.97–9.53 | 8,173 |
| Preview regional highlights | 8.61 | 8.61–9.12 | 8,112 |

Cached Amount recipe interpolation averaged about 0.12 microseconds per call over
5,000 calls per arm. That excludes applying the recipe, publishing textures or
painting; it is not a pointer-latency or frame-rate claim. The complete timing
receipt is `outputs/adaptive-visible-review/analysis-timing.json`:

```powershell
cargo build --release -p strehl-edit --example adaptive-benchmark
& outputs/quality-october20-target/release/examples/adaptive-benchmark.exe ../strehl-1792368598430-22840-1/result.tiff outputs/adaptive-visible-review/analysis-timing.json outputs/adaptive-visible-review/garnet-reflection-recipe.json reflection
```
