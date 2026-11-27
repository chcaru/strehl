# Capture planning flow: range, measure, decide

**Status:** Proposal, **replaced on 2026-11-27** by
[the capture calibration specification](2026-11-capture-calibration-spec.md), which is the
document to implement. This one is kept as the record of how that design was reached: its
findings (section 1), the exposure model (6.2), the step rule (6.3) and the facts and
staleness table (6.1) are cited from there and stand; its flow (sections 3 to 5), its
automatic run (17) and several candidates of section 16 were changed or withdrawn after
measurement and after the owner's correction that "automatic" meant the calibration, not
the capture. Its mockup links point at screens that have since been redrawn.
**Date:** 2026-11-26. Revised 2026-11-27: the automatic run (section 17), which changes
rules 5 and 6 and decisions 1, 2 and 6; the candidates of section 16 staged; the
Calibration page set aside for its own proposal (section 18).
**Owner's request:** "on the Capture screen, when in planning: the flow of 2. Exposure -> 3.
Depth doesn't seem to work cohesively and constructivly as is. can you take a look into a
better calibration and planning flow. you can design it however you like. just plan it out
and write up your design."
**Scope:** the Capture station while planning: the plan column, the live view's tools, the
depth rail and the pre-flight strip. Stage labels (P0 to P7, E1 to E10, H1, H2) are plan-local;
allocate milestone rows before dispatch (section 14).
**Audience:** the owner, then an implementing agent.
**Written against:** `origin/main` at `b2c8a07aa`, the source of the installed desktop
(build `desktop-91cc19f0619a9ac4`). Paths below are in `crates/strehl-ui/src/` unless they
say otherwise.
**Mockups:** [`experiments/capture-planning-flow-2026-11-26/mockups/`](../../experiments/capture-planning-flow-2026-11-26/mockups/README.md),
five screen states drawn in the Studio 2 language.

Labels: MEASURED (a number from a results note, cited), VERIFIED (read in the code at the
commit above, or seen in an offscreen render of the installed build), DERIVED, ARGUED,
UNVERIFIED. No camera, light or Pi was used for this proposal, and no product code changed.

---

## 1. What is wrong today

The plan column has four numbered steps: Rig, Exposure, Depth, "While it runs, and after".
Steps 2 and 3 each depend on the other, so neither can be finished in order.

