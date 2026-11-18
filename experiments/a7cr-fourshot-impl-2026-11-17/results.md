# A7CR four-shot quality: implementation results (2026-11-17)

Status: implementation, author-run, not independently reviewed. Nothing
committed. Owner request (2026-11-16): "implement the ones you can without
extra captures needed from me", from
[the proposal](../../docs/proposals/2026-11-a7cr-four-shot-quality-improvements.md).
Every item is behind its own switch, default off; the default render is
unchanged byte for byte (below).

Subject: the white scarab four-shot run
`D:/StrehlCaptures/stack-1794786793543-11226` (196 groups, FE 100 mm macro
with the 2x converter wide open, ISO 100, 0.6 s), the same run the proposal
was measured on. One subject: every size here is to be re-measured on a
second subject before any default changes (proposal section 10).

Renders: `strehl stack <run> --demosaic`, CPU fold, 32 threads, Ryzen 9
9950X3D, 61.6 GB RAM; binaries copied from `target/release/strehl.exe` at
each step into ignored `outputs/a7cr-fourshot-impl/bin/` (banner build
string `cbca976b7e96-dirty` throughout; the copies are named by step). Half
stacks are `STREHL_FRAME_PARITY=odd` / `even`. Instruments are the
proposal's, from `experiments/a7cr-fourshot-quality-2026-11-16/` and
`experiments/a7cr-full-potential-2026-11-14/`; outputs in ignored
`outputs/a7cr-fourshot-impl/`.

## What was built

| Item | Switch | Where |
| --- | --- | --- |
| 1 Self-built flat field | `STREHL_SELF_FLAT=on` (`placebo`: map rolled 5, 3 photosites) | `merge_cmd/self-flat.rs`; applied in the banded gather's sample reads (`align_cmd.rs`) |
| 8 Lateral colour by component | `STREHL_CA_COMPONENTS=on` (`placebo`: shares reversed) | `merge_cmd/colour-components.rs`; gather in `align_cmd.rs`; shares and own-band scales in `strehl_core::optics::A7CR_FE100GM_2XTC_COMPONENTS`; band-limited residual check `strehl_core::ca_refine::measure_band` |
| 5 Gather kernel in the restoration's model | `STREHL_OPTICAL_RESTORE_GATHER=on` | `strehl_core::optical_restore` (`gather_table`, `ChannelModel::gather`), `merge_cmd/optical-restore.rs` |
| 3 Measured chroma filter | `STREHL_CHROMA_FILTER=measured` | `merge_cmd/optical-restore.rs` (after the restoration; the write skips the 1 px smoothing) |
| 2 Calibrated fusion | `STREHL_FUSION=calibrated` | `merge_cmd/fusion-calibrated.rs` (two folds; bands combined at the write) |
| 10 Frame registration refinement | `STREHL_REFINE_FRAMES=on` (`placebo`: reversed) | `merge_cmd/frame-refine.rs`; composed into each placement in `load_frame_impl_observed` |

Not built: item 4 (a true finest band) and item 6 (per-channel focus in the
depth guide) both need per-plane weights inside `strehl_core::pyramid`'s
accumulators, whose weight sum is shared by all twelve planes of a level;
item 7 the proposal says not to build; items 9 and 11 need captures.

A fix found on the way: the lateral-CA refinement's preview kept every
`stride`-th frame index counted from 0, so under `STREHL_FRAME_PARITY=odd`
with an even stride it kept no frame and the render failed ("every frame was
refused by the alignment solve"; the four-shot run's 784 raw files give
stride 8). It now counts from the first frame the parity keeps; unset or
`even`, the selection is unchanged (`ca_refine::on_stride` in
`merge_cmd.rs`).

## Default unchanged (VERIFIED)

`STREHL_PIXEL_SHIFT=remosaic`, everything else default (colour carry,
restoration and CA refinement on), full stack, with the item-8 binary:
SHA-256 `02A6C8C2...CC14CA`, identical to round 2's
`outputs/a7cr-fourshot-quality/default-full.tif` from the binary before any
change. The final binary's check is in the section "Final renders".

## Item 1: self-built flat field (MEASURED)

