# Retakes: the limit, retakes by hand, and runs of one-shot planes (h-retake)

**Date:** 2026-11-22. **Branch:** `studio2/h-retake`, from `d359bbe28`.
**Scope:** the camera host's retakes (`crates/strehl-capture`), the checker's
end of a run (`crates/strehl-cli/src/follow-cmd.rs`, one test in
`pixel-shift-cmd.rs`), and in the desktop the feed rows' content and actions,
a coverage warning above the feed, the review's retake action and the
max-retakes setting. Nothing deployed; the Pi, rig and camera were not
touched. **Labels:** MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED.

## The owner's words (verbatim)

On the Capture screen:
- "make the max number of retakes configurable."
- while stacking: "if retakes exceed the max number of allowed retakes and end
  in failure, i would like an option to manually queue a retake"
- "if too many planes fail in a row, per the calibrated overlap, such that the
  final stack would likely risk degradation, i would like some warning and
  corrective action, such as to retry the whole span."

## How the stack chooses among a plane's tries (found)

| Fact | Where | Label |
| --- | --- | --- |
| The stack uses a plane's **last complete group in journal order**; a later incomplete group loses to an earlier complete one. No verdict is read: the stack judges each group itself and folds a demoted group to member 1 | `strehl-cli/src/pixel-shift-cmd.rs` `plane_groups` (via `all_groups`, which reads every `capture_buffered`/`capture_complete` event, also ones after `finished`) | VERIFIED (code; existing test `a_retaken_plane_uses_its_last_complete_group`; new test below) |
| The checker (`strehl follow`) re-reads the whole journal each pass and checks every complete group it has not checked; it exits once `result.json` exists and every chosen group is complete | `follow-cmd.rs` `run` | VERIFIED (code) |
| The receiver accepts new frames and an appended `events.jsonl` in a run that has `result.json`; it refuses to change `result.json` or `manifest.json` | `receiver.rs` `create_run`, `receive_file`, `append_journal` | VERIFIED (code) |
| A single-shot run has no four-shot group, so the stack takes **every** RAW in the folder: a retake of a single-shot plane is a second frame at that depth, not a replacement (true of error correction's retakes already) | `merge_cmd.rs` (`four_shot_planes` is `None`) | VERIFIED (code); not changed |

So a retake by hand is used by the stack because it is recorded after the
plane's earlier tries under the same plane number. What remained was to make
sure such a retake never replaces a try that **passed**: the host checks the
plane's newest try before taking it (see below), and the desktop offers
"Retake" only on a plane's newest try when it failed.

## Decisions

### 1. The limit: 0 to 5, default 2, set with error correction

- **Where:** the host's `error_correction` command gains an optional
  `max_retakes` (`Command::ErrorCorrection { enabled, max_retakes: Option<u8> }`),
  next to the switch it belongs to. It is held between stacks like the switch
  and journalled at the start of each run (`error_correction` event:
  `{"enabled","max_retakes"}`).
- **Range 0-5** (`worker::MAX_RETAKES_LIMIT`). In the owner's run of 2026-11-21
  (211 planes) the second try passed 18 of 34 times and the third 7 of 15
  (MEASURED from the checker's journal, scratch copy): a later try still
  passes about half the time, so more than two can help. Each retake costs
  about 10.2 s (MEASURED in g-flight, 49 retakes): five is at most about 51 s
  on one plane, and a plane still failing after six tries is better left to a
  retake by hand. **0** keeps every plane checked (the feed and the warning
  still work) and retakes none automatically. (ARGUED)
- **Compatibility:** the field is skipped when `None`, so an older host never
  sees it, and the desktop sends it only when `capabilities.max_retakes` is
  reported. A newer host given an older desktop's `error_correction` (no
  field) uses **2** (VERIFIED, test). The switch now always sends the current
  value, since a missing field means two.
- **The desktop's words** use the run's value: the host reports `retakes.max`;
  rows say "Taking it again (try 2 of 4)", the policy "Retaken, up to 3
  times", and with 0 "Not retaken: retakes are set to 0." The checker's tally
  is resolved by the same value (the follower is told it each frame), so the
  counts above the feed, the health line and the checker's activity agree.
  An older host reads as 2.

### 2. Retakes by hand

- **Host control:** a new command `queue_retakes { planes }` on the same
  `/api/command` channel, bound to the capture by `sequence_id` like Pause and
  Stop (not to the latest revision, which changes every plane). Capabilities
  gain `max_retakes` and `queue_retakes`; state gains
  `retakes: {max, limit, accepted, queued, run, followup}`.
- **During the capture** (or paused): the planes join a queue the worker reads
  between planes, where error correction's own retakes are taken, through the
  same approach move, recorded as `retake_intent` with `"manual": true` and
  the plane number. A plane whose newest group is still being checked waits
  for its check. One whose newest try passed, or that error correction is
  about to retake anyway, is not taken (`manual_retake_skipped` with the
  reason). A plane not taken yet is refused. A retake by hand is **one try**:
  if it fails, error correction does not follow it with more
  (`retake_exhausted` with `"manual": true`); the user can ask again. Retakes
  still queued when the capture stops or ends are journalled as
  `manual_retakes_dropped` and the queue is emptied, so the desktop offers
  them again.
- **After the capture** (complete or stopped): the host takes just those
  planes again **into the same run**. It reads the run's manifest and journal
  (`RunRecord`: plan, positions, initial exposure, RAWs and planes so far,
  each plane's newest group). It refuses before any move or exposure unless
  the run was a stack stored on the PC, and the camera is the same body with
  the same RAWs a plane, program, ISO, shutter and aperture. It then reopens
  the journal for appending (`Journal::reopen`) and continues the PC run
  (`Camera::resume_run`: the next frame names and the plane count, registering
  the run again if the camera was switched off). The journal records
  `followup_started` (`{"planes","manual":true}`), each retake, and
  `followup_finished` with `taken`, `skipped` and the outcome. `result.json`
  is untouched. Planes asked for while these retakes run join them. With
  managed power the camera is woken and the light warmed, then both are
  switched off again as after a stack.
- **The checker after the capture:** `strehl follow` treats a run with an open
  `followup_started` as not finished, so its new groups are checked; the
  desktop restarts its checker on that run while the host reports a
  follow-up, and does not offer the capture to the library a second time.
- **The desktop:** "Retake" (warning colour) under "Show" on the newest try of
  a plane left to one shot that nothing else will retake (error correction gave
  up, the checker's rule, error correction off, capture ended, RAWs missing),
  when the host takes retakes by hand. Once asked the row reads QUEUED, "Retake
  asked for: taken between planes." (or "Retake asked for." after the capture)
  and "Asked" in place of the link, until the plane's next try is checked, or,
  the host no longer running and holding nothing for it, three seconds have
  passed. In the review, under the summary: "Retake the N planes that failed
  every try". "Show" moved to the row's left edge so "Retake" under it clears
  the detail text.

### 3. Runs of one-shot planes against the calibrated overlap

The rule (`flight::risk_spans`, ARGUED):

- A plane stacked from one shot still adds its depth's detail, at one shot's
  resolution. So what a run of such planes loses is four-shot detail, and
  only where no four-shot plane is sharp enough.
- The calibrated sharp width (`strehl focus-step`) is the width of a point's
  sharpness peak at **half height**. For a peak of that width, sharpness is
  about 84 % of the peak a quarter-width away, and 50 % at half the width.
- For a run of `k` neighbouring one-shot planes, the four-shot planes either
  side are `gap = (k + 1) × step` apart. The depth midway is `gap / 2` from
  both.
- The run is at risk when that depth is more than a quarter of the width
  from both, i.e. `gap > width / 2`: fewer than two four-shot planes hold it
  sharp. The band at risk is `gap − width / 2` focus units.
- At the calibration's suggested step (width / 7) this needs three planes in
  a row. One plane alone needs a step coarser than width / 4, beyond the
  measured knee (width / 5) that the step table already marks.

Avoiding false alarms:

- A plane whose retake is still to come is not counted. Nor is a plane not
  checked yet. Either one breaks a run.
- Planes the checker did not retake (shift pattern, residual compensation)
  **do** count. The warning says why each was not retaken, in the feed's own
  words ("2 not retaken: shift pattern off (by the checker's rule)").
- Without a calibration, the width is taken as 7 steps, the step a
  calibration suggests, and the warning says so ("assumed; Calibrate step
  measures it").

Checked against the owner's run of 2026-11-21 (step 7, MEASURED from the
checker's journal): its 27 one-shot planes form 17 single planes, one pair
and two runs of four (30-33 and 144-147). At width 50 (the pencil subject's
calibration) only the two runs of four would be named. (DERIVED: the run's
own width was not measured.)

The warning sits **above the feed**, in the side column, so it stays out of
the proof's region (lane h-proof):

- A square, ruled box with a warning-coloured rule and mark.
- "Planes 44–47: 4 in a row from one shot".
- What it costs: "The four-shot planes either side are 35 units apart, more
  than half the sharp width (50): about 10 units of depth there get one
  shot's detail, not four."
- Why, by kind.
- "Retake planes 44–47". After the click it reads "Retakes asked for planes
  44–47".
- It shows the two longest runs. When there are more, it adds "N more runs
  like these" and "Retake all N planes".
- It is the same in flight and in the review.
- It is computed only when the feed or its context changes, never per frame.

## What changed (files)

| File | What |
| --- | --- |
| `crates/strehl-capture/src/worker.rs` | `Snapshot` (`max_retakes`, `retakes_accepted`, `retake_queue`, `followup`), `Followup`; `Action::ErrorCorrection { enabled, max_retakes }`, `Action::Followup`; `Worker::send` (follow-up admission), `Worker::queue_retakes`; `run` (both actions; waking a switched-off camera keeps the run's record); `StackRun.followup`, `run_stack`; `capture` (the run's limit, journalled; manual retakes between planes and at the end; dropped ones said); `MAX_RETAKES_LIMIT`; `Owed.manual`, `PlaneRecord`, `Retakes`, `check_passed`; `collect_verdicts`, `due_retakes`, `manual_due`, `retake` (manual intent); `warm_light` (moved out of `capture`); `RunRecord`, `followup` |
| `crates/strehl-capture/src/session.rs` | `Command::ErrorCorrection.max_retakes`, `Command::QueueRetakes`; `dispatch`; `state` (`retakes`, capabilities `max_retakes`, `queue_retakes`) |
| `crates/strehl-capture/src/journal.rs` | `Journal::reopen` |
| `crates/strehl-capture/src/backend.rs` | `Camera::resume_run`; test-only `sim::PcSim` (four-shot PC camera numbering planes as `PcCamera`, scripted checker, injected requests and Stop) |
| `crates/strehl-capture/src/transfer.rs` | `PcCamera::resume_run` |
| `crates/strehl-capture/src/worker-retake-tests.rs` | new tests (below) |
| `crates/strehl-cli/src/follow-cmd.rs` | `followup_open`; `run`'s "finished" |
| `crates/strehl-cli/src/pixel-shift-cmd.rs` | test only |
| `crates/strehl-ui/src/capture-host.rs` | `Capabilities.max_retakes/queue_retakes`, `Retakes`, `Followup`, `HostState.retakes`, `KNOWN_KEYS`; `max_retakes`, `takes_manual_retakes`, `retakes_in_hand` |
| `crates/strehl-ui/src/capture-follow.rs` | `Tally` (raw counts, `max`, `resolve`, `counts`), `JournalReader::set_max_retakes`, `ReaderShared.max_retakes`, `reader_thread`, `Follower::start`, `Follower::set_max_retakes` |
| `crates/strehl-ui/src/capture-flight.rs` (shared) | see the list below |
| `crates/strehl-ui/src/capture-station.rs` (shared) | `Station.asked`, `AskedRetake`, `ASKED_GRACE`, `retakes_in_hand`; `load_fixture` (`flight+retakes`, `flight+retakes-done`); `apply_plan` (`SetRetake` sends the limit, `SetMaxRetakes`); `apply_flight` (`QueueRetakes`); `queue_retakes`; `flight_inputs` (`retakes`); test module |
| `crates/strehl-ui/src/capture-workspace.rs` (shared) | `poll_follow`: restart the checker for retakes after the capture; tell the follower the limit |
| `crates/strehl-ui/src/capture-rig-settings.rs` | `Key::MaxRetakes`, its `Spec` (0-5, default 2), `RigValues.max_retakes`, the row under the Error correction switch ("2, fixed on this host" on an older host), `intent`; the switch's line says about 10 s a retake (measured), not 8.5 |
| `crates/strehl-ui/src/capture-plan.rs` | `PlanIntent::SetMaxRetakes` |
| `crates/strehl-ui/src/capture-fixture.rs` | `plan_state` reports the new capabilities; `retake_checks`, `retake_progress`, `add_retakes` |
| `crates/strehl-ui/src/main.rs` | the fixture names' comment |
| `crates/strehl-ui/src/capture-retake-tests.rs`, `capture-retake-station-tests.rs` | new tests |
| `crates/strehl-ui/src/capture-flight-tests.rs`, `capture-host-tests.rs`, `app-station-capture-tests.rs` | literals for the new fields; the feed benchmark also sweeps `flight+retakes` |
| `experiments/desktop-studio-2-impl/visual-check.py` | routes `capture-flight-retakes[-lightbox]`, `capture-flight-retakes-done[-lightbox]`, `capture-plan-rig-retakes` |

Functions touched in `capture-flight.rs` (shared with h-proof):

- Module doc and imports.
- `health`: the tally resolved by the run's limit.
- `FeedContext`: new fields `max_retakes` and `manual`, and its own
  `Default`. New `RetakeOffer`; `FeedRow.retake`.
- `feed_row`, now a wrapper of the new `feed_row_with`.
- New `Failure::policy_for`.
- `FlightInputs.retakes`; new `RetakeInputs`; `FlightIntent::QueueRetakes`;
  `FlightView.risk`.
- `canvas`: two small edits after the proof's caption. `cx` comes from
  `feed_context`, and `risk_banner` runs before `feed_ui`. The proof's
  rectangle and caption are untouched.
- `feed_ui`: takes `in_hand`, resolves the tally, adds the review's action.
- `feed_row_ui`: "Show" moved to the left edge, and the Retake link.
- New: `feed_context`, `newest_tries`, `one_shot_why`, `exhausted_planes`,
  `RiskSpan`, `ASSUMED_OVERLAP`, `risk_spans`, `plane_list`,
  `risk_sentence`, `risk_banner`.

`FlightInputs` gains a field. Lane h-proof's edits to `FlightInputs` and to the
test literal in `capture-flight-tests.rs` will need a one-line merge.

## Tests

Host (`worker-retake-tests.rs`, `session.rs`), on the simulated PC camera:

| Test | What it holds |
| --- | --- |
| `the_runs_max_retakes_decides_how_often_a_plane_is_taken_again` | 0, 1, 2, 3 retakes as set (and 99 held to 5); `retake_exhausted` carries the limit; the run journals its setting |
| `a_retake_queued_mid_run_is_taken_between_planes` | queued mid-run: taken after the next plane, through the approach, journalled manual under its plane number; a failing manual retake is not retaken |
| `an_exhausted_plane_can_be_retaken_by_hand` | exhausted then manual: a fourth try, the newest group, which passes |
| `a_manual_retake_never_replaces_a_pass` | a passed plane and one error correction is retaking are skipped; one not taken yet is refused; each said |
| `retakes_after_the_capture_go_into_the_same_run` | queued after the end, a span (3-4) with a passed plane (skipped): same run, plane numbers kept, frame names continue (17, 21; then 25), events numbered on, `result.json` byte-identical, phase back to Complete |
| `a_stop_part_way_keeps_what_was_taken` | Stop after two of four retakes afterwards: `stopped`, 2 taken; during a capture, a queued retake dropped and said |
| `retakes_after_the_capture_need_the_captures_exposure` | ISO changed, single shot, a plane beyond the stack: each refused before any focus move |
| `a_retake_asked_during_the_retakes_after_joins_them` | asked while retakes afterwards run: joins them; a plane never taken refused |
| `an_ended_run_is_read_back_from_its_journal`, `a_card_capture_takes_no_manual_retakes` | the run record; a card capture refuses |
| `max_retakes_is_optional_bounded_and_reported` (session) | an older desktop's `error_correction` parses and sets 2; 6 refused; the request omits the field when unset; state reports `retakes` and the capabilities |
| `retakes_are_queued_during_and_after_a_capture` (session, end to end through the controller and its worker thread) | queued while paused, taken on Resume; queued after Complete, taken into the same run under the same sequence; another capture's request refused |

The `cli` test `a_retake_after_the_capture_is_the_group_the_stack_uses`
(`pixel-shift-cmd.rs`) covers two things:

- A retake recorded after `finished` and `followup_started` is the plane's
  chosen group.
- `followup_open` is true until `followup_finished` is written.

Desktop (`capture-retake-tests.rs`, `capture-retake-station-tests.rs`, and
amended tests):

- `rows_say_the_runs_own_limit`: tries left, the policy and the tally by the
  limit, 0 included.
- `retake_is_offered_where_nothing_else_will_retake`.
- `a_run_too_long_for_the_overlap_is_named_with_its_cost`: the rule.
  - The fixture's span 44-47 (gap 35, band 10, why).
  - Width 80: no warning. An assumed width: a warning that says so.
  - Singles: never. At width / 7: three in a row warn, two do not.
  - A retake to come and a plane not yet checked each break a run.
- `the_warning_and_the_rows_ask_for_retakes`: clicks.
  - "Retake planes 44–47" sends `QueueRetakes([44..47])`.
  - A row's RETAKE sends its plane; QUEUED/ASKED show for plane 59.
  - The review's "Retake the 2 planes that failed every try" sends
    `[45, 52]`.
  - An older host gets the warning without the actions.
- `retakes_are_asked_of_the_host_and_shown_until_taken`: the command sent; in
  hand until the next try, another capture's not; an older host is not asked.
- `the_retake_setting_travels_with_error_correction`.
- `progress_counts_planes_as_the_engine_resumes_them` (the tally resolved by
  0).
- `the_simulators_state_reads_typed_through_a_whole_capture` (the
  capabilities, `retakes`, `KNOWN_KEYS`).
- `an_older_hosts_state_reads_with_its_newer_fields_absent`.

Placebo: making `collect_verdicts` use the constant 2 instead of the run's
limit makes `the_runs_max_retakes…` fail. Restored, it passes. (MEASURED)

## Commands and results

Worktree `C:\w\h-retake`, Windows 11, 32 logical CPUs, other lanes building
at the same time.

| Command | Result |
| --- | --- |
| `cargo test --locked -p strehl-capture` | MEASURED: Compiling strehl-capture; 75 passed, 0 failed (12 of them new: 63 at the base, DERIVED) |
| `cargo clippy --locked -p strehl-capture --all-targets --no-deps -- -D warnings` | MEASURED: Checking strehl-capture; exit 0 |
| `cargo fmt -p strehl-capture -- --check` | MEASURED: exit 1, every difference in `receiver.rs` (untouched; differs at the base too) |
| `cargo test --locked -p strehl-ui` | MEASURED: Compiling strehl-ui; 1,547 tests, 1,503 passed, 0 failed, 44 ignored (the new ignored one is the benchmark `risk_spans_cost`) |
| `cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings` | MEASURED: Checking strehl-ui; exit 0 |
| `cargo fmt -p strehl-ui -- --check` | MEASURED: exit 0 |
| `cargo test --locked -p strehl-cli --lib -- a_retake_after_the_capture a_retaken_plane_uses` | MEASURED: Compiling strehl-cli; 2 passed |
| `cargo clippy --locked -p strehl-cli --all-targets --no-deps -- -D warnings` | MEASURED: exit 101. Every error is in files this lane did not touch (`image_out.rs`, `merge_cmd.rs`, `focus-step-cmd.rs`, `gatefloor.rs`, `known-scene-benchmark.rs`, the native adapter). None is in `follow-cmd.rs` or `pixel-shift-cmd.rs` |
| `cargo fmt -p strehl-cli -- --check` | MEASURED: differences only in untouched files; `follow-cmd.rs` and `pixel-shift-cmd.rs` clean |
| `wsl -u root bash build-pi.sh /mnt/c/w/h-retake /mnt/c/strehl-scratch/h-retake/pi` (a copy of the script with LF endings: the worktree's copy is checked out CRLF and bash stops at `set -o pipefail`) | MEASURED: Compiling strehl-capture (aarch64), release, exit 0; `strehl-capture-headless` sha256 `b5afa69f…24718ac`, `strehl-sony-ptp` `1c4d1ada…a891ed76` (scratch, not deployed) |
| `visual-check.py --exe target\debug\strehl-ui.exe --out C:\strehl-scratch\h-retake\shots capture-flight-retakes capture-flight-retakes-lightbox capture-flight-retakes-done capture-flight-retakes-done-lightbox capture-plan-rig-retakes capture-flight capture-flight-done` | VERIFIED by eye (below) |

### Frame cost (MEASURED, release)

The feed sweep `capture_flight_feed_sweeps` is the whole shell with the
pointer over the feed and the wheel scrolling it. Each figure is in ms a
frame, the minimum of six sweeps of 80 frames. The base binary
(`d359bbe28`, built in a scratch worktree) and this branch were run
interleaved, three rounds each.

| Fixture | Base r1 / r2 / r3 | Branch r1 / r2 / r3 | Vertices base / branch |
| --- | --- | --- | --- |
| flight (61 planes) | 0.134 / 0.135 / 0.134 | 0.137 / 0.135 / 0.137 | 8,582 / 8,582 |
| flight+long (5,400 planes) | 0.137 / 0.137 / 0.135 | 0.137 / 0.138 / 0.137 | 9,444 / 9,444 |
| flight+retakes (warning, an asked plane) | — | 0.134 / 0.135 / 0.135 | — / 9,016 |

No measurable change: the differences are within the base's own spread. The
warning adds about 430 vertices and no measurable time. The rule runs only
when the feed changes (a new check, about every 5.7 s): over the 5,681 items
of the 5,400-plane run it takes 0.178 ms (MEASURED, release,
`risk_spans_cost`, mean of 20).

## Screenshots looked at (scratch, not in Git)

`C:\strehl-scratch\h-retake\shots\`:

- `capture-flight-retakes.png` and `-lightbox.png`: the warning above the
  feed, square and ruled in the warning colour, with "Retake planes 44–47";
  plane 59 QUEUED with "Asked"; RETAKE under SHOW at the row's left edge.
  Nothing clipped; the proof untouched.
- `capture-flight-retakes-done.png` and `-lightbox.png`: the review. The
  warning, then the summary, then "Retake the 2 planes that failed every
  try", then the failure kinds.
- `capture-plan-rig-retakes.png`: the Rig settings. "Retakes a plane · 2
  retakes" with steppers under the Error correction switch, and its line.
- `crop-retakes.png`: the feed column at 2x.
- `capture-flight.png` and `capture-flight-done.png`: unchanged apart from
  SHOW's position.

The fixture is synthetic (no owner pictures). The Lightbox canvas uses the
canvas inks, as before.

## Deploy and rig test (not done here)

1. Deploy the host (`strehl-capture-headless`, and the bridge unchanged) as
   in the README's "Pi deploy", with the receiver and desktop of this branch.
   Check `/api/state` has `capabilities.max_retakes`/`queue_retakes` and
   `retakes`. Restore "manage power" to on afterwards.
2. Rig settings: set Retakes a plane to 0, 1 and 4. The host's `retakes.max`
   follows, and each run's `events.jsonl` starts with its
   `error_correction` event.
3. A short four-shot stack (about 20 planes) with Retakes 1, with motion
   induced on a few planes:
   - Rows say "try 2 of 2" and "Failed 2 tries".
   - "Retake" on an exhausted plane mid-run is taken between planes. Its row
     goes QUEUED, then a new try appears.
   - Its RAWs carry the plane's number; the checker checks them.
4. A run of three or more one-shot planes (cover the subject briefly at step
   about width / 7): the warning names it; "Retake planes A–B" takes them.
5. After the end, with manage power **on** (the owner's setting):
   - "Retake" on a plane wakes the camera and warms the light.
   - The plane is taken into the same run: new frame names, the same plane
     number, `followup_started`/`followup_finished` in `events.jsonl`.
   - The desktop's checker restarts and checks it. Then the rig powers down.
   - Re-stack from the library: the new try is used (the render log's
     "demoted" planes drop).
6. Stop part-way through retakes afterwards: `stopped`, the run stays
   complete and listed.
7. An older desktop against the new host still captures with error
   correction (two retakes). This desktop against the old host shows "2,
   fixed on this host" and no Retake.
8. End with the camera and light off.

## Open, or needs the owner

- UNVERIFIED on the rig: everything above the simulator (the PTP camera's
  plane numbering on `resume_run`, the receiver's re-registration after a
  power cycle, managed power around retakes afterwards, the checker restart
  in the desktop: `poll_follow`'s restart has no automated test).
- Retakes after the capture are used only when the capture is stacked again.
  A capture already stacked by "Stack it, then show the checks" is not
  re-stacked on its own, and the proof does not update. Re-stacking
  automatically would need the owner's decision.
- A single-shot run stacks every RAW (the engine's rule, unchanged), so a
  retake of a single-shot plane adds a frame rather than replacing one.
  This was already true of error correction's retakes.
- The coverage rule's quarter-width threshold is argued from the half-height
  definition of the sharp width, not measured. The direct check would be to
  render a stack with a planted run of one-shot planes and compare detail in
  the band. The owner may prefer the stricter width / 5 knee, which would
  warn on shorter runs.
- Whether to retake shift-pattern failures by default remains the engine's
  question (g-flight). By hand they can now be retaken.
- Merge: `FlightInputs` and its test literal also change in lane h-proof.
  `canvas` is edited only after the proof's caption.
