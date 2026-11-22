# g-zoom: Develop and Export resolve detail when zoomed

**Status:** results note for the owner's feedback after the Studio 2 run-through. Branch
`studio2/g-zoom`, based on `7f83d3f22`. **Date:** 2026-11-21. **Evidence labels** as in
`AGENTS.md`.

> on the Develop page: zooming into the image doesn't increase the quality/resolution as it should.
> on the Export page: zooming into the image doesn't increase the quality/resolution as it should.

## Root cause

Develop and Export draw the photograph through `photo-viewport.rs` (P7, unchanged in
Studio 2): a 1600 px overview plus **one** detail patch, its stride a power of two, bounded
at 3072 px per side and 6 Mi pixels (`MAX_PATCH_SIDE`, `MAX_PATCH_PIXELS`), padded 35 %
around the view. When the view needed more than the bound, the planner doubled the stride
rather than splitting the work.

- **Half resolution on a 4K canvas.** The owner's display is 3840 x 2160 (VERIFIED,
  `Win32_VideoController`). Beside the inspector and bars the canvas is about 3290 x 1750
  physical pixels (DERIVED from the shell's layout; the owner's Windows scaling was not
  read). On that canvas the baseline build published (MEASURED, benchmark below):

  | View of the weevil (7032 x 4688) | Texels the view needs | Baseline published |
  | --- | --- | --- |
  | Fit (2625 x 1750 screen px) | 2625 x 1750 | stride 4: 1758 x 1172 for the whole photograph |
  | 50 % | 3290 x 1750 | stride 4: 1758 x 1172 |
  | 100 % | 3290 x 1750 | stride 2: 2848 x 1536 |
  | 200 % | 1645 x 875 | stride 1 |

  So "100 %" showed half the master's pixels; detail arrived only past about 200 %. On
  9504 x 6336 (the latest render) and 14064 x 9376 the patch stayed between 1758 and 2848
  texels wide from fit to 100 % (MEASURED): zooming in did not add resolution.
- **No true pixels.** Magnified texels were filtered bilinearly (sampler and float shader),
  so even at stride 1 a view half a pixel off the grid was blurred, and above 100 % pixels
  were never square. At 100 % the baseline's screen pixels differed from the export's by
  up to 255 codes on the weevil (sum 2,012,658 over a 400 x 300 crop) and 56 on 9504 x 6336
  (sum 726,620; MEASURED).
- **Zoom ceiling.** The wheel stopped at 16x the fitted size and Export's **Actual pixels**
  at 8x. In a 1680 x 1050 window a 14064 px master needs 10.7x for 100 % (DERIVED), so
  Actual pixels stopped at 75 %.
- **Export showed the development.** The default Web preset writes 2560 px, but the view
  showed the master's 7032 px: zooming in revealed detail the file does not contain, and
  never the file's own pixels.
- **Offscreen screenshots** ran without a presenter, where the patch was capped at 1024 px,
  so screenshots could neither show the problem nor its fix.

## Design

**Tiles** (`photo-viewport.rs`). A power-of-two pyramid on the master's pixel grid: a tile
at stride `s` holds up to 1024 x 1024 texels, each the mean of an `s` x `s` bin, developed
by `LinearImage::render_display_region_mode` with the current recipe (the same per-pixel
code as export; heals and backdrop run per band with their halo). Every tile carries a
one-texel apron so bilinear filtering is continuous across tile edges; bins stay on one
global grid (VERIFIED, `tile_bins_share_one_global_grid_and_aprons_equal_the_neighbouring_core`).
- **Level:** the coarsest stride whose texels are no larger than a screen pixel (1 %
  tolerance, so an exact 50 % view takes stride 2), coarsened only above 40 Mi texels (an
  8K canvas at nearly 2x). Texels per screen pixel stay in [0.99, 2) below native
  (VERIFIED by a sweep from fit to 800 % on both sizes).
- **Worker:** one long-lived thread develops one tile at a time (each tile is already
  row-parallel), visible tiles nearest the centre first, then a one-tile ring for pans.
  A newer view replaces the queue; the tile in flight continues only if still wanted,
  otherwise it is cancelled. Uploads happen on the worker through the presenter, as
  before. Results from before a reset or a new overview are never published, even when a
  reopened document repeats the identity (an epoch).
- **Settle:** a new level waits 80 ms of rest (zoom); a new recipe waits 80 ms of rest too,
  so while a slider is dragged only the overview follows it and no tile competes for the
  CPU; tiles of the old recipe are dropped when the new overview is published. Pans at
  the same level plan at once.
