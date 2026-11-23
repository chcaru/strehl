# Capture in flight: the plane view replaces "Proof so far" (h-proof)

**Date:** 2026-11-22. **Branch:** `studio2/h-proof`, from `d359bbe28`. **Scope:** the
in-flight panel that showed "Proof so far" and its data path. **Labels:** MEASURED,
VERIFIED, DERIVED, ARGUED, UNVERIFIED.

## The owner's words (verbatim)

> the 'Proof so far' doesn't seem to do anything useful? tbh, as is, i have no idea what
> it's for. the image seemingly didn't change ever. noodle on something better here. i
> would probably want the last plane, at full res, and maybe some diagnostics on top of the
> image, with the history and diagnostics + info about it all. the space needs to be used
> better.

## Why the proof did not help

The proof was a blend of the camera previews decoded at 480 px (`DRAFT_SIDE`,
`draft-preview.rs`), registered and blended every four planes or five seconds and
stretched over a panel two to four times its width (VERIFIED, code). It never showed a RAW;
early in a stack the composites differ little (g-flight measured 13 updates over 55 planes),
and nothing on screen said what it was for. A focus-stacked preview is not what a person
watching a capture needs: they need to see the plane just taken, whether it is good, and
where the stack is in the subject.

## What it is now

The panel is the **plane view** (`capture-plane-view.rs`), drawn in the place the
flight canvas leaves for it (`FlightView::plane`), with its data in `capture-planes.rs`.

| Part | What |
| --- | --- |
| Head | `PLANE 52 · TRY 2 OF 3` (the picture shown), the state ("following the newest", "holding while you look · newest 54", "reading plane 53…", "camera preview: zoom in for the RAWs"), and square switches: **Sharp**, **Checks** (accent-underlined when on), **Fit**, **1:1**, and **Newest · 54** when a plane is picked. |
| Picture | The try's RAWs as the stack uses them: **four shots combined** when the group's offsets cover the four CFA parities (each site's red, both greens and blue from the members that sampled it), otherwise the **first shot** demosaiced (bilinear), as the stack folds that group; a one-shot plane demosaiced. Developed with the camera's matrix and white balance (highlight handling as the render's `Render::with_saturation`) and one display gain for the run (99.5th percentile of luma to 0.9, 1-8x, said as "display +2.0 EV"). Tiled at full resolution: 1024 px tiles with a one-texel apron from an 8-bit pyramid, the stride chosen by `photo_viewport::target_stride` (g-zoom), nearest-neighbour from 100 %, uploaded on workers through the presenter. Wheel zooms about the pointer, a drag pans, a double click goes between fit and 100 % of the sensor's pixels. The zoom is kept against the sensor's pixels, so the camera preview and the RAWs share one geometry. |
| When the RAWs are read | When their detail can be seen: zoomed in, a plane picked (feed "Show", the strip, ← →), or a fitted view wider than the camera's preview (a 4K window). **Following at fit, the camera's preview is the picture** (no RAW decoded): see "Frames" for why. A picked plane shows its preview at once, then its RAWs. |
| Sharp | Cells (48 across) where this plane is within 70 % of the sharpest any plane has been, above a floor four octaves under the run's strong detail: the band of the subject in focus now, outlined in the plane colour over a light fill. From each try's camera preview (about 1024 px): mean squared Laplacian of luma per cell. A display aid, not a quality measure and never a merge input (ARGUED; engineering rule 3 does not apply to a display). |
| Checks | The checker's findings where they have a place: **witness tiles** over its limit (z² ≥ 2.5 × median, the checker's tile ratio) in the warning colour when the group failed on them, in a quiet ink in a group that passed; the **witness pairs' shift per quadrant** after the residual correction the checker applies, drawn (0.2 photosite = 40 points) only when the group failed on misregistration or a quadrant is over the limit. Measured here with the checker's own function (below). |
| Facts | In rows as they fit, the diagnostic ones first: verdict and what the stack does ("Four shots agree. The stack uses this try.", "Shots differ in places. Something moved, or focus slipped. Retaken: try 2 follows."); "Sharp in 9 % of the frame · 99 % shared with plane 169, 96 % with 171" (no overlap with either neighbour is flagged "a gap in depth?"); "Witness tiles 1.89× median at p99 (limit 2.5), 59 over · pair shift 0.09 px (limit 0.2)"; focus and the step from the plane before; when it was taken; exposure; what the picture is, its size and display gain. Hovers give the checker's reason, offsets, gains, structure and the build's cost. |
| History | One bar a plane across the planned stack, its height the share of the frame sharp there, a red or orange tick under planes that failed (one shot) or wait for a retake, the plane shown marked in the accent. The bars rise and fall as the focus passes through the subject; empty bars at either end are planes outside it. Click or drag to pick; 5,400 planes fold to a pixel each (the most sharp, the worst mark). |
| Keys | ← → step planes, End returns to the newest (added to the hint bar). |
| Following | The newest try is shown as it arrives; zooming or panning holds the plane shown for 2.5 s ("holding while you look"); a pick stops following until **Newest** or End. While following, the last picture stays until the next is ready (no flash). |
| Stack so far | Dropped from the flight view. Glance mode still shows it, unchanged (open below). |

## The data path (`capture-planes.rs`)

- **Tries.** `TryTail` follows the run's `events.jsonl` (`capture_buffered` lists each
  group's files with `name`, `plane`, `group_id`, `member_index`; the focus and time come
  with it) and `transfer-receipts.jsonl`; a try arrives when each member has a durable
  receipt, a retake is the plane's next try, a group missing a RAW does not hold up later
  ones, and without bindings every `shots` RAWs are a plane.
