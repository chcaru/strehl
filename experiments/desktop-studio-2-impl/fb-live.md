# Capture feedback: depth rail scale, subject box handles, live view (fb-live)

**Date:** 2026-11-21. **Branch:** `studio2/fb-live`, from `ef98da086`; code
commit `b3513c88b`. **Scope:** the owner's three requests on the Capture
screen, plus the jog buttons' minus sign (found by the parallel plan agent).
Files: `capture-rail.rs`, `capture-live.rs`, `capture-aids.rs` and their
`-tests.rs` siblings; small additive edits to `capture-station.rs`,
`capture-fixture.rs`, `main.rs`, `app.rs`, the UI README's key table and
`visual-check.py`. `capture-axis.rs` is the Stack station's capture axis and
needed no change. **Labels:** MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED.

## Requests (verbatim)

1. "on the Capture screen, in the depth rail, i need a way to change the scale
   of the rail, so i can change focus large to fine. i think a natural way to
   do this would be some slide that is bound to scroll when hovering over the
   depth rail."
2. "on the Capture screen, i want to be able to resize the subject box by
   grabbing the typical box handlers. right now, i can only redraw the entire
   box and it is awkward."
3. "on the Capture screen, the "LIVE VIEW" graph doesn't look good. it's not
   antialiased. would be nice to enrich with useful information."

## What was built

