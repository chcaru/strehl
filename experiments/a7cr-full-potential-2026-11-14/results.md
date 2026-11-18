# A7CR full potential: results (2026-11-14 to 2026-11-15)

Status: prototype, author-verified, uncommitted. One capture, one subject (a
coin cell: specular, with clipped highlights). Not independently reviewed. Not
a product path: Python on the GPU. The [brief](brief.md) fixed the arms and
bars before any arm ran; deviations from it are listed.

## Result

On capture 3's four-shot run, against the shipped `strehl stack` on the same
frames, over 96 in-focus tiles of 256 px (6.3 MP), from independent
realisations (MEASURED, [evaluate.py](evaluate.py); values are red / green /
blue, each a ratio to the shipped stack):

| Arm | Fine-detail signal, 0.25-0.40 cycles/px | Signal, 0.10-0.25 | High-pass noise |
| --- | --- | --- | --- |
| S0 shipped | 1 | 1 | 1 |
| C1 shipped + P3's linear filter (66 tiles) | 2.01 / 1.57 / 1.23 | 1.28 / 1.27 / 1.15 | 1.86 / 1.50 / 1.23 |
| Selector, four shots, own focus per channel | 1.13 / 1.47 / 1.72 | 1.16 / 1.06 / 1.18 | 0.35 / 0.32 / 0.50 |
| Selector, one demosaiced shot | 1.02 / 1.24 / 1.51 | 1.05 / 1.04 / 1.13 | 0.55 / 0.48 / 0.68 |
| Fusion, one demosaiced shot | 0.76 / 1.03 / 1.19 | 1.00 / 0.97 / 1.07 | 0.14 / 0.13 / 0.18 |
| P1 fusion, four shots, green's focus for all | 0.87 / 1.25 / 1.45 | 0.92 / 0.98 / 1.10 | 0.12 / 0.08 / 0.17 |
| Placebo: red and blue depth maps swapped | 0.95 / 1.25 / 1.38 | 0.99 / 0.98 / 1.04 | 0.12 / 0.08 / 0.17 |
| **P2** fusion, own focus, lateral colour ("clean") | 1.03 / 1.25 / 1.50 | 1.09 / 0.98 / 1.11 | 0.12 / 0.08 / 0.17 |
| P3 linear restoration (target sigma 0.70) | 2.02 / 1.97 / 1.87 | 1.52 / 1.25 / 1.29 | 0.29 / 0.15 / 0.20 |
| **P3** root-domain restoration ("restored") | 2.06 / 2.14 / 2.07 | 1.60 / 1.35 / 1.40 | 0.28 / 0.15 / 0.22 |
| P3 root-domain, target sigma 0.60 ("crisp") | 2.56 / 2.63 / 2.57 | 1.71 / 1.44 / 1.49 | 0.41 / 0.23 / 0.30 |

**Correction (2026-11-15, see "Matte subject: scarab" below): the S0
baseline here pairs two separate captures, which inflates S0's noise about
3x and costs it 8-12 % of fine-detail signal on this coin (measured against
odd/even half-stacks of one capture). Against that fairer baseline the
figures become roughly 1.8x the signal at 0.5-0.8 of the noise (DERIVED by
rescaling, not re-run; the halves were deleted). The row values are kept as
measured against the original S0.**

Reading: the recommended output ("restored") carries about twice the shipped
stack's fine-detail signal at 0.15 to 0.28 of its noise; "clean" carries 1.0
to 1.5 times the signal at 0.08 to 0.17 of the noise. Naively sharpening the
shipped stack with the same filter (C1) buys its signal with 1.2 to 1.9 times
the noise.

What the four shots themselves add, same pipeline, one demosaiced shot per
plane against four measured-colour shots: fine-detail signal x1.35 / 1.21 /
1.26 and fine-detail signal-to-noise x1.6 / 2.0 / 1.35 (fusion rows), or
signal x1.10 / 1.18 / 1.14 with the selector. The rest of the gain over the
shipped stack is the pipeline and would apply to single-shot captures too.

Viewing renders (one colour and tone transform, [render.py](render.py)) are
in ignored `outputs/a7cr-full-potential/final/`: `shipped-srgb.tif`,
`new-clean-srgb.tif`, `new-restored-srgb.tif`, `new-crisp-srgb.tif`, 1/4-scale
previews, and crops `crops-100pct-a.png`, `crops-100pct-b.png` (400 px,
origins (1400,1500), (4200,2800), (7100,1500), (2100,2900)) and
`crops-300pct.png` (128 px repeated 3x, for the eye only; origins (1560,1640),
(4340,2930), (7230,1630), (2330,3060)). Columns: shipped, clean, restored.

## Bars

| Bar | Verdict | Evidence |
| --- | --- | --- |
| N1 noise, P3 <= 1.05 x S0 | **Pass** | 0.28 / 0.15 / 0.22 |
| R1, P1 >= 0.95 x S0 | **Pass green and blue, fail red** | 0.87 / 1.25 / 1.45. Red's shortfall is axial colour (P1 puts red on green's focus); P2 lifts it to 1.03 |
| R1, P3 >= 1.5 x S0 | **Pass** | 2.06 / 2.14 / 2.07 |
| C1 expected to pass R1 and fail N1 | **As predicted** | signal 2.01 / 1.57 / 1.23, noise 1.86 / 1.50 / 1.23. Blue's signal misses 1.5. Scored on 66 of the 96 tiles: the filtered shipped image trips the clip check on the others, so the tile sets differ |
| L1 lateral colour <= 0.10 px rms | **Fail** | One scale and offset per channel leaves 0.35 px (red) and 0.23 px (blue), from 2.50 and 0.89 px uncorrected. A free-form field scored 0.22 / 0.19 px held out (on an earlier arm of the same data) and was not adopted. The two halves' tile displacements agree to 0.04 px, so the residue is repeatable structure, not noise; its cause is not established |
| A1 own focus helps red and blue | **Pass**; placebo **fails as registered for red** | Red 0.87 -> 1.03, blue 1.45 -> 1.50. Swapped maps: blue falls to 1.38 (as required), red reads 0.95, above P1. Red's and blue's focus both lie on the same side of green's, so blue's map is nearer red's truth than green's is. The placebo was mis-specified for a same-side offset (fact 1416 says exactly this) |
| M1 demoted groups within 1.2x of passing groups | **Partial** | 24 of 35 demoted groups; median ratio 1.12, worst 2.60. The rest have a member blurred during its exposure |
| Eye | "clean" and "restored" pass at 1:1; linear P3 fails | Linear restoration drives pixels beside bright glints below zero (-259 DN beside a 10 000 DN glint on a 200 DN ground). The root-domain variant does not; at 3x it still shows faint ripples beside the brightest glints |

## What the pipeline is

Scripts in this directory; data flow:

1. [export-members.rs](export-members.rs): member mosaics per plane, with
   `pixel_shift::register`'s offsets and gains.
2. [pass0.py](pass0.py) with [fp.py](fp.py): assembly of measured R, G, B per
   plane. Each member's sub-photosite offset and blur difference is fitted
   jointly from the 2-photosite-period traces it leaves in all three channels
   (noise-corrected least squares, 28 unknowns) and compensated to first
   order. No group is demoted.
3. [align.py](align.py): per-plane similarity from spans 1-4 on quarter-scale
   green.
4. [fuse.py](fuse.py) `energy`, `depth`: through-focus band power per 1/8
   cell, Gaussian fit, depth map per channel, plane quality.
5. [coherence.py](coherence.py): measured coherent transfer of a plane j
   offsets from focus, per band.
6. `fuse.py fuse`: per channel and band, planes weighted by that measured
   transfer t and combined as sum(t Y) / sum(t^2), with odd and even planes
   kept as two independent halves.
7. [ca.py](ca.py): lateral colour measured on the fused image, one resampling
   of red and blue.
8. [restore.py](restore.py): cutoff, fusion transfer and noise measured from
   the halves; filter to a Gaussian target; optional root domain; highlight
   protection.

## Measured on this capture

