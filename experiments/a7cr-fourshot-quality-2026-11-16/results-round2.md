# A7CR four-shot quality, round 2: investigation results (2026-11-16)

Status: investigation, author-run, not independently reviewed. No product
code changed, nothing committed. The questions and controls were registered
in the [brief](brief.md) (section "Round 2") before any measurement here
ran. Round 1 is in [results.md](results.md); the recommendations from both
rounds are in
[the proposal](../../docs/proposals/2026-11-a7cr-four-shot-quality-improvements.md).

Subjects: the white scarab four-shot run
`D:/StrehlCaptures/stack-1794786793543-11226` (196 groups, FE 100 mm macro
with 2x converter wide open, ISO 100, 0.6 s) and, new in this round, the
neutral black-on-clear resolution slide of the calibration campaign (static
four-shot groups at one focus position: `stack-1794683752817-11226`, 8 groups
at 1.6 s, and `stack-1794683631859-11226`, 8 groups at 0.6 s; room light,
target tilted against the sensor). Renders: `target/release/strehl.exe`,
build `cbca976b7e96-dirty` of 2026-11-16 02:12 (unchanged since round 1),
CPU fold, 32 threads. Python 3, torch (CUDA), RTX 5090. Outputs in ignored
`outputs/a7cr-fourshot-quality/`.

Nothing here rests on an A7C II result. The coin-stack results of
2026-11-15 (frames 0.18 px apart, red 5.5 frames from green) were re-measured
on the scarab where they bear on a question.

## Summary

| # | Question | Answer | Label |
| --- | --- | --- | --- |
| R1 | Can the response map come from the stack itself? | Yes. A map built from half the stack's raw frames (inverse-energy weights, shrinkage for thinly sampled photosites) and applied to raw frames it has not seen leaves 9-10 % of the pattern's power in green, 17 % in red, 10 % in blue. The rolled-map placebo adds 55 %. A stored map from the 32-frame calibration burst is worse than no correction (its own noise and scene) | MEASURED |
| R2 | Exposure | Green already sits at the top of the linear range (99.999th percentile 9 360-9 390 DN; the photon-transfer slope bends from 9 500). Red and blue reach 4 770 and 3 970 DN: 32 % and 27 % of the range | MEASURED |
| R3 | Frame registration on a matte subject | Frames one plane apart sit 0.13 px rms from each other, eight apart 0.4-1.1 px. Nearly all of it is one similarity per frame pair (0.02 px left at one plane, 0.13-0.28 at eight), dominated by a scale error of 10 ppm per plane (the alignment's magnification step is about 8 % short). It costs a matched-weight average over +-8 frames 6-9 % of fine signal power; the election, nothing | MEASURED |
| R4 | What the frames around a point's focus hold | Per pixel, the fine band's power through focus has a half width of about seven frames each side. A 7-frame window keeps 0.90 of the amplitude and gives 5.7 best-frames of signal-to-noise; positive matched weights over +-8 frames give 7.6, and wider windows give no more. The election's participation ratio is 6.9 frames in textured areas and 5.6 in smooth ones (it picks by noise there). In smooth bright areas the fusion's noise amplitude is 0.38-0.59 of the election's. Red and blue focus 3-4 and 2.5 frames after green and keep 93 % and 96 % of their amplitude at green's focus | MEASURED |
| R5 | A signal-adaptive window along focus | Not prototyped: the fusion's fixed windows already do in smooth areas what the election does not (R4). Widening beyond them helps only below 0.25 cycles/px | DERIVED |
| R6 | Locally adaptive restoration | No. Withholding the restoration where a neighbourhood holds no detail changes noise and error by 1-2 %: the restoration is not a net noise amplifier | MEASURED |
| R7 | Channel registration | The displacement of red and blue against green depends on scale, in the raw frames themselves: coarse content of red sits -539 ppm from green and its detail finer than 0.24 cycles/px -16 ppm (blue +166 and +6). The lens profile moves the whole channel, so in a render fine red detail ends +425 ppm from green (1.03 px rms over the in-focus tiles; blue -173 ppm, 0.43 px). The fine part is green-band light passed by the red and blue filters: it sits at the same site as green with a flat transfer of 0.22 (red) and 0.15-0.19 (blue) of green's raw signal in every direction, which rules out neighbour crosstalk. Taking that share out before the channel is registered and adding it back afterwards brings red to 0.25 / 0.14 / 0.07 px rms at coarse / mid / fine scale (from 0.28 / 0.62 / 1.03) and blue to 0.15 / 0.11 / 0.05 (from 0.34 / 0.31 / 0.43) | MEASURED |
| R8 | Rig stability | Member positions scatter 0.05-0.08 px per axis about a fixed 0.05 px mechanism offset, the same as the static slide groups, with no growth from member 2 to member 4. The rig is not the limit on this run | MEASURED |
| R9 | Response outliers | None above 5 %. Photosites more than 2 % off in both the self map and the burst map: 17 red, 18 green, 121 blue of 47.6 million | MEASURED |
| R10 | By eye | Point-like glints on dark cuticle come out green, orange or blue in the four-shot render (neutral in the single-shot one, whose demosaic ties fine colour to green). Dark ground within 7 px of bright scales carries 2.2-2.8 points (of the bright level) more red and blue than green. On the neutral slide blue's contrast relative to green is 0.78-0.87 at 0.14-0.33 cycles/px where the restoration's model assumes 1.04-1.20. Equalising red and blue to green with the slide's ratios lowers the scarab's rim within 7 px by a quarter (red) and by a third to all of it (blue); the inverse filter raises it | MEASURED |
| R11 | A short-wavelength detail exposure | No: on the neutral target blue is softer than green, not sharper | MEASURED |

Three corrections to round 1:

1. **Round 1's "not displacement between channels" (Q1) was wrong at fine
   scale.** Its displacement control was fitted over 0.03-0.30 cycles/px
   with weights that let coarse content decide. Fitted on fine content the
   displacement is 1 px rms for red. With it repaired, red-green coherence
   at 0.25 / 0.30 / 0.35 / 0.40 cycles/px is 0.43 / 0.40 / 0.37 / 0.38
   where round 1 reported 0.25 / 0.18 / 0.12 / 0.10, and blue-green 0.59 /
   0.54 / 0.50 / 0.49 where it reported 0.54 / 0.47 / 0.40 / 0.38. The
   substance of Q1 stands, re-scored on the repaired halves
   (`cross-channel.py`): the shipped smoothing's error is 17.6 % (red,
   0.10-0.25 cycles/px), 98 % (red, 0.25-0.40), 8.5 % and 93 % (blue)
   against 3.0 %, 14.9 %, 2.7 % and 21.8 % for a per-channel filter, and
   the joint filter is 1.00-1.04 times the per-channel one. But a sixth of
   red's fine power and a quarter of blue's is green-band light in the
   wrong place (coherence squared), and proposal item 3 must come after
   the registration fix.
