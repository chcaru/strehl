# Setup page: measurements behind the spec

**Status:** author-run, 2026-11-27, no independent review. Ledger row
`setup-page-2026-11-27`. Spec:
[2026-11-setup-page-spec](../../docs/proposals/2026-11-setup-page-spec.md).

**Rig:** the owner's A7CR (ILCE-7CR), FE 100mm F2.8 Macro GM OSS with the 2x converter at
f/5.6, on the Pi capture host over USB at 5 Gbit/s, light a Schott KL 1500 LCD on a
switched plug (174 W). Subject on the stage: a dragonfly wing on a black ground, in focus
from about 32,360 to 33,140 lens units. Nobody was at the rig for R2 to R8: no lens cap,
no white card, nothing moved by hand, and the room, the owner said afterwards, was not
fully dark. For R9 the owner capped the lens and closed the door. All frames single shot,
14-bit uncompressed, 9504 x 6336 active.

**Builds:** analysis examples and `strehl-raw-archive` from `origin/main` at `31e778bfb`
(`target/release`); the two prototypes of this folder and the engine with the experiment
switch of R7 built in a scratch target from the same commit. Decoding by
`strehl_raw::decode` or, for other makers' files, the linked decoder directly.

Labels as in `AGENTS.md`.

---

## R1. What the decoder reports for other makers' files

`analysis/samples.py` fetched 24 distinct files from raw.pixls.us (public, CC0; 1.1 GB, not
committed; it fetched the Canon R5's compact file twice, for want of a stricter name
match). `probe-any.rs` (`cargo run --release -p strehl-raw --example setup-probe-any
-- FILE...`) reads each with the linked decoder, before Strehl's own gates. Full output:
[`analysis/probe-samples.jsonl`](analysis/probe-samples.jsonl).

MEASURED:

| Body | File | Decodes | Samples a pixel | Pattern at the active corner | Black | Declared white | Data: top code (samples on it) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Canon EOS R5 | CR3, compact | yes | 1 | RGGB | 510 | 14008 | 14998 (1) |
| Canon EOS 5D Mark IV | CR2 | yes | 1 | RGGB | 511, 512, 511, 512 | 14008 | 16383 (178) |
| Canon EOS 5D Mark IV | CR2, reduced size | yes | **3** | | 511 | 56032 | 58100 |
| Canon EOS 90D | CR3 | yes | 1 | RGGB | 512 | 13036 | 15047 (1) |
| Canon EOS 90D | CR3, compact | yes | 1 | RGGB | 512 | 13036 | 16383 (85) |
| Canon EOS R6 Mark II | CR3, full and cropped | yes | 1 | RGGB | 512 | 12735 | 16383 (504; 13) |
| Nikon Z 7 | NEF 14-bit, uncompressed | yes | 1 | RGGB | 1008 | 15520 | 16383 (6,208) |
| Nikon Z 7 | NEF 14-bit, compressed | yes | 1 | RGGB | 1008 | 15520 | 16372 (475) |
| Nikon Z 8 | NEF, High Efficiency | **no**: "NEF compression Some(HighEfficency) is not supported" | | | | | |
| Nikon Z 8 | NEF 14-bit lossless | yes | 1 | RGGB | 1008 | 15892 | 16383 (1,515,933) |
| Nikon D850 | NEF 12-bit, both compressions | yes | 1 | RGGB | 100 | 3880 | 1047; 903 (not clipped) |
| Fujifilm X-T4 | RAF (two files) | yes | 1 | **6 x 6 X-Trans** | 1022 | 16383 | 16383 |
| Panasonic S1R | RW2 | yes | 1 | **GBRG** | 510 | 16380 | 16368 at the 99.9th percentile; one stray 65531 |
| Panasonic GH5 | RW2 (two files) | yes | 1 | RGGB | 129, 128, 128, 129 | 4095 | 4095 (218,624) |
| Pentax K-1 II | DNG; PEF | yes | 1 | RGGB | 64 | 16318; 16315 | 16382 |
| Hasselblad X1D II | 3FR | yes | 1 | RGGB | 256 (one entry) | 65535 | 65535 (75,648) |
| Hasselblad X1D II | FFF | **no**: "Unknown camera" | | | | | |
| Sony A7R V | ARW lossless, large | yes | 1 | RGGB | 512 | 15360 | 16383 (645) |
| Sony A7R V | ARW lossless, medium | yes | **3** | | 1024 | 15360 | 19581 |

