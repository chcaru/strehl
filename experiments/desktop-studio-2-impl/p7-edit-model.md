# P7 model: Develop and Export in `strehl-edit`

**Status:** results note for the model half of phase P7 of
[the implementation plan](../../docs/proposals/2026-11-desktop-studio-2-implementation.md)
(sections 7.5, 7.6, 9 P7, P0 item 11). Branch `studio2/p7-edit`, based on `61effa01b`.
The Develop and Export stations were built on this model in UI stages 1 and 2 (below).
**Date:** 2026-11-21. **Evidence labels** as in `AGENTS.md`.

## What was built

| Item | Where | State |
| --- | --- | --- |
| Recipe fields `crop`, `scale_bar`, `heals`, `backdrop`, `layers_order` | `recipe.rs`, `recipe-finishing.rs` | Built, optional, omitted when unused; `version` stays 1 |
| `RegionShape::Stroke { points, radius }` (depth-brush mask) | `recipe.rs`, `recipe-prepared.rs` | Built; per-stroke cap 1024 points, recipe cap 4096; `stroke_from_path` simplifies a brush path |
| Bounding-box culling for every shape; `PreparedRecipe` for loops | `recipe-prepared.rs` | Built; bit-identical to the old loop |
| Layer order (tone application order, list order stays repair-blend order) | `recipe.rs` | Built; `application_order`, `move_layer`, `remove_region` |
| White-balance pick (7.5 formulas, post-`place`, square average, clamp flag) | `white-balance.rs` | Built |
| Export split: develop, f32 buffer, resize, sharpening, scale bar, encode | `export.rs`, `export-pipeline.rs`, `avif.rs` | Built; fused path kept when no stage runs |
| Crop and straighten in export (mapped UV, Catmull-Rom when turned) | `export-pipeline.rs` | Built |
| Resize in linear light, unclamped (Mitchell default, Lanczos 3) | `resample.rs` | Built |
| Output sharpening (luminance USM, cored) with the rule 9 flat-ROI control | `sharpen.rs`, `tests/export-pipeline.rs` | Built; no default preset uses it |
| Scale bar burn-in (bar plus `ab_glyph` label from Bahnschrift, then Segoe UI) | `scale-bar.rs` | Built |
| Metadata: TIFF tags + XMP (tag 700), PNG iTXt XMP, JPEG Exif + XMP APP1, AVIF Exif | `metadata.rs` | Built |
| Recipe in TIFF ImageDescription as a switch, default off (P0 item 11) | `ExportSettings::embed_recipe` | Built |
| Neighbourhood stage: heals, backdrop, halo-correct in export and preview | `neighbourhood.rs`, `display-region.rs`, `image.rs` | Built, export and preview |
| Engine: `Stroke` repairs through `Repairs::preflight`/`apply` | `strehl-cli/src/merge_cmd/region-repair.rs` | Built; prepared (culled) weights in the blend |
| Export presets library | `strehl-ui/src/export-presets.rs` | Model and tests only |

## Compatibility

- **Recipe files.** A recipe that uses no new field serializes byte-identically to the
  pre-P7 build, compact and pretty (VERIFIED, `tests/export-freeze.rs`
  `option_free_recipe_serialization_is_frozen`, JSON recorded at `61effa01b`). The
  pre-P7 schema, reproduced field for field with `deny_unknown_fields`, reads such a
  file and refuses each new feature when it is used (VERIFIED, `tests/finishing.rs`).
  `DevelopmentRecipe::uses_finishing()` tells the UI when that refusal applies.
- **Exports.** 86 option-free exports (TIFF, PNG, JPEG, AVIF SDR and HDR, three gamuts,
  three image kinds, neutral and 4-region recipes, coverage) hash identically to the
  pre-P7 build (VERIFIED, `option_free_exports_are_byte_identical_to_the_pre_p7_build`;
  hashes recorded by the same file at `61effa01b`; TIFF cases set `embed_recipe`, the
  pre-P7 behaviour). Mutation: a culling box shrunk by 2 % changes pixels on the culling
  test's grid (`a_shrunken_box_is_caught_by_the_same_grid`).