2. **The flat-field capture is no longer a prerequisite** for proposal
   item 1 (R1).
3. **Round 1's "four to five groups' worth" in the fine band** is a
   signal-to-noise equivalent. The election's weights spread over 6.9
   frames (5.6 in smooth areas); selection by noisy coefficients costs the
   rest.

Two instrument notes that matter to anyone repeating this:

- `STREHL_PYRAMID_WEIGHT_DUMP` numbers frames in the order accumulators were
  absorbed, not in file order. With the restoration's half-stacks on (the
  default for pixel-shift stacks), label `a` below `ceil(N / 2)` is frame
  `2 a`, otherwise frame `2 (a - ceil(N / 2)) + 1`. Decoded, the band-0
  winner per 256 px tile matches the tile's own energy peak with correlation
  0.965 (median offset -1 frame); undecoded the correlation was -0.26.
- Through-focus statistics over tiles are not through-focus statistics of a
  point on this subject: frames 6 apart share 13 % of their fine power
  across a tile, and frames 8 apart 2 %, while each still holds 80-90 % of
  the tile's peak power. Removing a smooth phase per frequency cell does
  not bring it back (0.08 against a placebo floor of 0.05-0.06): different
  parts of a tile are in focus in different frames.

## R1. A response map from the stack itself

[self-flat.py](self-flat.py), [self-flat-shrink.py](self-flat-shrink.py),
[fpn-raw.py](fpn-raw.py) (`--apply`, `--roll`, `--select-raw` added).

