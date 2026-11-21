# P3: the Stack station, stage 1

Branch `studio2/p3-stack`, from `61effa01b`. Implements the parts of
[spec 7.2](../../docs/proposals/2026-11-desktop-studio-2-implementation.md#72-stack-station) and
the improvements of spec 5.5 items 1 to 5, each as a self-contained module with its own tests,
on today's data structures. Stage 2 composes them into the station inside P1's frame.

Evidence labels as in the spec: MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED.

## Commits

| Commit | What |
| --- | --- |
| `38eb88131` | Depth rail model and painter (`depth-rail.rs`) |
| `038a5c195` | Plane lens; `DenseRegion::extract` off the paint path; instant inspection for the station |
| `aa63a1885` | Filmstrip and core sample |
| `4db0d3aaf` | Sparse resident tier, disk derivatives, worker-side texels and paced large uploads |
| `855ace995` | The timeline's lanes as one cached mesh |
| `59ffcc959` | Cached pin fingerprint; pooled probe heatmap |
| `0cd0305a0` | Long-stack paint, parts and scrub benchmarks |
| `f5c5e9218` | The mockup's interaction checks, ported; two fixes |
| `eda930bcd` | Dense region-probe evidence; benchmark fixes |
| `b2fb7a619` | In-place window recounts on long stacks |
| `1cb5a5e88` | The sparse tier warms in batches of 16 |
| `7f9f83998` | A cold sweep from open shows the sparse tier |

## Modules and their APIs

All in `crates/strehl-ui/src/`. New modules carry `#![allow(dead_code)]` until stage 2 uses
them; remove it then. Colours come in small palette structs with a `GRAPHITE` constant from
appendix A, so wiring P1's `Tokens` is one constructor per palette.

### `depth-rail.rs`

- `DepthRail::update(&mut self, archive, histories: &[SampledMaskHistory], planes, level, revision: u64) -> bool`:
  O(1) unless the key changed; recounts only receipts whose sequence changed.
- `evidence_revision(progress: &PipelineProgress) -> u64`: an O(1) key that moves with every
  packet, including history-only packets beyond the archive cap.
- `DepthRail::set_region(&mut self, key: Option<u64>, series: impl FnOnce() -> impl IntoIterator<Item = (plane, admitted, observed)>)`:
  the dashed line; feed it `CoreSample::rail_key` and `rail_series`.
- `DepthRail::interact(&self, ui, rect, id) -> RailResponse { hovered, clicked }`.
- `DepthRail::paint(&mut self, painter, rect, RailPalette, RailMarkers { hover, head })`.
- `paint_head(painter, rect, RailPalette, &RailHead { planes, step, reading })`.
- Queries: `share(plane)`, `evidence(plane)`, `peak()`, `brackets()`, `has_region()`.
- `RailGeometry::new(rect, planes)`, `x(plane)`, `plane_at(x)`, `columns`, `pooled()`.

Bars are the share of sampled sites admitted at the level, normalised to the busiest plane
(the peek and two-up print the absolute share). A plane observed at zero draws a 1 px rule; an
unobserved plane draws a hatch. "No subject detail" brackets use `NO_DETAIL_FRACTION` (3 % of
the peak), a display heuristic that is UNVALIDATED and must not become a check (D4).

### `filmstrip.rs`

- `Filmstrip::layout(&mut self, width, planes)`; `planes() -> Vec<usize>` (pass to
  `SourceBrowser::poll` as the visible set).
- `Filmstrip::sync(&mut self, epoch, photos: &[SourcePhoto], canonical: &[SourcePhoto])`:
  adopts only published textures; a canonical bridge never downgrades; a new run drops all.
- `Filmstrip::update(&mut self, archive)`: 17 × 8 counts per archive revision.
- `Filmstrip::interact(&self, ui, rect, id) -> FilmResponse { hovered, clicked }`.
- `Filmstrip::paint(&mut self, painter, rect, FilmPalette, FilmMarks { pointer, held })`.

### `plane-lens.rs`

- `PlaneLens`: `set_planes`, `hover(Option<plane>)`, `click(plane)`, `hold`, `release`,
  `step(delta)`, `key(LensKey, shift)`, `read_keys(ui) -> bool`, `choose_plane_lens(default)`,
  `set_level`; queries `shown()`, `held()`, `hovered()`, `peeking()`, `holding()`,
  `inspection() -> (hover, held)` for `ProcessTheater::set_inspection`.
- `PlaneLensView::region(&mut self, ctx, LensEvidence, plane, level) -> RegionLookup`
  (worker-backed; `lookup.frame` names the region actually drawn).
- `PlaneLensView::paint_final_region(painter, region, image, aperture, LensPalette)`;
  `PlaneLensView::dim(painter, image)`.
- `PlaneLensView::paint_peek(painter, card, anchor_x, plane, share, preview: Option<LensPhoto>, region, LensPalette)`.
- `PlaneLensView::paint_two_up(ui, &TwoUpLayout, LensEvidence, plane, level, final: LensPhoto, preview: Option<LensPhoto>, LensPalette) -> TwoUpResponse { level }`.
- `two_up_layout(canvas, aspect) -> TwoUpLayout`; `peek_rect(canvas, rail, planes, plane)`;
  `kept_share`, `percent`, `size_label`.

### `core-sample.rs`

- `CoreSample::show(&mut self, ui, CoreInput, previews: &dyn Fn(plane) -> Option<LensPhoto>, CorePalette) -> CoreResponse { region, live, leading, peak, action, popover }`.
- `CoreSample::pin(at, image, aperture)`, `unpin() -> bool`, `pinned()`,
  `rail_key(level)`, `rail_series(level)`, `probe_mut()` (for `set_fallback`, `resize`).
- `CoreAction::{ShowPlane(plane), Repair(region), Note(region)}`.
- `span(values, fraction) -> Option<Span>`; `sentence(values, observed, size, fallback)`.

### Changes to existing modules

- `process-admission-regions.rs`: `DenseRegionWorker` (`region`, `prefetch`, `ready`,
  `pending`, `poll`); `KeptStyle { fill, dots }` with `LENS` and `SMALL`;
  `DenseRegionPainter::paint_kept`.
- `process-theater.rs`: `instant_inspection` (the station sets it; the engine room keeps the
  0.24 s animation); `set_inspection(hover, held)`; `region_pending()`; single-capture regions
  use the worker.
- `process-region-probe.rs`: `measure`, `window_counts`, `leading`, `leading_sites`,
  `window_revision`, `measured_region`, `fallback_fraction`, `side`; `region_at` and
  `popup_placement` are `pub(crate)`; evidence is a dense per-level store.
- `source-browser.rs`: the sparse tier, `nearest_resident(index)`, worker texels, upload pacing.
- `source-preview.rs`: `DetailPreview`, `texels`; `source-preview-disk.rs` (disk derivatives).
- `process-participation.rs`: cached lane mesh; in-place window recounts.
- `process-fingerprint.rs`: cached cells; `process-region-visual.rs`: pooled heatmap.

## Performance

Machine: the owner's desktop (32 threads). Release test binaries: the baseline is the P0 build
of `61effa01b` (`target-bench`, 02:42), copied unchanged; P3 is built from this branch. Runs are
interleaved A/B by `perf/run-p3.sh`; CPU load and the number of running compilers (other agents)
are logged before each run in `perf/p3/run.txt`. Figures are the minimum per run of CPU paint plus
tessellation per frame (GPU and presentation excluded), with the run-to-run spread.

### Full workspace, 130 captures (spec 5.3 "pointer sweep paint")

MEASURED with `benchmark_finished_workspace_pointer_sweeps`, three interleaved runs each, CPU load
0 to 6 % and at most two other compilers (`perf/p3/run.txt`, 04:44). Minimum per run, ms per frame.

| View | Baseline `61effa01b` | P3 `b2fb7a619` | Change |
| --- | --- | --- | --- |
| Process | 1.243, 1.269, 1.251 | 0.712, 0.727, 0.725 | −42 % |
| Source | 0.456, 0.458, 0.456 | 0.407, 0.410, 0.408 | −11 % |
| Tessellated vertices (process, source) | 223,300 and 112,006 | 226,940 and 115,654 | +1.6 %, +3.3 % |

P0 recorded 1.28 to 1.32 and 0.45 to 0.48 at 1 % load. Earlier runs this session under load (29 to
100 %, five or six compilers): baseline 1.26 to 1.34, P3 0.78 to 0.81 (process); 0.455 to 0.461
against 0.457 to 0.476 (source). No regression beyond 5 % in any run. The gain comes from the
cached lane mesh and the cached pin fingerprint (DERIVED from the changes; not profiled).

### Long synthetic stacks, the existing theater (spec 5.3 budget: 6,000 within 1.25 × 130)

MEASURED, `benchmark_long_stack_pointer_sweeps`, two runs, P3 only (the baseline has no such
fixture). The archive keeps at most 8,192 maps today, so long fixtures carry 8,192 retained maps;
the fixture hands the theater at most 512 photographs, as `SourceBrowser` does.

| Planes | Maps retained / dropped | Process ms | Source ms |
| --- | --- | --- | --- |
| 130 | 1,040 / 0 | 0.703, 0.713 | 0.402, 0.407 |
| 1,500 | 8,192 / 3,808 | 2.243, 2.273 | 1.591, 1.619 |
| 6,000 | 8,192 / 39,808 | 2.647, 3.385 | 2.055, 2.703 |

**Budget not met:** 6,000 planes cost 3.7 to 4.8 times the 130-plane figure, against 1.25. Every
frame stays far inside 8.3 ms. See open issues for the cause and the stage-2 design.

### The Stack station's parts

MEASURED, `benchmark_stack_parts_pointer_sweeps` (rail, filmstrip, core sample, plane lens at the
reference rectangles; 120-step sweeps), two runs, P3 only. ms per frame, minimum.

| Planes | Over the photograph (live core sample, rail region line) | Along the rail (peek, worker regions) |
| --- | --- | --- |
| 130 | 0.118, 0.118 | 0.034, 0.032 |
| 1,500 | 0.619, 0.619 | 0.040, 0.043 |
| 6,000 (8,192 maps) | 0.668, 0.665 | 0.043, 0.042 |

Before the dense evidence store and in-place recounts (`f5c5e9218`): 0.16, 1.21 to 1.31 and 1.35
to 1.47 over the photograph. The rail sweep is flat: the series and engraving are cached, and
region extraction runs on the worker.

### Real RAWs, 299 planes (`bug-3/107MSDCF`, read-only)

MEASURED, `benchmark_real_stack_scrub_publication`, interleaved A/B, CPU load 0 to 9 %.

| | Baseline | P3 |
| --- | --- | --- |
| Resident warming | 1,461.5 and 1,439.3 ms | 1,455.6 and 1,452.7 ms (1,460.4 with sparse batches of 16) |
| Warm sweeps, both directions | 299 of 299 immediate, 0 uploads, 0 tasks (assertions pass) | same |
| Longest poll while warming | 2,360 and 2,630 µs | 574 and 731 µs |

Stacks up to 512 captures have no sparse tier and keep the baseline's schedule. The longest warming
poll falls about four times because detail texels are prepared on the worker and a large tier
uploads alone.

### Real RAWs, 1,444 planes (`bug-7/100MSDCF`, read-only)

MEASURED, P3 only (the baseline benchmark refuses more than 512 RAWs). The disk derivatives use an
emptied scratch folder per run. "At rest" timings start after a first 11.5 s cold sweep.

| | Sparse batches of 4 (`b2fb7a619`) | Batches of 16 (`1cb5a5e88`) |
| --- | --- | --- |
| Sparse tier warm, at rest | 2,054 and 2,113 ms | 1,072 and 1,462 ms |
| Sparse and scrub tiers warm | 4,136 and 4,220 ms | 3,193 and 3,566 ms |
| Reopen: sparse tier from the disk derivatives | 2,171 and 2,173 ms | 713 and 716 ms |
| Sparse tier memory | 33.0 MB (482 pictures, every third plane, 160 px) | same |

Acceptance sweep (scrub, overview and image tiers removed; sparse tier only), both directions,
both runs: every step shows the plane (482 and 491 steps) or a neighbour one plane away (962 and
953), never nothing. Poll p95 0.60 to 0.67 ms; maximum 4.6 to 7.9 ms when a refined plane uploads.

**First sweep straight after opening** (8 ms per step, nothing resident). Before `7f9f83998`, as in
the baseline, nothing was displayed on any of the 1,444 steps: every step is cold, so sparse
batches were cancelled as obsolete warming and outranked by the moving contact neighbourhood. After
it (`7f9f83998`, two runs, CPU load 5 %): a picture on 1,441 and 1,440 of 1,444 steps, from the
fourth step (about 30 ms after opening); the plane itself on 481 and 480 steps, otherwise a
neighbour one plane away (median and maximum distance 1). Poll p95 0.62 and 0.65 ms, maximum 1.7
and 3.1 ms. Sparse and scrub tiers warm 2,372 and 2,539 ms after the sweep; a reopen warms the
sparse tier from the disk derivatives in 633 and 631 ms. Raw outputs: `perf/p3/`,
`perf/p3-sparse16/`, `perf/p3-sweep/`.

## Tests added

- Depth rail (11): exact maps, history bins and missing planes; pooled history above 1,024
  planes; the revision key; recount only changed receipts; zero rebuilds under pointer motion;
  region series read only on key change; 646 columns at 6,000 planes; the scale at 299 planes and
  numerals hiding under markers; zero against missing drawing; brackets; geometry.
- Plane lens (9): peek, hold, hover-and-leave, click toggles; arrows, Shift, Escape and stale
  hover; `read_keys` per-event modifiers; the Plane lens default; worker extraction keeps the
  previous region and caches; layout against the reference rectangles; the two-up's eight maps,
  zero mesh rebuilds and a size-map click; prefetch never replaces the shown region; shares.
- Filmstrip (4), core sample (5), sparse tier, sweep-from-open and pacing (5), disk derivatives (2).
- Ported interaction checks (`stack-flow-tests.rs`, 4): check.html items 1 to 5 at module level.
- Theater: the production region worker reaches the photograph; the animation opt-out.
- Zero-rebuild extensions: the lane mesh under a sweep across all captures; the fingerprint.
- Benchmarks (ignored): `benchmark_long_stack_pointer_sweeps`,
  `benchmark_stack_parts_pointer_sweeps`, and the resident benchmark up to 6,000 RAWs.

Totals: `cargo test --locked -p strehl-ui`: 1,104 passed, 18 ignored (VERIFIED, last run at
`7f9f83998`).
`cargo clippy ... -D warnings`: the only failure is the pre-existing `unnecessary_cast` at
`capture-workspace.rs:1772`, fixed by another phase. `cargo fmt -- --check`: clean.

## What stage 2 must do

1. Compose the station in P1's frame at the appendix B rectangles: control strip, canvas (the
   photograph, or the two-up while holding), rail head 30, rail chart 84, filmstrip 75.
   `stack-flow-tests.rs` is a working reference for the wiring order: rail and filmstrip
   interact, `PlaneLens::hover`/`click`/`read_keys`, then the canvas (two-up or core sample and
   peek), then `set_region` and the rail and filmstrip paints.
