# Multi-frame super-resolution from focus breathing: experiment and decision

Status: **rejected for integration** (2026-11-01). Owner request: try
super-resolution as an experiment, integrate only if it is proven better.
Allocation: `super-resolution-2026-11-01` in the milestone ledger.

## Question

Can the original CFA samples of the frames that are in focus at a point,
offset from one another by focus breathing, be reconstructed jointly into more
real detail (dealiased colour, finer luminance) than the engine's per-frame
demosaic, pull and merge?

## Inputs and environment

- bug-4 (`D:/personal/macro/insects/bug-4`, read-only), pass 102 (global frames
  279..577), geometry from `outputs/multi-stack/bug4-01/out-auto-11/alignment.json`
  (warp-map bits parsed exactly; engine convention: placement pulls reference
  plane coordinates about `(gw/2, gh/2)`, sensor = 2 x plane). Sony A7C II
  (5.12 um), FE 100 mm GM + 2x TC, f/5.6 nominal, ISO 100. RGGB at the active
  origin; black 512; camera WB.
- CA: the engine's applied radial form (`A7C2_FE100GM_2XTC_X4CPL_RADIAL`,
  eps_r -508.4 ppm, eps_b +174.4 ppm, no translation). An early run that
  wrongly added the recorded translation produced colour fringes and lattice
  artifacts; it was stopped and discarded.
- Python 3.12, numpy 2.4.4, scipy 1.17.1, rawpy 0.27.0 (independent of the
  engine decoder). 24 decode workers; solves single-process. Concurrent host
  load: none of this lane's other jobs.
- Five ROIs of 192 sensor px (reference sensor coordinates): 1068,1364 (head,
  radius ~2500 px), 3308,2164 (centre), 5148,3284, 3548,3684, 2588,884.
  Measured breathing phase spread across each focus window (<= 9 frames):
  1.50/0.39, 0.31/0.35, 1.28/0.38, 0.16/0.70, 0.28/1.07 sensor px (x/y). The
  diversity is essentially one-dimensional (radial) and vanishes at the centre.

## Arms

- **A** engine emulation: per-frame Malvar-He-Cutler demosaic, Catmull-Rom
  pull, mean.
- **B** per-channel joint least squares: a full-resolution grid whose
  Catmull-Rom interpolation matches every original sample of that channel
  (Laplacian ridge).
- **Bp** placebo: B with every sample snapped to its nearest same-colour site
  of the reference lattice (sub-pixel phase destroyed, density kept).
- **C** joint correction of A: per-channel corrections fitted to all original
  samples, strong gradient penalty on the chroma corrections (R-G, B-G), small
  curvature on green, tiny ridge toward A. Parameters (0.02, 0.5, 0.001).
- **D / Dfused** C applied on top of a sharp base (the engine output, or a
  per-pixel sharpness-weighted fusion of the pulled frames), with every sample
  weighted by its frame's local sharpness ((F/F_max)^4, zero below 0.25).

## Instrument commissioning (MEASURED, `synthetic.py`)

Held-out raw-sample prediction (predict a left-out frame's own CFA samples,
with a cross-validated 25-tap linear filter offered to each arm) was the
planned real-data metric. The synthetic known-answer test **falsified it as a
discriminator**: the held-out frame's sites lie on the same lattice lines as
the training frames, so errors in the direction without phase diversity are
invisible. At 1.5 px spread, B beat A on held-out error (fitted 26.6 vs 57.5
x noise) while its truth error was worse (65,910 vs 58,471). At zero spread the
held-out score rewards whichever arm interpolates least. Held-out results are
therefore reported only as supporting evidence, never as proof.

Truth-scored synthetic results (band-limited random scene, mean of 7 folds):

| Condition | A truth MSE | B | Bp | C |
| --- | --- | --- | --- | --- |
| 1.5 px spread, no optics | 58,471 | 65,910 | 143,196 | 29,410 |
| 0 px spread, no optics | 71,751 | 153,137 | 157,991 | 71,271 |
| 1.5 px, f/16.8 diffraction MTF | 1,602 | 767 | 7,047 | 1,092 |
| 1.5 px, f/16.8, defocus 0.7 px at window edge, reg. error 0.15 px | 2,629 | 3,627 | 9,423 | 2,131 |
| 0 px, same | 3,147 | 7,773 | 7,775 | 3,141 |
| 3 px, 9 frames, same | 2,177 | 2,101 | 11,359 | 1,570 |