Estimator. For every raw frame and CFA plane, `r = M / gauss(M, 2) - 1`
(plane px). Each sample is weighted by the inverse of the local energy of
`r` actually seen (`gauss(r^2, 4)`, never above the noise model's weight),
so in-focus texture counts little; samples under 150 DN or within 12 plane
px of 13 500 DN are dropped. Per photosite the map is
`sum(w r) / (sum(w) + 1 / kappa^2)` with kappa 0.30 / 0.35 / 0.40 % for
R / G / B (round 1's sizes): a photosite seen rarely is pulled to zero.

Held-out test. The map from planes 1-98 is applied to the raw frames of
planes 120-123, 145-148, 170-173 and 190-193 (16-frame means, four focus
positions with different scene content), and the pattern common to those
means is measured on bright smooth tiles chosen before correction. A second
fold swaps the halves (map from 99-196, tested at planes 10, 35, 60, 85).
Pattern amplitude, % of level, at 1 plane px, and the share of its power
left:

| Arm | Red | Green | Blue |
| --- | --- | --- | --- |
| no correction (the other fold: 0.246 / 0.293 / 0.317) | 0.249 | 0.298 | 0.323 |
| inverse-energy weights + shrinkage | 0.103 (17 %) | 0.093 (10 %) | 0.102 (10 %) |
| hard smoothness gate + shrinkage | 0.136 (30 %) | 0.189 (40 %) | 0.133 (17 %) |
| the same, other fold | 0.157 (41 %) | 0.203 (48 %) | 0.149 (22 %) |
| hard gate, no shrinkage | 0.174 (49 %) | 0.221 (55 %) | 0.147 (21 %) |
| placebo: gated map rolled (5, 3) plane px | 0.326 (171 %) | 0.371 (155 %) | 0.441 (186 %) |
| stored map from the 32-frame burst of another day | 0.488 | 0.344 | 0.541 |

- The independent witness agrees: the covariance of the corrected stack
  means with the other day's 6 s burst falls from 0.296 % to 0.089 % in
  green (9 % of the power left), 0.247 to 0.087 in red, 0.321 to 0.086 in
  blue.
- At 2 plane px green reads 0.341 to 0.165 with a rolled-covariance floor of
  0.113 (smooth scene structure shared by the means, not sensor pattern);
  the witness reads 0.331 to 0.106 (10 %).
- Why the first form (a hard gate keeping a sample only where the local
  energy is under 1.25 times the noise model's) did worse: the pattern's own
  energy is a tenth to a quarter of the noise energy, so bright smooth areas
  sit at the threshold; the gate rejected 55 % of all samples and biased the
  map 10 % small (a 24-plane test: slope against the burst 0.771 gated,
  0.846 at a gate of 2.0, 0.860 ungated), and one in five photosites had
  less than half its prior's weight in data. With inverse-energy weights
  the same 98 planes give a median of 392 samples per photosite and 2.5 %
  of photosites under half weight.
- The stored burst map fails because it is 32 frames at a low level: its
  per-photosite noise is about 0.3 %, as large as the pattern, and its
  static defocused scene adds 0.07-0.13 % (the corrected stack's covariance
  with the other burst turns negative, -0.07 %). Round 1's capture request
  already asks for 256 frames near half scale and a nudged target for those
  two reasons.

What the test does not cover: the map applied to the frames it was built
from. A photosite's map then contains a few per cent of the scene detail
that was in focus on it (in-focus frames are down-weighted, not excluded),
which would shave that detail by the same few per cent. Building each
frame's map from frames at least 20 planes away removes the coupling and is
what the held-out test measured. Fooled by: the smooth-tile score cannot see
what the map does inside texture; a subject that never leaves a region
smooth (none of this frame: 97 % of photosites collected full weight).

Cost in the prototype: one pass over the raw frames (four Gaussian filters
per CFA plane); 392 frames took 40 s on the GPU with the decoded members
already in the file cache.

## R2. Exposure

[self-flat.py](self-flat.py) histograms every raw sample of the stack:

| Channel | p50 | p99 | p99.9 | p99.999 | of 14 848 DN |
| --- | --- | --- | --- | --- | --- |
| Red | 1 828 | 3 534 | 4 030 | 4 774 | 32 % |
| Green | 3 658-3 688 | 6 974 | 7 998 | 9 362-9 392 | 63 % |
| Blue | 1 488 | 2 882 | 3 348 | 3 968 | 27 % |

0.0006 % of green samples exceed 9 500 DN, where the photon-transfer slope
starts to fall, and none comes within 5 % of white. Green cannot take more
exposure without entering the compressed range; red and blue use a third
and a quarter of the sensor's range. DERIVED: light balanced so that red and
blue reach green's level (magenta filtration with the exposure lengthened,
or a tunable source) would give red 2.0 times and blue 2.4 times the
photons at the same green level: 0.71 and 0.65 of today's shot-noise
amplitude in those channels. No capture exists to confirm it. The response
curve above 9 500 DN was not measured further: nothing in this stack is up
there.

## R3. Frame registration

[series-focus.py](series-focus.py) on 33 single-group renders (planes
84-116, [series-frames.ps1](series-frames.ps1): raw carry, no restoration, profile lateral
colour). 288 tiles of 256 px (stride 128) with a clear focus peak between
frames 92 and 108. Each frame's displacement against the tile's focus frame
is the phase ramp of the green cross-spectrum over 0.03-0.30 cycles/px.

| Lag, frames | -8 | -4 | -2 | -1 | +1 | +2 | +4 | +8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rms, px | 0.442 | 0.319 | 0.200 | 0.133 | 0.135 | 0.254 | 0.477 | 1.105 |
| after one similarity per frame pair | 0.280 | 0.091 | 0.042 | 0.020 | 0.022 | 0.036 | 0.073 | 0.146 |
| fitted scale, ppm | +78 | +28 | +11 | +15 | -11 | -25 | -36 | -77 |

- The scale term is linear in the lag at about -10 ppm per plane against a
  magnification step of 124 ppm per plane. Tiles of 128 and 64 px give the
  same (-5 to -11 ppm per plane; 0.12-0.14 px at one plane).
- On the coin (2026-11-15) a similarity left 0.33 px of 0.53 at five frames,
  most of it one fixed pattern. On the matte scarab it leaves 0.09-0.12 of
  0.35-0.60: the coin's remainder was its specular highlights.
- Cost: a matched-weight average over +-8 frames, registered per tile
  against unregistered, keeps 0.993 / 0.966 / 0.943 / 0.938 / 0.927 / 0.914
  of the green signal power at 0.045 / 0.08 / 0.13 / 0.20 / 0.28 / 0.37
  cycles/px.
- Control: a shift of (0.30, -0.20) px planted on a tile's spectrum is
  returned exactly. That shows the estimator is unbiased for a pure shift;
  its noise is bounded by the one-plane residual after the similarity,
  0.02 px.

## R4. What the frames around a point's focus hold

### Per pixel (MEASURED)

[point-focus.py](point-focus.py): every pixel labelled by the full
render's election winner at plane band 1 (decoded, see the instrument note;
kept where band 2's winner agrees within two frames; 3.94 million pixels
with labels 92-108). Band coefficients of each of the 33 frames at those
pixels; products between frames averaged over pixels (noise-free off the
diagonal). Bands: fine `c - G(c, 1)`, mid `G(c, 1) - G(c, 2)`, coarse
`G(c, 2) - G(c, 4)`, output pixels.

Power through focus, green fine band, relative to its peak, at -7.5 ... +7.5
frames from the label: 0.35 0.41 0.47 0.54 0.62 0.71 0.80 0.89 0.96 0.99
1.00 0.98 0.92 0.84 0.75 0.65.

| Green, uniform window centred on the band's own focus | 3 frames | 5 | 7 | 11 | 17 (on the label) |
| --- | --- | --- | --- | --- | --- |
| fine: amplitude kept / signal-to-noise in best frames | 0.99 / 2.9 | 0.95 / 4.5 | 0.90 / 5.7 | 0.80 / 7.0 | 0.64 / 7.1 |
| mid | 1.00 / 3.0 | 0.98 / 4.8 | 0.96 / 6.5 | 0.91 / 9.2 | 0.82 / 11.5 |
| coarse | 1.00 / 3.0 | 0.99 / 4.9 | 0.98 / 6.8 | 0.96 / 10.1 | 0.91 / 14.0 |

- Positive matched weights over +-8 frames: 7.6 (fine), 11.8 (mid), 14.0
  (coarse) best frames. The fine band is at its ceiling inside the window;
  mid and coarse are cut off by it.
- The sum of the frames' own powers (what ideal weights could use if every
  frame carried the same image) reads 12.6 in the fine band, and a rank-2
  fit 10.6. The gap to 7.6 is at least partly label error (pixels pooled at
  slightly wrong depths), and the tile-level test above found no smooth
  phase to recover, so it is not counted as headroom.
- Placebo (labels rolled 400 px): the profile turns monotone across the
  window, the label holds 0.54-0.75 of the peak, matched weights give 4.4.
- Per channel, peak of the fine band against green's: red about +3 to +3.5
  frames, blue about +2 to +2.5; of the mid band, red +4, blue +2. At
  green's peak red's fine band holds 0.86 of its own peak power (0.93 of
  the amplitude), blue's 0.92 (0.96); mid band 0.87 and 0.95. The tile
  measure agrees (red 0.79-0.97, blue 0.89-0.96 over 0.06-0.42 cycles/px).

### What the election does with them (MEASURED)

[weight-dump.py](weight-dump.py) on the default render's
`STREHL_PYRAMID_WEIGHT_DUMP`. Noise-equivalent frames (participation ratio
of the weights) and the share of coefficients the ensemble gate sent to the
plain mean of all 196 frames:

| Plane band | Bright textured | Bright smooth | Smooth, averaged outright | Dark |
| --- | --- | --- | --- | --- |
| 0 (finest) | 6.9 | 5.6 | 39.6 % | 6.4 |
| 1 | 11.1 | 5.4 | 18.6 % | 6.1 |
| 2 | 15.5 | 7.0 | 0 % | 10.1 |
| 3 | 20.0 | 10.2 | 0 % | 13.8 |

Where there is no detail the weights follow noise and concentrate, so smooth
areas get fewer frames than textured ones. Half-stack noise per unit level
confirms it ([noise-by-class.py](noise-by-class.py); green; classes from
the full render):

