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

> **Second pass, added after the first version of this file.** The first pass
> reported that split-half FRC "has almost no power" (§3.6) and then went on
> using its numbers. That was not good enough. §3.7 establishes the *mechanism*
> — `0.4961 cyc/px` is not a measurement at all — and tries 32 repair settings;
> §3.8 runs a planted **known blur** past every metric and reports a **recovery
> ratio** per metric; §3.9 scores the pre-registered condition in code and asks
> how much of the verdict rests on the dead metric. **The verdict is unchanged
> and is now shown to be independent of the withdrawn metric.** New scripts
> `a10`–`a12`; nothing under `crates/**`, and no `a1`–`a9` script was edited.

## 0. Verdict

**R3 STANDS REFUTED.** The pre-registered kill condition fires on both stacks,
and the clause that carries it runs on a metric with a **measured recovery
ratio of +0.967 to +1.000 against a planted, known blur** (§3.8) and a
demonstrated ability to reject on real data (arm E, 144×/295×).

**The registered *detail* metric is withdrawn.** The FRC 1/7 crossing has
**no power at all** here — not "little": its recovery ratio against a planted
blur is *undefined*, because the statistic is right-censored at both ends of
every comparison (§3.7, §3.8). It cannot be repaired by ring count or threshold
(32 settings tried, zero work). **This does not change the verdict**, and that
is a measured fact rather than a hope:

> **DERIVED** (`out/a12_verdict.log`). With `n_D/n_A` = **3.4679** (109MSDCF)
> and **3.9080** (119MSDCF), both above the pre-registered 1.10×, the two
> REFUTED clauses — `f_D ≤ 1.02 f_A` **or** (`f_D > 1.02 f_A` **and**
> `n_D > 1.10 n_A`) — are **exhaustive over `f_D`**. Re-scored at
> `f_D/f_A` = 0.50, 0.80, 0.95, 1.00, 1.02, 1.021, 1.05, 1.20, 1.50, 2.00, 5.00
> the answer is **REFUTED at every one**. The verdict never depended on the FRC
> reading.

**What M41 therefore cannot say, and does not:** whether arm D buys any real
resolution. It has no metric with demonstrated power to measure resolution on
this data. The kill is a kill **on the noise axis alone**, and that is exactly
what the pre-registration licenses.

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
| 109MSDCF | 0.3680 | **≥0.4961** | ≥1.348 | 0.821× | 2.846× | **3.468** | second (noise) — REFUTED |
| 119MSDCF | **≥0.4961** | **≥0.4961** | *uninformative* | 0.846× | 3.305× | 3.908 | second (noise) — REFUTED |

Both stacks fire. Neither is close to the reopen condition, which needed
`n_D/n_A ≤ 1.05`; the measured values are 3.5× and 3.9×.

**Corrected in the second pass.** The first version of this table printed
`f_D = 0.4961` and `f_D/f_A = 1.000` on 119MSDCF and scored the *first* clause
on it. §3.7 shows `0.4961` is the **censored** value — it means "≥ 0.4961" —
so the ratio is a ratio of two lower bounds and carries no information in
either direction. Both stacks are now scored on the **noise** clause, which is
the one with demonstrated power, and §3.9 shows the verdict is the same for
every value `f_D` could have taken. The noise ratios here are quoted at full
precision (3.468 / 3.908); the first pass's 3.466 / 3.907 were the same numbers
recomputed from the rounded column entries.

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
| `a10_frc_diagnose.py` | **second pass** — why every arm reads `0.4961`, and 32 repair settings | `out/a10_frc_diagnose.log` |
| `a11_metric_power.py` | **second pass** — planted **known blur**, recovery ratio per metric | `out/a11_metric_power.log` |
| `a12_verdict.py` | **second pass** — the kill condition scored in code, and swept | `out/a12_verdict.log` |

Rule 15 was obeyed throughout: no script was edited after producing a result that
is reported here. `a1b`, `a4`, `a5`, `a6`, `a9` each carry, in their own
docstring, a statement of what was wrong with the script they replace. The
second pass added `m41lib3.py` and `a10`–`a12` and **edited none of `a1`–`a9`,
`m41lib.py` or `m41lib2.py`** — the censoring-aware crossing had to be a new
function in a new file for exactly that reason.

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

> **Superseded by §3.7 and §3.9.** The sentence above accepted `1.000` as a
> tie. It is not a tie — it is a ratio of two *censored* readings, and a
> censored reading is a bound. The correct scoring is in §3.9, and it reaches
> the same verdict by a route that does not touch FRC at all.

---

## 3.7 `0.4961` is not a measurement — the mechanism, and 32 attempted repairs

`a10_frc_diagnose.py`. §3.6 established that FRC lacks power. It did not
establish **why the same four digits kept appearing**, and it abandoned the
metric without trying to fix it. Both are done here.

### 3.7.1 The mechanism: a right-censored constant

`m41lib.frc_cross` walks the ring curve looking for two adjacent rings below the
threshold. If it never finds them it ends with

