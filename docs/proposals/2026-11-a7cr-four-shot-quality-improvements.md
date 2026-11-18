# A7CR four-shot path: image-quality improvements

**Status:** Proposal, partly implemented. Two investigation rounds done 2026-11-16
(author-run, not independently reviewed; the scarab stack, and in round 2 also the
neutral calibration slide). Items 1, 8, 5, 3, 2 and 10 were implemented on 2026-11-17,
each behind its own switch, default off, uncommitted:
[implementation results](../../experiments/a7cr-fourshot-impl-2026-11-17/results.md).
Item 10's first version (one linear rate per plane, measured on every textured tile)
lowers fine signal and must stay off; the rate changes sign along the stack. Items 4 and 6 are not built (they need per-plane weights inside the core merge), 7 is
not to be built, 9 and 11 need captures.
**Date:** 2026-11-16.
**Scope:** `strehl-core` (merge, depth guide, restoration, profiles), `strehl-cli`
(gather, merge orchestration, restoration at the write). CPU fold, `--demosaic`,
`STREHL_PIXEL_SHIFT=remosaic` with colour carry.
**Evidence:** [results](../../experiments/a7cr-fourshot-quality-2026-11-16/results.md),
[round 2 results](../../experiments/a7cr-fourshot-quality-2026-11-16/results-round2.md),
[brief](../../experiments/a7cr-fourshot-quality-2026-11-16/brief.md); scripts in the same
folder. Ledger rows `a7cr-fourshot-quality-2026-11-16` and
`a7cr-fourshot-quality-r2-2026-11-16` cover the investigation only.
**Order of work (revised after round 2):** 1 (flat field, now built from the stack
itself) and 8 (colour registration) are independent and need no capture; 3 (colour)
comes after 8; 2 (fusion) pays most after 1; 10 (frame registration) and 4 (finest
band) only matter once 2 is on; 9 (per-channel transfer) needs a capture; 5
(restoration model) can go any time. Items 8 to 11 are round 2's and are specified in
sections 11 to 13; round 2 also changed items 1, 2, 3 and 6, marked where it did.

Read first: [AGENTS.md](../../AGENTS.md), [ARCHITECTURE.md](../ARCHITECTURE.md) (the
pixel-shift and colour-carry paragraphs),
[research-workflow.md](../agents/research-workflow.md),
[the full-potential results](../../experiments/a7cr-full-potential-2026-11-14/results.md)
(what the four-shot path is today and how it was scored).

No milestone identifiers are allocated for the work below. Allocate one ledger row per
item before starting it. The item numbers are local to this document.

Labels: MEASURED (a command in the results file produced it), DERIVED (arithmetic on
measured values), ARGUED (a mechanism not separately tested), UNVERIFIED.

---

## 1. What the investigation found, in order of value

Everything was measured on the white scarab four-shot run (196 groups, FE 100 mm macro
with the 2x converter wide open, N_eff about 12, ISO 100, 0.6 s) with the build of
2026-11-16. The default four-shot render today is colour carry, optical restoration and
compensated group assembly on the election merge.