| Scale, px | Election, smooth / textured | Fusion / election, smooth (amplitude) | Fusion / election, textured (amplitude) |
| --- | --- | --- | --- |
| 0-1 | 1.09 | 0.59 | 0.74 |
| 1-2 | 1.15 | 0.46 | 0.64 |
| 2-4 | 0.77 | 0.40 | 0.64 |
| 4-8 | 0.82 | 0.38 | 0.66 |

(The textured figures include inter-half texture differences and are upper
bounds on the noise ratio.) Fusion here is the shipped, uncalibrated one;
round 1's calibration multiplies its finest band by 1.3 and the next by
1.05.

DERIVED: the election's fine-band signal-to-noise is about 4 best frames
(round 1 measured the calibrated fusion at 1.9 times the election; the
fusion's level-0 window sits at the 7.6 ceiling). So calibrated fusion
takes what the frames hold in the fine band; nothing wider is worth
building there.

### Per-band focus (unresolved)

Over tiles the 0.42-0.50 cycles/px annulus peaks 6 frames before the
0.16-0.24 band and holds 0.43-0.60 of its own peak power at that band's
focus (the smaller the tile, the lower). Per pixel the fine band peaks 0.9
frames after the mid band, the opposite sign. The two do not measure the
same bands (annuli against broad differences of Gaussians) and the tile
figure is exposed to depth mixing. Not used; listed as an open question.

## R6. Locally adaptive restoration (null)

[adaptive-restore.py](adaptive-restore.py) on the existing half-stacks:
`adaptive = merge + m (restored - merge)`, `m` the Wiener weight of the
restoration's increment from its local energy against its noise.

| Arm (green; mask from the other half) | Bright textured | Bright smooth | Dark |
| --- | --- | --- | --- |
| mean mask | 0.98 | 0.58 | 0.72 |
| noise against the global restoration | 0.997 | 0.979 | 0.990 |
| error against the independent half | 0.998 | 0.983 | 0.993 |
| share of the increment kept | 0.990 | 0.954 | 0.993 |

The control (mask forced to one) reads 1.000 everywhere; the mask from the
scored half reads within 0.004 of the cross arm. The restoration's increment
carries little of the image's noise, so withholding it buys nothing. Grain in
smooth areas is the merge's (R4), not the restoration's.

## R7. Channel registration

### The displacement depends on scale (MEASURED)

[channel-shift.py](channel-shift.py) (`--band` added) on the scarab
half-stacks rendered with the profile only (`h-f-carryraw-*`), 222 in-focus
tiles, radial model (offset plus scale) fitted to per-tile displacements:

| Band, cycles/px | Red: scale, ppm | Red: rms, px | Blue: scale, ppm | Blue: offset y, px | Blue: rms, px |
| --- | --- | --- | --- | --- | --- |
| 0.02-0.05 | -110 | 0.47 | -28 | +0.31 | 0.45 |
| 0.05-0.08 | -75 | 0.23 | +9 | +0.29 | 0.31 |
| 0.08-0.11 | +29 | 0.25 | -11 | +0.22 | 0.27 |
| 0.11-0.14 | +171 | 0.50 | -58 | +0.14 | 0.28 |
| 0.14-0.18 | +297 | 0.74 | -112 | +0.07 | 0.34 |
| 0.18-0.24 | +387 | 0.93 | -154 | +0.03 | 0.40 |
| 0.24-0.32 | +423 | 1.03 | -174 | +0.02 | 0.44 |
| 0.32-0.42 | +428 | 1.04 | -172 | 0.00 | 0.43 |

- In the two finest bands the radial model leaves 0.06-0.08 px (red) and
  0.05 px (blue): the fine displacement is one number per channel.
- The profile's applied scales are -464.6 (red) and +205.6 ppm (blue). The
  fine residuals are 92 % and 84 % of those with the opposite sign: fine
  detail in red and blue lies within about 35 ppm of green in the raw frame
  and the correction moves it away.
- [channel-register.py](channel-register.py), the same estimator on one
  image (channels of a raw-carry render have independent noise), reproduces
  the half-stack figures (blue offset +0.207, -54.8 ppm; red +91.8 ppm over
  0.03-0.30) and fits on one checkerboard colour of the tiles while scoring
  the other: fine-band validation rms 1.06 to 0.07 px (red), 0.44 to 0.05
  (blue).
- Single frames show it too ([series-focus.py](series-focus.py), fine band,
  red against green in the tile's focus frame: +449 ppm, 1.53 px rms to
  0.06 after the model).
- With the fine displacement removed, cross-half coherence with green at
  0.25 / 0.30 / 0.35 / 0.40 cycles/px: red 0.43 / 0.41 / 0.38 / 0.34 (as
  rendered 0.24 / 0.17 / 0.12 / 0.09; rolled-displacement placebo 0.16 /
  0.08 / 0.03 / 0.00), blue 0.60 / 0.54 / 0.49 / 0.46 (0.54 / 0.46 / 0.40 /
  0.37; placebo 0.50 / 0.41 / 0.33 / 0.29).

### In the raw frames, and what the fine part is (MEASURED)

[raw-channel-shift.py](raw-channel-shift.py): the same estimator on groups
assembled from the member cache at their integer offsets (nothing
interpolated, no lateral-colour correction, no merge; a site's red, green
and blue samples come from different exposures, so within-group
cross-spectra carry no common noise). Planes 20, 60, 100, 140, 180; 1 087
in-focus tiles; offset plus radial scale per band:

| Band, cycles/px | Red: scale, ppm | Red: offset, px | Blue: scale, ppm | Blue: offset, px |
| --- | --- | --- | --- | --- |
| 0.03-0.08 | -539 | (-0.10, -0.40) | +166 | (+0.05, +0.16) |
| 0.08-0.14 | -210 | (-0.06, -0.18) | +99 | (0.00, +0.10) |
| 0.14-0.24 | -39 | (-0.01, +0.07) | +27 | (0.00, -0.08) |
| 0.24-0.42 | -16 | (0.00, +0.07) | +6 | (0.00, -0.04) |

So the dependence is in the sensor data, not made by the product's gather:
adding the profile's -464.6 and +205.6 ppm to the render's residuals gives
the same figures. The slide's raw frames (two groups, 300 tiles) read one
scale at every band: red -251 / -241 / -244 / -250 ppm, blue +17 / +54 /
+65 / +68.

[raw-leak-kernel.py](raw-leak-kernel.py): the transfer of green into red
and blue in the raw frame, `T(f) = sum Re(F_c conj F_G) / sum Re(F_Ga conj
F_Gb)` (the two green samples of a site give a noise-free green power),
1 955 in-focus tiles of nine planes, raw units:

| cycles/px | 0.18 | 0.225 | 0.275 | 0.325 | 0.375 | 0.425 |
| --- | --- | --- | --- | --- | --- | --- |
| red, within 15 degrees of an axis | 0.227 | 0.222 | 0.219 | 0.215 | 0.215 | 0.229 |
| red, within 15 degrees of a diagonal | 0.231 | 0.223 | 0.216 | 0.208 | 0.199 | 0.186 |
| blue, axes | 0.232 | 0.207 | 0.185 | 0.176 | 0.189 | 0.244 |
| blue, diagonals | 0.215 | 0.193 | 0.172 | 0.156 | 0.148 | 0.140 |
| what crosstalk from the four adjacent green photosites would give, axes (x k) | 0.72 | 0.58 | 0.42 | 0.27 | 0.13 | 0.03 |
| the same, diagonals | 0.70 | 0.55 | 0.36 | 0.15 | -0.06 | -0.27 |

Red's transfer is flat within 5 % on the axes and does not change sign on
the diagonals: the green-coherent fine detail in red is green's image at
the same site, not a neighbour's. DERIVED: it is light of green's band
passed by the red filter (and by the blue one), which the lens images where
it images green. At most about a seventh of it could be neighbour crosstalk
(the diagonal figure falls 19 % from 0.18 to 0.425 cycles/px where a
crosstalk kernel would fall 140 %). The rise in the last axis bin (0.44 for
red and 0.66 for blue at 0.475) is the member-mismatch pattern of round 1's
Q6, which every channel of a group shares. Below 0.18 cycles/px T rises
(0.40 at 0.06): there the channels' own content is coherent too.

On a neutral subject the share predicts the mixture's displacement: 0.2 of
green's raw signal is 0.39 of a white subject's red signal, so the mixture
should sit at 0.61 of the own band's -865 ppm, -528; the scarab's coarse
band reads -539.

### What the product's own refinement does with it (MEASURED)

The default per-capture refinement measures one displacement per channel on
a preview merge and applies it. On this stack it applied red (-0.092,
-0.115) px and -12.6 ppm, blue (+0.039, +0.245) px and -34.2 ppm. By the
0.03-0.30 estimator the refined full render reads red 0.399 px rms (0.333
unrefined) and blue 0.125 (0.313). Its fine band still reads red +431 ppm
with offset (0.09, 0.14) and blue -138 ppm with offset (-0.04, -0.20): the
refinement fixed blue's coarse offset and moved blue's fine detail by the
same 0.2 px. The earlier unresolved disagreement between the refinement's
instrument and `lateral-profile.py` (full-potential results) is this: each
instrument has a passband and the displacement is not the same in all of
them.

### A model that fits: own band plus a green-band share (MEASURED)

[leak-fix.py](leak-fix.py). A carried channel is taken as its own band plus
a share `a` of the green band, `C = C_own + a G`: the colour filters'
passbands overlap, and the part of a channel's light that lies in green's
band images where green does. The profile's scale is right for `C_own` and
displaces `a G`. The merge applies one set of weights to every plane, so
the repair commutes with it and can be made on the finished image:
`C_fixed = warp(C - a warp(G, 1 - eps), 1 + delta) + a G`, `eps` the fine
displacement above, `delta` the extra scale the own band needs.

Scarab, cross-half scores (displacement by band, coherence with green, and
the colour-difference power the halves share):

| Arm | Scale coarse / mid / fine, ppm | rms, px | Coherence | Colour-difference power |
| --- | --- | --- | --- | --- |
| red as rendered | -97 / +237 / +425 | 0.28 / 0.62 / 1.03 | 0.956 / 0.598 / 0.171 | 1 / 1 / 1 |
| red, a 0.35 | -288 / -77 / -1 | 0.69 / 0.26 / 0.06 | 0.945 / 0.665 / 0.414 | 1.03 / 0.86 / 0.71 |
| red, a 0.35, delta -400 ppm | -76 / +34 / +14 | 0.26 / 0.16 / 0.08 | 0.959 / 0.676 / 0.399 | 0.85 / 0.83 / 0.72 |
| red placebo (eps reversed, a 0.3) | +76 / +328 / +214 | 0.31 / 0.84 / 0.61 | 0.953 / 0.622 / 0.341 | 0.97 / 0.98 / 0.89 |
| blue as rendered | -1 / -87 / -173 | 0.34 / 0.31 / 0.43 | 0.975 / 0.821 / 0.460 | 1 / 1 / 1 |
| blue, a 0.42, delta +80 ppm | +14 / -12 / -3 | 0.32 / 0.17 / 0.05 | 0.976 / 0.833 / 0.534 | 0.97 / 0.94 / 0.87 |
| blue placebo | -48 / -148 / -191 | 0.40 / 0.44 / 0.49 | 0.973 / 0.815 / 0.475 | 1.11 / 1.05 / 1.03 |
| red, a 0.35, delta -400 ppm, own band moved (-0.10, -0.20) px | -76 / +35 / +16 | 0.25 / 0.14 / 0.07 | 0.959 / 0.678 / 0.402 | 0.86 / 0.83 / 0.72 |
| blue, a 0.42, delta +80 ppm, own band moved (0, +0.38) px | +14 / -14 / -7 | 0.15 / 0.11 / 0.05 | 0.980 / 0.838 / 0.537 | 0.84 / 0.91 / 0.86 |

(Bands: displacement 0.03-0.08 / 0.11-0.18 / 0.24-0.42; coherence and power
0.05-0.10 / 0.10-0.25 / 0.25-0.40.) The share `a` is found where the fine
displacement crosses zero (red between 0.3 and 0.4, blue between 0.4 and
0.5), `delta` where the coarse one does. The own bands then sit at about
-865 ppm (red) and +285 ppm (blue), which is what the prototype measured
with each channel at its own focus (-800 / +259). In raw units the shares
are 0.18 (red) and 0.17 (blue) of green's signal (the raw-frame transfer
above reads 0.22 and 0.15-0.19). Blue's own band also sits a uniform 0.38
px from green in y (a decentring term; the profile records a translation
and does not apply it), which is the +0.21 to +0.31 px offset every
coarse-band measurement of blue shows; the green-band share does not have
it. With the own band moved by that offset as well, blue is registered at
every scale (last row).