- **The image rotates through the stack**: 1.34 mrad end to end (theta
  +7.5e-4 to -5.9e-4 rad over 107 planes), about 4 px at the corners, on top
  of a 1.5 % magnification change. The shipped warp map shows the same drift.
  Cause not established (a slow roll of the stabilised sensor is a guess).
- **Highlights walk with defocus.** After the similarity fit, span-1 tile
  residuals are 0.20 px rms and grow in proportion to span; 0.12 px per plane
  of that is a fixed field. ARGUED: a specular facet fills only part of the
  aperture, so its defocused image shifts as well as blurs. This is why
  lateral colour measured inside one plane was confounded (red is defocused
  where green is sharp, so its glints sit elsewhere).
- **Coherent transfer is wide.** In the finest band (above about 0.3
  cycles/px) a plane 2 from focus contributes 0.93-0.97 of the in-focus
  coefficient, 4 planes 0.81, 6 planes 0.54-0.60 (green, one 2048-px central
  crop). The incoherent amplitude is 3-7 % higher out to 4 planes and 18-26 %
  higher at 6, so the walk costs little near focus. Measured on the eval
  tiles, the fusion's net transfer against the selector is 0.85-0.97 over
  0.2-0.4 cycles/px (green 0.85-0.90); restoration divides it out. That bounds
  what trajectory compensation could add to amplitude at about 10-15 %.
- **Focus curve**: Gaussian sigma 5.1 / 6.1 / 7.6 planes in power for bands
  at 1, 2 and 4 px (step 8 units), so the stack oversamples focus about
  tenfold and the fusion's noise variance is 0.10 of one plane's in the finest
  band.
- **Axial colour**: red's focus is 5.3 planes (42 units) from green's at the
  median, 5.9 at the centre falling to 1.9 at the corner; blue's 1.45 planes,
  same side.
- **Lateral colour**: red -800 ppm (4.6 px at the corner), blue +259 ppm
  (1.5 px), offsets (+0.17, -0.34) and (-0.10, +0.23) px. The A7C II profile
  in `optics.rs` (-508 ppm red) is not applied to this body, which is part of
  why the shipped render fringes.
- **Diffraction cutoff, read from the selector's signal spectrum**: red 0.480,
  green 0.536, blue 0.616 cycles/px = 128 / 143 / 164 cycles/mm. At nominal
  channel wavelengths (0.600, 0.535, 0.465 um, assumed) each gives N_eff =
  13.1. Three independent fits agreeing is the evidence that the blur is
  diffraction; the absolute 13.1 inherits the assumed wavelengths. It replaces
  the 15 used in `a7cr-impl-2026-11-14/results.md`. Green's and blue's
  cutoffs lie above the sensor's 133 cycles/mm Nyquist.
- **Member motion**: largest member offset per group 0.079 px median, 0.127
  at the 90th percentile, 0.214 worst; rigid across the frame (per-tile spread
  about 0.02 px). 19 of 107 groups hold a member with a blur difference above
  0.08 (worst 0.37, about 2 px of smear in a 2 s exposure). Plane quality
  (in-focus power against the fitted curves) is 0.86 at worst, 1.00 median.
- **The shipped merge is noisier than one plane**: the selector's two-plane
  mean on demosaiced single shots reads 0.48 of the shipped noise, so one such
  plane is about 0.68 and the shipped output about 1.5 planes' worth of noise
  amplitude. Not investigated further.

## Limits and what would fool this

- One capture and one subject. The specular subject makes linear restoration
  ring; a matte subject would tolerate a sharper target. Nothing here is a
  default.
- "Signal" is whatever both realisations share: fixed pattern, deterministic
  ringing and, for S0, demosaic aliasing at a fixed CFA phase all count.
  "Noise" is whatever differs, including the shipped merge electing different
  frames in its two captures. S0's two realisations are separate captures;
  the prototype's are odd and even planes of one.
- The restored arms' signal figure includes the restoration's gain by
  construction; R1 for P3 shows the filter did what it was designed to do at
  the stated noise, not that detail was created. Nothing beyond the cutoff is
  recovered.
- The root-domain filter is not a linear filtering of the scene. Its designed
  response holds for low-contrast texture only.
- Restoration strength is a taste parameter bounded by ringing, not by noise:
  with a support limit near 0.5 cycles/px a positive point spread cannot be
  much sharper than the lens's own (target sigma 0.70 has about 1-2 % negative
  lobes, 0.50 about 6 %).
- Depth maps, coherence tables and alignment were fitted on the four-shot
  data and reused for the one-shot control. Red uses green's coherence table
  (its own rests on too few sites in the measured crop).
- Alignment uses near spans only; far planes random-walk. Fusion combines
  neighbours, so this bends global geometry slightly and was not scored.
- The frame is cropped to the box every plane covers (51 px left and right,
  37-43 px top and bottom).
- The noise model constants are the A7CR profile's; restoration uses measured
  spectra and does not depend on them, the member fit's bias correction does.
- Timings were not benchmarked. Order of magnitude on an RTX 5090: export 2
  min, pass 0 6 min, align 1 min, energy 2 min, each fusion pass 2-8 min.

## Deviations from the brief

- Lateral colour is corrected once on the fused image, not per plane.
- Fusion weights are the measured coherent transfer, not a Gaussian from the
  power fit. The first version normalised narrowed Gaussian weights by
  sum(h^2), which amplified the finest band by up to 1.41; found and replaced
  before any reported number.
- N1's high-pass is evaluated in the Fourier domain as auto- minus
  cross-spectrum, which removes registration from the noise figure.
- P3 has a root-domain variant and highlight protection, added after the
  linear filter failed the eye bar.
- Tiles require 50 % strongly focused cells (the first cut used 70 % and found
  30 tiles).

## Next

1. A second subject, matte, and a repeat of this one shot quieter (shorter
   exposure, nobody walking), to see which numbers are properties of the
   pipeline. Logged in `docs/captures-needed.md`.
2. Bare lens with 16-shot pixel shift, same subject. DERIVED: without the
   teleconverter N_eff is about 6.5 and green's cutoff about 285 cycles/mm at
   the sensor, more than twice the 133 cycles/mm that single or four-shot
   capture samples; 16 shots sample 266. That is the same sampling of the
   subject as today's rig over four times the area. Costs: the photosite
   aperture's response is lower toward the top of that band (0.30 against
   0.78 at three quarters of it, the same subject frequency in both rigs), 16
   files per plane, and the bare lens wide open may not be diffraction
   limited. UNVERIFIED until captured; the 16-shot assembly is not written.
3. Product path, in order of value per effort: lateral colour for this body
   (two scalars, measured here); per-channel focus; measured-offset assembly
   in place of demotion; coherent-weight fusion; restoration as an opt-in
   stage.

## Commands

Build `cbca976b7e96-dirty`; Python 3 with torch 2.11 (CUDA), RTX 5090. Run
from the repository root; `W=outputs/a7cr-full-potential/work`,
`E=experiments/a7cr-full-potential-2026-11-14`.

```sh
cargo build --locked --release -p strehl-cli --example a7cr-export-members --example a7cr-export-demosaic1
target-ui/release/examples/a7cr-export-members.exe D:/StrehlCaptures/stack-1794689780304-11226 outputs/a7cr-full-potential/cache4
python -X utf8 $E/pass0.py outputs/a7cr-full-potential/cache4 $W
python -X utf8 $E/align.py $W
python -X utf8 $E/fuse.py energy $W g --no-ca
python -X utf8 $E/fuse.py depth $W g
python -X utf8 $E/coherence.py $W g 3200 2100 2048
python -X utf8 $E/fuse.py fuse $W g ARMS.json   # f1, f2, f2x, selo: see fuse.py
python -X utf8 $E/ca.py $W f2 f2c --model-only  # likewise selo -> seloc
strehl stack <single-shot run> --demosaic --out s0/single.tif
STREHL_PIXEL_SHIFT=member1 strehl stack <four-shot run> --demosaic --out s0/member1.tif
python -X utf8 $E/evaluate.py $W outputs/a7cr-full-potential/s0 EVAL f2c seloc
python -X utf8 $E/restore.py $W EVAL f2c f5 --ref-arm seloc --sigma-t 0.70 --root
python -X utf8 $E/evaluate.py $W outputs/a7cr-full-potential/s0 EVAL f2c f4 f5 f5k f1 f2x seloc m1c m1selc
```