Counts: 22 of 24 decode; 18 of those are one sample a pixel with a 2 x 2 colour pattern
(17 RGGB at the active corner, 1 GBRG), 2 are X-Trans, 2 are three samples a pixel. In 13
of the 18 the top code in the data is above the declared white (by 64 codes on the Pentax,
by 491 to 3,648 on the Canon, Nikon Z and Sony files; the Panasonic S1R's is one stray
sample). Containers: 12 bit (D850 in 12-bit mode, GH5), 14 bit, 16 bit (Hasselblad). The
lens name is absent from 4 of the 18.

Direction this can be fooled: one or two frames a body say nothing about that body's other
modes (crop, silent shutter, bit depth), and a scene that does not clip cannot show the
top code.

---

## R2. Dark frames without a lens cap

`rig/e1-dark.py`, `rig/e1b-dark.py`; analysis by the existing
`a7cr-dark-analysis` example (the program that read the lens-capped series of
2026-11-14). 8 frames a burst.

**First attempt: lit.** The host manages power, and with that on every capture switches
the light on. The first seven "dark" bursts were taken with the light on (174 W), lens at
51,048, far out of focus. MEASURED, green (G1):

| ISO, shutter | Mean level | Pooled temporal deviation |
| --- | --- | --- |
| 100, 1/8000 s | 512.26 | 1.552 |
| 100, 1/100 s | 513.88 | 1.488 |
| 100, 0.6 s | 630.91 | 7.126 |
| 100, 2.5 s | 969.78 | 14.954 |

This is the failing input of the spec's Dark check: 455.9 DN between 1/100 s and 2.5 s.

**Second attempt: managed power off (`power_plan` disabled), light off, no cap, in a room
that was not fully dark** (R9 repeats it capped).
MEASURED, green (G1), against the capped series of 2026-11-14
(`experiments/a7cr-calibration-2026-11-14/results.md`, 16 to 32 frames each):

| ISO, shutter | Black | Read noise, pooled | Median photosite | Capped, pooled |
| --- | --- | --- | --- | --- |
| 100, 1/8000 s | 512.24 | **1.547** | 1.282 | not measured |
| 100, 1/1000 s | 512.22 | 1.331 | 1.069 | |
| 100, 1/100 s | 512.22 | 1.305 | 1.069 | 1.305 (1/8 s) |
| 100, 0.6 s | 512.34 | 1.323 | 1.069 | 1.330 |
| 100, 2.5 s | 512.41 | 1.373 | 1.165 | 1.363 |
| 320, 1/100 s | 512.31 | 3.754 | 2.850 | 3.836 (0.6 s) |
| 400, 1/100 s | 512.21 | 2.134 | 1.553 | 2.224 (0.6 s) |
| 3200, 1/100 s | 512.06 | 15.750 | 10.842 | 16.808 (0.6 s) |

- Black rises 0.19 DN from 1/100 s to 2.5 s (the passing input of the Dark check); 6
  photosites exceed 50 DN at 2.5 s, none at 0.6 s.
- Frame-to-frame black: within 0.05 to 0.21 DN at ISO 100, 0.5 DN at ISO 3200.
- Blue's read noise is 5.3 % under green's at ISO 100 (1.236 against 1.305), as on
  2026-11-14.
- At 1/8000 s the read noise is 17 % higher than at 1/1000 s and slower, with the light on
  and with it off. Cause not established (a different readout at that speed is the
  candidate).
- The median photosite reads lower from 8 frames (1.069) than from 32 (1.136 on
  2026-11-14): the median of a deviation estimated from few frames is biased low. The
  pooled figure is not.

Wall time, 8 single shots: 16.6 s at 1/100 s, 22.1 s at 0.6 s, 37.3 s at 2.5 s.

---

## R3. Gain, clip and linearity from an out-of-focus subject

`rig/e2-probe.py`, `rig/e2-white.py`; the prototype `sensor.rs`
(`cargo run --release -p strehl-raw --example setup-sensor -- OUT.json DIR=SECONDS...`)
and `analysis/sensor-report.py`. Light on for 10 minutes before the first burst.