| # | Improvement | What it buys | Evidence | Effort | Needs |
| --- | --- | --- | --- | --- | --- |
| 1 | Divide out the sensor's fixed response pattern before assembly, with a map built from the stack's own raw frames (round 2) | Removes a grain component that in green midtones is about as large as photon noise in the default output and does not average down; it becomes the dominant one under item 2. A self-built map removes 83-90 % of its power | MEASURED size, behaviour, and the self-built map on raw frames it had not seen; DERIVED share in the default output | Medium | Nothing (round 1 asked for a flat-field capture; no longer required) |
| 2 | Depth-guided fusion, calibrated: coarse levels from the election, each fused band at the election's amplitude | The election's sharpness at 0.74x its noise amplitude in textured areas (signal-to-noise power x1.9) and about 0.4-0.5x at 1-8 px scales in smooth bright areas (round 2), where the election averages fewest frames; the far-field dark lift gone | MEASURED on a post-merge prototype; the smooth-area figure is the shipped fusion's times the calibration gains (DERIVED) | Medium | A shadow reference before default-on |
| 8 | Round 2. Register red and blue by component: take the green-band share out of each channel before lateral colour is corrected, add it back afterwards | Red and blue registered with green at every scale: on in-focus tiles red goes from 0.28 / 0.62 / 1.03 px rms (coarse / mid / fine) to 0.25 / 0.14 / 0.07, blue from 0.34 / 0.31 / 0.43 to 0.15 / 0.11 / 0.05. Today fine red detail sits a pixel from green (2.4 px at the corners) and the 1 px smoothing hides it by discarding fine red | MEASURED in raw frames and on a post-merge prototype | Small to medium | Nothing |
| 3 | Keep measured colour: a filter from measured spectra in place of the fixed 1 px chroma smoothing | Red's and blue's own fine detail back (the smoothing replaces it with green's); on this subject the error of the red plane in 0.10-0.25 cycles/px falls from 18-23 % to 3 % of its signal power | MEASURED, and re-scored after item 8's repair | Small | Item 8 first; second subject |
| 9 | Round 2. Measured per-channel transfer in the restoration, in place of diffraction at a nominal wavelength | Red and blue restored to green's contrast (the model has blue sharpest; measured, it is softest at mid frequencies). A quarter (red) to a third or more (blue) of the coloured rim within 7 px of bright-on-dark edges | MEASURED on the neutral slide, and by a prototype on the scarab with the slide's ratios | Small to medium | A neutral-target stack under the stacks' light (section 9); item 8 |
| 4 | A true finest band in the merge | Under fusion, signal-to-noise in the top octave: today the fusion's gain falls from 2.8x at 0.15 cycles/px to 1.0x at 0.47 and below 1 beyond | MEASURED loss profile; gain DERIVED | Medium to large | Item 2 |
| 10 | Round 2. Refine frame registration after the alignment (one similarity per frame; the magnification step is 8 % short) | Under fusion, 4-8 % of fine signal amplitude back at no noise cost; nothing under the election | Residual MEASURED; gain DERIVED | Small to medium | Item 2 |
| 5 | Put the gather kernel into the restoration's model | The restoration reaches its stated target; today it falls short by 3 % at 0.2, 11 % at 0.3 and 26 % at 0.4 cycles/px on an axis. A linear gain: grain rises with detail | DERIVED (closed form), per-frame effect MEASURED | Small | None |
| 6 | Per-channel focus offsets inside the fusion's depth guide | Red and blue at their own focus: about +7 % (red) and +4 % (blue) fine amplitude on this run (red focuses 3-3.5 frames after green, blue 2-2.5) | Offsets and loss MEASURED (round 2); the correction unbuilt | Small once 2 exists | Items 2 and 10 |
| 7 | Sub-pixel reconstruction from the stack's natural phase spread | Little on this rig (the optics pass 2-7 % contrast beyond the pixel grid); the route for a sharper lens setting without sixteen-shot capture | Geometry MEASURED; gain DERIVED small | Large | Not now |
| 11 | Round 2, capture side. Balance the light so red and blue use the sensor's range | Red and blue shot noise about 0.71x and 0.65x at the same green exposure: they reach 32 % and 27 % of the range, and green is already at the top of the linear range | Exposure MEASURED; gain DERIVED, UNVERIFIED | A gel and a test stack | Owner (section 9) |

Checked and found fine, so not on the list (section 7): member mismatch leaves no
visible two-pixel pattern; the gather kernel leaves no visible grid in a full merge;
borrowing fine detail across colour channels gains nothing on this subject. Round 2
adds: a locally adaptive restoration gains 1-2 %; the rig's member stability is at the
static-target floor; no photosite is more than 5 % off; weights wider than the
fusion's add nothing in the fine band; blue is not the sharp channel at this lens
setting.

The half-stack scoring instrument has three blind spots that matter for judging the
items above, and round 2 found four more ways for the other instruments to mislead
(section 8). Read that section before trusting any "signal" or displacement figure.

Plain expectations, so nobody is oversold: at 1:1 the default four-shot render is
already clean. Items 1 and 2 together take about 40 % off the grain amplitude of
smooth bright areas in the band the eye reads as grain, 0.08-0.30 cycles/px (DERIVED:
pattern and photon noise are about equal there now; item 2 takes photon noise to 0.74
and item 1 removes about nine tenths of the pattern's power). Round 2 sharpens that
figure: 0.74 was measured on textured tiles; in smooth bright areas the fusion's noise
is 0.4-0.5 of the election's at these scales, which makes the pair worth 55-60 % there
(DERIVED the same way), and item 1 alone about a quarter. Without item 1, item 2
shows little in smooth areas, because the pattern is what remains. Items 8 and 9 are
fidelity fixes to colour at edges and in fine detail: with colour differences tripled
the rims visibly fade, at normal saturation the change is slight, and item 8 is
invisible while the 1 px smoothing is on (the smoothing hides the defect it fixes).
Item 3 is a fidelity fix that is hard to see on this pale subject and should show on
subjects with strong fine colour. Items 4 and 5 turn signal-to-noise into delivered
fine detail near the pixel limit, where N_eff 12 leaves little contrast to begin
with. None of this moves the diffraction limit.

---

## 2. Item 1: flat-field the sensor pattern

### What is wrong

Every photosite has its own response error. On this body it is 0.30 / 0.35 / 0.40 % of
level for red / green / blue photosites (high-passed at 2 plane px), nearly white, and
stable: the pattern measured in the stack's own raw frames correlates 0.95-0.97 with
the one measured from a calibration burst of a different scene the day before
(MEASURED, `prnu.py`, `fpn-raw.py`).

Four-shot assembly makes it worse than that figure suggests. A group reads every
photosite four times, once per member, at four adjacent output pixels. Each response
error therefore lands on a 2 x 2 block of the assembled image, which concentrates the
pattern at low and middle frequencies (four times the white density at low frequency,
none at Nyquist) while photon noise stays white (DERIVED). In 0.08-0.30 cycles/px, on
smooth bright tiles (green at 4 400 DN raw, 30 % of full scale):

| | Sensor pattern, share of band power R / G / B | Pattern : noise, green |
| --- | --- | --- |
| one gathered group | 0.11-0.13 / 0.25-0.29 / 0.16-0.17 | 0.33-0.41 |
| a four-group merge | 0.29 / 0.49 / 0.38 | 0.94 |

(MEASURED, `fpn-pairs.py`: the pattern is identified by sliding radially between frames
at the lens's magnification step, 124 ppm per plane; fitted 120, 220-240, 480-520 ppm
at one, two and four planes apart.) The pattern does not average down across
neighbouring groups because it moves only 0.1-0.4 px between them. The default merge
averages about four to five groups' worth of noise, so in green midtones the pattern's
power in this band is about equal to the photon noise's (DERIVED), more in highlights
since it grows with level, and about twice it once item 2 halves the photon noise.

Nothing in the pipeline corrects it. The scoring instrument cannot see it: both
half-stacks carry the same pattern, so it counts as signal.

### Round 2: the map can come from the stack itself (build this first)

A four-shot stack holds four raw frames per plane, all in sensor coordinates, with the
scene sliding under the sensor as focus moves. Round 2 built the map from them and
tested it on raw frames it had not seen (`self-flat.py`, `self-flat-shrink.py`,
`fpn-raw.py --apply`; map from the 392 raw frames of planes 1-98, scored on 16-frame
means at four focus positions between planes 120 and 193, tiles chosen before
correction):

| Map | Pattern power left, R / G / B |
| --- | --- |
| inverse-energy weights, shrunk | 17 % / 10 % / 10 % |
| hard smoothness gate, shrunk (two folds) | 30-41 % / 40-48 % / 17-22 % |
| placebo: the map rolled (5, 3) photosites | 171 % / 155 % / 186 % |
| stored map from the 32-frame calibration burst of another day | worse than no correction |

An independent witness (the corrected frames' covariance with the other day's burst)
reads 9 % left in green.

1. One pass over the stack's raw frames before the fold, per CFA plane of every
   member: `r = M / gauss(M, 2 plane px) - 1`; weight
   `w = 1 / max(gauss(r^2, 4 plane px), the noise model's energy)`, zero below 150 DN
   and within 12 plane px of a sample above 13 500 DN. Accumulate `sum(w r)` and
   `sum(w)` per photosite.
2. Map `= sum(w r) / (sum(w) + 1 / kappa^2)`, kappa the pattern's expected size
   (0.30 / 0.35 / 0.40 % for R / G / B on this body; profile data). A photosite that
   was rarely smooth gets little correction, not a noisy one.
3. Keep a frame's own neighbourhood out of the map applied to it: accumulate in
   segments of 30-50 planes and give each frame the sum of the segments that are not
   its own or adjacent (the test above used the far half). Otherwise a photosite's
   map carries a per cent or two of the detail that was in focus on it (ARGUED from
   the weights; not measured). Six segments are 2.9 GB of f32; halve it with f16.
4. Apply as in step 3 of the next subsection. Where a good stored map exists it
   enters step 2 as the prior mean in place of zero.

Do not gate samples with a hard smoothness threshold. The pattern's own energy is a
tenth to a quarter of the noise energy, so a threshold near 1 rejects bright smooth
areas, where the map matters most; that form rejected 55 % of samples, left a fifth
of photosites with less than half weight, and read 10 % small.

Bars: those of "How to know it worked" below, with the map from one part of the stack
scored on another, plus `fpn-raw.py --apply MAP --select-raw` (pattern power left
under 20 % in every channel; the rolled map must raise it above 100 %). A stack too
short to carry the scene across the sensor falls back to a stored map or to no
correction, and says which; where that limit lies is UNVERIFIED (this stack has 196
planes and 97 % of photosites reached full weight from half of them).

### What to build

1. **A response map per camera body**, in sensor coordinates over the whole decoded
   buffer, as a sidecar data file (it is 61 million values and belongs to one physical
   sensor, so it is neither compiled in nor keyed by model alone; key it by model and
   serial number, and record the ISO it was measured at). One signed byte per photosite
   in steps of 1/4096 covers +-3 %.
2. **A builder command** that turns a flat-field capture (section 9) into the map:
   per CFA plane, each frame scaled to the series' mean level (the lamp drifts
   0.3-1.2 % frame to frame), the mean over frames divided by its own Gaussian at 4
   plane px, minus one. Keep only that high-pass: the stack-against-burst covariance
   stops growing by 2-4 plane px (0.295, 0.329, 0.338, 0.328 % at 1, 2, 4, 8), and
   anything larger in a flat is the target's own shading. Store the odd-frame and
   even-frame maps' covariance with the file as the map's own signal-to-noise.
3. **Apply at the read**, in f32, before anything else touches the sample: in the
   four-shot gather's `measured_rows` (`align_cmd.rs`, the `at(j)` closure: each
   member's sample divided by one plus its own photosite's map value) and in the
   single-shot mosaic build beside it. Storage stays u16; nothing is written back.