The one-shot control: `a7cr-export-demosaic1.exe <run> $W/asm-m1`, then
`FP_ASM=asm-m1 python fuse.py fuse ...`. C1: `restore.py ... --apply-to-tiff`.
Working data (decoded members, assembled planes, fused arrays; about 150 GB at
peak) was deleted after the run; the commands regenerate it.

## Product integration: lateral and axial colour (2026-11-15)

Owner request: implement the two colour corrections in the product.
Build `cbca976b7e96-dirty` plus this change, `--release`, `--demosaic`, CPU
fold, decode-ahead on, 32 threads. Input: both runs of capture 3.

### Lateral colour: A7CR profile, default on (MEASURED)

- New `OpticalProfile` `a7cr-fe100gm-2xtc` in `crates/strehl-core/src/optics.rs`
  (ILCE-7CR, `LensType3` 33094), applied radially (translation recorded, not
  applied), picked up by the existing gear guard and per-capture refinement.
- Measured with [lateral-profile.py](lateral-profile.py) on the shipped
  stacker's own uncorrected renders (`outputs/a7cr-full-potential/s0/`):
  red -463.8 / -465.4 ppm, blue +205.8 / +205.3 ppm (single-shot / member 1),
  3014-3022 tiles, R^2 0.965 (red) and 0.951 (blue), permutation p <= 0.0005
  (2000 shuffles, none reached the observed |eps|), tiles out to 0.985 of
  the half diagonal. The A7C II record for the same lens and converter reads
  -508.4 / +174.4 ppm: agreement within that record's stated 151 ppm
  subject-to-subject spread, as expected when lateral CA belongs to the glass.
- These differ from the prototype's -800 / +259 ppm because the prototype
  read red and blue at their own focus; the shipped merge reads them at
  green's elected frame.
- Effect, [compare-colour.py](compare-colour.py), two independent captures,
  91 in-focus tiles of 256 px with under 1 % clipped pixels, ratios to the
  uncorrected render:

  | Arm | Coherent R-G fringe | B-G | Fine detail R / G / B (0.25-0.40 cycles/px) | High-pass noise R / G / B |
  | --- | --- | --- | --- | --- |
  | Profile, no refinement | 0.745 | 0.760 | 0.987 / 0.975 / 0.983 | 0.990 / 1.005 / 1.012 |
  | Profile + refinement (the default) | 0.739 | 0.732 | 0.982 / 0.976 / 0.978 | 0.985 / 1.002 / 1.003 |

  Default render times 60 s (single-shot) and 107 s (member 1) including the
  refinement preview; 41 s each without it.
- Residual displacement by the lateral-profile instrument (rms over tiles,
  sensor px): red 1.467 -> 0.538 and blue 0.681 -> 0.198 with the default.
  That instrument still reads -148 ppm of red radial residual after the
  default and -80 ppm after the profile alone, while the product's own
  refinement instrument moved the profile by +82 ppm (single-shot) and
  +54 ppm (member 1). The two instruments disagree by about 0.1-0.2 px at the
  corner; not resolved. The fringe metric prefers the default, narrowly.
- A7C II byte-freeze: 5 of 5 renders reproduce their recorded bytes
  (`STREHL_FREEZE_REQUIRE=1 cargo test --locked --release -p strehl-cli --test byte-freeze`).

### Axial colour: `STREHL_AXIAL_CA`, default off (MEASURED, not a net win here)

Superseded by "Axial colour investigation" below: this is the first version.
Its ARGUED cause (the highlight walk) was tested there and is not the main
one, and its placebo was not a clean control.

- `crates/strehl-cli/src/merge_cmd/axial-colour.rs`. Measurement from every
  frame (64 px tiles, through-focus peak per channel, smooth field fitted per
  channel). On capture 3: red +5.52 frames from green (IQR +4.87..+6.09),
  blue +2.11 (+1.64..+2.60), green site 1 against site 2 -0.009 (scatter
  0.17); 1389 of 3626 tiles left out for clipping; 19.3 s. The prototype
  measured +5.3 and +1.45.
- Merged frame `k` then takes red and blue interpolated from the frames at
  `k + d(x)`; green and the election are untouched. Default-off path: the
  module returns immediately (byte-freeze above).
- Effect, same instrument and tiles, ratios to the uncorrected render:

  | Arm | R-G fringe | B-G | Fine detail R / G / B | Noise R / G / B |
  | --- | --- | --- | --- | --- |
  | Lateral default | 0.739 | 0.732 | 0.982 / 0.976 / 0.978 | 0.985 / 1.002 / 1.003 |
  | + axial | 0.685 | 0.794 | 0.911 / 0.924 / 0.912 | 0.937 / 0.996 / 0.962 |
  | + axial placebo (offsets swapped) | 0.674 | 1.038 | 0.876 / 0.909 / 0.899 | 0.958 / 0.991 / 0.894 |

- Reading: by eye at 3x (`outputs/a7cr-colour/crops-3x.png`, origins
  (1560,1640), (300,5400), (7700,400), (2330,3060), 128 px; columns
  uncorrected, lateral default, + axial) the axial arm removes most of the
  red glow on the dark side of edges. But the fine-detail signal falls 5-7 %
  against lateral alone, and B-G coherence gets worse. The placebo is
  clearly worse for blue (B-G 1.038), so the instrument sees the offsets.
  Its red fringe result (offset 2.1 instead of 5.5) is as good as the real
  one, though red's fine detail is lower (0.876 against 0.911), so red's
  fringe gain is not mainly from landing on red's own focus. ARGUED:
  red read 5.5 frames away from green carries that frame's registration
  error relative to green's frame (the highlight walk the prototype measured
  grows about 0.12 px per plane), which the global alignment cannot remove,
  and the refinement then measures a noisier red residual (0.607 px rms
  against 0.337 with lateral only). The prototype's per-channel gain came
  with its own per-channel fusion, not a frame offset under a near-argmax
  election.
- Cost: 119 s against 60 s (single-shot).
- Two bugs found while running it, fixed before any number above: a blocking
  once-cell in the neighbour cache deadlocked when a rayon worker stole the
  next frame's job; and neighbour decodes routed through the decode-ahead
  source waited forever because that source serves each planned frame once,
  in order (`PyramidFrameSource::decode_direct` now bypasses the plan).

### Commands

```sh
cargo build --locked --release -p strehl-cli
strehl stack <single-shot run> --demosaic --out lateral-single.tif
STREHL_PIXEL_SHIFT=member1 strehl stack <four-shot run> --demosaic --out lateral-member1.tif
STREHL_AXIAL_CA=on strehl stack ...        # and =placebo; --refine-ca=off for profile-only
python -X utf8 $E/lateral-profile.py outputs/a7cr-full-potential/s0/single.tif --permutations 2000
python -X utf8 $E/compare-colour.py OUT base=s0/single.tif,s0/member1.tif lateral=... axial=... placebo=...
python -X utf8 $E/colour-crops.py crops-3x.png 128 3 s0/single.tif,lateral-single.tif,axial-single.tif 1560,1640 300,5400 7700,400 2330,3060
```

Renders and logs are in ignored `outputs/a7cr-colour/` (placebo and
profile-only TIFFs deleted; logs kept).

## Axial colour investigation (2026-11-15)

Owner request: investigate why the axial correction was not a net win.
Same build base, same two runs of capture 3, 32 threads, CPU fold.

### Result

Three causes, each measured, each fixed; the corrected version is a small
real gain on this capture and costs nothing it used to cost.

