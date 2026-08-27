# V-EYES: adversarial visual inspection of the DELIVER-V4 gallery

Status: complete. Agent: V-EYES. Subject: `C:\dev\strehl-out\DELIVER-V4\` (26
full-resolution JPEGs, 78 1:1 crops) and the masters behind them in
`C:\dev\strehl-out\acceptance\SHIP-V4\`.

I edited nothing under `crates/`. This report and `experiments/V-EYES/` are the
only files I wrote. `D:\personal\macro\` was read only; scratch went to
`C:\dev\strehl-out\V-EYES\`.

The brief asked me to assume the output is flawed and go find the flaw, and said
a "looks great" report is a failed report. I found three real defects, refuted
two hypotheses I had formed myself, and refuted the owner's stated complaint as
a property of the *current* file. The most consequential thing I found is that
the instrument I was told to use — my own eyes, through the `view` tool — is
itself a resampler above 400 px, which is the same class of error that produced
the complaint in the first place.

## 0. Bottom line

**Yes, I would hang these on a wall — but not before turning on the dust
correction, which is off by default and has shipped visible dirt into 18 of the
26 delivered images, at up to −13.3% local contrast on clean backgrounds.**

**The "cut-out sticker" halo the owner complained about is not in the
full-resolution file. It is manufactured by the 5× downscale that produced the
gallery he judged.** In 7 of 10 subjects a 5× Lanczos reduction increases edge
overshoot, and in two subjects it flips a *negative* overshoot into a strongly
positive bright rim. The delivery defect was worse than "it softened things": it
synthesised the exact artifact that was complained about.

The one change that would most improve these: **enable the static-defect
correction by default.** It is a one-flag change, it removes the only defect I
found that is unambiguously dirt rather than physics, and it is the defect a
print viewer's eye finds first because it sits on smooth empty background where
nothing else competes for attention.

## 1. Commission the viewer before trusting anything seen through it

This audit exists because a verdict was returned on a gallery that had been
resampled to 19.9% of master width. If the path from file to my eye also
resamples, I reproduce the error exactly and report softness that is not in the
file. So I measured it first, with `experiments/V-EYES/viewer_target.py`: a
target of black/white features at known sizes in file pixels — checkerboards at
1/2/3/4/8 px cell, line gratings at 1/2/3 px period, and a slanted edge.

| target size | 1 px horizontal grating | 1–2 px checkerboards | verdict |
| --- | --- | --- | --- |
| 1000 px | collapsed to a flat wash | coarse large-scale moiré | resampled |
| 600 px | collapsed to a flat wash | moiré present | resampled |
| 400 px | resolved as distinct lines | clean, reads as 50% stipple | 1:1 |

A 1 px checkerboard *correctly* reads as near-uniform grey at 1:1, so that patch
alone proves nothing. The discriminator is moiré and the collapse of the 1 px
grating: both are signatures of a resampler, and both are present at 600 px and
absent at 400 px.

**Consequence, and it applies to more than me.** The delivered crops are
1000 × 1000. Any inspection of them through this tool — including the
"1:1 inspection" the brief reports as saying the output is good — is looking
through a 2.5× reduction that destroys 1–2 px detail and adds moiré. My own
first-pass verdicts on four crops, formed before I ran this test, called the
output "mush"; those verdicts were inadmissible and I discarded them. Every tile
below is cut at 400 px and never resized (`experiments/V-EYES/tile.py`).

## 2. What the delivery claims that is true

The README says the crops are "cut straight out of the master with no resizing,
no sharpening and no grading". I tested it rather than accepting it, by locating
each crop inside its master by normalised cross-correlation and then refining to
the exact integer offset (`experiments/V-EYES/locate_crops.py`):

```
crop                                              x      y  residDN    peak
flower-bud-alone-cpl--1                        3000   1000     0.71  1.0000
flower-bud-alone-cpl--2                        3000   2500     0.66  0.9999
flower-bud-alone-cpl--3                        4000   2000     0.67  1.0000
```

Exact integer offsets, at round coordinates, with a mean absolute residual under
0.71 DN — that is JPEG quantisation noise and nothing else. **The crop claim is
honest.** The crops are genuine 1:1 cuts.

## 3. Defect 1 — the dust motes shipped, in 18 of 26 images

This is the one defect I found that is unambiguously not physics. Two sensor or
optic blemishes are documented at CFA coordinates (3202,121) and (3434,2305),
at −3.6% and −8.2%. Correction exists in the tool and **ships off by default**.
A mote cannot be averaged out by stacking, because it does not move relative to
the sensor while the subject does.

Master coordinates are twice CFA coordinates. I did not assume the position:
each subject gets its own `coverage` rescale of the field (0.84 to 1.00 across
the corpus), so a sensor-fixed blemish lands on a different output pixel in each
subject. `experiments/V-EYES/mote_census.py` searches a ±170 px neighbourhood
and only reports where the surrounding annulus is smooth, because on busy
texture the statistic is meaningless and would invent motes.

Commissioned in both directions on the same image before use:

```
COMMISSIONING on 109MSDCF.jpg
  smooth patch at (600,1400)
  CLEAN  arm: reads +0.08%  PASS (must be near 0)
  DEFECT arm: planted -6.00%, reads -5.93%  PASS
