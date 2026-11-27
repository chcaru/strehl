# Capture calibration: one button, then review

**Status:** Spec, for an implementing agent. Nothing here is built except where a section
says "exists".
**Date:** 2026-11-27.
**Replaces:** the design sections of
[the capture planning flow proposal](2026-11-capture-planning-flow.md) (its sections 3 to
10 and 16 to 17). That document stays as the record of how this one was reached; where
the two differ, this one holds.
**Evidence:** [grounding results](../../experiments/capture-planning-flow-2026-11-26/grounding/results.md),
measured 2026-11-27 on the owner's rig and on eight of their stacks. Section numbers given
as "R2.3" point there.
**Mockups:** [`experiments/capture-planning-flow-2026-11-26/mockups/`](../../experiments/capture-planning-flow-2026-11-26/mockups/README.md).
**Written against:** `origin/main` at `b2c8a07aa` (installed desktop
`desktop-91cc19f0619a9ac4`). Paths are under `crates/` unless they say otherwise.
**Stage labels** (F1 to F3, S1 to S6) are local to this plan; their milestone rows are
allocated (section 12).
**Decided:** 2026-11-27, the owner accepted the five assumptions of section 11 and
asked for the implementation.

Labels as in `AGENTS.md`: MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED.

---

## 1. What the owner asked for

In their words, 2026-11-26 and 27:

- "the flow of 2. Exposure -> 3. Depth doesn't seem to work cohesively and constructivly
  as is."
- "when i said 'automatic' originally, i was talking about the calibration process.
  pressing a single button and getting a full calibration run with the results. that would
  allow adjustment and confirmation before proceeding. still try to make that single
  calibration as auto-magic as possible."
- "the blur and highlights count as sharp when they're clearly visibly not."
- "i'm also not convinced the highlight feature is working well yet."
- "feel free to enrich the stage area with more diagnostic information/data from the
  calibration to help the reviewer process it … the ethos of the app so far has been
  'lenses' overlaying the stage area."
- "i want strehl to be driving the highest quality stack with the least effort at the
  highest performance possible."

So: **one button runs the whole calibration; its results fill the plan and are drawn on
the stage; the owner reviews, adjusts and starts.** The app never starts a capture on its
own decision.

---

## 2. What was measured, and what it changes

The first design argued from the code. This one stands on measurements. The ones that
shape it:

| # | Measured | Consequence here |
| --- | --- | --- |
| M1 | On the dragonfly the engine calls the subject in focus from the first plane to the last and offers bounds wider than the capture. It is in focus over 806 of the 1,200 units shot; 44 of 151 planes hold nothing (R1) | The depth rule is replaced (section 5.2). This is fix F2 and comes before any new screen |
| M2 | The cause is brightness: energy against noise ranks bright blur above dim detail. Energy against local brightness does not. One rule gives the in-focus range within a sharp depth on five subjects and correctly reports the three that run past their captures; a fresh survey of 26 RAWs shot the next night gives the dragonfly's range within 5 units of the stack's (R2, R4.1) | One focus measure, "contrast", for the survey, the plane checker and the lenses (5.1) |
| M3 | A 36 s live sweep of 33 positions over 6,080 units locates the dragonfly's range within 18 units, by the position of each tile's peak. The host's half-height rule on the same frames is 575 units too early and 1,090 too late (R2.4) | The range is found, not marked. No "Range" step. The sweep also yields a depth map in 36 s, which is the first lens |
| M4 | The dragonfly's highlight groups were captured correctly and not used: 0 of 151 planes fused; with fusion forced on, the default look goes black (R3) | Fixes F1 and F1b, first of all. A capture that takes frames the render silently drops is the worst fault found |
| M5 | The light's output falls 11 % in its first 140 s; a ratio measured then is up to 3 % off; the picture drifts 4 to 6 px in four minutes. A live sweep taken as the light came on reads the same as one taken warm (R4) | The pass does its live-view work first and its RAW exposure work after the light has been on 150 s |
| M6 | A camera just connected reports the last session's starting shutter (here the highlight groups' 1/40 s) and the lens is not where the subject is (R4) | The survey's shutters come from a test shot, never from the camera's state. The sweep's window comes from the remembered plan, or from the lens only after the owner has moved it |
| M7 | Pins are not local in depth on a subject whose highlights are 48 times over the pin; a highlight group's own check fails for want of signal; a group at 1/40 s fails the base check as often as one at 1.3 s (R3, R4) | Withdrawn from the earlier proposal: highlight groups "where the glints are", and "one stop shorter" as a cure for movement |
| M8 | The sharp depth differs by a third between subjects at one lens position, and a cluster shorter than four sharp depths reads it low (R5) | The dense cluster stays in every calibration and its spacing scales with the lens position's last known sharp depth |

---

## 3. The flow

```text
1 Rig          camera connected, light on                       (unchanged)
2 Calibrate    one button, about five minutes, unattended
3 Depth        Start, End, Step        filled by 2, adjustable
4 Exposure     ISO, shutter, groups    filled by 2, adjustable
  Run          check, retake, stack, power down                 (one row)
  Start
```

- There is no Range step. Before a calibration the Depth step holds today's Start and End
  marks and works as today.