```python
return float(ff[-1])
```

and `ff[-1]` is a property of the **ring grid**, not of the image:

> **MEASURED / DERIVED** (`out/a10_frc_diagnose.log`). At `n = 512`,
> `nbin = 64`: `rmax = 256`, 64 rings of width 4 px, last ring centred at
> 254 px, so `ff[-1] = 254/512 = ` **`0.49609375`** → printed as **`0.4961`**.
> Change only the binning and the "value" moves: **0.492188 / 0.496094 /
> 0.498047 / 0.499023** at `nbin` = 32 / 64 / 128 / 256. A measurement does not
> move when you change the histogram you report it in.

So `0.4961` means **"≥ 0.4961"** — *the curve never crossed 1/7 inside the
sampled band* — and it is emitted with no flag saying so.

> **MEASURED.** Re-scoring every stored curve from the run of record with a
> censoring flag (`m41lib3.cross`, same rule, same numbers): **9 of 12**
> detail-ROI crossings are censored. The minimum FRC over *all* rings is
> **+0.5199** for 119MSDCF arm A and **+0.9846** for 119MSDCF arm D — those
> curves do not approach 1/7 anywhere. All six 119MSDCF arms are censored;
> on 109MSDCF, A, B and D′ crossed and C, D and E did not.
> — `out/a10_frc_diagnose.log`

**DERIVED.** 119MSDCF's `f_D/f_A = 0.4961/0.4961 = 1.000` is therefore a ratio
of two lower bounds. Its entire content is "both are ≥ 0.4961", which is
compatible with `f_D` being larger, smaller or equal. **It was scored as a tie
in the first pass. That was wrong**, and it is the same failure mode as rule
13's "endpoint argmin reported as an optimum".

### 3.7.2 Can it be repaired? — 4 ring counts × 4 thresholds × 2 stacks

Pre-registered in `a10`'s docstring **before running**: a setting counts as a
repair only if it is (a) **uncensored** on the detail ROI for every arm and
(b) **separated** — detail crossing above flat crossing by more than one ring
width. Rule 20: an input producing "no repair" exists (a curve that never
decays); an input producing "repair" exists (a high threshold is crossed early
by any curve that decays at all). Both outcomes were producible.

> **MEASURED** (`out/a10_frc_diagnose.log`). `nbin` ∈ {32, 64, 128, 256} ×
> `thr` ∈ {1/7, 0.30, 0.50, 0.70}, arms A, C, D, detail and flat ROIs, both
> stacks — **32 stack-settings, and the number that repair is ZERO.**

Two separate reasons, and they are worth splitting:

- **Finer rings do not help, by construction.** Raising `nbin` moves the
  fallback *closer* to Nyquist (0.4922 → 0.4990). It buys resolution in the
  *reporting* of a number that was never crossed.
- **A higher threshold uncensors A and C but never D.** On 109MSDCF at
  `nbin = 64`, `thr = 0.30`, arm A reads flat **0.2792** / detail **0.3385**
  and arm C flat **0.3014** / detail **0.3365** — both uncensored and both
  separated. **Arm D reads flat 0.2490 / detail 0.4961 (censored)**, and stays
  censored at `thr = 0.70` at every ring count on both stacks. Arm D's
  split-half FRC **never falls below 0.70 at any frequency**. The estimator
  fails precisely on the arm under test.

**ARGUED, and this is the structural reason no tuning can fix it.** FRC is a
per-ring *correlation*, so it is amplitude-free; and split-half on two halves of
**one capture** shares the scene *and* the fixed pattern, both of which are
common-mode and therefore correlate at 1.0 at every frequency. Arm D amplifies
common-mode content, which **raises** its FRC. The quantity that would have to
be split apart — scene versus fixed pattern — is on the same side of the split.

> **MEASURED.** Common-mode fraction, flat-ROI FRC ÷ detail-ROI FRC at
> `nbin = 64`, 119MSDCF: arm A **0.956 / 0.842 / 0.764 / 0.696 / 0.632** at
> 0.10 / 0.20 / 0.2762 / 0.35 / 0.45 cyc/px; arm D **0.983 / 0.896 / 0.665 /
> 0.770 / 0.793**. On 109MSDCF arm D reads **0.939 / 0.584 / 0.318 / 0.979 /
> 0.943**. A region with no scene detail reproduces most of the detail ROI's
> "resolution" at nearly every frequency.
> (One cell is not usable: 109MSDCF arm A at 0.45 reads −91.072 because the
> denominator, detail-ROI FRC, is ≈ −0.001. A ratio through zero is not a
> number; it is excluded rather than quoted.)

**Conclusion, stated plainly as the brief requires.** The FRC 1/7 crossing
**must be abandoned for this comparison.** It is not repairable by ring count,
threshold, or band-limited reading of the same split. Of the two metrics named
in the kill condition, **the flat-ROI spatial-sigma-ratio survives and the FRC
crossing does not.** No substitute detail metric is quietly swapped in: §3.9
scores the condition as written and shows the surviving axis settles it.