```

Worst cases from the census over all 26 delivered JPEGs:

| subject | mote1 depth | at | mote2 depth | at |
| --- | --- | --- | --- | --- |
| highly-angled-ruler-mm-cpl | −4.32% | (6404,232) | **−13.28%** | (7008,4450) |
| 109MSDCF | −4.25% | (6444,212) | **−10.73%** | (6908,4640) |
| couch-fibers-cpl | −0.37% | (6474,252) | −8.33% | (6708,4620) |
| pencil-steep-angle-cpl | **−9.90%** | (6494,172) | −7.37% | (6968,4660) |
| tweezers-cpl | −1.55% | (6554,162) | −7.23% | (6928,4650) |
| coffee-bean | −2.27% | (6544,132) | −6.54% | (6918,4640) |
| flowers-cpl | −5.75% | (6544,412) | −3.91% | (6938,4660) |

**Detected below −1.5%: mote1 in 11/26, mote2 in 18/26.** Subjects with no
smooth background at that spot cannot show it, so these are floors, not counts
of affected images. The detected positions cluster tightly around the nominal
coordinates with exactly the per-subject scatter the coverage rescale predicts —
that recurrence across subjects with completely different content is what makes
this a sensor-fixed defect rather than debris in the scene.

**What I SAW.** In `flower-bud-alone-cpl` at master ≈(6404,232) the delivered,
unstretched rendition shows a soft grey disc roughly 45 px across on a near-white
background — subtle on screen, but at 300 DPI that is a 3.8 mm blob on empty
white, which is precisely what the eye locks onto in a print. A second fainter
disc sits at ≈(6500,240). Under a 2–98 percentile stretch both are unmistakable.

In `109MSDCF` the object at the same location is *not* a round mote but an
elongated diagonal streak roughly 85 px long, at master ≈(6882–6942, 4603–4663),
with **clear red/cyan chroma fringing at its two ends**. Different capture
session, different dirt. The fringing is a lateral-CA residual — CA correction is
on by default per the provenance, so this is what it leaves behind.

**Attribution: stacking pipeline, not capture.** The dirt is in the capture, but
shipping it is a default-configuration choice, and the tool already has the
correction.

## 4. Defect 2 — the halo is made by the downscale, not by the merge

The owner's specific complaint was a bright rim following the subject silhouette.
I could not find one at 1:1 in any subject I inspected (section 6). That left the
question of what he actually saw, and there is an obvious candidate: Lanczos and
bicubic kernels have negative lobes, so they overshoot at a step edge *by
construction*. Reducing 5× with such a kernel puts a bright rim on a
dark-to-light boundary that has none in the source.

`experiments/V-EYES/halo_profile.py` measures edge-normal overshoot in DN — the
maximum 1–6 px onto the bright side, minus the bright plateau taken as the median
12–20 px out — on the same edges twice: in the full-resolution delivered JPEG,
and in a 5× Lanczos reduction of it. Commissioned three ways on one tile:

```
COMMISSIONING on bee-1-cpl.jpg tile (2500,1500) 2000x2000
  CLEAN   mean overshoot  +44.97 DN  p95 +120.13  (71 edges)
  DEFECT  unsharp         +60.47 DN  p95 +176.26   PASS (must exceed clean)
  IMPROVE blur           +40.32 DN  p95 +109.61   PASS (must fall below clean)