- The Calibrate step is the only new control the owner must touch. Everything it measures
  can also be run alone from its opened form (rule 6 below).
- After a calibration the stage shows the Depth lens and the column shows steps 3 and 4
  open with the calibration's values. The owner looks, changes what they disagree with,
  and presses Start.

### Rules

An implementer who has to choose between two readings of this document picks the one that
keeps these.

1. **One button measures; the owner decides.** Nothing but the owner starts a capture.
2. **Measured, or held.** A value the owner has not set in this capture takes the
   calibration's value and carries the lamp. A value the owner set is never changed: its
   row shows what the calibration measured beside it, and one click takes that instead.
   "New capture" clears what was held.
3. **Evidence on the stage.** Every number the calibration fills has a lens that shows,
   on the subject, what it was read from (section 6).
4. **Measure the thing.** Focus is fine detail against its own brightness at a peak. A
   range is where peaks are. Neither is "energy above noise".
5. **One model, one adviser.** Every exposure suggestion comes from one function reading
   one model (section 5.6). No tool advises on its own.
6. **Every part can be run alone.** Sweep, test shot, survey, proof.
7. **A fact knows what it was taken under** and loses its lamp, alone, when that changes.
8. **Say what is not known.** Tiles with no peak are left uncoloured. "Still in focus at
   the last frame" is said in those words. There is no score and no adjective, as in the
   Stack station.
9. **The engine's noise model, injected.** No stage fits its own (`AGENTS.md`; R2.2 shows
   what a private fit does).

---

## 4. The calibration pass

One state machine in the desktop (`capture-measure.rs`, new) replaces `Calibration` in
`capture-tools.rs` and drives the host with commands it already has. No controller deploy
is needed for any of it.

| # | Stage | What it does | Uses | Time |
| --- | --- | --- | --- | --- |
| 1 | **Sweep** | 33 lens positions across a window, the preview read after each move. Per-tile peaks give a depth map, the range and the busiest position; the frames give the outline | `focus` and the preview the desktop already receives; `AutoSubject` for the outline (exists) | 36 s (MEASURED, 1.10 s a position) |
| 2 | **Light** | Waits until the light has been on 150 s. The sweep has usually used the wait | host `power.light`, the desktop's clock | 0 to 110 s |
| 3 | **Test shot** | One RAW at the busiest position, read inside the outline. Chooses the survey's two shutters. Repeated once if it clipped or was nearly black | `capture_positions`, kind `test`, with a shutter (exists) | 7.3 s (MEASURED, single RAW as a test run) |
| 4 | **Survey** | Single RAWs: every position of the survey grid at the long shutter, every second at the short; the dense cluster at the long | `capture_positions` with `shutters` (exists) | about 60 RAWs, 3.7 min (DERIVED from 49 RAWs in 179 s) |
| 5 | **Read** | `strehl survey` on the run: outline, depth, sharp depth and step, body, highlights, advice, the per-tile maps for the lenses | `strehl survey`, extended (section 7) | 13 s for 227 frames on this machine (MEASURED); a survey is a quarter of that |
| 6 | **Proof** | One plane exactly as the plan stands: the base group, then the highlight group if the plan has them. Checked by the capture's own plane check | two test runs (MEASURED to work: 12.5 s and 8.3 s) | 21 s |
| 7 | **Restore** | Four-shot, the shutter and ISO of the plan, the lens to the busiest position | exists | seconds |

About five minutes on a light that is already warm; six from cold. On the five stacks
measured, a correct range alone would have saved a fifth to a third of the capture (R2.3).

### 4.1 The sweep's window

- **Seed.** The lens position, if the owner has moved the lens since the camera connected.
  Otherwise the centre of the plan the host still holds for this subject. Otherwise the
  lens position. (After a power cycle the lens can stand tens of thousands of units from
  the subject; R4.)
- **Window.** 3,000 units either side of the seed, clipped to the lens's ends: 33
  positions about 190 apart. The measured sweep of that shape found a range 806 units
  long to within 18.
- **Nothing found** (fewer than 8 tiles with a peak that agrees with its neighbours): the
  step says "Nothing in focus between 29,500 and 35,580" and offers "Search the whole
  travel (about 6 min)" and "Mark by hand".
- **Running off an end** (3 % or more of the tiles with a peak have it at the window's
  first or last position): the window is moved half its width that way and swept once
  more. If that also runs off: the step says so and stops before any RAW is taken.
- The sweep always arrives at its first position from below (the capture's approach
  direction).

### 4.2 The survey grid

With `first` and `last` the sweep's range and `W0` the last sharp depth measured at this
lens position (section 8), else 45:

- **Grid:** from `first − 3 W0` to `last + 2 W0`, `W0` apart. Long shutter at every
  position; short shutter at every second, and at the first and the last.
- **Cluster:** 25 positions `W0 / 5` apart (never under 4 units), centred on the busiest
  position, long shutter. Its span is 4.8 `W0`: a shorter one reads the sharp depth low
  (R5).
- Why the margins: the sweep's range starts 44 to 83 units late on the five subjects
  measured (up to 2.2 sharp depths), because a preview tile averages over the nearest
  small features; its far end is within 44 (R2.4).
