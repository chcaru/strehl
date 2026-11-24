# Subject, highlights and detail: a plan

**Status:** Proposal (2026-11-23). Stages Q (Q1 to Q7) and S1 to S3 are built on
`studio2/subject-impl`, not yet rig-tested
([implementation log](../../experiments/subject-highlights-detail-2026-11-23/impl/README.md)).
The owner's decisions of 2026-11-23 are recorded in section 9; tiled capture (section 12)
is deferred.
**Date:** 2026-11-23.
**Owner's questions:** make the Capture subject a polygon, select it automatically with
manual correction, and let it drive the calibrations. The exposure advice over-exposes
shiny areas and glints: would per-plane multi-exposure help, planned at calibration and
corrected during capture? Could Develop drive corrective re-shoots while the subject is
still on the rig? Why does the new A7CR glitter-weevil stack not resolve the scales much
better than the A7C II one, and is there anything left to gain in software?
**Scope:** the desktop's Capture, Stack and Develop stations, the Pi controller, the engine
where frames are identified, gathered, restored and written. Stage labels (Q, S, X, R, D)
are plan-local; allocate milestone rows before dispatch.
**Audience:** the owner, then an implementing agent.
**Evidence:** [`experiments/subject-highlights-detail-2026-11-23/`](../../experiments/subject-highlights-detail-2026-11-23/results.md)
(brief, results, scripts, the rig series' index).

Labels: MEASURED, VERIFIED (read in the code or a log, or checked against an independent
result), DERIVED, ARGUED, UNVERIFIED. Every number below is from the results note unless
marked.

---

## 1. Answers

**The exposure advice cannot see glints, by construction.** It reads one test shot at
one focus position, pools red, green and blue, and puts the brightest 0.1 % of the whole
frame at 0.9 of full scale (VERIFIED in `capture-guide.rs` and `capture-test-shot.rs`).
Measured on the two stacks:

- A glint is bright only near its own focus. Ten planes away the weevil's glints read a
  quarter of their peak.
- The pinned samples are 0.0004 % of the weevil frame; the rule looks at 0.1 %.
- Pooling hides green: on scarab plane 162 the pooled figure is 0.71 while green is
  pinned.
- Followed on the weevil, the advice gives 1.6 s. At the nearby 1.3 s, 12,000 to 20,600
  sites of the subject pin in each in-focus plane, against 140 to 280 at the owner's 1/4 s.

**A highlight pass is worth building, and it is small.** The weevil's glints peak at 1.3 to
5.2 times the 1/4 s full scale. One short group five stops under a correct body exposure
holds all of them. Fusing a long and a short group of one plane per photosite agrees at
the hand-over to 0.1 % with noise-sized spread. A short four-shot group costs 3.6 s; the
shutter change costs 0.2 to 0.5 s.

**The owner is paying for the glints twice today.** Under-exposing by 2.4 stops to protect
them leaves one plane with a signal-to-noise power of 5 in the finest band, and some
glints still pin. With a highlight pass the body gets five times the light.

**The scales: mostly the lens, partly the software.**

- At this framing one pronotum scale is about 11 px wide on the A7CR and 8 px on the
  A7C II. Both renders hold the weevil at the same size on the sensor.
- The lens's point spread is at most 1.9 px wide at half height here (the narrowest
  glints), against 1.5 px for a perfect lens. It is near its limit, and nothing shows
  motion blur.
- The stack keeps what its sharpest plane has (signal ratio 1.1 to 1.6 by band). The merge
  and the focus step are not where detail goes.
- Three software faults do cost detail:
  - Restoration was silently not applied to the weevil (its cutoff fit failed).
  - Where restoration does run, its fixed target lowers the two finest bands on this lens
    setting (amplitude 0.83 and 0.66 of unrestored).
  - The capture is 2.4 stops short of light.
- A target of 0.5 or 0.4 px raises the fine bands by 1.3 to 1.8 times in amplitude at the
  same signal-to-noise. That is visible at 1:1, and it is not a different picture: an
  11 px scale stays an 11 px scale. Seeing scales as shapes needs more magnification
  (section 7, D5).

**The subject can be found automatically from frames the rig already takes.** The largest
focus energy over a few planes, set against the frame's own quiet background, traces the
weevil to within 8 px (median) from as few as seven planes. The scarab needs one more
step for its dark flank. Live view alone gives a looser outline without a RAW.

**Subject-aware bounds would have shortened both captures.** No part of the weevil is
sharpest in the first 30 or the last 35 of its 199 planes: a third of the capture. For
the scarab it is the first 9 and the last 20 of 211 (14 %), or 24 % if the outermost
0.2 % of the subject is left to the margin.

**A corrective re-shoot from Develop is feasible in a first form.** The pieces exist
separately (region to planes, retakes into a finished capture, re-stack). The host refuses
any exposure change on a retake, and a retake reaches the photograph only through a
re-stack. Section 6 joins them.