| Arm (ratios to the uncorrected render, 93 tiles) | R-G fringe | B-G | Fine detail R / G / B | Mid band R | Residual red vs green, px |
| --- | --- | --- | --- | --- | --- |
| Lateral default | 0.740 | 0.732 | 0.982 / 0.976 / 0.978 | 1.018 | 0.247 |
| First version (all of red and blue, two frames interpolated) | 0.686 | 0.793 | 0.911 / 0.924 / 0.912 | 1.053 | 0.470 |
| `on` now (red only, coarse part, registered) | 0.673 | 0.731 | 0.981 / 0.973 / 0.976 | 1.021 | 0.232 |
| `unregistered` (control) | 0.697 | 0.731 | 0.981 / 0.971 / 0.975 | 1.023 | 0.304 |
| `placebo` (offsets reversed) | 0.916 | 0.733 | 0.986 / 0.978 / 0.976 | 0.960 | 0.285 |

Fine detail is the coherent signal in 0.25-0.40 cycles/px, mid band
0.10-0.25, both from [compare-colour.py](compare-colour.py); the residual is
[lateral-profile.py](lateral-profile.py)'s rms about its radial fit on the
single-shot render, sensor px. Against lateral alone the corrected version
has 9 % less red fringe and is unchanged elsewhere (fine detail within
0.3 %). The placebo is 24 % worse than lateral alone on red fringe and loses
6 % of red's mid band, so the effect follows the direction of the measured
offset. Render time 148 s single-shot and 123 s member 1 (lateral default 60
and 107; `unregistered` 118 and 102). Still off by default: one subject.

### Cause 1: frames several apart do not sit on each other (MEASURED)

`STREHL_AXIAL_DUMP` (new, inert unless set) writes each gathered frame's red,
green and blue planes; [axial-probe.py](axial-probe.py) and
[axial-probe-pairs.py](axial-probe-pairs.py) measure displacement between
them per 64-px tile (band sigma 1-3 plane px, the lateral-profile
instrument). 107 frames, `--refine-ca=off`, 1825 usable tiles, nearly all in
focus between frames 72 and 100.

- Green in frame k + j against green in frame k, all tiles within 8 frames of
  focus, sensor px rms: 0.177 at j = 1, 0.531 at j = 5
  ([axial-an-pairs.py](axial-an-pairs.py), 24 frame pairs, 26 635 tiles).
- A similarity fitted per pair leaves 0.083 and 0.334. The similarities the
  alignment left behind at j = 5: scale sd 43 ppm, rotation sd 69 urad,
  translation sd 0.17-0.22 px. An affine does no better (0.324).
- What remains at j = 5 is largely one spatial pattern: the mean over pairs
  is 0.291 px rms and holds 74 % of the variance (leave-one-out); pairs k and
  k + 1 correlate 0.96, k and k + 12 0.36.
- Red and blue move with green: red-to-red against green-to-green at j = 5
  slope 0.99, correlation 0.94; blue 0.95 and 0.96
  ([axial-an-offsets.py](axial-an-offsets.py)).
- So red read from 5 frames away lands 0.64 px rms from green about a radial
  model against 0.36 when read in-frame, and blue from 2 frames away 0.34
  against 0.20.

Is that fixed pattern the highlight walk (ARGUED earlier)? A walk pivots on
each colour's own focus, so the in-frame red-against-green residual would
carry minus 4.8/5 of the pattern (slope -0.96) and blue's -0.36; plain frame
misregistration predicts 0. Measured: red -0.448 +- 0.021, blue
-0.121 +- 0.013 ([axial-an-pivot.py](axial-an-pivot.py), bootstrap over
tiles). Neither: roughly 40 % of the fixed pattern behaves as a walk, the
rest as misregistration. The per-pair similarity is misregistration outright.

Fix: each borrowed frame is registered to the borrowing frame on green luma
(per-tile displacement pooled over 3x3 tiles, two passes, robust similarity,
well-determined departures kept) and read at the displaced position. A
planted shift of 0.4 px plus 400 ppm of scale is recovered within 0.03 px
(unit test). Predicted from the probe
([axial-an-reregister.py](axial-an-reregister.py), optimistic by
construction): red 0.638 -> 0.352, blue 0.335 -> 0.203. In the render: red
0.470 -> 0.279 with everything borrowed, 0.232 in the final version.

### Cause 2: a frame's finest red belongs to that frame's green (MEASURED effect, ARGUED mechanism)

Registration fixed the registration and fine detail got worse, not better:
0.873 / 0.908 / 0.875 against the first version's 0.911 / 0.924 / 0.912.
Signal and noise in that band fell together (signal-to-noise power 2.31
against 2.34 for lateral), so this is attenuation, not lost information.

- Not the two-frame interpolation: reading the one nearest frame gave 0.912 /
  0.924 / 0.912 unregistered and 0.873 / 0.909 / 0.875 registered, the same
  to the third decimal.
- Not weaker borrowed detail: the red plane at k + 5 has 1.12 / 1.13 / 1.06 /
  1.01 of its amplitude at k from the finest band to the coarsest
  ([axial-an-bands.py](axial-an-bands.py); green 0.90 throughout).
- Partly the second resampling: Lanczos-3 instead of Catmull-Rom gave 0.881 /
  0.913 / 0.884.
- ARGUED: the gather demosaics each frame before warping it, and the final
  demosaic reads red's finest detail as a correction to green. Above the red
  plane's Nyquist that detail is aliased at the borrowed frame's sampling
  phase and cannot agree with this frame's green, however well registered.

Fix: borrow only what a Gaussian passes and keep the rest of the frame's own
red. Registered, nearest frame, red and blue both:

| Split sigma, plane px | R-G fringe | B-G | Fine detail R / G / B |
| --- | --- | --- | --- |
| none | 0.639 | 0.762 | 0.873 / 0.909 / 0.875 |
| 0.75 | 0.655 | 0.734 | 0.967 / 0.964 / 0.965 |
| 1.0 (shipped) | 0.673 | 0.730 | 0.980 / 0.972 / 0.976 |
| 1.5 | 0.700 | 0.729 | 0.982 / 0.975 / 0.979 |
| 1.0, unregistered | 0.693 | 0.736 | 0.981 / 0.971 / 0.977 |

1.0 is the smallest value tried that leaves fine detail within 0.4 % of
lateral alone. It is a choice on one subject, not a fitted constant.

### Cause 3: blue has nothing to fetch (MEASURED)

Blue's band amplitude at its own focus is 1.018 of its amplitude at green's
(red 1.115), and with blue corrected B-G read 0.730 against 0.732 without.
A channel under 1.03 is now left alone, which is also why the final arm is
faster than the split arms (166 s). The threshold is a judgement between the
two values seen here, not tuned.

### What this says about the size of the prize

The stack oversamples focus about tenfold, so red 5.5 frames from its focus
has lost only 6-13 % of its plane amplitude, and most of that sits in the
band that cannot be borrowed. On this capture axial colour is worth a 9 %
cut in red fringing. A stack shot with a coarser focus step, or a lens with
more axial colour, has more to gain; neither has been measured.

### Limits and what would fool this

- One subject, specular, and both captures share it. The fringe figure counts
  any coherent R-G difference in 0.05-0.25 cycles/px, including a sharpness
  mismatch between channels, not only displacement.
- The displacement instrument reads short when the two bands differ in blur
  and cannot see motion along a one-dimensional texture; the probe compares
  arms at like blur and the registration pools 3x3 tiles for that reason.
- The alignment's inter-frame residual (0.18 px between neighbours) is a
  finding about the shipped alignment, not only about this feature. Not
  pursued here.
- The refinement instrument and `lateral-profile.py` still disagree about
  red's radial residual (+29 ppm against -145 ppm on the final render); the
  disagreement noted above stands.
- Author-run. No independent review yet.

### Commands

