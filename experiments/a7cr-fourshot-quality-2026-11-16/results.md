# A7CR four-shot quality: investigation results (2026-11-16)

Status: investigation, author-run, not independently reviewed. No product
code changed, nothing committed. One subject (the white scarab, matte), one
rig setting (FE 100 mm macro with 2x converter, wide open, N_eff about 12,
ISO 100, 0.6 s). The [brief](brief.md) fixed the questions and controls
first. The recommendations drawn from this are in
[the proposal](../../docs/proposals/2026-11-a7cr-four-shot-quality-improvements.md).

Nothing here rests on an A7C II result. Where an older finding bore on a
question (sensor pattern, the gather kernel, restoration being
noise-limited) it was re-measured on A7CR four-shot data, or only its
camera-independent arithmetic was used.

Inputs: four-shot run `D:/StrehlCaptures/stack-1794786793543-11226` (196
groups), single-shot run `stack-1794785495615-11226`, calibration bursts
`stack-1794684207243`, `-4263347`, `-4439651` (16 x 0.6 s, 32 x 2.5 s,
16 x 6 s of a defocused scene), the prototype's member cache
`outputs/scarab-fp/cache4`, and the half-stack renders in
`outputs/scarab-rgb/`. New renders: `target/release/strehl.exe`, build
`cbca976b7e96-dirty` of 2026-11-16 02:12, CPU fold, 32 threads. Python 3,
torch 2.11 (CUDA), RTX 5090. Outputs in ignored
`outputs/a7cr-fourshot-quality/`.

## Summary

