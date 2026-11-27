# Grounding the capture planning design: results

**Run:** 2026-11-27, 01:10 to 03:30, on the owner's machine and rig, by the design's author.
**Brief:** [brief.md](brief.md). **Scripts:** [scripts/](scripts/). **Design it feeds:**
[the capture calibration specification](../../../docs/proposals/2026-11-capture-calibration-spec.md).

Labels: MEASURED (a number from a command named here), VERIFIED (read in code, or seen in
native crops), DERIVED, ARGUED, UNVERIFIED. Build under test: installed
`desktop-91cc19f0619a9ac4` (`strehl-cli.exe`, source `origin/main` `b2c8a07aa`). Host: 32
logical processors, RTX 5090, otherwise idle. Scratch (pictures of the owner's subjects,
caches, per-plane summaries): `C:/strehl-scratch/plan-flow/`, not in Git.

Focus positions are the camera's focus units. "Sharp depth" is the width at half height of
a tile's fine-detail curve against focus, as `strehl focus-step` defines it.

## Summary

| # | Finding | Label |
| --- | --- | --- |
| 1 | The owner's observation is correct. On the dragonfly the engine's depth rule calls the subject "in focus" from the first plane to the last and offers bounds wider than the capture (32,034 to 33,290 for a capture of 32,062 to 33,262). The subject is in focus from 32,355 to 33,161. 44 of the 151 planes shot hold nothing in focus | MEASURED, VERIFIED by eye |
| 2 | The cause is brightness. Out-of-focus highlights carry more gradient energy than in-focus texture: the in-focus wing sits at 148 DN (0.9 % of full scale), the blur that scores as sharp at 2,056 DN | MEASURED |
| 3 | Fine detail measured against the local brightness instead of against the noise ("contrast") separates focus from bright blur on a single RAW frame. A fresh survey of 26 single RAWs, shot the next night, gives the dragonfly's range as 32,350 to 33,166 against the stack's 32,355 to 33,161. On five stacks whose subject lies inside the captured range it gives the range to within one sharp depth, from 13 frames as from all of them, with no tile in focus at the end planes. On three stacks whose subject runs past the captured range it says so, and native crops confirm it | MEASURED on 8 subjects, VERIFIED by eye |
| 4 | A live sweep already holds the subject's depth, in the position of each tile's peak. The host's rule reads the width of the peak instead, which is nine times the sharp depth. From one 36 s sweep of 33 positions spread over 6,080 units, peaks give the dragonfly's range as 32,373 to 33,150; the host's rule gives 31,780 to 34,250 | MEASURED on the rig |
| 5 | The highlight groups of the owner's dragonfly stack never reached the picture: 0 of 151 planes fused. The capture was right (the 1/40 s groups hold every highlight). The merge's ratio fit refused every plane; the same engine's survey measures that ratio on every pair to within 1.8 % of commanded. A prototype that takes the ratio from the hand-over sites fuses all 151 planes | MEASURED, VERIFIED in a render |
| 6 | With fusion on, the default look turns the subject nearly black: the tone step places white 12.5 times higher, because it finds its highlights by looking for pinned samples and fusion leaves none | MEASURED |
| 7 | A highlight group's own four-shot check fails about half the time at 1/40 s, for want of signal, not for motion | MEASURED (rig and render) |
| 8 | After the light comes on its output falls 11 % in 140 s and the picture drifts 4 to 6 px in 4 minutes. A live sweep is not disturbed by this; an exposure measurement is | MEASURED, two series |
| 8b | The rig is not still. Of 26 four-shot groups at one position, 7 were clean (their shots within 0.11 px), the rest 0.14 to 0.50 px off; the capture's own gate would have retaken 5. A series with nobody walking was no better. One proof plane is one sample | MEASURED |
| 9 | Not confirmed, and withdrawn from the design: highlight groups only where the glints are (on this subject every plane pins, in focus or not); a shorter exposure as the cure for a group that moved (1/40 s groups fail the check as often); the sharp depth as a property of the rig alone (it differs by a third between subjects at one lens position) | MEASURED |
| 10 | The sharp depth read on 64 px tiles is 7 to 21 % wider than on 16 px tiles. The tile's own depth does widen it, by less than the first argument supposed | MEASURED on 8 subjects |

