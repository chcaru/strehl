# M102 — A calibrated focus-stack simulator

Status: Report
Milestone: M102
Owner: M102 agent
Pre-registration: `experiments/M102-simulator/PREREGISTRATION.md`, committed
`e133211`, before any arm.

---

## Verdict

**NOT ESTABLISHED — by my own pre-registration, and the reason is a defect in
the registration rather than in the instrument.**

PREREGISTRATION §5 says: *"If D1 or D2 fails to go red, the round-trip is not
a check — it has never been made to fail — and the milestone reports NOT
ESTABLISHED even if every other bar is green."* **Both** registered defect
plants failed to redden the registered bars. That clause is decisive and I am
honouring it.

What the evidence actually shows, which is better than that verdict sounds:

| | result | label |
|---|---|---|
| Synthetic stack decodes through the shipped path | 3/3 frames, correct ISO, black, white, CFA, camera | MEASURED |
| Round-trip, unplanted | median \|e\| **0.0000** frames, 97.94% within ±2, median signed **0.0000**, n = 44643 | MEASURED |
| D1 one-frame correspondence shift | recovered **−1.0000** frames exactly; registered threshold let it pass | MEASURED |
| D2 unmodelled warp, as registered | did **not** redden any bar | MEASURED |
| D2 swept | reddens at 32% scale = **2.91** depth-slab widths | MEASURED |
| Z1 reseed | all bars green | MEASURED |
| Z2 ignored TIFF tag | all bars green, index map **bit-identical** to unplanted | MEASURED |
| Aligner vs planted warp | recovers **96.96%**; shortfall 0.604 px vs 0.103 px self-consistency floor | MEASURED |
| N1 noise, synthetic | measured/predicted median **1.0638** \[1.0054, 1.1470] | MEASURED |
| N1 noise, real `bee-3-cpl` | measured/predicted **0.9946** | MEASURED |
| N2 through-focus width | synth/real width ratio **1.219** | MEASURED |
| N3 disconnected fraction | synth **0.523%** vs real **3.684%** under one operator | MEASURED |

The simulator exists, is faithful on all three registered realism bars, and
its round-trip recovers a planted correspondence shift to four decimal places.
The two things that failed are both mine: a threshold set equal to the plant
size, and a geometric plant sized without reference to the scene it had to
express through.

---

## 1. Architecture: out-of-tree, and why

Decided and argued in PREREGISTRATION §0 before any arm. Summary of the
reasoning, with the one point that turned out to matter most:

**Emitting *files* proved to be a materially stronger test than handing arrays
to `merge` would have been.** (MEASURED, S1.) The first synthetic file this
milestone wrote decoded with **exit 0 and "3 ok, 0 failed"** while reporting
`active area : 3737911296 x 646971392 at (425984000, 8388608)` and
`black 0.002674798`. Every inline TIFF tag was correct and every
heap-resident tag was garbage, because my writer computed its heap offset as
`base + ifd_size` while the file actually interleaved a second IFD between
the two. An in-crate generator handing arrays to `merge` cannot express that
class of bug at all, and a decoder that returns success while reporting a
black level of 0.0027 is exactly the kind of thing a simulator is supposed to
be able to catch. The file route exercises decode, black-level subtraction,
CFA interpretation and metadata; the array route exercises none of them.

**Cost, stated plainly: there is no CI test.** Proposed mitigation, routed
through the orchestrator because I may not edit `lib.rs`: commit one
generated 128×192 DNG as a fixture under `crates/strehl-raw/tests/`, so a
future in-tree test can assert the decoder's black/white/CFA/ISO handling
without a Python dependency. The file is 49,780 bytes.

---

## 2. What the generator models, and from which measured constant

Every constant is cited by SYNTHESIS fact number at its definition in
`src/m102lib.py`. Free parameters — the ones the owner's rail sets, not the
sensor — are collected in `SimSpec` and named as free.

| component | value | source |
|---|---|---|
| pixel pitch, CFA | 5.12 µm, RGGB | rig section, `AGENTS.md` |
| black / white | 512 / 15360 | `AGENTS.md`; `noise.rs:418` |
| effective aperture | `N_eff` = 16.8 at m = 2.0, p = 1.0 | fact 12 |
| wavelength | 0.55 µm | **DERIVED**, §6.2 |
| breathing | scale 1.0 → 1.055064 over 32 frames | facts 1177, 1254 |
| photometric drift | 1.0 → 0.898344 | fact 1254 |
| noise | `σ² = g·S + (RN·g)²`, g = 0.228938 DN/e⁻, RN = 4.2 e⁻ | `sensor_for()` |
| latent scene | slanted plane, occluding slab, smooth disc | fact 73 |