- **Shutters, from the test shot.** Long: the offered shutter that puts the body's top
  (the survey's own statistic, `body.top`) nearest 0.5 of full scale, at most 1.3 s.
  Short: five stops under the long. If the read reports pinned samples in the short
  frames (`census.pinned_short_sites` above zero), the short frames alone are taken again
  three stops shorter, once.

### 4.3 Stopping and failing

- Stop, a deadline or a failure ends the pass at once. Facts already measured stay, each
  with its source. The step names the stage that did not finish and offers "Run the rest".
- The camera is put back whatever happens: four-shot, the plan's shutter and ISO,
  magnifier off, the lens at the busiest position (or where it was if the sweep found
  nothing). The restore paths of today's `Calibration` carry over.
- While the pass runs, Start, Schedule, the jog buttons and the mark buttons are off, and
  the pre-flight strip says "The calibration is using the camera". Escape stops it.
- The survey's RAWs are kept until Start, New capture or the next calibration, so that an
  edited outline or a different target re-reads in seconds instead of re-shooting (about
  2 GB for 60 RAWs as the receiver stores them: 31.5 MB each in the dragonfly capture,
  MEASURED). They are single frames in the receiver's folder as today; the desktop
  removes them.

---

## 5. The algorithms

These are normative. Each was run on real data before it was written down; the script
named beside each is the reference implementation to port, and its numbers are the gates
(section 9).

### 5.1 Contrast: the focus measure

Reference: `block_contrast` in `grounding/scripts/general.py`. New code:
`strehl-core/src/focus-contrast.rs` (module `focus_contrast`; new files are kebab-case per
`AGENTS.md`), used by `strehl survey`, `strehl subject` and the plane checker.

On one green site plane of one decoded exposure, above black (the plane
`focus-step-cmd.rs` already reads):

1. **Block energy.** Per block of 8 × 8 samples (16 sensor pixels): `l` = the mean of the
   squared 4-neighbour Laplacian.
2. **Noise.** `n` = 20 × the injected noise model's variance at the block's mean level
   (four independent neighbours and four times the centre: 4 + 16). Take it from
   `strehl_core::profile::noise_model_for`; do not fit it.
3. **Detail.** `e = l − n` where `l ≥ 3 n`, else 0.
4. **Level.** `L` = the largest block mean within 3 blocks (a 7 × 7 block window).
   `L0` = 8 × the read-noise deviation of the same model.
5. **Block contrast.** `c = e / (L² + L0²)`.
6. **Tile contrast.** A tile is 4 × 4 blocks (64 sensor pixels). Its contrast is the 75th
   percentile of its 16 blocks.

Why each part is there (each removed a measured failure):

- Dividing by brightness: bright blur outranks dim detail by energy (in focus 148 DN, the
  blur that scores as sharp 2,056 DN; R1).
- The neighbourhood's brightest level, not the block's own: a blurred bright edge spills
  gradient into the dark blocks beside it (56 false tiles on the weevil; R2.2).
- The injected noise and `L0`: with a wrong dark-level noise, black backdrop reads as
  detail.
- The 75th percentile of blocks: one hot pixel or one glint rim does not make a tile.

### 5.2 In focus, and the subject's range

Reference: `contrast_range` in `general.py`.

Given tile contrasts for a set of frames at known focus positions, and the subject's
tiles (at least half their area inside the outline):

1. **Reference.** `R` = the 90th percentile, over the subject's tiles, of each tile's
   largest contrast in the set.
2. **In focus.** A tile is in focus in a frame when its contrast is at least `0.2 R`.
3. **A frame holds the subject** when at least 3 tiles and at least 0.05 % of the
   subject's tiles are in focus.
4. **Range.** `in_focus_first` and `in_focus_last` are the positions of the first and
   last frame that hold the subject.
5. **Running past.** `reaches_first` (or `reaches_last`) is true when the set's first (or
   last) frame holds the subject.
6. **Suggested bounds.** `suggested_start = in_focus_first − max(W / 2, spacing / 2)`,
   `suggested_end = in_focus_last + max(W / 2, spacing / 2)`, with `W` the sharp depth
   and `spacing` the set's largest gap between neighbouring frames near that end. When a
   `reaches_` flag is true that side has no suggestion, only the statement.

Measured (R2.3): within 64 units of the truth with every plane and within 43 with 13
planes, on five subjects with sharp depths of 37 to 51; zero tiles at the end planes of
those five; tiles at the end planes of the three that run past, confirmed by eye. Moving
0.2 between 0.1 and 0.4 and 0.05 % up to 0.2 % moves an end by one sharp depth or less on
four of the five.

The engine's present `first` and `last` (the plane of each cell's largest energy) and its
"core" stay in the JSON under their names for comparison and are no longer what anything
offers.

### 5.3 The live sweep: peaks

Reference: `live-sweep.py` (real preview frames) and `sim-live.py`. New code: in the
desktop, beside `AutoSubject`; the host's `bounds.rs` is not used by the calibration.

On the preview's luma (1024 × 680), per frame:

1. Smooth with a Gaussian of 1 px; take the squared gradient; average it and the luma
   over tiles of 32 × 32 px (31 × 21 tiles).
2. Tile measure `m = E / (Lnear² + 0.03²)`, `Lnear` the largest tile luma in the 3 × 3
   around.

