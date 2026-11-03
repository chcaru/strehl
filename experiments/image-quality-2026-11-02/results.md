# Image-quality improvements

Owner request (2026-11-02): "try way harder to find image quality improvements
... think way outside the box and come up with novel solutions", with the
standing rule from the same day: always ensure improvement and no regression.
Allocation `image-quality-2026-11-02`.

Host: Windows 11, 16 cores / 32 threads, 64 GB. Release builds of the working
tree on `codex/pr-3-local-2026-10-31`. Every arm of a comparison shares one
isolated warp map (`STREHL_WARPMAP`) so geometry is identical. Capture folders
were only read; half-stack and burst inputs are hard links in `D:\codex-work`.

## Instruments, and how each can fail

* `compare.py` -- reference-free tile statistics (high-pass luma, high-pass
  chroma, Laplacian luma) on flat and edge tiles classified from arm A. Can be
  fooled: high-pass energy rises with noise as well as detail. Used for
  orientation only.
* `halfnoise.py` -- noise of a render from two separately aligned half stacks,
  patch-registered, against two adjacent single frames. Residual texture after
  registration inflates the half-stack figure, so it can only understate a gain.
* `replicates.py` -- the main real-data instrument. `STREHL_FRAME_PARITY=even|odd`
  (experiment-only, in `merge_cmd.rs`) folds every other frame **under the
  whole stack's warp map**, so the two half renders are pixel-aligned
  replicates. In linear luma per tile: texture power = cross-covariance of the
  halves (independent noise cancels, common scene remains), noise power = half
  the variance of their difference. Binned by texture SNR. Can be fooled:
  selection bias that is the same in both halves (a selector picks the frame
  whose noise adds to the shared signal) counts as texture, so a selector's
  weak-texture power is *inflated* and a lower figure is not by itself a loss.
* `truth-score.py` -- error power against truth. Truth is the plain mean of 24
  held-out frames of a fixed-focus ISO 640 burst
  (`requests/12-...-repeat-diff-light`, DSC00456-487, one light); arms merge
  disjoint subsets (frames 0-3, 0-7) under the same warp map. Scored on the
  scene-linear `--linear-master` so the image-dependent SDR tone anchors cannot
  enter. Truth noise adds the same constant to every arm.