By eye on the scarab (`r7-crops-a-sat3.png`, colour differences tripled,
origins (1650, 2990), (8000, 1500), (700, 900), 120 px at 4x; columns as
rendered, repaired, shipped smoothing): the difference is small. Red rims at
the outer field thin a little; the purple rims in dark gaps stay.

### The neutral slide (MEASURED)

On the slide (static, one focus position, room light) the displacement is
the same at every scale: red +206 / +220 / +218 / +225 ppm and blue -183 /
-148 / -134 / -140 over the four bands of `channel-register.py`. A neutral
target carries the same structure in every band, so the phase ramp reads the
mixture's mean and cannot separate its parts; sharpness can. Scores with the
1.6 s and 0.6 s renders as independent halves:

| Arm | Red: coherence with green, fine | Red: transfer against green at 0.275 / 0.425 | Red rim excess at 3.5-5 px | Blue rim excess |
| --- | --- | --- | --- | --- |
| as rendered (profile) | 0.338 | 0.51 / 0.25 | 8.2 (green 3.2) | 6.0 |
| one re-fitted scale per channel | 0.553 | 0.61 / 0.34 | 4.9 | 6.5 |
| two components (red a 0.55, delta -100; blue a 0.6) | 0.749 | 0.88 / 0.75 | 3.2 | 6.3 |

