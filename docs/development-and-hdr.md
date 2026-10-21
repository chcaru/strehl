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
Integer TIFFs with Strehl's own sRGB, Display P3 and Rec.2020 ICC profiles are supported. Untagged integer RGB
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
TIFF, PNG, JPEG and AVIF exports are fully written, flushed, and then published without
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

## Editing in the workspace

**Edit** keeps the photograph in the process workspace. **Light** and **Color**
apply immediately to the whole photograph or the selected region; they do not
require another stack. Click a value to type, drag its track to adjust, or
double-click to reset. **Before** compares the original treatment. Undo/Redo
includes both adjustments and region geometry.

The resizable **Regions** shelf stays below the independently scrolling controls.
Click a name to select it; double-click to rename it inline. Its context menu
offers Duplicate, Reset light & color, and Delete. The checkbox enables the
region. Collapsing the shelf preserves its expanded height.

**Polygon** places points with clicks; Enter, a double-click, or the first point
closes it. **Lasso** draws a freehand boundary while the mouse is held down.
**Select** moves regions and exposes resize handles or editable vertices.
Double-click a polygon edge to add a point; Delete/Backspace removes a selected
point while retaining at least three. Escape cancels the current gesture before
changing the selection. Hold **Space** for photo navigation and **Alt** for
diagnostic inspection, so the inspection overlay does not compete with editing.

**Magic lasso** is experimental image-guided selection: draw a loose enclosure
with a little background around an object or defect. It measures supported
boundary colors, rejects isolated noise, and traces separate contrasting areas
inside the enclosure. Up to eight outlines are added together as one undoable
action. The resulting points stay editable. It uses a bounded crop on a worker,
including unclipped HDR values; it does not run semantic object recognition.
Flat or ambiguous enclosures produce an explicit no-selection result. Significant
holes cannot be represented by the current recipe: the tool can retain a
supported high-contrast core instead, or skip that component. Small raster gaps
may close. The status reports these approximations and any omitted regions.
Press Escape to cancel refinement. Changing tools, the photograph, or its recipe
prevents old work from appearing over newer edits.

**Source repair** is a separate, initially collapsed section. Choosing a capture
range queues a change to the merge; **Re-stack with source changes** applies it.
The current photograph remains unchanged by that source choice until stacking
finishes. Exports wait for pending source changes to be applied. This differs
from the immediate Light/Color controls above it.

## What HDR AVIF contains

**Export** is a separate sidebar pane. It defaults to AVIF, quality 100 and
HDR Rec.2020 for a scene-linear master. Choose sRGB or Display P3 when needed.
Existing SDR photographs export as SDR; changing the color-space tag cannot
restore discarded highlight data. TIFF and PNG use 16-bit channels; JPEG uses
8-bit channels. All three carry matching ICC profiles. AVIF carries matching
container and bitstream color metadata. See [export formats](export-formats.md)
for conversion semantics, including the SDR appearance policy.

Quality 100 is the highest setting for AVIF and JPEG, not lossless compression.
Encoder effort is separate: faster searches can change distortion and file size
at the same quality setting. The default balances these; the pane exposes the
tradeoff under Encoding options. Output size remains the photograph's full
resolution, independent of the on-screen preview.

The built-in Rust encoder writes **10-bit 4:4:4 AV1**, full range, BT.2020 primaries by default,
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

The status bar and **Edit → Display** report the active mode. File delivery has
its own **Export** pane. The Edit
header reports the display mode separately from the photograph's origin. An old
SDR TIFF stays SDR even on an HDR monitor. Unsupported graphics backends, Linux,
and displays without active HDR use the SDR path. The app never enables Windows
HDR or changes display brightness for you. An HDR screenshot is an SDR proxy;
use AVIF export to preserve HDR delivery values.