---

## 3.8 The planted positive control on the METRICS — recovery ratios

`a11_metric_power.py`. §3.2's plant is a control on the **arms**: can arm D win
where the forward model is true? It passed at +9.936 dB. That says nothing about
whether the **metrics** can see anything, and rule 20 is precisely about that
gap: *a null is not a kill until the harness has been shown to detect a real
effect.*

**What is planted.** A Gaussian blur of **known** sd `sb` ∈ {0, 0.5, 1, 2, 4} px,
applied in the Fourier domain so the planted MTF is exactly
`exp(−2π²sb²f²)` with no kernel truncation. Two noisy realisations are drawn per
step (the split-half protocol), at two SNRs — a single frame, and a 16-frame
half-merge — and at three **shared-noise fractions** `ρ` ∈ {0, 0.5, 0.9}.

**Recovery ratio, defined in the docstring before running:**

```
rec_lin(sb) = ( m(0) − m(sb) ) / ( pred(0) − pred(sb) )
rec_log(sb) = ln( m(0)/m(sb) ) / ln( pred(0)/pred(sb) )
1.0 = recovers the planted loss;  0.0 = BLIND;  <0 = WRONG SIGN
```

Both are reported side by side rather than one being picked after seeing the
numbers. `pred` is the **truth channel**: the metric on the *noiseless* blurred
source for the scalar metrics, and the analytic split-half expectation
`SNR/(1+SNR)` from the *known* source spectrum and the *known* σ for the FRC
family.

**Three sources, and rule 9 runs first.** `S3` is 119MSDCF's **flat** ROI — no
scene detail by construction; `S1` is 119MSDCF's detail ROI; `S2` is synthetic
broadband with power at every ring to Nyquist. `S2` is rule 13's escape hatch: a
metric that reads nothing on `S2` cannot blame the scene.

### 3.8.1 The truth channel is validated before it is used

> **MEASURED** (`out/a11_results.json`). Over the **17** ladder points where the
> analytic prediction and the measured independent split are both uncensored,
> measured ÷ analytic 1/7 crossing spans **0.9843 to 1.0472** — every point
> within **4.7 %**, most within 2 %. Examples: S2-synth frame `sb=1`
> 0.4521/0.4523 = **0.9996**; S1-real merged `sb=2` 0.2293/0.2269 = **1.0107**;
> S3-flat frame `sb=4` 0.0923/0.0916 = **1.0078**.

This control could have failed. It licenses reading the analytic channel's
verdict that the `sb = 0` reference is unobservable, below.

### 3.8.2 Recovery ratios — the table the brief asked for

**MEASURED**, `rec_lin` at planted `sb`, 16-frame-half noise, `ρ = 0` — the
**best case available to every metric**: independent noise, no common mode.

| metric | source | `sb=0.5` | `sb=1` | `sb=2` | `sb=4` | power? |
|---|---|---|---|---|---|---|
| **FRC 1/7 crossing** *(registered detail metric)* | S3-flat | — | — | — | — | **NONE** |
| | S1-real | — | — | — | — | **NONE** |
| | S2-synth | — | — | — | — | **NONE** |
| FRC crossing at thr 0.5 | all three | — | — | — | — | **NONE** |
| FRC value at `f_sig` | S3-flat | +1.113 | +0.921 | **+1.014** | +0.992 | yes |
| | S1-real | — | +0.551 | **+0.996** | +1.007 | yes |
| | S2-synth | — | — | **+1.059** | +0.992 | yes |
| **high-pass spatial sd** *(registered noise metric)* | S3-flat | +0.987 | +0.980 | **+0.967** | +0.942 | **yes** |
| | S1-real | +1.000 | +1.000 | **+1.000** | +1.000 | **yes** |
| | S2-synth | +1.000 | +1.000 | **+1.000** | +1.000 | **yes** |
| band-power ratio `P(>f_sig)/P(<f_sig)` | S3-flat | +1.002 | +1.000 | **+1.000** | +0.999 | yes |
| | S1-real | +1.001 | +1.001 | **+1.000** | +1.000 | yes |
| | S2-synth | +1.000 | +1.000 | **+1.000** | +1.000 | yes |
| mean \|∇\| | S3-flat | +0.988 | +0.984 | **+0.978** | +0.971 | yes |
| | S1-real | +0.998 | +0.999 | **+0.999** | +0.999 | yes |
| | S2-synth | +1.000 | +1.000 | **+1.000** | +1.000 | yes |

`—` is **undefined, not zero**: the reading is censored and a bound does not
divide. At the single-frame SNR the same table reads `hp_sd` **+0.720** on the
flat source at `sb=2` (against +0.998 on S1 and +0.999 on S2), so the ladder
does discriminate — it is not returning 1.000 by construction.

