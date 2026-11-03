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

Re-run after §1d/§1e with the *full* current selection (pooled, weighted base,
exponent 4, ratio 2; experiment-only switch, same alignment cache) against the
shipped session: dark-ground noise 0.842e-4 -> 0.865e-4 and black 1.573e-4 ->
1.726e-4 again. The bright iridescent highlight that gained most in the ordinary
merge kept a similar or slightly brighter halo; elsewhere the two are hard to tell
apart. The ordinary merge's win does not carry over to session fusion, so this is
not just the missing gate; porting the gate alone is not expected to change that
and is not scheduled.

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

## 1e. Counting finer levels more in pooled evidence (SHIPPED, 2026-11-03)

**Finding (MEASURED).** On `insects/bug-4/104MSDCF` (even half, 150 frames) a bright
iridescent edge still sat in a green glow after §1b/§1d. Single-frame linear renders
(every 12th frame, same warp map, crop origin 1080,1848) put the edge in focus at frame
~132 (local high-pass power 23,000 against ~40 for far frames). Green profile across the
edge, mean of 150 rows, 1e-3 linear:

| px from edge column 204 | 0 | +8 | +16 | +24 |
| --- | --- | --- | --- | --- |
| frame 132 (in focus) | 408 | 52 | 14.6 | 13.7 |
| frames 84-96 / 156-168 (moderately defocused) | 604-727 | 186-577 | 25-286 | 14-78 |
| pre-§1b default | 576 | 195 | 80 | 37.6 |
| pooled, exponent 2 | 544 | 163 | 52 | 17.1 |
| pooled, exponent 4 (shipped §1d) | 547 | 170 | 57 | 17.6 |
| **pooled, ratio 2 (shipped)** | 484 | **100** | **22.5** | 11.6 |
| pooled, ratio 4 | 428 | 65 | 13.0 | 11.3 |

**Cause (ARGUED).** Pooled evidence took the plain mean over levels, and moderately
defocused frames carry large mid-band energy in the light they spread beside a very
bright edge, so they kept part of the coarse bands. Counting finer levels more
(`MergeConfig::pooled_evidence_ratio`: level j enters band k with weight
ratio^(k-j), normalised) follows the levels that carry focus.

**Truth (MEASURED).** Synthetic stacks, current default otherwise, reference ratio 1:

| ratio | cells worse | worst cell | geo-mean error |
| --- | --- | --- | --- |
| 1.5 | 1/120 | 1.000 | 0.948 |
| **2 (shipped)** | 1/120 | 1.037 (flat N60 coarse weak texture) | **0.922** |
| 2.5 | 14/120 | 1.107 | 0.911 |
| 3 | 20/120 | 1.203 | 0.910 |
| 4 | 24/120 | 1.476 (coarse weak texture) | 0.921 |

2 is the knee: above it coarse texture starts to lose, which is the finer-only failure
of §1b. Burst truth (8 in-focus frames): coarse flat 2.250e-8 -> 1.940e-8 (-14%),
every other cell within 0.3%.

**Replicates, scene-linear (MEASURED;** A = shipped §1d default, B = ratio 2;
`D:/codex-work/iq2/l2-*.report`). Texture and noise power B/A within 0.98-1.03 in every
bin with SNR >= 1 on all six subjects. Low-SNR bins: bee-3 SNR < 0.3 texture *and*
noise 0.92/0.93 (fine) and 0.77/0.78 (mid), i.e. less noise; 109 mid SNR 0.3-1 texture
0.95 with noise 0.99 -- its worst cluster is a near-white out-of-focus backdrop where
the crops are visually identical; coffee-bean fine SNR < 0.3 texture 0.87 (noise
1.005), mid 0.96-0.98; wrapped-text noise +1.7-2.5%. Slide-2 scene-linear glow:
unchanged (0.94-0.96 of the composite at 2-128 px). bee-3 by eye: antenna, leg edge and
porous hair indistinguishable from the §1d default at 1:1.

**Exponent at ratio 2 (MEASURED,** synthetic, reference exponent 4): 3 is worse in
114/120 cells (geo-mean 1.020); 6 is 0.991 with 5 cells worse by at most 0.3%. The
shipped 4 stays within 1% of the best tested.