| # | Finding | Label |
| --- | --- | --- |
| F1 | The best exposure advice is produced by step 3's button. "Calibrate step" lives in Depth and needs both marks (`capture-workspace.rs`, `calibrate`: "Mark the start and end first"). Its survey produces the three exposure choices, which then appear back in step 2 under "From the calibration" (`capture-plan.rs`, `advice_rows`). Walking the steps top to bottom, the owner sets an exposure, then learns in step 3 that step 2 has changed. | VERIFIED |
| F2 | Step 2 holds two advisers that do not know about each other, drawn together, both saying "Suggested". One reads the test shot (`capture-guide.rs`, `advise`: the brightest 0.1 % to 0.9 of full scale). The other reads the survey (`advice_rows`). In the installed build's `plan+survey` fixture they read "Suggested. 2 s with groups at 1/25 s" and "Suggested ISO 100 · 0.4 s … Apply" in the same step. On the weevil the test-shot rule gave 1.6 s, which pins 12 to 20 thousand subject sites a plane (MEASURED, the [subject and highlights plan](2026-11-subject-highlights-and-detail-plan.md), section 1). | VERIFIED, MEASURED |
| F3 | A third exposure limit, the stillness check's "exposures up to … keep the blur under a quarter pixel", is a sentence only. Neither adviser reads it (no use of the stillness result in `capture-guide.rs`). | VERIFIED |
| F4 | The survey takes its long frames at whatever shutter the camera holds, and its short frames four stops under (`capture-workspace.rs`, `start_calibration`). So "exposure" must be set before the thing that measures exposure. The Pi restores each connection's camera settings at shutdown, so after a reconnect that shutter is not a choice anyone made. | VERIFIED |
| F5 | The survey's advice is in seconds at the survey's ISO. Applying a choice sends that shutter with the camera's current ISO (`capture-station.rs`, `PlanIntent::UseAdvice`). After an ISO change the applied exposure is off by the ISO ratio. | VERIFIED by reading; not exercised |
| F6 | Nothing goes stale. The test shot and the calibration are cleared only by "New capture" (`capture-station.rs`, `new_capture`). Moving the marks, changing the aperture, dimming the light or redrawing the outline leaves every earlier result on screen as if it still held. | VERIFIED |
| F7 | A green numeral means "nothing blocks Start", not "this is established". Exposure is green as soon as the camera reports an exposure program (`exposure_step`: `ready = exposure.is_some() && …`), with no test shot at all. Depth is green once both marks exist. The pre-flight chips follow the same blockers. | VERIFIED |
| F8 | Five separate tools, each waiting for a click, feed the two steps: the rail's "Survey" (a live sweep), the live view's "Auto" (needs that sweep's frames), "Test shot", "Check stillness (20 s)" and "Calibrate step". Three different things are called a survey, and "Calibrate step" also outlines the subject and advises exposure. | VERIFIED |
| F9 | Two offers of bounds sit under each other in Depth ("Use the survey's", "Use the subject's"), from two different measurements. | VERIFIED |
| F10 | The column does not fit. At 1680 × 1050 with a survey's results, the Exposure step runs to the 720th pixel row and the step table is cut after one row. At 1366 × 768 Depth is entirely below the fold. | VERIFIED (offscreen renders of the installed build) |
| F11 | Smaller leftovers: settle is set in two places (the Rig step's settings and the Depth step); the survey's dense cluster sits at the middle of the marks, not where the subject is sharpest (`capture-tools.rs`, `survey_positions`); the survey's RAWs are deleted as soon as they are read, so a changed outline or changed bounds cannot be re-read without shooting again. | VERIFIED |

None of this is a fault in a measurement. The pieces built on 2026-11-23 and 24 work. They
were added to a column whose shape came from before they existed.

---

## 2. Why: the information flows the other way

What each decision needs, and what provides it:

| Decision | Needs | Provided by |
| --- | --- | --- |
| Subject outline | Frames through focus | The live sweep (loose), the RAW survey (precise) |
| Start and End | The subject's sharp range, the sharp depth | The live sweep, refined by the RAW survey |
| Step | The sharp depth | The RAW survey's dense cluster |
| Base exposure | The body's level inside the outline over the range; how far the picture moves during an exposure | The RAW survey's long frames; the stillness check |
| Highlight groups | How far the glints go above the body | The RAW survey's short frames |
| Time and disk | Planes (from Start, End and Step), seconds a plane (from the exposure) | Arithmetic |

Three things follow.

1. **Exposure is an output of the measurement, not an input.** RAW values are linear in
   ISO × time, so the survey can be shot at any sensible shutter and its result scaled to
   every other. The survey can choose that shutter itself from one test shot.
2. **Depth is decided before exposure.** Start, End and Step do not depend on the exposure.
   The exposure's cost in minutes depends on the plane count.
3. **The only thing that must come from the owner first is a rough range.** Everything else
   can be measured in one pass from two marks.

So the order is: rig, a rough range, one measurement, then depth, then exposure.

---

## 3. The design on one page

Five steps, in the order the information flows:

| | Step | Who acts | What it settles |
| --- | --- | --- | --- |
| 1 | **Rig** | Owner | Camera connected, light on. Unchanged. |
| 2 | **Range** | Owner | Two rough marks: just before the subject's nearest sharp point, just past its farthest. |
| 3 | **Measure** | The app, one click, about four minutes unattended | Subject depth, outline, sharp depth, the body's brightness, the glints, stillness. |
| 4 | **Depth** | Owner, from the measurement | Start, End, Step. |
| 5 | **Exposure** | Owner, from the measurement | ISO, shutter, highlight groups, four-shot. |

"While it runs, and after" stops being a numbered step. Its four switches become one "Run"
row under step 5.

The table says who acts when the owner works the column by hand. Since 2026-11-27 the
default is that the app works it: Start fills in steps 2 to 5 by itself and the owner sets
only what they want to hold (section 17). Sections 4 to 9 describe each step as it reads
and as it is set by hand; section 17 says what the app does with the same steps.

Seven rules hold the design together. An implementer who has to choose between two
readings of this document should pick the one that keeps these.

1. **Each step uses only what earlier steps settled.** No step's button changes an earlier
   step's content.
2. **One model, one adviser.** Every suggestion about exposure comes from one function
   reading one exposure model. The test shot, the survey and the stillness check feed that
   model; none of them advises on its own. This is the plan column's version of "inject one
   noise model".
3. **A fact knows what it was taken under.** Each measured fact carries its source, its
   time, and the conditions it depends on. When a condition changes, that fact, and only
   that fact, loses its mark, and the row says why.
4. **Green means measured.** A numeral is green when its step stands on a fresh measurement
   or on a choice made in view of one. "Nothing blocks Start" is a separate statement, made
   by the Start button and the pre-flight strip as today.
5. **Start is never held back by a missing measurement.** Start measures what the plan
   lacks and then captures (section 17.2). "Start as it is" captures an unmeasured plan,
   labelled "your setting, not measured". Amber and red stay reserved for what blocks.
6. **Automatic unless held.** A value the owner has not set follows the measurement. A
   value the owner set is never changed, and its row shows what the measurement would
   give (section 17.3). The first draft read "offered, not applied"; it was revised on
   2026-11-27 for the owner's goal of one button, and it changes the owner's decision of
   2026-11-23 that bounds are offered (decision 9).
7. **Every part can be run alone.** The pass is one click, but the sweep, the test shot,
   the survey and the stillness check stay individually available.

The mockup states show the column at each point:
range,
measuring,
measured,
something changed,
the automatic run.
(Those five screens were replaced on 2026-11-27 by the specification's six; the folder's
`build.py` now builds the new ones.) The measured state is drawn after the owner has
taken the offers. The numbers in all five are made up to agree with one another and are
not measurements.

---

## 4. The steps

### 4.1 The column

- One column, 348 px, as today. The names, the destination line and "New capture" stay at
  the top; the footer with the finishing time, the disk line, Start and Schedule stays at
  the bottom.
- A step is **open** (its controls) or **folded** (one line: its numeral, name, a summary
  and one link). A folded step always says what it settled, so the whole plan can be read
  top to bottom without opening anything.
- Which steps are open is a pure function of the state, the column's height and what the
  owner last clicked:
  - no camera: Rig open;
  - rig ready, range unset: Range open;
  - range set, nothing measured: Range and Measure open;
  - measuring: Measure open, the rest folded;
  - measured: Depth and Exposure open, Rig, Range and Measure folded;
  - when the open steps do not fit the height, only the first undecided one stays open.
  A click on a step's header opens or folds it and that choice holds until the state moves
  to another line of this list. Nothing folds while the pointer is in it.
- Numeral colours: green, established (rule 4); bright, the step in hand; dim, not yet, or
  assumed.
- Marks, from the existing set: the lamp (measured and fresh), the ring (assumed, or
  measured under conditions that have changed), the triangle and the diamond (blocking), the
  half (running).

### 4.2 Step 1, Rig

Unchanged, with one move: settle is set here only (it leaves the Depth step, F11). The
folded line gains how long the light has been on ("light 41 W, on 9 min"), because the
light dims 9 % in its first minute (MEASURED,
`experiments/capture-implementation-2026-11-20/results.md`) and drifts the picture for
some minutes after (MEASURED, 2026-11-25 stillness series).

### 4.3 Step 2, Range

- A two-sentence instruction, the Start and End fields, "Mark start here" and "Mark end
  here" (keys S and E, and dragging on the rail, as today).
- The step says the marks may be rough. They are a search range, not the capture's bounds;
  step 4 sets those.
- The outline's state in one line: the box, a drawn outline, or "the measurement finds it".
  Drawing stays in the live view's tools.
- Established when both marks are set, at least 8 units apart, inside the lens's ends.
- Folded: "37,020 – 37,840 · 820 units". After a measurement: "37,020 – 37,840 searched".

Revised 2026-11-27. The first draft did not propose finding the range with no marks. It
is proposed now (section 17.5, Find): the owner still chooses the magnification by
choosing where the lens focuses, and that position is the search's seed. The marks are
then the search's result, and marking by hand holds them.

### 4.4 Step 3, Measure

Before: one sentence on what it does and how long it takes, and the **Measure** button
(key M). Disabled, with the reason, until the range is set.

Running: the stage in words with a count and the time left ("RAW survey · 31 of 49 · about
1 min left"), one progress line with a tick at each stage boundary, **Stop**, and the
readout. The readout is one row a fact:

| Fact | Value when known | Source line |
| --- | --- | --- |
| Subject depth | "37,100 – 37,764" | "live sweep, 33 positions", later "RAW survey, 13 frames" |
| Outline | "28.7 % of the frame, 3 parts" | "from the sweep, loose", later "RAW survey", or "drawn by hand" |
| Sharp depth | "72 units" | "44 to 92 across the subject · 25 RAWs" |
| Body | "full scale at 2.8 s, green" | "12 positions" |
| Glints | "4.8 stops above the body" | "12 positions, short frames" |
| Stillness | "moves 0.06 px in a second" | "live view, 21:32" |

A row not yet measured says what it will take. A row whose conditions changed gets the
ring and says what changed ("light was 41 W, is 33 W"). Stopping keeps every row already
filled.

Done and folded: "Measure 21:30 · 50 RAWs, none kept" and under it the four numbers the
plan stands on: "Sharp over 72 units · body full at 2.8 s · glints 4.8 stops above it ·
moves 0.06 px a second". The link is "Again".

Opened after it is done, the step shows the readout, "Again", and one link per part
(Sweep, Test shot, Survey, Stillness) for running a part alone (rule 7).

"Body full at 2.8 s" is the one new term: the exposure at ISO 100 at which the subject's
diffuse top reaches full scale. It is the survey's `body.top` turned into a time, and it
does not change when the owner changes the shutter. Section 6 defines it.

### 4.5 Step 4, Depth

- **Start and End**, with one line under them from one comparison: the marks against the
  subject's depth with half a sharp depth each side (`depth.suggested_start` and
  `suggested_end` of `strehl survey`).
  - Equal: lamp, "Fits the subject's sharp range · 736 units".
  - Marks wider: ring, "The subject is sharp from 37,100 to 37,764: 12 fewer planes, 3 min
    less" and **Use it**.
  - Marks narrower: triangle (not blocking), "Sharp detail reaches 40 units past End: that
    part would be soft" and **Use it**.
  - The survey found the subject still sharp at a mark: "Still sharp at the far mark: the
    subject may go on. Extend 200 units and measure again", one click (E2).
  Before a RAW survey the same line reads the live sweep's range and says so. This replaces
  the two stacked offers (F9): the RAW survey's range wins over the sweep's when both exist.
- **The step table**: Step, Keeps, Planes, Time, Disk. "Keeps" is the share of fine detail
  a step retains (section 6.3), to one decimal; it replaces Overlap, which moves to the
  row's hover. The current row and the marked rows past the knee are drawn as today. The
  suggested row carries the small square lamp instead of a line of text. Four rows, and
  "Other…" turns the last into the typed row.
- One line under it holds the target the suggestion is computed from: "Keep at least
  99 %", a picker, and "What changes" opening the comparison panel at Step.
- The seven-slice overlap diagram goes. The rail shows the same thing at true scale
  (section 7).
- Established when Start, End and Step are each either the measurement's suggestion or
  changed by the owner after the measurement existed.
- Folded: "37,064 – 37,800 · step 10 · 75 planes".
- Not measured: the fields and the table work as today, the step is not green, and the
  line reads "Not measured: step 7 is your setting".

### 4.6 Step 5, Exposure

- **ISO and shutter pickers and the four-shot switch** in one row. They are the state; the
  table under them is the advice.
- **One table of treatments.** Each is two lines: its name and what is shot, then four
  numbers. The current one is marked as the step table's current row is; the suggested one
  carries the lamp. A click applies it.

  | | Body | Glints | Noise | Stack |
  | --- | --- | --- | --- | --- |
  | **Highlight pass**: 2 s, and a group at 1/25 s | 71 % | held | least | 19 min |
  | **Protect highlights**: 1/25 s for everything | 1.4 % | held | +2.8 stops | 5 min |
  | **Accept specks**: 2 s for everything | 71 % | 9,340 pin | least | 14 min |
  | **Yours**: 1/8 s (only when the setting is none of the above) | 4.5 % | some pin | +2.0 stops | 5 min |

  - Body: the subject's diffuse top as a share of full scale at that exposure.
  - Glints: "held", or the subject sites a plane expected to pin.
  - Noise: stops against the row with the most light (final-image SNR rises as the square
    root of the exposure and does not depend on ISO; MEASURED,
    `experiments/capture-implementation-2026-11-20/results.md`).
  - Stack: the whole capture at step 4's plane count, highlight groups included.
- **Highlight groups**: Off, Every plane, Every 2nd, and their shutter, on one row. Shown
  when the current treatment has groups or the owner turns them on.
- **One stillness line**, from the same row: "Still enough: it moves 0.08 px in 2 s", or a
  triangle with "At 2 s it moves about 0.4 px (live view reads high): 1/4 s keeps it under
  a quarter pixel". Each table row whose shutter passes the limit carries the triangle.
- "What changes" opens the comparison panel at ISO and exposure, fed by the same model.
- Established when the current exposure is a row of the table computed from a fresh light
  model.
- Folded: "ISO 100 · 2 s, groups at 1/25 s · body 71 % · glints held".
- Not measured: the pickers, the live estimate's caveat, and one line: "Not measured. Take
  a test shot (T) for the body, or Measure for the body and the glints."
- After a test shot alone: one row, "By the body: 0.4 s", with "one plane, glints not
  separated" as its source. The same function produced it with less to read (rule 2).

Gone from this step: the test-shot sentence and its own "Suggested" line (the readout and
the table carry both), "From the calibration" as a heading, and "Check stillness (20 s)" as
a link (it is a part of the pass, and a link in the opened Measure step).

### 4.7 Run, footer, Start

- **Run**: Check each plane, Retake (with its count), Stack when done, Power down after.
  Two rows of two.
- The footer is unchanged. Start is enabled exactly when `preflight::start_blockers` is
  empty, as today.

---

## 5. The measurement pass

One state machine in the desktop replaces `Calibration`, drives the existing `TestShot`,
`StillnessCheck` and `AutoSubject`, and sends the host commands that exist today. Parts, in
order:

| Part | What happens | Uses today's | Time |
| --- | --- | --- | --- |
| Sweep | The lens steps through the range in live view; no RAW | `Command::Survey` | UNVERIFIED; 33 positions, measure it in P0 |
| Outline | The subject from the sweep's frames, off the UI thread | `AutoSubject` | Seconds |
| Test shot | One RAW at the sweep's sharpest position, read inside the outline; chooses the survey's two shutters; repeated at most twice if it clipped or was nearly black | `capture_positions`, `kind: test`, with a shutter for the position | 8 to 11 s each with the light warm (MEASURED, rig gate Q3) |
| Survey | One RAW a position: the dense cluster and the pairs at two shutters | `capture_positions` with `shutters` | 49 RAWs in 179 s (MEASURED, 2026-11-24, at 1/4 s) |
| Read | `strehl survey` on the run | `strehl survey` | UNVERIFIED on a full survey; seconds on fixtures |
| Restore | Four-shot back, the lens back where it was | `PixelShift`, `Focus` | Seconds |
| Stillness | 20 s of magnified live view, last, so the light has been on longest | `StillnessCheck` | 20 s and the magnifier's switch |

About four and a half minutes (DERIVED from the rows above). On the weevil, bounds from
the subject's depth saved 33 planes (MEASURED, the S4 results), which is about as long.

What changes inside the parts:

- **The survey's shutters come from the test shot** (fixes F4). Long: the shutter that
  puts the body's top near 0.4 of full scale, at most 1 s. Short: five stops under it. If
  the read reports `pinned_short_sites` above zero, the pairs' short frames alone are taken
  again three stops shorter, once.
- **The dense cluster is centred on the sweep's sharpest position**, not the middle of the
  marks (F11). The paired positions spread over the sweep's suggested range, or over the
  marks when the sweep found nothing reliable.
- **A hand-drawn outline is kept.** The pass replaces an outline only when it was automatic
  and not edited since. Otherwise the read is given the owner's outline
  (`strehl survey --subject`), and the readout offers "Use the survey's outline".
- **The survey's RAWs are kept until Start or New capture** (about 3 GB for 49 RAWs if a
  stored RAW is about 65 MB, the plan fixture's figure; ARGUED). A changed outline or a
  changed range is then a re-read of a second or two, not a re-shoot. They are deleted
  when the stack starts, on New capture, and on the next pass.
- **A skipped part says so.** The parts are remembered checkboxes in the opened step; a
  part skipped because its fact is fresh shows "kept from 21:30".

Stopping and failing:

- Stop, a deadline, or a failure ends the pass at once. Facts already measured stay. The
  step names the part that did not finish and offers "Run the rest".
- The camera is put back whatever happens: four-shot, the magnifier, the lens position.
  The shutter needs nothing: a positions run with per-position shutters is restored by the
  Pi. The existing restore paths in `capture-workspace.rs` (`Restoring`,
  `restore_four_after_calibration`) carry over.
- A sweep that reaches its search limit stops the pass before any RAW is taken, with
  "Still sharp at the far mark" and the one-click extension. Shooting a survey over a
  range known to be too short would waste three minutes.
- While the pass runs, Start, Schedule, Edit on Range and the jog buttons are off, and the
  pre-flight strip says "The measurement is using the camera". Escape stops it.

---

## 6. One model, one adviser

### 6.1 Facts

A new module (`capture-measure.rs`) owns what has been measured:

```text
Measurements
  depth    Fact<SubjectDepth>   first/last focus, core range, whether it reaches a mark
  outline  Fact<OutlineInfo>    area share, parts, provenance
  sharp    Fact<SharpDepth>     width (median, 10th, 90th percentile), suggested and edge step
  light    Fact<LightModel>     section 6.2
  motion   Fact<Motion>         movement by time span, drift, source

Fact<T>
  value, taken at, source (live sweep | test shot | RAW survey | live view | remembered)
  context: aperture, range covered, outline's hash, light's power and on-time,
           camera connection, whether the survey's RAWs still exist
  stale: None, or the reason as a sentence
```

Staleness is recomputed each frame from the host's state: a few comparisons, no I/O.

| Change the app can see | Facts that lose their mark | Way back |
| --- | --- | --- |
| Aperture | Sharp depth, body, glints | Measure again |
| The light's power by more than 10 %, or the light switched off and on | Body, glints | A test shot at a surveyed position rescales both (E1); or the survey again |
| Start or End moved outside the surveyed range | Subject depth | Sweep, or measure again |
| Outline edited | Body, glints, subject depth | Automatic re-read while the survey's RAWs exist; else the ring |
| Camera power-cycled (the marks are cleared and the lens has moved) | None; Range needs its marks again | Mark, then "Verify" |
| ISO or shutter | None: the model is in ISO-100 seconds | |
| Older than 30 minutes | None; the age is shown | "Verify" |

What the app cannot see: a moved light, a moved subject, a changed diffuser. For those
there is **Verify**: one test shot at a surveyed position, compared like for like with what
the survey read there (E1). If it agrees within 10 %, the facts keep their marks with a new
time. It takes ten seconds and is offered in the opened Measure step.

### 6.2 The exposure model

All in **ISO-100 seconds**: E = (ISO / 100) × effective seconds, with effective seconds
on the camera's third-stop series as `strehl survey` already reports them.

From a survey (`shutters.long_effective_s`, `shutters.iso`, `body.top`, `census.top`,
`census.margin_stops`):

- `body_full = E_long / body.top`: the exposure at which the subject's diffuse top reaches
  full scale. The pronotum survey of 2026-11-24: 0.25 / 0.0894 = 2.80.
- `glint_full = E_long / (census.top × 2^margin)`: the exposure at which the brightest
  confirmed glint, with its margin, reaches full scale. Same survey: 0.25 / (2.548 × 2) =
  0.049.
- Glints above the body, in stops: log2(census.top / body.top) = 4.8.

For any candidate exposure E:

- body level = E / body_full;
- glints held by one exposure when E ≤ glint_full;
- noise against the best row = 0.5 × log2(E_best / E) stops;
- seconds a plane and a stack from `strehl_capture::timing`, as today;
- movement during the exposure from the motion fact, read at that time span.

The three treatments are then: highlight pass, base at 0.8 × body_full and groups at
0.8 × glint_full; protect, the longest offered shutter with E ≤ glint_full; accept, the
base alone. On the pronotum survey this gives 2.24, 0.039 and 0.049, which are the
engine's own `advice` values (2.236, 0.03924, 0.04905; VERIFIED against
`experiments/subject-highlights-detail-2026-11-23/impl/rig/evidence/survey-pronotum.json`).
Each is snapped to the nearest offered shutter **at the camera's current ISO** (fixes F5).

From a test shot alone, `body_full` comes from that one RAW's brightest colour inside the
outline, and `glint_full` is unknown. The function then returns the one row it can.

**Where the rule lives.** One pure function in `strehl-core`, called by `strehl survey` for
its `advice` and by the desktop for the table, the folded line, the comparison panel and
the control snapshot. `capture-guide.rs`'s `advise`, `exposure_line` and `exposure_rows`
are deleted, not kept beside it.

**Pins for a setting that is none of the three.** Until E3, the "Yours" row says "none"
at or under `glint_full`, "about N" at the accept exposure (the survey's own count), and
"some" between. E3 gives every exposure a count.

### 6.3 Depth and step

Start and End are the survey's `suggested_start` and `suggested_end`. No new rule there.

**The suggested step is computed from retained detail** (the owner's expectation,
2026-11-26). It is not today:

- Today the suggestion is the sharp depth divided by a constant: `SAFE = 7.0` in
  `crates/strehl-cli/src/focus-step-cmd.rs`, "lost nothing measurable on the scarab
  stack" (VERIFIED). No retention figure for the subject in hand enters it.
- A retention measurement exists beside it and only feeds a hover and the marked rows:
  fine detail at the worst tenth of detail tiles, for renders from every k-th plane of two
  stacks (MEASURED, `experiments/capture-implementation-2026-11-20/results.md`). As a
  function of overlap (sharp depth / step) it is `guide::detail_kept`, which takes the
  lower of the two stacks.

The rule: **the suggested step is the coarsest step whose kept detail is at least the
target**, with the target a plan setting, 99 % by default. Kept detail is
`detail_kept(sharp depth / step)`.

| Target | Overlap needed | Step at a sharp depth of 72 | Planes over 736 units |
| --- | --- | --- | --- |
| 99.5 % | 10.6 | 6 | 124 |
| 99 % (default) | 7.1 | 10 | 75 |
| 98.5 % | 4.6 | 15 | 51 |
| 95 % | 3.6 | 19 | 40 |

(DERIVED from the two measured curves by linear interpolation, as `guide::detail_kept`
does; planes by the host's count. Script: `C:/strehl-scratch/plan-flow/step-rule.py`.)

- At 99 % the rule gives what width / 7 gives today: 10 at 72 units, 16 on the scarab's
  113, 7 at 50. So the default changes nothing the owner has seen.
- The curve is nearly flat between width / 7 and width / 5 (99.0 to 98.7 %) and falls
  after that. A target of 98.5 % therefore suggests 15 here: a third fewer planes for
  about a third of a percent of fine detail. The table shows this; the owner picks.
- The desktop computes the suggestion from the survey's `step.width`. The engine's
  `suggested_step` stays as it is for the command line; the two agree at the default
  target to within one unit.

Two limits, both stated on the screen's hover as today ("estimate from two measured
stacks"):

- The curve comes from two stacks, not from the subject in hand. It carries over through
  the measured sharp depth; that it holds for other subjects and lens positions is ARGUED.
  E6 would measure it per subject.
- The survey reports the sharp depth's spread (44 to 92 units around a median of 72 on the
  pronotum). The rule reads the median. In the narrowest tenth of the subject a step of 10
  is an overlap of 4.4, which keeps about 97.8 %. The readout shows the spread; decision 4
  asks whether the rule should read the narrow end instead.

### 6.4 Motion

The stillness check already measures movement over time spans from 0.2 to 8 s
(`capture-stillness.rs`, `Stillness::moves`). The adviser reads that curve at each row's
exposure. Until E4 the source is live view, which read about twice the RAWs' movement
along one axis on 2026-11-25 (MEASURED, the sway series), so the line says "live view
reads high" whenever it warns, and a warning never blocks.

---

## 7. Rail, live view, pre-flight, comparison panel

**The depth rail becomes the depth evidence.** It gains one 14 px lane between the plane
ticks and the bars (148 px in all while planning, 135 today):

- the subject's sharp range as a teal bracket in that lane, labelled with its ends;
- while the pass runs, the survey's positions in that lane: single marks for the dense
  cluster, double marks for the pairs, filled as they are taken;
- the glints by depth as a dashed line with a diamond at each paired position
  (`census.per_position`), in the warning colour, over the bars;
- the sharp depth as a ruler at the lens: a bracket one sharp depth wide that moves with
  the lens, so the plane ticks under it can be counted. This replaces the overlap diagram;
- planes that take a highlight group as taller ticks.

Its head keeps the jog buttons, the scale and Fit. "Survey" and "Survey again" become
"Sweep" and "Sweep again". "Use the survey's bounds" leaves the head; the offer is step 4's
one line. The rail's interactions and its frame-time budgets are untouched: the new layers
are built once per measurement into the mesh the rail already caches.

**Live view.** The tool bar keeps its tools. "Auto" keeps working from the last sweep's
frames. The outline's caption says where the outline came from ("from the sweep, loose",
"from the RAW survey", "drawn by hand"). While the pass runs the state chip reads "Live ·
following the lens" and the magnifier is off until the stillness part.

**Pre-flight strip.** Chips: Rig, Light, Range, Measured, Depth, Exposure, Disk, Receiver,
Subject. Range carries today's Start and End blockers. Measured, Depth and Exposure never
block. They show the lamp or the ring by rule 4, and the ring's hover says why. "Bounds"
and "Step" go; the unapplied-edits and focus-moving blockers move under Depth.

**Comparison panel ("What changes").** Its tabs stay. The ISO and exposure tab is fed by
the adviser of section 6.2.

**Names.** "Sweep": the live pass through focus. "Survey": the RAW part. "Measure": the
whole pass. "Test shot" keeps its name and its key. "Calibrate step" goes. "Outline"
replaces "Auto outline" in captions; the button stays "Auto".

**Keys.** M starts the pass. Escape stops it. S, E, T and Enter are unchanged.

---

## 8. Memory across captures

Two small stores, both plain JSON beside `capture.json`:

- **By setup**: camera, lens as the RAW names it, aperture, and the focus position to the
  nearest 2,000 units, mapped to the last sharp depth and its date. A new subject at the
  same setup then opens with "Step 10 from 24 Nov at this focus (72 units), not measured
  here": a better default than a fixed step, shown with the ring.
- **By catalog subject**: its last measurement and plan, beside the outline it already
  remembers. "New stack of this subject" and "Shoot again" open with them, each fact
  marked by section 6.1's rules, and Verify offered first.

Neither is ever applied silently and neither makes a numeral green.

---

## 9. Control interface

- New requests: `measure` (optionally `parts`), `stop_measure`, `verify_measurement`.
- `calibrate_step` stays and runs the survey and read parts with the camera's current
  shutter, as today.
- The snapshot gains `capture.tools.measure`: the stage, each part's state and time, each
  fact with its value, source, time and stale reason, and the adviser's rows.
  `capture.tools.calibration` and `test_shot` keep their shape, filled from the same state.
- `docs/desktop-control.md` and `scripts/strehl-control.py` are updated in the stage that
  adds each request.

---

## 10. Implementation stages

Each stage is installable on its own and leaves the station working. Desktop work follows
the owner's taste (square, ruled, instrument character) and the Studio 2 smoothness
budgets: nothing here may add I/O, a decode or an allocation per frame to the plan column
or the rail, and every engine call stays off the UI thread. Every stage ends with the UI
tests, an offscreen render of each fixture it touches, and the before and after frame
times of the plan column from the P0 benchmark.

### P0. Baseline and fixtures

- Render `plan`, `plan+survey`, `plan+rig` and `plan+guide` from the build under change at
  1680 × 1050 and 1366 × 768; keep them as the "before".
- Add fixtures for the new states: `plan+range`, `plan+measuring`, `plan+measured`,
  `plan+stale`, `plan+test-shot-only`, `plan+unmeasured`.
- Add a benchmark test that paints the plan column and the rail of `plan+survey` for a few
  hundred frames and reports paint plus tessellation per frame, in the manner of
  `benchmark_finished_workspace_pointer_sweeps`. Capture has none today. Record the result
  with the host's load, as the Studio 2 baseline did
  (`experiments/desktop-studio-2-impl/README.md`).
- Time the live sweep on the rig, once, and record it (the one UNVERIFIED duration of
  section 5).

### P1. One model, one adviser

No new camera work and no layout change beyond the Exposure step's content.

- `capture-measure.rs`: `Measurements`, `Fact`, contexts, the staleness function.
- The exposure function in `strehl-core`; `strehl survey` calls it; the desktop calls it.
- The Exposure step: pickers, the one treatment table, the highlight row, the stillness
  line. Delete `guide::advise`, `exposure_line`, `exposure_rows` and `plan::advice_rows`.
- The comparison panel's exposure tab on the same function.

Gates, each with the input that makes it fail:

- Exactly one row carries the suggested mark in `plan+survey`. Fails on today's build (two
  "Suggested").
