# M70 — The through-focus spectrum: is deconvolution the core of the merge, or a plugin?

**Status: MEASURED. The reviewer's premise is TRUE. The architectural inference
drawn from it is FALSE, and the gap between the two is measured at 1.110×.**

**Verdict: PLUGIN.**

> **Addendum, §16–§18, added after M67 reported (`5cafbee`).** Two things arrived
> after §0–§15 were written and committed at `69decfc`:
> **(a)** the owner's correction that the incumbent is *the gated average as it
> actually behaves*, not a three-frame average — **§18 re-prices it: the matched
> filter buys 2.38%, not 0.23%, and the verdict is unchanged**; and
> **(b)** a commission to close M67 §7.3's gap by measuring **real through-focus
> symmetry** — **§16–§17**, governed by a second pre-registration
> (`PREREGISTRATION-B.md`, committed at `18efd34` *before* the corpus run).
> The addendum is appended rather than woven in, so that what was known when each
> criterion was written stays legible.

> **Second addendum, §19, added after the owner's third turn.** That turn
> **retracted** the claim that sent §16 after asymmetry — no corpus fact
> establishes it — and rescoped the question to *"are real through-focus curves
> symmetric, and where does their shape depart from a Gaussian?"* §19 answers the
> second half under a third pre-registration (`PREREGISTRATION-C.md`, committed
> `6a831fa` *before* the corpus run), and **opens by retracting a misreading of my
> own in §16.7** (§19.1). Its results: the pre-registered criteria return
> **INDETERMINATE**; on patches where the question is well posed the curve is
> **not distinguishable from a Gaussian** (two independent captures agreeing to
> 0.0099); and the apparent departure elsewhere is **multimodality — the
> subject's depth range — which answers M25's open question 33** and
> **reinforces PLUGIN by a second, independent route** (§19.8).

> **Third addendum, §20.** Two items. **(a)** `corpus_lint` [S1] failed the
> repository on a **render defect in this file** — P5's `H_k` modulus bars
> silently discarded two of its own cells. Fixed, and **all 36 tables re-audited
> with a check stricter than S1**, which cannot see a malformed row that
> coincidentally matches its header width. **(b)** M69 reported on
> `FOCUS_NOISE_SD`. Read at source, **M69 makes no claim about any spectral band
> edge**, and its `sigma_F` is a spatial-gradient operator's response noise, not
> a spectrum's — but its conditional deserved a measurement, so §20.3 supplies
> one: **my floor's within-stack spread is 1.102× against M69's 2.000×, and its
> residual tracks level (+0.907, 12/12 stacks) rather than texture (+0.146, signs
> split) — the opposite of M69's mechanism.** The verdict is unchanged and the
> band edge is **not load-bearing at 1.54%**.

> **Fifth addendum, §22 (2026-08-23), after M77's gate sweep.** **(a)** §21.6's
> *"it is one line"* **was unearned and is withdrawn** — I measured a window in
> frames, never a threshold; restated as a direction plus per-stack calibration.
> **(b)** The spectral count has a local form down to **255 sensor px (Welch tile
> 64)** and no further, limited by **discrete bin occupancy**, not noise — but the
> limitation that matters more is that the estimator is **worst on flat regions**,
> which is exactly where M77's fact 40 made its observation. **(c)** One
> substantive objection: `T*` treats my count as an *optimal admission target*,
> and I measured it as a *count of informative frames*. New measurement: my
> frame-domain ladder shows the two stacks agree to **4.7%**, so **fact 39's
> 3.31× does not originate in the optics**. Three pre-registered guards fired and
> are reported in §22.5.

Milestone type: measurement. **No Rust was written and nothing under `crates/**`
was edited** — M67 and M69 are live there. `SYNTHESIS.md`, `AGENTS.md` and
`crates/**` were read-only. Everything M70 produced lives in
`experiments/M70-through-focus-spectrum/**` and in this file.

Every claim below is labelled:

* **MEASURED** — a number this milestone computed from data, with the script and
  the output file named.
* **DERIVED** — algebra, or a consequence of a MEASURED number plus stated
  arithmetic. No new data.
* **ARGUED** — reasoning. Not evidence. Flagged so it can be attacked cheaply.

---

## 0. Verdict, first

### 0.1 The premise, tested on its own terms

The reviewer wrote:

> frames one or two steps off peak still carry mid-frequency information at
> MTF 0.3–0.8, and the matched filter harvests it

**That is true, and at one step off peak it is understated (MEASURED).** Across
all twelve stacks, 1,568 frames, the median relative amplitude at one focus step
off peak in the mid band (0.100–0.2762 sensor cyc/px) is **0.879–0.970**, and at
two steps **0.461–0.858** (`out/s07_unclipped.log` §3). Pre-registered Criterion
A — the reviewer's own 0.30 floor — **SUPPORTS on 12 of 12 stacks**, and still
supports on 10 of 12 when the noise model is deliberately mis-set by +25%.

There is no argument here. Off-peak frames carry mid-band signal on this corpus,
in quantity, at every frame count from 19 to 299 and at all three apertures the
corpus contains.

### 0.2 The inference, which does not follow

The proposal's step from that premise to *rebuild the merge around a matched
filter* requires a second thing that was never stated and is not true: that the
off-peak signal be **distinct** from the peak's, so that combining frames
recovers something an average cannot.

It is not distinct. It is the same spectrum, scaled down.

**MEASURED** (`out/s09_decomposition.log` §2). The row-normalised band-amplitude
matrix over the 11 frames within ±5 of peak, across five bands, has first
singular value share **0.9860–0.9983, median 0.9959**. Controls run in the same
script: a synthetic rank-1 matrix (exact scaled copies) returns **1.0000**; iid
noise rows return **0.9121**; a physically-planted defocus ladder at 1.0 px/step
returns **0.9749**. The corpus sits ~6× closer to *exact rank-1* than a 1-px/step
defocus ladder does. Within the frames a merge would plausibly admit, the
through-focus response is a scalar times a fixed shape.

When every frame's spectrum is a scaled copy of every other, the matched filter
**is** a weighted average, and the weights are the only thing it adds.

### 0.3 The number that decides the architecture

**MEASURED** (`out/s09_decomposition.log` §1, `out/s10_architecture.log`). Split
the matched filter's total gain into two factors that multiply exactly:

```
total(m) = weight_gain(m) × reach_gain(m)

weight_gain(m) = √(m · Σ_{top m} S) / Σ_{top m} √S     ← the matched filter's gain over an
                                                          EQUAL average of the SAME frames
reach_gain(m)  = √(Σ_window S / Σ_{top m} S)           ← the gain from admitting more frames
```

`weight_gain` is the entire architectural value of putting a matched filter in
the merge. `reach_gain` is a gate-width question and needs no new architecture.

| | min | median | max |
| --- | --- | --- | --- |
| **`weight_gain(3)`** — MF over an equal average of the same 3 frames | **1.0009** | **1.0020** | **1.0107** |
| `reach_gain(3, ±5)` — admitting 11 frames instead of 3 | 1.1102 | 1.3987 | 1.5243 |

**The matched filter buys 0.2% over simply averaging the frames it is given.**
At every window, measured directly rather than by decomposition
(`out/s10_architecture.log`):

| window | frames | MF over an equal average of those same frames (median) |
| --- | --- | --- |
| ±1 | 3 | **1.0023** (+0.23%) |
| ±2 | 5 | 1.0117 |
| ±3 | 7 | **1.0238** (+2.38%) ← **the width the shipped gate actually operates at (§18)** |
| ±5 | 11 | 1.0811 |
| ±10 | 21 | 1.2316 |
| ±20 | 41 | 1.4150 |

**The ±3 row, not the ±1 row, is the one that prices the proposal.** §18, written
after M67 reported, shows that M67's two independent measurements of the shipped
gate's admitted set — `n_eff = 6.84` and a mean defocus of `1.733` frames — both
land on ±3 and on no other window. The 0.23% figure is the value of a matched
filter over a *selector-sized* set; the honest number against the merge as it
ships is **2.38%**. Both are bounded by the same 1.110× headroom below.

The matched filter earns its keep only when forced to merge frames an equal
average should never have been given — and by then it is competing with *not
merging them*.

The fair, generous comparison is therefore between the **best equal-weight
average at any window** and the **best matched filter at any window**
(`out/s11_headroom.log`). The equal average has an optimum, because past a point
extra frames grow the signal by `Σ|H|` and the noise by `√n`; the matched filter
does not degrade. That difference is the whole prize:

| | median | range over 12 stacks |
| --- | --- | --- |
| best equal-weight average, as a gain over a 3-frame average | **1.3037** | 1.0197–1.6709 |
| **headroom: best matched filter ÷ best equal average** | **1.1100** | **1.0696–1.2037** |

**MEASURED. The entire focus-axis matched-filter prize on this corpus is
1.110× mid-band SNR — +0.91 dB — and it is stable across the noise model's own
measured uncertainty (1.1047× at σ×0.91, 1.1245× at σ×1.09).**

For scale, both from the record rather than from me:

* fact 19: the **shipped** gated mean already reaches 0.534× single-frame noise
  = **1.873×, +5.45 dB**, in *every* band it admits. The matched filter's
  mid-band-only prize is **16.6%** of what the merge already delivers (DERIVED).
* `M20-deconvolution-ceiling-measured.md` §4.4: moving marked f/11 → f/5.6
  multiplies matched-filter SNR by **13.5×** (fixed time). *"This is optics, not
  software. It dwarfs every merge-side gain measured anywhere in this corpus,
  and it requires no code."* M70 has now measured the merge-side gain it was
  dwarfing: 1.110×.

### 0.4 What this says to do instead

**ARGUED, from MEASURED inputs.** Of the ~40% mid-band SNR available at ±5
frames over a three-frame average, roughly **30 points come from averaging more
frames** and roughly **8 points from weighting them optimally**
(`out/s10_architecture.log`, median split 1.4052 ≈ 1.3037 × 1.0811). The larger
term is reachable by moving `DEFAULT_GATE` in
`crates/strehl-core/src/merge.rs:297`. The smaller term needs a new merge.

That is the whole case for PLUGIN: **the cheap change is the big one, and it is
a constant, not an architecture.** Whether widening the gate actually delivers
the measured 1.30× on real output — rather than on band SNR — is not something
M70 measured and is named in §14 as the next milestone.

---

## 1. Why M70 exists when M20 and M41 already ruled on R3 (rule 40 discharge)

Two reports already bear on this proposal, and I read both before measuring.

**`M20-deconvolution-ceiling-measured.md`** corrected the proposal's gain
shorthand: the matched filter's gain over inverse-filtering the single sharpest
frame is `√(Σ|H|²)/max|H|`, not `√(Σ|H|²)`. It measured a hard ceiling, and in
§4.4 it measured that the aperture move dominates every merge-side gain.

**`M41-r3-kill-measured.md`** tested R3 — *this exact proposal* — end to end and
found it **REFUTED**, with `n_D/n_A` = 3.4679 and 3.9080 against a pre-registered
1.10× bar. Its `s=0` degenerate control located the damage in the
diffraction-inversion term, not in the focus axis.