* `synth-stack.py` + `synth-merge/` -- truth-referenced synthetic focus stacks
  folded by the **production** `BandMerge` (standalone crate linked by path).
  Truth is the burst mean (real texture); depth maps flat / tilt / step
  (occluder); Gaussian defocus growing 0.8 px per frame from focus; Poisson-
  Gaussian noise; contrast 1 and 0.3; N = 6, 22, 60; one smooth third. Each
  frame also gets a null probe, as the CLI supplies. The harness was itself
  caught out once (it never called `FrameWorkspace::next_frame`, so every frame
  reused frame 0's plane pyramids); fixed and checked with an identity stack
  that reproduces its input exactly.
* `crops.py` -- 1:1 or integer nearest-neighbour crops, same `>> 8` transform
  for every arm.

## 1. The default merge keeps single-frame noise where it should average (FIXED)

**Finding (MEASURED).** On `bee-3-cpl` (299 frames, ISO 100) the white
background of a 150-frame half stack carries 1.11x the luma noise of a single
frame (`halfnoise.py`, five flat patches, median), where averaging would give
1/sqrt(150) = 0.08x. The record already had the mechanism at band 0 on
`coffee-bean` -- "one frame cleared the gate and the rest did not"
(`pyramid.rs`, significance note) -- but no fix: the significance scaling acts
on weights, downstream of the gate.

**Cause (DERIVED, then MEASURED).** The noise gate is a per-frame test. A
smoothed band energy of pure noise exceeds 2x its expectation with probability
~1.5% (white noise) to several percent (warped frames, whose noise is spatially
correlated by the resampler and demosaic: measured effective degrees of freedom
9-10 at bands 0-3 against the white 13.4). Over 150-300 frames some frame
clears it at almost every coefficient, and that frame is then selected: the
multiple-comparisons problem. The selected frame is the one whose noise is
largest, so the result is not merely single-frame noise but amplified.

**Change: the ensemble gate** (`pyramid.rs`, `MergeConfig::ensemble`, default
on, `STREHL_PYRAMID_ENSEMBLE=0` disables). Per selected band and coefficient
the fold also keeps, over frames: the maximum and sum of band energy in each
frame's own noise units, and the sums of the luma coefficient and of its raw
smoothed energy (4 extra floats per coefficient-level). At finish a coefficient
keeps its ordinary soft-power selection only where the stack as a whole shows
signal, and otherwise ramps to the plain mean of all frames. Signal is any of:

* **dominance** -- strongest frame's energy over the mean of the *other*
  frames (detail sharp in one or a few frames);
* **coherence** -- `smooth5((sum L)^2) / sum smooth5(L^2)`: signal shared by
  `m` frames adds coherently (~`m`), independent noise does not (~1). Also over
  a 15x15 box for weak detail spread over an area. Needs no noise model; catches
  weak detail seen by many frames that no single frame's energy shows;
* **typical level** -- the other frames' mean energy above 2-4x the modelled
  noise (structure everywhere, e.g. coarse bands across focus).

**The thresholds are measured, not assumed.** The CLI's floor probe already
pushes independent synthetic noise through each frame's actual warp and
pyramid. Those probe bands are folded into a second, noise-only set of the same
accumulators over a central window (up to 512x512) of each band, and each
statistic's thresholds are percentiles of its measured null (99th to 99.9th).
Where a window is too small to read a percentile directly, the highest
supported percentile is read and carried up by the parametric model's ratio, so
the measured scale is always used. Unwarped frames (no probe) use the
parametric model. Each render reports, per band, the fraction averaged, the
mean selection and whether its null was measured.

Two earlier forms were tried and rejected on evidence, which is why it has
this shape: (a) dominance alone averaged weak paint texture on `109MSDCF`
(22 frames; mid-band texture 0.6-0.76x) -- coherence fixes that; (b) a
moment-matched chi-square null fired on 22-35% of pure-noise coefficients
instead of the nominal 10% (the tail shape matters for a max-of-N statistic) --
measured nulls fix that (unit-test noise: 0.92 -> at the plain-mean level).
A first version also averaged coarse bands across focus and lifted the bee's
dark legs; the typical-level test fixes that (tone map flat at +-80 DN).

### Evidence (shipped default unless stated)

**Truth, synthetic (production `BandMerge`).** `synth-summary.py` over
`synth-q99.txt`: the gate's error power against truth is lower than the
default's in **176 of 180** band/region cells. Fine-band smooth regions
0.03-0.72x; weak texture 0.04-0.39x; strong texture lower in every cell. The
four worse cells are all the **coarse band at the occluder boundary** of the
step scene, at most **+1.9%**.

**Truth, real fixed-focus burst** (error power, 8 frames; 4 frames same sign):

| arm | fine flat | fine textured | mid flat | mid textured | coarse flat |
| --- | --- | --- | --- | --- | --- |
| default | 2.650e-7 | 3.724e-4 | 1.238e-7 | 6.796e-5 | 3.923e-8 |
| ensemble gate | 2.061e-7 | 3.724e-4 | 0.934e-7 | 6.795e-5 | 3.207e-8 |
| plain mean (ideal here) | 1.957e-7 | 3.645e-4 | 0.847e-7 | 6.380e-5 | 1.561e-8 |

**Replicates, real stacks** (`run-replicates.sh`; noise / texture power,
gate over default; the earlier stricter ramp in brackets where it was run):

| subject (frames) | noise-only tiles, fine | weak texture (SNR 0.3-3) | textured | dark tiles |
| --- | --- | --- | --- | --- |
| bee-3-cpl (299) | 0.050 [0.016] | 0.99 fine, 0.96-0.98 mid [0.97, 0.93] | 1.008 | 0.82 |
| coffee-bean (105) | 0.027 [0.020] | 1.000 fine; 0.73-0.87 mid on 113 tiles | 1.001 | unchanged |
| razor, black ground (279) | -- | -- | 1.000 | **0.055** [same] |
| 109MSDCF (22) | 0.65 [q99.9] | 1.00 fine, 0.86-0.94 mid [q99.9] | 1.004 | 0.90 |
| wrapped-text-1 (130) | 0.48 | **0.97 fine, 0.92 mid** [0.91, 0.82] | 1.000 | -- |
| foam (100) | -- | 0.998 | 1.000 | 0.91 |
| bug-4 104MSDCF (299) | -- | -- | 1.000 | 1.000 |

The weak-texture figures below 1 cannot be read as loss on their own (see the
instrument's failure direction): on the burst, where truth exists, the gate is
at or below the default's error in textured tiles. On `wrapped-text-1` (paper
fibres) by eye the paper granules are a touch softer with the stricter ramp;
whether that is detail or removed selection inflation is **UNRESOLVED**, and it
is why the shipped ramp is the conservative 99/99.9 rather than 99.9/99.99,
which scored better against truth on every truth-referenced test.

**Controls.** With the gate off the output is byte-identical to the previous
default (`109MSDCF` half stack, burst 0-7). Unit tests in `pyramid.rs`: pure
noise is averaged (and the per-frame gate is shown to select it); detail in one
frame kept; weak detail in 12 of 60 frames kept; chunked absorb equals one fold;
thresholds deterministic and ordered; a sparse null keeps its measured scale.
Mutation-checked: forcing selection fails the noise test, removing dominance
fails the one-frame test, removing coherence fails the subset test. All 748
`strehl-core` unit tests pass with the gate on by default. Tone change
(31x31 low-pass) is a global auto-tone anchor shift of tens of DN, no structure.

**Cost.** See section 4.

### Not covered

Multi-pass *Best result* sessions use their own fusion operators
(`session-fusion.rs`) and do not get the gate; single-pass sessions delegate to
the ordinary stack and do. In a fixed-focus burst (and plateau-like parts of
any stack) every frame holds the same detail, coherence fires, and selection is
kept although averaging equal frames would be optimal: a frame-agreement test
is the natural next step, with its own risk for weak detail seen by a subset.

## 1b. Halo and glow around edges: pooled evidence and a weighted base (FIXED, 2026-11-03)

Owner report: haloing/ghosting around edges and fine structure, on the
calibration slides and the bee.

**Finding (MEASURED).** On `requests/misc-diagnostic/high-res-calibration-slide-2-cpl`
(299 frames, tilted backlit slide) every bright bar sits in a grey glow and the
black chrome is lifted. The frame in focus at that place shows near-black chrome
(`slide2/cmp-1700-5300-400.png`). On the *flat* slide (`flat-et2.5s`, 60
frames) the stack adds no glow over its in-focus frame (0.92% vs 0.95% of bright
level within 40 px of edges): the effect needs depth variation and many frames
far from focus.

**Instrument.** `localref.py`: a composite of 100 single-frame renders (every
third frame, `STREHL_FRAME_PARITY=i-i`, same warp map), taking per 64 px tile the
frame with the most high-pass energy -- on a planar subject each tile is an
in-focus observation including the lens's own veiling glare and no merge. Dark
ground is binned by distance to bright pixels; arm mean / composite mean.

**Cause (ARGUED, then tested).** Coarse bands select on their own energy, which
barely depends on focus: a defocused frame's blur spreads a bright bar's light,
keeping or raising coarse energy in the dark beside it. The base band was the
plain mean of every frame, i.e. of every defocus state.

**Change.** (a) *Pooled evidence* (`MergeConfig::pooled_evidence`, default on,
`STREHL_PYRAMID_POOLED_EVIDENCE=0` disables): every band selects on the mean of
its own and every finer band's energy, each in its own noise units, the finer
ones reduced onto its grid; floor, gate and exponents unchanged. (b) The base
band is *weighted* by the coarsest band's selection (`--pyramid-base weighted`,
now the default), and inherits that band's ensemble-gate blend, so it is the
plain mean only where the coarsest band is noise.

