# Capture calibration: implementation log

**Spec:** [capture calibration](../../docs/proposals/2026-11-capture-calibration-spec.md),
decided 2026-11-27. **Ledger:** section "Capture calibration (2026-11-27)" of
[the milestone ledger](../../docs/agents/milestone-ledger.md).
**Base:** `origin/main` at `45d2b552b` (the spec's own commit on `b2c8a07aa`).

Labels as in `AGENTS.md`. Private-corpus gates ran on the owner's machine against captures in
`D:/StrehlCaptures`, each arm with a private `STREHL_CACHE_DIR`; nothing was written into a
capture folder. Builds: release `strehl` from this tree (`strehl 0.1.0-alpha.6`), the base
arm the clean `b2c8a07aa` build. One RTX 5090, 32 threads; nothing else rendering.

## F1. Highlight groups reach the picture (`cpf-f1-highlights`)

### What changed

| Spec 5.7 | Where | What |
| --- | --- | --- |
| 1. The ratio | `strehl-cli/src/exposure-ratio.rs` (new), `highlight-fusion.rs` `fit_pair`, `survey-cmd.rs` `measure_ratio` | One estimator for `strehl survey` and the fusion: 8-photosite cells, the longer exposure between 5 % and 70 % of its range with nothing pinned, the shorter 10 standard errors above black, the median of the ratio. The fusion reads the companion through its placement. Checks: within 0.25 EV of the start; two interleaved halves within 1 %; the hand-over sites within 3 % when there are 400 and the companion is its own plane's |
| 2. No cells | `fit_pair` | The commanded ratio, when the pair's own hand-over sites confirm it within 3 % (see deviations) |
| 3. The texture test | `fit_pair` | Removed, with the 64-photosite patch fit. Motion: the companion's measured shift is refused over 2 photosites |
| 4. The highlight group's check | `pixel-shift-cmd.rs` `judge_highlight`, `WITNESS_SIGNAL_FLOOR`; `GROUP_CHECK_VERSION` 4 | A witness with under 1,000 measured tiles does not demote a highlight group on its local or pair test. The witness now reports `local_tiles`, so the journal version is bumped |
| 5. Tone | `strehl-core/src/color.rs` `Render::unfused_ceiling`; `tone-subject.rs` `near_pin` | In a fused render a site is set aside where the base exposure would have pinned it, not where the fused data pins |
| 6. Say it | `ui-progress.rs` `highlights`, `highlight-fusion.rs` `report_use`; `strehl-ui` `pipeline.rs` `HighlightUse`, `app-station-stack.rs` | `STREHL_UI_PROGRESS event=highlights planes= used= reason=`; the Stack station's checks gain "Highlight groups · Used on N of M planes", marked for a look when any went unused |

### Gates

Commands: `f1/gates.sh` (identity, the other tiered captures, planted ratios), and the
dragonfly render below. Evidence: `f1/evidence/`.

| Gate | Result | Label |
| --- | --- | --- |
| Dragonfly `stack-1795713444768-14989` uses its highlight groups | 151 of 151 planes fused (base build: 0 of 151); ratio 49.64 to 51.33 (commanded 50.8); 4 highlight groups demoted on their own check (prototype of 2026-11-27: 73); 0 sites with a pinned sample in their footprint left unreplaced | MEASURED |
| Tone white within 5 % of the unfused render | 0.69435 against the base build's 0.67335: +3.1 % | MEASURED |
| No highlight groups: byte-identical | weevil `stack-1795460665629-8651` and `stack-1795082306428-20449`: TIFF SHA-256 identical, base against new | VERIFIED |
| The other tiered captures on this machine | `stack-1795583186775-12502` 8 of 8 fused (base 0 of 8); `stack-1795638138175-14989` 6 of 6 (base 3 of 6); `stack-1795640925619-14989` 5 of 5 (5 of 5); `stack-1795649995211-14989` 11 of 11 (11 of 11) | MEASURED |
| Planted ratio error 5 % | 151 of 151 fused | MEASURED |
| Planted ratio error 25 % | 0 of 151 fused: "a correction of -0.368 EV, beyond the 0.25 EV bound" | MEASURED |
| Checks row on unusable groups | planted factor 2: `event=highlights planes=151 used=0 reason=...`; the desktop parses it to "Used on 0 of 151 planes; plane not fused: ..." with the look mark (unit test `the_highlight_groups_use_is_reported_for_the_checks`) | VERIFIED (parse) |
| Unit tests | `exposure_ratio` (4), `a_highlight_group_short_of_signal_is_not_demoted_on_its_witness`, the measurement digest at version 4, the desktop parse | VERIFIED |

The X4 fixtures named in the spec's F1 gate (the rig's every-1 and every-2 captures and the
three-plane fixture) are no longer on disk; the four tiered captures above stand in for
them. The weevil is a non-tiered capture and is the identity gate.

