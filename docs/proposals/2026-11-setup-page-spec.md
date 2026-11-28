# Setup: measuring the camera, lens, rig and light

**Status:** Spec, for an implementing agent. Nothing here is built except where a section
says "exists". Seven decisions are the owner's (section 17); each has a default the
implementer follows until told otherwise.
**Date:** 2026-11-27.
**Origin:** the Calibration page deferred by
[the capture planning proposal](2026-11-capture-planning-flow.md) (its section 18) and by
[the capture calibration spec](2026-11-capture-calibration-spec.md) (its S6).
**Evidence:** [results](../../experiments/setup-page-2026-11-27/results.md), measured
2026-11-27 on the owner's rig, on 24 public RAW files from six other makers and Sony, and on
stacks already on disk. "R3" points at that document's section 3.
**Mockups:** [`experiments/setup-page-2026-11-27/mockups/`](../../experiments/setup-page-2026-11-27/mockups/README.md).
**Written against:** `origin/main` at `31e778bfb` (installed desktop
`desktop-f88d128f907bcfba`). Paths are under `crates/` unless they say otherwise.
**Stage labels** (E1 to E4, P1 to P10) are local to this plan; their milestone rows are
allocated (section 19).

Labels as in `AGENTS.md`: MEASURED, VERIFIED, DERIVED, ARGUED, UNVERIFIED.

**To read it quickly:** sections 3 and 4 are the design, section 17 the decisions, section
18 the order of work. Sections 5 to 13 are for whoever builds it.

---

## 1. What the owner asked for

In their words:

- 2026-11-27, deferring it: the rig calibration "should be its own whole page, to do the
  other calibrations required as well, to cconfigure strehl properly for the camera's
  profile. right now, that's very bespoke."
- 2026-11-27, asking for this design: "a standalone full page rig/camera calibration
  feature … where a new user could calibrate strehl for their specific rig/camera (not
  just mine / baked into strehl)."
- "i would want it to support other cameras (Canon, Nikon, etc.) -- it should still accept
  RAW input, but it should also accept other camera formats."
- "tuning it to the camera/sensor/lens, like we manually do today, as well as other
  settings you would need to derive from the e2e rig, for an entirely different setup."
- "i'm imagining things like it takes dark fields images, white field, etc. … an entirely
  new user/setup should be able to do this, without an agent. i would imagine it could
  support multiple profiles."
- On the first draft of this document: "it would be good to make sure someone can manually
  do the setup too, if they don't have a driver. some of these would need to be optional
  too. for example, the light. not everybody would have a light. so the setup would need
  to be configurable. ofc optimize for the ideal setup (my current setup) though
  (automatic driver + my equipment / capability level)."

So: **a page where a person with a camera Strehl has never seen makes Strehl correct for
it. They say what equipment they have. For each thing worth measuring they put something
simple in front of the lens and either press one button, on a rig Strehl drives, or shoot
a short list by hand and drop the folder. What is measured is kept as profiles, several
of them, and the rest of the app uses them. The rig that can do everything does most of
it from one press.**

Read as written, "other camera formats" means the RAW formats of other makers (CR2, CR3,
NEF and so on), with RAW still the input. Rendered formats (JPEG, TIFF) are not accepted,
and section 16 says why.

---

## 2. What exists, and what was measured

### 2.1 What Strehl holds about a camera today (VERIFIED by reading the code)

| # | Fact | Where | For a camera it has not seen |
| --- | --- | --- | --- |
| F1 | The noise model (gain, read noise, the ISO where the gain mode changes) is a compiled table with two entries, the A7C II and the A7CR | `strehl-core/src/profile.rs` (`PROFILES`), whose header calls it "a stopgap … Moving it to a data file is owed before v1" | Unity gain and 4 e- read noise are guessed. The CLI prints "NO CALIBRATION … Every number below is untrustworthy"; the desktop shows nothing. `strehl compact` refuses |
| F2 | Black and white levels come from the decoder, the first entry only. One constant, 16383, stands for the top of the data | `strehl-raw/src/lib.rs` (`decode`), `strehl-core/src/clip.rs` (`CONTAINER_MAX_DN`) | Per-colour black is dropped. A 12-bit or 16-bit file meets a 14-bit constant |
| F3 | Only `.arw` and Strehl's own archive are scanned, and only an RGGB sensor decodes | `strehl-raw/src/lib.rs` (`is_raw_path`, `UnsupportedCfa`) | A Canon or Nikon folder "contains no .ARW … frames" |
| F4 | Lateral colour is two numbers per optical path, compiled for two paths (the 100 mm macro with the 2x converter on each body). The per-stack refinement only runs on top of a profile | `strehl-core/src/optics.rs` (`PROFILES`), `strehl-cli/src/merge_cmd.rs` (`ca_refine::applicable`) | No colour correction at all |
| F5 | The dust map is embedded for the A7C II. Its builders (`detect_dust`, `detect_hot`) are library code that no command calls | `strehl-core/src/defect_map.rs` | None, and no way to make one |
| F6 | The optical cutoff (the working aperture) is learned per stack and kept in `optical-cutoffs.json`, keyed by Sony's lens code, with four seed records from the owner's renders | `strehl-cli/src/merge_cmd/optical-cutoffs.rs` | Four-shot stacks only; other makers have no lens code |
| F7 | Scale is typed per subject: µm per pixel "measured on a slide", or a magnification and a pixel pitch | `strehl-ui/src/catalog-subjects.rs` (`ScaleCalibration`) | The same; nothing measures it |
| F8 | Settle, approach and the light's wait are constants found by hand: 500 ms and 128 units in the plan, 2 s after an approach, 150 s for the light | `strehl-capture/src/model.rs`, `worker.rs` (`AFTER_APPROACH_MS`), `strehl-ui/src/capture-measure.rs` (`LIGHT_SETTLED`), `capture-guide.rs` (`SETTLE_MEASURED`) | The owner's rig's numbers |
| F9 | The capture host has one `Camera` trait, and every layer above it reads Sony property names, Sony value encodings and a 16-bit lens position. The model name it reports is a literal | `strehl-capture/src/backend.rs`, `ptp.rs`, `worker.rs`, `session.rs` | Tethered capture is Sony only |
| F10 | The A7CR's profile was made by hand on 2026-11-14: 17 lens-capped dark series, three out-of-focus bursts, two analysis programs, then constants typed into `profile.rs` | `experiments/a7cr-calibration-2026-11-14/` | An agent's evening for each new body |

### 2.2 What was measured for this design (2026-11-27)

| # | Measured | Consequence here |
| --- | --- | --- |
| M1 | Of 24 public RAW files from Canon, Nikon, Fujifilm, Panasonic, Pentax, Hasselblad and Sony, the linked decoder reads 22. 18 of those are one sample per pixel with a 2 x 2 colour pattern: 17 with RGGB at the active area's corner, 1 GBRG (Panasonic S1R). 2 are X-Trans and 2 are reduced-size files with three samples per pixel. It cannot read Nikon's High Efficiency NEF or one Hasselblad variant (R1) | Other makers' files are within reach of the engine's gates, not of the decoder. Section 9 lists the gates to open and the files to refuse by name |
| M2 | In 13 of the 18 the data's top code is above the white level the decoder declares: Canon R6 II 16383 against 12735, Nikon Z 8 16383 (1.5 million samples on it) against 15892, Sony 16383 against 15360. Black is 64, 100, 128, 256, 510, 512 or 1008, and two bodies give different black per colour. Containers are 12, 14 and 16 bit (R1) | The top of the data is measured, never assumed. Per-colour black is kept. The 14-bit constant goes |
| M3 | Capped, with the door closed, 8 frames give the A7CR's read noise as 1.311 DN at ISO 100 and 2.144 at ISO 400. With no cap, the light switched off and the room not fully dark, the same 8 frames give 1.305 and 2.134: within 0.5 % at the four ISO settings tried, and black within 0.2 DN. The room's light shows only at the longest exposure: over 2.5 s the level rises 0.19 DN uncapped and 0.04 capped. With the light on and no cap the level rises 456 DN. With the cap on and the light on it rises 0.09 (R2, R9) | The dark measurement needs no cap on a rig with a switched light, a cap alone is enough in a lit room, and a two-shutter test tells a person at once whether their frames are dark |
| M4 | The A7CR's read noise at ISO 100 is 1.31 to 1.33 DN from 1/2000 s to 2.5 s, 1.385 at 1/4000 s, 1.546 at 1/8000 s and 1.594 at 8 s, while its black stays at 512.2 to 512.3 at every one (R9) | A camera is measured at the exposures it is used at. The very fast and the very long are not the same camera, and dark current shows as noise, never as level |
| M5 | From 40 single shots of the subject that happened to be on the stage, 5,000 units out of focus, taken in 2 min 40 s with no white card, the fit gives a green gain of 0.4040 DN/e- at ISO 100. The hand-made profile says 0.4040. One burst of 8 at each of ISO 200, 320, 400 and 800 gives the gain within -0.3 % to +1.4 % of proportional to ISO (R3) | The gain needs no flat field and no agent. "Proportional to ISO", unverified since 14 November, holds within 1.4 % |
| M6 | The sensor's response is linear to within 0.1 % up to the code where it clips, 16383, at ISO 100 and 400: the ratio of an 8 s burst to a 5 s burst stays within 0.07 % of flat from 1,300 to 15,400 DN above black. The engine's white is 15360 (R3) | 6.9 % of the range above black (0.1 stop) is treated as clipped today. Decision 3 |
| M7 | The light's level moved by 0.2 to 0.5 % from frame to frame inside a burst and stepped up 4 % six and a half minutes after it was switched on (R4) | Every exposure measurement removes the light's drift frame by frame, and says how large it was |
| M8 | Reached from 128 units below, the lens lands at the same place within 0.8 units (1.5 % of the sharp depth). Reached from above it lands 4.1 units lower. A reversal of 8 or 16 units does not undo that. After 5,000 units of travel upward it lands 3 to 4 units high with 2 to 4 units of scatter, stays there for the 12 s watched, and a 128-unit approach straight after does not always cure it (R5) | The approach distance and direction are measurable facts of a focus axis. The rig measurement finds them and Capture uses them |
| M9 | The host switches the light on for every capture when it manages power, so the first dark series of this work was lit; the camera's magnifier resets on a focus move; and the camera wakes with the exposure and shot mode of its last capture, not the last ones set, so an exposure put back and not shot is gone at the next power-on (R2, R5, R11) | Two host changes: a capture kind that leaves the light alone, and one that ends on a capture at the settings it found. Nothing here depends on the magnifier surviving a move |
| M10 | A plain Fourier peak finds the pitch of the calibration slide's dot grid as 108.46 and 108.56 sensor pixels along its two axes in one region and 108.36 and 108.13 in another (R6). The slide's own labels do not give an absolute size (it is a photographic reduction) | Scale is a pitch Strehl counts in pixels and a length the person types |
| M11 | Starting from a lens profile of zero, two passes of the engine's own per-stack instrument reach the same lateral colour as one pass on top of the hand-made profile, within 3 to 7 ppm in red on three stacks and 36 ppm on the fourth, where the hand-made profile is 214 ppm off. Between stacks with the same lens the colour shift itself runs from -215 to -386 ppm in red and +30 to +188 in blue (R7) | An unknown lens needs no hand-made profile, and a stored one is a start, not the answer. Decision 4 |
| M12 | With the settle before an exposure set to 100, 250, 500, 1,000 and 2,000 ms, the picture is 0.29 to 0.58 px (median) from rest when a 1/100 s exposure starts, with no trend; the test could have seen 0.23 px (R8) | On this rig the settle is not what moves the picture: its own movement between frames is. The settle test must be able to say "no difference" |
| M13 | From cold the light's level falls 8 % in 40 s and is inside 1.05 % from 2 min 47 s; its colour is still moving at 3 min 24 s (R4) | The 150 s constant is close. The light's wait is measured per light, by rule |

Section 14 lists what was not measured and is argued or left open.

---

## 3. The design in one page

A sixth destination in the station bar, **Setup**, apart from the five that a picture
passes through.

```text
01 Library   02 Capture   03 Stack   04 Develop   05 Export            Setup ●
```

A **setup** is a camera, a lens, a rig and, where there is one, a light, each with what
Strehl has measured about it. Setup shows one setup at a time and holds as many as the
person owns.

Everything is measured in **sittings**. A sitting is everything Strehl can measure with
one thing in front of the lens:

| Sitting | In front of the lens | Gives | Who needs it |
| --- | --- | --- | --- |
| 1 Dark | Nothing: the light off, or the cap on | Black level, read noise at each ISO, where the gain mode changes, hot photosites | Every camera |
| 2 Bright | Anything bright, far out of focus. A white card is best | Gain at each ISO, the code the data clip at and how far they stay linear; with a card, the dust map, the sensor's fixed pattern and the light's colour | Every camera |
| 3 Scale | A ruler, a stage micrometer or a slide, in focus | Micrometres per pixel at this focus position | Anyone who wants a scale bar or depth in millimetres |
| 4 Detail | Nothing new: a stack already shot of a finely detailed subject | The lens's lateral colour, its sharp depth and working aperture | Every lens |
| 5 Motion | The same detailed subject | How the focus axis returns to a position, how long the picture takes to settle, how still it is | Anyone who steps focus with a rail or a motor |
| 6 Warm-up | Anything | The light's level against minutes since it was switched on | Anyone with a continuous light |

**Three ways to a number.** Strehl measures it: one button, on a rig it drives. You shoot
it: a list in your camera's own words, then a folder dropped on the page. You type it,
where you simply know it: a pixel pitch, a rail's step, a scale. The analysis is the same
program for the first two, and the page says which of the three every number came from.

**What you have.** A setup begins with three questions: how frames reach Strehl, what
moves the focus, what lights the subject (section 4). The answers decide which sittings
are offered and how each is worded. Nothing a setup does not have is asked for.

**One press for the rig that can do everything.** Where Strehl's host drives the camera
and the focus and switches the light, Dark, Warm-up, Motion and Bright need nothing
changed in front of the lens. "Measure the rig" runs the four unattended in about 21
minutes (section 4.4). Scale needs a ruler put down; Detail needs a stack.

What a sitting measures goes into the setup's **parts** (camera, lens, rig, light), which
are files. The engine reads them where it reads its compiled tables today. Where a
measurement is missing and costs quality, the app says so at the place it costs: on the
stack, in Capture's Rig step, on the scale bar.

### Rules

An implementer who has to choose between two readings of this document picks the one that
keeps these.

1. **One thing in front of the lens, one button.** A sitting never asks the person to
   swap the target half-way. Sittings that share a target can run back to back.
2. **Strehl tells you when the target is wrong, in its first ten seconds, and says what to
   do.** "These frames are not dark: the level rises with exposure time." A check that
   only an agent can read is not a check.
3. **Every sitting can be done by hand.** A rig Strehl drives automates the shooting. It
   never adds a measurement that a folder of the same frames could not give.
4. **Where a number came from is always said.** Measured here, shipped with Strehl, from
   a file, entered, or guessed (section 5.9), with the date and what it was taken under.
   Nothing is called calibrated because a file exists.
5. **A measurement that passes its checks is kept. One that would replace an earlier
   measurement shows both and waits.** One that fails a check is never kept without a
   click, and names the check.
6. **Evidence on the stage.** Each sitting ends on a plate (section 8.4): a ruled figure
   of what was measured, with the fit drawn through the points. No score, no adjective.
7. **The engine's models, filled in.** A sitting produces the parameters the engine
   already uses (one noise model, one colour model). It adds no private estimate, and
   no stage of the engine fits its own (`AGENTS.md`).