The lens was driven from the subject (32,750) to 37,750, 5,000 units away, chosen from one
frame at each of four offsets (at 1.3 s the green 99.9th percentile was clipped at +1,000,
7,713 DN at +2,500, 3,085 at +5,000, 1,585 at +10,000). In focus the scene's green median
is 44 DN at 1.3 s: most of the frame is the black ground.

**ISO 100, five bursts of 8 (0.4, 1.3, 3.2, 5, 8 s; 2 min 40 s of shooting).** MEASURED:

| | Red | Green 1 | Green 2 | Blue |
| --- | --- | --- | --- | --- |
| Gain, fit 30 to 4,000 DN, DN/e- | 0.3992 | 0.4040 | 0.4040 | 0.3757 |
| Fit to 8,000 DN | 0.3992 | 0.4049 | 0.4050 | 0.3762 |
| Fit to 12,000 DN | 0.3992 | 0.4053 | 0.4055 | 0.3762 |
| Top code, 8 s burst | 6014 | 16383 (2,134,044 samples) | 16383 (2,133,199) | 10648 |

The hand-made profile of 2026-11-14 holds 0.4040 (green), 0.398 to 0.402 (red), 0.37 to
0.38 (blue).

Variance less the dark's read variance, over signal, green 1, by level: 0.395 at 240 DN,
0.406 at 1,420, 0.416 at 4,460, 0.425 at 9,500, 0.408 at 13,500. The rise of 5 % between
1,400 and 9,500 DN is light that the per-frame drift removal did not remove (0.15 % of
level would do it); the fit therefore stops at a quarter of the range. The frame levels'
relative deviation inside a burst was 0.16 to 0.52 %.

**Linearity by exposure ratio.** The sum of the longer burst's photosite means over the
shorter's, in 128 DN bins of the longer's level, against its flat value (the median from
1,500 to 6,000 DN):

| Pair | Flat ratio (time ratio) | Departure from flat, 1,300 DN to the top |
| --- | --- | --- |
| 1.3 s over 0.4 s | 3.1685 (3.250) | -0.5 % to +0.07 %, to 3,100 DN |
| 3.2 s over 1.3 s | 2.5328 (2.462) | -0.26 % to +0.13 %, to 7,860 DN |
| 5 s over 3.2 s | 1.5868 (1.562) | within 0.05 %, to 12,340 DN |
| 8 s over 5 s | 1.6208 (1.600) | within 0.07 %, to 15,425 DN; first bin 1 % off at 15,868 (the clip is 15,871 above black) |

The flat ratios differ from the time ratios by up to 2.9 %: that is the light between
bursts, and why the test reads the shape and not the value. Departures of 0.3 to 0.5 %
below about 1,500 DN are the out-of-focus scene drifting by a fraction of a pixel between
bursts; a white card would not show them.

So: linear within 0.1 % up to the clip, and the clip is the container's top, 16383. The
decoder declares 15360, 6.9 % of the range above black lower.

**Other ISO settings, one burst of 8 each (fit 30 to 4,000 DN), green 1:**

| ISO | Gain, DN/e- | Against 0.4040 x ISO / 100 | Shutter, wall time |
| --- | --- | --- | --- |
| 200 | 0.8078 | 0.0 % | 1.6 s, 31 s |
| 320 | 1.2883 | -0.3 % | 1 s, 26 s |
| 400 | 1.6322 (four bursts) | +1.0 % | 1/3 to 2 s |
| 800 | 3.2782 | +1.4 % | 0.4 s, 25 s |

At ISO 400 the 2 s burst clips at 16383 (2,205,349 samples) and the ratio of 2 s over
1.3 s is within 0.10 % of flat to 15,424 DN.

The fit's intercept is not the read noise: -0.07 DN^2 at ISO 100 where the darks give
+1.70, +2.98 at ISO 400 where they give +4.55.

Reading a burst of 8 took 2.0 to 2.4 s.

