# M97r — a per-tile outlier mask that survives a focus stack

Commit `8be4b38`. Module `crates/strehl-core/src/outlier.rs`, registered in
`crates/strehl-core/src/lib.rs`, priced by
`crates/strehl-cli/examples/m97-outlier.rs`.

**Nothing is wired into the merge.** This milestone builds and prices the
instrument; it does not ship a behaviour change. See §6.

---

## 1. The gap, and why the standard answer does not survive contact with it

One twitching antenna poisons both the reference and the average, and there is
no defence at all today. The reference shape is Wronski et al., *Handheld
Multi-Frame Super-Resolution* (HDR+), Eq. 5–9: per-tile disagreement against a
reference, normalised by predicted noise. This project is unusually well
equipped for the second half — `NoiseModel` is a calibrated, type-enforced
`σ²(S) = gS + (RN·g)²`, which turns "disagrees by more than noise explains" from
a magic threshold into a measurable statement.

**But HDR+ assumes every frame is the same scene at the same focus, and a focus
stack is the one case where that is false by construction.** Every frame
legitimately disagrees with the reference wherever it is differently focused,
and that disagreement *is the signal the stack exists to harvest*. A naive port
fires hardest exactly where the merge is doing its job.

That is not a hypothetical. It is fact **W1** below.

---

## 2. Method

Four arms, three synthetic scenes, one instrument. The scene is a disc plus a
two-axis ripple, so every tile carries gradient in both directions.

| case | construction | what it must do |
| --- | --- | --- |
| `static` | same scene, same focus, independent noise | **PLACEBO** — every arm inert |
| `defocus` | same scene, **different focus** | **TRAP** — no arm may fire |
| `motion` | same focus, translated 1.0 px | **PLANT** — must fire |
| `faint` | contrast comparable to noise, static | **NOISE PLANT** — must not fire |

The `defocus` and `motion` rows together are the whole measurement. An arm is
useful only if it separates them, and a `defocus` null means nothing unless some
other arm demonstrably finds something in the same input.

Statistic for the disagreement arms is the **reduced chi-square** of the
difference, `(1/N)·Σ (a−b)²/(var_a+var_b)`. Under the null `Var(a−b) =
var_a+var_b` exactly, so `E[χ²] = 1` regardless of signal level, tile size,
exposure or scene. The unit is "times the noise the model predicts", never DN.

---

## 3. Results

64 tiles of 32 px on a 256×256 plane, `k = 6`, `σ = 4 DN`. `chi2only` gates on
significance alone; `gated` is the shipping conjunction of §5.

| case | arm | chi2only | gated | mean χ² | mean \|s\| px | max \|s\| px |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| static | Raw | 0.0% | — | 1.00 | — | — |
| static | LowFreq | 0.0% | — | 1.04 | — | — |
| static | Shift | 0.0% | 0.0% | 0.92 | 0.0059 | 0.0156 |
| static | **ShiftFree** | 0.0% | **0.0%** | 0.92 | 0.0059 | 0.0156 |
| defocus | Raw | **100.0%** | — | 85.31 | — | — |
| defocus | LowFreq | **100.0%** | — | 972.98 | — | — |
| defocus | Shift | 60.9% | 0.0% | 59.17 | 0.0640 | 0.1751 |
| defocus | **ShiftFree** | 34.4% | **0.0%** | 10.38 | 0.0268 | 0.1027 |
| motion | Raw | 100.0% | — | 91.80 | — | — |
| motion | LowFreq | 100.0% | — | 1861.56 | — | — |
| motion | **ShiftFree** | 100.0% | **100.0%** | 30886.02 | 1.0005 | 1.0258 |
| faint | **ShiftFree** | 6.2% | **0.0%** | 4.19 | 0.7637 | 1.8837 |

---

## 4. Facts

**W1 — MEASURED. The naive HDR+ port is not a detector on a focus stack.**
`Raw` fires on **100.0%** of tiles of a stationary, differently-focused scene,
and separates defocus from motion by a factor of **1.08** (mean χ² 85.31 vs
91.80). Nothing useful can be built on that ratio.

**W2 — MEASURED. Low-pass filtering, the obvious remedy, makes it worse.**
Defocus is approximately a low-pass, so filtering both sides "should" make a
differently-focused frame agree. `LowFreq` instead fires on **100.0%** of the
trap at mean χ² **972.98**, an order of magnitude *above* `Raw`'s 85.31.