---

## 2. Rules for the implementer

- Engineering invariants in `AGENTS.md` hold: u16 CFA storage, f32 arithmetic, one injected
  noise model, gather at the consumer, capture folders read-only.
- A capture without a subject or highlight groups must render byte-identically to today.
  Gate every engine stage on that, on the weevil and the scarab folders above.
- New host abilities are announced in `capabilities` and omitted from requests to older
  hosts, as `test_shot` and `queue_retakes` are.
- Do not put a clip mask into the focus election (M54, SYNTHESIS fact 684). Highlight
  fusion replaces samples before the merge sees them; it does not change the election.
- An exposure ratio is measured per pair of groups, never taken from the marked shutter
  times. The light moved 5 % between groups and members of one group differed by up to
  7.5 %.
- The subject is normalised to the sensor's active area. Live view shows that same area
  (MEASURED: 100.0 % by 99.8 %), so normalised live coordinates are sensor coordinates.
- Desktop work follows the owner's taste (square, ruled, instrument character) and the
  smoothness budgets of Studio 2. Mask and census work runs off the UI thread.
- Rig tests run with "manage power" on, the owner's setting.

---

## 3. Quick fixes (Q)

Small, independent, and each one removes a fault measured in this round.

| # | Fault | Fix | Gate |
| --- | --- | --- | --- |
| Q1 | Restoration silently skipped on the weevil; the only trace is a line in the render log | When the cutoff cannot be measured, use the nearest stored fit for the same camera, lens, converter and aperture (keyed by focus position; three fits exist: 0.740 at 31,006, 0.768 at 15,718, 0.776 at 30,564, so fits scatter by about 5 % at nearly one position). Say which was used in the log and in the Stack station's checks. Store every successful fit with the render. | The weevil renders restored without an environment variable; the three other stacks' bytes do not change |
| Q2 | The fixed 0.70 px target lowers the finest bands when the lens is better than the target | Never ask for less than the system delivers: target = the larger of the system response and the Gaussian. Then D2 chooses the strength. | On the scarab, harlequin and lanternfly logs, "restored" is not below "system" at 0.3 and 0.4 cycles/px |
| Q3 | With "manage power" on, every run waits the light warm-up even when the light has been on for minutes (70 s a test shot, 10 s without) | Skip the wait when the light has been on at least the warm-up time | A second test shot within a minute takes about 10 s with manage power on |
| Q4 | A test shot meters pooled colours | Report levels per colour and advise on the brightest colour. S and X replace the rule; this is the stop-gap. | Scarab plane 162 reads "green pinned", not 0.71 |
| Q5 | The four-shot plane check gets stricter as the exposure gets brighter. At closest focus the same offset between the four shots failed at about 0.26 px at 1 s and at about 0.59 px at 1/4 s; a 1 s capture took 95 groups and 51 manual retakes for 24 planes | Judge the offset in pixels against the lens's blur width, independent of exposure, and line the four shots up to their measured offsets instead of falling back to one shot. Offsets of 0.2 to 0.5 px are normal here (median 0.28 px over 149 groups). Keep retakes for whole-pixel slips and for motion inside one part of the frame | The 1/4 s and 1 s captures of the close tile give the same verdict for the same offset; the stopped 1 s capture renders with no plane reduced to one shot for an offset under the tolerance; a planted one-pixel slip still fails |
| Q6 | A capture stopped by hand is not offered for stacking, although its folder passes the desktop's own stopped-capture check (380 RAWs, 24 planes) | Find why the Capture station does not offer it. A stopped capture with at least two complete planes is offered for stacking as it stands | Stop a five-plane capture after three planes: it is offered, stacks, and reaches the library |
| Q7 | Nothing warns when the picture is not still. At closest focus it sways 0.5 px along one axis, and the finished 1/4 s tile keeps a third of the fine detail along that axis | A stillness check before Start: about 20 s of magnified live view registered frame to frame. Report the sway in pixels of the planned capture, its axis, and the longest exposure that keeps the blur under a quarter of a pixel | On the rig as it stands the check reports about 0.5 px along the picture's vertical axis, as the RAW burst did; a still rig reports under 0.1 px |

Q1's cause is open. The fit ran to its ceiling, which is what a spectrum with no roll-off
does. Two candidates: the reference frames' top band is mostly noise at this exposure
(signal-to-noise power 5), or glints add broadband energy. Test both before choosing the
permanent fix: fit with the measured noise spectrum subtracted, and fit with tiles that
hold near-pinned samples left out.

Q5 to Q7 come from the close-tile test
([results](../../experiments/subject-highlights-detail-2026-11-23/results-close-tile.md)).
Q5 must land before X2 advises longer exposures: the check as it stands measures how
statistically clear a mismatch is, which grows with light, so it punishes exactly the
brighter captures X asks for.