4. A switch, default off, banner line stating the map's identity, date, ISO and
   signal-to-noise; refuse a map whose body does not match, and say so when the stack's
   ISO is in the other conversion-gain range (400 and above on this body) than the
   map's.

Round 1 left the self-built map for later; round 2 measured it (subsection above) and
it is now the first route: no capture, no body-specific file to keep, and it follows
dust. The stored map of steps 1-2 remains the fallback for short stacks and the
prior for the self-built one. A stored map must be good to be worth having: the
existing 32-frame burst, used as a map, made the pattern worse (its per-photosite
noise is as large as the pattern).

### How to know it worked

- Instrument: `fpn-pairs.py --band 0.08,0.30 --flat` on single groups rendered alone
  (`STREHL_FRAME_PARITY=K-K`) and on two four-group merges.
- Bar: pattern-to-noise in that band falls at least fivefold (green one group from
  0.33-0.41 to under 0.08; four-group merge from 0.94 to under 0.19).
- The map must not have seen the frames it is scored on: another session for a
  stored map, other planes of the stack for a self-built one.
- Placebo: the same map rolled by (5, 3) photosites must not lower the figure (it
  should raise it: a wrong map adds a pattern).
- Positive control: a synthetic pattern of 0.5 % multiplied into the decoded members
  must read at its planted size and rate, and vanish when the same pattern is supplied
  as the map.
- Default-off renders byte-identical; A7C II byte-freeze.
- Eye: a smooth bright scale surface at 1:1 with an 8x contrast stretch about its
  mean, before and after, identical transform.

### Cost and risk

One multiply per sample at the read. A noisy map adds its own pattern: at 200 frames
near half scale the map's noise is 0.05 % against a 0.30-0.40 % pattern (2 % of its
power), and the 0.95-0.97 day-to-day correlation leaves another 6-10 %; together about
a tenth of today's power (DERIVED). Dust moves over weeks; the high-pass
keeps the map to what is the sensor's. Response non-uniformity can differ between
conversion-gain ranges; UNVERIFIED on this body, hence the refusal above.

The self-built map (round 2) costs one more pass over the raw frames, four Gaussian
filters per CFA plane: 40 s for 392 frames in the GPU prototype with the members
already decoded; the CPU cost is UNVERIFIED. It leaves 10-17 % of the pattern's power
where a good stored map was derived to leave about a tenth, so the two are
comparable, and it cannot be stale.

---

## 3. Item 2: calibrated fusion

### What is known