- A survey at ISO 100 with the camera at ISO 400 offers shutters two stops shorter than
  with the camera at ISO 100. Fails on today's build (F5).
- The function's three treatments equal the `advice` block of `survey-pronotum.json` and
  of the census fixtures' evidence files, code for code.
- `strehl survey`'s JSON for those fixtures is byte-identical before and after the move.
- With a stillness fact that limits exposures to 1/4 s, the 2 s rows carry the warning;
  with none, no row does.
- A test shot alone yields one row and no highlight pass.

### P2. The column

- Steps Rig, Range, Measure, Depth, Exposure; folded summaries; the open-steps function
  with unit tests over every line of 4.1's list at both window sizes.
- Rule 4's readiness; the pre-flight chips; settle only in Rig; the Run row.
- Depth's single bounds line; the step table's Keeps column, the target and the suggested
  step computed from it (section 6.3); the overlap diagram removed.
- Until P3 lands, the Measure step's button runs today's parts through today's code: the
  sweep, then Auto, then today's two-shutter survey at the camera's shutter. It is already
  one click instead of three.

Gates:

- In `plan+unmeasured` the Depth and Exposure numerals are not green and Start is enabled.
  Fails on today's build (F7).
- In `plan+measured` at 1680 × 1050 nothing in the column is below the footer (the
  existing `nothing_runs_past_the_plan_column` test, extended to height). At 1366 × 768
  the first undecided step is fully visible without scrolling.
