# Strehl desktop

Strehl is a native Rust workspace for RAW focus stacking. Windows is the primary
desktop target; source import currently accepts Sony ARW brackets. The application
includes its processing engine. Stacking runs on the CPU and the GPU draws the
workspace. See the [build prerequisites](../../docs/desktop-build.md).

Build a source-inclusive package and launch the application from the repository
root:

```powershell
./scripts/package-desktop.ps1 -Destination ./outputs/strehl-desktop
./outputs/strehl-desktop/Strehl.exe
```

Choose a fresh destination: the packager refuses to overwrite an existing package.
The package includes **Strehl.exe**, the standalone **strehl-cli.exe**, the matching
source and rebuild instructions. Keep the source kit and licence notices with
redistributed binaries; see the [RAW decoder notice](../../docs/raw-decoder-notice.md)
and [release checklist](../../docs/public-release.md).

**Working with a stack**

1. Open **Projects** and choose **New stack**, press Ctrl/Cmd+O, or drop a source
   folder onto the workspace. The bracket chooser supports folder navigation,
   camera previews and direct-folder capture counts.
2. Use projects and folders to organize stacks. These are virtual library objects;
   reorganizing them does not move source photographs. A stack keeps the recipe
   for its next render and its saved revisions.
3. Open **Adjust** to set the next render's pyramid, exposure, geometry, capture
   limit and execution options. Default values follow the engine; **Reset** clears
   overrides. The desktop exposes the photographic pyramid controls described in
   the [settings audit](../../docs/desktop-settings-audit.md), rather than every
   research or alternative-backend CLI option.
4. Choose an output destination and press **Stack**. The default output is a
   full-resolution, 16-bit sRGB TIFF. Half-size output changes spatial sampling;
   it still uses every included capture. Each run gets a fresh output folder and
   log. **Stop** cancels the owned render process; a partial TIFF is not published
   as the finished photograph.
5. Inspect the result in the same Process workspace. Opening a saved revision
   restores its photograph and recorded observations without rendering again.
   Source previews are withheld if the recorded source identities no longer match.
   Identity checks use ordered paths, sizes and modification times, not file hashes.

**Exploring the photograph**

The photograph, detail views and capture timeline remain together. **Projects**,
**Adjust**, **Edit**, **Agent**, **Review** and **Activity** open in the resizable sidebar. Drag pane
boundaries to change proportions; double-click a boundary or use **Reset layout**
to restore them. The compact window dock provides Move, minimize, maximize and
close controls; outer edges and corners resize the window.

After completion, hover or scrub the capture timeline to compare a camera source
beside the final photograph. Click to hold a capture. With the timeline focused,
Left/Right and Home/End move the comparison; the wheel steps through captures.
**Photograph** or Escape returns to the final view. During processing, **Live**
returns to the developing image and **Sources** opens camera inspection.

Shift-click or Shift-drag selects a capture range; Ctrl-drag adds another range,
Ctrl-click adds or removes a capture, and Shift-arrows extends the active range.
Pinned ranges keep their identities and colors during ordinary source scrubbing,
clicks and keyboard steps. Their estimated regions remain visible alongside a
separate region for the current capture, including when it lies within a pinned
range. Mixed stripes mark spatial intersections. Escape, **Photograph**, or a
completed-timeline double-click clears the selection; **Fit** also resets linked
views and ranges. **Undo** and **Redo** restore exploration changes.

On the finished photograph, wheel or pinch to zoom. Drag at fit to select a
region; while zoomed, drag to pan or Shift-drag to select another region. Click
to focus a point. The linked details follow the same region, and the overview
inset helps navigate while zoomed. Double-click or **Fit** restores the scene.
Hold Space for a temporary clean photograph. The **Overlay** menu, also available
by right-clicking the photograph, controls admission marks, estimated regions,
and optional sample marks over selected ranges.

**Reading the diagnostics**

Camera previews are embedded JPEGs with camera processing. They are distinct from
Strehl's developing image and final TIFF. The live coarse green reconstruction is
an intermediate view before final bounds and color development. Display textures
use RGBA8; the saved 16-bit TIFF is unchanged. The desktop is not an ICC soft-proofing
viewer, and a reduced preview cannot establish native-pixel sharpness.

Admission marks record where sampled coefficients passed the detail gate. They
are not fractional RGB ownership, a winning-frame map, or a quality score. Region
polygons estimate coherent areas between those samples; their boundaries are not
pixel-exact provenance. Gaps mean missing observations, while an observed zero
remains a measured value. Broad-tone fallback can contribute even where detail
admission is zero. Earlier runs retain the diagnostic resolution they recorded.

Overlays on a finished photograph require compatible output geometry. Detail
labels use photograph pixels when that geometry is known and explicit grid pixels
otherwise; the spacing describes the coefficient grid, not feature width. Dashed
regions on the original camera JPEG are an approximate normalized projection,
not a measured registration. A source comparison does not turn camera pixels into
an aligned diagnostic surface.

**Save confidence map** adds an observation-balance pass and is enabled for new
stacks. Saved recipes retain their own setting. When present, the map can be viewed
as **Observation balance**. It describes the rank balance of aligned observations;
it is not a confidence probability or defect detector. Missing observations and
bounded diagnostic retention remain explicit. **Activity** provides the engine
log; reported memory plans are not live RAM measurements.

**Developing and repairing a photograph**

Open **Edit** after stacking. **Photograph focus** gives the image more space
while retaining the timeline; turn it off to show the process instruments again.
Adjust the whole photograph, or choose **Circle**, **Box**, or **Lasso** and draw a
region. Select its name to adjust only that region, set its feather, or leave a
note. **Before** temporarily shows the original rendering; Undo/Redo also covers
these edits. Recipes save beside the result, preserving the original image.

**Stack repair · next run** restricts a region to a chosen capture span. Press
**Stack** to rebuild it; changing that span or region does not change the already
rendered pixels. Each run saves a new result and editable float master. Export a
new TIFF or HDR AVIF from **Edit**. Older SDR results remain editable but need a
new stack for HDR. See the [development guide](../../docs/development-and-hdr.md)
for supported preset controls and HDR limits.

Use **Agent → Enable agent access** to connect an existing MCP host. Its
conversation stays in that host; annotations, suggestions, adjustments, and
results appear in Strehl. **Circle an issue** opens the same region tool used for
manual edits. See [connection instructions](../../docs/agent-interface.md).

**Development**

The Cargo crate and development binary retain the internal name `strehl-ui`:

```powershell
cargo run -p strehl-ui
cargo test -p strehl-ui
```

See [desktop build and rebuild instructions](../../docs/desktop-build.md), the
[settings audit](../../docs/desktop-settings-audit.md), and the
[reproducible application artwork](assets/README.md). Normal builds need neither
Python nor a separately installed engine. Diagnostic launch options such as
`--screenshot` are development tools. CPU paint timings exclude GPU presentation,
decoding and operating-system input, so they do not measure end-to-end frame rate
or interaction latency.