| # | Question | Answer | Label |
| --- | --- | --- | --- |
| Q1 | Do red and blue carry fine detail the output discards? | Yes, and not the kind expected. The three channels' fine detail is largely independent on this subject (red-green coherence 0.54 at 0.15 cycles/px, 0.18 at 0.30), so a joint filter gains nothing (1.00-1.07x), but the shipped 1 px chroma smoothing replaces real red and blue detail with green's: in 0.10-0.25 cycles/px it raises red's error from 3 % to 23 % of red's signal power, and in 0.25-0.40 to 133 % | MEASURED |
| Q2 | Sensor fixed pattern | 0.30 / 0.35 / 0.40 % of level per red / green / blue photosite. Four-shot assembly copies each photosite onto a 2 x 2 block of output pixels, which moves the pattern out of the top frequencies and quadruples its density at low ones. It is 25-29 % of one gathered group's power in 0.08-0.30 cycles/px (green, midtones), 49 % after a four-group merge, and a flat from the day before predicts it with correlation 0.95-0.97 | MEASURED |
| Q3 | Gather kernel | Each gathered frame's fine noise power swings by 0.48 (peak to peak over mean, per axis) on a 59 px grid, as the kernel's closed form predicts. The grid is not detectable in full merges (excess under 0.03). The kernel's mean loss (0.89 / 0.82 / 0.74 at 0.30 / 0.35 / 0.40 cycles/px, per axis) is not in the restoration's model | MEASURED, DERIVED |
| Q4 | Fusion's dark lift | Real under an independent mask, and mostly not an edge effect: +0.5 to +0.7 % of the bright level everywhere in dark areas, +2.4 % within 6 px of bright edges. One gain per band against the election, with everything coarser than 32 px taken from the election, removes the far part and two thirds of the near part and keeps the fusion's signal-to-noise (23-25 against the election's 12-13) | MEASURED (post-merge prototype) |
| Q5 | Finest detail in coarse pyramid levels | The fusion's loss against the election is flat at 0.82 from 0.24 to 0.38 cycles/px, then falls to 0.59 at 0.49; its signal-to-noise gain falls from 2.8x at 0.15 to 1.0x at 0.47 and 0.74x at 0.49. The knee sits where output detail moves into plane levels 1 and 2 | MEASURED, mechanism ARGUED |
| Q6 | Two-photosite-period pattern from member mismatch | Negligible: 0.02 % of level at (0, 0.5), under 0.006 % at the other two points. Residual compensation works: it cuts the noise beyond the cutoff by 34 % against the ungated arm, and the reversed-sign placebo raises it 86 % | MEASURED |
| Q7 | Sub-pixel phase spread of neighbouring planes | Good with ten planes: noise amplification of a 2x reconstruction under 2 on 80 % of the frame, under 4 on 96 % (median 1.14); poor with four (median 7.7) | MEASURED (geometry only) |
| Q8 | By eye | Clean and quiet at 1:1; soft at 3x as diffraction dictates; a faint blue rim at some bright-on-dark edges that the single-shot render also shows | observation |

Three side findings change how earlier numbers should be read:

1. **The half-stack instrument counts three things as signal that are not
   scene**: the sensor pattern (it is the same in both halves), detail the
   election manufactures (below), and, after chroma smoothing, green detail
   copied into red and blue. The fine-detail "signal-to-noise power" of the
   chroma-smoothed arms (red 5.8 to 11.9 in the colour-carry section of the
   full-potential results) was the third.
2. **The election inflates the planes it elects on.** The two native green
   site planes carry 10 % more noise power and 3 % more shared "signal" than
   the two carried green planes in the finest plane band (0.30-0.50
   cycles/plane px); under fusion, whose weights come from a depth map, all
   four agree within 0.3 %.
3. **Merges share a floor beyond the lens's cutoff that single frames do
   not**: 0.17 / 0.47 / 0.17 of the half-stack noise power in the frequency
   corners. It is not sensor pattern (assembly removes that there), not
   member motion (compensated, placebo and ungated arms read the same
   shared power), and the fusion halves it. ARGUED: near-argmax selection
   among frames that sit a fraction of a pixel apart is a nonlinear
   operation and generates harmonics. Size: about 0.15 % of level, in a band
   the lens leaves empty. Not pursued further.

## Q1. Colour detail

[cross-channel.py](cross-channel.py), [channel-shift.py](channel-shift.py),
[chroma-crops.py](chroma-crops.py). Odd/even half-stacks of the four-shot
run with colour carried and not smoothed (`h-f-carryraw-*`, build of
2026-11-15, raw witness gate). 222 in-focus tiles: 112 design, 110
validation (checkerboard of the tile grid).

Cross-channel coherence of what the halves share (design set):

| cycles/px | 0.05 | 0.15 | 0.25 | 0.30 | 0.35 | 0.40 |
| --- | --- | --- | --- | --- | --- | --- |
| red-green | 0.976 | 0.541 | 0.250 | 0.176 | 0.119 | 0.098 |
| blue-green | 0.983 | 0.785 | 0.536 | 0.465 | 0.403 | 0.378 |
| red-blue | 0.948 | 0.404 | 0.084 | 0.047 | 0.028 | 0.041 |

- Not displacement between channels. Per-tile displacement: red against
  green 0.33 px rms (an offset and a radial term leave 0.24), blue against
  green 0.31 px (0.10). Removing each tile's own displacement lifts
  red-green coherence at 0.30 from 0.167 to 0.258; the rolled-displacement
  placebo reads 0.153. The channels' fine detail is different content.
- Not sensor pattern: at 0.15 cycles/px red's shared power is 29 times its
  half-stack noise; the pattern (Q2) is under a twentieth of that.
- By eye ([chroma-crops.py](chroma-crops.py), colour differences
  exaggerated 3-4x, `q1-chroma-4x.png` origins (4700,3100), (2400,2600);
  `q1-chroma-4x-b.png` origins (5200,2700), (3300,3400); 96 px at 4x): the
  scales carry a pastel mottle a few pixels across that sits at the same
  places in the odd and the even half-stack. The single-shot render shows
  the broader patches and not the fine ones.
- The full default render against the same with the smoothing off
  (`default-full.tif`, `rawchroma-full.tif`; `q1-default-vs-rawchroma-4x.png`
  as rendered and `-boost.png` with colour differences 3x, origins
  (4700,3100), (3300,3400)): at normal saturation the two are hard to tell
  apart on this pale subject; exaggerated, the unsmoothed render shows the
  finer mottle and more colour grain with it.
- The single-shot run agrees where it can see: its red-green coherence is
  0.931 and 0.892 at 0.095 and 0.115 cycles/px (four-shot 0.864, 0.753),
  and its demosaic imposes coherence above that (0.85-0.93 throughout, with
  channel noise correlated at 0.6-0.95).

What each treatment costs, validation tiles: mean squared error of the
estimate of a channel's noise-free content, as a percentage of that
channel's signal power (the other half supplies an unbiased reference with
independent noise; lower is better; 100 % is what writing no detail at all
would score).