- **Cache:** tiles the view shows are always kept; others up to 384 MiB of texture, least
  recently wanted first. The ring is prefetched only within that budget. Tiles of other
  levels stay and paint (one finer level, coarser fallbacks) while a new level arrives.
- **Paint:** the overview, then tiles coarse to fine, each clipped to its own core. The
  finest level whose opaque tiles cover the view is the whole base: the overview and
  coarser levels are not drawn. New tiles fade in over 120 ms (unchanged reveal).
- **True pixels:** native (stride 1) tiles magnify with nearest-neighbour, the
  photographic convention, and minify linearly: SDR tiles register a sampler with
  nearest magnification; the float shader has a nearest path chosen per tile when it is
  shown at 100 % or more. Coarser levels and the overview stay bilinear, so the
  placeholder while detail develops is smooth, not blocky.
- **Loading mark:** a one-pixel ruled line along the bottom of the visible photograph, in
  the theme's line and accent colours, showing the share of visible tiles present. It
  appears only after 150 ms and only while the view itself lacks detail. No spinner, no
  overlay.

**Export** (`photo-export.rs`, `strehl-edit/src/export-preview.rs`). When the selected
preset's stages change pixels (a resize, output sharpening, a burned-in scale bar), the
view shows the export's own pixels: `render_export_preview` runs the export's
`Job::staged_buffer` (crop and straighten, heals and backdrop, development, resize,
sharpening, scale bar) and codes it as `save_sdr` does, 16-bit then the JPEG path's 8-bit
reduction, in sRGB primaries. It runs on a worker after 80 ms of rest, is uploaded with
nearest magnification and drawn as one quad over the crop (turned for a straightened
crop). Over it, **Actual pixels** means one output pixel per screen pixel, and the
vector scale bar is not drawn again. Without stages the export is the development, so the
tiles already are its pixels. Not previewed: HDR presets (they show the HDR development),
transparent coverage, outputs over 40 Mi pixels, and a pending depth repair; JPEG and AVIF
codec loss is not simulated.

**Elsewhere.** The zoom ceiling on Develop and Export is now 16x the photograph's own
pixels (`ProcessScales::set_max_zoom`; maps keep 16x); `set_photo_view` uses it. The Stack
station and the legacy Result view use the same viewport and get the tiles too.
`PhotoPresenter::offscreen` gives offscreen screenshots and benchmarks the production
path (worker uploads, registered textures). `--photo-scale <screen px per master px>`
holds an exact scale for offscreen Develop/Export screenshots (re-applied if the canvas
changes size). `docs/development-and-hdr.md` describes the new behaviour.

## Pixel correctness

- **Detail tile = full-resolution development = export** (VERIFIED,
  `detail_tile_pixels_equal_the_full_resolution_development_and_the_export`): a synthetic
  300 x 220 image with exposure, contrast, shadows, a feathered region, a heal and a dark
  backdrop whose neighbourhoods cross tile edges; three stride-1 tiles (inside, corner,
  photograph edge) equal `render_sdr8` exactly and the 16-bit PNG export within its
  rounding, 9,424 pixels. Negative control: exposure +0.05 is caught.
- **Export preview = export** (VERIFIED, `strehl-edit` `export_preview::tests`): resize;
  resize + sharpening + scale bar + crop; straightened crop + sharpening at full size. Every
  value equals the PNG export's 16-bit codes reduced as JPEG reduces them; a different
  sharpening amount is caught.
- **Screen = export on the real masters** (MEASURED, GPU readback through the production
  path, 400 x 300 crop at the canvas centre, no dithering): at 100 % the displayed codes
  equal the full-resolution PNG export's, 0 of 360,000 values differ, on the weevil and on
  9504 x 6336. The Export view at the Web preset's own 100 % equals the Web export before
  encoding, 0 of 360,000 values differ, on both.
- **Square texels** (VERIFIED on the RTX 5090, DX12,
  `magnified_native_texels_stay_square_and_bilinear_remains_the_default`): float and SDR
  layers at 4x replicate texels exactly with nearest and blend without it (the control).
  The other four real-GPU display tests still pass with the shader's 48-byte uniform.

## Measurements

