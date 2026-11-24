# Plan S4, engine side: what the subject drives

Ledger row `shd-s4-engine-2026-11-24`. Branch `studio2/shd-s4` from `7b786abae`.
Author-run, not independently reviewed. Labels: MEASURED, VERIFIED, DERIVED, ARGUED,
UNVERIFIED.

## What was built

- **Subject region** (`strehl_core::subject::SubjectRegion`, `subject-region.rs`): the
  outline rasterised at 8 px cells, grown by a margin; whether a rectangle of the active
  area touches it and its bounding box, in the geometry of any plane (scaled about the
  centre by `plane_scale`, the evidence's convention).
- **Loading** (`strehl-cli/src/subject-use.rs`): `--subject <file>` reads a manifest's
  `plan.subject` or the JSON `strehl subject --out` writes; without it, the capture's own
  `manifest.json` `plan.subject` is used when present. Margin: half a 64 px tile.
- **`focus-step --subject`**: the width, its 10th/90th percentiles and the step are over
  the tiles touching the subject, each judged in the geometry of the plane where it is
  sharpest; the whole frame's figures are kept in `whole_frame`.
- **Plane checker** (`pixel-shift --subject`, `follow --subject`, manifest default):
  the stack's own measurement decides what is assembled, unchanged. When it demotes a
  group, it is judged again with the witness's local disagreement taken over the subject's
  tiles only (p99); every other gate reads what the stack read. A demotion that then
  passes is "backdrop only", no retake. Whole-group faults (a slipped shot, a misregistered
  pair, levels) keep the stack's retake. The members are also registered on the subject's
  bounding region and the offsets reported beside the stack's (`registration.agrees`), with
  no vote (see "Registration" below).
- **Bounds** (`strehl subject`, key `bounds`): the subject's first and last sharp focus
  plus half a sharp width each side, in the run's direction, rounded outward; the width
  from `--width`, else the run's `focus-step.json`, else 0. Also the same from the depth's
  central 99 % (`core`).
- **Sharp share and risk banner:** desktop only, nothing built (see the end).

## Gates

Commands: [run-base.ps1](run-base.ps1) (engine built at `7b786abae`) and
[run-new.ps1](run-new.ps1) (this branch: the same commands, then with outlines);
analysis [s4-gate.py](s4-gate.py) -> [evidence/gate.txt](evidence/gate.txt). Release
builds, private `STREHL_CACHE_DIR` per arm, outputs under `C:/w/shd-s4-out/`; capture
folders only read. Fixtures: weevil `stack-1795460665629-8651` (199 planes), scarab
`stack-1795300522964-6430` (211), close tile 1/4 s `stack-1795476520452-8651` (190 groups,
153 planes) and stopped 1 s `stack-1795478933629-8651` (95 groups, 24 planes). Outlines:
`strehl subject <run>` (13 planes, defaults) on each capture.

### Without a subject: identical (VERIFIED)

- `focus-step --json`, four captures: bytes identical, text identical.
- `pixel-shift --all-groups --json`, both close tiles (285 groups): bytes identical; text
  identical except the line naming the report's own path. The offsets, residuals and
  gains in it come through `Reference::new`, now `new_in` on the same central half: the
  refactor computes the same bits on every group.
- `follow` on the stopped 1 s tile (95 groups): plane journal identical with `seconds`
  removed; the render's group journal identical (95 records).
- `strehl subject --json`, weevil and scarab: identical except the added `bounds` key.
- Stack renders were not run: no render path reads the subject (the gather, `StackGroups`
  and the journal are untouched); the only change on that path is the `new_in` refactor
  above (VERIFIED in the code and by the identical offsets).

### Focus step, whole frame against the subject (MEASURED)

| Capture | Tiles touching the subject | Measured, whole / subject | Width, whole | Width, subject (p10 / p90) | Step |
| --- | --- | --- | --- | --- | --- |
| Weevil | 6,234 of 14,652 | 4,812 / 4,811 | 44.1 | 44.1 (33.8 / 58.1) | 6 / 6 |
| Scarab | 6,982 | 5,514 / 5,483 | 36.7 | 36.7 (22.2 / 51.1) | 5 / 5 |
| Close tile 1/4 s | 4,435 | 3,275 / 3,210 | 97.7 | 97.3 (64.1 / 131.6) | 13 / 13 |
| Close tile 1 s | 2,198 | 505 / 505 | 89.6 | 89.6 (48.8 / 117.5) | 12 / 12 |

The subject changes nothing on these four: tiles of a plain dark backdrop never peak six
times above their floor inside a run, so the whole-frame measure was already the
subject's. It will matter on a textured backdrop in focus (UNVERIFIED; no such capture).

### Plane checker on the close tiles (MEASURED)

| Capture | Groups | Demoted by the stack | Retakes without / with the subject | Backdrop only |
| --- | --- | --- | --- | --- |
| Stopped 1 s | 95 | 40 (all slips) | 40 / 40 | 0 |
| 1/4 s | 190 | 34 (27 slips, 1 pair, 6 local) | 34 / 34 | 0 |

No verdict changed; the stack's verdicts and reasons are those of the base engine. The
six local faults of the 1/4 s capture are on the subject: subject p99 equals the frame's
(0.517 to 0.757 px; plane 147 reads 0.757 px over 365 subject tiles, backdrop 0.388 px).
`follow --subject` on the 1 s capture gives the same retakes as without.

On a dark backdrop the subject arm cannot change a local verdict in practice: the backdrop
has almost no measured witness tiles. A 768 px patch moved 2 px on the backdrop of 1 s
plane 18 left the stack's p99 at 0.210 px (pass); on three of the four planted groups no
backdrop place had measured tiles at all
([plants with the real outline](evidence/plants-subject-outline.txt)).

**Planted faults** (VERIFIED on real groups,
`cargo test --release -p strehl-cli --lib planted_backdrop -- --ignored --nocapture`,
`STREHL_S4_FIXTURES`, 1/4 s planes 74 and 100, 1 s planes 10 and 18, shot 3 patch moved
2 px). To exercise the backdrop rule where witness tiles exist, the subject was given as a
box over part of the real subject (x 0 to 0.38, y 0.19 to 0.30, normalised), so the rest
of the insect stands in for a textured backdrop
([evidence](evidence/plants-box-outline.txt)):

- patch outside the box: the stack demotes (2.03 to 2.10 px); the box's tiles read 0.32 to
  0.45 px: **backdrop only, no retake** (three groups); on the fourth the patch dragged a
  shot's whole-frame fit onto the next photosite: a slip, retaken.
- patch inside the box: 2.24 to 2.41 px on the subject: **retake** (four groups).
- with the real outline: every subject plant retaken (two local, two slips).

### Registration on the subject's bounding region (MEASURED, reported only)

The subject-box offsets differ from the stack's central-half offsets by one photosite in one
member in 7 of 95 groups (1 s) and 3 of 190 (1/4 s), both ways:

- two stack slips (1 s planes 9 and 19) whose box offsets cover the four parities, with
  the subject's witness passing on them (0.29, 0.41 px);
- six groups the stack assembles (1 s planes 4, 8, 12; 1/4 s planes 69, 137, 142) whose
  box offsets do not cover the parities;
- two stack slips (1 s planes 5, 11) that stay slips.

Structure is 0.99 or more in every case, so this is not a weak fit: the integer offset of a
shot near half a photosite depends on where it is measured, as a sway that differs across
the frame would make it (the close tile sways about 0.5 px; ARGUED). An earlier cut of the
checker let the box registration vote: it called planes 9 and 19 "backdrop only" with no
retake, but the stack registers on the central half and would still fold them to one shot.
So the box registration is reported (`registration`, with `agrees`) and does not vote.
Registering the stack itself on the subject is a change to the gather's identity (the X4
work's lane); these ten groups say it would move verdicts both ways, and which offsets
render better is UNVERIFIED.

### Bounds (MEASURED)

Width from `focus-step --subject` (weevil 44.1, scarab 36.7 units).

| Capture, planes used | Depth (first-last; central 99 %) | Suggested start-end | Planes kept / saved | Core: kept / saved |
| --- | --- | --- | --- | --- |
| Weevil, all 199 | 5-164; 36-162 | 24487-25646 (run 24482-25866) | 166 / 33 (84 % of the range) | 133 / 66 (67 %) |
| Weevil, 13 | 17-182; 34-166 | 24571-25772 | 172 / 27 | 139 / 60 |
| Scarab, all 211 | 3-185; 25-180 | 31001-32313 (run 31006-32471) | 187 / 24 (90 %) | 160 / 51 (77 %) |
| Scarab, 13 | 1-193; 18-193 | 30987-32369 | 195 / 16 | 180 / 31 |

Against the results note (no part sharpest in the weevil's first 30 or last 35 of 199; the
scarab's first 9 and last 20 of 211, 24 % with the outermost 0.2 % left to the margin):

- The central-99 % range reproduces it: weevil 36-162 (note 34-162 at 99.8 %), a third of
  the capture saved; scarab 25-180, 24 % saved.
- The extremes do not at the start: a few cells make the weevil's first sharp plane 5 and
  the scarab's 3. The last planes agree (weevil 164 = 199 - 35; scarab 185, inside 191).
  `start`/`end` follow the plan's rule (first and last); `core` is the robust offer.
- With 13 planes the extremes sit one survey plane wide (the three-plane mean repeats the
  edge plane) and the scarab's reaches the run's first plane (`reaches_run_start`).
- The close tiles were bounded tightly by hand: depth fills both runs, 0 planes saved, and
  both ends flagged as reaching the run.

## Checks

- `cargo test --locked -p strehl-core --lib -- subject pixel_shift` (26 passed);
  `cargo test --locked -p strehl-cli --lib -- subject_use subject_cmd focus_step
  pixel_shift_cmd follow_cmd` (17 passed, 2 ignored: the plant tests, run in release as
  above).
- The gate binary was built before the last edits, which touched only comments and the
  ignored plant test (its slip case); the plant runs used the final code.
- New tests: `tiles_and_bounds_of_a_square`, `scale_maps_about_the_centre`,
  `an_empty_outline_touches_nothing` (core); `subjects_load_from_a_manifest_or_an_outline`,
  `backdrop_faults_ask_no_retake`, `registration_region_follows_the_subject`,
  `bounds_from_depth`, the ignored `planted_backdrop_and_subject_faults_on_real_groups`.
- `cargo clippy --locked -p strehl-cli` / `-p strehl-core --all-targets --no-deps -- -D
  warnings`: both fail on the base tree's findings; none in the code changed here (the one
  in `focus-step-cmd.rs`, `!(peak > ...)` in `half_width`, predates it). The lib's errors
  stop clippy before every test target is linted;
  `rustfmt --edition 2024 --check` clean on the files changed here.

## Not done

- No capture has `plan.subject` in its manifest yet: the manifest default is covered by
  the unit test only.
- The stack's own registration and assembly do not read the subject (see Registration).
- "Backdrop only" was verified with a box standing in for the subject; no real capture with
  a textured backdrop exists.
- Minutes saved by the bounds: the desktop's timing model.
- Sharp share and risk banner: desktop only. The share is
  `strehl-ui/src/capture-planes.rs` (`DeckSnapshot::sharp`, `DeckSnapshot::share`,
  `TryInfo::share`: preview focus maps on the deck's grid, a cell sharp when within `KEEP`
  of the most any try showed), drawn as the "Planes · sharp share" strip in
  `capture-plane-view.rs`. The coverage banner is `capture-flight.rs` (`risk_spans`,
  `risk_sentence`, `risk_banner`): runs of planes left to one shot against the sharp width,
  from the follow feed, with no cell share in it. The engine computes neither.
- The desktop's in-process plane view (`capture-planes.rs`, `measure_with_tiles` and
  `retake_helps`) is not weighted; `strehl_cli::subject_use::{check_subject, weigh}` are
  the calls to use.