```sh
cargo build --locked --release -p strehl-cli
STREHL_AXIAL_DUMP=$O/planes strehl stack <single-shot run> --demosaic --refine-ca=off --out $O/dump-run.tif
python -X utf8 $E/axial-probe.py $O/planes $O/probe.npz
python -X utf8 $E/axial-probe-pairs.py $O/planes $O/pairs.npz
python -X utf8 $E/axial-an-offsets.py; python -X utf8 $E/axial-an-pairs.py
python -X utf8 $E/axial-an-pivot.py; python -X utf8 $E/axial-an-reregister.py; python -X utf8 $E/axial-an-bands.py
STREHL_AXIAL_CA=on strehl stack <single-shot run> --demosaic --out $O/final-on-single.tif   # also =unregistered, =placebo
STREHL_AXIAL_CA=on STREHL_PIXEL_SHIFT=member1 strehl stack <four-shot run> --demosaic --out $O/final-on-member1.tif
python -X utf8 $E/compare-colour.py $O/compare-final base=... lateral=... first=... on=... unreg=... placebo=...
python -X utf8 $E/lateral-profile.py $O/final-on-single.tif --permutations 20
cargo test --locked --release -p strehl-cli --lib axial_colour
```

`$O` is ignored `outputs/a7cr-axial-investigation/`. The interpolation,
kernel and split arms were rendered through temporary environment knobs
(`STREHL_AXIAL_PICK`, `STREHL_AXIAL_KERNEL`, `STREHL_AXIAL_SPLIT`) that are no
longer in the code; their renders and logs are kept there. Crops at 3x:
`$O/crops-3x.png`, columns lateral default, first version, `on`, `placebo`.

## Matte subject: scarab (2026-11-15)

Owner capture, the first request in `docs/captures-needed.md`: a white
scarab's scaled back (matte, no glints), same rig, nobody home, foam under
the tripod. Prepared and run by
[capture-scarab.py](capture-scarab.py); preparation record in ignored
`outputs/scarab-capture/prep.json`.

### Capture (MEASURED)

- Bounds 50300-51860, step 8, 196 planes, from two live-preview focus sweeps
  (the back's tiles peak between 50460 and 51660). ISO 100, f/5.6, 0.6 s:
  two single test RAWs at focus 51563 read green's brightest photosite at
  1572 (1/10 s) and 9661 (0.6 s) of 14848 DN headroom, ratio 6.1. In the run
  green's brightest photosite stayed under 10 000; nothing near white.
- Single-shot run `D:/StrehlCaptures/stack-1794785495615-11226`, 196 RAWs,
  21.6 min; four-shot run `stack-1794786793543-11226`, 784 RAWs, 53.6 min.
  The live checker passed 182 of 196 groups; 13 of the 14 flagged sit just
  over the 0.2-photosite witness tolerance (0.202-0.288), one shows local
  disagreement (plane 138). Coin: 19 of 107 flagged.
- Prototype alignment: span-1 tile residual 0.15 px (coin 0.20); rotation
  over the stack 0.38 mrad (coin 1.34). Lateral colour at own focus: red
  -599 ppm, blue +168 ppm; after the model 0.21 / 0.15 px (coin 0.35 /
  0.23). Red's focus 3.2 planes from green's, blue's 2.0. Diffraction cutoff
  from the selector's spectrum: N_eff 11.1-11.8 (coin 13.1; a different
  focus distance, so a different bellows factor).

### The baseline was biased (MEASURED)

`evaluate.py` and `compare-colour.py` scored the shipped stack (S0) from two
separate captures. Against odd/even half-stacks of one capture
(`STREHL_FRAME_PARITY`), that pairing keeps 0.67-0.74 of the shipped
stack's fine-detail signal on the scarab and 0.89-0.92 on the coin, and
reads 1.8-1.9x (scarab) and 2.8-3.2x (coin) its noise: captures nearly an
hour apart do not overlay at the finest scale, and the merge elects
differently in each. Every ratio to S0 in this file is therefore flattering
to the prototype, the coin's noise figures most. Below, S0 is the shipped
stack's own halves from the four-shot run.

### Shipped stack, what the four shots add (MEASURED)

Odd/even half-stacks, 222 in-focus tiles, `compare-colour.py`, ratios to the
single-shot run:

| Arm | Fine detail R / G / B | Noise in that band R / G / B | Fine-detail SNR power R / G / B |
| --- | --- | --- | --- |
| Single-shot run | 1 | 1 | 5.0 / 5.2 / 4.6 |
| Four-shot run, member 1 | 0.96 | 1.01 | 4.6 / 4.7 / 4.2 |
| Four-shot run, `STREHL_PIXEL_SHIFT=remosaic` | 1.00 / 1.01 / 0.99 | 0.86 / 0.79 / 0.87 | 6.7 / 8.5 / 6.0 |

Within one capture, measured colour gives 1.8x (green) and 1.4-1.5x (red,
blue) the fine-detail signal-to-noise of one shot, at the same signal. Its
coherent chroma reads 1.10x member 1's (measured colour, or residual
misregistration; not separated). By eye at 3x the three are hard to tell
apart: at N_eff 11 the lens, not the sampling, sets the sharpness.

### Prototype against the shipped four-shot stack (MEASURED)

`evaluate.py`, 628 tiles, S0 = shipped remosaic halves (third column: S0 =
shipped member-1 halves):

| Arm | Fine detail R / G / B | High-pass noise R / G / B | Fine detail vs member-1 S0 |
| --- | --- | --- | --- |
| Selector (`seloc`) | 1.60 / 1.58 / 1.48 | 1.32 / 1.00 / 1.63 | 1.66 / 1.67 / 1.53 |
| Blend, "clean" (`f2c`) | 1.53 / 1.45 / 1.32 | 0.62 / 0.43 / 0.77 | 1.59 / 1.52 / 1.36 |
| Restored, root domain, sigma 0.70 (`f5`) | 2.15 / 1.80 / 1.44 | 0.80 / 0.48 / 0.73 | 2.23 / 1.90 / 1.49 |
| Restored, linear, sigma 0.70 (`f5l`) | 2.14 / 1.80 / 1.44 | 0.80 / 0.48 / 0.73 | 2.23 / 1.90 / 1.49 |
| Crisp, root domain, sigma 0.60 (`f6`) | 2.75 / 2.32 / 1.84 | 1.09 / 0.67 / 0.96 | 2.87 / 2.45 / 1.90 |

- The prototype's selector alone reads 1.5-1.6x the shipped stack's fine
  detail, so most of the "clean" gain over the shipped stack is the shipped
  merge losing detail on this low-contrast texture, not the blend. Cause not
  established; the shipped merge's noise-gated averaging is the first
  suspect (ARGUED).
- Restoration at sigma 0.70 lifts fine detail by about 1.25-1.4 over the
  blend at modest noise; with no glints, the linear and root-domain filters
  agree to the third decimal, and at 1:1 neither rings
  (`outputs/scarab-fp/crops-100pct.png`, origins (4600,3000), (2300,2500),
  400 px; `crops-300pct.png`). Sigma 0.60 adds visible grain.