- **Real master** (MEASURED, rule 50). `C:\Users\chris\Pictures\Strehl\strehl-1793781369068-68052-3\master.tiff`,
  7032 x 4688, with its own `result.strehl-edits.json` ("real") and that recipe plus 128
  random ellipse, rectangle and polygon regions ("many"). Probe
  `experiments/desktop-studio-2-impl/p7-export-freeze.rs`, release build; its
  `develop` and `export` modes were built before any change and after (the
  `export-with` mode was added later). Every output is byte-identical:

  | Output | SHA-256 (before = after) |
  | --- | --- |
  | `render_sdr16`, real | `7606532dd60b3978843de6eb8ffd2a5af9452254d0388df2de78e4678e7baee5` |
  | `render_sdr16`, many | `596dcfa4a47fb7d27d34a8a46af70f28339f10e12c4501b53570f6d5cf44db05` |
  | TIFF sRGB (recipe switch on), real | `f8e536104817f1782bd18c5043443f6b5e9f05a8aada3caabe9dfbd9881b93ae` |
  | TIFF sRGB (recipe switch on), many | `a199f7535c944281e0a85cf9ae549968385d2790953ae6063d619587c6dc86cf` |
  | PNG Display P3, real | `6bafd06d0c6fc0ba51ec114788ee19b6a8eb71bc89eda7ad9d86135c92ad4fab` |
  | JPEG sRGB q90, real | `0caadc4aa72aa28f309245212086f11ce446d76018e63cd32ca8d49492b9bde4` |
  | AVIF HDR Rec.2020 speed 10, real | `7dec762879aa141a10cda0d275c93efa0fece82e913dd962ca33b1203507c559` |

  The AVIF encoder repeated its bytes on a second before-run (MEASURED).
- **P0 item 11 changes one default on purpose.** `ExportSettings::default()` no longer
  writes the recipe into TIFF exports; the desktop's TIFFs lose that text unless the
  switch is on. Nothing reads it back (VERIFIED: the only `ImageDescription` readers are
  `load_tiff`'s checks and the master's `DisplayBaseline`/`BakedSourceRecipe` lines). The
  CLI `develop` command keeps writing it (`embed_recipe` for TIFF), so its output is
  unchanged. A recipe with non-ASCII region names, which failed TIFF export before
  (TIFF ASCII tags refuse UTF-8), now embeds as ASCII-escaped JSON.
- **Settings in the catalog.** New `ExportSettings` fields are omitted at their
  defaults, so export history entries and the agent snapshot's `defaults` keep their
  keys. An entry that uses a new option is refused by an older build (as for recipes).
- **Masters.** The engine still embeds the full applied recipe (`BakedSourceRecipe`),
  so a master rendered from a recipe that uses a new field cannot be opened by an older
  build. Unchanged for recipes without new fields (ARGUED from the serialization freeze).

## Performance

Host load: another agent's CPU render (`strehl-new stack`, lane p2) held the CPU at
99 % throughout; runs were interleaved before/after to share that load. Best of three
`render_sdr16` per run (MEASURED):

| Recipe | Before | After |
| --- | --- | --- |
| real (1 spatial treatment, no regions) | 0.189 s, 0.178 s | 0.175 s, 0.165 s |
| many (real + 128 regions) | 6.963 s, 7.135 s | 0.426 s, 0.369 s |

Culling makes the 128-region development about 17x faster with identical bytes. PNG
and JPEG export times were within run-to-run noise (PNG 0.65/1.03 s before, 0.82/1.01 s
after; JPEG 0.67/0.72 s before, 0.74/0.68 s after). The AVIF fused path now develops
64-row bands in parallel and keeps the sequential row-major statistics, so its HDR
metadata sums are unchanged (VERIFIED by the AVIF hash above).

Memory: the fused path allocates as before. A staged export (resize, sharpening or
scale bar) holds an f32 buffer of the cropped size (12 bytes a pixel); heals or a
backdrop add a staged copy of the master (12 bytes a pixel) for the export only.

## Measurements behind defaults

- **Resize filter** (MEASURED, `resample-tests.rs`): a hard step downscaled 4x
  overshoots by 0.77 % with Mitchell and 1.70 % with Lanczos 3. Mitchell is the default
  because rule 48 measured a 5x Lanczos inventing halos. The `image` crate's `resize`
  was not used: on `f32` it clamps every sample to 0..1 (VERIFIED in
  `image-0.25.10/src/imageops/sample.rs`, `clamp(t, min, max)` with the `f32` range),
  which would clip HDR. Weights accumulate in f64 and divide by their own sum, so a
  constant (including 3.0 x 203 nits) stays exactly constant.