Direction this can be fooled: residual light drift raises the apparent gain at high
levels (seen, and the reason for the fit's range); a scene that moves between frames adds
variance on its edges (not seen at 5,000 units of defocus; the spec's even-and-odd check
is the guard).

---

## R4. The light

`rig/e3-warm.py`, `rig/e-final.py` (part 1), `analysis/series-an.py`: 70 single shots at
1.3 s, ISO 100, subject in focus, one every 2.9 s. Level: mean above black over photosites
between 5 % and 50 % of the range in the first frame. Position: a 1,536-pixel central crop,
2 x 2 summed, registered against the first frame with a gain and an offset.

**From cold** (off 20 min 0 s, on at t = 0). MEASURED, green, against the mean of the last
12 frames:

| t | Level | Red over green | Blue over green | Picture, px |
| --- | --- | --- | --- | --- |
| 6.9 s | +8.14 % | 1.1152 | 1.1798 | 0, 0 |
| 18.3 s | +4.63 % | 1.1218 | 1.1731 | -0.14, +0.11 |
| 29.7 s | +0.95 % | 1.1275 | 1.1700 | -0.16, +0.15 |
| 41.1 s | -0.16 % | 1.1294 | 1.1689 | -0.08, +0.24 |
| 52.5 s | +2.43 % | 1.1295 | 1.1743 | -0.09, +0.53 |
| 109.5 s | +1.08 % | 1.1370 | 1.1804 | -0.14, +0.63 |
| 155.4 s | -0.92 % | 1.1414 | 1.1803 | -0.31, +0.99 |
| 204.2 s | -0.58 % | 1.1427 | 1.1816 | -0.50, +1.19 |

Deviation of the level over the last 60 s: 0.52 %. With a tolerance of twice that
(1.05 %), the last frame outside is at 164 s and the level is inside from 167 s.

**Already on** (a second series from 277 s to 475 s after an earlier switch-on, a different
framing): within 0.6 % until 377 s, then +1.7 % at 392 s, +4.4 % at 435 s, +3.2 % at 475 s.
Picture drift -0.8 px in x over 198 s.

The capture calibration's constant is 150 s (`LIGHT_SETTLED`), from the two earlier
measurements its spec cites ("falls 11 % in its first 140 s").

---

## R5. How the focus axis returns to a position

`rig/e4-return.py` (286 s, live view only, 524 frames of 1024 x 680), `rig/e-final.py`
(part 2), `analysis/e4-an.py`, `analysis/e4-trans.py`, `analysis/e6-an.py`. The
instrument is the fingerprint of the spec's section 7.0; target P = 32,933.

**The instrument.** 310 of 672 tiles carry a usable change. MEASURED:

| | Without a gain per frame | With one |
| --- | --- | --- |
| A sweep frame read against the fingerprint it is part of | 0.26 units rms | 0.16 |
| With its position left out | 2.61 rms, worst 9.3 | 1.82 rms, worst 6.6 |
| The second sweep (4 min later) against the first | -0.7 mean, 2.6 rms | -1.6 mean, 2.2 rms |

Without the gain, a run of frames at one commanded position flips between readings about
4 units apart, and the reading follows the frame's mean luma (19.2 against 18.4 of 255):
live view's brightness changes by 4 % from frame to frame. With the gain it does not.
Readings still gather near multiples of 2 units; whether that is the lens's smallest step
or the fingerprint's straight lines between samples 4 units apart was not separated.

**Arrivals at P** (read position minus P; two frames each, mean of the two, six repeats,
four for the far moves). MEASURED, with the gain:

| Arriving | Mean | Deviation | Repeats |
| --- | --- | --- | --- |
| From 128 below | -2.05 | 0.81 | -2.0 -1.6 -1.6 -3.7 -1.8 -1.7 |
| From 128 above | -6.18 | 0.19 | -6.1 -6.1 -6.1 -5.9 -6.5 -6.3 |
| From 16 below | -5.26 | 1.07 | -4.0 -5.9 -3.8 -5.9 -6.1 -5.8 |
| From 16 above | -4.93 | 1.10 | -5.7 -3.9 -6.1 -4.1 -6.0 -3.8 |
| From 8 below | -4.62 | 1.66 | -6.0 -3.7 -2.0 -6.1 -5.9 -4.0 |
| From 8 above | -5.35 | 1.23 | -6.1 -3.6 -6.3 -3.9 -6.1 -6.1 |
| From 5,000 above, then 128 below | -0.93 | 1.07 | -2.0 +0.0 -1.7 -0.0 |
| From 5,000 below, then 128 below | +3.50 | 4.23 | +8.3 +5.8 -0.1 +0.0 |
| From 5,000 above | -5.97 | 0.19 | -5.8 -5.8 -6.2 -6.1 |
| From 5,000 below | +4.11 | 3.66 | +2.3 +8.1 +6.1 -0.1 |

The kinds were interleaved, so each short arrival started from wherever the one before
left the lens.

**For 12 s after a 5,000-unit move** (three each way, a fresh fingerprint): from below
+3.2 (deviation 2.0) in the second second and +2.8, +3.7, +3.3, +3.1, +2.9, +3.2 in the
bins to 12 s; from above -4.5 then -4.5, -4.4, -4.9, -4.2, -4.2, -4.3. No creep.

**After a short move** (every live frame for 4.5 s; four repeats of +8, +128 and -128):
the first frame that shows the new position arrives 0.72 to 0.91 s after the command; from
it on, the read position is within 1.5 units of its final value and the picture within 0.3
to 0.5 sensor pixels of its final place, which is this measure's floor (one live pixel is
9.3 sensor pixels). Live frames come at 5.6 to 6.0 a second.