- Caveats as before: the restored arms' signal includes the filter's gain by
  construction, odd/even halves share fixed pattern, S0's halves each fold
  half the frames (their noise is at most that of the full stack's), and this
  is one subject. Author-run, not independently reviewed.

### Commands

```sh
python -X utf8 $E/capture-scarab.py --start 50300 --end 51860 --step 8 --shutter 393226
strehl stack <single> --demosaic --out outputs/scarab/single.tif   # also member1, remosaic
STREHL_FRAME_PARITY=odd|even [STREHL_PIXEL_SHIFT=member1|remosaic] strehl stack <run> --demosaic --refine-ca=off --out h-<arm>-<parity>.tif
python -X utf8 $E/compare-colour.py OUT single=h-single-odd,h-single-even member1=... remosaic=...
a7cr-export-members.exe <four-shot run> outputs/scarab-fp/cache4; pass0.py; align.py; fuse.py energy|depth; coherence.py W g 3200 2100 2048
fuse.py fuse W g arms.json   # selo (select), f2 (coherent, floor 0.3)
ca.py W f2 f2c --model-only; ca.py W selo seloc --model-only
restore.py W EVAL f2c f5 --ref-arm seloc --sigma-t 0.70 --root   # f6: 0.60 --root; f5l: 0.70
evaluate.py W <S0 dir: shipped halves as single.tif / member1.tif> EVAL f2c f5 f6 f5l seloc
```

## Merge diagnosis and depth-guided fusion (2026-11-15)

Owner request: fix the shipped merge's detail loss and port the prototype's
blending. Scarab single-shot run unless stated; scores from odd/even
half-stacks of one capture (`STREHL_FRAME_PARITY`), [compare-colour.py](compare-colour.py)
or [tile-signal.py](tile-signal.py) / [arm-summary.py](arm-summary.py),
ratios to the default merge's halves. Build `cbca976b7e96-dirty` plus this
work, `--release`, CPU fold, 32 threads.

### Where the shipped stack loses against the prototype (MEASURED)

| Test | Result |
| --- | --- |
| Prototype on the same demosaiced single shots (`m1selc`, `m1c`) against shipped member-1 halves | selector 1.26 / 1.43 / 1.50 fine detail at 1.20 / 1.16 / 1.37 noise; blend 1.05 / 1.26 / 1.26 at 0.47 / 0.48 / 0.55 |
| Shipped merge against its own best single frame per tile (41 frame pairs, frames 60-141; [tile-signal.py](tile-signal.py)) | 0.94-0.97 fine detail (best-of-41, biased up) or 0.98-1.01 (mean of the three around the best), at 0.67-0.69 of the noise: the merge loses nothing against the frames it is given |
| Prototype outputs through the shipped CFA round trip ([remosaic-mhc.py](remosaic-mhc.py)) | single shot 1.43 -> 1.32 green (3-8 %); four shots 1.67 -> 1.45 green, 1.66 -> 1.37 red (13-17 %): the shipped gather keeps one colour per site and re-demosaics, discarding most of the measured colour |
| `--resampler lanczos3` | fine detail and noise both x1.11: a linear gain, no information |
| `--cover crop` | unchanged (0.99-1.00) |
| `--pyramid-select hard-max` | detail x1.13, noise x1.85 |

So the default merge is not the main loss for single shots; the four-shot
loss is the CFA round trip (carry RGB through the merge: not yet done).

### Depth-guided fusion, `STREHL_FUSION=depth` (opt-in, MEASURED)

`crates/strehl-core/src/pyramid-depth-guide.rs` (weights; `BandMerge::set_guide`)
and `crates/strehl-cli/src/merge_cmd/depth-guide.rs` (measurement). One
gather of every frame measures per-band focus planes (8-plane-px cells) and,
from band products of frames 1-12 apart about each sampled tile's focus,
the coherent transfer width per band; each frame's weight is that Gaussian
transfer at its distance from the band's focus, matched filter
`sum(t L) / sum(t^2)` on the three finest levels and a weighted mean on
coarser ones.

| Arm (single-shot halves) | Fine detail R / G / B | Noise in band | SNR power G |
| --- | --- | --- | --- |
| Default merge | 1 | 1 | 5.2 |
| Coherent widths (7.1 / 11.6 / 16.4 frames), the mode as shipped | 0.80 / 0.78 / 0.80 | 0.54 / 0.53 / 0.54 | 11.2 |
| Widths x0.5 | 0.92 / 0.90 / 0.92 | 0.73 | 7.9 |
| Widths x0.3 | 1.06 / 1.03 / 1.06 | 0.85-0.88 | 7.6 |
| Widths x0.18 | 1.15 / 1.11 / 1.15 | 0.98-1.03 | 6.7 |

Bugs found and fixed before these numbers, each by a failing test or
measurement: (1) one depth map for every band; (2) the matched filter on
coarse levels and the base, which amplified bands that do not fade (a
synthetic test showed a 1.9 % brightness bias; the first real-data arms read
0.73 detail at 0.88 noise); (3) widths from the energy curve (10-17 frames),
which do not see that frames several apart do not add up coherently.

Reading: the mode dominates the default on signal-to-noise everywhere on
the curve; at its measured widths it trades 20 % of the finest detail for
half the noise, at x0.18 it adds 11-15 % detail at equal noise. The finest
detail evaluated here is above the half-resolution planes' bands and
decorrelates faster than the finest band the mode can measure; restoration
that knows the blend's transfer is the intended partner (prototype path).
At 1:1 (`outputs/scarab-merge/crops-coh-1x.png`, origins (4600,3000),
(2300,2500), 400 px; default left) the fusion is cleaner on the scale
surfaces, similar in apparent sharpness, with a faint purple rim at
bright-on-dark edges (red and blue take green's weights). Off by default.
Default renders unchanged: A7C II byte-freeze below.

### Commands

```sh
STREHL_FRAME_PARITY=odd|even [STREHL_FUSION=depth [STREHL_FUSION_WIDTH=s]] strehl stack <run> --demosaic --refine-ca=off --out h-<arm>-<parity>.tif
STREHL_FRAME_PARITY=K-K strehl stack <run> --demosaic --refine-ca=off --out one-K.tif   # single-frame arms
python -X utf8 $E/compare-colour.py OUT default=h-single-odd.tif,h-single-even.tif depth=...
python -X utf8 $E/tile-signal.py OUT.npz shipped=... fK=one-K.tif,one-K+1.tif ...
python -X utf8 $E/remosaic-mhc.py W/fused/m1selc-odd.npy OUT.npy; evaluate.py ... file:LABEL:A.npy:B.npy
cargo test --locked --release -p strehl-core --lib depth_guide; cargo test --locked --release -p strehl-cli --lib depth_guide
```

Renders in ignored `outputs/scarab-merge/`.

## Colour carry and optical restoration (2026-11-15)

Owner request: port the restoration and carry full colour through the merge.
Both are opt-in. Scarab runs as above, odd/even half-stacks of one capture
(`STREHL_FRAME_PARITY`), [compare-colour.py](compare-colour.py), 222
in-focus tiles. Build `cbca976b7e96-dirty` plus this work, `--release`, CPU
fold, 32 threads. Renders, logs and per-arm peak memory in ignored
`outputs/scarab-rgb/` (`batch.txt`).

### Colour carry, `STREHL_CARRY_RGB=on` (MEASURED)

`crates/strehl-cli/src/merge_cmd/colour-carry.rs`; the gather's
`CARRIED_SITES` in `align_cmd.rs`. The gather keeps each site's other two
channels (measured for a four-shot group, Malvar otherwise), the merge folds
12 planes on the unchanged green election, and the output is full-resolution
RGB with no second demosaic. Red and blue are then green plus their
difference from green smoothed at 1 px (`STREHL_CARRY_RGB=raw` skips that).

- Native-site channels are bit-identical to the plain `remosaic` render: 0 of
  60,217,344 samples differ (VERIFIED, full four-shot stack,
  [native-sites.py](native-sites.py)); 99.4 % of the carried channels
  differ. A first version used the carried plane count in the chunk planner,
  which changed the reduction order (0.15 % of native samples off by one
  code value); the planner now uses four planes.
- Four-shot halves, ratios to plain `remosaic`:

| Arm | Fine detail R / G / B | Noise R / G / B | SNR power R / G / B | Colour-edge coherence R-G / B-G |
| --- | --- | --- | --- | --- |
| `remosaic` | 1 | 1 | 6.6 / 8.3 / 5.9 | 1 |
| carry, raw | 1.03 / 1.14 / 0.95 | 1.09 / 0.92 / 1.22 | 5.8 / 12.8 / 3.5 | 1.21 / 1.21 |
| carry (chroma 1 px, the default) | 0.96 / 1.14 / 1.04 | 0.71 / 0.92 / 0.73 | 11.9 / 12.8 / 11.8 | 0.94 / 0.92 |
| carry, chroma 2 px (probe) | 1.09 / 1.14 / 1.14 | 0.78 / 0.92 / 0.77 | 12.8 / 12.8 / 12.8 | 0.62 / 0.60 |

  Raw carry recovers green's round-trip loss but makes red and blue worse:
  a carried sample carries its channel's full noise, where Malvar borrowed
  green's cleaner fine detail. Smoothing the colour difference keeps
  green's gain and doubles red's and blue's signal-to-noise; at 2 px the
  colour edges smear. The 1 px probe ([chroma-smooth.py](chroma-smooth.py))
  and the built-in step agree to the third decimal.
- Cost: 182 s against 121 s for the plain four-shot render, peak private
  memory 22.4 GB against 14.0 GB (61 MP).

### Optical restoration, `STREHL_OPTICAL_RESTORE=on` (MEASURED)

`crates/strehl-core/src/optical-restore.rs` (spectra, fits, filter, kernel)
and `crates/strehl-cli/src/merge_cmd/optical-restore.rs` (measurement and
application at the write). The prototype's `restore.py` (arm `f5`: sigma 0.70,
square-root domain), with what the product has to measure for itself:
halves from the fold (alternate folded frames in a second accumulator; their
sum is the full stack), a reference of the two folded frames at each tile's
focus (from the depth measurement, run for this when the fusion is off), and
in-focus tiles from the depth map.

What changed on the way, each forced by a measurement:

1. **Single shots cannot measure the lens.** At f/12 the green diffraction
   cutoff is about 0.61 cycles/px, above a single Bayer frame's 0.5 Nyquist;
   the demosaiced single-shot reference shows no roll-off (its corners hold
   demosaic structure at signal-to-noise up to 150,000) and the fit runs to
   its ceiling in all three channels. Restoration now refuses such a stack
   unless given cutoffs (`STREHL_OPTICAL_RESTORE_CUTOFF=r,g,b`, measured on a
   four-shot run of the same setup, and labelled as given in the log).
2. **One aperture for three channels.** Fitted per channel on four-shot data
   the cutoffs came out red 0.572 = green 0.572, blue 0.804; the planted-blur
   tests showed every per-channel tail estimator biased by unmodelled blur.
   Diffraction ties the channels by wavelength, so one parameter is fitted
   to all three: green 0.616, red 0.549, blue 0.709 on the full four-shot
   stack (0.612 and 0.636 on its halves), against the prototype's N_eff
   11.1-11.8 (green 0.60-0.63).
3. **The blend transfer only where the reference is reliable.** The raw ratio
   rose from 0.84-0.89 to 1.2-1.3 exactly where the reference's
   signal-to-noise fell through one (two adjacent frames do not overlay at
   the finest scale); a cubic through it put a narrow bump into the filter.
   Now fitted on bins with reference SNR at least 2, held, and made
   non-increasing.
4. **A windowed kernel.** Plain truncation spread ripple everywhere (16 % of
   the peak gain at radius 24); a Hann-windowed kernel of radius 32,
   pre-corrected three times, delivers 0.95-0.98 of the designed gain in
   0.25-0.40 cycles/px (printed per channel). The rest is under-restoration.
5. **Restore before chroma smoothing.** Smoothing first gave red and blue
   green's fine detail and spoiled the one-aperture fit (residual 0.0045
   against 0.0013).