`STREHL_FUSION=depth` averages frames around each point's focus plane with weights
from the measured through-focus transfer. It doubles fine-detail signal-to-noise power
(23.7 / 25.2 / 23.5 against the election's 12.1 / 12.9 / 11.9) and has stayed off for
two reasons: it keeps only 0.82 of the finest detail, and it lifts dark areas by about
10 %.

Measured here:

- The lift is real with an independent mask (the earlier measurement chose dark pixels
  on one of the scored images) and it is mostly not an edge effect: +0.5 to +0.7 % of
  the bright level from 6 px to beyond 200 px from any bright pixel, +2.4 % in the
  first 6 px (`halo-distance.py`). On a ground a twentieth as bright as the scales
  that is the 10 %.
- It is a calibration error, not light the method inevitably spreads. Bringing each
  band of the fusion back to the election's amplitude with one gain per band, and
  taking everything coarser than 32 px from the election, gives (`calibrated-fusion.py`,
  built from the finished renders):

| Arm (ratios to the election) | Fine detail R / G / B | Noise in that band | SNR power | Dark level, 3-6 px | 6-100 px | 100+ px |
| --- | --- | --- | --- | --- | --- | --- |
| election | 1 | 1 | 12.1 / 12.9 / 11.9 | 1 | 1 | 1 |
| fusion as shipped | 0.82 | 0.58 | 23.7 / 25.2 / 23.5 | 1.26 | 1.08-1.14 | 1.09-1.18 |
| calibrated | 1.00-1.04 | 0.72-0.75 | 23.3 / 24.9 / 23.2 | 1.08 | 0.95-0.97 | 1.01 |

  The gains needed: 1.27-1.32 in the finest band (0-1 px), 1.03-1.08 at 1-2 px,
  0.98-1.01 from 2 to 32 px.
- The far-field lift lives in the fusion's coarse levels. The existing knob
  `STREHL_FUSION_COARSE=election` does not cure it: in that arm, dark areas more than
  100 px from anything bright are 14-35 % brighter than the election's at 32-64 px
  scales, worse than the plain fusion's 7-17 % (MEASURED, `coarse-compare.py`). With
  the three finest levels guided, the election of the remaining levels does not
  reproduce the plain election's. Find out why before anything else in this item; the
  election's pooled evidence from finer levels is the first suspect (ARGUED).
- Keeping the fusion only where it agrees with the election within noise
  (`gated-fusion.py`) removes the lift and nearly all the gain. Do not build that.
- The election has a small defect of its own that the fusion does not: the planes the
  election's weights are computed from carry 10 % more noise power than the planes
  that only receive those weights (`parity-bias.py`). Under the fusion all four site
  planes of a channel agree within 0.3 %.

### What to build

1. **Coarse levels and base exactly as the election produces them.** The straightforward
   way is two folds: the election first (keep its finished planes, 0.7 GB), then the
   fusion; build both pyramids at the end and take every level past the guided ones
   from the election. Cost: one more pass over the frames. Cheaper routes exist once
   the knob's defect is understood.
2. **Unit transfer for the guided levels.** Per guided level and channel, the gain
   `<E E'> / <F E'>` over confident in-focus cells, with `E'` the election's other
   half so noise does not bias the ratio (the half-stack accumulators already exist
   for the restoration). Apply before the collapse.
3. **Let the restoration equalise what a per-level gain cannot.** Inside one plane
   level the loss still varies with frequency (flat 0.82 over 0.24-0.38 cycles/px,
   falling to 0.59 at 0.49). The restoration's blend transfer is the right place, but
   measure it against the election's merge, not against two single frames: that
   reference is clean at every frequency, so the fit no longer needs to stop at
   reference signal-to-noise 2 or be forced monotone. Check its clamp (0.3-1.15)
   against the 1.3 the finest band needs.
4. Leave the remaining +8 % in the first 6 px for a second step. It behaves like
   light spread across a bright-dark boundary by averaging frames whose blur differs.
   The candidate is a robust combination: reject, per coefficient, frames whose value
   departs from the transfer model by more than their noise allows.

### How to know it worked

- `halo-distance.py` with the mask from the other half: every distance bin within 3 %
  of the election, the first within 5 %. Control: the election's own other half reads
  1.00.
- `compare-colour.py`: fine detail at least 0.98 of the election's in every channel,
  signal-to-noise power at least 1.8 times.
- `radial-ratio.py`: the signal ratio to the election flat within 3 % from 0.05 to
  0.40 cycles/px.
- **A shadow reference before default-on.** Which merge has the right shadow level is
  not established: against one in-focus frame rendered alone, every full merge reads
  darker (election 0.79-0.89, fusion 0.83-0.91, calibrated 0.74-0.83), and one focus
  step moves that figure by 3 % (`shadow-truth.py`). Until a stack of a target with a
  known dark level exists (section 9), 5 % is the tightest tolerance that means
  anything.
- A7C II byte-freeze; default four-shot render unchanged while the switch is off.

### Round 2 additions

- **Where the gain is largest.** The election's weights follow noise where there is
  no detail, so smooth bright areas get the fewest frames: 5.6 noise-equivalent
  frames in the finest plane band against 6.9 in textured areas, 5.4 against 11.1
  one level up, and 9-15 % more noise per unit level than textured areas at scales
  under 2 px (`weight-dump.py`). The shipped fusion's noise amplitude in smooth
  bright areas is 0.59 / 0.46 / 0.40 / 0.38 of the election's at 0-1 / 1-2 / 2-4 /
  4-8 px; with this item's gains on the two finest bands, about 0.77 / 0.48 / 0.40 /
  0.38 (DERIVED). Smooth areas are where grain shows.
- **The windows are about right.** Per pixel (`point-focus.py`), a 7-frame window
  keeps 0.90 of the fine band's amplitude at 5.7 best frames of signal-to-noise;
  positive matched weights over 17 frames reach 7.6, and nothing wider adds to it.
  The mid and coarse bands keep gaining to the edge of 17 frames (11.8 and 14.0).
  Signed or complex weights across focus are not worth trying: frames on opposite
  sides of focus hold different detail, not the same detail with a phase
  (`phase-coherence.py`).
- **A later refinement:** widen the window where a neighbourhood holds no detail
  above noise; there is nothing there to blur, and the coarse band tolerates 17
  frames at 0.91. DERIVED, not prototyped: smooth-area noise would fall by about a
  further third.
- **Part of the 0.82 is misregistration, not defocus** (item 10). Fix that first
  and the finest band needs less gain, so costs less noise.
- A reader of `STREHL_PYRAMID_WEIGHT_DUMP` must decode its frame numbers (section
  8, point 7).

### Cost and risk

One more fold (about 100-190 s on this run) and the depth pass the default already
pays. Memory as today if the election's finished planes, not its accumulators, are
kept. The fusion's weights assume one focus plane per cell; depth edges inside a cell
are where the first 6 px come from.

---

## 4. Item 3: keep the measured colour

### What is wrong

Colour carry writes red and blue as green plus their difference from green smoothed at
1 px. That was introduced because a carried red or blue sample has all of its own
noise, and the measure used then (shared power between half-stacks) rose. It rose
because green's fine detail was being copied into red and blue.

Scored instead by how well each output plane matches that plane's own content in the
independent half (`cross-channel.py`), the smoothing is a loss on this subject: the
three channels' fine detail is largely independent here (red-green coherence 0.54 at
0.15 cycles/px, 0.18 at 0.30; not a displacement between channels, not sensor pattern,
visible as a fine pastel mottle that repeats between independent half-stacks).

| Error, % of the channel's own signal power | Red, 0.10-0.25 | Red, 0.25-0.40 | Blue, 0.10-0.25 | Blue, 0.25-0.40 |
| --- | --- | --- | --- | --- |
| as carried | 3.4 | 17.5 | 2.9 | 28.3 |
| per-channel Wiener | 3.3 | 14.7 | 2.7 | 21.6 |
| shipped smoothing | 23.5 | 133 | 9.2 | 105 |
| joint three-channel Wiener | 3.2 | 14.7 | 2.7 | 21.1 |

(Half-stack noise; 100 % is what writing no fine detail would score.) The
colour-difference signal is far above noise in the full stack: red minus green reads
60, 23, 11 at 0.155, 0.255, 0.355 cycles/px, of which the 1 px Gaussian keeps 0.62,
0.28, 0.08.

By eye the two renders are hard to tell apart at normal saturation on this pale
subject (`q1-default-vs-rawchroma-4x.png`); with colour exaggerated the unsmoothed one
shows the finer mottle and also more colour grain. Expect the difference to matter on
subjects whose fine detail is strongly coloured.

### Round 2: do item 8 first

Round 1's control for "not a displacement between channels" was fitted where coarse
content decides. Fine red detail is displaced a pixel from green (item 8). The
conclusion survives the repair, re-scored on registered half-stacks
(`cross-channel.py`): the shipped smoothing's error is 17.6 % and 98 % of red's
signal power in the two bands of the table above and 8.5 % and 93 % of blue's,
against 3.0 %, 14.9 %, 2.7 % and 21.8 % for a per-channel filter; the joint filter is
1.00-1.04 times the per-channel one. Red-green coherence at 0.30 cycles/px is 0.40
once registered (0.18 in the table's data) and blue-green 0.54 (0.47). Without item
8, switching the smoothing off exposes fine red and blue in the wrong place.

### What to build

Replace `colour_carry::smooth_chroma` with a filter designed from the stack's own
spectra, in the restoration, where the half-stacks already are:

1. Extend the restoration's spectra to the cross-channel terms: per radial bin the
   3 x 3 matrix of what the halves share between channels (symmetrised, projected to
   positive semi-definite) and the per-channel noise.
2. Per bin, `W = S (S + N)^-1` with the full stack's noise (half the half-stack's),
   then each channel's restoration gain. Nine small kernels where there are three;
   same square-root domain and highlight guard.
3. This one filter is the per-channel Wiener where the channels are independent (this
   subject) and borrows from green where they agree (a neutral subject), so it
   subsumes today's smoothing where today's smoothing is right. When a stack cannot
   measure it (the cases where the restoration already falls back), fall back to
   today's smoothing.

### How to know it worked

- `cross-channel.py`'s instrument on the restored halves: for every channel and band
  the error no worse than the per-channel Wiener's.
