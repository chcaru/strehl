# Strehl Studio 2: the desktop re-formed around the life of a photograph and the depth of a stack

**Status:** Proposal, second iteration (2026-11-21). Nothing here is built. The mockups are
design intent, not application code. Section 13 records what the owner asked for after the first
iteration and what changed.
**Date:** 2026-11-20, revised 2026-11-21.
**Owner's question:** the desktop began as a focus stacker and now also captures, diagnoses,
edits and exports. Take stock of the whole flow, interface and experience, and propose how to
re-integrate and redesign it into a graceful, capable macro studio: theme and style, layout and
organisation, workflow features, missing gaps. Think big; show the visual ideas as mockups.
**Scope:** the desktop workspace (`crates/strehl-ui`), with the engine, the editing model and
the camera host named only where a proposed display needs something they do not yet provide.
**Audience:** the owner, then an implementing agent.
**Mockups:** [`experiments/desktop-studio-2026-11-20/mockups/`](../../experiments/desktop-studio-2026-11-20/mockups/README.md),
built into one interactive HTML file (thirteen screens, three themes).
**Evidence labels:** MEASURED (from the catalog or from pixels of offscreen renders), VERIFIED
(read in source by the author, with file and line), REPORTED (read in source by a delegated
inventory with file and line, not re-read by the author), ARGUED, UNVERIFIED.

## 1. Summary

The application is capable and carefully made. Its difficulty is arrangement. Each capability
arrived as another pane beside the last, so the window is organised by the order features were
added and speaks the engine's vocabulary. After a stack, the photograph occupies 8.1 % of the
window (MEASURED, section 3). Starting a capture depends on ten conditions the screen does not
show (VERIFIED). The owner's library holds seven stacks named "100MSDCF" (MEASURED).

The proposal has one organising idea and one signature instrument.

- **The organising idea is the life of a photograph.** A subject has stacks; a stack has
  renders; a render has versions; a version has exports. Five stations follow that order:
  Library, Capture, Stack, Develop, Export. The stations are the navigation, and each one shows
  its state for the open stack.
- **The signature instrument is the depth rail.** Depth is what every part of the application
  is about: it is the lens travel when planning, the planes filling in while shooting, what
  each plane contributed when checking, and the planes to take from when repairing. Today's
  timeline already charts it well, at the foot of the Process view. The rail takes that chart
  and makes it one component, drawn the same way on every station.

Around these sit eight further moves, each with a mockup screen:

| # | Move | In one line | Screen |
| --- | --- | --- | --- |
| 1 | Depth rail | One instrument for depth, everywhere | Stack, Capture, Develop |
| 2 | Lenses and the core sample | Hover a plane: the photograph shows where it was kept. Hover the photograph: a region's sources open beside it | Stack |
| 3 | Checks in plain words | A count and a list of measured facts, each with its evidence and an action | Stack |
| 4 | Flight plan and pre-flight | Capture as four numbered steps and a strip that names what is missing | Capture, plan |
| 5 | The proof | The picture comes into focus on screen while it is shot | Capture, in flight |
| 6 | Job tray and glance mode | Every long task has the same five states and one home | Glance, any top bar |
| 7 | Subjects with a lifecycle | The library by what was photographed, with lineage | Library, Subject |
| 8 | Depth brush and macro finishing | Repair by painting, then heal, clean the backdrop, crop, add a scale bar | Develop |
| 9 | Presets and batches | One photograph leaves as several files | Export |

Section 9 phases the work so that every phase ships on its own. Phase 0 is a dozen small
changes to today's code that need no redesign and remove the worst friction.

## 2. How this was done

- **Screens.** Twelve offscreen renders of the installed desktop at 1680 × 1050
  (`Strehl.exe --offscreen-screenshot`, the path `scripts/strehl-control.py screenshot` wraps),
  against a copy of the owner's catalog in a scratch folder: a finished 299-plane stack in the
  default, Edit, Export, Projects and Agent states, a 1,488-plane stack, an unstacked bracket,
  camera metadata, Capture with the rig off, and the empty state. The interactive catalog was
  not opened.
- **Source inventories.** Four delegated read-only readings of `crates/strehl-ui/src`
  (capture; process and diagnostics; shell, library, Adjust and jobs; Edit, Export and Agent),
  each returning labels, states and flows with file and line. Twenty of their claims were
  re-read by the author; all twenty held. Those are marked VERIFIED below, the rest REPORTED.
- **The incident.** The same day's "Calibrate step" hang (commit `2d18c6b31`) is used as a
  worked example of a class of problem: a long task waiting in silence.
- **Not done.** No usability sessions; there is one user, the owner, and this is argued from
  the inventory and from incidents. No application code was written. Nothing was built or
  benchmarked.

## 3. Where version 1 stands

### 3.1 What to keep

- **The engine's honesty.** Diagnostics state what they are and are not ("not a winning-frame
  map", "not a quality score"; `run-review.rs:1` opens with "No inferred quality grade",
  VERIFIED). Version 2 keeps every one of those cautions; section 5.3 says how.
- **Linked exploration.** One shared state drives pin, zoom region, detail size, inspected
  capture and pinned ranges across every panel, with undo (REPORTED, `process-theater.rs:60-74`).
  The depth rail and core sample are built on it.
- **The photograph viewer.** Overview plus a progressively refined detail patch, HDR
  presentation, 80 ms settle (REPORTED, `photo-viewport.rs:15-18`).