**W3 — DERIVED, and it explains W2.** Filtering shrinks the defocus residual but
shrinks the noise faster, and the statistic is their ratio. For a step edge, the
residual between focus levels differing by `r_d` has amplitude of order
`C·r_d/R` after filtering at radius `R`, while the filtered noise is of order
`σ/R`. The ratio is `C·r_d/σ`, **independent of `R`**. Filtering cannot buy
defocus-blindness because it rescales signal and noise together. Motion behaves
identically, so the arm separates nothing.

**W4 — ARGUED, and it is the design pivot.** Stop measuring *disagreement* and
measure *displacement*, because displacement is the thing defocus does not have.
Estimate the local Lucas-Kanade shift and test its significance.

**W5 — MEASURED. The unconditional displacement arm is also fooled, on 60.9% of
the trap.** The symmetry argument holds for a straight edge and fails for a
curved one: in edge-normal coordinates `∇²s = ∂²s/∂n² + κ·∂s/∂n`, and the
curvature term is **collinear with the gradient**. A disc shrinks under blur.
Blurring a curved feature genuinely displaces it. This is real image formation,
not an artefact.

**W6 — MEASURED. Entering the Laplacian as an explicit nuisance parameter and
projecting it out via its Schur complement cuts the trap response 5.7×** (mean
χ² 59.17 → 10.38, mean |s| 0.0640 → 0.0268 px) **at 0.1% cost to motion
sensitivity** (30920 → 30886, within noise). Any residual lying in the defocus
direction is absorbed by the third parameter and cannot inflate the displacement
statistic. This is blindness by construction, not by tuning.

**W7 — MEASURED, then DERIVED and corrected. The gradients are measured from
noisy samples, so the information matrix is biased upward by the noise's own
variance.** `E[g²_meas] = g²_true + Var(g_noise)`. On a low-contrast tile the
noise term (`0.5·var_b = 8`) exceeded the true gradient energy (0.165) by **48×**
— the matrix was almost entirely noise. Symptom: the statistic read **0.50**
where the null is 1.00, because the inflated matrix shrank the estimate toward
zero. This is regression dilution, and it also made the abstention guard measure
noise instead of signal.

The four bias terms are derivable from the noise model, which is precisely why
having one calibrated is worth the trouble:

| term | bias | reason |
| --- | --- | --- |
| `gxx`, `gyy` | `0.5·var_b` | `Var(½(n₊₁ − n₋₁))` |
| `gll` | `20·var_b` | `Var(n₊₁+n₋₁+n₊w+n₋w − 4n₀)` |
| `gxy`, `gxl`, `gyl` | `0` | disjoint samples; the ±1 terms cancel |
| Laplacian rhs | `4·var_b` | `Cov(lap, a−b)`; both touch `n₀` |

**Subtracting them moved the planted 1.0 px translation from 0.9934 px to
1.0000 px.** That the correction lands on the known ground truth to four decimals
is the evidence it is the right correction and not merely a helpful one.

**W8 — MEASURED. Significance alone cannot be the discriminant, because it is
too sensitive.** A **0.027 px** defocus bias is 10σ significant when the noise is
4 DN and the gradients are large, so `ShiftFree` still fires on 34.4% of the trap
on significance alone. The separation lives in the **magnitude**: 0.0268 px
(defocus, worst tile 0.1027) against 1.0005 px (motion) — a **37×** mean
separation and **9.7×** between the worst trap tile and the mean plant tile.

**W9 — MEASURED. A pixel bar is dimensionally legitimate where a DN bar is
not.** Motion is a geometric quantity and pixels are its natural unit; the bar
does not move when exposure, gain or scene brightness does. This is the
distinction that separates it from the absolute DN tolerance behind the
waxy-blob artefact (fact 1470).

**W10 — MEASURED. Each of the three gates stops something the others let
through.** On the `faint` plant, **18 of 20** informative tiles clear the
magnitude bar on noise alone, reaching **2.15 px** — six times the bar. The
significance gate vetoes 14; the resolution requirement takes the remaining 4 to
**zero**, while leaving the motion plant at 100%.

**W11 — MEASURED. The abstention guard, once debiased, correctly refuses
low-information tiles.** On `faint`, **44 of 64** tiles abstain. An abstaining
tile never fires: no information is not the same as agreement.

