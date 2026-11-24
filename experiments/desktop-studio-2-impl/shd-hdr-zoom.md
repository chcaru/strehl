# shd-hdr-zoom: full resolution on Develop and Export, HDR included

**Status:** results note. Branch `studio2/shd-hdrzoom`, based on `e09d0593f`. **Date:**
2026-11-23. **Evidence labels** as in `AGENTS.md`. Follows [g-zoom](g-zoom.md), whose
"Not done" list this works through.

> the preview images on the Develop and Export pages still don't show the full resolution
> images. this was supposed to be fixed already and isn't.

## What was found

- **Steady HDR is not the cause.** A new real-GPU test drives the actual viewport
  (demand, worker, float tiles, `PhotoPresenter` paint) on an `Rgba16Float` target with
  HDR active, at 100 %, across a tile corner. The canvas equals the native float
  development to a worst relative error of 0.00088 (f16 rounding), at 100 % display
  scaling on the pixel grid and at 150 % 0.37 px off it (VERIFIED, RTX 5090, DX12,
  `hdr_tiles_show_native_pixels_and_survive_display_changes`). The overview alone fails
  the same comparison (error 5.1, detail 0.003 against 0.54): the control can fail.
- **A change of display state dropped the photograph to the overview** (VERIFIED, same
  test, before the fix: detail 0.0031). With HDR tiles published, `paint_regions`
  returned false as soon as the display stopped presenting HDR (Windows HDR switched
  off, the window moved to the SDR display), and the fallback drew the 1600 px overview,
  since float tiles keep no SDR texture. When the editor then published the SDR
  overview, every tile was cleared and the view stayed soft until the SDR tiles
  developed. The same happened in the other direction.
- **The owner's displays** (MEASURED, read-only DXGI and DisplayConfig queries,
  `display_capability_replies_are_stable_while_nothing_changes`): `DISPLAY2` HDR on,
  peak 499 nits, SDR white 240 nits; `DISPLAY1` HDR off. 200 replies each, none
  differing: the capability reply does not flicker, so a steady window is not
  repeatedly reset. Which display the owner's window was on is UNVERIFIED.
- **"Display: HDR · peak 1000 nits" is the photograph, not the display** (DERIVED,
  `develop-station.rs`: `hdr_photo` and the recipe's `peak_nits`). It does not show
  that the owner's window was presenting HDR.
- **Export shows the selected preset's file** (DERIVED from `default_presets` and
  `export_preview_settings`; MEASURED in g-zoom). The default Web preset writes 2560 px,
  and the view shows exactly those pixels, by design: on a 9504 x 6336 render that is
  27 % of the photograph's width, and zooming shows 2560 px squares. The strip said
  "2560 × 1707 · sRGB · about … MB" and nothing more. ARGUED: this is most likely what the
  owner saw on Export. The UI did not make it clear enough.
- **Split view's Before half was the 1600 px overview** (DERIVED; g-zoom "Not done").

## Fix

- **Float tiles stay on screen when the display state changes**
  (`hdr-display.rs` `paint_regions`, `paint_layer_clipped`). When the display is not
  presenting HDR, or float tiles are painted under an SDR identity, they go through the
  photo shader fitted to SDR white (reference white at SDR white, brighter light clipped
  with its hue kept), on a float or sRGB target (`fits_float_to_sdr`). Only an 8-bit
  non-sRGB target still falls back to the overview. The look differs from the SDR tone
  curve only until the SDR detail arrives (about 0.3 s).
- **Tiles are carried across an HDR-only identity change** (`photo-viewport.rs`
  `carry`, `drop_carried`). Publishing an overview whose identity differs only in `hdr`
  keeps the tiles shown over the view, painted beneath the new state's tiles (which fade
  in over them), until the new state's tiles cover the view. A new recipe, snapshot or
  Before/After never carries. Carried tiles are outside the cache budget: at most the
  view's tiles, for one generation (`tiles_carried` in the stats).
- **Split view's Before half has its own tiles** (`edit-workspace.rs` `before_view`,
  `before_paint`; `develop-station.rs` `split_view`). A second viewport develops the
  default recipe's tiles for the part left of the line only, uploaded by the presenter
  as the "after" ones are, in the same display state as the After half (it was always SDR
  before). Its shapes go into the slot reserved beneath the crop frame and tools
  (`PhotoPaint::paint_shapes`). Leaving Split frees them. Offscreen screenshots of Split
  wait for them.
- **Export says what the view shows** (`export-station.rs` `control_strip`). For a preset
  that writes a smaller file: "view shows this file's pixels · photograph 9504 × 6336",
  with a hover explaining that zoom cannot show more than the file holds and that a
  full-size preset, or Develop, shows the photograph's own pixels. The design (file
  pixels for resizing presets) is kept.
- **Not changed:** the Clipping overlay is still a 1024 px mask. It marks clipped pixels
  over the photograph and does not soften it; making it tiled would need its own worker
  and cache. Left out of scope.

## Tests

