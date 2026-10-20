# Development, progressive display, and HDR

Strehl keeps an optional **scene-linear RGB32-float master** alongside its familiar
16-bit SDR photograph. The master is taken after the camera color transform and
sensor highlight handling, before SDR tone placement, gamut clipping, the sRGB
curve, and quantization. Negative channel values and highlights above 1 survive.
It is one final merged image; source frames are still gathered in CFA space.

The master records the original display placement separately. Opening it with a
neutral development recipe reproduces the original photograph's rendering; the
underlying samples remain available for further exposure and color changes.
An existing sRGB TIFF can also be edited, but is marked **display referred** and
cannot be exported as recovered HDR.
Integer TIFFs with Strehl's sRGB ICC profile are supported. Untagged integer RGB
TIFFs are assumed to be sRGB; camera-native and explicitly linear files are
rejected. Other embedded profiles are rejected rather than silently interpreted
as sRGB. General ICC profile conversion is not implemented yet.

## Commands

```console
strehl stack captures --srgb --out photograph.tiff --linear-master master.tiff
strehl import-preset preset.xmp --out development.json
strehl develop master.tiff --recipe development.json --out edited.tiff
strehl develop master.tiff --recipe development.json --hdr --out photograph.avif
```

`develop` writes new files and refuses to overwrite an existing output. Applying
another recipe does not restack or alter the master.
TIFF and AVIF exports are fully written, flushed, and then published without
replacement, including when another application creates the destination during
encoding. Interrupted work does not leave a partially written final filename.

## Portable recipes and regional feedback

The same validated JSON recipe is consumed by the desktop, command line, and
agent interface. Version 1 offers exposure, contrast, highlights, shadows, whites,
blacks, saturation, vibrance, and relative temperature/tint. Temperature is a
relative correction, not an absolute Kelvin measurement. Zero is neutral.

Ellipses, rectangles, and polygons use normalized photograph coordinates, stable
IDs, names, notes, and an inward smooth feather. The controls remain tied to the
same subject region when a preview is resized or cropped. Tone adjustments blend
in linear light and preserve headroom until export.

An optional inclusive, zero-based `source_range` is a **restacking instruction**.
It is not an ordinary image adjustment. The engine records the actually rebuilt
region recipe in the master. Exports compare the current enabled region shapes,
feathers, source ranges, and ordering against that record and refuse a mismatch.
Tone and note changes remain possible without another stack.

## What HDR AVIF contains

The built-in Rust encoder writes **10-bit 4:4:4 AV1**, full range, BT.2020 primaries,
and the SMPTE ST 2084 PQ transfer function. Both the AV1 sequence header and AVIF
container describe those values. Content light metadata is calculated from the
actual developed image. No external encoder program is required.

The default maps developed linear 1.0 to 203 cd/m² and caps the export at 1000 cd/m².
The recorded display placement and recipe apply to HDR too. The original contrast
curve extends monotonically above SDR white, preserving highlight order instead of
clipping or evaluating the SDR cubic outside its valid range.
Reference white and peak brightness are explicit recipe settings; the export
report includes clipped sample counts and measured content light levels.
No fictitious mastering-display metadata is invented.

This is HDR **development and output from the preserved RAW-derived master**.
It does not recover sensor-clipped information and is not an exposure-bracket
fusion algorithm.

## Progressive photograph display

Completed photographs open with a retained overview. The visible area then
refines according to the window's physical pixel density and the source pixels
covered by the current view. At close inspection the patch uses the original
source pixels. Zooming does not enlarge a permanently fixed 1600-pixel preview.

High-resolution development, validation, and native texture uploads happen on
background workers. A small initial overview still uses the regular UI upload
path. The viewer keeps the previous image while work finishes, discards obsolete
requests, and reveals new detail gradually. A small margin around the visible
area reuses nearby detail while panning. The patch is bounded to 3072 pixels per
side and about 6.3 million pixels; this bounds transfer and working memory on large
displays. Changing the recipe or Before state cannot mix generations of pixels.