| slide-2 dark ground vs composite | 2-8 px | 8-16 | 16-32 | 32-64 | 64-128 | 128-256 | mean excess |
| --- | --- | --- | --- | --- | --- | --- | --- |
| previous default | 1.14 | 1.34 | 1.41 | 1.47 | 1.30 | 1.28 | +35% |
| weighted base only | 1.01 | 1.20 | 1.30 | 1.24 | 1.07 | 0.86 | +21% |
| pooled (cumulative) only | 1.11 | 1.30 | 1.37 | 1.42 | 1.29 | 1.26 | +31% |
| **pooled + weighted (shipped)** | 0.90 | 1.10 | 1.27 | 1.23 | 1.02 | 0.86 | **+14.5%** |
| finer-only + weighted (rejected) | 0.82 | 1.05 | 1.25 | 1.21 | 0.99 | 0.85 | +11% |

**The remaining 16-64 px "glow" is the tone curve, not the merge (MEASURED,
2026-11-03).** The table above scores 16-bit sRGB renders, and each render, including
every single-frame render in the composite, sets its own tone anchors.
`localref-linear.py` rebuilds the composite from scene-linear single-frame masters
(100 frames, every third, streamed and deleted) and scores linear masters (dark =
composite 9x9 mean below 5% of its 99.5th percentile, 32% of pixels):

