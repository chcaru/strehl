# P6 Capture station: model and host (Studio 2)

**Phase:** P6 of the [Studio 2 implementation plan](../../docs/proposals/2026-11-desktop-studio-2-implementation.md)
(sections 7.4 and 8, P0 items 2, 4 (part), 7, 9, 10, 13). Milestone row
`desktop-studio-2-p6-2026-11-21`.
**Date:** 2026-11-21. **Branch:** `studio2/p6-capture`, from `61effa01b`.
**Scope:** the model and host part. The new Capture screens (plan, rail, step
table, in flight, glance) are not built here; the existing Capture tab gained
only what its fixes needed (a test-shot row, the preview's clip estimate,
confirmations, the first blocker beside Start, the stopped list, cancels).
**Labels:** MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED as in the plan.

## What was built

| Item | Where | What |
| --- | --- | --- |
| 1 Typed host state | `crates/strehl-ui/src/capture-host.rs` | `HostState` (`#[serde(default)]`) over every field the desktop reads, parsed on the client thread in `Snapshot::set_state`; the raw `Value` stays in `Snapshot::state` for the agent snapshot. Control fields are strict (a malformed one gives a disconnected default plus `host_error`, which refuses every request and is shown in red); display-only fields are lenient. Every `s.state[...]` read in `capture-workspace.rs` and `capture-tools.rs` now reads `s.host`; `capture-schedule.rs` still reads the raw value (its recipe is untyped). |
| 2 Pre-flight | `capture-preflight.rs` | `start_blockers(s, ui) -> Vec<Blocker>` (`check`, `chip`, `sentence`, `fix`); Start is enabled exactly when it is empty and the first sentence is shown beside Start. Adds the H1 exposure problem, a running calibration or test shot. `can_schedule` keeps scheduling available while the schedule editor is open. |
| 3 H1 | `crates/strehl-capture/src/worker.rs`, `session.rs` | `exposure_problem(status)` is the one rule behind `validate_exposure` and `state.exposure.problem`; `exposure.mode` is `M`/`P`/`A`/`S`/`other`. |
| 3 H2 | same | `Command::CapturePositions { kind: PositionsKind }`, `serde(default, skip_serializing_if = "PositionsKind::is_positions")`; `kind: "test"` needs exactly one position, journals `capture_kind` `test`, and is not held by error correction. `state.capabilities = {test_shot, exposure_check}`. |
| 3 H3 | not built | `plan.positions` would be up to 65,536 numbers (about 390 KB of JSON, DERIVED) in every 5 Hz poll, and the desktop already uses the host's own `Plan::positions()` from the shared crate, so there is no duplicated logic to remove. |
| 4 Test runs | `capture-test-shot.rs`, `capture-client.rs` | `CaptureWorkspace::test_shot()` sends one position at the current focus, `keep_power_on: true`, `kind: "test"` only when `capabilities.test_shot`; the run is remembered (`Connection::mark_test_run`) so it stays out of the lists on an older host too; `verify_completed` refuses `capture_kind` `test`; such runs are never followed. `read_levels` decodes the RAW with `strehl_raw::decode` on a worker and reports the clipped share (at or above `levels.white`), the 1st percentile, median and 99.9th percentile above black as shares of black to white. |
| 5 Stopped captures | `capture-client.rs` | `verify_stopped` (outcome `stopped` or `uncertain`, not a test, at least one plane and one RAW with a durable receipt at its recorded length; unverified RAWs counted). `Snapshot::stopped`, `StoppedCapture::label()` "stopped · N planes", handoff accepts them, the tab lists them. |
| 6 Per-plane records | `capture-follow.rs` | `JournalReader` reads the checker's journal incrementally (64 KiB a poll, torn lines kept), keeps the counts line by line and each plane's last line in `Progress::planes` (at most `MAX_PLANE_RECORDS` 8,192). `Follower::progress()` replaces the field. |
| 7 Jobs and waits | `capture-tools.rs` | `EngineJob` holds its `OwnedChild`; `cancel()` kills at once and the job's thread reaps; `elapsed()`; dropping a job ends its engine. `Slot::cancel/elapsed/public`. Calibration stages carry deadlines (`SWITCH_TIMEOUT` 45 s, `SURVEY_TIMEOUT` 360 s plus warmup, `MEASURE_TIMEOUT` 300 s), `gives_up_in`, `stop`, `expire`; Stop waiting at every stage; a stopped measurement ends the engine before the survey folder is deleted. `ConnectWait` (`CONNECT_TIMEOUT` 60 s) with Stop waiting; nothing is sent while waiting or giving up. |
| 8 Preview levels | `capture-aids.rs`, `capture-client.rs` | `PreviewLevels::analyze` (256-bin Rec. 709 luma, share of pixels with a channel at or above 254) beside `Peaking::analyze` on the client thread; `CAUTION` "estimate from the camera preview, not the RAW". |
| 9 Incremental proof | `draft-preview.rs` | `ProofJob` (thread at `THREAD_PRIORITY_BELOW_NORMAL` on Windows): `add_frame(path)`, `finish()`, `poll()`; `Incremental` caches each frame's decode and pyramid at `DRAFT_SIDE`, keeps measured pairs by source index, re-solves and blends every `PROOF_EVERY_PLANES` 4 planes or `PROOF_EVERY` 5 s; above 512 frames (or the 256 MiB budget) it keeps every second plane, plane 0 always. The batch API is unchanged (`build` now shares `prepare`, `register_cached` and `compose`); the header caution is kept. |
| 10 Cadence | `capture-client.rs`, `capture-workspace.rs` | `Cadence::{Background (1 Hz, no preview), Sequence (5 Hz), Live (5 Hz with preview)}`, an atomic beside the client's `Work` channel, a `Work::Cadence` wake. The workspace sets it every poll from `set_station_open` (or, until the shell calls it, from `show()` having run). |
| 11 P0 fixes | `capture-workspace.rs` | clippy `unnecessary_cast` fixed (the storage line); `unread_notice()`; Stop, Disconnect and Shut down camera ask for a second click; FAULT and the failure message are drawn in `FAULT_RED` (`#e5604c`, a marked local stand-in for the shell's red token). |

`docs/native-capture.md` gained the protocol additions and the stopped list.

## Calls for the UI and the shell

```rust
// CaptureWorkspace (capture-workspace.rs)
pub fn poll_background(&mut self, ctx: &egui::Context, engine: Option<&Path>); // connect when configured, then poll_follow
pub fn set_station_open(&mut self, open: bool);
pub fn cadence(&self) -> Option<Cadence>;
pub fn unread_notice(&mut self) -> Option<String>;
pub fn status_line(&self) -> Option<String>;
pub fn start_blockers(&self) -> Vec<preflight::Blocker>;
pub fn follow_progress(&self) -> Option<&follow::Progress>;    // .planes, .plane(n), .latest(n)
pub fn test_shot(&mut self) -> anyhow::Result<()>;
pub fn stop_test_shot(&mut self);
pub fn stop_waiting_for_camera(&mut self);
pub fn stop_calibration(&mut self);
pub fn cancel_focus_step(&mut self);
pub fn cancel_compact_estimate(&mut self);
pub fn import_stopped(&mut self, index: usize) -> anyhow::Result<()>;
pub confirm: Option<Confirm>;                                   // Stop | Disconnect | ShutDown
// preflight (capture-preflight.rs)
pub(crate) fn start_blockers(s: &Snapshot, ui: &CaptureWorkspace) -> Vec<Blocker>;
pub(crate) fn can_schedule(blockers: &[Blocker]) -> bool;
pub(crate) fn capacity_error(s: &Snapshot) -> Option<String>;
// Snapshot (capture-client.rs): host, host_error, stopped, levels, notice_id
// draft-preview.rs
ProofJob::start() -> ProofJob; add_frame(&self, PathBuf) -> bool; finish(&self); poll(&self) -> Option<ProofEvent>
ProofEvent::{Updated(Box<ProofUpdate>), Failed(String)}; ProofUpdate { draft, received, used, stride, revision }
```

The proof is not fed yet: the in-flight screen should start a `ProofJob` per
followed run and offer one RAW per plane (the first member: the follow
journal's `names[0]` in `Progress::planes`, or `receiver.latest.path` when the
checker is off), and show `PROOF_CAUTION` with it.

Agent snapshot keys are unchanged; additions only: `capture.stopped`,
`capture.host_state_error`, `capture.preview_levels`,
`capture.tools.{test_shot, connect_wait, connect_note}`,
`capture.tools.calibration.gives_up_seconds`, `elapsed_seconds` in each tool slot,
`capture.follow.checker.planes_kept`.

## Commands and results

Worktree `C:\w\p6`, debug profile, `CARGO_BUILD_JOBS=8`, Windows 11, other
agents building in their own worktrees at the same time (host loaded; no
timing below depends on it except the benchmark, which states its profile).

| Command | Result |
| --- | --- |
| `cargo test --locked -p strehl-capture` | MEASURED: Compiling strehl-capture; 63 passed, 0 failed |
| `cargo clippy --locked -p strehl-capture --all-targets --no-deps -- -D warnings` | MEASURED: Checking strehl-capture; exit 0 |
| `cargo fmt -p strehl-capture -- --check` | MEASURED: no difference in files changed here; `receiver.rs` differs at `61effa01b` already and was not touched |
| `cargo test --locked -p strehl-ui` | MEASURED: Compiling strehl-ui; 1097 passed, 0 failed, 18 ignored |
| `cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings` | MEASURED: Checking strehl-ui; exit 0 (the pre-existing `unnecessary_cast` is gone) |
| `cargo fmt -p strehl-ui -- --check` | MEASURED: no difference |
| Placebo: remove `!test &&` from the error-correction switch, run `a_test_shot_is_not_held_for_a_check` | MEASURED: the test fails (the burst is asked for its verdict); rule restored |
| `STREHL_CAPTURE_RUNS='D:\StrehlCaptures' cargo test -p strehl-ui real_runs_are_listed -- --ignored --nocapture` (read only) | MEASURED: 54 runs with `result.json`: 46 complete, 0 listed as stopped. The one stopped run and five complete ones have receipts without `logical_name` (an older receipt format, which `verify_completed` refuses too); the two uncertain runs have 0 planes |
| `cargo test --release --locked -p strehl-ui proof_update_cost -- --ignored --nocapture` | MEASURED (release, synthetic 480 x 320 previews, host loaded by other agents' builds, one thread): 511 planes offered, 106 updates in 69.9 s including frame preparation; worst update 1.24 s (at about 320 planes), last 0.84 s over 256 of 511 planes (stride 2); every plane kept up to 322, an even half from then on; peak resident 255 MiB; 2,096 pairs kept. An earlier run let off-stride planes in through `add_image` after thinning; fixed and tested before this run |

Tests added (each fails if its rule is removed, ARGUED from their assertions
except where a placebo is listed above):

- Host: `capture_positions_kind_is_omitted_unless_a_test_shot` (old JSON parses
  as a burst, a burst serialises without `kind`, an unknown kind is refused),
  `state_reports_capabilities_and_the_exposure_problem_before_start`,
  `a_test_shot_is_one_position_marked_test_in_its_manifest`,
  `a_test_shot_is_not_held_for_a_check`,
  `exposure_problem_names_the_first_rule_the_check_enforces`; the existing
  `keep_power_on` compatibility test still passes.
- Typed state: the simulator's real `Session::state()` read typed through a
  whole capture, with its top-level keys equal to `KNOWN_KEYS`; an older host's
  state without the new fields; strict control fields, lenient display fields,
  an unknown phase.
- Pre-flight: no blockers when ready; each host condition alone; H1; offline
  and unreadable host first; capacity, receiver, simulator, sending; edits,
  focus, calibration, test shot, schedule editor (`can_schedule`); order.
- Screen: Stop, Disconnect and Shut down need a second click and only the
  second sends; FAULT and its message are `FAULT_RED`; the first blocker beside
  Start; a notice is unread once; the cadence follows station and sequence; a
  test shot names its kind only to a host that accepts it.
- Tools: a cancelled engine job ends its process and is reaped; a failed job
  reports its last error line; calibration stages give up and stop; a stopped
  measurement ends its engine before failing; the connect wait ends connected,
  failed or timed out.
- Follow: incremental reading equals a whole read, torn lines wait, bounded
  plane records keep the newest; relayed verdicts unchanged.
- Proof: the incremental composite equals a fresh registration of the same
  frames (identical bytes); even subsampling above 512 frames, skipped planes
  unread; due after two planes, then four or five seconds; the worker end to
  end on synthetic TIFF-wrapped camera JPEGs.
- Levels: preview histogram and clip share; RAW levels against black and
  white; the first durable RAW of a run; the test shot's stages.

## Needs a rig test (the Pi deploy is done)

1. Done 2026-11-21: deployed the host (H1, H2) to the Pi and restarted the
   controller; manage power switched back on (see the README's "Pi deploy").
2. With manage power on, on a structured subject: check `exposure.mode` and
   `exposure.problem` with the dial in A and M, fixed and auto ISO, Bulb; take a
   test shot (single and four-shot): its manifest says `test`, it is not followed,
   not listed, not opened; its RAW levels against a known over-exposure.
3. Connect and Power on & connect: the wait, its 60 s limit and Stop waiting.
4. A calibration with Stop waiting at each stage, and its time limits.
5. A stack stopped part way: listed as "stopped · N planes" and opened.
6. An older desktop against the new host (keep using bursts and retakes), and
   this desktop against the old host (no `kind` sent, test shot remembered).
7. End with the camera and light off.

## Open issues

- A test shot's run (one RAW group, about 125 MB single shot, 500 MB four-shot)
  stays on disk, unlisted; a survey the user stopped waiting for is hidden but
  not deleted. Deleting them would need the owner's decision.
- (Resolved in the Capture UI stage below: the follow journal is now read on
  its own thread.)
- The proof's 256 MiB resident budget held 322 synthetic 480 x 320 previews
  (MEASURED, about 0.8 MB a frame), so thinning starts there rather than at 512.
- The proof's cost beside the checker during a real capture is unmeasured
  (plan section 12); the benchmark above is synthetic.
- `capture-schedule.rs` still reads the raw state; old-format receipts (no
  `logical_name`) are neither completed nor stopped, as before.
- Not done here (shell or later phases): wiring `poll_background`,
  `set_station_open`, `status_line` and `unread_notice` into `app.rs`; the red
  theme token; the agent commands for the test shot, stopped imports and cancels;
  the milestone ledger row.

## Capture UI, stage 1 (2026-11-21)

The Capture station's screens, built as self-contained modules that take
their inputs as parameters and return intents, to be composed into the P1
shell in stage 2. Look: the locked mockups (`capture-plan.html`,
`flight.html`, `glance.html`, `base.css`, `screens.css`): square corners,
hairlines, tracked capitals, drawn status marks, through a
`CapturePalette` (graphite by default; P1's tokens map onto it in one place).

| Module | What | API |
| --- | --- | --- |
| `capture-style.rs` | Palette, drawn marks (lamp, triangle, diamond, ring, half), tracked capitals, square buttons, toggles, links, chips, bars, fields; Sony ISO and shutter codes (`iso_label`, `shutter_label`) | `CapturePalette`, `Mark`, `button`, `toggle`, `option`, `field`, ... |
| `capture-preflight.rs` (view) | The chip strip: Rig, Light, Exposure, Bounds, Step, Disk, Receiver (Schedule while open), each met or unmet from `start_blockers`; "Ready" and the plan's summary, or the first blocker | `strip_chips(s, blockers) -> Vec<StripChip>`, `strip_ui(ui, chips, blockers, summary, palette) -> Option<Fix>` |
| `capture-plan.rs` | The inspector: subject and stack name; four numbered steps with ready numerals; ISO and shutter pickers; test shot with its RAW levels; Start/End and Mark here; Calibrate step with its stage and "gives up in"; the step table (overlap = sharp width / step, planes as `Plan::positions()` counts them, minutes by `timing::initial_plane` + `initial_setup` + warmup, gigabytes by `StoredRaws::expected` or `capacity::required`; rows below focus-step's EDGE 3.6 marked); the staircase; 4-shot and settle; the four after-switches; footer "Ends about", disk line, Start stack (disabled with the first blocker) and Schedule | `PlanView::show(ui, &PlanInputs, palette) -> Vec<PlanIntent>`; pure `step_rows`, `plane_count`, `stack_seconds`, `rig_summary`, `test_shot_sentence`, `calibration_sentence`, `footer_lines`, `strip_summary` |
| `capture-rail.rs` | The focus rail: survey profile bars (median of the 24 tiles, interpolated to one bar per plan step), planned or flight ticks pooled to 2 px, accent Start/End handles (drag to move a bound), the lens, hover, jog buttons, survey links; keys Left/Right 1, Shift 16, S/E | `FocusRail::show(ui, &RailInputs, palette) -> Vec<RailIntent>`; one cached `Arc<Mesh>` keyed on survey, plan, ticks revision, rect and scale |
| `capture-flight.rs` | Headline (plane, bar, left, ends, pace, RAWs taken); the proof; the latest plane; the last five planes from the journal with verdict marks; health (transfer, checks, disk, rig); when-it-finishes switches; Pause/Resume, Stop… (confirm), Glance; G and Space | `canvas(ui, &FlightInputs, palette)`, `inspector(...) -> Vec<FlightIntent>`; pure `headline`, `health`, `recent_planes`, `flight_ticks`, `needs_you` |
| `capture-glance.rs` | Full-screen status: colour bar (green fine, amber needs you, red stopped, blue done), dial with one tick per plane (pooled to 180), time left and ends, four health lines, next-step sentence, Esc | `show(ui, &GlanceInputs, palette) -> bool` (back); pure `glance_state`, `next_sentence`, `glance_lines` |
| `capture-live.rs` | Live view: Fit/100 %, peaking with threshold, clipping overlay (from the preview's clip mask, computed on the client thread), thirds grid, subject box with corner marks (drag to redraw), magnifier (cycles the host's ratios), estimate panel with the histogram "estimate, not the RAW" and the exposure | `LiveView::show(ui, s, palette) -> Vec<LiveIntent>`; textures uploaded only on a new preview generation |
| `capture-station.rs` | The composition and the intents applied through the workspace's checks: settings, exposure, marks, test shot, calibration, switches, Start (re-checked against `start_blockers`), Stop (confirmed), a dragged bound (focus there, then mark once the lens arrived; 20 s limit), survey links, ROI, magnifier; the proof (`ProofJob::for_run` tails the run's receipts, one RAW a plane); recovery, connection and schedule windows | `station_strip`, `station_canvas`, `station_rail`, `station_inspector`, `station_glance`, `glance_open`, `open_glance`, `station_mode`, `station_hints`, `take_open_rig`, `take_show_plane` |

Also: the follow journal is now read on its own thread (`capture-follow.rs`,
spec 5.2): the UI takes the published `Arc<Progress>` and polls only the
checker's exit; `ProofJob::for_run(run, shots)` follows a capture's receipts
on the proof's below-normal thread.

Until the shell composes them, `STREHL_CAPTURE_STATION=1` (or `glance`) lays
the station out inside today's Capture tab (control strip 36 px, canvas, rail
135 px or 127 px in flight, inspector 348 px).

### Commands and results (stage 1)

| Command | Result |
| --- | --- |
| `cargo test --locked -p strehl-ui` | MEASURED: Compiling strehl-ui; 1127 passed, 0 failed, 18 ignored |
| `cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings` | MEASURED: Checking strehl-ui; exit 0 |
| `cargo fmt -p strehl-ui -- --check` | MEASURED: no difference |
| Offscreen renders (`strehl-ui --capture --capture-settings <scratch> --catalog <scratch> --size 1680x1050 --offscreen-screenshot`, `STREHL_CAPTURE_STATION=1` / `glance`) against `strehl-capture-headless --demo` on 127.0.0.1 (the host's simulator: no camera, light or Pi) | VERIFIED by eye against `capture-plan.png`, `capture-flight.png` and `glance.png`: the plan inspector, strip, rail, live view, flight headline, health column and glance lay out as the mockups. Renders not kept (scratch, deleted). The chrome around them is today's app, not P1's |

Tests added: intents from clicks (plan: Start, Test shot, marks, a table row,
a switch, Calibrate; flight: Stop… asks, Stop now, Keep going, Pause, Glance;
G opens glance), blocked Start sends nothing, the first blocker beside Start,
rail keys (and none in flight, without the keyboard or when not editable),
zero rail rebuilds on pointer motion and on lens moves in plan mode, one
rebuild per changed plan or plane state, ticks pooled to 2 px at 6,000 planes,
dragging a handle (MoveBound) and a click (Focus), live-view uploads only on a
new preview, drawing a subject box, the photo rectangle (1160 x 773 in the
mockup's canvas), glance states and Escape, the dial bounded at 180 ticks, the
station applying each intent as the host's command, a dragged bound reached
then marked, the step table against the host's rules (`plane_count` equals
`Plan::positions().len()`), the follow journal read on its thread, the proof's
run tail (one RAW a plane, the end reported once).

### Open issues (stage 1)

- Composition into the P1 shell (stage 2): frames, top bar, hint bar
  (`station_hints`), rig popover (`take_open_rig`), "Show" of a retaken plane
  (`take_show_plane`), the activity tray, and the theme tokens.
- Fonts: the mockups use Bahnschrift; the screens use the app's face (D11 and
  P1 decide). Letter spacing follows the mockup.
- The subject and stack name are held by the plan view only; naming the
  captured stack and the catalog's subjects belong to P4.
- "Tell my phone" and a 2 min power-down grace are in the mockup but have no
  host support; not shown.
- The proof is fed from the receiver's receipts while a capture is written
  with the receiver on this PC; a card-only capture has no proof.
- Flight in the simulator shows no proof or checks (no receiver, no RAWs); the
  proof, the checks and the health lines need the rig test of the main list.

## Capture station in the shell, stage 2 (2026-11-21)

The Capture station is the only Capture screen: the `STREHL_CAPTURE_STATION`
gate and the old one-page screen (sequence, focus, preview, scrub, power,
test shot, follow and calibration panels) are removed. The composition is one
file, `crates/strehl-ui/src/app-station-capture.rs`; the shell's Capture arms
call it.

- Layout (spec 7.4): no tools column; the inspector is the plan, or the
  flight inspector while a capture runs, with no tabs; the control strip is
  the pre-flight strip (absent in flight); the rail is the depth rail (135 px
  planning, 127 px in flight); the canvas is the live view or the flight
  canvas; glance covers the window above the shell. Colours come from
  `studio_theme::tokens` (`CapturePalette::from_tokens`), so the station
  follows all three themes.
- Hint bar from `station_hints`; the rig popover opens from the plan's rig
  step (`take_open_rig`); Shut down and Disconnect from the popover ask in a
  modal first (P0 item 7); the top bar's capture activity reads the time left
  (`activity_phase`), and the capture client's success notice goes to the
  shell's notices once.
- "Show" on a retaken plane: the plane in the Stack station when that run is
  open, else the plane's RAW in the live canvas (Esc or "Back to the
  capture"). The flight's last-planes list keeps the newest retaken plane in
  its last row so Show stays in reach.
- Naming: the plan's subject field suggests the catalog's subjects (read once
  per catalog revision). A finished capture lands in the named subject (found
  by name, else created in the selected project, else in a "Captures"
  project) under the plan's stack name, or P4's `default_stack_name`.
- Every frame (shell tick): `set_station_open`, then `poll_background` in the
  window (`poll_follow` offscreen and in tests); the background cadence and
  the follower apply when the station is closed.
- Connection, storage and past captures (with import, compact and focus-step
  measurement) moved to a "Captures, storage and connection" window opened
  from the plan's last line.
- `--capture-fixture plan|flight|glance` draws the station from fabricated
  states (`capture-fixture.rs`: a synthetic subject, no owner pictures); the
  fixture connection sends and receives nothing.

### Commands and results (stage 2)

| Command | Result |
| --- | --- |
| `cargo test --locked -p strehl-ui` | MEASURED: Compiling strehl-ui; 1262 passed, 0 failed, 22 ignored |
| `cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings` | MEASURED: Checking strehl-ui; exit 0 |
| `cargo fmt -p strehl-ui -- --check` | MEASURED: exit 0 |
| `visual-check.py --exe target/release/strehl-ui.exe --reference <main checkout's reference folder> capture capture-plan capture-flight glance capture-flight-lightbox capture-plan-instrument capture-plan-lightbox` (isolated `--capture-settings`, fixtures) | VERIFIED by eye against `capture-plan.png`, `capture-flight.png`, `glance.png` and `capture-flight-lightbox.png`: slots, inspector, strip, rail, flight headline, health column, last planes with the retaken plane and Show, glance. Lightbox draws the canvas with the canvas inks |
| `strehl-ui --route capture --capture-settings <scratch>` against `strehl-capture-headless --demo` on 127.0.0.1:18787 (no camera, light or Pi), Graphite and Lightbox | VERIFIED: "Camera host online"; the plan, strip and rail of a host with no camera connected |
| `cargo test --locked --release -p strehl-ui capture_station_pointer_sweeps -- --ignored --nocapture` | MEASURED: whole shell plus station, paint and tessellation, 6 sweeps of 80 frames: plan 0.156-0.164 ms/frame (8,644 vertices), flight 0.114-0.133 ms/frame (6,208 vertices). Not the P0 process-view harness; its baseline was 1.28-1.32 ms/frame |
| `pointer_motion_over_the_station_rebuilds_nothing` | MEASURED: rail mesh builds and live-view uploads unchanged over a 24-frame sweep through the shell |

### Open issues (stage 2)

- The breadcrumb shows only "Library" on Capture (P1 leaves Capture out of
  the crumbs); the mockup shows subject / stack / Capturing.
- The activities tray is P5's; the capture activity is the shell's row.
- Glance keeps the window's minimise / maximise / close buttons above it.
- Mockup details without data: frame rate in the live badge, "Tell my
  phone", the power-down grace, icons in the flight inspector.