- **Non-destructive everything.** Renders are never replaced, versions are immutable and
  hash-bound, exports never overwrite.
- **Edit with "Give photograph more room".** The photograph large, the timeline beneath. This
  is the application at its best, and version 2 makes it the rule on every station.
- **The capture machinery.** Pipelined capture, checks as planes arrive, error correction,
  calibrate step, compaction, scheduling, managed power, the phone pairing. Capture's problem is
  presentation, not capability.
- **Scripted control and offscreen rendering.** They make every proposed screen checkable.

### 3.2 Measures

| Observation | Measure | Label |
| --- | --- | --- |
| Photograph's share of the window after a stack | 463 × 308 px of 1680 × 1050 = 8.1 % | MEASURED |
| Stacks named after a camera folder | 21 of 35; seven are "100MSDCF" | MEASURED |
| Saved runs in the catalog | 50 (44 saved, 3 cancelled, 3 failed); largest 1,650 frames | MEASURED |
| Conditions that disable "Start stack" | 10 in `start`, 2 more on the button; none shown | VERIFIED `capture-workspace.rs:1684-1698` |
| Library thumbnails | 22 × 18 px; preview cache holds 40 | VERIFIED `project-explorer.rs:724`, `explorer-previews.rs:19` |
| Controls in the Capture column | more than 50, in one scroll | DERIVED from the inventory's list |
| Places showing detail kept by plane and size | 9 | REPORTED |
| Places showing fallback | 6 | REPORTED |
| Time estimate while stacking | none; hover text says the bars do not estimate time | VERIFIED `processing-view.rs:48,181` |
| Jobs that can wait | none; "A stack is already running" | VERIFIED `app-workspace.rs:106` |
| Type sizes in use | more than 15, from 8 pt | REPORTED |
| Colours for failure | none; amber serves warnings, errors and running work | VERIFIED `theme.rs:2-10` |

### 3.3 Problems, by kind

**Structure.**

1. The left rail mixes four kinds of thing: places (Projects, Capture), steps on one stack
   (Adjust, Edit, Export), tools (Agent, Review, Activity) and actions (Stack starts a render at
   once; Layout resets the layout, with no undo). Order: VERIFIED `app-workspace.rs:545-554`.
2. There is no finished state. The instruments keep their full layout after completion
   (REPORTED, `process-theater.rs:925-934`), so the photograph stays small.
3. Nothing leads from one step to the next: not from import to Stack, nor from a finished stack
   to Edit and Export, nor from a finished capture to its result unless three conditions hold.
4. Capture is one scrolling column that mixes set-once items with per-shot ones; finished
   captures are at the very bottom under names like `stack-1794611692641-9758`.
5. A legacy layout (filmstrip, canvas, right dock) still ships and is reached by dropping an
   image (REPORTED, `app.rs:1220-1365`).

**Feedback.**

6. One status string and one sticky error string serve the whole application; there are no
   notifications (REPORTED, `app.rs:206-207`). Success notices in Capture are set and never
   shown (REPORTED, `capture-client.rs:516-563`).
7. Long tasks wait in silence or cannot be stopped: the camera connect wait, "Measure focus
   step", the compaction estimate, "Compact now" (about 2.5 minutes with no percentage).
   "Calibrate step" waited on a camera that had been switched off.
8. Controls are disabled without a visible reason: Start stack, Calibrate step with unapplied
   edits, "Open in Projects" while a job runs.
9. Nothing outside the Capture tab shows that a capture is running, and checking and automatic
   stacking do not start unless the Capture tab was opened in the session (REPORTED).
10. The capture phase is coloured by link freshness, so FAULT is drawn green (VERIFIED,
    `capture-workspace.rs:1618`). A running result is drawn amber like a failure, because the
    status is written "Stacking" and the tree matches "Rendering" (REPORTED).

**Language.**

11. One thing has several names: photos, frames, captures, camera frames, focal planes; stack,
    capture, bracket, run, sequence; result, revision, render; region, selection, annotation,
    issue. "Recipe" means both stack settings and edits. "Survey" names two features. "Stack
    while capturing" does not stack.
12. The diagnostics use the engine's terms as titles: direct fits, admitted, fallback,
    accumulated, at pin, noise limit, folds, accepted prefix. The inventory lists forty.
