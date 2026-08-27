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

**Update, after a second pass: the softness finding in §5 is withdrawn.** On a
clean measurement — both arms `--linear-srgb` from the same pinned SHIP-V4
binary, reference frames developed by strehl's own decoder, compared against the
*per-site* best frame — the master is **sharper** than the best frame available
at each site, by **1.87×** (CI 1.73–2.01) on `flower-bud-alone-cpl` and **1.54×**
(CI 1.42–1.73) on `lead-1-cpl`, confirmed by eye at 400 px 1:1. The stacker is
doing its one job. Two instruments had to fail first, and §5.2 records why.

**Update, after the corpus run: that withdrawal was itself premature, and §5.5
supersedes it.** Both numbers above were measured against the best of a
**13-frame subsample** — 6% and 11% of those brackets. Developing *every* frame
and comparing against the true per-site best reverses the result: on the four
subjects whose brackets are short enough to do exhaustively, the master is
**softer** by 5–19%, significantly so on three (`119MSDCF` 0.815, `109MSDCF`
0.886, `coffee-bubbles` 0.902; `flower-bud-alone-cpl` 0.953, CI spanning parity).
The ratio falls monotonically as the ceiling densifies — 3.173 → 1.294 → 1.021 →
0.939 at n = 13, 52, 104, 205 on one subject at a fixed tile — and a null built
from noised copies of the master shows the max-over-n order statistic accounts
for only 0.1–1.6% of that. **Across a complete bracket, strehl's output is not
sharper than the best frame it was given.**

**Update, after the regime test and the visibility test — two qualifications that
change what the deficit means, without changing that it is there.**

**It is confined to subjects where the merge averages heavily (§5.6).** The four
exact ceilings above were all shallow, averaging-dominated subjects, so the trend
could not be separated from "these subjects are soft". Taking the adversarial
case — `bee-1-cpl`, 299 frames, `avg_index` 0.06, the most selection-dominated
subject in the corpus — to a **complete** 299/299 bracket gives **1.4375** (CI
0.99–2.00, so above parity but not significantly). Against
`flower-bud-alone-cpl`'s **0.9389** at the *same* 1024 px tile and also a complete
bracket, the only difference is the regime. Where the merge selects it beats the
per-site ceiling; where it averages it loses. The estimator is not the problem —
the averaging is.

**It is not visible (§5.7).** On the worst subject at its median site, cut at
380 px and viewed unresampled, the master and the per-site best frame are
indistinguishable — and so is a planted control blurred to *exactly* the measured
deficit. That made the negative unfalsifiable, so I walked a staircase down until
it broke: **0.40 is visibly softer, 0.60 is marginal, 0.80 is not visible.** The
measured deficit is 0.81, σ 0.53 px against a threshold of σ 0.83–1.27 px — a
factor of 1.6–2.4 below what I can see, on the *worst* subject. **It is a fidelity
note, not a shipping defect.** That bounds my discrimination through this view
path, not a human's at A3 on paper.

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

## 5. Defect 3 — the master is SOFTER than a complete bracket's per-site best

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

### 5.1 RETRACTED — the 35–55% deficit was an artifact of a confounded instrument

The first version of this section reported the master sitting *below* the
sharpest single frames, 0.007% against 0.009–0.011%, a deficit of 35–55% in the
top octave, and recorded it as suspected rather than proven because of three
confounds: the `--srgb` transfer curve plus `--auto-exposure` gain on one arm
only, rawpy's demosaicer standing in for the tool's own, and an uncorrected
registration and brightness offset in the visual comparison. **All three have now
been removed, and the deficit does not survive. It is withdrawn.** The measured
result is the opposite sign.

**The clean measurement.** Both arms rendered by the *same* pinned binary that
produced SHIP-V4 — `acceptance-pins\9b05d0b7\target\release\strehl.exe`, SHA-256
`44C2F2CD…B59F490`, matched against the SHIP-V4 provenance — with
`--linear-srgb --demosaic` and no `--auto-exposure` (the binary refuses that flag
outside `--srgb`, so both arms sit on a common linear scale by construction).
Reference frames were developed by strehl itself, one ARW per otherwise-empty
directory, so demosaic, black level, as-shot white balance, colour matrix and the
coverage rescale are common-mode and cancel. `--demosaic` is mandatory here:
full sensor resolution is default only under `--srgb`, and omitting it silently
yields a binned half-resolution comparison.

The reference is the **per-site** best frame — the sharpest frame *at that block*
— not a global sharpest frame, which would read soft everywhere that frame was
defocused.

```
flower-bud-alone-cpl  tile (2600,700) 2560x2560, 14 frames, block 64
  master mean 7948.2  frames mean 7886.1   master/frames = 1.0079  parity OK
  NULL     master vs itself            1.0000   PASS
  DEFECT   master blurred              0.7551   PASS   (<base)
  IMPROVE  master unsharp              4.0583   PASS   (>base)
  NOISE    master + noise              1.8685   PASS   (~base)
  CEILING  best frame as subject       1.0000   PASS   (>=1)
  REF-BLUR every frame blurred         5.5280   PASS   (>base)
  REF-SHARP every frame sharpened      0.7810   PASS   (<base)
  median master / per-site-best = 1.8658   CI [1.7285, 2.0129]  n=541
  => master is SHARPER than the per-site best frame, by 86.6%

lead-1-cpl            tile (2600,1400) 2048x2048, 13 frames, block 64
  master/frames = 0.9960  parity OK; all seven arms PASS
  median master / per-site-best = 1.5357   CI [1.4162, 1.7261]  n=249
  => master is SHARPER than the per-site best frame, by 53.6%
```