**Why the registered detail metric is undefined everywhere.** Not because the
blurred arm cannot be read — it can, from `sb = 1` upward — but because the
**`sb = 0` reference is censored**, in the measured channel *and in the analytic
truth channel*, on all three sources at both SNRs. The statistic has no
observable zero point at this SNR, so no ratio to a reference exists to be
formed. **MEASURED** (`out/a11_metric_power.log`, censoring ladder): blurred arm
first uncensored at `sb = 1` (five of six source×SNR cells) or `sb = 2`
(S2-synth merged); the `sb = 0` reference censored in **6 of 6**.

**Rule 9, and it bites everything that works.** Every metric with power also
recovers the plant on the **flat** source at ≥ +0.94. **ARGUED:** these are
*blur* detectors, not *resolution* detectors — they cannot distinguish "the
merge blurred the scene" from "the merge smoothed the noise". That is exactly
why `hp_sd` is admissible in M41's kill condition, where it is applied to the
**flat ROI as a noise statistic** and firing on featureless noise is the point,
and why detail-ROI `hp_sd` appears only descriptively in §4.3 and in no gate.

### 3.8.3 The mechanism, measured on a knob that can be turned

> **MEASURED.** FRC-at-`f_sig` recovery at `sb = 2`, merged noise, as the shared
> noise fraction `ρ` rises: S3-flat **+1.014 → +0.515 → +0.105**; S1-real
> **+0.996 → +0.507 → +0.103**; S2-synth **+1.059 → +0.520 → +0.103** at
> `ρ` = 0 / 0.5 / 0.9.

**DERIVED.** That is `(1 − ρ)` — 1.00 / 0.50 / 0.10 — reproduced to within 4 %
on all three sources. A split-half FRC's ability to see a real blur is scaled
down by exactly the fraction of its content that is common to both halves. On
two halves of one capture the scene *and* the fixed pattern are both common, and
§3.7.2 measures that fraction at 0.63–0.98 on real data. The metric is not
noisy; it is **attenuated by construction**.

---

## 3.9 Scoring the condition in code, and how much rests on the dead metric

`a12_verdict.py`. The condition is transcribed **once** from
`PREREGISTRATION.md` into a function and then applied; it is never re-worded in
prose and scored by eye.

**Rule 20, the input that makes this scorer return something other than
REFUTED:** an arm with `n ≤ 1.10 n_A` and `f > 1.02 f_A`. Such an arm **exists
in this experiment** — arm C, the plain mean, at 0.536× and 0.451× the shipped
merge's flat-ROI high-pass noise.

> **MEASURED** (`out/a12_verdict.log`). Every arm put in D's seat, milestone
> verdict: **D → REFUTED**, D′ → REFUTED, E → REFUTED, B → REFUTED,
> **C → SPLIT REOPEN/REFUTED**. The scorer is not a tautology.
>
> Arithmetic check: over an 800 000-point `(f, n)` grid there are **0** cases
> where the REFUTED and REOPEN clauses both fire. As written they are disjoint,
> so no data could ever satisfy both.

**The FRC-independence sweep.** Hold the measured noise ratios fixed and let
`f_D/f_A` be anything at all:

| `f_D/f_A` | 0.50 | 0.80 | 0.95 | 1.00 | 1.02 | 1.021 | 1.05 | 1.20 | 1.50 | 2.00 | 5.00 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **arm D** | R | R | R | R | R | R | R | R | R | R | R |
| arm C | R | R | R | R | R | IND | RE | RE | RE | RE | RE |

(R = REFUTED, IND = INDETERMINATE, RE = REOPEN; **MEASURED**,
`out/a12_verdict.log`.)

**DERIVED.** Arm D is REFUTED at every value the withdrawn metric could have
taken, because `n_D/n_A` = 3.468 / 3.908 clears 1.10× and the two REFUTED
clauses then partition the whole `f_D` line. Arm C's row is what a verdict that
*does* depend on the FRC axis looks like — it moves from REFUTED to REOPEN
across the sweep. **The M41 verdict is safe; the pre-registration was luckier
than it was careful**, because had arm D's noise cost landed at 1.05× instead of
3.5×, the milestone would have had to report "cannot be scored".

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
5. **It does not measure resolution at all.** This is the honest cost of §3.7
   and §3.8. The registered detail metric has no power, no repair was found,
   and no replacement with demonstrated power on *real* data was available. Two
   candidates recovered the planted blur at ≥ +0.99 — the band-power ratio
   `P(>f_sig)/P(<f_sig)` and FRC's *value* at `f_sig` — but both also fire on a
   **flat** source at ≥ +0.94 (rule 9), so neither is admissible as a detail
   metric without a way to separate blur from smoothing. **M41's kill runs on
   the noise axis and on out-of-range fraction, and on nothing else.**

---

## 6. Proposed facts (460–479 reserved for M41)

Numbers claimed per rule 25; the block was assigned by the orchestrator and no
other namespace is touched here.