| slide-2, scene-linear | 2-8 px | 8-16 | 16-32 | 32-64 | 64-128 |
| --- | --- | --- | --- | --- | --- |
| previous default (pooled off, mean base, exponent 2) | 1.16 | 1.08 | 1.04 | 1.05 | 1.08 |
| current default (pooled, weighted base, exponent 4) | 0.96 | 0.93 | 0.94 | 0.94 | 0.93 |

The current merge has no excess that falls off with distance from bright detail; it
sits ~6% below the composite everywhere. Turning the ensemble gate off does not change
the sRGB scores either (identical to two decimals). Glow is closed on this subject;
use linear masters for any further glow measurement.

**Truth.** Synthetic stacks (`synth-arms.py`, production `BandMerge`, 120 cells):
pooled + weighted is worse than the previous default in **0 of 120** cells
(geometric-mean error 0.852); *finer-only* evidence, which looked slightly better
on the slide, is worse in 40 of 120 (coarse strong texture up to 3.5x) and was
rejected; the weighted base alone is neutral (0.986). Burst truth (8 frames):
coarse-flat error 3.21e-8 -> 2.24e-8, every other cell within 0.03%.

**Bee (MEASURED by eye, then attributed).** Pooled + weighted removes most of the
light hairs that the previous default drew across the dark legs. Single-frame
renders show those hairs sharp only at frames ~140, behind the leg (in focus at
~frame 100, where the leg is solid dark): they were see-through ghosts. The
antenna ghost (background hair inside the near antenna) is *not* fixed; see
section 3.

**Unit test.** `pooled_evidence_and_a_weighted_base_remove_the_glow_around_bright_detail`:
41 frames, two depths, bright bars on dark: glow 9.5 -> 2.0 DN, bar-level error
66 -> 33 DN against truth. Mutation-checked: without pooled evidence the bar
error fails; without the weighted base the glow fails. Hull tests keep their
excursion-producing plants on `legacy_merge()` (the new merge does not overshoot
on them); registered research configs (m194d, known-scene benchmark, temporal
energy, common-stack) are pinned to the previous merge.

**Replicates, scene-linear masters** (`run-replicates-linear.sh`; arm A = the
previous default: gate on, `STREHL_PYRAMID_POOLED_EVIDENCE=0 --pyramid-base
mean`; B = shipped). Linear masters, because the SDR tone anchors move with the
base band and scaled texture and noise together by ~0.97 on sRGB replicates.

| subject | texture power B/A (bins with SNR >= 0.3) | noise power B/A |
| --- | --- | --- |
| bee-3-cpl | 1.000-1.010 | 1.000-1.013 |
| 109MSDCF | 0.997-1.006 | 0.995-1.005 |
| coffee-bean | 0.996-1.032 | 1.001-1.035; **1.093** in 1023 weak mid tiles |
| wrapped-text-1 | 0.972-1.008 (0.97 on 12 tiles) | 0.96-1.013 |
| bug-4 104MSDCF | 1.002-1.018 | 1.002-1.012 |
| garnet | 1.002-1.018 | 1.002-1.018 |