**Also found.** The camera's magnifier is back at 0 after a focus move
(`magnifier_current`), so a magnified view cannot be held through this test.

Direction this can be fooled: the fingerprint assumes the picture does not shift sideways
by a tile between sweep and test (drift was under a sensor pixel); a subject with detail
at one depth only gives few tiles.

---

## R6. The pitch of a regular target

`analysis/slide-look.py` and `analysis/pitch.py`, on frame 9 of the owner's
calibration-slide stack `stack-1795638138175-14989` (2026-11-25, lens near 43,450), the
half-resolution green plane. A 768-sample box, mean removed, Hann window, two-dimensional
Fourier transform; the two strongest peaks not opposite each other, each refined by the
centroid of the power in the 5 x 5 bins around it.

MEASURED:

| Box (row, column of its corner, green samples) | Pitch along the two axes, sensor px | Axis angles |
| --- | --- | --- |
| 2300, 2900 | 108.456, 108.562 | 179.85, -90.55 degrees |
| 1700, 3100 | 108.363, 108.126 | 89.60, 179.72 degrees |

0.1 % between the axes of the first box, 0.4 % between boxes. The slide's own labels are
no standard: the bar group marked "-2 1" has bars 127 sensor pixels wide, which at any
plausible magnification is far finer than that group of a full-size target; the slide is a
photographic reduction.

---

## R7. Lateral colour measured from nothing

The engine's own per-stack instrument (`strehl_core::ca_refine::measure` on the preview
render of `strehl stack --srgb`). An experiment switch, in this folder's worktree only and
not for merge, made the matched profile's coefficients zero (`STREHL_CA_ZERO_PROFILE=1`)
or two given numbers (`=R,B` in ppm) so that a second pass could be run
(`analysis/ca-zero-profile.patch`). `analysis/ca-zero.sh` ran each stack three ways; four-shot stacks with
`STREHL_PIXEL_SHIFT=remosaic`. Isolated cache (`STREHL_CACHE_DIR`), no output kept.

MEASURED, scale in ppm, red / blue:

| Stack | Pass 1 from nothing | Pass 2 finds left over | Two passes | Shipped profile (-464.6 / +205.6) leaves | Shipped plus that | Tiles kept |
| --- | --- | --- | --- | --- | --- | --- |
| Coin, single shot, `stack-1794689213508-11226` | -404.9 / +191.8 | +19.4 / -4.0 | -385.5 / +187.8 | +82.3 / -17.5 | -382.3 / +188.1 | 613 of 625 |
| Dragonfly, `stack-1795713444768-14989` | -295.6 / +58.9 | -9.8 / +1.3 | -305.4 / +60.2 | +156.7 / -142.2 | -307.9 / +63.4 | 504 of 506 |
| `stack-1795433406862-8651` (focus 31,239) | -234.3 / +30.2 | +0.8 / -0.3 | -233.5 / +29.9 | +223.9 / -175.5 | -240.7 / +30.1 | 412 of 412 |
| Close tile, `stack-1795476520452-8651` (61,812) | -210.7 / +125.6 | -4.2 / +5.7 | -214.9 / +131.3 | +213.5 / -69.0 | -251.1 / +136.6 | 277 of 294 |

Translations were 0.01 to 0.24 px and the same to 0.03 px between the three ways. The
preview pass took 2.7 to 14.1 s (it is every third of 107 frames on the coin).