### Cost

Dragonfly, warm cache, GPU fold, default render: 31 s for the base build (which fused
nothing) against 38 s (the render's own line: 23.0 s against 29.3 s). The fusion's summed
work was 37.3 s over its threads; the new ratio step is 2.6 s of it over 216 frame
preparations, at most 0.11 s a pair (`seconds_load_shift_bright_ratio_sites_gather`).
MEASURED. The extra time is the fusion now doing its work, not the ratio.

### Deviations from the spec, with the measurement behind each

- **The hand-over check gates only a companion of the same plane.** On the dragonfly every
  second plane borrows its neighbour's highlight group, taken 8 focus units away. Own-plane
  pairs read 0.990 to 1.002 at the hand-over sites (117 pairs), borrowed pairs 0.971 to
  1.019 (96), and the two the 3 % limit refused were borrowed pairs whose cell ratios agreed
  between halves within 0.11 %. Near highlights a change of focus moves those sites more
  than the ratio does. MEASURED.
- **Motion is refused over 2 photosites, not 1.** The measured shift between a highlight
  group and its base group was 0.21 median and 0.83 largest over 213 pairs on a rig whose
  four-shot members are 0.14 to 0.50 px apart. The placement includes the shift; the guard
  is for gross motion. MEASURED.
- **No cells: the pair's own hand-over sites confirm the commanded ratio**, rather than "the
  capture's other pairs agree". A check across pairs depends on the order in which planes
  are prepared, which would make a render's bytes depend on scheduling. No capture on this
  machine reaches this path. ARGUED.
- **Tone sets aside where the base exposure pins** (`PIN_NEAR` of the base ceiling), not
  every site the fusion blended. Setting aside everything from the blend's start (0.75 of
  the pin) put white at 0.56208, 16 % under the unfused render; sites in the blend hold
  values the base exposure measured itself. MEASURED.
- **Not built: the same sentence in the capture flight's Captured panel.** The Stack station
  shows the row; the flight panel does not see the stack's progress, and carrying it there
  is desktop plumbing left for S2.

## F2. Bounds from contrast (`cpf-f2-bounds`)

### What changed