| Band, cycles/px | Estimator | Red | Green | Blue |
| --- | --- | --- | --- | --- |
| 0.10-0.25 | as carried | 3.4 | 1.1 | 2.9 |
| | own Wiener (no borrowing) | 3.3 | 1.1 | 2.7 |
| | shipped: green + 1 px Gaussian of the difference | 23.5 | 1.1 | 9.2 |
| | joint three-channel Wiener | 3.2 | 1.1 | 2.7 |
| 0.25-0.40 | as carried | 17.5 | 8.1 | 28.3 |
| | own Wiener | 14.7 | 7.4 | 21.6 |
| | shipped | 133 | 8.1 | 105 |
| | joint | 14.7 | 7.5 | 21.1 |
| 0.40-0.50 | as carried | 64 | 29.5 | 82 |
| | own Wiener | 37.7 | 22.4 | 44.6 |
| | shipped | 204 | 29.5 | 139 |
| | joint | 37.5 | 22.4 | 42.7 |

These are half-stack figures; the full stack has half the noise. The
instrument's own check: a scalar Wiener filter's error is S N / (S + N), so
"own" must reproduce the band's directly measured S/N; it reads 1-6 % above
it in every band and channel (a filter that follows frequency inside a band
should sit a little above the band average).

Registered placebo (`--shift-placebo`: red and blue rolled 8 px against
green in both halves): cross-channel coherence above 0.25 cycles/px falls to
0.00 +- 0.04, the joint filter's error equals the per-channel one's to three
figures in every band, and the shipped smoothing's red error in 0.10-0.25
rises from 23.5 % to 40 %. The instrument sees borrowing only where the
channels really agree.

Colour-difference signal against noise, full stack (twice the half-stack
figure), and what each filter keeps of it:

| cycles/px | 0.155 | 0.205 | 0.255 | 0.305 | 0.355 | 0.405 | 0.455 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| red minus green, S/N | 60 | 35 | 23 | 16 | 11 | 6.6 | 3.1 |
| blue minus green, S/N | 31 | 20 | 14 | 9.4 | 6.2 | 3.8 | 2.2 |
| 1 px Gaussian keeps | 0.62 | 0.44 | 0.28 | 0.16 | 0.08 | 0.04 | 0.02 |
| Wiener would keep (red) | 0.98 | 0.97 | 0.96 | 0.94 | 0.92 | 0.87 | 0.76 |

Reading: on this subject the colour differences at fine scale are measured
at signal-to-noise 10 to 60 and the fixed smoothing discards most of them.
The cross-channel borrowing this question set out to test is refuted here.
Fooled by: one subject, and an unusual one (pale scales with a fine colour
sheen); a neutral, colourless subject would show coherence near one and the
smoothing would cost nothing there. A measured filter covers both.

## Q2. Sensor fixed pattern

### Size (MEASURED)

[prnu.py](prnu.py) on the three defocused fixed-focus bursts. Split-half
covariance of the relative high-pass residual (Gaussian 2 plane px) of the
odd- and even-frame means, minus the same with one half rolled (5, 3) plane
px:

| Series | Red | Green 1 | Green 2 | Blue |
| --- | --- | --- | --- | --- |
| 16 x 6 s, 700-8200 DN | 0.297-0.312 % | 0.344-0.365 % | 0.336-0.366 % | 0.387-0.420 % |
| 32 x 2.5 s, 330-3900 DN | 0.314-0.357 % | 0.355-0.373 % | 0.351-0.378 % | 0.400-0.454 % |

- Flat in level above about 500 DN (multiplicative); rising below it (the
  0.3 DN offset pattern of the dark campaign: 0.46 % at 161 DN).
- Temporal noise against the injected model (0.4040 DN/e-, 1.334 DN):
  0.93-0.97 at 2 plane px and 1.00-1.02 at 8 for red and green, so the
  decode and scaling are right. Blue reads 0.86-0.95, the known in-camera
  processing of blue.
- At 4 and 8 plane px the bursts' own covariance grows to 0.5 % and 1.2 %
  with neighbours correlated 0.6-0.95: that is the bursts' static defocused
  scene, not the sensor (next table: the stack does not share it).

### In the stack's own raw frames, and against a flat from another day (MEASURED)

[fpn-raw.py](fpn-raw.py): means of 16 raw frames (four planes, four
members) at planes 20, 70, 120 and 170 of the scarab run, tiles bright and
smooth in both means, against the 6 s burst taken a day earlier.