(`leak-fix.py`, [channel-transfer.py](channel-transfer.py),
[rim-colour.py](rim-colour.py); rim excess is the dark level near bright
detail minus the far ground, % of the bright level.)

- By eye (`r7-slide-crops.png`, origins (8240, 1500), (1010, 5560), (6850,
  5060), 110 px at 4x): as rendered the dots carry a red rim on one side and
  a blue one on the other; the re-fitted scale removes most of it; the
  two-component render is not visibly better than that. A blue-purple ring
  all round the dots remains in both.
- The slide's parameters (a 0.45-0.55, delta 0 to -100 ppm by the phase
  criterion) differ from the scarab's (0.35, -400): they depend on the light
  and the subject and must be fitted per stack.
- Caution: on a neutral target a larger `a` always lowers the colour
  difference (it copies green into red), and the repaired red's fine
  amplitude reads 1.08-1.23 of green's at a 0.55, which is too much for a
  re-registered channel. The transfer figures of the third row are inflated
  by that; the rim figure is not (it is a mean level). Fit `a` on phase, not
  on colour difference.

## R8. Rig stability

`members.jsonl` of the scarab run (196 groups, residuals of members 2-4
against member 1 as the product measured them): mean offsets (0.00, 0.05),
(0.00, 0.04), (-0.01, -0.01) px; scatter about the mean 0.047-0.076 px per
axis for every member (no growth from member 2 to 4, so no drift within a
group); magnitude median 0.08, 90th percentile 0.14-0.15, largest 0.32.
Member gains agree within 0.08-0.11 % rms. The static slide groups of the
calibration campaign read 0.05-0.13. A position scatter of 0.05 px inside
an exposure would cost 0.8 % of the contrast at 0.4 cycles/px.

## R9. Response outliers

Self map (full stack, at least 150 samples) against the burst map, same
sign in both: beyond 2 %: 17 (red), 18 (green), 121 (blue) photosites;
beyond 3 %: 5, 4, 9; beyond 5 %: none. The dark campaign found no photosite
50 DN above black at this exposure. No defect handling is needed beyond the
flat field.

## R10. By eye, and what it led to

[survey-crops.py](survey-crops.py), default render beside the single-shot
render.

- Clean defocused background, no banding (`r10-b.png`, origin (8600, 200)).
- **Coloured glints** (`r10-specks-a.png`, origins (8408, 5028), (8424,
  5066), (8442, 4966), 48 px at 6x): point-like bright specks on dark
  cuticle are 2-3 px across (the diffraction core at this aperture) and come
  out green, orange-to-blue across their length, or blue in the four-shot
  renders. The single-shot render shows them in the same places, paler. The
  shipped fusion erases the two faint ones and turns the third into a 25 px
  blur (its depth map does not know them). They are the smallest features
  in the frame and show every chromatic error at once; nothing is proposed
  for them specifically.
- **Rim colour** ([rim-colour.py](rim-colour.py); classes from the other
  half-stack; % of the bright level; the far ground is neutral within 0.1):

| Dark pixels, distance from bright | 3.5-5 px | 5-7 | 7-10 | 10-15 | 15-30 |
| --- | --- | --- | --- | --- | --- |
| default render: green level | 11.05 | 10.19 | 8.70 | 6.93 | 5.48 |
| red minus green | +2.74 | +2.23 | +1.66 | +1.26 | +1.02 |
| blue minus green | +2.77 | +2.38 | +1.54 | +0.65 | +0.01 |
| merge only, profile lateral colour, no refinement, no restoration (odd half): red minus green | +4.79 | +3.30 | +2.15 | +1.49 | +1.14 |
| blue minus green | +0.85 | +1.63 | +1.45 | +0.71 | +0.06 |
| default render with chroma as carried: red / blue minus green | +3.67 / +2.67 | +2.57 / +2.27 | +1.77 / +1.47 | | |

  Red's excess does not grow with radius (+2.3 to +2.5 from the centre to 0.8
  of the half diagonal, +4.8 beyond); the two-component repair removes the
  part that does (to +1.7 at 0.4-0.8, +3.4 beyond). From 15 px outward the
  red excess (+0.8 to +1.1) is the beetle: brown cuticle shows between the
  scales, and the neutral slide reads +0.4 there.
- **The pooled figure hides a displacement.** Blue's jump between the
  merge-only row and the restored rows is not the restoration (like for
  like, `h-f-carry-odd` against `h-f-carry-restore-odd`, the restoration
  moves blue minus green by +0.2 and red minus green by -0.35). It is the
  registration of blue. By side (dark pixels 3.5-10 px from bright detail,
  split by where the nearest bright pixel lies; red minus green, blue minus
  green):

