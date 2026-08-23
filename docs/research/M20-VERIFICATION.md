# M20 — INDEPENDENT VERIFICATION

**Verifier:** independent agent (not the author). **Date:** 2026-08.
**Document under test:** [`M20-deconvolution-ceiling-measured.md`](M20-deconvolution-ceiling-measured.md) @ `dd1326e`,
with its triage [`../proposals/2026-08-external-review.md`](../proposals/2026-08-external-review.md).
**Status:** VERIFIED WITH CORRECTIONS.

Project rule 12: the author never verifies their own work. M20 was written by the
orchestrator and was the weakest-provenance document in the corpus. This is the
independent pass.

**Method.** Every number below was re-derived with code written from the report's *prose
specification*, not from the author's scripts. The author's scripts in
`experiments/m20-deconvolution-ceiling/src/` were read to understand what was done and
were **never executed**. The verifier's code is in
`experiments/m20-deconvolution-ceiling/verify/` (`v1`–`v10`). Where the verifier had a
stronger method available than the author used (analytic proof instead of Monte Carlo,
five stacks instead of one, a direct calibration instead of a unit conversion), it was
used.

---

## 0. Verdict summary

| Gate | Claim | Verdict |
| --- | --- | --- |
| 1 | The optics model reproduces facts 12 / 27 / 28 | **REPRODUCED** — arithmetic exact. **But the gate is a TAUTOLOGY** (§1). |
| 2 | `L̂ = ΣH*Y/(Σ\|H\|²+σ²/S)` is MMSE; gain is `√(Σ\|H\|²)/max\|H\|` | **REPRODUCED** and strengthened to an analytic proof. **CORRECTED**: the residual's cause is misattributed (§2). |
| 3.1 | Unguarded Wiener is worse than selection, by up to 31% | **REPRODUCED** — all 20 cells to 4 dp; worst penalty 31.3% (§3). |
| 3.2 | Implementable crossover σ ≈ 0.03; power-law prior loses everywhere | **REPRODUCED** — crossover 0.0324 (§3). |
| 3.3 | 15.1% of real pixels below crossover; median 3.3× past; survives 2× error | **REPRODUCED on 109MSDCF, REFUTED as a corpus figure** — the range is 3.5%–65.8% (§4). |
| 3.4 | The guard is a real change and τ is not tuned | **REPRODUCED** — genuine one-parameter family, flat to τ=48. One row **CORRECTED** (§3). |
| 3.5 | Depth model does not drive the result | **CORRECTED** — true for selection/guarded, false for the unguarded Wiener (§3). |
| 4 | f/11→f/5.6 gives 9.6× contrast, 13.5×/6.9× SNR | **REPRODUCED at the stated parameters; CORRECTED as a point estimate** — 3.1×–12.6× over B, 3.3×–∞ over λ (§5). |
| 5 | mean\|∇\| is one-sided; sel reads above truth at σ=0.05 | **REPRODUCED** (§6). Fact-24 corroboration **CORRECTED** for baseline mismatch. |
| — | **Headline: "deconvolution stays opt-in, not the core merge"** | **SURVIVES.** The margin does not — see §7. |

---

## 1. Gate 1 — the optics model: REPRODUCED, but it is a tautology

### 1.1 Arithmetic (`v1_optics.py`)

Re-derived from first principles: incoherent cutoff `1/(λN)` cyc/mm × pitch → `f_c = pitch/(λ·N_eff)`
cyc/px. The diffraction MTF `(2/π)(acos u − u√(1−u²))` was independently cross-validated against a
*numerical autocorrelation of a circular pupil* (max abs deviation 1.1e-4, sampling-limited), and the
geometric defocus-disc OTF `|2J₁(πdf)/(πdf)|` against a numerically integrated semicircular line-spread
function (max abs deviation ~1e-5). The formulae are right.

| Row | Claimed | Verifier | Match |
| --- | --- | --- | --- |
| `f_c(N_eff = 33.7)` | 0.2762 | **0.27620** | exact |
| `N_eff` at `f_c` = Nyquist | 18.618 | **18.6182** | exact |
| MTF@Nyq, m=2.0, marked f/5.6, B=3 | 0.0361 | **0.03614** | exact |
| MTF@Nyq, marked f/8 | 0.0000 | **0.00000** | exact |
| MTF@Nyq, marked f/11 | 0.0000 | **0.00000** | exact |
| Critical sampling, marked | f/6.206 | **f/6.2061** | exact |

Six of six. **REPRODUCED.**

### 1.2 The circularity audit the report did not run

The report calls this a *gate* — an external check that licenses the model. It is not.

`M5-diffraction-measured.md` line 26 records the actual provenance: M5 measured a spectral knee at
`f_sig = 0.2762` sensor cyc/px on 109MSDCF at marked f/11, then **inverted the very same equation**
`f_c = pitch/(λN)` to obtain `N_eff = 33.706` and hence the bellows factor `B = 33.706/11 = 3.064`.
Fact 12's provenance column reads "F (DERIVED)". So:

- **Row 1** (`f_c(33.7) = 0.2762`) is the exact algebraic inverse of its own input. It cannot fail.
- **Rows 2 and 6** contain no measured quantity at all — they are `pitch/(λ·f_Nyq)` and a division.
- **Rows 3–5** use `N_eff = marked × B`, and `B` came out of the same equation on the same knee.

There is exactly one empirical fact in the chain — *that 109MSDCF has a spectral knee at 0.2762 and a
floor matching the photon model* — and M20 re-derives neither.

**Verdict: the arithmetic is REPRODUCED; the gate is a TAUTOLOGY.** No configuration of the model
could have failed this table. The report's sentence "All six reproduce to 3–4 digits. **The model is
gated.**" overstates what happened by a wide margin.

### 1.3 The non-circular check that *was* available and was not made