| Channel | Scale, plane px | Stack with stack | Rolled placebo | Burst with burst | Stack with burst | Correlation |
| --- | --- | --- | --- | --- | --- | --- |
| Red | 1 | 0.247 % | -0.001 % | 0.259 % | 0.247 % | 0.952 |
| Green 1 | 1 | 0.295 % | -0.017 % | 0.302 % | 0.295 % | 0.974 |
| Green 2 | 1 | 0.293 % | +0.020 % | 0.298 % | 0.291 % | 0.972 |
| Blue | 1 | 0.321 % | -0.052 % | 0.326 % | 0.319 % | 0.972 |
| Green 1 | 2 | 0.324 % | +0.071 % | 0.356 % | 0.329 % | 0.941 |
| Green 1 | 4 | 0.237 % | +0.251 % | 0.521 % | 0.338 % | (placebo as large as the figure) |

The stack-with-burst covariance is the clean one (different scenes,
different days: only what belongs to the sensor is common): 0.295 % at one
plane px, 0.329 % at two, 0.338 % at four, 0.328 % at eight for green. The
pattern is close to white with a little short-range correlation, and a
day-old flat predicts it.

### Where it sits after four-shot assembly (DERIVED, then MEASURED)

A four-shot group reads every photosite four times, once per member, at
four adjacent output pixels. So each photosite's response error lands on a
2 x 2 block of the assembled image and the pattern's spectrum becomes
4 cos^2(pi fx) cos^2(pi fy) times its white level: four times the white
density at low frequency, half at 0.25 cycles/px on an axis, nothing at
Nyquist. Photon noise stays white (every raw sample is used once). So in
the band the eye reads as grain the pattern's share is four times what the
per-photosite figure suggests.

[fpn-pairs.py](fpn-pairs.py) on single groups rendered alone
(`STREHL_FRAME_PARITY=K-K`, raw carry, no restoration): scene content sits
at the same output position in every frame; a sensor pattern slides
radially between frames at the magnification step. Band 0.08-0.30
cycles/px, 147 bright smooth tiles (green 19 300 of 65 535, 4 400 DN raw):

| Pair | Predicted rate | Fitted rate | Share of band power, R / G / B | Share if fixed to the output |
| --- | --- | --- | --- | --- |
| frames 100, 101 | 124 ppm | 120 ppm | 0.128 / 0.288 / 0.167 | (overlaps at this distance) |
| 100, 102 | 248 | 220-240 | 0.125 / 0.277 / 0.164 | |
| 100, 104 | 496 | 480-520 | 0.111 / 0.247 / 0.158 | 0.037 / 0.065 / 0.042 |
| 100, 108 | 992 | search-limited | 0.064 / 0.133 / 0.109 | 0.003 / -0.003 / 0.004 |
| merges 98-101, 102-105 | 496 | 500-520 | 0.285 / 0.485 / 0.382 | |

- The pattern moves with the sensor at the lens's breathing rate (the
  prototype's alignment gives 1.24e-4 per plane), so it is the sensor's, and
  nothing in this band on these tiles is fixed to the scene (last column at
  eight frames apart).
