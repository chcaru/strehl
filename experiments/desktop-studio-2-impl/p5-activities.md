# P5 stage 1: activities, the stack queue, ETA, Quiet mode and the tray

Stage 2 (composition into the shell) is recorded below, under "Stage 2: composition into the
Studio 2 shell (done)".

**Date:** 2026-11-21. **Branch:** `studio2/p5-activities` from `55a07d64c`.
**Scope:** plan 6.6 (steps 1-3, 5 and 6 as models and adapters), 5.2, 9 (P5), 11. Stage 1 adds
the model, the adapters, the queue and its file, the ETA, Quiet mode and the tray. Nothing in
`app.rs`, `app-workspace.rs`, `theme.rs` or `main.rs` changed except `#[path]` module lines. The
wiring into `StrehlApp` is stage 2, after P1 merges; the exact edits are listed below.
**Environment:** Windows 11, rustc 1.98.0, `CARGO_BUILD_JOBS=8`, debug builds.

## What was added

| File | What it is |
| --- | --- |
| `activity.rs` | `ActivityKind`, `ActivityState` (Waiting, Running, NeedsYou, Stopped, Done, each with its obligation), `Lane`, `CancelMode`, `ActionId`, `ActivityStatus`, trait `Activity`; the `Activities` registry; `HistoryEntry`; `QuietMode`; adapters for crate-level owners (capture-tool slots, calibration, the capture checker, camera metadata, the render). |
| `activity-queue.rs` | `FrozenRequest` (a `RenderRequest` that can be stored), `QueuedStack`, `QueueEntry`, `StackQueue` (serial Heavy lane, `StartGate`, reorder, remove, pause, reconcile on load), the `activities.json` store (`load`, `save`, `ActivityStore::save_if_changed`). |
| `render-eta.rs` | Parses the engine's stage lines (`frames … (first decode X s)`, `alignment … X s`, `folded : N / M frames in X s (Y s per frame …)`, `collapse+write`, `total`) into `StageTimes`, one per pass; `EtaTracker` timestamps `frame-finished` events on receipt; `read_seed`/`spawn_seed` read the last 1 MiB of a previous `render.log` on a worker. Not in `pipeline.rs`. |
| `activity-tray.rs` | The tray popover: header with the Quiet switch; running rows with phase, frames, time left, "ends HH:MM", bar and Stop; the Waiting group with Remove (and Resume when the queue is paused); Earlier today with Reveal/Log/Retry and Full log; the Quiet explanation while it holds. Returns `TrayIntent`. Drawn with the shared `library-paint.rs` palette and marks; a moon glyph and a square toggle were added there. |
| `app-activities.rs` | `StrehlApp::report_activities` (render, export chain, view bundle, session import, metadata, capture), `activities_value` for the agent snapshot, `render_outcome_note`. |
| Owner accessors | `CaptureWorkspace::report_activities` (capture on the Camera lane, checker, calibration, focus step, compaction estimate, compaction on the Heavy lane); `export_phase()` in `app-photo-history.rs` (the three-task export chain as phases 1-3, from a new `export` tag on its pending task); `BundleProgress` and `export_with_progress` in `session-bundle-export.rs` (the unused observer, now counting bytes against the bundle's size). |
| Fixtures | `crates/strehl-ui/fixtures/render-logs/{cpu-299,gpu-1321}.log`: stage lines and a few progress events cut from two real render logs (2.2 KB and 2.7 KB), capture paths replaced, no diagnostic hex. |

Design notes (ARGUED):

- **Owners keep their work; they report status.** Each frame the shell calls `begin`, each
  owner reports, `end` notes changes and records a terminal state once even when the owner keeps
  showing its last result. A frame touches only this frame's and last frame's lists; history
  grows only on a terminal state (bounded at 200, the file likewise).
- **A loaded queue is paused.** After a restart heavy work never starts by itself; the tray
  offers Resume. A stack that was running when the desktop closed is recorded as stopped with
  Retry (its catalog run is reconciled to Interrupted by P4's `reconcile_interrupted_runs`), and
  queued stacks whose catalog stack is gone are dropped with a note.
- **Quiet** reads `SHQueryUserNotificationState` at most every 2 s and holds on
  `QUNS_RUNNING_D3D_FULL_SCREEN` or `QUNS_BUSY` (VERIFIED in the locked `windows-sys` 0.61.2
  `Win32_UI_Shell`, already enabled). Whether a borderless-windowed game reports either state is
  UNVERIFIED; the switch covers that case.
- **ETA:** in the merge, remaining frames × rate + the seed's collapse+write; the rate is live
  once 8 frames over at least 1 s have arrived, else the previous render's seconds per frame;
  time since the last frame counts down; the write stage counts down from the seed's
  collapse+write. Before the merge, the seed's whole-render estimate. A log may hold a quick
  preview pass before the full one; only a complete pass seeds.

## Results

Commands: `cargo test --locked -p strehl-ui`, `cargo clippy --locked -p strehl-ui --all-targets
--no-deps -- -D warnings`, `cargo fmt -p strehl-ui -- --check`; the tray picture with
`$env:STREHL_P5_SHOTS=<dir>; cargo test --locked -p strehl-ui -- offscreen_tray_picture --ignored --nocapture`.

- **Tests** (MEASURED): 1,162 passed, 0 failed, 21 ignored; "Compiling strehl-ui" observed. 27
  new, plus the ignored offscreen tray picture: registry (frame cycle, revision, once-only terminal records, bounded history, public JSON,
  frame cost), Quiet (timer, switch, the real probe runs), adapters (slots incl. a running engine
  on Windows, calibration stages, render), queue (serial lane, gates, reorder, remove, Waiting
  reasons, file round trip, atomic write, bounded history, unreadable and newer files left
  untouched, restart reconcile), ETA (both fixtures, preview pass ignored, tail read of a 2 MiB
  log, malformed lines ignored, seed then live rate, countdown, write stage, new pass, no seed),
  tray (contents, every intent, Resume), app adapters (idle, import and bundle, outcome notes).
- **Clippy and format** (MEASURED): clean with `-D warnings`; "Checking strehl-ui" observed.
- **Falsification** (MEASURED): the no-seed ETA test caught a real bug (an eager `seed?` hid the
  live rate when no seed existed), fixed; removing the once-only check fails the history test;
  dropping the running-stack hold fails the serial-lane test.
- **Frame cost** (MEASURED, debug build): 12 activities reported and closed in 3.1-3.2 µs a
  frame, the same with an empty and a full (200) history.
- **Look** (VERIFIED by viewing an offscreen render beside `capture-flight-jobs.png`): header,
  Quiet switch, running row with bar, Waiting group with Remove, Earlier today with Full log and
  Reveal, and the Quiet note match the mockup's layout; fonts are the system face until P1.

## Stage 2: the `app.rs` integration plan

Line numbers are at `55a07d64c`; search by the quoted name.

1. **Fields** on `StrehlApp` (`app.rs` near 120-230): `activities: activity::Activities`,
   `quiet: activity::QuietMode`, `queue: activity_queue::StackQueue`,
   `activity_store: activity_queue::ActivityStore`, `eta: render_eta::EtaTracker`,
   `eta_seed: Option<Task<Option<render_eta::StageTimes>>>`, `running_queue_id: Option<u64>`.
   Change `view_bundle_export` to `Option<(Task<PathBuf>, Arc<session_import::BundleProgress>)>`.
2. **`from_launch`** (near 242): after loading the catalog, `catalog.reconcile_interrupted_runs(&[])`
   (P4), then `let (mut queue, history, error) = activity_queue::load(path)` with
   `path = activity_queue::default_path()` (or beside `--catalog` for isolated launches);
   `let notes = queue.reconcile(&catalog, timestamp())`; `Activities::with_history(history)`
   and `record` each note; show `error` as a notice.
3. **Queueing** (`start_render`, near 661): split it. `queue_render()` freezes today's request
   (`RenderRequest` as built now), the pending `Run` and a `QueueEntry` (stack id, "Stack ·
   <name>", planes, `StageTimes::estimate` from the stack's last seed) into `queue.enqueue`. The
   agent's `StartStack` (`app-agent.rs` near 639) keeps answering `"queued"`, now true.
   `start_queued(item)` holds today's body of `start_render` with
   `RenderRequest::from(item.request)`, `pending_run = Some(item.run)`,
   `pending_stack = Some(item.stack)`, and sets `running_queue_id`.
4. **Each frame** in `poll` (near 761), before the render events:
   `let gate = StartGate { heavy_busy: self.job.is_some() || self.activities.heavy_busy(), quiet: self.quiet.holds(now) };`
   `if let Some(item) = self.queue.take_next(gate, unix) { self.start_queued(item) }`.
   After the events: `activities.begin()`, `queue.report(&mut activities, gate, quiet.reason())`,
   `self.report_activities(&mut activities, self.eta.eta(now))`, `activities.end(now, unix)`,
   `activity_store.save_if_changed(&queue, &activities)`. Request a repaint only while something
   runs (each owner already wakes on its own completion).
5. **Render events** (near 883-980): `Started` → `self.eta = EtaTracker::new(None)` and, when the
   stack has an earlier run, `eta_seed = Some(render_eta::spawn_seed(previous.log, ctx))`; poll
   the seed with `try_recv` and `eta.set_seed`. `Log(text)` → also `self.eta.ingest(&text, now)`.
   `Finished` → `queue.finish(id)`, `activities.record(Self::render_outcome_note(...))`.
6. **The per-job move** (6.6 step 4): `progress` (78 uses across `app*.rs`), `logs` (8),
   `started` (6), `pending_run` (7), `pending_stack` (4) move into one `RenderSlot { job,
   progress, logs, started, run, stack, eta, queue_id }`. The open document's view reads the
   slot whose stack is open; a finished slot's `progress` moves to the document as today.
7. **The tray**: the top bar's job status opens `activity_tray::show(ctx, anchor, TrayInputs {
   activities, quiet_switch, quiet_holds, palette, now, unix })`. Route `TrayIntent`:
   `Cancel(id)` by `activities.find(id).kind` (Stack → `job.cancel()`; Export →
   `editor.exporting` task cancel; ViewBundle and Import → their task's `cancel()`; FocusStep →
   `capture.cancel_focus_step()`; CompactEstimate → `capture.cancel_compact_estimate()`;
   Calibration → `capture.stop_calibration()`; Capture → today's confirmed Stop; Metadata →
   `camera_metadata`'s `cancel`, made `pub(crate)`); `Remove(id)` → `queue.remove`; `SetQuiet` → `quiet.switch` and
   Preferences; `ResumeQueue` → `queue.resume()`; `Action` → open stack or run, reveal, show log,
   retry (queue again); `FullLog` → the history view.
8. **Agent snapshot** (`app-agent.rs` `agent_snapshot`): add
   `snapshot["activities"] = Self::activities_value(&self.activities)`. Every key in plan 6.6's
   hazard list stays as it is.
9. **Shutdown and undo:** `prepare_headless_shutdown` (`app-headless.rs` near 209) saves the
   queue (it is persisted, so shutdown need not wait for it) and refuses only while a stack runs;
   Projects and Recipe undo stay disabled for the running stack only.
10. **View bundle:** `start_view_bundle_export` uses
    `session_import::export_view_bundle_with_progress`; its activity reports `copied`/`total`.

## Stage 2: composition into the Studio 2 shell (done)

**Date:** 2026-11-21. **Branch:** `studio2/p5-activities`, merged with the integration branch at
`82ccbfd45` (merge `49c967e36`). **Build:** release `strehl-ui.exe` from this branch;
`CARGO_BUILD_JOBS=8`.

**The merge.** The P1 shell had its own `activity.rs` (190 lines) and `activity-tray.rs` (362
lines). The P5 model is the authority; it took the shell's `ActivityKind::Open` (reading a
bracket, reopening a render), `key()`, `facts`, `ActivityStatus::running` and `progress_line`
(phase · count · time left, or elapsed). `Shell::activities()` now reads the registry (this
frame's reports minus waiting stacks) for the top-bar indicator; the snapshot key `activities`
is `Activities::public` plus `queue_paused`, one key, the shell's `route` and `notices` kept.
The tray is drawn inside the shell's popover with Studio 2 tokens and widgets, in the mockup's
order: header with moon, Quiet and its switch; running rows (title, Stop on the title line,
phase · count · time left · ends HH:MM, the facts line, an ok-coloured bar); Waiting (numbered,
Remove, Resume when paused, the head's reason on the right); Earlier today (Full log, Reveal/
Log/Retry/Open or the finish time); then the shell's Notices (Mark all read, Log/Open, Dismiss,
"N earlier") and Engine log/Agent links; the Quiet note while it holds. `TrayAction` replaces
both earlier enums.

**`app.rs`** (contained; the rest is in `app-activities.rs`): one field
`activity_hub: activities::ActivityHub` (the name `activity` was taken by a bool); startup calls
`ActivityHub::load`, which runs P4's `reconcile_interrupted_runs(&[])` and loads, reconciles and
pauses the queue beside the catalog (`activities.json`; offscreen pictures read none);
`start_render` first calls `queue_while_running`; the job start and view reset moved into
`launch_render(request)`, shared with the queue; one-line hooks in the `Started`, `Log` and
`Finished` events; `activities_frame(ctx)` once per poll after the events. Step 6 (a per-job
struct) was skipped as instructed: the Heavy lane is serial.

**Policy (ARGUED).** The queue starts its head when no Heavy work runs, Quiet does not hold,
and the workspace can take a stack (no file dialog, nothing opening, and not under a hand in
Develop or Export with a photograph loaded). A queued stack that is not the open one is opened
with `open_project_stack` first, then launched with its frozen request and run record. Start
(shortcut or palette) while a stack renders queues the open stack's current recipe; the same
render as the running one, or one already waiting, is refused, so a repeated press queues
nothing. The Start button itself stays disabled while a stack runs, and the agent's
`start_stack` answers as before. Quiet is the Preferences switch "Quiet" (`studio.json`
`quiet`, on by default) and the tray's switch writes the same preference; when off, the
foreground is not read. Tray Stop routes per owner; a capture only opens its own confirmation
on the Capture screen; compaction reports `CancelMode::None` and shows no Stop. Camera
metadata's `cancel` is `pub(crate)`. The view-bundle export reports bytes copied. A failing
`activities.json` save is tried once per change, not every frame.

**Agent (additive).** `queue_stack {id}`, `remove_queued_stack {queue_id}`,
`move_queued_stack {queue_id, position}`, `resume_queue {}`; MCP schemas and
`docs/desktop-control.md` updated.

### Stage 2 results

- **Tests, clippy, format** (MEASURED): `cargo test --locked -p strehl-ui` 1,288 passed,
  0 failed, 23 ignored ("Compiling strehl-ui" observed); clippy `-D warnings` and
  `fmt --check` clean. New: app-level queue (Start while rendering queues a variant once, the
  duplicate is refused, the queue starts it after the first ends, history records both), the
  workspace hold and Remove from the tray, a restored queue waits paused (offscreen reads none),
  tray Stop routing (capture asks first; compaction has no Stop); tray tests rewritten for the
  merged tray, including notices and Dismiss.
- **End to end** (VERIFIED, release, headless agent, scratch catalog, isolated capture
  settings, three brackets of 3, 40 and 40 frames copied from a capture folder into scratch):
  three `queue_stack` calls; alpha started at once with beta and gamma listed waiting "the stack
  before it"; `start_stack` while running answered `"A stack is already running"` as before;
  queueing alpha again was refused; beta started once alpha had saved; `cancel_stack` on
  beta, then gamma started and beta read "Cancelled"; alpha queued behind gamma; the process was
  killed with gamma running and alpha waiting. `activities.json` held alpha queued and gamma
  running. After relaunch the snapshot read `queue_paused: true`, alpha "waiting for you to
  resume the queue", gamma "stopped: the desktop closed while this stack was running", and the
  catalog run gamma `Interrupted`; nothing started in 3 s; `resume_queue` started alpha, whose
  time left came from its earlier log (0.5 s in the merge, 0.41 s writing) and it saved.
  Renders of 40 frames merged in under a second here, so no live rate (8 frames over 1 s) formed
  in this run; the live path is covered by the log-fixture tests.
- **Look** (VERIFIED by viewing): the tray rendered offscreen in Graphite, Instrument and
  Lightbox (`offscreen_tray_pictures`, ignored test) beside `capture-flight-jobs.png`: same
  sections, order, rules, marks, caps links and bar; detail lines run full width under the title
  as in the mockup. `visual-check.py library stack` (release): the top bar reads "Nothing
  running" as before.
- **Performance** (MEASURED, release, `--test-threads 1`): the activities pass with a paused
  two-stack queue and 200 history entries 0.22-0.23 µs a frame; the open tray painted and
  tessellated under a pointer sweep 0.063-0.081 ms a frame
  (`benchmark_activities_frame_and_tray_pointer_sweep`). The P0 pointer sweep
  (`benchmark_finished_workspace_pointer_sweeps`), three repeats: process 1.25-1.40 ms a frame
  (medians 1.28-1.33), source 0.44-0.45 (one 0.55 sample); a first run straight after the
  release build read 1.35-1.49 and was repeated.

## Open issues

- Stage 1 items now closed: the capture's Stop goes only through its own confirmation;
  compaction shows no Stop (`CancelMode::None`); release figures are above; the milestone row is
  marked done.
- A waiting stack shows "about N s" only when the running render is the same stack (its seed);
  an estimate for any queued stack needs its previous log read on a worker at enqueue (not
  built).
- In the end-to-end run the seeded estimate appeared in the merge and the write but not while
  the resumed stack aligned (Preparing); whether the seed arrived late or a 3-frame log lacks
  the stage lines for a whole-render estimate is UNVERIFIED.
- The live rate needs 8 frames over at least 1 s; very fast stacks finish their merge first
  and show time left only from a seed.
- Queueing from the UI: Ctrl+Enter and the palette's Start while a stack runs, and the agent.
  The Stack station's disabled Start button (P3) and a Library "Queue" action (P4 stage 2) can
  call `queue_stack(id)` / `queue_while_running()`; not added here.
- A capture that finishes while a stack runs still reports that stacking is blocked rather than
  queueing it (`app-workspace.rs` follow path).
- Whether a borderless-windowed game reports a Quiet state is still UNVERIFIED; switching Quiet
  off in Preferences or the tray removes the hold.