---

## 4. The subject (S)

### S1. One object, kept with the capture

Today the subject is a rectangle in host memory, cleared on every reconnect, used only by
the bounds survey and the live-view aids, and saved nowhere (VERIFIED).

Replace it with a `Subject`:

- **Outline:** rings of points (outer rings and holes, even-odd), normalised to the active
  area, at most 256 points a ring. Use `strehl_edit::RegionShape::Polygon`'s limits so the
  same outline can become a Develop region.
- **Reference plane:** the focus position the outline was drawn at, and the magnification
  rate per focus unit, so it can be mapped to any plane. The weevil's rate reads about
  -13 ppm a unit; take the rate from the survey's own registration or the alignment.
- **Raster:** derived, one cell per 8 sensor px, with the buffer as a soft edge. Every
  calibration reads the raster.
- **Provenance:** manual, or automatic with its sensitivity, growth and buffer, plus the
  manual strokes laid over it.

Where it lives:

- Host: `Controls.subject`, `Command::Subject`, state `"subject"`. `roi` stays as the
  outline's bounding box for the camera magnifier and older clients. It survives a
  reconnect within one host session.
- Capture: written into `manifest.json` (`subject`), so the engine and the library have it.
- Desktop: remembered with the catalog's subject, so the next capture of the same subject
  starts from it.

### S2. Automatic selection

The method measured in the results note, in product terms:

1. **Frames.** K planes spread over the marked range. Seven are enough; more cost nothing
   when they exist. Two sources:
   - the bounds survey's live-view frames (no RAW): a loose first outline in seconds;
   - the RAW survey of section 5: the precise one.
2. **Evidence per frame.** Squared 4-neighbour Laplacian of one green plane (luma for live
   view), averaged over 8 px cells, divided by what the injected noise model gives for
   that cell's level, then a 3 x 3 cell mean. Use the profile's noise model here; the
   prototype's fitted floor was only a stand-in.
3. **Registration.** One magnification rate about the frame centre.
4. **Focus evidence.** The largest value over the planes of a three-plane running mean.
5. **Threshold against the frame's own quiet population.** The largest of N noisy values
   sits well above 1, by an amount that depends on N and the sensor's dark statistics. Take
   the low mode of log evidence and its lower-side spread; the threshold is the mode plus
   `2 x sensitivity` spreads (default sensitivity 3). If the mode itself is above 6 times
   the noise floor there is no quiet background: use an absolute threshold and say so.