2. Feed the lens into the theater with `ProcessTheater::set_inspection(lens.inspection())` and
   set `instant_inspection = true` on the station's theater, so previews come through
   `SourceBrowser` as today. Previews for the peek card and the two-up: the theater's inspection
   slot (`texture_snapshot`); never a new decoder.
3. Pass `Filmstrip::planes()` into `SourceBrowser::poll` as visible frames.
4. Give `CoreSample` the photograph rect, aperture, the result texture, the analysis and output
   extents, and `probe_mut().set_fallback(...)` from the averaging packet, as `ResultPhoto` does.
   Route its clicks: a photograph click calls `pin` unless inside `response.popover`;
   `CoreAction::ShowPlane` holds; `Repair` opens Develop with the region; Escape unpins.
5. Palettes from P1's tokens; the detail spectrum from appendix A (`SPECTRUM_DARK` today).
6. Peek dimming: brightness is an overlay today (`PlaneLensView::dim`); the 75 % saturation needs
   the photograph presenter's shader (`PEEK_SATURATION`).
7. Swap `evidence_revision` for P2's evidence-file revision if P2 adds one; raise nothing here.
8. Repeat the full-app checks (spec 10.1 items 6 to 9) and the offscreen renders (10.2).

## Stage 2: the composed station

Merged the integration branch twice (`00f1e810e`, then `91ebd7e70` with every other station);
conflicts kept both sides. The station lives in `app-station-stack.rs` (`StackStation`, one field
on `StrehlApp`); the Stack arms in `studio-shell.rs` call into it.

