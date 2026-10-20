# Adaptive development

Adaptive is an original, deterministic photographic starting point. It proposes
ordinary editable controls rather than introducing another hidden rendering
pipeline. It does not use a learned model, reproduce Adobe's AI profiles, infer
the subject, invent texture, or automatically change the default stack rendering.

`analyze_adaptive(image, recipe)` returns the frozen base recipe, a suggested
recipe, sampled statistics, explanations for each changed control, and
limitations. `suggestion.recipe_at(amount)` blends from that frozen base at
amounts from 0 to 1. Amount zero returns the original recipe exactly. Moving the
slider does not reanalyze the photograph or accumulate previous slider changes.
Analysis belongs on a worker; applying a cached amount is inexpensive.

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

Color adjustment uses at most ten points of the existing vibrance control.
It requires at least 5% of non-dark samples to have both relative chroma above
0.10 and a linear channel span of at least 0.035. The amount scales with that
measured support; strongly saturated scenes receive less. This avoids a binary
decision that gives almost-gray scenes a full color boost. Neutral pixels remain
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
on the sampled RGB values and a logarithmic neutral ramp. It reduces or declines
a suggestion that adds more than a small sampled above-ceiling channel allowance
or reverses neutral light order. Counts are working-space linear channel checks,
not a calibrated quality score or a measurement of final AVIF gamut clipping.

The policy constants are deliberately conservative creative choices, not fitted
camera constants or universally optimal photographic settings. The result is a
reviewable suggestion, not an automatic quality verdict.

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

## Recorded review: October 20, 2026

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