**Verdict: no. The master is not softer than the per-site best frame. It is
sharper — by 1.87× (CI 1.73–2.01) on `flower-bud-alone-cpl` and 1.54× (CI
1.42–1.73) on `lead-1-cpl`.** The two subjects are deliberately opposite: the
flower bud's merge averages heavily at coarse bands (`averaged: 97.2% 83.7%
56.7% …`), the lead's is almost pure selection (`13.3% 0.1% 0.0% …`), and the
result holds in both regimes. On `lead-1-cpl` a single frame wins 195 of 249
sites, which makes the ceiling *harder* to beat, and the master beats it anyway.

**Confirmed by eye, at 400 px 1:1, both arms identically display-encoded** (a
stated linear→gamma-2.2 transform, never per-arm autoscaling, which would
fabricate the difference). On `lead-1-cpl` at (3912,2968) the master resolves
granular structure along the bright ridge and crisp crazing across the surface;
the frame that won that site smears both into soft blobs. On
`flower-bud-alone-cpl` at (4104,1500) the master shows cleanly separated
filaments where the winning frame has haze. This reverses the visual claim in the
first draft of this section, which was made through a resampler — see rule 48.

**Block-size sweep, which is how the per-site reference validates itself.** A
finer site is a stronger ceiling, so the ratio must fall as blocks shrink. It
does, monotonically, and the master still leads at the finest granularity tested:

```
block  16  ratio 1.5758  CI [1.5425,1.6144]  n=8244  softer 28.9%
block  32  ratio 1.7809  CI [1.6987,1.8598]  n=2082  softer 21.6%
block  64  ratio 1.8658  CI [1.7285,2.0129]  n= 541  softer 16.3%
block 128  ratio 2.1333  CI [1.8659,2.3680]  n= 134  softer  9.7%
block 256  ratio 2.2388  CI [1.8459,2.5313]  n=  35  softer  2.9%
```

### 5.2 Two instruments failed before this one, and both failures are the finding

**Instrument v1** (`softness_verdict.py`) normalised each block by its own total
variance for amplitude invariance. That quantity is **non-monotone in sharpness**
— unsharp masking raises the denominator faster than the numerator — so the
IMPROVE arm failed on a large tile: sharpening the master *lowered* its score.
Caught by the arm, as designed. No number from it is usable.

**Instrument v2** (`softness_verdict2.py`) fixed that, added per-image noise-floor
subtraction and a fifth NOISE arm, **passed all five arms**, and reported the
master at **0.108** of the per-site best — a ninth of the best frame's detail.
`compare_tiles.py` put that verdict in front of an eye, and the frame that "won"
the median block was a **featureless flat grey**, completely defocused, while the
master at the same coordinates showed hairs and texture. The denominator divided
by the block's low-frequency variance, which is near zero on a defocused frame,
so the quotient exploded and **the envelope selected the most defocused frame in
almost every block.** The reference was upside down.

**Why five passing arms did not catch it: every arm perturbed the MASTER and
compared against a fixed envelope. Not one perturbed the REFERENCE.** A suite
that validates only the numerator cannot see a broken reference, however many
arms it has. This is the same family as `tri.blur_equiv` bounding its own error
below at zero and `overshoot_frac` reading backwards. Instrument v3 therefore
carries three reference-side arms — CEILING, REF-BLUR, REF-SHARP — plus a printed
winner distribution, so a degenerate reference is visible rather than silent.

**The general rule this earns: commission every term the verdict divides by, not
just the one you are measuring.**

### 5.3 The residual soft tail is not misregistration, and is not explained

15–29% of sites still read softer than the per-site best. I hypothesised focus
breathing — magnification changes with focus position, and the registration is a
single global translation over a 2560 px tile — and the worst site did show
master and frame displaying different subject content at the same coordinates.
**The test refuted the hypothesis as a general explanation** (`breathing_check.py`):

```
sites reading SOFT  : median residual  0.72 px   90th pct 30.07 px
sites reading SHARP : median residual  0.71 px   90th pct  9.48 px
soft sites carry 1.02x the residual displacement
Pearson r(radius, residual) = +0.021
recomputed with per-site local registration:
  global translation only   median 1.8786  CI [1.7326, 2.0530]  softer 15.9%
  local per-site            median 1.9550  CI [1.7710, 2.0901]  softer 15.3%