- Placebo, as in that script: red and blue rolled 8 px against green before the
  filter is designed; the joint filter must then match the per-channel one.
- The second subject, when it exists: on a subject with little fine colour, noise in
  red and blue no worse than 1.1 times today's.
- Eye: crops with colour differences exaggerated 3x, both halves side by side; what
  repeats between halves should survive, what does not should not be amplified.

### Cost and risk

About 12 s more at the write (DERIVED: three kernels take 6 s today). A global filter
is tuned to the in-focus tiles'
statistics; the square-root domain keeps shot noise roughly uniform across levels, but
dim areas with little chroma signal may show more colour grain than today. A taste
control (a power on the shrinkage) costs nothing to add.

---

## 5. Item 4: a true finest band

### What is wrong

The carried merge folds twelve half-resolution site planes, each with its own
pyramid. A level of a plane-domain pyramid passes output frequencies near every
multiple of 0.5 cycles/px, so output detail above 0.375 cycles/px is carried by plane
level 1, above 0.4375 by level 2, and so on, and is merged with those levels' frame
weights. Under the election that costs nothing measurable (the merge matches its own
best frames). Under the fusion, whose windows widen with level (7.1, 11.6, 16.4
frames), the finest detail, which decorrelates across frames fastest, gets the widest
windows:

| cycles/px | 0.156 | 0.256 | 0.356 | 0.406 | 0.444 | 0.469 | 0.494 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fusion signal / election | 0.874 | 0.820 | 0.815 | 0.800 | 0.739 | 0.679 | 0.587 |
| fusion SNR / election | 2.79 | 2.28 | 1.74 | 1.52 | 1.23 | 1.00 | 0.74 |

(MEASURED, `radial-ratio.py`.) The top octave is exactly where the restoration is
short of signal-to-noise: it delivers 0.16-0.19 of a 0.21 target at 0.4 cycles/px.

### What to build

Two routes; try the first.

1. **Split each channel's four site planes before the pyramid** into their mean and
   three difference planes (a 2 x 2 Haar step per quad, per channel, linear and
   exactly invertible). The mean plane goes through the pyramid as now. The three
   difference planes hold the top octave by orientation; merge them as one band, at
   plane resolution, with the finest weights and, under the fusion, their own measured
   window. Invert after the merge and interleave. Twelve planes stay twelve.
2. **A full-resolution three-plane pyramid** for four-shot stacks: the gather writes
   red, green and blue at output resolution (the same sample count), one more level,
   election on full-resolution green. Cleaner, and a larger change to the merge's
   plane geometry and planners.

In both, measure the fusion's window for the new band the way the depth pass measures
the others. Under the election, consider the difference planes' energy as the focus
cue for the finest level: it falls with defocus faster than anything else in the
frame. That is a separate arm with its own bar.

### How to know it worked

- `radial-ratio.py`: the fusion's signal-to-noise ratio to the election at least 1.5
  at 0.45 cycles/px, and no knee between 0.38 and 0.45.
- Election arm: signal within 1 % of today's at every frequency (the split must be
  neutral when the weights do not differ).
- A planted zone plate through a synthetic stack with a known sub-pixel drift: no
  moire at the split's band edge.

### Cost and risk

Route 1: one linear step per frame and per merge. The 2 x 2 mean is a weak low-pass
(0.38 at 0.375 cycles/px on an axis), so between a tenth and a fifth of the top
octave's power still travels in the mean plane (DERIVED); that is the residual to
expect. Bit-identity of the native
sites with plain `remosaic` goes away under the switch.

---

## 6. Items 5 to 7

### Item 5: the gather kernel in the restoration's model

Every frame is gathered through a four-tap Catmull-Rom at a sub-pixel phase that
cycles every 59 px (the coverage fit scales every frame by 0.9827). Averaged over
phase the kernel passes 0.973 / 0.889 / 0.821 / 0.743 at 0.20 / 0.30 / 0.35 / 0.40
cycles/px per axis (`kernel-table.py`); one gathered frame's fine noise power swings
by 0.48 on that grid, as predicted (`phase-pattern.py`). The restoration models
diffraction, the photosite aperture and the blend, not this, so it under-delivers its
own target by that factor (reaching the target takes +3 %, +12 % and +35 % at 0.2, 0.3
and 0.4 cycles/px on an axis, less on the diagonals, and only where noise allows).

Build: multiply `optical_restore::system_mtf` by the phase-averaged response on each
axis (`strehl_core::restore::gather_mtf` already computes it per kernel), and divide
the reference spectra by its square before the cutoff fit, since the reference frames
were gathered too. Verify with a Catmull-Rom-gathered synthetic in the existing
planted-cutoff tests (the fitted cutoff must not move), and on the scarab halves:
restored fine detail up by the predicted factor with signal-to-noise power unchanged
(a linear filter cannot change it; that is the control).

This raises grain with detail. If the owner prefers today's balance, the target sigma
is the control, and it then means what it says.

A longer kernel for four-shot gathers (eight-tap Lanczos passes 0.90 at 0.40 and
flattens the per-frame swing from 0.64 to 0.83 of the noise power at the worst phase)
is optional: once the mean loss is modelled, what is left is under 6 % of
signal-to-noise from mixing phases (DERIVED).

### Item 6: per-channel focus in the depth guide

Red's focus sits 3.2 planes and blue's 2.0 from green's on this run (the prototype's
measurement, A7CR). Round 2 measured it per pixel on the product's own gathered
frames (`point-focus.py`): red's fine band peaks 3-3.5 frames after green's and
blue's 2-2.5, and at green's focus red keeps 0.93 of its own peak amplitude and blue
0.96. So the prize is about +7 % and +4 % of fine amplitude. With colour carried, every channel is fully sampled, so the
objection that sank per-channel focus on single-shot data (a frame's finest red
belongs to that frame's green) does not apply; the other one does (frames several
apart sit 0.3-0.5 px from each other), and a fusion window already averages across
it. Build: a per-channel offset field added to the depth guide's focus plane for the
red and blue site planes. Bar: red-minus-green and blue-minus-green edge-band
coherence no higher than without it, red and blue fine detail no lower, and the
reversed-offset placebo worse. The offsets and the loss are MEASURED; the correction
is unbuilt. Frames three apart sit 30 ppm of scale from each other until item 10
exists, which would cost most of a 7 % prize at the corners.

### Item 7: sub-pixel reconstruction

With ten planes sharing a point's focus, their natural sub-pixel phases are spread
well enough to double the sampling density over most of the frame (noise amplification
under 2 on 80 % of it, `phase-coverage.py`). On this rig there is almost nothing
beyond the pixel grid to recover: the lens passes 2 % (green) to 7 % (blue) contrast
at 0.55 cycles/px (DERIVED from the fitted cutoffs). Record it as the software route
to the bare-lens experiment that sixteen-shot capture was proposed for; do not build
it for this lens setting.

---

## 7. Checked, and not worth building