A bellows factor can be predicted a-priori from geometry: `B = 1 + m/p` with pupil magnification
`p ≈ 1` at `m = 2` gives **B = 3.000**, entirely independently of any spectral measurement. That
predicts a knee at **0.2821 cyc/px** against M5's measured **0.2762** — agreement to **2.1%**.

*That* is a genuine, falsifiable, one-line gate on the optics model, and it passes. The report should
have used it. It is the only reason the verifier is willing to let §4.4 stand at all.

**Corroboration check (fact 24).** The report claims the untuned simulation reproduces fact 24's
−58%/−53% gradient loss for the plain mean, measuring −49% to −51%. Reproduced (−50.2% to −51.7%)
**but mis-based** — see §6.3.

---

## 2. Gate 2 — the estimator algebra: REPRODUCED, one CORRECTION

### 2.1 Analytic proof (stronger than the report's control) (`v2_estimator.py`)

The report confirms the estimator by three numerical routes. The verifier proved it instead.

For `y = h·L + n`, `L ~ CN(0,S)`, `n ~ CN(0,σ²I)`: `w = R_yy⁻¹ r_yL` with
`R_yy = S·hh^H + σ²I`, `r_yL = S·h`. Sherman–Morrison gives
`R_yy⁻¹ h = h / (σ² + S‖h‖²)`, hence

```
w = S·h / (σ² + S‖h‖²) = h / (‖h‖² + σ²/S)      →   L̂ = Σ H_k* Y_k / (Σ|H_k|² + σ²/S)   ∎
MMSE = 1 / (1/S + ‖h‖²/σ²)
```