**W12 — MEASURED. The null is byte-identical, and by construction rather than by
luck.** `git grep outlier HEAD -- crates/` returns exactly one reference outside
the module and its harness: `lib.rs:23  pub mod outlier;`. Every other hit is
`align.rs`'s pre-existing MAD pass or a comment. Byte-freeze **5/5**, both rows
HOLD at `D99F5D82337AA2F093202D12677FBD1DE6D78A94761C0DE250020085271C76CA` and
`119936E656CD4E844F8345F23D8196B6B282C883C4B828318BADC6E222BAD709` — unchanged
from before this milestone.

**W13 — MEASURED. Final configuration.** `ShiftFree` with the conjunction gate:
placebo **0.0%**, trap **0.0%**, plant **100.0%**, noise-plant **0.0%**.

---

## 5. The gate that ships

Three conditions, conjunctive. Each was added because a measurement showed the
others let something through:

1. `sigma_px · 3.0 ≤ min_shift_px` — the tile must be able to **resolve** the
   bar it is judged against. Stops imprecise tiles being evidence either way.
2. `chi2 > 1 + k` — stops **noise** inventing a displacement (W10).
3. `|s| > min_shift_px` — stops **defocus curvature** (W5, W8).

`DEFAULT_MIN_SHIFT_PX = 0.35`, sitting 3.4× above the worst measured defocus tile
(0.1027 px) and 2.9× below typical motion (1.0005 px), near the geometric mean.
`RESOLUTION_MARGIN = 3.0`.

---

## 6. What this milestone does NOT claim

**The gate configuration is in-sample.** The design changed four times in
response to measurement — `LowFreq` → `Shift` → `ShiftFree` → debias →
resolution gate — and the 0.35 px bar and the 3.0 margin were chosen **against
the very cases used to report them**. The placebo/trap/plant numbers in §3 are
therefore not held out, and they overstate what an independent scene would show.
This is the single most important caveat for whoever verifies this.

**No real frames were used.** Every number here is synthetic. The `foam` stack
(which physically moved between frames) and the bubble-motion stack are the
obvious next material, and the 0.35 px bar must be re-measured against them
before it means anything about the corpus. The defocus-induced shift scales with
scene curvature and with focus step, so a bracket with finer steps could tolerate
a smaller bar and a coarser one may need a larger.

**Nothing is wired into the merge**, and no `n_eff` cost has been priced on real
data, because there is no merge path to price. `merge_cmd.rs` is revoked from me
(M109 owns it), so the CLI flag has to be proposed rather than applied.

**The third discriminator was not built.** Analysis-by-synthesis — comparing
against the running estimate re-blurred to the frame's own focus — is the only
form where focus difference is absent from the data term by construction. It
needs the merge's running estimate, and this module is deliberately free of the
merge.

**I did not verify this.** ORCH is routing an independent agent.

---

## 7. Disciplines

**D-W1.** *A filter that rescales signal and noise together buys no
discrimination.* Before reaching for a low-pass to suppress a nuisance, check
whether the nuisance and the noise scale the same way under it. If they do, the
normalised statistic is invariant and the filter is decoration (W2, W3).

**D-W2.** *When a symmetry argument justifies a null, name the geometry it
assumes.* "Symmetric blur carries no displacement" is true for a straight edge
and false for a curved one, and the failure is 60.9% of tiles, not a rounding
error (W5).

**D-W3.** *A nuisance you can name, you can project out.* Entering the known
contaminating direction as an explicit parameter and taking the Schur complement
is strictly better than hoping it cancels — and it degrades honestly, abstaining
where the ambiguity is real instead of guessing (W6).

**D-W4.** *If you estimate from noisy measurements, debias the information
matrix.* Squared measured gradients carry the noise variance, which inflates
apparent precision, shrinks the estimate toward zero, and makes any guard built
on that matrix measure noise. A calibrated noise model makes the correction
derivable rather than guessed; verify it against a planted ground truth, where
it should land exactly (W7).

**D-W5.** *Significance and magnitude answer different questions.* A tiny
systematic bias can be overwhelmingly significant. Gate on both, and require the
instrument to resolve the magnitude it is being asked about (W8, W10).

**D-W6.** *Every gate needs a plant showing what it stops, or it is decoration.*
Three gates, three demonstrated failure modes. The `faint` case existed solely to
show that the significance and resolution gates are load-bearing — and its first
version **failed its own expressibility assertion**, which is the assertion
earning its place (W10).

**D-W7.** *A design that changed in response to its own validation set is
in-sample and must say so.* Reporting tuned numbers as if they were held out is
the most comfortable way to mislead, and the caveat is worth more than the
numbers (§6).