### What is wired

- **Layout:** control strip 36, canvas, rail 190 (head 30, chart 84, filmstrip 75) and the
  inspector, per appendix B; the photograph at 128, 94, 1076, 718 (tested).
- **Control strip:** lens switch (Photograph, Plane; Depth, Soft spots and Alignment shown but
  off until their evidence exists), detail size 2 to 256 underlined in the spectrum, the hold note
  with Esc, Fit / 100 %, and the render pair.
- **Canvas:** the photograph through the same HDR presenter and detail patches as Develop
  (`editor.photo_paint`, `request_view`), wheel zoom about the pointer, drag pan, double-click
  fit. The plane lens: peek (dimmed photograph, kept region with fill, contour and 7 px sample
  dots, the 372 x 276 card with the plane's camera preview and approximate outline), hold (the
  two-up and eight size maps; a size map sets the detail size), keys 1-5, Left/Right, Shift,
  Escape, Space for the clean photograph. The core sample live under the pointer, pinned by a
  click, Show the plane holds its leader, Repair here opens Develop.
- **Rail:** head (title, plane count, keys, reading), the depth rail with hover and head markers
  and the core sample's dashed line, and the filmstrip (textures from `SourceBrowser` only, its
  frames warmed as visible contacts).
- **Inspector:** Checks (verdict, tally, check rows with marks only where the threshold is a fact,
  spec D4), Recipe (today's Adjust controls), Renders (the stack's renders; click reopens one).
  Footer: Develop this render, Render again; while a stack runs, Stop and Queue a render (P5's
  `queue_while_running`).