**The ISO is never typed into the generator.** (MEASURED.) `s2_generate.py`
names the real reference stack `bee-3-cpl`, calls M92b's `sensor_for()` for
its EXIF triple, uses the returned gain and read noise in the noise model,
and writes the returned ISO into the DNG. The written value read back through
the shipped decoder is **ISO 100**, matching. This closes the exact loop M92
found broken, where `ISO = 500` as a module constant was applied to an
ISO-160 stack; my guard now governs my own generator.

### 2.1 Optics, checked against the corpus rather than asserted

The defocus term is a filled disc, `MTF = 2·J₁(2πrf)/(2πrf)`; the diffraction
term is the incoherent circular-pupil OTF at the measured `N_eff`. Two
independent checks:

- **DERIVED**: inverting fact 12's extinction point `0.5 = 5.12/(λ·18.6)`
  gives λ = 0.5505 µm. Using 0.55 µm reproduces fact 12's `N_eff = 18.6` to
  three digits.
- **DERIVED**: at m = 2.0, f/5.6, the model gives `f_c = 0.5541` cyc/px and
  MTF at Nyquist = **0.0349**. The dispatch brief states ~0.036. The
  simulator reproduces the corpus's own diffraction figure.

### 2.2 Occlusion, which is the reason for the layer model

Layers are blurred individually and composited with `over` **after** blur,
not blurred as one flat image. That is what makes a defocused foreground
spread its alpha over the background behind it. M87 and M96 both need
occlusion ground truth and neither has it; the generator emits an explicit
`mask_occ` band — the dilation of the occluder by its own worst-case defocus
radius — so occlusion error can be scored separately from everything else.
It is **reported and not gated** (PREREGISTRATION R4), because `stack --help`
states the shipped merge "does not yet model occlusion" and a bar on a
known-unmodelled effect would fail for a reason unrelated to the hypothesis.

Occlusion-band result, unplanted arm (MEASURED): n = 3720, median \|e\| =
0.0000, 84.97% within ±2, against 97.94% on the textured mask.

---

## 3. Round-trip

Run with breathing disabled and `STREHL_ALIGN=0`, so the output grid is the
latent grid binned 2× with no crop and **no fitted transform anywhere in the
scorer**. Nothing in this arm solves for a registration, which is what makes
a geometric plant a real plant rather than something a fit can absorb.

MEASURED, `out/s3_nb_base.json`, n = 44643 textured pixels:

- R1 median \|index error\| = **0.0000** frames (bar ≤ 1.0) — GREEN
- R2 fraction within ±2 = **0.9794** (bar ≥ 0.90) — GREEN
- R3 median signed error = **0.0000** frames (bar \|·\| ≤ 1.0) — GREEN

Descriptive, no bar: smooth region n = 2545, 79.84% within ±2; occlusion band
n = 3720, 84.97% within ±2.

**The smooth-region number is not evidence and I am not claiming it as
such.** (ARGUED.) The smooth disc sits at the background's depth, and the
background wins 40.00% of all pixels — it is the plurality answer. An
estimator that returned "background" everywhere would score well there. Fact
73 says the focus measure is undefined on such a region; this arm is
consistent with that and tests nothing.

---

## 4. Controls, including the two I made fail

### 4.1 D1 — one-frame correspondence shift. Plant recovered exactly; bar defective.

The generator renders the defocus schedule one frame late while recording the
unshifted index as truth. Per discipline 615 this perturbs the
**correspondence only**: every frame remains a physically valid frame of the
same stack, with the same noise, texture and defocus statistics. Only which
frame is sharp where moves.

MEASURED: median signed error = **−1.0000** frames, against **0.0000** on the
unplanted arm, over 44643 pixels. The instrument recovered the planted shift
to four decimal places and got its sign right.

**The registered bar let it through.** I registered `R3: |median signed| ≤
1.0` and then planted a shift of exactly 1.0, so the plant lands precisely on
the threshold and `≤` resolves in favour of green. This is the same class of
defect as M92's disciplines 608/609: a registered bar that can resolve the
wrong way for a reason unrelated to the hypothesis.