Across the sweep's positions, per tile:

3. Smooth `m` along focus over 40 units (at 190-unit spacing that is the 0.7-sample
   minimum).
4. The tile has a peak when its largest value is over 3 times its 15th percentile and is
   not at the first or last position. The peak's position is the vertex of the parabola
   through the largest sample and its two neighbours.
5. A peak is kept when it lies within 2 `W0` of the median of the peaks in the 3 × 3
   tiles around it. This is what removes backdrop and stray highlights: without it the
   same sweep's extremes were 30,415 and 35,262.
6. **Offset.** Add the lens's coarse-to-fine offset (section 8; +27 units measured here,
   +9 to +42 across eight stacks, always positive). Until one is known, add half of `W0`.
7. **Range** = the smallest to the largest kept peak. **Busiest position** = the mode of
   the kept peaks in bins of `W0`. **Depth map** = the kept peaks, by tile.

Measured: per-tile error against the RAW focus, half within 14 to 17 units and 90 %
within 45 to 49, at 20-unit and at 190-unit spacing alike. Do not use the width of the
curve for anything: it is 400 to 570 units here, nine or more sharp depths.

### 5.4 The sharp depth and the step

- The sharp depth `W` is `strehl survey`'s `step.width` from the dense cluster, as today,
  with the cluster of section 4.2. It is reported with the tile size it was read at
  (64 px); 16 px tiles read 5 to 21 % narrower (R5) and the step rule's constant was
  fitted at 64, so the tile size does not change.