- **Two tiers, off the UI thread.** The deck's worker measures every try's preview (17-50 ms
  and 4 ms for the map, MEASURED) and builds the picture asked for: one build at a time, only
  while the view is painted (1.5 s), after 220 ms without a newer request, a newer request
  stopping it before its group check. A tile worker cuts and uploads the tiles in view, the
  newest request first. Built pictures arrive with their overview and the tiles in view
  already uploaded, so a new plane replaces the old in one frame.
- **Cost controls.** Six pool threads at below-normal priority. Big buffers are reused, not
  allocated per plane: the four members' samples (decoded with the decoder's serial path,
  each member on its own thread, into its reused file buffer), the pyramid's levels (taken
  back when a picture is retired), one texel buffer for uploads. Pictures and textures the UI
  lets go of are freed on the worker. Leaving the flight view drops the deck.
- **The checker's measurement.** `strehl_cli::pixel_shift_cmd::measure_with_tiles` (new,
  three lines: `measure_impl(frames, noise, false)`) is the group check the checker runs,
  with the witness's tile map. Its verdicts are compared with the checker's journal below.

## Feed and shared files (exact edits)

- `capture-flight.rs`: `canvas` no longer draws the proof or the "latest plane" picture; it
  records the plane view's rectangle in `FlightView::plane` (new field) and starts the feed
  list at the same top. `FlightInputs` lost `proof`, `proof_note` and `latest`; the
  functions `picture` and `label` (used only by those) are removed. **Not touched:**
  `feed_ui`, `feed_row_ui`, `feed_row`, `FlightIntent::ShowPlane` and every other feed
  function.
- `capture-station.rs`: `apply_flight`'s `ShowPlane` arm now picks that try in the plane
  view (the selection hook); `Done` returns it to following. The "pinned RAW" canvas
  (`PinnedPlane`, `pinned_canvas`, `show_plane_raw`, `plane_raw`, `take_show_plane`) is
  removed: the plane view is where Show goes. The deck is made beside the proof job in
  `poll_station`; `load_fixture_planes`, `set_presenter`, `plane_view_settled` added;
  flight hints gain ← → and End.
- `app-station-capture.rs`: `capture_show_plane` removed; `capture_tick` hands the
  presenter to the capture workspace. `app.rs`: one line, offscreen screenshots wait for
  `plane_view_settled()` on the Capture station.