The corrected bar introduces no new freedom, because both numbers are already
collected: **R3′ = \|median signed\| ≤ 0.5** separates 0.0000 from −1.0000
with a factor of two of margin on each side. A bar must not be set equal to
the plant size it is meant to detect.

### 4.2 D2 — unmodelled warp. Failed as registered; swept to find the threshold.

Registered: an extra global scale on the second half of the stack, magnitude
"0.5% of the half-diagonal". On a 512 px frame that is 4.127% of scale. It
did **not** redden any bar.

Rather than re-tune it quietly, I swept the magnitude (`s5_warp_sweep.py`).
MEASURED:

| warp | displacement at r = 256 | in slab widths | median \|e\| | within ±2 | verdict |
|---|---|---|---|---|---|
| 4.127% (as registered) | 10.15 px | 0.48 | 0.0000 | 0.9672 | GREEN |
| 8.0% | 18.96 px | 0.89 | 0.0000 | 0.9550 | GREEN |
| 16.0% | 35.31 px | 1.66 | 0.0208 | 0.9228 | GREEN |
| 32.0% | 62.06 px | 2.91 | 0.0625 | **0.8348** | **RED** |

**The check is real — it reddens at 2.91 slab widths.** The registered
magnitude was under-powered by roughly 8×.

The mechanism, and it generalises (DERIVED from the table): **an index-map
round-trip is blind to a geometric error smaller than the depth
autocorrelation length of the scene**, because displacing texture within a
constant-depth region maps depth to the same depth. The scene's plane is
quantised into 24 slabs of 21.33 CFA px; degradation of `within ±2` is
monotone in displacement (0.9672 → 0.9550 → 0.9228 → 0.8348) and crosses the
bar between 1.66 and 2.91 slab widths. **R1 never reddens at all**, even at
62 px of displacement — the median is dominated by locally-constant depth,
and only the tail statistic R2 sees it.

Consequence for control design, and it is the transferable part: **a
geometric plant must be sized against the depth structure of the scene it
must express through, not against the sensor's dimensions.** Sizing it as a
fraction of the half-diagonal, which is what I did, is sizing it against the
wrong quantity.

### 4.3 Z1, Z2 — the no-ops, per discipline 618

- **Z1, reseed only**: median \|e\| 0.0000, within ±2 = 0.9804, all bars
  green. (MEASURED.)
- **Z2, an extra valid-but-ignored `ImageDescription` tag in every file**:
  all bars green **and the recovered index map is bit-identical to the
  unplanted arm** — SHA-256 prefix `caed790f2e6f43bf` for both. (MEASURED.)

Z2 is the stronger of the two and it is the one worth keeping: it asserts the
whole chain from TIFF writer through decoder to elected index is insensitive
to a change carrying no physics, at the level of bytes rather than statistics.

### 4.4 A control I broke and report against myself

The realism arm's first revision reported a synthetic noise ratio of exactly
**0.000** on all 32 frames while simultaneously reporting **0.9946** on the
real stack. (MEASURED, superseded.) Cause: `noise_in_flat()` was handed a
frame with the off-mask pixels filled by a constant and took the median
absolute deviation over the whole image; more than half the pixels had
exactly zero residual, so the MAD was exactly zero. The bug was visible only
because the same function ran on a real stack in the same execution and
returned a sane number. A single-arm version of this measurement would have
reported 0.000 and I would have had to reason about it from nothing. The
function now takes the mask explicitly and the docstring records the failure.

---

---

## 4b. The aligner, scored against a known warp for the first time

Requirement 2 asked for a warp "the aligner is expected to solve, so `align`
can be scored against truth for the first time". The corpus has measured the
aligner's drift, its held-out residual and its cycle-consistency floor, but
those are internal: they compare the aligner to itself.

Setup (MEASURED, `out/s6_align_truth.json`): 16 synthetic frames at 1024²
CFA → 512² plane, breathing on, `--reference 0`. Nothing is fitted; the truth
is the number the generator used. A 512² plane is the smallest this arm can
use — at 256² the aligner exits with *"the fine tile grid does not fit in
this plane"*.