Cost disclosed: where coarse bands used to average defocused frames, they now
select in-focus ones, so a little low-SNR noise comes back (coffee-bean mid band,
up to +9% power, ~4.5% amplitude, in weak tiles). Truth tests favour the change
overall; the noise is the price of the glow.

**Sessions (MEASURED; not enabled).** Session fusion (Best result) has its own
coefficient consumer. It now implements pooled evidence and the weighted base, and
`pooled_evidence_and_weighted_base_match_the_ordinary_merge` pins it to the
ordinary merge (six sources, each its own group, max difference < 0.01). The parity
test failed by 2.4 DN until the noise unit carried the ordinary merge's
`.max(1.0)` clamp. Enabled on `insects/bug-4` (1231 frames, 6880x4584 master),
against the previous commit's binary on the same alignment cache, it made
dark-ground noise ~3% RMS higher (green high-pass 0.842e-4 -> 0.866e-4 at 3 px,
1.560e-4 -> 1.615e-4 at 33 px) and the black level ~10% higher, with no glow
reduction (dark ground new/old 1.02-1.04 at every distance from bright
pixels). Session fusion has no ensemble gate, and without it the two select
noise in flat dark ground. Sessions keep the previous selection
(`session-cmd.rs`) until the gate is ported.

## 1d. A sharper coarse exponent now that coarse bands see focus (SHIPPED, 2026-11-03)

**Hypothesis (ARGUED).** The coarsest-band exponent of 2 was chosen when coarse bands
selected on their own energy, which barely depends on focus; soft selection there limited
the damage of a wrong pick. With pooled evidence (§1b) a coarse band selects on its finer
bands' focus evidence, so soft selection now just averages defocused frames back in.

**Synthetic truth (MEASURED;** `synth-merge` with `SYNTH_EXPONENT`, 12 scenes x 10 cells,
pooled + weighted base + ensemble gate in every arm; reference arm exponent 2):

| coarse exponent | cells worse | worst cell | geo-mean error ratio |
| --- | --- | --- | --- |
| 3 | 12/120 | 1.022 (flat N22 coarse smooth) | 0.947 |
| **4 (shipped)** | 10/120 | 1.037 (flat N22 coarse smooth) | **0.930** |
| 6 | 10/120 | 1.041 | 0.923 |
| 8 | 9/120 | 1.041 | 0.921 |
| 3, sharpen 1.2 | 20/120 | 1.025 (mid strong texture) | 0.987 |
| 4, sharpen 1.0 | 49/120 | 1.318 (coarse strong texture) | 1.017 |

At 4 the gain is mostly coarse: strong texture 0.73x, boundary 0.82x, smooth 0.89x
(but up to +3.7% on N22 flat/tilt), mid 0.96-0.98x, fine ~0.98-0.99x. The fine
ramp must stay: flattening it (sharpen 1.0) is worse. Returns flatten past 4, and 4
keeps the coarsest bands below the 8.0 cap.

**Burst truth (MEASURED,** 8 in-focus frames vs held-out mean of 24): every cell within
0.3% (coarse flat 2.243e-8 -> 2.250e-8). No noise cost where all frames agree.

**Replicates, scene-linear (MEASURED,** current binary both arms, A = exponent 2,
B = `--pyramid-exponent 4`, reports `D:/codex-work/iq2/x4-*.report`): texture and noise
power B/A within 0.98-1.02 in every SNR bin on bee-3, 109, bug-4, coffee-bean and garnet;
wrapped-text 0.94-0.96 for both texture *and* noise in its low-SNR bins (2 of 3978
textured tiles below 0.85; the worst-cluster crop is visually identical). bee-3's 56 dark
tiles fall to 0.63-0.85 (less haze).