Host: RTX 5090 (DX12), the 32-thread desktop of the earlier notes; CPU load 0-4 % at the
start of every run (MEASURED, `Win32_Processor.LoadPercentage`). Release builds. **After:**
this branch. **Before:** `git archive 7f83d3f22` in scratch with the same benchmark file
and the same `PhotoPresenter::offscreen` added, nothing else. Masters are scratch copies;
the 14064 x 9376 one is synthetic (the weevil upsampled 2x, `make_synthetic_four_shot_render`)
because no four-shot render exists yet: it measures size, not detail.

Command (per master, before and after):

```text
STREHL_UI_BENCH_RUN=<render folder copy> STREHL_UI_BENCH_OUT=<scratch> STREHL_UI_BENCH_EXPORT=0|1 \
  cargo test --release --locked -p strehl-ui zoom_benchmark -- --ignored --nocapture
```

The benchmark (`photo-viewport-bench.rs`) opens the master in an `EditorState`, draws its
photograph into a 3290 x 1750 offscreen canvas every frame through egui-wgpu and waits
for the GPU. "UI ms" is the UI thread's frame (egui, tessellation, buffers, submit).
Peak working set was sampled every 100 ms from the test process (`Get-Process`).

**Cold zoom to sharp** (MEASURED): from a settled fit view, all detail dropped, jump to the
view; ms until every visible tile is present and revealed. Both builds include the 80 ms
settle and the 120 ms reveal.

| Master | View | Before: level, texels | Before ms | After: level, texels | After ms |
| --- | --- | --- | --- | --- | --- |
| 7032 x 4688 | fit | 4, 1758 x 1172 | 134-136 | 2, 3516 x 2344 | 172 |
| | 50 % | 4, 1758 x 1172 | 136-138 | 2 | 163-166 |
| | 100 % | 2, 2848 x 1536 | 230 | **1** | 255-256 |
| | 200 % | 1 | 234-235 | 1 | 234-236 |
| | 400 % | 1 | 210-214 | 1 | 235 |
| 9504 x 6336 | fit | 4, 2376 x 1584 | 148 | 2, 4752 x 3073 | 213-216 |
| | 50 % | 4 | 148-149 | 2 | 203-206 |
| | 100 % | 2, 2816 x 1504 | 234 | **1** | 292-295 |
| | 200 % / 400 % | 1 / 1 | 233-234 / 211-212 | 1 / 1 | 236-239 / 223-224 |
| 14064 x 9376 | fit | 8, 1758 x 1172 | 154 | 4, 3516 x 2344 | 179 |
| | 50 % | 4, 2848 x 1536 | 232 | 2 | 262 |
| | 100 % | 2, 2816 x 1504 | 234 | **1** | 293 |
| | 200 % / 400 % | 1 / 1 | 235 / 212 | 1 / 1 | 240 / 237 |

After, the visible tiles are all present (settle included; the rest is the reveal) at
fit in 50, 93 and 57 ms, at 100 % in 134-136, 171-174 and 171 ms, and at 200-400 % in
103-118 ms (7032, 9504 and 14064 px masters). The after views develop 2-4x the before
views' pixels at fit and at 100 %, for 25-66 ms more.

**Interaction** (MEASURED; before / after):

| | 7032 x 4688 | 9504 x 6336 | 14064 x 9376 |
| --- | --- | --- | --- |
| Back to 100 % after visiting 400 % | 231-234 / 2.3-2.7 ms | 232-234 / 2.4-2.8 ms | 234 / 2.7 ms |
| Pan at 100 %, 1800 px in 300 frames: frames not sharp | 98 / 0-5 | 102 / 15-22 | 103 / 19 |
| Pan: sharp after it stops | 84 / 2.2-2.7 ms | 115-160 / 2.5-2.8 ms | 110 / 2.7 ms |
| Pan: UI ms median, p95, max | 0.10, 0.23, 0.38 / 0.11, 0.23, 1.14 | 0.12, 0.22, 0.35 / 0.13, 0.25, 0.32 | 0.10, 0.23, 0.28 / 0.13, 0.24, 0.38 |
| Slider drag at 100 % (40 edits at 60 Hz): edit to overview, median | 18.7 / 16.3 ms | 18.0 / 16.1 ms | 18.7 / 16.0 ms |
| Drag: UI ms max | 1.5 / 1.5 | 2.0 / 0.7 | 2.1 / 1.0 |
| Drag: release to sharp | 149 / 240 ms | 150 / 274 ms | 146 / 274 ms |