8. **Geometry stays fitted at run time.** Nothing here stores focus breathing, its centre
   or a per-frame alignment (`AGENTS.md`). What is stored is what does not change from
   stack to stack.
9. **Measure in the mode you shoot in.** ISO, shutter type, bit depth and compression are
   part of what a measurement was taken under (M4).
10. **Pixels do not change by surprise.** Reading the two shipped profiles from files
    renders the same bytes as today. Anything that changes a render of an existing stack
    is a decision in section 17.
11. **Nothing a setup lacks is asked for.** No light, no warm-up to measure and none
    drawn as missing. The station's mark counts what applies.
12. **The best-equipped rig has the shortest path.** Whatever a host can do unattended,
    it does unattended; a press is spent only where a person's hands are needed.

---

## 4. What you have

A setup starts by saying what the equipment is. Three questions, asked once when a setup
is made and editable afterwards: the first two on the Rig sheet, the third on the Light
sheet or, for a setup with no light yet, from the setup's menu (section 8.2). Where a host
is connected the page fills in the answers it can see and the person corrects them.

### 4.1 Three questions

**How do frames reach Strehl?**

| Answer | Means |
| --- | --- |
| Strehl's host takes them | A camera the capture host drives (today Sony bodies, F9). Sittings are one button |
| I shoot and bring the files | Anything else: the camera's own bracketing, a rail controller, another tethering program. Sittings are shot lists |

**What moves the focus?** (`axis.kind` in the rig part)

| Answer | Positions | Notes |
| --- | --- | --- |
| The lens's motor, driven by Strehl | Read back from the lens for every frame | The owner's rig |
| A motorised rail with its own controller | Counted from the step the person types, in micrometres | Not driven by Strehl; the person runs the controller |
| The camera's own focus bracketing | None: frames are in order and nothing more is known | The camera cannot be sent back to a position, so Return is not offered |
| By hand: a manual rail, a helicoid, the focus ring | None, or a typed step if the rail has a scale | |

**What lights the subject?** (`kind` in the light part; the last answer means no light
part at all)

| Answer | Warm-up | Dark without a cap | Bright's exposures |
| --- | --- | --- | --- |
| A continuous light Strehl switches | One button | Strehl switches it off | Set by shutter time |
| A continuous light switched by hand | By hand, with frames at a steady interval | "Cap the lens" | Set by shutter time |
| Flash | Not offered: a flash has no warm-up | "Cap the lens" | Set by flash power; the page asks for five powers |
| Nothing of its own: daylight, room light | Not offered | "Cap the lens" | Set by shutter time; the Light check is advice only |

Every setup has a rig part, if only to hold these answers. A setup that works from files
adds to it whatever the person measures by hand or types.

### 4.2 What the answers change

Nothing a setup does not have is asked for, drawn as missing, or counted in the station's
mark. A sitting that does not apply is not on the list; the Rig or Light sheet says why in
one line ("No light to warm up").

| Sitting | A rig Strehl drives | By hand |
| --- | --- | --- |
| Dark | One button. With a switched light Strehl turns it off; otherwise "Cap the lens, then Continue" | Shot list, folder drop |
| Bright | One button. Strehl drives the focus away; with an axis it cannot drive, "Turn the focus away until the bar is under the line, then Continue" | Shot list, folder drop |
| Scale | One frame, then a band dragged on it | One file, then the band |
| Detail | A stack chosen from the Library | A stack chosen or dropped |
| Motion: Return | One button | Shot list (a short stack, then arrivals at one position), folder drop. Not offered for the camera's own bracketing |
| Motion: Settle | One button | The same short run shot at two settle delays of the person's controller |
| Motion: Still | 20 s of live view | Ten frames with nothing touched |
| Warm-up | One button, with a light Strehl switches | Frames at a steady interval from switch-on. Continuous lights only |

Sections 6 and 7 give each by-hand list in the words the page uses.

### 4.3 What can be typed instead

Some facts a person simply knows. They are entered on a sheet, marked "entered", and used
exactly as a measured value would be:

| Fact | Where | Used for |
| --- | --- | --- |
| Pixel pitch, or the sensor's width in millimetres | Camera sheet (filled from the file when it gives one) | Magnification; the working aperture |
| A rail's step in micrometres | Rig sheet | Depth in millimetres; the step's sharpness advice |
| Scale: micrometres per pixel, or a magnification | Lens sheet (and per subject, as today) | Scale bars |
| The settle delay and approach in use on an outside controller | Rig sheet | Shown beside what Motion measured |
| How long the person waits for their light | Light sheet | Shown beside what Warm-up measured |

Not typed: noise, gain, levels and lens colour. Those are measured, shipped or imported
as a file from someone who measured them (section 5.2). A typed gain would be believed by
every stage of the engine and checked by none.

### 4.4 The rig that can do everything: one button

The owner's rig is the case to be best at: Strehl's host drives the camera and the lens
and switches the light. There, with a detailed subject in focus on the stage, four
sittings need nothing changed in front of the lens, and **Measure the rig** runs them back
to back, unattended:

| Order | Sitting | Light | Time, measured 2026-11-27 |
| --- | --- | --- | --- |
| 1 | Dark | Off (switched off by Strehl) | 2 min 52 s |
| 2 | Warm-up | On, from cold | 3 min 25 s |
| 3 | Motion: Return, Settle, Still | On | 4 min 46 s, 4 min 34 s, 20 s |
| 4 | Bright (the subject, far out of focus) | On for 13 minutes by now | 4 min 40 s for five ISO settings |
| | The lens is put back where it was; exposure, four-shot and the light as they were | | |

20 min 37 s of shooting, about 21 minutes with the reading. The order is the light's:
dark first while it is off, the warm-up when it comes on, the exposure work last when it
has been on longest.

- Before it starts the page says what it will do and what it cannot: "The light has been
  off for 4 minutes. Warm-up needs 20: wait until 22:31, or skip it." "No white card:
  Bright will give gain and levels, not the dust map."
- A sitting whose check fails stops, keeps nothing of its own, and the chain goes on to
  the next. Nothing later depends on an earlier one except Bright's plate, which draws
  the read noise Dark gave.
- At the end the summary plate (8.5) shows what each sitting gave, with the ones that
  would replace an earlier measurement waiting side by side (rule 5).
- Stop works at any moment and leaves the rig as it was found.

Scale needs a ruler or slide put on the stage, and Detail needs a stack: those two stay
their own buttons. So a rig like this one is fully measured in two presses and a stack.

### 4.5 Supporting other cameras: what it means here

Two different things are called support, and only one of them is in this spec.

**From files (in scope, complete).** A person shoots with whatever controls their camera.
They drop the folder into the Library. Strehl decodes it, finds or asks for the camera's
and lens's profiles, and stacks it. Every sitting has a by-hand form (4.2), so the whole
setup can be done with no driver. This works for every camera whose files pass section
9's gates: on the evidence of M1, current Canon, Nikon, Pentax, Hasselblad, Sony and
Bayer Panasonic bodies.

**Tethered (not in scope, prepared for).** Strehl's capture host drives the camera, the
focus axis and the light. Today that is a Sony body over Sony's PTP dialect with focus by
the lens motor (F9). A Canon or Nikon body, or a motorised rail, needs a driver, and a
driver needs the hardware on a bench. This spec does not write one. It does two things so
that one can arrive without redesigning the page: every automatic sitting is written
against the capabilities in section 11.3, not against Sony; and section 15 lists what a
driver must provide and every Sony-only path it has to replace.

Refused, by name, with a sentence the person can act on (section 9.2): Fujifilm X-Trans
sensors, Foveon sensors, reduced-size RAW (Canon sRAW and mRAW, Sony's M and S lossless),
Nikon High Efficiency NEF, and demosaiced (linear) DNG.

---

## 5. Profiles

### 5.1 The four parts and the setup

| Part | Is a property of | Identified by | Holds |
| --- | --- | --- | --- |
| **Camera** | The body's sensor and its electronics | Maker and model as the decoder cleans them; the serial number where the file gives one | Section 5.3 |
| **Lens** | The whole optical path on this body: lens, converter, tubes, filter, aperture | The body's model, the lens as the file names it (Sony's lens code where present), the f-number, and a name the person gives the path | Section 5.4 |
| **Rig** | The focus axis, the stand, the host | A name, and the host's identity | Section 5.5 |
| **Light** | The lamp and its supply | A name, and the plug's identity where it is switched | Section 5.6 |

A **setup** is a name and one of each part that applies. It always has a camera, a lens
and a rig part: the rig part holds the answers of section 4.1 even when nothing else about
the rig is known. It has a light part when it has a light of its own. The same camera
part can sit in several setups; so can any part.

Why four and not one: a measurement belongs to what it is a property of. The lens's
lateral colour "is a property of the glass, not of the body"
(`optics.rs`, MEASURED across the two bodies); a new lens must not discard the camera's
noise model, and a second camera must not inherit the first one's dust.

### 5.2 Files

One folder per machine, beside `capture.json`:

```text
%LOCALAPPDATA%\Strehl\setup\
  setups.json                     the setups, and which is current
  camera-<slug>.json              one per camera part
  lens-<slug>.json                one per lens part
  rig-<slug>.json
  light-<slug>.json
  maps\<slug>-<kind>.txt          defect maps in the existing text format (`strehl-defect-map 2`)
  plates\<part>-<sitting>.json    the points behind each plate (small; no pictures)
  scratch\                        a sitting's RAW frames while it runs
```

- JSON, `serde`, a `schema` string in each file (`strehl.setup.camera.v1` and so on), one
  final newline, written through a temporary file and a rename as `optical-cutoffs.rs`
  does. Unknown fields are kept on rewrite.
- The engine finds the folder from `--setup-dir`, then `STREHL_SETUP_DIR`, then the
  default above (`dirs::data_local_dir()` on other systems). The desktop always passes
  it. `STREHL_SETUP_DIR=off` reads no files, for tests and for comparing with the shipped
  tables.
- **The shipped profiles become files of the same schema**, embedded in the engine with
  `include_str!`: `camera-ilce-7cm2.json`, `camera-ilce-7cr.json`,
  `lens-ilce-7cm2-fe100gm-2x.json`, `lens-ilce-7cr-fe100gm-2x.json`. The compiled
  constants in `profile.rs` and `optics.rs` go, and their tests read the files. This is
  the move `profile.rs` says is owed.