**Tests.** `pooled_levels_is_the_total_weight_of_the_pooled_levels`; the default is pinned
in `the_base_band_default_is_the_measured_one`. Session fusion implements the ratio, and
its parity test now runs at ratio 2. Mutation-checked: a session consumer that ignores the
ratio differs from the ordinary merge by 19.6 DN. The bars plant of §1b keeps ratio 1;
at ratio 2 it reads glow 0.94 -> 1.29 DN and bar error 8.6 -> 6.2 DN, i.e. mixed and
tiny. Two compact plants (a clean bright step, and a bright foreground edge over a
farther textured background) drew no glow at either ratio, so the bug-4 mechanism is
not reproduced by a unit test; the evidence is the measurements above. Byte freeze
re-baselined and attributed bit-exactly (ratio 1.0 reproduces the previous row).

## 1f. Regression sweep on subjects not used above (MEASURED, 2026-11-03)

Start-of-night selection (gate on, `STREHL_PYRAMID_POOLED_EVIDENCE=0 --pyramid-base mean
--pyramid-exponent 2`) against the current default (pooled, weighted base, exponent 4,
ratio 2), one warp map per subject, full stacks, linear masters plus sRGB; the two
256-px tiles with the largest coarse-scale difference were inspected at 1:1
(`D:/codex-work/iq4/*-ab.png`, overviews `*-ov.png`).

* **bug-3 104MSDCF** (coarse difference within -1.4%..+3.5% of white at the 0.1/99.9th
  percentiles): leg spines and blue scales crisper, less haze over the black ground; no
  artefact.
* **maldon-sea-salt** (-2.8%..+3.2%): crystal surfaces slightly higher in contrast; no
  artefact.
* **bee-1** (-9.7%..+8.9%): the largest change is the tip of the left wing, which enters
  focus only at the far end of the bracket. Single-frame renders (every 15th frame) show
  no wing at frames 0-150 and its dark, blurred membrane from ~285. The old merge
  averaged it with the ~250 wing-free frames into a semi-transparent ghost (mean green
  202.6e-3 over the crop); the new merge shows it as the nearest-focus frames do (185.8e-3,
  frame 285 at 188.5e-3). Correct, and more visible.
* `flower-marigold-cpl` is a folder of sub-stacks, not a capture; not run.

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

**Other minerals (MEASURED,** current default merge, same recipe pair
`shadow_protection=0.85` with `glint_compression` 0 vs 0.85; `D:/codex-work/iq3/*`):
*peacock-ore* 102MSDCF -- the blown white patch is toned down and shows texture,
pixels above 95% white 0.133% -> 0.001%; *rainbow-opal-cabochon* -- no change (0.2%
-> 0.2%): its bright area is large and sets its own cell level, as designed;
*rutile-star-on-hematite* -- above-95% pixels 0.245% -> 0%, but the golden rutile
blades themselves are dimmed, not only their sparkle, because on dark hematite a
whole blade is more than 2 stops above its cell's typical level. **Limitation:** the
control's notion of "small" is a grid cell (~350 px on a 7000 px frame), so bright
subjects smaller than a cell on a dark ground are treated as glints. Use a lower
setting there. (Superseded for dark-ground images by the lit-subject level below.)

*Tried and reverted:* fading the compression where a cell's bright slice is mostly
*coloured* pixels (the lattice's existing colour moment; glints should be near
neutral). No fade range separates the cases. Pixels above 95% white:

| fade range | rutile | peacock | garnet |
| --- | --- | --- | --- |
| off (no taming) | 0.245% | 0.133% | 0.120% |
| none (shipped, 0.85) | 0.000% | 0.001% | 0.005% |
| 0.3-0.7 | 0.010% | 0.119% | 0.117% |
| 0.6-0.95 | 0.000% | 0.090% | 0.113% |
| 0.85-1.0 | 0.000% | 0.022% | 0.043% |

Rutile's blades kept their level at 0.3-0.7 (mean 0.0776 vs 0.078 untreated, 0.0739
shipped), but peacock's and garnet's speculars are tinted by the stone (and by blurred
neighbours in the lattice), so they read as coloured too and lost the taming.