- From nothing, two passes land within 3.2, 2.5, 7.2 and 36.2 ppm (red) and 0.3, 3.2, 0.2
  and 5.3 ppm (blue) of one pass on top of the shipped profile. The 36 ppm is the close
  tile, where the shipped profile is 214 ppm off and one pass does not close that.
- One pass from nothing leaves up to 19 ppm.
- The lens's colour shift differs by stack far more than either way of measuring: red
  from -215 to -386 ppm, blue from +30 to +188, with the same lens, converter and
  aperture.

---

## R8. Settle

`rig/e-final.py` (part 3), `analysis/e5-an.py`. Eleven bursts of ten single shots at
planes 8 units apart (32,933 to 33,005), 1/100 s, ISO 3200, with the plan's settle set to
2000, 100, 250, 500, 1000, 2000, 100, 250, 500, 1000, 2000 ms in that order (274 s). Each
frame registered against the first burst's frame at the same position; the burst's
first-plane shift (which always follows a 2 s wait) subtracted.

MEASURED, planes 2 to 10, distance from rest in sensor pixels:

| Settle | Median | Mean | Deviation | 90th percentile | Max | Frames |
| --- | --- | --- | --- | --- | --- | --- |
| 100 ms | 0.37 | 0.44 | 0.25 | 0.78 | 1.05 | 18 |
| 250 ms | 0.58 | 0.55 | 0.26 | 0.89 | 0.98 | 18 |
| 500 ms | 0.29 | 0.38 | 0.25 | 0.61 | 1.20 | 18 |
| 1,000 ms | 0.44 | 0.54 | 0.29 | 0.89 | 1.29 | 18 |
| 2,000 ms (the two later bursts) | 0.36 | 0.46 | 0.30 | 0.88 | 0.97 | 18 |

Pooled deviation about the medians 0.28 px; twice the standard error of a difference of
two medians 0.23 px. No settle differs from 2,000 ms by that much (250 ms is closest, at
0.22). The first-plane shifts between bursts ran from -0.13 to -0.61 px in x.

Direction this can be fooled: anything under 0.23 px is invisible to this test, and a
1/100 s single shot says nothing about movement during a 1.3 s exposure or between the
four exposures of a group.

---

## R9. Darks again, capped, with the door closed

`rig/capped.py`, the same analysis as R2. The owner capped the lens and closed the door. A
live frame read 0.8 of 255 with the light off and 0.7 with it on before the run. 8 frames a
burst (4 at 8 s), light off except for the last two rows.

MEASURED, green (G1):

| ISO, shutter | Black | Read noise, pooled | Median photosite | Over 50 DN | R2, no cap |
| --- | --- | --- | --- | --- | --- |
| 100, 1/100 s | 512.25 | 1.311 | 1.069 | 0 | 512.22, 1.305 |
| 100, 2.5 s | 512.29 | 1.325 | 1.069 | 1 | 512.41, 1.373 |
| 200, 1/100 s | 512.22 | 2.416 | 1.847 | 0 | |
| 250, 1/100 s | 512.27 | 3.002 | 2.264 | 0 | |
| 320, 1/100 s | 512.27 | 3.745 | 2.800 | 0 | 512.31, 3.754 |
| 400, 1/100 s | 512.19 | 2.144 | 1.512 | 0 | 512.21, 2.134 |
| 800, 1/100 s | 512.14 | 4.171 | 2.850 | 5 | |
| 1600, 1/100 s | 512.20 | 8.170 | 5.548 | 378 | |
| 3200, 1/100 s | 512.25 | 15.812 | 10.609 | 7,390 | 512.06, 15.750 |
| 100, 1/8000 s | 512.23 | 1.546 | 1.246 | 0 | 512.24, 1.547 |
| 100, 1/4000 s | 512.24 | 1.385 | 1.126 | 0 | |
| 100, 1/2000 s | 512.24 | 1.318 | 1.069 | 0 | |
| 100, 1/1000 s | 512.21 | 1.325 | 1.069 | 0 | 512.22, 1.331 |
| 100, 0.6 s | 512.30 | 1.323 | 1.069 | 0 | 512.34, 1.323 |
| 100, 8 s (4 frames) | 512.28 | 1.594 | 1.291 | 9 | |
| 100, 1/100 s, light on | 512.25 | 1.305 | 1.069 | 0 | |
| 100, 2.5 s, light on | 512.34 | 1.319 | 1.069 | 0 | |