- A sitting's RAW frames live in `scratch\` and are deleted when its result is kept or
  discarded. A switch on the page, off by default, keeps them ("Keep the frames, 0.4 to
  3 GB a sitting"). What is always kept is the plate's points, so the figure can be drawn
  again.
- A part or a whole setup exports to one `.strehl-setup` file (a zip of the JSON, maps and
  plates) and imports from one. A camera part measured on one body is a fair start for
  another body of the same model; a lens part likewise. The page says "from a file,
  measured on another camera" until the person measures their own.

### 5.3 The camera part

```text
schema            "strehl.setup.camera.v1"
make, model       as the decoder cleans them ("Canon", "EOS R5")
serial            Option<String>
sensor            { width_px, height_px, origin_shift: [0|1, 0|1], container_bits,
                    pixel_pitch_um: Option<f64>, pitch_source: "file" | "entered" }
modes             [ Mode ]
source            "measured" | "shipped" | "imported"
```

A **mode** is one way the camera reads its sensor out: a shutter type, a bit depth, a
compression. Most people have one. A second is made on the Camera sheet ("New mode…")
and measured by running Dark and Bright again in it.

```text
Mode
  label           "Mechanical shutter", "Silent": the person's words; "Default" for the first
  signature       { container_bits, compression: String, width_px, height_px }
  iso             [ IsoPoint ]
```

Which mode a stack uses: the one its setup names, for a stack Strehl captured (section
11.1). For an imported stack, the mode whose signature its first frame matches; when two
modes share a signature (the A7CR at 1/8000 s and at 1/100 s do, M4), the current setup's
choice, shown on the stack and changeable there.

```text
IsoPoint
  iso                 f32
  black               [f32; 4]      measured mean of dark frames, by CFA position
  black_declared      [f32; 4]      what the files of that sitting declared
  read_dn             [f32; 4]      pooled rms of each photosite's temporal deviation
  read_dn_median      [f32; 4]
  gain_dn_per_e       Option<[f32; 4]>
  clip                Option<[u16; 4]>   the highest code the data reach
  linear_to           Option<[f32; 4]>   DN above black the response is linear to (1 %)
  read_dn_long        Option<{ shutter_s, read_dn: [f32; 4] }>   the Dark sitting's burst b
  taken               { unix, frames, shutter_s: [..], sitting: "dark" | "bright" }
```

Plus, for the mode as a whole: `gain_modes` (the ISO ranges that share one conversion
gain, found by the Dark sitting, 6.1), `prnu_kappa: Option<[f32; 3]>`, `hot_map:
Option<path>`, and `notes` (the processing flags of 6.1: "blue is filtered in camera",
"black is truncated").

**How the engine reads it** (`profile::noise_model_for`, section 10.2). For a frame of
camera C at ISO I in mode M:

1. An `IsoPoint` at I with gain and read noise: use it. Provenance `Measured`, or
   `Profile` for a shipped part.
2. No point at I, and I lies inside a gain mode that has at least one point with gain:
   gain scales in proportion to ISO from the nearest such point (M5: within 1.4 % over
   three stops); read noise in DN is interpolated between the two nearest points of that
   gain mode, or scaled in proportion to ISO from the one. Provenance the same, and the
   report says "ISO 250 taken from ISO 200".
3. Otherwise: today's fallback, provenance `Fallback`, now shown (section 8.6).

The engine uses green's gain and read noise for all four planes, as today
(`profile.rs`: "All four planes share the same coefficients"). The per-colour numbers are
kept for the plate and for a later decision; M5 repeats the 14 November finding that the
A7CR's blue reads 7 % low because the camera filters it.

**Black.** The engine keeps taking each frame's own declared black, per colour now, and
adds the part's `black - black_declared` for that ISO. Canon declares a different black
in every file from its masked pixels; a stored absolute would be wrong for the next
frame, a stored correction is right.

**White.** Section 6.2 and decision 3.

### 5.4 The lens part

```text
schema            "strehl.setup.lens.v1"
camera_model      String
lens              { model: Option<String>, sony_type3: Option<u16>, name: String }
f_number          f32
path              String     "2x converter, no filter": the person's words
lateral           [ { focus: Option<f64>, red: { scale, translation }, blue: { .. }, fit: FitStats,
                      from: String, unix } ]
scale             [ { focus: Option<f64>, um_per_px: f64, unix, how: "pitch" | "length" | "entered" } ]
live_offset       [ { focus: f64, units: f64, unix } ]          section 7.1; lens-motor axes
colour_focus      [ { focus: Option<f64>, red: f64, blue: f64, unit: String, unix } ]   section 6.4
depth             [ { focus: Option<f64>, width: f64, unit: String, unix } ]
cutoff            [ { focus: Option<f64>, green: f64, residual, tiles, unix } ]
dust_map          Option<path>      at this f-number, for one camera serial
travel            Option<{ near, far }>
source            "measured" | "shipped" | "imported"
```

- **Matching a stack to a lens part.** Same camera model; same lens as the file names it
  (`sony_type3` when both have it, else `model`); f-number within 0.05. Several parts can
  match, since tubes and manual lenses leave no trace in a file: then the stack's own
  manifest decides (Strehl's captures record the setup, section 11.1), else the current
  setup's lens if it matches, else the newest. The Stack station names the part it used
  and lets the person choose another.
- **`lateral`** is `optics::OpticalProfile`'s `eps_r`, `eps_b` and translation with its
  fit statistics, one record for each stack it was measured from, with that stack's focus
  position. The engine starts from the record nearest in focus (the rule of `cutoff`
  below). It replaces the compiled table. MEASURED (M11): the shift differs between
  stacks by more than between ways of measuring it, so a record is where the per-stack
  measurement starts, never what a render ends on.
- **`cutoff`** absorbs `optical-cutoffs.json` and its seeds: the same records, the same
  nearest-in-focus rule and `MAX_FOCUS_DISTANCE`, now keyed by the lens part and so no
  longer by Sony's lens code alone.
- **`depth`** is where the capture calibration's lens memory
  (`capture-lens-memory.json`, `LensMemory.entries`) records the sharp depth by position.
  That file keeps its subject memory and light times; its lens entries move here.
- `focus` is `None` for a path with no readable focus position (a rail, a manual lens):
  then one value stands for the path.

### 5.5 The rig part

```text
schema        "strehl.setup.rig.v1"
name          String
host          Option<String>         the controller's identity
frames        "host" | "files"       section 4.1's first answer
axis          { kind: "lens" | "rail" | "camera" | "hand", driven: bool, unit: String,
                um_per_unit: Option<f64>, step: Option<f64> }
approach      Option<{ distance, from: "below" | "above", repeat_sd, hysteresis,
                       after_far_move: { offset, scatter }, unix }>
settle        Option<{ ms, after_approach_ms, table: [ { ms, moved_px } ], limit_px, unix }>
stillness     Option<{ moved: [ { span_s, px } ], drift_px_per_min, exposure_limit_s, unix }>
level         Option<{ across_width, across_height, bowl, unit: String, unix }>     section 6.4
timing        Option<{ per_plane_s, per_image_s, link_mbps, unix }>
```

`driven` is true when Strehl's host moves the axis. `unit` is "lens units", "um" or
"frames"; an axis with no positions counts in frames. Each measurement carries its own
source (5.9); a host's rig part starts with today's constants (F8) marked "default".

### 5.6 The light part

```text
schema        "strehl.setup.light.v1"
name          String
kind          "switched" | "continuous" | "flash"     section 4.1's third answer
plug          Option<String>
warm_up       Option<{ settled_s, tolerance, curve: [ { s, level } ], drift_px_per_min, unix }>
steadiness    Option<{ rel_sd, at_shutter_s, unix }>      frame to frame; flash to flash for a flash
balance       Option<{ red, blue, target: String, unix }>      multipliers against green
```

`warm_up` exists only for the two continuous kinds. A setup lit by daylight has no light
part; what Bright sees of its light's steadiness is on Bright's plate and nowhere else.

### 5.7 What makes a measurement out of date

A part is never "stale" as a whole. Each measurement says what it was taken under, and the
page marks it with a ring instead of a dot when one of these is true:

| Measurement | Ring when |
| --- | --- |
| Dust map | The lens was taken off since (the host saw the lens identity change, or the person says so), or it is older than 30 days |
| Light balance, warm-up | The person says the lamp or its setting changed. Strehl cannot know |
| Approach, settle | The rig part's axis description was edited |
| Anything | The camera's firmware string changed, where the file gives one |

Sensor noise and levels do not age on these time scales and are never ringed for age.

### 5.8 Several setups

- `setups.json` holds `{ name, camera, lens, rig, light }` rows and `current`.
- **Capture uses the current setup.** When the connected camera or the lens on it is not
  the current setup's, Capture's Rig step and Setup both say so in one line, "This is a
  different lens: FE 90mm F2.8 Macro G OSS", with two actions: switch to a setup that has
  it, or make a new setup that keeps the camera, rig and light.
- **The Library does not ask.** An imported stack finds its camera part by model and its
  lens part by 5.4's rule, whatever the current setup is.
- A new setup starts from a copy of the current one's parts or from nothing, and with
  section 4.1's three questions.

### 5.9 Where a number came from

Every number on the page, in a sheet's table and on a stack's checks row carries one of
these, drawn as a mark and said in a word:

| Source | Mark | Means |
| --- | --- | --- |
| Measured here | ● | A sitting on this machine gave it, on the date shown |
| Shipped | ○ "shipped" | It came with Strehl, measured on another body or lens of the same model |
| From a file | ○ "from a file" | Imported from a `.strehl-setup` someone else made |
| Entered | ○ "entered" | The person typed it (section 4.3) |
| Default | ○ "default" | A constant Strehl has always used: today's settle, approach and light wait |
| Guessed | ○ in the warning colour, "guessed" | Nothing stands behind it: the noise model of a camera nobody has measured |

---

## 6. The sittings

### 6.0 What every sitting shares

- **A burst** is a number of frames at one ISO and one shutter time with the focus and the
  target untouched. A sitting is a list of bursts. Sittings 1 and 2 are always single
  shots: four-shot darks equal single-shot darks (MEASURED 2026-11-14, 1.335 against
  1.330 DN).
- **On a rig Strehl drives** a sitting runs in four stages the page names as it goes:
  *Check* (live view, a few seconds: is this the right target?), *Shoot* (the host takes
  the bursts as a capture of kind `setup`, section 11.2), *Read* (the engine's
  `strehl setup <sitting>`, section 10.4), *Plate* (the result on the stage).
- **By hand** (the button says "From files…") the page shows the shot list in plain words
  with the camera's own settings, and a place to drop the folder. A list needs nothing but the camera, its own controls
  and the thing in front of the lens. `strehl setup sort` groups what was dropped into
  bursts by ISO, shutter and mode signature, tells dark frames from lit ones by their
  level, and shows what it found against the list: "ISO 100, 1/100 s: 8 dark frames.
  ISO 400: 2 dark frames, 8 are needed." Where a list needs frames in a known order
  (Motion), it numbers them and the page shows each dropped frame against its number
  before reading. Then *Read* and *Plate* as on the rig.
- **Left as found.** A sitting on a rig ends by putting back the exposure, the shot mode,
  the light and the focus position it found. MEASURED (M9, R11): on this camera a setting
  that was changed and not shot does not survive the power-off. Three times a restored
  exposure was gone at the next wake, and the camera came up with the last burst's. So the
  sitting's last act is one capture at the settings it found, which it discards.
- **A rig that drives only part of it** never fails for want of the rest. Where the host
  takes the frames but cannot do a step itself (switch the light, move the focus), the
  sitting waits on one sentence and a Continue button: "Cap the lens, then Continue."
- **Time.** MEASURED on the A7CR over the Pi: a burst of 8 single shots takes 16.6 s at
  1/100 s, 22 s at 0.6 s, 27 s at 1.3 s, 37 s at 2.5 s and 82 s at 8 s, so about 2.1 s a
  frame beside its exposure. The page's time for a sitting is that sum, shown before it
  starts.
- **Checks** are listed per sitting with the sentence the person reads when one fails.
  Each has a number in the results that passes it and one that fails it; an implementer
  adding a check supplies both (`AGENTS.md`: "specify an input that makes it fail").
- **The frames' mode** (section 5.3) is read from the first frame and every other frame
  of the sitting must match it. The page shows it before the sitting starts: "14-bit,
  uncompressed, 9504 x 6336".

### 6.1 Dark

**In front of the lens:** nothing. With a light Strehl switches: "Strehl switches the
light off and puts it back afterwards." Otherwise: "Put the lens cap on. On an SLR, cover
the viewfinder too."

**What dark has to mean.** MEASURED (M3, R2, R9), 8 frames a burst, green, the same
night: capped with the door closed; no cap, light off, room not fully dark; and the
capped series of 14 November (16 to 32 frames, at 0.6 s unless marked).

| ISO, shutter | Capped: black, read noise | No cap, light off: black, read noise | 14 November, capped |
| --- | --- | --- | --- |
| 100, 1/100 s | 512.25, 1.311 | 512.22, 1.305 | 1.305 (1/8 s) |
| 100, 2.5 s | 512.29, 1.325 | 512.41, 1.373 | 1.363 (2.5 s) |
| 200, 1/100 s | 512.22, 2.416 | | 2.467 |
| 320, 1/100 s | 512.27, 3.745 | 512.31, 3.754 | 3.836 |
| 400, 1/100 s | 512.19, 2.144 | 512.21, 2.134 | 2.224 |
| 800, 1/100 s | 512.14, 4.171 | | 4.406 |
| 3200, 1/100 s | 512.25, 15.81 | 512.06, 15.75 | 16.81 |
| 100, 1/100 s, capped, light on | 512.25, 1.305 | | |
| 100, 2.5 s, capped, light on | 512.34, 1.319 | | |

- The numbers the engine uses (black and read noise at 1/100 s) are the same with and
  without the cap, within 0.5 %. A rig with a switched light needs no cap.
- The room's stray light shows at 2.5 s and nowhere else: black +0.12 DN and read noise
  +3.6 % against the capped burst. It passes the check below and the page says so in a
  note; it is the passing input nearest the line.
- A cap alone is enough with the light on.
- Tonight's read noise is 2 to 6 % under the 14 November series from ISO 200 up. That
  series was shot at 0.6 s on a camera that had been running for an hour; which of the
  two matters was not separated.

**Shot list.**

| Burst | ISO | Shutter | Frames |
| --- | --- | --- | --- |
| a | The lowest ISO that is not an extension | T1 = 1/100 s | 8 |
| b | The same | T2 = the longest shutter this setup shoots at (Capture's plan; 2.5 s if unknown) | 8 |
| c… | Each further whole stop up to 3200 | T1 | 8 each |
| d… | Where the read noise in DN divided by ISO falls by more than a quarter from one whole stop to the next: the third-stops between them | T1 | 8 each |

A7CR: a, b, five of c and two of d: nine bursts, 2 min 52 s (MEASURED, R9).

**By hand.** "Put the lens cap on. Shoot 8 frames at 1/100 s at each ISO you use, and 8
more at your lowest ISO at your longest exposure." Burst d is offered after the first
read if a fall was found: "The gain mode changes between ISO 200 and 400. Shoot ISO 250
and 320 to find where."

T1 is 1/100 s because every camera's ordinary shutter does it and nothing odd happens
there. MEASURED (M4, R9), A7CR, ISO 100, capped:

| Shutter | 1/8000 s | 1/4000 s | 1/2000 s | 1/1000 s | 1/100 s | 0.6 s | 2.5 s | 8 s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Read noise, DN | 1.546 | 1.385 | 1.318 | 1.325 | 1.311 | 1.323 | 1.325 | 1.594 |
| Black | 512.23 | 512.24 | 512.24 | 512.21 | 512.25 | 512.30 | 512.29 | 512.28 |

A person who stacks at the fastest speeds or with a silent shutter makes a second mode
and measures it there. Long exposures are covered by burst b.

**Check, in live view (rig):** the frame's mean is under 4 of 255 and its 99.9th
percentile under 16 (the test that guarded the 14 November series). Otherwise the sitting
does not start: "The picture is not dark yet."

**Read** (prototype: `experiments/a7cr-calibration-2026-11-14/dark-analysis.rs`), per
burst and per CFA position over the active area:

1. Each photosite's temporal mean `m` and unbiased temporal variance `v`, accumulated
   against the first frame so that 32-bit sums keep precision.
2. `black` = the mean of `m`. `read_dn` = the square root of the mean of `v` (pooled).
   `read_dn_median` = the median of `sqrt(v)`, divided by the median of a chi distribution
   with N-1 degrees over `sqrt(N-1)` (0.952 for 8 frames), so that 8 frames and 32 give
   the same number.
3. Truncation: when the counts of samples more than 1.5 `read_dn` below and above `black`
   differ by more than a fifth, the camera clips its black. Then `read_dn` is taken from
   the upper half alone (the root mean square of `sample - black` over samples at or above
   `black`) and the mode's notes say "black is truncated".
4. Fixed pattern: the spatial deviation of `m` with `mean(v) / N` removed.
5. Hot photosites, from burst b: `m - black` above the larger of 50 DN and 10 `read_dn`.
   Written as a defect map (the existing format, hot arm); the engine's use of it is
   unchanged (off, `defect_map.rs` records why).
6. Long exposures: burst b's `read_dn`, kept as `read_dn_long` with its shutter time. The
   camera holds its black whatever the exposure (the table above), so dark current never
   shows in the level, only as noise. When b reads more than 5 % over a, the mode's notes
   say so: "At 8 s the read noise is 21 % higher (1.59 DN). Strehl's model uses 1.31."
   The engine goes on using burst a's figure; section 14.
7. Row and column noise beyond the photosites' share, and the correlation of a
   photosite's temporal noise with its same-colour neighbours. A correlation above 0.01
   and three times its own error gets the note "<colour> is filtered in camera" (the
   A7CR's blue, MEASURED 2026-11-14).
8. Gain modes: with the points in ISO order, a new mode starts at the first ISO whose
   `read_dn / ISO` is under three quarters of the previous point's. A7CR: 0.0131 at 100,
   0.0121 at 200, 0.0120 at 250, 0.0117 at 320, 0.0054 at 400, 0.0052 at 800, so a mode
   starts at 400 (MEASURED 2026-11-14 and R9).

**Checks.**

| Check | Passes when | Sentence on failure | Measured pass / fail |
| --- | --- | --- | --- |
| Dark | `black_b - black_a` is at most 0.5 DN | "These frames are not dark. The level rises with exposure time: 513.9 at 1/100 s, 969.8 at 2.5 s. Switch the light off or cap the lens." | 0.04 DN capped, 0.09 capped with the light on, 0.19 uncapped in a dim room / 455.9 DN with the light on (R2, R9) |
| A little light (a note, not a failure) | The same rise is over 0.1 DN | "A little light reaches the sensor at long exposures (0.19 DN in 2.5 s). It does not change the numbers Strehl uses; cap the lens if you want it gone." | 0.19 / 0.04 |
| Steady | No frame's mean is further from its burst's than the larger of 0.5 DN and 0.15 `read_dn` | "The black level moved during the burst (1.4 DN). Let the camera idle for a minute and repeat." | 0.05 to 0.21 DN at ISO 100 / none seen; a planted 2 DN step is the failing input |
| One mode | Every frame has the first frame's signature | "Frame 5 is 12-bit and the others are 14-bit. Shoot the sitting in one mode." | |
| Enough | At least 6 frames in every burst | "ISO 400 has 2 dark frames; 8 are needed." | |
| Sane | `read_dn` between 0.2 DN and 2 % of the range | "The read noise does not look like a sensor's (0.0 DN). Are these RAW files as the camera wrote them?" | 1.3 to 15.8 DN / a developed or stacked file |

**Gives:** `black`, `black_declared`, `read_dn`, `read_dn_median` for each ISO;
`read_dn_long` at the lowest; the gain modes; the hot map; the notes.

### 6.2 Bright

**In front of the lens:** anything bright, far out of focus. "A white card that fills the
frame is best: it also gives the dust map, the sensor's fixed pattern and the light's
colour. Whatever is on the stage will do for gain and levels."

**Why a flat field is not needed for gain and levels.** MEASURED (M5, M6, R3): a dragonfly
wing on a black ground, the lens driven 5,000 units from focus, five bursts of 8 at ISO
100 (0.4, 1.3, 3.2, 5 and 8 s), 2 min 40 s:

| | This sitting | Hand-made profile, 2026-11-14 |
| --- | --- | --- |
| Green gain, fit from 30 to 4,000 DN | 0.4040 and 0.4040 DN/e- (the two greens) | 0.4040 |
| Red, blue | 0.3992, 0.3757 | 0.398 to 0.402, 0.37 to 0.38 |
| Top code, green | 16383, 2.13 million samples on it | "the data reach 16383" |
| Linear to | The clip: ratio flat within 0.07 % from 1,300 to 15,400 DN | Not measured |
| Light's drift inside a burst | 0.16 to 0.52 %, removed | 0.3 to 1.2 % |

One burst of 8 at each other ISO, 25 to 33 s each: 0.8078 at ISO 200, 1.2883 at 320,
1.6322 at 400, 3.2782 at 800; against proportional to ISO that is 0.0 %, -0.3 %, +1.0 %
and +1.4 %.

**Shot list.**

| Burst | ISO | Shutter | Frames |
| --- | --- | --- | --- |
| a to e | The lowest ISO | Five shutters from the camera's list that put the frame's top near 8 %, 25 %, 55 %, 85 % and 140 % of the range (the last clips on purpose) | 8 each |
| f… | Each other ISO the Dark sitting measured | The shutter that puts the top near 55 % | 8 each |
| g, h, i (card only) | The lowest ISO | The 55 % shutter, at three different amounts of defocus | 4 each |

"The top" is the 99.9th percentile of green above black; "the range" is the top code
found so far minus black, the container's until a burst clips.

**Shoot (rig).**

1. *Out of focus.* The page notes where the axis is, then drives it 100 sharp depths away
   (5,000 units on this lens when no depth is known), toward the end with more travel. In
   live view the fine contrast (section 7.0's tile measure, summed over the frame) must
   fall under a tenth of what it was; if not, it drives further. On an axis it cannot
   drive it shows the same bar and says "Turn the focus well away from the subject until
   the bar is under the line."
2. *Exposure.* One test frame at the camera's shutter gives the top; the five shutters
   follow by proportion. If the longest shutter cannot reach 85 %, the page says "This
   scene is too dim to reach the top of the range at ISO 100. Gain is measured; the clip
   level is measured at ISO 400", and does that.
3. The bursts, in the order a to e, f, then g to i with the axis moved by a quarter of the
   defocus between them. The card is never touched (rule 1).

**By hand.** The list, in the page's words:

> Turn the focus well away from the subject, so that nothing in the frame is sharp. At
> your lowest ISO shoot 8 frames at each of five exposures, from dim to clearly
> overexposed. With a continuous light, change the shutter time: a quarter of your usual,
> your usual, then 2.5, 4 and 6 times it. With a flash, change its power over the same
> range. Then 8 frames at each other ISO you shoot at, at your usual exposure. Touch
> nothing between frames. If you have a white card that fills the frame: 3 more bursts of
> 4, moving the card a finger's width between them.

The page reads what was dropped against what it needs and says what is missing in the
words of the checks below: "Nothing clipped: add one burst twice as bright." The five
exposures need not be exact; the Spread and Reaches the top checks are what count.

**With a flash** the same analysis holds: flash-to-flash differences are removed frame by
frame exactly as a continuous light's drift is, and reported as the light's steadiness
("Flash to flash 3.1 %"). The Light check is then advice, not a ring. UNVERIFIED: no flash
series was shot for this design.

**Read** (prototype: `experiments/setup-page-2026-11-27/sensor.rs`), per burst and CFA
position:

1. The burst's frame levels: each frame's mean above black over photosites that are
   between 100 DN above black and half the range in the first frame. `d2` = the variance
   of those levels divided by their mean squared. A colour with no such photosites takes
   green's.
2. Each photosite's temporal mean `S` above black and unbiased variance `V`; `V' = V - S^2
   d2` removes the light's drift.
3. `S` and `V'` averaged in bins 128 DN wide. **Gain** = the slope of a weighted line
   through bins holding at least 500 photosites with `S` from 30 DN to a quarter of the
   range (weights: count over predicted variance squared, eight iterations). The intercept
   is not used; read noise comes from the Dark sitting (MEASURED: the intercept reads
   -0.07 DN^2 where the darks give +1.78).
4. **Clip** = the highest code present, in a burst where at least one sample in ten
   thousand of that colour sits on it.
5. **Linear to**: for each pair of consecutive bursts, the sum of the longer's `S` over
   the sum of the shorter's, in the same 128 DN bins of the longer's `S` (photosites with
   the shorter's `S` at least 64 DN). `flat` = the median over bins from 10 % to 40 % of
   the range. `linear_to` = the lower edge of the first run of three bins more than 1 %
   from `flat`; the clip, when there is none below it.
6. **White for the engine** (decision 3): `clip - 3 sqrt(read_dn^2 + gain (clip -
   black))`, the highest level whose samples do not reach the clip (DERIVED). A7CR at
   ISO 100: 16383 - 240 = 16143.
7. Card only, where at least four fifths of the frame's 2 x 2 cells are above a quarter of
   the range in bursts g to i:
   - **Fixed pattern** (`prnu_kappa`), per colour: the variance of `mean / smooth(mean) -
     1` (three passes of a 61-cell box, `defect_map.rs`'s high-pass) less the noise's
     share `gain / (S N)`; its square root. For comparison: 0.30, 0.35 and 0.40 % on the
     A7CR by the stack's own frames (MEASURED 2026-11-16).
   - **Dust**: bursts g, h and i are three captures for `defect_map::detect_dust` as it
     stands (median across captures, recurrence, depth floor, component size; VERIFIED on
     the A7C II's flats, 4 motes and 618 cells, with every capture rolled 0). The map is
     kept with the lens part at this f-number.
   - **Balance**, when the person ticks "the card is neutral": green's mean over red's and
     over blue's.
   Where the cover is less, the plate hatches the uncovered part "not measured" and gives
   no fixed pattern.
8. **Light's steadiness**: the median over bursts of the frame levels' relative
   deviation, at the 55 % shutter.

**Checks.**

| Check | Passes when | Sentence on failure | Measured pass / fail |
| --- | --- | --- | --- |
| Out of focus and still | Gain fitted from the even frames and from the odd frames agrees within 1 %, and variance over signal stays within 6 % of the fit up to a quarter of the range | "The picture changed between frames. Move the focus further from the subject, and wait for the rig to be still." | 0.40407 against 0.40404 (2026-11-14); 0.395 to 0.415 against 0.404 (R3) / a burst in focus, drifting 0.1 px |
| Spread | At least 20 bins hold 500 photosites between 30 DN and a quarter of the range | "The scene is too even or too dark to measure gain. Use something with light and dark parts, or a brighter light." | 126 bins / a lens-capped burst |
| Reaches the top | In the longest burst at least one green sample in a thousand is on the top code | "Nothing reached the top of the range, so the clip level was not measured." (the rest is kept) | 1.8 % / the 5 s burst, top 13679 |
| Light | The frame levels' relative deviation is under 2 % in every burst | "The light changed by 4.1 % during a burst. It was removed; measure again when the light has warmed up." (kept, ringed) | 0.16 to 0.52 % / the minute after switch-on |
| Colours agree | Red's and blue's gain within 10 % of green's | No failure: the note "<colour> reads 7 % low: the camera filters it" | A7CR blue 0.930 of green |
| Full well | `gain x (clip - black)`, in electrons, between 1,000 and 500,000 | "The gain does not look like a sensor's." | 39,300 e- |

**Gives:** `gain_dn_per_e`, `clip`, `linear_to` for each ISO; `prnu_kappa`; the dust map
(lens part); `balance` and `steadiness` (light part).

### 6.3 Scale

**In front of the lens:** something with a known length, in focus, lying square to the
lens. A ruler when more than 2 mm is in view; a stage micrometer or a calibration slide's
grid above about 5x.

**Shoot:** one single shot at the subject's exposure. **By hand:** one RAW of the target
dropped on the page. A person who already knows their scale types it instead (4.3).

**On the stage** the frame at fit, with two tools:

- **Pitch.** The person drags a band along a run of evenly spaced marks, or a box over a
  grid. Strehl finds the pitch in pixels and draws a tick on every mark it counted. The
  person types what one pitch is ("0.1 mm"), or what the counted marks span ("23 marks,
  2.3 mm").
- **Length.** The person drags from one mark to another and types the length. The ends
  snap to the nearest edge's half-height crossing along the line. For targets with no
  repeating marks.

**Read**, for a band: the samples along its long axis, averaged across its width (32
pixels unless dragged wider), mean removed, a Hann window, a Fourier transform; the
strongest peak between 3 cycles and a third of the samples; its frequency refined by the
centroid of the power in the five bins around it. For a box: the same in two dimensions,
the two strongest peaks not opposite each other. Green photosites only (the half-resolution
green plane), so that lateral colour does not enter.

MEASURED (M10, R6) on the owner's slide, a 768-sample box in two places: 108.46 and 108.56
sensor pixels along the two axes, then 108.36 and 108.13: 0.4 % between regions with the
plain centroid.

**Checks.**

| Check | Passes when | Sentence on failure |
| --- | --- | --- |
| Two halves | The pitch from the band's two halves (the box's two axes) agrees within 0.5 % | "The two ends disagree by 0.8 %. The target is tilted, or not in focus across the band." (kept with the spread shown, ringed) |
| Enough | At least 10 pitches, or a length of at least 1,000 pixels | "Too few marks for a scale: 4. Drag across more of them." |
| Marks | The peak holds at least half the band's power outside its mean | "No regular marks were found along the band." |

**Gives:** one `scale` sample in the lens part: micrometres per pixel, the focus position
if the axis reports one, the date. Magnification is shown when the camera part has a pixel
pitch (`pixel pitch / um_per_px`).

**How it is used.** A stack's scale is the sample nearest its median focus position;
between two samples, linear in position. Outside the samples the nearest one holds and the
scale bar's popover says "measured at 43,450; this stack is at 61,800". The subject page's
"Measured on a slide" and "Magnification and pixel pitch" entries stay and win when the
person has set them for a subject.

Not here: the shape of magnification against focus position could be read from every
stack's fitted alignment and anchored by one sample. It is ARGUED, not measured, and
rule 8 wants care; section 16.

### 6.4 Detail

**From:** a stack with fine detail over most of the frame, shot with this camera and lens.
"Use a stack you have shot" lists the Library's stacks whose first frame matches the
setup's camera and lens; a folder can be dropped instead. A person with no stack yet
shoots one in Capture; the page links there. There is no separate capture for this
sitting.

**Lateral colour.** MEASURED (R7) with the engine's own per-stack instrument
(`strehl_core::ca_refine::measure` on its preview render), the A7CR coin stack of 107
planes, starting from a profile of zero:

| | Red, ppm | Blue, ppm | Tiles | Time |
| --- | --- | --- | --- | --- |
| Pass 1, from nothing | -404.9 | +191.8 | 613 of 625 | 2.7 s |
| Pass 2 finds left over | +19.4 | -4.0 | 615 of 631 | 2.7 s |
| Two passes, total | -385.5 | +187.8 | | |
| From the shipped profile (-464.6, +205.6), one pass leaves +82.3, -17.5; total | -382.3 | +188.1 | 613 of 631 | |

So the instrument reaches the same total from nothing as from the profile, within 3.2 ppm
in red and 0.3 in blue. The shipped profile itself was read 82 ppm away in red by a
different instrument on the same stack, inside the 151 ppm that `optics.rs` records
between subjects.

**Read.**

1. Pass 1: the preview render with no colour correction, measured at a quarter of the
   resolution (so that the instrument's 3-pixel limit spans 12 sensor pixels: 2,000 ppm at
   the corner of a 61-megapixel frame), then at full resolution with that applied.
2. Pass 2: again with the sum applied. The part's `lateral` is the sum of the passes; its
   fit statistics are pass 2's.
3. Sharp depth at this focus position: `strehl focus-step` as it stands.
4. The working aperture: the restoration's cutoff fit for this stack, when it made one
   (`optical-cutoffs.rs`).

**Checks.**

| Check | Passes when | Sentence on failure |
| --- | --- | --- |
| Tiles | At least 200 tiles kept by the fit for each colour | "This stack has too little fine detail across the frame to measure the lens (37 tiles). Use a subject that fills the frame." |
| Converged | Pass 2's scale is under 40 ppm for both colours | "The measurement did not settle (pass 2 moved it by 180 ppm)." |
| Halves | The fit from tiles left of centre and from tiles right of centre agree within 80 ppm | "The left and right halves disagree: the lens may be decentred, or the subject is coloured on one side." (kept, ringed) |
| Size | Scale under 3,000 ppm and translation under 3 pixels | "This is more colour shift than a lens gives. Was the stack rendered from RAW by Strehl?" |

**Gives:** the lens part's `lateral`, one `depth` sample, one `cutoff` record.

**Two more readings from the same stack** (stage P10, decision 7: proposed here, and the
last things to build).

- *Colour focus.* Red and blue come to focus at a different depth from green. The sharp
  depth's measure (`focus-step`, a tile's contrast against focus) is taken on the red
  and on the blue photosites as well as the green; the median over tiles of red's peak
  less green's, and of blue's less green's, in the axis's unit, goes to `colour_focus`
  and is drawn on the Depth plate as three curves. MEASURED 2026-11-16 by another route
  (`point-focus.py`, the scarab stack at a step of 8 units): red peaks 3 to 3.5 frames
  after green and blue 2 to 2.5, and at green's focus red keeps 0.93 and blue 0.96 of
  their own peak. No default render uses it (`STREHL_AXIAL_CA` is off). It tells a person
  what a coarse step costs first, and it is the number that switch would start from.
- *Level.* When the person says the stack is of a flat target, each tile's best focus
  (`strehl survey`'s `maps.focus`) is fitted with a plane, then a plane and a bowl: the
  tilt across the frame's width and height and the field's curvature, in the axis's unit
  and in sharp depths, kept in the rig part's `level` and drawn on a Level plate as
  contours over the frame. It says how square the stage lies to the sensor, which a
  rebuilt stand or a tiled capture needs. ARGUED, and not measured: the flat-target
  stacks on disk are too shallow. Its guard is measured (R10): on the slide stack of
  2026-11-25 (6 planes over 38 units) 3,622 of 14,751 tiles peak inside the stack and
  7,119 are sharpest at its first plane, and the fit that results is not to be believed.
  The check: at least four fifths of the tiles with detail peak inside the stack, or
  "The stack is too shallow to tell: 7,119 tiles are sharpest at or before its first
  plane. Shoot from further below the target to further above it."

**What the engine does without it** (decision 4): today an unknown lens gets no colour
correction (F4). With the default of decision 4 the engine runs the same two passes on
every stack whose lens has no part, and the Stack station's checks row says "Lens colour
measured on this stack (no lens in Setup)". The Detail sitting then matters for stacks
with too little detail to measure themselves, and for the plate.

---

## 7. Motion and Warm-up

These two are about the rig and the light, not the sensor or the lens. A host does them
unattended. By hand they are shot lists like the others (4.2). They measure what Capture
takes from constants today (F8).

### 7.0 The fingerprint: reading where the lens is from live view

Both parts of Motion need to know where the focus axis actually is, to a fraction of the
sharp depth, without trusting the number the camera reports. The instrument:

1. **Sweep.** With a detailed subject in focus at position `P`, step from `P - 1.25 W` to
   `P + 1.25 W` in 33 steps, always from below (`W` is the sharp depth; 52 units on this
   lens, so 4 units a step), and keep two live frames at each.
2. **Tiles.** Each live frame is cut into 32-pixel tiles; a tile's contrast is the mean
   square of its luma less a 1.5-pixel Gaussian blur of it, over its mean luma squared
   plus 16 squared. (This is the measure of `capture-sweep.rs`'s `frame_tiles` in all but
   constants; the implementer uses that function.)
3. **Fingerprint.** For each tile, contrast against position, from the sweep, joined by
   straight lines. Tiles are kept whose contrast changes over the sweep by more than six
   times the difference between their two frames (310 of 672 here).
4. **Read.** A frame's position is the `p` that minimises the weighted squared difference
   between its tiles and `g x fingerprint(p)`, with the gain `g` solved at each `p`. The
   gain matters: live view's brightness changes by 4 % from frame to frame, and without
   it a brighter frame reads 2 units further (MEASURED, R5).

MEASURED (R5): a frame of the sweep read against the fingerprint returns its own position
within 0.16 units; with its own position left out of the fingerprint, within 1.8 units
(worst 6.6). A second sweep four minutes later reads 1.6 units lower. So the instrument is
good to about 2 units, 4 % of the sharp depth, and the page says so on the plate.

The magnifier is not used: the camera drops it on every focus move (M9).

**By hand** the same reading is made from RAW frames instead of live ones: the sweep is a
short stack at the person's finest step, the tiles are 64-pixel tiles of the
half-resolution green plane, and positions count in the typed step or in frames. The
arithmetic is the same function. UNVERIFIED on RAW frames: the lens was capped by the
time this was written down; stage P6 gates it against the live-view result on this rig.

### 7.1 Motion: Return

**In front of the lens:** a subject with fine detail at several depths, in focus. The
subject of a capture will do; the sitting can run just before one.

**Shoot** (live view only, no RAW; 4 min 46 s on the rig, which included R5's recordings
after short moves):
the sweep, then arrivals at `P`, two live frames each, six of each kind, the kinds
interleaved: from below and from above by the plan's approach (128 units), by an eighth of
it (16) and by the plan's step (8); and four each from 5,000 units below and above,
directly and followed by an approach from below. Then the sweep again.

MEASURED (M8, R5), position read minus `P`, in units; the sharp depth is 52:

| Arriving | Mean | Deviation between repeats |
| --- | --- | --- |
| From 128 below (the plan's approach) | -2.1 | 0.8 |
| From 128 above | -6.2 | 0.2 |
| From 16 below / above | -5.3 / -4.9 | 1.1 / 1.1 |
| From 8 below / above | -4.6 / -5.4 | 1.7 / 1.2 |
| From 5,000 above, then 128 from below | -0.9 | 1.1 |
| From 5,000 below, then 128 from below | +3.5 | 4.2 |
| From 5,000 above, directly | -6.0 | 0.2 |
| From 5,000 below, directly | +4.1 | 3.7 |

And for 12 s after a 5,000-unit move, three times each way: from below it sits at +3.2
(deviation 2.0) from the first second to the twelfth, from above at -4.4 (1.8). It does not
creep; it lands off and stays.

What that says about this axis: arriving from above lands about 4 units lower than
arriving from below; a reversal of 8 or 16 units does not undo it, 128 does; a long run
upward leaves 3 to 4 units and more scatter, which one approach does not always remove.
All of it is under a tenth of the sharp depth. For a stack shot in one direction with
steps of 8 it is a constant; for a retake, a mended plane or the first plane after the
calibration's sweep it is the error to expect.

**Read** (`strehl setup motion return`):

- `hysteresis` = the mean from above less the mean from below, at the approach distance.
- `repeat_sd` = the deviation between repeats from the approach side the plan uses.
- `take_up` = the smallest tested distance whose landing, from below, is within the
  instrument's 2 units of the largest's. The rig part's `approach.distance` is that, and
  never less than the plan's present value unless the person takes it.
- `after_far_move` = the offset and scatter after 5,000 units, directly and after one
  approach.

**Checks.**

| Check | Passes when | Sentence on failure |
| --- | --- | --- |
| Detail | At least 150 tiles kept | "Too little of the picture changes with focus here to read the lens's position (41 tiles). Use a subject with detail at several depths." |
| Instrument | Leaving a position out, the sweep reads itself within a tenth of the sharp depth | "The reading is not steady enough to judge (9 units). Is the subject moving, or the light changing?" |
| Drift | The second sweep reads within a tenth of the sharp depth of the first | "Focus drifted 7 units during the test. Let the rig warm up and repeat." |

**By hand**, for a rail or any axis that can be sent back to a position (not the
camera's own bracketing). The list, in the page's words:

> 1. Shoot a stack of 33 frames through the subject at your finest step, going up.
> 2. Go down past the start by your usual run-up, come up to where frame 17 was, shoot one
>    frame. Do that five times.
> 3. Go up past the end, come down to where frame 17 was, shoot one frame. Five times.
> 4. Shoot the stack of step 1 again.

The page shows the 76 dropped frames against the list before it reads them. The answer is
in the person's own unit: "From below it returns within 0.4 of a step. From above it
lands 3 steps low: your rail has 3 steps of backlash. Always arrive from below."

**Live view against RAW** (a lens axis on a host; stage P10, decision 7). Capture's pass
finds the subject in live view and then in RAW, and the two disagree: RAW focus less the
live sweep's peak was +29.8 and +29.0 units on the dragonfly (MEASURED 2026-11-27 by the
pass itself, `LensMemory`; cause not established, and R5 shows it is not the axis's
hysteresis, which is 4 units). After the sweep the sitting takes 13 single shots from
`P - 24` to `P + 24` units, reads each tile's peak from them and from the live frames, and
keeps the median difference in the lens part's `live_offset` by focus position. Capture's
pass starts from it instead of from zero, and goes on measuring its own.

**Gives:** the rig part's `approach`; the lens part's `live_offset`. Capture's Rig step
shows the approach beside the plan's own (8.6).

### 7.2 Motion: Settle

**Why not live view.** MEASURED (R5): the first live frame arrives 0.7 to 0.9 s after a
move is commanded, one live pixel is 9.3 sensor pixels, and by that first frame the
picture is already within 0.3 to 0.5 sensor pixels of where it stays. Live view cannot see
a settle of half a second.

**Shoot** (RAW; 4 min 34 s on the rig): bursts of ten single shots at planes one plan step
apart, at 1/100 s with the ISO raised to keep the exposure (3200 here), so that the
exposure freezes the picture at the moment the settle ends. One burst each with the
settle at 2,000 ms (the reference), then 100, 250, 500, 1,000 and 2,000 ms, twice over,
interleaved. Each uses 11.2's `settle_ms`, so the person's plan is not rewritten.

**Read** (`strehl setup motion settle`; prototype `analysis/e5-an.py`): each frame is
registered against the reference burst's frame at the same position (a 1,536-pixel
central crop, 2 x 2 summed so that no colour pattern remains, a shift with a gain and an
offset). The first plane of every burst waits 2 s after the approach whatever the settle
(`AFTER_APPROACH_MS`), so its shift is the slow drift since the reference and is
subtracted. What is left for planes 2 to 10 is how far the picture was from rest when
the exposure began.

MEASURED (R8), 18 frames at each settle:

| Settle | Median distance from rest, px | 90th percentile |
| --- | --- | --- |
| 100 ms | 0.37 | 0.78 |
| 250 ms | 0.58 | 0.89 |
| 500 ms | 0.29 | 0.61 |
| 1,000 ms | 0.44 | 0.89 |
| 2,000 ms (the later two bursts) | 0.36 | 0.88 |

There is no trend. The picture is as far from rest after 100 ms as after 2 s, and the 0.4
pixels is the rig's own movement between one frame and the next, the same movement the
Still check reports (0.15 to 0.64 px within 0.4 to 2.4 s, `capture-stillness.rs`'s notes).
On this rig the settle is not what moves the picture; this agrees with the pass counts of
2026-11-20 (`SETTLE_MEASURED`: 48 of 48 at 500 ms and at 2 s).

So the sitting's answer has two forms, and the page must be able to give the first:

- "No difference between 100 ms and 2 s. The picture moves 0.4 px between frames whatever
  the settle: the rig's own movement is the limit." The rig part's `settle.ms` is then the
  shortest settle tested, marked with the size of effect the test could have seen. The
  test is of single shots at 1/100 s: it does not see movement inside a long exposure or
  between the four exposures of a group. For those the four-shot checker's pass counts
  stay the evidence, and the page says so beside the value.
- "The picture is still moving at 250 ms (0.9 px against 0.4 at 2 s); it is at rest by
  500 ms." `settle.ms` is the shortest settle from which every longer one is also at
  rest.

The rule: a settle is "still moving" when its median exceeds the reference's by more than
twice the standard error of that difference (1.25 times the pooled deviation over the
square root of the count, for each median; 0.23 px here, with a pooled deviation of 0.28
px). The detection limit is that figure, and it is printed: "would have seen 0.23 px". The
250 ms row sits at its edge (0.22 px over the reference), which is why the page prints the
limit and not a verdict.

**Checks.** Exposure: the 1/100 s frames' 99th percentile is at least 300 DN above black
("Too dark at 1/100 s to register; raise the light"). Registration: the reference burst
registers against itself (even against odd planes shifted back) within 0.1 px.

**Gives:** the rig part's `settle`, with the table. Capture offers it; the plan keeps its
own until the person takes it. `AFTER_APPROACH_MS` stays 2 s: this sitting does not test
the plane after an approach.

**By hand.** "Shoot the same run of ten steps three times: with your controller's settle
delay at 2 s, at the delay you use, and at 2 s again. Use 1/100 s, or flash." The first
run is the reference and the third shows what drift and wander leave; the reading is the
one above.

**Still** is `capture-stillness.rs` as it is, run from this sitting's row and kept in the
rig part with its date. **By hand:** "Shoot ten frames at 1/100 s with nothing touched."
The frames are registered against the first as in Settle, and the movement between
frames is reported with the times between them.

**Timing**: the seconds per plane and per image are read from the bursts every sitting
shoots (a host's journals carry the times; by hand, the files' own times) and kept in
`timing`.

### 7.3 Warm-up

**In front of the lens:** anything lit, in focus or not.

Offered for continuous lights only (4.1). A flash's frame-to-frame steadiness comes from
Bright.

**Check:** the light has been off for 20 minutes (the page knows from the plug, or from
the time it last saw the light go off). "Start anyway" runs it and marks the result "the
light was warm".

**Shoot** (3 min 25 s): the light is switched on and one burst of 70 single shots at the
plan's exposure starts at once, a frame about every 2.9 s.

**By hand.** "Leave the light off for 20 minutes. Set the camera to shoot a frame every 3
to 5 seconds at your usual exposure. Switch the light on, start the camera at once, and
let it run for 4 minutes. Tell Strehl how many seconds passed between the switch and the
first frame." The frames' own times place them, to the second where the file gives no
finer.

**Read** (`strehl setup warm-up`; prototype `analysis/series-an.py`): each frame's level
is its mean above black over photosites that are between 5 % and 50 % of the range in the
first frame, per colour; its position, the registration of 7.2 against the first frame.

MEASURED (R4), from cold (off 20 minutes), level against the mean of the last 35 s:

| Since switch-on | Level | Red over green |
| --- | --- | --- |
| 7 s | +8.1 % | 1.115 |
| 18 s | +4.6 % | 1.122 |
| 30 s | +1.0 % | 1.128 |
| 41 s to 2 min 44 s | within 2.4 %, wandering: +2.4 % at 52 s, +1.1 % at 1 min 50 s | 1.129 to 1.141 |
| 2 min 47 s to 3 min 24 s | within 1.0 % | 1.141 to 1.143 |

The picture moved 1.3 px in those 3 min 24 s (0.4 px a minute). A second series, from 4
min 37 s to 7 min 55 s after an earlier switch-on, held within 0.6 % for two minutes and
then stepped up 4 % over a minute.

- `tolerance` = twice the deviation of the level over the last 60 s (1.05 % here).
- `settled_s` = the time of the first frame after the last one outside that tolerance:
  167 s here. Capture's constant is 150 s (`LIGHT_SETTLED`); this is its first
  measurement by rule.
- `drift_px_per_min` over the last minute.

**Checks.** Two series: the page asks for a second run on another day before it calls the
time measured without a ring, because one series cannot tell a warm-up from a wander
("Measured once. Run it again from cold to confirm."). Falling: the level at 10 s is above
the settled level, or the page says "This light does not droop as it warms; nothing to
wait for" and sets `settled_s` to the first frame inside the tolerance.

**Gives:** the light part's `warm_up`. Capture's pass waits `settled_s` and says where the
number came from. The light's colour was still moving at the end of the series (red over
green +2.4 % in 3 min 24 s), so the Bright sitting's balance is taken after at least five
minutes of light.

---

## 8. The page

### 8.1 Where it is

After `05 Export` in the station bar (`studio-shell-bars.rs`, `stations`), a hairline, then
**Setup**: no numeral, because it is not a step a picture passes through; the same tracked
lettering; the same state mark. Key `6`. The mark is:

| Mark | When |
| --- | --- |
| ● | The current setup's camera has gain and read noise for the ISO in use, measured or shipped, and its lens has a lateral colour record |
| ◐ | Something the app would use is missing: say which in the tip ("Scale not measured") |
| ○ | The camera's noise is guessed |

Only what the setup has counts (rule 11). A setup that works from files in daylight is ●
with its camera and lens measured.

### 8.2 Layout

The skeleton is Capture's (`app-station-capture.rs`, `capture-station.rs`,
`studio-shell.rs`'s `StationLayout`): a control strip, the stage, a strip where Capture has
its rail, and the inspector at the right, 348 px, where Capture has its plan.

```text
 01 Library  02 Capture  03 Stack  04 Develop  05 Export  |  Setup ◐
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ SETUP  A7CR · FE 100 + 2x ▾     ● Camera   ● Lens   ◐ Rig   ○ Light        12 min left    │
├───────────────────────────────────────────────────────────┬──────────────────────────────┤
│  Noise   Levels   Field                      Fit   100 %  │ Sittings  Camera Lens Rig Light│
│                                                           │ ──────────────────────────── │
│                                                           │ 1  Dark                  ●   │
│                                                           │    27 Nov · 7 ISO settings   │
│                 the stage:                                │ 2  Bright                ●   │
│                 live view, or a plate                     │    what goes in front …      │
│                                                           │    9 bursts of 8 · 3 min     │
│                                                           │    [ Measure ] From files…   │
│                                                           │    Gain   0.404   ● 27 Nov   │
│                                                           │    Clip   16,383  ● 27 Nov   │
│                                                           │ 3  Scale                 ○   │
│                                                           │    not measured              │
│                                                           │ 4  Detail                ●   │
│                                                           │    shipped with Strehl       │
│                                                           │ 5  Motion                ◐   │
├───────────────────────────────────────────────────────────┤ 6  Warm-up               ○   │
│ a 100·0.4 s ▮▮▮▮▮▮▮▮  b 100·1.3 s ▮▮▮▮▮▮▮▮  c 100·3.2 s ▮▮▮▯▯▯ │ ──────────────────────────── │
│ d 100·5 s ▯▯▯▯▯▯▯▯  e 100·8 s ▯▯▯▯▯▯▯▯  f 400·1.3 s ▯▯▯▯▯▯▯▯  │ Measure Detail and Motion    │
└───────────────────────────────────────────────────────────┴──────────────────────────────┘
```

**The control strip** (where Capture has its pre-flight chips): the setup's name as a
selector, whose menu is the other setups, New setup…, Rename, Export…, Import…; then one
chip for each part the setup has, with its mark, which opens that part's tab; at the
right, what is left for this setup as time.

**The inspector's first tab, Sittings** (a view that returns intents, as `capture-plan.rs`
does).

- One row for each sitting that applies to this setup (4.2), numbered as in section 3 so
  that a number always means the same sitting. Rows are drawn with `capture-plan.rs`'s
  `step` (hairline, 26 px numeral, green when everything it gives is measured). Closed,
  a row is its name, its mark and one line: the date and what it gave, or what is
  missing in the words of 8.6.
- One row is open at a time. Open, it shows, in this order: the sentence about what goes
  in front of the lens, with a drawn pictogram 48 px high (a cap; a card with a blurred
  edge; a ruler; a patch of fine texture; a double-headed arrow on an axis; a lamp); the
  shot list in one line with its time ("9 bursts of 8 · about 3 min"); the buttons
  **Measure** (primary; present where the host can shoot it) and **From files…** (always;
  primary when it is the only one); and after a run the
  readout (`capture-plan.rs`'s `readout`: what, value, source) with one row for each
  number it gave.
- Under a value that came from this sitting: "● measured 27 Nov". Under one that did not:
  "○ shipped with Strehl", "○ from a file" or "○ guessed". The dot and ring are
  `capture-plan.rs`'s `value_marker` with new words.
- Footer: where section 4.4 applies, **Measure the rig**, with its time and what it will
  skip ("21 min · Warm-up skipped: the light has been off 4 min"). It is the primary
  button of the page on such a rig until those four sittings are measured.
- Sittings that do not apply are not listed. The Rig and Light sheets say why (4.2).

**The stage.**

| State | Shows |
| --- | --- |
| A sitting is open, a rig is connected, nothing running | Live view (`capture-live.rs`'s `LiveView` without Capture's lenses) with the sitting's meter over it (8.3) |
| A sitting is open, by hand | The shot list set large, and the drop target: a ruled rectangle, "Drop the folder here". After a drop: the frames found against the list, and Read |
| Waiting on the person | The live frame, one sentence and Continue: "Cap the lens, then Continue." |
| Measure the rig is running | As Shooting. The progress line has one segment for each of the four sittings, the Sittings tab marks each as it ends, and the plate of the one just finished shows until the next has something to draw |
| Shooting | The last live frame held, dimmed by a third, and over it the burst being shot: "ISO 400 · 1/100 s · frame 5 of 8". The progress line (`capture-plan.rs`'s `progress_line`) has one tick per burst |
| Read | The plate (8.4) |
| No sitting open | The setup's summary plate (8.5) |

The toolbar where Capture has its lens buttons holds the open sitting's plates as buttons
of the same kind (`ButtonKind::On` / `Quiet`): Dark has *Read noise*, *Black*, *Hot*;
Bright has *Noise*, *Levels*, *Field*; Scale has *Target*, *By focus*; Detail has
*Colour*, *Depth*; Motion has *Return*, *Settle*, *Still*; Warm-up has *Level*.

**The strip** (96 px, in the rail's place): one cell for each burst of the open sitting,
in shot-list order. A cell is its letter, ISO and shutter, and one small bar per frame:
outlined when planned, filled as each arrives, struck through when a check dropped it.
Hovering a cell isolates its points on the plate, as the rail's hover isolates a position
in Capture; clicking it keeps the isolation. With no sitting open the strip is empty.

**The inspector's other four tabs** are the parts. A tab is that part's sheet: what it is
identified by, where it came from, every number it holds in a ruled table, and its
actions.

| Sheet | Table | Actions |
| --- | --- | --- |
| Camera | One row per ISO: black, read noise (DN and electrons), gain, clip, linear to. Notes under it | Mode (selector; New mode…), Pixel pitch (a field, filled from the file when it gives one), Use another camera part…, Compare with shipped, Export…, Forget |
| Lens | Lateral colour by focus position; scale samples; depth samples; working aperture; the dust map's date and count | Name of the path (a field: "2x converter, no filter"), Use another…, Export…, Forget a row |
| Rig | The first two answers of 4.1; the axis's unit and step; approach; settle; stillness; level; time per plane | The two answers as ruled choices; name; unit and step (fields, 4.3); Use in Capture (shows what Capture's Rig step will take, 8.6) |
| Light | The third answer of 4.1; warm-up; steadiness; balance | The answer as a ruled choice; name; "The lamp or its setting changed" (rings what depends on it); "No light of its own" removes the part |

A setup with no light part has no Light tab and no Light chip.

Compare with shipped draws both in the sheet's table, the difference in a third column,
and on the open plate as a second line in the third ink.

### 8.3 Meters

A meter is a strip 28 px high along the stage's lower edge while a sitting waits to start.
It reads live view and answers one question.

| Sitting | Meter | Start is offered when |
| --- | --- | --- |
| Dark | A level bar from 0 to 16 of 255 with a mark at 4: "Dark enough" / "Not dark yet" | Mean under 4 and 99.9th percentile under 16. "Start anyway" is always there, quiet |
| Bright | Two bars: fine contrast against its value when the sitting was opened, with a mark at a tenth; and the live histogram with the top marked | Contrast under the mark |
| Scale | The fine contrast in the dragged band: "In focus" at its highest seen | Always |
| Motion | The count of tiles with a peak in live view (`capture-sweep.rs`'s measure): "enough detail" over 150 | Over 150 |
| Warm-up | Minutes since the light went off: "Cold enough" at 20 | At 20; "Start anyway" marks the result "light was warm" |

### 8.4 Plates

A plate is a figure that fills the stage: what was measured as points, what was fitted as
a line, and one sentence. Every number in the Sittings tab can be found on a plate.

| Plate | Across | Up | Drawn | Sentence (example) |
| --- | --- | --- | --- | --- |
| Dark: Read noise | ISO, log | Read noise in DN, log; a second scale in electrons once gain is known | A square at each ISO measured, per colour; gain modes as bands of the raised ground; the model's line through them | "Read noise 1.31 DN at ISO 100. The gain mode changes at ISO 400." |
| Dark: Black | ISO | Black level, DN | Measured black per colour; the file's declared black as a ring; frame-to-frame range as a whisker | "Black is 512.2, as the files declare." |
| Dark: Hot | The frame | | A dot at each hot photosite, larger with level; counts by level beside it | "6 photosites over 50 DN at 2.5 s." |
| Bright: Noise | Signal above black, DN, log | Noise, DN, log | A square per bin and colour; the model `sqrt(read^2 + gain S)` as a line; the read floor as a dashed line; the clip as a wall at the right. Below it, a band 60 px high: variance over signal against signal, with the fitted gain as a line and the fit's range marked | "Gain 0.404 DN per electron. The sensor holds 39,300 electrons at ISO 100: 13.6 stops over its read noise." |
| Bright: Levels | Level of the longer burst, DN | Ratio of two bursts against its flat value, per cent, from -3 to +1 | One curve per burst pair; a band at +-1 %; the clip as a wall; the file's declared white as a dashed line | "Linear to the clip at 16,383. The files declare 15,360." |
| Bright: Field | The frame | | The card's brightness as contour lines every 2 % from the centre; dust as rings sized to the mote; uncovered parts hatched | "4 dust shadows, the deepest 1.8 %. Fixed pattern 0.35 %." |
| Scale: Target | The frame at the band, 100 % | | The picture; a tick on every mark counted; the pitch in pixels; the two halves' values | "108.5 px to a mark. With marks 0.25 mm apart: 2.30 um per pixel, 1.63x." |
| Scale: By focus | Focus position | Micrometres per pixel | A square per sample with its date; lines between | "Measured at 2 positions." |
| Detail: Colour | Distance from the centre, px | Shift against green, px | A point per tile, red and blue; the fitted lines; pass 2's left-over as a second, paler set. Beside it the frame with each tile's shift drawn as a stroke 200 times its length | "Red -385 ppm, blue +188 ppm: 2.2 px and 1.1 px at the corner, removed." |
| Detail: Depth | Focus position | Tile sharpness | The median curve and its quartiles; the half-height width marked | "A point stays sharp over 52 units here." |
| Motion: Return | Where the lens landed, units from the target | One row per way of arriving | A square per arrival; the mean and deviation of each row; the chosen approach marked | "From 128 units below it returns within 0.8 units. From above it lands 4 units low." |
| Motion: Settle | Settle time, ms, log | How far the picture is from rest, px | A square per frame; the median per settle as a line; the reference's median as a band as wide as the detection limit | "No difference between 100 ms and 2 s. The picture moves 0.4 px between frames whatever the settle." |
| Motion: Still | Time span, s, log | Movement, px | `capture-stillness.rs`'s figure, unchanged | Its own sentence |
| Warm-up: Level | Minutes since on | Level against its settled value, per cent | A square per frame; the settled band; the time it is entered | "Inside 1 % from 2 min 47 s after switch-on. Measured once." |

### 8.5 The summary plate

With no sitting open the stage shows the setup on one sheet: a ruled panel for each part
it has, each with its three or four headline numbers in the readout face and their
marks, and under them the one thing most worth doing next with its time: "Scale is
not measured. 1 min with a ruler." This is also what a new person sees first, with most
of it empty.

First visits:

| Situation | The page says | Offers |
| --- | --- | --- |
| No camera known, no rig | "Strehl has not met a camera here yet." | Drop a folder of RAW files from your camera · Connect a rig (Capture's connection sheet) |
| A folder from an unmeasured camera | "Canon EOS R5. Strehl is guessing its noise until you measure it: two sittings, about 10 minutes with the camera in your hands." | Dark and Bright open, From files |
| A rig with a shipped camera and lens | "A7CR with the FE 100mm F2.8 Macro GM OSS + 2X Teleconverter. Shipped with Strehl, measured on another A7CR on 14 November 2026." | Measure your own · Scale, Motion and Warm-up as not measured |
| A new setup | "What do you have?" and the three questions of 4.1, each a row of ruled choices, with what a connected host can see already chosen | Continue, to the summary plate with the sittings that apply |
| A file that cannot be used | Section 9.2's sentence for it | |

### 8.6 Where the rest of the app says it

A missing measurement is said where it costs, in one line, with a link to the sitting.

| Place | Line | When |
| --- | --- | --- |
| Stack station, the checks row (`app-station-stack.rs`, beside "Highlight groups") | "Camera noise guessed · Measure" | The noise model's provenance is `Fallback` (the engine reports it, section 10.2) |
| The same row | "Lens colour measured on this stack" / "Lens colour not corrected" | No lens part; by decision 4 |
| Library, a stack's camera name | A ring before the name; tip "Not measured in Setup" | The same |
| Capture, the Rig step's summary (`capture-plan.rs`, `rig_summary`) | "A7CR · FE 100 + 2x · settle and approach not measured" | The rig part is defaults |
| Capture, the Rig step's settings (`capture-rig-settings.rs`) | Beside Settle, Approach and Light warm-up: "Setup measured 250 ms · Use" | The rig or light part has the value and the plan's differs (the capture spec's rule 2: the person's own setting is never changed) |
| Develop, the scale bar's popover | "Scale from Setup, measured 27 Nov at 43,450" / "typed for this subject" | A scale is drawn |
| `strehl compact` and the desktop's Compact | Refuses as today, with "Measure this camera in Setup first" | No gain for the camera |

### 8.7 Taste

- Square, ruled, lettered in the DIN faces (`studio-fonts.rs`); hairlines; no card, pill,
  glow or rounded corner. Colour is for data: the three sensor colours on plates, the
  accent for a fitted line and for the one primary button.
- A plate is an engraving, not a chart from a library: tick scales with a short tick at
  every division and a long one at each labelled value, numbers in the readout face,
  points as 5 px open squares, no legend box (the colours are named once in the sentence
  or at the line's end), no grid.
- The pictograms are drawn marks in the line weight of the station marks, not icons from
  a set.
- One sentence under a plate, in the words of 8.4. No verdict words: not "good",
  "excellent" or "poor". Numbers and what they were compared with.
- Nothing animates but the progress line and the bars of the strip filling.
- Plates are drawn from the small files of 5.2. Drawing one costs no more than Capture's
  Depth lens: the smoothness gate is section 13's.

---

## 9. Files from other cameras

### 9.1 What the engine accepts

MEASURED on the 24 sample files (M1, M2, R1): what the linked decoder reports before any
of Strehl's gates.

| Body | File | Pattern at the active corner | Black | Declared white | Top code in the data |
| --- | --- | --- | --- | --- | --- |
| Canon EOS R5 | CR3 (compact RAW) | RGGB | 510 | 14008 | 14998 |
| Canon EOS 5D Mark IV | CR2 | RGGB | 511, 512, 511, 512 | 14008 | 16383 |
| Canon EOS 90D | CR3, and compact | RGGB | 512 | 13036 | 15047, 16383 |
| Canon EOS R6 Mark II | CR3, full and cropped | RGGB | 512 | 12735 | 16383 |
| Nikon Z 7 | NEF, 14-bit, uncompressed and compressed | RGGB | 1008 | 15520 | 16383, 16372 |
| Nikon Z 8 | NEF, 14-bit lossless | RGGB | 1008 | 15892 | 16383 (1.5 million samples) |
| Nikon D850 | NEF, 12-bit, both compressions | RGGB | 100 | 3880 | 1047, 903 (not clipped) |
| Panasonic S1R | RW2 | **GBRG** | 510 | 16380 | 16368 at the 99.9th percentile |
| Panasonic GH5 | RW2 | RGGB | 129, 128, 128, 129 | 4095 | 4095 |
| Pentax K-1 II | DNG and PEF | RGGB | 64 | 16318 | 16382 |
| Hasselblad X1D II | 3FR | RGGB | 256 | 65535 | 65535 |
| Sony A7R V | ARW, lossless | RGGB | 512 | 15360 | 16383 |

The changes, all in `strehl-raw` unless named:

1. **Scanning.** `is_raw_path` accepts, beside `.arw` and the archive: `cr2`, `cr3`,
   `nef`, `nrw`, `dng`, `pef`, `rw2`, `orf`, `raf`, `3fr`, `fff`, `iiq`, `srw`, `erf`,
   `rwl`. One folder holds one of them. The texts that say ".ARW" (`jobs.rs`,
   `library-station.rs`, `bracket-browser.rs`) say "RAW".
2. **One sample per pixel, integers.** As today, with 9.2's sentences.
3. **Any Bayer order.** A pattern that is a 2 x 2 arrangement of one red, two greens on a
   diagonal and one blue is accepted. The active area's corner moves one column, one row
   or both so that it starts on red, and its width and height shrink to stay even. Every
   consumer keeps assuming RGGB at the active corner (`CfaPlane::rggb_at`,
   `pixel_shift::cfa_colour`); none changes. The move is recorded in the camera part
   (`sensor.origin_shift`).
4. **Black per colour.** The decoder's four black levels are read, not the first. When
   they differ, each colour's samples are shifted at decode by the rounded difference from
   the highest, so that one black holds for the frame (storage stays `u16`; the two bodies
   that differ, differ by 1 DN). `Frame` gains `black_declared: [f32; 4]` for Setup.
5. **The top of the container.** `clip::CONTAINER_MAX_DN` (16383) stops being a constant.
   `Frame` gains `container_max: u16`: the camera part's `clip` for this ISO when it has
   one; else the smallest of 4095, 16383 and 65535 that holds the declared white. Its
   uses change to read it: `merge_cmd.rs` (four), `highlight-fusion.rs` (four),
   `color.rs` (one), `strehl-raw-codec/src/calibrated.rs` (`WHITE`, which the calibrated
   archive must take from the frame it stores).
6. **Identity.** Make, model, lens name, f-number, ISO and exposure time come from the
   decoder's own metadata for every maker (`raw_metadata(..).exif`, as
   `experiments/setup-page-2026-11-27/probe-any.rs` reads them). Sony's lens code and
   focus metadata stay Sony's and optional. 4 of the 18 files give no lens name: the lens
   part's `name` is then what the person typed.
7. **Order.** A stack that Strehl did not capture is in file-name order, as today.

### 9.2 What it refuses, and how it says so

| File | Sentence |
| --- | --- |
| Fujifilm X-Trans (the decoder reports a 6 x 6 pattern) | "This camera's sensor has Fujifilm's X-Trans colour layout. Strehl reads Bayer sensors only." |
| Three samples per pixel (Canon sRAW and mRAW, Sony's M and S lossless) | "This is a reduced-size RAW. The camera has already made its own pixels from the sensor's. Shoot full-size RAW." |
| Nikon High Efficiency NEF | "Strehl cannot read Nikon's High Efficiency RAW. Set RAW recording to lossless compression." |
| A DNG with developed pixels, or floating point | "This DNG holds developed pixels, not the sensor's. Use the camera's own RAW files." |
| Anything else the decoder does not open | The decoder's reason, after "Strehl cannot read this file:" |

They appear where a folder is dropped (Library, Setup) in place of today's "contains no
.ARW … frames".

### 9.3 Gate

`experiments/setup-page-2026-11-27/analysis/samples.py` fetches the 24 files (public,
CC0, 1.1 GB, not committed). A test, skipped when they are absent as the private-corpus
tests are, asserts for each: accepted or refused as the table says; black, the pattern's
shift and the container. For the shift, the check that can fail: with the corner moved as
decided, the two sites the engine calls green must agree with each other better than
either agrees with the other diagonal (mean absolute difference of the half-resolution
planes), on every accepted file; move the corner one column further and the test must
fail.

Not gated here, and section 14 says so: no stack from another maker has been rendered,
because none is on disk.

---

## 10. Engine

### 10.1 `strehl-core/src/setup.rs` (new)

The types of section 5, their `serde` forms, the folder's resolution (5.2), reading with
the shipped parts embedded, and writing by temporary file and rename. Three lookups:

```rust
pub fn camera_for(model: &str, serial: Option<&str>) -> Option<Arc<CameraPart>>;
pub fn lens_for(camera_model: &str, lens: &LensId, f_number: f32, focus: Option<f64>,
                prefer: Option<&str>) -> Option<Arc<LensPart>>;
pub fn keep(result: &SittingResult) -> Result<Kept>;   // merges a sitting's result into its part
```

Precedence for a camera: a part measured here, then an imported one, then the shipped
one (decision 6). `keep` replaces only the ISO points and records the sitting gave, and
returns what it replaced so the page can show both (rule 5).

### 10.2 The noise model

`profile::noise_model_for` keeps its signature and reads `setup::camera_for`, by section
5.3's three steps. `CameraProfile` and the `PROFILES` table go; their numbers are the two
shipped files.

- `Provenance::Measured` today means "fitted from this stack" and is built only in tests.
  It becomes "measured in Setup on this machine"; `Profile` stays "shipped"; the stack
  printout's three sentences change to match.
- The engine tells the desktop: one `ui-progress.rs` event at the start of a render,
  `event=camera` with `provenance`, `iso`, and `from_iso` when step 2 of 5.3 was used.
  `pipeline.rs` carries it to the Stack station's checks row (8.6).
- `strehl compact` reads the same lookup; its refusal gains the sentence of 8.6.
- `merge_cmd/self-flat.rs`'s prior takes `prnu_kappa` when the camera part has it, in
  place of its two compiled cases.

**Gate (E1).** With `STREHL_SETUP_DIR=off` and with the default folder holding no measured
part, the A7C II byte-freeze and the A7CR default render are byte-identical to
`31e778bfb`, GPU and CPU fold. The existing test
`the_a7cr_profile_reproduces_its_dark_floor_and_errs_high_within_a_mode` passes reading
the file.

### 10.3 Lens colour

`optics::OpticalProfile` is built from a lens part's `lateral` record nearest the stack's
focus position (owned, no longer `&'static`); `profile_for_capture` matches by 5.4's rule;
the two compiled profiles are the two shipped lens files, each with one record.

MEASURED (R7): the lens's colour shift is not one number. With the same lens, converter
and aperture the instrument reads red at -385 ppm on the coin, -305 on the dragonfly,
-234 on the stack at 31,239 and -215 at closest focus (61,812); blue at +188, +60, +30
and +131. `ca-refine.rs` already records why (the scene's spectrum weights each colour's
wavelength). So a stored record is a start and a fallback, never the answer, and the
per-stack measurement is what a render uses.

Decision 4's default: `ca_refine::applicable` stops requiring a profile. With no lens
part the preview is measured twice from nothing as section 6.4 describes, under the wider
bounds of that section's Size check; with a part, once on top of it under today's bounds
(1,000 ppm, 1.5 px), as now. One `event=lens_colour` reports `source` (`part`, `stack` or
`none`) and the two totals.

**Gate (E4).** From nothing, two passes, on the four A7CR stacks of R7, against one pass
on top of the shipped profile:

| Stack | From nothing, red / blue | From the shipped profile, red / blue |
| --- | --- | --- |
| Coin, single shot (`stack-1794689213508-11226`) | -385.5 / +187.8 | -382.3 / +188.1 |
| Dragonfly (`stack-1795713444768-14989`) | -305.4 / +60.2 | -307.9 / +63.4 |
| `stack-1795433406862-8651` | -233.5 / +29.9 | -240.7 / +30.1 |
| Close tile (`stack-1795476520452-8651`) | -214.9 / +131.3 | -251.1 / +136.6 |

The implementation reproduces the left column within 10 ppm. Renders of the first three
with the shipped lens file present are byte-identical to today's (rule 10). The failing
input: a stack of a featureless card must report "no fit" and render uncorrected, not
apply a wild number.

### 10.4 `strehl setup`

One subcommand with the sittings under it, in `strehl-cli/src/setup-cmd.rs` and one file
per sitting (`setup-dark.rs`, `setup-bright.rs`, `setup-scale.rs`, `setup-detail.rs`,
`setup-motion.rs`, `setup-warm-up.rs`). Each reads folders, writes a result as JSON
(`--json`) and prints the same in words. None writes a part; `strehl setup keep
<result.json>` does, through `setup::keep`.

```text
strehl setup sort    <folder>...                 bursts found, their roles, against the shot list
strehl setup dark    <folder>...                 section 6.1
strehl setup bright  <folder>...                 section 6.2
strehl setup scale   <raw> --band x0,y0,x1,y1[,width] | --box x,y,w,h     section 6.3
strehl setup detail  <stack folder>              section 6.4
strehl setup motion  return|settle <recording>   section 7.1, 7.2
strehl setup warm-up <folder> --on <unix>        section 7.3
strehl setup show    [--camera M] [--iso I]      what the engine would use, and from where
strehl setup keep    <result.json>
```

A result is `{ schema, sitting, taken_under, gives: {..}, checks: [ { name, pass, measured,
sentence } ], plate: {..} }`. The exit code is 0 when the frames were read, whatever the
checks say; the desktop reads the checks.

Speed, MEASURED with the prototypes on this machine (61-megapixel archived frames): 2.0
to 2.4 s to read a burst of 8 in either sitting. A whole Dark or Bright sitting reads in
under half a minute.

### 10.5 What changes pixels, and what does not

| Change | Renders of stacks from the two shipped cameras | Renders from a new camera |
| --- | --- | --- |
| Parts as files (E1) | Byte-identical | Nothing yet |
| Other makers' files (E2) | Byte-identical | Decode at all |
| A measured noise model (E3) | Unchanged until the person measures their own body; then by the difference (the A7CR tonight: gain +1.0 % at ISO 400) | The guessed model is replaced |
| Lens colour from nothing (E4) | Byte-identical while the shipped lens file matches | Corrected |
| White from the measured clip | **Changes** A7CR renders near the top of the range. Decision 3, off until decided | Uses the measured clip from the start: there is no earlier render to keep |
| Dust map, fixed pattern | Measured, stored, drawn. Not applied: both corrections are off by default today (`STREHL_DEFECT`, `Corrections::prnu`) and turning one on is a shipping decision with its own before and after (`AGENTS.md`, Shipping performance). Decision 5 | The same |
| Scale | Display only | Display only |

---

## 11. Host

### 11.1 The setup a stack was shot with

No host change. At Start the desktop writes the current setup's part names into the
stack's catalog record; a stack imported later has none and matches by section 5.4.

### 11.2 A capture kind for sittings

`capture_positions` (`strehl-capture/src/session.rs`, `worker.rs`) gains:

| Field | Values | Why |
| --- | --- | --- |
| `kind: "setup"` | Beside `"positions"` and `"test"` | Journalled as `capture_kind` "setup": the PC neither follows it nor lists it as a stack, and error correction does not wait for a verdict (as for `"test"`) |
| `light` | `"wake"` (default, today's behaviour under managed power), `"keep"`, `"off"` | MEASURED (M9): with managed power on, every capture switches the light on, so a dark burst is lit. `"off"` switches it off first and leaves it off; `"keep"` does not touch it |
| `exposures: [ { iso, shutter } ]` | One per position; generalises `shutters` | A sitting's bursts differ in ISO as well as shutter; one command per sitting avoids a mode change the worker has to idle through between bursts |
| `settle_ms` | Optional, for this run only | The settle ladder (7.2) without rewriting the person's plan |

Kind `"setup"` never powers the camera or the light down at its end, whatever the power
plan says. Its last capture is one group at the exposure and shot mode it started with,
marked in the journal to be discarded on the PC (6.0, "Left as found").

The receiver keeps a `"setup"` run in `setup\scratch\` rather than among the captures.

### 11.3 Capabilities

The page asks the host what it can do and never what it is. `/api/state.capabilities`
(it exists) gains:

| Capability | Sittings that need it |
| --- | --- |
| `sets_exposure` (with the ISO and shutter lists the state already carries) | Dark, Bright on the rig |
| `drives_focus`, with `focus_unit` and the travel | Bright's defocus, Motion |
| `live_view` | Every meter; Motion's return test |
| `switches_light` | Dark without a cap; Warm-up |
| `reports_focus` | A focus position on scale, depth and colour records |

A step whose capability is missing waits on the person (6.0), and every sitting has its
by-hand form (4.2). The capabilities also fill in section 4.1's answers for a new setup:
a host that reports `drives_focus` and `switches_light` is the rig of section 4.4.

### 11.4 Who the camera is

`ptp.rs` reports the literal "ILCE-7CR" (two places). It reads the model and serial from
the device's own description instead. The lens comes from the first frame's file, on the
PC.

---

## 12. Desktop

### 12.1 The station

`Station::Setup`, the sixth, through the touch points every station has: `studio-route.rs`
(`Station`, `ALL`, `number`, `label`, `has_state`; `Route::Setup(SetupView)`, `station()`,
`for_station`, `key()`; `LaunchRoute` and `NAMES`; `Navigator::legacy` with no `Sidebar`
mapping), `studio-shell.rs` (`station_layout`, `station_paints_legacy`, `station_canvas`,
`station_control_strip`, the inspector's tabs, body and footer, the last-station restore),
`studio-shell-bars.rs` (`stations` draws it after a rule with no numeral; `station_mark`,
the palette's icons, `station_purpose`, `hints`, `tip`), `studio-preferences.rs`
(`sanitized` admits 6), `app.rs` (offscreen readiness), `scripts/strehl-control.py` and
`docs/desktop-control.md` (`--route setup`).

`SetupView { open: Option<Sitting>, sheet: Part, plate: Plate }`.

### 12.2 New files (`strehl-ui/src`)

| File | Holds |
| --- | --- |
| `app-station-setup.rs` | The adapter: layout, where the views are placed, intents applied |
| `setup-station.rs` | The station's state: the store, the open sitting, the run in progress |
| `setup-column.rs` | The column as a view returning intents (8.2) |
| `setup-sheets.rs` | The inspector's four sheets |
| `setup-plates.rs` | The plates of 8.4 and 8.5, drawn from plate files |
| `setup-meters.rs` | The meters of 8.3 |
| `setup-run.rs` | A sitting as a small state machine, Check, Shoot, Read, Plate, with stop and failure, in the manner of `capture-measure.rs`'s `Pass` |
| `setup-files.rs` | The files path: the shot list's words, the drop, `strehl setup sort` |
| `setup-store.rs` | The folder of 5.2 through `strehl_core::setup`; watching it for a part kept by the command line |
| `setup-equipment.rs` | Section 4: the three questions as a view, and one function, `applies(setup) -> [Sitting]`, that the Sittings tab, the station's mark and Measure the rig all read |
| `setup-chain.rs` | Measure the rig (4.4): the order, the waits, what is skipped and why, stop and restore |
| `setup-fixture.rs` | Fixtures (12.5) |

Reused as they are: `capture-client.rs` and `capture-host.rs` (the host), `capture-live.rs`
(`LiveView`), `capture-sweep.rs` (`frame_tiles`, the contrast measure of the meters and of
Motion), `capture-stillness.rs` (Still), `capture-tools.rs` (`EngineJob`),
`capture-style.rs` and `studio-widgets.rs`.

### 12.3 What Capture takes from a setup

| Today | With a setup |
| --- | --- |
| `capture-measure.rs` `LIGHT_SETTLED` (150 s) | The light part's `warm_up.settled_s` when measured |
| `capture-measure.rs` `LensMemory.entries` (sharp depth and coarse-to-fine offset by position) | Written to and read from the lens part's `depth` and the rig part's `approach.after_far_move` |
| The plan's settle and approach defaults (`model.rs`, 500 ms and 128) | Offered from the rig part beside the plan's own (8.6); never changed for the person |
| `capture-stillness.rs` `sensor_width`, `capture-auto-subject.rs` `active_px`, `capture-client.rs` `FORMAT_2_OVER_1` (per-model tables) | The camera part's `sensor` |
| `timing.rs` and `capture-guide.rs` time estimates (A7CR constants) | The rig part's `timing` when measured |

### 12.4 Control

Requests (`agent-interface.rs`, `app-agent.rs`, `docs/desktop-control.md`):
`setup_describe { frames, axis, light }`, `setup_measure_rig`, `setup_continue`, `open_setup`,
`setup_select { setup }`, `setup_open { sitting }`, `setup_measure { sitting }`,
`setup_from_files { sitting, folders }`, `setup_stop`, `setup_keep`, `setup_discard`,
`setup_scale { band | box, pitch_um | marks, length_um }`, `setup_detail { stack }`.

The snapshot gains `setup`: the current setup's name, each part's source and headline
numbers, the open sitting, the run's stage and burst, and the last result's checks with
their sentences.

### 12.5 Fixtures

`--setup-fixture NAME --route setup --offscreen-screenshot PNG`:

| Name | State |
| --- | --- |
| `empty` | No camera known, no rig |
| `unmeasured` | A folder from a Canon EOS R5 dropped; nothing measured |
| `shipped` | The A7CR rig, shipped parts, Scale, Motion and Warm-up not measured |
| `dark-not-dark` | The Dark sitting stopped by its first check, with R2's numbers |
| `bright-noise`, `bright-levels` | The Bright sitting's plates from R3's points |
| `scale` | The Target plate with a band |
| `motion-return` | R5's points |
| `shooting` | A sitting in its Shoot stage, burst c of 9 |
| `refused` | An X-Trans folder dropped |
| `new-setup` | The three questions, for a Canon body on a rail with a flash |
| `waiting` | Dark on a host with an unswitched light: "Cap the lens, then Continue" |
| `rig-chain` | Measure the rig in its third sitting of four |
| `by-hand-return` | Motion from files: the list, and 76 frames found against it |

The plates' fixture points are the measured ones in
`experiments/setup-page-2026-11-27/plates/`, so a fixture screenshot shows real numbers.

---

## 13. Speed and smoothness

- Drawing a plate with 600 points: at most 0.3 ms of CPU a frame, measured with a
  `#[ignore]` benchmark beside `benchmark_depth_lens_frame_time` (which reads 0.094 ms
  still and 0.31 ms moving). Plates are tessellated once per result and per size.
- Opening Setup with ten setups and forty parts on disk: the first frame within one frame
  of the Library's. Parts are read on a worker; the column draws the names first.
- A sitting's Read stage runs as an engine job at below-normal priority like every other
  tool; the page stays live and Stop works within a second in every stage.
- Setup adds nothing to a render's path but the part lookup, once per run.
- Station pointer sweeps (`capture_station_pointer_sweeps`' kind) for Setup, before and
  after each stage of section 18.

---

## 14. What was not measured

Said here so that nobody reads the rest as more certain than it is.

| Not measured | What stands in | Who settles it |
| --- | --- | --- |
| A stack from a Canon, Nikon or any other maker's camera, rendered end to end. None is on disk; the samples are single frames | The decoder's report on 24 files (R1) and the list of gates in section 9 | Stage E2 needs one real stack from another maker before it is called done. The owner has no such camera: a borrowed folder, or a public one, is an input the implementer asks for |
| The Bright sitting with a white card: the dust map, the fixed pattern, the light's balance | The dust detector's own record on the A7C II's flats (`defect_map.rs`), and 2026-11-16's fixed-pattern figures. The subject on the stage tonight is a wing on a black ground, dark over most of the frame, and nobody was at the rig to place a card | Stage P3's rig gate, with the owner placing a card |
| Any sitting done by hand by a person reading the shot list | The same analysis run on the rig's frames | Stage P2: the owner shoots Dark and Bright by hand on the A7C II and the page must reach the shipped numbers |
| The by-hand forms of Return, Settle, Still and Warm-up, on RAW files | The same functions on live frames (Return) and on RAW frames the host shot (Settle, Warm-up) | Stages P6 and P7: the host shoots each by-hand list and the files must give the host's own answer |
| A flash | Nothing. The analysis treats flash-to-flash differences as it treats a lamp's drift | The first person with a flash, at stage P2 |
| The stage's level | Its guard only (R10) | Stage P10, with a flat target shot through focus |
| Long exposures in the engine's noise model. At 8 s the A7CR reads 21 % more noise than the model's figure (M4) | The note of 6.1 | A later decision, if anyone stacks at such exposures |
| The scale against a second standard | Two regions of one grid agreeing to 0.4 % (R6). The slide's own labels are not a standard: it is a reduction | Stage P4, with a ruler and the slide in the same frame |
| That a second mode (silent shutter, 12-bit) is told from the first by its signature alone | ARGUED from the samples: bit depth and compression differ between the modes seen (R1). The A7CR's 1/8000 s frames have the same signature as its 1/100 s frames and 17 % more read noise (M4) | The mode is the person's to name; a stack says which it was shot in through its setup. Decision 2 touches this |
| The lens's step. The return test reads positions that cluster about 2 units apart, which may be the lens's own smallest step or the instrument's interpolation between samples 4 units apart (R5) | Nothing depends on it | A fingerprint sampled every unit, in stage P6 |
| What changing the white level to the measured clip does to a finished picture | DERIVED: 6.9 % more of the range before a photosite counts as clipped | Decision 3's gate |
| Whether live view can time a settle. It gives a first frame 0.7 to 0.9 s after a move and one live pixel is 9.3 sensor pixels (R5) | The RAW ladder of 7.2 | Done in R8 |
| A rail, or any axis that is not the lens's motor | By hand: section 4's axis kinds and sittings written in the person's own step. Driven by Strehl: nothing | A rail owner at stage P6; a driver, section 15 |

---

## 15. Tethering other makers: what a driver must provide

Deferred, each maker its own decision with a body on the bench. Listed so that the page
and the profiles do not have to change when one arrives.

**What the page needs from a driver** is section 11.3's capabilities and nothing else:
set ISO and shutter from the camera's own lists; take a single shot and hand over the
RAW; a live frame; optionally drive focus and report where it is; optionally switch a
light.

**What is Sony's today and a driver replaces** (VERIFIED by reading `strehl-capture`):

| Sony-only | Where |
| --- | --- |
| The PTP dialect: connection handshake, property codes, the events for "focus arrived" and "image arrived", the USB identity | `ptp.rs`, whole |
| The bridge's text protocol and its hello flags | `backend.rs` (`Native`) |
| Property names used as keys above the trait: `ShutterSpeed`, `IsoSensitivity`, `Focus_Magnifier_Setting`, `FocusPositionCurrentValue` and others | `worker.rs`, `session.rs`, `schedule.rs` |
| Value encodings: shutter as numerator and denominator packed in 32 bits; ISO's AUTO mask; program 1 for M; the magnifier's packed ratio and its 639 x 479 frame | `timing.rs`, `worker.rs`, `session.rs` |
| Focus as a 16-bit position where "arrived" means readback equals target | `model.rs` (`Plan`, `LensTravel`), `backend.rs` (`Camera::focus`) |
| Four-shot groups: one or four shots, the group's completion event | `backend.rs`, `worker.rs` (`validate_capture`) |
| `.ARW` in file names, the receiver's compression keyed on it, the journal's `raw_format` | `transfer.rs`, `receiver.rs`, `journal.rs` |
| Waking and standby by watching for the A7CR on USB | `worker.rs` |
| Messages that name the A7C II and A7CR | `worker.rs`, `session.rs`, `app.rs` |

**What will differ and the rig part already allows for.** A camera that moves focus only
by relative steps with no position to read back (UNVERIFIED: this is how Canon and Nikon
bodies are commonly driven over USB; check on the bench) has `reports_focus` false: its
positions are counted, the return test of 7.1 matters more, and its records carry no
focus position. A rail has `axis.kind` "rail" and, usually, real micrometres.

Licences, before any driver is written: the libraries that speak other makers' USB
dialects carry their own terms (libgphoto2 is LGPL; some of its camera drivers and the
`gphoto2` program are GPL). `AGENTS.md`'s table decides what may be opened, and a new
entry there comes before the first line of code.

---

## 16. What is deliberately not here

- **JPEG, TIFF or HEIF as input.** A rendered file has had the camera's tone curve, noise
  reduction and sharpening applied, so the one noise model everything in the engine
  weighs by has nothing to stand on. Not a format gap: a different product.
- **A profile downloaded for your camera.** Export and import are files between people.
  A shared library of parts is worth having and needs a home, a licence and a way to say
  who measured what; not this page.
- **Colour calibration from a chart.** The colour matrix stays the decoder's.
- **Applying the dust map, the fixed pattern or a vignetting correction** (section 10.5,
  decision 5).
- **Pixel shift from other makers.** Strehl's four-shot path reads its own capture
  journal.
- **Magnification's shape from the alignment's fitted scales** (6.3). Argued, attractive,
  and next to rule 8.
- **A wizard.** The six rows are the guide. Nothing walks the person through pages with
  Next and Back; any sitting can be done alone, in any order, any number of times.
- **Calibrating by itself.** Setup measures when asked. It never starts a sitting because
  time has passed.
- **Four more measurements a setup could hold.** A mechanical shutter's blur by shutter
  speed; a lens's sharpness by aperture, for people who can stop down; the direction,
  scale and return of an XY stage, which tiled capture will want when the stage exists;
  and micrometres per lens unit along the focus axis, for depth in millimetres. Each fits
  the page as another sitting or another reading of one. None is designed here.

---

## 17. Decisions for the owner

Each has a default the implementer follows until told otherwise.

| # | Question | Default |
| --- | --- | --- |
| 1 | The names: the page **Setup**; the sittings Dark, Bright, Scale, Detail, Motion, Warm-up; the parts Camera, Lens, Rig, Light. Capture's step 2 stays "Calibrate" (it measures the subject; Setup measures the instrument) | As written |
| 2 | What "support other cameras" delivers first: other makers' RAW **from files**, complete, with every sitting doable by hand, and tethering for another maker left to its own decision when a body is on the bench (sections 4, 15). The larger reading, a Canon or Nikon driver now, cannot be tested on the hardware here | Files first |
| 3 | Take the engine's white level from the measured clip (A7CR: 16,143 in place of 15,360)? It changes finished pictures near the top of the range and moves the pin counts Capture's exposure advice reads. Its gate: the dragonfly and one more stack rendered both ways, compared at the highlights at 100 %, the Light and Glints lenses' counts side by side | Off for the two shipped cameras until you have looked. A camera with no shipped part uses its measured clip from the start: it has no earlier renders to keep, and its files' declared white is the thing M2 shows cannot be trusted |
| 4 | With no lens in Setup, measure the lens's colour shift on each stack and correct it (today: no correction)? R7: within 3 to 7 ppm of the shipped profile's result on three stacks in two passes of a few seconds | Yes |
| 5 | The dust map and the sensor's fixed pattern: measured and drawn only, or applied to renders? Both corrections exist and are off by default | Measured and drawn only |
| 6 | When your own measurement of a camera exists beside the one shipped with Strehl, which does the engine use? | Yours, with "Compare with shipped" on the sheet and one click back |
| 7 | Three further readings are proposed: the lens's colour focus and the stage's level, both from a stack (6.4), and live view against RAW (7.1). Build them, and when? | Yes, last (P10) |

---

## 18. Stages, in order, with their gates

E stages are the engine and can land before any screen. Every stage ends with the checks
`AGENTS.md` names for the crates it touched, and every desktop stage with a station sweep
before and after (section 13).

### E1. Parts as files

Section 5.2, 10.1, 10.2 for the two shipped cameras and lenses; `strehl setup show`.

- Gate: section 10.2's byte-identity. `strehl setup show --camera ILCE-7CR --iso 100`
  prints 0.4040 DN/e-, 1.334 DN, "shipped".
- Failing input: a camera part with a gain of zero must be refused when read, by name.

### E2. Other makers' files

Section 9.

- Gate: 9.3 on the 24 samples. One real stack from another maker renders, with the
  checks row saying "Camera noise guessed" (section 14's first row: the stack is an
  input to ask for).
- Byte-identity for the two shipped cameras.

### E3. Dark and Bright in the engine

`strehl setup sort`, `dark`, `bright`, `keep`; the noise model read from a measured part.

- Gate, on the frames kept from 2026-11-27 (`D:/StrehlCaptures/setup-page-2026-11-27/`,
  listed in R11): Dark gives the capped column of 6.1's table within 0.01 DN; its Dark
  check fails on the lit bursts (1/100 s against 2.5 s) with the sentence of 6.1, passes
  on the uncapped pair with the note about a little light, and passes capped with the
  light on; Bright gives green 0.4040 at ISO 100 and 1.632 at ISO 400 within 0.3 %, clip
  16383, linear to the clip; the gain mode starts at ISO 400.
- Gate, independent: the same commands on the 14 November folders that still exist give
  that day's numbers.
- A render of an A7CR stack with the measured part differs from the shipped render only
  where the two models differ; say by how much.

### E4. Lens colour without a profile

Section 10.3, decision 4.

- Gate: its table.

### P1. The station, empty

Sections 4.1 to 4.3, 5.9, 8.1, 8.2, 8.5, 12.1, 12.2 (store, equipment, sheets, summary
plate), 12.5's `empty`, `new-setup`, `unmeasured`, `shipped`, `refused`. No sitting runs
yet; the sheets show the shipped parts.

- Gate: the five fixtures against the mockups; the first-visit sentences of 8.5; Setup
  opens within a frame of the Library; pointer sweep.
- Gate: `applies` for four setups: the owner's rig lists all six sittings; a Canon on a
  rail with a flash lists Dark, Bright, Scale, Detail and Motion and has no Warm-up; a
  camera using its own bracketing in daylight lists Dark, Bright, Scale, Detail and
  Motion without Return, and has no Light tab; a host with an unswitched light lists all
  six with Dark waiting on the person.

### P2. Dark and Bright by hand

`setup-files.rs`, `setup-run.rs`'s Read and Plate stages, the Dark and Bright plates, rule
5's keep and replace.

- Gate: the 2026-11-27 folders dropped in give E3's numbers on the plates. The owner
  shoots both sittings by hand on the A7C II from the shot list alone; the page reaches
  the shipped part's gain within 1 % and read noise within 5 %, and every sentence they
  had to read is noted.
- Fixtures `dark-not-dark`, `bright-noise`, `bright-levels`.

### P3. Dark and Bright on the rig

Section 11.2, 11.3; the meters; the Shoot stage.

- Gate, rig: with managed power on, the Dark sitting's frames are dark (the first run of
  this work was not). Both sittings end within 10 % of the time the page promised. A
  white card: the Field plate, the dust map through `detect_dust`, the fixed pattern
  against 2026-11-16's 0.30, 0.35, 0.40 %.
- Stop in each stage leaves the camera's exposure, shot mode, the light and the lens as
  they were, checked again after the camera has been powered off and on.

### P4. Scale

Section 6.3; the scale's use in Develop and on the subject page.

- Gate: a ruler and the slide in one frame agree within 1 %. The two regions of R6 agree
  within 0.5 % with the refinement the implementer chooses. The failing input: a band
  across blank glass says "No regular marks".

### P5. Detail

Section 6.4; `strehl setup detail`; the lens sheet.

- Gate: E4's table through the page. A lens part made from the coin stack makes the
  dragonfly's render differ from today's by less than the left-over of one pass.

### P6. Motion

Section 7.1 and 7.2; Capture's Rig step reading the rig part (12.3, 8.6).

- Gate, rig: the Return plate reproduces R5 within the instrument's 2 units; the settle
  ladder reproduces R8. Capture offers the measured settle and approach and changes
  nothing by itself.
- Gate, by hand: the host shoots the by-hand lists as RAW (the stack, the arrivals, the
  stack; the run of ten at three settles; ten untouched frames). Read as dropped files
  they give the host's own answers: hysteresis within 2 units, the settle table within
  its detection limit.

### P7. Warm-up

Section 7.3; Capture's light wait.

- Gate, rig: two runs from cold agree on the settled time within 20 s. Capture's pass
  waits the light part's time and says where it came from.
- Gate, by hand: a cold series shot by the host, read as dropped files with the delay
  typed, gives the host's own settled time within one frame. A setup whose light is a
  flash is not offered the sitting.

### P8. Several setups, and the rest of the app

Section 5.8; export and import; section 8.6's lines; section 12.3's last rows.

- Gate: a second setup with another lens leaves the first's camera part untouched; a
  part exported and imported on a clean folder renders the same bytes; each line of 8.6
  appears in the state that calls for it and not otherwise.

### P9. Measure the rig

Section 4.4; `setup-chain.rs`.

- Gate, rig: one press with a detailed subject on the stage and the light cold. It ends
  within 23 minutes; each sitting's numbers pass that sitting's own gate; the rig is as
  it was found.
- Failing inputs: with the light left on by hand, Dark stops at its check and the other
  three still run. With the light off for 4 minutes, the page offers the wait or the
  skip before it starts. Stop in each of the four leaves exposure, four-shot, light and
  lens as they were.

### P10. Further readings

Decision 7: colour focus and level (6.4), live view against RAW (7.1).

- Gate: colour focus on the scarab stack gives red 3 to 3.5 frames and blue 2 to 2.5
  after green (2026-11-16's figures by another route).
- Gate: level on a flat target the owner shoots through focus; and the slide stack of
  2026-11-25 fails with R10's sentence.
- Gate, rig: live view against RAW within 5 units of what Capture's pass measures on the
  same subject the same hour.

---

## 19. Ledger and evidence

Allocated in [the milestone ledger](../agents/milestone-ledger.md) on 2026-11-27, section
"Setup page (2026-11-27)":

| Identifier | Scope |
| --- | --- |
| setup-page-2026-11-27 | This design, its measurements and mockups. Done, design only |
| setup-e1-parts, setup-e2-files, setup-e3-sensor, setup-e4-lens-colour | Section 18, E1 to E4 |
| setup-p1-station … setup-p10-further | Section 18, P1 to P10 |

Evidence: [results](../../experiments/setup-page-2026-11-27/results.md) with its scripts
under `rig/` and `analysis/`, the two prototype programs `sensor.rs` and `probe-any.rs`
(examples of `strehl-raw`), and the plates' points under `plates/`. The frames behind
E3's gate are kept outside the repository (R11).
