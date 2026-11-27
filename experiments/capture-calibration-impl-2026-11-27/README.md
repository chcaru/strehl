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