Checked against brute-force `numpy.linalg.solve` at 200 random `(K, h, S, σ²)` draws: worst relative
error **2.043e-13** (machine precision). This is not a restatement of the author's algebra — it is a
different derivation route (matrix inversion lemma vs. the author's normal-equations solve) validated
against a third (direct inversion). **The rewritten control is sound. CONFIRMED.**

Monte-Carlo triple-route check independently rebuilt with **L-BFGS-B** (a different optimiser family
from the author's Nelder–Mead): A/B and A/C = **1.0000056 – 1.0000157** against the report's
1.0000043 – 1.0000071. Same Monte-Carlo noise floor, different seeds. **REPRODUCED.**

### 2.2 The gain shorthand — REPRODUCED; its explanation is CORRECTED

`√(Σ|H|²)/max|H| = 1.613982` is confirmed, and the verifier can say something the report does not:
this quantity is **exactly** `√(MSE_selection-inverse-filtered / MSE_matched-filter)` in the
`S → ∞` limit. The review's bare `√(Σ|H|²)` = 1.4526 is wrong. **The CORRECTION stands.**

But the report's account of its own 0.9% residual does not:

| Quantity | Report | Verifier |
| --- | --- | --- |
| Measured amplitude gain | 1.6294 | **1.632993** |
| Excess over the shorthand | "0.9%" | **+1.178%** |
| Cause | "the selection baseline was inverse-filtered rather than single-frame Wiener" | **the finite prior `S`** |

Test: rebuild the baseline as a proper single-frame **Wiener** (the report's stated explanation) and
the gain becomes **1.584812**, i.e. **−1.807%** — it overshoots to the *other side* of the shorthand.
That explanation would have to make the residual smaller; it makes it larger and flips its sign.

Drive `S → 10⁶` with the *inverse-filtered* baseline unchanged and the excess falls to **0.0000%**.
The shorthand is the `S → ∞` limit of the exact ratio; the 1.2% is the regularisation term `σ²/S`.

**CORRECTED.** The number is right, the physics attached to it is not. Not decision-changing.

### 2.3 Positive controls

| Control | Report | Verifier | Analytic |
| --- | --- | --- | --- |
| Inverse-filtered selection, MSE ratio | 2.655× | **2.671×** | 2.667× |
| Gain-matched plain mean, MSE ratio | 1.124× | **1.123×** | — |

**REPRODUCED.**

---

## 3. Gate 3, parts 1/2/4/5 — the simulation: REPRODUCED, two CORRECTIONS

Independent reimplementation of the stated forward model (`v4_sim.py`), written from §3's prose, not
from `wiener*.py`.

### 3.1 §5 RMSE table — REPRODUCED digit-for-digit

All 20 cells agree to 4 decimal places (0.0534 / 0.0840 / 0.0403 / 0.0403 … 0.0826 / 0.0848 / 0.1003 /
0.0805). Worst unguarded penalty vs. selection: **31.3%** at σ=0.05 — the report's "up to 31%" is
correct and, if anything, rounded down.

**The strongest single result in the report.** Oracle depth *and* oracle prior — an upper bound on any
implementation — and the unguarded estimator the reviewer proposed as the *core merge* still loses to
argmax selection at every σ ≥ 0.01. **REPRODUCED.**

### 3.2 §7 prior table and the σ≈0.03 crossover — REPRODUCED

| σ | oracle (rep/ver) | est-sel (rep/ver) | est-mf (rep/ver) | power-law (rep/ver) |
| --- | --- | --- | --- | --- |
| 0.010 | 0.865 / **0.865** | 0.859 / **0.859** | 0.871 / **0.871** | 1.069 / **1.069** |
| 0.020 | 0.925 / **0.925** | 0.936 / **0.936** | 0.961 / **0.960** | 1.043 / **1.043** |
| 0.030 | 0.954 / **0.954** | 0.995 / **0.994** | 1.027 / **1.026** | 1.038 / **1.038** |
| 0.050 | 0.978 / **0.978** | 1.042 / **1.040** | 1.053 / **1.051** | 1.042 / **1.042** |

Interpolated implementable crossover **σ = 0.0324** ✓ "σ ≈ 0.03". Power-law > 1.0 at every σ.
**REPRODUCED.** *(The two 0.001–0.002 discrepancies are seed noise.)*

### 3.3 The guard is genuinely different — REPRODUCED; one row CORRECTED

The report discloses that its *first* guard was algebraically identical to the unguarded Wiener. The
replacement `w = Σ|H|²/(Σ|H|² + τσ²/S)` was tested for that failure mode explicitly:

| τ | ‖guarded − unguarded‖ | ‖guarded − selection‖ |
| --- | --- | --- |
| 1e-6 | 4.1e-7 | 0.485 |
| 1e+6 | 0.485 | 1.0e-6 |

It is a genuine one-parameter family interpolating **selection ← → Wiener**, with both endpoints hit.
**Not a null change. REPRODUCED.**

τ sweep, guarded/selection, extended by the verifier past the report's range to τ=48:

| σ | Report | Verifier |
| --- | --- | --- |
| 0.010 | 0.856–0.901 | **0.856–0.901** ✓ |
| 0.030 | *(not quoted)* | **0.938–0.962** |
| 0.050 | "0.938–0.978 for τ ≥ 2" | **0.973–0.985** |

**CORRECTED.** The report's σ=0.05 range is wrong: **0.938 is the σ=0.03 value**, and two rows have
been conflated. The conclusion (wins at every τ ≥ 1, saturates by τ≈3, broad and flat, not fitted) is
unaffected and holds out to τ=48. Not decision-changing, but it is a transcription error in a
published table.

### 3.4 Depth model — CORRECTED

The report: ramp / 5 slabs / single plane "give results within 3% of each other."

| depth model | Wiener/sel σ=0.01 | Wiener/sel σ=0.03 | guarded/sel σ=0.01 | guarded/sel σ=0.03 |
| --- | --- | --- | --- | --- |
| continuous ramp | 1.039 | 1.297 | 0.858 | 0.951 |
| 5 slabs | 1.058 | 1.313 | 0.864 | 0.951 |
| **single plane** | **1.088** | **1.385** | 0.868 | 0.977 |
| **spread** | **4.7%** | **6.8%** | 1.2% | 2.7% |

**CORRECTED.** For selection and the guarded merge, "within 3%" holds (1.2% and 2.7%). For the
**unguarded** Wiener — the quantity the §5 headline is about — the spread is **4.7% at σ=0.01 and
6.8% at σ=0.03**, twice the claimed bound.

The correction runs *in the report's favour*: the single-plane case, which has **no cross-slab
ringing at all**, is the *worst* case for the unguarded Wiener. So the penalty is not an artifact of
depth discontinuities. The report's stated conclusion is right; its stated bound is not.

---

## 4. Gate 3.3 — the real-data measurement: REPRODUCED on 109, REFUTED as a corpus figure

### 4.1 The CFA phase is CORRECT

The task brief flagged this as a possible silent error. It is not one.

```
raw_pattern = [[0, 1],
               [3, 2]]        color_desc = b'RGBG'
```

Index 1 → `color_desc[1]` = **G**. So `raw_image_visible[0::2, 1::2]` selects raw_pattern[0][1] = 1 =
**green**. Correct. The full assignment is R=`[0::2,0::2]`, G1=`[0::2,1::2]`, G2=`[1::2,0::2]`,
B=`[1::2,1::2]`.

Controls run: the **G2** plane gives percentiles agreeing with G1 to 3 decimals and a fraction of
**15.2%** vs 15.1% — if the phase were wrong the "green" plane would be R or B and the two would
diverge sharply. Black level 512 ✓. Visible frame (4688, 7028) → green plane (2344, 3514) ✓.

**REPRODUCED.** No silent error here.

### 4.2 The noise model is independently confirmed

`g = ISO/436.8` DN/e⁻ and `RN = 4.20 e⁻` (below ISO 400; 1.47 e⁻ at/above) reproduce fact 241's
published noise-floor boundaries **2.019 / 2.474 / 6.461 DN** at ISO 50 / 500 / 160 exactly.
**REPRODUCED.**

### 4.3 109MSDCF reproduces digit-for-digit

| percentile | Report | Verifier |
| --- | --- | --- |
| p5 | 0.0890 | **0.0890** |
| p10 | 0.1795 | **0.1795** |
| p25 | 0.7073 | **0.7073** |
| **p50** | **1.1279** | **1.1279** |
| p75 | 1.3330 | **1.3330** |
| p90 | 1.5041 | **1.5041** |

15.1% / 21.2% / median 3.28× past crossover ✓. Robustness sweep **9.7 / 15.1 / 24.4 / 40.5 / 79.6%** ✓
exact at all five multipliers. **REPRODUCED.**

### 4.4 The corpus — where the headline breaks (`v7_corpus.py`)

The report measured one stack and said so (§9, "One subject"). The verifier measured five.

| stack | ISO | marked | frames | p50 σ_rel | **% below crossover** | oracle bound | median/crossover |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **109MSDCF** | 160 | f/11 | 22 | 1.1279 | **15.1%** | 21.2% | 3.28× |
| 119MSDCF | 50 | f/5.6 | 33 | 0.4628 | **30.5%** | 86.9% | 1.35× |
| 112MSDCF | 500 | f/11 | 79 | 0.3950 | **43.7%** | 64.2% | 1.15× |
| 113MSDCF | 500 | f/11 | 63 | 0.2813 | **57.9%** | 72.7% | 0.82× |
| coffee-bean | 50 | f/8 | 105 | 0.0638 | **65.8%** | 87.3% | 0.19× |

**Range 3.5% – 65.8%** at native frame counts (3.5% is 112MSDCF capped to 22 frames); **3.5% – 47.2%**
at a common 22-frame budget. Oracle-bound range **15.2% – 87.3%** against the report's 21.2%.

**The 15.1% figure is REPRODUCED for 109MSDCF and REFUTED as a statement about the rig.** 109MSDCF is
near the *favourable-to-the-report* end of its own corpus. On `113MSDCF` the median pixel is **already
past the crossover in the other direction** (0.82×) and the majority of pixels want deconvolution.

**119MSDCF specifically: 30.5%, double the claimed 15.1%.** Its median pixel is 1.35× past the
crossover, not 3.3×. (Note: `D:\personal\macro\119MSDCF` is a byte-identical mirror per fact 69; the
`C:\dev\macro\test` copy was used. 22-frame-capped it gives 29.1%, so this is not a frame-count effect.)

**Aside — fact 88 does not survive contact with the noise model.** Fact 88 reports 119MSDCF flat-ROI
`single_sigma` of 43.2–53.1 DN vs 109's 27.6–30.0 DN, and the task brief expected 119 to be *noisier*.
It is not. 119 is ISO 50 (`g` = 0.1145) with local means ≤ 4585 DN, so the project's own photon-transfer
model caps its temporal σ at **22.9 DN**. 109 at ISO 160 matches its model almost exactly (27.6–30.0
measured vs 29.7 predicted). Fact 88's 119 figures are therefore almost certainly **spatial** standard
deviations containing subject structure, not temporal noise — rule-10 territory. 119 has *better* local
SNR than 109, which is why more of its pixels want deconvolution. **Proposed fact 138 flags this.**

### 4.5 The statistic is frame-count biased, and that is not disclosed (`v9_framecount.py`)

"For each pixel, its **best** frame in the stack" = argmin over frames of a *noisy* σ_rel estimate.
`min` over `K` noisy draws falls with `K`. The verifier separated the two mechanisms by re-selecting
the best frame with a **decoupled 27-px sharpness score** (not the quantity being minimised):

| stack | K | selector | % below crossover |
| --- | --- | --- | --- |
| 109MSDCF | 22 | argmin-σ_rel (report's) | **15.1%** |
| 109MSDCF | 22 | decoupled sharpness | **12.7%** |
| 113MSDCF | 22 | argmin-σ_rel | 15.9% |
| 113MSDCF | 63 | argmin-σ_rel | 57.9% |
| 113MSDCF | 22 | decoupled sharpness | 13.0% |
| 113MSDCF | 63 | decoupled sharpness | **47.8%** |
| coffee-bean | 22 | decoupled sharpness | 44.4% |
| coffee-bean | 105 | decoupled sharpness | **65.4%** |

Two findings:

1. **Selection bias inflates the report's number**, by ~2.4 points at 109/22 (15.1% → 12.7%) and
   ~10 points at 113/63. The bias runs **in the report's disfavour**, i.e. the true fraction wanting
   deconvolution on 109 is *lower* than published. This **strengthens** the refutation.
2. **The frame-count dependence is real and physical**, not just bias: with the decoupled selector
   113 still goes 13.0% → 47.8% from 22 to 63 frames. Denser focus sampling genuinely gives each pixel
   a sharper best frame. **The report's headline is a function of how many frames you shoot and never
   says so.**

### 4.6 The 0.3440 mapping — the report is right that it is the softest number, and it is soft in a way the report did not identify

The report describes 0.3440 as a 1-D→2-D window conversion. It is not; it is a *ratio*, and the
verifier reverse-engineered it exactly:

```
0.3440 = 0.03 / 0.0872
```

where **0.0872 is the median local standard deviation (W=9) of the simulation's noise-free LATENT**
(exact match to 4 dp; this constant appears in no committed script). So the recipe pairs an
**unblurred, noise-free** contrast in the numerator's denominator against a **blurred,
noise-subtracted, observed** contrast on the real-data side. Those are not the same quantity. Using
the *observed in-focus frame* instead — the like-for-like object — gives `0.03/0.0642` = **0.467**.

Three checks the report should have made:

1. **Is the invariant even the right one?** Yes. The forward model is linear and the estimator
   scale-covariant: scaling the plant amplitude by ×1 / ×3 / ×0.3 with σ scaled to match leaves
   gua/sel at 0.9945 and the median σ_rel at 0.3707 **identically**. `σ_local/signal_local` is the
   correct invariant. **CONFIRMED — the mapping is defensible in kind.**
2. **Does the window scale matter?** Yes, mildly. Measured on the CFA green grid (W=9 CFA px = 18
   sensor px), σ_rel is **0.83–0.86×** its sensor-grid value. The report calibrated at one scale and
   applied at another.
3. **What is the crossover if you just measure it directly?** The verifier did what the report did
   not: bin simulation pixels by *their own* local σ_rel and find where guarded stops beating
   selection (`v8_calib.py`).

| prior | sensor grid | **CFA grid (matched)** | report |
| --- | --- | --- | --- |
| est-sel (implementable) | 0.4341 | **0.2996** | 0.3440 |
| oracle | 0.7328 | **0.6703** | 0.5734 |

**Verifier's best estimate: crossover = 0.30 (implementable), 0.67 (oracle), each ±~0.15
(≈ ±1 bin of the calibration).** The report's implementable value is ~15% too high; its oracle value
~17% too low. Both sit comfortably inside the report's own 2× robustness envelope, and applying the
verifier's values to 109MSDCF gives **13.9%** (vs. the report's 15.1%) and **23.9%** (vs. 21.2%).

**Verdict on 0.3440: CORRECTED, but not decision-changing for 109MSDCF.** It is soft — but its
softness is ±15%, not the ×2 the report worried about, and the *real* fragility is elsewhere (§4.4).

---

## 5. Gate 4 — the aperture result: REPRODUCED at the stated parameters, CORRECTED as advice

This is the claim being turned into shooting advice, so it got the most adversarial treatment.

### 5.1 The invariance argument — verified, but it is definitional, not optical (`v3_aperture.py`)

Claim: blur-per-step in pixels is aperture-invariant because step ∝ DOF ∝ `N_eff` while CoC growth
∝ 1/`N_eff`.

From CoC geometry at magnification `m`, an object-space defocus `δ` gives blur
`c = m²·δ / N_eff`. Fixing a capture policy of "step by a constant CoC increment `C`" gives
`δ(c=C) = C·N_eff/m² ∝ N_eff` — so `step_µm ∝ N_eff` **exactly** and CoC-per-step is constant.
Verified numerically to machine precision.

But note what this is: **if you step by a fixed CoC increment, CoC-per-step is constant by
construction.** It is a restatement of the capture policy, not an independent property of the optics.
The real physical content is the corollary the report also states: **frames ∝ 1/`N_eff`** for fixed
subject depth. That is correct and it is the load-bearing part. **REPRODUCED — with the caveat that
the report presents a definition as a discovered invariance.**

### 5.2 The budget tables

| quantity | Report | Verifier |
| --- | --- | --- |
| MTF@0.25 c/px, f/4 | 0.5977 | **0.5969** |
| f/5.6 | 0.4467 | **0.4457** |
| f/8 | 0.2416 | **0.2404** |
| f/11 | 0.0463 | **0.0453** |
| f/16 | 0.0000 | **0.0000** |
| σ/frame, fixed total time | 0.603 / 0.714 / 0.853 / 1.000 / 1.206 | **identical** |
| **contrast ratio f/11→f/5.6** | **9.6×** | **9.84×** |
| **SNR ratio, fixed time** | **13.5×** | **13.80×** |
| **SNR ratio, fixed light** | **6.9×** | **7.03×** |
| frame-count ratio | 2× | **1.98×** |
| matched-filter factor | (implicit) | **2.078, identical at every aperture** |

**REPRODUCED** (sub-1% differences are rounding of `N_eff` and of the frame count).

**Two extra controls the report does not have** (`v10_aperture_robust.py`):

- **The result does not depend on the focus-step choice.** The matched-filter factor
  `√(Σ|H|²)/max|H|` at 0.25 cyc/px is 4.14 / 2.94 / 2.08 / 1.47 / 1.04 at steps of 0.25 / 0.5 / 1 /
  2 / 4 px, and is stable in `K` once `K·step` covers the slab. Because it is aperture-invariant it
  **cancels exactly** in the f/5.6 : f/11 ratio. The 13.8× therefore survives any step policy; only
  the absolute 2.08 depends on it.
- **The "best frame" column is an optimistic bound.** The table assumes the best frame is at exactly
  zero defocus. The typical pixel sits up to half a step away, costing an extra MTF factor of 0.981
  at a 1 px step (0.925 at 2 px). Aperture-invariant, so it cancels in the ratio, but the absolute
  MTF column is a ceiling, not a typical value.

### 5.3 Is "fixed total time" smuggling photons? — No

It is, and the report handles it. Fixed total time does give f/5.6 **3.9×** more light than f/11
(2× the frames × 1.96× the aperture area). The fixed-*light* budget removes exactly that, and the
win is still **7.03×**. The verifier added a third budget the report does not have — **fixed
per-frame exposure** (the naïve field practice: same shutter speed, just more frames) — and the
ratio there is **19.3×**. All three budgets agree on the sign and the order of magnitude, and the
report's chosen pair brackets the practical case. **No smuggling. REPRODUCED.**

One thing the report does not say: the fixed-*light* budget implies a **3.9× shorter total
exposure** at f/5.6, which is a strange thing to hold fixed in practice. The honest practical budget
is fixed total time (13.8×); the honest optics-only number is the contrast ratio (9.8×).

### 5.4 CORRECTED — the ratio is not a point estimate, and its instability is not disclosed

The 9.6× is quoted with no uncertainty. It has a great deal.

**Sensitivity to B** (`v3_aperture.py`):

| B | contrast ratio | SNR ratio (fixed time) |
| --- | --- | --- |
| 2.41 (M5 lower bracket) | **3.09×** | 4.34× |
| 2.60 | 3.98× | 5.59× |
| 2.90 | 7.27× | 10.21× |
| 3.00 (report) | **9.84×** | 13.80× |
| 3.064 (M5 point) | **12.58×** | 17.64× |

**Sensitivity to λ** (`v10_aperture_robust.py`), which the report never sweeps although M5 explicitly
flags λ-sensitivity for the neighbouring critical-sampling number:

| λ | MTF f/11 | MTF f/5.6 | contrast ratio |
| --- | --- | --- | --- |
| 450 nm | 0.1657 | 0.5409 | **3.26×** |
| 550 nm | 0.0453 | 0.4457 | **9.84×** |
| 600 nm | 0.0072 | 0.3996 | **55.3×** |
| 650 nm | 0.0000 | 0.3548 | **∞** |

**The ratio is unstable because its denominator is near zero.** At B=3, f/11's cutoff is 0.2821 cyc/px,
barely above the 0.25 cyc/px evaluation point, so the denominator sits on the near-vertical tail of the
MTF curve. Any quantity of that shape should not be published as "9.6×".

**The robust way to say the same thing — and the verifier endorses this version:**

> At 4-px detail (0.25 cyc/px), marked f/11 at m=2 delivers a modulation of **0.00–0.17** depending on
> wavelength — for green light, effectively nothing. Marked f/5.6 delivers **0.35–0.54** across the
> whole visible band. The change is from *no usable contrast* to *usable contrast*, at the cost of
> ~2× the frames.

That statement is true at every B in [2.4, 3.1] and every λ in [450, 650] nm. **The advice survives;
the multiplier does not.**

### 5.5 An unflagged extrapolation, and a provenance issue

- **The model is diffraction-only.** There is no aberration term. Real lenses are aberration-limited at
  wide apertures and diffraction-limited stopped down, so a diffraction-only model is *systematically
  optimistic about f/5.6* — exactly the aperture the advice recommends moving to. §9 does not list this.
- **f/5.6 is outside the calibrated range.** M5's own "do not quote" list states that any claim its
  f/5.6 exposure *measured* something is not quotable: M5's measured f/5.6 knee is **0.2431**, *below*
  f/11's 0.2762, i.e. texture-limited rather than a cutoff. So the recommendation is a two-stop
  extrapolation from the single aperture where the model was calibrated, using a model with no
  aberration term. **This is the single largest unflagged risk in the document.**
- **M5 §9.1/§9.2 already published the substance.** M5 has MTF_d 0.446 vs 0.045 and "collapses by 10×".
  §4.4 is best described as *confirming and budgeting* M5's finding, not as new. More seriously, M5
  **explicitly declined** to publish the DOF/frame-count relationship, writing that "publishing an
  unverified DoF formula is exactly the failure mode this project has already had to retract once."
  M20 supplies exactly that relationship as DERIVED, without re-opening M5's objection or noting that
  it is doing so.
- M5's "do not quote" list also bans a two-sided point estimate of B; the defensible form is
  **"B ≈ 3, bracketed [2.4, 3.1]"**. §4.4's tables use B = 3.0 with no bracket.

**Verdict: REPRODUCED at the stated parameters. CORRECTED as advice.** Shoot wider — the direction is
robust and worth acting on. Do not plan around "9.6×".

---

## 6. Gate 5 — the metric claim: REPRODUCED

This is load-bearing for M18, so it was re-derived independently (`v4_sim.py`).

### 6.1 The σ=0.010 comparison

| quantity | Report | Verifier |
| --- | --- | --- |
| mean\|∇\|, selection | 0.0296 | **0.0295** |
| mean\|∇\|, Wiener | 0.0367 | **0.0365** |
| **magnitude difference** | **+24%** | **+23.7%** |
| ∇-correlation, selection | 0.8595 | **0.8578** |
| ∇-correlation, Wiener | 0.7538 | **0.7538** |
| **correlation difference** | **−12%** | **−12.1%** |

**REPRODUCED.**

*One column drifts.* The selection gradient-correlation at high σ differs by more than seed noise
elsewhere: report 0.7340 / 0.5592 at σ=0.030 / 0.050 against the verifier's **0.7266 / 0.5446**
(−1.0% / −2.6%). The direction and the crossing point are unaffected (at σ=0.050 the Wiener's
correlation overtakes selection's in both: 0.6629 vs 0.5592 in the report, 0.6631 vs 0.5446 here),
so this changes nothing, but it is the largest unexplained divergence between the two
implementations in the whole simulation.

### 6.2 The σ=0.050 inversion

Ground-truth latent mean|∇| = 0.0392 (verifier: **0.0392**). Argmax selection at σ=0.05 reads
mean|∇| = **0.0454** (report 0.0455) — **above the ground truth.** Noise inflates the metric past the
true value. **REPRODUCED.**

**The conclusion dispatched to M18 is correct and should stand: mean|∇| is valid only as a one-sided
test against collapse; a gradient *increase* is a flag to investigate, never a pass.** The verifier
found no way to break this. It is the second-strongest result in the document.

### 6.3 The fact-24 corroboration — CORRECTED

The report: "the plain mean loses **49–51%** of its gradient on this plant, against fact 24's measured
**−58% / −53%**… Same sign, same magnitude, from a model built for a different purpose."

The simulation number is reproduced (**−50.2% to −51.7%**) but it is measured against the **noise-free
latent**. Fact 24's numbers are measured against **a single observed frame** (11.89 → 5.02 = −58%;
18.58 → 8.81 = −53%). Those are different baselines.

Re-based like-for-like — plain mean against a single observed frame, in the simulation:

| σ | mean vs. single observed frame |
| --- | --- |
| 0.002 | **−12.9%** |
| 0.010 | −15.1% |
| 0.020 | −21.6% |
| 0.030 | −30.0% |
| 0.050 | **−45.2%** |

**CORRECTED.** Same sign; magnitude 13–45% against fact 24's 53–58%, not "same magnitude". And the
agreement improves as σ rises — which is *because of* §6's own finding that noise inflates a single
frame's mean|∇|. The corroboration is real but weaker than claimed, and it is partly circular with
§6. Not decision-changing.

---

## 7. Does the headline survive?

**Yes. The verdict "deconvolution stays opt-in post-merge, not the core merge" SURVIVES.** Four
independent legs, all of which the verifier tried and failed to break:

1. **§4.3 — the hard-zero argument.** If `H_k(f) = 0` ∀k then `L̂(f) = 0` exactly. This is not
   statistical; it is arithmetic, and it is not circular in the way §3's table is. At this rig's
   habitual f/8–f/11 it holds at Nyquist. Unbreakable.
2. **§5 — the unguarded estimator loses to argmax selection** at σ ≥ 0.01 *with oracle depth and
   oracle prior*, by up to 31.3%. Reproduced exactly. An upper bound that loses to the trivial
   baseline is a strong result.
3. **§7 — the parametric power-law prior loses at every σ.** Reproduced exactly. The reviewer's
   estimator is not shippable in the form proposed.
4. **§6 — the claimed prize is not there.** The ∇-correlation gain is ≈0; the entire measured benefit
   is RMSE, i.e. noise. Reproduced.

**Two arguments make the refutation *stronger* than the report claims:**

- **The argmax-selection baseline strengthens it, decisively.** The report flags this (§8.7) and is
  right. Argmax selection is the weakest possible merge — no regularisation, no noise gating, no
  sub-pixel handling. The proposed *core merge* losing to it is a much harder failure than losing to
  the project's actual planned merge would be. Every margin here is generous to deconvolution, so
  against M18's regularised noise-gated merge the true fraction of pixels wanting deconvolution is
  **below** the numbers published, on every stack.
- **The selection-bias correction (§4.5) also runs in the report's favour**: 109's true fraction is
  ~12.7%, not 15.1%.

**But the margin is REFUTED as stated.** "15.1% of pixels" is a property of one capture, not of the
rig. Across five stacks it is **3.5% – 65.8%**, and on two stacks (`113MSDCF`, `coffee-bean`) the
*majority* of pixels sit below the crossover. On `113MSDCF` the median pixel is on the wrong side of
it (0.82×). The report's "median pixel is 3.3× past" is true for 109MSDCF and false for most of the
corpus.

Three things make the margin narrower than the report implies:

- **Frame count.** More frames ⇒ sharper best frame ⇒ more pixels want deconvolution. 113 goes
  13% → 48% from 22 to 63 frames. Deep stacks are exactly where a focus-stacking project ends up.
- **Aperture.** §4.4's own advice — shoot wider — *raises* local SNR and therefore *raises* the
  deconvolution-wins fraction. 119MSDCF at f/5.6 is at 30.5%. **§4.4 and §7 point in opposite
  directions and the report does not notice.** If the owner takes the aperture advice, the
  deconvolution case gets stronger, not weaker.
- **The guard's win is partly structural.** `w = Σ|H|²/(Σ|H|² + τσ²/S)` blends *toward the selected
  frame*, so "guarded Wiener" is literally "selection, plus a deconvolution correction where SNR
  permits". It is bounded below by selection by construction at large τ. This does not invalidate
  anything — it *reinforces* the architectural conclusion, which is precisely that the shippable
  object is selection-with-a-correction rather than deconvolution-as-merge.

**Net:** the plan change the report recommends (`B-algorithms-sota.md` §7.5 unchanged; guarded;
locally gated; data-estimated prior) is correct and the verifier endorses it. The *quantitative*
claim "it wins on 15% of pixels" should be restated as **"on this corpus, between ~4% and ~66% of
pixels depending on subject, aperture and stack depth — with 109MSDCF, a shallow f/11 stack, at the
low end."** The gating recommendation is unaffected: a *local* gate is the right answer at 4% and
still the right answer at 66%.

---

## 8. What the report should have measured and did not

1. **A non-circular gate on the optics model.** The a-priori `B = 1 + m/p = 3.0` prediction (2.1%
   agreement with M5's measured knee) was available, costs one line, and is the only genuine check in
   the vicinity. §3's table cannot fail.
2. **More than one stack.** §9 lists "one subject" as a limitation, but the headline number is quoted
   without a range in §2, §7 and §8. Four more stacks were on disk and the measurement is ~40 s each.
3. **Frame-count control.** The central statistic is an argmin over frames and is monotone in `K`.
   Never mentioned.
4. **The crossover measured directly rather than converted.** Binning simulation pixels by their own
   σ_rel takes one extra loop and removes the report's self-identified weakest link entirely.
5. **A sensitivity band on `B` and `λ` for §4.4.** The 9.6× spans 3.1×–12.6× over B's own published
   bracket and 3.3×–∞ over the visible band. Published as a point estimate.
6. **An aberration term, or an explicit flag that there isn't one.** §4.4 recommends moving *two stops
   wider than the only aperture the model was calibrated at*, using a diffraction-only model that is
   systematically optimistic in exactly that direction.
7. **The interaction between §4.4 and §7.** They give opposite advice about how much deconvolution
   matters and the document treats them as independent ("§4.4 … does not depend on deconvolution at
   all"). It does — through local SNR.
8. **Unbiased local variance.** The `uniform_filter` estimator is the population variance, biased low
   by `(n−1)/n`: −1.2% on the real 2-D W=9 window (n=81) but **−11%** on the 1-D W=9 simulation window
   (n=9). Calibrating on one and applying to the other injects a systematic offset. Immaterial for
   109 (15.15% → 15.21%) but it should have been checked, not assumed.
9. **A 2-D control.** §9 argues 2-D "likely makes deconvolution look worse". Plausible, and the
   verifier agrees on the direction — but it is the one place the report reasons instead of measuring
   while the measurement was cheap.

---

## 9. Proposed facts

Numbered from 130 per the verification brief. **Proposed, not yet in SYNTHESIS.md** — the verifier does
not own that file.

> **FOLD NOTE (added by the orchestrator, not the verifier).** These landed in SYNTHESIS as
> **facts 122-139**, a uniform shift of **−8**. The brief's "number from 130" collided with M20's
> own facts 140-145, which were already published; the verifier had no way to know that and the
> error is the orchestrator's. Read `130→122 … 147→139`. Two cross-milestone disciplines
> (**250, 251**) were also derived from this report together with M39 and are numbered outside
> the block, because neither milestone owns them alone.

| # | Fact | Provenance |
| --- | --- | --- |
| 130 | M20's §3 optics "gate" is a tautology: `B` = 3.064 was itself obtained by inverting `f_c = pitch/(λN)` on the same measured knee the gate re-derives. The table cannot fail. | VERIFIED (v1_optics.py); M5 line 26 |
| 131 | The a-priori bellows factor `B = 1 + m/p = 3.000` predicts a knee at 0.2821 cyc/px against M5's measured 0.2762 — **2.1% agreement**. This is a genuine, non-circular gate on the optics model, and it passes. | VERIFIED (v1_optics.py) |
| 132 | `L̂ = ΣH*Y/(Σ\|H\|²+σ²/S)` is the MMSE linear estimator — proved analytically via Sherman–Morrison, worst relative error 2.043e-13 against brute-force inversion over 200 random cases. MMSE = `1/(1/S + ‖h‖²/σ²)`. | VERIFIED (v2_estimator.py) |
| 133 | The matched-filter gain over inverse-filtered selection exceeds `√(Σ\|H\|²)/max\|H\|` by **+1.18%**, and the cause is the finite prior `S` (the excess → 0.0000% as S→∞), **not** the choice of selection baseline as M20 §4.2 states. | CORRECTED (v2_estimator.py) |
| 134 | On `109MSDCF` the fraction of pixels below M20's deconvolution crossover is **15.1%** with the report's argmin-σ_rel selector and **12.7%** with a decoupled sharpness selector; the argmin statistic is biased in favour of deconvolution. | VERIFIED/CORRECTED (v5, v9) |
| 135 | The "% of pixels wanting deconvolution" ranges **3.5%–65.8%** across the five-stack corpus (109/119/112/113/coffee-bean). It is not a property of the rig. `109MSDCF` sits at the low end. | REFUTES M20's point estimate (v7_corpus.py) |
| 136 | The statistic is **monotone in frame count**: `113MSDCF` goes 13.0% → 47.8% from 22 to 63 frames with a bias-free selector. Denser focus sampling raises the deconvolution-wins fraction. | VERIFIED (v9_framecount.py) |
| 137 | M20's crossover constant 0.3440 is `0.03 / 0.0872` where 0.0872 is the median local σ of the **noise-free latent** — a units mismatch against the real data's blurred, noise-subtracted observed contrast. Direct calibration at matched CFA scale gives **0.2996** (implementable) and **0.6703** (oracle). | CORRECTED (v6, v8) |
| 138 | Fact 88's `119MSDCF` flat-ROI σ of 43.2–53.1 DN is inconsistent with the project's own photon-transfer model, which caps 119's temporal σ at 22.9 DN at ISO 50. Those figures are almost certainly spatial σ containing subject structure. **119 is less relatively noisy than 109, not more.** | REFUTES fact 88 (v5_realdata.py) |
| 139 | `σ_local/signal_local` is the correct scale-invariant for the sim→real mapping: scaling plant amplitude ×3 / ×0.3 with σ matched leaves gua/sel at 0.9945 and median σ_rel at 0.3707 identically. | VERIFIED (v6_mapping.py) |
| 140 | The `f/11 → f/5.6` contrast ratio at 0.25 cyc/px is **9.6×–9.8× only at B=3.0 and λ=550 nm**. It spans **3.09×–12.58×** over B's published bracket [2.41, 3.064] and **3.26×–∞** over 450–650 nm, because f/11's cutoff (0.2821 cyc/px at B=3) sits just above the evaluation point. | CORRECTED (v3, v10) |
| 141 | The robust form of the aperture result: at 4-px detail, marked f/11 at m=2 gives modulation **0.00–0.17** across the visible band; marked f/5.6 gives **0.35–0.54**. True at every B in [2.4, 3.1] and every λ in [450, 650] nm. | VERIFIED (v10_aperture_robust.py) |
| 142 | M20 §4.4's blur-per-step invariance is definitional, not optical: `c = m²δ/N_eff` means a fixed-CoC-increment capture policy has constant CoC/step **by construction**. The physical content is `frames ∝ 1/N_eff`. | CORRECTED (v3_aperture.py) |
| 143 | The `109MSDCF` CFA green-plane extraction `raw_image_visible[0::2, 1::2]` is **correct** for `raw_pattern [[0,1],[3,2]]` / `RGBG`; the G2 plane `[1::2,0::2]` agrees to 3 decimals (15.2% vs 15.1%). | VERIFIED (v5_realdata.py) |
| 144 | mean\|∇\| is one-sided: at σ=0.010 the unguarded Wiener has **+23.7%** gradient magnitude and **−12.1%** gradient correlation with truth; at σ=0.050 argmax selection reads mean\|∇\| = 0.0454 **above** the latent's 0.0392. | VERIFIED (v4_sim.py) — independently confirms M20 §6 for M18 |
| 145 | The unguarded Wiener's penalty vs. selection is **worst under a single-plane depth model** (1.088× RMSE) and *mildest* under a continuous ramp (1.039×). Cross-slab ringing does not drive M20's refutation; removing it makes the Wiener look worse. | CORRECTED (v4_sim.py) — M20 claims "within 3%"; actual spread 6.2% |
| 146 | M20 §4.4 (shoot wider) and §7 (few pixels want deconvolution) point in **opposite** directions: wider apertures raise local SNR and therefore raise the deconvolution-wins fraction (119MSDCF at f/5.6 → 30.5%). M20 treats them as independent. | VERIFIED (v7_corpus.py) |
| 147 | M20's aperture recommendation is a **two-stop extrapolation from the only calibrated aperture** using a diffraction-only model with no aberration term — systematically optimistic about f/5.6. M5's own f/5.6 knee (0.2431) is texture-limited and not quotable as a cutoff. | UNFLAGGED RISK (v3_aperture.py; M5 §11) |

---

## 10. Verifier's code

`experiments/m20-deconvolution-ceiling/verify/` — written independently from the report's prose; the
author's `src/` scripts were read but never executed.

| script | covers |
| --- | --- |
| `v1_optics.py` | Gate 1; formula cross-validation vs pupil autocorrelation and numerical LSF; circularity audit; B sweep |
| `v2_estimator.py` | Gate 2; Sherman–Morrison proof; three-route MC with L-BFGS-B; gain decomposition; S→∞ |
| `v3_aperture.py` | Gate 4; CoC invariance; three photon budgets; B sensitivity |
| `v4_sim.py` | Gates 3.1/3.4/3.5 and Gate 5; independent forward model; guard-identity test; depth controls; fact-24 re-basing |
| `v5_realdata.py` | Gate 3.3; CFA phase audit; G1/G2 control; unbiased-variance control; 109 + 119 |
| `v6_mapping.py` | §7 priors; reverse-engineering of 0.0872; scale-invariance; window-scale error |
| `v7_corpus.py` | five-stack sweep with 22-frame cap |
| `v8_calib.py` | direct per-pixel crossover calibration at matched CFA scale |
| `v9_framecount.py` | frame-count bias control with a decoupled sharpness selector |
| `v10_aperture_robust.py` | λ sweep, focus-step sweep, half-step best-frame penalty |