| Idea | Finding | Label |
| --- | --- | --- |
| Borrow fine detail across colour channels (a joint filter to lift fine-band signal-to-noise) | 1.00-1.07x. The channels' fine detail is not shared on this subject. The joint filter is still the right replacement for the chroma smoothing (item 3), for a different reason | MEASURED |
| Correct a two-pixel-period pattern from member exposure or position mismatch | 0.02 % of level at worst. The shipped first-order residual compensation already removes the member-motion noise beyond the cutoff (34 % lower than uncompensated; the reversed-sign placebo 86 % higher) | MEASURED |
| Remove a resampling grid from the output | One frame carries one (depth 0.48, 59 px); a full merge does not (excess under 0.03) | MEASURED |
| Gate the fusion on agreement with the election | Removes the lift and the gain together | MEASURED |
| A sharper interpolation kernel as a source of detail | A linear gain that the restoration can supply once the kernel is in its model (item 5) | DERIVED |
| Round 2: withhold the restoration where a neighbourhood holds no detail (locally adaptive restoration) | Noise and error move by 1-2 %. The restoration's increment carries little of the image's noise; smooth-area grain is the merge's (item 2) and the sensor's (item 1) | MEASURED |
| Round 2: weights wider than the fusion's in the fine band, or signed weights across focus | The fine band is at its ceiling inside 17 frames (7.6 best frames against 5.7 for a 7-frame window); frames on opposite sides of focus hold different detail | MEASURED |
| Round 2: a defect map for four-shot stacks | No photosite more than 5 % off in response; 17 / 18 / 121 (R / G / B) more than 2 % off; none 50 DN above black in the darks. The flat field covers them | MEASURED |
| Round 2: the existing 32-frame calibration burst as a stored response map | Worse than no correction | MEASURED |
| Round 2: a blue-lit exposure for detail (pixel shift samples blue fully and diffraction favours it) | Blue is the softest channel at mid frequencies at this lens setting: 0.78-0.87 of green's contrast at 0.14-0.33 cycles/px | MEASURED (neutral slide) |
| Round 2: a stiffer rig | Member positions scatter 0.05-0.08 px per axis, as on a static target, with no growth across a group | MEASURED |

---

## 8. The scoring instrument's blind spots

Every table in the full-potential results, and several here, scores an arm by the
power its odd-frame and even-frame half-stacks share ("signal") and the power they do
not ("noise"). Three things count as signal that are not scene:

1. **The sensor pattern.** It is the same in both halves. After item 1 the "signal" of
   smooth areas will fall; that is the pattern leaving, not detail.
2. **Detail the election makes.** Merges share power beyond the lens's cutoff that
   single frames do not: 0.17 / 0.47 / 0.17 of the half-stack noise power in the
   frequency corners for red / green / blue, unchanged by member compensation, halved
   by the fusion. And the planes the election's weights come from carry 3 % more
   shared power and 10 % more noise than the planes that only receive the weights.
   ARGUED: near-argmax selection among frames a fraction of a pixel apart is
   nonlinear. It is small (about 0.15 % of level) and sits where the lens leaves
   nothing, but it means an election arm's "signal" is not purely optical.
3. **Content copied between channels or frames.** The chroma smoothing's doubling of
   red's and blue's "signal-to-noise power" was green's detail counted as red's.

Round 2 found four more ways to be fooled:

4. **A channel displacement has a passband.** Red's and blue's displacement against
   green is not one number (item 8): coarse and fine content sit at different
   magnifications. An estimator weighted by spectral power reads the coarse value;
   state the band of any channel-displacement figure, and measure at least a coarse
   band (0.03-0.08 cycles/px) and a fine one (0.24-0.42). This is the standing
   disagreement between the refinement's instrument and `lateral-profile.py`.
5. **Tile statistics through focus are not a point's.** Over a 256 px tile of this
   subject, frames six apart share 13 % of their fine power while each holds 80-90 %
   of the tile's peak: different parts of the tile are in focus in different frames.
   Use per-pixel products grouped by a depth label from another band
   (`point-focus.py`).
6. **A pooled rim level hides a displacement.** Dark pixels are not spread evenly
   around bright detail, so shifting a channel moves the pooled mean. Split by side
   (`rim-colour.py`) before blaming a filter.
7. **`STREHL_PYRAMID_WEIGHT_DUMP` does not number frames in file order** when the
   restoration's half-stacks are on (the default for pixel-shift stacks): label `a`
   below `ceil(N / 2)` is frame `2 a`, otherwise `2 (a - ceil(N / 2)) + 1`.

What to use instead, by case:

- A step that can move content between channels or frames: the error against the
  independent half, per output plane (`cross-channel.py`).
- The sensor pattern: the displaced-pair measurement (`fpn-pairs.py`).
- Dark levels: classes from an image that is not scored (`halo-distance.py`).
- Any arm that only filters linearly must leave per-frequency signal-to-noise
  unchanged; `radial-ratio.py` on the restoration reads 0.995-1.015. Use that as the
  instrument's daily check.

---

## 9. Captures needed

Round 2 changed this list: capture 1 is no longer required (item 1 now builds its map
from the stack), and captures 4 and 5 are new.

1. **A flat-field series on the A7CR** (for item 1; optional since round 2, as a
   cross-check and as the stored fallback for short stacks). Lens as for a stack,
   focus run far off a plain matte white target so nothing is resolved, even light,
   ISO 100,
   single-shot, shutter chosen so green sits near 8 000 DN above black (about 55 % of
   full scale: the response starts to compress above 9 500). 256 frames at one fixed
   focus position. If convenient, nudge the target between four blocks of 64 so its
   own texture cannot repeat. About ten minutes and 31 GB before compression. One
   series should serve every later stack in the same conversion-gain range (ISO
   100-320 on this body; UNVERIFIED across ISO); repeat at ISO 400 if stacks are ever
   shot there.
2. **A second four-shot subject** (already request 4 in `captures-needed.md`); item 3
   in particular wants one with little fine colour and one with a lot.
3. **A shadow reference** (for item 2, before default-on): a matte white card with a
   clean edge over a deep black cavity (a box lined with black flock), stacked through
   the edge's depth, four-shot. The cavity's true level is the darkest any in-focus
   frame shows next to the edge; merges are then scored against that.
4. **A neutral-target stack** (round 2; for item 9, and as the second check of item
   8's shares): the black-on-clear resolution slide, lit exactly as subject stacks
   are (not room light), four-shot, stacked through its depth at the normal focus
   step, 30-40 planes; a tilt is welcome. Fifteen minutes.
5. **A light-balance pair** (round 2; item 11): one subject and framing, two short
   four-shot stacks of about 20 planes, the first as normal, the second with a
   magenta gel over the lamps and the shutter lengthened until green's histogram is
   back where it was.

Not needed for any of this: the sixteen-shot bare-lens capture.

---

## 10. Working rules for the implementing agent

- Every item behind its own switch, default off, declared in
  `scripts/check-defaults.py`; default renders byte-identical; A7C II byte-freeze
  after any change to the gather or the merge. Default-on is the owner's call, per
  item, after the second subject.
- One subject stands behind every number here (round 2 added the neutral slide, for
  items 8 and 9 only). Re-run the instrument named in each item on the second subject
  before believing a size.
- State each claim's label. The sizes in section 1 that are DERIVED (the pattern's
  share in the default output, item 2's smooth-area figure, item 4's gain, item 5's
  gain, item 10's gain, item 11's gain) are predictions to be replaced by
  measurements.