- **Evidence:** kept shares from P2's `plane_share`; a pooled `Bin` source is labelled
  approximate on the peek card and the two-up.
- **Engine room (E):** today's process view with its 0.24 s animation, also shown while a render
  has not finished. The old process view no longer shows in the photograph room.
- **Themes:** palettes from `studio_theme::tokens`; `station_paints_legacy(Stack)` is false in the
  photograph room, true in the engine room.
- **Offscreen:** `--route stack --open-run <run>`; `--plane-hold N` holds plane N.
- **Develop hook:** `station_stack::DevelopRangeRail { station: &mut self.stack_station,
  progress: &self.progress }` implements P7's `develop_station::DepthRail` from the real rail
  (pooled kept share at the finest size, the range shaded, drag to choose). P7 replaces
  `&mut RangeFallback` in `app-develop.rs` with it.
- **Develop and Export canvas:** `ProcessTheater::photograph_only`, set by `station_canvas` for
  both: the photograph alone in the standalone layout (no journey, timeline, instruments,
  captions, legend, review strip or Scene button; diagnostics suppressed), `edit_mapping`
  unchanged for P7's overlay. Verified offscreen on `develop` and `export`.
- **Open issues closed:** bounded recounts (`RECOUNT_BUDGET`, 4,096 windows per frame, double
  buffered, newest window after the current one); pinned ranges off the paint path
  (`DenseSelectionWorker`); readiness while the station owns the canvas (`set_station_busy`).