| quantity | value |
|---|---|
| planted corner drift, frame 0 → 15 | **19.8963** plane px |
| aligner's measured corner drift | **19.2920** plane px |
| recovery ratio | **0.96963** |
| shortfall | **0.6043** plane px |
| aligner's own cycle-consistency floor | 0.103 plane px |
| edges measured / refused | 49/49, 0.0% refused |
| frames placed | 16/16 |

**The aligner recovers 96.96% of the planted breathing drift, and its
shortfall is 5.87× its own cycle-consistency floor.** (MEASURED for the
numbers; DERIVED for the ratio.) The two quantities measure different things
and the corpus has not previously been able to compare them: cycle
consistency asks whether the aligner agrees with itself around a loop, and it
answers 0.103 px. Accuracy against truth is 0.604 px. **An aligner's
cycle-consistency floor is not a bound on its accuracy** — here it
under-states the real error by a factor of six.

Caveats I can state and have not resolved (ARGUED). The shortfall is a
*systematic under-estimate of scale*, consistent with a bilinear-resampling
bias in either my generator or the aligner's own resampler; this arm cannot
separate those two. The corner-radius convention contributes at most ±0.03 px,
so it does not explain 0.604 px. This is one stack, 16 frames, one reference
choice — fact 127's standing lesson applies and I am not presenting 0.96963
as a constant.

---

## 5. Realism, measured against `bee-3-cpl`
One operator, implemented once, applied to both stacks. Every comparison is a
ratio or a normalised width, never an absolute scene-dependent quantity — the
constraint is discipline 609, which I earned in M92 by writing exactly such a
bar.

**N1 — noise against the calibrated model.** MEASURED.
- Synthetic: measured/predicted median **1.0638**, range \[1.0054, 1.1470]
  across 32 frames. Bar \[0.90, 1.10] on the median — GREEN. The maximum
  exceeds 1.10 on the later frames and I am not hiding it; the drift is with
  frame index, consistent with the residual 0.4% modulation in the smooth
  disc not scaling with the photometric falloff that the prediction follows.
- Real `bee-3-cpl`, 38 frames, 384 px central ROI: **0.9946**. No bar was
  registered on the real stack, deliberately. This is an independent
  corroboration of the M48 gain/read-noise calibration and of `sensor_for()`:
  the model predicts real per-frame noise on this body to **0.54%**.

**N2 — through-focus response width.** MEASURED. Synthetic half-width 3.0 of
32 frames = 9.375% of stack; real 23.0 of 299 = 7.692%. Ratio **1.219**, bar
factor 2 — GREEN.

**This number is only trustworthy because the first version of it was
wrong.** (MEASURED, superseded.) Measuring the real stack at stride 8 gave a
half-width of exactly **1.0 sample** — the measurement was pinned at its own
resolution limit, and the synth/real ratio built on it was **3.5625**, which
would have failed the bar for a reason that had nothing to do with the
simulator. Re-measuring on a dense stride-1 window of 64 consecutive real
frames resolves the half-width as 23 frames. A width measurement whose answer
equals its own sampling quantum is not a measurement.

**N3 — disconnected competitive set.** MEASURED. Synthetic **0.523%**
(mean gap 12.94 frames); real, under the same operator, **3.684%** (mean gap
10.14 frames). Registered bar — non-zero and below 0.60 — GREEN.

**The registered bar is weak and I flagged it as weak in advance.** The
substantive number is the ratio: the simulator produces **7.04× less**
disconnectedness than the real stack. See §6.1.

**N4 — focus-measure histogram.** Declared descriptive at registration
precisely so that a favourable-looking shape could not be promoted to
evidence afterwards. It is not promoted.

---

## 6. Where this simulator lies

The required deliverable. Ordered by how much I think each one matters.

### 6.1 Its depth structure is ~7× too simple

MEASURED: 0.523% of synthetic pixels have a disconnected competitive set
against 3.684% of real ones under the same operator. The scene is a slanted
plane in 24 slabs, one occluding slab and a background: depth is piecewise
constant over regions tens of pixels across. A real bee is not. **Any
conclusion about occlusion prevalence, competitive-set topology or
depth-discontinuity handling drawn from this simulator will be optimistic**,
and §4.2 shows the same simplicity is what makes the round-trip blind to
geometric error below ~1.7 slab widths.

