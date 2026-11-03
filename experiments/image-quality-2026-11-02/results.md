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
the pyramid (PMax-like) transparency artefact. Not addressed here; the gate
neither causes nor fixes it.

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