**By eye, with a reference (MEASURED).** bee-3: the milky veil of defocused light hair
over the dark legs and thorax thins and contrast rises (`x4-bee3/ab-coarse.png`); the
antenna ghost (§3) is unchanged to slightly fainter. Garnet: the glow ring in the black
ground around the gem drops; one background patch reads 7% *redder*, and single-frame
renders show that is the truth: frame 182, the one in focus there (local high-pass
power 2.27 vs the merges' 2.15), has red 5.28e-4; exponent 4 gives 5.47/5.00 (half
stacks), exponent 2 gives 4.17/3.88 -- below every single frame. Coffee bean: smooth
coarse changes (rim darker where background light spilled in, interior +2-3%), no
blotches. Slide-2 glow vs composite: 16-32 px 1.27 -> 1.25, 32-64 px 1.23 -> 1.20 --
the residual glow is not soft coarse selection.

**Unit test.** `pooled_evidence_and_a_weighted_base_remove_the_glow_around_bright_detail`
now also folds at `DEFAULT_EXPONENT`: glow 2.0 -> 0.94 DN, bar error 33 -> 8.6 DN;
mutation-checked (with the default at 2 it fails). Research configs pinned to the
previous merge also pin `exponent: 2.0`; sessions keep their own default of 2 with
their previous selection. Byte freeze re-baselined, attributed bit-exactly.

## 1c. Taming bright glints on gems (development control, 2026-11-03)

Owner request: a way to reduce super-bright spots, as on the minerals.

Specular glints are real light; the merge should keep them. The control is in
development, next to *Soften highlights*: **Tame glints**
(`AdaptiveParameters::glint_compression`, desktop slider, agent-MCP schema, and a
*Gems and glints* treatment preset). It lives in the existing spatial treatment
(20 x ~13 cells x 33 half-stop luminance slices, a bilateral grid): per cell,
light more than 2 stops above that cell's typical level is compressed at up to
-0.5 EV per stop (2:1), after the centering solve so nothing else is lifted; the
existing order limiter keeps every curve monotone (`SpatialTreatment::validate`).
Large bright areas set their own cell level and are left alone. It cannot
recover clipped texture; where a specular blob was not clipped, its surface
texture reappears.

MEASURED on `minerals/etched-spessartine-garnet` (183 frames), headless
(`adaptive-recipe/` + `strehl develop`): the large specular facet goes from flat
white to showing its surface texture; the V-shaped glint and sparkle are toned
down; crystal body and black ground unchanged (`garnet/gl-*.png`). Test
`glint_compression_lowers_small_bright_spots_but_not_large_bright_areas`
(mutation-checked: a knee out of reach fails it); the strongest-controls
order test now includes it. 80+ strehl-edit tests and 1039 strehl-ui tests pass.

## 2. Fuse each source's reconstructed RGB instead of re-mosaicing (REJECTED)

**Hypothesis.** The default full-resolution gather demosaics each source (MHC),
resamples RGB, keeps one colour per site (re-mosaic), merges CFA planes, then
demosaics again. Fusing all three reconstructed colours and skipping the second
demosaic should keep colour information that phase-diverse frames supply.

**Synthetic (MEASURED, `remosaic-synth.py`).** Truth from binned quads of a real
frame, band-limited shifts: RGB fusion +1-4 dB over re-mosaic, most where
frames average. Self-test: identity shift reproduces MHC exactly.

**Real (MEASURED).** Implemented as 12 quarter-resolution planes (4 sites x 3
colours) with selection weights bit-identical to the default; identity control
(one frame, CA off, crop cover) matches to 1e-8 in camera space. On the neutral
razor blade (truth: no chroma) high-frequency chroma rose **1.48-1.57x** and the
finest luma fell ~8%; on `109MSDCF` chroma noise rose 1.8x. One frame shows the
cause: the second MHC on a resampled mosaic acts as a chroma low-pass (0.0100
against 0.0141 for the gathered RGB). Not integrated; the arm is archived as
`rgb-fusion-arm.patch` and `rgb-fusion-arm-merge_cmd.diff`.

## 3. Open: see-through ghosting at occlusions

At 1:1 on `bee-3-cpl` the most visible remaining defect is background hair
showing through the near antenna and translucent-looking hairs over the shiny
thorax: in far-focused frames a thin defocused occluder transmits the sharp
background, whose band energy beats the occluder's own faint texture. This is
the pyramid (PMax-like) transparency artefact. The ensemble gate neither causes
nor fixes it. Pooled evidence with the weighted base (§1b) removes the variant
where hairs *behind* a dark leg showed through it, but not the antenna case.