This is also the reason **my 0.523% must not be compared to M96's 25.247%
(fact 1263)**. My operator is a 17×17 local Laplacian energy with a 10%
competitiveness threshold; M96's is the shipped noise-gated criterion. The
two numbers are different quantities. The only comparison I am entitled to
make is synthetic-vs-real under my own single implementation, which is the
7.04× above.

### 6.2 λ is derived, not measured

The wavelength is obtained by inverting fact 12's extinction point, not by
measurement. It reproduces fact 12 to three digits and the brief's Nyquist
MTF to 0.0349 vs ~0.036, but it is one number carrying the entire chromatic
behaviour of the diffraction model, and the simulator is monochromatic in its
optics: R, G and B are blurred by the *same* PSF. Real longitudinal chromatic
aberration puts the three channels at different focus. **A simulator built to
test demosaic or colour-fringing behaviour must not use this one as-is.**

### 6.3 Photometric drift reproduces the predicted value, not the measured one

The generator derives irradiance falloff from 1/m² off the same scale track
that produces the geometric warp. That yields **1.1132** — fact 1254's
*predicted* value — where the *measured* value is **1.1091**, a 0.37%
difference. The agreement is therefore partly circular: it reproduces the
geometry's prediction by construction and cannot be used as evidence that the
prediction is right. M99 scoring a photometric correction against this
simulator would be scoring it against the model, not against the rig.

### 6.4 No fixed-pattern noise

Fact 610 MEASURED FPN at ρ = 0.3094 of single-frame noise variance on this
body, and fact 612 MEASURED that it is white to Nyquist and censored an
entire FRC-based metric family. The generator models shot and read terms
only. Predicted consequence, and it is testable: the synthetic N1 ratio
should sit *below* the real one, because the real measurement contains a
variance component the prediction omits. **It does not** — synthetic 1.0638
against real 0.9946. I cannot reconcile those two numbers with a missing 31%
variance component, and I am reporting the tension rather than an
explanation. The likeliest reading is that the 9×9-median-residual MAD
estimator suppresses a spatially-fixed component on the real stack, which
would mean my N1 operator is partly blind to exactly the thing fact 612 says
matters most. **Anything that depends on FPN must not use this simulator.**

#### 6.4.1 Addendum 2026-08-27 — the missing terms are now measured, and the decision is to EXTEND rather than rebuild

When §6.4 was written, no dark frame or flat field existed for this body, so
the generator could not have modelled the fixed-pattern terms even in
principle. Both captures have since been delivered and reduced.
`experiments/V-CALIB/`, reported in `docs/research/V-LINEAR2.md` §12 item 4,
measures on this body: black 512.10 DN against a nominal 512; gain 0.2232
DN/e⁻ against the corpus model's 0.2289; read noise 0.887 DN = 3.974 e⁻
against the model's 4.200; and the two terms this simulator lacks — **DSNU
0.389 DN and PRNU 0.286% of signal**.

The decision, taken with the orchestrator and recorded here so it is not
re-argued: **extend this generator with those two terms and cite V-CALIB;
do not rebuild it.** A rebuild would re-derive numbers that already exist at
full cost for the same content, and it would discard §6's own honest
accounting of where the generator is circular, which is the most useful part
of this document.

What the addendum does **not** license. §6.4's tension is unresolved and
adding a DSNU term does not resolve it: the synthetic N1 ratio sits *above*
the real one where a missing variance component predicts *below*, and the
likeliest reading remains that the 9×9-median-residual MAD estimator is partly
blind to a spatially-fixed component. Adding FPN to the generator and watching
that gap close would be evidence; asserting it will close is not. Until it is
measured, §6.4's prohibition stands as written.

What is still open after V-CALIB is the **band-resolved** split of the
fixed-pattern structure. The scalar magnitudes above do not say how much of it
lands at 0.40–0.48 cyc/px, which is precisely the band where
`docs/research/V-LINEAR2.md` §10.1's `DISJOINT` arm reads 40.2% and where a
noise measurement therefore has the most at stake. That needs the flats
developed through the same linear path as the subject frames.

### 6.5 The scale track is linear; the corpus only says smooth and monotonic

Fact 1177 MEASURED the drift as smooth and monotonic over 299 frames. Linear
is an assumption I added. Curvature has not been measured, and §7 names it as
the capture I would commission.

### 6.6 Small remaining items

- The colour matrix in the DNG is plausible, not measured on this body. It
  affects `--srgb` only; every bar here is on the linear binned output.
