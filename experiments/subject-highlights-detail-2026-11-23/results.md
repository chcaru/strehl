# Subject, highlights and detail: results (2026-11-23)

Author-run, not independently reviewed. Questions and controls are in
[brief.md](brief.md); the plan built on these numbers is
[docs/proposals/2026-11-subject-highlights-and-detail-plan.md](../../docs/proposals/2026-11-subject-highlights-and-detail-plan.md).

Labels: MEASURED (a command in this folder produced the number), VERIFIED
(checked against an independent result), DERIVED (arithmetic on measured
numbers), ARGUED, UNVERIFIED.

## Inputs and build

- Weevil, A7CR four-shot: `D:/StrehlCaptures/stack-1795460665629-8651`
  (199 planes, step 7, ISO 100, 1/4 s, 205 groups with retakes).
- Scarab, A7CR four-shot: `D:/StrehlCaptures/stack-1795300522964-6430`
  (211 planes, step 7, ISO 100, 1/10 s).
- Weevil, A7C II single shot: `D:/personal/macro/insects/bug-3/107MSDCF`
  (299 frames), read only through its render log and render.
- Rig series taken for this brief: 55 single-plane test runs and 30 live-view
  frames, listed in [rig-index.json](rig-index.json) (folders
  `D:/StrehlCaptures/stack-17954668…` to `stack-17954676…`, all
  `capture_kind` "test"). Script: [rig-series.py](rig-series.py).
- Engine: a copy of the installed build `desktop-c30cb075f79533d0`
  (`strehl-cli.exe`), `STREHL_PIXEL_SHIFT=remosaic`, private
  `STREHL_CACHE_DIR`. Control: the default re-render of the weevil is
  byte-identical to the owner's `result.tiff` (VERIFIED, `numpy.array_equal`).
- Pictures and arrays are in `C:/strehl-scratch/i-round/` and are not part of
  the repository. Text outputs of the three longest analyses are in
  [evidence/](evidence/).

Rig state afterwards (VERIFIED by powering the camera on once more): ISO 100,
1/4 s, f/5.6, four-shot; "manage power" on; plan 24482-25866 step 7 as before;
camera and light off. The focus marks read "not set", which is what any camera
power cycle does.

## Q1. What clips, and what the exposure advice sees

`extract-planes.py`, `clip-summary.py`, `meter-compare.py`. Levels are shares
of black to the 16383 pin; member 1 of each plane.

| | Weevil (1/4 s) | Scarab (1/10 s) |
| --- | --- | --- |
| Green 99.9th percentile over the planes | 0.114 to 0.160 | 0.62 to 1.00 |
| Planes with any pinned green sample | 119 of 199 | 208 of 211 |
| Pinned green samples per plane, median / most | 15 / 125 | 26,592 / 33,779 |
| Brightest green sample far from focus | 0.15 to 0.20 (planes 0-20 and 175-198) | 0.955 (plane 0) |

All MEASURED. What the product's rule (pooled colours, whole frame, 99.9th
percentile to 0.9, one test shot) would ask for, from the same samples:

| Plane metered | Product's number | Stops it would add | Green pinned in the subject at the capture's own shutter |
| --- | --- | --- | --- |
| Weevil 0 (out of focus) | 0.111 | +3.0 | none |
| Weevil 100 | 0.135 | +2.7 | 75 samples |
| Weevil 140 | 0.143 | +2.7 | 134 samples |
| Scarab 0 (out of focus) | 0.503 | +0.8 | none |
| Scarab 108 | 0.617 | +0.5 | 27,157 samples, 0.21 % of the subject's green |
| Scarab 162 | 0.712 | +0.3 | 32,824 samples, 0.25 % |

Three things hide the highlights from the rule, each MEASURED above:

- Pooling red, green and blue. Scarab plane 162: pooled 0.712, green 1.000.
- One focus position. See Q2.
- A percentile. On the weevil the pinned samples are 0.0004 % of the frame;
  the rule looks at the brightest 0.1 %, and its "the test shot clipped" limit
  is 0.01 % of samples.

Metering inside the subject mask instead of the whole frame raises the
weevil's 99.99th percentile from 0.193 to 0.263 (plane 100) and from 0.242 to
0.350 (plane 140); the backdrop is 65 % of the frame.