Four-shot halves, ratios to plain `remosaic` (the last row: the single-shot
run's default, for scale):

| Arm | Fine detail R / G / B | Noise R / G / B | SNR power R / G / B |
| --- | --- | --- | --- |
| `remosaic` | 1 | 1 | 6.6 / 8.3 / 5.9 |
| carry | 0.96 / 1.14 / 1.04 | 0.71 / 0.92 / 0.73 | 11.9 / 12.8 / 11.8 |
| carry + restore | 1.14 / 1.34 / 1.19 | 0.83 / 1.06 / 0.82 | 12.3 / 13.4 / 12.5 |
| carry + fusion | 0.78 / 0.93 / 0.84 | 0.42 / 0.54 / 0.42 | 23.5 / 25.0 / 23.3 |
| carry + fusion + restore | 1.16 / 1.38 / 1.22 | 0.60 / 0.78 / 0.60 | 24.4 / 26.1 / 24.5 |
| single-shot default | 1.00 / 0.98 / 1.01 | 1.15 / 1.26 / 1.14 | 4.9 / 5.1 / 4.6 |

Single-shot halves (cutoffs given from the four-shot run), ratios to the
default merge:

| Arm | Fine detail R / G / B | Noise R / G / B | SNR power R / G / B |
| --- | --- | --- | --- |
| default | 1 | 1 | 5.0 / 5.2 / 4.6 |
| fusion | 0.80 / 0.78 / 0.80 | 0.54 / 0.53 / 0.54 | 11.2 / 11.2 / 10.0 |
| restore | 1.24 / 1.05 / 0.82 | 1.24 / 1.02 / 0.81 | 5.0 / 5.5 / 4.8 |
| fusion + restore | 1.23 / 1.06 / 0.82 | 0.82 / 0.70 / 0.55 | 11.3 / 11.8 / 10.3 |

Reading:

- With everything on, the four-shot stack has 1.16-1.38x the plain pixel-shift
  render's finest detail at 0.60-0.78x its noise: about 3-4x its fine-detail
  signal-to-noise power, and about 5x the single-shot default's.
- A linear filter cannot add signal-to-noise inside a narrow band, and does
  not here (restore alone: 11.9 -> 12.3 red). Restoration turns the fusion's
  signal-to-noise into visible detail; the fusion supplies it.
- On single shots blue comes out at 0.82: one target (sigma 0.70) for all
  channels sits below blue's own transfer at 0.3 cycles/px, so blue is
  softened toward the others.
- Caveats: the restored arms' detail includes the filter's gain by
  construction (the noise column is the cost); odd/even halves share fixed
  pattern; one subject; each restored half designs its own filter from its
  own halves of halves; author-run, not independently reviewed. Blur the
  model omits biases the fitted cutoff low and over-restores: planted
  spectra with 0.4-0.7 px extra blur read up to 0.15 cycles/px low.
- Memory: peak private 21-23 GB for the four-shot arms with carry (with or
  without restoration: a restoration fold runs as one chunk so no retained
  copy of either half-stack is held), 10 GB single-shot. An earlier version
  was stopped by the session for memory pressure; the single-chunk fold and
  reusing the gather's buffers for the carried planes fixed it.

### What the eye sees, and the fusion's glow (MEASURED)

Crops at 1:1 and 3x (`outputs/scarab-rgb/crops-1x.png`, origins (4600,3000)
and (2300,2500), 400 px, columns single-shot default / `remosaic` / carry /
carry + fusion + restore; `crops-3x.png`): the full combination is visibly
less grainy on the scale surfaces with the same outlines, and nothing rings.
At 4x on a bright scale against the dark gap (`crops-edge-4x.png`,
`crops-edge-coarse-4x.png`, origin (2560,2540)) every fusion arm shows a
soft, faintly purple glow into the gap that carry and carry + restore do not.

[halo.py](halo.py) measures it: mean value of dark pixels 3-12 px from bright
ones ("near") and 30+ px from anything bright ("far"), ratios to `remosaic`,
odd halves:

| Arm | Near R / G / B | Far R / G / B |
| --- | --- | --- |
| carry | 1.01 / 1.02 / 1.02 | 1.00 / 1.00 / 1.00 |
| carry + restore | 0.91 / 0.92 / 0.94 | 0.98 / 0.99 / 0.99 |
| carry + fusion | 1.09 / 1.10 / 1.10 | 1.11 / 1.11 / 1.12 |
| carry + fusion + restore | 1.00 / 1.04 / 1.02 | 1.09 / 1.10 / 1.10 |
| same, coarse levels by election (`STREHL_FUSION_COARSE=election`) | 0.94 / 0.99 / 0.96 | 1.09 / 1.11 / 1.10 |

The fusion lifts dark areas by about 10 %, near edges and far from them:
it averages defocused frames' light into shadows. Restoration tightens the
edge (near drops) but cannot remove a lift. Leaving the levels past the
third to the election trims the near-edge glow at 10 % of the fusion's
signal-to-noise (22.1 / 23.4 / 22.1 against 24.4 / 26.1 / 24.5) and leaves
the far lift; it stays an experiment knob. This lift, with one subject and
no independent review, is why the fusion stays off by default.

### Checks (VERIFIED unless stated)

- A7C II byte-freeze 5/5 (default renders unchanged); `strehl-core` 786 lib
  tests pass, including the 7 new restoration tests; the colour-carry and
  depth-guide CLI tests pass.
- `strehl-cli` lib: 246 pass, 8 fail, all research controls that demand a
  pinned environment (`STREHL_GREEN_PROBE_OUTPUT`, `STREHL_DEFECT=off`,
  `STREHL_FIX_CA=off`, ...) before touching any code changed here.
- Clippy: no findings in the new modules or the lines added to shared files
  (the crates' older findings remain). rustfmt clean on new files and on the
  added hunks of shared files.
- `scripts/check-defaults.py` declares every new switch; it still exits 1 on
  the existing `STREHL_RESTORE` row and 76 switches undeclared before this
  work (including `STREHL_FRAME_PARITY`, present at HEAD).

### Commands

```sh
S=D:/StrehlCaptures/stack-1794785495615-11226; F=D:/StrehlCaptures/stack-1794786793543-11226
pwsh -File outputs/peak-run.ps1 LOG "STREHL_FRAME_PARITY=odd|even;STREHL_PIXEL_SHIFT=remosaic;STREHL_CARRY_RGB=on[;STREHL_FUSION=depth][;STREHL_OPTICAL_RESTORE=on]" stack $F --demosaic --refine-ca=off --out h-<arm>-<parity>.tif
... "STREHL_FRAME_PARITY=odd|even;STREHL_OPTICAL_RESTORE=on;STREHL_OPTICAL_RESTORE_CUTOFF=0.549,0.616,0.709[;STREHL_FUSION=depth]" stack $S ...
python -X utf8 $E/native-sites.py carry.tif remosaic.tif
python -X utf8 $E/chroma-smooth.py 1.0 cs1.0 h-f-carry-odd.tif h-f-carry-even.tif   # raw-carry halves
python -X utf8 $E/compare-colour.py OUT remosaic=... carry=... carry-restore=... carry-fusion=... carry-fusion-restore=... single=...
python -X utf8 $E/colour-crops.py crops-edge-4x.png 110 4 A.tif,B.tif,... 2560,2540
python -X utf8 $E/halo.py h-f-remosaic-odd.tif h-f-carry-odd.tif ...
cargo test --locked --release -p strehl-cli --test byte-freeze
cargo test --locked --release -p strehl-core --lib optical_restore; cargo test --locked --release -p strehl-cli --lib colour_carry
```

## Group rescue: compensating member motion (2026-11-16)

The shipped four-shot gate demoted a group to its member 1 when its green
witness pairs disagreed by 0.2 photosite or more. On the scarab four-shot run
that demoted 13 groups at 0.20-0.29 photosite, plus one (frame 137) whose
witness tiles disagree locally.

### The residuals are real member motion (MEASURED)

Each member's registration against member 1 (`pixel_shift::register`, block
luma, central half of the frame) already carries a sub-photosite residual.
The difference of two members' residuals predicts their witness pair shift,
measured independently on unresampled green: correlation 0.91 / 0.98 / 0.94
/ 0.98 and slope 0.86 / 1.00 / 0.97 / 0.97 per component over all 196 groups
(`outputs/scarab/pixel-shift.json`). Many passing groups sit at 0.15-0.19:
the members drift by a few tenths of a photosite over a group's ~35 s.

### Compensation, `STREHL_PIXEL_SHIFT_RESIDUAL` (default `compensate`)

`pixel_shift::compensate_rows` corrects each assembled sample to first order,
`v + r_k . grad C` (the assembled channel's own central-difference gradient;
green takes its two members' mean residual), and the gate judges the witness
shift minus the residuals' prediction. A planted test: compensation cuts the
assembly error 3.7x (30 -> 8, the rest second order), the reversed sign makes
it worse. `off` restores the old assembly and gate; `negate` is the placebo.

Four-shot halves with `STREHL_CARRY_RGB=on`, ratios to the gated carry arm:

| Arm | Demoted (odd half) | Fine detail R / G / B | Noise R / G / B | SNR power R / G / B |
| --- | --- | --- | --- | --- |
| gate on raw witness (`off`) | 5 | 1 | 1 | 12.1 / 12.9 / 11.9 |
| every group assembled, uncompensated (`remosaic-ungated`) | 0 | 1.02 / 1.02 / 1.02 | 0.84 / 0.85 / 0.84 | 17.6 / 18.4 / 17.6 |
| `compensate` | 1 (frame 137) | 1.02 / 1.02 / 1.02 | 0.85 / 0.86 / 0.84 | 17.3 / 18.2 / 17.4 |
| `negate` (placebo) | 1 | 1.02 / 1.02 / 1.01 | 0.89 / 0.90 / 0.88 | 15.6 / 16.5 / 15.7 |

Reading:

- Rescuing the groups is the gain: 1.43x fine-detail signal-to-noise power.
  The demoted groups cluster where much of the subject is in focus, so four
  times the photons there shows up across the in-focus tiles.
- The compensation itself is measurably neutral here: uncompensated assembly
  of the same groups reads the same, so at N_eff ~12 a 0.1-0.3 photosite
  member residual costs nothing the metric sees; doubled (the placebo) it
  costs 10 %. It is kept because it keeps the gate meaningful where the
  lens is sharper and still refuses local motion (frame 137), which the
  ungated arm assembles. Cost: 9 % of fold time (95 s against 87 s per half).
- An unset render is byte-identical to explicit `compensate` (VERIFIED, odd
  half); A7C II byte-freeze 5/5. The live checker (`strehl follow`) uses the
  same gate, so it no longer asks for retakes of groups the stack accepts.
- Against plain pixel shift as first measured (`remosaic`, raw gate, no
  carry: 6.6 / 8.3 / 5.9), carry plus rescue reads 17.3 / 18.2 / 17.4.
  Caveats as before: one subject, odd/even halves share fixed pattern,
  author-run.

### Commands

```sh
# residual prediction vs witness: per group, r[b] - r[a] (residual_px) against
# witness_pair_shift_px for each pair in witness_pairs, outputs/scarab/pixel-shift.json
STREHL_FRAME_PARITY=odd|even STREHL_PIXEL_SHIFT=remosaic|remosaic-ungated STREHL_CARRY_RGB=on [STREHL_PIXEL_SHIFT_RESIDUAL=off|compensate|negate] strehl stack $F --demosaic --refine-ca=off --out h-f-carry-<arm>-<parity>.tif
python -X utf8 $E/compare-colour.py OUT carry=... ungated=... comp=... neg=...
cargo test --locked --release -p strehl-core --lib pixel_shift
```

## Defaults for pixel-shift stacks (2026-11-16)

Owner decision: colour carry and optical restoration on by default for
four-shot stacks, to be measured on a second subject later. Single-shot
renders are unaffected (restoration cannot measure a single-shot stack, and
the carry was not measured there).

- `STREHL_CARRY_RGB` and `STREHL_OPTICAL_RESTORE`, unset, switch on when
  `STREHL_PIXEL_SHIFT=remosaic` (or `remosaic-ungated`) assembles groups;
  restoration only with the carry active. `off` disables either.
- Defaulted, an unsupported combination (no `--demosaic`, axial colour, region
  repair, `STREHL_RESTORE`, temporal energy, a requested GPU fold) leaves the
  feature off with a log line; a restoration that cannot measure (a depth
  measurement that fails, a half-stack with no frames, too few in-focus tiles)
  writes the unrestored image with a warning. Explicitly on, all of these stay
  errors.
- VERIFIED: a pixel-shift render with nothing set is byte-identical to one with
  both switches on (scarab four-shot, odd half); a single-shot render is
  byte-identical to the build before the change; A7C II byte-freeze 5/5. Both
  fallbacks complete and write an image: one folded frame (an empty half-stack;
  this first panicked, "cannot finish a merge with no frames", and is fixed)
  and two frames outside the focus range (no in-focus tiles).
- Cost of a four-shot render with the defaults: peak private memory about 22 GB
  against 14 GB, and an extra gather of every frame for the depth measurement
  (about 2 minutes on this 196-group run).