- First form of the instrument, the frequency corners beyond the cutoff:
  nothing (0.004-0.008, the search's own noise). That is the 2 x 2 block
  spectrum, not an absence.
- One group: pattern to noise 0.33-0.41 (green), 0.13-0.15 (red), 0.19-0.20
  (blue). The white-pattern prediction with the block spectrum is 0.28,
  0.11, 0.16 at the tiles' mean level; brighter tiles weigh more in the
  measurement.
- A four-group merge: 0.94 (green), 0.40, 0.62, about three times one
  group's ratio. ARGUED: these tiles are smooth, so the merge averages all
  four groups and photon noise falls about fourfold; the pattern then lost
  about a quarter of its power. It does not average down across
  neighbouring groups, because between neighbours it moves by 0.1-0.4 px
  and its correlation length in this band is several pixels.

DERIVED for the default output: the default merge averages about four to
five groups' worth of noise in the fine band (reference-pair noise against
half-stack noise in the restoration's dump, 2.4-2.5 per half), so in green
midtones the pattern's power in 0.08-0.30 cycles/px is about equal to the
photon noise's, more in highlights (it grows with level), and under the
fusion (half the photon noise again) about twice it.

Fooled by: the smooth-tile selection (a smooth tile in one frame is often a
defocused one; the eight-frames-apart control shows no scene-locked share);
the search range (+-3 px, so pairs more than about four frames apart are
clipped and read low).

## Q3. Gather kernel

[kernel-table.py](kernel-table.py), response against an ideal shift, one
axis, summarised over sub-pixel phase:

| Kernel | | 0.20 | 0.30 | 0.35 | 0.40 | 0.45 cycles/px |
| --- | --- | --- | --- | --- | --- | --- |
| Catmull-Rom, 4 taps (shipped) | mean | 0.973 | 0.889 | 0.821 | 0.743 | 0.667 |
| | worst phase | 0.949 | 0.780 | 0.634 | 0.449 | 0.233 |
| Lanczos-3, 6 taps | mean | 1.012 | 0.989 | 0.930 | 0.833 | 0.715 |
| | worst | 1.000 | 0.977 | 0.858 | 0.647 | 0.349 |
| Lanczos-4, 8 taps | mean | 0.996 | 1.010 | 0.985 | 0.898 | 0.751 |
| | worst | 0.992 | 1.000 | 0.970 | 0.791 | 0.451 |
| Kaiser sinc, 12 taps | mean | 1.001 | 1.000 | 0.997 | 0.945 | 0.793 |
| Kaiser sinc, 16 taps | mean | 1.000 | 1.000 | 1.000 | 0.978 | 0.837 |

Noise power at phase 0.5: 0.641 (Catmull-Rom), 0.786, 0.829, 0.859, 0.885.

[phase-pattern.py](phase-pattern.py), fine noise power (green, value minus
1 px Gaussian, squared, over local level), first-harmonic depth (peak to
peak over mean) by fold period:

| Image | Best period | Depth | Floor |
| --- | --- | --- | --- |
| frame 100 alone, central 2048 px | 59.0 px | 0.47 (x), 0.47 (y) | 0.012 |
| frames 100 minus 101 | 59.25 px | 0.57 | 0.013 |
| merges 98-101 minus 102-105, 512 px tiles | 60 px | 0.25 | 0.04-0.06 |
| odd minus even half-stack, 512 px tiles | none in 45-81 px | excess 0.00-0.03 | 0.08-0.11 |
| fusion halves | none | excess 0.00 | 0.06-0.10 |

The coverage fit scales every frame by 0.9827, so every frame is gathered
at a phase that cycles every 58-59 px. One frame's fine noise power, and so
its finest detail, is modulated as the closed form says (0.44 predicted for
white noise). In a full merge the frames' grids differ in period and offset
and the pattern is not detectable. So the kernel leaves no visible grid in
the default output; what it leaves is its mean loss, which the
restoration's model (diffraction, photosite aperture, blend) does not
contain: the delivered response falls short of the stated target by that
factor (per axis 3 % at 0.2, 11 % at 0.3, 26 % at 0.4).

## Q4. The fusion's dark lift

[halo-distance.py](halo-distance.py): classes from the even carry half,
scores on odd halves, ratios to the carry arm's odd half, green:

| Arm | 3-6 px | 6-12 | 12-20 | 20-30 | 30-50 | 50-100 | 100-200 | 200+ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| remosaic (control) | 0.964 | 0.983 | 0.992 | 0.995 | 0.996 | 0.996 | 0.997 | 0.998 |
| fusion | 1.259 | 1.080 | 1.091 | 1.121 | 1.138 | 1.101 | 1.175 | 1.088 |
| fusion, as % of bright | +2.4 | +0.68 | +0.58 | +0.64 | +0.66 | +0.50 | +1.2 | +0.55 |
| fusion + restore | 1.133 | 1.019 | 1.063 | 1.104 | 1.123 | 1.086 | 1.165 | 1.083 |
| same, coarse levels by election | 1.027 | 0.973 | 1.011 | 1.038 | 1.060 | 1.028 | 1.334 | 1.093 |
| carry + restore | 0.861 | 0.903 | 0.941 | 0.965 | 0.973 | 0.973 | 0.982 | 0.990 |
| gated fusion (below) | 0.996 | 0.998 | 0.998 | 0.998 | 0.998 | 0.998 | 0.999 | 0.999 |
| calibrated fusion (below) | 1.082 | 0.969 | 0.969 | 0.962 | 0.956 | 0.954 | 1.007 | 1.014 |

The lift is the same +0.5 to +0.7 % of the bright level from 6 px out to
beyond 200 px: a small loss of low-frequency contrast, which on a dark
ground a twentieth as bright reads as 10 %. Only the first 6 px behave like
light spread from the edge.

Two post-merge prototypes on the finished renders:

- [gated-fusion.py](gated-fusion.py): keep each band of (fusion minus
  election) only where it is within noise of zero. Removes the lift
  entirely and almost all of the gain with it (fine-detail signal-to-noise
  power 12.6 / 13.7 / 12.5 against the election's 12.1 / 12.9 / 11.9): in
  textured areas the fusion's attenuation is itself a difference above
  noise. Not the fix.
- [calibrated-fusion.py](calibrated-fusion.py): one gain per band (ratio of
  the election's signal to the fusion's, from cross-half products), and
  everything coarser than 32 px from the election. Gains R / G / B: 1.32 /
  1.31 / 1.27 (0-1 px), 1.04 / 1.08 / 1.03 (1-2 px), 0.98-1.01 (2-32 px).

| Arm (odd/even halves, ratios to carry) | Fine detail R / G / B | Noise in that band | SNR power |
| --- | --- | --- | --- |
| carry (election) | 1 | 1 | 12.1 / 12.9 / 11.9 |
| fusion | 0.82 / 0.82 / 0.82 | 0.58 / 0.58 / 0.58 | 23.7 / 25.2 / 23.5 |
| calibrated fusion | 1.04 / 1.03 / 1.00 | 0.75 / 0.74 / 0.72 | 23.3 / 24.9 / 23.2 |

  The far lift came from the fusion's coarse levels and the near one mostly
  from the finest band's 30 % shortfall. What is left: +8 % within 6 px,
  and shadows 3-5 % darker than the election's from 6 to 100 px.

The knob that should have done the coarse part does not.
[coarse-compare.py](coarse-compare.py), green low-passed at 32 and 64 px,
ratios to the carry + restore arm's low-pass, dark pixels by distance from
bright ones:

| Arm | 32 px: 30-100 | 100-200 | 200+ | 64 px: 30-100 | 100-200 | 200+ |
| --- | --- | --- | --- | --- | --- | --- |
| carry (control) | 0.995 | 0.996 | 0.998 | 0.996 | 0.997 | 0.998 |
| fusion + restore | 1.051 | 1.157 | 1.170 | 1.019 | 1.066 | 1.138 |
| same, `STREHL_FUSION_COARSE=election` | 1.025 | 1.319 | 1.348 | 1.009 | 1.136 | 1.216 |
| calibrated fusion (prototype) | 0.992 | 0.998 | 0.970 | 0.997 | 1.000 | 0.988 |

With the three finest levels guided, the election of the remaining levels
does not give the plain election's coarse content: far from anything bright
it is 14-35 % brighter. Cause not established.

Which is right in the shadows is not established.
[shadow-truth.py](shadow-truth.py) scores dark pixels whose bright
surroundings are in focus in frame 100, against frame 100 rendered alone:
frame 102 reads 1.04-1.07, the 98-101 merge 0.95-0.98, the election
0.79-0.89, the fusion 0.83-0.91, the calibrated fusion 0.74-0.83. Every
full merge is darker than the single frame, one focus step moves the
figure by 3 %, and the election and the fusion differ by less than either
differs from the frame. A reference with known shadow levels is needed
before a tolerance tighter than about 5 % means anything.

## Q5. Where the fusion loses

[radial-ratio.py](radial-ratio.py), green, fusion against carry, 222 tiles:

| cycles/px | 0.056 | 0.106 | 0.156 | 0.206 | 0.256 | 0.306 | 0.356 | 0.406 | 0.444 | 0.469 | 0.494 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| signal | 0.983 | 0.950 | 0.874 | 0.834 | 0.820 | 0.812 | 0.815 | 0.800 | 0.739 | 0.679 | 0.587 |
| noise | 0.701 | 0.582 | 0.523 | 0.519 | 0.543 | 0.583 | 0.618 | 0.649 | 0.665 | 0.677 | 0.684 |
| SNR | 1.97 | 2.66 | 2.79 | 2.59 | 2.28 | 1.94 | 1.74 | 1.52 | 1.23 | 1.00 | 0.74 |

Control: restore against carry has SNR ratio 0.995-1.015 at every
frequency, as a linear filter must.

The carried merge folds twelve half-resolution site planes. A plane-domain
pyramid level passes output frequencies near every multiple of 0.5
cycles/px, so output detail above 0.375 cycles/px is carried by plane level
1 and above 0.4375 by level 2, with those levels' frame weights. The
fusion's widths grow with level (7.1, 11.6, 16.4 frames), and the finest
detail decorrelates across frames fastest; the measured knee at 0.40-0.44
is where the two meet. Within level 0 (0.24-0.38) the loss is a flat 18 %:
that level's width is measured on its dominant 0.125-0.25 content.

## Q6. Member mismatch

[spectrum2d.py](spectrum2d.py), in-focus tiles. Power at the three Nyquist
points against the neighbouring bins, as a pattern amplitude: 0.017-0.021 %
of level at (0, 0.5) (alternate rows), 0.005 % at (0.5, 0), 0.001-0.004 %
at (0.5, 0.5). Noise in the ring 0.65-0.70 cycles/px, green, same tiles:
compensated 0.0293, ungated and uncompensated 0.0443, reversed-sign placebo
0.0822 (the excesses over the compensated arm are 1 : 3.5; first-order
theory says 1 : 4).

[parity-bias.py](parity-bias.py), each channel's four site planes scored
separately, finest plane band, ratios to the channel's mean:

| Arm | Green, native sites | Green, carried sites |
| --- | --- | --- |
| election: shared power | 1.012, 1.018 | 0.984, 0.986 |
| election: noise | 1.050, 1.050 | 0.949, 0.952 |
| fusion: shared power | 1.000, 1.000 | 1.001, 0.999 |
| fusion: noise | 0.998, 1.001 | 1.001, 1.000 |

## Q7. Phase spread

[phase-coverage.py](phase-coverage.py), from the prototype's per-plane
similarity, 48 x 32 positions, K planes about plane 100:

| K | Noise amplification p10 / median / p90 | Under 2 | Under 4 | Random phases, median |
| --- | --- | --- | --- | --- |
| 4 | 1.67 / 7.71 / 35.6 | 14 % | 29 % | 3.27 |
| 6 | 1.06 / 1.89 / 6.51 | 52 % | 76 % | 1.48 |
| 10 | 1.03 / 1.14 / 2.82 | 80 % | 96 % | 1.19 |
| 16 | 1.02 / 1.06 / 1.59 | 95 % | 99 % | 1.11 |

Geometry only. What the optics pass beyond the grid on this rig is small
(DERIVED from the fitted cutoffs: diffraction times photosite aperture at
0.55 cycles/px is about 2 % for green and 7 % for blue), so this is a
route for a sharper lens setting, not a gain here.

## Q8. By eye

`default-full.tif`: the default four-shot render of the whole run (colour
carry, restoration, residual compensation; 314 s, peak 23.6 GB).
`q8-overview.png` (1/8 scale, orientation only); `q8-crops-a.png`, 200 px
at 3x, origins (1900,960) and (4700,3100), default beside the single-shot
render. Scale outlines are clean, nothing rings, grain is hard to see at
1:1. At 3x the image is soft in the way N_eff 12 makes it (the Airy disc is
about five photosites). Some bright-on-dark scale edges carry a faint blue
rim one to two pixels wide, in both renders. [edge-fringe.py](edge-fringe.py)
over every bright boundary is too blunt to size it (channel ratios move
1-4 % across the boundary, mostly the dark cuticle's own colour).

## Commands

```sh
E=experiments/a7cr-fourshot-quality-2026-11-16; O=outputs/a7cr-fourshot-quality; R=outputs/scarab-rgb
python -X utf8 $E/cross-channel.py $O/q1-cross-channel.json $R/h-f-carryraw-odd.tif $R/h-f-carryraw-even.tif
python -X utf8 $E/channel-shift.py $O/q1-channel-shift.json $R/h-f-carryraw-odd.tif $R/h-f-carryraw-even.tif
python -X utf8 $E/chroma-crops.py $O/q1-chroma-4x.png 96 4 3 $R/h-f-carryraw-odd.tif,$R/h-f-carryraw-even.tif,$R/h-f-carry-odd-cs1.0.tif 4700,3100 2400,2600
target-ui/release/examples/a7cr-export-members.exe D:/StrehlCaptures/stack-1794684439651-11226 $O/ptc-1794684439651   # and the other two bursts
python -X utf8 $E/prnu.py $O/q2-prnu.json $O/ptc-1794684207243 $O/ptc-1794684439651 $O/ptc-1794684263347 --save-map $O/q2-prnu-map.npy
python -X utf8 $E/fpn-raw.py $O/q2-fpn-raw.json outputs/scarab-fp/cache4 $O/ptc-1794684439651 --planes 20,70,120,170 --group 4
pwsh -File $O/single-frames.ps1                          # frames 100 101 102 104 108 130, each alone; then -Frames @('98-101','102-105','94-101','102-109')
python -X utf8 $E/fpn-pairs.py $O/q2-fpn-pairs.json $O/one-100.tif $O/one-101.tif ... --rate 1.24e-4 --frames 100,101,102,104,108,130
python -X utf8 $E/fpn-pairs.py $O/q2-fpn-pairs-band.json (same) --band 0.08,0.30 --flat
python -X utf8 $E/fpn-pairs.py $O/q2-fpn-merge4.json $O/one-98-101.tif $O/one-102-105.tif --rate 1.24e-4 --frames 0,4 --band 0.08,0.30 --flat
python -X utf8 $E/floor-vs-level.py $O/q2-floor-vs-level.json $R/h-f-carryraw-odd.tif $R/h-f-carryraw-even.tif 1.909,1.0,2.442
python -X utf8 $E/spectrum2d.py $O/q6-carryraw-focus $R/h-f-carryraw-odd.tif $R/h-f-carryraw-even.tif        # also carry-comp, carry-neg, carry-ungated, carry-fusion, remosaic
python -X utf8 $E/parity-bias.py $O/q6-parity-carryraw.json $R/h-f-carryraw-odd.tif $R/h-f-carryraw-even.tif  # and the fusion halves
python -X utf8 $E/kernel-table.py
python -X utf8 $E/phase-pattern.py $O/q3-phase-one100.json $O/one-100.tif                                      # and pairs; --size 4096 for merges
python -X utf8 $E/halo-distance.py $O/q4-halo-distance.json $R/h-f-carry-even.tif $R/h-f-carry-odd.tif <arms, odd halves>
python -X utf8 $E/gated-fusion.py $O/q4-gated $R/h-f-carry-odd.tif $R/h-f-carry-even.tif $R/h-f-carry-fusion-odd.tif $R/h-f-carry-fusion-even.tif
python -X utf8 $E/calibrated-fusion.py $O/q4-calibrated (same four)
python -X utf8 experiments/a7cr-full-potential-2026-11-14/compare-colour.py $O/q4-cmp2 carry=... fusion=... calibrated=$O/q4-calibrated-odd.tif,$O/q4-calibrated-even.tif
python -X utf8 $E/shadow-truth.py $O/q4-shadow-truth.json $O/one-100.tif $R/h-f-carry-odd.tif <single frames and even halves>
python -X utf8 $E/radial-ratio.py $O/q5-radial-ratio.json carry=... fusion=... restore=... fusion-restore=...
python -X utf8 $E/phase-coverage.py outputs/scarab-fp/work/align.json
python -X utf8 $E/coarse-compare.py $R/h-f-carry-even.tif $R/h-f-carry-restore-odd.tif $R/h-f-cfr-coarse-odd.tif $R/h-f-carry-fusion-restore-odd.tif $R/h-f-carry-odd.tif $O/q4-calibrated-odd.tif
pwsh -File outputs/peak-run.ps1 $O/default-full.log "STREHL_PIXEL_SHIFT=remosaic" stack <four-shot run> --demosaic --out $O/default-full.tif
pwsh -File outputs/peak-run.ps1 $O/rawchroma-full.log "STREHL_PIXEL_SHIFT=remosaic;STREHL_CARRY_RGB=raw" stack <four-shot run> --demosaic --out $O/rawchroma-full.tif
```

Two instrument faults found and fixed before any number above: an empty
radial bin (a NaN in the joint filter), and an empty fold bin in the first
phase-pattern version that read as a depth of 1.07 at 30 px in every image.
[noise-depth.py](noise-depth.py) did not measure what it was written for
(its "smooth" tiles are in focus elsewhere in the stack, so the halves
differ by scene) and none of its output is used.