Windows DX12 uses extended-linear scRGB when the window's active display has HDR
enabled. macOS Metal uses the display's current EDR headroom. Photograph storage,
development, and HDR GPU working textures remain f32; only the final operating-system
presentation boundary uses its required float16 surface. Ordinary controls follow
SDR white, while the photograph retains supported highlight headroom. Moving
between displays or changing HDR availability refreshes the presentation.

The status bar and **Edit → HDR display & output** report the active mode. An old
SDR TIFF stays SDR even on an HDR monitor. Unsupported graphics backends, Linux,
and displays without active HDR use the SDR path. The app never enables Windows
HDR or changes display brightness for you. An HDR screenshot is an SDR proxy;
use AVIF export to preserve HDR delivery values.

GPU readback tests establish color arithmetic and above-white preservation.
Physical HDR-monitor appearance still needs testing on an enabled HDR display;
the development machine used for this change reported SDR. General ICC soft
proofing and native HDR on Linux are not implemented.
See the [display verification record](development/progressive-display-verification.md)
for the native interaction controls, matched CPU measurements, and their limits.

## XMP presets

The importer reads supported numeric settings and reports what it applied.
Adobe processing algorithms, adaptive/AI profile references, proprietary Looks,
sharpening, noise reduction, and unsupported color operators are not reproduced.
A profile name or stub does not contain the model or lookup table needed to
execute it. Imported numeric values use Strehl's operators, so the result is not
claimed to match Lightroom.

Private preset contents are not copied into the repository.

## Adaptive light and color

**Edit → Adaptive** measures the current photograph and proposes an editable
treatment. It uses bounded, stratified scene samples to assess tonal range,
highlight headroom, dark backgrounds, strongly separated light/dark compositions,
and color saturation. It is an original deterministic alternative to an opaque
profile, not a learned model or a reproduction of Adobe's Adaptive Color.

The treatment adjusts ordinary exposure, contrast, shadow/highlight, white, and
vibrance controls. **Amount** blends against the recipe that preceded the
analysis; moving the slider repeatedly does not compound the effect. **What
changed** shows the proposed control values and the measurements behind them.
Undo restores the previous recipe. Manual changes remain possible; analyze again
to start from those new settings.

Nearly flat or extremely dark scenes, unstable spatial samples, strongly
saturated subjects, and isolated color outliers constrain the suggestion.
Scene-linear masters retain valid HDR headroom above diffuse white; the delivery
ceiling comes from the recipe's peak/reference-white ratio. An imported SDR image
uses its existing white. This is a starting point for judgment, not a guarantee
of a better photograph or a repair for focus, alignment, noise, or clipped capture
data. Existing regions, source-span repairs, white balance, and HDR settings are
preserved.

Analysis runs off the UI thread and is discarded if the photograph or edits
change before it returns. Agents can request the same operation with
`adaptive_develop` and inspect the returned analysis in a workspace snapshot.

## Verification

```console
cargo test -p strehl-edit
cargo test -p strehl-cli --lib linear_master_is_observational_and_neutral_edit_matches_legacy_pixels
cargo run -p strehl-edit --example hdr-fixture -- outputs/hdr-edit-validation
python scripts/verify-hdr-avif.py outputs/hdr-edit-validation
```

The first controls require negative and above-white samples to survive a float
TIFF round trip, reject malformed recipes and fake HDR from an SDR input, and
exercise feathered regional edits. The CLI control compares the entire SDR TIFF
with master capture on and off, then compares neutral master development with
the original pixel codes.

The independent FFmpeg/ffprobe check decodes known absolute luminance patches,
checks 10-bit PQ/BT.2020 signaling and content light metadata, and rejects a
deliberately mislabeled transfer function. These are encoding correctness
checks, not photographic quality or display-compatibility claims.

Primary implementation references:
[rav1e encoder configuration](https://docs.rs/rav1e/0.8.1/rav1e/config/struct.EncoderConfig.html),
[AVIF color and light metadata](https://docs.rs/avif-serialize/0.8.9/avif_serialize/struct.Aviffy.html),
[AV1 image format specification](https://aomediacodec.github.io/av1-avif/),
[ITU-T H.273 color signaling and full-range quantization](https://www.itu.int/rec/T-REC-H.273-202107-S/en).
