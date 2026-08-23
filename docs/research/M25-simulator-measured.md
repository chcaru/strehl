# M25 — A calibrated capture simulator, and the evidence for and against it

> **NOT INDEPENDENTLY VERIFIED.** Same author as the code and the
> measurements. Rule 12: everything below is a hypothesis until someone else
> re-runs it. The gates were pre-registered in
> `experiments/m25-simulator/PREREGISTRATION.md`, which was committed before
> any simulated result existed (commit `70a931b`); that file is the contract
> this report is scored against.

Every claim is labelled **MEASURED** (a number this milestone computed from
data), **DERIVED** (a consequence of measured numbers plus stated arithmetic),
or **ARGUED** (a judgement).

---

## 0. The headline, before the detail

**The simulator reproduces the project's noise-and-selection machinery and does
not reproduce its optics or its subjects.** That sentence is the deliverable.

| | verdict |
|---|---|
| Gate 1a — fact 35's φ↔excess mechanism | **PASS, 16/16 configurations** |
| Gate 1b — facts 19/23's levels, pre-registered five axes | **PARTIAL, 3/5** |
| Gate 1b′ — post-hoc axes (c(1), floor, excess over 16 measures) | **PASS 3/3** — declared post-hoc, see §5.3 |
| Gate 1c — M21's occlusion enrichment | **FAIL** (three attempts; two of the three failures were mine, the third is the simulator's) |
| Gate 2 — negative control on the simulator | **FIRED on 3 of 4** mis-specifications; **blind to dropping diffraction entirely** |

**ARGUED.** Use it for anything about noise, selection, argmax bias,
regularisation and confidence. Do **not** yet use it to score deconvolution,
PSF estimation, or occlusion reconstruction — those depend on exactly the axes
Gate 2 showed the validation is blind to and Gate 1c showed do not match.

---

## 1. What was built

`experiments/m25-simulator/src/strehl_sim/` — a Python package (numpy/scipy;
Rust is off-limits to this milestone, `crates/**` belongs to M18).

```
config.py    rig constants: sensor, optics, breathing, per-stack capture
optics.py    diffraction OTF, defocus OTF, their composition, pixel aperture
scene.py     latent scenes: flat / tilted plane / terrace / two-layer occlusion
sensor.py    electrons -> DN: shot, read, DSNU, hot pixels, black, white, clip
render.py    the forward model
focus.py     a validated port of the m9-support focus/merge harness
stackio.py   loading real stacks; ROI/tile extraction; a rawpy-compatible shim
build.py     fitting scene nuisance parameters from a real ROI
```

### 1.1 The forward model, written out

For frame `k`, latent scene layers `l` ordered far → near, each with radiance
`R_l` (electrons), alpha `A_l`, and focus map `F_l` (in units of frame index),
on a grid `S` times finer than the sensor:

1. **Geometry.** `R_l, A_l, F_l ← W_k[·]`, where `W_k` is the 4-parameter
   similarity `x ↦ c + s_k (x − c)`, `s_k` the per-frame scale, `c` the scale
   centre. Cubic spline, inverse mapping. Rotation and translation are
   supported and default to zero (fact 17: rotation is unmeasurable on this
   corpus).
2. **Per-layer blur.** For each layer, the defocus diameter is
   `d = |F_l − k| · coc_px_per_frame` and the PSF is
   `PSF_k,l = defocus(d) ⊛ diffraction(N_eff, λ)`, composed as a product of
   OTFs. Where `F_l` varies spatially the layer is split into `depth_bands`
   bands, each blurred with its own PSF and recombined by its band weight.
3. **Composite — blur first, composite second.**
   `acc ← C_l + (1 − A_l^blur)·acc` accumulating far → near, where
   `C_l = (A_l R_l) ⊛ PSF_k,l` and `A_l^blur = A_l ⊛ PSF_k,l`.
   This is the premultiplied form of
   `I_k = α_k·(F ⊛ PSF_k^F) + (1−α_k)·(B ⊛ PSF_k^B)` with α itself blurred.
   **Each layer is blurred by its own depth's PSF before any compositing
   happens, and the alpha is blurred with it.** Blurring a composited image is
   the wrong order and destroys veiling; `scene.flatten_scene` implements that
   wrong order deliberately, as a negative control, and nothing in the forward
   model calls it.
4. **Photometric gain.** `× g_k`, default 1.0, injectable per frame (fact 180:
   real drift is 0.91 %–11.70 % peak-to-peak and EXIF does not predict it).
5. **Sampling.** Integrate each `S×S` latent block (the pixel aperture), then
   select **one** colour per photosite in RGGB `[[0,1],[3,2]]`. Aperture
   integration happens **before** colour selection, because a photosite
   integrates all the light falling on it and only then reports one channel.
   Rendering RGB and mosaicking afterwards gives the same answer here only
   because the aperture is channel-independent; doing it in this order makes
   that assumption visible instead of implicit.
6. **Noise, in electrons.** `Poisson(S_e)` + `Normal(0, RN_e)`, then
   `DN = e⁻ · g` with `g = ISO/436.8`, plus DSNU (row/column/pixel), plus the
   hot-pixel population, plus black 512, rounded, clipped to `[0, 15360]`.
7. **Truth.** Every stack carries `L`, `Z`, per-frame `z_k`, `s_k`, `g_k`, the
   visible focus map, the front alpha, and the per-pixel index of the
   truly-best-focused frame.

### 1.2 Self-tests — 27 assertions, `data/selftest.txt`

