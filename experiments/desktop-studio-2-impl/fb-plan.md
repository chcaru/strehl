# Capture plan: owner feedback on settings, guidance and scheduling (Studio 2)

**Date:** 2026-11-21. **Branch:** `studio2/fb-plan`, from `ef98da086`.
**Scope:** the Capture plan inspector and its windows (the owner's three
requests below). The live view, depth rail and histogram are another lane's
(`studio2/fb-live`); the Library is a third.
**Host crate:** unchanged. Nothing here needs a Pi redeploy: every control
sends a command the deployed controller already accepts (`settings`,
`set_warmup`, `power_plan`, `error_correction`, `apply_bounds`,
`schedule_stack`, `cancel_schedule`).
**Labels:** MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED.

## The requests and what answers them

| Owner's words | Built |
| --- | --- |
| "where do i configure approach units, warmup time, etc.?" | The Rig step shows the settings at a glance ("Approach 128 · settle 500 ms · warm-up 5 s") and **Settings** opens them in place: approach, settle, exposure timeout, light warm-up (number field, steppers along a ladder, typing), manage power, error correction, each with what it does and its default; links to the rig popover (light and camera power) and to connection and storage. |
| "more information and guidance as to what the optimal settings are across ISO, exposure, start, end, step size (where can this be manually changed?), and settle ... how the options would likely impact the resulting image" | One guidance line per step (exposure suggestion with **Apply**; bounds against the survey with **Use the survey's**; the step's knee), a typed-step row in the step table, settle choices with their cost and measured passes, and **What changes**: a comparison panel (ISO and exposure, step, settle, light warm-up) with noise, SNR, highlights, detail kept, planes, RAWs, time, end and disk, every source labelled. |
| "the Schedule overlay isn't great ... title duplicated ... datetime picker ... local time ... hr/mm from now, with a nice picker" | One modal titled once ("Schedule this stack"). **At a time**: a month calendar and hour and minute wheels (click, scroll, drag, arrow keys). **In a while**: chips +15 m, +30 m, +1 h, +2 h, +4 h, +8 h and hours and minutes wheels. Both show the local start with its UTC offset, how far away it is, and the estimated end. An armed schedule shows in the footer ("Scheduled · Today · 14:35") and the dialog then shows and cancels it. |

## Files

| File | What |
| --- | --- |
| `crates/strehl-ui/src/capture-guide.rs` (new) | Guidance arithmetic (exposure advice and rows, detail kept, settle and warm-up rows, bounds line, step line) and the **What changes** panel with its ruled table. Tests in `capture-guide-tests.rs`. |
| `crates/strehl-ui/src/capture-rig-settings.rs` (new) | Specs (range, default, ladder, line), validation by the host's rules, the values read from the host, the inline editor, the drawn stepper. Tests in `capture-rig-settings-tests.rs`. |
| `crates/strehl-ui/src/capture-schedule.rs` (rewritten) | Local-time resolution, labels, the dialog (calendar, wheels, chips, outlet actions, armed view), the footer label, the stack's timing. Tests in `capture-schedule-tests.rs` (the old inline test is replaced). |
| `crates/strehl-ui/src/capture-plan.rs` | New intents (`SetApproach`, `SetCaptureTimeout`, `SetWarmup`, `UseSurveyBounds`, `OpenGuide`), the Rig step's settings, guidance lines, the typed-step row, the settle menu, `stack_seconds_at`, `step_row`, `parse_step`, `marked_planes`, `consume_enter`, the footer's schedule state; `DETAIL_LIMIT` is now the measured knee (width / 5). |
| `crates/strehl-ui/src/capture-station.rs` (small) | The test shot's exposure into the view; the panel drawn left of the inspector; the dialog without its outer window; `send_plan` for approach and timeout; the new intents; station and rail keys off while the dialog is open; fixture panels. |
| `crates/strehl-ui/src/capture-workspace.rs` (small) | Module declarations; the exposure a test shot was taken at. |
| `crates/strehl-ui/src/capture-fixture.rs`, `main.rs` (small) | The plan fixture's shutter list in thirds from 1/25 s to 1 s and a test RAW at 24 % (so it shows a suggestion); `--capture-fixture` values `plan+rig`, `plan+guide`, `plan+guide-step`, `plan+guide-settle`, `plan+guide-light`, `plan+schedule` and `plan+schedule-in`. |
| `experiments/desktop-studio-2-impl/visual-check.py` | Routes for those fixtures in three themes. |
| `docs/native-capture.md` | The desktop's rig settings, What changes and schedule dialog. |

## Decisions

- **Rig settings in the plan, not the shell's popover.** The owner looks for them on the
  Capture screen; the popover stays for power and connection and is linked from the settings.
  Settle appears in both the settings and the Depth step (one value, one command).
- **Every value is the host's.** The settings show the host's plan and power state; a typed value
  is judged by `Plan::validate` (approach 1-4096 units and the lens limit before the start mark,
  settle 100-30000 ms, timeout 5-3600 s) and the schedule store's 0-300 s warm-up, and refused with
  the range before anything is sent. Approach and timeout go out as `settings` with the draft's step
  and settle, as the step and settle edits already did.