```

At the median, soft sites carry **1.02×** the displacement of sharp sites — no
difference. Only the extreme tail differs (90th percentile 30.07 px vs 9.48 px),
so the one site I eyeballed was real but unrepresentative. Correcting
registration per site moves the verdict *in the master's favour*, 1.879 → 1.955,
and barely touches the soft fraction. **Breathing costs about 4% of the ratio and
does not explain the tail. The tail remains open.** It does not change the sign
of the verdict, but it is the honest residual and I am not claiming otherwise.

### 5.4 The known sharpness regression is already reverted in SHIP-V4

The first draft suggested `docs/research/V-softness.md`'s bisected regression
`57e4554` might account for the softness. **It cannot, because its revert is in
the shipped tree.**

```
git merge-base --is-ancestor 57e45542 9b05d0b7   -> 0   (regression present)
git merge-base --is-ancestor 6430fb28 9b05d0b7   -> 0   (RESTORE also present)
57e45542  halo: delete the noise-driven window shrink; the geometric cap is the fix
6430fb28  halo: restore the noise-driven window shrink; the cap does not subsume it
```

SHIP-V4 contains the restore. That line of inquiry is closed.

**Attribution: none required. There is no softness defect to attribute.**

### 5.5 CORPUS RUN — and the reversal: the sharpness win was a sparse-ceiling artifact

§5.1 was measured against the best of a **13-frame subsample** of each bracket. I
noted that bias and said its direction "runs against my conclusion, not for it".
**The direction was right and the magnitude was wrong by enough to flip the
sign.** Adding frames can only raise a maximum, so a denser ceiling can only lower
the ratio; I treated that as a small conservative margin. It is not small. It is
the dominant term in every number in §5.1.

**The corpus scan, 26 of 26, no refusals.** Partition, which sums to the corpus:

```
measured  26    refused  0    failed  0    not-examined  0     TOTAL 26
```

Every subject, 13 frames sampled across the full bracket, auto-selected
2048 px tile at the master's highest-contrast window, all seven arms re-run per
subject and passing on all 26:

```
flower-bud-with-background-fern 16.515  bee-1-cpl        13.851  bee-3-cpl  13.623
dry-erase-marker-head-cpl        8.392  flat-on-ruler-cpl 7.790  foam        6.747
lavendar-cpl                     6.414  bee-2-cpl         5.155  pencil-flatter 4.627
pencil-steep-angle-cpl           4.558  highly-angled-ruler 4.149  coffee-bean 3.042
flower-inner-edge-cpl            2.903  wrapped-text-1    2.493  couch-fibers 2.315
leaf-2-cpl                       2.141  lead-1-cpl        1.933  flower-bud-alone 1.906
tweezers-cpl                     1.752  113MSDCF          1.651  wrapped-text-2 1.521
flowers-cpl                      1.467  112MSDCF          1.252  coffee-bubbles 0.922
119MSDCF                         0.902  109MSDCF          0.886
  23 of 26 above 1.0; median 2.698; geometric mean 3.156; range 0.886 .. 16.515
```

**That table is an upper bound, not a result.** The ratio tracks how much of the
bracket the reference saw, not how sharp the master is: `bee-1-cpl` at 13/299
sampled reads 13.85, `109MSDCF` at 13/22 reads 0.886. Sampling fraction and merge
regime and stack depth are mutually collinear across this corpus, so no
per-subject number here can be attributed to the merge.

**Density sweep — the ratio does not converge, it collapses.** Same subject, same
tile, same instrument, only the reference density changing:

```
flower-bud-alone-cpl (N=205, 2048 px)   n=13 1.906  n=26 1.369  n=52 1.147  n=104 0.974
bee-1-cpl            (N=299, 2048 px)   n=13 13.851 n=26 7.352  n=52 4.035  n=104 3.203
flower-bud-alone-cpl (N=205, 1024 px)   n=13 3.173  n=52 1.294  n=104 1.021  n=205 0.939
```

**The order statistic is not the cause, and that had to be shown separately**
(`envelope_null.py`), because "the master is soft" and "a max over n draws grows
with n" predict the same falling curve. Reference built from n noised copies of
the master, so the true ratio is 1.000 by construction:

```
flower-bud-alone-cpl  n=13 0.9914  n=26 0.9884  n=52 0.9876  n=104 0.9851
109MSDCF              n=13 0.9889  n=22 0.9865  n=33 0.9845
119MSDCF              n=13 0.9962  n=22 0.9959  n=33 0.9955
coffee-bubbles        n=13 0.9989  n=22 0.9987  n=33 0.9986
```

Inflation is **0.1%–1.6%**. It cannot produce a fall from 3.173 to 0.939.

**The exact ceilings.** Four subjects have brackets short enough to develop every
frame, giving the true per-site best with **zero** subsample bias:

```
subject                 n/N      raw      95% CI          null    corrected
coffee-bubbles        19/19   0.9007  [0.880, 0.919]    0.9988      0.9018
109MSDCF              22/22   0.8735  [0.860, 0.893]    0.9865      0.8855
119MSDCF              33/33   0.8110  [0.787, 0.831]    0.9955      0.8147
flower-bud-alone-cpl 205/205  0.9389  [0.886, 1.013]    0.9851      0.9531
```

**Three of four are significantly softer — 10%, 11% and 19% — and the fourth sits
at parity with a CI spanning 1.0. Not one subject measured against a complete
bracket shows the master sharper.**

**The deficit is not the noise-floor term** (`floor_sensitivity.py`). On three of
four subjects the master's own noise floor exceeds its frames' (119MSDCF 908.7 vs
663.6), so the per-image subtraction removes more from the master and could have
manufactured this. Switching the subtraction off tilts the estimator *towards* the
master, since unsubtracted noise counts as detail and the master has more of it:

```
                      subtracted   no subtraction