| Item | What |
| --- | --- |
| Rail scale | The wheel over the rail zooms around the pointer (one notch scales the span by √2; over the head row, around the lens while it is in view). Shift and the wheel, a sideways wheel, or a drag on the empty rail pans. The head row's **Scale** slider shows the span on a log scale (the whole travel at the left, 32 units across at the right) with decade ticks and an accent mark where Fit is; beside it the visible span and units a pixel ("1,074 units · 0.83/px"). **Fit** (or a double click on the slider) returns to the bounds and the survey. The caption "lens travel, in the camera's focus units" became the hover text of DEPTH RAIL to make room. |
| Easing | A change of view eases over 140 ms (ease-out cubic, span on a log scale, the position under the pointer held still); a new goal mid-way restarts from where the view is; reduced motion snaps. A drag pans directly. |
| Travel | Views stay inside 0-65,535 (the host's focus range) and no finer than 32 units across. |
| Re-picked scale | Major labels about every 110 px on 1-2-5 steps; minor ticks the finest 1-2-5 step that divides the major and leaves 9 px (single units when zoomed in). |
| Bars | One bar a plane on the plan's grid (whole steps, at least 3 px), so they stay put while panning; each as tall as the survey profile's peak over the focus range it stands for (coarse bars keep the peaks); bars wholly out of view are skipped. |
| Ticks | Planned or flight ticks inside the view, pooled to 2 px columns counted from focus 0. |
| Precision | A click, a dragged bound or the dragged lens lands on the scale's resolution: the smallest of 1, 2, 5, 10 ... units not finer than a pixel (1 unit at fit for the fixture, 100 at the whole travel). The hover readout shows the same value. |
| Markers | START/END drag as before; the lens is now draggable (a "Focus to" ghost, `Focus` on release, through the existing coalesced focus path). Bounds and lens out of view get edge markers with their values. A lens moved out of a zoomed view brings it along (to the margin after a short move, centred after a long one); the first sighting and deliberate pans do not. |
| Cache | The rail mesh is rebuilt only when its inputs or the view change, into the previous mesh's buffers when the painter has let go of it; the survey profile and the planned positions are cached by their inputs. |
| Jog minus | "-128 -16 -1" in ASCII: the UI face draws U+2212 on the baseline ("_128"). No other U+2212 in these files. |
| Subject box | Eight 7 px square handles (corners and edge midpoints), white-ruled over a dark fill, the one under the pointer or being dragged filled white; the corner marks are kept. Hit order: corners, edge midpoints, the edges themselves (4 px), inside, outside; handles reach 8 px. A handle resizes (resize cursors NW-SE, NE-SW, horizontal, vertical); inside moves (Grab, Grabbing); outside draws a new box (Crosshair). Clamped to the picture, at least 0.05 a side (the host's `Roi::valid`), never inside out. While dragging the caption gives the size ("62 × 48 % of the frame"). The box goes to the host on release as before (`SetRoi`), and the sent box is shown until the host reports it (3 s at most), so it does not jump back. The picture's hit area reaches the handles on its border; the estimate panel absorbs presses. |
| LIVE VIEW panel | 300 × 202 (was 244 × 106; it rises above the tool bar when the picture is too narrow for both). Histograms antialiased: luma filled and stroked (1.25), R, G and B as 1 px feathered lines, square-root scale over the codes between the end zones, 5-tap binomial smoothing, curves drawn only where they hold counts. End zones: codes 0-3 and 254-255, stronger when they hold pixels; under them "N % black" and "N % clipped" (warn above 0.05 %). FOCUS · SUBJECT BOX: the box's focus over the last 48 previews (newest at the right, sharpest marked with a rule), "N % of the best", "sharpest at lens 37,540", "last N previews". Exposure (ISO, shutter, aperture) and previews a second. "estimate, not the RAW" kept. |
| Focus reading | The mean squared luma Laplacian over the subject box (the peaking filter's response before its floor), from tiles. The trace restarts when the box, magnifier ratio, ISO, shutter or preview size changes (readings are not comparable across them). |
| Analysis | On the client thread only, once per preview, where the clip mask was computed: `PreviewLevels::analyze` adds R, G, B histograms and the black share (all channels at or below code 3) and uses integer Rec. 709 luma; `Peaking::analyze` sums the squared Laplacian over a fixed 32 × 24 tile grid in the loop it already ran (per tile span, in integers, no bounds checks). The UI reduces at most 768 tiles to the box once per preview or box, and rebuilds the histogram and trace meshes once per preview. |
| Fixture and flags | The plan fixture seeds a fabricated focus trace (a peak at 37,540) so the panel shows one offscreen. `--capture-rail-view LO-HI` opens the rail zoomed. `visual-check.py` gained `capture-plan-rail-zoom`, `capture-plan-rail-travel` and `capture-plan-box-hover` (`--screenshot-hover` on the east handle). Hint bar: "Wheel · rail scale". |

## Decisions

- The slider runs coarse to fine left to right, so the wheel turned away from
  you (finer) moves its thumb right. The readout gives both the span and the
  units a pixel; the span tells how much of the travel is visible, the units
  a pixel what a click can resolve.
- Bars stay one a plane at every scale rather than one a pixel, so zoomed in
  they are the planes' slabs and line up with the plane ticks.
- Clicks are quantised to the scale's resolution instead of to single units:
  a click at the whole travel cannot mean a single unit anyway (about 51 a
  pixel), and the jogs and arrow keys still move by 1.
- The lens drag sends one focus target on release, not a stream: the rail's
  editable flag drops while a focus move is in flight, which would cancel a
  live drag, and the host's focus moves are slow.
- The focus measure is relative only (share of the best of the trace), never
  an absolute number: it depends on the subject's texture, exposure and the
  preview's JPEG coding, and is labelled with the panel's caution.
- Histograms are frame-wide, like the clip overlay and the agent snapshot's
  `clipped_share`; the black share in a black-background macro frame is
  honest but large (68 % in the fixture).
- The trace is computed from the host's box (what the survey and magnifier
  use), not a box being dragged.

## Commands and results

Worktree `C:\w\f-live`, `CARGO_BUILD_JOBS=12`, Windows 11, 32 logical CPUs,
other agents building in their own worktrees at the same time.

| Command | Result |
| --- | --- |
| `cargo test --locked -p strehl-ui` | MEASURED: Compiling strehl-ui (in the preceding `rail::tests` run on the same sources); 1404 passed, 0 failed, 34 ignored. Base `ef98da086` had 1417 tests in all; 19 tests and 2 ignored benchmarks were added |
| `cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings` | MEASURED: Checking strehl-ui; exit 0 |
| `cargo fmt -p strehl-ui -- --check` | MEASURED: exit 0 |
| `cargo test --release --locked -p strehl-ui preview_analysis_cost -- --ignored --nocapture --test-threads=1` (60 runs, median; synthetic preview with a textured ellipse) | MEASURED, release. Base `ef98da086` (same test, run first): 640 × 480 Peaking 0.340 + Levels 0.758 = 1.098 ms; 960 × 640 0.668 + 1.487 = 2.155 ms; 1024 × 680 0.767 + 1.710 = 2.477 ms. After (two rounds, equal to 0.005 ms): 640 × 480 0.498 + 0.436 = 0.934 ms; 960 × 640 0.983 + 0.866 = 1.849 ms; 1024 × 680 1.107 + 0.979 = 2.086 ms. Peaking costs about 0.3 ms more (the tiles), Levels about 0.6 ms less (integer luma): the client thread's per-preview total is lower at all three sizes. The base and after runs were about an hour apart, with other agents building. The UI's box reduction from the tiles: 0.0016 ms median |
| `cargo test --release ... rail_zoom_cost -- --ignored --nocapture --test-threads=1` (rail alone, 1332 × 135, 665 planned ticks, paint and tessellation, 240 frames, three runs, two rounds) | MEASURED: hovering 0.0198-0.0214 ms/frame (1 mesh build); zooming with the wheel every frame (208 mesh builds in 240 frames) 0.0256-0.0271 ms/frame |
| `cargo test --release ... capture_station_pointer_sweeps -- --ignored --nocapture --test-threads=1`, the new binary and the saved base binary interleaved, two rounds | MEASURED: plan 0.169-0.170 ms/frame after (12,120 vertices) against 0.154-0.156 base (8,724 vertices); flight 0.110-0.111 against 0.106-0.109. The added vertices are the antialiased histogram and trace, the handles and the head's scale controls |
| `pointer_motion_over_the_station_rebuilds_nothing` (existing) and the new `a_zoomed_rail_rebuilds_on_scale_not_on_motion`, `uploads_follow_the_preview_not_the_pointer` | MEASURED: no rail mesh build, texture upload, histogram or trace mesh build on pointer motion; one histogram and one trace mesh per new preview |
| `python experiments/desktop-studio-2-impl/visual-check.py --exe target/debug/strehl-ui.exe --out C:\strehl-scratch\f-live\shots capture-plan capture-flight capture-plan-lightbox capture-plan-instrument capture-plan-rail-zoom capture-plan-rail-travel capture-plan-box-hover --reference <main checkout's reference folder>` (fixtures, scratch catalog and capture settings, no camera host) | VERIFIED by eye, native crops: the head row fits at 1680 × 1050 in plan and flight; the rail at fit, at 120 units (37,500-37,620: one bar a plane, edge markers for START and END, labels every 20 units) and at the whole travel (labels every 10,000); handles on all eight points, the hovered east handle filled; the panel antialiased in Graphite, Instrument and Lightbox; jog buttons read "-128 -16 -1" |

Tests added (each fails if its rule is removed, ARGUED from their
assertions): view clamping, wheel zoom holding the pointer's position, the
easing (anchor held, monotonic, lands exactly), click resolution at the whole
travel (100 units) and zoomed in (1 unit), label and minor tick steps, the
wheel through the shell of the rail (eased in 2-20 frames, readout, Shift
pan, Fit), panning by drag (no intent), lens drag (`Focus` at the dragged
unit), lens follow (inside, margin, centred), zoomed rebuilds and bars per
plane, coarse bars keeping peaks, pooled columns stable under a pan, jog
labels in ASCII; handle hit order and cursors, resize and move clamps, the
east handle and an inside drag through the view with the sent box shown, the
cursor over handles, inside and outside, nothing sent while the camera is
busy; the focus trace (once a preview, best lens, share, rate, restart on a
new box, bounded); the histogram feathered and its clip zone; curve runs and
smoothing; channel histograms and black share; tile focus against a flat
picture, the whole-frame mean, the box against the corners, and falling with
box blurs of radius 1, 2 and 4.

## Not done or not verified

- UNVERIFIED on the rig: the wheel's feel with the owner's mouse and touchpad
  (line wheels are one notch; touchpad points count 50 to a notch), and the
  focus trace against real camera previews while stepping the lens (tests use
  synthetic pictures and blurs). The preview's lens position is the host's
  position at the poll that fetched it; a preview that lags a move would be
  credited to the new position.
- The agent snapshot (`capture.preview_levels` in `capture-client.rs`, the
  plan agent's file) does not carry the black share or the focus reading.
- Leftover smoothed scroll from a line wheel after the rail consumed it could
  reach a scroll area the pointer moves onto within a few frames (egui keeps
  it privately); no scroll area borders the rail.
- The panel is larger and covers more of the picture's lower right; it has
  no collapse.