```

| subject | full-res mean | 5× Lanczos mean | change |
| --- | --- | --- | --- |
| lead-1-cpl | **−2.85** | **+33.21** | sign flip, +36.1 |
| 109MSDCF | **−12.16** | **+10.26** | sign flip, +22.4 |
| tweezers-cpl | +18.60 | +36.77 | doubled |
| lavendar-cpl | +7.97 | +21.80 | tripled |
| pencil-steep-angle-cpl | +6.06 | +12.32 | doubled |
| bee-2-cpl | +0.32 | +1.54 | +1.2 |
| dry-erase-marker-head-cpl | +3.38 | +4.21 | same |
| bee-1-cpl | +14.76 | +8.09 | fell |
| flower-bud-alone-cpl | −12.69 | −6.29 | rose, still negative |
| wrapped-text-1 | −7.11 | −4.24 | rose, still negative |

**In 7 of 10 subjects the reduction increases overshoot, and in `lead-1-cpl` and
`109MSDCF` it converts a clean edge into a bright rim of +33 and +10 DN.** That
is the cut-out-sticker look, and the delivery made it.

Two honest limits on this. The absolute values are not trustworthy on hairy
subjects — the "bright plateau" logic is confounded when the bright side is full
of hairs, which is why the `bee-1-cpl` commissioning tile reads +44.97 DN as
"clean". Only the full-versus-5× comparison on identical content is valid, and
that is the comparison the claim rests on. And `bee-1-cpl` falling is unexplained;
I did not chase it.

**Attribution: delivery, now fixed.** This exonerates the merge on the owner's
stated complaint. It also means the re-render was the right call for a reason
beyond softness.

## 5. Defect 3 — softness is real but modest, and my measurement is confounded

I formed the hypothesis that the masters are secretly half-resolution. The
provenance supports it on its face: `planes : 3516 x 2344 per CFA plane`, one
focus decision per 2×2 quad, `Interpolated -- do not measure resolution on it`,
plus a per-subject `coverage` upsample of up to 1.19×. **I tested it and it is
false**, which is the most useful thing I did for the requester's peace of mind.

`experiments/V-EYES/hf_octave.py` measures the fraction of spectral power in the
top octave, 0.5–1.0 Nyquist, against a planted defect (2× down, 2× up — an exact
model of "decided at half pitch then interpolated") and a planted improvement
(unsharp mask).

```
flower-bud-alone-cpl--SHIP-V4.tiff  tile (3400,900) 1024x1024  green channel
  master as delivered                          HF(0.5-1.0 Nyq) =   0.007%
  master -> 2x down -> 2x up (half-pitch model) HF(0.5-1.0 Nyq) =   0.001%
  master + unsharp mask (amount 1.0, sigma 1.2) HF(0.5-1.0 Nyq) =   0.027%
  defect arm  PASS: 0.001% < 0.007%
  improve arm PASS: 0.027% > 0.007%
  master / half-pitch-model ratio = 5.463
  DSC00091.ARW (rawpy demosaic, full res)      HF(0.5-1.0 Nyq) =   0.011%
  DSC00101.ARW (rawpy demosaic, full res)      HF(0.5-1.0 Nyq) =   0.010%
  DSC00141.ARW (rawpy demosaic, full res)      HF(0.5-1.0 Nyq) =   0.009%