### Offscreen comparison (release, 1680 x 1050, the 299-plane weevil run)

`visual-check.py ... stack stack-plane-held stack-instrument stack-lightbox engine` (the new
`stack-plane-held` route uses `--plane-hold 128`), each looked at in full beside its reference:

| Screen | Verdict |
| --- | --- |
| `stack` | Matches the chrome and slots: strip, photograph rectangle, rail head, chart, scale, 17 frames with marks, Checks tab, footer, hint keys. Data is real, so bars, brackets and checks differ from the illustrative mockup; no scale rule (no calibration, D12). |
| `stack-plane-held` | Matches: captions, two-up at 16, 186, 643 x 429, eight size maps with kept shares, held frame and head marker. |
| `stack-instrument`, `stack-lightbox` | Render natively in their tokens (paper panels, dark surround on Lightbox). |
| `engine` | Today's process view in the engine room, as intended. |

### Performance (stage 2)

MEASURED with `perf/run-p3-stage2.sh` (baseline P0 binary and the stage-2 binary `8f92802ac`,
interleaved; CPU load 0 to 13 %; outputs in `perf/p3-stage2/`). Minimum ms per frame, CPU paint
plus tessellation (GPU excluded).

| Measurement | Baseline | Stage 2 |
| --- | --- | --- |
| Engine room, 130 planes, process view | 1.245, 1.251, 1.332 | 0.736, 0.708, 0.732 |
| Engine room, 130 planes, source view | 0.443, 0.464, 0.474 | 0.394, 0.394, 0.408 |
| Stack station, photograph sweep (live core sample): 130 / 1,500 / 6,000 synthetic | n/a | 0.173-0.175 / 0.355-0.365 / 0.512-0.547 |
| Stack station, rail sweep (peek): 130 / 1,500 / 6,000 | n/a | 0.116-0.126 / 0.113-0.121 / 0.116-0.140 |
| Stack station, held arrow steps: 130 / 1,500 / 6,000 | n/a | 0.138-0.149 / 0.129-0.140 / 0.133-0.146 |
| Stack station, the real 1,444-plane render (11,552 maps, log streamed read-only): photo / rail / held | n/a | 0.426 / 0.168 / 0.182 |
| Engine room, 6,000 synthetic planes (48,000 maps): process / source | n/a | 2.63-3.81 / 2.19-3.15 |
| Resident warming, 299 real RAWs | 1,464.6, 1,463.3 ms | 1,467.5, 1,452.0 ms |
| 1,444 real RAWs: both tiers / sparse-only sweeps / reopen | n/a | 2,387 ms / never blank, worst one plane / 632 ms |