- **Sharpening coring** (MEASURED, sweep on synthetic fields, amount 0.5, sigma 0.8 px,
  gradient energy of coded green on 16-bit TIFF exports): flat 18 % grey with uniform
  noise of +-8 %: threshold 0.012 adds 4.85 %, 0.016 adds 0.27 %, 0.02 adds 0.00 %; a
  1-2 px edge (logistic scale 0.5 px) gains 8.69 %, 6.70 %, 4.76 % respectively. The
  default is 0.016. The control can fail: uncored, the same flat field gains over
  100 %. No visual claim is made; per rule 48 the owner judges native crops of 400 px
  or smaller before any preset turns sharpening on. The default presets do not.
- **Stroke cap** (MEASURED, `tests/finishing.rs`): 8192 stroke points pretty-print to
  587,702 bytes, too much of the engine's 1 MiB `--region-recipe` cap; 4096 points take
  296,462 bytes, so the recipe-wide cap is 4096.
- **Backdrop** (MEASURED, `tests/neighbourhood.rs`): on a 1600 x 1000 field with 5 %
  noise, backdrop noise SD 0.0231 -> 0.0047; subject pixels below the key bit-identical;
  the backdrop 3-6 px from the subject keeps 98 % of its level (no bleed).

## Tests and commands

Commands were run in `C:\w\p7` with `CARGO_BUILD_JOBS=8`, never `-q`.

- `cargo test --locked -p strehl-edit`: all binaries pass (VERIFIED). New:
  `tests/export-freeze.rs`, `tests/finishing.rs`, `tests/export-pipeline.rs`,
  `tests/neighbourhood.rs`, `src/recipe-prepared-tests.rs`, `src/metadata-tests.rs`,
  `src/resample-tests.rs`.
- `cargo test --locked -p strehl-cli source_repair`: 7 pass, including
  `source_repair_accepts_a_depth_brush_stroke_and_blends_only_under_it` (VERIFIED).
- Real master, staged path (MEASURED, probe `export-with`, release build): the run's
  recipe plus a 2-degree straighten, crop, Web preset (JPEG, 2560 px) with a 1 mm
  scale bar and metadata took 0.28 s; output 2560 x 1796 from a 5344 x 3750 crop,
  4.175 µm per output pixel at an illustrative 2.0 µm per source pixel (not the lens's
  calibration). A native 400 x 296 crop at (2160, 1500) shows the bar and its
  Bahnschrift label; PIL reads the file's Exif, XMP and ICC profile. Functional check
  only: no quality claim rests on it.

## Check record

| Crate | Check | Result |
| --- | --- | --- |
| `strehl-edit` | `cargo test --locked -p strehl-edit` | All 15 binaries pass, after the last edit (VERIFIED) |
| `strehl-edit` | `cargo clippy --locked -p strehl-edit --all-targets --no-deps -- -D warnings` | Clean (VERIFIED) |
| `strehl-edit` | `cargo fmt -p strehl-edit -- --check` | Clean (VERIFIED) |
| `strehl-cli` | `cargo test --locked -p strehl-cli --no-fail-fast -- --skip m194f_independent --skip m194g_private --skip independent_green_probe_controls --skip independent_parallel_writeback_controls` | Lib 256 passed; `tests/byte-freeze.rs` 5 passed (680 s); one doctest fails on a pre-existing indented doc comment (`lib.rs:234`, `Command::Stack`) |
| `strehl-cli` | The 13 skipped tests | Fail without `STREHL_GREEN_PROBE_OUTPUT` and private source files, in modules this work does not touch; the same tests leave `independent-input-*` folders in the main checkout. Their leftovers from this run were deleted by name |
| `strehl-cli` | clippy `-D warnings` | Fails on pre-existing findings in other files (`image_out.rs`, `merge_cmd.rs`, `gatefloor.rs`, experiment sources); none in `region-repair*.rs` or `develop_cmd.rs` |
| `strehl-cli` | `cargo fmt -p strehl-cli -- --check` | Clean for my hunks; the crate has pre-existing diffs elsewhere |
| `strehl-ui` | Build at this branch | Does not compile until `p7-stroke-ui-arms.patch` is applied (reserved files) |
| `strehl-ui` | With the patch, in a scratch copy of the tree: `cargo test --locked -p strehl-ui` | 1068 passed, 0 failed, 16 ignored, including the 7 export-preset tests |
| `strehl-ui` | Same copy: clippy `-D warnings` | Only the known `unnecessary_cast` at `capture-workspace.rs:1772` |
| `strehl-ui` | `cargo fmt -p strehl-ui -- --check` | Clean |