## 1. The dragonfly stack and what is truly in focus

Input: `D:/StrehlCaptures/stack-1795713444768-14989`. 151 planes from 32,062 to 33,262 at
step 8, four-shot, 1.3 s at ISO 100, highlight groups at 1/40 s on every second plane, 952
RAWs, 30 GB, 30 min 47 s. The owner's outline (a hand-drawn polygon of 30 points) covers
58 % of the frame.

Method (`extract.py`, `curves.py`, `truth.py`, `narrow.py`): member 1 of every plane's
last complete base group is restored from its archive and read with rawpy; on one green
site plane the 4-neighbour Laplacian's energy (the measure `strehl focus-step` sums) is
taken per 16 px block for every plane. A 64 px tile's curve against focus is then judged by
its own shape: a point in focus gives a peak about one sharp depth wide, so the curve is
high-passed over 3.5 sharp depths and matched against a Gaussian of that width. A tile's
focus is its strongest such peak, at least 1.5 widths from either end of the run.

| Quantity | Value |
| --- | --- |
| Subject tiles (64 px) | 8,583 |
| With a narrow peak | 88 % of them; 2 of 6,168 backdrop tiles (the control) |
| Sharp depth, median (10th to 90th percentile) | 45 (35 to 59); the engine's own survey reads 48 (38 to 62) |
| In focus from, to | **32,355 to 33,161** (peaks that agree with their neighbours) |
| Planes outside that range and half a sharp depth | 44 of 151: 34 before, 10 after |

Checked by eye (`witness.py`, native crops of the green plane, one display transform a
row): the tile with the earliest plain energy peak (32,320) shows only bokeh discs there
and comes into focus near 32,400; tiles at 32,420, 32,740, 33,115 and 33,161 are sharp at
those positions and nowhere near the ends; tiles that "rise to the first plane" or "to the
last" are clipped highlight blobs whose rims stay hard at every focus.

What the installed build says (`strehl-cli subject <run>`, `strehl-cli survey <run>`,
outputs in scratch, the capture folder unchanged):

| Tool | Depth | Bounds it suggests |
| --- | --- | --- |
| `strehl subject`, 13 planes | planes 1 to 151, "sharpest at the first plane; sharpest at the last plane" | 32,034 to 33,290, "105 % of the range" |
| the same, "core" (central 99 % of cells) | | 32,330 to 33,090 |
| `strehl survey`, the whole stack as a survey | first 32,062, last 33,262 | `suggested_start` 32,038, `suggested_end` 33,286; core 32,358 to 33,062 |

The desktop offers `suggested_start` and `suggested_end` (`survey-cmd.rs`, `depth.first`
and `depth.last` with half a sharp depth; nothing under `crates/strehl-ui/src/capture-*`
reads the core). The core is nearer but cuts the far end by 100 units here and the near
end by 94 units on the patterned beetle (section 4).

The engine's automatic outline from 13 planes is good: it traces both wings and the gap
between them. The problem is depth, not area.

### Why

Curves of single tiles in three bands (`witness-curves.png`): where a tile is in focus,
the fine band has a narrow peak (30 to 56 units) inside wider peaks of the mid and low
bands, all at one position. A bokeh disc gives a hump 141 units wide; a clipped blob gives
energy that rises to the ends of the run, because a defocused highlight far above full
scale stays pinned while it spreads, and its rim stays hard. On this subject the
highlights reach 48 times the base exposure's full scale, so they stay pinned over
hundreds of units.