## Q2. A glint is only bright near its own focus

`glint-focus.py`, block peaks (8x8 px) over their 3x3 neighbourhood, planes
not registered. MEASURED.

| Planes from the glint's brightest plane | Weevil: median peak | Scarab: median peak |
| --- | --- | --- |
| 0 | pinned | pinned |
| 2 before | 0.75 | 0.91 |
| 5 before | 0.45 | 0.76 |
| 10 before | 0.23 | 0.59 |
| 20 before | 0.12 | 0.41 |
| 40 before | 0.07 | 0.24 |

- Weevil: 4,745 separate glints reach 0.9 of full scale somewhere in the
  stack; a glint stays pinned for a median of 4 planes (90th percentile 10).
- Scarab: 8,211 separate bright regions; pinned for a median of 21 planes
  (its highlights are broad reflections, not points).
- So a test shot ten planes (70 focus units) from a weevil glint sees it at a
  quarter of a peak that is itself only a lower bound.

## Q3. How bright the weevil's glints are

`ladder.py` on the shutter ladder at planes 70, 100 and 140 (positions 24972,
25182, 25462): 1.3 s, 1/4 s (first and last), 1/15, 1/60, 1/250, 1/1000 s.
Full output: [evidence/ladder.txt](evidence/ladder.txt). MEASURED.

| Shutter | Sites with a pinned sample in the subject (three planes) | Share of the subject |
| --- | --- | --- |
| 1.3 s (what the advice would roughly choose; its own answer is 1.6 s, DERIVED) | 14,697 / 11,999 / 20,560 | 0.055 to 0.095 % |
| 1/4 s (the owner's) | 142 / 161 / 279 | 0.0007 to 0.0013 % |
| 1/15 s | 0 / 2 / 0 | none |
| 1/60 s and shorter | 0 | none |

Radiance of the glints in units of the 1/4 s full scale, read from the longest
rung in which a 9x9 window is unpinned and scaled by measured exposure ratios:

- 28, 39 and 47 separate regions per plane exceed the 1/4 s full scale.
- Their peaks: median 1.3 to 1.4, 90th percentile 2.1 to 2.8, largest 2.5,
  5.2 and 3.7. Nothing reaches 8; no site was still pinned at the shortest
  shutter.
- DERIVED: against a 1.3 s exposure the brightest glint is about 26 times
  full scale (4.7 stops). One short group five stops under the body exposure
  holds every glint seen here.

Exposure ratios (control). Measured against 1/4 s on green block means: 1.3 s
5.04 (nominal 5.2), 1/15 s 0.238 (0.267), 1/60 s 0.0625 (0.0667), 1/250 s
0.0150 (0.0160), and the repeated 1/4 s 0.945. Sony's marked times are
rounded (1/15 is 1/16 s, 1.3 is 1.26 s: DERIVED from the camera's third-stop
series), which explains all but about 5 %; the rest is the light moving
between groups. Members of one group differ by 0.1 to 7.5 % in level
(largest at 1/1000 s and once at 1.3 s). A fusion must measure its ratio.

## Q4. Fusing a long and a short group of one plane

`hdr-fuse.py`, plane 100, long 1.3 s, short 1/15 s, a 1536 x 1024 px window
with the most glints. MEASURED.

- Shift between the two groups (taken 40 s apart, separate approaches):
  0.15, 0.30 px.
- Exposure ratio 20.23 / 20.17 / 20.21 for red, green, blue.
- 2.3 % of the window's sites take the short group; 5,492 were pinned in the
  long group and none in the short one.
- Hand-over check on green at 50-75 % of the pin: scaled short over long
  0.9991, spread 2.5 % (noise).
- Fused peak 13.7 times the long group's pin.
- Control: fusing the long group with itself divided by 16 returns it within
  0.001 DN.
- With the 1/60 s group as the short one: ratio 79.1, hand-over 0.975,
  spread 4.0 %. Its shift was 0.16, 0.75 px.

By eye (4x crops in scratch): the long group alone turns the glints into pale
blobs; the fused plane keeps their colours. The difference is modest in a
single plane and was not judged on a finished stack (UNVERIFIED there).

## Q5. Time

`timing.py` in scratch over the test runs' journals. MEASURED.

| | Camera seconds per group |
| --- | --- |
| Four shots at 1.3 s | 8.14 |
| Four shots at 1/4 s | 4.27 (38 groups, 4.20 to 4.34) |
| Four shots at 1/15 s | 3.81 |
| Four shots at 1/60 to 1/1000 s | 3.62 to 3.65 |
| One shot at 1/60 s | 1.66 |

- Changing the shutter: 0.23 to 0.46 s. Switching four-shot to single and
  back: 0.23 s each.
- The owner's capture ran at 6.28 s a group (205 groups in 1,286.5 s, settle
  2 s).