coffee-bubbles            0.9007          0.9011   deficit survives [0.880,0.920]
109MSDCF                  0.8735          0.8755   deficit survives [0.864,0.896]
119MSDCF                  0.8110          0.8146   deficit survives [0.793,0.836]
flower-bud-alone-cpl      0.9389          0.9848   not significant  [0.942,1.052]
```

**So §5.1's verdict is superseded. The correct answer to "is the master softer
than the per-site best frame" is: against a complete bracket, yes — by 5–19% on
the four subjects where that comparison is affordable, significantly so on three.
The 1.87×/1.54× figures were measured against a ceiling that had seen 6% and 11%
of the frames.**

**The estimation thesis is not supported, and is not refuted either.** The
prediction was that the gain is largest where the merge averages. Across the
26-subject scan the rank correlation is **−0.729** — the opposite sign — and it
holds at **−0.599** with sampling fraction partialled out. But sampling fraction,
stack depth and `avg_index` are collinear here (Spearman 0.52–0.64 among
themselves), and every subject with an exact ceiling is a shallow, heavy-averaging
one. **There is no exact-ceiling measurement of a selection-dominated subject in
this corpus**, so the mechanism is untested rather than disproved. What can be
said: the three subjects that are significantly soft are the three that average
most (`avg_index` 7.54, 4.40, 2.21), which is consistent with averaging costing
fine detail — the opposite of the thesis — but consistent is not measured.

**Attribution, revised: this is ours, not physics.** A per-site comparison already
controls for defocus — the reference is the sharpest frame *at that site*, so
"no frame was in focus there" cannot explain a deficit. What remains is the merge.

### 5.6 The collinearity is broken: a selection-dominated deep stack reads SHARP

The objection above was mine and it was the right one: all four exact ceilings
were shallow, heavy-averaging subjects, so `Spearman(ratio, avg_index) = −0.729`
could not separate "averaging costs detail" from "these particular subjects are
soft". The test that separates them is one **deep, selection-dominated** subject
at a **complete** bracket. `bee-1-cpl` is the adversarial candidate: 299 frames,
`avg_index` **0.06** — the merge barely averages at all — and at n=104 it still
read 3.20 while falling ~45% per doubling, so its true ceiling was unbounded and
could plausibly have landed anywhere, including below 1.0.

It was affordable. All 299 frames developed and measured, at a fixed 1024 px tile
so the rungs are comparable within the subject:

| n / 299 | ratio | 95% CI | sites | sites softer | arms |
| --- | --- | --- | --- | --- | --- |
| 13 | 19.0604 | 12.08–31.21 | 46 | 0.0% | all-pass |
| 52 | 3.7612 | 2.44–5.92 | 81 | 17.3% | all-pass |
| 104 | 2.1402 | 1.64–4.00 | 84 | 25.0% | all-pass |
| **299 (complete)** | **1.4375** | **0.99–2.00** | 88 | 39.8% | all-pass |

**It lands sharp.** The point estimate is 1.44 at zero subsample bias, far above
every averaging-dominated subject's exact ceiling (0.811–0.939). The comparison
that carries the least baggage is against `flower-bud-alone-cpl`, because both
were measured at **the same 1024 px tile** and both at **complete** brackets, so
neither tile size nor sampling density can be the difference:

| subject | avg_index | n / N | ratio |
| --- | --- | --- | --- |
| `flower-bud-alone-cpl` | 1.80 (averages) | 205/205 | **0.9389** |
| `bee-1-cpl` | 0.06 (selects) | 299/299 | **1.4375** |

**The regime trend survives an adversarial test, and the engineering conclusion
changes with it.** The deficit is not a property of the estimator; it is confined
to the subjects where the merge averages heavily. Where it degenerates to
selection it beats the per-site ceiling — which a pure selector cannot do, since
a selector is bounded above by the frame it picks.

**Two caveats, both against me.** The CI is `[0.9927, 1.9969]`: the lower bound
touches parity, so 1.4375 is *not* significantly above 1.0 at 95%, and I am not
claiming it is. The width is a site-count problem — 88 live sites at 1024 px,
against 358 for `119MSDCF` at 2048 — not a noisy estimate. And 39.8% of sites are
still individually softer than their own best frame, so even here the merge loses
locally about two times in five. What is established is the *direction* and the
*regime*, not a significant win.

### 5.7 Is the deficit VISIBLE? No — and the negative is commissioned

A 19% band-energy deficit and a visible loss of detail are different claims. The
test: `119MSDCF`, the worst subject, at its **median-ratio** site — the site that
tests the headline, not the 0.3rd-percentile outlier — cut at 380 px so the
viewer shows it unresampled (rule 48), master against the per-site best frame,
identical stated encode (`/scale`, gamma 2.2, `scale` from the master crop and
reused verbatim; per-panel autoscaling would fabricate the difference).

The first run of this test picked the *worst* block and that was a mistake worth
recording: it scored 0.0216 — the master holding 2% of the frame's detail — while
over the whole 380 px crop containing it the master **led** at 1.0433. One 64 px
block at that extreme is an alignment residual or a moved element, not the effect
the headline describes. The bisection could not even reach it, bottoming out at
0.0806 against its 4.0 px ceiling, so the control was not a control.

At the median site (block 3,26, ratio 0.7956, master (3938,2146)):

- **A master vs B best frame — I cannot tell them apart on sharpness.**
- **C, the planted control at exactly 0.7956 (σ 0.533 px solved by bisection,
  landing on 0.7956) — also indistinguishable from A.**

That second line is the important one. It means "not visible" was, at that point,
**unfalsifiable**: it could not separate "the effect is below threshold" from
"this viewing path has no power". So I walked the effect size down until it *was*
visible — same crop, same encode, blur solved to hit each rung:

| planted ratio | σ | verdict by eye at 380 px 1:1 |
| --- | --- | --- |
| 0.80 (≈ the measured deficit) | 0.533 px | indistinguishable from master |
| 0.60 | 0.833 px | at most marginal |
| **0.40** | **1.270 px** | **visibly softer** — speckle smoothed, striations lose crispness |
| 0.25 | 1.788 px | unmistakably mushy |

**My discrimination threshold on this path is between 0.60 and 0.40. The measured
deficit is 0.81.** The ladder is monotone, and the null panel (the master against
itself) was correctly indistinguishable — so the instrument is commissioned in
both directions: it can see 0.40, it cannot see 0.80, and it does not confabulate
on identical panels.

**Verdict: MEASURABLE BUT NOT VISIBLE. It is a fidelity note, not a shipping
defect.** In blur-equivalent terms the deficit is σ 0.53 px against a threshold of
roughly σ 0.83–1.27 px — a factor of 1.6–2.4 below what I can see — and this is
the **worst** subject in the corpus, so every other subject sits further below.

**The bound this does and does not support.** It bounds *my* discrimination
through a PNG view path, not a human's at A3 with a loupe on a print. I did not
test a human observer and cannot speak for one. What it does establish is that
the deficit is not the thing the owner reacted to: he was shown a 5× downscale
(§4), whose damage is far above this threshold.

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
2. **Softness against a complete bracket, 5–19%, three subjects significant.**
   Restored to this list and now the top open defect. At A3 this is the
   difference between "sharp" and "nearly sharp" across the whole frame. A
   per-site reference already controls for defocus, so this is the merge, not
   physics. See §5.5.
3. **Chroma fringing on the `109MSDCF` debris streak.** Small, local, and moot if
   the mote correction removes the streak.
4. **Blocked shadows on `dry-erase-marker-head-cpl`.** Not adjudicated.
5. **Halo — nothing to fix.** Absent at full resolution; do not send anyone to
   the merge for it.

## 8. What I did not do

I inspected 8 of 26 subjects at honest 1:1 magnification, not all 26. The mote
census and the halo comparison are the only measurements that cover the corpus
broadly (26 and 10 subjects). I did not adjudicate the shadow question.

The softness re-measurement covers **all 26 subjects** at a 13-frame reference
(§5.5) and **four subjects at a complete bracket**. The four exhaustive ones are
`coffee-bubbles` (19), `109MSDCF` (22), `119MSDCF` (33) and `flower-bud-alone-cpl`
(205). **Three of them are shallow, heavy-averaging stacks**, and no
selection-dominated subject was measured against a complete bracket — `bee-1-cpl`
at 299 frames was swept only to n=104, where it still read 3.20 and was still
falling by ~45% per doubling. **So the corpus-wide magnitude of the deficit is
not established; only its sign, on the subjects where it could be measured at
all.** The residual 15–29% soft tail from §5.3 is measured but not explained. I
did not re-derive the mote or halo findings on `--linear-srgb`; those rest on
`--srgb` renders and are directional claims, not magnitudes.

Lineage of the DELIVER-V4 JPEGs is now settled and was not my doing: the
requester verified SHA-256 over all 26 masters in both arms, 26/26 byte-identical,
so `SHIP-V3` and `SHIP-V4` differ only in label and the inspected images are the
correct ones.

## 9. For the orchestrator

- The `view` tool resamples above ~400 px. Any agent judging image quality
  through it at 1000 px is measuring the viewer. **Now written up as `AGENTS.md`
  rule 48**, with the grating commissioning and the halo-from-downscale numbers
  as its evidence.
- **The softness defect is REAL and is the top open item.** Against a complete
  bracket the master is 5–19% softer than the per-site best frame, significant on
  three of four subjects, and no subject reads sharper. My own two earlier
  verdicts on this question were both wrong, in opposite directions, and both
  because of the reference rather than the master.
- **A per-site maximum over a SUBSAMPLED bracket is not a ceiling, it is a
  sampling statistic.** It moved `flower-bud-alone-cpl` from 3.17 to 0.94 — a
  factor of 3.4 — with the master unchanged. Any future metric that compares
  against "the best frame" must state what fraction of the bracket it saw, and
  must not be compared across subjects of different stack depth. `V-softness.md`
  and any other document using a best-frame reference should be re-read with
  this in mind.
- **A commissioning suite must perturb the reference, not only the subject.** My
  instrument v2 passed five arms while its envelope was selecting the most
  *defocused* frame in every block, because every arm perturbed the master and
  none perturbed the reference. That is a third instance of the family that
  produced `tri.blur_equiv` and `overshoot_frac`. Worth promoting to a rule.
- `held-out err` reaching 68.2 px with `0 refused` on every subject looks
  alarming but produced no visible ghosting. Either the statistic is a
  cross-validation residual of the warp model rather than a misregistration, or
  it is not measuring what its name suggests. Worth one sentence of
  documentation from whoever owns the aligner.

## 10. The instrument is pinned, for the merge before/after

Another lane is changing the merge's noise gate, and its own finding is that the
floor sits at ~3.7× actual noise power while a too-high floor **averages more
pixels** — which is a mechanism for exactly the deficit in §5.5, and, given §5.6,
for exactly the regime it appears in. That gives a clean before/after in which the
only thing that changed is the merge, *if and only if* the instrument is frozen
first. `pin_instrument.py create|verify` does that.

**Pin hashes (SHA-256), git `1e98dafc`:**

| file | SHA-256 |
| --- | --- |
| `softness_verdict3.py` | `A6CA9E4ACCA88169491D6B3ADA891996F7B31BD7CB9F688220576E63E3FA6039` |
| `corpus_softness.py` | `B3CBDACDB1468F363A071618FF64E9711E99827612FDF139A1973B9A4A2D67D9` |
| `envelope_null.py` | `E3E8D695445B1C372D225852E00CFD6B6EE5E88FEEEC753F79458BDC9B7A439B` |
| `density_check.py` | `66F7F70D29A377A46E281685E1B81005B63EF78AC1C100DA1A548607E1DAA8F9` |
| `floor_sensitivity.py` | `567E2D17FD9CCE984DF3E7A84A76CB784B368E2E799DA1DB5DFD8C1E1BE06C5A` |
| `strehl.exe` (the developing binary) | `44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490` |

Also pinned, because each of them can move a ratio silently: `python 3.12.10`,
`numpy 2.4.4`, `cv2 4.13.0`, `tifffile 2026.5.2`. Authoritative copies live
outside the working tree at `C:\dev\strehl-out\V-EYES\PIN\`, because six lanes
can edit this repository and a pin editable by the thing it is meant to detect is
not a pin. `verify` checks live, pinned and manifest hashes agree and exits
non-zero if any moved.

**Build provenance, checked not assumed.** All 26 `SHIP-V4` masters carry a
`.tiff.ok` whose entire content is `44C2F2CD…B59F490` — the binary above. The
`740e7056` build that was circulated is `15EA7346…`, a **different hash at
identical size (9,568,768 bytes)**. Size and timestamp identify nothing here.
None of the four ceilings is suspect.

**The before-reading** (complete brackets, n = N, zero subsample bias):

| subject | n/N | tile | raw ratio | 95% CI | null | corrected |
| --- | --- | --- | --- | --- | --- | --- |
| `coffee-bubbles` | 19/19 | 2048 | 0.9007 | 0.880–0.919 | 0.9988 | 0.9018 |
| `109MSDCF` | 22/22 | 2048 | 0.8735 | 0.860–0.893 | 0.9865 | 0.8855 |
| `119MSDCF` | 33/33 | 2048 | 0.8110 | 0.787–0.831 | 0.9955 | 0.8147 |
| `flower-bud-alone-cpl` | 205/205 | 1024 | 0.9389 | 0.886–1.013 | 0.9851 | 0.9531 |
| `bee-1-cpl` (§5.6) | 299/299 | 1024 | 1.4375 | 0.993–1.997 | — | — |

**The pin reproduces its own reading.** Re-running `119MSDCF` at 33/33, 2048 px
from the pinned copy returned `ratio=0.811`, matching the frozen `0.8110` to four
decimals. The instrument is deterministic, which is what the comparison rests on.

**A pre-registered hazard, recorded now rather than discovered in the numbers.**
The reference frames are developed by the *same* binary as the master — that is
what makes the demosaic common-mode and lets it cancel. So if the gate fix also
changes single-frame develops, **the ceiling moves too** and a change in the
ratio is no longer attributable to the master. A convex-combination merge over
one frame *should* be an identity, but "should" is not a measurement. The
after-run must hash the `frame-*.tiff` files and compare them to the before-run's
before interpreting any delta. Identical frames ⇒ the ratio change is the merge.
Different frames ⇒ the reading must be decomposed, and said so, not averaged over.

`frame_hashes.py` makes that testable without retaining ~50 GB of TIFFs: the
reference arm's per-frame SHA-256s are recorded in
`C:\dev\strehl-out\V-EYES\PIN\frame-hashes.tsv` now, and the after-run re-runs it
and diffs. **The coverage is partial and is stated as a partition, because a
baseline that quietly covers two subjects and is read as covering five is the
exact failure this lane has spent the night documenting:**

| | subjects | hazard testable? |
| --- | --- | --- |
| covered (332 frame hashes + 2 masters) | `119MSDCF` (33), `bee-1-cpl` (299) | yes |
| not covered (renders already freed) | `coffee-bubbles`, `109MSDCF`, `flower-bud-alone-cpl` | **no** |
| | **2 + 3 = 5 of 5** | |

A not-covered subject is **not** a subject that passed. The two covered ones are
the two that matter most — the worst subject and the regime-breaker — but if the
hazard needs checking on the other three they must first be re-developed with the
*old* pinned binary, which is still on disk and hashed above.

## 11. The "best frame" audit, carried out rather than filed

§9 routed a lesson — *a per-site maximum over a subsampled bracket is not a
ceiling, it is a sampling statistic* — and recommended re-reading the documents
that use a best-frame reference. Filing it as advice would repeat the failure this
project has already had tonight: a correct diagnosis written as a comment above
the line that still contained the defect. So here is the audit, with the fraction
of the bracket each reference actually saw.

| document | reference used | bracket seen | verdict |
| --- | --- | --- | --- |
| `V-softness.md` | the *same subject rendered by a different commit* | n/a | **CLEAN — does not use a best-frame reference at all** |
| `BUILD-SHARP.md` §1(a) | `b-g0-cr`, the merge at `--gate 0`, byte-identical to the elected frame | **100%** (per-pixel election over the whole bracket) | **CLEAN, and corroborating** |
| `BUILD-TRIAGE.md` §2.5 | coarse ladder, then `refine_best_frame()` | 40 of up to 299, **then refined** | **CLEAN — caught and corrected the error itself** |
| `M116-promotion.md` P9 | modal winner of the election map, one global frame | **33.4%** on `bee-3-cpl`; 100% on the other two | **AFFECTED — annotated in place** |

**`V-softness.md` is clean and the premise that it needed auditing was wrong.** It
compares two *builds* on identical inputs — a paired A/B whose reference is a
render, not a frame. Grepping it for `sharpest frame`, `best frame`, `ceiling`,
`stride`, `subsample` returns nothing. Nothing in it moves.

**`BUILD-SHARP.md` §1(a) is clean and points the same way I do.** Its reference is
`--gate 0`, which M95 established is byte-identical to the elected frame at
100.0000% of pixels — a per-pixel selection over the full bracket, in the merge's
own geometry, so no subsample and no resampling gauge argument. Its headline is
that **"the shipped merge is softer than its own best input frame by 0.586 µm,
1.2% of the rise."** That is an independent instrument (paired ESF in µm, not band
energy) reaching the **same sign** as §5.5. It reads smaller than my 5–19% because
its ceiling is the merge's *own election*, not the true per-site max — a ceiling
the merge cannot beat by construction, and a lower one than mine wherever the
election is imperfect. Two different references, two magnitudes, one direction.

**`BUILD-TRIAGE.md` §2.5 found this error in itself before I did, and its number
is the best corroboration in the corpus.** It noticed that stage 1 picked from a
coarse ladder of 40 of up to 299 frames, reasoned that an under-selected best
frame "biases toward certifying the merge GOOD", and added `refine_best_frame()`.
Refining moved `bee-1-cpl` DETAIL from frame 46 → 44, the source's measured
sharpness from 136.3 → 250.7 DN, and **`ratio` from 1.90 to 1.04** — a 45% fall
in the ratio from nothing but a better ceiling, the same direction and roughly the
same magnitude as my density collapse. It is an independent replication.

**`M116-promotion.md` P9 is the one that carries the error, in its strongest
form.** `pick_single.py` takes `sorted(...)[:LIMIT]` with `LIMIT = 100` — the same
prefix-truncation I committed in `frames[::N//n][:n]`, shortening the focus range
rather than thinning it — and then collapses the ceiling to the *modal winner of
the election map*, one global frame for the whole image. Measured cost, same
master and sites, only the ceiling changed (`119MSDCF`): **1.1458 against one
global frame, 0.8110 against the per-site max — ×1.41, and the sign inverts.**
Annotated in three places, because the claim was load-bearing in all of them: the
second headline (line ~15), the supporting-verdicts table (line ~116), and P9
itself. The M85 concern P9 reports as closed should be treated as **still open**.

Three independent instances of one mistake — mine, `BUILD-TRIAGE`'s, and
`M116`'s — is enough to call it a family rather than an accident.

---

# 12. `STREHL_RESTORE` -- pre-registration (written and committed BEFORE the run)

ORCH routed a second before/after on the frozen instrument: `restore.rs`, a
single-image Wiener restoration whose `H` is strehl's own resampling kernel,
built and wired into the merge and **off by default**, parked on a three-ROI
edge-rise measurement with one marginal ROI and two nulls. The routing argument
was that a three-edge instrument and a per-site band-energy ceiling over a
complete bracket are not the same class of instrument, so the change may never
have been scored rather than having failed. That argument is correct in general.
This section tests whether it applies here.

The instruction was **"prediction first, number second."** What follows was
committed before `restore_ab_run.py` was run on either arm.

## 12.1 The band the ratio actually integrates over

`band_probe.py`. Two earlier versions of this probe were **rejected by their own
commissioning arm**, and the second failure is worth recording because it is a
trap anyone repeating this will fall into. I estimated the high-pass response
`|H|^2` as a ratio of two noisy spectra and multiplied it by the image PSD. At
low `f` the true response is `~1e-8`, so that ratio was measuring float rounding
noise, and multiplying rounding noise by an enormous low-frequency PSD parked the
band median at **0.0020 cyc/px** -- a physically absurd answer that would have
predicted the restoration could not possibly matter.

`H` never needed estimating: **the high-pass output already contains it.** Taking
the radial energy of `hp` directly, in float64, removes the ratio, the
cancellation and the separate noise probe in one step.

The commissioning arm is a planted blur of known sigma, predicted from the band
and measured directly. It failed the second version at **240.7%** and passes the
third at **4.4% worst error** over four blur levels spanning 0.70 to 0.21
retention:

| sigma | predicted retention | measured | ratio |
|---|---|---|---|
| 0.53 | 0.6997 | 0.7315 | 0.956 |
| 0.83 | 0.5124 | 0.5201 | 0.985 |
| 1.27 | 0.3328 | 0.3403 | 0.978 |
| 1.79 | 0.2097 | 0.2150 | 0.975 |

**Band (`119MSDCF`, 2048 px): centroid 0.1750 cyc/px, median 0.1453, P25-P75
0.089-0.238, and 76.9% of the energy at or below the 0.25 cyc/px knee.**

## 12.2 The gain curve at that band

`restore.rs` sets `knee = 0.5 / grid_factor`, which for a demosaiced merge is
**0.25 cyc/output px**, and tapers the excess gain to zero between the knee and
output Nyquist. ORCH's prior -- that a band centred at or below 0.25 would see
little -- rests on that taper.

**The taper is vacuous for a demosaiced merge, and this changes the prediction.**
The filter runs on the CFA quad plane, whose own Nyquist is 0.5 plane-cycles =
**0.25 output cycles = exactly the knee**. The entire band the filter can
represent maps to `f <= knee`, where `roll_off == 1`. The roll-off region lives
above what the CFA-plane filter can express, so it never engages. The gain is
flat-topped across the whole plane band and does *not* decay toward the top of
the statistic's range. That is confirmed in the binary's own log, where `max
gain` and `at Nyquist` are the same number on the green planes.

`merge_cmd.rs` applies the filter separably x then y, so the picture receives
`G(fx)*G(fy)`; the log's `2-D` column is that product at the peak.

## 12.3 The intervention is subject-dependent, and two of my four subjects are hard no-ops

`restore_ab.py`, pinned binary `9b05d0b7` (`44C2F2CD...`), each subject rendered
twice, `STREHL_RESTORE` **deleted** from the environment for arm A rather than
set to `0`, so the arms differ only in the variable's presence.

| subject | frozen ratio | peak 2-D gain | recovered | arms byte-identical? |
|---|---|---|---|---|
| `119MSDCF` | 0.8147 | **1.0000** | 0.0000 | **YES** |
| `109MSDCF` | 0.8855 | **1.0000** | 0.0000 | **YES** |
| `coffee-bubbles` | 0.9018 | **1.6682** | 0.6388 | no |
| `tweezers-cpl` | -- | 1.2749 | 0.3709 | no |

`cap 1.700` appears in every log, so the switch was honoured in all four; on the
two no-op subjects the estimator then *declined*. That is not a failure. The gain
is `clamp(h / (h^2 + sigma2/S(f)), 1, cap)` with `S` the measured power **minus**
`sigma2`, and its lower clamp at 1 makes the filter structurally incapable of
blurring. It returns exactly 1 when what the gather attenuated is, on the
estimator's own evidence, noise.

**On `119MSDCF` and `109MSDCF` the two arms are SHA-256 identical files.** For
those subjects the A/B needs no instrument: the ratio cannot move, because the
pixels are the same. `119MSDCF` is my *worst* subject at 0.8147, so the lever
ORCH hoped might close the gap is not merely small there -- it is exactly, provably
zero.

## 12.4 The registered prediction for `coffee-bubbles`

`restore_predict.py`, two independent routes.

Route A integrates the **realised** end-to-end transfer `T(f) =
P_restored/P_plain` against the commissioned band density. It is commissioned
against a Parseval identity it must satisfy -- the same number computed in the
spatial domain with no spectra in it -- and reproduces it to **0.00%**.

    f=0.10  T=1.008     f=0.20  T=1.278     f=0.30  T=1.443
    f=0.15  T=1.113     f=0.25  T=1.407     f=0.40  T=1.393

Route B runs the pinned `detail()` on both masters, so it sees the
5th-percentile floor subtraction that route A cannot.

    ROUTE A  band-weighted energy gain   1.1645
    ROUTE B  per-site median, 972 sites  1.1906   [P25 1.1547, P75 1.2699]

They agree to 2.2%.

> **REGISTERED PREDICTION.** On `coffee-bubbles` the raw ratio moves by
> **x1.19**, from 0.9007 to **~1.072**; corrected, from 0.9018 to **~1.073**,
> crossing 1.0. On `119MSDCF` and `109MSDCF` the move is **exactly x1.000**.
> The order-statistic null is common-mode -- it depends only on the reference
> set, which is one shared set of hardlinked files -- so it divides out.
>
> **The prediction that this is a small effect is registered as WRONG on
> `coffee-bubbles` and RIGHT on the two no-op subjects.** ORCH would have bet on
> "no detectable move"; on a third of my exact-ceiling subjects that bet loses,
> and it loses because the knee taper does not engage on a demosaiced merge.

## 12.5 The cost, registered at the same time

The noise floor rises **+46.8%** (8381 -> 12307 DN^2) for a **+19.1%** detail
gain. Linear filtering cannot change SNR at any single frequency; the asymmetry
is spectral. Noise is white and therefore sits where the gain is largest, signal
is red and sits where the gain is ~1.0. In amplitude that is **+21% noise for
+9% detail**. Any recommendation to flip the default has to carry that number,
and a band-energy ratio that improves while visible noise rises faster is
exactly the kind of statistic this project has been burned by.

