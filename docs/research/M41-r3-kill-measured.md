# M41 — the R3 kill experiment, measured

**Milestone:** M41. **Owns:** this file, `experiments/m41-r3-kill/**`.
**Executes:** §8 of `docs/research/G-edof-deconvolution.md`, pre-registered in M19.
**Tests:** external-review item **R3** — *elevate multi-frame Wiener deconvolution
across the focus axis to the core merge* — currently marked REFUTED in
`docs/proposals/2026-08-external-review.md` on the strength of M20 alone, a Python
proxy that never touched `crates/**`.

Every claim below is labelled **MEASURED** (a number I ran and read),
**DERIVED** (arithmetic on measured numbers), or **ARGUED** (reasoning, not a
result). The author does not verify his own work; this milestone wants a verifier.

---

## 0. Verdict

**R3 STANDS REFUTED.** The pre-registered kill condition fires on both stacks,
by two different clauses, and the metric it fires on is proven to have power by
a control that could have failed and didn't.

The mechanism is not the one M20 proposed. It is sharper and more specific:

> **MEASURED.** Arm D's damage is almost entirely the *diffraction-inversion*
> term, not the focus axis. With the focus axis switched off completely (`s = 0`,
> every frame's OTF identical), the diffraction term alone already puts
> **33.271 %** (109MSDCF) and **61.880 %** (119MSDCF) of detail-ROI pixels
> outside the range of every input frame, against arm D's full 63.966 % and
> 81.249 %. The focus axis contributes the remaining half to a quarter.
> — `out/a9_degenerate.log`, `out/a6_run.log`

And the reason is fact 27. The measured optical cutoff is `f_sig = 0.2762 cyc/px`
against a Nyquist of 0.5. A regularised inverse filter divides by `Σ|H_k|²`, and
the measured diffraction OTF **is zero at and above `f_sig`**. Half the band is a
division by zero held back by nothing but the noise guard, and on real data the
guard is not enough. The same estimator on a planted synthetic — where the OTF is
exactly the one being inverted — wins by **+9.936 dB PSNR**. That gap between
+9.9 dB on the plant and a 3.5–3.9× noise penalty on the sensor is the whole
result.

**Answer to the question §8 was written to settle:** neither core merge nor
opt-in post-process, *as specified*. The guarded RIF **without** the diffraction
term (arm D′) is the only variant that is not obviously harmful, and it is a
candidate for a *future* opt-in experiment, not for this one's verdict.

---

## 1. The kill condition, stated before the data

Committed in `experiments/m41-r3-kill/PREREGISTRATION.md`, commit **`f809772`**,
before any arm was run. Verbatim:

> Let `f_D`, `f_A` be the FRC-1/7 crossing frequency of arms D and A; `n_D`, `n_A`
> their flat-ROI noise ratios.
>
> **R3 STANDS REFUTED if** — on both stacks — `f_D <= 1.02 * f_A`, **OR**
> `f_D > 1.02 * f_A` but `n_D > 1.10 * n_A`.
>
> **R3 MUST BE REOPENED if** — on both stacks — `f_D >= 1.05 * f_A` **and**
> `n_D <= 1.05 * n_A`.
>
> The band between is **INDETERMINATE**. The experiment is **VOID** if the planted
> positive control fails.

Rule 20 was discharged in `PREREGISTRATION.md` §3: an input was named in advance
for each outcome. Arm E (unguarded, `σ²/S = 0`) was pre-declared as the proof
that the noise clause *can* fire; arm C (plain mean) as the proof the detail
clause can fire in the other direction.

**How it resolved — DERIVED from `out/a6_run.log`:**

| stack | `f_A` | `f_D` | `f_D/f_A` | `n_A` | `n_D` | `n_D/n_A` | clause |
|---|---|---|---|---|---|---|---|
| 109MSDCF | 0.3680 | 0.4961 | 1.348 | 0.821× | 2.846× | **3.466** | second (noise) — REFUTED |
| 119MSDCF | 0.4961 | 0.4961 | **1.000** | 0.846× | 3.305× | 3.907 | first (`≤1.02`) — REFUTED |

Both stacks fire. Neither is close to the reopen condition, which needed
`n_D/n_A ≤ 1.05`; the measured values are 3.5× and 3.9×.

---

## 2. What was run, and where

Everything is in `experiments/m41-r3-kill/src/`. Corpora were opened read-only;
nothing was written to `C:\dev\macro` or `D:\`.

| script | what it did | log |
|---|---|---|
| `a1_rois.py` | **VOID.** Scored candidate ROIs by a single centre pixel, not a window mean; its "flat" ROI carried 50–148× the modelled σ. Not used. | `out/a1_rois.log` |
| `a1b_rois.py` | ROI selection, block-reduced correctly | `out/a1b_rois.log` |
| `a2_run.py` | **VOID for arms A, D, D′, E** — wrong gate rule *and* a broken overlap-add. Superseded by `a6`. | `out/a2_run.log` |
| `a3_planted.py` | **VOID.** Planted control using the broken overlap-add. | `out/a3_planted.log` |
| `a4_shipped_gate.py` | the shipped focus operator + gate rule, and the operator control | `out/a4_run.log` |
| `a5_planted.py` | planted positive control, corrected estimator | `out/a5_planted.log` |
| `a6_real.py` | **THE RUN OF RECORD** — six arms, both stacks, permutation and circularity controls | `out/a6_run.log` |
| `a7_degenerate.py` | attempted degenerate control on `coffee-bubbles`; **premise falsified** | `out/a7_degenerate.log` |
| `a8_frc_power.py` | power check on split-half FRC | `out/a8_frc_power.log` |
| `a9_degenerate_s0.py` | degenerate control imposed by construction (`s = 0`) | `out/a9_degenerate.log` |

Rule 15 was obeyed throughout: no script was edited after producing a result that
is reported here. `a1b`, `a4`, `a5`, `a6`, `a9` each carry, in their own
docstring, a statement of what was wrong with the script they replace.

**Data.** `C:\dev\macro\test\109MSDCF` (22 ARW, ISO 160) and
`C:\dev\macro\test\119MSDCF` (33 ARW, ISO 50); `D:\personal\macro\coffee-bubbles`
(19 ARW, ISO 1000). All arms work on the green quad plane
`G = (G1 + G2)/2 = 0.5·(v[0::2,1::2] + v[1::2,0::2]) − 512` of
`rawpy.raw_image_visible` — the active area only (rule 7). Detail and flat ROIs
are 512×512 quad px with a 32 px operator margin, chosen by `a1b_rois.py`:

| stack | detail ROI | flat ROI | flat `hp_sd/model σ` |
|---|---|---|---|
| 109MSDCF | (2215, 699) | (1356, 32) | **1.14** |
| 119MSDCF | (2251, 800) | (1396, 32) | **1.81** |

MEASURED. The last column is rule 10's own detector applied to the ROI choice: a
flat ROI must be noise-dominated, and 1.14/1.81 says these are. The *detail* ROIs
read 6.87 and 18.74 on the same statistic.

---

## 3. Controls, reported before the arms

### 3.1 The arm-A operator control — PASSES

Arm A had to be re-implemented in Python: the shipped merge writes a
white-balanced RGB TIFF and the arms work on the raw quad plane.
`crates/strehl-core/src/merge.rs` and `through_focus.rs` were **read, never
edited** (M40 owns them). Two things were read out of them and re-implemented:
the focus response is a box mean of the **σ-normalised gradient magnitude**
(`merge.rs:104–131`), and the gate is **absolute and noise-scaled** —
`best − focus ≤ t·√2·FOCUS_NOISE_SD`, `FOCUS_NOISE_SD = 0.015214`
(`merge.rs:131`, `merge.rs:140–186`).

The control: push a pure-noise plane through the Python operator and read the sd
of the regularised interior response. The shipped constant is *measured* in Rust
by `the_focus_noise_constant_is_the_measured_one`.

> **MEASURED.** Python: `0.015367 ± 0.000359` (6 seeds). Shipped: `0.015214`.
> **Ratio 1.0101×.** — `out/a6_run.log:2`

This control could have failed and is what licenses calling column A "the shipped
rule". Gate solved for the project's calibration target `n_eff = 3` (fact 212):
`t = 3.3269` on 109, `t = 4.1758` on 119, both giving detail-ROI `n_eff = 3.00`.
The shipped default ladder on the same ROIs reads `n_eff` = 1.26 / 1.52 / 2.10 /
3.49 (109) and 1.23 / 1.47 / 1.97 / 2.92 (119) at `t` = 0.5 / 1 / 2 / 4 —
MEASURED, and consistent with fact 324's finding that a fixed gate is not a
calibration.

### 3.2 The planted positive control — PASSES

`a5_planted.py`. A real macro texture is *defined* as the latent, frames are
generated through the same OTF the arms invert, calibrated noise added at four
levels. This is deliberately an **inverse crime**: it is a control on the
harness, not on realism.

**MEASURED**, PSNR in dB against the known latent (`out/a5_planted.log`):

| noise | A | B | C | D | D′ | E | **D − A** |
|---|---|---|---|---|---|---|---|
| ×0.25 | 28.262 | 29.472 | 28.047 | **39.434** | 30.226 | 14.742 | **+11.172** |
| ×1 | 28.261 | 29.489 | 28.047 | **38.198** | 30.222 | 8.748 | **+9.936** |
| ×4 | 28.260 | 29.512 | 28.046 | **36.813** | 30.206 | 2.739 | **+8.553** |
| ×16 | 28.250 | 29.441 | 28.041 | **35.873** | 30.144 | −3.224 | **+7.623** |

The estimator works, and the advantage decays monotonically with noise exactly as
theory says it must. The experiment is not void.

Two readings from the same table that matter later:

- **DERIVED.** D′ (no diffraction term) gains only **+1.965 / +1.961 / +1.946 /
  +1.894 dB** over A. So on the plant, **≈ 8 dB of D's ≈ 10 dB advantage is the
  diffraction term**, and only ≈ 2 dB is the focus axis.
- **MEASURED.** Arm E collapses from 14.742 to −3.224 dB across the sweep. The
  unguarded ablation behaves as the theory demands.
- **Rule 13, honestly.** `D − A` never crosses zero inside the sweep
  (+11.17 → +7.62 dB). **No turnover was found within the sweep.** I did not
  demonstrate a noise level at which D loses to A on the plant; the sweep would
  have to be extended. E's collapse is what proves the plant can express failure.

### 3.3 The degenerate control — §8's version could NOT be run; a valid one substituted

§8.4 named `coffee-bubbles` as "19 frames at constant focus, so every `H_k` is
equal and D must reduce to C" (fact 49).

> **MEASURED, and it falsifies the premise.** On `coffee-bubbles`' detail ROI the
> regularised focus response runs **3.60367 to 8.66036** across the 19 frames —
> a spread of **235.02 gate σ** — with a through-focus FWHM of **8 of 19 frames**.
> That is a strongly peaked focus curve. — `out/a7_degenerate.log`

**ARGUED.** Whatever fact 49 means by "constant focus", the shipped focus operator
does not see it; the subject itself changes between frames. `a7`'s D-vs-C
residuals therefore measure a real focus sweep and say nothing about degeneracy.
This is a correction to fact 49's usability as a degenerate control, not a
failure of arm D.

**Minimal deviation:** impose the degenerate condition by construction instead of
hunting for it — run the arms with `s = 0`, so every frame's OTF is identical.
The prediction is then exact and can fail (`a9_degenerate_s0.py`):

> **MEASURED.** `D′(s=0)` vs `C`: RMS residual **0.0099 DN** (0.0013 % of |C|)
> on 109MSDCF and **0.0013 DN** (0.0001 %) on 119MSDCF; max |residual| 0.12 and
> 0.05 DN; out-of-range **0.000 %** on both. — `out/a9_degenerate.log`

The estimator collapses to the plain mean to one part in 10⁵ when the focus axis
is removed. **PASSES.**

The same run is the paper's most useful single number:

> **MEASURED.** `D(s=0)` vs `C` — the diffraction term alone, focus axis off:
> RMS residual **86.4240 DN (11.1237 % of |C|)**, max 632.73 DN, **33.271 %
> out-of-range** on 109MSDCF; RMS **465.6277 DN (28.1239 %)**, max 4421.69 DN,
> **61.880 % out-of-range** on 119MSDCF.

### 3.4 The permutation null — uninformative, and I say so

`a6_real.py` shuffles the frame→OTF assignment. Pre-registered target: D's
advantage collapses to ≤ 1.05×.

**MEASURED** (`out/a6_run.log`):

| stack | FRC 1/7, D | FRC 1/7, permuted | hp_sd, D | hp_sd, permuted | oor, D | oor, permuted |
|---|---|---|---|---|---|---|
| 109MSDCF | 0.4961 | 0.4961 | 271.424 | 135.753 | 63.97 % | 48.00 % |
| 119MSDCF | 0.4961 | 0.4961 | 1148.136 | 524.013 | 81.25 % | 63.74 % |

**ARGUED.** The null cannot do its job: D has no FRC advantage over A on 119 to
collapse, and on the detail axis the permuted arm is *identical* to D. What the
null does show is that the frame→OTF assignment is load-bearing for the *damage*
— permuting halves the excess noise (2.00× and 2.19×) and cuts out-of-range by
16–18 points. The correct OTF assignment makes the deconvolution more aggressive
in the right places, and on this data "more aggressive" is the harm.

### 3.5 The circularity control — the self-calibration barely matters

The blur growth `s` is self-calibrated from the through-focus curve's own width,
which is the reviewer's claim in §5 of the survey. **MEASURED:**
`s = 1.1856` quad px/frame on 109 (through-focus FWHM 10 frames measured, 9
modelled) and `s = 0.6017` on 119 (17 measured, 17 modelled).

Running D at `0.5 s` and `2 s` — a 4× span (`out/a6_run.log`):

| stack | metric | 0.5 s | s (self-cal) | 2 s |
|---|---|---|---|---|
| 109MSDCF | FRC 1/7 | 0.4961 | 0.4961 | 0.4961 |
| 109MSDCF | detail hp_sd | 233.963 | 271.424 | 268.037 |
| 109MSDCF | out-of-range | 55.92 % | 63.97 % | 67.09 % |
| 119MSDCF | FRC 1/7 | 0.4961 | 0.4961 | 0.4961 |
| 119MSDCF | detail hp_sd | 1032.771 | 1148.136 | 1059.034 |
| 119MSDCF | out-of-range | 78.52 % | 81.25 % | 80.36 % |

`s` = 1.1856 → 0.5928 / 2.3712 on 109MSDCF; 0.6017 → 0.3009 / 1.2034 on 119MSDCF.

**DERIVED.** The output is nearly insensitive to a 4× error in `s`. That kills
the circularity worry — the advantage does not depend on the self-calibrated
widths — but it also says something worse for R3: **the focus-axis part of the
estimator is doing very little on this data.** An estimator whose output barely
moves when you change the parameter it is supposed to be estimating is not
exploiting that parameter.

### 3.6 Split-half FRC has almost no power on this sensor — my own metric, corrected

This is the methodological finding of the milestone and it corrects M19.

**The anomaly, MEASURED** (`out/a6_run.log`): split-half FRC ranks arm **C**
(plain mean) *above* arm A at 0.28 cyc/px on 109MSDCF — 0.595 vs 0.565 — and
ranks arm **E**, whose flat-ROI high-pass noise is 144–295× a single frame and
99 % of whose pixels are out of range, at **0.970 at 0.45 cyc/px** on 119MSDCF.
Fact 19 and `M39-verify-detail-metric.md` say the mean is not sharper than
selection.

**The test** (`a8_frc_power.py`): run the identical split-half FRC protocol on
the **flat ROI**, where by construction there is no detail to resolve. Predicted
in the script docstring before running: if FRC is measuring resolution it must
collapse there; if it is measuring common-mode content it will not.

> **MEASURED.** Arm C, split-half FRC on the **flat** ROI —
> 109MSDCF: 1/7 crossing **0.4961 cyc/px** (Nyquist), FRC @0.10/@0.20/@0.2762/
> @0.35/@0.45 = **0.899 / 0.430 / 0.295 / 0.251 / 0.255**.
> 119MSDCF: crossing **0.4961**, **0.974 / 0.831 / 0.677 / 0.636 / 0.598**.
> — `out/a8_frc_power.log`

**DERIVED.** A region containing no scene detail reproduces **0.295/0.595 = 50 %**
(109) and **0.677/0.950 = 71 %** (119) of the detail ROI's FRC at `f_sig`, and
crosses 1/7 at Nyquist on both. Split-half FRC on two halves of the same sensor
is dominated by common-mode content — fixed-pattern non-uniformity, which is
identical in both halves and therefore perfectly correlated at every frequency —
compounded by FRC being a per-ring *correlation*, so it is amplitude-free and
cannot see that an arm has emptied a band.

**Failed control, disclosed.** `a8` also computed FRC on the two halves with the
all-frame mean subtracted. It reads **−1.000 at every frequency on every stack**.
That is a degenerate artefact of my own construction, not a finding: for an
even/odd split of equal size the all-frame mean is (a+b)/2, so the residuals are
+(a−b)/2 and −(a−b)/2, exactly anti-correlated by algebra. That arm carries no
information and is void.

**Consequence for the verdict.** The kill condition does not lean on FRC where
FRC lacks power. On 119MSDCF it fires on `f_D/f_A = 1.000` — a *tie*, which is
what a metric without discrimination produces and which the pre-registration
already routed to REFUTED. On 109MSDCF it fires on the **noise clause**, which
uses a metric proven to have power by arm E. **ARGUED:** had FRC been the only
axis, this experiment would have had to be declared indeterminate.

---

## 4. The six arms

### 4.1 Noise axis — flat ROI, high-pass spatial sd, ratio to the single middle frame

**MEASURED** (`out/a6_run.log`). All σ here are **SPATIAL** sd and are never
compared to a temporal σ (rule 10).

| arm | 109MSDCF hp ratio | 119MSDCF hp ratio | 109 out-of-range | 119 out-of-range |
|---|---|---|---|---|
| A — shipped rule, `n_eff = 3` | **0.821×** | **0.846×** | 0.000 % | 0.000 % |
| B — plain argmax | 1.240× | 1.283× | 0.000 % | 0.000 % |
| C — plain mean | 0.440× | 0.382× | 0.000 % | 0.000 % |
| D — guarded RIF, defocus ⊗ diffraction | **2.846×** | **3.305×** | 13.916 % | 35.166 % |
| D′ — guarded RIF, no diffraction term | 0.943× | 0.979× | 1.112 % | 0.601 % |
| E — unguarded RIF | **144.391×** | **295.487×** | 99.034 % | 99.403 % |

Reference frames: 109 flat single middle frame hp sd 11.770 DN (model σ 8.77 DN);
119, 13.098 DN (model σ 6.90 DN).

**Two metric choices disclosed (rule 24).** The pre-registration said "flat-ROI
spatial sigma ratio" without saying high-pass. The **raw** sd ratio reads
A 0.999× / D **1.146×** on 109 and A 0.989× / D 1.060× on 119 — i.e. it would
have made D look almost harmless. It has no power: the flat ROI's raw sd is
76.272 DN against a modelled σ of 8.77 DN, so **≈ 99 % of its variance is
residual scene, not noise**. Arm E settles it: raw sd ratio 22.767×, high-pass
ratio 144.391× — the raw statistic under-reports a catastrophic noise explosion
by **6.3×**. The high-pass ratio is the one reported above and the one the kill
condition is evaluated on.

### 4.2 Detail axis — split-half FRC, detail ROI

**MEASURED** (`out/a6_run.log`). Read with §3.6's caveat: this metric has little
power on this sensor.

| arm | 109: 1/7 crossing | @0.20 | @0.2762 | @0.35 | 119: 1/7 crossing | @0.20 | @0.2762 | @0.35 |
|---|---|---|---|---|---|---|---|---|
| A | 0.3680 | 0.875 | 0.565 | 0.224 | 0.4961 | 0.982 | 0.934 | 0.855 |
| B | 0.3214 | 0.766 | 0.228 | 0.033 | 0.4961 | 0.924 | 0.657 | 0.537 |
| C | 0.4961 | 0.946 | 0.595 | 0.252 | 0.4961 | 0.993 | 0.950 | 0.838 |
| D | 0.4961 | 0.954 | 0.724 | 0.789 | 0.4961 | 0.995 | 0.986 | 0.991 |
| D′ | 0.3906 | 0.950 | 0.709 | 0.298 | 0.4961 | 0.995 | 0.977 | 0.927 |
| E | 0.4961 | 0.949 | 0.623 | 0.685 | 0.4961 | 0.995 | 0.960 | 0.969 |

One real signal survives the caveat: **B is the worst arm on both stacks at every
frequency**, exactly as the project's thesis says selection should be. FRC
separates selection from averaging cleanly; what it cannot do is separate
averaging from deconvolution.

### 4.3 Detail ROI, all arms

**MEASURED** (`out/a6_run.log`). `P(>f_sig)/P(<f_sig)` is the fraction of power
the arm put above the measured optical cutoff — where fact 27 says the scene has
none.

| arm | 109 hp_sd | 109 oor | 109 P above/below | 119 hp_sd | 119 oor | 119 P above/below |
|---|---|---|---|---|---|---|
| A | 87.973 | 0.000 % | 7.7251e-05 | 210.143 | 0.000 % | 1.0746e-04 |
| B | 87.634 | 0.000 % | 3.8921e-04 | 209.450 | 0.000 % | 3.0268e-04 |
| C | 49.053 | 0.000 % | 5.4482e-06 | 115.666 | 0.000 % | 5.6789e-06 |
| D | 271.424 | **63.966 %** | 3.0754e-05 | 1148.136 | **81.249 %** | 2.1224e-03 |
| D′ | 98.652 | 26.338 % | 9.7235e-05 | 230.389 | 23.217 % | 1.3276e-04 |
| E | 5201.106 | 98.764 % | 5.2612e-01 | 22153.346 | 99.351 % | 6.5495e-01 |

**Context, MEASURED in M19 (fact-400 block):** Forster et al. 2004 measured that
max-abs complex-wavelet selection puts **≈ 30 %** of pixels outside the dynamic
range of every input frame, and treated that as the defect motivating their
method. **Arm D is at 64 % and 81 %** — two to two-and-a-half times worse than
the artefact rate that motivated a published EDOF method. **ARGUED:** this alone
would disqualify D as a default merge even if the noise clause had not fired.

---

## 5. What this does and does not say

**DERIVED, and the core of the result.** Set the four readings side by side:

| | plant (OTF exactly true) | 109MSDCF | 119MSDCF |
|---|---|---|---|
| D − A | **+9.936 dB PSNR** | noise **3.466×** A, 64 % oor | noise **3.907×** A, 81 % oor |
| D′ − A | +1.961 dB PSNR | noise 1.149× A, 26 % oor | noise 1.157× A, 23 % oor |
| diffraction term's share of D−A | ≈ **8 of 10 dB** | ≈ 33 of 64 points of oor | ≈ 62 of 81 points of oor |

The term that carries four fifths of the benefit when the model is exactly right
is the same term that carries most of the damage when it is not. **ARGUED:** that
is the signature of an estimator whose gain lives entirely in a band the real
optics does not populate. Fact 12 measured MTF@Nyquist = 0.036 / 0.000 / 0.000 at
f/5.6, f/8, f/11 at m = 2.0; fact 27 measured the cutoff at 0.2762 of a 0.5
Nyquist. Inverting `Σ|H_k|²` where `H` is genuinely zero is not sharpening, it is
amplifying whatever else is there — and on this sensor what else is there is
fixed-pattern non-uniformity and read noise, which §3.6 shows is correlated
enough between frame subsets to fool a correlation metric.

**What this does NOT say.**

1. It does not say deconvolution is worthless on this rig. Arm D′ — guarded RIF
   with **no** diffraction term — is at 0.943×/0.979× flat-ROI noise (vs A's
   0.821×/0.846×) and 1.1 %/0.6 % out-of-range on the flat ROI. It gains
   +1.96 dB on the plant. It is the survivor and it was never the thing R3 asked
   for. Its 23–26 % detail-ROI out-of-range is still at Forster's defect level.
2. It does not test deconvolution *after* alignment. **MEASURED:**
   `crates/strehl-cli/src/merge_cmd.rs` contains no alignment step, so all six
   arms ran on unaligned frames. Holding alignment constant at *none* is the
   right controlled comparison for a claim about the merge rule, but no absolute
   number here is a statement about the shipped pipeline's eventual quality.
3. It does not test an iterative arm. Fact 404 (M19): a regularised inverse
   filter lands within 0.19 dB of Richardson–Lucy at 1/237 the cost. **ARGUED:**
   an iterative arm would move the numbers by tenths of a dB and change no
   verdict here.
4. It is one 512×512 ROI per stack. M20's verification found its 15.1 % headline
   was one capture from a 3.5–65.8 % corpus range; the same caution applies.

---

## 6. Proposed facts (460–479 reserved for M41)

Numbers claimed per rule 25; the block was assigned by the orchestrator and no
other namespace is touched here.

- **460.** MEASURED. The M41 Python re-implementation of the shipped regularised
  focus operator reproduces `FOCUS_NOISE_SD` at `0.015367 ± 0.000359` against the
  Rust-measured `0.015214`, a ratio of 1.0101×. `experiments/m41-r3-kill/out/a6_run.log`
- **461.** MEASURED. Guarded focus-axis RIF (arm D, defocus ⊗ measured diffraction
  OTF) costs **3.466×** (109MSDCF) and **3.907×** (119MSDCF) the flat-ROI
  high-pass spatial noise of the shipped noise-gated merge at `n_eff = 3`.
- **462.** MEASURED. Arm D puts **63.966 %** (109MSDCF) and **81.249 %**
  (119MSDCF) of detail-ROI pixels outside the range of every input frame, against
  0.000 % for arms A, B and C. Forster et al. 2004 measured ≈ 30 % for max-abs
  selection and called that the defect.
- **463.** MEASURED. With the focus axis switched off (`s = 0`), the diffraction
  term alone produces **33.271 %** / **61.880 %** out-of-range and an 11.12 % /
  28.12 % RMS residual against the plain mean. Most of arm D's damage is
  diffraction inversion, not the focus axis.
- **464.** MEASURED. On a planted synthetic where the OTF is exactly the one being
  inverted, arm D beats the shipped merge by **+11.172 / +9.936 / +8.553 /
  +7.623 dB** PSNR at noise ×0.25 / ×1 / ×4 / ×16. The estimator is correct; the
  optics is what refuses it.
- **465.** DERIVED. On that plant, the *diffraction* term carries ≈ 8 dB of arm
  D's ≈ 10 dB advantage; the focus axis carries ≈ 2 dB (D′ − A = +1.961 dB).
- **466.** MEASURED. Arm D′ (guarded RIF, no diffraction term) reduces exactly to
  the plain mean when `s = 0`: RMS residual **0.0099 DN (0.0013 %)** on 109MSDCF
  and **0.0013 DN (0.0001 %)** on 119MSDCF, 0.000 % out-of-range.
- **467.** MEASURED. Split-half FRC on the **flat** ROI — no scene detail by
  construction — crosses 1/7 at Nyquist on both stacks and reads 0.295 (109) and
  0.677 (119) at `f_sig = 0.2762 cyc/px`, i.e. 50 % and 71 % of the detail ROI's
  own value. Split-half FRC on two halves of one sensor is dominated by
  common-mode content and is not a valid resolution metric here.
- **468.** MEASURED. Split-half FRC ranks the plain mean above the shipped merge
  (0.595 vs 0.565 at `f_sig`, 109MSDCF) and ranks arm E — 295× noise, 99 %
  out-of-range — at 0.970 at 0.45 cyc/px. This corrects M19's recommendation of
  FRC as the ground-truth-free sharpening metric: it resists *independent* noise
  amplification, not amplification of *common-mode* content.
- **469.** MEASURED. The flat-ROI **raw** spatial sd ratio under-reports arm E's
  noise explosion by 6.3× (22.767× raw vs 144.391× high-pass). On a flat ROI whose
  raw sd is 76.272 DN against a modelled σ of 8.77 DN, ≈ 99 % of the variance is
  residual scene; the high-pass ratio is the statistic with power.
- **470.** MEASURED. `coffee-bubbles` is **not** at constant focus in the shipped
  operator's units: its regularised focus response spans 235.02 gate σ across the
  19 frames with a through-focus FWHM of 8 frames. It cannot serve as a
  degenerate control. (Correction to the usability of fact 49.)
- **471.** MEASURED. The through-focus curve self-calibrates the blur growth to
  `s = 1.1856` (109MSDCF, FWHM 10 frames measured / 9 modelled) and `s = 0.6017`
  (119MSDCF, 17 / 17) quad px per frame. Arm D's output is nearly insensitive to a
  4× error in `s` (out-of-range 55.92 / 63.97 / 67.09 % at 0.5s / s / 2s on
  109MSDCF), so the self-calibration is not circular — and the focus axis is doing
  little.
- **472.** MEASURED. Solving the shipped gate for `n_eff = 3` on a 512×512 detail
  ROI needs `t = 3.3269` (109MSDCF) and `t = 4.1758` (119MSDCF); the default
  ladder `t` = 0.5/1/2/4 gives `n_eff` = 1.26/1.52/2.10/3.49 and
  1.23/1.47/1.97/2.92. Consistent with fact 324.
- **473.** MEASURED. `crates/strehl-cli/src/merge_cmd.rs` contains no alignment,
  warp or registration step; every M41 arm therefore ran on unaligned frames, and
  alignment is held constant at *none* across all six.
- **474.** ARGUED. R3 stands refuted **on the shipped code path's own focus
  operator and gate**, by two independent clauses of a kill condition committed
  before the data (`f809772`), with the noise clause carried by a statistic proven
  to have power by arm E.

---

## 7. Disciplines proposed (numbers deliberately omitted — §5 has collided twice)

- **A correlation metric is not a resolution metric until it has been run on a
  region with no resolution in it.** FRC crossed 1/7 at Nyquist on a flat ROI on
  both stacks. Any ground-truth-free sharpening metric adopted in future must be
  run first on the flat ROI, and its reading there reported next to its reading
  on detail.
- **When a control's premise is a corpus fact, measure the premise.** The
  degenerate control failed not because the arm misbehaved but because
  `coffee-bubbles` does not have the property fact 49 attributes to it. Facts
  about *data* decay the same way facts about code do.
- **Impose a degenerate condition rather than hunting for one.** `s = 0` gave an
  exact-equality prediction that passed to one part in 10⁵ in two minutes; the
  corpus hunt cost a decode pass and produced nothing.
- **An estimator whose output does not move when you change the parameter it
  estimates is not using that parameter.** A 4× swing in `s` moved arm D's
  out-of-range fraction by 11 points on one stack and 2 on the other. Report
  parameter sensitivity next to parameter accuracy.

## 8. Questions proposed (unnumbered)

- Does arm D′ — guarded RIF **without** the diffraction term — beat the shipped
  merge on a metric with power, at ≤ 1.10× its noise? It is the only survivor
  here and it was never what R3 asked for.
- What ground-truth-free detail metric *does* have power on this sensor, given
  that split-half FRC does not? A candidate: FRC between the merges of two
  *independent captures* of the same subject (112MSDCF / 113MSDCF), where the
  fixed-pattern component is still common-mode but the read-noise realisation and
  the subject sampling are not — this would bound how much of §3.6's effect is
  FPN and how much is amplitude-free correlation.
- Does the diffraction term become safe once the merge aligns? All six arms here
  ran unaligned; misregistration puts energy above `f_sig` that the deconvolution
  then amplifies.
- What is arm D's out-of-range fraction across the whole corpus, not one ROI per
  stack? M20's 15.1 % headline was one capture from a 3.5–65.8 % range.

---

## 9. Reproduction

```powershell
$env:PYTHONIOENCODING = 'utf-8'
cd C:\dev\blog\death-of-software\projects\strehl\experiments\m41-r3-kill
python src\a1b_rois.py          # ROI selection            -> out/rois_b.json
python src\a4_shipped_gate.py   # shipped operator control -> out/a4_run.log
python src\a5_planted.py        # positive control         -> out/a5_planted.log
python src\a6_real.py           # THE RUN OF RECORD        -> out/a6_run.log
python src\a8_frc_power.py      # FRC power check          -> out/a8_frc_power.log
python src\a9_degenerate_s0.py  # degenerate control       -> out/a9_degenerate.log
```

Total wall clock ≈ 11 minutes on the reference machine. Decode dominates:
17.9 s for 22 frames × 2 ROIs (109MSDCF), 26.8 s for 33 (119MSDCF).
`out/` is git-ignored for `*.npy`, `*.npz`, `*.tif`; the `.log` and `.json`
artefacts committed here are a few kB each.

## 10. What a verifier should re-choose, not re-compute (rule 24)

1. **The noise statistic.** I chose high-pass (9×9 box residual) spatial sd over
   raw spatial sd, and justified it with arm E. Re-choose: a temporal-difference
   estimator, or a smaller/larger high-pass kernel. Does D/A stay near 3.5–3.9×?
2. **The reference for the noise ratio.** I used the single middle frame, matching
   the shipped invariant. Re-choose: the sharpest frame, or the per-pixel winner.
3. **The gate.** I solved for `n_eff = 3` on the detail ROI. Re-choose: the
   shipped default ladder, or `n_eff` solved on the whole frame. Arm A gets
   quieter as `n_eff` rises, which makes D's penalty *larger*; the direction of
   this choice's bias is against R3 and should be checked.
4. **The ROI.** One 512×512 detail ROI per stack, chosen by maximum
   noise-corrected Tenengrad. Re-choose: the fact-142 candidate subset, or a
   random ROI sample.
5. **`S(f)`.** A 1/f² prior normalised to the tile's measured signal variance.
   Re-choose: a flat prior, or a per-tile fitted power law. This sets how hard the
   guard bites and is the most likely place a pro-D result is hiding.
6. **The tile.** 128 px, 50 % overlap, Hann. Re-choose the size; the defocus radius
   reaches ≈ 13 px on 109MSDCF, which is not negligible against 128.