| Spec | Where | What |
| --- | --- | --- |
| 5.1, C1 | `strehl-core/src/focus-contrast.rs` (new) | `tiles`: block contrast `(l - n) / (L^2 + L0^2)` with the injected noise model, the 7 x 7 block neighbourhood's level and an 8 read-noise floor, the 75th percentile of a 64 px tile's 16 blocks. `range`, `tile_focus`, `widen` |
| 5.2, C2 | `strehl-cli/src/depth-contrast.rs` (new) | The green site plane, the subject's tiles (at least half inside the outline), the range with `in_focus_first/last`, `reaches_first/last`, `per_position`, `suggested_start/end`, and `maps` (per-tile focus) |
| C2 | `survey-cmd.rs` | `depth` gains the fields above from contrast over every long frame; the earlier `first/last/core_*` stay, `first_plane/last_plane` become nullable; `suggested_start/end` now follow 5.2; `maps`; the summary says "in focus from A to B" and "still in focus at the first/last frame" |
| C2 | `subject-cmd.rs` | The same from the planes used (one decode: `run_evidence` returns their tiles); top-level `in_focus` and `maps`; `bounds` follow the range (a reached side keeps the run's end) |
| C3 | `focus-step-cmd.rs`, `survey-cmd.rs` | `span_widths` and `width_low`: the planes' span in widths, low under 4 |
| UI | `strehl-ui/src/capture-plan.rs` `in_focus_line` | The Depth step's line from the calibration survey: "In focus from A to B · the marks fit it", "N planes outside A to B hold nothing in focus, T" with **Use**, "the marks leave part of it out", or "Still in focus at the survey's last frame, X: the subject may go on" |

### Gates

Command: `python f2/gates.py <strehl> <out> [--frames 2]` (`strehl subject` with every plane
and with 13, on the spec's eight stacks). Evidence: `f2/evidence/`.

| Gate | Result | Label |
| --- | --- | --- |
| Unit tests of C1 | dim texture against a blurred bright disc (the disc under 0.2 of the texture), a blurred bright edge on black (no tile passes), flat frames (nothing), a gain of 1.25 (contrast within 5 %), the range and its reaches, the widening | VERIFIED |
| The eight stacks, 13 planes | all eight within one spacing of the reference, `reaches_` as the table | MEASURED |
| The eight stacks, every plane | six within one spacing; scarab `stack-1795300522964-6430` first 31,111 (reference 31,125) and pale scales `stack-1795371396674-6430` first 15,843 (15,833): two planes, 10 to 14 units, a third of a sharp depth | MEASURED |
| The failing input | today's build: the dragonfly's bounds 32,034 to 33,290 (grounding R1); this build: in focus 32,374 to 33,174, suggested 32,349 to 33,199 from `strehl survey` | MEASURED |
| `strehl survey`'s other blocks | identical on the dragonfly stack (every key but `depth`, `maps`, `summary`); `step` gains two keys | VERIFIED |

The two-plane differences are the port's: the reference fitted its noise per stack and used
its own subject mask; this reads the injected model and `strehl subject`'s outline. The gate
passes at two planes (`--frames 2`). ARGUED that the difference is immaterial at a third of
a sharp depth; not tuned away.

### Cost

`strehl survey` on the dragonfly stack (151 long frames): 21.6 s against 15.9 s, for 151
more decodes and their contrast. A calibration survey has about 25 long frames. MEASURED.

## S1, S2 and F3, first part: the pass, the column, the Depth lens (`cpf-s1-sweep`, `cpf-s2-pass`, `cpf-f3-light`)

### What changed

| Spec | Where | What |
| --- | --- | --- |
| 4.1, 5.3 | `strehl-ui/src/capture-sweep.rs` (new) | The live sweep: the window (33 positions, 3,000 units each side of the seed, inside the lens's ends, approached from below), the second fresh preview after each move measured off the UI thread, the tile measure `E / (Lnear^2 + 0.03^2)` on 32 px tiles, the peak rule (smoothed over 40 units, 3 times the 15th percentile, not at an end, parabola vertex), coherence within two sharp depths of the 3 x 3 median, the offset, range, busiest position and the end test |
| 4 | `strehl-ui/src/capture-measure.rs` (new), `capture-workspace.rs` `poll_pass` | The pass: Sweep, Light (switched on if off; waits until on 150 s as this desktop saw it), Test (a two-shutter pair at the busiest position read by `strehl survey`; its body top sets the survey's long shutter), Survey (the grid of 4.2 and the cluster), Return (lens to the busiest position, the camera's ISO and shutter as before). The test and the survey run on the existing survey machinery, so one-RAW switching, deletion and restoring four-shot are unchanged |
| 6.4 | `capture-plan.rs` | The column: 1 Rig, 2 Calibrate, 3 Depth, 4 Exposure, Run (no numeral). Calibrate: the button; while running the stage in words, a ruled progress line with a tick a stage, Stop; the readout a row at a time (In focus, Outline, Sharp depth, Body, Highlights) with each source. Depth's "Calibrate step" button is gone; the host's half-height line speaks only before a calibration has measured the range |
| 6.1, 6.2 | `capture-live.rs` | The Depth lens: one cached mesh of the measurement's own tiles (from RAW once the survey is read, else from the sweep), a hairline of picture between them, 62 % opacity, one ramp; tiles with no peak clear; hover reads "in focus at N"; once the lens leaves the position the pass left it at, tiles not within half a sharp depth of it dim ("in focus now"), rebuilt only when the position changes. A ruled legend with the ramp, its ends, the lens position and the source |
| C8 | `agent-interface.rs`, `app-agent.rs`, `docs/desktop-control.md` | `calibrate`, `stop_calibration`; `capture.tools.calibration.pass` in snapshots. `calibrate_step` stays |
| Fixtures | `capture-fixture.rs`, `capture-station.rs` | `plan+calibrated`, `plan+calibrating` (a fixture's pass never advances) |

### Gates

| Gate | Result | Label |
| --- | --- | --- |
| S1 rig gate, replayed: the sweep's range against the stack's in-focus range (32,374 to 33,174): far end within one sharp depth, near end within two and a half | The owner's sweep of 2026-11-27 replayed from its saved previews through this code (`the_recorded_dragonfly_sweep_finds_its_range`, `STREHL_SWEEP_FRAMES`): wide sweep (33 positions, 29,500 to 35,580) 32,331 to 33,150; dense sweep (77 positions) 32,369 to 33,149; no end flagged | MEASURED (replay, not a live rig run) |
| Planted sweeps | two depths come back as two populations; a stray peak unlike its neighbours is dropped; a flat scene finds nothing; a subject just past the window's end is flagged; the measure is the same at twice the brightness | VERIFIED |
| The end test | First version flagged the real dragonfly sweep as running off its far end (16 of 450 prominent tiles peaked there, 2,400 units past the subject, as strays). An end-peaking tile now counts only with three such neighbours: 0 flagged on both real sweeps, and the planted subject past the end still is | MEASURED |
| Survey grid and shutters | The dragonfly's range gives 24 grid positions (32,220 to 33,255), 13 shorts and the cluster 9 apart around the busiest position; a camera left at 1/40 s with a test top of 0.0148 and one at 1.3 s with 0.77 both choose 1 s for the survey (unit tests) | VERIFIED (arithmetic) |
| Desktop suite | 1,583 passed, 0 failed | VERIFIED |
| Offscreen | `plan+calibrated` and `plan+calibrating` at 1680 x 1050 rendered and read (renders kept in scratch) | VERIFIED |

### Not yet done, in this part

- **No live rig run.** The owner's desktop holds the receiver; a second desktop was not
  started against the host. The pass's first run on the rig is the owner's, or the next
  session's with the owner's go-ahead.
- **Frame time** of the live view with the Depth lens on is not measured (S1's last gate).
- S3's other lenses (Cover, Light, Glints), the core sample and the rail's hover
  isolation; S4 (the proof plane, Still); S5 (memory): not built yet. Per-value lamps
  ("the calibration gives 10 · Use" under a held value) are not drawn; the readout's
  Plan row says what was set and what was kept.

## S2 rule 2 and S3's rail bars

- **Measured, or held** (`capture-measure.rs` `Held`, `fill`, `step_for`; the station's
  intent loop). Marking Start or End, choosing a step, an exposure, an advice row or a
  highlight plan by hand holds that value until "New capture". When a pass finishes,
  what is not held takes the calibration's value, one command a frame once the camera
  is ready: Start and End from `suggested_start/end` (a side the subject reaches keeps
  the marks), the coarsest step keeping 99 % of the detail by the measured retention
  curve, the suggested exposure (with its highlight groups). The readout's Plan row says
  what was set and what was kept. Unit-tested (`a_pass_fills_only_what_the_owner_has_not_set`,
  `the_step_keeps_ninety_nine_percent`). VERIFIED (unit), not run on the rig.
- **The rail's bars** (`capture-workspace.rs` `rail_samples`): once calibrated, the
  subject's tiles in focus by frame from the survey, else the live sweep's kept peaks
  counted per sweep position, captioned with their source; the host's half-height
  bounds are no longer offered on the rail. The rail interpolates between frames, so
  a bar can lean one survey spacing past the range. Rendered in `plan+calibrated`.
  Desktop suite 1,585 passed.
- The survey's RAWs are still deleted once read (decision 2 says keep them until Start).

## Live on the rig, and the rest of S3, S4 and S5 (2026-11-27, afternoon)

The owner opened the rig for live runs. The RAW receiver was the only Strehl process
running; it was stopped, each package copied over the install
(`%LOCALAPPDATA%\Programs\Strehl`) and the receiver started again
(`rig/deploy.ps1`). A desktop window was launched through the control helper with a
scratch catalog and driven by `rig/drive.py` (`open_capture`, `calibrate`, snapshots);
the bench helper powered and connected the camera. Subject: the dragonfly of
2026-11-26, whose stack reads in focus 32,374 to 33,174 by F2.

### Three runs

| Run | Build | What happened |
| --- | --- | --- |
| 1 | `desktop-11bbfc38cb2219da` | Light switched on just before. Sweep 33 positions in 37.5 s: range 31,627 to 33,203, busiest 32,730. Light wait, test pair (body top 0.49 at 1.3 s: survey at 1.3 s and 1/25 s), survey of 88 long frames: in focus **32,392 to 33,112**. Stuck in Return: the exposure and the lens move were sent in one frame; the host applied the first and dropped the second. Fixed (one command at a time, a dropped move sent again) |
| 2 | `desktop-d982743fcb893b3d` | Lens left at 35,662: the sweep seeded from the plan's held range (fix of this afternoon). Sweep 35.2 s: 31,444 to 33,128. The new kept-peaks histogram showed why the near end was early: one tile alone at 31,349, one at 32,099; the rest from 32,287. Survey in focus **32,389 to 33,154**; the pass finished in 478 s and set the plan: Start and End 32,363 to 33,180, the suggested exposure (1 s with highlight groups at 1/60 s), step 8. The proof did not start: its request met the fill's last one still in flight and it gave up. Fixed (retries every 2 s, ten times) |
| 3 | `desktop-9eb18e5c95a523cd` | Seeded from the marks run 2 set. Sweep 37.8 s: **32,407 to 33,157** (near end 33 units from the stack's range, far end 17: S1's rig gate, within 120 and 48). Test top 0.37 at 1 s: survey at 1.3 s and 1/25 s; in focus **32,407 to 33,127**, sharp depth 52. The pass measured the lens's coarse-to-fine offset itself, **+29.8 units** (the grounding's hand measurement: +27), and stored it with the depth for the 32,000 position. The proof plane followed on its own (22.2 s): the capture's gate kept it, the checker demoted it (local 0.29 px against 0.51). "Prove five times" took 123 s: **1 of 5 groups clean, 3 would be retaken** (local 0.57 to 0.70 px), 22.3 s a plane. The rig's stillness, as in the grounding (7 of 26 clean last night) |

A peak alone (no neighbours with peaks) passed the coherence test, its own
neighbourhood's median being itself. A kept peak now needs two neighbours with peaks,
and an end of the range needs two other peaks within two sharp depths. Replays of the
three recorded sweeps are unchanged by it (32,331 / 32,369 / 32,302 near ends). A
warm sweep recorded with the grounding's method between runs 1 and 2 replays to
32,302 to 33,140. MEASURED.

The light wait counts from when this desktop first saw the light on: a desktop started
with the light already on for half an hour still waits 150 s, since the host does not
say when its outlet switched on.

### Built

- **Cover, Light, Glints, Still** lenses (`capture-live.rs`): one switch with Depth;
  Light and Glints read the survey's new per-tile `maps.level` and `maps.glint`
  (`depth-contrast.rs` `tile_levels`; `survey-cmd.rs`) scaled to the chosen exposure;
  Glints outlines tiles the highlight groups hold and fills those that pin anyway;
  Still draws the last proof plane's per-tile disagreement against the retake limit.
  Each draws as one cached mesh with a ruled legend in words. Fixtures
  `plan+lens-cover|light|glints|still`.
- **Rail hover** isolates the Depth lens at the hovered position (spec 6.2).
- **The proof plane** (S4, `capture-measure.rs` `Proof`, `ProofResult`; workspace
  `prove`, `poll_proof`): a test run of the base group at the busiest position as the
  plan stands, the highlight group's after it, the base group checked by `strehl
  pixel-shift`, the runs deleted once read; one after every pass, "Prove five times"
  in the Exposure step and `prove {count}` in the control interface; the readout's
  Proof row and the Still lens.
- **Lens memory** (S5, `LensMemory`, `measured_offset`): after each survey, the sharp
  depth and the coarse-to-fine offset the pass measured (RAW focus less the sweep's
  peak, median over shared tiles) are kept by focus position to the nearest 2,000 units
  in `capture-lens-memory.json` beside `capture.json`, and seed the next pass there.
- **Frame time** (`benchmark_depth_lens_frame_time`, release, CPU paint and
  tessellation, best of six rounds of 60 frames): live view alone 0.022 ms, Depth lens
  on 14,652 RAW tiles 0.094 ms, the lens moving every frame (mesh rebuilt each frame)
  0.31 ms. MEASURED.

Afterwards the camera and the light were switched off (the host cuts the camera's
power only while connected, to confirm standby first). The plan the host holds is the
calibration's of run 3 (marks, step, exposure and highlight groups): that is what the
pass does; set them by hand to keep others. The owner's install is updated to the final
build of this work (below); `capture-lens-memory.json` beside `capture.json` keeps
run 3's measurement for the 32,000 position.

### Still not built

- The core sample (click a tile: its three nearest survey frames at 100 %). It needs the
  survey's RAWs kept until Start (decision 2); they are still deleted once read, so
  neither is built.
- Per-value lamps beside the Depth and Exposure fields; the readout's Plan row says
  what the pass set and kept.
- "Run the rest" and "Search further" actions after a stopped or past-the-end pass;
  the stop and the messages are there.
- Memory by catalog subject (its last calibration and plan); staleness marks on facts
  whose conditions changed.
- The highlight sentence in the capture flight's Captured panel.
- The light wait cannot know a light switched on before the desktop started.