C never loses to A and gains 19-28% MSE in the realistic rows; B is unsafe
(loses badly without diversity); the placebo removes the gain, as it must.

## Real texture, real geometry (MEASURED, `realscene.py`)

Scene: a region of the bug-4 linear master (master pixel 1000,1300); frames
sampled at the actual pass placements with calibrated noise.

| Window (geometry) | Defocus/frame, reg. error | A r/g/b | C r/g/b |
| --- | --- | --- | --- |
| 414..422 (pass 102) | 0.25 px, 0.1 px | 1445 / 679 / 1220 | 1153 / 730 / 1078 |
| 135..143 (pass 100, 3x breathing) | 0.25 px, 0.1 px | 979 / 768 / 1118 | 856 / 797 / 1010 |
| 135..143 | 0.05 px, 0.05 px | 913 / 340 / 631 | 484 / 185 / 436 |

With equally sharp frames and accurate registration the gain is large (about
half the error); with the defocus that necessarily separates the frames
providing the phase diversity it is ~10-20% on red/blue and slightly negative
on green. Crops of truth/A/B/C at this setting are visually indistinguishable.

## Real captures

- Held-out (fixed CA, `holdout2-bug4-102.json`): B and C predict held-out raw
  samples 2-4x better than A in every ROI, Bp does not. Because of the
  commissioning failure above this is not taken as proof of detail.
- Native crops, one display transform (`outputs/sr-exp-01/v-all.png`): C is
  crisper than the plain average A, but A is not the engine.
- Against the engine: pass 102 rendered alone by the real CLI
  (`outputs/sr-exp-01/run-engine-102/`, 131 s, exit 0; images deleted after
  inspection for disk). With D, fused and Dfused built from identical frames
  and weights (`outputs/sr-exp-01/e102-all.png`): Dfused is visually the same as
  the sharpness-weighted fusion; D is marginally crisper but shows a faint
  lattice texture in flat dark regions. Nearly all the visible difference from
  the plain average comes from per-pixel focus selection, which the engine
  already does, not from sub-pixel reconstruction. (The engine crop's lifted
  blacks are not interpreted: the single-pass render has its own gauge, matched
  to these ROIs only to NCC 0.82-0.92, and a least-squares colour map over
  misregistered pixels compresses contrast.)

## Decision

DERIVED from the above: focus-breathing super-resolution has a real but small,
spatially limited benefit on these captures (one-dimensional diversity, none at
the centre, eroded by the defocus between the frames that supply it). It does
not produce a visible improvement over sharpness-selected fusion, and it adds a
lattice-texture risk. It is not integrated and the merge is unchanged.

What would change this: captures with two-dimensional sub-pixel diversity at
equal focus (rail or handheld repeats at each focus step, sensor-shift
multi-shot), where the synthetic rows show ~50% error reduction. The C
estimator (correction of a base with chroma-smooth prior, sharpness-weighted
data) is the arm to revisit; B must not be used.

## Reproduce

```text
python experiments/super-resolution-2026-11-01/synthetic.py --spread 1.5 --optics 16.8 --defocus 0.7 --reg-noise 0.15 --c 0.02,0.5,0.001
python experiments/super-resolution-2026-11-01/realscene.py --master outputs/multi-stack/bug4-01/out-auto-11/master.tiff --alignment outputs/multi-stack/bug4-01/out-auto-11/alignment.json --window 414,422 --roi 1068,1364,192 --texture 1000,1300
python experiments/super-resolution-2026-11-01/holdout.py --alignment outputs/multi-stack/bug4-01/out-auto-11/alignment.json --pass-range 279,577 --roi 1068,1364,192 --roi 3308,2164,192 --roi 5148,3284,192 --roi 3548,3684,192 --roi 2588,884,192 --variants 1:0.02:0.5:0.001 0:0.02:0.5:0.001 --out outputs/sr-exp-01/holdout2-bug4-102.json
python experiments/super-resolution-2026-11-01/engine-refine.py --alignment outputs/multi-stack/bug4-01/out-auto-11/alignment.json --master outputs/sr-exp-01/engine-102/master.tiff --crop auto --pass-range 279,577 --roi 1068,1364,192 --ca 0 --out outputs/sr-exp-01/e102-1068,1364,192
```