*Tried and archived (2026-11-03): a coarse-consistency gate.* A frame's fine-band
weight was multiplied by how well its own coarse luma (pyramid level 2) agreed
with a reference coarse luma from a full render's sensor master, after removing a
per-frame scale (`consistency-gate-experiment.py`, `coarse-reference.py`). It
changed 1.1% of pixels by more than 256/65535 but left the antenna streaks
unchanged: the streaks are 10-20 px wide and already present in the reference
built from the same merge, so the frames that draw them read as consistent. A
reference free of the ghost needs occlusion order. The bracket order is known on
this rig (Sony focus position rises monotonically; on bee-3 the antenna is sharp
at frame ~40 and the hair behind it at ~260-280), so a depth-ordered first pass
is the open lead.

*Tried and archived (2026-11-03): a depth-ordered occlusion prior*
(`occlusion-prior-experiment.patch`). A first pass (~6 s on 299 frames) decodes
each frame's green per quad at half the analysis plane, pulls it onto the
reference grid by its placement, scores a log local high-pass energy, and takes
per cell the nearest frame whose score is within a factor of the best; at the
three finest bands, frames more than 20 beyond that near surface lose weight.
With the near surface "within 1/2 of best" the antenna map read the hair behind
it (~frame 108) and nothing changed; "within 1/8" found the antenna and removed
most of its ghost streaks -- but it also visibly softened mixed-depth hair (crops
`bee3/o3-*`, `o4-*`): a hair mat is *porous*, and farther hair genuinely visible
through its gaps was suppressed. A depth-coherence filter on the map (drop labels
whose 13x13 neighbourhood spread exceeds 10 frames) did not separate the cases.
The rule needs an opacity estimate (solid leg/antenna vs porous strands), which a
quarter-resolution map cannot resolve. Not shipped.

*Tried and archived (2026-11-03): a streaming, full-resolution occlusion rule*
(`occlusion-stream-experiment.patch`, `STREHL_OCCLUSION_STREAM=zsig,margin,softness,levels`).
Frames fold near to far, so per coefficient the merge recorded the first frame
whose *own* band energy reached `zsig` times its noise energy, and frames more than
20 folds later lost weight (Gaussian, 15 folds) at the three finest bands -- no
map, no relative-to-best criterion. On `bee-3-cpl` (299 frames, current default
otherwise) at zsig 8 and 4 it removed most antenna ghost streaks and softened the
same porous hair as the map-based prior (crops `iq/bee3/xs-*`), plus the
in-focus background hair fans beside the antenna. A hair mat has a nearer layer
whose energy is significant within the smoothing reach of almost every gap pixel.
The negative now covers both a coarse map and a per-coefficient rule. Any
ordering rule needs an opacity estimate.

Pooled evidence makes the antenna ghost slightly *more* contrasty than before
(antenna-strip 99th percentile 59 -> 61 in 1e-3 linear units, both half
stacks): coarse bands now follow the frames where the background hair behind it
is sharp. Disclosed as a cost of §1b.

## 4. Cost (MEASURED)

`insects/bug-4/102MSDCF`, 299 frames, `--srgb`, shared warp map, eight runs
through `experiments/multi-stack-2026-10-28/run-command.py`, gate off/on
interleaved. **The host was not idle**: a foreground process outside this lane
held the CPU at ~76% load, so wall time (123-196 s for both arms) is not a
usable comparison and is not claimed. Owned-process CPU time and peak memory
are stable across runs:

| arm | sampled CPU s (4 runs) | mean | sampled peak private |
| --- | --- | --- | --- |
| gate off | 1961, 1966, 1968, 2027 | 1980 | 5.54-5.55 GB |
| gate on | 2033, 2047, 2084, 2141 | 2076 | 5.93 GB |

About **+5% CPU** (the four extra accumulators, the null window, and the
per-band blend maps at finish) and **+0.38 GB** peak. The memory planner counts
the extra accumulators (`planning_accumulator_floats`), which moves the
canonical chunk count and therefore the floating-point reduction order: gate-on
renders are not byte-comparable to gate-off renders for that reason as well.