- Score with the instruments of section 8, each with its named control, before using
  it on a new arm.
- Capture folders are read-only; renders one at a time (a four-shot render peaks at
  22-24 GB).
- Open questions this investigation leaves: why `STREHL_FUSION_COARSE=election` does
  not give the election's coarse levels; what the true shadow level is; what the
  first 6 px of lift under the calibrated fusion are; whether the response map
  transfers across conversion-gain ranges.
- Open after round 2: whether the green-band shares of item 8 are constants of the
  body (one subject and one light gave them); how the own bands' lateral colour
  varies with the light; why the alignment's magnification step is 8 % short;
  whether the finest band focuses at a different plane from the mid band (tiles say
  six frames earlier, pixels say one frame later; neither is trusted); how short a
  stack can be and still build its own response map; what the remaining rim (+1.2 to
  +2.4 points on every side after registration) is made of on a subject that is not
  itself coloured at its edges.

---

## 11. Item 8 (round 2): register red and blue by component

### What is wrong

The red and blue filters pass some of the light that makes green's image. The lens
images that light where it images green; the rest of each channel (its own band) is
displaced by lateral colour. A red or blue plane is therefore two images at two
magnifications, and one lateral-colour scale per channel cannot register both.

Measured in the raw frames of assembled groups, with no resampling and no correction
(`raw-channel-shift.py`, 1 087 in-focus tiles of five planes), the radial scale of
each channel against green:

| cycles/px | 0.03-0.08 | 0.08-0.14 | 0.14-0.24 | 0.24-0.42 |
| --- | --- | --- | --- | --- |
| red, ppm | -539 | -210 | -39 | -16 |
| blue, ppm | +166 | +99 | +27 | +6 |

Coarse content is displaced; fine detail is not. The fine part is green's image at the
same site: its transfer from green is flat at 0.22 (red) and 0.15-0.19 (blue) of
green's raw signal from 0.18 to 0.43 cycles/px, on the axes and on the diagonals
(`raw-leak-kernel.py`). Charge or light arriving from the four adjacent green
photosites would fall to a tenth by 0.4 cycles/px on the axes and change sign on the
diagonals; it does neither, so this is the filters' spectral overlap (DERIVED from
the kernel's shape). On the neutral slide every band reads one scale (red -251 to
-241 ppm), as a mixture must when both parts carry the same structure.

What that does today:

- The profile (-464.6 / +205.6 ppm, fitted to coarse content) moves each whole
  channel, so in a render fine red detail lies +425 ppm from green: 1.03 px rms over
  the in-focus tiles, 2.4 px at the corners. Fine blue lies -173 ppm away, 0.43 px.
- The per-capture refinement measures one displacement in one passband and applies
  it to the whole channel. On the scarab it moved blue 0.245 px to register blue's
  coarse content, which put blue's fine detail 0.2 px off, and it left red's fine
  detail where it was (+431 ppm afterwards).
- The 1 px chroma smoothing hides all of it by replacing fine red and blue with
  green's. Item 3 removes that smoothing, so this item comes first.
- It is why the profile read -465 ppm on shipped renders and -800 with each channel
  at its own focus, and why the refinement's instrument and `lateral-profile.py`
  have never agreed.

### What to build

1. In the four-shot gather (`align_cmd.rs`, `measured_rows`) every tap site holds a
   measured green as well as the channel being gathered. Gather the channel's own
   band, `C - k G` (raw units, after black level and member gain, the site's two
   greens averaged), at the channel's lateral-colour coordinates, and add `k` times
   green as gathered at green's coordinates for the same output sample. Three sample
   reads per tap where there was one. Where member residuals are compensated, do
   that first.
2. `k` for red and blue: per camera body, in the profile. Measured here: 0.18 and
   0.17 by nulling the fine-band displacement, 0.22 and 0.15-0.19 by the raw-frame
   transfer. Start from 0.20 and 0.17.
3. The own bands' lateral colour replaces the profile's figures: about -865 and
   +285 ppm under the scarab's light (the profile's -464.6 and +205.6 are the
   mixtures' on the coin). It depends on the light (the slide under room light
   implies about -400 for red; DERIVED), so keep the per-capture refinement, run it
   on the own-band planes, and let it apply the translation it measures: blue's own
   band sits a uniform 0.38 px from green in y on this run and the green-band share
   does not.
4. A per-stack check of `k`: after the correction the radial scale in 0.24-0.42
   cycles/px must be null. A residual with the sign of the own band's scale means
   `k` is too small. Print the coarse-band and fine-band residuals in the banner.
5. Single-shot stacks are not touched: green is not measured at red and blue sites,
   and the demosaic already ties fine colour to green.

Because the merge applies one set of weights to every plane, the repair commutes with
it, and the prototype (`leak-fix.py`) made it on finished half-stacks:
`C_fixed = warp(C - a warp(G, 1 - eps), 1 + delta, t) + a G`, `a` the share in
white-balanced units (0.35 red, 0.42 blue).

### How to know it worked

- `channel-shift.py --band` on raw-carry half-stacks, in 0.03-0.08, 0.11-0.18 and
  0.24-0.42 cycles/px: radial scale within 80 ppm of zero and offset within 0.07 px
  in every band, both channels; displacement rms over in-focus tiles no more than
  0.25 / 0.15 / 0.08 px (red) and 0.15 / 0.12 / 0.06 (blue). The prototype reached
  those.