## What the UI and preview path still need

- The Develop and Export stations themselves (P7a/b/c screens), including the crop
  overlay, the white-balance tool hint ("the controls stop at a factor of 2"), the
  layers list, and the depth brush (P7c).
- **Strokes need three match arms in reserved files.** Adding `RegionShape::Stroke`
  makes `strehl-ui` fail to compile until `edit-regions.rs` (move, resize guard) and
  `edit-workspace.rs` (bounds, outline) handle it. Those files were outside this lane,
  so the arms are in `p7-stroke-ui-arms.patch` beside this note for the orchestrator.
- The overview raster: the desktop develops a 1600 px `preview` image. Heals and the
  backdrop then run at that resolution: supports scale with the long edge (key 1/3000,
  smoothing 1/800) and heal offsets round to preview pixels, so the overview is close
  to, not equal to, the export. Detail patches from the master are exact.
- Thumbnails (`render_region_sdr8`) apply heals and the backdrop row by row; crop is an
  export operation and no renderer shows it yet.
- `apply_pixel`, `developed_pixel` and `display_pixel` stay per-call; desktop loops that
  call them per pixel (`adaptive-effect.rs`, `edit-magic.rs`, `app-adaptive.rs`,
  `app-agent.rs`) should switch to `recipe.prepare()` once layer orders or strokes are
  in use.
- Export presets: wire the library into the Export station, persist per-subject
  destinations, and run a batch through `available_path` (files are never overwritten).
  The Archive preset is a copy of master and recipe, which the station implements.

## UI stage 1: Develop and Export parts (2026-11-21)

Built as self-contained parts for the Studio 2 shell (P1 is still in another lane): each
takes its inputs as parameters and returns intents. Nothing is composed into the shell
yet; that is stage 2. Branch `studio2/p7-edit` after merging the integration branch
(`251928367`).

| Part | File | API |
| --- | --- | --- |
| Palette and widgets | `crates/strehl-ui/src/develop-style.rs` | `StudioPalette::GRAPHITE` (base.css tokens); `caps`, `sect`, `seg`, `slider`, `toggle`, `checkbox`, `button`, `link`, `tag`, `mark`, `tabs`, `icon`. Swapping in P1's tokens is one constructor |
| Develop station | `develop-station.rs` | `tools_strip`, `tool_shortcut`, `control_strip(view, canvas, rail)`, `inspector(panel, view, rows)`, `DevelopCanvas::overlay`; `DevelopIntent`; `DepthRail` trait with `RangeFallback` |
| Layers | `develop-layers.rs` | `layer_rows`, `apply_layer_intent`, `layers_panel`; `LayerIntent::{Select, SetVisible, Remove, MoveTo}` |
| Export station | `export-station.rs` | `inspector`, `control_strip`, `history_table`; `ExportIntent`; `plan_batch`, `run_batch`, `BatchProgress::snapshot` |
| App glue | `app-develop.rs` | `show_develop_{tools,strip,inspector}`, `show_export_{inspector,strip,history}`, `start_depth_repair`, `start_export_batch`, `develop_can_export`, `repair_export_note` |

Behaviour that changed in today's desktop:

- **P7c.** "Re-stack with source changes" became "Rebuild in the background": the
  repair runs as its own render job (`DevelopApp::repair`), `self.job` stays free, the
  photograph stays loaded and editable, and Export stays enabled. While the repair is
  pending, exports use `EditorState::export_recipe` (the live tone with the repairs the
  master holds, `with_baked_repairs`) and the pane says so. On completion the live
  recipe is written beside the new render (never over an existing sidecar) and the
  repaired render opens. VERIFIED by `app::develop::tests::a_pending_depth_repair_keeps_the_photograph_and_export_enabled`.
- **Looks.** Recalculate keeps the Amount (it reset to 1.00); a double-click on the
  chosen look resets to that look; each look has a one-line description.
- **Loops.** `adaptive-effect.rs`, `edit-magic.rs` and `app-agent.rs` prepare the
  recipe once per loop (`developed_pixel_prepared`, `display_pixel_prepared`).