```

**The master carries 5.5× more top-octave energy than a 2× upsample would. It is
not a disguised half-resolution image.** The same test at tile (3000,1000) gave
ratio 4.96 with both arms passing. The nominal 33 MP is not a lie.

But the master sits *below* the sharpest single frames of the same region:
0.007% against 0.009–0.011%, a deficit of 35–55% in the top octave. The frames
were chosen by a focus ranking that behaves properly — a clean unimodal sweep
with a 17.70× ratio between sharpest (DSC00091) and softest (DSC00001), which is
what a focus bracket should look like.

**What I SAW**, at 400 px 1:1 on `flower-bud-alone-cpl`, the control subject —
coverage 1.00, held-out error 0.35 px, the best-aligned stack in the corpus, so
neither upsample nor misregistration can be blamed. Master tile at (3600,1050):
the trichomes at the bud edge are soft and blended, thick-edged, with a waxy
quality. The sharpest source frame at the same region shows the same hairs as
**thin, dark, cleanly separated filaments**. The difference is visible.

**Three confounds I could not remove, and they matter.**

1. `docs/research/V-softness.md` records a standing project rule that quality is
   never judged on an `--srgb` render, because the transfer curve moves every
   ratio a metric computes, and that results have been retracted for exactly
   this. The SHIP-V4 masters are `--srgb`. Both sides of my comparison are
   gamma-encoded, but the master carries `--auto-exposure` gain and the frames do
   not, so the two sit at different points on the curve. **This measurement
   violates that rule and should be repeated on `--linear-srgb` before anyone
   acts on the magnitude.**
2. rawpy's demosaicer is not the tool's Malvar-He-Cutler. A 35–55% gap between
   two different reconstructions is within the range a demosaicer difference can
   produce on its own.
3. The visual comparison had a brightness and a registration offset between the
   two tiles that I did not correct.

So: **softness is real to my eye and directionally confirmed by a commissioned
metric, but the magnitude is not established.** I record it as suspected, not
proven. It is independently corroborated by `docs/research/V-softness.md`, which
bisects a library-wide sharpness regression to `57e4554` and gives the mechanism
— the focus-election window growing 3.6×–4.0× — and that is a far better-founded
account than mine. I did not verify whether that revert had landed in SHIP-V4.

**Attribution: merge, probably.** Not upsample, not misregistration — those are
excluded by the control subject.

## 6. What I looked for and did not find

Negative results, each from tiles I actually viewed at 400 px 1:1, never resized.

| defect sought | where I looked | result |
| --- | --- | --- |
| bright/dark rim at silhouettes | 8 subjects, 16 edge tiles chosen for edge strength AND tonal range | **not found at 1:1** |
| ghosting, doubled edges | `pencil-steep-angle-cpl` (2568,2432) — worst held-out error in corpus, 68.2 px | **not found**; graphite/wood boundary is clean |
| banding, posterisation | `bee-2-cpl` (800,3600) and `109MSDCF` (1200,800) backgrounds under 1–99 stretch | **not found**; smooth noise, no steps |
| zippering, blotchy frame switching | all tiles above | **not found** |
| chroma fringing | high-contrast edges | found only on the `109MSDCF` debris streak; a CA residual, not general |

The edge tiles were selected by `experiments/V-EYES/edge_tiles.py`, which ranks
by gradient strength times tonal range rather than by mean |Laplacian| as the
delivery's own crop chooser does — the delivery's metric favours busy texture and
can skip a clean silhouette entirely, which is exactly where a halo would live.

Two positive impressions worth recording, since the brief warned against a
"looks great" report and these are the counter-evidence to my own criticisms.
`tweezers-cpl` at (2128,2000) is genuinely excellent at 1:1: machining
striations crisp and separated, speculars point-like, a clean edge against the
dark background with no rim. `bee-1-cpl` at (3472,2792) resolves individual
golden hairs with defined edges.

One tonal observation: `dry-erase-marker-head-cpl` at (2432,2248) is very dark
with blocked-up shadow detail in the felt. I did not adjudicate it against source
frames, so I cannot say whether that is the tone path or the subject.

## 7. Ranked by how much it would bother someone printing at A3

1. **Dust motes, up to −13.3%, in 18 of 26.** On a smooth background at A3 there
   is nothing to distract from them. Trivially fixable — the correction exists.
   Fix: enable static-defect correction by default.
2. **Softness relative to the sharpest frame, 35–55% of top-octave energy,
   magnitude unproven.** At A3 this is the difference between "sharp" and
   "nearly sharp". Already diagnosed with a better mechanism in `V-softness.md`.
3. **Chroma fringing on the `109MSDCF` debris streak.** Small, local, and moot if
   the mote correction removes the streak.
4. **Blocked shadows on `dry-erase-marker-head-cpl`.** Not adjudicated.
5. **Halo — nothing to fix.** Absent at full resolution; do not send anyone to
   the merge for it.

## 8. What I did not do

I inspected 8 of 26 subjects at honest 1:1 magnification, not all 26. The mote
census and the halo comparison are the only measurements that cover the corpus
broadly (26 and 10 subjects). I did not verify that the DELIVER-V4 JPEGs derive
from SHIP-V4 rather than SHIP-V3 — the delivery README points at `SHIP-V3`, and
the timestamps are merely consistent with V4. I did not adjudicate the shadow
question. I did not repeat the HF measurement on `--linear-srgb`, which the
project's own standing rule requires before the softness magnitude is trusted.

## 9. For the orchestrator

- The `view` tool resamples above ~400 px. Any agent judging image quality
  through it at 1000 px is measuring the viewer. This is worth a line in
  `AGENTS.md` — it is the same failure that produced the original complaint.
- The delivery README references `../acceptance/SHIP-V3/` while the shipped
  masters are in `SHIP-V4`. One of the two is wrong; lineage is unverified.
- `held-out err` reaching 68.2 px with `0 refused` on every subject looks
  alarming but produced no visible ghosting. Either the statistic is a
  cross-validation residual of the warp model rather than a misregistration, or
  it is not measuring what its name suggests. Worth one sentence of
  documentation from whoever owns the aligner.