- Moving a mark outside the surveyed range, changing the aperture, and changing the light's
  power each put the ring on exactly the facts of section 6.1's table.
- At the default target the suggested step is 10 for a sharp depth of 72, 16 for 113 and
  7 for 50; at 98.5 % it is 15 for 72. A build that still divides by a constant gives 10
  for every target. Compare with a small tolerance: the scarab's own point sits exactly on
  99 %.
- Frame time of the column within the P0 baseline.

### P3. The pass

- The `Measure` state machine with the parts, order, restores, deadlines and "Run the
  rest" of section 5; the test shot choosing the survey's shutters; the dense cluster at
  the sweep's peak; the survey's RAWs kept and re-read; the lens returned.
- `measure`, `stop_measure` in the control interface.

Rig gates, with "manage power" on (the owner's setting):

- From two marks to a filled readout in one click; afterwards the camera reads four-shot,
  the owner's shutter and ISO, the magnifier off, and the lens within one unit of where it
  was.
- Stopped once in each part: the camera is as above, earlier facts are kept, "Run the
  rest" finishes the pass.
- Started with the camera at 1/15 s and again at 2 s on the same subject: `body_full`
  agrees within 10 % between the two. This is the gate that F4 is fixed; a survey shot at
  the camera's own shutter is the failing input.
- Redrawing the outline after the pass refreshes Body and Glints without a new RAW, and
  the survey folder is gone after Start.
- The pass on a subject with the range set too short stops after the sweep with the
  extension offered, and takes no RAW.

### P4. The rail's evidence

The lane, the subject bracket, the survey's positions, the glint line, the sharp-depth
ruler, the taller ticks. Gates: the rail's scrub and zoom frame times within the P0
baseline at a 6,000-plane plan; the bracket and the ruler land on the pixel the scale says
(a test over three zoom levels).

### P5. Memory

Section 8, and Verify. Gate: a second stack of a subject opens with its earlier plan under
rings, and one Verify on an unchanged rig turns them to lamps; with the light dimmed 20 %
it does not.

### P6. Engine and host additions, each optional and gated on its own

| # | Addition | Why | Gate |
| --- | --- | --- | --- |
| E1 | `strehl survey` reports the body's top per paired position (`body.per_position`) | A test shot can then be compared like for like for Verify and for rescaling after a light change | A fixture rebuilt with its long frames scaled by 0.8 rescales `body_full` by 1.25 within 2 %; an unscaled one by under 2 % |
| E2 | `depth` reports whether subject evidence is still rising at the first or last surveyed position | "Still sharp at the mark" from RAW, not only from the sweep | A fixture cut short at one end reports that end; the full one reports neither |
| E3 | `census.tail`: subject sites a plane above each of about 24 levels | A pin count for any exposure, so "Yours" and the comparison panel show a number | The tail at the accept exposure equals `pinned_sites_per_plane`; it is monotonic; a fixture with no highlights gives zeros |
| E4 | `motion` from the survey's pairs: the shift between the long and short frame of a pair, and the long frame's fine-band loss against the short | A stillness reading from frozen RAWs, which the 2026-11-25 series found steadier than live view | Research first, per the workflow: a planted shift and a planted blur on a fixture are recovered, a flat region gives nothing, and the reading is compared with the RAW bursts of 2026-11-25 before any line in the UI uses it |
| E5 | The number of paired positions follows the range: spacing at most 1.5 sharp depths, between 12 and 24 positions | On a deep subject twelve positions pass a glint many planes from its focus, where it reads a fraction of its peak (MEASURED on the weevil: 0.45 of peak at 5 planes, 0.23 at 10), and the one-stop margin no longer covers it (DERIVED) | On the weevil stack, a survey thinned to the proposed spacing recovers the full stack's glint top within the margin; one thinned to twelve does not |
| E6 | Retention measured on the subject in hand: from the dense cluster's per-tile focus curves, the fine detail left half a step from a tile's best focus | The step rule then reads this subject and this lens position, not two reference stacks | Research first, per the workflow: on the scarab and the dark stack it must reproduce the every-k-th-plane renders' figures (the table in the 2026-11-20 results) before it replaces the curve; a flat tile set must report nothing |
| H1 | A host command that sets Start and End to given positions | "Use it" then needs no lens moves; today the desktop drives the lens to each mark in turn | Compatibility test with a host that lacks it; rig check |

---

## 11. What is kept

The rail's scale, zoom, drag and keys; the step table and its hover; the comparison panel;
the Rig step's settings; the live view's tools; the subject and stack names; Schedule;
"New capture"; every host command; `calibrate_step` for agents; the three treatments' names
and rules; the owner's decisions of 2026-11-23 (bounds offered, four-shot highlight
groups, every second plane as the default density).

