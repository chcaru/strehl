# Development and HDR export

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
fusion algorithm. The current desktop SDR surface cannot prove HDR monitor
presentation; inspect the AVIF in a compatible HDR viewer and display.

## XMP presets

The importer reads supported numeric settings and reports what it applied.
Adobe processing algorithms, adaptive/AI profile references, proprietary Looks,
sharpening, noise reduction, and unsupported color operators are not reproduced.
A profile name or stub does not contain the model or lookup table needed to
execute it. Imported numeric values use Strehl's operators, so the result is not
claimed to match Lightroom.

Private preset contents are not copied into the repository.

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