**MEASURED.** All 27 pass. The ones that matter:

* `N_eff = f/33.0` at marked f/11, m = 2.0, p = 1.0 (fact 27's bellows range).
* Diffraction cutoff **0.2821** cyc/px against M5's measured knee **0.2762**.
* Cutoff reaches Nyquist at `N_eff = f/18.62`; M5 measured f/18.6.
* Synthesised noise σ matches `σ²(S) = g·S + (RN_e·g)²` to **≤0.2 %** at three
  levels × two ISOs.
* Hot pixels **0.0346 %** of the plane, excess **across the flagged pixels**
  mean **+3.0 DN**, median **0.0 DN** (M22).
* Group D: a pixel behind the occluding edge reads **1296.8 DN**, strictly
  between background 736.0 and foreground 2909.0 — i.e. veiled, not selected.
* Group D: blur-then-composite differs from composite-then-blur by **5.2 % of
  level in a 48 px band** at the edge. The distinction is not academic.

### 1.3 The port check — the prerequisite, not a gate

**MEASURED**, `data/port-check-109MSDCF.txt`. The Python port of `m9-support`
reproduces that milestone's committed numbers on the **real** 109MSDCF stack:
max |Δφ| **0.000006**, max |Δc(1)| **0.000049**, max |Δfloor| **0.000046**,
ρ(φ, excess) **+0.917** and ρ(support, excess) **−0.207**, both exactly as
committed. Every Gate 1a/1b number below is produced by this code, so the
comparison is like-for-like rather than a re-derivation.

---

## 2. What is fitted and what is tested

This is the whole question for a simulator, so it is stated before any result.

| fitted from real data | how | why it is not a physics claim |
|---|---|---|
| mean green level (e⁻) | mean of the real ROI | subject radiometry |
| texture contrast (e⁻ sd) | ROI sd minus modelled noise variance, then one noise-free render to undo the optical attenuation | subject statistics |
| spectral slope β | log-log fit of the ROI power spectrum over 0.02–0.20 cyc/green-px | subject statistics |
| scene placement (which frame the plane is sharpest on) | measured from the real stack — see §5.2 | scene geometry, not rig physics |
| per-frame gain series | measured per-frame level of the real ROI | fact 180 |
| **radial power spectrum profile (Gate 1c only)** | 64-bin measured profile — a substantial widening, declared in §4.3 | subject statistics |

`coc_px_per_frame` is **swept, not fitted** in Gate 1a and Gate 2, and is the
single free parameter in Gate 1b. Everything the gates score — the φ↔excess
coupling, the zero-centre-tap null, the noise-versus-width curve, the plain
mean, the placebo, the regularised speckle, the occlusion enrichment — is left
free.

---

## 3. The pre-registered gates

Reproduced from `PREREGISTRATION.md` in summary; that file is authoritative.

* **Gate 1a.** ρ(φ, excess) ≥ +0.70 at p < 0.05 at **every** swept `coc`, and
  `tenengrad-w0` excess < 0.02 → PASS. ρ(support, excess) significant with
  |ρ| > 0.5 → FAIL in the other direction.
* **Gate 1b.** One `coc` reproducing all five of argmax c(1), plain-mean ratio,
  placebo ratio, width-17 ratio and width-17 speckle, each within ±0.05 in
  ratio (speckle ±2 points at width 17) → PASS; ≥3 of 5 → PARTIAL.
* **Gate 1c.** M21's committed `03-permutation-placebo.py`, run byte-identical
  through a `rawpy` shim: enrichment ≥ 2.0× with placebo 1.00 ± 0.15 → PASS;
  enrichment < 1.3× → FAIL.
* **Gate 2.** Mis-specify the physics; if a mis-specification passes every
  gate, "that gate is not a gate, and this must be reported as the headline
  result, not buried".
* **Gate 3.** The failure-axis list.

### 3.1 Deviations from the pre-registration, declared

1. **Gate 1a swept 15 regulariser widths, not 19.** Truncating at width 97
   moves m9's own committed pooled floor by at most **0.006962** — checked
   against the real CSV before the change, and an order of magnitude below the
   ±0.05 tolerance.
2. **Gate 2 ran four mis-specifications, not two.** NC-C (correlated noise) and
   NC-D (no noise) were added *after* NC-B failed to fire, to establish whether
   the gates have teeth at all. This is a strengthening of the control, not a
   weakening, but it is post-hoc and is labelled as such.
3. **Gate 1c attempt 3 fits a 64-bin subject spectrum**, a much wider nuisance
   fit than the pre-registered single β. Declared in §4.3.

### 3.2 The pre-registered predictions, scored

The pre-registration recorded an expected value for each gate before running
(discipline 142). Scoring them is the cheapest available check on whether this
milestone's intuitions are calibrated.

| prediction | outcome |
|---|---|
| Gate 1a: "ρ ≈ +0.9 … PASS at low `coc` and possible decay at high `coc`" | **Right on the value** (+0.894…+0.976); **wrong on the decay** — ρ is if anything slightly *higher* at coc 2.0 |
| Gate 1b: "**I expect this [mean] axis to miss** and I am saying so before running it" | **Right.** It missed, by +0.066 |
| Gate 1c: "I expect enrichment to exceed the real 4.38× rather than fall short" | **Wrong, and badly** — 0.77×. The reasoning ("the plant's edge is cleaner than any real one") was sound and irrelevant; the binding constraint was the subject's spectrum, which I had not thought about |
| Gate 2: "I am less confident about diffraction … If it does not [fire], that is a finding about which physics the gates are actually sensitive to, and I will report it as such rather than replacing the control with one that fires" | **Right about the risk**, and the commitment was honoured — §4.4 |

---

## 4. Results

### 4.1 Gate 1a — **PASS**, 16 of 16 configurations

**MEASURED**, `data/gate1a-phi.txt`. Two scenes (fronto-parallel plane, plane
tilted across 6 frames of depth) × `coc ∈ {0.25, 0.5, 1.0, 2.0}` px/frame ×
2 seeds. The full 16-treatment crossed design, the 15 regulariser widths, and
the same φ probe as `m9-support`.

| | real (m9, 109MSDCF) | simulated range, 16 configs |
|---|---|---|
| ρ(φ, excess) | **+0.918 / +0.894** | **+0.894 … +0.976**, p < 0.0001 everywhere |
| ρ(support, excess) | −0.170 / −0.243, p = 0.53 / 0.37 | **−0.231 … −0.298**, p = 0.26 … 0.39, **never significant** |
| `tenengrad-w0` c(1) (zero centre tap) | **0.9952** | 0.949 … 0.999 |
| `tenengrad-w0` excess | **0.0000** | **0.0000 in all 16** |

**ARGUED, and this is the strongest single piece of evidence in the
milestone.** Nothing in the simulator knows what φ is. φ is a property of the
focus operator's sensitivity kernel, measured afterwards by the same probe m9
used. The simulator was given a sensor noise model, an optical model and a
textured plane; the ordering of sixteen focus operators by their noise excess
then reproduced the ordering by their centre-tap sensitivity fraction, at
ρ ≈ +0.9, across two scenes, four defocus rates and two seeds — and the
operator with a mathematically zero centre tap showed **exactly zero** excess
in every one. Fact 35's mechanism — *a pixel's own noise votes for its own
selection* — falls out of the physics.

The support-radius null also reproduces: negative, small, never significant,
which is what makes this a discriminating test rather than a "the sim is
noisy, the real thing is noisy" observation.

### 4.2 Gate 1b — **PARTIAL, 3 of 5**

**MEASURED**, `data/gate1b-prereg-rerun.txt`. m9's ROI `2272,1344` (fact 19's
and fact 23's ROI), targets from m9's own committed CSV where it has the
number and M2's where it does not, `coc` swept over {0.5, 1.0, 1.5, 2.0, 3.0}.

| axis | target | source | best simulated | Δ | |
|---|---:|---|---:|---:|---|
| argmax c(1) | 1.2527 | m9 CSV, this ROI | 1.2016 (coc 0.5) | −0.051 | **MISS** |
| plain mean | 0.534 | fact 19 (M2 harness) | 0.6002 (coc 3.0) | +0.066 | **MISS** |
| placebo | 0.981 | fact 19 (M2 harness) | 0.9795 (coc 2.0) | −0.002 | ok |
| width-17 ratio | 1.0737 | m9 CSV, this ROI | 1.0475 (coc 0.5) | −0.026 | ok |
| width-17 speckle | 0.829 pp | m9 CSV, this ROI | 0.612 pp (coc 3.0) | −0.217 | ok |

No single `coc` satisfies all five; the best is 3 of 5 at coc 2.0.

**The two misses pull in opposite directions and that is the finding.**
DERIVED: argmax c(1) is best at the *smallest* defocus rate and the plain mean
at the *largest*, so no defocus rate can satisfy both. One of the two is
mis-modelled. The pre-registration named the mean in advance — *"I expect this
axis to miss and I am saying so before running it"* — because 0.534× requires
the drift and the defocus rate to be simultaneously right and 109MSDCF's own
drift is unpublished.

**MEASURED, and this decomposition is the useful part.** At coc 0.5 the
argmax ratio splits as:

| | c(1) | floor | excess = c(1) − floor |
|---|---:|---:|---:|
| real, ROI 2272,1344 | 1.2527 | **1.0735** | **0.1793** |
| simulated, coc 0.5 | 1.2016 | **1.0235** | **0.1781** |

The *noise-coupled selection* term — the thing fact 35 is about — matches to
**0.7 %**. The entire c(1) shortfall is the **floor**, which is 0.050 low.
DERIVED: the floor is what a fully regularised merge converges to, i.e. the
variance the merge cannot remove no matter how much the selection is smoothed.
The simulator is missing a source of real merged-image variance. ARGUED: PRNU
is the leading suspect and is **unmeasured** — the flat-field capture has not
happened (`docs/captures-needed.md`).

### 4.3 Gate 1c — **FAIL**, and the third attempt is the informative one

Three attempts. The first two failures were mine; the third is the
simulator's. All three are reported because the diagnosis is the value.

**Attempt 1** (`04-gate1c-occlusion.py`) — enrichment **0.98×**, 81.4 % of
pixels multi-peaked. I read this as a failure. It is not: M21's own committed
table reports **109MSDCF at 60.7 % multi-peak and 0.87× enrichment**, and says
the detector is noise-saturated there. I had rendered 109MSDCF's flat-ROI
radiometry (1.4 % contrast, structure:noise ≈ 1:1) and compared it against
**4.38×**, a number that exists only on `coffee-bean`. **The simulator had
reproduced the saturated regime correctly and I scored it against the wrong
regime.**

**Attempt 2** (`07-gate1c-coffee.py`) — re-run at `coffee-bean`'s **measured**
conditions: ISO 50, mean 1528 DN, sd 616 DN (40.3 % contrast), modelled noise
9.36 DN → **66:1** structure:noise, β 3.454, focus peak frame 5 of 21, level
peak-to-peak 17.95 %. M21's script run byte-identical via `runpy` through a
`rawpy`/`glob` shim, with the `coffee-bean` slot served 105 paths so that
M21's `[::5]` reads exactly 21 distinct rendered frames.

**MEASURED**, `data/gate1c-coffee.txt`:

| cell | overall multi-peak | enrichment | permuted |
|---|---:|---:|---:|
| occlusion — depth step **with** alpha edge (the test) | 28.5 % | **0.77×** | 0.99 |
| terrace — same depth step, **no** alpha edge | 46.1 % | 1.05× | 1.03 |
| tilt — depth variation, **no** step | 38.0 % | 0.95× | 1.00 |
| *real* `coffee-bean` (M21) | 4.8 % | **4.38×** | 1.01 |

The placebo behaves perfectly (0.99–1.03), so the harness is being driven
correctly. The overall multi-peak fraction is **28.5 % against a real 4.8 %**:
the detector is drowning in the simulated stack and cannot see the edge.

**The diagnosis, MEASURED** (`10-spectrum-check.py`, `data/spectrum-check.txt`).
Radially averaged power of the green plane, simulated ÷ real, same total sd:

| band (cyc/green-px) | 109MSDCF flat ROI | coffee-bean crop |
|---|---:|---:|
| 0.02–0.05 | 1.09 | **6.21** |
| 0.05–0.10 | 1.12 | **6.26** |
| 0.10–0.20 | 1.02 | **5.93** |
| 0.20–0.30 | 0.85 | 1.13 |
| 0.30–0.40 | 0.91 | **0.49** |
| 0.40–0.50 | 0.97 | **0.43** |
| slope, 0.02–0.20 | real +1.75, sim +1.90 | real +3.70, sim +4.11 |
| slope, 0.20–0.45 | real +0.77, sim +0.56 | real **+0.16**, sim **+1.99** |

**Gate 1a/1b's regime matches to within 15 % in every band. Gate 1c's does
not.** DERIVED: a real subject is not a single power law. `coffee-bean`'s green
plane falls at `f^-3.70` below 0.2 cyc/px and is nearly **flat** (`f^-0.16`)
above it — an organic subject has abundant detail right up to Nyquist. Fitting
one slope on the low band and pushing it through an optical chain that reddens
it again starves the fine scales by **2×** in power. The R = 2 multi-peak
detector works at exactly those fine scales, so it sees mostly noise.

**Attempt 3** (`12-gate1c-shaped.py`) — replace the single slope with a
**measured 64-bin radial amplitude profile** (`scene.shaped_texture`,
`build.calibrate_psd`), iterated against a noise-free render until the
delivered spectrum matches. **MEASURED** (`data/psd-shaping-check.txt`): the
worst band error falls from **8.99× to 1.51×**, and the shaping iteration
converges (median |log ratio| 1.10 → 0.054 → 0.051 → 0.050).

**DECLARED, because it weakens the gate.** This widens the fitted nuisance set
from one number to roughly sixty numbers of the subject's second-order
statistics. It is still not circular *for this gate*: a radial power spectrum
is stationary and isotropic and carries no information whatsoever about which
pixels sit at a depth discontinuity, which is the only thing the enrichment
ratio scores. But it is a much larger fit and the report should not pretend
otherwise.

**MEASURED**, `data/gate1c-shaped.txt`, with the calibration run **before** the
`coc` fit (the fit's through-focus curve depends on which frequencies the
subject has):

| cell | overall multi-peak | enrichment | permuted |
|---|---:|---:|---:|
| occlusion (test) | 28.5 % → **17.4 %** | 0.77× → **1.03×** | 0.98 |
| terrace | 46.1 % → **21.8 %** | 1.05× → **1.30×** | 1.05 |
| tilt | 38.0 % → **15.2 %** | 0.95× → **0.96×** | 1.00 |
| *real* `coffee-bean` | 4.8 % | 4.38× | 1.01 |

**Large improvement, still a FAIL.** The overall multi-peak fraction fell by
39 % and the enrichment moved in the right direction, so the diagnosis was
correct and incomplete. Under the pre-registered grid, enrichment 1.03× with a
correct placebo is below the 1.3× FAIL threshold: **FAIL**.

<!--GATE1C3-->

#### The remaining cause, isolated

Two candidates remained, with opposite implications: (a) the veiling physics is
not reproduced, or (b) the *fitted defocus rate* is wrong. The fit ran to the
grid edge at **12.0 px/frame**; with the occluder at focus index 4 and the
background at 16 that is a **144 px** blur across the edge — far wider than
both the R = 2 bimodality scale and the R = 13 depth-step scale M21 uses. A
correct two-depth signature would then be smeared out of the detector's reach
and the physics would never get a chance to show.

`13-coc-probe.py` varies **only** `coc_px_per_frame`, serving the *same*
occlusion scene into all three of M21's slots at 1.0, 3.0 and 12.0 px/frame.
**MEASURED**, `data/coc-probe.txt`:

| coc px/frame | edge blur | overall multi-peak | enrichment | placebo |
|---:|---:|---:|---:|---:|
| 1.0 | 12 px | **6.6 %** | 1.03× | 0.99 |
| 3.0 | 36 px | **5.9 %** | 0.92× | 1.01 |
| 12.0 | 144 px | 17.4 % | 1.03× | 0.98 |
| *real* `coffee-bean` | — | **4.8 %** | **4.38×** | 1.01 |

**Two findings, and they point in opposite directions.**

**(i) The base rate now matches.** At coc 1.0 the simulator produces **6.6 %**
overall multi-peakedness against the real **4.8 %** — after the subject-spectrum
fix, the detector operates in the same regime on simulated data as on real. It
was 81.4 % in attempt 1 and 28.5 % in attempt 2. The saturation problem is
solved.

**(ii) The enrichment does not, and the defocus rate is not why.** Across a
**12× range** of defocus rate — a 12 px edge blur to a 144 px one — enrichment
is **flat at 1.03×, 0.92×, 1.03×**. Cause (b) is eliminated by measurement.

#### Ground truth, used for the first time in this project

M21 cannot know which *real* pixels sit at a depth discontinuity, so it
estimates them from the R = 13 argmax, median-filtered 5×5. The simulator
knows. `14-stepmap-truth.py` asks the two questions the real corpus cannot
answer. **MEASURED**, `data/stepmap-truth.txt`:

| | coc 1.0 | coc 3.0 |
|---|---:|---:|
| pixels M21's estimator flags as a depth step | 227,995 | 139,411 |
| pixels that **truly** sit at a depth step | 39,854 | 39,927 |
| over-flagging factor | **5.72×** | **3.49×** |
| precision | **1.8 %** | **3.4 %** |
| recall | **10.5 %** | **11.9 %** |
| enrichment with M21's **estimated** step map | 1.03× | 0.92× |
| enrichment with the **true** step map | **0.24×** | **0.30×** |
| enrichment on **truly veiled** (0.02 < α < 0.98) pixels | **0.24×** | **0.28×** |

**Two separate results, and the second is the bad one.**

**MEASURED.** On this plant M21's step-map estimator has **1.8–3.4 %
precision** and **10.5–11.9 % recall** against ground truth. It over-flags by
3.5–5.7×. That is a real and previously unknowable property of the detector,
and it is the kind of thing this milestone was built to find.

**MEASURED, and it is the milestone's most uncomfortable number.** With a
*perfect* depth-step map, the truly-veiled pixels of the simulated scene are
multi-peaked at **1.6 %** against **6.8 %** on smooth depth — an enrichment of
**0.24×**. The effect does not merely have the wrong magnitude; **it has the
wrong sign.**

<!--LUMSTEP-->

### 4.4 Gate 2 — the negative control **fired on 3 of 4**, and the one it
missed is the important one

**MEASURED**, `data/gate2-negative-control.txt`. Four mis-specifications, each
**re-calibrated so the rendered ROI's mean and sd still match the real ROI's** —
the hard version of the control: wrong physics tuned to look right on the
summary statistics. Scored on three axes: ρ(φ, excess) ≥ 0.70 at p < 0.05;
`tenengrad-w0` excess < 0.02; median |excess_sim − excess_real| over the 16
measures ≤ 0.05.

| variant | ρ(φ,excess) | zero-tap excess | excess MAD | excess slope | fired? |
|---|---:|---:|---:|---:|---|
| baseline | +0.931 | 0.0000 | 0.0104 | 1.015 | no (correct) |
| **NC-A** `g` doubled | +0.976 | 0.0000 | **0.0903** | **1.524** | **YES** |
| **NC-B** no diffraction | +0.959 | 0.0000 | 0.0214 | 0.986 | **no — blind spot** |
| **NC-C** correlated noise | +0.920 | 0.0000 | **0.0602** | **0.766** | **YES** |
| **NC-D** no noise | **+0.516** | 0.0000 | **0.1366** | **0.016** | **YES** |

* **NC-A.** The gain is mis-stated by 2× and the electron budget re-derived
  from the mis-stated gain — the error a mis-calibrated `g` actually causes:
  you believe you have half the electrons you have, so you model √2 too much
  shot noise. Excess inflates by **52 %**. Fired.
* **NC-C.** The *same* per-pixel noise variance, passed through a 3×3 binomial
  within each Bayer parity plane — right amount of noise, wrong independence
  structure. Excess **falls 23 %**. DERIVED: this is a second, independent
  confirmation of fact 35's mechanism. If the excess came from anything other
  than each pixel's own independent noise voting for its own selection,
  spatially smearing the noise while preserving its variance would not have
  moved it.
* **NC-D.** With no noise at all, excess collapses to a slope of **0.016** and
  the φ coupling falls below threshold. The gate's floor behaves.
* **NC-B — the blind spot, reported as the headline the pre-registration
  demanded.** Dropping diffraction entirely does **not** move Gate 1's
  statistics.

**Is NC-B blind because the knob does nothing?** No — that was checked
(`09-diffraction-effect.py`, `data/diffraction-effect.txt`). **MEASURED**, on
identical latent scenes with no contrast re-calibration:

| | with diffraction | without |
|---|---:|---:|
| in-focus green structure sd | 20.81 DN | 28.44 DN (**1.37×**) |
| power ratio at 0.295 cyc/green-px | — | **7.9×** |
| power ratio at 0.455 cyc/green-px | — | **123×** |
| amplitude ratio over 0.30–0.48 cyc/px | — | **4.52×** |

The rendered image changes enormously. **Gate 1 is simply insensitive to it.**

**ARGUED, and it is the most important sentence in this report:** Gate 1 is a
test of the *noise and selection* machinery. It is **not** evidence that the
optics are right. Any future use of this simulator that depends on the PSF —
deconvolution scoring, EDoF, PSF estimation, MTF claims — is **unvalidated** by
the work in this milestone and needs its own gate.

---

## 5. What I got wrong, and how I found it

Documented in full, because on this project the author's errors have repeatedly
been the most reusable output.

### 5.1 The reference-frame leak — a plant that could not express its own quantity

The first Gate 1b run placed the simulated plane's best focus on **frame 11** —
the exact frame the m9 harness divides by. The winner then *is* the reference
frame, so the ratio floors at **1.000 by construction** and no `coc` could ever
reach the real floor of 1.0646. All five axes were individually reachable and
**zero** configurations satisfied them jointly (`data/gate1b-levels.txt`).

Found by measuring the real stack instead of assuming. **MEASURED:** on
109MSDCF's four m9 flat ROIs the `ring-1-3` focus response peaks at frames
**10, 10, 10 and 7** — *never* at frame 11 — and sd@peak exceeds sd@ref by
**2 %–12.6 %**, which accounts for the real floor almost exactly.

This is discipline 24 territory: a plant that coincides with the harness's own
reference cannot express the quantity being measured. It is subtler than the
usual version because nothing was leaked *into* the plant; the plant was
merely placed where the measurement has a fixed point.

### 5.2 Comparing across regimes — §4.3, attempt 1

rendering one stack's radiometry and scoring it against another stack's
published number. The simulator was right and I was wrong, and I nearly filed
it as a simulator failure. The corpus is not homogeneous: 1.4 % contrast versus
40.3 %, structure-to-noise ≈ 0.9:1 versus 66:1, multi-peak 60.7 % versus 4.8 %.

### 5.3 Changing the gate after seeing the data

After diagnosing §5.1 I wrote a *different* Gate 1b — c(1), floor and excess
across all 16 measures, pooled over four ROIs — and it **passed 3/3**
(`data/gate1b-measured-placement.txt`): excess sim-vs-real Pearson
**r = +0.992**, Spearman **ρ = +0.977**, **slope 1.005**, median |Δexcess|
**0.0148**.

That is a real and informative result, and it is **not** the pre-registered
gate. Choosing the scoring axes after seeing which ones failed is precisely
what pre-registration exists to prevent. So the pre-registered five axes were
re-run with only the placement bug fixed (§4.2) and **that** — PARTIAL, 3/5 —
is what Gate 1b scores. The post-hoc version is reported as **Gate 1b′** and
labelled post-hoc everywhere it appears.

### 5.4 The four-ROI pooling trap

m9's S8 table pools four ROIs; its φ table (`sensitivity-109MSDCF.csv`) uses
only `2272,1344`. Mixing the two scopes makes a *correct* port look 0.5–5 %
wrong. Cost: one debugging session before the port check went green.

### 5.5 The hot-pixel mean

M22's "+3.0 DN mean" is the excess **across the flagged pixels**, not
sensor-wide. Implementing it sensor-wide would have injected **~2,900×** too
much added energy. Caught by the self-test that reproduces both the mean and
the median.

### 5.6 A calibration probe below the quantisation floor

`calibrate_psd`'s first version rendered its noise-free probe with a contrast
of **1 electron** — about 0.11 DN, far below the integer DN rounding in
`expose`. The probe measured quantisation noise, the iteration diverged
(mismatch 4.45 → 4.93 → 5.71), and the "fix" made the spectrum **worse**
(worst band error 8.99× → 35.9×). Found by noticing that the delivered power
was flat at exactly the modelled noise floor in every band. Passing the real
fitted contrast converged it in two iterations.

### 5.7 A super-Nyquist tail that ate the whole variance

The shaped texture initially extrapolated the measured profile *flat* above the
green Nyquist. At S = 2 that region is ~97 % of the latent Fourier plane by
area, so unit-sd normalisation spent nearly all the variance on content the
sensor cannot represent, and the delivered structure collapsed to the noise
floor. Now set to zero, with the cost — under-modelled aliasing — stated.

---

## 6. Gate 3 — the failure axes

Ordered by how much they matter for the intended uses. **ARGUED** throughout
except where a measurement is cited.

### 6.1 Load-bearing — fix or avoid before relying on the simulator

| axis | evidence | why it matters |
|---|---|---|
| **The optics are unvalidated.** | Gate 2 NC-B: removing diffraction entirely changes high-frequency power by 4.5× in amplitude and passes every gate. | Any deconvolution, EDoF or PSF claim scored on this simulator is scored by a suite proven blind to the PSF. |
| **Subject spatial statistics.** | §4.3: a single power law over-produces low-frequency power 6× and starves 0.3–0.5 cyc/px by 2× on a real organic subject. | This is what broke Gate 1c. Shaping helps (worst band 8.99× → 1.51×) but is a 64-parameter fit of the real subject. |
| **The merged-noise floor is ~0.03–0.05 low.** | §4.2 and `data/gate1b-measured-placement.txt` (median |Δfloor| 0.0324, max 0.0515, systematically low). | The floor *is* the estimator's target. Under-modelling it makes every merge look better in simulation than in reality. |
| **PRNU is not modelled at all** — because it is unmeasured. | No flat-field capture exists. | Leading suspect for the floor deficit. Cannot be modelled honestly until measured. |
| **Speckle runs high.** | `ring-1-3` 50.25 % vs 38.15 %; `ring-4-12` 27.7 % vs 10.9 %; `tenengrad-w0` 54.8 % vs 44.7 %. | Regulariser-sizing work would be tuned against a pessimistic winner map. |

### 6.2 Real, bounded, quantified

| axis | measured size |
|---|---|
| Wide-support excess deficit | `ring-4-12` excess 0.022 vs 0.115; `ring-2-6` 0.081 vs 0.186 |
| Read noise at ISO 50 | fact 14's model gives 0.541 DN against M4's measured 0.987 DN — **45 % low**. Affects `coffee-bean` and `119MSDCF`. At ISO 160 it is accurate to 2.6 % and shot variance exceeds read variance **233:1** in the flat ROI, so Gates 1a/1b/2 are unaffected. |
| Cubic resampling is not neutral | round-trip RMS 0.00918 of unit contrast (discipline 11) |
| Pixel aperture at S = 2 | MTF error at 0.25 cyc/px rises from 0.65 % to ~2.6 % |
| Drift is smooth in frame index | fact 1 says explicitly it is *not* a low-order polynomial; the generator's default is a constant rate and is labelled a **generator convenience, not a model**. Gates that need real drift are given the measured per-frame series. |
| Through-focus curve shape | on `coffee-bean` the fitted `coc` runs to the grid edge (12.0 px/frame) with RMS shape error 0.17–0.19; the real curve is asymmetric and falls faster than any simulated one |
| DSNU row/column/pixel split | M4 publishes a scalar; the ⅓/⅓/⅓ split is **ARGUED**, not measured |

### 6.3 Not modelled at all

Lens aberrations beyond diffraction (coma, astigmatism, spherical, field
curvature); chromatic aberration, both lateral and longitudinal; PRNU; dust;
lens distortion; sensor crosstalk and micro-lens effects; subject motion;
within-layer self-occlusion (a layer's own depth variation cannot occlude
itself — only inter-layer occlusion is modelled); aliasing of super-Nyquist
subject detail in the shaped-texture path; non-Gaussian read-noise tails; the
real texture statistics of insects and organic subjects beyond a second-order
radial spectrum.

**ARGUED, per axis, for the intended uses:** chromatic aberration matters for
demosaic and colour work and not for green-plane noise work. Distortion matters
for registration validation and is currently absent, so the simulator cannot
be used to score a registration algorithm's robustness to distortion. Subject
motion is the reason `foam` is unusable and should be added before any claim
about robustness to it. Within-layer self-occlusion means a *tilted* surface
near grazing incidence is wrong; a two-layer scene is right.

---

## 7. Proposed facts (190+)

**190. MEASURED.** A forward simulator built from the project's own calibrated
constants reproduces fact 35's mechanism from first principles: across 16
configurations (2 scenes × 4 defocus rates × 2 seeds), ρ(φ, excess) is
**+0.894 … +0.976** (p < 0.0001 everywhere) against the real **+0.918/+0.894**;
ρ(support, excess) is **−0.231 … −0.298** and **never significant**, against
the real −0.170/−0.243; and a zero-centre-tap operator shows **exactly zero**
excess in every configuration. Nothing about φ is built into the simulator.

**191. MEASURED.** On m9's ROI `2272,1344` the real argmax ratio decomposes as
c(1) 1.2527 = floor 1.0735 + excess 0.1793; the simulator at `coc` 0.5 gives
1.2016 = 1.0235 + **0.1781**. The noise-coupled selection term matches to
**0.7 %** and the entire shortfall is the floor, **0.050 low**.

**192. MEASURED.** The simulated merged-noise **floor** is systematically
0.03–0.05 ratio units below the real floor across all 16 focus measures
(median |Δ| 0.0324, max 0.0515), while simulated **excess** tracks real excess
at Pearson r = **+0.992**, slope **1.005**. The unexplained variance is in what
the merge *cannot* remove, not in what selection *adds*.

**193. MEASURED.** No single defocus rate reproduces both fact 19's argmax
ratio (best at coc 0.5) and fact 19's plain-mean ratio (best at coc 3.0);
the pre-registered five-axis test reaches 3 of 5.

**194. MEASURED.** A validation suite built on the m9 focus-merge statistics
fires on a 2× gain mis-specification (excess slope 1.52), on spatially
correlated noise of the correct variance (0.77), and on no noise at all (0.02)
— but is **blind to removing the diffraction PSF entirely**, which changes
green-plane power at 0.455 cyc/px by **123×** and in-focus structure sd by
**1.37×**. Focus-merge noise statistics are not evidence about the PSF.

**195. MEASURED.** Replacing per-pixel independent noise with 3×3-binomial
correlated noise of identical per-pixel variance *reduces* argmax noise excess
by 23 %. Independent confirmation of fact 35's mechanism by a route that does
not involve φ.

**196. MEASURED.** The green plane of `coffee-bean` at M21's crop is not a
single power law: it falls at `f^-3.70` over 0.02–0.20 cyc/green-px and at
`f^-0.16` over 0.20–0.45. Synthetic `f^-β` texture fitted on the low band
over-produces 0.02–0.20 power by **6×** and under-produces 0.30–0.50 by
**2.3×**.

**197. MEASURED.** On 109MSDCF's four m9 flat ROIs the `ring-1-3` focus
response peaks at frames **10, 10, 10 and 7** of 22 — never at the harness's
own reference frame 11 — and sd@peak exceeds sd@ref by 2 %–12.6 %.

**198. MEASURED.** With `coffee-bean`'s measured radiometry and a two-layer
occlusion scene with a genuine alpha boundary, M21's committed detector run
byte-identical reports 28.5 % overall multi-peak against the real 4.8 %, and
enrichment 0.77× against the real 4.38×; the permutation placebo is correct at
0.99. The detector saturates on synthetic texture before it can see the edge.

**199. MEASURED.** Blur-then-composite and composite-then-blur differ by
**5.2 % of level in a 48 px band** at an occluding edge under this rig's
parameters. The ordering is not a refinement.

**200. MEASURED.** Fact 14's two-level read noise under-predicts M4's measured
dark σ_temporal at ISO 50 by **45 %** (0.541 DN vs 0.987 DN) while being within
20 % at ISO 100–2000 and within 2.6 % at ISO 160.

---

## 8. Proposed discipline items (100+)

**100.** A synthetic plant must not be placed at a fixed point of the harness
measuring it. Placing a plane's best focus on the frame the harness divides by
pins the merged/single ratio at 1.000 by construction. Extends discipline 24:
the leak need not be *into* the plant.

**101.** Before comparing a simulated statistic against a committed number,
check which stack the number was measured on and reproduce that stack's
*regime* — contrast, ISO, structure:noise — not just its harness. Across this
corpus the same detector reads 4.8 % and 60.7 % on two real stacks.

**102.** If the gates are changed after seeing which axis failed, the original
gate must still be run and reported. Report the post-hoc version separately and
label it post-hoc wherever it appears.

**103.** A negative control on a simulator must mis-specify the physics **and
then re-calibrate the summary statistics back onto the real values**. A
mis-specification that changes the mean or sd is caught trivially and proves
nothing.

**104.** When a negative control does *not* fire, determine whether the knob is
a no-op before concluding the gate is insensitive. The two have opposite
implications and the check is one render.

**105.** A calibration probe rendered below the quantisation floor measures
rounding, not signal. Any noise-free probe must be rendered at a realistic
contrast.

**106.** Fitting a subject's second-order statistics on a sub-band and
extrapolating is not conservative: an optical chain reddens the spectrum again,
so the delivered fine-scale content is starved twice.

**107.** State the fitted-versus-tested split as a table before presenting any
simulated result, and state the *count* of fitted numbers. "β" and "a 64-bin
radial profile" are different claims about how much of reality was assumed.

---

## 9. Open questions (30+)

**30.** What accounts for the 0.03–0.05 merged-noise floor deficit? PRNU is the
leading suspect and is unmeasured. A flat-field capture would settle it and is
already on `docs/captures-needed.md`.

**31.** Would a real-texture latent scene — a high-resolution photograph of an
organic subject used as `L` — close the Gate 1c gap? The simulator supports it;
the corpus does not yet contain a suitable high-magnification flat capture.

**32.** What gate would be sensitive to the PSF? Candidates: through-focus MTF
against M5's measured aperture sweep; the through-focus curve *shape* (real
curves are asymmetric and fall faster than any simulated one at `coffee-bean`);
edge-spread reconstruction against a real razor edge.