Model additions for the UI (strehl-edit): `enabled` on `Heal`, `Backdrop` and
`ScaleBar` (the Layers eye; omitted when true, so recipes keep their bytes); a dark
backdrop key (`BackdropKey::Dark`, clean to black, as in the mockup's "clean to black
below 1.2 %"); `with_baked_repairs`; public prepared pixel accessors. The freeze tests
still pass (VERIFIED).

Performance (5.2/5.4), by construction (ARGUED; no 5.3 measurement for this stage):
the histogram is computed on the preview worker from a 256 px development; the split
view's "before" is one SDR overview per photograph, developed and uploaded on a worker,
so slider drags never redevelop it; the station parts draw shapes only. VERIFIED by
test: pointer-only motion over the inspector raises no intent.

Tests (VERIFIED): `cargo test --locked -p strehl-ui` 1143 passed, 0 failed, 19 ignored;
clippy `-D warnings` and `cargo fmt --check` clean for strehl-ui. New tests cover the
scope switch, layer ordering (tone order moves, repair-blend list order does not),
intents from inspector clicks, the depth brush, the depth repair flow, batch progress
and never-overwrite naming.

Open for stage 2 and later:

- Composition into the P1 shell, and the offscreen visual comparison at 1680 x 1050
  against `develop*.png` and `export.png` (10.2); not done here.
- The depth rail is the `RangeFallback` (two plane fields) until the Stack station's
  rail implements `DepthRail`.
- The HDR/SDR switch is stored (`prefer_sdr`); the presenter has no force-SDR call yet.
  The Clipping toggle is state only.
- Split view: the "before" side is the SDR overview (soft when zoomed past it).
- No camera-preview fill inside a painted stroke (optional, not built); the repair is a
  full re-stack in the background until E4/P7d.
- Archive files from a batch are not recorded in the export history.

## UI stage 2: Develop and Export in the shell (2026-11-21)

Composed into the P1 shell after merging the integration branch (`82ccbfd45`). The
composition lives in `crates/strehl-ui/src/app-station-develop.rs`; the shell's Develop and
Export arms are one-line calls into it.

| Shell slot | Develop | Export |
| --- | --- | --- |
| Tools (44 px) | `tools_strip`, 9 tools; keys B, M, C, W, H, D, R, S, N; `[` `]` brush size, `\` before/after | none |
| Control strip (36 px) | The tool's options (inline sliders), then After/Before/Split, surround, HDR/SDR, Clipping | Preview of the ticked presets, output size and estimate; Fit / Actual pixels |
| Rail | Depth rail while the depth brush is out (`RAIL_HEAD` + 34 px) | Exports of this photograph (152 px) |
| Canvas | `show_process`; overlays through the editor (brush, crop, heal, backdrop, scale bar, split, clipping) | `show_process`, then the selected preset's crop outline and scale bar |
| Inspector tabs | Adjust, Layers · n, Versions · n | Export |
| Inspector body | `tab_contents`, plus today's controls kept reachable (below) | Presets, preset editor, In every file, Name and place, View bundle |
| Footer (53 px) | Export… (chevron) and Save version | Export N files with its time estimate, or the batch with Cancel |
| Hint bar | B depth brush, `[ ]` brush size, `\` before and after, Ctrl Z, F | Ctrl E export the ticked presets, F, Ctrl K |

The palette is `StudioPalette::from_tokens(studio_theme::tokens(ctx))`, so Graphite,
Instrument and Lightbox all work; `station_paints_legacy` is false for both stations.

**The depth rail hook.** `show_develop_rail` passes `RangeFallback` (two plane fields) to
`station::depth_rail`. The Stack station's rail (P3) plugs in by implementing `DepthRail`
(`show(ui, palette, range, planes) -> Option<(first, last)>`) and replacing `RangeFallback`
in that one call; the head and the strip's "Take from planes …" stay.

**The HDR/SDR switch and Clipping work.** `ViewportRefinement::prefer_sdr` makes
`hdr_active` false while `hdr_available` stays true; the switch is shown only for an HDR
photograph on an HDR display. Clipping builds a 1024 px mask on a worker once per edit
(never while a button is held), uploads it there, and paints it over the photograph;
VERIFIED by `clipping_builds_its_overlay_on_a_worker_and_clears_it`.

**Today's controls that the mockup has no place for** stay reachable, so nothing was lost
with the old Edit and Export panes: Adjust ends with "Look in detail" (the adaptive panel:
treatment, where it changes, analysis notes), "Saved looks" (develop presets, Import XMP,
reset) and "Source evidence" (for a selected region); Layers ends with "Regions in
detail" (rename, duplicate, enable, source planes, shapes). They paint with the Graphite
constants, so on a light theme they sit in a Graphite well (`legacy_inset`). Retained
recipes and the editor's errors show at the top of the body; Display (status, peak and
reference white) was rebuilt on tokens. `edit_panel` and `export_panel` are no longer
called by the app (`expect(dead_code)` outside tests); they remain for their tests and as
the benchmark baseline.

### Offscreen comparison (1680 x 1050)

`visual-check.py` against `develop.png`, `develop-layers.png`, `develop-versions.png` and
`export.png`, plus Instrument and Lightbox renders of both stations (a temporary,
uncommitted hook opened the Layers and Versions tabs and the depth brush):

- Develop: tools, control strip, tabs, Adjust (scope, histogram, looks, Light, Colour,
  groups) and footer match the mockup's geometry and type. Layers and Versions match
  (this photograph has no layers, so Layers shows its empty state). The depth brush
  shows the strip and the rail head with `RangeFallback`.
- Export: presets with ticks, the Web preset editor, In every file, Name and place, the
  footer and the history table under the canvas match.
- Lightbox and Instrument: every station part is legible and ruled; the canvas stays
  dark (the theater paints its own ground).
- **Differs (not P7's file):** the canvas is still the theater, which keeps its contributions
  strip and filmstrip under the photograph and its "PHOTOGRAPH / EDIT" caption; on Export
  the theater is not in its focused layout in the offscreen render (also on the
  integration branch). The mockup shows the photograph alone. This needs a
  photograph-only mode in `process-theater.rs` (the Stack lane's file).

### Measurements (release, MEASURED)

Host: Ryzen 9 9950X3D (32 logical), CPU load 1 % at the end; build `82ccbfd45` plus this
stage's changes; `--test-threads=1`.

`benchmark_develop_and_export_pointer_sweeps` (CPU paint + tessellation, 6 rounds of 120
frames, 96 x 64 photograph):

| Arm | ms per frame |
| --- | --- |
| Shell, Develop | 0.142 – 0.152 |
| Shell, Export | 0.140 – 0.154 |
| Panel only, Studio 2 Develop inspector | 0.112 – 0.116 |
| Panel only, today's Edit pane | 0.141 – 0.162 |

The fixture has no captures, so these are not comparable with P0's 1.28–1.32 ms process
view; the like-for-like comparison is the last two rows (no regression).

`benchmark_develop_latency_on_a_real_master` (a copy of the weevil run, 7032 x 4688,
overview 1600 x 1067; canvas driven through `request_view` / `draw_overlay` as
`show_process` does):

| Measurement | Result |
| --- | --- |
| Slider drag to updated overview (40 steps at 60 Hz) | median 36.6, p95 86.1, max 114.6 ms |
| Frame time during the drag | median 0.19, p95 0.35, max 9.8 ms |
| Histogram per overview (256 px, on the preview worker) | median 0.74, p95 0.95 ms |
| Release to sharp patch at 6x | 124 ms |
| Pointer sweep at fit, After | median 0.15, p95 0.23 ms per frame |
| Split handle drag | median 0.08, p95 0.20 ms per frame; 0 viewport jobs, revision unchanged |

The overview pipeline is the stage 1 code that today's pane also uses; the histogram adds
0.74 ms (about 2 %) to each overview. Pointer-only motion over both stations changes no
recipe, history, library, tab, outbox or batch (VERIFIED by
`pointer_only_motion_over_develop_and_export_changes_nothing`).

Tests (VERIFIED): `cargo test --locked -p strehl-ui` 1264 passed, 0 failed, 23 ignored;
clippy `-D warnings` and `cargo fmt --check` clean for strehl-ui.

Open:

- The theater's photograph-only mode (above), and Export's focused canvas.
- The depth rail is `RangeFallback` until P3's rail implements `DepthRail`.
- "Compare with full size" (Export strip) is not built, so it is not shown.
- `edit_panel` / `export_panel` and their helpers can be deleted once the benchmark
  baseline is no longer wanted.