- `capture-live.rs`: `preview_handle` removed (only the old latest-plane picture used it).
- `hdr-display.rs`: `upload_sdr_slice` (borrowed texels); `upload_sdr_sampled` calls it.
- `draft-preview.rs`: `LineTail` and `lower_thread_priority` made `pub(crate)`.
- `strehl-cli/src/pixel-shift-cmd.rs`: `measure_with_tiles` added (no behaviour change).
- `strehl-ui/Cargo.toml` and `Cargo.lock`: `rayon` (workspace version) for the build pool.

## Verification

| Check | Result | Label |
| --- | --- | --- |
| Group findings against the checker's journal of `stack-1795300522964-6430` (read only; journal copied to scratch): planes 1, 3, 24, 27, 30, 41, 51, 123, 126, 130, every try, 15 groups (passes, misregistration, shift pattern, witness tiles) | verdict, reason text (numbers included) and offsets identical for 15 of 15 | VERIFIED (`plane_build_cost` with `STREHL_PLANE_JOURNAL`) |
| Four-shot assembly | a synthetic coloured scene shifted per member is returned exactly at every interior site; wrong offsets mix colours (control) | VERIFIED (test) |
| Pyramid | halves in linear light (black beside white gives sRGB 188, not 128) | VERIFIED (test) |
| Tiles | cores tile the picture without gaps or overlaps; aprons equal the neighbour's edge texels | VERIFIED (test) |
| Sharp | a try is sharp only where it shows the most detail; flat cells never; a tenth of the detail is not sharp | VERIFIED (test, synthetic previews) |
| Following, Show, ← →, End, Newest | through the panel with a fixture deck | VERIFIED (test) |

## Measurements