6. **Growth.** Weaker evidence (three spreads, or a level that differs from the backdrop's)
   counts where it touches the sure subject. This is what takes in the scarab's dark flank.
   In live view, use focus evidence only for growth: the defocused glow around the subject
   differs from the backdrop and inflates the outline.
7. **Clean-up.** Close by 3 cells; fill holes under 0.05 % of the frame, leave larger ones
   out (the backdrop between legs); drop parts under 0.2 %; grow by the buffer (default
   16 px).
8. **Outline.** Trace each part and hole, simplify to at most 256 points.

It also yields, at no extra cost:

- **The subject's depth range:** the first and last plane at which any subject cell is
  sharpest. This is S4's bounds.
- **A coarse depth map** (cell to sharpest plane) for the highlight plan of section 5.

Measured behaviour and limits:

| Case | Result |
| --- | --- |
| Weevil, 199 / 25 / 13 / 7 planes | One part, 35.6 % of the frame; intersection-over-union 0.98 with fewer planes; outline within 8 px median, 16 to 22 px at the 95th percentile |
| Weevil, sensitivity doubled / quadrupled | 0.97 / 0.94 |
| Scarab without / with growth | Dark flank missing / one silhouette and the detached leg |
| Live view, 30 or 8 frames | Found, loose: 45 % of the frame against 35 % |
| Textured backdrop in focus inside the range | Not tested. Expect it to join the subject; the depth-range limit and the subtract brush are the remedies |
| Subject filling the frame | Not tested; the absolute threshold is the fallback |

### S3. Editing

In the live-view panel, replacing the box's handles:

- **Auto:** runs S2 on whatever frames exist; **Sensitivity**, **Grow** and **Buffer**
  sliders re-threshold stored evidence without new frames.
- **Polygon:** click to place points, drag a point, click an edge to add one, Delete to
  remove. Reuse Develop's region tools (`edit-regions.rs`) rather than writing new ones.
- **Add / Subtract brush** on the raster, kept as strokes so a re-run of Auto keeps them.
- **Depth limit:** two marks on the depth rail; evidence outside them is ignored.
- **Box:** still there, as the simplest polygon.

The outline is drawn on live view, on the plane view and on the test shot.

### S4. What the subject drives

| Calibration or check | Reads today | With the subject |
| --- | --- | --- |
| Exposure metering | Whole frame, pooled colours, one plane | Subject cells, per colour, over the survey's planes (section 5) |
| Bounds | 6 x 4 tiles in the box, live view | First and last plane with subject evidence, plus half a sharp width each side. Offered as start and end with the planes and minutes saved |
| Step calibration (`focus-step`) | 64 px tiles over the whole frame that show a focus peak | The same tiles inside the subject: `--subject <manifest or json>`; report the median and the tenth percentile |
| Plane checker (`follow`, `pixel-shift`) | Witness tiles over the whole frame; registration on the central half | Tiles weighted by the subject; registration on the subject's bounding region. A failure confined to the backdrop does not ask for a retake |
| Sharp share, risk banner | Share of all cells | Share of subject cells |
| Live histogram, clipping readout, focus trace | Whole preview / the box | The subject |
| Tone placement at the write | 99.9th percentile of the frame to 0.90 | The subject's diffuse level, with a shoulder above it (X6). On the scarab today the glints set white and the body renders dark |
| Restoration's tiles and noise measurement | In-focus tiles anywhere | In-focus tiles of the subject |
| Stack and Develop | Nothing | A "Subject" region, a crop suggestion, and the backdrop tool's key from the mask instead of a luminance threshold |

### S5. Gates

- The weevil and scarab outlines of the results note are reproduced by the product's own
  code from 13 survey planes (intersection-over-union at least 0.97 against the
  prototype's masks).
- A plane set with the subject out of focus throughout gives an empty mask and says so.
- A capture without a subject renders and checks exactly as today.
- Outline editing holds the frame-time budget with live view running.

---

## 5. Exposure and highlights (X)

### X1. One survey that feeds every calibration

Today "Calibrate step" takes 25 single RAWs 8 units apart around the middle of the range,
and the exposure advice takes one test shot. Neither sees the subject's depth or its
highlights.

One **Calibrate** pass instead:

1. **Live sweep** (the existing bounds survey, no RAW): loose subject and depth range.
2. **RAW survey**, single shots:
   - about 12 positions spread over the range, each at two shutters: the current one and
     one four stops shorter;
   - the existing dense cluster for the sharp width.
3. From these: the subject (S2), its depth range, the step, the body's level per colour,
   and a **highlight census**.

The census is the distribution of radiance above the body, in the subject, per colour,
from the short frames. A sparse survey meets a glint up to four planes from its focus,
where it reads about half its peak (MEASURED on the weevil; the scarab's broad highlights
fall more slowly). So the census is a lower bound by about one stop: the plan carries that
margin, and X5 catches what it misses during the capture.

The host must take a list of positions with a shutter each (X3 provides it).

### X2. Advice that shows the trade

Replace "longest exposure whose brightest 0.1 % stays under 0.9" with three choices, each
shown with its body level, noise against now, highlights lost, and capture time:

| Choice | Rule | Weevil, from this round's numbers |
| --- | --- | --- |
| **Highlight pass** (suggested when the census exceeds the body by more than a stop) | Body: the subject's diffuse top (99.9th percentile of the brightest colour inside the subject, highlights set aside) at 0.8. Short group: the census's top, with its margin, at 0.8 | 1 to 1.3 s plus a short group 5 stops under; 4 to 5 times today's light; no pinned glint; 12 to 14 s a plane at 1.3 s |
| **Protect highlights** (one exposure) | The longest shutter at which the census, with its margin, stays unpinned | About 1/25 s; a sixth of today's light |
| **Accept specks** (one exposure) | The body rule alone; states how many sites will pin | 1.3 s; 12,000 to 20,600 pinned sites a plane |

The owner's current practice (1/4 s) sits between the last two: 140 to 280 pinned sites a
plane at a fifth of the light.

### X3. Exposure tiers on the host

The host refuses exposure changes during a run and checks before every group that the
shutter still equals the run's first (VERIFIED, `worker.rs`). Change that to a commanded
exposure per group.

- **Plan:** `highlight: Option<{ shutter, every, first_plane, last_plane, shots }>`.
  `every` 1 takes a short group at every plane in the range, 2 at every second.
- **Sequence at a plane:** base group; set shutter; highlight group; set shutter back; move.
  The lens does not move between the two groups, so they share focus and lie within a
  fraction of a pixel (0.15 px inside a group; 0.3 px between groups 40 s apart).
- **Check before a group:** the camera's exposure equals the tier's commanded one.
- **Journal:** `capture_intent` and `capture_buffered` carry `tier` ("base" or
  "highlight") and the commanded `exposure`; each file entry carries `tier`.
- **Positions runs:** `capture_positions` accepts a shutter per position (the survey).
- **Follow-up passes:** `queue_pass { planes, tier, shutter }` appends groups of a tier to
  a finished capture (section 6 uses it). The exposure check compares against the tier.
- **Timing model:** a highlight group adds its four exposures, 3.6 s of overhead and two
  shutter changes.
- **Capability:** `capabilities.exposure_tiers`.

Cost (MEASURED parts, DERIVED sums, weevil's 199 planes at 2 s settle):

| Plan | Seconds a plane | Minutes |
| --- | --- | --- |
| Today, 1/4 s | 6.3 | 21 |
| 1.3 s body | 10.2 | 34 |
| 1.3 s body, highlight group every plane | 14.2 | 47 |
| 1.3 s body, highlight group every second plane | 12.2 | 40 |
| The last one over the subject's own depth (about 135 planes) | 12.2 | 27 |

`every` is a plan setting in the Capture station, beside the retake count, default 2
(owner's decision). A glint stays near its peak for several planes, and a plane 7 units
from best focus keeps 0.83 to 0.87 of the fine bands' power. The guidance row shows what
each value costs in time.

Highlight groups are four shots (owner's decision). A single-shot highlight frame (1.7 s
instead of 3.8 s) is possible, since switching the shot count takes 0.23 s, but its colour
would be interpolated at exactly the small, coloured features it exists for. One pair was
taken for whoever wants to compare (results note, Q10).

### X4. Fusion at the gather

The default stack path has no clip handling and no per-frame exposure; the session
pipeline has both, for whole passes (VERIFIED). Reuse its pieces; do not route four-shot
captures through sessions.

- **Identity.** `all_groups` reads `tier`. `plane_groups` keeps the last complete group
  per plane and tier. A base frame gets its plane's highlight group as a companion, or the
  nearest plane's when `every` is above 1.
- **Ratio.** Start from the journal's shutter ratio; correct it from sites well exposed
  in both groups (the session code's bounded fit, `session-photometry.rs`). If the
  correction is refused, render the base alone and say so.
- **Where the base sample is replaced.** Any colour of the site within the resampling
  footprint at or near the raw pin (the session sampler's `footprint_clipped` carries the
  pin through the stencil), with a two-pixel guard. A smooth ramp between 0.75 and 0.90 of
  the pin on the site's brightest colour, so all three colours switch together.
- **Value.** The companion's sample at the same output site through its own warp, times
  the ratio. For a same-visit companion, measure its shift against the base as member
  offsets are measured; for a later pass, align it as a frame.
- **Storage.** The base plane stays u16 and exact. Replaced sites are sparse (0.06 to
  0.1 % of the weevil's subject at 1.3 s; 0.25 % of the scarab's at its shutter): keep them
  as a per-frame list of site, f32 value and variance scale, applied when the plane is
  lifted to f32. This keeps the u16 invariant and bounded memory.
- **Noise.** The same injected model, evaluated on the companion's raw sample and scaled by
  the ratio squared. One model, no private estimate.
- **Merge.** Unchanged. It receives planes whose pinned sites hold real values; its input
  hull follows.
- **GPU fold.** The patch list is applied in preparation, before luma and variance.
- **Output.** The writer's ceiling comes from the fused data. A sample is neutralised only
  where the companion is pinned too. The linear master keeps the values (it is f32
  already).

The alternative is to treat short groups as frames of their own with a per-frame gain and
a validity mask inside the election, as session fusion does. It is more general and it
changes the election, which M54 measured as harmful when no replacement data existed. Keep
it as the fallback if patch lists prove awkward on the GPU.

### X5. During the capture

The follower already decodes every group. Add a highlight verdict per plane: pinned sites
in the subject, in cells that plane has sharp.

- **Highlight pass off:** the flight view keeps a running count ("Highlights: 4,745
  spots pinned so far") and offers one action, **Add a highlight pass**, which queues
  `queue_pass` over the affected planes once the main run ends. This is the reactive
  form: it needs nothing planned.
- **Highlight pass on:**
  - a highlight group that still pins queues a shorter one for that plane (two stops);
  - when no base group has pinned in the subject for several planes, highlight groups
    pause until one does. A glint announces itself: five planes before its focus it
    already reads 0.45 of its peak (weevil), so a base sample above about 0.4 of full
    scale in the subject is the cue to resume.
- **Retake checks** on a highlight group use its own exposure for the witness.

### X6. Develop and export

- **Master:** carries the fused highlights above 1.0.
- **Tone at the write:** white from the subject's diffuse level, a shoulder above it, so
  glints no longer set the picture's white point.
- **"Tame glints"** (`glint_compression`) now has texture to recover. Its own description
  says it cannot recover clipped texture; with fused data it can.
- **Clipping overlay:** add a RAW-referred view (sites pinned in every available group),
  beside today's output-referred one.
- **HDR AVIF:** unchanged code, real highlights. Its 1,000 nit peak over 203 nit white
  is 2.3 stops; the weevil's glints reach 4.7, so the shoulder still matters.

### X7. Gates

- A capture with no highlight groups: bytes identical.
- Rig: a 20-plane four-shot capture of the weevil with a highlight group at every plane
  and at every second plane. Pinned sites in the subject of the fused planes: zero. The
  hand-over check of the results note (0.999, noise-sized spread) holds on every plane.
- The fused stack's unpinned areas equal the base-only stack's within rounding.
- A planted ratio error of 5 % is corrected; one of 25 % is refused and reported.
- The owner looks at native crops of glints: base alone, fused, fused with "Tame glints".

---

## 6. The re-shoot loop (R)

Goal: from Stack or Develop, with the subject still on the rig, mark a fault, let the
rig take what would fix it, and get the corrected photograph.

### R1. Is the subject still there?

- A stack knows its capture folder; the host reports its latest run's folder name. They
  match, the camera settings match the manifest, and the host accepts follow-up passes.
- A **probe group** at one stored plane, compared with that plane's stored group: shift
  and focus difference. Measured here: revisits land within 0.3 to 0.8 px and about 2
  focus units; 1.2, 2.7 px across the first minutes after the light came on. Show the
  numbers; refuse nothing on them, since the engine registers each new frame.
- A "Rig" line in Stack and Develop says which of these hold. The tool is offered only
  when they do.

### R2. From a region to a recipe

The owner marks a region (any region shape, or a click on a blown glint). The desktop
already ranks the planes behind a region (`probe_region`, admitted share on a lattice of
about 55 px). Add per-plane RAW evidence to `evidence.strehl` (record kinds 10 and up): a
pinned-site map and a signal-to-noise map on the same lattice. Then propose:

| What the evidence shows | Pass proposed |
| --- | --- |
| Pinned sites in the planes behind the region | **Highlight pass** on those planes, shutter from how far the neighbours overshoot |
| Signal-to-noise under a set level in the region | **Shadow pass**: a longer exposure on those planes. Photons are what counts (M30), and one long group costs less overhead than several short ones |
| The region's focus peak falls between planes, or at the stack's first or last plane | **Infill**: planes at half the step across that range, or more planes beyond the end |
| A demoted or failed group among those planes | **Retake** |

Each proposal states planes, shutter, time, and what it expects to change. The owner
confirms or edits.

### R3. Taking it

`queue_pass` (X3) into the same capture folder. Infill planes get positions between or
beyond the plan's, and their own plane records. The flight view shows the pass like a
retake run.

### R4. Using it

- **First version:** re-stack the capture. The engine already takes a plane's last
  complete group; with X4 it fuses highlight and shadow tiers; infill planes are simply
  more frames. A 199-plane re-stack takes 15 to 46 s. The Develop recipe carries over
  (its regions are normalised).
- Region-only repair cannot be used yet: it refuses colour carry and optical restoration,
  both on by default for these stacks, and it accepts only one contiguous range of the
  original frames (VERIFIED). Lifting those refusals is a later optimisation, not a
  prerequisite.
- The catalog records that the render came from a re-shoot and which planes changed.

### R5. Gates

- With the subject on the rig: mark a glint region on a stack taken without a highlight
  pass, accept the proposed pass, and get a re-stack whose region has no pinned site.
- Same for a deliberately skipped plane (infill) and a group shaken during capture
  (retake).
- With the camera off, or another capture taken since, the tool is not offered and says
  why.

---

## 7. Detail (D)

| # | Stage | Why | Expectation |
| --- | --- | --- | --- |
| D1 | Q1 and Q2, made permanent | Restoration skipped on one stack and softening the finest bands on three | Restoration always runs on four-shot stacks, and never lowers a band |
| D2 | Restoration strength from the stack's own signal-to-noise | One fixed target cannot suit a cutoff of 0.62 and of 0.77 | See below |
| D3 | The highlight guard follows real pinning | It kept 1.8 % of the weevil frame unrestored; with X4 few sites are pinned | Restoration reaches the scales around glints |
| D4 | Exposure (X) | 2.4 stops short | Signal-to-noise power 5 times, which D2 turns into crispness |
| D5 | Tiled capture, for scale-level detail | Section 1: an 11 px scale stays 11 px | Deferred by the owner; outlined in section 12 |

**D2.** The filter stays the one shipped: a Wiener gain toward a target, in the square-root
domain, noise from the half-stacks. Change how the target is chosen:

- Candidates: Gaussian targets from 0.70 down to 0.35 px, each floored at the system
  response (Q2).
- Budget: the restored noise power in the 0.3 to 0.5 cycles/px bands may rise to B times
  the unrestored, measured on the half-stacks as now. Take the sharpest candidate inside
  the budget.
- One owner-facing control, "Detail", from natural to crisp, maps to B. Measured anchors
  on the weevil: B about 1.7 gives 0.50 px (fine amplitude 1.3 times); B about 3.3 gives
  0.40 px (1.6 to 1.8 times).
- The default is the safe anchor, B about 1.7 (0.50 px on the weevil), and the control is
  the owner's to move (owner's decision). It is a Stack recipe setting, so it is stored
  with the render and re-rendering with another strength reuses the stack's caches.
- Gate: on each of the four A7CR stacks the chosen target, its amplitude gain by band and
  its noise cost are in the log, and a flat tile's noise rise equals B within 10 %.

**D5, and what is physically there.** The lens resolves about 1.5 to 1.9 px at half
height at this framing, which is 6 to 7 um on the sensor. The A7CR samples that properly;
the A7C II did not. That is why the new stack shows hairs and glint colours the old one
lacks, and why the scales still read as soft discs: each is about six blur widths across.
No filter changes that ratio much. Magnification does, though less than in proportion:
at twice the magnification a scale is 22 px and the blur grows to between 2.0 and 2.6 px,
so eight to eleven blur widths across (DERIVED from the working aperture's growth with
magnification, taking today's framing as about life size; UNVERIFIED on this lens). The
same framing then needs a mosaic of stacks: four tiles at 1.7 times, nine at twice
(section 12). The engine has a session mosaic path; the rig has no way to move the
subject by a known amount. The owner has deferred it (section 9); it remains the route
to scale-level detail on whole insects.

Not worth building now:

- **Sixteen-shot.** At these stacks' cutoff (0.74 to 0.78 cycles/px) the lens does pass
  some contrast beyond the four-shot grid (about 0.15 at 0.5 cycles/px, falling to zero),
  unlike the coin test that set the earlier verdict. The camera offers only 1 and 4 shots
  over this connection. Revisit if that changes.
- **A finer focus step.** Half a step from best focus keeps 0.84 to 0.88 of the finest
  bands' power, and tiles this size overstate the loss.
- **Merge changes for detail.** The stack matches its sharpest plane.

---

## 8. Order

Each stage ends with its gate. Stages in one row can run in parallel.

| Step | Stages | Needs |
| --- | --- | --- |
| 1 | Q1 to Q7 | Nothing: the two close-tile captures are Q5's fixtures. Q1 and Q2 alone make the weevil visibly crisper; Q5 comes before any brighter capture |
| 2 | S1, S2 (engine and desktop), S3 | Nothing; the two stacks are the fixtures |
| 3 | S4 (bounds, metering region, step, checker, shares), X1 survey, X2 advice | Step 2; X3's per-position shutter for the two-shutter survey |
| 4 | X3 host tiers, X4 fusion, X6 output | A Pi deploy; a rig session for X7 |
| 5 | X5 during capture, D2, D3 | Step 4 |
| 6 | R1 to R4 | Steps 3 and 4 |

Steps 1 and 2 need no capture and no host change. Step 4 is where the rig and the owner's
eye are needed.

---

## 9. Decisions (owner, 2026-11-23)

| # | Question | Decision |
| --- | --- | --- |
| 1 | Bounds from the subject's depth: applied or offered? | Offered, with the planes and minutes saved |
| 2 | Highlight groups: four shots or one? | Four |
| 3 | Highlight groups at every plane or every second? | A setting; every second is the default |
| 4 | The default "Detail" strength | A setting; the safe strength (0.50 px on the weevil) is the default |
| 5 | What counts as "no highlights lost"? | No pinned site in the subject |
| 6 | Tiled capture for scale-level detail | Deferred, after the close-tile test. Section 12 keeps the outline and what was measured |

---

## 10. Risks and what was not verified

- No stack with highlight groups exists; fusion was measured on single planes. Its
  behaviour through the merge, the restoration and the tone stage is UNVERIFIED.
- The glints of one subject were measured. The scarab's broad reflections, wet subjects
  and minerals may need a second short tier.
- The subject mask was tested on two dark-backdrop subjects. Light or textured backdrops
  are untested.
- The census's one-stop margin comes from the weevil's through-focus profile.
- The drift after the light comes on (2.7 px in the first minutes) is one observation; its
  cause is argued, not measured.
- Why the weevil's cutoff fit failed is open (Q1).
- The magnification argument in D5 is derived, not shot.
- All measurements are author-run and not independently reviewed.

---

## 11. Evidence

- [Close-tile test](../../experiments/subject-highlights-detail-2026-11-23/results-close-tile.md):
  the lens at closest focus, the 1 s attempt, the plane check's dependence on exposure, the
  stillness test.
- [Results](../../experiments/subject-highlights-detail-2026-11-23/results.md) and
  [brief](../../experiments/subject-highlights-detail-2026-11-23/brief.md).
- Prototypes to port, in that folder: `subject-mask.py` and `live-mask.py` (S2),
  `hdr-fuse.py` (X4), `glint-focus.py` (X1's margin), `meter-compare.py` (X2).
- Instruments to keep: `stack-vs-plane.py`, `glint-psf.py`, `sweep.py`, `ladder.py`,
  `rig-series.py`.
- The rig series' 55 test runs are listed in `rig-index.json` and remain in
  `D:/StrehlCaptures/` as fixtures (ladder at three planes, six revisits, a fine sweep, a
  four-shot and single-shot pair).
- Prior work this builds on: M30 and SYNTHESIS fact 243 (support HDR co-bracketing, trigger
  it per stack), M54 and fact 684 (do not mask the election),
  [capture round 4](2026-11-a7cr-capture-and-storage-plan-4.md) (exposure and step
  measurements), the
  [four-shot quality proposal](2026-11-a7cr-four-shot-quality-improvements.md)
  (restoration), [Studio 2](2026-11-desktop-studio-2-implementation.md) (stations,
  evidence, region repair).

---

## 12. Tiled capture, in outline

Deferred by the owner on 2026-11-23. Not part of this plan's stages. Written down because
the owner asked what it would look like; it needs its own measurements before it is
planned.

**What it is.** The subject is shot closer, in overlapping tiles. Each tile is an ordinary
focus stack. The finished tiles are joined into one photograph.

**What it gives.** DERIVED throughout, taking today's weevil framing as about life size
and the working aperture as growing with magnification from the fitted cutoff:

| Magnification against today | Tiles for today's frame | Photograph | One scale | Real detail against today |
| --- | --- | --- | --- | --- |
| 1 (today) | 1 | 9,504 x 6,336 (60 MP) | 11 px | 1 |
| 1.7 | 4 | 16,200 x 10,800 (174 MP) | 19 px | about 1.3 |
| 2 | 9 | 19,000 x 12,700 (241 MP) | 22 px | about 1.4 |
| 2.8 (the lens's closest with the converter) | 9 to 16 | 26,600 x 17,700 (472 MP) | 31 px | about 1.6 |

Real detail grows more slowly than the pixel count because the lens's working aperture
narrows as it focuses closer. Tiles with no subject in them are skipped (the weevil covers
35 % of today's frame).

**What it costs.**

- Depth of field shrinks: about 2.1 times the planes for the same depth at 2x, 2.7 times
  at 2.8x. Each tile needs only its own part's depth.
- Each exposure needs about 1.9 times the time at 2x and 2.9 times at 2.8x for the same
  brightness.
- The weevil at 2x: roughly 900 to 2,500 planes, 120 to 300 GB as captured (about 122 MB a
  four-shot plane), a third of that compacted. An afternoon to a night on the rig.

**What it needs.**

- **A way to move between tiles.** By hand with the app guiding (a ghost of the last
  tile's edge to line up against), or a motorised stage driven by the Pi. For a shiny
  subject it matters what moves: moving the subject under fixed lights changes its glints
  from tile to tile; moving the camera, or carrying the lights with the subject, does not
  change how it is lit.
- **Capture.** A tile plan laid over the subject's outline from one overview; calibration,
  bounds and highlight plan per tile; a queue of stacks; compacting as it goes.
- **Engine.** Joining tiles on a known grid: refine the placement on the overlaps, correct
  parallax with each tile's own depth (a 10 mm sideways move seen from about 20 cm shifts a
  point 5 mm deep by a quarter of a millimetre, tens of pixels at 2x), match exposure,
  route seams through quiet areas. The experimental session "Wider mosaic" has the canvas
  and coverage machinery and has not yet produced a qualified real mosaic; a known grid is
  the easier case.
- **Stations.** Library, Develop and Export on photographs of 240 to 470 MP.

**First test, before any of this.** One close tile of the pronotum at the lens's closest
setting, shot as an ordinary stack, compared with today's crop at matched scale. It shows
what a tile is worth with no new software.

**Beyond the lens.** Ridges inside a scale (1 to 2 um) are out of this lens's reach at any
setting. A microscope objective in front of the lens would raise real detail 2.5 to 5
times, with a field of a few millimetres and a focus rail in place of the lens's focus
drive: a different rig.

**Measured since (close-tile test, 2026-11-23).** The first test has been shot.

- The lens's closest focus is 2.83 times life size on this rig. A tile is 12.6 x 8.4 mm
  and one scale is about 32 px wide.
- Real detail is about twice life size's, not the 1.6 times derived above: the working
  aperture narrows less than assumed (about f/12; object-side aperture about 0.12).
- That is close to a 5x objective's 0.14. A 5x objective would add about 1.2 times for a
  field 2.5 times smaller and a rail. Objectives pay from 10x, which is for regions.
- Stillness comes first. The picture sways 0.5 px along one axis at this magnification,
  and the finished tile keeps a third of the fine detail along it. Remove the sway before
  planning tiles; Q7 measures it.
- A 1 s exposure was not usable (Q5, and the sway). More light has to come from the
  lights, not the shutter.
