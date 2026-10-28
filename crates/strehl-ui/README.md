# Strehl desktop

Strehl is a native Rust workspace for RAW focus stacking. Windows is the primary
desktop target; source import currently accepts Sony ARW brackets. The application
includes its processing engine. Stacking runs on the CPU and the GPU draws the
workspace. See the [build prerequisites](../../docs/desktop-build.md).

For scripted work, use the [local control guide](../../docs/desktop-control.md)
and [`strehl-control.py`](../../scripts/strehl-control.py) to launch a headless
workspace, read state, inspect metadata, and send revision-checked commands.

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
4. Choose an output destination and press **Stack**. New sessions default to
   your Pictures/Strehl folder, independently of the launcher's working directory.
   The default output is a
   full-resolution, 16-bit sRGB TIFF. Half-size output changes spatial sampling;
   it still uses every included capture. Each run gets a fresh output folder and
   log. **Stop** cancels the owned render process; a partial TIFF is not published
   as the finished photograph.
5. Inspect the result in the same Process workspace. Opening a saved revision
   restores its photograph and recorded observations without rendering again.
   Source previews are withheld if the recorded source identities no longer match.
   Identity checks use ordered paths, sizes and modification times, not file hashes.

**Working with several passes of one subject**

Import a source stack, then choose **Create multi-stack session** in Projects or
Adjust. The new session has its own saved recipe; the original stack remains in
the library. Add an **independent pass** for a repeat, changed exposure or lighting
treatment. Use **Add continuation folder** when another directory continues the
same focus sweep. Folder segments and passes have explicit order; folder names
never imply matching focus.

Choose **Combine detail**, **Repeated captures**, **Exposure range**, or **Aligned
layers**. Combined output currently requires matching aperture and ISO; exposure
range can vary shutter time. Use layers for incompatible capture conditions.
Proposed repeats must pass the engine's agreement checks; uncertain matches remain
separate. This feature does not stitch different viewpoints into a mosaic.

An optional **Primary** pass anchors framing and appearance and retains its reliable
content when matched sources disagree. Automatic framing gives no pass that
preference. The capture timeline shows pass ranges, continuation boundaries and
the selected primary. Camera metadata inspects the selected folder segment.

Adjust exposes the session **RAM budget** and **CPU thread limit** alongside its
supported pyramid and exposure controls. Session rendering uses full resolution
and retains a linear master. It does not apply temporal detail smoothing,
source-range repairs or automatic exposure. Develop the resulting photographs
after rendering; earlier photographs and edits remain intact.

Every run saves a fresh manifest, source snapshot and log. The engine's photographs,
masters, alignment envelope and reports live in its `session-output` subdirectory.
Original CFA and matching alignment caches are shared between revisions under
`.strehl-session-cache` in the chosen output destination, outside all source folders.
Aligned layers each have a `layer-NN` folder; use **Aligned layer** in Projects or
Review to inspect them individually. A running job uses an immutable snapshot even
if the next recipe is edited later. Sources changed since import require Reload.

The local control API can compose already imported catalog stacks without granting
new filesystem access:

```json
{
  "expected_revision": 12,
  "command": {
    "operation": "create_session",
    "name": "Repeated subject",
    "passes": [
      {"name": "First pass", "stack_ids": [3, 4]},
      {"name": "Repeat", "stack_ids": [5]}
    ],
    "mode": "repeat",
    "primary_pass": null,
    "memory_limit_gib": 16
  }
}
```

Use actual stack IDs and the latest workspace revision from a snapshot. Stack IDs
within one pass are ordered folder segments. The queued response does not mean the
scan or render has finished. Snapshot `session.capture_groups` and `stack_blocker`
expose readiness; `start_stack` launches the saved recipe.

**Experimental detail smoothing**

Under **Adjust → Merge**, **Temporal detail smoothing** uses neighboring captures
to guide the finest detail layers on the next stack. It defaults Off and saves
with each stack recipe. It can reduce grain, but may remove faint detail visible
in only one capture. Compare an Off result before retaining an On result. Use
full-resolution output and a positive/default Noise gate, without source-range
repairs. See the [mode guide](../../docs/temporal-energy.md).

**Exploring the photograph**

The photograph, detail views and capture timeline remain together. **Projects**,
**Adjust**, **Edit**, **Export**, **Agent**, **Review** and **Activity** open in the
resizable sidebar. Drag pane boundaries to change proportions; double-click a
boundary or use **Reset layout**
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
an intermediate view before final bounds and color development. Completed
photographs retain an overview while the visible area progressively refines to
source pixels. Supported Windows DX12 and macOS Metal displays can present a
linear master's HDR headroom; other display paths remain SDR. The saved 16-bit
TIFF is unchanged. The desktop is not an ICC soft-proofing viewer, and a reduced
preview cannot establish native-pixel sharpness. See the
[display guide](../../docs/development-and-hdr.md#progressive-photograph-display).

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
Adjust the whole photograph, or choose **Ellipse**, **Rectangle**, **Polygon**, or
**Lasso** and draw a region. Select its name to adjust only that region, set its
feather, or leave a note. **Before** temporarily shows the original rendering; Undo/Redo also covers
these edits. Recipes save beside the result, preserving the original image.

**Stack repair · next run** restricts a region to a chosen capture span. Press
**Stack** to rebuild it; changing that span or region does not change the already
rendered pixels. Each run saves a new result and editable float master. Export a
new TIFF, PNG, JPEG, or HDR AVIF from the separate **Export** pane. Older SDR
results remain editable but need a new stack for HDR. See the
[development guide](../../docs/development-and-hdr.md)
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

## Camera metadata

Select a capture on the timeline and click **Camera metadata**. The legacy
**Sources** toolbar opens the same native panel. One background read loads the
imported bracket; the panel follows the selected capture without another engine
call. Click a focus-chart point to select that capture in the workspace.

The panel shows the stored AF grid, exact hovered record bits and flags, and
focus position/scalar A/scalar B progression across the bracket. Click a grid
cell and choose **Selected AF cell** to follow its stored values. **Signed view
(i16)** uses a two's-complement display interpretation on a fixed -32768 to
32767 color scale; it does not establish the camera's arithmetic or depth units.
Unavailable or incompatible frames leave gaps in the progression chart.

Optical curves show all 16 shading, 16 distortion and 32 color-fringing samples
against their stored indices. RAW settings and MakerNote settings remain separate.
A zero setting does not erase a table or activate a correction. **Full capture
details** expands the original values inside Strehl. The CLI's optional `--html`
export remains available for a standalone report.

JSON and worker logs live in fresh `metadata/strehl-*` folders under the selected
output destination. **Refresh bracket metadata** rereads the bracket. Closing the
panel or importing another bracket cancels its owned read; a replacement waits
for that worker to finish. Reopening a completed snapshot reuses its cache.
Inspection leaves the render recipe and source photographs unchanged.

Source size and modification time are checked before and after reading; the
entire RAW is not hashed. AF units, exact mapping onto the photograph, complete
flag meanings and exposure-time freshness remain uncalibrated. Optical sample
indices do not establish a radius, channel assignment or correction law.
Unsupported, malformed, missing and unreadable metadata remain distinct; AF and
optical outcomes are independent.
