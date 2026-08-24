# M70 — pre-registration

**Written and committed before the decisive corpus measurement was run.**
Rule 2. The criteria below were fixed with only the following in hand: the EXIF
census (`out/exif-census.json`), the M5 reproduction (`out/s02_reproduce_m5.log`),
and the plant / rule-20 / negative-control run (`out/s03_plant.log`). No band
power from any corpus stack had been computed.

---

## 0. The question

An external reviewer proposes that `strehl`'s merge should be a multi-frame
Wiener deconvolution along the focus axis rather than the shipped gated
noise-aware average, on the empirical premise that

> frames one or two steps off peak still carry mid-frequency information at
> MTF 0.3–0.8, and the matched filter harvests it: an SNR gain of roughly
> √(Σ|H|²) in the band where the current analysis counts them as zero.

M70 measures that premise. The architectural output is binary: **core** (the
merge is rebuilt around deconvolution) or **plugin** (deconvolution stays an
opt-in stage behind a boundary).

## 1. The observable

For a patch at frequency band *b* and frame *k*, the measured band power is

```
P_k = |H_k|² |L|² + σ²          S_k := P_k − σ̂²
```

`|L|` is the latent, common to every frame, so it cancels in any ratio across
`k`. Two statistics follow directly:

* `n_eff_MF = Σ_k S_k / max_k S_k` — the matched filter's effective frame
  count. `√(n_eff_MF)` **is** M20 §4.2's corrected gain shorthand
  `√(Σ|H|²)/max|H|`: the SNR gain of the matched filter over inverse-filtering
  the single sharpest frame. This is the reviewer's own claimed mechanism,
  expressed as something measurable without knowing `L`.
* `rel_amp_d = A_{peak±d} / A_peak = |H_{peak±d}| / |H_peak|` — a *relative*
  MTF at ±d focus steps from peak. This is the reviewer's "MTF 0.3–0.8 one or
  two steps off peak", tested on its own terms.

`σ̂²` is the shipped photon-transfer model from `crates/strehl-core/src/profile.rs`
(`σ² = g·S̄_{w²} + (RN_e·g)²`), evaluated at the w²-weighted patch mean because
that is the level the Welch periodogram's expectation actually integrates.
`FOCUS_NOISE_SD` is **not** used anywhere: M66 found it 19–21% low on real
texture and M69 is live on it.

## 2. What the controls already established (`out/s03_plant.log`)

These are inputs to the criteria, not results of them.

| control | result |
| --- | --- |
| **rule 20** — static repeat burst, K=41, truth `n_eff_MF = 41` | measured **40.11 / 40.13 / 39.72** raw in b3/b4/b5 (recovery 0.969–0.979). The estimator *can* report "many frames carry mid-band signal". |
| **plant** — real 119MSDCF texture through a known OTF ladder, δ swept 0.125→2.0 px/step (16×) | recovery of `n_eff_MF_raw` = **0.994–1.041** at every δ and every mid band. Truth spans 30.5 → 1.17, so the plant can express both a wide and a collapsed response (rule 13). |
| **negative control** — flat latent, calibrated noise only, K=41 | `n_eff_MF_raw` = **4.69–8.49**, not 0. There is a positive floor. |
| rule-4 mitigation, measured not argued | the `[1,2,1]`-smoothed denominator **inflates** `n_eff_MF` by up to **1.93×** at δ=2.0 and by **2.7×** on noise alone. The *raw* statistic is the honest one and is the pre-registered primary. The smoothed one is reported only as a generous bracket. |

**Consequence, and it is binding:** a bare `n_eff_MF` cannot be read against 1.
Every reading is scored against a floor measured at the same K, by two routes:

* **synthetic** — noise-only frames at that stack's own K and ISO;
* **empirical (primary)** — the stack's own *flat* patches, which contain no
  signal at any frequency and therefore absorb PRNU, model bias and drift as
  well (rule 9's flat-ROI control, doing double duty).

## 3. Design, fixed here

* **Patches:** a deterministic 4×6 grid of GQ patches, 256 GQ samples each
  (511×511 sensor px), at row fractions (0.20, 0.40, 0.60, 0.80) and column
  fractions (0.15, 0.32, 0.49, 0.66, 0.83, 0.95→clamped) of the active area.
  No patch is chosen by its focus behaviour (rule 17).
* **Textured vs flat:** a patch is *textured* on a stack if its peak-frame
  low-band (0.025–0.050 cyc/px) power exceeds 10× the modelled noise floor —
  M5's own `DYN_GATE = 10.0`. The low band is chosen because it is the least
  focus-sensitive band available, so the classification is close to orthogonal
  to the mid-band statistic being tested. Flat patches become the control
  population.
* **Bands (sensor cyc/px, fixed in `m70lib.BANDS` before any corpus spectrum
  was computed):** b1_low 0.025–0.050, b2 0.050–0.100, **b3_mid 0.100–0.150,
  b4_mid 0.150–0.200, b5_mid 0.200–0.2762**, b6_above_f11_cut 0.2762–0.3400.
  Mid bands are b3/b4/b5.
* **All twelve stacks**, every frame, no subsampling. If any stack is
  subsampled for time it will be named as such in the report.

## 4. Pre-registered criteria

### Criterion A — the reviewer's own number

Statistic: per stack, the median over textured patches of `rel_amp_1` and
`rel_amp_2` in the mid bands.

* **SUPPORTS the premise** if median `rel_amp_2 ≥ 0.30` on **≥ 6 of 12** stacks.
* **REFUTES the premise** if median `rel_amp_2 < 0.30` on **≥ 9 of 12** stacks.
* Otherwise **INDETERMINATE**.

0.30 is the bottom of the reviewer's own quoted MTF range.

### Criterion B — the decisive architectural criterion

Statistic: per stack, the median over textured patches of mid-band
`√(n_eff_MF_raw)`, together with the same median over the flat control
population at the same K.

* **CORE** if median `√(n_eff_MF_raw) ≥ 1.50` on **≥ 7 of 12** stacks **and**
  the textured median exceeds the flat median by **≥ 2×** on those stacks.
* **PLUGIN** if median `√(n_eff_MF_raw) ≤ 1.25` on **≥ 7 of 12** stacks.
* Otherwise **INDETERMINATE**.

1.25× SNR is 1.9 dB. The shipped gated mean already reaches 0.534× single-frame
noise (fact 19) = 1.87× SNR in the bands it admits; a mechanism that buys under
1.9 dB in a *restricted* band, at the cost of rebuilding the merge, is a plugin
by inspection. 1.50× (3.5 dB) is set as the level at which the mid-band prize
becomes comparable to what the whole existing gate achieves.

### Criterion C — gain over what actually ships

Statistic: per stack, the median over textured patches of mid-band
`mf_gain_over_top_m(m)` for m ∈ {1, 2, 3, 5}. m=3 is the headline (fact 212's
`n_eff` target; M38 measured 2.26–7.42 across five stacks). The estimator uses
`Σ|H_k|` where `|Σ H_k|` is correct and `|ΣH| ≤ Σ|H|`, so it is a **lower
bound** on the gain — conservative against the proposal, deliberately.

* **CORE** if median `mf_gain_over_top_3 ≥ 1.30` on **≥ 7 of 12** stacks.
* **PLUGIN** if median `mf_gain_over_top_3 ≤ 1.10` on **≥ 7 of 12** stacks.
* Otherwise **INDETERMINATE**.

### Criterion D — step-density dependence (the corpus's free design)

The corpus spans 19→299 frames (≈15× in focus-step density) at comparable
subject scale. Whatever A–C return, the report must state whether the answer is
a property of the physics or of one shooting habit.

* **PHYSICS** if the stack-median mid-band `n_eff_MF` varies by **< 3×** across
  the 15× frame-count span, or if it scales sub-linearly with frame count such
  that `rel_amp_1` is stable to within ±0.15 across the span.
* **HABIT** if `n_eff_MF` scales roughly linearly with frame count
  (regression slope of log `n_eff_MF` on log K in [0.7, 1.3] with the span
  covering ≥ 5×), which would mean the answer is set by how finely the operator
  stepped and not by the optics.

## 5. Conditions that VOID a reading (report faithfully, do not reinterpret)

1. **Floor swamp.** If for a stack the flat-patch median mid-band `n_eff_MF`
   exceeds **50%** of the textured median, that stack's Criterion B and C
   readings are VOID and are reported as VOID, not as low or high.
2. **Broken subtraction.** On the three f/11 stacks, fact 27 says the
   0.2762–0.3400 band contains no optical signal. If `n_eff_MF` in b6 is **not**
   below the mid-band value there, the noise subtraction is not working and all
   f/11 readings are suspect and must be reported as such.
3. **σ sensitivity.** `σ̂²` is scaled by 0.75× and 1.25×. If either scaling
   flips a pre-registered verdict, the verdict is reported **INDETERMINATE**
   regardless of the point estimate.
4. **Patch-size sensitivity.** The whole measurement is repeated at 128 GQ
   samples on a subset. A patch mixes depths within its footprint, which
   broadens the apparent through-focus response and is therefore *generous* to
   the proposal. If halving the patch changes the stack-median `n_eff_MF` by
   more than 1.5×, the 256-sample numbers are reported as an upper bound only.

## 6. Named adversarial inputs (rule 20)

The inputs that would make each answer come out the *wrong* way, and where each
is handled:

| would produce | mechanism | handled by |
| --- | --- | --- |
| falsely **large** `n_eff_MF` | a static repeat burst / no focus variation at all | it does: 40.1/41 measured. This is the discharge — the estimator is *capable* of the large answer. |
| falsely **large** | PRNU / fixed-pattern structure, frame-invariant, masquerading as off-peak signal | flat-patch floor absorbs it; fact 27's floor/model 0.950× and this milestone's reproduced 0.977–0.996× bound it small |
| falsely **large** | under-subtracted σ̂² leaving a positive pedestal in every frame | negative control measures the pedestal at matched K; σ ±25% sweep; VOID condition 1 |
| falsely **large** | subject drift moving texture through a fixed patch on deep stacks | peak-windowed `n_eff_MF` variant; Criterion D |
| falsely **large** | patch footprint spanning multiple depths | VOID condition 4 |
| falsely **small** | winner's curse inflating `max_k S_k` | measured on the plant: raw recovery 0.994–1.041, so ≤ 4% — and it biases *against* the proposal, so a low reading is not explained by it |
| falsely **small** | over-subtracted σ̂² | σ ±25% sweep |
| falsely **small** | the estimator simply being unable to see wide responses | refuted by the rule-20 arm and by the δ=0.125 plant (truth 30.5, measured 30.7) |

## 7. What this measurement cannot see, stated in advance

* **Phase.** Only `|H_k|` is observable from single-frame power spectra. A
  matched filter's true gain uses complex `H`. Criterion C's `Σ|H|` denominator
  makes the reported gain a lower bound; nothing here bounds phase error.
* **Absolute MTF.** Every statistic is a *ratio* across frames at fixed
  frequency. This measures the through-focus response, not the optical
  response. The brief's third question (attenuated-but-present vs absent below
  the cutoff) is therefore only partially answerable and will be reported as
  such.
* **Whether a deconvolution would actually be better.** M41 already measured
  that and refuted it on the noise axis. M70 measures the premise only.