| Sample | Median level, DN above black | With a sample over half of full scale in the tile |
| --- | --- | --- |
| In focus (within a quarter width of the tile's peak) | 148 | 12 % |
| Over four widths from focus and yet strong (energy at least 15 times its noise) | 2,056 | 73 % |

## 2. A measure that is not fooled

### 2.1 One frame: energy against noise, and against brightness

(`index.py`; 64 px tiles; truth as above.) Fine-band energy over its noise expectation, by
the plane's distance from the tile's focus:

| Distance, sharp depths | median | 95 % | 99.9 % |
| --- | --- | --- | --- |
| under 0.25 (in focus) | 75 | 811 | 2,650 |
| 1 to 2 | 4.6 | 86 | 514 |
| 2 to 4 | 1.5 | 19 | 228 |
| 4 to 8 | 1.1 | 3.7 | 61 |
| over 8 | 1.1 | 1.5 | 10 |

A tile in focus has a median of 75 and a tile eight widths away can reach 10 to 61: no
threshold on this quantity separates them. The engine's threshold is 1.75.

The same energy above its noise, divided by the level squared:

| Distance, sharp depths | median | 99 % | 99.9 % |
| --- | --- | --- | --- |
| under 0.25 | 1.9 | 8.4 | 13 |
| 1 to 2 | 0.07 | 0.79 | 1.5 |
| 2 to 4 | 0 | 0.27 | 0.64 |
| 4 to 8 | 0 | 0.045 | 0.23 |
| over 8 | 0 | 0.0007 | 0.014 |

(The block form: contrast per 16 px block, the tile takes the 75th percentile of its 16
blocks.) A threshold that keeps 90 % of in-focus samples passes 2.6 % at one to two
widths, 0.13 % at two to four and 0.02 % beyond.

A ratio of the fine band to a mid band was also tried and does not work: far from focus
both are noise and the ratio is large again (23 % of samples over four widths away pass).

### 2.2 The rule, as tested

1. Per 16 px block of one green site plane: fine energy `e` = mean squared 4-neighbour
   Laplacian, less its noise expectation `n(level)`; zero unless the raw energy is at
   least `3 n`.
2. Contrast `c = e / (L² + L0²)`, with `L` the brightest block mean within three blocks
   and `L0` eight read-noise deviations.
3. A 64 px tile's contrast is the 75th percentile of its 16 blocks.
4. The subject's reference is the 90th percentile, over its tiles, of each tile's largest
   contrast in the frames at hand. A tile is in focus in a frame when its contrast is at
   least 0.2 of the reference.
5. A frame holds the subject when at least 3 tiles, and at least 0.05 % of the subject's,
   are in focus. The subject's range is the first to the last such frame.

Two faults were found and fixed on the way, both on the weevil (the rule above, in
`general.py`, is the fixed one):

- With the block's own level as divisor, blurred edges of a bright body against a black
  backdrop passed (56 tiles at the first plane): the blur spills gradient into dark
  blocks. The neighbourhood's brightest level is the fix.
- A straight-line noise fit put the dark-level noise at a fifth of its real value, so
  noise in black backdrop read as detail. A product implementation must take `n` from the
  engine's injected noise model (the Laplacian of four independent neighbours has 20
  times a photosite's variance), not fit its own.

### 2.3 Eight subjects

(`batch-stacks.py`, `general.py`; seven more A7CR stacks from `D:/StrehlCaptures`, read
only; subject from the engine's own outline where the capture has none.)

| Stack | Subject | Captured | In focus (narrow peaks) | Contrast rule, all planes | Contrast rule, 13 planes | Tiles in focus at the first, last plane |
| --- | --- | --- | --- | --- | --- | --- |
| 1795713444768 | dragonfly wings | 32,062 – 33,262 | 32,355 – 33,161 | 32,366 – 33,174 | 32,366 – 33,166 | 0, 0 |
| 1795460665629 | glitter weevil | 24,482 – 25,866 | 24,689 – 25,618 | 24,699 – 25,644 | 24,713 – 25,637 | 0, 0 |
| 1795300522964 | green scarab | 31,006 – 32,471 | 31,117 – 32,261 | 31,125 – 32,287 | 31,132 – 32,231 | 0, 0 |
| 1795433406862 | spotted planthopper | 30,564 – 31,910 | 30,768 – 31,727 | 30,704 – 31,754 | 30,784 – 31,684 | 0, 0 |
| 1795371396674 | patterned beetle | 15,718 – 16,522 | 15,824 – 16,397 | 15,833 – 16,418 | 15,853 – 16,388 | 0, 0 |
| 1795476520452 | weevil, close tile | 60,830 – 62,800 | past both ends | 60,830 – 62,800 | the same | 74, 114 |
| 1794786793543 | pale scales, frame-filling | 50,300 – 51,860 | past both ends | 50,300 – 51,860 | the same | 467, 258 |
| 1794689780304 | coin | 61,050 – 61,898 | past the first end | 61,050 – 61,898 | the same | 163, 33 |

- On the five stacks whose subject lies inside the capture, the rule's ends are within 64
  units of the narrow-peak ends with every plane, and within 43 with 13 planes (one sharp
  depth is 37 to 51 there).
- On the last three the rule reports tiles in focus at the end planes. Native crops of
  those tiles (`sheet.py`) show sharp scales at the first and at the last plane of the
  close tile and of the pale scales, and at the coin's first plane; the coin's last plane
  is within about a width of focus. The narrow-peak method cannot see these (it needs
  both sides of a peak), so there the rule is checked by eye only.
- Moving the rule's two numbers (the share from 0.1 to 0.4, the tile count from 0.05 % to
  0.2 %) moves an end by at most 64 units on four of the five, 145 on the fifth, and never
  puts a tile at an end plane (`robust.py`, A).
- What the engine's depth says on the same five (from `strehl subject`): dragonfly, the
  whole run; scarab and planthopper and patterned beetle, "sharpest at the first plane"
  with starts 111, 204 and 106 units early; weevil 95 early and 131 late.

Planes shot outside the in-focus range and half a sharp depth, on those five: 44 of 151,
60 of 199, 42 of 211, 35 of 136, 40 of 162. Between a fifth and a third of each capture.

### 2.4 Live view: read the peak, not the width

Rig, the dragonfly, light warm (`rig-series.py`, `live-sweep.py`): the camera's 1024 × 680
preview saved after every lens move.

| Sweep | Positions | Time | A position |
| --- | --- | --- | --- |
| 31,900 to 33,420, 20 apart | 77 | 89.8 s | 1.17 s (the move 0.83 s) |
| 29,500 to 35,580, 190 apart | 33 | 36.2 s | 1.10 s |
| the same, 2 s after the light came on | 33 | 35.9 s | 1.09 s |

On 32 px preview tiles (about 300 sensor pixels), gradient energy over the level squared,
smoothed over 40 units, each tile's peak located by a parabola through its three highest
samples:

| | Dense sweep | Wide sweep |
| --- | --- | --- |
| Width of a tile's curve at half height | 400 units | 570 units |
| Peak against the RAW focus of the same area, before any correction | −28 units | −33 units |
| After a constant +27: half the tiles within | 14 units | 17 units |
| 90 % within | 49 units | 45 units |
| Range of peaks that agree with their neighbours | 32,359 – 33,152 | **32,373 – 33,150** |
| The host's rule on the same frames (re-implemented from `bounds.rs`) | 32,120 – 33,220 | 31,780 – 34,250 |

The truth is 32,355 to 33,161. The owner's own sweep of the day before (33 positions over
their marks, read from the host's state) came back "clipped": the full range retained.

The −27 is optical, not a drift between days: reducing the stack's own planes to preview
size gives −26 (`sim-live.py`). Coarse detail peaks before fine detail on this lens. The
same simulation on all eight stacks: the offset is −9 to −42 units (a quarter to nine
tenths of a sharp depth, always the same sign); after it half the tiles are within 5 to
19 units and 90 % within 21 to 49 (144 on the coin, whose dots repeat). The sweep's range
starts 44 to 83 units late on the five inside stacks (a preview tile averages over the
nearest small features) and ends within 15 units, 44 on the scarab. Subject tiles whose
curve is still rising at an end position: 0 to 7 on those five; 16, 121 and 21 on the
three that run past.

Since the live sweep of the 27th and the stack of the 26th agree to 2 units after a power
cycle, the lens returns to a focus position across days to within a few units (MEASURED,
one case).

## 3. Highlights

### 3.1 What the capture took

(`highlights.py`, member 1 of every group.)

| | |
| --- | --- |
| Base frames (1.3 s): samples at the pin, a plane | median 126 thousand (3.5 R, 99 G, 23 B), every one inside the outline, at every plane from the first to the last |
| 64 px subject tiles holding a pinned sample | 2.1 % (1.6 to 3.7 %) a plane; 7.7 % at some plane |
| Highlight frames (1/40 s): samples at the pin | none in any of 76 |
| Their brightest sample | 0.43 of full scale (median), 0.89 (largest) |
| Highlights over the base full scale | 22 times (median plane), 45 times (largest): 5.5 stops above the pin |
| The body: green, 50 / 99 / 99.9 % of subject sites | 0.008 / 0.21 / 0.77 of full scale (`strehl survey`) |

The survey's advice on these frames (`advice`): a highlight pass with the base at 1.3 s
(the body's top at 0.8 of full scale) and groups at 1/100 s. The owner shot 1.3 s and
1/40 s, which held everything.

Pins are not local in depth here: the survey reports 113 to 144 thousand pinned sites in
the long frame at every one of 76 positions, most at the far, out-of-focus end. The
highlights' peak value is local (48 times full scale at 32,750, 6 times at 33,262); the
pinned area is not.

### 3.2 What the render did with them

From the owner's `render.log`:

> highlights : 0 planes fused …, 151 the base exposure alone; ratio inf--inf; 0 sites
> replaced or blended … hand-over not measured

with, for each plane, "its exposure ratio was refused: only 0 patches are well exposed in
both groups (need 12)". 304 of the capture's 952 RAWs, 9.4 GB and about ten of its 31
minutes went unused, and the picture's highlights are flat white with green and magenta
fringes.

The cause is in `fit_pair` (`crates/strehl-cli/src/highlight-fusion.rs`): a candidate
patch of 64 photosites must be below 0.70 of the pin everywhere in the base, and its
dimmest colour, divided by the ratio, must stand 12 noise deviations above the
companion's noise sample by sample. With a ratio of 51 that asks the whole patch for
about a fifth of full scale in its dimmest colour. A dark subject with small bright
highlights has no such patch. Later checks in the same function ask each patch for
texture 16 times the companion's noise, which a group five stops under cannot show
either.

The ratio is measurable all the same:

| Estimate | Result |
| --- | --- |
| Commanded, by third-stop shutter values | 50.80 |
| `strehl survey` on the same frames, per pair | 49.9 to 51.0 on 43 to 54 thousand cells each (−0.5 to +1.8 % of commanded) |
| Median of 8 × 8 block means, base 5 to 60 % of full scale (`highlights.py`) | 50.5 to 50.7 by colour; 2.1 to 2.4 % from plane to plane; standard error 0.01 to 0.02 |
| The same by brightness, 2 % to 60 % of full scale (the black-level control) | 50.2 to 51.2: no trend beyond 1 % |

Prototype (`patch-fusion.py`, applied to a worktree of `origin/main`, built as
`strehl 0.1.0-alpha.6 (b2c8a07aaa76-dirty)`, not installed): when the patch fit is refused
and `STREHL_HIGHLIGHT_RATIO=handover` is set, the ratio is the median of start × companion
/ base over the sites where the base's green is at 0.50 to 0.75 of the pin, bounded to
0.25 EV, two interleaved halves agreeing within 1 %. Rendered with the owner's settings
and a private cache:

> highlights : 151 planes fused (0 of them a demoted base group's member 1, 73 with a
> demoted highlight group's member 1), 0 the base exposure alone; ratio 49.103-53.051;
> 147777580 sites replaced or blended (103124808 with a pinned sample in their footprint,
> 0 of those not fully replaced; 0 near the companion's own pin) … 38.5 s

1 min 14 s for the whole render with its alignment. The per-plane ratio is wider here
(49.1 to 53.1) than the block estimate, because a plane without its own group borrows its
neighbour's, taken 8 units of focus away. The survey's cell estimator is the better one;
the hand-over sites are the right place to check it.

### 3.3 The picture after fusion

The fused render's own default look is nearly black outside the highlights. Its tone step
reports:

| | Without fusion (the owner's) | With fusion |
| --- | --- | --- |
| Subject sites set aside as highlights | 2.74 % (1.33 % pinned) | 1.52 % (0 % pinned) |
| Diffuse top (99.9th percentile of what is left) | 0.57 | 7.15 |
| White (linear) | 0.673 | 8.415 |
| Subject's median luminance placed at | 0.007 | 0.001 |

The step sets highlights aside chiefly by finding pinned samples. After fusion none is
pinned, the highlights count as the subject's diffuse top, and white goes 3.6 stops up.

Both linear masters through one identical display transform (white 0.673, one shoulder;
`fusion-same-tone.png`): the fused master shows the highlights in their own colour with
their folds, where the other has white patches with coloured fringes; everything else is
the same.

### 3.4 The highlight group's own check

In the fused render 73 of 151 highlight groups were "demoted" (only their member 1 used).
On the rig, 5 of 13 highlight groups failed the retake gate (local disagreement over 0.51
px at the 99th percentile) against 1 of 13 base groups taken 10 s earlier at the same
position; the check had 175 to 193 tiles to judge a highlight group by, against 3,200 for
a base group; and the highlight group registered against its base group within 0.2 px in
12 of 13 (`proofs.py`). The check is short of signal at five stops under, not seeing
motion.

## 4. Proof planes, the light, and stillness

(`rig-series.py`, `proofs.py`. A proof plane here is two test runs at the stack's sharpest
populated position, 32,734: a four-shot group at 1.3 s, then one at 1/40 s. Cold start:
the light had been off since the day before. Checked with `strehl-cli pixel-shift`.)

| After the light, s | Base group | Members' largest residual, px | Light level | Ratio | Picture against the first, px (x, y) |
| --- | --- | --- | --- | --- | --- |
| 0 | **retake** (local 0.53 px, limit 0.51) | 0.41 | 1.000 | 50.5 | 0, 0 |
| 30 | pass | 0.10 | 0.955 | 52.1 | +0.2, +0.3 |
| 60 | no retake (demoted) | 0.25 | 0.927 | 51.3 | +0.2, +1.9 |
| 100 | pass | 0.10 | 0.913 | 51.6 | +0.4, +3.6 |
| 140 | pass | 0.09 | 0.891 | 50.8 | +0.2, +4.0 |
| 190 | no retake (demoted) | 0.38 | 0.893 | 50.5 | +0.5, +4.2 |
| 250 | pass | 0.11 | 0.897 | 50.2 | +0.5, +5.6 |
| 320 | no retake (demoted) | 0.40 | 0.905 | 50.6 | +0.4, +5.8 |
| 400 | pass | 0.10 | 0.904 | 50.7 | +0.8, +5.9 |
| 500 | pass | 0.08 | 0.897 | 50.7 | +1.4, +6.0 |
| 620 | no retake (demoted) | 0.28 | 0.893 | 50.4 | +1.6, +6.1 |
| 760 | no retake (demoted) | 0.24 | 0.885 | 50.3 | +1.6, +5.8 |
| 910 | no retake (demoted) | 0.20 | 0.892 | 50.6 | +2.0, +7.9 |

- **The light.** Its output falls 10.9 % in the first 140 s and then holds within 1 %. The
  outlet's power reading moves 2 % and does not track it. A ratio measured between two
  groups 12 s apart reads up to 3 % high while the light is falling.
- **Drift.** 6 px along one axis in the first 250 s (1.9 px in the first minute), then
  about 0.1 px a minute; 2 px along the other over 15 minutes.
- **The check.** By the capture's own retake gate, one base group of 13 fails: the first,
  taken as the light came on. By the checker's stricter "demote" verdict, 7 of 13 do, with
  members 0.20 to 0.41 px off against 0.08 to 0.11 px for the ones that pass. The two
  populations do not overlap and do not follow the warm-up: the last three all fail it.
- **Time.** A base group as a test run takes 12.5 s and a highlight group 8.3 s (median
  of 13), each with its own approach and two-second settle.
- **At connection** the camera reported 1/40 s, the highlight groups' shutter, not the
  stack's 1.3 s, and the lens stood at 51,048, not in the stack's range. The battery
  reads null on this rig.

### 4.1 The second series: a still house, and an independent survey

(`rig-series-2.py`, 02:37 to 02:47 with the owner asleep; the light had been off 22
minutes after 15 on, so not fully cold.)

- **A sweep while the light warms.** The wide sweep begun 2 s after the light came on
  reads the same as one taken warm: per-tile peaks −35 and −33 units from the RAW focus
  before correction, half within 17 and 16 units after it, 90 % within 52 and 50. The
  sweep can use the light's settling time.
- **An independent survey.** 26 single RAWs at 1.3 s, 48 units apart over the stack's
  range, each its own test run: 7.3 s a RAW, 188 s in all. Read by the contrast rule:

  | | In focus from, to | Tiles in focus at the first, last frame |
  | --- | --- | --- |
  | All 26 frames | 32,350 – 33,166 | 0, 0 |
  | Every second (13) | 32,350 – 33,118 | 0, 0 |
  | The stack of the day before, every plane | 32,355 – 33,161 | |

  Tiles in focus at each position, tonight against the same position in the stack: 7
  against 4 at 32,350; 512 against 504 at 32,446; 1,134 against 1,121 at 32,734; 65
  against 71 at 33,118; 7 against 11 at 33,166; none in either before 32,350 or after
  33,166. The measure repeats across a day and two power cycles. The subject's mean level
  was 0.988 of the day before's (0.968 to 1.010 by position).
- **Thirteen more proof planes.** Members' largest residual 0.14 to 0.50 px; the
  checker passes 1 of 13 base groups and the capture's own gate would retake 4 of 13
  (two of them for a member half a photosite off, which the offsets then round the wrong
  way). With nobody walking the groups are no stiller than in the first series (6 of 13
  clean, 1 retake). Whatever moves the picture by a few tenths of a pixel between shots,
  it is not footsteps. The residual is one shift for the whole frame, so it is the rig or
  the camera, not the wing fluttering. Not resolved here.
- The light's level: 1.000 at 60 s, 0.974 at 150 s, then 0.966 to 0.981. The ratio: 50.1
  to 51.3. The picture: +4.0 px along one axis by 380 s, then still.

## 5. Smaller questions

| Question | Answer | Label |
| --- | --- | --- |
| The sharp depth against tile size (64 / 32 / 16 px) | dragonfly 45 / 43 / 40; weevil 44 / 42 / 41; scarab 37 / 35 / 32; planthopper 51 / 48 / 46; patterned beetle 37 / 36 / 35; close tile 98 / 90 / 80; pale scales 113 / 105 / 89; coin 88 / 82 / 71. Smaller tiles read 5 to 21 % narrower | MEASURED |
| The sharp depth as a rig fact | At lens positions 30,500 to 32,500 three subjects read 37, 45 and 51: a third apart. It must be measured on the subject | MEASURED |
| How short may the dense cluster be | The median width from 13 / 17 / 25 planes at the stack's spacing, against the whole stack: dragonfly 41 / 44 / 46 of 45; scarab 33 / 34 / 36 of 37; close tile 66 / 78 / 90 of 98; coin 43 / 56 / 68 of 88. A cluster must span four to five sharp depths or it reads low; at close focus 25 planes 8 apart do not | MEASURED |
| What coarser steps keep, from the stack's own tile curves | Amplitude kept at the worst tenth of tiles, by overlap (sharp depth / step): about 2.7: 0.90 to 0.95; about 1.8: 0.83 to 0.91; about 1.4: 0.79 to 0.86, across five subjects. The earlier render-measured curve reads 0.92, 0.87 and 0.84 there. The spread between subjects is larger than the curve's steps | MEASURED; the comparison DERIVED |
| Magnification through focus | −12.5 to −18.1 ppm a unit on eight stacks (`strehl subject`); the dragonfly's render kept 0.9862 of the field ("1.4 % of width dropped") over 1,200 units | MEASURED |
| A stop rule a capture could run | With a threshold from the planes seen so far, the far end would be found 44 to 124 units past the last in-focus plane on four stacks, saving 4 to 18 planes; the near end cannot be found this way | MEASURED (`robust.py`, B) |

## 6. What was not done

- No second subject was put on the rig. Everything about other subjects comes from their
  stacks; the live sweep on them is simulated from stack planes.
- The contrast rule and the peak rule exist as Python over extracted planes, not in the
  engine or the host.
- The fusion prototype has no tests and its estimator is not the one to ship (section
  3.2).
- Nothing was installed, committed or deployed. The rig was left as found: camera and
  light off, "manage power" on, approach 128, shutter and four-shot as at connection.
- The milestone ledger was not edited (see the brief).

### Left behind

- In scratch (`C:/strehl-scratch/plan-flow/`, 13 GB): the dragonfly's extracted planes,
  curves and per-tile maps (the mockups' pictures are drawn from them); the two rig
  series' records, plane-check reports and live-view frames; each other stack's
  `general.json` and per-tile maps; the fused render and its master
  (`dragonfly/render/`); the prototype build and its diff (`prototype/`).
- Deleted: the 78 test runs the rig series made in the receiver's folder (7.6 GB;
  `clean-test-runs.py`), the other seven stacks' extracted planes (`batch-stacks.py`
  rebuilds one in about a minute), the prototype's worktree and branch.
- The host's "latest capture" is now a test run, as after any test shot. A re-shoot pass
  into the dragonfly capture of the 26th is therefore no longer offered by the host.

## 7. Commands

```text
python scripts/extract.py  D:/StrehlCaptures/stack-1795713444768-14989 <scratch>/dragonfly/planes 12
python scripts/curves.py   <scratch>/dragonfly/planes <scratch>/dragonfly/curves 12
python scripts/truth.py    <scratch>/dragonfly/curves <run> <scratch>/dragonfly/truth
python scripts/narrow.py   <scratch>/dragonfly/curves <run> <scratch>/dragonfly/truth
python scripts/index.py    <scratch>/dragonfly/curves <scratch>/dragonfly/truth <scratch>/dragonfly/index.json
python scripts/highlights.py <scratch>/dragonfly/planes <run> <scratch>/dragonfly/highlights.json
python scripts/batch-stacks.py <scratch>/stacks <seven run names>
python scripts/general.py  <scratch>/<stack> <run>              (each of the eight)
python scripts/robust.py   <scratch>/<stack> ...
python scripts/sim-live.py <scratch>/<stack>
python scripts/rig-series.py   <scratch>/dragonfly/rig/series-1
python scripts/rig-series-2.py <scratch>/dragonfly/rig/series-2
python scripts/proofs.py   <scratch>/dragonfly/rig/series-N
python scripts/live-sweep.py <scratch>/dragonfly/rig/series-1 dense|wide <scratch>/dragonfly
python scripts/lenses.py   <scratch>/dragonfly <scratch>/dragonfly/lenses
strehl-cli subject <run> --width 56 --out … --mask-png …        (STREHL_CACHE_DIR private)
strehl-cli survey  <run> --json … --decodes 8
strehl-cli pixel-shift <test run> --json …
python scripts/patch-fusion.py C:/w/cpf ; cargo build --locked --release -p strehl-cli --bin strehl
STREHL_HIGHLIGHT_RATIO=handover STREHL_PIXEL_SHIFT=remosaic strehl stack <run> --merge pyramid --srgb --out … --linear-master …
```

`<scratch>` is `C:/strehl-scratch/plan-flow`; `<run>` is the dragonfly capture.