*Measured, not built:* a size test using the share of each cell's samples above the knee
does not separate them either. Per-cell share p50 / p90 / max: rutile 0.18 / 0.28 / 0.36,
peacock 0.07 / 0.09 / 0.12, garnet 0.08 / 0.18 / 0.31. The cause is upstream: a cell's
typical level is the mean log light including the dark ground, so on a black background
any lit surface is "more than 2 stops above typical". A typical level of the lit subject
alone is the place to start if this is revisited.

**Fixed: a lit-subject typical level (SHIPPED, 2026-11-03).** Pure black never
enters the lattice (luma below 0.002 is skipped), so garnet and peacock have no ground
in it; hematite does. The analysis now splits the image's luminance histogram in two
(Otsu over the 33 slices) and, when the two populations' means are at least 3.5 stops
apart, takes each cell's typical level over the lit slices only, pulled toward the
whole cell's mean with 5% of the cell's population. A cell holding only glints on the
ground (tiny lit share) keeps its old level, so those glints are still tamed.
Measured separations: peacock 2.2, garnet 2.9 (no ground: recipes **byte-identical**
to before), rutile 4.2, opal 6.8 (ground).

MEASURED (`glint-score.py`: share of pixels with any channel above 95% white, and the
mean treated/untreated luma ratio per bin of untreated developed luma; same recipe pair
as above, masters re-rendered with the current default merge):

| subject | arm | above 95% | 0.05-0.2 | 0.2-0.4 | 0.4-0.6 | 0.6-0.8 | 0.8-0.9 | 0.9-1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rutile | untreated | 0.263% | 1 | 1 | 1 | 1 | 1 | 1 |
| rutile | before | 0.000% | 0.997 | 0.955 | 0.938 | 0.921 | 0.875 | 0.852 |
| rutile | lit level | 0.143% | 1.000 | 1.000 | 0.999 | 0.996 | 0.986 | 0.970 |
| opal | before | 10.414% | 0.988 | 0.998 | 1.000 | 1.000 | 1.000 | 1.000 |
| opal | lit level | 10.414% | 0.991 | 0.999 | 1.000 | 1.000 | 1.000 | 1.000 |