- With "manage power" on, every run waits the light warm-up again (60 s on
  this rig) even when the light is already on. A test shot took 70 s; with
  manage power off, 10 s.
- DERIVED for the weevil's 199 planes: today 20.8 min; body exposure 1.3 s
  33.7 min; plus a four-shot highlight group on every plane 47 min, on every
  second plane 40.5 min; with a single-shot highlight frame on every plane
  42 min.

## Q6. Revisiting a plane

`sweep.py`, [evidence/sweep.txt](evidence/sweep.txt). MEASURED.

- Six revisits of position 25182, ten seconds apart, each after its own
  approach: shifts against a reference group between 0.33 and 0.83 px, moving
  by 0.07 to 0.56 px from one revisit to the next.
- A group taken 7.6 minutes before that reference, four minutes after the
  light came on: 1.2, 2.7 px away. The light draws 178 W; the drift after it
  switches on is the likely cause (ARGUED).
- Focus: the revisits' 0.3-0.4 cycles/px power is 0.986 to 1.054 of the
  reference, where 2 focus units change it by about 4 %. A revisit lands
  within about 2 units.
- Within one group the engine's own check read 0.15 px.

## Q7. The stack against its own sharpest plane, and the lens

Stack against plane: `stack-vs-plane.py`,
[evidence/stack-vs-plane.txt](evidence/stack-vs-plane.txt). Signal is the
cross-spectrum of two views that share the scene and not the noise: the odd
and even half-stacks; two revisit groups of plane 100 rendered by the same
engine. 40 tiles of 256 px where plane 100 is the sharpest over 37-77 % of
the tile (the rest of each tile favours the stack). MEASURED.

| Band, cycles/px | Half-stack signal power over the plane's | Signal over noise power: plane, half-stack |
| --- | --- | --- |
| 0.20-0.30 | 1.13 | 123, 95 |
| 0.30-0.40 | 1.23 | 22.6, 29.7 |
| 0.40-0.50 | 1.59 | 5.0, 8.5 |

- The stack keeps what its sharpest plane has. The merge is not where the
  detail goes. (Its log's "61.5 % of the finest band averaged" does not show
  as a loss on these tiles.)
- One plane at 1/4 s has a signal-to-noise power of 5 in the top band. The
  capture is 2.4 stops under what the body could take.

Focus step (`sweep.py`, 24 tiles of 512 px, step 2 over 48 units): a plane
3.5 units from a tile's best focus keeps 0.88 of the 0.3-0.4 band's power and
0.84 of the 0.4-0.5 band's (0.94 and 0.91 in amplitude). Tiles this large mix
depths, so this is a bound, not a curve. Step 7 is not the problem.

Glint widths (`glint-psf.py`, unpinned 1/60 s and 1/15 s groups, Gaussian
fits on isolated glints): the narrowest twentieth have a full width at half
height of 1.9 to 2.0 px (narrow axis 1.7), with no preferred direction.
DERIVED for a perfect lens at the cutoff the other stacks fitted (0.768
cycles/px) with a 1 px photosite: 1.46 px. A glint is not a point, so the
lens's spread is at most 1.9 px. The optics are close to their limit; there
is no sign of motion blur.

Framing: the weevil spans the same 25 mm of sensor in both cameras' renders
(about 6,790 px on the A7CR and 4,900 px on the A7C II, read off 1,800 px
previews, so good to a few per cent). One
pronotum scale is about 11 px wide on the A7CR and 8 px on the A7C II.

## Q8. Restoration