- **460.** MEASURED. The M41 Python re-implementation of the shipped regularised
  focus operator reproduces `FOCUS_NOISE_SD` at `0.015367 ± 0.000359` against the
  Rust-measured `0.015214`, a ratio of 1.0101×. `experiments/m41-r3-kill/out/a6_run.log`
- **461.** MEASURED. Guarded focus-axis RIF (arm D, defocus ⊗ measured diffraction
  OTF) costs **3.4679×** (109MSDCF) and **3.9080×** (119MSDCF) the flat-ROI
  high-pass spatial noise of the shipped noise-gated merge at `n_eff = 3`.
  (First pass quoted 3.466 / 3.907, recomputed from the rounded table columns;
  these are the full-precision values from `out/a6_results.json`.)
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

*Added by the second pass (`a10`–`a12`).*

- **475.** MEASURED. The FRC "1/7 crossing = 0.4961 cyc/px" that every M41 arm
  reported is not a measurement: it is `ff[-1]`, the centre of the last ring of
  `m41lib.frc`'s 64-ring grid at n = 512 (`254/512 = 0.49609375`), returned by
  `frc_cross` when the curve never crosses. It moves to 0.492188 / 0.498047 /
  0.499023 at `nbin` = 32 / 128 / 256. **9 of 12** run-of-record detail-ROI
  crossings are this constant, including all six on 119MSDCF, so
  `f_D/f_A = 1.000` there is a ratio of two lower bounds.
  `experiments/m41-r3-kill/out/a10_frc_diagnose.log`
- **476.** MEASURED. Split-half FRC could not be repaired: 4 ring counts × 4
  thresholds × 2 stacks = **32 settings, 0 repairs**, where a repair must be
  uncensored on the detail ROI for arms A, C and D *and* separate detail from
  flat by more than one ring width. Raising the threshold uncensors A and C but
  **never D**, whose split-half FRC never falls below 0.70 at any ring on either
  stack. A flat ROI reproduces 0.63–0.98 of the detail ROI's FRC at every
  frequency on 119MSDCF.
- **477.** MEASURED. Recovery ratios against a planted Gaussian blur of known sd
  (2 px, 16-frame-half noise, independent split — the best case), on a flat
  source / a real detail source / a synthetic broadband source: **FRC 1/7
  crossing UNDEFINED / UNDEFINED / UNDEFINED** (the `sb = 0` reference is
  censored in 6 of 6 source×SNR cells, in the measured *and* the analytic
  channel); high-pass spatial sd **+0.967 / +1.000 / +1.000**; band-power ratio
  **+1.000 / +1.000 / +1.000**; mean |∇| **+0.978 / +0.999 / +1.000**; FRC value
  at `f_sig` **+1.014 / +0.996 / +1.059**. Every metric with power also fires on
  the flat source at ≥ +0.94, so all of them are blur detectors, not resolution
  detectors. `experiments/m41-r3-kill/out/a11_metric_power.log`
- **478.** DERIVED. Split-half FRC's recovery of a planted blur scales as
  **(1 − ρ)** in the fraction ρ of noise power shared between the halves:
  +1.014 / +0.515 / +0.105 (flat), +0.996 / +0.507 / +0.103 (real),
  +1.059 / +0.520 / +0.103 (synthetic) at ρ = 0 / 0.5 / 0.9 — within 4 % of
  1.00 / 0.50 / 0.10. The analytic `SNR/(1+SNR)` truth channel it is measured
  against reproduces the measured crossing to within 4.7 % at all 17 uncensored
  ladder points.
- **479.** DERIVED. With `n_D/n_A` = **3.4679** (109MSDCF) and **3.9080**
  (119MSDCF), both above the pre-registered 1.10×, M41's two REFUTED clauses are
  **exhaustive over `f_D`**: the verdict is REFUTED at `f_D/f_A` = 0.50 through
  5.00, so it does not depend on the withdrawn FRC metric. The scorer is not a
  tautology — arm C, at 0.536× / 0.451× noise, returns SPLIT REOPEN/REFUTED, and
  the REFUTED and REOPEN clauses are disjoint (0 conflicts over an 800 000-point
  grid). `experiments/m41-r3-kill/out/a12_verdict.log`

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

*Added by the second pass.*

- **A crossing statistic must return its censoring flag, or the flag will be
  divided.** `frc_cross` returned the last ring centre when the curve never
  crossed, and the result was published as a measurement and used as the
  numerator and the denominator of a ratio. Any threshold-crossing, first-index,
  or argmin-at-the-edge estimator should return `(value, censored)` and every
  caller should be forced to handle the flag. This is fact 475 and it is rule
  13's endpoint-argmin in a new costume.
- **Repair a metric only where ground truth exists; never on the data under
  test.** The tuning ladder that would have "fixed" the FRC threshold was run on
  the real stacks, where a setting that separates arms cannot be distinguished
  from a setting that flatters one. The verdict on the repair came from the
  planted control, where the answer was known before the run.