13. README and in-app labels have drifted ("Photograph focus", "Stack repair · next run",
    Adaptive's "Analyze").

**Gaps.**

14. Library: no grid, dates, sizes, sort, delete, archive or relink; a moved source folder is
    discovered on open and choosing it makes a second stack; importing a folder twice makes a
    duplicate.
15. Capture: no exposure control, histogram, clipping or test shot, though the camera host
    accepts ISO and shutter (VERIFIED, `strehl-capture/src/session.rs:522,669`); no picture of
    the focus range; no per-plane verdicts though the journal holds them (VERIFIED,
    `capture-follow.rs:57-70`); stopped captures are not listed; no provisional image.
16. Stack: no answer to "is it good, and if not, what do I change or re-shoot?"; refused planes
    are a count; no time estimate; no comparison of two renders.
17. Edit: ten sliders and a look (VERIFIED, `strehl-edit/src/recipe.rs:12-26`). No crop,
    white balance picker, curve, sharpening, noise reduction, healing, backdrop clean-up, scale
    bar or histogram. The one repair tool needs a full re-stack and disables Export (VERIFIED,
    `app-export.rs:238`).
18. Export: one file at a time, no presets, resize or metadata, settings reset at launch; TIFF
    export writes the whole recipe, region names and notes included, into ImageDescription
    (VERIFIED, `strehl-edit/src/export.rs:209-221`).
19. Shell: no preferences, help or about; one global undo list across view, edits, project
    organisation and stack settings.

**Style.**

20. Surfaces are blue-tinted (`#10141C`), which biases colour judgement of the photograph
    beside them. The Camera metadata window switches to a light theme (VERIFIED,
    `camera-metadata.rs:651`). Four button idioms coexist. Paths are shown with the `\\?\`
    prefix.

## 4. Principles

1. **The photograph is the page.** On every station the picture is the largest thing, on a
   neutral surround. Evidence comes to the picture; the picture does not shrink for it.
2. **Plain words first, numbers one step behind.** Each reading has a photographer's name and a
   sentence saying what it means. The measured value and the engine's term follow it.
3. **One spine.** The stations are the order of the work, and the depth rail is the same
   object on each.
4. **Nothing waits in silence.** A task that can take more than two seconds says what it is
   doing, how far it is, what it waits for, how to stop it and what follows.
5. **A disabled control says why,** beside the control, with the fix one click away.
6. **Findings come with actions.** A check that finds something offers what can be done about
   it: tighter bounds, trim, extend, repair, render again.
7. **One word for one thing** (section 8).
8. **Measured, or labelled.** No display implies more than the engine measured. Section 5.3
   lists the source of every proposed reading.

## 5. The design

### 5.1 The model

| Object | Is | Replaces today |
| --- | --- | --- |
| Collection | A named group of subjects | Project, folder |
| Subject | A specimen or object: name, notes, optics, scale, journal | (new) |
| Stack | One sweep through focus: planes, each one RAW or a four-shot group | Stack, capture run |
| Render | One run of the stacker with a recipe | Result NN, revision |
| Version | A developed look of a render, with its layers | Edit version |
| Export | A file written from a version by a preset | Export |

A subject is new and is where three existing things come together. Import already knows the
parent folder (`D:\...\bug-3\107MSDCF` yields "bug-3"). A capture can ask for the subject before
it starts. And the multi-stack "session" (several passes of one subject: repeats, interleaved
focus, exposure range, mosaic, views) is by definition a combination of one subject's stacks,
so "Combine stacks…" moves from a feature-gated panel in Projects to the subject page.

Catalog migration: every existing project becomes a collection; every stack gets a subject
named after its parent folder when its own name matches a camera folder pattern, otherwise
after itself; stacks that share a parent folder share a subject. Nothing on disk moves. The
owner's 35 stacks would become 20 subjects (DERIVED from the catalog's source paths).

### 5.2 The shell

Variant A, "Stations", is recommended and is what the mockups draw.

- **Top bar** (also the window's drag area): brand, breadcrumb (Library › subject › stack ›
  render › version, each segment a switcher to its siblings), the stations, then the rig chip,
  the job pill, Ctrl K and the window buttons.
- **Stations:** Library, then Capture › Stack › Develop › Export. Each of the four carries a
  state glyph for the open stack: done, needs a look, running, not yet.
- **Canvas** in the middle, **inspector** on the right (one per station, with tabs),
  **depth rail** along the bottom (three heights: closed, chart, chart with filmstrip), a one-line
  **hint bar** at the foot for the keys that apply here.
- **Rig chip:** camera, light, link speed, camera host and receiver in one popover with the
  power switches, on every station. Amber for a slow USB link or a stopped receiver.
- **Job tray:** section 5.8.
- **Ctrl K:** every subject, stack and command by name with its shortcut.
- **Focus mode (F):** variant C. The photograph fills the window; the inspector and rail
  become floating panels that fade after two seconds without the pointer.

Variant B keeps today's left rail and sidebar, reduced to the five stations, and is the
cheapest first release (section 9, phase 1). The mockup's "Shell and themes" page draws all
three with their trade-offs.

Where today's panes go:

| Today | Version 2 |
| --- | --- |
| Projects | Library and Subject |
| Capture | Capture (plan, in flight, glance) |
| Adjust | Stack › Recipe |
| Review | Stack › Checks |
| Process workspace | Stack (photograph, lenses, core sample) and the engine room (E) |
| Edit | Develop |
| Export | Export |
| Activity | Job tray › Full log, with search, copy and "open log file" |
| Agent | App menu › Agent access; agent notes become note layers; agent actions appear in the job tray in plain words with Apply and Dismiss |
| Camera metadata | Engine room › Camera data, in the application's theme |
| Legacy workbench | Retired; its wipe comparison becomes "vs plane" and "vs Render N" on Stack |
| Stack (rail button), Layout | Render again (Stack inspector); View menu › Reset layout, undoable |
| (none) | App menu: Preferences, Help, About |

Undo becomes scoped to the station: Develop undoes develop changes, Stack undoes exploration
and recipe changes, Library undoes organisation. The hint bar names what the next undo will
undo.

### 5.3 The depth rail, lenses, core sample and checks

**The rail.** A horizontal strip, near on the left and far on the right, drawn as today's
timeline is: one bar per plane, a pale outline with a dot on each bar, a dashed line for the
region under the pointer. It sits on an engraved scale (a tick every five planes, a numeral
every twenty-five) with the filmstrip beneath it. Its layers:

| Layer | Shows | Station | Source today |
| --- | --- | --- | --- |
| Bars | Detail each plane holds | Stack, Develop, Subject (miniature) | Capture contributions: share of sampled points admitted per capture and size (`process-ledger.rs`); the timeline's "Full image" trace. Exists |
| Dashed line | Detail in the region under the pointer or pin, by plane | Stack, Develop | The timeline's "Current region" trace and the probe's rows. Exists |
| Ticks | One per plane: checked, retaken, still on the camera host, to come | Capture | Checker journal. Exists |
| Bounds and lens | Start, end, lens position, planned planes | Capture | Controller state; numbers only today |
| Survey profile | Where the subject is sharp across the lens travel | Capture | Bounds survey; whether the profile is returned or only its result is UNVERIFIED |
| Ranges | Pinned ranges; planes a repair takes from | Stack, Develop | Pinned ranges. Exist |
| Brackets | Planes holding no subject detail | Stack | DERIVED from the bars; threshold UNVERIFIED |
| Filmstrip | A frame every few planes, with a mark per detail size under each | any | Timeline thumbnails and their per-size bars. Exist (48 frames at most today) |

With 6,000 planes the rail bins planes to pixels and magnifies under the pointer. Performance
at that size is UNVERIFIED.

**The plane lens: a plane and its region.** This is today's timeline hover, kept whole and
given a second step.

- *Hover* any plane on the rail or filmstrip. The photograph shows where that plane was kept:
  filled regions with sample marks, in the plane colour. The plane itself rises above the rail
  at the pointer, as a preview with the same region outlined in dashes. Nothing reflows.
- *Click* to hold. The canvas becomes two-up, final beside plane, with one small map per detail
  size beneath (today's "FINAL admit / px" strip). Escape or "Photograph" returns.
- The outline on the camera preview is labelled as today: approximate, not a registration.

Source: estimated admission regions and the "Source + final" split
(`process-admission-regions.rs`, `process-theater.rs:2919-3148`, REPORTED). Both exist; the
work is presentation.

**Lenses** paint evidence on the photograph, with one switch.

| Lens | Shows | Source |
| --- | --- | --- |
| Plane | Where the held or hovered plane was kept, at the chosen detail size | Estimated admission regions. Exist |
| Depth | Focus order: which part of the range each area came from | The engine's regularised focus field. Multi-stack sessions already save focus ordinals, support and ambiguity ("Save focus evidence"); ordinary stacks do not. Engine work, section 7 |
| Soft spots | Areas where no plane passed the gate | Fallback samples and estimated regions. Exist |
| Alignment | Placement residual by area | Alignment evidence exists as run totals; a per-area map is UNVERIFIED |
| Balance | Observation balance, when recorded | "Save confidence map". Exists |

The Depth lens is the regularised field, never a per-pixel sharpest-frame pick: the decision
record measures raw winner-index speckle at 34.4 % against 0.868 % for the 17 × 17 regularised
field (fact 20), and the engineering invariants forbid treating a raw argmax as a reference.
Its legend says "an order of planes, not a measured distance", and it leaves low-support areas
uncoloured.

**The core sample: a region and its sources.** This is today's "This region / source support"
popover, kept and tidied. Hovering the photograph marks a square region with its sample points
and opens the popover beside it; a click pins it. It holds:

- the final crop beside the same crop from the planes that lead there, each with its share of
  samples kept;
- one strip per detail size, plane by plane, in the detail spectrum (section 6), with the
  leading planes marked;
- a sentence ("Fine detail here comes from planes 61–70. Broad shapes draw on 58–73. Nothing
  was filled in.");
- today's cautions, kept: kept is support at the noise gate, not a share of the blend; planes
  can overlap.

While it is open, the rail's dashed line is this region's profile. It replaces "At pin /
capture admission", the hover probe and the two lens crops; pinned, it offers "show the plane",
"repair here" and "note".

**Checks.** The Review pane's stance is "no inferred quality grade". The proposal keeps that:
there is no score and no adjective. There is a count of checks that exceed a stated threshold,
and each check is one measured fact with "Show".

| Check | Fact shown | Source | Status |
| --- | --- | --- | --- |
| Every plane read and placed | n of N; refused planes named | Run log; names are new | Exists as counts |
| Alignment | Pair fits accepted; worst residual | Run evidence | Exists |
| Empty planes at the ends | Planes whose kept share is near zero at every size | Ledger | DERIVED; threshold to validate |
| Soft spots | Share of the subject filled in | Fallback | Exists; "of the subject" needs a subject mask |
| Slices overlap | Step against measured sharp width | `strehl focus-step` | Exists when calibrated or measured |
| Range covers the subject | Whether kept detail is still rising at plane 1 or N | Ledger | DERIVED; to validate |
| Light steady | Plane-to-plane level change | Checker level test | Exists per group; a run summary is new |
| Four-shot groups | Groups that passed | Checker | Exists |
| Observation balance | Recorded or not | Recipe | Exists |

Every threshold is a gate in the sense of the research workflow: before it ships, name an
input that makes it fail and exercise it on the corpus. Until a check is validated it is shown
as a fact without a mark.

On the mockup's 299-plane stack the illustrative bars are empty for planes 1–55 and 212–299.
That finding carries two actions: tighter bounds next time, and "Trim sources…", which is
`strehl thin` behind an explicit confirmation. The owner decided on 2026-11-20 that thinning
stays numbers-only for now; the button is drawn to show where it would live.

**The engine room (E).** Nothing in the Process view is removed. The ring, the detail ladder
and the plane-by-size grid move to their own page with 12 px minimum type, one shared legend,
plain titles with the engine's term as a subtitle, and the nine duplicate views of detail kept
reduced to one grid plus the rail. While a stack runs this is the live view, with a time
estimate learned from earlier renders of the same camera and plane count (UNVERIFIED: needs
per-stage times in the render log).

### 5.4 Capture

**Plan.** The inspector is a flight plan of four steps, each with a ready mark and a one-line
summary: Rig; Exposure; Depth; While it runs, and after. The subject and stack name are asked
first.

- **Pre-flight strip.** One chip per start condition (rig, light, exposure, bounds, step,
  disk, receiver). An unmet chip is amber and says what to do.
- **Exposure.** ISO and shutter from the camera host's existing command; a live-view histogram
  labelled as an estimate; **Test shot**, which takes one RAW at the current focus and reports
  clipping and shadow level from the RAW itself. A stack of 1,488 four-shot planes takes 2.3
  hours at the measured 5.65 s a plane; one RAW first is cheap insurance.
- **Depth.** The rail carries the lens, bounds, planned planes and the survey profile. The step
  is chosen from a table of consequences: for each candidate step, the overlap (sharp width
  divided by step), planes, minutes and gigabytes, with rows beyond the measured limit marked.
  The limit is the round-4 follow-up's finding that detail is kept to about a fifth of the
  sharp width.
- **While it runs, and after.** Check each plane as it arrives, retake planes that fail, stack
  when it finishes, power the rig down after a grace period. Four switches in one step instead
  of three sections.

**In flight.** One headline (plane, time left, finishing time), the proof, the latest plane
with its verdict, the last few verdicts with reasons, the rail filling tick by tick, and four
health cards (transfer, checks, disk, rig). Pause, Stop and Glance.

**The proof** is assembled from the camera previews inside the arriving RAWs, plane by plane.
The application already builds such a composite for a whole bracket (`draft-preview.rs`). Its
header states the limit, and the proposal adopts it: camera processing has changed colour,
noise and local contrast, so the proof cannot predict the RAW merge's detail or noise and is
never an acceptance metric. It is for framing, lighting, gross movement and whether the range
covers the subject. It is labelled "from the camera previews, not the RAW stack" wherever it
appears.

**Glance mode (G).** Full screen: a coloured bar (fine, needs you, stopped), the time left,
the proof, four health lines, and a sentence saying what will happen next. The same state goes
to the paired phone.

**After.** When the capture ends, Stack opens with the checks and a card: "Subject still on
the rig? The camera and light switch off in 0:52. Keep the rig on · Extend the stack… ·
Reshoot…". Extending shoots further planes beyond a bound and appends them as a continuation
folder, which the session engine already supports. A stopped capture is kept as a stack that
can be extended. The grace period is the direct remedy for the class of fault behind the
calibration hang: the application knows whether the rig is still needed before it powers it
down.

### 5.5 Library and subject

- **Library:** subject cards with a real thumbnail, name, counts, last date, size on disk and
  four lifecycle dots. A left list answers "what needs me": on the rig, to stack, to check, to
  develop, exported. Collections below. A storage card shows the disk, Strehl's share and what
  compaction would free.
- **Subject:** the hero photograph, notes, optics and scale, sizes; each stack on one line
  with its depth signature, lifecycle and size; under an open stack, the lineage from renders
  to versions to exports; "Shoot again with these settings"; a journal of what was done with
  which settings.
- **Scale.** Magnification is in the lens data; with the pixel pitch it gives micrometres per
  pixel, which gives a scale bar and a step size in micrometres. How reliable the recorded
  magnification is with a teleconverter fitted is UNVERIFIED; the value is editable per lens.
- **Missing sources** are a card state with "locate…", which relinks instead of creating a
  second stack.
- **Storage review:** stacks by size with their options (compact, with the measured estimate;
  trim; delete sources and keep results), each behind its own confirmation.

### 5.6 Develop

- **Tools:** move, crop and straighten, white balance picker, depth brush, heal, backdrop,
  region shapes, scale bar and labels, note.
- **Depth brush.** Paint an area; the rail shows that area's sharpness trace; drag a range on
  the rail to choose the planes to take from; the canvas previews at once from the camera
  previews; the engine rebuilds only that area in the background. Until it finishes, exports
  use the last finished pixels and say so. This is today's "Source repair" made direct. The
  render already reports "Rebuilding region i / n" as a step (VERIFIED, `app.rs:917`); whether
  that step can run alone against an existing master is UNVERIFIED and is the engine question
  in section 7.
- **Scope is explicit.** A switch above the sliders says what they address: the whole
  photograph or a named layer.
- **Looks.** Adaptive's profiles become named looks with a line each; choosing one applies it;
  Recalculate keeps the amount; the defaults reset to the chosen look, not to Natural.
- **Layers.** Regions, depth repairs, heals, the backdrop and the scale bar in one list, each
  with an eye.
- **Viewing.** Before and after as toggle, split and a key; a surround of black, dark, mid
  grey or white; histogram and clipping.
- **Versions** can be carried to a new render in one step.

How far Develop should go is the owner's call (section 10, D8). The recommendation is the
tools that are specific to finishing a stacked macro photograph (crop, white balance, heal,
backdrop, scale bar, output sharpening), and a clean hand-off for the rest.

### 5.7 Export

Presets (format, range, colour space, size, sharpening, quality), ticked and exported together
through the job tray; a name template; a destination remembered per subject; switches for a
scale bar, copyright and description, and for writing the recipe and notes into the file, off
by default; a history under the photograph that says which version made each file and flags
files older than the current version.

### 5.8 Jobs

One task model for capture, transfer, checks, stacking, repairs, exports, compaction and
calibration. Every task has five states, and each state has an obligation:

| State | Must say | Example |
| --- | --- | --- |
| Waiting | For what, and when it gives up | Waiting for the camera to connect · gives up in 40 s · Stop waiting |
| Running | The step, how far, the time left, how to stop | Surveying · shot 14 of 25 · 32 s left · Cancel |
| Needs you | What is wrong and the one action that fixes it | Paused: the receiver stopped answering · Start receiver |
| Stopped | Why, and what was kept | Camera disconnected at plane 61 · 60 planes saved as a stack |
| Done | The result and what happens next | Step 7 suggested · four-shot mode restored · Use step 7 |

Stacks can queue. A finished capture is stacked when the queue reaches it, instead of only
when nothing else is running and the right tab is open. **Quiet** holds heavy work (stacks,
repairs, compaction) while a full-screen program is in front or on request; captures and
transfers never wait. The owner uses this PC for other things while the rig runs.

## 6. Visual language: engraved

The first iteration's mockups looked like any rounded dark application. The owner's verdict was
"vibe-coded", and it was fair. The second iteration takes its manners from the instruments on
the bench: the white and amber scales engraved on a lens barrel, the vernier of a focusing
rail, the graticule in an eyepiece. It is also closer to what the application is today, which
already uses zero corner radius and one-pixel rules.

- **Square, ruled, flat.** No rounded cards, pills, glows or translucent panels. Corners are
  square. Structure comes from hairlines, alignment and space; a control carries a one-pixel
  outline and nothing else.
- **Scales, not gauges.** Quantities are drawn the way instruments draw them: bars on a ruled
  axis, ticks, an index line. The depth rail, the sliders (a rule and an index, with a tick at
  the default), the glance dial (one tick per plane) and the millimetre rule under the
  photograph share one grammar.
- **Lettering.** One family in the DIN tradition, in four weights: light for large figures,
  regular for sentences, semibold for statements, and tracked semibold capitals at 10.5 px for
  labels, stations and links. Sizes: 64, 24, 15, 13, 12, 10.5. Figures are tabular. A
  monospaced face appears only for file names. The mockups use Bahnschrift, which ships with
  Windows and cannot be redistributed; the application would bundle an open face of the same
  tradition (Barlow or D-DIN, both under the Open Font Licence).
- **Colour measures.** Amber marks what is selected and the main action, as today. Sage green
  is detail kept (today's GREEN). Teal is the plane under the pointer (today's overlay
  colour). Status has drawn shapes as well as colours, so it reads without colour vision: a
  lamp for fine, a triangle for look, a diamond for failed, a ring for not yet, a half for
  running. A red is added for failure.
- **The detail spectrum.** Detail size (2 px to 256 px) gets one ramp, cool for fine and warm
  for broad, used wherever size is shown: the core sample's strips, the marks under each
  filmstrip frame, the detail-size switch, the engine room's grid. It replaces today's eight
  unrelated chip colours.
- **Themes.** Graphite (recommended): today's amber, sage and warm white on neutral greys, so
  nothing beside the photograph tints the judgement of its colour; the surround is adjustable.
  Instrument: the same language on today's navy. Lightbox: paper white for a bright room. All
  three share one set of tokens.
- **Paths** are shown without the `\\?\` prefix and shortened from the middle.
- **Feasibility in egui.** Square panels, hairlines, custom painting and the rail are ordinary
  egui work, and nearer to the current code than the first iteration was. Lens blending and
  region fills belong in the photograph's shader, where HDR presentation already lives. The
  fit of every screen is checked with the offscreen renderer.

## 7. What each move needs

"Interface" means `crates/strehl-ui` only.

| Move | Interface | Engine, model or camera host |
| --- | --- | --- |
| Stations, top bar, hint bar | Rework `app-workspace.rs`, `window-chrome.rs`, `workspace-layout.rs` | none |
| Themes and components | `theme.rs`, `controls.rs`, `edit-controls.rs`; retire off-token fills | none |
| Job tray and five states | One task type over `jobs.rs`, `development-job.rs`, `capture-tools.rs`, export | Queue; cancel points in focus-step and compact; per-stage times in the render log for estimates |
| Subjects and library | `workspace-history.rs` (catalog), `project-explorer.rs`, `explorer-previews.rs` (larger previews, larger cache) | none |
| Storage review | New view over existing estimates | none (thin stays numbers-only) |
| Photograph-first Stack | `process-theater.rs` layout; reuse the Edit layout path | none |
| Checks | Rework `run-review.rs`; read ledger and checker journal | Names of refused planes in the log; threshold validation |
| Depth rail on Stack | Rework `process-participation.rs`; keep its bar chart and filmstrip | none |
| Plane lens: peek and hold | Rework the timeline hover and the "Source + final" split in `process-theater.rs` | none |
| Core sample | Rework `process-region-probe.rs` and `process-region-visual.rs`; fold in `process-fingerprint.rs` and `process-contribution.rs` | none |
| Depth lens | Shader blend in the viewer | Save focus evidence for ordinary stacks; cost in time and disk to be measured |
| Engine room | Re-typeset the existing panels; one legend | none |
| Flight plan, pre-flight | Rework `capture-workspace.rs` | none |
| Exposure and test shot | New controls | `Exposure` exists; test shot can reuse the single-RAW path that calibration uses; a RAW clipping read is new |
| Depth rail on Capture | New mode | Survey profile from the camera host if not already returned |
| Per-plane verdicts | List from the journal | none |
| The proof | Feed `draft-preview.rs` plane by plane | Preview extraction from arriving archive RAWs |
| Glance and phone status | New full-screen view | Status endpoint for the phone page |
| Stop keeps the stack, extend | List incomplete runs; continuation hand-off | Controller: resume from a position list (`CapturePositions` exists) |
| Develop scope, looks, layers | `app-editing.rs`, `app-adaptive.rs`, `edit-regions.rs` | none |
| Depth brush | Brush mask; rail range picking | Region-only rebuild against an existing master; a brush mask in the recipe |
| Crop, white balance, heal, backdrop, scale bar | New tools | Additions to `strehl-edit` |
| Export presets and batch | `app-export.rs`; presets file | Resize and output sharpening in `strehl-edit/src/export.rs`; metadata writing |

## 8. One word for one thing

| Today | Version 2 |
| --- | --- |
| photos · frames · captures · camera frames · focal planes | plane (a focus position) · RAW (a file) |
| stack · capture · bracket · run · sequence | stack |
| Result NN · revision · run | Render N |
| edit version · look · recipe (also stack settings) | Version (of a render) · Recipe (of a render) |
| Projects › folders | Collections › subjects |
| admitted · admission | kept |
| fallback · stack fallback | filled in · soft spots |
| direct fits · placement | pair fits · alignment |
| accumulated | result so far |
| Adaptive · Signature | Look |
| Source repair · Stack repair | Depth repair, made with the depth brush |
| region · selection · annotation · issue | layer |
| Stack while capturing | Check each plane as it arrives |
| Survey (two meanings) | Survey (finds the bounds) · Calibrate step |
| Pi · camera host | camera host |
| Save confidence map · Confidence | Observation balance |

The engine's terms stay in the log, the engine room's subtitles and the documentation, so
anyone reading a log can still find the matching panel.

## 9. Phases

Each phase ships on its own and is checked with offscreen renders at 1440 × 940 and
1680 × 1050.

**Phase 0: today's code, no redesign.**

1. Name a new stack after its parent folder when the folder is a camera folder, and offer the
   name for editing at import (`app-workspace.rs:440`).
2. Show the first unmet start condition beside "Start stack" (`capture-workspace.rs:1684`).
3. After a stack completes, switch to the photograph-large layout that Edit already uses, with
   the instruments one key away.
4. Add a red; draw FAULT in it; stop drawing a running result as a failure.
5. Strip `\\?\` from displayed paths.
6. Draw Camera metadata in the application's theme.
7. Confirm Stop, Disconnect and Shut down camera; add Cancel to "Measure focus step" and the
   compaction estimate.
8. Show a running capture in the status bar on every tab, and start checking whether or not
   the Capture tab was opened.
9. Show the success notices Capture already sets.
10. Add the "Stop waiting" pattern from the calibration fix to the camera connect wait.
11. Make export's "write the recipe and notes into the TIFF" a visible choice.
12. Bring the README's labels back in line with the application.

Acceptance: the photograph is at least 40 % of the window after a stack; no new stack is named
after a camera folder; every disabled Start shows a reason.

**Phase 1: shell and library.** Stations (variant B first if preferred), top bar, rig chip,
job tray with the five states and a queue, themes and components, subjects in the catalog with
migration, library grid, subject page, storage review, preferences.
Acceptance: a capture started and left alone ends as a stacked render without the Capture tab
open; every long task can be stopped or says why not; nothing readable is below 12 px.

**Phase 2: Stack.** Photograph-first page, checks (validated ones marked, the rest as facts),
depth rail with bars and filmstrip, the plane lens (peek and hold), core sample, lens for soft spots, recipe
with intents and "changes from the defaults", renders with comparison, engine room, time
estimates. The Depth lens follows when focus evidence is saved for ordinary stacks.
Acceptance: the photograph is at least 50 % of the window with the inspector open; a refused
plane can be named and opened in two clicks.

**Phase 3: Capture.** Flight plan, pre-flight strip, the rail in capture mode, exposure and
test shot, the step table, the in-flight page, per-plane verdicts, the proof, glance mode,
stop-keeps-the-stack and extend, the grace period before power-down.
Acceptance: from "rig off" to "capturing" without scrolling; the proof appears within the
first ten planes; a stopped capture is listed and can be extended.

**Phase 4: Develop and Export.** Scope switch, looks, layers, before and after, surround,
histogram; depth brush with region rebuild; crop, white balance picker, heal, backdrop, scale
bar; export presets, batch, resize, metadata, history.
Acceptance: a depth repair previews in under a second and does not disable Export; a web copy
and a full-size file leave in one action.

**Beyond.**

- **Plate composer.** Several views of one subject (dorsal, lateral, frontal) on one sheet
  with matched scale bars and labels: the natural-history plate, built from a subject's
  versions.
- **Focus-through clip.** Export a short clip that travels through the planes, or rocks the
  view slightly using the focus order, for showing depth on a screen.
- **Rig profiles.** Per lens and magnification: calibrated step, settle, light warm-up,
  micrometres per pixel, applied when the lens is recognised.
- **Re-shoot planner.** From a finished stack, propose bounds and step for the next view.
- **Light sequences.** Several lighting set-ups per plane or per pass through the managed
  outlets, feeding the session modes that already combine passes.
- **Agent as reviewer.** Notes pinned on the photograph by an agent appear as note layers;
  suggestions carry Apply and Dismiss; the consent text lists the real scope, capture included.

## 10. Decisions for the owner

| # | Decision | Recommendation |
| --- | --- | --- |
| D1 | Shell: stations across the top (A), or today's rail put in order (B) as the first step | A; B only if phase 1 must be smaller |
| D2 | Default theme: neutral Graphite, or keep the navy identity | Graphite, with Instrument selectable |
| D3 | Adopt the vocabulary in section 8 | Yes, with the engine's terms kept as subtitles |
| D4 | Checks: show a count against stated thresholds | Yes, each one validated on the corpus before it carries a mark |
| D5 | Introduce subjects and migrate the catalog | Yes; nothing on disk moves |
| D6 | Save focus evidence for ordinary stacks so the Depth lens exists | Measure its cost first, then decide whether it defaults on |
| D7 | Region-only rebuild in the engine for the depth brush | Yes if the existing region step can run alone; otherwise keep the full re-stack but stop it blocking Export |
| D8 | How far Develop goes | Macro finishing tools in; curves, colour mixing and heavy retouching by hand-off |
| D9 | Thinning from the library ("Trim sources…") | Keep to numbers until the owner lifts the 2026-11-20 decision |
| D10 | Whether the mockups' pictures may be committed | They are the owner's unpublished captures and the repository is public; left out of Git pending a decision |

## 11. Risks and what was not verified

- **No usability evidence.** One user; the design is ARGUED from an inventory and from
  incidents. The first check of each phase should be the owner using it for a real stack.
- **The mockups' data is illustrative.** The depth map, per-plane bars, plane regions, core-sample grid, soft-spot mask
  and proof in the mockups were computed from the bracket's unaligned embedded camera JPEGs
  (local Laplacian energy; `make-assets.py`). They show what the displays would look like. They
  are not engine output, and the JPEG composite's own header says such pixels cannot predict
  the RAW merge. The application would draw the engine's recorded evidence.
- **Mockup figures.** Times, sizes and counts on the screens are plausible, and most are
  derived from measured rates (5.65 s a four-shot plane; 51.0 GB for 784 RAWs), but they are
  not measurements of a real run.
- **Thresholds.** Every check that carries a mark needs a failing input and a corpus pass
  first. "Empty planes" and "range covers the subject" are the least certain.
- **Scale.** The rail, the library grid and previews at 6,000 planes and several hundred
  stacks are untested.
- **Engine questions.** Region-only rebuild, focus evidence for ordinary stacks, per-stage
  times and preview extraction during capture are each UNVERIFIED as to cost.
- **The inventories.** Most file-and-line references come from delegated readings. Twenty were
  re-read and held; the rest are REPORTED and should be re-read by whoever implements the part
  they describe.
- **egui.** No proposed screen was built in egui. The second iteration uses no blur or
  translucency; everything in it is believed ordinary.
- **Type.** The mockups depend on a face installed with Windows. On a machine without it they
  fall back to another DIN-style face or the system face, and look plainer.
- **Web technologies in the mockup** (blend modes, clip paths) do not transfer directly; they
  stand for shader work.

## 12. Evidence and how to view the mockups

- Mockup sources: [`experiments/desktop-studio-2026-11-20/mockups/`](../../experiments/desktop-studio-2026-11-20/mockups/README.md).
  `python build.py` writes `outputs/strehl-studio-2-mockups.html`, one self-contained file.
  Without the private pictures it builds with placeholders.
- `make-assets.py` builds the pictures and the illustrative data from offscreen renders, the
  explorer preview cache and one bracket's embedded JPEGs. It reads only; it writes to the
  ignored `outputs/` folder.
- Screens: Overview, Today, Library, Subject, Capture · plan, Capture · in flight, Glance,
  Stack, Engine room, Develop, Export, Shell and themes, Design system. Arrow keys move
  between them. On Stack, move the pointer over the photograph, then along the rail, and
  click a plane.
- Deep links select a theme and a state, for example
  `strehl-studio-2-mockups.html?theme=lightbox&do=peek:128#stack` (also `hold:128`,
  `hover:0.36,0.40`, `lens:depth`, `tab:recipe`, `pop:jobs`).