Release to sharp is slower after because the view now holds full resolution (about 8
million texels at 100 %, against 4.4 million at stride 2 before). Repeated cold pans
(12 x 300 frames plus the main pan, weevil, no export step): UI max 0.48 ms, no frame over
8 ms (MEASURED). In runs that first made the benchmark's own full-resolution PNG export
and decode (about 1.6 GB allocated and freed), the first pan after it had one or two
frames of 33-48 ms, all in render plus submit; never without that step. The cause is
UNVERIFIED (likely the driver releasing memory); it does not occur in the viewer's own
paths as measured here.

**Export view** (MEASURED, Web preset, 2560 x 1707): preview developed in 245 ms (weevil)
and 433 ms (9504 x 6336); from choosing the preset to its pixels revealed 451 and 640 ms,
settle and reveal included. The tiles show the development meanwhile.

**HDR path** (MEASURED, `benchmark_float_tile_frames`, an `Rgba16Float` surface with HDR
active, a 3290 x 1750 target, every tile one float-shader draw while panning): 12 / 28 / 40
tiles cost a UI median of 0.12 / 0.23 / 0.32 ms (max 0.36 / 0.32 / 1.39 ms); until the GPU
is done, median 0.24 / 0.53 / 0.72 ms. HDR was not tried on the owner's display.

**Memory** (MEASURED, peak working set without the export comparison, before / after):
7032 x 4688 616 / 605 MiB; 9504 x 6336 936 / 921 MiB; 14064 x 9376 1744 / 1736 MiB. GPU
tile textures (after): peak 134, 187 and 168 MB in these runs; at most the view's tiles
plus 384 MiB (DERIVED; the old single patch held at most 24 MiB SDR, 96 MiB HDR). An HDR
view of a 4K canvas at worst holds about 40 float tiles, 640 MiB of texture (DERIVED). The
Export preview adds its export's transient buffers (12 bytes per developed pixel: about
400 MB for the weevil) while it is built, as the export itself does.

## Tests and checks

All after the last code edit, Compiling/Checking seen:

| Check | Result |
| --- | --- |
| `cargo test --locked -p strehl-ui --no-fail-fast` | 1,471 passed, 0 failed, 40 ignored (36 before, plus four explicit GPU and benchmark tests) |
| `cargo test --locked -p strehl-edit --no-fail-fast` | 188 passed, 0 failed; `tests/export-freeze.rs` 2 of 2 |
| `cargo test --locked -p strehl-ui hdr_display -- --ignored` (real GPU) | 5 passed |
| `cargo clippy --locked -p strehl-edit -p strehl-ui --all-targets --no-deps -- -D warnings` | Clean |
| `cargo fmt -p strehl-ui -p strehl-edit -- --check` | Clean |

New tests: `photo-viewport-tests.rs` (planner on the owner's canvas, tile grid and aprons,
pixels against development and export, stale results across snapshots and resets, one
generation per overview, overview elision, paced reveal, settling, worker wake, failed and
panicking tiles without retry, pan prefetch, eviction, nearest magnification, the quiet
mark, and the Export view: own pixels, per recipe and preset, turned crops),
`export-preview-tests.rs`, and the GPU sampling test.

## Screenshots

`python experiments/desktop-studio-2-impl/visual-check.py --exe target/release/strehl-ui.exe
--out C:\strehl-scratch\g-zoom\shots --run <scratch copy of the weevil> develop export
develop-50 develop-100 develop-400 export-actual export-400 stack` (the new `--run` points a
catalog copy at the copy, so nothing is written beside the original). In
`C:\strehl-scratch\g-zoom\shots`: the routes, `*-crop400.png` native crops, and the pairs
`weevil-new-develop-100-vs-export.png` (screen at 100 % beside the export, identical),
`weevil-baseline-develop-100-vs-export.png` (before: soft), and
`*-export-web-vs-file.png` (Export at the Web preset's 100 % beside the file's pixels).
Looked at: tiles join without seams at fit and 50 %, 400 % shows square pixels, Export at
400 % shows the 2560 px file's pixels as 4 x 4 squares, and **Actual pixels** is selected
at the output's 100 %.

## Not done

- **Split view's Before half** is still the SDR overview, soft when zoomed; **Before** alone
  uses the tiles. The Clipping overlay is still a 1024 px mask.
- Not tried in the owner's window or on the rig: offscreen and GPU harnesses only (no
  Computer Use). HDR tiles were measured only by the micro-benchmark.
- No real 14064 x 9376 four-shot render exists; that size is synthetic.
- Export: codec loss, HDR presets, coverage, outputs over 40 Mi pixels and pending repairs
  show the development (labelled above).