---

## 12. Decisions for the owner

| # | Question | This design assumes |
| --- | --- | --- |
| 1 | After a measurement on a new subject, apply the suggested bounds, step and exposure, or only offer them? | Revised 2026-11-27: apply to every value the owner has not set (decision 9). The first draft assumed offer. |
| 2 | Is the stillness check part of the pass by default? | Revised 2026-11-27: once the proof plane exists (C1) it takes the check's place in a run (17.8, M2). The 20 s check stays as a tool, and stays in the pass until then. |
| 3 | Keep the survey's RAWs (about 3 GB) until Start so edits re-read instead of re-shoot? | Yes. |
| 4 | Answered 2026-11-26: the suggested step is computed from retained detail (section 6.3). Two values remain. The target: 99 % reproduces today's suggestions, 98.5 % takes a third fewer planes. And where it is read: the subject's median sharp depth, or its narrowest tenth (steps 10 and 6 on the pronotum at 99 %). | 99 %, at the median. Both are settings in the Depth step. |
| 5 | The names: Range, Measure, Sweep, Survey. | As written. |
| 6 | When the sweep finds the subject still sharp at a mark: extend and go on by itself, or stop and offer? | Revised 2026-11-27: extend and go on, up to the lens's ends (17.5, Find). The first draft assumed stop and offer. |
| 7 | Which of section 16's candidate additions to take (C1 to C8)? | Answered 2026-11-27: "gotcha, i like these", with C7 deferred to its own page outside the Capture station (section 18). C1 to C5 and C8 are staged in section 17.12. C6 (settle) is a fact of the rig and is proposed to go with C7; say if it should stay here. |
| 8 | Start means "measure what is missing, then capture", with "Start as it is" for today's meaning? | Yes (17.2). |
| 9 | A value you have not set is applied from the measurement without asking; a value you set is never changed. This changes the decision of 2026-11-23 that bounds are only offered. | Yes (17.3). The flight closing its own ends (17.7) is what makes applied bounds safe. |
| 10 | The glance: the decided plan on screen for ten seconds before the capture begins, with Hold. | On. A recipe setting. |
| 11 | When the run asks first: a capture longer than 45 minutes, or more than half the free disk. | Those two defaults. Recipe settings. |
| 12 | What a run makes at the end: the stack only, the stack with the default look, or also an export with a preset of yours. | Stack, default look, and one export preset named in the recipe. |
| 13 | How the camera is powered during a capture: mains, or its battery? | Not known to this design. It decides whether the battery line (17.10) can block a long run. |
| 14 | A flash of the taskbar button and one sound when a run stops for you or ends. | On. A setting. |
| 15 | The names: Recipe, Find, Prove, Mend, Verdict; the A lamp and "held". | As written. |

---

## 13. Risks and what was not verified

- No rig time was used. The pass's order, its restores and its four and a half minutes
  are DERIVED from parts measured separately.
- The live sweep's duration is UNVERIFIED (P0).
- F5 was read, not exercised.
- The test shot that chooses the survey's shutters reads one plane. A subject much
  brighter elsewhere in depth could pin the survey's long frames. The read already reports
  pinned long frames per position; the pass should say so and offer the survey again one
  stop shorter. UNVERIFIED how often this happens.
- Staleness sees only what the host reports. A moved light or subject is invisible to it.
  Verify exists for that, and the opened Measure step should say so in one line.
- The light's power is a proxy for its output. A 10 % threshold is ARGUED, not measured.
- The census is a lower bound, more so on deep subjects (E5).
- The retained-detail curve behind the step rule is two stacks' worth of evidence, both
  at step 8 on this rig. It is an estimate for any other subject until E6.
- The live stillness reading is known to read high. Until E4 its line must stay advisory.
- The mockups are fixed at 1680 × 1050. The small-window rule of section 4.1 is specified
  and gated, not drawn.
- The mockups' numbers are fabricated to be consistent with one another. The rail's curves
  are drawn by a formula.
- The automatic run (section 17) is a design on paper. Its order is built from parts
  measured separately; none of its thresholds has met a subject. Section 17.12 names the
  gate that sets each one.
- A wrong automatic outline moves the bounds, the exposure and the step together. The
  run's defence is agreement between two readings (17.6) and the glance. A subject that
  fools both the live sweep and the RAW survey in the same way gets through.
- Mending relies on the lens returning to a plane's position after other moves. Retakes
  and highlight passes do this today; how exactly the lens returns is UNVERIFIED here
  and belongs on the Calibration page (section 18).

---

## 14. Ledger rows to allocate before dispatch

This proposal was written in a checkout 42 commits behind `origin/main`, so the ledger was
not edited from it. Add a section "Capture planning flow (2026-11-26)" to
[the milestone ledger](../agents/milestone-ledger.md) on `main` with:

| Identifier | Scope |
| --- | --- |
| capture-planning-flow-2026-11-26 | This design and its mockups. Done 2026-11-26, design only. |
| cpf-p0-baseline | P0 |
| cpf-p1-adviser | P1 |
| cpf-p2-column | P2 |
| cpf-p3-pass | P3; a rig run with the host commands the Pi already has (no deploy) |
| cpf-p4-rail | P4 |
| cpf-p5-memory | P5 |
| cpf-e1 … cpf-e6, cpf-h1 | One row each when taken up; E4 and E6 follow the research workflow |
| cpf-c1-proof … cpf-c5, cpf-c8 | The accepted candidates of section 16, one row each; C8 follows the research workflow |
| cpf-p7a … cpf-p7e | The automatic run, section 17.12 |
| cpf-e7 … cpf-e10, cpf-h2 | Section 17.12's additions; E7, E8 and E10 follow the research workflow |
| (not allocated here) | The Calibration page, section 18: its own proposal and its own rows |

---

## 15. Evidence

- Code read at `b2c8a07aa`: `capture-plan.rs`, `capture-guide.rs`, `capture-tools.rs`,
  `capture-workspace.rs`, `capture-station.rs`, `capture-preflight.rs`, `capture-live.rs`,
  `capture-rail.rs`, `capture-stillness.rs`, `capture-test-shot.rs`, `capture-fixture.rs`,
  `app-station-capture.rs`; `crates/strehl-capture/src/bounds.rs`, `session.rs`,
  `worker.rs`.
- Offscreen renders of the installed desktop (`Strehl.exe --offscreen-screenshot … --route
  capture --capture-fixture plan | plan+survey | plan+rig | plan+guide`, an isolated catalog
  copy and a fresh capture-settings path, 1680 × 1050 and 1366 × 768). Kept in scratch,
  `C:/strehl-scratch/plan-flow/`.
- Earlier results: the [subject and highlights plan](2026-11-subject-highlights-and-detail-plan.md)
  and its [implementation log](../../experiments/subject-highlights-detail-2026-11-23/impl/README.md);
  the survey's [results](../../experiments/subject-highlights-detail-2026-11-23/impl/census/results.md)
  and the rig survey `survey-pronotum.json`.