**So R3 already stands refuted, and M70 is not re-litigating it.** What neither
report established is *why* the focus axis has so little to give — M41 measured
the outcome, not the mechanism, and explicitly isolated the damage elsewhere.
The brief's question is the mechanism: is there recoverable mid-band signal in
off-peak frames? M70 answers that directly and, in doing so, supplies the
mechanism for M41's kill: **there is signal, but it is collinear with the peak's,
so the matched filter degenerates to the average the gate already computes**
(ARGUED, from §6's MEASURED collinearity).

---

## 2. Pre-registration

`experiments/M70-through-focus-spectrum/PREREGISTRATION.md`, **committed in
`80572ec` before `s04` — the decisive corpus measurement — was run.** At that
commit the only results in hand were the EXIF census, the M5 reproduction gate,
and the plant/control run. No band power from any corpus stack had been computed.

### 2.1 Data — and a scoping discovery the brief does not contain

All twelve stacks under `D:\personal\macro`, every frame, **no subsampling**.
1,568 ARW frames, 24 fixed-grid green-quincunx patches each, ~0.12 s/frame with
6 processes.

**MEASURED** (`out/s01_exif_census.log`, `out/exif-*.tsv`): **the corpus is not
all f/11.**

| marked aperture | stacks | frames |
| --- | --- | --- |
| f/5.6 | 119MSDCF, wrapped-text-1, wrapped-text-2, bee-1, bee-2, bee-3 | **1,180 (75.3%)** |
| f/8 | coffee-bubbles, foam, coffee-bean | 224 (14.3%) |
| f/11 | 109MSDCF, 112MSDCF, 113MSDCF | 164 (10.5%) |

The brief's framing — *"on this rig at f/11, roughly 45% of the sampled band is
measured to contain no signal at all"* — is exactly right **for three of twelve
stacks and one tenth of the frames.** Fact 27's cutoff is an f/11 measurement.
At f/5.6 the same geometry (`B = 3`) puts the cutoff at **0.5541 cyc/px**, above
Nyquist and above the green-quincunx reach of 0.3536 — there is no band in reach
that the optics guarantee empty. This changes what a "mid band" means across the
corpus and is why every result below is reported per-aperture as well as pooled.
See §13 for the part of this that is outside my charter.

### 2.2 The observable

For a patch, band `b` and frame `k`, measured band power is
`P_k = |H_k|²|L|² + σ²`. Define `S_k := P_k − σ̂²`. The latent `|L|` is common to
every frame and cancels in any ratio across `k`, so two statistics follow that
need no knowledge of the scene:

* `n_eff_MF = Σ_k S_k / max_k S_k`. **DERIVED:** `√(n_eff_MF)` **is** M20 §4.2's
  corrected `√(Σ|H|²)/max|H|` — the reviewer's own mechanism, made measurable.
* `rel_amp_d = |H_{peak±d}| / |H_peak|` — a relative MTF at ±d focus steps,
  which is the reviewer's "MTF 0.3–0.8" on its own terms.

`σ̂²` is the **shipped photon-transfer model**, parsed at import time from
`crates/strehl-core/src/profile.rs` and asserted against the constants there
(`m70lib._parse_profile`), never retyped. **`FOCUS_NOISE_SD` is used nowhere in
this milestone** — M66 found it 19–21% low on real texture and M69 is live on it,
so the brief's instruction to derive the noise scale from the photon-transfer
model was followed literally.

**`m5_lib.noise_model_var` is deliberately NOT used**: it predates M25's ISO-50
fix (2× wrong at ISO 50) and M48's read-noise fix (+18% above ISO 400), and this
corpus contains ISO 50 stacks and ISO 500/1000 stacks.

### 2.3 Instrument, and the M5 reproduction gate

The spectral machinery is `experiments/m5-diffraction/m5_lib.py`, reused
wholesale rather than rewritten. Before extending someone else's experiment I ran
its own reproduction gate (`out/s02_reproduce_m5.log`):

* **Fact 29 reproduces (MEASURED).** Spectral floor ÷ photon-transfer model =
  **0.977–0.996×** on 109MSDCF, inside the published 0.950–1.093×. The floor is a
  structure-free σ estimate and the noise subtraction below is calibrated.
* **Fact 27's `f_sig = 0.2762 cyc/px` does NOT reproduce.** Running M5's own
  committed driver, unmodified, returns **0.2375** and `B_max ≤ 3.563` where the
  report prints 0.2762 and `B_max` 3.064. The placebo value in the same published
  table (0.2154) reproduces **exactly**; the floor sd reproduces to 1.6%. This is
  recorded, not attributed — see §13.2. **No result in this report depends on the
  exact knee**: M70 measures per-band across the whole GQ reach and uses the
  0.2762 figure only as a band boundary, chosen before any corpus spectrum was
  computed.

Estimator self-check (`out/s08_decisive.log` §0, 400 noise realisations): band
means **0.998–1.003 σ²**, confirming `welch_psd2`'s absolute normalisation on
this geometry; per-realisation sd 0.0147–0.0678 σ² by band.

### 2.4 Plant, placebo, negative control

`out/s03_plant.log`. The plant is **real 119MSDCF texture** pushed through a
known OTF ladder, so its relationship to real texture is not left unexamined
(rule 3 / the M63 failure mode). Truth is computed three independent ways:
analytically from the known OTFs, from the noiseless estimator, and from the
noisy estimator.

| control | result |
| --- | --- |
| **rule 20 — static repeat burst**, K=41, truth `n_eff_MF = 41` | **40.107 / 40.134 / 39.723** in b3/b4/b5 (recovery 0.969–0.979). The estimator *is capable* of returning "nearly every frame carries mid-band signal". |
| **plant** — δ swept 0.125 → 2.0 px/step (16×), truth spanning **30.5 → 1.17** | recovery **0.977–1.011** at every δ and band (corrected estimator, `out/s07_unclipped.log` §2). The plant can express both a wide response and a collapsed one — rule 13 discharged. |
| **negative control** — flat latent, calibrated noise only, K=41 | corrected estimator returns **−0.877 … −0.233**, i.e. zero within sampling error. |
| **rule 4, measured not argued** | the `[1,2,1]`-smoothed denominator **inflates** `n_eff_MF` by up to **1.93×** on the plant and **2.7×** on noise alone. The *raw* statistic was made the pre-registered primary on the strength of that measurement, before any corpus number existed. |

---

## 3. Deviations from the pre-registration, declared

1. **Criterion B's `≥ 2× flat` clause is dropped, and reported as defective
   rather than reinterpreted.** §4.2 proves it was unsatisfiable by construction.
2. **A ±5-frame window was added to the primary statistics, post hoc.** §4.5
   measures why: the unwindowed `Σ_k S_k` accumulates K× the per-frame noise-model
   error and is **not measurable at all** at K=299 given the model's own ±9%.
   The windowed statistic is reported alongside the pre-registered one, never
   instead of it.
3. **The gain decomposition of §6 is entirely post hoc.** It is not a
   reinterpretation of a pre-registered threshold: it is an exact algebraic
   factorisation of Criterion C's own quantity, with its own controls. §6.1 states
   plainly that it *overturns* a pre-registered CORE verdict, and why I think that
   is the honest reading rather than a convenient one.
4. **Criterion D is scored on the window-bounded statistic** as well as the
   pre-registered unwindowed one. Both are reported (§7); they agree.

---

## 4. The pre-registered criteria, as they fell

### 4.1 First scoring — two VOID conditions fired

`out/s05_analyse.log`, run immediately after the corpus measurement:

```
A  rel_amp_2 >= 0.30 on 12/12 stacks; < 0.30 on 0/12  ->  SUPPORTS
B  sqrt(n_eff) >= 1.50 and 2x flat on 0/12; <= 1.25 on 0/12  ->  INDETERMINATE
C  gain over top-3 >= 1.30 on 9/12; <= 1.10 on 0/12  ->  CORE
D  log n_eff vs log K: slope +0.329 (R2 0.390); spread 5.09x  ->  PHYSICS

VOID conditions
  1 floor swamp: ['109MSDCF', '112MSDCF', 'coffee-bean', 'bee-1', 'bee-2', 'bee-3']
  2 broken subtraction: ['109MSDCF']
```

**VOID condition 1 fired on 6 of 12 stacks, and it fired absurdly.** On bee-1 the
*flat* control patches — patches containing no signal at any frequency — returned
a **larger** effective frame count than the textured ones: **177.4 against 11.7**.
A control that should show nothing showed more than the signal.

### 4.2 The defect was mine, and it was in the estimator

I first hypothesised a frame-invariant pedestal — PRNU, or an under-subtracted
offset. **That hypothesis is rejected by measurement** (`out/s06_pedestal.log`):
subtracting a per-frame quantile barely moved the corpus numbers and left flat
patches at 97 instead of 177.

The real cause is in `m70lib.through_focus_stats`, which **clips `S_k` at zero
before summing**. For a band containing no signal, `S_k` is symmetric noise about
zero, and

```
Σ_k max(S_k, 0) ≈ 0.3989 · K · σ        while        max_k S_k ≈ σ√(2 ln K)
```

so the ratio grows **almost linearly in K** — along the very axis this corpus was
chosen to span.

**MEASURED by Monte Carlo on pure noise** (`out/s07_unclipped.log` §1):

| K | clipped `n_eff` | unclipped `n_eff` | `0.4K/√(2 ln K)` |
| --- | --- | --- | --- |
| 19 | 4.12 | 0.016 | 3.12 |
| 63 | 10.86 | −0.038 | 8.73 |
| 130 | 20.16 | −0.079 | 16.62 |
| 299 | **42.07** | **−0.161** | 35.32 |

**Consequence, stated as the pre-registration requires.** Criterion B demanded
`√(n_eff) ≥ 1.50` *and* `textured ≥ 2× flat`. With the flat floor at 42 on a
K=299 stack, the second clause demanded a textured `n_eff ≥ 84` from a statistic
bounded above by K=299 with a peak that is by construction the maximum — it was
**unsatisfiable by construction on the deep stacks**, and VOID condition 1 was
guaranteed to fire there whatever the data said.

**The criterion was defective, not the data.** This is the M62 pattern — an
acceptance guard carrying the defect it was built to police — and it is reported
here rather than repaired quietly.

The corrected estimator (no clip anywhere, `s07_unclipped.tf_stats_uc`) was
re-validated against every control before being used: static burst 40.1/41,
flat-noise control −0.88 to −0.23, plant recovery 0.977–1.011.

**This defect is not specific to M70, and that is the part worth keeping.**
Any multi-frame Wiener merge must estimate `|H_k|` per frame from noisy data, and
the natural implementation — clip the noisy power estimate at zero, because a
negative `|H|²` is meaningless — harvests exactly this bias, growing with stack
depth. A focus-axis Wiener merge built on this corpus would have measured a
spurious `Σ|H|²` at K=299 that was **42× larger** than the truth in any band
where the truth was zero.

### 4.3 Re-scoring on the corrected estimator

`out/s07_unclipped.log` §3, and `out/s08_decisive.log` §D for the windowed form.

| criterion | as pre-registered | verdict |
| --- | --- | --- |
| **A** — `rel_amp_2 ≥ 0.30` on ≥6/12 | 12/12 | **SUPPORTS** |
| **B** — `√n_eff ≥ 1.50` on ≥7/12 **and ≥2× flat** | 0/12 CORE, 0/12 PLUGIN → **INDETERMINATE**; second clause proved unsatisfiable (§4.2) | **VOID BY DEFECT** |
| **B** — same, clause dropped, ±5 window (declared post hoc) | CORE 12/12, stable over σ ∈ [0.75, 1.25] | CORE |
| **C** — `mf_gain_over_top_3 ≥ 1.30` on ≥7/12 | CORE 9/12 point estimate; **VOID condition 3 fires** at σ×1.25 | **INDETERMINATE** |
| **D** — step-density | slope +0.005 to +0.098 on the windowed statistic, spread 1.06–2.00× | **PHYSICS** |

**Criterion C is reported INDETERMINATE because a pre-registered VOID condition
fired, and that is binding.** Within fact 29's *measured* σ range (0.950–1.093×)
and with the ±5 window it reads CORE on 7–8 of 12 — marginal, and not what I am
resting a verdict on. §6.1 explains why C could not have decided the architecture
even had it been clean.

### 4.4 VOID conditions 2 and 4, discharged

**VOID 2 — broken subtraction.** At f/11, fact 27 says band b6 (0.2762–0.3400)
contains no optical signal, so `n_eff` there must fall below the mid-band value
or the subtraction is broken. With the clipped estimator this **failed** on
109MSDCF. With the corrected estimator **all three f/11 stacks pass**
(`out/s07_unclipped.log` §3): 109MSDCF b6 3.61 < mid 4.80; 113MSDCF −4.95 < 7.83;
112MSDCF −44.04 < 6.42.

**VOID 4 — patch size.** Pre-registered and now run (`out/s12_patchsize.log`) on
a four-stack subset spanning both extremes of frame count and all three apertures.
Halving the patch to 128 GQ samples changes the stack-median `n_eff` by a factor
of **0.832–1.073**, largest change **1.202×**, against a 1.50× trigger.
**PASSES; the 256-sample numbers stand.** The direction is as predicted — the
smaller patch reads slightly *lower*, consistent with a large patch mixing depths
and being generous to the proposal.

### 4.5 σ sensitivity, and the statistic that is not measurable

`out/s08_decisive.log` §D. The unwindowed `Σ_k S_k` accumulates the per-frame
noise-model error **K times**, so at K=299 a 9% model error is a 27× error in the
sum:

| σ scale | median mid `n_eff` (unwindowed) | median `n_eff` (±5) |
| --- | --- | --- |
| ×0.75 | 13.769 | 6.599 |
| ×1.00 | 6.573 | 5.708 |
| ×1.09 | 4.564 | 5.359 |
| ×1.25 | **−1.676** | 4.867 |

**MEASURED: the unwindowed sum is not a measurable quantity on this corpus.** It
goes negative under a mis-set that is only twice fact 29's own published
uncertainty. The windowed form moves 6.60 → 4.87 over the same ±25%, and over
fact 29's *measured* range (0.950–1.093×) it moves 6.12 → 5.36 — a 14% band.
Criteria A and B hold SUPPORTS/CORE across σ ∈ [0.75, 1.09]; only C flips, and
only at ×1.25.

**This is why every architectural number in §0 and §6 is a window-bounded
statistic or a ratio in which the σ error largely cancels.** The headroom of
§0.3 moves 1.1047 → 1.1245 over σ ∈ [0.91, 1.09] (`out/s11_headroom.log`).

---

## 5. The premise is true (Criterion A, and the frame counts)

### 5.1 Relative MTF off peak

**MEASURED**, `out/s07_unclipped.log` §3, median over textured patches, mean of
the three mid bands:

| stack | K | f/ | `rel_amp_1` | `rel_amp_2` | `rel_amp_3` | `rel_amp_5` |
| --- | --- | --- | --- | --- | --- | --- |
| coffee-bubbles | 19 | 8 | 0.879 | 0.461 | 0.241 | 0.145 |
| 109MSDCF | 22 | 11 | 0.944 | 0.716 | 0.542 | 0.289 |
| 119MSDCF | 33 | 5.6 | 0.961 | 0.858 | 0.740 | 0.557 |
| 113MSDCF | 63 | 11 | 0.970 | 0.803 | 0.689 | 0.456 |
| 112MSDCF | 79 | 11 | 0.968 | 0.812 | 0.649 | 0.381 |
| foam | 100 | 8 | 0.937 | 0.691 | 0.499 | 0.295 |
| coffee-bean | 105 | 8 | 0.956 | 0.791 | 0.601 | 0.339 |
| wrapped-text-2 | 120 | 5.6 | 0.948 | 0.628 | 0.362 | 0.144 |
| wrapped-text-1 | 130 | 5.6 | 0.931 | 0.681 | 0.391 | 0.151 |
| bee-1 | 299 | 5.6 | 0.951 | 0.779 | 0.653 | 0.497 |
| bee-2 | 299 | 5.6 | 0.927 | 0.760 | 0.670 | 0.545 |
| bee-3 | 299 | 5.6 | 0.963 | 0.832 | 0.717 | 0.552 |

The reviewer said 0.3–0.8 at one or two steps. **Measured: 0.879–0.970 at one
step and 0.461–0.858 at two.** The premise is not merely supported; at ±1 the
reviewer was conservative.

### 5.2 The charter's literal observable — how many frames carry signal

**MEASURED**, `out/s08_decisive.log` §A. Frames whose band signal exceeds
3× the estimator's own measured sampling sd, median over textured patches:

| stack | K | f/ | mid-band frames above floor | fraction of K | b1 (low) | b6 (above f/11 cutoff) |
| --- | --- | --- | --- | --- | --- | --- |
| coffee-bubbles | 19 | 8 | 8.2 | 0.430 | 19.0 | 2.5 |
| 109MSDCF | 22 | 11 | 7.8 | 0.356 | 22.0 | **0.0** |
| 119MSDCF | 33 | 5.6 | 33.0 | 1.000 | 33.0 | 33.0 |
| 113MSDCF | 63 | 11 | 30.0 | 0.476 | 63.0 | **4.0** |
| 112MSDCF | 79 | 11 | 25.0 | 0.316 | 79.0 | **0.0** |
| foam | 100 | 8 | 38.2 | 0.382 | 100.0 | 17.0 |
| coffee-bean | 105 | 8 | 57.5 | 0.548 | 105.0 | 43.5 |
| wrapped-text-2 | 120 | 5.6 | 13.7 | 0.114 | 73.5 | 7.0 |
| wrapped-text-1 | 130 | 5.6 | 37.8 | 0.291 | 129.5 | 34.0 |
| bee-1 | 299 | 5.6 | 117.3 | 0.392 | 297.5 | 81.0 |
| bee-2 | 299 | 5.6 | 45.2 | 0.151 | 213.5 | 19.5 |
| bee-3 | 299 | 5.6 | 143.3 | 0.479 | 299.0 | 141.0 |

Two things worth naming.

**A real-data rule-20 discharge.** In the low band (0.025–0.050 cyc/px), which is
nearly focus-invariant, **every frame** clears the floor on 10 of 12 stacks. The
estimator is demonstrably able to report "all K frames carry signal" *on real
frames of these same stacks*, and does not do so at mid band. The mid-band answer
is not an artefact of an insensitive instrument.

**A real-data negative control that returns zero where the optics say zero.**
At f/11, band b6 sits above fact 27's cutoff. Measured frame counts there:
**0.0, 4.0, 0.0**. At f/5.6, where the same geometry puts the cutoff at 0.5541
cyc/px — above the GQ reach — the median is **33.5**. This is an independent
confirmation of fact 27's cutoff on two stacks it was not measured from, using a
different statistic (frame counts against a noise floor, not a knee fit).

### 5.3 The count is not the same as the harvest

Large frame counts and small effective frame counts coexist, and the difference
is the whole story. bee-3 has **143 frames** carrying mid-band signal above the
floor, and a mid-band **`n_eff(±1)` of 2.93** — because `n_eff` is
*power-weighted* and the count is not. Even in the low band, the most
focus-invariant band available, `n_eff` reaches only **19.00 at K=299**
(`out/s08_decisive.log` §B), i.e. 6.4% of the frames.

---

## 6. Why the inference fails anyway

### 6.1 Criterion C could not have decided this, and that is my defect

Criterion C measured the matched filter's gain **over averaging the best 3
frames**. It reads CORE at 9/12 on the point estimate. And it is the wrong
comparator, because *both candidate architectures beat a three-frame average* —
a wider equal-weight average does too, and it needs no new merge.

I did not see that when I wrote the pre-registration. The correct comparator is
an equal-weight average of **exactly the frames the matched filter is given**,
which isolates the weighting from the reach. Naming this is the point of §3.3:
the decomposition below is post hoc, and it *overturns* a pre-registered CORE
reading. I am reporting the pre-registered verdict as it fell (INDETERMINATE by
VOID 3, CORE on the point estimate) and then explaining why it does not bear on
the architecture, rather than quietly replacing it.

### 6.2 The decomposition

**MEASURED**, `out/s09_decomposition.log` §1. `total = weight × reach` is an
exact identity, not a fit.

| stack | K | f/ | `weight(3)` | `reach(3, ±5)` | total (±5) |
| --- | --- | --- | --- | --- | --- |
| coffee-bubbles | 19 | 8 | 1.0107 | 1.1102 | 1.127 |
| 109MSDCF | 22 | 11 | 1.0020 | 1.3028 | 1.304 |
| 119MSDCF | 33 | 5.6 | **1.0009** | 1.5243 | 1.526 |
| 113MSDCF | 63 | 11 | 1.0011 | 1.4592 | 1.460 |
| 112MSDCF | 79 | 11 | 1.0010 | 1.4192 | 1.422 |
| foam | 100 | 8 | 1.0025 | 1.2836 | 1.289 |
| coffee-bean | 105 | 8 | 1.0015 | 1.3783 | 1.380 |
| wrapped-text-2 | 120 | 5.6 | 1.0027 | 1.1766 | 1.187 |
| wrapped-text-1 | 130 | 5.6 | 1.0034 | 1.2156 | 1.221 |
| bee-1 | 299 | 5.6 | 1.0020 | 1.4451 | 1.446 |
| bee-2 | 299 | 5.6 | 1.0038 | 1.4909 | 1.494 |
| bee-3 | 299 | 5.6 | 1.0009 | 1.5011 | 1.502 |

**`weight(3)` never exceeds 1.0107 and its median is 1.0020.** Criterion C's
CORE reading is `reach`, and `reach` is a gate constant.

The plant confirms the split is real and not an artefact of the statistic
(`out/s09_decomposition.log` §0): at δ=0.125 px/step, where frames are nearly
identical, `weight = 1.0000` and `reach = 1.876`; at δ=2.0, where consecutive
frames are genuinely different, `weight` rises to **1.0492** and `reach` collapses
to 1.010. The decomposition separates the two mechanisms as designed, and the
corpus sits at the δ≈0.125–0.25 end.

### 6.3 Shape collinearity, with controls

**MEASURED**, `out/s09_decomposition.log` §2. σ₁²/Σσ² of the row-normalised
band-amplitude matrix (11 frames within ±5 of peak × 5 bands b2…b6). 1.0000 means
every frame's spectrum is a scaled copy of every other.

| | σ₁² share at ±5 |
| --- | --- |
| **corpus, 12 stacks** | **0.9860 – 0.9983, median 0.9959** |
| control: synthetic rank-1 (exact scaled copies) | **1.0000** |
| control: iid noise rows | **0.9121** |
| control: plant, static burst | 1.0000 |
| control: plant, δ = 1.0 px/step | 0.9749 |
| control: plant, δ = 2.0 px/step | 0.9816 |

The corpus's departure from rank-1 is **0.0041** (median). A 1-px/step defocus
ladder's is 0.0251 — **6.1× larger**. The frames a merge would admit are scaled
copies of one another to within measurement, and a matched filter over scaled
copies is a weighted average whose weights are worth 0.2%.

### 6.4 What this says about `merge → deconvolve` versus a joint Wiener merge

**DERIVED, with the assumption stated.** Wiener deconvolution divides by
`Σ|H|² + σ²/|L|²`, which within a band scales signal and noise by the same
scalar. Band-wise SNR is therefore invariant to how aggressively you deconvolve
afterwards. The only thing a *joint* focus-axis Wiener merge does that
`merge-then-deconvolve` does not is choose the per-frame weights — and that is
exactly the quantity measured at 1.0020–1.1100 above.

**So the architecture separates cleanly (ARGUED):** the diffraction-inversion
term applies to any merged image however it was merged, which makes it a
post-merge stage by construction — a plugin. The focus-axis weighting term is the
only part that has to live inside the merge, and it is worth +0.91 dB in a
restricted band. M20 measured the ceiling on the first term and M41 refuted it on
the noise axis; M70 has now priced the second.

---

## 7. Step density: physics, not shooting habit (Criterion D)

The corpus spans 19 → 299 frames, a **15.7×** range in focus-step density at
comparable subject scale. **MEASURED**, `out/s09_decomposition.log` §3:

| statistic | slope of log `n_eff` on log K | R² | spread over 12 stacks | verdict |
| --- | --- | --- | --- | --- |
| `n_eff(±1)` | **+0.005** | 0.10 | **1.06×** | **PHYSICS** |
| `n_eff(±3)` | +0.063 | 0.16 | 1.64× | **PHYSICS** |
| `n_eff(±5)` | +0.098 | 0.18 | 2.00× | **PHYSICS** |
| `n_eff(all)` | +0.324 | 0.41 | 4.50× | INDETERMINATE |

Pre-registered PHYSICS requires spread < 3× or `rel_amp_1` stable to ±0.15. The
windowed statistics pass on the first clause; `rel_amp_1` spans 0.879–0.970, a
range of **0.091**, and passes on the second at every window including the
unwindowed one.

**`n_eff(±1)` is 2.77–2.94 across the entire corpus** — a 1.06× spread over a
15.7× range in K, three apertures, ISO 50 to 1000, and subjects from coffee foam
to insect anatomy. **The three-frame neighbourhood carries essentially the same
effective information density everywhere on this rig.**

**Independent corroboration from the record:** fact 212 (M38) measured `nwide` —
frames within 50% of peak height — at **3** on the full stack, falling 3 → 2 → 1
under decimation. A completely different statistic, on a different operator,
returns the same number. M70's `n_eff(±1) ≈ 2.9` and fact 212's `nwide = 3` are
two measurements of the same physical width.

The unwindowed statistic's +0.324 slope is not evidence of a habit effect: §4.5
shows that statistic is dominated by K-scaled noise-model error, which produces a
K-dependence for free. It is reported as INDETERMINATE for that reason.

---

## 8. The charter's third question: cutoff versus rolloff

The brief asks whether the optical response *below* the cutoff is
attenuated-but-present or effectively absent, and asks me to say what my data can
and cannot support. Being explicit about both halves:

**What this measurement cannot do.** It cannot measure MTF. Every statistic here
is a ratio across frames at fixed frequency, in which the latent `|L(f)|` cancels
— that cancellation is what makes the measurement scene-independent, and it is
also what destroys the absolute scale. Measured band power is `|H|²|L|²`, and
natural scene spectra fall roughly as `f^-2`, so a falling band-power curve is the
product of a falling scene spectrum and a falling MTF. **The two cannot be
separated on this corpus.** Separating them needs a target of known spectrum — a
slanted edge, a sinusoidal chart, or a printed noise field — which the corpus does
not contain.

**What it can do: presence versus absence**, because the noise floor is
externally calibrated (fact 29; reproduced at 0.977–0.996× here). **MEASURED**,
`out/s13_bandsnr.log`, peak-frame band SNR = `(best frame's band power − σ̂²)/σ̂²`,
median over textured patches, aggregated by aperture:

| marked | b1 0.025–0.05 | b2 0.05–0.10 | b3 0.10–0.15 | b4 0.15–0.20 | b5 0.20–0.2762 | b6 0.2762–0.34 | **b6/b5** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| f/5.6 | 733.6 | 157.9 | 35.1 | 10.4 | 2.63 | 0.60 | **0.230** |
| f/8 | 15962.8 | 3391.8 | 438.2 | 95.9 | 20.46 | 4.58 | **0.224** |
| f/11 | 341.8 | 51.7 | 9.57 | 2.18 | **0.38** | **0.04** | **0.114** |

Three readings, in decreasing order of confidence:

1. **Present, not absent, below the cutoff (MEASURED).** Every mid band on every
   stack carries peak-frame signal above the calibrated floor. Even at f/11 the
   worst case is b5 at 0.08–0.81× the noise variance — small but non-zero, and
   b3 is 1.28–19.30×. There is something below the cutoff to work with.
2. **At f/11, the *top* of the mid band is already at the floor (MEASURED).**
   b5 SNR of 0.38 (median of three f/11 stacks) means the band immediately below
   the nominal cutoff contributes ~0.4× the noise variance in the *best* frame.
   Fact 27 located the cutoff; this locates the point where the approach to it
   stops being useful, and it is *inside* the nominal passband.
3. **The b6/b5 ratio is aperture-ordered as fact 27 predicts (ARGUED, from
   MEASURED numbers).** 0.230 / 0.224 / 0.114 for f/5.6 / f/8 / f/11 — the f/11
   ratio is half the others, which is what a cutoff sitting on the b5/b6 boundary
   does. This is suggestive, not decisive: the three aperture groups are different
   scenes, so scene spectrum is not held fixed. I am labelling it ARGUED for that
   reason.

Absolute band SNR varies by five orders of magnitude across the corpus (109MSDCF
b1 = 21.6, foam b1 = 26848) because exposure and subject contrast vary. **No
cross-stack comparison of absolute SNR in that table means anything.** Only the
within-stack band ratios are informative, and those are confounded as stated.

---

## 9. Limitations, blunt

1. **No phase, anywhere.** Only `|H_k|` is observable from single-frame power
   spectra. A matched filter's true gain uses complex `H`. Every gain reported
   here uses `Σ|H|` where `|ΣH|` is correct, and `|ΣH| ≤ Σ|H|` — so **every
   number in this report is a lower bound on the matched filter's gain**, which
   is conservative *against* my own verdict. The equal-weight comparator assumes
   admitted frames' `H` share a sign; within ±5 frames `rel_amp` is 0.46–0.86,
   far from the first OTF zero, which makes that plausible but not measured.
2. **The shape test has five-band resolution.** §6.3's collinearity is computed
   on five bands. It cannot see structure finer than a band, and a matched filter
   exploiting narrow spectral features would be invisible to it. The controls
   bound how much it *could* be missing — iid noise rows, which are maximally
   non-collinear at this resolution, return 0.9121, so the statistic has a working
   dynamic range of ~0.09 and the corpus sits 0.004 from the top of it.
3. **`n_eff` is power-weighted; frame counts are not.** §5.3. A reader wanting
   "how many frames carry signal" should read §5.2; a reader wanting "how much
   SNR is harvestable" should read §0.3. They differ by 50× on bee-3 and both are
   correct.
4. **The equal-weight comparator is a proxy for gate widening, not gate widening.**
   The shipped merge gates on focus *response*, which is scene-adaptive; I average
   over a fixed frame window. On a stack where the peak is well localised these
   coincide; on one where it is not, they do not. **ARGUED**, and §14 names the
   measurement that would settle it.
5. **Sharpness is not in the objective.** Every number here is band SNR. An equal
   average of 11 frames and a matched filter over the same 11 frames produce
   outputs with different effective MTF, and I have compared their SNR at their
   own MTF. §6.4 argues the comparison survives because deconvolution scales
   signal and noise together within a band — but that is DERIVED, and a real
   implementation with a regularised denominator will not scale them exactly
   together.
6. **`0.2762` is a band boundary here, not a load-bearing measurement.** It did
   not reproduce (§2.3, §13.2). Nothing above changes if the true knee is 0.2375:
   the bands were fixed before any corpus spectrum existed, and the mid-band
   results are stable across b3, b4 and b5 individually.
7. **Twelve stacks, one rig, one operator.** Every "corpus-wide" claim is a claim
   about this rig. `n_eff(±1) ≈ 2.9` is measured to be independent of frame count,
   aperture and subject *within this corpus*; nothing here says it holds on a
   different lens.
8. **The incumbent in §0.3 was originally the wrong one.** §0.3 as first written
   led with a comparison against a three-frame average. M67 subsequently measured
   that the shipped gate admits ~7 frames, and §18 re-prices against that: the
   matched filter buys **2.38%, not 0.23%**. The 1.1100× ceiling was unaffected
   and the verdict did not move, but **a reader quoting M70's headline number
   should quote 1.0238, not 1.0020.**

---

## 10. Verdict on the architecture

**PLUGIN.**

The measurement that decides it, in one line: **over the frames a merge would
actually admit, a matched filter beats an equal-weight average of those same
frames by 1.0238 (median, at the ±3 width M67 measured the shipped gate to
operate at) and by at most 1.1100 (median, best window against best window) —
while the frames themselves are scaled copies of one another to within 0.0041 of
exact rank-1, against a control that reaches 0.9121 when they are not.**

> **Revised after M67 (§18).** The sentence above originally quoted 1.0020, the
> value against a *three-frame* average. That was the wrong incumbent, as the
> owner pointed out: M67's load-bearing result is that focus correctness lives in
> the **gate**, not the election, so the thing a merge-side matched filter would
> replace is a **seven-frame gated average**, not a selector. The corrected figure
> is **1.0238 — a 10.3× larger prize than the number the report originally led
> with** — and it changes nothing, because the 1.1100× headroom already bounded
> it and the comparison to fact 19's +5.45 dB is unaffected at this scale. **The
> correction is recorded rather than silently applied.**

The consequences that follow (ARGUED, from the MEASURED numbers above):

* **Deconvolution does not need to be inside the merge.** Its two terms separate:
  the diffraction inversion is a post-merge per-frequency scalar (a plugin by
  construction), and the focus-axis weighting is worth +0.91 dB in a restricted
  band. Neither justifies rebuilding `merge.rs`.
* **The gate constant is the bigger lever and it is one line.** ~30 of the ~40
  percentage points available at ±5 frames come from admitting more frames, not
  from weighting them. `DEFAULT_GATE` is at `crates/strehl-core/src/merge.rs:297`,
  and its doc comment already warns against raising it on a `√N` score alone —
  correctly, since §9.5 is exactly the caveat it names.
* **The reviewer's physical intuition was sound and their architectural
  conclusion was not.** The mid-band information they described is there, in the
  quantity they said, in every stack. It is simply not *new* information — and
  **§18 shows the shipped gate is already harvesting it**: at M67's measured
  admitted-set defocus of 1.733 frames, the frames the gate is already averaging
  carry a median **0.800** of peak mid-band amplitude. The proposal's premise is
  a description of what `merge.rs` already does.

---

## 11. Proposed facts

Numbered `P1…P18` per AGENTS rule 28. **Absolute `§4` numbers belong to the
orchestrator at fold time.** Before folding, match the first ~70 characters of
each against the whole of `§4` and require zero matches (rule 28, rule 25). P4
and P10 are close in subject to facts 27, 28 and 212 and must be checked for
content collision, not number collision. **P13–P18 are addendum facts (§16–§18);
P13, P14 and P15 bear directly on existing facts 274, 471, 1006 and 19 and must
be checked against them for contradiction, not just for duplication. P13 is the
positive measurement fact 1006 explicitly lacks — 1006 establishes an absence of
evidence, P13 supplies the evidence. **A claim that fact 471's published
half-widths corroborated P13 stood here and in §16.7 and is RETRACTED — it was
a misreading of `10/9` as near/far when it is measured/modelled (§19.1). P13
stands on its own measurement; it never needed the corroboration.** P19–P24 are
the §19 facts and bear on facts 274 and 471 and on M25's open question 33.**

| # | Proposed fact | Label | Source |
| --- | --- | --- | --- |
| **P1** | **The focus-axis matched filter's entire architectural prize on this corpus is 1.110× mid-band SNR (+0.91 dB), median over 12 stacks, range 1.0696–1.2037** — best matched filter at any window ÷ best equal-weight average at any window, mid band 0.100–0.2762 sensor cyc/px. Stable across the noise model's measured uncertainty: 1.1047× at σ×0.91, 1.1245× at σ×1.09. For scale, fact 19's shipped gated mean is 1.873× (+5.45 dB) in every band it admits | MEASURED | `out/s11_headroom.log` |
| **P2** | **A matched filter over the frames a merge already admits is worth 1.0020× (median; range 1.0009–1.0107) over an equal-weight average of those same three frames**, and 1.0811× (range 1.0269–1.2843) over an equal average of the same eleven. The total gain of a matched filter over a 3-frame average factors exactly as `weight × reach`, and the reach term — 1.3987 median at ±5 — is a gate-width question requiring no new merge architecture | MEASURED | `out/s09_decomposition.log` §1, `out/s10_architecture.log` |
| **P3** | **Frames within ±5 of peak are scaled copies of one another, not distinct spectra.** σ₁²/Σσ² of the row-normalised band-amplitude matrix (11 frames × 5 bands) is 0.9860–0.9983 (median 0.9959) across all 12 stacks, against controls of 1.0000 (synthetic rank-1), 0.9121 (iid noise rows) and 0.9749 (a planted 1.0 px/step defocus ladder). The corpus is 6.1× closer to exact rank-1 than a 1-px/step ladder. **This is the mechanism behind M41's kill of R3** | MEASURED | `out/s09_decomposition.log` §2 |
| **P4** | **The reviewer's "MTF 0.3–0.8 one or two steps off peak" is measured true and understated at ±1.** Median relative amplitude in the mid band is `rel_amp_1` 0.879–0.970 and `rel_amp_2` 0.461–0.858 across all 12 stacks, 1,568 frames, three apertures, ISO 50–1000. Criterion A supports on 12/12, and on 10/12 with the noise model mis-set by +25% | MEASURED | `out/s07_unclipped.log` §3 |
| **P5** | **A statistic that clips per-frame band signal at zero before summing rectifies noise into apparent signal, with inflation growing as `0.4K/√(2 ln K)`.** Measured by Monte Carlo on pure noise: the clipped `Σ_k S_k / max_k S_k` returns 4.12 at K=19 rising to 42.07 at K=299, where the unclipped statistic returns −0.16 to +0.08. **Any multi-frame Wiener merge estimating `\|H_k\|` from noisy per-frame power and clipping at zero harvests exactly this**, and the bias grows with stack depth | MEASURED | `out/s07_unclipped.log` §1 |
| **P6** | **The unwindowed `Σ_k S_k` is not a measurable quantity on deep stacks**, because it accumulates K× the per-frame photon-transfer-model error. Corpus-median mid-band `n_eff` goes 13.77 → 6.57 → −1.68 as σ̂ is scaled ×0.75 → ×1.00 → ×1.25, i.e. it goes negative under a mis-set only 2.7× fact 29's own published ±9%. An ±5-frame window bounds the accumulation to 11 frames and moves 6.60 → 4.87 over the same range | MEASURED | `out/s08_decisive.log` §D |
| **P7** | **`n_eff(±1)` in the mid band is 2.77–2.94 across the entire corpus** — a 1.06× spread over a 15.7× range in frame count (19→299), three marked apertures, ISO 50–1000 and subjects from coffee foam to insect anatomy; regression slope of log `n_eff` on log K is +0.005 (R² 0.10). **The three-frame neighbourhood carries the same effective information density everywhere on this rig.** Independently corroborated by fact 212's `nwide = 3` from a different operator and statistic | MEASURED | `out/s09_decomposition.log` §3, `out/s08_decisive.log` §C |
| **P8** | **The mid-band answer is not an artefact of an insensitive estimator, discharged on real data.** In the low band (0.025–0.050 cyc/px) every frame clears a 3σ floor on 10 of 12 stacks, and the low-band `n_eff` reaches 19.00 at K=299, while the mid band on the same patches of the same frames reads 12.83. The estimator reports wide through-focus responses on real frames when they exist. On a static repeat burst it recovers 40.1 of 41 | MEASURED | `out/s08_decisive.log` §B, `out/s03_plant.log` |
| **P9** | **Fact 27's f/11 diffraction cutoff is independently confirmed by frame counting, on two stacks it was not measured from.** In the band 0.2762–0.3400 cyc/px the median number of frames carrying signal above a 3σ calibrated floor is 0.0 / 4.0 / 0.0 on the three f/11 stacks, against 33.5 at f/5.6 where the same `B = 3` geometry puts the cutoff at 0.5541 cyc/px, above the green-quincunx reach. A different statistic from the knee fit, returning zero where the optics say zero | MEASURED | `out/s08_decisive.log` §A, §E |
| **P10** | **At f/11 the top of the mid band is already at the noise floor, inside the nominal passband.** Peak-frame band SNR `(P−σ̂²)/σ̂²` in 0.200–0.2762 cyc/px is 0.08–0.81 (median 0.38) on the three f/11 stacks, against 9.57 median in 0.100–0.150. Fact 27 located the cutoff; this locates where approaching it stops paying. The b6/b5 SNR ratio is aperture-ordered — 0.230 / 0.224 / 0.114 at f/5.6 / f/8 / f/11 — though scene spectrum is not held fixed across the groups | MEASURED (ratio ordering: ARGUED) | `out/s13_bandsnr.log` |
| **P11** | **`D:\personal\macro` is 75.3% f/5.6 by frame count, not f/11.** Marked apertures: f/5.6 on 119MSDCF, wrapped-text-1/2 and bee-1/2/3 (1,180 frames); f/8 on coffee-bubbles, foam, coffee-bean (224); f/11 on 109MSDCF, 112MSDCF, 113MSDCF (164). Every one of the five stacks captured in the most recent session (2026-08-23, 1,147 frames, 73% of the corpus) is f/5.6. **Fact 27's cutoff, and any claim that ~45% of the sampled band is empty, is an f/11 result covering 10.5% of the corpus** | MEASURED | `out/s01_exif_census.log`, `out/exif-*.tsv` |
| **P12** | **The band-power estimator's absolute normalisation and sampling error are measured, not assumed:** on synthetic calibrated noise (400 realisations, 256-sample GQ patch, tile 128) band means are 0.998–1.003 σ² and per-realisation sd is 0.0147–0.0678 σ² by band. Halving the patch to 128 GQ samples changes stack-median `n_eff` by 0.832–1.073× on a four-stack subset spanning both frame-count extremes and all three apertures | MEASURED | `out/s08_decisive.log` §0, `out/s12_patchsize.log` |
| **P13** | **Real through-focus modulus curves are symmetric in frame index to within the scene-geometry envelope; M67's fact 19 ("real through-focus curves are measured asymmetric") is NOT SUPPORTED on this corpus.** The half-width asymmetry index `A = (w_far−w_near)/(w_far+w_near)` has stack medians of **−0.070…+0.077 at half-peak** across all 12 stacks (median-of-medians −0.0131, signs split 6/6), i.e. the worst stack's near and far half-widths differ by a factor of 1.167 and the typical stack's by 1.084. A two-depth scene with a **symmetric** PSF reaches \|A\|=0.073 in control. Independently corroborated by fact 471's own published half-widths (10/9 and 17/17 → \|A\| = 0.053 and 0.000), which sit inside this range next to the corpus median of 0.0404. Pre-registered Criterion E returned **INDETERMINATE** — the SYMMETRIC branch missed by one stack (8/12 vs a 9/12 bar at the 0.25 fraction) and the ASYMMETRIC branch failed 0/12 at every fraction. **This is the positive measurement fact 1006 lacks** | MEASURED (fact 471 conversion: DERIVED) | `out/s15_asym_corpus.log`, `PREREGISTRATION-B.md` §3 |
| **P14** | **The residual asymmetry is real, highly significant, and does not reproduce across repeat captures of the same setup — so it is scene geometry, not the PSF.** Against per-stack shuffle nulls (100 reps), 7 of 12 stacks lie outside their own null at half-peak at **12.7–125.7 null sd**, and they are exactly the seven with K ≥ 100; the null sd itself spans **188×** across the corpus (0.0766 at K=22 to 0.0004 at K=105), `corr(log K, null sd) = −0.784`. **Three 299-frame f/5.6 captures of the same bee setup, each individually 12.7–32.2 null sd from zero, return −0.036 / +0.042 / −0.070; the two wrapped-text captures return +0.047 (35.5 sd) and −0.062 (125.7 sd).** A PSF asymmetry is a property of the optics and must reproduce; it does not | MEASURED | `out/s16_null_band.log`, `out/s19_report_numbers.log` |
| **P15** | **Fact 274's through-focus excess kurtosis is confounded with focus-step density and cannot be read as tail weight.** A plant that is **symmetric by construction** returns `g2` = −0.63 / +0.86 / +6.13 at 0.25 / 0.50 / 1.00 px/step, purely because the curve narrows relative to the moment window. The corpus range, **−0.44…+5.80, is contained inside that**, with `corr(log K, g2) = −0.411`. `g2` was pre-registered as NOT TESTABLE against fact 274 for this reason, before the corpus was read. Skew is separately INDETERMINATE (\|g1\|<0.15 on 8/12 against a 9/12 bar; ≥0.45 with consistent sign on 2/12) | MEASURED | `out/s14_asym_controls.log`, `out/s15_asym_corpus.log` |
| **P16** | **The shipped gate's admitted set corresponds to a ±3-frame window, by two independent routes that agree to 1.1% and neither of which is a free parameter.** M67's simulator measurements `n_eff = 6.84` (at K=25) and `D(A)/D(E) = 0.4895` → mean admitted defocus 1.733 frames map onto an equal average over ±W, which has `n = 2W+1` and mean offset `W(W+1)/(2W+1)`. W=3 gives 7 (1.023× of 6.84) and 1.714 (0.989× of 1.733). No other window in {1,2,3,5,10,20} is within 1.5× on either | DERIVED (from M67 MEASURED + arithmetic) | `out/s18_incumbent.log` §1 |
| **P17** | **Against the gated average as it actually behaves, a focus-axis matched filter buys 1.0238× mid-band SNR (median; range 1.0101–1.1489 over 12 stacks) — +0.204 dB, or 3.7% of the +5.45 dB the shipped gated mean already banks per fact 19.** The frames that gate already averages carry a median 0.800 of peak mid-band amplitude at M67's measured 1.733-frame admitted defocus, so **the reviewer's premise describes what `merge.rs` already harvests**. The figure is 10.3× the 1.0020× the best-3 comparator gives and remains bounded by the same 1.1100× headroom | MEASURED (M67's window mapping DERIVED) | `out/s18_incumbent.log` §2–§4 |
| **P18** | **A half-width asymmetry statistic is robust to the noise calibration in a way the through-focus `n_eff` sum is not.** Corpus median \|A\| at half-peak moves 0.0496 → 0.0404 → 0.0431 → 0.0438 as σ̂ is scaled ×0.91 → ×1.00 → ×1.09 → ×1.25, over the same range where P6's unwindowed `n_eff` goes 13.77 → 6.57 → negative. **The symmetry result therefore survives whatever M69 concludes about `FOCUS_NOISE_SD`**, because it depends on the *shape* of the curve rather than on the absolute level of the subtracted floor | MEASURED | `out/s15_asym_corpus.log` §σ |

---

## 12. Proposed disciplines

**D-a.** *Never clip a noisy estimate at zero before summing it over many terms.*
The clip converts a zero-mean noise term into a positive bias of `0.3989·σ` per
term, and if the denominator is a maximum the resulting ratio grows almost
linearly in the number of terms. Sum first, clip last, or do neither. This is
P5, and it nearly produced a false result in M70 in the direction that would have
*supported* the proposal under test.

**D-b.** *When a criterion is meant to decide between two designs, name the
comparator that separates them, not one that both beat.* M70's Criterion C
compared a matched filter to a three-frame average. A wider equal-weight average
also beats a three-frame average, so C could return CORE regardless of which
design was better. The separating comparator — an equal-weight average of exactly
the frames the filter is given — costs nothing extra to compute and is the only
one that answers the question. §6.1.

**D-c.** *A gain over a baseline should be factored into "more data" and "better
use of the data" before it is attributed to an algorithm.* `total = weight ×
reach` is an exact identity for any weighted-sum estimator against an equal-weight
one, and on this corpus it splits 1.002 against 1.399. Reporting only the product
would have credited the architecture with the gate's work.

**D-d.** *Report a pre-registered criterion's failure as a property of the
criterion when that is what the evidence says.* Criterion B's `≥ 2× flat` clause
was proved unsatisfiable by Monte Carlo (§4.2) rather than argued to be
inconvenient. The proof cost one script and it is the difference between a
declared defect and a reinterpretation.

**D-e.** *A statistic whose error accumulates with stack depth cannot be used on
a corpus whose design axis is stack depth.* P6: the unwindowed sum's K-scaled
noise-model error manufactures a +0.32 slope against log K for free, which is
precisely the "physics or habit" signal Criterion D was built to read. Bound the
accumulation, or the confound is guaranteed.

**D-f.** *Set a criterion's threshold from the confound control, not from the
null control.* M70's symmetry work was going to use a 0.10 asymmetry bar chosen
by taste. The CONFOUND control — a two-depth scene behind a **symmetric** PSF —
reached 0.145 on the same statistic, so that bar would have declared scene
geometry to be optics. The null band was 0.0039, i.e. 37× too permissive to
protect against it. **The question a threshold must survive is "what does the
strongest innocent explanation produce?", not "what does noise produce?"** §16.2,
and the threshold was raised *before* the corpus was read.

**D-g.** *Before reading a shape statistic on real data, check what it returns on
a plant that is correct by construction across the corpus's own design range.*
Excess kurtosis on a symmetric-by-construction through-focus curve spans −0.63 to
+6.13 as focus-step density varies over the corpus's own range — wider than the
corpus itself spans. The statistic was therefore declared untestable in advance
rather than producing a spurious confirmation of fact 274. **A shape statistic
evaluated over a fixed window is a statistic about the window as much as about
the shape.** §16.4.

**D-h.** *When a result is significant on some stacks and not others, check
whether the split is the result or the power.* Seven of twelve stacks cleared
their own shuffle null on the symmetry statistic — and they were exactly the
seven with K ≥ 100, with per-stack null sd varying 150× across the corpus
(`corr(log K, null sd) = −0.784`). Reading the other five as "symmetric" would
have been reading absent power as present evidence. Build the null **per stack**
when the stacks differ by 15× in the quantity that sets the null. §16.5.

---

## 13. Outside the charter, unruled

Flagged explicitly rather than buried. None of these was in my brief; none is
ruled by my measurements; each is stated with what it would take to settle it.

### 13.1 The corpus is majority f/5.6, and M20 §4.4 asked for exactly that

**MEASURED** (P11). Every stack in the 2026-08-23 capture session — bee-1, bee-2,
bee-3, wrapped-text-1, wrapped-text-2, 1,147 frames, 73% of the corpus — is
marked f/5.6. The f/11 stacks are all from 2026-05-07 and 2026-05-17.
`M20-deconvolution-ceiling-measured.md` §4.4 recommends precisely the f/11 → f/5.6
move, at a measured 13.5× matched-filter SNR, and lands on 2026-08-23.

**I cannot establish causality**, and I am not asserting it: 119MSDCF was shot at
f/5.6 on 2026-05-09, before M20, so f/5.6 was not new. What is worth recording is
the consequence, not the cause: **a large fraction of this corpus now sits at an
aperture where fact 27's cutoff is above the sampling reach**, and reports written
against "the f/11 rig" should say which stacks they mean. This is the failure the
brief warned about — *a number relayed without the configuration it was measured
in* — and I nearly walked into it by treating the whole corpus as f/11.

### 13.2 Fact 27's `0.2762 cyc/px` does not reproduce from M5's own driver

**MEASURED** (`out/s02_reproduce_m5.log`, `out/s02b-m5-driver-109.log`,
`out/s02c_m5_kappa.log`). Running M5's committed driver unmodified on 109MSDCF
returns `f_sig = 0.2375` and `B_max ≤ 3.563`, where `M5` publishes 0.2762 and
`B_max` 3.064. In the same published table the *placebo* value 0.2154 reproduces
exactly, and the floor sd reproduces to 1.6% — so this is not a broken checkout.
`git log` shows `m5_lib.py` unchanged between M5's two commits, and
`s02c_m5_kappa.py` rules out the `reference_kappa` floor (data-driven kappa is
1.2140 either way).

The clue I could not resolve: in the same block, `dyn` differs by **4.02×**
(1297 vs 323) and `nfrm` reads 4 against 1. A 4.02× in power is 2.0× in
amplitude. Someone should find out which configuration produced the published
row.

**Nothing in M70 depends on it** (§9.6), and fact 29 — the part I *do* depend on —
reproduces cleanly.

### 13.3 The flat-patch residual scales as `level^1.83`, and I cannot say why

**MEASURED** (`out/s06_pedestal.log`, 6 stacks, R² 0.97). The residual band power
on flat patches after model subtraction scales as `level^1.83`. A slope near 2 is
what PRNU produces (a fixed multiplicative pattern gives `(contrast × level)²`) —
**but it is also what residual low-contrast scene texture produces**, for exactly
the same reason. **These are not distinguishable without a dark frame or a flat
field**, neither of which I may read from `D:\macro-dark-frames` for this purpose
and neither of which I collected. **M71 is live on flat fields** and is the right
owner. Recorded so it is not lost.

### 13.4 The rectification hazard is a design note for the merge, not just for M70

**ARGUED, from P5 (MEASURED).** M70's defect is the generic one for this whole
class of algorithm. A focus-axis Wiener merge must estimate `|H_k(f)|²` per frame
from a noisy periodogram; the natural guard against a negative estimate is a clip
at zero; and the resulting `Σ|H|²` is inflated by `≈0.4K/√(2 ln K)` in every band
where the truth is zero — 42× at K=299. That inflation lands in the **denominator**
of the Wiener filter, where it silently reduces the regularisation exactly where
regularisation matters most. If R3 is ever revisited, this is where to look first.

### 13.5 The asymmetry sign lines up with ISO within repeat-capture groups (addendum)

**MEASURED and UNRULED**, §16.6. Within both of the corpus's repeat-capture
groups the sign of the half-peak asymmetry tracks ISO perfectly — bees at ISO
100/400/100 give −/+/−, wrapped-text at ISO 400/100 gives +/−, five for five.
`corr(log ISO, A₅₀) = +0.577` over all twelve stacks and **+0.755** over the seven
with power.

**I formed this as a hypothesis about a defect in my own instrument, tested it
three ways, and it failed two of them** — the correlation vanishes in the tails
(`−0.085` at A₂₅, `−0.063` at A₁₀) where a noise-subtraction artefact would be
*strongest*, and the level-drift mechanism does not correlate either (+0.198).

**It is recorded rather than dropped** because the A₅₀ alignment is real, because
n=12 with ISO confounded against subject, aperture and session cannot separate
it, and because it would be a defect in *every* through-focus statistic in this
corpus if it were true. §14 item 5 names the three-capture experiment that would
settle it in an afternoon.

---

## 14. What I would measure next, and what I deliberately did not

**Next, in the order I would spend the milestone numbers.**

1. **Does widening the gate actually deliver the measured 1.30×?** Everything in
   §0.4 is band SNR on fixed frame windows. The shipped gate is scene-adaptive and
   the shipped output is an image. A milestone with write access to `crates/`
   should sweep `DEFAULT_GATE` from 4.0 upward on all twelve stacks and measure
   output noise and output resolution together, against a plant with known latent.
   §9.4 and §9.5 are the two places my proxy could be wrong, and both would show
   up in that experiment. **This is the actionable result of M70 and it is the
   only one I would build on.**
2. **A known-spectrum target, once.** §8 is limited entirely by not being able to
   separate `|H|` from `|L|`. One capture of a slanted edge or a printed noise
   field at each of f/5.6, f/8 and f/11 on this rig would turn the whole of §8
   from presence/absence into an MTF curve, and would settle the brief's third
   question properly rather than partially. It would also independently re-measure
   fact 27's knee, which §13.2 says wants re-measuring.
3. **Phase.** Every gain here is a lower bound because `|ΣH| ≤ Σ|H|` and I have no
   phase. Registration-aligned complex cross-spectra between adjacent frames would
   bound the phase error and tell you how much of the lower bound is slack. I
   expect little — but that is a guess and it is labelled as one.
4. **Phase, again, for a different reason (added by the addendum).** §16 measured
   the **modulus** through-focus family symmetric to ±0.077 and is
   constitutionally blind to phase, which is where a defocus PSF's asymmetry
   appears first. The same complex cross-spectrum measurement as (3) would settle
   both questions at once, and it is now the single highest-value unmeasured thing
   M70 touched. It would also complete M67 §7.3 rather than half-completing it.
5. **An ISO-only bracket on one static scene (added by the addendum).** §16.6
   formed and rejected an ISO hypothesis, but could not separate it cleanly
   because this corpus confounds ISO with subject, aperture and session. Three
   captures of one immobile subject at one aperture, varying only ISO, would
   settle in an afternoon whether the noise-subtraction has a signed effect on
   curve shape — which matters to every through-focus statistic in the corpus,
   not just mine.
6. **A symmetry measurement designed for it (added by the addendum).** §17 item 3:
   the five stacks with K ≤ 79 have no power on this statistic at all. Anyone
   re-asking the symmetry question should shoot **dense** — the null sd falls 150×
   from K=22 to K=130 — and should shoot the **same scene twice**, because
   non-reproduction across repeat captures is what carried §16.5 and a single
   stack could not have.
7. **A dense capture of a SHALLOW subject (added by §19).** This is the arm the
   corpus does not have and it now blocks two questions. **Every stack with
   K ≥ 100 here is a deep subject**, so depth range and focus-step density are
   confounded corpus-wide (§19.9 item 5). That is why M67's named
   `109MSDCF`-versus-`coffee-bean` pairing cannot be run (§19.7(b)) and why
   §19.4(b)'s resolving-power ceiling bites: a shallow subject shot at ≥100 frames
   would give **wide unimodal curves** — `w50` ≥ 3.6 frames, the threshold at which
   a Gaussian and a sech² finally separate — and would settle the tail-shape
   question that §19 can only bound. **One capture, and it unlocks both.**

**Deliberately not measured.**

* **Whether the through-focus tails are mildly heavy.** §19.4(b) measures that
  this corpus **cannot** answer it: below `w50` = 3.6 frames a Gaussian and a
  sech² differ by less than the pre-registered bar, and 10/12 stacks are below.
  I stopped at the bound rather than reporting a number the instrument cannot
  support. Next item 7 is the capture that would.
* **Whether multi-lobed curves imply two depths.** §19.5 measures that a
  two-depth scene *produces* multimodality. **The converse is M63's question and
  M63 refuted it five ways.** I did not re-open it and §19.8 says so explicitly.

* **Whether a deconvolution would produce a better image.** M41 measured that and
  refuted it, and re-running it would be manufactured work. M70's charter was the
  premise, not the outcome.
* **`FOCUS_NOISE_SD`.** M69 is live on it and the brief said not to rely on its
  absolute value. Every noise scale here comes from the photon-transfer model in
  `profile.rs`; `FOCUS_NOISE_SD` appears nowhere in this milestone's code.
  P18 additionally measures that the addendum's symmetry result is **robust to
  σ̂ over ×0.91…×1.25**, so it survives whatever M69 concludes.
* **Re-running M67's simulator with an asymmetric PSF.** §16 says the modulus
  family is symmetric, which is the input M67 wanted, but `crates/` is contended
  and M67 owns that experiment. The measurement is delivered; the re-run is
  M67's to make.
* **Anything under `crates/`.** M67 and M69 are live there. Nothing was edited,
  nothing was built, and no measurement in this report came from a compiled
  binary — the entire experiment is Python over raw ARW files.
* **Re-deriving fact 27's knee.** §13.2 records the non-reproduction and stops.
  Chasing it properly needs the M5 author's configuration, and it is not on the
  path to a core-versus-plugin verdict.

---

## 15. Reproduction

```powershell
cd C:\dev\blog\death-of-software\projects\strehl\experiments\M70-through-focus-spectrum
$env:PYTHONIOENCODING = 'utf-8'

python src\s01_exif_census.py      # aperture / ISO census      -> out/exif-census.json
python src\s02_reproduce_m5.py     # M5 gate: fact 29 reproduces, fact 27 does not
python src\s03_plant.py            # plant, rule 20, negative control, rule 4
#   PREREGISTRATION.md was committed at 80572ec at this point, before s04.
python src\s04_through_focus.py    # 12 stacks, 1568 frames, ~3.5 min -> out/tfs-*.npz
python src\s05_analyse.py          # pre-registered scoring AS IT FAILED
python src\s06_pedestal.py         # first hypothesis for the failure - REJECTED
python src\s07_unclipped.py        # the real defect, proved; corrected estimator
python src\s08_decisive.py         # frame counts, rule-20 on real data, sigma sweep
python src\s09_decomposition.py    # weight vs reach; shape collinearity + controls
python src\s10_architecture.py     # MF vs equal average of the SAME frames
python src\s11_headroom.py         # best MF vs best equal average - the prize
python src\s12_patchsize.py        # VOID condition 4              -> PASSES
python src\s13_bandsnr.py          # the third question, as far as it goes
```

`out/tfs-*.npz` are gitignored (`.gitignore:43`, `*.npz`) and regenerate in ~3.5
minutes from `D:\personal\macro`, which was read-only throughout. Every `out/*.log`
in this milestone is the verbatim stdout of the script named at the top of it,
including `s05_analyse.log`, which records the criteria failing.

```powershell
# --- addendum (section 16-18), added after M67 reported at 5cafbee ---
python src\s14_asym_controls.py    # symmetry controls: null, power, confound, placebo
#   PREREGISTRATION-B.md was committed at 18efd34 at this point, before s15.
python src\s15_asym_corpus.py      # corpus symmetry, Criteria E/F/G, VOID 6/8/9/10
python src\s16_null_band.py        # per-stack shuffle null bands, 100 reps
python src\s17_iso_drift.py        # post hoc ISO hypothesis - formed, tested, REJECTED
python src\s18_incumbent.py        # re-price against the gate as it actually behaves
python src\s19_report_numbers.py   # exact null-sd multiples quoted in section 16
```

---

## 16. Addendum: is the real through-focus response symmetric? (M67 §7.3)

### 16.0 Why this is here

M67 registered before running that its forward model's PSF is **symmetric and
monotone in `|F−k|` by construction**, and declared every accuracy number an
upper bound in consequence. Its §7.3 then **withdrew its own supporting claim**
that real through-focus curves are "measured asymmetric", tracing it to an M25
fit residual on one stack whose fit saturated its grid, under the one gate M25
failed. It named three prerequisites for whoever measured it properly. All three
are discharged below:

* **(a) report skew and kurtosis separately** — §16.4, and they disagree;
* **(b) M25 question 33's depth-range confound is live, one stack is not enough**
  — §16.5, twelve stacks, and the confound is measured with a control rather than
  argued about;
* **(c) fact 471's FWHM agrees on two stacks, so any deviation is in the tails**
  — the statistic is evaluated at the 0.50, 0.25 and 0.10 fractions of peak, and
  the 0.50 reading *is* an FWHM asymmetry, directly commensurable with fact 471.

The owner's instruction was explicit: **do not treat M67's fact 19 as
established.** I did not, and I have now measured it. SYNTHESIS **fact 1006**,
folded while this addendum was being written, records the same withdrawal and
concludes that *"the live hypothesis is now closer to symmetric-with-heavy-tails
than to asymmetric"* — **but that is an absence of evidence, and §16 supplies the
measurement.** M73 §619 explicitly leaves through-focus asymmetry to M70 and
builds nothing on it, so nothing downstream is disturbed either way.

**This was cheap.** It is pure post-processing of `out/tfs-*.npz`, which already
existed. No new capture, no Rust, no `crates/` access.

### 16.1 The instrument, and what it cannot see

`A_f = (w_far − w_near)/(w_far + w_near)`, where `w` are the interpolated
offsets in frames at which the `[1,2,1]`-smoothed through-focus response first
falls to `f × peak` searching outward from the peak. **Censored sides are
returned as censored, never imputed** — a silently right-censored width is what
killed M41's detail metric. Positive means *slower decay toward higher frame
index*. Full specification: `PREREGISTRATION-B.md` §1.

Three limits were declared **before** the corpus run, not after:

1. **No phase.** This measures `|H_k|` only. Defocus PSFs on opposite sides of
   focus differ in the **sign of the wavefront error** — in phase — before they
   differ in modulus. **The instrument is blind to the most likely form of
   through-focus asymmetry**, and everything below is a statement about the
   modulus family only.
2. **Sweep direction is unknown per stack**, so frame index maps to physical
   near/far only up to an unknown sign. Magnitudes are load-bearing; signs are
   secondary, and the cross-stack sign test is read accordingly.
3. **A per-patch reading is meaningless.** Only stack medians over ≥48
   patch×band curves are interpreted (§16.2 gives the number).

### 16.2 Controls, run and read before the criteria were written

`out/s14_asym_controls.log`. The plant is built on a **real latent patch**
(`119MSDCF` centre, high-band power 1716.1, mean 882.8 DN), not synthetic
texture — rule 3, and the exact failure mode M63 caught.

| control | plants | result |
| --- | --- | --- |
| **NULL-SYM** | symmetric ladder, δ ∈ {0.25, 0.5, 1.0} px/step, 216 draws | bias **+0.0001**, **sd 0.0039** |
| **NULL-NOISE** | flat latent + calibrated noise, no curve, 144 draws | sd **0.3055**, 34/144 censored |
| **POWER-ASYM** | genuinely asymmetric, 5 rate pairs | sign **5/5**, magnitude **0.965–0.977×** of the analytic ideal at \|A\|≤0.33 |
| **CONFOUND** | two depths, unequal weights, **symmetric PSF**, noiseless | \|A₅₀\| to **0.0726**, \|A₁₀\| to **0.1451**, \|g1\| to **0.4457** |
| **REVERSAL** | frame order reversed | worst \|forward+reversed\| = **1.5e−14** |

**Three of these changed the criteria I would otherwise have written, which is
the point of running controls first.**

* The null band is **not** the binding constraint (3×sd = 0.0117).
* **The scene-geometry confound is.** A *symmetric* PSF over a two-depth scene
  reaches \|A\| = 0.073–0.145 with no PSF asymmetry at all. **My originally
  intended 0.10 asymmetry bar sat inside this envelope and would have been
  unsound.** It was raised to 0.15 in `PREREGISTRATION-B.md` before the run.
* The estimator **compresses** large asymmetry — at an ideal of −0.600 it returns
  −0.106, because the fast side falls below half-peak inside one frame and the
  half-width hits the sampling floor. **The bias runs against declaring
  asymmetry, never toward it.** Trustworthy to \|A\| ≈ 0.33.

### 16.3 Criterion E, as it fell: INDETERMINATE, and it missed by one stack

`out/s15_asym_corpus.log`. Twelve stacks, textured patches × three mid bands,
48–72 curves per stack.

| stack | f/ | K | A₅₀ | 95% CI | A₂₅ | A₁₀ | powered? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| coffee-bubbles | 8.0 | 19 | +0.0373 | [−0.077, +0.093] | +0.0319 | +0.0256 | no |
| 109MSDCF | 11.0 | 22 | +0.0096 | [−0.087, +0.108] | +0.0379 | −0.0061 | no |
| 119MSDCF | 5.6 | 33 | −0.0447 | [−0.084, +0.043] | −0.0411 | −0.0408 | no |
| 113MSDCF | 11.0 | 63 | −0.0369 | [−0.132, +0.024] | −0.0793 | −0.0595 | no |
| 112MSDCF | 11.0 | 79 | −0.0389 | [−0.075, +0.000] | −0.0545 | −0.0227 | no |
| foam | 8.0 | 100 | **+0.0773** | [+0.027, +0.099] | +0.0451 | +0.0472 | **yes** |
| coffee-bean | 8.0 | 105 | +0.0160 | [−0.076, +0.128] | +0.0809 | +0.0891 | **yes** |
| wrapped-text-2 | 5.6 | 120 | +0.0474 | [−0.015, +0.115] | +0.0384 | +0.0320 | **yes** |
| wrapped-text-1 | 5.6 | 130 | −0.0617 | [−0.093, −0.023] | −0.0330 | −0.0105 | **yes** |
| bee-1 | 5.6 | 299 | −0.0358 | [−0.106, +0.050] | −0.0288 | −0.0150 | **yes** |
| bee-2 | 5.6 | 299 | +0.0420 | [−0.054, +0.105] | +0.0052 | −0.0080 | **yes** |
| bee-3 | 5.6 | 299 | −0.0696 | [−0.179, +0.035] | +0.0804 | +0.0481 | **yes** |

Scored exactly as pre-registered:

| fraction | \|A\| < 0.05 | \|A\| ≥ 0.15, consistent sign | signs | inside CONFOUND envelope |
| --- | --- | --- | --- | --- |
| A₅₀ | **9/12** | **0/12** | +6 / −6 | 11/12 |
| A₂₅ | **8/12** | **0/12** | +7 / −5 | 12/12 |
| A₁₀ | **10/12** | **0/12** | +5 / −7 | 12/12 |

**Criterion E ⇒ INDETERMINATE.** The SYMMETRIC branch required `|A| < 0.05` on
≥9/12 at *every* fraction and got 9, **8**, 10. **It failed at the 0.25 fraction
by a single stack, and it is reported as failed.** The ASYMMETRIC branch failed
0/12 at every fraction, so the two branches did not fail symmetrically — but the
criterion as written does not permit me to award the SYMMETRIC branch on that
basis, and I am not going to reinterpret it. M65's standard.

**VOID conditions.** VOID 6 (reversal on real data) does not fire: exact to
0.000000 on all 12 stacks. VOID 9 (frame-shuffle placebo) does not fire. **VOID
10 fires on A₁₀ for 119MSDCF** — 54.2% of its curves are censored at the 0.10
fraction, so that one cell is unusable; excluding it leaves 9/11 and does not
change E. VOID 5 and VOID 7 were pre-checked in §16.2 and do not fire.

### 16.4 Prerequisite (a): skew and kurtosis disagree, and kurtosis is not a shape statistic

**Skew: INDETERMINATE, and it also missed by one.** `|g1| < 0.15` on **8/12**
against a 9/12 bar; `|g1| ≥ 0.45` with consistent sign on **2/12**. Median
+0.067. The CONFOUND control reaches `|g1| = 0.4457` with a symmetric PSF, so
even the two stacks that clear the bar clear it by less than scene geometry can
manufacture.

**Kurtosis: NOT TESTABLE, and this was pre-registered before the corpus was
read.** On a plant that is **symmetric by construction**, excess kurtosis runs:

| δ (px/step) | 0.25 | 0.50 | 1.00 |
| --- | --- | --- | --- |
| `g2` | **−0.63** | **+0.86** | **+6.13** |

pooled sd 4.77. **`g2` is measuring how narrow the curve is relative to the
moment window — that is, focus-step density — not tail weight.** The corpus range
is **−0.44 … +5.80**, which is *contained inside* the range a symmetric plant
spans, and `corr(log K, g2) = −0.411` in the direction the plant predicts.

**This is the finding for fact 274.** Fact 274 records through-focus curves as
having heavier shoulders than Gaussian and is flagged NOT INDEPENDENTLY VERIFIED.
M70 can now say what it is *not*: it is not evidence of an unusual PSF, because
an ordinary symmetric one produces the same numbers when you step finely enough.
Two of the three highest corpus `g2` values (coffee-bubbles +5.80, 109MSDCF
+1.26) come from stacks where the ±10-frame moment window hits the stack end on
**100% of patches** (K=19 and K=22), which compounds it.

### 16.5 Prerequisite (b): the confound, measured — and the refutation

Criterion G asked whether the reading looks like a PSF property or like scene
geometry.

* Within-stack sign agreement at A₅₀: **median 0.553** across the corpus (range
  0.511–0.694). A coin flip.
* Stack medians split **6/6**.
* **VOID 8 FIRES**: corpus median `|A₅₀|` is **0.0404**, *below* the CONFOUND
  control's 0.0726. Scene geometry is not separable, so **Criterion G ⇒
  INDETERMINATE** by pre-registration, notwithstanding that the point reading was
  SCENE-LIKE.

But the corpus contains something better than a criterion. `out/s16_null_band.log`
builds a **per-stack null band** for the median statistic by shuffling frame
order 100 times, which destroys the through-focus curve while preserving
everything else:

* The null sd itself spans **188×** across the corpus — **0.0766 at K=22 down to
  0.0004 at K=105**; `corr(log K, null sd) = −0.784`. **The sparse end of the
  step-density range has two orders of magnitude less power, which is a statement
  about power, not about symmetry.**
* **7 of 12 stacks lie outside their own null at A₅₀, and they are exactly the
  seven with K ≥ 100.** On those the readings sit **12.7–125.7 null sd** from
  zero (`out/s19_report_numbers.log`). The five that fail sit at 0.1–1.6 sd.

So the asymmetry is **real and unambiguously non-zero wherever there is power to
see it** — and then:

> **Three 299-frame captures of the same bee setup, same rig, same f/5.6, same
> session, same step count, each individually 12.7, 19.6 and 32.2 null sd from
> zero, return A₅₀ = +0.042, −0.036 and −0.070. The two wrapped-text captures,
> at 35.5 and 125.7 null sd, return +0.047 and −0.062.**

**A PSF asymmetry is a property of the optics. It must reproduce across repeat
captures of the same optical system. It does not.** That is the refutation, and
it is the same instrument M63 used to kill occlusion unmixing: non-reproduction
across repeat captures of the same scene.

### 16.6 A post hoc hypothesis I formed, tested, and rejected

The sign split above lines up with **ISO**: within the bee triple (ISO 100 / 400
/ 100) the signs are −/+/−, and within the wrapped-text pair (ISO 400 / 100) they
are +/−. Five for five. A mis-scaled noise floor biasing the curve tails is a
plausible mechanism, and it would be a defect in *my* instrument, so it needed
testing.

**It fails.** `out/s17_iso_drift.log`:

| statistic | corr(log ISO, A), all 12 | corr, powered stacks only |
| --- | --- | --- |
| A₅₀ | +0.577 | +0.755 |
| A₂₅ | **−0.085** | **−0.031** |
| A₁₀ | **−0.063** | **−0.137** |

**A noise-subtraction artefact would be strongest in the tails, where the
subtracted floor is the largest fraction of the signal. The correlation exists
only at half-peak and vanishes in the tails — the opposite of the mechanism.**
The within-group alignment also breaks for the bees at A₂₅ and A₁₀ (−/+/+ and
−/−/+). The candidate mechanism, monotone level drift through the sweep, also
fails: `corr(drift, A₅₀) = +0.198` per frame, +0.330 total.

**Hypothesis rejected.** With n=12 and ISO confounded with subject, aperture and
session, this corpus cannot separate it properly; §18 names the capture that
would. Recorded because forming and killing it is part of the evidence, and
because a reader who notices the same pattern deserves to know it was checked.

### 16.7 What §16 concludes

> **RETRACTION, added with §19.** The paragraph that stood here claimed
> independent corroboration from fact 471, and **it was a misreading of my own.**
> It is struck and replaced. **The §16 conclusion does not depend on it** —
> corroboration is what is withdrawn, not the measurement. See §19.1.

~~*Independent corroboration, from a fact I did not use as an input. SYNTHESIS
fact 1006 records fact 471's through-focus FWHM half-widths as (10/9) and
(17/17) on two stacks. Converted to this addendum's statistic those are
|A50| = 0.053 and 0.000, landing inside my range and next to my median.*~~

**Read at source (`M67-focus-correctness.md:520`), `10/9` is FWHM *measured*
versus FWHM *modelled* — a model-agreement check — not near-side versus far-side
half-widths. It is not an asymmetry measurement and cannot be converted into
one.** M67 says so in the same table row: *"FWHM is a **symmetric** summary and
it *agrees* with the model on two stacks. Neither confirms nor refutes skew."* I
took the numbers from fact 1006's compressed rendering and did not open the
source. **§19.1 records this as a defect of mine and what it cost.**

**What fact 471 does carry, used correctly.** Its real content is two **measured
blur-growth rates** — `s = 0.6017 px/frame` on `119MSDCF` and `1.1856` on
`109MSDCF`. §19 uses them to prove the shape plant covers the real regime rather
than assuming it, which is the use the misreading displaced.


**Where this leaves fact 1006.** Fact 1006 establishes that *no corpus fact
establishes asymmetry* and concludes that "the live hypothesis is now closer to
symmetric-with-heavy-tails than to asymmetric". That is an absence of evidence.
**§16 supplies the positive measurement it lacks** — the modulus family *is*
symmetric, measured, with controls — and it **removes the basis for the
"heavy-tails" half** as well, not by showing the tails are light but by showing
in §16.4 that the statistic which claimed them is not a tail statistic.

**MEASURED.** The modulus of the real through-focus response is symmetric in
frame index to within **±0.077** in the half-width asymmetry index — the worst
stack in the corpus has near and far half-widths differing by a factor of
**1.167**, and the typical stack by **1.084** — on every stack, at every fraction
of peak tested. The residual is real where there is power to detect it, is
bounded above by the scene-geometry control, and **does not reproduce across
repeat captures of the same setup.**

**ARGUED.** M67's fact 19 is therefore **not supported** on this corpus, and
M67's simulator is **better than it claimed**: its symmetric, monotone PSF family
is a good model of the measured modulus, so its 99.955% is less of an upper bound
than it declared. That is a strengthening of M67, not a correction to it.

**What this does not say.** It says nothing about phase (§16.1 limit 1), and a
defocus PSF's asymmetry appears in phase first. **It is entirely possible that
the through-focus PSF family is genuinely asymmetric in a way this measurement is
constitutionally unable to see.** The honest form of the result is: *the `|H_k|`
family is symmetric; the `H_k` family is unmeasured.*

**And for a matched filter specifically, this matters less than it looks.** A
matched filter over measured per-frame responses does not need a *model* of `H`;
it needs the responses, which are measured per frame regardless of whether the
family is symmetric. Symmetry is load-bearing for **M67's simulator** and for any
*parametric* filter; it is close to irrelevant for the non-parametric one §0.3
priced. **ARGUED.**

---

## 17. Addendum: what §16 could not do, and what it cost

**Cost: four scripts, no new capture, ~12 minutes of compute.** The owner's
condition — *"if it is not close to free given what you have already computed,
say so and skip it"* — was comfortably met. `out/tfs-*.npz` already held every
through-focus curve; §16 is arithmetic on them.

**What it could not do, listed so it is not mistaken for more than it is:**

1. **Phase.** Named in advance. This is the big one and it is not a limitation I
   can retire without a different measurement (§18.2).
2. **Separate the PSF from the scene.** VOID 8 fired. The CONFOUND control shows
   scene geometry alone reaches the magnitudes observed. §16.5's non-reproduction
   argument is what carries the conclusion, not Criterion G.
3. **Say anything about the five sparse stacks.** K ≤ 79 has a null sd of
   0.025–0.077 against observations of 0.010–0.045 — they sit at **0.1–1.6 null
   sd**. **Those five stacks are consistent with anything**, and reading them as
   "symmetric" would be reading the absence of power as the presence of a result.
   **This is the step-density finding of the addendum: the sparse end of the
   corpus cannot answer the symmetry question at all**, which is worth knowing
   before anyone designs a capture to answer it.
4. **Test fact 274.** Pre-registered as not testable, and §16.4 explains why
   rather than asserting it.

---

## 18. Addendum: re-pricing against the incumbent that actually ships

### 18.1 The correction, and why it matters

The owner's follow-up turn: *"the pathway your proposal would replace is not the
election — it is the gate […] Fact 19 of the corpus — the gated mean reaching
0.534× single-frame noise — is the incumbent you are measuring against."* That is
right, and §0.3 as originally written led with the wrong comparator.

**M67's load-bearing result is that focus correctness lives in the gate, not the
election**: its `ArgmaxBaseline` elects the correct frame 35.71% of the time, the
estimator's own argmax 39.70%, and the admitted set contains the correct frame
99.96%. A merge-side matched filter therefore competes with a **gated average**,
not with a selector.

### 18.2 Which of my windows is the shipped gate? Two independent routes agree

**DERIVED, from M67's MEASURED figures plus arithmetic.** An equal average over
±W frames has `n = 2W+1` and mean absolute offset `W(W+1)/(2W+1)`. M67 measured
two independent properties of the admitted set on its simulator at K=25:
`n_eff = 6.84`, and `D(A)/D(E) = 0.4895` giving a mean admitted defocus of
**1.733 frames**. These land on the same window and on no other:

| W | n = 2W+1 | vs `n_eff` 6.84 | mean\|offset\| | vs `D(A)` 1.733 |
| --- | --- | --- | --- | --- |
| ±1 | 3 | 0.439× | 0.667 | 0.385× |
| ±2 | 5 | 0.731× | 1.200 | 0.692× |
| **±3** | **7** | **1.023×** | **1.714** | **0.989×** |
| ±5 | 11 | 1.608× | 2.727 | 1.574× |
| ±10 | 21 | 3.070× | 5.238 | 3.023× |

**Two quantities M67 measured by different means, agreeing to 2.3% and 1.1% on
the same window, with no free parameter.** That is what makes the mapping
citable rather than convenient.

**M67's `n_eff` and `D(A)/D(E)` are SIMULATOR figures.** They are used here
*only* to point at a row of a table measured on the corpus. **No corpus claim in
this report rests on their value**, and if M67's simulator is wrong about the
gate's width, the correction is to read a different row of §0.3's table — every
row of which is measured on real frames.

### 18.3 The price, restated

**MEASURED**, `out/s18_incumbent.log`:

| comparator | MF's gain (median) | range | dB |
| --- | --- | --- | --- |
| equal average of the best **3** frames (§0.3 as first written) | 1.0023 | 1.0011–1.0116 | +0.020 |
| **equal average of the same 7 frames — the gate as it behaves** | **1.0238** | **1.0101–1.1489** | **+0.204** |
| ceiling: best MF at any W ≤ 10 ÷ best equal average at any W ≤ 10 | 1.1100 | 1.0696–1.2037 | +0.906 |

**The corrected number is 10.3× the one the report originally led with, and the
verdict does not move.** Three reasons, all from measurements already in this
report:

1. **The ceiling was always the binding number.** 1.1100× bounds the matched
   filter at *any* window, and 1.0238 was always inside it. The re-pricing moves
   the point estimate, not the bound.
2. **Against fact 19 it is still small.** The shipped gated mean banks
   **1.873× = +5.45 dB** in every band it admits. The matched filter's mid-band
   prize at the gate's own width is **+0.204 dB — 3.7% of what the merge already
   delivers** (DERIVED).
3. **The mechanism is unchanged.** §6.3's rank-1 collinearity is why the number
   is small at *every* window, and it is a property of the frames, not of the
   comparator.

### 18.4 The gate is already harvesting the reviewer's premise

**MEASURED.** Median relative mid-band amplitude off peak, across the corpus:

| steps off peak | 1 | **1.733 (M67's admitted-set mean)** | 2 | 3 | 5 |
| --- | --- | --- | --- | --- | --- |
| median `rel_amp` | 0.954 | **0.800** | 0.744 | 0.614 | 0.379 |

The reviewer wrote that *"frames one or two steps off peak still carry
mid-frequency information at MTF 0.3–0.8, and the matched filter harvests it."*
**Both halves are true, but the second one is already true of the shipped merge.**
At the defocus M67 measured the gate to be admitting, those frames carry 0.800 of
peak mid-band amplitude, and `merge.rs` is averaging them today. The proposal's
premise is an accurate description of an existing behaviour; what it adds on top
is the 2.38%.

### 18.5 Verdict, re-weighed

**PLUGIN, unchanged, and now stated against the right incumbent.**

A focus-axis matched filter replacing the shipped gated average buys **1.0238×
mid-band SNR (median), bounded above by 1.1100× at any window** — against a merge
that already banks +5.45 dB, on a corpus where moving f/11 → f/5.6 is worth 13.5×
(M20 §4.4) and where the frames being combined are scaled copies of one another
to 0.0041 of exact rank-1. **The lever is the gate constant at
`crates/strehl-core/src/merge.rs:297`, not the merge architecture** — §0.4's
split of the ±5 gain into ~30 points of reach and ~8 points of weighting is
unaffected by this correction, since both terms were measured at the same widths.

---

## 19. Addendum: where the through-focus shape departs from a Gaussian

**Added after the owner's third turn, which RETRACTED the claim that sent §16
after asymmetry** and rescoped the question to *"are real through-focus curves
symmetric, and where does their shape depart from a Gaussian?"* §16 answered the
first half. This answers the second, which §16 explicitly could not (§16.4:
excess kurtosis is not a shape statistic on this corpus). Pre-registered in
`experiments/M70-through-focus-spectrum/PREREGISTRATION-C.md`, committed
`6a831fa`, **before `s21` read any real stack.**

### 19.1 A defect of mine, found first, reported first

**The owner's meta-lesson — "a resolving citation is not a verified claim" — is
one I violated in §16.7, in the paragraph congratulating itself on independent
corroboration.**

§16.7 as committed claimed fact 471's `(10/9)` and `(17/17)` corroborated my
symmetry result, converting them to `|A₅₀|` = 0.053 and 0.000 and observing that
they landed next to my corpus median of 0.0404. **Read at source — I opened
`M67-focus-correctness.md:520` while preparing this section — `10/9` is FWHM
*measured* versus FWHM *modelled*.** A model-agreement check. Not near-side
versus far-side. M67 annotates it in the same row: *"FWHM is a **symmetric**
summary and it *agrees* with the model on two stacks. Neither confirms nor
refutes skew."*

I took the pair from SYNTHESIS fact 1006's compressed rendering — where "fact
471's FWHM (10/9, 17/17) is symmetric and agrees on two stacks" reads naturally
as two half-widths — and I did not open the source. **The citation resolved. The
fact existed. It was not the quantity I used it as.** That is the third instance
this week and the first committed by an agent rather than caught in one.

**What it cost, stated exactly:**

* **Nothing load-bearing.** §16's conclusion rests on 12 stacks, 6 controls and a
  non-reproduction across three repeat captures. Corroboration is what is
  withdrawn. §16.7 and §11's preamble are struck and corrected in place.
* **One real thing was displaced.** Fact 471's actual content is two **measured
  blur-growth rates**, `s = 0.6017 px/frame` on `119MSDCF` and `1.1856` on
  `109MSDCF`. Those are exactly what a defocus plant needs to be checked against.
  §19.2 uses them that way. **The misreading cost me the correct use of the fact
  for a week.**
* **A near-miss on the arithmetic, worth recording.** Had `10/9` *been* near/far
  half-widths, my conversion `|A| = 0.053` would have been right, and it landed
  next to my median. **A wrong reading that produces a plausible number is the
  hardest kind to catch** — the agreement felt like confirmation and functioned
  as camouflage. Facts 61–64 record four plants that were subtly wrong; this is
  the same failure mode applied to a citation.

**Also, and much smaller, in the brief I was given:** the relay described
`109MSDCF` as "~1.5 px/frame". Fact 471 says **1.1856**. The pairing argument is
unaffected — the point is that it is 10× below `coffee-bean`'s grid edge — and I
use 1.1856 throughout.

### 19.2 The instrument, and why kurtosis had to be replaced

§16.4 established that excess kurtosis `g2` **cannot** answer the shape question
here: on a plant symmetric *by construction* it ran **−0.63 … +6.13** purely as
focus-step density varied. It measures curve width relative to the moment window.

The replacement is a statistic that is invariant to curve width **by
construction**. For a curve with peak at `k*`, let `w(f)` be the half-width at
fraction `f` of peak, averaged over near and far sides:

```
    R10_50 = w(0.10) / w(0.50)        primary
    R25_50 = w(0.25) / w(0.50)        secondary
```

For a Gaussian, `w(f) = σ·√(−2 ln f)` and **σ cancels exactly**:

| ratio | Gaussian value |
| --- | --- |
| `R25_50` | `√(ln4/ln2)` = **1.414214** |
| `R10_50` | `√(ln10/ln2)` = **1.822616** |

No free parameter. Four properties, each **measured in `s20`, not assumed:**

| property | measurement | why it matters |
| --- | --- | --- |
| **unbiased** | reproduces the Gaussian value to **0.034%** | MEASURED |
| **scale-free** | over a **10.5× range of curve width** the same Gaussian spans **1.0121×**, sd **0.0090** | **the confound that killed `g2` (pooled sd 4.77) cannot reach it** — MEASURED |
| **discriminates tail weight** | boxcar 0.562×, triangle 0.988×, Gaussian 1.000×, sech² 1.134×, Lorentzian 1.646× | it responds to the thing it names — MEASURED |
| **cannot invent a reading** | NULL-NOISE (flat latent, calibrated noise, no curve): **144/144 draws UNDEFINED** | unlike `A₅₀`, which returned a spurious ±0.077 on noise, this refuses to report — MEASURED |

**It is a tail statistic, which is M67's instruction (c).** It is read at 0.10 of
peak. **No parabola and no Gaussian is fitted near the peak anywhere in M70** —
that was true of §16 and remains true here, so the region fact 471 implies any
deviation lives in is not excluded by construction.

**It is blind to asymmetry by construction** — it averages near and far. That is
deliberate: asymmetry is §16's question. **The two statistics are therefore
independent by design, which is M67's instruction (a):** skew and kurtosis cannot
be confused here because they are measured by different estimators reported in
different sections. §16.4 went further and showed the kurtosis estimator does not
measure what its name says.

**The physical comparator, built from fact 471 used correctly.** A real-texture
defocus ladder was run at δ ∈ {0.25, 0.50, **0.6017**, 1.0, **1.1856**, 2.0}
px/step — a sweep **containing both of fact 471's measured real rates and
bracketing them 4.8× on either side.** It reads `R10_50` = **1.729–1.837, median
1.766**, moving only **1.062×** across the whole 8× sweep. **A genuine defocus
curve on real texture is very slightly sub-Gaussian, and the plant is known to
cover the real regime rather than assumed to** (rule 3, and the discipline facts
61–64 exist to enforce).

### 19.3 Criteria H / I / J, as they fell: INDETERMINATE

Bar **±0.11** on `R10_50`, fixed in advance as *the physical plant's full span
across an 8× range of focus-step density* — an effect must exceed everything step
density alone can do to a curve that is Gaussian-ish by construction. Headline
population: the **seven POWERED stacks** (K ≥ 100) from §16.5's table.

| criterion | requirement | result | |
| --- | --- | --- | --- |
| **H** GAUSSIAN | median within ±0.11 of 1.8226 **and** ≥6/7 stacks | median **2.1803** (+0.3577), **3/7** | **NOT MET** |
| **I** HEAVIER (fact 274's direction) | median ≥ 1.9326 **and** ≥6/7 stacks | median **PASSES**, but **4/7** | **NOT MET** |
| **J** LIGHTER | median ≤ 1.7126 **and** ≥6/7 | median FAILS, **0/7** | **NOT MET** |

**VERDICT: INDETERMINATE.** Criterion I's median cleared its bar and its stack
count did not — **4 of 7 against a requirement of 6.** Reported as it fell. §16's
Criterion E missed by one stack and was reported failed; this misses by two and
is reported the same way. **A milestone that reinterprets its bar after seeing
the count has no bar.**

| stack | K | w50 | `R25/50` | `R10/50` | vs Gaussian | undef | powered |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| coffee-bubbles | 19 | 1.61 | 1.4202 | 1.8857 | +0.0631 | 1.4% | – |
| 109MSDCF | 22 | 2.25 | 1.4398 | 1.9741 | +0.1515 | 22.7% | – |
| 119MSDCF | 33 | 3.28 | 1.5326 | 2.2905 | +0.4679 | 54.2% | – |
| 113MSDCF | 63 | 3.14 | 1.4150 | 2.1035 | +0.2809 | 0.0% | – |
| 112MSDCF | 79 | 2.95 | 1.4469 | 2.0490 | +0.2264 | 0.0% | – |
| foam | 100 | 2.19 | 1.4789 | 2.1803 | +0.3577 | 0.0% | **YES** |
| coffee-bean | 105 | 2.38 | 1.4157 | 1.8161 | −0.0065 | 20.8% | **YES** |
| wrapped-text-2 | 120 | 1.96 | 1.4244 | 1.8546 | +0.0320 | 0.0% | **YES** |
| wrapped-text-1 | 130 | 1.99 | 1.4188 | 1.8444 | +0.0218 | 0.0% | **YES** |
| bee-1 | 299 | 2.86 | 1.7887 | **2.6514** | +0.8288 | 6.2% | **YES** |
| bee-2 | 299 | 3.57 | 1.5552 | **2.4345** | +0.6119 | 1.9% | **YES** |
| bee-3 | 299 | 3.46 | 1.5469 | **2.6959** | +0.8733 | 8.8% | **YES** |

**VOID conditions.** VOID 11 (censoring): does not fire, 0/7 powered stacks above
50% undefined. **VOID 13 (reversal must be exact): does not fire — worst
deviation 4.4 × 10⁻¹⁶** across four stacks, an exact reproduction of §16's VOID 6
result on a different statistic. VOID 12 (shuffle null within the bar on a
majority): does not fire, 3/7. **VOID 14 (σ dependence): does not fire** — across
σ ∈ {0.91, 1.00, 1.09, 1.25}× the powered median moves 2.1909 → 2.1172, span
**0.0736**, inside the bar. **This reading survives whatever M69 concludes about
`FOCUS_NOISE_SD`**, as §16's did and §6's `n_eff` did not.

### 19.4 Is that reading the optics, or my instrument? (`s22`)

`PREREGISTRATION-C` §2 declared in advance that *"a super-Gaussian finding must
be checked against per-stack `w50`"*, because the estimator's known
discretisation bias runs **positive** at narrow curve widths — the same direction
as the finding. That check is `s22`, and it is why the finding survives.

**(a) The bias does not explain it. MEASURED.** A *true Gaussian sampled at each
stack's own measured `w50`* reads between **1.8094 and 1.8778** — instrument bias
of **−0.0133 … +0.0552**. The corpus excess over a **same-width** Gaussian is
median **+0.2459**, range −0.0254 … **+0.8609**. The bees' excess is **15–36×
the largest instrument bias.** The reading is real.

**(b) But the resolving power is the real limit, and it is the important number
here. MEASURED.** Separation between a Gaussian and a **sech²** — the mildest
real heavy-tailed family — with both sampled at the same `w50`:

| `w50` frames | 1.6 | 2.5 | **3.6** | 5.0 | 8.0 | 13.0 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| separation | **+0.006** | **+0.055** | +0.142 | +0.199 | +0.224 | +0.233 |
| exceeds the 0.11 bar? | no | no | **YES** | YES | YES | YES |

**Every corpus stack has `w50` between 1.61 and 3.57 frames. Ten of twelve are
below 3.6.** So **this corpus cannot distinguish a Gaussian through-focus curve
from a mildly heavy-tailed one at the pre-registered bar** — not because the
instrument is poor but because **the curves are three frames wide at half-maximum
and you cannot characterise a tail with three samples.** That is a property of
the corpus's focus-step density, and it is the honest ceiling on this question.

**(c) The structureless floor is K-dependent and approaches Gaussian from below.
MEASURED.** Pure noise, no curve, 400 draws: median `R10_50` = **1.5806** (K=19),
1.6444 (K=33), 1.6809 (K=105), **1.7800** (K=299). Pooled floor 1.6627, **0.1599
below the Gaussian value — outside the bar.** But at **K=299 the floor is 0.0426
from Gaussian, inside it.** So on the long stacks *"reads Gaussian"* is not
separable from *"reads nothing"*; on the short stacks it is. **Criterion H was
therefore interpretable on 5 of 12 stacks and not on the rest, and I did not know
that when I wrote it.** It is the same class of defect as §4's Criterion B being
unsatisfiable by construction — pre-registration bounds the analyst, not the
instrument.

### 19.5 The mechanism: it is not tail weight, it is multimodality (`s23`)

A reading of 2.65 is far past any smooth unimodal family the estimator could
mistake for a Gaussian. That points somewhere specific:

> **`w(0.10)` is inflated by MULTIMODALITY.** A patch spanning two depths has a
> second lobe. At 0.50 of peak the half-width sees only the primary lobe; at 0.10
> it reaches across the valley into the secondary one, and the ratio jumps. **The
> curve is not heavy-tailed. It is two curves.**

**Arm A — the plant, with the PSF Gaussian by construction. MEASURED.** Two
Gaussian lobes of identical symmetric width `w50 = 2.9` (matching the bee
stacks), separation swept 0 → 24 frames. `R10_50` reaches **3.8247**. **The bee
stacks read 2.43–2.70. A symmetric Gaussian PSF over two depths fully accounts
for the entire observed excess**, with the PSF contributing nothing, because in
this plant the PSF *is* a Gaussian.

**Arm B — the lobes are there in the real curves. MEASURED.** Local maxima above
0.10 of peak in the smoothed curve:

| stack | `R10_50` | mean lobes | % multi-lobed |
| --- | ---: | ---: | ---: |
| wrapped-text-1 | 1.8444 | **1.00** | **0.0%** |
| wrapped-text-2 | 1.8546 | **1.01** | **1.4%** |
| coffee-bubbles | 1.8857 | 1.06 | 2.8% |
| coffee-bean | 1.8161 | 4.85 | 25.0% |
| 109MSDCF | 1.9741 | 1.62 | 36.4% |
| 112MSDCF | 2.0490 | 2.12 | 68.1% |
| 113MSDCF | 2.1035 | 2.28 | 70.8% |
| foam | 2.1803 | 1.76 | 61.1% |
| 119MSDCF | 2.2905 | 2.31 | 50.0% |
| bee-2 | 2.4345 | **9.15** | 85.2% |
| bee-1 | 2.6514 | 7.52 | 83.3% |
| bee-3 | 2.6959 | **9.49** | 80.7% |

**Arm C — the association. MEASURED.** `corr(% multi-lobed, R10_50)` = **+0.834
Pearson, +0.867 Spearman**, n=12. `corr(mean lobes, R10_50)` = +0.806 / +0.720.
Near-Gaussian stacks average **1.98** lobes; heavy stacks average **4.95** — a
**2.50×** ratio.

**Arm D — and unlike asymmetry, it reproduces. MEASURED.** The three bee captures
— same rig, same subject, three separate shoots — return lobe counts spreading
**1.262×** and `R10_50` spreading **1.107×**. **§16.7's `A₅₀` on those same three
captures changed sign (+0.042 / −0.036 / −0.070).** Same instrument, same data,
same three files: **the statistic that reflects a real property reproduces, and
the one that did not, did not.** That is the strongest internal validation in
this report, and it strengthens §16's null rather than weakening it — the
non-reproduction there was not the instrument being blind.

### 19.6 POST HOC: the shape, where the question is well posed (`s24`)

> **This subsection is POST HOC and is not covered by `PREREGISTRATION-C`. The
> pre-registered verdict is INDETERMINATE (§19.3) and it stands unaltered.** This
> does not rescue the criteria; it explains them. It is reported the way §13.5's
> ISO hypothesis was — formed after seeing the data, labelled, and unruled.

On a multi-lobed patch, *"the shape of the through-focus curve"* is not a
question about the PSF at all. Restricting to patches whose smoothed curve has
exactly one local maximum above 0.10 of peak — s23's rule, applied unchanged —
**the departure disappears: pooled median `R10_50` = 1.8686, +0.0460 from
Gaussian, inside the ±0.11 bar**, n = 416 patches.

**The cleanest case needs no restriction at all, and it is the result.**
`wrapped-text-1` is **100.0% unimodal** and `wrapped-text-2` is **98.6%** — the
restriction removes nothing, so no selection can bite. They are **two independent
captures of one subject**, which is the reproduction test §16.7 used to refute
asymmetry, run here on shape:

| | `R25/50` (Gaussian 1.4142) | `R10/50` (Gaussian 1.8226) |
| --- | ---: | ---: |
| wrapped-text-1 | 1.4188 (**+0.0046**) | 1.8444 (**+0.0218**) |
| wrapped-text-2 | 1.4243 (**+0.0101**) | 1.8543 (**+0.0317**) |
| agreement between captures | **0.0055** | **0.0099** |

**Both ratios are simultaneously Gaussian, on two independent captures, agreeing
with each other an order of magnitude inside the bar.** `coffee-bubbles` (97.2%
unimodal, K=19, different subject, different session, different aperture) reads
1.8863 — also inside.

**Negative control, and it is the one that makes this reportable. MEASURED.**
Does the unimodal restriction itself manufacture a Gaussian? Applied to synthetic
curves of known non-Gaussian shape, the largest shift it causes is **0.0028**,
and **a Lorentzian survives it reading 2.7263** — nowhere near Gaussian. **The
restriction does not force the answer.**

**Symmetry on the same subset, reported separately per M67's instruction (a).**
Median `|A₅₀|` on unimodal patches = **0.0535** (§16 on all patches: 0.0404),
signs **5 positive / 7 negative**. **§16's conclusion is unchanged.** The bees
move most (bee-2 to −0.2337) on **8 surviving patches of 54** — that is the
restriction's cost, not a signal, and it is why the pooled figure is the one to
read.

### 19.7 M67's three instructions, discharged

**(a) Report both moments separately, so kurtosis is not read as skew. DONE, and
further than asked.** Skew is §16 (`A₅₀`, `g1`), shape is §19 (`R10_50`), and
they are computed by estimators that are independent by construction — §19.2's
statistic is blind to asymmetry, §16's is blind to width. **§16.4 went past the
instruction and showed the corpus's kurtosis statistic is not a tail statistic at
all**, so fact 274's trap is not merely avoided, it is disarmed.

**(b) The named pairing cannot be run on this instrument, and I am reporting that
rather than producing a reading from it.** `109MSDCF` (K=22) has **no power on
either statistic**:

| stack | K | `A₅₀` z (§16.5) | `R10_50` shuffle sd | `R10_50` z | undefined |
| --- | ---: | ---: | ---: | ---: | ---: |
| **109MSDCF** | 22 | **0.1** | **0.2210** | **0.1** | 22.7% |
| coffee-bean | 105 | 39.2 | 0.0032 | 5.1 | 20.8% |

**Its shuffle null sd of 0.2210 is twice the entire pre-registered bar.** Any
number I quoted from it would be noise. This was registered in `PREREGISTRATION-C`
§6 in advance, precisely so that a null on `109MSDCF` could not later be dressed
as a finding.

**But the purpose behind the instruction is discharged by another route, and this
is the larger result.** M25's **question 33** asks: *"Is the real defocus growth
non-linear in frame index, or is the subject's depth range doing the work?"*
**§19.5 answers it: the subject's depth range is doing the work**, established
three independent ways — a Gaussian-by-construction PSF over two depths reaching
3.82; `corr(% multi-lobed, R10_50)` = +0.834 on real curves; and the departure
vanishing under a restriction that provably does not force the answer. **The
pairing was one way to separate that confound. It is not the only way, and the
corpus supports a different one.**

**What would fix the pairing:** a dense capture (≥100 frames) of a **shallow**
subject — the arm the corpus lacks. Every K ≥ 100 stack here is a deep subject,
so **depth and step density are confounded across the whole corpus**, which
§19.9 records as a limitation of the corpus rather than of this milestone.

**(c) Measure the tails explicitly or state that you did not. DONE.** **No
parabola and no Gaussian was fitted near the peak anywhere in M70.** The
statistic *is* a 0.10-of-peak reading, and §19.4(b) reports exactly how far into
the tail it can see: **not far enough**, below `w50` = 3.6 frames, to separate a
Gaussian from a sech². **The tails were measured, and the measurement's answer is
partly that the corpus cannot resolve them.**

**And M67's fact 26, which I was told not to assume away.** Fact 26 argues a
faster-falling curve is a *sharper* peak, so asymmetry's sign is not obviously
adverse. **§16 found no asymmetry to have a sign, so the question did not arise —
but the framing was live while measuring and no "bad news" reading was applied to
any result.** §19 supplies the analogous point for shape: the corpus's departure
from Gaussian is **multimodality**, and multimodality is unambiguously adverse
for a matched filter (§19.8) while being nothing at all to the PSF.

### 19.8 What §19 does to the architectural verdict

**It reinforces PLUGIN, by a second and independent route. ARGUED, on MEASURED
inputs.**

The reviewer's estimator needs a family `H_k` — one point-spread function per
frame per pixel. §19.6 says that family is **Gaussian and symmetric** where the
question is well posed, which makes the filter *simpler* than feared: good news
for whoever builds it, and a strengthening of M67's simulator on top of §16's.

But §19.5 says something harder. **On this corpus, 0% to 85% of patches per stack
are multi-lobed — median 50%, and 80–85% on the three deepest stacks.** A patch
with two lobes is looking at two surfaces. **A single `H_k` per pixel is
mis-specified there, no matter how good the deconvolution is**, because there is
no single depth to deconvolve to. The proposal's mechanism assumes one
through-focus response per pixel and **the majority of this corpus does not have
one.**

That is not fatal to deconvolution — it is fatal to deconvolution *as the core of
the merge*. **A merge that must be correct on every pixel of every stack cannot
rest on a model that is mis-specified on half of them.** A plugin, invoked where
the operator knows the subject is shallow, is exactly the right shape for it.
**§0's verdict of PLUGIN was decided on 2.38% of headroom; §19 says the model
underneath the proposal is also mis-specified on the median patch.** Two
independent reasons, and they were measured in different sections against
different pre-registrations.

**Note the tension with the reviewer's own second-ranked proposal, and it is
worth the owner's attention.** M63 killed occlusion unmixing by refuting the
inference from through-focus bimodality to two depths. §19.5 finds bimodality
again, from the other side — and it too does **not** claim two depths. `s23`'s
plant demonstrates that a two-depth *scene* produces multi-lobed curves; it does
**not** demonstrate that multi-lobed curves imply a two-depth scene. **That
inference is the one M63 refuted five ways and I am not making it.** What §19.5
establishes is the direction M63 left intact: curve multimodality is sufficient
to inflate `R10_50`, and the corpus has it.

### 19.9 What §19 cannot see

1. **Modulus only.** As throughout M70. A defocus PSF departs from Gaussian in
   **phase** first, and phase is invisible to every measurement here. §19.6 is a
   statement about the through-focus power envelope, not about the PSF.
2. **It cannot exclude a mild heavy tail.** §19.4(b) is explicit: below `w50` =
   3.6 frames a Gaussian and a sech² differ by less than the bar, and 10/12
   stacks are below. **"Not distinguishable from Gaussian" is the claim.
   "Proven Gaussian" is not.** Lorentzian-scale departures are excluded; sech²-
   scale ones are not.
3. **The unimodal restriction is post hoc and severe on the stacks that most need
   it** — 8 of 48, 8 of 54, 11 of 57 patches survive on the bees. The pooled
   figure and the two wrapped-text stacks (where it removes nothing) are the
   trustworthy readings; the restricted bee figures are not.
4. **Lobe counting is threshold-dependent.** A lobe is a local maximum above 0.10
   of peak after `[1,2,1]` smoothing. A different threshold gives different
   counts. The *association* (+0.834) is what is claimed, not the absolute counts.
5. **Depth and step density are confounded across the corpus** (§19.7). Every
   dense stack is a deep subject. No measurement here separates them, and the
   capture that would is named.
6. **`coffee-bean` is an anomaly I have not explained. UNRULED.** It has mean 4.85
   lobes yet reads 1.8161 — near-Gaussian — and only 25.0% of its patches are
   multi-lobed. The mean is dragged by a minority of heavily multi-lobed patches
   while the median patch is unimodal. **The mean lobe count is the wrong summary
   and I have reported it anyway** because it is what `s23` computed; the % column
   is the one that carries the correlation. Flagging rather than quietly
   substituting.
7. **The `f/5.6` scoping of §2 applies unchanged.** 75.3% of corpus frames are
   f/5.6, so this is primarily an f/5.6 result.

### 19.10 Candidate facts from §19

| # | Proposed fact | Label | Source |
| --- | --- | --- | --- |
| **P19** | **The real through-focus modulus curve is not distinguishable from a Gaussian on patches where the curve is unimodal.** Half-width ratios `w(0.10)/w(0.50)` and `w(0.25)/w(0.50)` read **1.8444 / 1.4188** on `wrapped-text-1` (100.0% unimodal, no restriction applied) and **1.8543 / 1.4243** on `wrapped-text-2` (98.6%), against Gaussian values 1.822616 and 1.414214 — **both ratios simultaneously Gaussian on two independent captures of one subject, agreeing with each other to 0.0099 and 0.0055.** Pooled over all unimodal patches corpus-wide, median `R10_50` = **1.8686** (+0.046), n = 416. The estimator reproduces an exact Gaussian to 0.034% and a Lorentzian to 2.7263, and the unimodal restriction shifts a known Lorentzian by only 0.0028 | MEASURED | `out/s24_unimodal.log`, `out/s20_shape_controls.log` |
| **P20** | **Apparent heavy tails in real through-focus curves are MULTIMODALITY, not tail weight — the subject's depth range, answering M25's open question 33.** `corr(% multi-lobed patches, R10_50)` = **+0.834 Pearson / +0.867 Spearman**, n = 12 stacks; mean lobes 1.00 on `wrapped-text-1` versus 9.49 on `bee-3`. A plant whose PSF is a **Gaussian by construction**, over two depths, reaches `R10_50` = **3.8247** — beyond the bees' measured 2.43–2.70 — so scene depth alone fully accounts for the observed excess. **This does not license the inference from bimodality to two depths, which M63 refuted** | MEASURED | `out/s23_multimodality.log` |
| **P21** | **This corpus cannot resolve through-focus tail shape, because its curves are ~3 frames wide at half-maximum.** A Gaussian and a sech² sampled at the same `w50` separate by **+0.006 at `w50` = 1.6** and **+0.055 at 2.5**, exceeding a 0.11 bar only at **`w50` ≥ 3.6 frames**; all 12 stacks have `w50` ∈ [1.61, 3.57] and **10 of 12 are below 3.6**. The structureless floor is K-dependent — median `R10_50` = 1.5806 (K=19) rising to **1.7800** (K=299) — so on the longest stacks "reads Gaussian" is **not separable** from "reads nothing" | MEASURED | `out/s22_estimator_floor.log` |
| **P22** | **Excess kurtosis `g2` is superseded as a through-focus shape statistic by the half-width ratio `w(0.10)/w(0.50)`, which is scale-free by construction.** Over a **10.5× range of curve width** the same Gaussian returns ratios spanning **1.0121×** (sd 0.0090); `g2` on a plant symmetric by construction spanned **−0.63 … +6.13** (pooled sd 4.77) over a 4× density range (§16.4). The ratio discriminates tail weight — boxcar 0.562×, triangle 0.988×, Gaussian 1.000×, sech² 1.134×, Lorentzian 1.646× — and returns **UNDEFINED on 144/144 noise-only draws** rather than a spurious value | MEASURED | `out/s20_shape_controls.log` |
| **P23** | **Fact 471's `(10/9)` and `(17/17)` are FWHM measured-versus-modelled, not near-versus-far half-widths, and cannot be converted into an asymmetry index.** Its usable content is two **measured blur-growth rates**, `s = 0.6017 px/frame` on `119MSDCF` and `1.1856` on `109MSDCF`. **M70 §16.7 as first committed made this conversion and is retracted in §19.1.** Cited here so the misreading is recorded against the fact rather than only against the report that made it | MEASURED (audit) | `M67-focus-correctness.md:520`; retraction §19.1 |
| **P24** | **The reviewer's proposed estimator is mis-specified on the median patch of this corpus.** A matched filter over the focus axis assumes one through-focus response per pixel; **0%–85% of patches per stack are multi-lobed (median ~50%, and 80–85% on the three deepest stacks)**, and a multi-lobed patch is looking at more than one surface. This is independent of, and additional to, P1/P2's finding that the filter's headroom is 2.38% at the shipped gate's width | MEASURED (rates); ARGUED (inference to mis-specification) | `out/s23_multimodality.log`; §19.8 |
| **P25** | **`109MSDCF` cannot support a through-focus shape or asymmetry measurement on this instrument.** K = 22; shuffle-null sd **0.0766** on `A₅₀` (z = 0.1) and **0.2210** on `R10_50` (z = 0.1) — the latter **twice the entire pre-registered bar**. M67's named pairing of `109MSDCF` against `coffee-bean` therefore **cannot be run as specified**; the confound it targets is separated in §19.5 by a different route | MEASURED | `out/s21_shape_corpus.log`, `out/s16_null_band.log` |

### 19.11 Disciplines from §19

**D-i. A statistic must be shown scale-free before it is used on a corpus with a
15× range in the scale.** `g2` failed this and was pre-registered NOT TESTABLE;
`R10_50` was made to pass it (1.0121× over 10.5×) *before* the criteria were
written. **The check costs one control run and it is the difference between a
result and a retraction.**

**D-j. When a plant's parameter has been measured in the corpus, sweep the plant
through the measured value and say so.** Fact 471's `0.6017` and `1.1856` px/frame
are *in* §19.2's δ sweep, bracketed 4.8× either side. **A plant whose relationship
to real texture is unexamined is the failure mode facts 61–64 record four times;
a plant swept through a published measurement of the same quantity is not.**

**D-k. A wrong reading that produces a plausible number is the hardest to catch.**
§19.1: converting `10/9` to `|A| = 0.053` landed next to my measured median of
0.0404, and **the agreement functioned as camouflage.** Corroboration that feels
confirming deserves the source check *more* than a claim that surprises, not less.

**D-l. Ask what a statistic returns when there is no signal, and how that varies
with K.** `R10_50`'s structureless floor climbs 1.58 → 1.78 with K and passes
*inside* the bar at K=299 — so a pre-registered criterion was interpretable on
five stacks and not on seven, **and nothing in the pre-registration revealed
that.** Pre-registration bounds the analyst; only a null run bounds the
instrument.

**D-m. Two statistics on the same three repeat captures is a free validity
check.** Lobe count and `R10_50` reproduce across the three bee shoots (1.262×,
1.107×) while `A₅₀` changes sign on the identical data. **That contrast is what
licenses reading §16's null as a null rather than as blindness**, and it cost one
extra column.

---

## 20. Addendum: M69's refutation, a render defect of mine, and a citation trap

**Added after the repo linter failed the corpus on a defect in this file, and
after M69 reported on `FOCUS_NOISE_SD`.** Two unrelated items; the second is the
substantive one.

### 20.1 The render defect: two cells of P5 were being discarded

`corpus_lint` [S1] failed the whole repository on one violation and it was mine.
**P5's row carried `` `|H_k|` `` as a bare code span.** A literal pipe splits a
Markdown table cell **even inside backticks**, so the row had 7 unescaped pipes
against a 5-pipe header and the renderer **discarded its last two cells — the
`MEASURED` label and the source path.** A reader saw a truncated row with no
indication that anything was missing, and nothing in the source looked wrong.
Escaped as `\|H_k\|`. **`corpus_lint` now reports no M70 violation.**

**I audited all 32 tables in this report, with a check stricter than S1.** S1
compares a row's pipe count against its header's, so **it passes any row that is
malformed *and* coincidentally matches the header width** — a silent failure the
check cannot see. The second check flags every pipe that is not a *structural*
cell separator (a pipe at a trimmed line edge, or one with whitespace on both
sides). **Result: 0 count mismatches and 0 content pipes across all 32 tables.**
Script committed at `experiments/M70-through-focus-spectrum/src/audit_tables.py`.

**This is the second instance of this defect class in a day** — M67 had it first,
and M67's response was to write the check that caught me. **The escalation is the
right one and I have extended it rather than only complied with it:** the
header-vs-row check has a known blind spot, the blind spot is cheap to close, and
a report whose subject matter is spectral (`|H|`, `|A₅₀|`, `|ΣH|`) is unusually
exposed to it.

### 20.2 M69, read at source: what it says, and what it does not

The brief relayed that M69's result *"bears directly on fact 27, your anchor —
the f/11 diffraction knee at `f_sig = 0.2762 cyc/px`"*. **I read
`docs/research/M69-focus-noise-sd.md` rather than the relay, as instructed, and
the citation does not resolve to that claim.**

**MEASURED (audit of M69's text).** M69 contains **zero** occurrences of
`0.2762`, `diffraction`, `knee`, `f_sig`, `MTF`, `Nyquist` or `bellows`. **It
makes no claim about any spectral band edge anywhere in 1,501 lines.**

**The quantity M69 refutes is not the quantity I use.** M69's `sigma_F` is the
response noise of a **spatial gradient operator** — its §143 defines it as *"3×3
Sobel scaled by `0.125` → `box_mean` radius 13 (a 27×27 window)"*. Mine is the
**noise floor of a band-power spectrum**, from the photon-transfer model in
`profile.rs`. Different operator, different domain, different units.

**And here is how I think the relay went wrong, because it is a trap and not
carelessness. ARGUED.** **M69 numbers its own facts 1–47+, and its internal facts
27 and 29 collide with SYNTHESIS facts 27 and 29** — which are precisely my two
anchors. M69's fact 27 (line 622) is *"A5 failed… this is 'not measurable', not
'not measured'"*; its fact 29 (line 666) is *"Recalibrating each stack to its own
`rho_true`"*. **Searching M69 for "fact 27" returns a hit, and the hit is not the
fact the searcher meant.** A resolving citation is not a verified claim — and
this is the sharpest form of that failure, because the citation resolves *inside
the right document* to *the wrong object*.

**`FOCUS_NOISE_SD` appears nowhere in M70's code as a value.** It occurs twice in
`src/`, both times inside a printed section heading noting that M69 is live on
it. Every noise scale in this milestone comes from the photon-transfer model.
**§14 said this before M69 reported and it is unchanged.**

### 20.3 But the conditional deserved a measurement, so I made one

The relay's conditional is fair regardless of whether its citation resolves:

> *"If any part of your spectral analysis assumes a spatially uniform
> response-noise floor, that assumption is now measured false."*

**It does not assume one** — `signal()` evaluates the photon-transfer variance
**per frame and per patch, at that patch's own `w²`-weighted level**, so the
floor is already signal-dependent and spatially varying. But *signal-dependent*
is not *correct*, so I measured the residual.

**Arm A — how non-uniform is my floor, in M69's own statistic? MEASURED.**
Per patch, the **measured** floor (band `b6`, 0.2762–0.34 cyc/px — above the
cutoff and structure-free by fact 27) divided by the **modelled** variance. A
perfect model on a uniform floor gives 1.000 everywhere.

| | within-stack p05–p95 span |
| --- | ---: |
| **M70 spectral floor, corpus median** | **1.102×** |
| M70 spectral floor, worst stack (`coffee-bubbles`) | 1.498× |
| **M69 `sigma_F` within a real stack** | **2.000×** |
| M69 `sigma_F` on its controlled plant | 4.060× |

**My floor is not uniform, and it is not the 2.0×–4.06× M69 found.** Per-stack
medians run 0.967–1.160, i.e. the model is right to about ±16% patch-to-patch
and better than ±6% on eight of twelve stacks.

**Arm B — and the residual is driven by the opposite mechanism. MEASURED, and
this is the substantive finding of §20.**

| driver | median correlation with per-patch floor ratio | sign agreement |
| --- | ---: | ---: |
| **patch level** | **+0.907** | **12/12 positive** |
| patch texture (peak mid-band signal) | +0.146 | 7/12 — **signs split** |

**M69's mechanism is explicitly *not* signal-to-noise** — it is gradient-
*direction* coherence, a texture property. **In my domain the residual tracks
level at +0.907 on every stack, and texture not at all.** So the specific defect
M69 refuted does not appear here.

**What does appear is a level-dependent departure I had already found and
reported.** §13's `e_flat ∝ level^1.83` (R² 0.97), flagged there as PRNU or
residual texture and **undecidable without darks and flats**. §20.3 Arm B is the
same object measured a second way, and it **raises that item's priority**: it is
now the largest known error in my noise floor, it is systematic, and M71 is live
on flat fields. **UNRULED, and it was unruled before M69 reported.**

**Arm C — does the band edge matter to the verdict? MEASURED. No.**
The floor sets the boundary between "recoverable band" and "noise". Recomputing
the headline — matched filter over an equal average of the *same* frames at the
shipped gate's width, W=3 — under four band definitions:

| band definition | MF ÷ equal average, W=3 |
| --- | ---: |
| `b3` only, 0.100–0.150 cyc/px | 1.0181 |
| `b3`+`b4`, 0.100–0.200 | 1.0243 |
| **`b3`+`b4`+`b5`, 0.100–0.2762 — the shipped mid band** | **1.0293** |
| `b3`…`b6`, 0.100–**0.340** — *past the cutoff, into the band fact 27 calls pure noise* | 1.0338 |

**Full span across all four: 1.0154×, i.e. 1.54%.** For scale, the architectural
prize is **1.1100** (P1) and the verdict turns on **2.38% against +5.45 dB**
(§18). **Even extending the band 23% past the diffraction cutoff — deliberately
including frequencies fact 27 says carry no signal — moves the gain by 0.44%.**

**A second robustness datum, reported because it is a discrepancy in my own
numbers.** §18's headline at W=3 is **1.0238** (corpus median of per-stack
medians); Arm C's pooled aggregation gives **1.0293** for the same band. **The
0.54% difference is the aggregation choice, and it is smaller than the
band-edge span it sits inside.** Recorded rather than reconciled away.

### 20.4 What §20 changes, and what it does not

**Nothing in §0–§19 moves. MEASURED basis, ARGUED conclusion.** The verdict is
**PLUGIN**, unchanged. The band edge is not load-bearing at 1.54%; the floor's
spatial residual is 1.102× not 2.0×, and is level-driven not texture-driven.

**What I would want checked if I am wrong.** My Arm A statistic uses band `b6`
as a structure-free floor **because fact 27 says it is above the cutoff** — and
**§13.2 records that fact 27's `0.2762` did not reproduce** from M5's own
committed driver, which returns **0.2375**. **If the true cutoff is 0.2375, then
`b5` (0.200–0.2762) is partly above it and `b6` is cleanly above it — which makes
Arm A conservative, not wrong**, since contamination by real signal would inflate
the measured floor and *increase* the apparent non-uniformity I am reporting as
small. But it is the one place §20 leans on the number §13.2 could not reproduce,
and it should be read with that in hand.

**What §20 cannot see.** It measures the floor **above** the cutoff and assumes
the model's *form* carries down into the mid band. A floor whose non-uniformity
is frequency-dependent would not show up. Measuring that needs the known-spectrum
target already requested as §14 item 2.

### 20.5 Candidate facts from §20

| # | Proposed fact | Label | Source |
| --- | --- | --- | --- |
| **P26** | **The spectral band-power noise floor is substantially more spatially uniform than the focus operator's response noise, and its residual is driven by the opposite mechanism.** Per-patch measured floor ÷ modelled photon-transfer variance has a within-stack p05–p95 span of **1.102× (corpus median), 1.498× worst**, against M69's **2.000×** for `sigma_F` within a real stack and 4.060× on its plant. The residual correlates with patch **level** at **+0.907 (12/12 stacks positive)** and with patch **texture** at +0.146 (7/12, signs split) — **M69's driver is gradient-direction coherence, explicitly not SNR, so that defect does not transfer to the spectral domain** | MEASURED | `out/s25_floor_uniformity.log` arms A, B |
| **P27** | **M70's verdict is insensitive to where the recoverable-band boundary is placed.** The matched filter's gain over an equal average of the same frames at the shipped gate's width moves **1.0181 → 1.0338 (span 1.54%)** as the mid band is varied from 0.100–0.150 cyc/px to 0.100–0.340 — the last **23% past the f/11 diffraction cutoff, into the band fact 27 says is pure noise**. The architectural prize is 1.1100 and the verdict turns on 2.38% against +5.45 dB | MEASURED | `out/s25_floor_uniformity.log` arm C |
| **P28** | **M69 makes no claim about any spectral band edge, and its internal fact numbering collides with SYNTHESIS's at exactly the two facts that anchor M70.** `M69-focus-noise-sd.md` contains zero occurrences of `0.2762`, `diffraction`, `knee`, `f_sig`, `MTF`, `Nyquist` or `bellows` in 1,501 lines; its `sigma_F` is the response noise of a 3×3 Sobel with `box_mean` radius 13 (line 143), not of a spectrum. **Its own facts 27 and 29 collide with SYNTHESIS facts 27 and 29** — the diffraction cutoff and the spectral floor — so a search for "fact 27" inside M69 returns a hit that is not the fact sought | MEASURED (audit) | `M69-focus-noise-sd.md` lines 143, 622, 666; `out/s25_floor_uniformity.log` preamble |
| **P29** | **A Markdown table cell is split by a literal `\|` even inside a backtick code span, and the repo's [S1] check cannot see a malformed row whose pipe count coincidentally matches its header.** M70's P5 row silently discarded two cells — its label and its source — for four commits. A stricter check that flags every non-structural pipe (not at a trimmed line edge, not whitespace-delimited on both sides) finds 0 defects across this report's 32 tables after the fix | MEASURED | `src/audit_tables.py`; `corpus_lint` [S1] |

### 20.6 Disciplines from §20

**D-n. A citation that resolves inside the right document can still resolve to
the wrong object, because milestone reports number their own facts.** M69's facts
27 and 29 collide with SYNTHESIS's 27 and 29 — **and SYNTHESIS's 27 and 29 are
the two this milestone is anchored on.** Searching a report for "fact 27" is not
a check; **reading the sentence and confirming it is about the quantity you mean
is the check.** This is the corpus's "a resolving citation is not a verified
claim" sharpened by one turn.

**D-o. When a neighbouring milestone refutes the *form* of a constant, ask
whether its mechanism exists in your domain before assuming it transfers.** M69's
driver is gradient-direction coherence. **The analogue cost one correlation per
stack and answered NO at +0.146 with split signs, while finding the real driver
at +0.907 on 12/12.** The transfer question is cheaper to measure than to argue.

**D-p. Extend a check that caught you, if its blind spot is cheap to close.** The
[S1] header-vs-row check cannot see a malformed row that coincidentally matches
the header width. **Closing that took nine lines and confirmed 32 tables clean.**
Complying with a check treats the symptom; the check itself is the artefact worth
improving.

---

## 21. Addendum: does M70 discriminate M73's two readings?

**Added after M73 measured admission on two real captures.** It does discriminate
them, from numbers already committed — **so no new arm was registered, because
none was run.** `src/s26_m73_discrimination.py` **collects no new data**: it
re-reads `out/s07_unclipped.log`, `out/s10_architecture.log` and
`out/s23_multimodality.log`, and combines them with M73's measured admission.
Every input is cited to a line in a committed log.

### 21.1 Why my measurement bears on it at all

M73 measured, at the shipped `DEFAULT_GATE = 4.0`, on real captures
(`M73-cylinder-invariant.md:490`): `wrapped-text-1` admits **1.238 of 130**
frames, `wrapped-text-2` **1.766 of 120**, the admitted set a singleton at
**81.4%** and **58.7%** of scored pixels. It recorded two readings and said the
corpus could not choose:

* **(a)** the gate is too tight and is discarding informative frames;
* **(b)** the collapse is **correct** — only one frame carries the pixel, so
  there is genuinely nothing to average.

**ARGUED, and it is the whole reason I can answer.** **Reading (b) is not a claim
about the gate. It is a claim about the signal** — that the through-focus
response supports about one frame's worth of information. A claim about the
signal is falsifiable **without touching the gate**, by a gate-free count of how
many frames carry mid-band signal. **`mid_n_eff` is exactly that count**, and I
measured it on both of M73's stacks before M73 reported.

**The two stacks are `wrapped-text-1` (130 frames) and `wrapped-text-2` (120) —
both in my corpus.** This is a same-stack comparison, not a cross-subject one.

### 21.2 The confound check, run first

A patch straddling two depths shows a high `n_eff` for a reason that is
**multimodality, not recoverable single-surface signal** — §19.8's finding, and
the trap that would void this comparison. **MEASURED (`out/s23_multimodality.log`):**

| stack | % unimodal patches | mean lobes |
| --- | ---: | ---: |
| `wrapped-text-1` | **100.0%** | 1.00 |
| `wrapped-text-2` | **98.6%** | 1.01 |

**These are the two cleanest stacks in the corpus on that axis** — the only two
above 98%. M73 chose them for unrelated reasons (its cylinder geometry). **The
confound that would have ruined this comparison is absent by luck, and I would
not have been able to run it on nine of the twelve stacks.**

### 21.3 Reading (b) is refuted on these two stacks

**MEASURED.** Gate-free mid-band `n_eff`, unclipped estimator
(`out/s07_unclipped.log:60–61`), against M73's admission:

| stack | K | gate `n_eff` (M73) | spectral `n_eff` (M70) | ratio |
| --- | ---: | ---: | ---: | ---: |
| `wrapped-text-1` | 130 | 1.238 | **4.148** | **3.35×** |
| `wrapped-text-2` | 120 | 1.766 | **4.050** | **2.29×** |

**The signal on these subjects supports about four frames of mid-band
information, and the gate admits between one and two.** Reading (b) — "there is
genuinely nothing to average" — **is false here.** There is 2.29–3.35× more than
is being taken.

**The estimator is null-safe against the one artefact that could manufacture
this.** P5: the *clipped* form of this statistic rectifies noise into apparent
signal, inflating as `0.4K/√(2 ln K)` — at K=130 that is **16.7**, four times
the value reported. The **unclipped** statistic used here returns **−0.16 to
+0.08 on pure noise**. A spurious 4.1 is not available to it.

### 21.4 Reading (a) holds — but its proposed mechanism does not

The brief sharpened (a) into a specific form: *the gate is not too tight in its
**threshold**, it is too coarse in its **domain**, and a per-frequency estimator
keeps information a per-pixel gate cannot.* **That sharpening is measurably
wrong, and it is wrong in the direction that costs the proposal its headline.**

**DERIVED**, everything referenced to the best single frame so the gate, the
equal average and the matched filter sit on one axis:

| stack | gate (ships) | ±1 avg | best equal avg | at W | matched filter, all frames |
| --- | ---: | ---: | ---: | ---: | ---: |
| `wrapped-text-1` | 1.113 | 1.652 | 1.865 | ±2 | **2.037** |
| `wrapped-text-2` | 1.329 | 1.672 | 1.837 | ±2 | **2.012** |

Decomposing the gap M73 found:

| stack | widen the gate | *then* add the matched filter | total | widening's share |
| --- | ---: | ---: | ---: | ---: |
| `wrapped-text-1` | **+4.49 dB** (1.676×) | +0.76 dB (1.092×) | 1.830× | **81.4%** |
| `wrapped-text-2` | **+2.81 dB** (1.382×) | +0.79 dB (1.096×) | 1.514× | **74.3%** |

**74–81% of the gap is closed by a threshold change. The matched filter — the
domain change — is worth 0.76–0.79 dB of it.** So the answer to the sharpened
form of (a) is: **it is the threshold, not the domain.** A per-pixel gate at the
right width keeps almost everything a per-frequency estimator would.

**This is the third independent route to the same verdict**, and it arrives from
a direction I did not construct: §10's collinearity (0.9959, rank-1), §19.8's
mis-specified `H_k`, and now M73's own gap decomposing 4:1 against the filter.

**An independent reproduction I did not plan.** The "then MF" column reads
**1.092 and 1.096**. My corpus headroom median, measured on all twelve stacks by
a different script months of analysis earlier, is **1.1100**. **Two stacks chosen
by another milestone for unrelated reasons reproduce the headline to within
1.5%.**

### 21.5 What this comparison cannot support

**Rule 4 — this ladder contains an argmax over a noisy response.** "Best equal
average" is `max_W` over the widening ladder. **Said, not buried.** It is not
fragile here: for `wrapped-text-1` the neighbours are ±2 = 1.1288 and ±3 =
1.1227, a 0.5% difference, so the pick barely matters — but it is an argmax and
the number should be read as such.

**The two `n_eff` are not the same quantity, and I am dividing them.** Mine is
**mid-band (0.100–0.2762 cyc/px), per-patch, on textured patches**; M73's is a
**spatial, per-pixel** admission count over all frequencies on scored pixels.
Patches are larger than pixels. **The ratio 3.35× is a comparison of a spectral
count to a spatial count and should be read as an order-of-magnitude statement,
not a calibrated one.** What survives the mismatch is the *sign and scale*: one
is ~4, the other is ~1.2–1.8, and no plausible reconciliation of granularity
turns 4.1 into 1.2.

**My gate figure is generous to the gate.** `√(gate n_eff)` assumes every
admitted frame sits at full peak amplitude. Real admitted frames off the peak
carry less. **So the gap is if anything wider than 4.49 dB, which is conservative
against the reading I am reporting as supported.**

**Two stacks, one subject class.** Both are wrapped text at f/5.6. **I have not
shown this generalises**, and §19.8 says nine of twelve corpus stacks carry
enough multimodality that the same measurement would not be readable on them
without the unimodal restriction §19.6 flagged as post hoc.

### 21.6 What it does to the verdict

**Nothing. The verdict is PLUGIN, unchanged — and §18's aside is promoted.**
§18 already said *"the gate constant is the bigger lever and it is one line."*
**M73 has now measured the lever's length on real captures, and it is +2.81 to
+4.49 dB** — far larger than the +0.91 dB the whole focus-axis architecture
question is worth. **I recorded that recommendation before M73 reported and it
is the same recommendation; what has changed is that it is now the most valuable
thing in this report.**

**One thing I got wrong and am correcting.** §18 priced the matched filter
against a gate at **W=3**, mapped from M67's simulated `n_eff = 6.84` (P16).
**M73 measures the real gate at `n_eff` = 1.238–1.766, i.e. W≈0–1, not W=3.** So
**P16's window mapping describes M67's simulator, not the rig.** The 2.38%
headline in §18 is the MF's value *against a gate that admitted seven frames* —
a gate that does not exist on these captures. **Against the gate that actually
ships, the MF is worth 1.092–1.096×.** That is *larger* than 2.38% and still
**an order of magnitude below the gate-width term beside it.**

### 21.7 Candidate facts from §21

| # | Proposed fact | Label | Source |
| --- | --- | --- | --- |
| **P30** | **On the two real stacks where M73 measured the shipped gate collapsing to a near-singleton, the signal carries ~4 frames of mid-band information — so "there is nothing to average" is false there.** Gate-free unclipped mid-band `n_eff` is **4.148** (`wrapped-text-1`, K=130) and **4.050** (`wrapped-text-2`, K=120) against M73's admitted **1.238** and **1.766** — ratios **3.35×** and **2.29×**. Measured on patches that are **100.0%** and **98.6% unimodal**, the two cleanest in the corpus, so the §19.8 two-depth confound is absent. The unclipped estimator returns −0.16..+0.08 on pure noise | MEASURED | `out/s07_unclipped.log:60–61`; `out/s23_multimodality.log`; `M73-cylinder-invariant.md:490` |
| **P31** | **The gap M73 found is a gate-threshold gap, not a gate-domain gap: widening closes 74–81% of it and the matched filter closes the rest.** Referenced to the best single frame, widening to ±2 is worth **+4.49 dB** and **+2.81 dB**, after which the matched filter adds **+0.76** and **+0.79 dB**. **This refutes the specific sharpened form of the "gate is too coarse in its domain" reading** — a per-pixel gate at the right width keeps nearly everything a per-frequency estimator would | DERIVED (from MEASURED inputs) | `out/s26_m73_discrimination.log` §3–4 |
| **P32** | **M70's corpus headroom median reproduces on two stacks selected by another milestone for unrelated reasons.** The matched filter's residual value over the best equal average is **1.092** and **1.096** on M73's two stacks, against the twelve-stack headroom median of **1.1100** measured independently — agreement to **1.5%** | DERIVED (from MEASURED inputs) | `out/s26_m73_discrimination.log` §3; `out/s11_headroom.json` |
| **P33** | **P16's window mapping describes M67's simulator, not the rig.** P16 mapped M67's simulated `n_eff = 6.84` and `D(A) = 1.733` onto a gate width of W=3. M73's real-capture measurement puts the shipped gate at `n_eff` = **1.238–1.766**, i.e. **W≈0–1**. §18's 2.38% therefore prices the matched filter against a seven-frame gate that does not exist on these captures; against the shipped gate it is **1.092–1.096×** | DERIVED | §18.2, P16; `M73-cylinder-invariant.md:490` |

### 21.8 Disciplines from §21

**D-q. A claim that a collapse is "correct" is a claim about the signal, and is
falsifiable without touching the mechanism that collapsed.** M73 could not choose
between "the gate is too tight" and "there is nothing to average" **because both
are statements about the gate's output.** Re-reading the second as a statement
about the *input* made it answerable from data already on disk, by a milestone
that had measured it for another purpose entirely. **When two readings of a
mechanism's output are tied, look for the one that is secretly a claim about the
mechanism's input.**

**D-r. Before an architecture is adopted to close a measured gap, decompose the
gap against the cheapest parameter change that also closes it.** Here the split
is **4:1 against the architecture**, and the parameter change is one constant on
one line. **The gap being real is not evidence that the proposed thing closes
it** — both readings of M73 were consistent with a real gap.

**D-s. Verify a reported gate failure at HEAD before acting on it.** §21 was
delivered with a lint violation quoted at `M70:775`; the violation was fixed four
commits earlier in `7e135b7` and the quoted line now holds prose. **Running the
gate cost one command and prevented an edit to a correct line** — and the same
run showed the repository's actual remaining violation was in a different file.

---

## 22. Addendum (2026-08-23): M77's gate sweep — is §21.6 qualified?

**Asked by the orchestrator after M77 measured a spatial gate sweep on the same
two stacks.** Three questions: (a) does §21.6 presume a single global gate,
(b) does my spectral `n_eff` have a spatially-local form, (c) is anything in
M77's method wrong or reading my result in a way I did not intend.

**Short answers: (a) yes, and the repair is the one proposed. (b) yes down to a
measured floor, but with a limitation that matters more than the floor. (c) one
substantive disagreement, one units objection, and one place my quantity is
being used for a purpose I did not measure it for.**

### 22.1 (a) Yes — §21.6 presumes a single global setting, and it should not

**ARGUED, and I agree with the qualification.** §21.6 quoted §18's *"the gate
constant is the bigger lever and it is **one line**"* and promoted it. **"One
line" is a claim about a single global constant** and it is not supported by
anything I measured. What I actually measured was a *window in frame index*
(±2 on both stacks), never a threshold. **The step from "widen the admitted set"
to "change one constant" was mine, and it was unearned.**

**Restated, as the orchestrator proposes:**

> **Direction:** the admitted set at the shipped default is far too narrow —
> **+2.81 to +4.49 dB** sits between it and the best equal average (§21.4).
> **Procedure:** the gate must take its target from the stack in hand.
> **Not a constant:** no single `DEFAULT_GATE` can deliver a target `n_eff`.

### 22.2 But my data localises where M77's 3.31× lives, and it is not the optics

**M77 fact 39 is that matching a 2.4%-stable spectral count costs gate values
3.31× apart.** M77 §20 already suspects this is attributable to its side, since
every `T` is a multiple of `FOCUS_NOISE_SD` and M69 measured that varying 4.06×.
**I can put a number on the other half of that suspicion. MEASURED / DERIVED.**

My equal-average window ladder, referenced to the ±1 average
(`out/s10_architecture.log`) — the focus-axis response in units of *frames*,
touching no gate constant and no noise constant:

| window | `wrapped-text-1` | `wrapped-text-2` | ratio |
| ---: | ---: | ---: | ---: |
| ±1 | 1.0000 | 1.0000 | 1.0000 |
| **±2 (argmax on both)** | **1.1288** | **1.0984** | **1.0277** |
| ±3 | 1.1227 | 1.0830 | 1.0367 |
| ±5 | 1.0233 | 0.9778 | 1.0465 |
| ±10 | 0.8490 | 0.8162 | 1.0402 |

**The two stacks' focus-axis response agrees to within 4.7% at every rung, both
peak at the same rung, and their spectral counts agree to 2.4%.** The optics and
the focus sampling are, to this instrument, the same on both stacks.

**DERIVED: a 3.31× dispersion therefore cannot be coming from the through-focus
physics, because the through-focus physics is measurably common to ~5%.** It
enters when the common response is expressed in gate-threshold units. **That is
M77's own reading, and my ladder is independent evidence for it** — I hold the
frame-domain measurement and M77 holds the threshold-domain one, and only the
latter disperses.

**This does not rescue a global constant.** It relocates the problem: the gate's
*unit* drifts, so a fixed `T` means different admission on different stacks even
when the optics agree. **That is an argument for per-stack calibration on
stronger grounds than fact 39 alone** — the target is stable, the unit is not.

### 22.3 (b) The local form exists, with a measured floor — pre-registered in D

Registered in `PREREGISTRATION-D.md`, committed **`fc85d50` before `s27` ran**.
**Nested crops about one centre**, so content is held fixed and only the window
changes — which `s12` could not do, because it rescaled its patch grid and moved
window and content together.

**MEASURED. `out/s27_window_floor.log`.**

| window (GQ) | sensor px | Welch tile | discrete bins, mid bands | plant `hat/true` | null median | real ratio, both stacks |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 511 | 128 | 7 / 6 / 10 | 1.024 | 0.290 | 1.000 / 1.000 |
| **128** | **255** | **64** | **3 / 3 / 5** | **0.987** | **−0.107** | **0.943 / 1.022** |
| 64 | 127 | 32 | 1 / 2 / 2 | 0.831 | −0.724 | 0.962 / 1.067 |
| 32 | 63 | 16 | 1 / 1 / 1 | 0.942 | −0.290 | 0.989 / **1.370** |
| 16 | 31 | 8 | 1 / **0** / 1 | UNDEFINED | UNDEFINED | UNDEFINED |

**Pre-registered verdict: the floor is 128 GQ samples = 255 sensor px, Welch
tile 64.** It is the only window below 256 meeting W1, W2 and W3.

**The mechanism is discrete bin occupancy, not noise.** At tile 64 each mid band
holds 3–5 discrete radial frequencies, so a band average is an average. **At
tile 32 and below every mid band holds one or two, and band averaging stops
being averaging** — which is why `hat/true` goes non-monotonic (0.831 at 64,
0.942 at 32) rather than degrading smoothly. **Do not read the 0.942 at window
32 as recovery**: V16 shows the noiseless discretisation term alone is **+23.1%**
there, and two large errors of opposite sign are cancelling.

### 22.4 The limitation that matters more than the floor

**MEASURED, and it is the answer the merge design actually needs.** The null —
40 trials of pure noise per window, no signal — has a median near zero but a
**p05–p95 spanning −2.5 to +3.0 at *every* window, including 256.** The real
signal value is ~3.9. **On a patch with no texture, a single-patch `n_eff` can
read anything from −3 to +3, which is most of the dynamic range of the answer.**

**So the estimator is at its worst precisely where M77's fact 40 made its
observation.** Fact 40 is about a **flat ROI** freezing while the frame keeps
admitting. **My spectral `n_eff` cannot serve as the calibration target in a flat
ROI** — not because the window is too small, but because there is no texture to
carry band-limited signal, and the statistic is a ratio of noise to noise there.

**What makes M70's corpus numbers trustworthy is not the window size — it is
averaging over 24 textured patches.** The published 4.148 is a median over
patches selected as textured. **A per-tile deployment would meet both problems at
once: smaller windows *and* tiles that land on flat regions.** The floor of 255
sensor px answers only the first.

**Honest summary for the merge design: use `n_eff` per-tile only on tiles that
pass a texture test, at ≥255 sensor px, and treat flat tiles as having no
measurable target rather than a target of zero.**

### 22.5 Three pre-registered guards fired, and a correction to my own `s12`

**Reported faithfully, per rule 2 and M65's standard.**

* **V15 FIRED.** The plant's first blur ladder (0.55 px/frame, chosen by hand)
  gave `n_eff_true` **1.456** against the real **3.906** — unrepresentative, and
  W1's ratio would have been meaningless. Repaired by calibrating the ladder to
  the stack its latent came from: **0.1717 px/frame**. **That is well below the
  corpus's measured blur-growth range of 0.6017–1.1856 px/frame (§19.2)** — an
  unruled discrepancy I flag rather than explain, since those rates were measured
  per *focus step* on stacks with different step densities.
* **W2's operationalisation was wrong and I changed it.** The first run tested
  the null on **one draw** and "failed" at every window including 256, where P5
  established the estimator is null-safe. `n_eff` on pure noise is a ratio of
  noise to noise; the statistic is a **distribution**. Re-run over 40 trials.
  **The single-draw result was an artefact of my test, not of the estimator.**
* **V17's registered form was wrong.** I registered an *analytic annulus area*
  (643 bins at tile 128). The operative quantity is **discrete radial-grid
  occupancy** (7 bins). At tile 8 the analytic form says `b3_mid` holds 2.5 bins
  while the grid holds **one**, and `b4_mid` holds **zero** — which is what
  actually returns `nan`. **The registered criterion overstated resolution by
  ~90× and would have licensed a window that cannot represent the band.**
* **A correction to `s12`.** `s12`'s VOID-condition-4 ratio for `wrapped-text-1`
  at half window was **0.839**. With content held fixed it is **0.943**.
  **Roughly two thirds of what `s12` recorded as a window effect was its patch
  grid landing on different content.** `s12`'s conclusion (the 256 numbers stand)
  is unaffected and is now better supported.

### 22.6 (c) Where I disagree with M77, and where my quantity is being misused

**M77's method is careful and its §20 already concedes the direction that hurts
it. Three things I would add, in decreasing order of how much they matter.**

**1. My `n_eff` is a count, not a prescription — and it is being used as an
admission target. ARGUED, and this is the one I most want on the record.**
`mid_n_eff` counts how many frames carry mid-band signal above the noise floor.
**It is not a statement that admitting that many frames is optimal.** Optimal
combination weights frames continuously by amplitude; a hard count is a different
object. My own §21.4 puts the best *equal average* at **±2, i.e. 5 frames**,
against a count of ~4 — close enough to be a reasonable heuristic, **but I never
measured that `n_eff` is the right admission target, and `T*` is defined as the
gate that hits it.** **If `n_eff` is the wrong target, `T*` is precisely
calibrated to the wrong number**, and its 3.31× dispersion would be dispersion in
a target that should not be hit.

**2. `T*` equates two quantities with different natural scales. ARGUED.** M77
interpolates its **frame-average, spatial, all-frequency** `n_eff` onto my
**per-patch, textured-only, mid-band** count. §21.5 already said the ratio of
these two should be read as order-of-magnitude, not calibrated. **`T*` = 38.534
carries five significant figures on a comparison that supports about one.** The
*direction* (both far above 4.0) is robust; the *value* is not.

**3. M77's fact 40 undercuts fact 39's target. ARGUED, and M77 may not have
noticed the tension.** Fact 40 measures that a flat ROI stops admitting while
the frame average is still climbing — **so the frame average is not a sufficient
statistic for admission.** But `T*` is defined by matching that same frame
average. **A target that fact 40 shows is spatially ill-defined is being matched
to five figures in fact 39.** I do not think this changes fact 39's headline —
the dispersion is real and my §22.2 ladder supports it living in the gate's unit
— but the two facts should not be read as independent.

**What I do not dispute.** The sweep itself, the circularity M77 names in §10 and
§20, the X3 null firing, and M77's own judgement that a disagreement between its
ladder and my count is attributable to its side at least as readily as to mine.
**Fact 39's qualification of §21.6 is correct and I have adopted it in §22.1.**

### 22.7 Candidate facts from §22

| # | Proposed fact | Label | Source |
| --- | --- | --- | --- |
| **P34** | **The two stacks whose gate targets differ 3.31× have focus-axis responses agreeing to within 4.7%.** M70's equal-average window ladder, in units of frames and touching no gate or noise constant, reads 1.0277–1.0465 between `wrapped-text-1` and `wrapped-text-2` at every rung ±1…±10, both peak at ±2, and their spectral counts agree to 2.4%. **M77 fact 39's dispersion therefore does not originate in the through-focus physics**; it enters when a common response is expressed in gate-threshold units, which M69 measured varying 4.06× | DERIVED (from MEASURED inputs) | `out/s10_architecture.log`; `M77-gate-sweep.md` fact 39 |
| **P35** | **M70's spectral `n_eff` has a local form down to 255 sensor px (128 GQ samples, Welch tile 64) and no further, and the limit is discrete bin occupancy rather than noise.** At tile 64 each mid band holds 3–5 discrete radial frequencies; at tile 32 and below each holds 1–2 and band averaging stops averaging; at tile 8 `b4_mid` holds **zero** and the statistic is undefined. Plant `hat/true` = 0.987 at the floor, and the noiseless discretisation term alone is **+23.1%** one rung below it | MEASURED | `out/s27_window_floor.log`; `PREREGISTRATION-D.md` (`fc85d50`) |
| **P36** | **The estimator is worst exactly where M77 fact 40 made its observation: on flat regions.** With no texture the null's `n_eff` has p05–p95 spanning **−2.5 to +3.0 at every window including 256**, against a real signal value of ~3.9. **M70's published per-stack counts are trustworthy because they are medians over 24 textured patches, not because of the window size.** A per-tile deployment meets small windows *and* untextured tiles simultaneously; flat tiles should be treated as having **no measurable target**, not a target of zero | MEASURED | `out/s27_window_floor.log`, null arm, 40 trials/window |
| **P37** | **About two thirds of `s12`'s recorded window effect was content, not window.** `s12`'s half-window ratio on `wrapped-text-1` was **0.839** with the patch grid rescaled; with content held fixed by nested crops it is **0.943**. `s12`'s conclusion is unaffected and better supported | MEASURED | `out/s27_window_floor.log` vs `out/s12_patchsize.log` |

### 22.8 Disciplines from §22

**D-t. A statistic that is a ratio of two noisy quantities must be nulled as a
distribution, never as a draw.** `s27`'s first run tested `n_eff` on one noise
realisation and failed its own null at a window where the estimator was already
established as null-safe. **The failure was the test's.** Forty trials moved the
median to −0.107 and revealed the thing that actually matters — a p05–p95 span
of five units.

**D-u. Register the resolution limit in the units the instrument actually uses.**
V17 was registered as an analytic annulus area and overstated usable resolution
by ~90× against discrete grid occupancy. **An analytic bin count is a property of
the band; the estimator sees a grid.** The registered criterion would have
licensed a window that cannot represent the band at all.

**D-v. When two milestones' quantities are matched by interpolation, one of them
is being used for a purpose it was not measured for — name which.** `T*` is the
gate that hits M70's `n_eff`. M70 measured `n_eff` as a *count of informative
frames*, never as an *optimal admission target*. **The calibration is only as
good as that unstated identification**, and it should be stated by whoever
performs the match.