- **The cap against no cap.** At 1/100 s the read noise agrees within 0.5 % at ISO 100,
  320, 400 and 3200 and black within 0.19 DN. At 2.5 s the uncapped burst reads black
  0.12 DN higher and read noise 3.6 % higher: the room's light. From 1/100 s to 2.5 s the
  level rises 0.04 DN capped, 0.09 capped with the light on, 0.19 uncapped, and 455.9
  with the light on and no cap (R2).
- **A cap is enough with the light on:** the last two rows against the first two.
- **Shutter time.** Read noise is 1.31 to 1.33 DN from 1/2000 s to 2.5 s, 5.6 % higher at
  1/4000 s, 18 % higher at 1/8000 s and 21 % higher at 8 s. Black does not move: the
  camera holds it, so dark current cannot be read from the level. Why the fastest speeds
  are noisier was not established.
- **The gain mode.** Read noise over ISO: 0.0131 at 100, 0.0121 at 200, 0.0120 at 250,
  0.0117 at 320, 0.0054 at 400, 0.0052 at 800, 0.0051 at 1600, 0.0049 at 3200. The rule of
  the spec's 6.1 (a fall to under three quarters) starts a mode at 400 and nowhere else.
- **Against 2026-11-14** (capped, 0.6 s, 16 frames): tonight reads 2.1 % lower at ISO 200,
  3.6 % at 400, 5.3 % at 800, 5.5 % at 1600 and 5.9 % at 3200, and 0.5 % lower at ISO 100.
  Tonight's ladder is at 1/100 s on a camera a few minutes on; that one at 0.6 s after an
  hour of series. The cause was not separated.
- **Time.** The nine bursts of the spec's Dark list took 172 s.

---

## R10. Level from a flat target: the guard

`analysis/flat.py` on the calibration-slide stack `stack-1795638138175-14989` (6 planes at
43,432 to 43,470, one frame a plane). Per 64-pixel tile, the Laplacian's energy over the
tile's mean squared; a tile's best focus is the vertex of a parabola through its three
highest planes; tiles sharpest at the first or last plane are left out.

MEASURED: of 14,751 tiles, 3,622 peak inside the stack, 7,119 are sharpest at the first
plane and 2,443 at the last. A plane fitted to the 3,622 reads +8.0 units across the
frame's width and +7.8 across its height with 10 units of scatter, and two random halves
agree (7.1, 7.4 against 8.8, 7.8). That agreement means nothing: the tiles used are the
ones that happened to peak inside 38 units, the median best focus by region runs from
43,438 in the middle of the frame to 43,465 on the right with nothing like a plane in
it, and most of the frame's focus lies outside the stack.

So this stack cannot give the slide's tilt, and the count of tiles peaking inside is the
number that says so. The spec's Level reading is otherwise unmeasured.

---

## R11. What is kept, and the state the rig was left in

- **Frames kept for the spec's stage E3**, outside the repository:
  `D:/StrehlCaptures/setup-page-2026-11-27/` (8.6 GB, 31 bursts): thirteen capped dark
  bursts (the spec's nine, 1/8000 s, 8 s, and two with the light on), the two uncapped
  ISO 100 bursts that show the room's stray light, the four lit ISO 100 bursts that fail
  the Dark check, and the twelve bright bursts, each in a folder named for it, with
  `index.json`. Delete it when E3 has landed.
- **Deleted:** the two warm-up series, the settle ladder, the defocus probe, the three
  lit bursts at other ISO settings, six uncapped dark bursts the capped set replaces and
  four capped bursts at other shutter speeds (14.6 GB), the live-view recordings and the
  sample files in scratch. Their numbers are in this document
  and in `plates/`.
- **Rig:** camera and light off; four-shot, error correction and managed power on; the
  plan (32,332 to 33,169, step 8, settle 500 ms, approach 128) and the exposure (ISO 100,
  1.3 s) as found. During the work managed power was off for 43 minutes and error
  correction for 52, and again for 6 minutes during R9.
- **The owner's desktop** was not opened; the receiver ran throughout and was not
  restarted.