The map is built before the fold from all 784 raw frames (every member of
every group): 129 s on the CPU (`self flat field` banner line), six
segments of the 196 planes, each frame corrected by the segments neither
its own nor adjacent. Map rms (segment 0's, sampled over the active area)
0.41 / 0.44 / 0.49 % for R / G / B, mean trust 0.89 / 0.94 / 0.92, 1.4-2.2 %
of photosites under half trust.

Instrument: `fpn-pairs.py --band 0.08,0.30 --flat` on single groups rendered
alone (`STREHL_FRAME_PARITY=K-K`, raw carry, restoration off, refinement
off) and on two four-group merges, against round 1's renders of the same
frames with the same settings; read at the pattern's predicted rate
(`fpn-at-rate.py`: C at `a = -124 ppm x frame distance` and at `a = 0`,
where scene content sits). C is the pattern's share of the band's power,
`pattern / (pattern + noise)`.

| Green, C | at the pattern's rate | at rate 0 (scene) |
| --- | --- | --- |
| frame 100 against 101, as shipped | 0.288 | 0.276 |
| same, self flat | 0.093 | 0.094 |
| same, rolled placebo | 0.409 | 0.390 |
| frame 100 against 104, as shipped | 0.247 | 0.128 |
| same, self flat | 0.047 | 0.047 |
| frame 100 against 108, as shipped | 0.094 | 0.017 |
| same, self flat | -0.014 | -0.015 |
| four-group merges 98-101 against 102-105, as shipped | 0.485 | 0.303 |
| same, self flat | 0.134 | 0.143 |

Red and blue behave alike (frame 104: red 0.111 to 0.025, blue 0.158 to
0.018). With the map, C at the pattern's rate equals C at rate 0 in every
pair: no peak where the sensor pattern sits, so what remains is scene
content fixed to the output. Bars (proposal section 2): one group's green
pattern-to-noise from 0.33-0.41 to under 0.08 (the loosest bound, C at the
pattern's rate on the four-plane pair, 0.047, gives 0.05); four-group merge
from 0.94 to under 0.19 (loosest bound 0.134, giving 0.155); the rolled map
must raise it (0.288 to 0.409). All met.

By eye (`i1-stretch-merge4.png`: three smooth bright crops of 256 px chosen
on an image not shown, origins (8960, 2048), (7040, 512), (6912, 1152);
each channel relative to its 6 px local mean, stretched 20x; columns as
shipped, self flat, placebo): the as-shipped merge carries a fine mottle
with horizontal streaks; with the map it is visibly finer and the streaks
are gone; the placebo is as coarse as the shipped one or coarser.

## Item 8: lateral colour by component (MEASURED)

Instrument: `channel-shift.py --band` on raw-carry halves (restoration off),
three bands, displacement rms over 222 in-focus tiles (px), with the fitted
radial scale and offset.

| Arm | Red rms, coarse / mid / fine | Blue rms | Largest scale | Largest offset |
| --- | --- | --- | --- | --- |
| as shipped (profile only) | 0.289 / 0.600 / 1.026 | 0.338 / 0.303 / 0.428 | +423 ppm (red fine) | 0.308 px (blue y) |
| components on, refinement off | 0.248 / 0.192 / 0.079 | 0.306 / 0.150 / 0.051 | -62 ppm | 0.306 px (blue y) |
| components on, refinement on (own bands) | 0.225 / 0.181 / 0.077 | 0.141 / 0.102 / 0.048 | +60 ppm | 0.055 px |
| placebo (shares reversed) | 1.719 / 2.264 / 2.035 | 0.698 / 0.851 / 0.921 | +915 ppm | 0.311 px |
| bar | 0.25 / 0.15 / 0.08 | 0.15 / 0.12 / 0.06 | 80 ppm | 0.07 px |

(Bands 0.03-0.08 / 0.11-0.18 / 0.24-0.42 cycles/px.) With the refinement
run on the own bands, every scale is within 80 ppm and every offset within
0.07 px; blue meets its rms bars in every band, red in the coarse and fine
bands, and red's mid band reads 0.181 against the bar's 0.15 (the prototype
reached 0.14). The refinement measured red -17 to -31 ppm and blue +52 to
+59 ppm with blue's own-band offset (+0.014 to +0.017, +0.424 to +0.438) px
on the two halves, the 0.38 px the proposal found. The render's own
residual check (banner `colour by part : residual`) read, refined, coarse
red -16 to -23 ppm, blue +10 to +12 ppm; fine red +21 to +22 ppm, blue -1
ppm.

Noise and colour (`compare-colour.py`, ratios to as shipped): fine-band
noise amplitude red 1.033-1.034 (power 1.07; bar 1.08), blue 1.015-1.019,
green 1.000 (green is untouched by construction); coherent red-minus-green
edge-band chroma 0.917, blue-minus-green 0.935 (fringes are chroma signal
to this instrument, so lower is less fringe); placebo 1.496 and 1.260.

Rim colour by side (`rim-colour.py`, classes from the base arm's even half,
odd halves scored; red-minus-green difference between opposite sides of
bright detail, 3.5-10 px): as shipped -0.72 (vertical) and -1.36
(horizontal) points; components with the refinement -0.63 and -0.61 (bar:
within 0.7); placebo -4.29 and +5.27. Blue-minus-green vertical: +2.48 as
shipped, +1.29 refined.

## Item 2: calibrated fusion (MEASURED)

Halves with raw carry, restoration off, refinement off; the election is the
same settings with no fusion (`i8-base`). Two folds per render: 335 s per
half against about 100 s for the election, peak 24.0 GB.

A first version split the bands on each half-resolution site plane. It
fixed the dark lift but left fine detail at 0.92 (green) of the election's:
a site plane holds output detail above 0.25 cycles/px only aliased, so one
gain on its top band could not reach it (band gains came out 1.07-1.13
where the prototype found 1.27-1.32). The shipped version interleaves each
channel's four site planes to full resolution and takes the prototype's
bands there: gains (both halves) R 1.24-1.25 / 1.03-1.04 / 0.99 / 0.98 /
0.99 / 1.01, G 1.27-1.28 / 1.07 / 1.01 / 1.00 / 1.00 / 1.01, B 1.23-1.24 /
1.03 / 0.99 / 0.98 / 0.99 / 1.01 at 0-1 / 1-2 / 2-4 / 4-8 / 8-16 / 16-32
output px (the prototype: 1.27-1.32, 1.03-1.08, 0.98-1.01).

`compare-colour.py`, ratios to the election (fine band 0.25-0.40 cycles/px):

| Arm | Fine detail R / G / B | Noise R / G / B | Signal-to-noise power R / G / B |
| --- | --- | --- | --- |
| election | 1 / 1 / 1 | 1 / 1 / 1 | 8.64 / 18.24 / 4.56 |
| fusion (`depth`) | 0.90 / 0.81 / 0.85 | 0.66 / 0.60 / 0.70 | 15.95 / 33.45 / 6.67 |
| calibrated, per-plane bands (first version) | 0.99 / 0.92 / 0.91 | 0.73 / 0.68 / 0.75 | 15.98 / 33.54 / 6.68 |
| calibrated (`calibrated`) | 1.09 / 1.01 / 1.01 | 0.81 / 0.75 / 0.84 | 15.77 / 33.04 / 6.59 |

`radial-ratio.py`, green, calibrated against the election: signal 0.99-1.03
from 0.05 to 0.43 cycles/px, then 0.95 / 0.88 / 0.77 at 0.444 / 0.469 /
0.494 (the top octave, item 4's territory); signal-to-noise 1.8-2.6x below
0.25 cycles/px, 1.4-1.8x at 0.3-0.4.

`halo-distance.py` (classes from the election's even half, odd halves,
green, ratio of the dark level to the election's):

| Arm | 3-6 px | 6-12 | 12-20 | 20-30 | 30-50 | 50-100 | 100-200 | 200+ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fusion | 1.260 | 1.078 | 1.090 | 1.120 | 1.137 | 1.101 | 1.171 | 1.087 |
| calibrated | 1.090 | 0.968 | 0.968 | 0.963 | 0.958 | 0.955 | 1.007 | 1.014 |

Against the proposal's bars: fine detail at least 0.98 of the election's in
every channel, met; signal-to-noise power at least 1.8x, met in red (1.83x)
and green (1.81x), not in blue (1.45x; the uncalibrated fusion's blue is
also 1.46x: the guide weights blue by green's focus while blue focuses
about two frames later, which is item 6); signal ratio flat within 3 % from
0.05 to 0.40, met; dark level within 3 % of the election's beyond 6 px and
5 % within, not met (3.2-4.5 % darker at 6-100 px, 9 % lighter within 6 px;
the prototype read the same). Which shadow level is right is still not
established (proposal section 9, capture 3): the far-field lift is gone,
and the remaining differences are within the 5 % that a single-frame
reference could resolve.

## Item 10: frame registration refinement (MEASURED: does not help; leave off)

Built as the proposal describes, up to the solve. After the global solve,
every frame's green is gathered; frames two to four planes apart are
measured with `strehl_core::ca_refine::measure` (579 pairs, 230-240 s).
The result is a correction composed before each frame's placement.

A first version solved one free similarity per frame from those pairs,
with the anchor fixed. It returned corrections of up to 2 413 ppm and 2.9 px
rms, which is not a residual of a working alignment, and was replaced
before any scoring. The shipped version fits one rate per plane: a
trimmed, weighted mean of each pair's scale and translation divided by its
distance. Frame k is corrected by rate x (k - anchor).

What the pairs say (`STREHL_REFINE_FRAMES_DUMP`, `i10-pairs.json`): median
pair y offset 0.092 / 0.143 / 0.201 px at 2 / 3 / 4 planes, about 0.05 px
per plane, the size of the proposal's 0.13 px rms at one plane. But the
rate is not constant along the stack. Per plane in y it is +0.085 over
planes 0-50, +0.057 over 50-100, +0.041 over 100-150 and -0.046 over
150-196. Scale per plane is +15, +14, -9 and -46 ppm. The fitted rates:
scale -7.3 ppm, translation (+0.004, +0.047) px per plane, so the ends of
the stack move about 4.6 px. Pair scale left after the fit: 81.5 ppm rms.

Halves as in item 2 (raw carry, restoration off), `compare-colour.py`,
ratios to the election, fine band:

| Arm | Fine detail R / G / B | Noise R / G / B | Signal-to-noise power R / G / B |
| --- | --- | --- | --- |
| fusion | 0.902 / 0.814 / 0.846 | 0.665 / 0.613 / 0.702 | 15.95 / 33.45 / 6.67 |
| fusion, refined | 0.898 / 0.783 / 0.866 | 0.687 / 0.617 / 0.724 | 14.83 / 30.55 / 6.56 |
| fusion, refinement reversed (placebo) | 0.873 / 0.816 / 0.819 | 0.669 / 0.614 / 0.703 | 14.70 / 33.28 / 6.25 |
| calibrated | 1.093 / 1.010 / 1.014 | 0.807 / 0.763 / 0.844 | 15.77 / 33.04 / 6.59 |
| calibrated, refined | 1.064 / 0.962 / 1.008 | 0.815 / 0.759 / 0.845 | 14.65 / 30.14 / 6.48 |

`radial-ratio.py`, green, fusion: the refined arm's signal is below the
unrefined one's from 0.12 cycles/px up: 1 % at 0.16, 4-5 % at 0.31-0.36,
9 % at 0.44 (slightly above it below 0.1). The calibrated fusion's finest-band gains (fusion to election)
fell slightly with the refinement: G 1.274-1.278 to 1.263-1.268, but its
1-2 px band also fell from 1.07 to 1.05, and red and blue lost more.

Against the bars (proposal item 10): under the fusion, fine signal should
come back at no noise cost. Green lost 4 %, red 0.4 %, and signal-to-noise
fell in every channel. The placebo should be worse than the refinement.
It is in red and blue, not in green. Not met. The proposal's residual bars
(`series-focus.py` within 3 ppm per plane and 0.12 px rms at four planes)
were not run: they need the 33 single-group renders, and the end-to-end
result already rules this version out.

`halo-distance.py` cannot score this arm. It classifies dark and bright
from the election's half, and the refinement moves content by up to 4 px
depending on which frame it is sharp in, so its dark classes land on
moved edges (refined G ratio 3.85 at 3-6 px, placebo 3.06; bright 0.98).
That reading is the instrument's geometry, not a halo.

Why it fails (ARGUED): the rate changes sign along the stack, so one
linear rate fixes the middle and adds error at both ends. And the
measurement weights every textured tile, not only tiles sharp in both
frames as the proposal specifies. Defocused content whose centroid moves
with focus (rail tilt, non-telecentric blur) reads as misregistration
that is not there. The free solve's blow-up points the same way. Next
version, unbuilt: restrict the pairs to tiles sharp in both frames, fit a
smooth (per-segment or spline) rate along the stack, and validate against
`series-focus.py` and a planted 40 ppm per plane before any render.

## Item 5: the gather kernel in the restoration's model (MEASURED)

Halves with raw carry and the default restoration, with and without
`STREHL_OPTICAL_RESTORE_GATHER=on`; `radial-ratio.py`, green, ratio of the
arm to the restoration as shipped:

| cycles/px | 0.106 | 0.156 | 0.206 | 0.256 | 0.306 | 0.356 | 0.406 | 0.444 | 0.494 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| signal | 0.985 | 0.979 | 0.979 | 0.990 | 1.010 | 1.040 | 1.065 | 1.066 | 1.041 |
| signal-to-noise | 0.999 | 1.000 | 1.000 | 0.999 | 0.999 | 0.998 | 1.000 | 1.003 | 0.995 |

Signal-to-noise is unchanged at every frequency, as a linear filter must
leave it (the control). The gain in signal is much smaller than the
proposal predicted (+3 / +12 / +35 % at 0.2 / 0.3 / 0.4 cycles/px on an
axis): about -2 % at 0.2, +1 % at 0.3, +6.5 % at 0.4. The banner shows why:
with the gather's power divided out of the reference spectra, the joint
cutoff fit moved from 0.620 to 0.664 cycles/px (green; red 0.553 to 0.592,
blue 0.713 to 0.764). On this stack the fit had been absorbing the gather's
roll-off into a lower diffraction cutoff, which is the bias the module's
own "Limit" note describes, so the old model already restored most of what
the gather takes. The proposal's planted test (the fitted cutoff must not
move) holds on synthetic spectra (`a_gathered_planted_cutoff_is_recovered_
once_the_gather_is_divided_out`); on real data the cutoff is not separable
from other blur. Worth keeping as the more honest model; not worth much on
its own.

## Item 3: measured chroma filter (MEASURED)

Halves with components on (item 8) and the default restoration: the 1 px
smoothing (as shipped), the measured filter, and no chroma step at all
(raw carry). Instrument: [chroma-error.py](chroma-error.py), each arm's odd
half scored against the raw arm's even half (independent noise, same
registration and restoration), 262 in-focus tiles; error of the estimate of
each channel's own content, % of that channel's signal power (100 % is what
writing no detail would score). Control: the raw odd half scored as an arm
reads its own noise (E = N), as it must.

| Arm | Red 0.10-0.25 / 0.25-0.40 cycles/px | Green | Blue |
| --- | --- | --- | --- |
| 1 px smoothing (as shipped) | 13.4 / 82.0 | 0.7 / 5.4 | 6.8 / 126 |
| measured filter | 2.1 / 12.0 | 0.7 / 5.4 | 1.7 / 19.8 |
| none (raw carry, restored) | 2.1 / 12.3 | 0.7 / 5.4 | 1.7 / 19.1 |

The measured filter matches the no-filter arm (which carries the
restoration's per-channel Wiener) within 0.7 points everywhere, the
proposal's bar, and has a sixth to a seventh of the smoothing's error in
the fine band on this subject. It kept 0.98 / 0.94 / 0.87 / 0.72 of red
minus green and 0.96 / 0.90 / 0.83 / 0.72 of blue minus green at 0.1 / 0.2 /
0.3 / 0.4 cycles/px (banner): the scarab's colour differences are well
above noise, so the filter stays near "keep". On a subject with little fine
colour it should fall toward the smoothing's behaviour; that is the
second-subject check the proposal asks for and it is not done. (The
script's noise column mixes signal mismatch into noise and is not used.)

By eye (`i3-chroma-sat3.png`, colour differences tripled, origins (1650,
2990), (8000, 1500), (4700, 3100), 110 px at 4x; columns smoothing,
measured odd, measured even, raw): the measured filter looks like raw carry,
with the finer pastel colour mottle the smoothing removes; at normal
saturation the difference is slight on this pale subject.

## Final renders

Full stack, `STREHL_PIXEL_SHIFT=remosaic`, everything else default (colour
carry, restoration and CA refinement on), final binary
`bin/strehl-final.exe` (`batch-final.ps1`, `batch-final2.ps1`):

| Render | Switches | Time | Peak private |
| --- | --- | --- | --- |
| `final-default-full` | none | 341 s | 23.9 GB |
| `final-election-full` | `STREHL_SELF_FLAT=on`, `STREHL_CA_COMPONENTS=on`, `STREHL_CHROMA_FILTER=measured`, `STREHL_OPTICAL_RESTORE_GATHER=on` | 495 s | 25.2 GB |
| `final-calibrated-full` | the above plus `STREHL_FUSION=calibrated` | 847 s | 26.7 GB |

The planned third render, every switch including `STREHL_REFINE_FRAMES=on`,
was stopped once item 10 measured harmful and was replaced by
`final-calibrated-full`.

Default unchanged (VERIFIED): `final-default-full.tif` SHA-256
`02A6C8C2FAAFC3E266627F1E540F0E98A9690429BADC20B590EB5C32CBCC14CA`, equal to
round 2's `outputs/a7cr-fourshot-quality/default-full.tif`. A7C II
byte-freeze on the final tree (VERIFIED): 5 of 5 renders reproduce their
recorded bytes, each twice
(`STREHL_FREEZE_REQUIRE=1 cargo test --locked --release -p strehl-cli --test byte-freeze`,
exit 0, `Compiling strehl-cli` in the log, `byte-freeze.log`).

Banners on the full stack (MEASURED, this run):

- Self flat: 124-127 s, maps reused by the preview and both fusion passes.
- Colour by part, residual after the refinement: coarse red -14.5 ppm,
  blue +9.3 ppm (election); -31.6 ppm and -6.2 ppm (calibrated). Fine red
  +18.2 / +16.7 ppm, blue -2.0 / -4.2 ppm. Every offset is within 0.07 px.
- Restoration with the gather in the model: cutoffs R/G/B 0.599 / 0.672 /
  0.773 cycles/px against the default's 0.556 / 0.624 / 0.718. The
  restored MTF reaches the 0.68 target at 0.2 cycles/px in every arm.
- Measured chroma filter, kept share of red minus green at 0.1/0.2/0.3/0.4
  cycles/px: 0.99/0.97/0.93/0.85 (election) and 1.00/0.99/0.96/0.90
  (calibrated). Blue minus green: 0.98/0.95/0.90/0.83 and 0.99/0.97/0.94/0.87.
  These are higher than on the half-stacks because the full stack has
  more signal.
- Calibrated band gains, 0-1 / 1-2 px: R 1.267 / 1.038, G 1.311 / 1.076,
  B 1.262 / 1.030 (the half-stacks read 1.24-1.28 / 1.03-1.07).

By eye (orientation, not measurement; crops chosen on the default render,
one display transform, no resampling; columns default, election-full,
calibrated-full):

- `final-detail3.png`: 320 px crops of the most detailed tiles, origins
  (6560, 1120), (3200, 2560), (6240, 1920). The three are hard to tell
  apart at native scale. The calibrated column is slightly crisper on
  scale edges.
- `final-smooth3.png`: 256 px smooth bright crops, stretched 20x about
  each crop's local mean, origins (7040, 256), (8960, 1408), (8192, 768).
  - The default carries isolated single-pixel coloured dots and a fine
    diagonal texture. With the new switches most dots are gone and the
    mottle is finer.
  - The election-full column keeps magenta streaks that the default's
    1 px chroma smoothing weakens. The measured filter keeps colour that
    both half-stacks share, which includes scene colour and any fringe
    common to both, so whether these streaks are scene is not
    established.
  - The calibrated column replaces the election's blotchy mottle with
    fine, even grain, and the magenta streaks are absent. They may be
    content the election takes from one frame and the fusion averages
    away. Which is right is not established.