- **The suggested step is the coarsest step whose kept detail is at least the target**,
  99 % by default (the owner's answer of 2026-11-26). Kept detail is
  `guide::detail_kept(W / step)` as today. Table, hover and target picker as in the
  earlier proposal's section 6.3, which stands.
- After every finished capture the desktop records `W` (from `strehl focus-step` on the
  capture) and the coarse-to-fine offset against the lens position (section 8). Thinning
  each tile's own curve to every k-th plane reproduces the shape of the render-measured
  retention curve and shows subjects differing by more than the curve's steps (R5): the
  per-subject retention figure belongs in that record, and replaces the two-stack curve
  when a research stage has compared it with thinned renders (S6).

### 5.5 Facts and staleness

As the earlier proposal's section 6.1, which stands, with these facts:

```text
depth    in-focus range, reaches_first/last, the per-tile focus map, source (sweep | survey)
outline  rings, area share, parts, source (sweep | survey | drawn)
sharp    W, its spread, the cluster's span, suggested step at the target
light    body_full, glint_full, the per-tile level and highlight maps, light-on seconds when taken
proof    verdict, members' residuals, ratio, pins, body level against prediction, seconds a plane
```

Added to its table of changes: **the light has been on under 150 s** when a light fact is
taken marks that fact "taken while the light was settling" (ring, not lamp).

### 5.6 The exposure model and the adviser

The earlier proposal's section 6.2 stands unchanged: `body_full`, `glint_full`, the three
treatments, one pure function in `strehl-core` called by `strehl survey` and the desktop,
snapped to the camera's shutters at the current ISO; `guide::advise`, `exposure_line`,
`exposure_rows` and `plan::advice_rows` deleted. On the dragonfly it reproduces the
engine's advice: base 1.3 s, groups at 1/100 s (R3.1).

Two additions from the rig:

- The treatment table's Body column gains the body's median beside its top when they are
  more than four stops apart ("body 77 %, median 0.8 %"). On this subject the top tenth of
  a percent sets the exposure and half the subject sits seven stops under it; the owner
  should see that before choosing. No new rule is proposed from one subject.
- Highlight groups are planned for every plane or every second, over the whole stack, as
  today. Planning them by depth is withdrawn (M7).

### 5.7 Highlight fusion: make the frames count

This is fix F1 and it is not optional. Reference: R3 and `patch-fusion.py`.

1. **The ratio.** `fit_pair` in `strehl-cli/src/highlight-fusion.rs` takes its ratio from
   the estimator `strehl survey` already uses for the same quantity (cells well exposed
   in the base, the median of base over companion; ±1.8 % of commanded on 76 pairs here),
   moved to one shared function. Its checks become: within 0.25 EV of commanded; two
   interleaved halves of the cells within 1 %; and the hand-over sites (base green at 0.50
   to 0.75 of the pin, nothing brighter near) reading 1.00 ± 0.03 after the ratio, when
   there are at least 400 of them.
2. **No cells at all** (a subject with nothing between 5 % and 60 % of full scale): use
   the commanded ratio when the capture's other pairs agree with their commanded ratios
   within 3 %, and say so in the log.
3. **The texture test goes.** A group five stops under cannot show texture 16 times its
   noise. Motion between the groups is judged by the companion's registration against its
   base group (which the fusion already measures as `shift`), refused over 1 px.
4. **The highlight group's own four-shot check** is not applied below a signal floor:
   when fewer than 1,000 tiles carry signal the group is not demoted on the witness test
   (73 of 151 were, on 175 to 193 tiles each).
5. **Tone.** `tone-subject.rs` sets aside, as highlights, every site the fusion replaced
   or blended, exactly as it sets aside pinned sites today. Gate: white within 5 % of the
   same capture rendered with fusion off.
6. **Say it.** The stack's checks gain one row: "Highlight groups used on 151 of 151
   planes", or "on 0 of 151: the exposure ratio could not be measured", with the triangle
   when any plane with a group went unused. The same sentence in the flight's "Captured"
   panel once the stack exists. A capture must never again spend a third of its frames
   silently.

### 5.8 The proof plane

One plane as the plan stands, at the busiest position, after the exposure is known.
Reference: `rig-series.py`, `proofs.py`.

- Two test runs today (base group, then highlight group with its shutter): 12.5 s and
  8.3 s. A single positions run with two shutters would save one approach; test runs are
  one position each, so that needs a host change and is not required.
- The base group goes through `strehl pixel-shift --json`. Reported: the verdict, the
  members' largest residual, the local disagreement against its limit, and whether the
  capture would have retaken it.
- The pair gives the ratio (5.7's estimator), the pins in the base group, whether the
  highlight group holds them (no pinned sample), and the body's level against the
  adviser's prediction (which is also the earlier proposal's "Verify").
- Seconds a plane and bytes a RAW, for the footer's finishing time and disk line.
- **One proof is one sample.** Of 26 base groups taken at one position in two series, 7
  were clean (their shots within 0.11 px) and 19 were 0.14 to 0.50 px off, in no order,
  and no better with nobody walking; the capture's own gate would have retaken 5 (R4).
  The step therefore offers "Prove five times" (about 100 s), which reports "3 of 5
  groups clean, 1 would be retaken" and from it the retakes the footer's finishing time
  should allow for. It does not suggest a shorter exposure: groups at 1/40 s failed as
  often.
- What moves the picture between shots was not found. It is one shift for the whole
  frame, so it is the rig or the camera, not the subject. That is the owner's rig work,
  outside this spec; the proof plane is how Capture reports it.

---

## 6. The review surface

The owner's direction: evidence as lenses over the stage. The Stack station already has
the pattern (the proposal `2026-11-desktop-studio-2.md`, 5.3): one switch, evidence
painted on the picture, uncoloured where support is low, no adjectives.

### 6.1 Lenses

One switch in the live view's tool bar: **Off · Depth · Cover · Light · Glints · Still**.
The picture under a lens is the live view while planning (or the test shot, when live
view is off). A lens is square tiles with a hairline of picture between them, at 62 %
opacity, with one ruled legend at the bottom left. Tiles are the measurement's own: 32 px
preview tiles from the sweep, 64 px sensor tiles from the survey. No smoothing, no
blending between tiles, no rounded shapes.

| Lens | Shows | Source | Legend |
| --- | --- | --- | --- |
| **Depth** | Where each part of the subject is in focus, near to far, in one colour ramp. Tiles with no peak are left uncoloured | The sweep at once (36 s into the pass), replaced by the survey's when it is read | The ramp with Start, End and the in-focus range ticked; "from the live sweep, coarse" or "from RAW" |
| **Cover** | Against the plan as it stands: tiles the planes cover; tiles in focus only before Start or after End, in the warning colour, with their count | The depth map and Start, End, Step | "All of the subject is covered", or "214 tiles (2.5 %) lie before Start" |
| **Light** | The body's level at the chosen exposure, by tile, in five bands: under 1 %, 1 to 10 %, 10 to 50 %, 50 to 90 % of full scale, pinned | The survey's long frames scaled to the chosen exposure | The five bands with the share of the subject in each |
| **Glints** | Tiles whose highlights pass the pin at the chosen exposure, coloured by how many stops over; outlined when the plan's highlight groups hold them, filled when they will pin | The survey's short frames | "7.7 % of the subject, up to 5.5 stops over; held by groups at 1/40 s" |
| **Still** | The proof plane's local disagreement between its four shots, by tile, against the retake limit | `strehl pixel-shift --json` (`tile_local_map`, exists) | The limit, the proof's 99th percentile |

The mockups draw Depth and Glints from the real measurements of 2026-11-27 (the depth map
from the 36 s sweep; the glints from the stack's highlight frames).

### 6.2 What a lens answers

- **Hover a tile** under Depth: the rail's lens marker jumps a ghost to that tile's focus
  and the readout says "in focus at 32,742". **Click** pins a core sample beside it, as
  the Stack station does: the tile at 100 % from the three survey frames nearest its
  focus, its contrast against focus as a small curve, and one sentence ("In focus at
  32,742, seen in 3 survey frames"). The crops are RAW, developed with one fixed
  transform for the three.
- **Hover the rail** under Depth: the tiles in focus within half a sharp depth of that
  position keep their colour and the rest dim. This is the plane lens of the Stack
  station, before any plane exists. It answers "what is in focus here?" at any depth,
  which is how the owner checks an end.
- **Move the lens** (jog, keys, drag): the same isolation follows the lens. A tile is
  "in focus now" when the lens is within half a sharp depth of its measured focus. This
  costs nothing per frame (it is a comparison of two numbers per tile) and replaces
  reading gradient peaking on a subject whose blur and highlights light up the peaking.
  Peaking itself stays as it is, a different tool.
- **Drag Start or End** on the rail under Cover: the tiles that fall outside change
  colour as the mark moves, and the count updates. The owner sees what a tighter range
  loses before choosing it.

### 6.3 The rail

The depth rail carries the same evidence along focus (148 px while planning; the earlier
proposal's section 7 stands for its lane and its ruler):

- **Bars: tiles in focus by position** (the contrast rule), not energy. Where the
  survey has frames the bars are the survey's counts; between them the sweep's peak
  histogram, dimmer. A broad hump of "sharpness" is never drawn again.
- The in-focus range as the teal bracket; Start and End as today; the survey's positions
  as marks in the lane, filled as they are taken; the dense cluster where it is.
- The highlight line: the highlights' top by position (`census.per_position`), dashed.
- The sharp depth as a ruler at the lens.

### 6.4 The column

- **2 Calibrate.** Before: one sentence, the button (key C), and what it will take
  ("about 5 min; about 60 single RAWs, not kept as a stack"). Running: the stage in words with
  its count and time left, one progress line with a tick at each stage boundary, Stop,
  and the readout filling a row at a time. Done and folded: when it ran, what it took,
  and the four numbers the plan stands on.

  | Readout row | When known | Source line |
  | --- | --- | --- |
  | In focus | "32,355 – 33,161" | "live sweep, 33 positions in 36 s", then "survey, 22 frames" |
  | Outline | "51 % of the frame, 1 part" | "from the sweep", "from the survey", "drawn" |
  | Sharp depth | "45 units" | "35 to 59 across the subject · 25 RAWs over 216 units" |
  | Body | "full scale at 1.6 s; median 0.8 %" | "22 positions, light on 4 min" |
  | Highlights | "up to 5.6 stops over the body's top" | "11 positions, short frames" |
  | Proof | "clean: its shots within 0.10 px; ratio 50.6; 12.5 s a plane" | "one plane, 02:25" |

- **3 Depth.** Start and End with their lamps or "held"; one line under them from 5.2
  ("In focus from 32,355 to 33,161 · the marks fit it" / "34 planes before 32,332 hold
  nothing in focus: 7 min" with **Use** when the marks are held / "Still in focus at the
  survey's last frame, 33,340: the subject may go on" with **Search further**). The step
  table with Keeps, and the target.
- **4 Exposure.** Pickers, the one treatment table, the highlight groups row, the proof's
  line with "Prove five times". Under the table, when the light fact is marked: "Measured
  while the light was settling: calibrate the exposure again" as a link that runs stages
  3 to 5 for exposure only.
- A value's state: the lamp when it is the calibration's; nothing, and a second line
  ("the calibration gives 10 · Use"), when held.
- The pre-flight strip: Rig, Light (with its minutes on), Calibrated, Depth, Exposure,
  Disk, Receiver, Subject. Calibrated, Depth and Exposure never block Start.

### 6.5 Taste

For the implementer, because this owner cares and has said so:

- Square, ruled, engraved. The lens is a grid of the measurement's own tiles with picture
  showing between them; it must look like an instrument's reticle, not a heat map from a
  dashboard. No gradients across a tile, no glow, no rounded corners, no drop shadows.
- One ramp for depth, the same one on the stage and on the rail's legend. Warning colour
  only for what the plan would lose or pin.
- Words on the stage are few and are measurements: "in focus at 32,742". Never "good",
  "sharp enough", "optimal".
- Nothing reflows while the pass runs. Rows fill in place. Nothing folds under the
  pointer.
- Smoothness is a requirement with a number (section 9, S3): the lens is one textured
  quad or one cached mesh built when its fact changes, never per frame; the isolation of
  6.2 is a uniform or a per-tile alpha written on a position change, not a rebuild.

---

## 7. Engine, desktop and host changes

| # | Where | Change |
| --- | --- | --- |
| C1 | `strehl-core`, new `focus_contrast` | 5.1 and 5.2 as pure functions over a decoded frame's green plane, the noise model and a tile mask. Unit tests with planted frames: fine texture at 1 % of full scale beside a blurred disc at 30 % (the disc must score under 0.2 of the texture); a blurred bright edge against black (no tile passes); a flat frame (nothing); gain placebo (contrast unchanged under ×1.25) |
| C2 | `strehl-cli/src/survey-cmd.rs`, `subject-cmd.rs` | `depth` gains `in_focus_first`, `in_focus_last`, `reaches_first`, `reaches_last`, `per_position` (tiles in focus), and `suggested_start` / `suggested_end` by 5.2. The old `first` / `last` / `core_*` stay. A `maps` block: the tile grid, per-tile focus (the position of the tile's largest contrast among frames where it is in focus, null otherwise), per-tile body level, per-tile highlight top. The summary sentence stops saying "sharp from the first to the last plane" on evidence 5.2 rejects |
| C3 | `strehl-cli/src/focus-step-cmd.rs` | Reports the cluster's span in sharp depths and marks the width "low: the cluster spans under four widths" when so |
| C4 | `strehl-cli/src/highlight-fusion.rs`, `tone-subject.rs`, the stack's checks | 5.7 |
| C5 | `strehl-ui`, new `capture-measure.rs`; `capture-tools.rs` | The pass (section 4); `Calibration`, `survey_positions`, `two_shutter_survey` retired. The sweep of 5.3 beside `AutoSubject` (off the UI thread) |
| C6 | `strehl-ui/src/capture-plan.rs`, `capture-guide.rs`, `capture-preflight.rs` | The column of 6.4; rule 2's measured-or-held state per value; the one adviser; the chips |
| C7 | `strehl-ui/src/capture-live.rs`, `capture-rail.rs` | Lenses, core sample, the rail's bars and marks (6.1 to 6.3) |
| C8 | `strehl-ui/src/capture-control.rs`, `docs/desktop-control.md`, `scripts/strehl-control.py` | Requests `calibrate` (optionally `stages`), `stop_calibration`, `prove`; the snapshot's `capture.tools.calibration` carries the stage, each fact with value, source, time and stale reason, the adviser's rows and the lens in view. `calibrate_step` stays as an alias that runs stages 4 and 5 |
| C9 | host | Nothing required. Optional later: a positions run that accepts two shutters at one position in a test, to save the proof's second approach |

---

## 8. What is remembered

Plain JSON beside `capture.json`, as the earlier proposal's section 8, with what the
measurements showed is worth keeping:

- **By lens and focus position (to the nearest 2,000 units):** the sharp depth and the
  coarse-to-fine offset of every finished capture, newest first. They seed `W0` and the
  sweep's offset for the next calibration there. They are never shown as this subject's
  figures: the sharp depth differed by a third between subjects at one position.
- **By catalog subject:** its last calibration and plan. "New stack of this subject"
  opens with them under rings, and the sweep's window is centred on them.
- The lens returned to a focus position within a few units a day and a power cycle later
  (one case, R2.4), so a remembered range is a fair seed and not a plan.

---

## 9. Stages, in order, with their gates

Each is installable alone. Desktop stages end with the UI tests, an offscreen render of
every fixture they touch, and before-and-after frame times. "Private corpus" gates run on
the owner's machine against stacks that are not in the repository; their expected values
are in R2.3 and are restated here so the gate does not depend on that file surviving.

### F1. Highlight groups reach the picture (engine; first)

5.7, points 1 to 6.

- Private corpus: `stack-1795713444768-14989` renders with highlight groups used on 151
  of 151 planes; the tone step's white is within 5 % of 0.673; no site with a pinned
  sample in its footprint is left unreplaced. Fails today (0 of 151; and 8.415 with
  fusion forced).
- Captures without highlight groups render byte-identical before and after.
- The weevil and pronotum highlight fixtures of the X4 stage keep their results.
- A planted ratio error of 5 % is corrected and one of 25 % refused (the existing
  `STREHL_HIGHLIGHT_RATIO_PLANT` gate).
- The checks row reads "0 of N" with the triangle on a capture whose groups are made
  unusable (their files replaced by black frames).
- `AGENTS.md`'s shipping rule applies: time the render before and after on GPU and CPU.
  The prototype's whole render took 1 min 14 s with its alignment.

### F2. Bounds from contrast (engine, one line of UI)

C1, C2, C3, and the Depth step's one line reading the new fields.

- Unit tests of C1 as listed there.
- Private corpus, `strehl survey` or `strehl subject` with all planes and with 13:

  | Run | `in_focus_first` – `in_focus_last`, all planes | 13 planes | `reaches_` |
  | --- | --- | --- | --- |
  | stack-1795713444768-14989 | 32,366 – 33,174 | 32,366 – 33,166 | neither |
  | stack-1795460665629-8651 | 24,699 – 25,644 | 24,713 – 25,637 | neither |
  | stack-1795300522964-6430 | 31,125 – 32,287 | 31,132 – 32,231 | neither |
  | stack-1795433406862-8651 | 30,704 – 31,754 | 30,784 – 31,684 | neither |
  | stack-1795371396674-6430 | 15,833 – 16,418 | 15,853 – 16,388 | neither |
  | stack-1795476520452-8651 | 60,830 – 62,800 | the same | both |
  | stack-1794786793543-11226 | 50,300 – 51,860 | the same | both |
  | stack-1794689780304-11226 | 61,050 – 61,898 | the same | first; last allowed either way |

  Tolerance: one frame spacing of the set, since a port will differ in details (the
  reference read the whole visible area and fitted its noise). The failing input is
  today's build: the first row's bounds come back 32,034 to 33,290.
- `strehl survey`'s other blocks are byte-identical on the census fixtures.

### F3. Exposure work waits for the light; the survey's shutters come from a test shot

- With the light on 20 s, the pass's first RAW is taken at 150 s or later; with it on
  ten minutes, at once.
- Started with the camera reporting 1/40 s and again at 1.3 s on one subject: `body_full`
  agrees within 10 %. The failing input is today's `start_calibration`.

### S1. The sweep, the Depth lens, "in focus now"

C5's sweep, C7's Depth lens from it, the rail's peak histogram, 6.2's hover and
lens-following isolation. The Calibrate button exists and runs stage 1 only.

- Rig gate, the dragonfly or any subject with a stack on disk: from a seed 2,000 units
  off, the sweep's range lies within one sharp depth of the stack's `in_focus_` range at
  the far end and within two and a half at the near end; it takes under 45 s.
- A demo-camera sweep with a planted two-plane subject gives two populations of tile
  focus, and a backdrop with texture of its own, lit brighter than the subject, gives no
  kept peak (the coherence test's failing input).
- Frame time of the live view with the Depth lens on, and while jogging with the
  isolation following, within the baseline of the live view alone (measure first; Capture
  has no frame-time benchmark today: add one in the manner of
  `benchmark_finished_workspace_pointer_sweeps`).

### S2. The pass and the column

Section 4 entire; 6.4; rule 2; C6; C8.

- From a connected camera and a framed subject, one press fills Depth and Exposure; the
  camera afterwards reads four-shot, the plan's shutter and ISO, magnifier off.
- Stopped once in each stage: the camera is as above, earlier facts are kept, "Run the
  rest" completes.
- A step held at 7 before the press is 7 after it, and its row offers the calibration's.
- Exactly one treatment row carries the suggested lamp in `plan+survey` (fails today:
  two "Suggested").
- Nothing in the column lies under the footer at 1680 × 1050 in the calibrated fixture
  (extend `nothing_runs_past_the_plan_column`); at 1366 × 768 the first open step is
  fully visible.
- Fixtures: `plan+calibrating` (stage 4 part-way), `plan+calibrated`, `plan+held`,
  `plan+past-end` (reaches_last), `plan+light-settling`, `plan+nothing-found`.

### S3. The survey's lenses and the rail's evidence

Cover, Light, Glints; the core sample; the rail's bars from 5.2.

- The lens and the rail land on the pixel the scale says, at three zooms.
- Dragging End under Cover at a 6,000-plane plan holds the rail's frame-time budget.
- The bars of `plan+calibrated` are zero outside the in-focus range (today's profile is
  a hump over the whole sweep).

### S4. The proof plane and the Still lens

5.8.

- A proof with a planted half-pixel shift in one member reads "not clean"; an unshifted
  one "clean". Five proofs report a count.
- The body level it reports is within 10 % of the adviser's prediction on the rig, light
  warm.

### S5. Memory and staleness

Section 8; 5.5; Verify by the proof plane.

### S6. Later, each its own decision

- A capture that stops itself when the subject ends. Measured on four stacks: it would
  end 44 to 124 units past the last in-focus plane and save 4 to 18 planes; it cannot find
  the near end. Small gain; an option, off by default, if wanted.
- Per-subject retention from the capture's own curves, compared with thinned renders
  before it replaces the two-stack curve. Research workflow first.
- The Calibration page (the owner's own item, outside the Capture station): the list in
  the earlier proposal's section 18, plus the coarse-to-fine offset and the sharp depth by
  lens position that section 8 here starts recording.

---

## 10. What is deliberately not here

- **An unattended capture.** The earlier proposal's section 17 read the owner's goal as
  "press Start and get a picture". They meant the calibration. Nothing here starts,
  extends or mends a capture by itself. The parts of that section which survive are the
  found range, the proof plane, and the measured-or-held state.
- **Highlight groups by depth**, **a shorter exposure against movement**, **skipping the
  dense cluster on a known rig**: each was proposed and each failed its measurement (M7,
  M8).
- **A change to gradient peaking.** It stays; "in focus now" is the answer to its
  weakness.
- **A host deploy.** Not needed.

---

## 11. Decisions for the owner

Decided 2026-11-27: "assumptions in decisions sound good. 4. keep 99% 5. sure". Each row
below is now the decision.

| # | Question | Decided |
| --- | --- | --- |
| 1 | After a calibration, do Start, End, Step and the exposure take the calibration's values (unless you had set them), or does it only offer them? You decided "offer" for bounds on 2026-11-23, when the offer was the engine's wide one | Take them, with the lamp, and review on the stage. Your own settings are never changed |
| 2 | Keep the survey's RAWs (about 2 GB) until Start so edits re-read instead of re-shoot? | Yes |
| 3 | The names: Calibrate; the lenses Depth, Cover, Light, Glints, Still | As written |
| 4 | The retained-detail target: 99 % as today's suggestions, or lower (98.5 % is a third fewer planes)? | 99 % |
| 5 | F1 changes what a finished stack looks like when it has highlight groups (they will be used). Re-render the dragonfly after it lands? | Yes; nothing is re-rendered automatically |

---

## 12. Ledger and evidence

Allocated in [the milestone ledger](../agents/milestone-ledger.md) on 2026-11-27, section
"Capture calibration (2026-11-27)":

| Identifier | Scope |
| --- | --- |
| capture-planning-flow-2026-11-26 | The first proposal and its mockups. Done, design only |
| cpf-grounding-2026-11-27 | The measurements this spec stands on. Done |
| cpf-f1-highlights, cpf-f2-bounds, cpf-f3-light | Section 9, F1 to F3 |
| cpf-s1-sweep … cpf-s5-memory | Section 9, S1 to S5 |
| cpf-s6-* | One row each when taken up; the retention item follows the research workflow |

Evidence: [results](../../experiments/capture-planning-flow-2026-11-26/grounding/results.md)
and [its scripts](../../experiments/capture-planning-flow-2026-11-26/grounding/scripts/);
the fusion prototype is `patch-fusion.py` there (a patch to apply to a worktree, with no
tests: a demonstration, not the change to merge).