- Inventory sources: `crates/strehl-ui/src` at commit `2d18c6b31`; the owner's catalog
  (37 nodes, 50 runs) read from a scratch copy; offscreen renders made with the installed
  build of the same commit.

## 13. Second iteration: the owner's feedback and what changed

The owner liked the direction and asked for four things (2026-11-21).

| Asked | Changed |
| --- | --- |
| The interface looked "vibe-coded", mostly from the corner radii; it should not read as a generic generated UI | A new visual language, section 6: square and ruled, DIN lettering, drawn status marks, scales in place of gauges, no pills, cards or glass |
| The filmstrip hover that shows a plane's in-focus region on the final image against the same region on the plane was missed | Restored as the plane lens, section 5.3: hover to peek, click to hold two-up with a map per detail size |
| The popover that highlights a region of the final image and lists its sources was missed | Restored as the core sample, section 5.3: marked region, final crop beside the leading planes, a strip per detail size |
| Today's filmstrip chart was preferred | The rail is redrawn as one bar per plane with a dashed region line, on an engraved scale, with the filmstrip beneath |

Dropped from the first iteration: the circular loupe that showed a lens only under the
pointer. The marked region and its core sample do that job and are what the owner uses today.

Carried in from the first iteration unchanged: the model, the stations, the checks, the
capture flight plan, the proof, the job tray, the library, Develop, Export, and the phases.