**33.** Why does the fitted `coc_px_per_frame` run to the grid edge on
`coffee-bean` (12.0 px/frame, RMS shape error 0.17) but sit comfortably at 1.5
on 109MSDCF? Is the real defocus growth non-linear in frame index, or is the
subject's depth range doing the work?

**34.** Does the excess deficit at wide support (`ring-4-12`: 0.022 vs 0.115)
share a cause with the floor deficit, or is it a separate mismatch in how
correlated the real focus field is at long range?

**35.** Is the simulated speckle excess (50.3 % vs 38.2 %) fully explained by
the subject-spectrum mismatch, or does it survive spectrum shaping?

---

## 10. How to reproduce

```powershell
cd C:\dev\blog\death-of-software\projects\strehl
$env:PYTHONIOENCODING='utf-8'

python experiments\m25-simulator\src\00-selftest.py                 #   2 s
python experiments\m25-simulator\src\01-port-check.py               # 300 s
python experiments\m25-simulator\src\02-gate1a-phi.py               # ~1.9 h
python experiments\m25-simulator\src\03-gate1b-levels.py            # 617 s   (the buggy placement, kept)
python experiments\m25-simulator\src\04-gate1c-occlusion.py         # ~20 m   (wrong regime, kept)
python experiments\m25-simulator\src\05-gate2-negative-control.py   # 840 s
python experiments\m25-simulator\src\06-gate1b-measured-placement.py # 761 s  (post-hoc axes)
python experiments\m25-simulator\src\07-gate1c-coffee.py            # 1445 s
python experiments\m25-simulator\src\08-gate1b-prereg-rerun.py      # 244 s   (the scored Gate 1b)
python experiments\m25-simulator\src\09-diffraction-effect.py       #  60 s
python experiments\m25-simulator\src\10-spectrum-check.py           # 120 s
python experiments\m25-simulator\src\11-psd-shaping-check.py        # 200 s
python experiments\m25-simulator\src\12-gate1c-shaped.py            # ~25 m
```

Outputs land in `experiments/m25-simulator/data/`. Reads
`C:\dev\macro\test\109MSDCF` and `C:\dev\macro\test\coffee-bean`
(read-only), `experiments/m9-support/data/sweep-109MSDCF-coupled.csv`, and
runs `experiments/m21-occlusion-bimodality/src/03-permutation-placebo.py`
unmodified via `runpy`.

Scripts 03 and 04 are retained deliberately. They are the two documented
mistakes of §5.1 and §5.2 and deleting them would erase the evidence for the
discipline items they generated.
