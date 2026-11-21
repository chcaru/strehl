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

## Needs a Pi deploy and a rig test (not done: no Pi, camera or light touched)

1. Deploy the host (H1, H2) to the Pi (cross-built in WSL as root) and restart
   the controller; switch "manage power" back on afterwards.
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
- `capture-follow.rs` still reads the journal on the UI thread (now at most
  64 KiB a poll instead of the whole file); moving it to the client thread is
  left to the in-flight screen.
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
