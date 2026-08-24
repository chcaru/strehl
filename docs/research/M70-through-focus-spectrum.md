# M70 — The through-focus spectrum: is deconvolution the core of the merge, or a plugin?

**Status: MEASURED. The reviewer's premise is TRUE. The architectural inference
drawn from it is FALSE, and the gap between the two is measured at 1.110×.**

**Verdict: PLUGIN.**

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
| ±3 | 7 | 1.0238 |
| ±5 | 11 | 1.0811 |
| ±10 | 21 | 1.2316 |
| ±20 | 41 | 1.4150 |

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

---

## 10. Verdict on the architecture

**PLUGIN.**

The measurement that decides it, in one line: **over the frames a merge would
actually admit, a matched filter beats an equal-weight average of those same
frames by 1.0020 (median, best-3) to 1.1100 (median, best window against best
window) — while the frames themselves are scaled copies of one another to within
0.0041 of exact rank-1, against a control that reaches 0.9121 when they are not.**

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
  quantity they said, in every stack. It is simply not *new* information.

---

## 11. Proposed facts

Numbered `P1…P12` per AGENTS rule 28. **Absolute `§4` numbers belong to the
orchestrator at fold time.** Before folding, match the first ~70 characters of
each against the whole of `§4` and require zero matches (rule 28, rule 25). P4
and P10 are close in subject to facts 27, 28 and 212 and must be checked for
content collision, not number collision.