- Placebo: `k` with its sign reversed must raise the fine-band displacement (the
  prototype's placebo, the share moved the wrong way, read 0.61 px for red and
  raised blue's colour-difference power 3-10 %).
- `rim-colour.py` by side: red-minus-green differs by no more than 0.7 points
  between opposite sides of bright detail (prototype -0.37 and -0.65; as carried
  -0.72 and -1.37; whole-channel re-fit -0.26 and -1.88).
- `cross-channel.py`: no channel's error worse; coherence with green at 0.30
  cycles/px about 0.40 (red) and 0.54 (blue).
- Red's and blue's fine-band noise power no more than 1.08 times today's (DERIVED:
  green's noise enters twice, at two interpolation phases, times `k` squared).
- The neutral slide: one scale at every band before and after; red's rim on dark
  ground no worse than a single re-fitted scale gives (4.9 points against 8.2 as
  rendered, green 3.2).
- Default-off renders byte-identical; A7C II byte-freeze.

### Cost and risk

Two more sample reads per red and blue tap. The shares come from one subject under
one light; on a neutral subject the phase check of step 4 cannot identify `k`
(both parts carry the same structure), so the profile's value stands there. Two
components stand in for a continuum of wavelengths: the prototype leaves up to 80
ppm between bands. At normal saturation the picture changes little; the point is
that fine colour is in the right place for items 3 and 9, and that the refinement
stops trading coarse registration against fine.

---

## 12. Item 9 (round 2): measured per-channel transfer in the restoration

### What is wrong

The restoration gives each channel the transfer of a diffraction-limited lens at the
channel's nominal wavelength, one aperture fitted to all three. That makes blue the
sharpest channel and gives it the least gain (scarab log, system to restored at 0.2
and 0.3 cycles/px: green 0.54 to 0.67 and 0.32 to 0.39; blue 0.56 to 0.65 and 0.36 to
0.35). Measured on the neutral slide (`channel-transfer.py`, amplitude relative to
green, in-focus tiles):

| cycles/px | 0.065 | 0.10 | 0.14 | 0.18 | 0.225 | 0.275 | 0.325 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| blue, measured | 0.95 | 0.91 | 0.87 | 0.82 | 0.81 | 0.78 | 0.81 |
| blue, the model | 1.01 | 1.02 | 1.04 | 1.06 | 1.10 | 1.14 | 1.20 |
| red, measured | 0.96 | 0.91 | 0.86 | 0.84 | 0.86 | 0.91 | 0.99 |
| red, the model | 0.99 | 0.98 | 0.96 | 0.94 | 0.91 | 0.87 | 0.82 |

Aberration lowers a lens's middle frequencies and leaves its cutoff, which is why the
cutoff fit is sound (blue's own fit reads 0.724 cycles/px) and the curve is not. Red
above 0.3 cycles/px is not a clean transfer until item 8 exists (it contains the
displaced green-band share).

The visible form is a coloured rim: after registration is repaired, dark ground 3.5-10
px from bright detail still carries 1.2-2.4 points (of the bright level) more red and
blue than green, on every side. Filtering red and blue by one over the slide's ratios
(`equalise-channels.py`, gains up to 1.18 and 1.26) moved the scarab's rim:

| Dark pixels, distance from bright | 3.5-5 px | 5-7 | 7-10 |
| --- | --- | --- | --- |
| red minus green: before / equalised / inverse filter (placebo) | +4.12 / +3.10 / +5.06 | +2.59 / +2.07 / +3.07 | +1.66 / +1.52 / +1.80 |
| blue minus green | +0.81 / -0.34 / +1.88 | +1.58 / +1.00 / +2.14 | +1.42 / +1.25 / +1.59 |

About one point of red's figure at every distance is the beetle's brown cuticle.

### What to build

1. A table per lens setting in the optical profile: red's and blue's transfer
   relative to green's at about ten frequencies, with the light it was measured
   under.
2. A builder that measures it from a neutral-target stack (section 9, capture 4):
   in-focus tiles, `sqrt(S_cc / S_GG)` from two half-stacks, after item 8 has
   registered the channels.
3. In `optical_restore`, red's and blue's system transfer becomes green's model
   times the table. The cutoff fit, the blend transfer, the target and the noise
   term stay as they are.
4. No table for the gear: today's behaviour, and the banner says so.

### How to know it worked

- The neutral-target stack, restored: red's and blue's amplitude within 5 % of
  green's from 0.05 to 0.30 cycles/px.
- `rim-colour.py` on a subject stack: red-minus-green and blue-minus-green within 7
  px of bright detail each at least a quarter lower than without the table; the
  inverse table raises them.
- `radial-ratio.py`: per-frequency signal-to-noise unchanged (a linear filter).
- Eye: bright-on-dark edges with colour differences tripled, before and after.

### Cost and risk

Nothing at run time. Blue's gain rises by up to 1.26 at 0.3 cycles/px (noise power
x1.6 there before the restoration's noise term trims it). The ratios used on the
scarab were borrowed from the slide under room light at one focus position; the test
shows the direction and rough size, not the table to ship. The rim is partly the
subject's own colour on this beetle (scale margins are bluer than their centres), so
judge the result on the neutral target first.

---

## 13. Items 10 and 11 (round 2)

### Item 10: refine frame registration after the alignment

Gathered frames one plane apart sit 0.13 px rms from each other on in-focus content,
four apart 0.32-0.48 px, eight apart 0.44-1.1 px (`series-focus.py`, 288 tiles, 33
single-group renders). One similarity per frame pair removes nearly all of it (0.02
px left at one plane, 0.07-0.09 at four), and its scale is linear in the distance:
10 ppm per plane against a magnification step of 124. The alignment's step is about
8 % short. On the coin the same test left most of the residual in place; that was the
coin's specular highlights, not the alignment.

The election reads one frame's worth of content and loses nothing by this. Anything
that combines neighbours does: a matched-weight average over 17 frames keeps
0.94-0.91 of the green signal power from 0.13 to 0.37 cycles/px against the same
frames registered, and a 7-frame window loses about 4 % of amplitude at 0.3 cycles/px
and 8 % at 0.4 (DERIVED from the displacements). That is a quarter to a third of the
fusion's 0.82, and unlike item 2's gain it comes back without noise. It also bounds
item 6.

Build: after the global solve, a second pass over the gathered frames. Per frame,
displacements against the frames two to four planes either side on tiles sharp in
both (the phase ramp of the green cross-spectrum over 0.03-0.30 cycles/px), solved
jointly for one residual similarity per frame with the anchor fixed (a joint solve,
not a chain), applied in the gather. Measure it per stack: the engineering rules
forbid carrying a fitted shrinkage correction from one scene to another, and this
residual is that shrinkage.

Bars: `series-focus.py`'s fitted scale within 3 ppm per plane and no more than 0.12
px rms at four planes; under the fusion, item 2's finest-band gain falls. Placebo:
the refinement with its sign reversed doubles the residual. Positive control: a
planted 40 ppm per plane is recovered.

### Item 11 (capture side): balance the light

Raw levels over the whole stack (`self-flat.py`): green's 99.999th percentile is
9 360-9 390 DN of 14 848, at the top of the linear range (the photon-transfer slope
bends from 9 500), so the exposure is already as high as it can go. Red and blue
reach 4 770 and 3 970 DN: 32 % and 27 % of the range. Light with less green in it (a
magenta gel over the lamps, the shutter lengthened until green is back at its level)
could give red up to 2.0 times and blue up to 2.4 times the photons before they
reach green's level: 0.71 and 0.65 of their shot-noise amplitude (DERIVED from the
levels, for a white subject and a gel that passes red and blue).

Costs: about twice the exposure time, and member motion grew with exposure time on
the coin (2 s against 0.6 s); the own bands' lateral colour and the channels'
relative transfer both move with the light, so items 8 and 9 would be re-measured
under it. UNVERIFIED until the pair of section 9, capture 5, exists. It matters most
once item 3 keeps measured colour, because colour grain is then red's and blue's
own.