Host: the 32-thread desktop, RTX 5090 (DX12), 64 GB, no other builds running (MEASURED,
`tasklist`), CPU load 0.6-2.8 % before each run. Release builds. Owner's RAWs read in place
from `D:\StrehlCaptures` (read only). Frame times through the production GPU path:
`capture_plane_view_frames` (offscreen egui-wgpu target and the offscreen presenter, the
whole app's `update_workspace` each frame, 60 Hz pacing); "UI ms" is the UI thread's frame
(egui, tessellation, buffers, submit).

**Build cost** (MEASURED, `plane_build_cost`, 61 MP four-shot groups, six threads below
normal): decode 95-185 ms (four members), group check 155-205 ms, development 217-350 ms,
pyramid 33-70 ms: 0.5-0.7 s a plane; a 240 MB pyramid. Preview and focus map 19-55 ms a try.

**Frames** (MEASURED, 1680 x 1050 unless said; "planes arriving" is a replay of the owner's
run at one plane every 1.5 s, four times the rig's pace):

| Run | Frames over 16 ms | UI ms median / p99 / max | Builds | Process CPU |
| --- | --- | --- | --- | --- |
| No plane view (baseline: the same app and fixture without the deck) | 0 of 2,122 | 0.56 / 1.0 / 1.5 | 0 | 0.04 cores |
| Following arrivals at fit (previews only) | 0 of 1,178; 0 of 1,179 (final build) | 0.66-0.67 / 1.25-1.28 / 6.2-7.2 | 0 | 0.14-0.16 cores |
| Following arrivals at 100 % (a RAW build per plane) | 5 of 1,178; 6 of 1,177 (final build) | 0.84-0.86 / 6.7-13.1 / 21.2-22.4 | 14 | 2.0 cores |
| Same, panning | 2 of 1,177; 3 of 1,177 (final build) | 0.82-0.83 / 2.26 / 19.9-22.1 | 13 | 1.9 cores |
| Picking a plane a second, fit / 100 % / panning | 0 / 1 / 1 of about 705 each | 0.82-0.84 / 1.8-1.9 / 2.4, 22.9, 26.8 | 11-12 each | 2.7-3.0 cores |
| `flight+long` (5,400 planes, 5,681 tries), synthetic 6000 x 4000, 1280 x 800, a plane a second, fit / 100 % / panning | 0 of 590 each | 0.68-0.75 / 1.4-2.6 / 5.97-6.47 | 10 each | 0.63-0.68 cores |

The plane view's own work on the UI thread (its poll and its painting) measured 0.02-0.06
ms a frame, including the frames that were slow (MEASURED, per-frame timers).

**The stall I could not remove.** While full-resolution RAW builds run, the UI thread
occasionally spends 14-28 ms in egui's tessellator (rarely in egui's pass or the submit)
on a frame whose shapes tessellate in microseconds when repeated alone (MEASURED: each of
the frame's ~660 shapes re-tessellated singly took at most 0.014 ms). The thread is charged
60-116 million cycles for those milliseconds with no page faults, the egui context lock is
free just before (probe 0.00 ms), and no traced step of the workers (decode, group check,
development, pyramid, uploads, retire) overlaps most of these frames. It does not happen
with previews only, nor with synthetic full-size pictures built and uploaded the same way
(0 frames over 16 ms with 9504 x 6336 synthetic builds), nor without the deck. Ruled out by
experiment (each MEASURED, 8-12 s runs): worker priority (normal or below normal: same),
texture destruction (kept alive: same), GPU uploads (none: fewer and shorter, 14-17 ms),
buffered or unbuffered RAW reads (same), allocation churn (a separate experiment,
`large_buffers_stall_small_allocations`, showed a worker allocating and freeing 4 x 122 MB
stalls another thread's small allocations up to 28 ms against 2.2 ms alone, and 6.8 ms when
the buffers are reused; reusing every big buffer here took the stalls from 25-50 ms to
14-28 ms but did not end them). UNVERIFIED cause; the cycles charged to the UI thread point
at interrupt or inter-processor work landing on its core (DERIVED, not measured). What was
done instead: **following at fit reads no RAW**, so the default state while a long stack
runs has no stall (0 of 1,178 frames over 16 ms). Zoomed in, or with a plane picked, about
one or two frames in four builds are over 16 ms in this harness.

**Memory** (MEASURED, peak of the benchmark process, sampled every 100 ms): 0.98 GB for
the 5,400-plane fixture; 2.2-2.4 GB with real 61 MP builds (2.20 GB in the final run), of which the reused buffers are
about 490 MB of member samples, up to 520 MB of spare pyramid and 116 MB of the decoder's
per-thread file buffers, and the picture shown 240 MB (DERIVED from their sizes). Bounded:
one build at a time, one picture shown, the spare buffers capped; all freed when the flight
view is left. GPU: the tiles in view plus 48 more (192 MB) at most (DERIVED).

**Contention with the capture** (DERIVED from the rows above): following at fit, 0.14
cores at four times the rig's pace (each try's preview and map); at 100 %, about 3.3
core-seconds a plane, about 0.6 cores at the rig's 5.7 s a plane, at below-normal priority.
The checker (`strehl follow`) is a separate process; it and the plane view both decode each
group when the view is zoomed in (the checker's own measurement is not shared).

## Tests and checks

| Command | Result |
| --- | --- |
| `cargo test --locked -p strehl-ui --no-fail-fast` | MEASURED: Compiling strehl-ui; 1,511 passed, 0 failed, 46 ignored |
| `cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings` | MEASURED: Checking strehl-ui; exit 0 |
| `cargo fmt -p strehl-ui -- --check` | MEASURED: exit 0 |
| `cargo clippy --locked -p strehl-cli --all-targets --no-deps -- -D warnings` | MEASURED: exit 101, every finding in files this lane did not touch (`image_out.rs`, `merge_cmd*`, `focus-step-cmd.rs`, experiments' sources; newer lints); none in `pixel-shift-cmd.rs` |
| `rustfmt --edition 2024 --check crates/strehl-cli/src/pixel-shift-cmd.rs` | MEASURED: exit 0 (`cargo fmt -p strehl-cli` would reformat eight untouched files; not done) |

New tests: `capture-planes-tests.rs` (`the_tail_binds_tries_and_waits_for_their_raws`,
`without_bindings_every_shots_raws_are_a_plane`,
`sharp_is_where_a_try_shows_the_most_detail`,
`the_four_shot_assembly_takes_each_colour_from_its_member`,
`the_pyramid_halves_in_linear_light`, `tiles_cover_the_picture_and_their_aprons_match`,
`the_deck_builds_what_the_view_asks` (a newer request supersedes an older one; a pattern
failure is its first shot), `tiles_are_uploaded_off_the_ui_thread`,
`the_display_gain_is_bounded`; ignored: `plane_build_cost`,
`large_buffers_stall_small_allocations`), `capture-plane-view-tests.rs`
(`the_picture_is_placed_fitted_or_zoomed_and_clamped`,
`the_tiles_in_view_cover_the_aperture`, `neighbours_overlap_and_bars_carry_shares_and_marks`,
`the_verdict_says_what_the_stack_does`, `the_panel_follows_the_newest_and_show_picks_a_try`),
`capture-flight-tests.rs` `the_plane_view_has_the_space_beside_the_feed` (replaces the
proof's fit test), `capture-station-tests.rs` (Show picks, Done returns), and the ignored
GPU benchmark `capture_plane_view_frames` (`app-station-capture-tests.rs`). The benchmark's
switches (`STREHL_BENCH_*`) and the workers' step trace exist only in test builds.

## Fixtures and offscreen checks

`--capture-fixture flight` and its variants get a synthetic subject tilted in depth (a
plane is sharp in a band that moves down it), with witness tiles and pair shifts made to
match each fixture verdict; `flight+show` shows plane 52's first try. For offscreen checks
of a real run (never committed): `STREHL_FIXTURE_RUN=<capture folder>` and
`STREHL_FIXTURE_JOURNAL=<copy of its checker journal>`, with `STREHL_FIXTURE_SHOW=<plane>`,
`STREHL_FIXTURE_ZOOM=<screen px a photosite>,<u>,<v>`, `STREHL_FIXTURE_REPLAY_MS` (tries
arrive at that pace) and `STREHL_FIXTURE_SIZE=WxH` (synthetic size).

Screenshots looked at (scratch, not in Git), release build, scratch catalog copies:
`C:\strehl-scratch\h-proof\final\fx1680\` (`capture-flight`, `-lightbox`, `-show`, `-long`,
`-done`), `fx1280\` (`capture-flight`, `-lightbox`, `-show`), and of the owner's run
`real\` (following at fit; plane 130 picked, Graphite and Lightbox, 1680 x 1050 and
1280 x 800; plane 170 at 100 %). VERIFIED by eye: square and ruled; the picture fills the
space beside the feed; facts fit in three rows at 1280 x 800; the Sharp band follows the
subject's stripes on the owner's beetle; witness tiles cluster on the moving parts of a
motion failure; 100 % shows the four-shot pixels.

## Open, or for the owner

- **The stall above** (UNVERIFIED cause). Zoomed in while following, one or two frames in
  four builds are 14-28 ms. A separate process for the RAW builds (as the checker is) would
  take the work out of the UI's process; not built.
- **Fit on a 4K window** reads the RAWs (the fitted picture is wider than the 2048 px camera
  preview), so it meets the stall above. Not tried on the owner's display.
- **Glance** still shows the stack-so-far composite. Whether it should show the newest
  plane instead is the owner's call; the proof job still runs for it.
- **The checker and the view both decode a group** when the view builds it. Sharing the
  checker's decoded group (or its tile map in its journal) would halve that; it touches the
  engine and the journal's size.
- **Display gain** is set by the first RAW picture built in a run (a plane before the
  subject can make it brighter than later planes need).
- **The Sharp map** comes from the camera previews (about 1024 px): fine detail beyond the
  preview's resolution does not count. A plane early in a stack is "sharp" relative to the
  planes so far.
- **Observed, not this lane's:** at 1280 x 800 with the owner's numbers the headline's
  "412 RAWs taken · 196 for retakes" and "49 retakes of 34 planes" overlap.
- Not tried on the rig or the owner's window (offscreen and test harnesses only).