- **Score a pre-registered condition in code, once, and then sweep the axis you
  no longer trust.** Transcribing the condition into a function forced the
  clauses to be exhaustive-checked (0 conflicts over 800 000 points) and made
  the FRC-independence sweep a three-line loop. Scoring by eye in prose is what
  let `0.4961 / 0.4961 = 1.000` pass as a tie.
- **When a milestone's verdict survives only because one measured ratio landed
  far from its threshold, say so.** M41 is REFUTED at 3.5× noise against a 1.10×
  bar. Had it landed at 1.2×, half the condition would have rested on a metric
  with no power and the honest answer would have been "cannot be scored".

## 8. Questions proposed (unnumbered)

- Does arm D′ — guarded RIF **without** the diffraction term — beat the shipped
  merge on a metric with power, at ≤ 1.10× its noise? It is the only survivor
  here and it was never what R3 asked for.
- What ground-truth-free detail metric *does* have power on this sensor, given
  that split-half FRC does not? A candidate: FRC between the merges of two
  *independent captures* of the same subject (112MSDCF / 113MSDCF), where the
  fixed-pattern component is still common-mode but the read-noise realisation and
  the subject sampling are not — this would bound how much of §3.6's effect is
  FPN and how much is amplitude-free correlation. §3.8.3 puts a number on the
  prize: recovery scales as (1 − ρ), and the measured common-mode fraction on one
  capture is 0.63–0.98.
- Is there **any** admissible detail metric here at all? The band-power ratio and
  FRC-at-`f_sig` both recover a planted blur at ≥ +0.99, but both also fire at
  ≥ +0.94 on a flat ROI, so neither separates "blurred the scene" from "smoothed
  the noise". Does a *paired* statistic — detail reading conditioned on the flat
  reading of the same merge — separate them, and can that be shown on a plant
  where only one of the two is present?