| Render | Bright above | Bright below | Bright left | Bright right | Blue, above minus below |
| --- | --- | --- | --- | --- | --- |
| merge only, profile | +1.91, +3.21 | +2.62, +0.73 | +2.04, +1.22 | +3.41, +2.15 | +2.48 |
| whole channel re-fitted (what the refinement does) | +2.29, +2.36 | +2.54, +1.24 | +1.91, +1.56 | +3.80, +1.91 | +1.13 |
| two-component repair with own-band offsets | +1.59, +2.42 | +1.96, +1.18 | +1.24, +1.28 | +1.89, +2.06 | +1.25 |
| default render | +1.76, +2.46 | +1.75, +1.45 | +1.76, +1.51 | +2.50, +2.27 | +1.01 |

  As carried, blue's rim differs by 2.5 points between the two sides of
  bright detail (blue is displaced in y); either correction halves that,
  and the dark pixels are not spread evenly around bright detail, so the
  pooled mean moves. The two-component repair gives red the smallest and
  most even rim (+1.2 to +2.0; the whole-channel re-fit leaves +1.9 to
  +3.8). What is left, about +1.2 to +2.4 on every side, is not
  displacement.
- **Is the rim the lens or the beetle?** Not answerable on the scarab:
  [edge-match.py](edge-match.py) finds per-band gains that bring red's edge
  spread onto green's within 2 points on both sides of the edge (from +6 /
  -4), with the same figures on the other half-stack, but blue's profile
  shows the scales' margins are bluer than their centres (blue reads 2-3
  points above green inside bright areas 5-20 px from an edge), so an edge's
  colour is partly the subject's.
- **On the neutral slide it is the lens.**
  [channel-transfer.py](channel-transfer.py), amplitude relative to green
  (magnitude, so registration does not enter), in-focus tiles:

| cycles/px | 0.065 | 0.10 | 0.14 | 0.18 | 0.225 | 0.275 | 0.325 | 0.375 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| blue, measured | 0.95 | 0.91 | 0.87 | 0.82 | 0.81 | 0.78 | 0.81 | 0.85 |
| blue, the restoration's model | 1.01 | 1.02 | 1.04 | 1.06 | 1.10 | 1.14 | 1.20 | 1.29 |
| red, measured (as rendered) | 0.96 | 0.91 | 0.86 | 0.84 | 0.86 | 0.91 | 0.99 | 1.03 |
| red, the restoration's model | 0.99 | 0.98 | 0.96 | 0.94 | 0.91 | 0.87 | 0.82 | 0.74 |

  The restoration takes each channel's transfer from diffraction at its
  nominal wavelength, so it treats blue as the sharpest channel and gives it
  the least gain (scarab log: system to restored at 0.2 / 0.3 cycles/px,
  blue 0.56 to 0.65 and 0.36 to 0.35; green 0.54 to 0.67 and 0.32 to 0.39).
  Measured, blue is the softest at mid frequencies. Red's measured curve
  above 0.3 is not a clean transfer (it contains the displaced green-band
  share). Fooled by: the slide was lit by room light and sits at one focus
  position, tilted; the ratios belong to that light and to green's focus.
- **Borrowing those ratios for the scarab**
  ([equalise-channels.py](equalise-channels.py): red and blue filtered by
  one over the slide's ratio up to 0.30 cycles/px, gains 1.02 / 1.10 / 1.17
  / 1.18 / 1.05 (red) and 1.03 / 1.10 / 1.17 / 1.23 / 1.26 (blue) at 0.05 /
  0.10 / 0.15 / 0.20 / 0.30; applied to the repaired merge-only half):

| Dark pixels, distance from bright | 3.5-5 px | 5-7 | 7-10 | 10-15 |
| --- | --- | --- | --- | --- |
| red minus green: before | +4.12 | +2.59 | +1.66 | +1.22 |
| equalised | +3.10 | +2.07 | +1.52 | +1.23 |
| placebo (the inverse filter) | +5.06 | +3.07 | +1.80 | +1.21 |
| blue minus green: before | +0.81 | +1.58 | +1.42 | +0.70 |
| equalised | -0.34 | +1.00 | +1.25 | +0.72 |
| placebo | +1.88 | +2.14 | +1.59 | +0.69 |

  By eye with colour differences tripled
  (`r10-registration-crops-sat3.png`, origins (8000, 1500), (1650, 2990),
  (5200, 5300), 110 px at 4x; columns merge only, whole-channel re-fit,
  two-component repair, the same equalised): the purple in dark gaps at the
  outer field and the red seams between scales fade from left to right and
  are nearly neutral in the last column. At normal saturation the
  difference is slight.

## R11. A short-wavelength detail exposure

Pixel shift samples blue at every site, and diffraction favours blue
(cutoff 0.70 against 0.61 cycles/px), which suggested a blue-lit stack for
detail. The measured blue transfer above (0.78-0.87 of green) says this lens
setting does not deliver the advantage. Not pursued.

## Commands