(Opal's 10% above 95% is its high-key body, untouched by both arms, as designed.)
Native crop on rutile's large golden blade, origin (5000,2300), 400 px
(`iq3/rutile/bladeL.png`): before, the blade is flatter, dimmer and less saturated;
now it matches the untreated development. The largest white rutile face, origin
(1200,3600) (`cmpL.png`), is now only trimmed at the top; the shipped version had
compressed the whole face and shown more of its texture. That is the price: on this
subject the control now does little, because rutile has few highlights that are small
*relative to the lit blades*. Dim specks on hematite next to a blade are no longer
tamed (they sit below the blade's level); specks in cells without a blade still are.
Prior sweep 0.02 / 0.05 / 0.1 on rutile: above-95% 0.155 / 0.143 / 0.117%, 0.4-0.6
bin 1.000 / 0.999 / 0.998.

Test `glint_compression_judges_a_lit_subject_on_dark_ground_by_its_own_level` (blades
on a ground 3.7 stops below, glints on the blades). Mutation-checked: no ground split
fails it (blade 0.066 -> 0.054); no prior fails the existing small-glint test (0 of
100 glints lowered).

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

*Tried and archived (2026-11-03): an opacity cue from light agreement*
(`occlusion-opacity-experiment.patch`, `STREHL_OCCLUSION_OPACITY=zsig,margin,softness,levels,up,d0,d1,noise`).
The idea: at a gap in a porous mat, the frame focused on the near layer already shows
the blurred background, so a far frame's coarse light agrees with it; at a solid
occluder it does not. Per coefficient at the three finest bands, the first frame
significant there recorded its luma `up` levels coarser; frames more than 20 folds later
lost weight where their own coarse luma disagreed (relative difference smoothstepped
from `d0` to `d1`, plus `noise` x the level's noise sigma). On `bee-3-cpl` (current
default otherwise, same warp map, experiment binary built from `a9fc6fc25`) four arms --
zsig 8 and 4; `up` 2 and 1; `d0-d1` 0.25-0.6, 0.12-0.35 and 0.03-0.15 -- changed at most
0.85% of pixels by more than 256/65535 and left the antenna interior unchanged at 3x
(`iq/bee3/op-zoom.png`, `op4-zoom.png`, origin (4880,2900), 150 px); porous-hair
high-pass energy moved by under 0.2%. The antenna is ~130 px wide, so in the frames that
draw the ghost its interior stays dark at every coarse scale: the light barely shifts while
any texture still shows on the dark surface. Light agreement does not measure what the
ghost needs.

Pooled evidence makes the antenna ghost slightly *more* contrasty than before
(antenna-strip 99th percentile 59 -> 61 in 1e-3 linear units, both half
stacks): coarse bands now follow the frames where the background hair behind it
is sharp. Disclosed as a cost of §1b.

## 3b. Per-channel focus offset for longitudinal CA (REJECTED, 2026-11-03)

SYNTHESIS fact 1417 proposed (ARGUED, unexplored) keeping the green-led selection but
folding red and blue from a frame offset by the measured focus difference; the
novelty list names per-channel stacking exploiting longitudinal CA.

**The offset is real (MEASURED, `loca-focus-curves.py`).** Per 8 x 8 tile, a contrast-
normalised band-pass energy per raw CFA channel per frame, sub-frame parabolic peak,
tiles with a clear peak only. Flat calibration slide (`flat-et2.5s-sw4-cpl`, 60
frames), mid band: R-G **-1.92** frames (IQR -2.01 to -1.79), B-G **-1.86** (-2.10 to
-1.65), 64 tiles; finest band: R-G -2.16, B-G -1.62, and R and B keep only **0.882**
and **0.927** of their own best energy at green's best frame. `bee-3-cpl` (299 frames,
finer step), finest band: R-G -0.84, B-G -0.62 frames, 47 tiles; 0.973 / 0.990. Red and
blue focus nearer than green, together -- the secondary-spectrum pattern -- and the
offset in frames is stack-dependent, so it would need a runtime fit.

**Folding them from the offset frame does not help (MEASURED).** Experiment
(`loca-delay-experiment.patch`, `STREHL_LOCA_DELAY=dR,dB`): a ring buffer of past R and
B planes in the frame workspace (chunks run serially, so it spans chunk boundaries);
frame g's weights fold R and B from frame g-d, fractional d interpolating two frames.
Flat slide, same warp map, linear masters, `fringe.py` (per-channel gains from bright
flat pixels make the target grey; edge band = top 3% of green gradient):

| arm | edge fringe R | edge fringe B | edge hp R/G | edge hp B/G |
| --- | --- | --- | --- | --- |
| default | 4.267% | 3.763% | 0.7656 | 0.7186 |
| d = 2, 2 | 4.438% | 3.965% | 0.7851 | 0.6924 |
| d = 2.16, 1.62 | 4.512% | 3.985% | 0.7877 | 0.7026 |
| d = 2, 0 | 4.433% | 3.749% | 0.7900 | 0.6879 |
| d = 1, 0 | 4.329% | 3.755% | 0.7823 | 0.7002 |

Red gains ~3% edge energy and blue *loses* it even when blue is not delayed: the second
(MHC) demosaic borrows red's local gradients to fill in blue, so the channels are
coupled. Fringing rises in every arm. Chroma-boosted crops (`loca/flat/edge-cmp.png`,
origin (4116,2224), 120 px, 3x) show why: the visible fringe is red on one side of each
line and blue on the other -- a residual *lateral* shift, which a focus offset cannot
move. The lateral-CA record (facts 1414-1903; no scalar fix, scene-dependent effective
wavelength, fact 1570) is the place for that defect. Not built.

## 3c. Per-capture lateral-CA refinement (MEASURED, 2026-11-03; not yet built)

While testing 3b, chroma-boosted crops of the flat slide showed red on one side of every
line and blue on the other, near the centre -- a lateral offset the shipped correction
leaves. SYNTHESIS fact 1570: no scalar CA fix exists (effective wavelength is
scene-dependent); improvement must come from per-capture estimation.

**Instrument (`ca-residual.py`).** On a linear master: per 256 px tile with enough green
gradient, the sub-pixel shift of R and of B against G by phase correlation on gradient
magnitude; a least-squares fit of displacement = translation + scale x (position from
centre). Control: an integer roll of green is recovered exactly. On raw frames
(`ca-raw-shift.py`), each CFA site set is bilinear-interpolated on its own so samples stay
where they were taken; the null (G1 sites alone vs G2 sites alone, same sparsity as R or B)
reads (+0.02, +0.02) px / -13 ppm against R's (-0.13, -0.19) px / -582 ppm on the flat slide.

**What the shipped correction leaves (MEASURED, output residual, shipped constants
eps_r -508.4 ppm, eps_b +174.4 ppm, translation not applied):**

| subject | R residual t (px), scale | B residual t (px), scale |
| --- | --- | --- |
| flat slide | (+0.01, -0.28), -75 ppm | (-0.11, +0.19), +4 ppm |
| slide-2 | (+0.04, -0.29), -103 | (-0.08, +0.25), +58 |
| razor | (+0.09, -0.10), +75 | (-0.10, +0.05), -33 |
| bee-3 | (+0.08, -0.13), +134 | (-0.02, +0.13), +11 |
| bug-4 104MSDCF | (+0.05, 0.00), +250 | (-0.03, +0.04), -115 |
| garnet | (+0.02, +0.01), +142 | (0.00, +0.09), -8 |
| peacock 102MSDCF | (+0.08, +0.05), +106 | (-0.01, +0.06), -45 |
| rutile | (+0.08, +0.04), +100 | (-0.02, +0.13), +37 |

Red's native scale is -258 to -611 ppm across these captures against -508 shipped:
over-corrected by 75-250 ppm on natural subjects (0.25-0.85 px at 0.8 field height).

**Raw-frame estimates are not reliable enough.** On rutile one mid frame gave the right
scale (-397 ppm; output-calibrated native -399) but a wrong translation (red residual
+0.04 -> +0.30 px when applied): a partial field couples translation and scale. Pooling 11
frames gave -262 ppm; keeping each tile's sharpest frame gave -557. Not used.

**Output-domain two-pass converges (MEASURED; experiment `ca-refine-experiment.patch`,
`STREHL_CA_OVERRIDE`, script `ca-two-pass.sh`).** Pass 1 renders with the shipped
correction; the residual measured on its linear master is added to the correction; pass
2 re-renders. A control passing the shipped constants through the override is
byte-identical to the default. Pass-2 residuals: <= 0.03 px and <= 32 ppm on six of
seven subjects; bug-4 and peacock keep +71 / +48 ppm (response below 1:1; a second
step would be needed). Fringe on the neutral targets (`fringe.py`):

| subject | R fringe shipped -> refined | B fringe shipped -> refined |
| --- | --- | --- |
| flat slide | 4.267% -> 2.634% | 3.763% -> 2.056% |
| slide-2 | 7.343% -> 3.154% | 5.371% -> 2.137% |
| razor | 4.069% -> 3.746% | 4.456% -> 4.182% |

Visible at 3x with chroma boost: the flat slide's diagonal bars lose their red-above /
blue-below fringe (`loca/flat/trans-cmp.png`); bug-4 hairs at r 0.63, origin (980,1260),
read more neutral (`ca/bug4/ca-edge0.png`). Caveat: whole-image fine energy in R/B fell
3-7% on bee-3 and the razor (unchanged on slide-2); some of that is the demosaic's
cross-channel overshoot at misaligned edges disappearing (the razor's edge colour error
fell), but a resampling softening is not excluded.

**Cost of measuring.** The residual from every 8th frame (16.5 s vs ~95 s for the full
stack) matches the full stack on bug-4 (+248 vs +250 ppm) and is 42 ppm low on bee-3; a
half stack matches both within 11 ppm. So a preview pass of a subset, then one render,
is viable at roughly +20-30% time.

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