- Why is the `sb = 0` split-half FRC reference censored on **every** source,
  including the analytic truth channel? Correlated content surviving to Nyquist
  (aliasing, PRNU) and spectral leakage from the window are both candidates; a
  Blackman window and a 9×9 high-pass pre-filter each restore an uncensored
  crossing at `sb = 4` but neither was traced to the `sb = 0` case here.
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
python src\a5_planted.py        # positive control (arms)  -> out/a5_planted.log
python src\a6_real.py           # THE RUN OF RECORD        -> out/a6_run.log
python src\a8_frc_power.py      # FRC power check          -> out/a8_frc_power.log
python src\a9_degenerate_s0.py  # degenerate control       -> out/a9_degenerate.log
# second pass
python src\a10_frc_diagnose.py  # FRC mechanism + repair   -> out/a10_frc_diagnose.log
python src\a11_metric_power.py  # positive control (metrics) -> out/a11_metric_power.log
python src\a12_verdict.py       # condition scored in code -> out/a12_verdict.log
```

Total wall clock ≈ 13 minutes on the reference machine. Decode dominates:
17.9 s for 22 frames × 2 ROIs (109MSDCF), 26.8 s for 33 (119MSDCF); `a10` adds
≈ 50 s of decode-and-re-merge and `a11`/`a12` need no camera data at all.
`out/` is git-ignored for `*.npy`, `*.npz`, `*.tif`; the `.log` and `.json`
artefacts committed here are a few kB each.

`a10` and `a12` re-read `out/a6_results.json`, so the run of record must exist
before them; `a11` is self-contained apart from one decode of 119MSDCF's two
ROIs.

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
7. **The repair criterion for FRC** (§3.7.2). I required *uncensored on detail
   for A, C and D* **and** *detail above flat by more than one ring width*.
   Re-choose: drop the flat-separation clause and accept any uncensored setting —
   arm D is still censored at all 16, so the ladder should still return zero, and
   if it does not, my criterion was doing work I did not declare.
8. **The split model.** Even/odd frames of one capture. Re-choose: two
   independent captures. §3.8.3 predicts the recovery ratio rises as (1 − ρ)
   falls, and that is the single change most likely to resurrect a detail metric.
9. **The recovery definition** (§3.8.2). I reported linear and log ratios side by
   side and quoted linear. Re-choose: quote log, or define recovery as the
   ratio of *slopes* over the whole `sb` ladder rather than a two-point
   difference. The metrics that read +1.000 should be insensitive to this; the
   ones near +0.95 may not be.
10. **The planted blur family.** An exact Fourier Gaussian, chosen so the planted
    MTF has no truncation error. Re-choose: a defocus pillbox — which is what the
    arms actually face, has zero crossings, and could plausibly halt a
    monotone-in-`sb` metric that the Gaussian never challenges.

---

## Proposed SYNTHESIS entries

Fact rows for §4. Numbers 460–479 were reserved for M41 by the orchestrator.
Disciplines (§7 above) and questions (§8 above) are proposed **without numbers**
— §5 and §10 of SYNTHESIS have collided four times.

| # | Fact | Consequence | Source |
|---|---|---|---|
| 460 | The M41 Python re-implementation of the shipped regularised focus operator reproduces `FOCUS_NOISE_SD` at 0.015367 ± 0.000359 against the Rust-measured 0.015214, a ratio of 1.0101x. | The experiment measures the shipped operator, not a lookalike; arm A is shipped-equivalent to 1 %. | `experiments/m41-r3-kill/out/a6_run.log` (M41/M44) |
| 461 | Guarded focus-axis RIF (arm D: defocus OTF composed with the measured diffraction OTF) costs 3.4679x (109MSDCF) and 3.9080x (119MSDCF) the flat-ROI high-pass spatial noise of the shipped noise-gated merge at `n_eff = 3`. | The noise clause of M41's kill condition fires on both stacks with 3x margin over its 1.10x bar. | `out/a6_results.json` (M41/M44) |
| 462 | Arm D puts 63.966 % (109MSDCF) and 81.249 % (119MSDCF) of detail-ROI pixels outside the range of every input frame, against 0.000 % for arms A, B and C. | Forster et al. 2004 measured ~30 % for max-abs selection and called that the defect; the RIF is twice as bad. | `out/a6_run.log` (M41) |
| 463 | With the focus axis switched off (`s = 0`), the diffraction term alone produces 33.271 % / 61.880 % out-of-range and an 11.12 % / 28.12 % RMS residual against the plain mean. | Most of arm D's damage is diffraction inversion, not the focus axis R3 proposed. | `out/a9_degenerate.log` (M41) |
| 464 | On a planted synthetic where the OTF is exactly the one being inverted, arm D beats the shipped merge by +11.172 / +9.936 / +8.553 / +7.623 dB PSNR at noise x0.25 / x1 / x4 / x16. | The RIF estimator is correctly implemented; the optics, not the algebra, is what refuses it. Rule-20 positive control on the arms. | `out/a5_planted.log` (M41) |
| 465 | On that plant the diffraction term carries ~8 dB of arm D's ~10 dB advantage; the focus axis carries ~2 dB (D' - A = +1.961 dB). DERIVED. | R3's headline mechanism (the focus axis) is the smaller half of even its best case. | `out/a5_planted.log` (M41) |
| 466 | Arm D' (guarded RIF, no diffraction term) reduces exactly to the plain mean when `s = 0`: RMS residual 0.0099 DN (0.0013 %) on 109MSDCF, 0.0013 DN (0.0001 %) on 119MSDCF, 0.000 % out-of-range. | Degenerate control passes by construction; the D' implementation is trustworthy. | `out/a9_degenerate.log` (M41) |
| 467 | Split-half FRC on the flat ROI — no scene detail by construction — crosses 1/7 at Nyquist on both stacks and reads 0.295 (109) / 0.677 (119) at `f_sig`, i.e. 50 % and 71 % of the detail ROI's own value. | Split-half FRC on two halves of one capture is dominated by common-mode content and is not a valid resolution metric on this sensor. | `out/a8_frc_power.log` (M41) |
| 468 | Split-half FRC ranks the plain mean above the shipped merge (0.595 vs 0.565 at `f_sig`, 109MSDCF) and ranks arm E — 295x noise, 99 % out-of-range — at 0.970 at 0.45 cyc/px. | Corrects M19's recommendation of FRC as the ground-truth-free sharpening metric: it resists independent noise amplification, not amplification of common-mode content. | `out/a8_frc_power.log` (M41) |
| 469 | The flat-ROI raw spatial sd ratio under-reports arm E's noise explosion by 6.3x (22.767x raw vs 144.391x high-pass); on a flat ROI whose raw sd is 76.272 DN against a modelled sigma of 8.77 DN, ~99 % of the variance is residual scene. | The high-pass residual sd is the noise statistic with power; raw spatial sd must not be used for noise ratios on real ROIs. | `out/a6_run.log` (M41) |
| 470 | `coffee-bubbles` is not at constant focus in the shipped operator's units: its regularised focus response spans 235.02 gate sigma across 19 frames with a through-focus FWHM of 8 frames. | It cannot serve as a degenerate control. Correction to the usability of fact 49. | `out/a7_degenerate.log` (M41) |
| 471 | The through-focus curve self-calibrates blur growth to `s = 1.1856` (109MSDCF, FWHM 10 measured / 9 modelled) and `s = 0.6017` (119MSDCF, 17 / 17) quad px per frame; arm D's out-of-range is 55.92 / 63.97 / 67.09 % at 0.5s / s / 2s. | The self-calibration is not circular — and a 4x error in `s` moving the result by 11 points means the focus axis is doing little. | `out/a6_run.log` (M41) |
| 472 | Solving the shipped gate for `n_eff = 3` on a 512x512 detail ROI needs `t = 3.3269` (109MSDCF) and `t = 4.1758` (119MSDCF); the default ladder t = 0.5/1/2/4 gives `n_eff` 1.26/1.52/2.10/3.49 and 1.23/1.47/1.97/2.92. | Consistent with fact 324. Arm A was held at a fixed, stated averaging depth so D's noise penalty is not an artefact of gate tuning. | `out/a6_run.log` (M41) |
| 473 | `crates/strehl-cli/src/merge_cmd.rs` contains no alignment, warp or registration step. | Every M41 arm ran on unaligned frames; alignment is held constant at *none* across all six, and R3's proposal was never given aligned input. | `crates/strehl-cli/src/merge_cmd.rs` (M41) |
| 474 | ARGUED: R3 (replace the merge with a multi-frame focus-axis Wiener deconvolution) stands refuted on the shipped code path's own focus operator and gate, by a kill condition committed as `f809772` before any arm ran. | R3 is closed. Re-opening it requires a guarded RIF at <= 1.05x the shipped merge's flat-ROI high-pass noise. | `docs/research/M41-r3-kill-measured.md` (M41) |
| 475 | The "FRC 1/7 crossing = 0.4961 cyc/px" reported by every M41 arm, both nulls and both circularity variants is not a measurement: it is `ff[-1]`, the last ring centre of `m41lib.frc`'s 64-ring grid at n = 512 (254/512 = 0.49609375), returned by `frc_cross` when the curve never crosses. It moves to 0.492188 / 0.498047 / 0.499023 at nbin = 32 / 128 / 256, and 9 of 12 run-of-record detail-ROI crossings are this constant. | A right-censored bound was published as a measurement and then used as both numerator and denominator of a ratio: 119MSDCF's `f_D/f_A = 1.000` is a ratio of two lower bounds and carries no information. Rule 13's endpoint-argmin defect in a new costume. | `out/a10_frc_diagnose.log` (M44) |
| 476 | Split-half FRC could not be repaired on this data: 4 ring counts x 4 thresholds x 2 stacks = 32 settings, 0 of which are uncensored on the detail ROI for arms A, C and D and also separate detail from flat by more than one ring width. Raising the threshold uncensors A and C but never D, whose split-half FRC never falls below 0.70 at any ring on either stack. A flat ROI reproduces 0.63-0.98 of the detail ROI's FRC at every frequency on 119MSDCF. | The FRC 1/7 crossing is withdrawn as an M41 metric, not merely doubted. It fails hardest on the arm under test, because arm D amplifies exactly the common-mode content the split cannot separate. Of the two metrics in the kill condition, only the flat-ROI noise ratio survives. | `out/a10_frc_diagnose.log` (M44) |
| 477 | Recovery ratios against a planted Gaussian blur of known sd (2 px, 16-frame-half noise, independent split), on flat / real-detail / synthetic-broadband sources: FRC 1/7 crossing UNDEFINED / UNDEFINED / UNDEFINED (the sb=0 reference is censored in 6 of 6 source x SNR cells, in the measured and the analytic channel); high-pass spatial sd +0.967 / +1.000 / +1.000; band-power ratio P(>f_sig)/P(<f_sig) +1.000 / +1.000 / +1.000; mean grad +0.978 / +0.999 / +1.000; FRC value at `f_sig` +1.014 / +0.996 / +1.059. | Rule 20 discharged on the metrics, not just the arms. The registered detail metric cannot recover a known blur at all; the noise metric can, which is what licenses M41's surviving clause. Every metric with power also fires on a flat source at >= +0.94, so all of them are blur detectors, not resolution detectors, and none is admissible as a detail statistic without a way to separate blur from smoothing. | `out/a11_metric_power.log` (M44) |
| 478 | Split-half FRC's recovery of a planted blur scales as (1 - rho) in the fraction rho of noise power shared between halves: +1.014 / +0.515 / +0.105 (flat), +0.996 / +0.507 / +0.103 (real), +1.059 / +0.520 / +0.103 (synthetic) at rho = 0 / 0.5 / 0.9 — within 4 % of 1.00 / 0.50 / 0.10. The analytic SNR/(1+SNR) truth channel reproduces the measured crossing to within 4.7 % at all 17 uncensored ladder points. | The failure is structural, not statistical: a split-half FRC is attenuated by exactly its common-mode fraction, measured at 0.63-0.98 on one capture. The repair is a different split (two independent captures), not a different threshold or ring count. | `out/a11_metric_power.log` (M44) |
| 479 | DERIVED: with `n_D/n_A` = 3.4679 (109MSDCF) and 3.9080 (119MSDCF), both above the pre-registered 1.10x, M41's two REFUTED clauses are exhaustive over `f_D`; the milestone scores REFUTED at every `f_D/f_A` from 0.50 to 5.00. The scorer is not a tautology — arm C at 0.536x / 0.451x noise returns SPLIT REOPEN/REFUTED — and the REFUTED and REOPEN clauses are disjoint (0 conflicts over an 800 000-point grid). | M41's verdict does not depend on the withdrawn FRC metric; it is carried by the noise clause alone. The pre-registration survived by margin rather than by design — at 1.2x noise instead of 3.5x, half the condition would have rested on a metric with no power and the honest answer would have been "cannot be scored". | `out/a12_verdict.log` (M44) |