```sh
E=experiments/a7cr-fourshot-quality-2026-11-16; O=outputs/a7cr-fourshot-quality; R=outputs/scarab-rgb
# R10 crops
python -X utf8 $E/survey-crops.py $O/r10-a.png 180 3 1.6 $O/default-full.tif,outputs/scarab/single.tif 6800,2200 1650,2950 3850,3180
python -X utf8 $E/survey-crops.py $O/r10-specks-a.png 48 6 6 $O/default-full.tif,$O/rawchroma-full.tif,$R/h-f-carry-fusion-restore-odd.tif,outputs/scarab/single.tif,outputs/scarab/remosaic.tif 8408,5028 8424,5066 8442,4966
# R5 / R4: weight dump of the default render
pwsh -File outputs/peak-run.ps1 $O/wd/default-wd.log "STREHL_PIXEL_SHIFT=remosaic;STREHL_PYRAMID_WEIGHT_DUMP=outputs/a7cr-fourshot-quality/wd/default" stack <four-shot run> --demosaic --out $O/wd/default-wd.tif
python -X utf8 $E/weight-dump.py $O/r5-weight-dump.json $O/wd/default $O/wd/default-wd.tif
python -X utf8 $E/noise-by-class.py $O/default-full.tif $R/h-f-carry-odd.tif $R/h-f-carry-even.tif      # and the fusion halves
# R7
python -X utf8 $E/channel-register.py $O/r7-rawchroma-full.json $O/rawchroma-full.tif [--band LO,HI]     # and h-f-carryraw-odd, one-100, the slide
python -X utf8 $E/channel-shift.py $O/r7-channel-shift-fine.json $R/h-f-carryraw-odd.tif $R/h-f-carryraw-even.tif --band 0.16,0.42   # and eight bands
python -X utf8 $E/leak-fix.py $O/r7-leak-fix.json $R/h-f-carryraw-odd.tif $R/h-f-carryraw-even.tif
python -X utf8 $E/leak-fix.py $O/r7-leak-fix-final.json (same) --a-r 0.35 --a-b 0.42 --delta-r=-400e-6 --delta-b=80e-6 --write $O/r7-repaired
pwsh -File outputs/peak-run.ps1 $O/slide-1p6s.log "STREHL_PIXEL_SHIFT=remosaic;STREHL_CARRY_RGB=raw;STREHL_OPTICAL_RESTORE=off" stack D:/StrehlCaptures/stack-1794683752817-11226 --demosaic --refine-ca=off --out $O/slide-1p6s.tif   # and -1794683631859 as slide-0p6s
python -X utf8 $E/leak-fix.py $O/r7-slide-leak.json $O/slide-1p6s.tif $O/slide-0p6s.tif --a-r 0,0.2,0.35,0.5 --a-b 0,0.2,0.42,0.6 --delta-r=215e-6,0,-200e-6,-400e-6,-600e-6 --delta-b=-140e-6,0,80e-6,160e-6
python -X utf8 $E/channel-transfer.py $O/r10-transfer-asis.json $O/slide-1p6s.tif $O/slide-0p6s.tif      # and the repaired pairs
python -X utf8 $E/rim-colour.py $O/r10-rim-colour.json $R/h-f-carry-even.tif $O/default-full.tif $O/rawchroma-full.tif $R/h-f-carryraw-odd.tif $O/r7-repaired-odd.tif $R/h-f-carry-fusion-odd.tif
python -X utf8 $E/edge-match.py $O/r10-edge-match $R/h-f-carry-even.tif $O/r7-repaired-odd.tif $R/h-f-carry-odd.tif $O/r7-repaired-even.tif
python -X utf8 $E/raw-channel-shift.py $O/r7-raw-scarab.json outputs/scarab-fp/cache4 --planes 20,60,100,140,180
target-ui/release/examples/a7cr_export_members.exe D:/StrehlCaptures/stack-1794683752817-11226 $O/slide-members
python -X utf8 $E/raw-channel-shift.py $O/r7-raw-slide.json $O/slide-members --planes 1,5
python -X utf8 $E/raw-leak-kernel.py $O/r7-raw-leak-kernel.json outputs/scarab-fp/cache4 --planes 20,40,60,80,100,120,140,160,180
python -X utf8 $E/leak-fix.py $O/r7-leak-fix-full.json $R/h-f-carryraw-odd.tif $R/h-f-carryraw-even.tif --a-r 0.35 --a-b 0.42 --delta-r=-400e-6 --delta-b=80e-6 --t-r=-0.10,-0.20 --t-b=0.0,0.38 --write $O/r7-repaired2
python -X utf8 $E/channel-register.py $O/r7-whole-odd.json $R/h-f-carryraw-odd.tif --apply $O/r7-whole-odd.tif
python -X utf8 $E/cross-channel.py $O/r7-cross-channel-repaired.json $O/r7-repaired-odd.tif $O/r7-repaired-even.tif
python -X utf8 $E/equalise-channels.py $O/r10-equalised-odd.tif $O/r7-repaired-odd.tif $O/r10-transfer-asis.json            # and --invert
python -X utf8 $E/rim-colour.py $O/r10-rim-sides.json $R/h-f-carry-even.tif $R/h-f-carryraw-odd.tif $O/r7-whole-odd.tif $O/r7-repaired2-odd.tif $O/default-full.tif $O/rawchroma-full.tif
# R3 / R4: the frame series
pwsh -File $E/series-frames.ps1 -First 84 -Last 116
python -X utf8 $E/series-focus.py $O/r4-series-focus $O/series 84 116            # also --tile 128 --stride 128, --tile 64 --stride 128
python -X utf8 $E/point-focus.py $O/r4-point-focus.json $O/series 84 116 $O/wd/default
python -X utf8 $E/phase-coherence.py $O/r4-phase-coherence.json $O/series $O/r4-series-focus.npz
python -X utf8 $E/rank-check.py $O/r4-series-focus.npz
# R1 / R2 / R9
python -X utf8 $E/self-flat.py $O/r1-self-flat.json outputs/scarab-fp/cache4 $O/q2-prnu-map.npy --save $O/r1-self-map.npy                  # hard gate, whole stack; also prints R2
python -X utf8 $E/self-flat.py $O/r1-sf-soft-a.json outputs/scarab-fp/cache4 $O/q2-prnu-map.npy --planes 1-98 --soft --save $O/r1-sf-soft-a.npy
python -X utf8 $E/self-flat-shrink.py $O/r1-map-soft-a-shrunk.npy 0.0030,0.0035,0.0040 $O/r1-sf-soft-a
python -X utf8 $E/fpn-raw.py $O/r1-fold-a-soft-fixed.json outputs/scarab-fp/cache4 $O/ptc-1794684439651 --planes 120,145,170,190 --group 4 --apply $O/r1-map-soft-a-shrunk.npy --select-raw   # and none, gated, --roll, the burst map, the other fold
# R6
python -X utf8 $E/adaptive-restore.py $O/r6-adaptive-restore.json $R/h-f-carry-odd.tif $R/h-f-carry-even.tif $R/h-f-carry-restore-odd.tif $R/h-f-carry-restore-even.tif
```

Instrument faults found and fixed before the numbers above: the weight
dump's frame numbering (decoded and checked, see the notes); a first
per-pixel run with undecoded labels (flat profiles, discarded); the
self-flat's hard gate (kept in the table as an arm, since it is the obvious
first design); `leak-fix.py`'s argument parser dropped `--delta-r=...`
values in its first run (the first sweep ran at delta 0 only, as its output
showed). A first reading of the rim table blamed the restoration for
blue's rim; the like-for-like halves and the by-side split corrected it
before this file was finished. The score `left` printed by `self-flat.py` divides by the burst's
own split-half covariance, which contains the burst's scene; it is not used
above.