- Not applied to the weevil. Its log: "the diffraction cutoff is not
  measurable on this stack (the one-aperture fit … ran to its ceiling: green
  0.900 cycles/px)". It was applied to the scarab, the harlequin beetle and
  the lanternfly (fitted green cutoffs 0.740, 0.768, 0.776). MEASURED from
  the owner's render logs.
- With the cutoff supplied (`STREHL_OPTICAL_RESTORE_CUTOFF=0.685,0.768,0.884`)
  the weevil renders restored. Against the unrestored half-stack, same tiles
  as Q7 (MEASURED):

| Target (Gaussian sigma) | Amplitude at 0.2-0.3 / 0.3-0.4 / 0.4-0.5 | Noise power at the same bands | Signal over noise |
| --- | --- | --- | --- |
| 0.70 px (shipped) | 0.97 / 0.83 / 0.66 | 0.90 / 0.59 / 0.30 | unchanged |
| 0.50 px | 1.27 / 1.33 / 1.32 | 1.59 / 1.74 / 1.63 | unchanged |
| 0.40 px | 1.40 / 1.62 / 1.82 | 1.98 / 2.67 / 3.27 | unchanged |

- The shipped target lowers the top two bands on this lens setting. Its own
  log lines say so on the three stacks where it ran ("system -> restored MTF
  at 0.4: 0.28 -> 0.21"). The target was set when the fitted cutoff was 0.62;
  at 0.74 to 0.78 the lens already delivers more than the target asks for.
- A linear filter cannot change signal over noise in a band; these arms trade
  crispness for grain. More light changes the trade.
- By eye (2x crops of the pronotum in scratch): 0.50 and 0.40 are crisper
  than the owner's render; 0.40 shows more grain.
- The highlight guard kept restoration off 1.8 % of the frame.
- Restoration takes about 150 s on a half-stack render and did not finish in
  ten minutes on a one-plane input (not investigated).

## Q9. Finding the subject automatically

`subject-mask.py` on the per-plane summaries; `live-mask.py` on live-view
frames. MEASURED.

- Weevil, all 199 planes: one part, 35.6 % of the frame. Laid over the
  owner's render it follows legs, tarsi, antennae and hairs.
- Fewer planes: 25, 13 and 7 planes give an intersection-over-union of 0.98
  with the all-planes mask; the outline lies within 8 px (median) and
  16 to 22 px (95th percentile) of it.
- Sensitivity: twice and four times the default threshold give 0.97 and 0.94.
  Below the quiet population's spread the mask floods the frame, which is why
  the threshold is set against the frame's own quiet blocks.
- Scarab: focus evidence alone leaves the dark, smooth flank out. With the
  growth step (weaker evidence counts where it touches the sure subject) the
  mask is one silhouette plus the detached leg.
- Live view only (30 frames of 1024 x 680, no RAW): finds the weevil with a
  loose margin, 45 % of the frame against 35 %; 0.85 against the RAW mask.
  Eight frames give the same.
- Live view shows the active area: live pixel (x, y) is sensor pixel
  (9.285 x + 34, 9.303 y + 31) of the 9564 x 6376 visible frame, a field of
  100.0 % by 99.8 % (correlation 0.982).
- Where the subject is in focus: weevil planes 30 to 163 of 0 to 198 (99.8 %
  of subject blocks between 34 and 162); scarab 9 to 190 of 0 to 210 (20 to
  179). DERIVED: no subject block is sharpest in 65 of the weevil's 199 planes
  (33 %) and 29 of the scarab's 211 (14 %); outside the range that holds
  99.8 % of blocks it is 35 % and 24 %. Blocks are 8 px and a three-plane mean
  was used, so fine tips may reach a few planes further.

## Q10. Not measured

- The sharp width inside the mask against the whole frame. The product's
  measure already skips tiles without a focus peak; the sweep here was too
  short (48 units) to give a width.
- A finished stack with highlight groups. The host cannot change exposure
  inside a run, so no such capture exists yet.
- Single-shot highlight frames: one was taken beside its four-shot twin
  (`stack-1795467615919-8651` and `stack-1795467606459-8651`), not compared.
- Why the weevil's cutoff fit failed. Glints and the low exposure are both
  candidates.