- **Exposure suggestion:** base ISO (the lowest fixed ISO offered) and the longest offered exposure
  whose test-RAW brightest 0.1 % (99.9th percentile), scaled by ISO x exposure, stays at or under
  90 % of full scale (about 0.15 stop of room). A test RAW with more than 0.01 % of samples at white
  counts as clipped and only shorter settings are suggested. The test shot's exposure is now
  remembered when it is sent, because the RAW reports ISO but the decoder does not report the
  shutter.
- **Exposure rows:** the options nearest whole stops from now, reaching a stop past the suggestion,
  plus now and the suggestion; at most seven. Rows are clickable (Exposure command).
- **Detail kept:** linear in overlap (sharp width / step) between the measured steps of the two
  stacks, the lower of the two shown, "<82 %" past what either measured. The step table's warning
  mark moved from width / 3.6 (`focus-step`'s EDGE) to width / 5, the knee the later step-curve runs
  found.
- **What changes** is a panel over the canvas, left of the inspector and below the pre-flight strip,
  not part of the inspector, so the default view stays short; Escape or Close shuts it.
- **Schedule:** a modal (blocks the rest of the station), Sunday-first calendar, past days not
  offered, minutes in fives, "in a while" up to 72 h, starts at least 60 s away. Times are resolved
  through the PC's zone: a skipped local time is refused with a sentence, a repeated one takes the
  first and says so. The zone is shown as its UTC offset at the chosen date (a zone name would need
  another Windows API feature in `Cargo.toml`; not added).
- **Enter in a field is the field's.** Typing a step, a rig value or a subject name and pressing
  Enter used to fall through to the station's Enter, Start stack. Those fields now take it.
- **ASCII minus.** The UI face draws U+2212 on the baseline (it looks like "_"); signed numbers and
  offsets use "-" and the steppers are drawn. The depth rail's jog buttons ("−128") show the same
  glyph problem; that file is the live lane's.

## Where every guidance number comes from

All from `experiments/capture-implementation-2026-11-20/results.md` and its `evidence/`, or from the
host's code, checked against those files on 2026-11-21.

| Shown | Number | Source | Label |
| --- | --- | --- | --- |
| Noise follows exposure, not ISO | final-image SNR 67.7 (0.6 s), 48.1 (1/3), 32.4 (1/6), 27.2 (1/10), 15.4 (1/25); 1/25 s ISO 100 pushed four stops 12.1 against ISO 1600 11.0 | follow-up table; `exposure-quality.txt` | MEASURED; the square-root formula DERIVED (a test holds it within 15 % of each measured SNR) |
| SNR and noise columns | 10 log10(t / now) dB; -0.5 log2(t / now) stops | from the above | DERIVED, shown as estimates |
| Plane and stack time | `strehl_capture::timing::initial_plane` and `initial_setup`, plus the managed warm-up | host code (its floor: four-shot 4.29-4.44 s below 1/6 s) | the host's estimate; floor MEASURED (`exposure-floor.txt`) |
| Wi-Fi and RAW size | 63 of 69 MB/s at 1/25 s ISO 1600; 67.3 MB a RAW against 47.5 MB at ISO 100 | results.md; `exposure-floor.txt` | MEASURED |
| Highlights | test RAW p99.9 x (ISO x t) / (ISO0 x t0); suggestion at 90 % | RAW linearity | DERIVED; target ARGUED; not rig-tested |
| Detail kept | scarab (width 113) p10 detail 1.000, 0.990, 0.988, 0.946, 0.895, 0.863, 0.818 at steps 8, 16, 24, 32, 48, 64, 96; dark (width 88) 1.000, 0.989, 0.983, 0.982, 0.962 at 8-48 | `step-curve-scarab4.txt`, `step-curve-dark4.txt` (1.5 px rows) | MEASURED; interpolation DERIVED; another subject UNVERIFIED |
| Knee width / 5 | scarab 24 kept what 16 kept, 32 lost 5 % | step-curve table | MEASURED on two stacks; as a rule ARGUED |
| Finer steps, no less noise | flat-tile energy -21 to +19 % step to step, no direction | step-curve text | MEASURED |
| Settle passes | 500 ms 48 of 48 with the 2 s first plane (`ab-settle-first-plane.txt`), 45 of 48 before; 1000 ms 45 of 48; 2000 ms 48 of 48; walking 13 of 24 and 20 of 24 | K4 table and evidence | MEASURED (all but the first 500 ms row before the first-plane rule, marked †) |
| Plane periods by settle | 5.66-5.69, 6.00-6.02, 7.03-7.05 s | K4 table | MEASURED |
| First plane settles 2 s | `AFTER_APPROACH_MS = 2000` | `crates/strehl-capture/src/worker.rs` | VERIFIED in code (mirrored as `FIRST_PLANE_SETTLE_MS`, private there) |
| Retake cost | about 8.5 s | K3 | MEASURED |
| Light warm-up | dimmed 9 % over the first 60 s, 6 % over the next run; later -6 to +4 % | "The light" | MEASURED; effect on the stacked image ARGUED/UNVERIFIED |
| Survey margin | "two survey intervals of margin" | `bounds.rs` explanation | VERIFIED in code |
| Ranges and defaults | approach 128 (1-4096), settle 500 (100-30000), timeout 120 (5-3600), warm-up 5 (0-300) | `Plan::default`, `Plan::validate`, `default_warmup`, `Store::set_warmup` | VERIFIED by a test against those functions |

## Commands and results

Worktree `C:\w\f-plan`, Windows 11, `CARGO_BUILD_JOBS=8`, other agents building in their own
worktrees at the same time.

| Command | Result |
| --- | --- |
| `cargo test --locked -p strehl-ui` | MEASURED: Compiling strehl-ui; 1415 passed, 0 failed, 32 ignored |
| `cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings` | MEASURED: Checking strehl-ui; exit 0 |
| `cargo fmt -p strehl-ui -- --check` | MEASURED: exit 0 |
| Placebo: `consume_enter` reading Enter without taking it, `enter_in_a_field_is_not_start` | MEASURED: the test fails (the station would see Enter); restored, passes |
| `visual-check.py --exe target/release/strehl-ui.exe` with the plan, rig, guide (four sections), schedule (both modes), flight and glance routes in Graphite, Instrument and Lightbox, at 1680 x 1050 and 1280 x 800 | VERIFIED by eye: nothing clipped or overlapping; square, ruled; the dialog's title once; flight and glance unchanged. Renders in `C:\strehl-scratch\f-plan\shots` (not committed) |
| `cargo test --locked --release -p strehl-ui capture_station_pointer_sweeps -- --ignored --nocapture`, its fixture list widened for this run only (reverted, not committed) | MEASURED (release, whole shell and station, paint and tessellation, 6 sweeps of 80 frames, host shared with other agents' builds): plan 0.170-0.174 ms/frame (9,392 vertices); with the settings open 0.189-0.196 (10,482); What changes on ISO and exposure 0.214-0.217 (14,124), on Step 0.202-0.210 (14,060); the schedule dialog 0.206-0.225 (11,676); flight 0.111-0.112 (6,306). P6's recorded plan was 0.156-0.164 ms/frame (8,644 vertices) in another session, so the plan's added lines cost about a tenth of that (not a same-session comparison) |
| `pointer_motion_over_the_station_rebuilds_nothing` (in the suite) | MEASURED: passes; no rail rebuild or live-view upload on pointer motion |

Tests added (each fails if its rule is removed, ARGUED from the assertions except the placebo above):

- Guide: the square-root rule against the measured SNRs; base ISO; highlights scale with ISO and
  time, a clipped test speaks only for darker settings; the suggestion (longer, already best, at
  base ISO from ISO 400, shorter, too bright, clipped, no test shot) and the 90 % target; rows a stop
  apart with the host's own times; the line and its action; detail kept at the measured points and
  between them; rows marked at the knee; typed steps parsed and counted as `Plan::positions`;
  settle and warm-up rows; bounds against the survey (match, outside, beyond, at the search limit);
  numbers kept on the line of their unit; the panel's tables never overlapping at 1680 and 1100 px,
  a row click choosing, nothing chosen when not editable, Escape closing.
- Rig settings: every value judged exactly as `Plan::validate` and `Store::set_warmup` judge it
  (17 values each), the lens limit, units after numbers; ladders and defaults equal the host's; the
  values read and summarised; each setting's command on the wire (`settings` keeps step, settle,
  approach and timeout; `set_warmup`; `error_correction`; `power_plan`; `apply_bounds`); the editor:
  a stepper, a typed value on Enter, an out-of-range value refused with its range, the switches,
  error correction only with the checker, nothing past a 282 px column.
- Schedule: winter, summer, a skipped and a repeated hour in a rule-based Pacific zone; the PC's zone
  round-trips in every season; labels, spans, the default start; wheels wrap and minutes carry; the
  title drawn once; "+2 h" schedules two hours from now with the host's warm-up and every outlet
  action; a calendar day and a wheel click send that local time's Unix seconds; switching mode keeps
  the start; an armed schedule shows, cancels, and labels the footer.
- Plan: nothing past the inspector at 300, 348 and 440 px with the settings open; the settings open
  from the Rig step; Apply and What changes; a typed step previewed, chosen by link or Enter, digits
  only; Enter in a field is not Start.

## Not done, and open questions

- Nothing was tried on the rig (no Pi, camera or light was touched): the settings' commands, the
  warm-up and the schedule dialog against the live controller need a rig check; the highlight
  prediction from a test shot has not been compared with a second test shot at the suggested setting.
- The plan inspector is now about 60 px taller than the window at 1680 x 1050 with the default
  fixture: step 4's last switch and the connection link sit below the fold (the footer with Start
  stays fixed).
- The time zone is shown as an offset, not a name.
- The depth rail's "−128" jog labels have the same baseline-minus glyph (live lane's file).
- The milestone ledger row for this work is the orchestrator's to allocate.