| Test | What it shows | Label |
| --- | --- | --- |
| `photo_viewport::hdr_tests::hdr_tiles_show_native_pixels_and_survive_display_changes` (real GPU, ignored) | HDR at 100 %: canvas = native float development (worst rel. error 0.00088), at ppp 1 and 1.5; overview-only control fails; HDR off with float tiles still published: detail 0.5295 (was 0.0031); every frame after the SDR overview stays sharp, then the native SDR development (0.00085); back to HDR, the same; carried tiles go once covered; a new recipe never carries | VERIFIED |
| same, with carrying disabled (placebo, reverted) | fails at "frame 1 after the SDR overview fell to the overview: 0.0031" | VERIFIED |
| `hdr_display::platform::tests::display_capability_replies_are_stable_while_nothing_changes` (ignored) | the owner's two displays; no reply differs in 200 | MEASURED |
| `edit_workspace::development_tests::split_before_half_shows_native_tiles_left_of_the_line` | Split at 100 %: "before" publishes stride-1 tiles for x 700..1200 of 2400 only; `paint_shapes` returns them and leaves nothing painted twice; the After view is unaffected; leaving Split frees them | VERIFIED |
| `export_station::tests::the_strip_says_when_the_view_shows_a_smaller_files_pixels` | the note for Web (2560 px), none for HDR or Print | VERIFIED |

All after the last code edit, Compiling/Checking seen:

| Check | Result |
| --- | --- |
| `cargo test --locked -p strehl-ui --no-fail-fast` | 1,540 passed, 0 failed, 51 ignored |
| `cargo test --locked -p strehl-ui hdr_ -- --ignored` (RTX 5090, DX12) | 8 passed (the 5 existing display tests, the two above, the float-tile benchmark) |
| `cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings` | Clean |
| `rustfmt --edition 2024 --check` on the touched files | Clean |

## Measurements

Host: RTX 5090 (DX12), release builds. **Before** is `e09d0593f` built in a detached
scratch checkout with its own target directory; **after** is this branch. Another
session's debug `strehl.exe` was running at times, so CPU load is recorded per run
(`Win32_Processor.LoadPercentage`). Master: a scratch copy of the 9504 x 6336 four-shot
render (`C:\w\shd-out\render-weevil`).

**HDR paint path** (`benchmark_float_tile_frames`, 3290 x 1750 float target, UI-thread
median ms for 12 / 28 / 40 float tiles; MEASURED). Four alternating before/after pairs,
load 2-80 % at their start. In three: before 0.12 / 0.24 / 0.33-0.34, after 0.12 / 0.24 /
0.34 (one after run read 0.61 for 40 tiles). In the fourth, both builds slowed alike
(0.12-0.21 / 0.30-0.41 / 0.57-0.60). No difference attributable to the change.

**Zoom benchmark** (`zoom_benchmark_on_a_real_master`, `STREHL_UI_BENCH_EXPORT=0`, load
5 % then 0 %; MEASURED, before / after):

| | Before | After |
| --- | --- | --- |
| Cold to sharp: fit, 50 %, 100 %, 200 %, 400 % (ms) | 502, 435, 456, 292, 244 | 475, 430, 448, 296, 239 |
| Pan at 100 %: UI ms median, p95, max | 0.12, 0.27, 2.16 | 0.12, 0.24, 1.60 |
| Pan: frames not sharp of 300 | 43 | 45 |
| Zoom sweep: UI ms median, max | 0.10, 0.31 | 0.13, 0.44 |
| Slider drag at 100 %: UI ms median, max; release to sharp | 0.18, 0.62; 427 ms | 0.20, 2.38; 431 ms |

**Split at 100 %, production path** (the same benchmark's new split segment, with the
offscreen presenter; after only, nothing to compare before): the Before half sharp
221 ms after Split was switched on; the line dragged from 0.1 to 0.9 of the view over
120 frames: UI ms median 0.13, p95 0.24, max 0.46, none over 8 ms; 20 of 120 frames had
"before" detail still arriving; `before_view` held 12 stride-1 tiles, 126 MB (MEASURED).
Split doubles the tile memory while it is shown: a second cache of up to 384 MiB plus
its view (DERIVED).

**Develop latency benchmark without a presenter** (`benchmark_develop_latency_on_a_real_master`,
egui textures uploaded on the UI thread, a path the window does not use): split handle
drag at fit, median 0.07 ms both; max 0.40 before, 5.77 / 0.22 / 5.35 ms in three after
runs (one frame each, load 1-3 %; MEASURED). ARGUED: the "before" tiles' texture
uploads on the UI thread, two per frame, which the presenter does on its worker; the
production-path split segment above has no such frame.

## Not done

- Not tried in the owner's window or on the owner's HDR display with the app; the
  display state was only read. Offscreen and GPU harnesses only.
- The Clipping overlay is still a 1024 px mask (above).
- After a display change the Export preview is rebuilt for the new identity (its file
  pixels do not depend on it); meanwhile the full-resolution development shows.
- If the owner's photograph is a render whose writer string the installed build cannot
  parse (`OutputGeometry::parse`, fixed on the integration branch after `e09d0593f`),
  how the stations behaved with it is UNVERIFIED here.