The 6,000-plane fixtures now keep all 48,000 maps (P2's cap). Against spec 5.3's 1.25 x budget:
the station's rail and held steps are flat with length (1.0-1.1 x); its photograph sweep is 3.0 x
its own 130-plane figure, and 0.41 x the baseline's 130-plane process view. The engine room's
process view still grows with length (timeline region lane; the probe is bounded). Live render
frame times (`check-display-performance.py` during a render) were not measured: it needs the
desktop window and a full render on the owner's machine.

## Open issues

- Long-stack paint budget (spec 5.3: 6,000 planes within 1.25 × the 130-plane figure) is not met
  by the engine-room theater's timeline (the region probe is now bounded; stage 2 above). MEASURED above. The cost is the pointer's region: each
  time it crosses a sample cell, the timeline's region lane and the region probe recount every
  plane at the level (inherently O(planes); DERIVED from the code paths and the measured scaling,
  not profiled); constant factors are reduced here. Design for
  stage 2: double-buffered, budgeted recounts (at most about 2,000 planes per frame, the previous
  complete series shown until the new one completes, the newest window started only after the
  current one finishes), so frame cost is bounded at any length while the display stays
  consistent. P2's raised archive cap (65,536 maps) increases this cost at coarse levels.
- Pinned ranges moved to `DenseSelectionWorker` in stage 2; the synchronous cache remains as the
  tests' reference.
- Peek saturation (75 %) is not applied: it needs a presenter uniform and an SDR path; brightness
  is dimmed.
- The engine-room timeline's region lane now recounts within the budget (round 3); its lane mesh
  and plot still rebuild at each commit.
- The lane mesh adds 3,640 tessellated vertices at 130 captures (circles tessellated without
  egui's prepared discs, which `FontsView` does not expose in egui 0.33). MEASURED; paint time
  still fell.
- Disk derivatives are bounded at 160 MiB and 1,024 entries (spec: "e.g. 128 MiB / 512") because
  the sparse and scrub tiers share the folder. The folder is new on the owner's machine:
  `%LOCALAPPDATA%\Strehl\source-previews` (next to the catalog). Unit tests never use it.
- A sweep straight after opening a long stack shows nothing for its first three or four steps
  (about 30 ms), until the first sparse batch lands. MEASURED.
- The sparse tier changes the film lane's order only for stacks longer than 512 captures and only
  while it is incomplete; shorter stacks keep the baseline's schedule (their tests are unchanged).
- "No subject detail" threshold and the per-size mark scaling in the filmstrip (per level, across
  the frames shown) are display choices, UNVALIDATED.

## Round 3: flakes, long stacks, live render (after P2 round 2)

`studio2/p2-evidence` (27e30b95e) is merged into this branch (`54c0f7808`). The probe keeps its
dense store and bounded recount and takes P2's ordered archive pass; the perf fixture keeps its
`frames` field and takes `STREHL_UI_BENCH_FRAMES`. P2's 24 `ui_` CLI tests and all strehl-ui
tests pass; 13 research tests in strehl-cli (`m194f`/`m194g`, gatefloor controls) fail here for
want of private experiment files, unrelated to either branch.

### Flaky tests

- `last_filmstrip_photos_remain_fixed_and_opaque_during_end_follow_and_real_wheel_input`: the
  selection's neighbour overview (radius 4 reaches frame 27) can land before the contact batch
  and legitimately give the contact a derived 3:2 thumbnail (ARGUED from the scheduler; not
  reproduced in 192 parallel isolated runs or 10 full-suite runs of the old build). A test-only
  `hold_canonical_tiers` keeps detail, scrub and sparse off until the native contacts are in,
  asserted, then releases it (`0b8c656e1`).
- A second flake turned up in the first five-run check (1 of 5):
  `dropping_a_session_answers_pending_requests_with_an_error_instead_of_losing_them`. The app
  publishes final replies before it deletes `session.json`; a client that checked for its reply
  just before and for the descriptor just after reported a disconnection. It now looks once more
  for its reply (`aef460f3d`). ARGUED from the code; not reproduced in 256 isolated runs.
- MEASURED: five full `cargo test --locked -p strehl-ui` runs in a row on `423bffdfb`, 1,366
  passed each, 0 failures (`perf/p3-round3/suite5-final.txt`; the earlier five, with the bridge
  flake, are in `suite5-before-bridge-fix.txt`).

### Long stacks (spec 5.3: 6,000 within 1.25 x the 130-plane figure)

Temporary section timers (not committed) found, at 6,000 planes: the region probe recounting all
eight levels (4,096 windows a frame), the engine room's region lane recounting all 6,000 captures
per window crossing (about 1 ms) and its lane mesh rebuilt on each crossing (0.6 ms). Only the
active level is ever read, so the probe now counts that level alone; the region lane recounts
within the same budget, staged and committed at once (`423bffdfb`). Budget 512: a 6,000-plane
window commits after twelve frames, the previous complete one shown meanwhile.

MEASURED, release, interleaved: A = merge commit, B = this change at budgets 4,096, 1,024 and 512
(one binary, budget from an environment variable for the run only). Load 7 to 22 %. Minimum ms per
frame; outputs in `perf/p3-round3/`.

| | A | B 4,096 | B 1,024 | B 512 |
| --- | --- | --- | --- | --- |
| Station photograph sweep 130 / 6,000 | 0.155-0.167 / 0.448-0.453 | 0.122 / 0.250-0.251 | 0.123-0.125 / 0.163-0.170 | 0.122-0.123 / 0.137-0.141 |
| Engine room process 130 / 6,000 | 0.703-0.715 / 2.78-3.52 | 0.622-0.625 / 1.65-1.90 | 0.624-0.629 / 1.15-1.18 | 0.618-0.624 / 0.90-0.91 |
| Engine room source 130 / 6,000 | 0.379 / 2.33-2.63 | 0.325 / 1.04-1.09 | 0.324-0.333 / 0.57-0.69 | 0.325-0.335 / 0.45-0.49 |

At 512 the station's photograph sweep meets the budget (1.12-1.15 x). The engine room does not:
1.45 x its own 130 figure for process, 1.33-1.5 x for source (1.27 x the old 130 figure). What
remains is the lane mesh and plot rebuilt at each commit (DERIVED from the timers).

### Live render frame times (item 4)

MEASURED with `p3-live-measure.py`: a native window driven only through the control interface,
isolated catalog, output, capture settings (absent) and LOCALAPPDATA / STREHL_CACHE_DIR in
scratch; desktop sha256 `60dfe168…` (the item-2 build); GPU fold; default route (the Stack
station). `App::update` CPU ms per frame:

| Render | Stage | Frames | p50 | p95 | Max | Over 16 ms |
| --- | --- | --- | --- | --- | --- | --- |
| 299 (24.5 s, load 53 %) | Alignment / Merge / Rendering / Complete | 1,654 / 565 / 179 / 149 | 0.28 / 0.36 / 0.29 / 0.29 | 0.53 / 0.93 / 0.92 / 0.53 | 9.6 / 2.9 / 1.5 / 2.9 | 0 |
| 1,444 (65 s, load 69 %) | Alignment / Merge / Rendering / Complete | 6,172 / 3,432 / 255 / 218 | 0.25 / 0.35 / 0.38 / 0.30 | 0.72 / 1.01 / 0.84 / 0.59 | 44.3 / 15.2 / 4.6 / 11.8 | 10 / 0 / 0 / 0 |

While evidence streams (Merge) no frame exceeds 16 ms (P2 measured 4 to 16 such frames, max 20
to 36 ms, before this branch). Ten Alignment frames at the 1,444 start, before any evidence,
reach 25 to 44 ms; not attributed (open).

### Not done this round

- Peek saturation (75 %): the presenter's `Parameters` uniform could take a look vector, but the
  SDR path draws through egui images and would have to route through the shader; not contained
  in the time. Brightness is still dimmed.
- DevelopRangeRail (done, `14773d8a7`): offscreen with `--depth-brush` on the 299 run, the rail
  drew the kept-share series and the brush range correctly but in a fixed 280 px box beside a
  stale caption; it now spans the slot. VERIFIED by a second offscreen render (crop inspected).