| # | Proposed fact | Label | Source |
| --- | --- | --- | --- |
| **P1** | **The focus-axis matched filter's entire architectural prize on this corpus is 1.110× mid-band SNR (+0.91 dB), median over 12 stacks, range 1.0696–1.2037** — best matched filter at any window ÷ best equal-weight average at any window, mid band 0.100–0.2762 sensor cyc/px. Stable across the noise model's measured uncertainty: 1.1047× at σ×0.91, 1.1245× at σ×1.09. For scale, fact 19's shipped gated mean is 1.873× (+5.45 dB) in every band it admits | MEASURED | `out/s11_headroom.log` |
| **P2** | **A matched filter over the frames a merge already admits is worth 1.0020× (median; range 1.0009–1.0107) over an equal-weight average of those same three frames**, and 1.0811× (range 1.0269–1.2843) over an equal average of the same eleven. The total gain of a matched filter over a 3-frame average factors exactly as `weight × reach`, and the reach term — 1.3987 median at ±5 — is a gate-width question requiring no new merge architecture | MEASURED | `out/s09_decomposition.log` §1, `out/s10_architecture.log` |
| **P3** | **Frames within ±5 of peak are scaled copies of one another, not distinct spectra.** σ₁²/Σσ² of the row-normalised band-amplitude matrix (11 frames × 5 bands) is 0.9860–0.9983 (median 0.9959) across all 12 stacks, against controls of 1.0000 (synthetic rank-1), 0.9121 (iid noise rows) and 0.9749 (a planted 1.0 px/step defocus ladder). The corpus is 6.1× closer to exact rank-1 than a 1-px/step ladder. **This is the mechanism behind M41's kill of R3** | MEASURED | `out/s09_decomposition.log` §2 |
| **P4** | **The reviewer's "MTF 0.3–0.8 one or two steps off peak" is measured true and understated at ±1.** Median relative amplitude in the mid band is `rel_amp_1` 0.879–0.970 and `rel_amp_2` 0.461–0.858 across all 12 stacks, 1,568 frames, three apertures, ISO 50–1000. Criterion A supports on 12/12, and on 10/12 with the noise model mis-set by +25% | MEASURED | `out/s07_unclipped.log` §3 |
| **P5** | **A statistic that clips per-frame band signal at zero before summing rectifies noise into apparent signal, with inflation growing as `0.4K/√(2 ln K)`.** Measured by Monte Carlo on pure noise: the clipped `Σ_k S_k / max_k S_k` returns 4.12 at K=19 rising to 42.07 at K=299, where the unclipped statistic returns −0.16 to +0.08. **Any multi-frame Wiener merge estimating `|H_k|` from noisy per-frame power and clipping at zero harvests exactly this**, and the bias grows with stack depth | MEASURED | `out/s07_unclipped.log` §1 |
| **P6** | **The unwindowed `Σ_k S_k` is not a measurable quantity on deep stacks**, because it accumulates K× the per-frame photon-transfer-model error. Corpus-median mid-band `n_eff` goes 13.77 → 6.57 → −1.68 as σ̂ is scaled ×0.75 → ×1.00 → ×1.25, i.e. it goes negative under a mis-set only 2.7× fact 29's own published ±9%. An ±5-frame window bounds the accumulation to 11 frames and moves 6.60 → 4.87 over the same range | MEASURED | `out/s08_decisive.log` §D |
| **P7** | **`n_eff(±1)` in the mid band is 2.77–2.94 across the entire corpus** — a 1.06× spread over a 15.7× range in frame count (19→299), three marked apertures, ISO 50–1000 and subjects from coffee foam to insect anatomy; regression slope of log `n_eff` on log K is +0.005 (R² 0.10). **The three-frame neighbourhood carries the same effective information density everywhere on this rig.** Independently corroborated by fact 212's `nwide = 3` from a different operator and statistic | MEASURED | `out/s09_decomposition.log` §3, `out/s08_decisive.log` §C |
| **P8** | **The mid-band answer is not an artefact of an insensitive estimator, discharged on real data.** In the low band (0.025–0.050 cyc/px) every frame clears a 3σ floor on 10 of 12 stacks, and the low-band `n_eff` reaches 19.00 at K=299, while the mid band on the same patches of the same frames reads 12.83. The estimator reports wide through-focus responses on real frames when they exist. On a static repeat burst it recovers 40.1 of 41 | MEASURED | `out/s08_decisive.log` §B, `out/s03_plant.log` |
| **P9** | **Fact 27's f/11 diffraction cutoff is independently confirmed by frame counting, on two stacks it was not measured from.** In the band 0.2762–0.3400 cyc/px the median number of frames carrying signal above a 3σ calibrated floor is 0.0 / 4.0 / 0.0 on the three f/11 stacks, against 33.5 at f/5.6 where the same `B = 3` geometry puts the cutoff at 0.5541 cyc/px, above the green-quincunx reach. A different statistic from the knee fit, returning zero where the optics say zero | MEASURED | `out/s08_decisive.log` §A, §E |
| **P10** | **At f/11 the top of the mid band is already at the noise floor, inside the nominal passband.** Peak-frame band SNR `(P−σ̂²)/σ̂²` in 0.200–0.2762 cyc/px is 0.08–0.81 (median 0.38) on the three f/11 stacks, against 9.57 median in 0.100–0.150. Fact 27 located the cutoff; this locates where approaching it stops paying. The b6/b5 SNR ratio is aperture-ordered — 0.230 / 0.224 / 0.114 at f/5.6 / f/8 / f/11 — though scene spectrum is not held fixed across the groups | MEASURED (ratio ordering: ARGUED) | `out/s13_bandsnr.log` |
| **P11** | **`D:\personal\macro` is 75.3% f/5.6 by frame count, not f/11.** Marked apertures: f/5.6 on 119MSDCF, wrapped-text-1/2 and bee-1/2/3 (1,180 frames); f/8 on coffee-bubbles, foam, coffee-bean (224); f/11 on 109MSDCF, 112MSDCF, 113MSDCF (164). Every one of the five stacks captured in the most recent session (2026-08-23, 1,147 frames, 73% of the corpus) is f/5.6. **Fact 27's cutoff, and any claim that ~45% of the sampled band is empty, is an f/11 result covering 10.5% of the corpus** | MEASURED | `out/s01_exif_census.log`, `out/exif-*.tsv` |
| **P12** | **The band-power estimator's absolute normalisation and sampling error are measured, not assumed:** on synthetic calibrated noise (400 realisations, 256-sample GQ patch, tile 128) band means are 0.998–1.003 σ² and per-realisation sd is 0.0147–0.0678 σ² by band. Halving the patch to 128 GQ samples changes stack-median `n_eff` by 0.832–1.073× on a four-stack subset spanning both frame-count extremes and all three apertures | MEASURED | `out/s08_decisive.log` §0, `out/s12_patchsize.log` |

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

**Deliberately not measured.**

* **Whether a deconvolution would produce a better image.** M41 measured that and
  refuted it, and re-running it would be manufactured work. M70's charter was the
  premise, not the outcome.
* **`FOCUS_NOISE_SD`.** M69 is live on it and the brief said not to rely on its
  absolute value. Every noise scale here comes from the photon-transfer model in
  `profile.rs`; `FOCUS_NOISE_SD` appears nowhere in this milestone's code.
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