- The defocus PSF is a filled disc: no spherical aberration, no
  apodisation, no bokeh structure.
- No dust, no hot pixels, no dead columns, no shutter-timing jitter.
- Rendering is at CFA resolution with no supersampling, so sub-pixel
  geometry is limited by the sample grid; the slanted edge is analytically
  ramped over 2 px to compensate, which is itself a small lie.

---

## 7. The measurement I would commission

Nothing blocked this milestone — a faithful-enough simulator was achievable
with what the corpus has. One capture would remove the largest remaining
assumption, §6.5: **a bracket of ≥ 60 frames on a flat, high-contrast, planar
target at fixed focus spacing, with the rail position recorded per frame**,
so the breathing scale can be measured *per frame* rather than assumed linear
between its measured endpoints. Fact 1177 gives the total; nothing in the
corpus gives the shape. That capture would also let the aligner be scored
against a physically known warp rather than against my model of one.

---

## 8. Reproduction

```
python src/s1_spike_dng.py                       # decoder acceptance
python src/s2_generate.py <dir> [--plant ...] [--no-breathing] [--size N]
python src/s3_roundtrip.py <dir> <tag>           # R1/R2/R3
python src/s4_realism.py                         # N1/N2/N3 vs bee-3-cpl
python src/s5_warp_sweep.py                      # D2 sensitivity threshold
python src/s6_align_truth.py <dir> <measured>    # align vs planted warp
```