- Mockups: [`experiments/capture-planning-flow-2026-11-26/mockups/`](../../experiments/capture-planning-flow-2026-11-26/mockups/README.md).

---

## 16. Candidate additions to the calibration

Raised 2026-11-26 after the first draft, in answer to the owner's question of what the
calibration still lacks. The order is the recommended one.

The owner's answer, 2026-11-27: "gotcha, i like these. tbh, i think #7 should be its own
whole page, to do the other calibrations required as well, to cconfigure strehl properly
for the camera's profile. right now, that's very bespoke. i would defer this one though,
outside the scope of the Capture screen, into its own." So C7 leaves this proposal
(section 18), and the others are staged in section 17.12. Reading "i like these" as
acceptance of C1 to C6 and C8 is this document's reading; decision 7 records it.

The common thread of the first three: the pass measures inputs and predicts. Nothing
confirms the prediction at the final settings, nothing shows what the final picture will
contain, and nothing measured reaches the capture or the render.

| # | What is missing | Evidence | What to add | Cost |
| --- | --- | --- | --- | --- |
| C1 | **A proof plane.** The pass shoots single RAWs. The four-shot group, the highlight group and their fusion are never exercised before Start, so a green plan can still retake or demote plane after plane. | A 1 s close-tile capture took 95 groups and 51 manual retakes for 24 planes; 4 of 21 highlight groups were refused for sway (MEASURED, the subject plan's Q5 and its implementation log) | After the exposure is chosen: one plane exactly as planned (the base group, then the highlight group, at the sharpest position), run through the capture's own plane check and ratio fit. It reports the body level against the prediction (which is also Verify), pins in the base group, whether the highlight group holds, the members' offsets from frozen RAWs, real seconds a plane and real bytes a RAW, and can show a 100 % crop. The members' offsets are the stillness reading that matters and replace E4's research | One plane: 11 to 19 s at 2 s (MEASURED per-plane times) plus the check. One positions run, the position twice with two shutters, four-shot on: the host accepts repeated positions with a shutter each today (VERIFIED, `two_shutter_survey`); at four-shot it is UNVERIFIED |
| C2 | **The final frame.** Magnification changes through focus, and the merge by default shrinks the field of view to what every frame covers and upsamples (VERIFIED, the `cover` field's comment in `merge_cmd.rs`). The picture that comes out is smaller than the one framed in live view, and nothing says so before the capture. | -17.6 ppm a unit on the pronotum survey, about -13 on the weevil (MEASURED): 4.2 % over 2,400 units, 1.8 % over the weevil's 1,393 (DERIVED) | Once the rate is measured (`subject.ppm_per_unit`), draw the covered frame on the live view with its share ("the final frame: 96 % of this"), and put the triangle on the outline where it crosses that frame. The Depth step's bounds line says what tighter bounds give back | Arithmetic and one rectangle. No camera work |
| C3 | **The measurement reaches the capture and the render.** It lives in the desktop's memory. The manifest's plan records the outline and the highlight groups only (VERIFIED, `Plan` in `crates/strehl-capture/src/model.rs`). | Optical restoration was skipped on the weevil and is skipped on the 2 s pronotum capture, where every measured tile is near clipping (the implementation log's open list). The survey's dense cluster is unclipped, in focus and at the capture's lens position | Write the facts, their conditions, the chosen plan and the proof plane's result beside the manifest, so the Stack station can show what a stack was planned on. Then, as an experiment with its own gate: seed the optical cutoff store from the survey's dense frames, and give the render the body's diffuse level the survey measured with the glints set aside | The record: small. The cutoff seed needs an engine entry point; whether the fit works on single-shot survey frames is UNVERIFIED |
| C4 | **A look at both ends.** Both the sweep and the survey threshold on area and energy. The host's own text says "fine or low-contrast features may be missed", and the mask drops parts under 0.2 % of the frame (the subject plan, S2). Antenna tips and setae are such parts. | ARGUED; no case measured | Two links in the Depth step, "Look before Start" and "Look past End": each drives the lens just outside the mark with peaking on, and returns | UI only |
| C5 | **What the survey already measures and nobody sees.** The light's steadiness, the drift over the pass, the link's real speed, a RAW's real size. | The light moved 5 % between groups and one frame read 7 % bright (MEASURED, the census results); the picture drifts 1 to 2 px a minute after the light comes on (MEASURED, 2026-11-25); the disk estimate reads the newest earlier capture, not this subject | Three more rows in the readout: "Light steady within 1.4 %" from the twelve measured ratios (`ratio.per_position`); "Drift 0.4 px a minute" from one more RAW at the survey's first position at its end; the finishing time and the disk line from the survey's own transfer rate and file sizes | One extra RAW; the rest is already in the survey's output or the receiver's receipts |
| C6 | **Settle, measured on the rig as it stands.** Settle is chosen from a table whose "Passed" column is a set of constants from 2026-11-20 (VERIFIED, `SETTLE_MEASURED` in `capture-guide.rs`). The pass measures the picture at rest, not how long it takes to come to rest after a move. | The table's own numbers; the rig has changed since and is about to change again | In the stillness part: command a one-step move a few times under the magnifier and time the return to the at-rest level. Live view's bias cancels, because the reading is compared with its own floor | About 30 s of live view. Low value today, since up to 500 ms is free behind the last RAW's fetch; it becomes first-order with a stage that moves the subject |
| C7 | **Moved out 2026-11-27, to section 18.** A rig calibration beside the subject's. Some facts belong to the lens and the rig and are measured once: magnification by lens position, settle, the light's warm-up, the sharp depth by lens position (section 8). The design has only the per-subject pass. | The scale is typed in or measured from a slide for each subject, and nothing reads magnification from the RAW (VERIFIED, the scale's schema in `agent-mcp.rs`) | A "Rig calibration" action in the Rig step's settings: the calibration slide shot at a few lens positions gives micrometres a pixel for every later subject at any position, so the scale bar and "sharp over 0.21 mm" need no typing | A one-time session with the slide the owner already has. Needs a slide-reading measurement: research first |
| C8 | **The subject's tilt.** Depth is what the capture's time is made of, and re-posing the specimen is the only thing that changes it. The sweep already yields a coarse map of which area is sharp where. | ARGUED; not measured on any stack | Show that map on the live view (near to far), fit a plane to it, and say what part of the depth is tilt: "Levelling the left end by 300 units would take 75 planes to about 40" | The map exists; the fit and its wording need an experiment on the owner's stacks before any number is shown |

Looked at and left out: aperture advice (the owner shoots wide open); ISO (final-image
noise does not depend on it; MEASURED); a flat-field capture (the stack's own frames
build one). Two smaller items sit under the ones above: the highlight groups' density is a
default, not a measurement (the proof plane and the flight's own count catch it), and the
A7CR's white level reads 15360 in the engine while the data reach 16383 (the census
results), which should be settled before a pin count is trusted to the last few percent.

---

## 17. The automatic run

Added 2026-11-27. The owner, after sections 1 to 16: "i want it to be as automatic as
possible. set the minimumum info needed, press a button, get a great macro stack e2e.
that's the idea."

Sections 3 to 9 describe a column the owner works through. This section makes the same
column something the app works through by itself, from a framed subject to an exported
picture. No step is withdrawn. Each can still be opened and set by hand, and a value set by
hand is kept. What changes is who fills the column in by default, what Start means, and
what happens when a prediction turns out wrong.

Three ideas carry it.

1. **Automatic unless held** (17.3). This is rule 6 as revised.
2. **Ask early or never.** Everything that can need the owner is found in the first
   minutes, before the long part. Once the capture has begun the run does not stop for a
   question. It mends what it can and reports the rest.
3. **Predict, check, mend.** Each prediction the plan stands on is checked by a second
   reading before the capture (17.6). The flight then corrects what the plan still got
   wrong, while the subject is on the stage (17.7).

### 17.1 What the owner gives

| The owner gives | How | Why the app cannot |
| --- | --- | --- |
| The subject on the stage, framed, with some part of it in focus | By hand, in live view | The framing is the picture, and on this lens the focus position sets the magnification |
| The light | By hand | It is the picture too |
| A name | Typed. An unnamed subject blocks Start today (VERIFIED, the test `an_unnamed_subject_blocks_start_and_its_chip_says_so`); that stays | The catalog needs it |
| A recipe | Chosen once and remembered (17.4) | Taste: how much detail to keep, what to do about glints, what to make at the end |

Everything else is measured, or decided from a measurement: the outline, the range, the
step, the exposure, the highlight groups, and when the rig is at rest.

### 17.2 One button

There is no new button. **Start does whatever the plan still lacks, then captures.** The
line above it says what that is, so pressing it is never a surprise:

- nothing measured: "Find the range, measure, prove, capture, stack, export · about 25 min
  (from the last capture at this setup)";
- measured and decided: "Capture 75 planes, stack, export · 19 min";
- everything held by hand: "Prove, capture 75 planes, stack · 19 min".

"Start as it is" is a link beside Start (Shift+Enter). It captures with the settings as
they stand and measures nothing, which is what Start does today. Schedule takes the same
two forms.

The Measure step's own button stays. It runs the pass and decides, and does not capture.

### 17.3 Automatic or held

Every value of the plan is in one of two states, as on a camera's dials.

- **A**: it follows the measurement. The field carries a small A lamp. When its fact
  arrives the value is set, and when the fact is measured again the value follows.
- **Held**: the owner set it. Nothing changes it. Its row shows what the measurement
  gives ("held at 7 · the measurement gives 10"), and a click on the lamp gives it back.

The values: the outline, Start, End, the step, the exposure with its treatment and
highlight groups, and settle. Typing in a field, dragging a mark, drawing the outline or
clicking a table row holds that value. "New capture" returns every value to A. A recipe
can hold a value for every capture (a fixed ISO, say).

A step's numeral is green by rule 4 as before: an A value on a fresh fact is established,
and so is a held value set in view of one.

For values on A this replaces the "Use it" offers of sections 4.5 and 4.6. Those lines
then state what was done ("Start and End set from the subject's sharp range: 12 fewer
planes"). The offer remains on a held value only.

### 17.4 The recipe

A named set of standing choices, kept with the capture settings. One is the default, and
one may be all the owner ever has.

| Choice | Default | Feeds |
| --- | --- | --- |
| Keep at least | 99 % of fine detail | The step (section 6.3) |
| Glints | Hold them when the adviser suggests it. Others: always hold, let them pin | The treatment (section 6.2; today's rule is `suggested` in `survey-cmd.rs`) |
| Four-shot | On | The exposure step |
| Finish | Stack, the default look, export with a named preset | 17.9 |
| Ask me first | Above 45 minutes, or above half the free disk | 17.5, Decide |
| Check and retake | On, up to 2 retakes | The flight |
| Glance | Ten seconds before the capture | 17.5, Prove |
| Power down after | Off | 17.9 |
| Held values | None | 17.3 |

The recipe is the only place taste enters a run. It is shown folded at the top of the
column as one line ("Recipe · keep 99 % · hold glints · export Archive") with Edit. The
Run row of section 4.7 stays where it is: its four switches are the recipe's, shown and
changeable for this capture.

### 17.5 The stages

| | Stage | What it does | It stops for the owner when |
| --- | --- | --- | --- |
| 1 | **Find** | Sweeps around where the lens stands. If the subject is still sharp at one side of the window, widens that side and sweeps again, as far as the lens's ends. Then the outline from the sweep's frames | Nothing sharp is found; the lens's end is reached with the subject still sharp; the outline is empty |
| 2 | **Measure** | The pass of section 5 from the test shot on, shortened by 17.8 | The survey cannot be read; two readings disagree (17.6) |
| 3 | **Decide** | Sets every value on A from the adviser and the step rule | The plan passes the recipe's "ask me first" limits; the disk does not hold it |
| 4 | **Prove** | The proof plane (C1) at the decided settings. If its shots moved: waits a minute and proves again, twice; then proves one stop shorter, twice (17.8, M2). Last, the glance: the final plan on screen for ten seconds | It still moves; the highlight group is refused three times; the exposure is held and its proof moved; the owner presses Hold during the glance |
| 5 | **Capture** | The flight as today: every plane checked, failed planes retaken | The rig fails (as today). Nothing else |
| 6 | **Mend** | With the subject still on the stage: retakes still owed; a highlight pass over planes that pinned with no group; more planes past an end that is still sharp (17.7) | Never. What could not be mended goes into the verdict |
| 7 | **Finish** | Stack, look, export, verdict (17.9); then power down if the recipe says so | Never |

Stages 1 to 4 hold every question the run can ask. They take about five minutes on a new
setup and two to three on a known one (17.8). The owner can stay for those and leave, or
leave at once and find either a picture or one question waiting.

**Find, in detail.** The first window is the catalog subject's last range when it has
one, else 1,000 units either side of the lens. (The weevil's stack spans 1,393 units,
MEASURED; a 2,000-unit window puts the sweep's 33 positions 63 units apart, under the
pronotum's sharp depth of 72.) The host's sweep already reports when focus support
reaches a search limit (`suggestion.clipped`, VERIFIED in `bounds.rs`). On that report the
desktop widens the clipped side by the window's width and sweeps again, at most three
times. A sweep is 33 positions, each a move, the settle, and four fresh preview frames
(VERIFIED, `scan` in `worker.rs`): of the order of 40 s (DERIVED from that loop at a
500 ms settle; UNVERIFIED on the rig, P0 times it). Find needs H1 (marks set to given
positions), which becomes a requirement instead of an option. A range held by hand is not
widened: the run stops and asks, as section 5 says.

### 17.6 The run checks itself

A run that asks nothing must know when it should not be trusted. It never judges a single
reading. It compares two readings of the same thing, and a disagreement is the only reason
it asks.

| Thing | First reading | Second reading | Disagreement |
| --- | --- | --- | --- |
| Outline | The live sweep's | The RAW survey's | They share under half their joint area |
| Range | The live sweep's | The RAW survey's subject depth | The survey's range leaves the swept window (then Find again, once) |
| Body level | The test shot | The survey's long frame at that position | More than 20 % apart: the light moved during the pass |
| Exposure | The adviser's predicted body level | The proof plane | More than 20 % apart (then Measure again, once) |
| Stillness | None before the capture | The proof plane's shots | The capture's own plane check fails them |
| Bounds | The plan | The flight's first and last planes | Still sharp at an end (mended, 17.7) |
| Step | The retention curve | The stack's own focus curves | Detail kept under the target (reported, and learned from: 17.8, M6) |

The thresholds are ARGUED, and each is set in its stage on the owner's captures. The
table is the design; its numbers are placeholders.

### 17.7 The flight corrects the plan

Before the capture, the range rests on 33 preview frames and 13 RAWs, and the glints on
twelve positions. During it, the checker reads every plane. The flight is the better
instrument, so three of the plan's values can be closed by it instead of predicted
exactly.

- **Ends.** The checker reports, for the first and last three planes, the share of the
  subject's tiles that are sharpest at the very end plane, which is what a subject running
  past the end looks like (E8). When that share is above its threshold at the far end, the
  host goes on past End a few planes at a time until it falls, up to a quarter more planes
  or the lens's end. At the near end the same is done as a pass after the last plane,
  approached as the capture's first plane was. This needs a host command that appends
  planes to a capture (H2): `QueuePass` covers planes the capture already has (VERIFIED,
  `session.rs`). With this the automatic bounds can be tight without being a risk, which
  is what lets decision 9 apply them.
- **Glints.** Planes whose base group pinned and that have no highlight group get one
  highlight pass after the last plane. This exists as a button
  (`FlightIntent::HighlightPass`, plan X5, VERIFIED); the run presses it. So the groups
  need not be planned over the whole stack (17.8, M4).
- **Planes.** Retakes as today. A plane that failed every retake is stacked as the flight
  already does and is named in the verdict.

What the flight cannot correct is the exposure, because every plane must share it. That is
why the exposure, and only the exposure, has to be right before the capture, and why the
proof plane is there.

### 17.8 Changes to the measurements themselves

| # | Change | Why | Label |
| --- | --- | --- | --- |
| M1 | **The range is found, not marked** (17.5). Two marks stay possible and hold the range | It is the one input that needs the owner's hands on the lens twice | The parts exist; the loop is new |
| M2 | **The proof plane is a run's stillness measurement and its rest gate.** It is repeated after a wait before anything else is tried, then one stop shorter. The 20 s live check leaves the run and stays a tool | The live check reads about twice the RAWs' movement along one axis (MEASURED, 2026-11-25) and needs the magnifier. After the light comes on the picture drifts 1 to 2 px a minute (MEASURED): 0.2 to 0.4 px across an 11 s group (DERIVED), against 0.06 to 0.10 px between the shots of a group at rest (MEASURED on the slide). Waiting cures drift and a shorter exposure cures sway; the proof plane tells which was needed | ARGUED from those measurements |
| M3 | **Find out what the sharp depth measures** (E7). Each 64 px tile's focus curve is the lens's response widened by the depth the subject spans inside that tile. A sloping subject then reads a wider "sharp depth" than a flat one through the same lens. The step rule divides by that figure, and its constant was fitted on one subject's median | The pronotum's tiles spread from 44 to 92 units around 72 (MEASURED), which slope inside tiles would produce. If so, the narrow end is the lens and the median is the subject; decision 4's second question has an answer; and a steep subject gets too coarse a step today | ARGUED. Research first: the same stacks re-read at 64, 32 and 16 px tiles, and a flat target |
| M4 | **Highlight groups go where the glints are.** The adviser sets the groups' first and last plane from the positions whose long frames pinned, one sharp depth of margin each side | The host takes a span (`Highlight.first_plane`, `last_plane`); the desktop always sends the whole stack (`first_plane: 1, last_plane: u32::MAX` in `capture-station.rs`, VERIFIED). A glint reads 0.45 of its peak five planes from its focus (MEASURED, weevil), so glints are local in depth. A plane without a group takes 11.3 s instead of 19.0 s (MEASURED). The mend stage covers a plane the span missed | DERIVED |
| M5 | **The survey shoots its short frames only where the long ones pin.** The twelve long frames first; a short frame only at the positions that pinned | On a matte subject none pins and twelve RAWs are saved; `glint_full` then comes from the long frames, which hold the glints unclipped. Needs `strehl survey` to read a run whose pairs are partly single (E9) | UNVERIFIED that the read accepts it |
| M6 | **Every stack measures its own retention** (E6, widened). After a capture each tile's focus curve is known at the full plane spacing. Thinning those curves to every second and third plane gives the detail a coarser step would have kept on this subject, with no render | The step rule then learns from every stack of the owner's, by setup, instead of resting on two reference stacks. It is also the check of the step in 17.6 | Research first, with E6's gate |
| M7 | **The dense cluster only when the setup has no sharp depth.** With a remembered figure for this lens, aperture and focus position under 30 days old, a run skips the 25 dense RAWs and says so ("step 10 from 24 Nov at this setup"). The step's numeral then carries the ring, not the lamp (section 8) | The cluster is 25 of the survey's 49 RAWs: about 90 s of its 179 s if every RAW costs the same (DERIVED). It depends on E7, because only a figure that belongs to the lens may be carried to another subject | ARGUED |
| M8 | **The focus axis is a fact.** The model names the axis it moves (lens focus today), with its unit, its ends, its magnification rate, its settle and how exactly it returns | A stage that moves the subject is being planned. With one, magnification does not change through the stack (C2's shrink goes), positions are lengths, and framing no longer sets the focus position. Naming the axis now costs a struct; finding the lens's behaviour spread through the pass later costs a rewrite | ARGUED |

With M2, M5 and M7 a run's measurement on a known setup is the sweep, the test shot,
twelve to twenty-four RAWs and the proof plane: two to three minutes instead of four and a
half (DERIVED from the survey's 3.7 s a RAW and the sweep's estimate; UNVERIFIED).

Considered and left out, or left for later: a third level in the exposure model for the
backdrop (whether it clips at the chosen exposure; my idea, not measured on any stack); a
step that varies through the stack; an output-size choice that trades planes for
resolution (the owner's standing aim is the camera's full resolution).

### 17.9 Finish and verdict

- **Stack** as today ("Stack it when the capture finishes").
- **Look**: the Develop defaults, which already take white from the subject's diffuse
  level when the capture has an outline (plan X6) and the "Safe" detail strength (D2). No
  new processing.
- **Export**: one preset from the export presets library (`export-presets.rs`), named in
  the recipe. None named: no export.
- **Verdict**: one line with its evidence under it, in the Captured inspector and in the
  record beside the manifest (C3). Either "Good: 75 planes, all placed, none failed,
  glints held, both ends closed", or what is not: "3 planes stacked from one shot (31 to
  33)", "still sharp at End", "detail kept 97.6 %, under the 99 % asked". Each line a
  re-shoot can fix carries the Stack station's existing "Re-shoot…" (R1 to R4).
- **Power down** comes after the verdict, and only when the recipe asks. A mend the run can
  do by itself is done before it.

The record beside the manifest (C3) also holds what the run decided and on which reading.
It is the place to look when a run chose badly.

### 17.10 What an unattended run needs besides

- **To tell the owner.** No call that asks for attention outside the window was found in
  `crates/strehl-ui/src` (a search for toast, notification and attention finds only the
  agent interface's protocol messages; VERIFIED by that search). Add a flash of the
  taskbar button and one sound when a run stops for the owner or ends (decision 14).
- **The battery.** The host reports it (`battery` in the snapshot) and the desktop reads
  it nowhere (VERIFIED: its only uses are the field and its name in `capture-host.rs`).
  Add a pre-flight line, and a stop at Decide when it is low and the plan is long. How
  the camera is powered decides the threshold (decision 13).
- **The light's first minute.** The light dims 9 % in its first minute (MEASURED). The run
  sweeps during it and waits for the minute to pass before the test shot.
- **Time and disk from this subject.** C5's real transfer rate and file size, so the "ask
  me first" limits compare against the truth.

### 17.11 The screen

Drawn in the fifth mockup state,
the automatic run.

- **The run strip.** A ruled strip of seven segments under the names: Find, Measure,
  Decide, Prove, Capture, Mend, Finish. Done segments are filled; the current one carries
  the half mark. It is the pass's progress line of section 4.4, extended.
- **The steps fill themselves.** Each step folds with its result as its stage completes.
  The stage in hand is open with its readout. The column needs no scrolling during a run,
  because at most one step is open.
- **A and held.** The A lamp sits at each value. A held value has no lamp and a second
  line with the measurement's value.
- **A question.** The step that needs the owner opens with the question in one sentence
  and two buttons, the pre-flight strip shows the diamond on that chip, and the taskbar
  flashes. Nothing else on the screen moves.
- **The glance.** After the proof, the footer reads "Capturing in 8 s" with Hold and
  "Capture now". The final plan is in the folded steps above it.
- **The footer.** The line that says what Start will do (17.2), Start, "Start as it is",
  Schedule.

The owner's taste and the smoothness budgets of section 10 apply unchanged. The strip is
static geometry rebuilt on a stage change, never per frame.

### 17.12 Stages, gates, additions

The accepted candidates of section 16, placed:

| Candidate | Where |
| --- | --- |
| C1 proof plane | Its own stage after P3; P7c depends on it |
| C2 final frame | P4, with the rail's evidence |
| C3 record beside the manifest | P5 for the record; the cutoff seed is E10, research first |
| C4 a look at both ends | P2 (two links). In a run, 17.7 does the same job by measurement |
| C5 light steadiness, drift, real rate and size | P3, three readout rows |
| C6 settle measured | Proposed to move to the Calibration page with C7 (decision 7) |
| C8 tilt | Research first; then P4 |

The run itself, each part installable alone:

| Stage | Content | Needs |
| --- | --- | --- |
| P7a | A and held on every value; Decide applies; Start fills in what is missing using the parts that exist (two marks still needed); "Start as it is"; the footer's line | P2, P3 |
| P7b | Find: the window, the widening, the range with no marks | H1 |
| P7c | Prove as the rest gate; the glance; the recipe and its limits; the notification; the battery line | C1 |
| P7d | Mend by itself (retakes owed, the highlight pass); Finish (look, export preset); the verdict; the run strip | P7a |
| P7e | The flight closes its ends | E8, H2 |

Gates, each with the input that makes it fail:

- On the demo camera, from a framed subject and a name: one press of Start ends with an
  export file and a verdict, and no other input. Fails today (Start is blocked with no
  marks).
- A step held at 7 survives a run: the manifest's plan has 7 and the row shows what the
  measurement gives. A build that applies over held values fails it.
- A demo subject deeper than the first window: Find widens once and the bounds contain the
  subject. A subject past the lens's end: the run stops in Find and takes no RAW.
- A plan over the recipe's time limit stops at Decide, before the proof plane.
- A proof plane with a planted shift between its shots: the run waits and proves again.
  With the shift on every proof it stops before the capture and no plane is taken.
- Nothing stops after Capture begins: a plane that fails every retake produces a verdict
  line and the run still reaches Finish.
- An outline from the sweep and one from the survey that share under half their area stop
  the run at Measure. A matching pair does not.
- Rig gate: one real subject from framed to exported file with no input after Start, each
  stage's time recorded, and the same subject by hand (section 4's column) for comparison.

Additions:

| # | Addition | Why | Gate |
| --- | --- | --- | --- |
| E7 | The sharp depth by tile size (64, 32, 16 px), and on a flat target | M3: is the figure the lens's, or the lens's widened by the subject's slope | Research first. A synthetic stack of a tilted plane with a known blur must read wider at 64 px than at 16; a flat one must read the same at all three |
| E8 | The plane checker reports the share of subject tiles sharpest at an end plane | 17.7: the flight closes its ends | A stack cut short at one end reports that end; the full stack reports neither; a backdrop with texture of its own must not trigger it |
| E9 | `strehl survey` reads a run whose pairs are partly single | M5 | A fixture with the short frames removed where the long did not pin gives the same `advice` as the full fixture |
| E10 | The optical cutoff store seeded from the survey's dense frames (from C3) | Restoration was skipped on two captures for want of unclipped tiles | Research first, as C3 states |
| H2 | A host command that appends planes past either end of the latest capture | 17.7 | Compatibility with a host that lacks it; a rig check that appended planes register with their neighbours |
| H1 | Now required (was optional): marks set to given positions | Find | As in P6 |

---

## 18. Deferred: a Calibration page

The owner, 2026-11-27: C7 "should be its own whole page, to do the other calibrations
required as well, to cconfigure strehl properly for the camera's profile. right now, that's
very bespoke. i would defer this one though, outside the scope of the Capture screen, into
its own."

So it is not designed here. This section only keeps what this proposal found that belongs
there, so that it is not lost. Each is a fact of the camera, the lens or the rig, measured
once and then used by every capture.

| Fact | Used here by | Today |
| --- | --- | --- |
| Magnification by focus position (from the calibration slide) | C2's final frame; the scale bar; depth in millimetres | Typed or measured for each subject (VERIFIED, the scale's schema in `agent-mcp.rs`) |
| The lens's sharp depth by focus position and aperture | The step rule; M7 skips the dense cluster | Measured on each subject, possibly mixed with the subject's slope (M3) |
| Settle after a move (C6) | The Rig step's settle | Constants from 2026-11-20 (`SETTLE_MEASURED`) |
| How exactly the focus axis returns to a position | Mend, retakes, appended planes | Not measured |
| The light's warm-up: level and drift against minutes on | The run's wait before the test shot; the rest gate | Two measurements in results notes |
| The sensor's white level | The pin counts | The engine reads 15360; the data reach 16383 (the census results) |
| The camera profile's own data (noise model, levels, four-shot registration, flat field) | Everything | Produced by hand; "very bespoke" in the owner's words |

Until that page exists this proposal does not depend on it: every fact above has the
fallback named in its row.