GPU readback tests establish color arithmetic and above-white preservation.
Monitor appearance is separate from those arithmetic controls. Windows capability
queries are associated with the window's current monitor; a reply from a monitor
the window has left is discarded. General ICC soft proofing and native HDR on
Linux are not implemented.
See the [display verification record](development/progressive-display-verification.md)
for the native interaction controls, matched CPU measurements, and their limits.
The [editor verification record](development/edit-workspace-verification.md)
covers region gestures, Magic selection and monitor-transition checks.

## XMP presets

The importer reads supported numeric settings and reports what it applied.
Adobe processing algorithms, adaptive/AI profile references, proprietary Looks,
sharpening, noise reduction, and unsupported color operators are not reproduced.
A profile name or stub does not contain the model or lookup table needed to
execute it. Imported numeric values use Strehl's operators, so the result is not
claimed to match Lightroom.

Private preset contents are not copied into the repository.

## Spatial light and color

In **Edit → Spatial light & color**, choose **Analyze photograph** or, with an
annotation selected, **Analyze region**. The treatment responds to both location
and pixel brightness: similar colors in different parts of the photograph can
receive different adjustments. It preserves the ordinary Light/Color sliders
and stores its local curves separately in the recipe. It is deterministic,
not a learned model, semantic subject detector, or reproduction of Adobe's
Adaptive Color.

**Amount** controls the stored treatment without analyzing the image again.
It remains available after reopening; zero disables that scope's treatment,
and returning to the previous amount restores it without compounding edits.
Under **Shape the treatment**, adjust **Light balance**, **Local contrast**, and
**Color**, then choose **Recalculate treatment**. Those parameter changes are
drafts until recalculation, so dragging a control does not repeatedly run an
analysis. Manual adjustments and other regions remain intact. Undo restores
the previous recipe.

**Where it changes** shows an optional, sampled map of the actual developed
difference: warm tint for lifted light, cool tint for deeper light, and violet
for color changes. The tints are amplified for visibility. The comparison
includes region feathering and existing edits; it is not a source-contribution
map or evidence of recovered detail. **Analysis notes** contains the measurements,
reasoning and limitations from the last analysis.

The operator protects dark floor values, near-white channels, neutral areas and
already saturated colors. It constrains overall light placement while shaping
local tones. A scene-linear master retains valid HDR headroom above diffuse
white; an imported SDR photograph is limited to its stored range. This is an
adjustable starting point, not a guarantee of a better photograph or a repair
for focus, alignment, noise, or clipped capture data. Source-span repairs and
HDR settings are preserved.

With a region selected, **Balance highlights** remains a separate action. It
adjusts that region's ordinary Highlights control and reports whether the stored
image still contains tonal variation there. It can reduce distracting brightness;
it cannot reconstruct texture already clipped out of the input TIFF or RAW.
Its **Highlight amount** blends the proposed change against the preceding
regional adjustment.

Analysis and effect-map sampling run off the UI thread. A changed photograph,
recipe, or selected scope invalidates pending analysis. Agents can request the
same treatment with `adaptive_develop` and inspect compact analysis metadata in
a workspace snapshot. The [spatial-treatment record](development/adaptive-spatial-treatment.md)
documents the algorithm, research, photographic review and limits.

## Named presets

In **Edit → Presets**, choose **Save look…** and give the current treatment a
name. A preset stores the selected scope's light and color controls, plus its
spatial parameters and Amount when present. It excludes the photograph's measured
curves, annotation geometry, source-repair ranges and HDR delivery settings.

Select a saved look and choose **Apply to photograph** or **Apply to selection**;
double-clicking its name also applies it. Spatial treatment is recomputed for the
destination photograph or region in a worker. Applying replaces the addressed
controls and treatment as one undoable edit, preserving other scopes and source
repairs. A static preset clears the addressed spatial treatment rather than
silently layering over it.

The preset context menu offers Rename and Delete; a deleted preset can be
restored with the shelf's Undo action. Presets are saved locally. If saving fails
or the library changes externally, the pane reports the problem and offers retry
or recovery instead of silently overwriting another version. This library is
separate from the limited numeric XMP importer described above.

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