Artefacts under `experiments/M102-simulator/out/`; generated stacks under
`C:\dev\strehl-out\M102\` and not committed.

---

## § Candidate facts

**P1.** A hand-written uncompressed CFA DNG with `PhotometricInterpretation`
32803 and the raw image in IFD0 is decoded by the shipped `strehl` binary
with correct dimensions, black level, white level, CFA pattern, camera model,
white balance and ISO — so synthetic focus stacks can enter the pipeline
through the same decode path a real capture uses, with no change to any
crate. Significance: ground truth becomes available end-to-end for every
future milestone; a plant can be *specified* rather than designed and hoped
for. MEASURED (M102 S1, `strehl probe` exit 0, 3 ok / 0 failed; ISO 100,
black 512, white 15360, 192×128).

**P2.** The shipped selector recovers a planted per-pixel focus index from a
synthetic stack with median absolute error **0.0000** frames and 97.94% of
textured pixels within ±2 frames (n = 44643), and recovers a planted
one-frame correspondence shift as a median signed error of exactly
**−1.0000** frames. Significance: the first end-to-end score of the focus
election against known truth; it establishes that the round-trip has real
resolving power, which is what makes its blind spots in P3 meaningful.
MEASURED (M102 S3, `out/s3_nb_base.json`, `out/s3_d1_index1.json`).

**P3.** An index-map round-trip is blind to unmodelled geometric error
smaller than the depth autocorrelation length of the scene. On a scene whose
depth is piecewise constant over 21.33 px slabs, an extra 4.127% scale on
half the stack (10.15 px displacement, 0.48 slab widths) leaves every bar
green; the round-trip first reddens at 32% (62.06 px, 2.91 slab widths), and
only the tail statistic moves — median absolute error never exceeds 0.0625
frames even at the reddening magnitude. Significance: a geometric control
must be sized against the scene's depth structure, not against the sensor
dimensions, and a median-based acceptance bar will not see a warp defect at
any magnitude tested. MEASURED (M102 S5, `out/s5_warp_sweep.json`).

**P4.** The calibrated noise model `σ² = g·S + (RN·g)²`, with gain and read
noise taken from EXIF via M92b's `sensor_for()`, predicts the measured
per-frame noise of the real `bee-3-cpl` stack to **0.54%** (measured/predicted
= 0.9946, 38 frames, 384 px central ROI). Significance: an independent
out-of-sample corroboration of the M48 calibration on a stack it was not
fitted to, and it is the constant the whole simulator's noise arm rests on.
MEASURED (M102 S4, `out/s4_realism.json`).

**P5.** A defect control whose magnitude is set equal to the acceptance
threshold it must cross cannot fail. M102 registered `|median signed index
error| ≤ 1.0 frame` and planted a shift of exactly 1.0 frame; the estimator
recovered −1.0000 exactly and the bar resolved GREEN on `≤`. Significance:
extends disciplines 608/609 from "a bar that can fail for unrelated reasons"
to "a bar that cannot fail for the *related* reason"; the corrected form is
that a bar must be separated from the plant size by a stated margin — here
0.5 frames separates 0.0000 from −1.0000 with 2× margin either side.
MEASURED (M102 S3, `out/s3_d1_index1.json` vs `out/s3_nb_base.json`).

**P6.** A width measurement can be pinned at its own sampling quantum and
report a confident wrong ratio. M102's through-focus width arm sampled the
real stack at stride 8, measured a half-width of exactly 1.0 sample, and
produced a synth/real width ratio of 3.5625 that failed its bar; re-measuring
on a dense stride-1 window of 64 consecutive frames gave a half-width of 23.0
frames and a ratio of **1.219**, which passes. Significance: any width,
gap or duration statistic whose result equals one sampling interval is
reporting its own resolution, and the corpus's strided measurements should be
checked for this. MEASURED (M102 S4, `out/s4_realism.json`,
`strided_ratio_superseded`).

**P7.** The M102 simulator produces **7.04×** less competitive-set
disconnectedness than the real `bee-3-cpl` stack under a single shared
operator (0.523% vs 3.684%), because its depth is piecewise constant over
tens of pixels. Significance: the simulator is documented as optimistic for
occlusion, depth-discontinuity and competitive-set topology work — the areas
M87 and M96 occupy — and any milestone using it there must inflate its
expectations accordingly. MEASURED (M102 S4, `out/s4_realism.json`).

**P8.** The simulator's photometric drift agrees with fact 1254's *predicted*
1.1132 by construction, not with the *measured* 1.1091, because it derives
irradiance falloff from 1/m² off the same scale track that generates the
geometric warp. Significance: a photometric correction scored against this
simulator is being scored against the model rather than against the rig, and
M99 in particular must not read agreement here as validation. DERIVED (M102
§6.3; generator prints `photo_first_last` = \[1.0, 0.898344], 1/0.898344 =
1.11316).

**P9.** The M102 simulator models shot and read noise only, with no
fixed-pattern component, yet its measured/predicted noise ratio (1.0638) sits
*above* the real stack's (0.9946) rather than below it, which a missing
ρ = 0.3094 variance component (fact 610) does not explain. The likeliest
reading is that a 9×9-median-residual MAD estimator suppresses spatially
fixed structure on the real stack. Significance: flags both that the
simulator is unusable for FPN-dependent work and that MAD-after-median-filter
noise estimators elsewhere in the corpus may be partly blind to the component
fact 612 showed is decisive. MEASURED for the two ratios, ARGUED for the
explanation (M102 S4, §6.4).

**P10.** A synthetic frame written with a wrong TIFF heap offset decodes withexit 0 and "3 ok, 0 failed" while reporting an active area of
3737911296 × 646971392 and a black level of 0.002674798 — every inline tag
correct, every heap-resident tag garbage. Significance: the decoder's success
return does not imply its metadata is sane, and any milestone that trusts
decode success without asserting on black/white/active-area values is
unguarded against this; it is also the concrete reason an out-of-tree
file-emitting generator tests more than an in-crate array generator.
MEASURED (M102 S1, superseded revision).

**P11.** Scored against a planted breathing warp, the shipped aligner
recovers **96.96%** of the true corner drift (19.2920 of 19.8963 plane px
over 16 frames, `--reference 0`), leaving a **0.6043** plane px systematic
shortfall — **5.87x** its own cycle-consistency floor of 0.103 plane px on
the same run. Significance: the first accuracy-against-truth number for
`align` in this project, and it shows that cycle consistency under-states
real alignment error by roughly six times, so the corpus's internal alignment
figures are not bounds on accuracy. MEASURED (M102 S6,
`out/s6_align_truth.json`; one stack, 16 frames, fact 127's caution
applies).

**P12.** The shipped aligner refuses a 256x256 plane with *"the fine tile grid
does not fit in this plane"*, so any synthetic or cropped stack intended to
exercise `align` must be at least 1024x1024 CFA. Significance: a practical
floor on synthetic-stack size for every future milestone that wants to score
alignment, and the reason M102's round-trip and alignment arms run at
different resolutions. MEASURED (M102 S6, `strehl align` exit 1 at 512x512
CFA / 256x256 plane).
