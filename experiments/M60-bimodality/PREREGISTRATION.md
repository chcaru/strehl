# M60 — PRE-REGISTRATION

**Frozen before any occlusion-cell result was computed.** Committed as its own
file so that the commit graph shows it preceded the measurement. Gate 0
(`data/gate0.txt`) and the corpus survey (`data/01-survey.txt`,
`data/02-drift.txt`, `data/03-previews.txt`) were run first, because they
characterise the *instrument and the corpus*, not the hypothesis.

---

## 1. The claim under test

An external reviewer argues that at an occluding edge a background pixel near the
boundary is **veiled** by the defocused foreground, so the observation is a
two-layer composite

```
I_k = a_k·(F ⊛ PSF_k) + (1 − a_k)·(B ⊛ PSF_k)
```

whose through-focus curve is **bimodal**: one peak where the foreground is in
focus, one where the background is. The load-bearing premise is that the second
peak is *there, at a usable separation and amplitude*. Everything downstream —
posterior-weighted merge, entropy confidence, bimodality-as-occlusion-detection,
boundary mass as "no frame in focus" — rests on it.

M21 already measured a version of this and folded facts 150–152. M60 exists
because M21's answer is **enrichment of a shape statistic at depth steps
inferred from the same focus volume**, and three things it explicitly did not do
are the three that decide the design:

1. it never used the calibrated noise model, only a frame-permutation placebo;
2. its "depth steps" were `|∇ argmax|`, not labels — M21 §8 lists "no ground
   truth" as its first unmeasured item;
3. it never measured the **separation in frames**, only the *rate* of
   multi-peakedness.

## 2. Data, and why these stacks

The corpus is `D:\personal\macro`, **read only**. `C:\dev\macro\test` holds a
subset and is not used.

| stack | frames | ISO | shutter | marked | role |
| --- | ---: | ---: | ---: | ---: | --- |
| `bee-3` | 299 | 100 | 0.20 s | f/5.6 | **primary.** Finest focus sampling in the corpus; lowest gain of the two ISO-100 bee stacks; genuine occluding geometry (legs, antennae, wings standing off a body) |
| `bee-1` | 299 | 100 | 0.50 s | f/5.6 | **replication.** A *different pose* of the same subject (NCC 0.60 against `bee-3`) |
| `bee-2` | 299 | 400 | 0.05 s | f/5.6 | **not an independent scene.** NCC **0.9562** against `bee-3` — the same setup at a second ISO. Used only as an ISO arm, never counted as a second sample (fact 50's trap) |
| `wrapped-text-1` | 130 | 100 | 0.067 s | f/5.6 | **negative control.** Printed text on a smoothly curved surface: dense broadband texture, *continuous depth, no discontinuity anywhere*, and self-similar at the glyph pitch — so it is simultaneously the no-occlusion control and the periodic-structure control |
| `wrapped-text-2` | 120 | 400 | 0.025 s | f/5.6 | negative control, second framing and second ISO |
| `109MSDCF` | 22 | 160 | 1.3 s | f/11 | **shallow arm.** Whether a 22-frame stack can resolve two peaks at all |

Excluded on purpose: `foam` (scene evolves during capture), `coffee-bubbles`
(bubble motion). Both are confounds for this measurement.

`112`/`113`/`119`/`coffee-bean` are not run: they are not deeper than `bee-*`,
carry no deliberate occlusion, and `coffee-bean` is where M21's number already
lives.

**Corpus note.** These directories were named `134MSDCF`, `135MSDCF`,
`136MSDCF`, `131MSDCF`, `133MSDCF` when this milestone started and were renamed
by the owner *while a probe was running* (which is what the `LibRawIOError` in
the first run of `02` was). The mapping is fixed by exact fingerprint — frame
count, ISO, shutter and EXIF timestamps — recorded in `data/02-corpus-rename.txt`.
Nothing under `D:\` was written by this milestone.

## 3. Instrument

**Focus measure.** `f_k(x)` = box mean of Sobel gradient magnitude at radius `R`
on the G1 green sublattice, black level 512 subtracted. This is the project's
own operator family (facts 70–73). Sobel is applied to a 2-D plane only; the
library asserts it (AGENTS rule 23, M32's defect).

`R = 2` is the **primary** setting, pre-registered from fact 152: bimodality is
*depleted* (0.36×) at the shipped `R = 13` because a 27×27 CFA box is 54 sensor
px and averages both layers together. `R ∈ {1, 2, 4, 8}` is swept.

**Noise.** `σ²(S) = g·S + (RN_e·g)²` with `g = max(ISO,100)/436.8` DN/e⁻,
`RN_e = 4.20` below ISO 400 and `1.2392` at or above it — transcribed from
`crates/strehl-core` and asserted against that source in `00-selftest.py`
(AGENTS rule 3: the model is injected, never re-derived).

`σ_f(k, x)`, the **sampling sd of the focus response**, is obtained by Monte
Carlo: draw independent noise at the observed signal level, recompute `f`, take
the sd over reps. Rep count is fixed by a convergence check reported before use.

**Two-peak decomposition.** Per pixel: `k1 = argmax_k f_k`; `k2` = the interior
local maximum, other than `k1`, with the greatest prominence over the running
minimum between it and `k1`; `kd` = the argmin on the closed interval `[k1,k2]`.

```
prom = f(k2) − f(kd)                       DN
z    = prom / sqrt( σ_f(k2)² + σ_f(kd)² )  dimensionless
```

Frames are independent captures so the two variances add. **No smoothing along
the frame axis** — a frame-axis smoother correlates neighbouring samples and
would make that addition wrong.

`prom` and `sqrt(σ_f² + σ_f²)` are reported **separately** as well as the ratio
(AGENTS rule 39, discipline 338). The denominator is a *predicted* sd from an
external model, not a measured null residual, which is the distinction discipline
338 turns on — but the separate numbers are published anyway so a reader can
check that.

## 4. Registered threshold policy

`z*` is **not** fixed a priori and no σ-count is asserted. `k2` is a maximum over
O(n/2) candidate frames, so its null distribution is a multiplicity tail, not a
Gaussian tail; quoting "3σ" would be arithmetic and not evidence (AGENTS rule
20). `z*` is calibrated on null **N1** to a **1% per-pixel false-positive rate at
the same `n` and the same population size**, and the calibration curve is
published. Every hit rate in the results is quoted against that `z*`.

## 5. Labels — and why they are drawn by eye

Bins and binned quantity must not share a driving mechanism (AGENTS rule 17).
M21's first number was **29.47×** and collapsed to 4.38× once the depth-step map
was moved to an independent scale, because a bimodal pixel *manufactures* the
`|∇ argmax|` step it is credited with landing on. The clean fix is a label that
never touches the focus volume:

* **Occlusion cells** are rectangles drawn by hand on rendered frames, each
  straddling a visible silhouette where a nearer element crosses in front of a
  farther one.
* Each cell carries two hand-drawn **reference patches**, `FG` and `BG`, placed
  on unambiguous unoccluded ground on each side, well away from the boundary.
* **Control cells** are rectangles drawn on continuous surfaces — the
  `wrapped-text-*` label, and single-surface patches of the bee — matched on
  texture and signal.

`M13`'s "occluding-edge cells" were considered and **do not fit as real cells**:
they are a *synthetic plant* (a Porter-Duff `over` composite of two real corpus
textures at two chosen defocus levels, `experiments/m13-window-depth/src/edge.rs`),
not a hand-labelled set on real frames. M13 §2.5 item 4 says so itself — "the
plant has no disocclusion; both layers are fully observed everywhere". It is
therefore reused here in the role it can actually fill: **the positive control
P1**, re-implemented independently in Python.

## 6. Hypotheses, with the falsifying observation stated

| id | claim | predicted direction | falsified if |
| --- | --- | --- | --- |
| **H1** | real occluding edges show a second peak clearing the calibrated noise floor | hit rate at occlusion cells **>** matched controls | rates within the controls' own between-cell sd, or occlusion **<** control |
| **H2** | the separation is usable | `\|k2 − k1\|` well above the through-focus FWHM, and tracking the depth step measured from the *unoccluded* FG/BG reference patches | `\|k2 − k1\|` piles up at ≤ FWHM, or is uncorrelated with the reference step |
| **H3** | bimodality is *occlusion*, not texture or periodicity | `\|k2 − k_BG,ref\|` at occlusion cells **<** the same statistic under permuted cell↔reference pairing; and control-cell hit rate at the calibrated `z*` **≈ 1%** | control cells fire at occlusion-like rates, or `k2` is unrelated to the background's own focus frame |
| **H4** | posterior entropy is a real confidence output | entropy separates occlusion from control with AUC > 0.55 | AUC ≤ 0.55, or entropy is degenerate (saturated), which would replicate M32 |

## 7. Controls, each with what it cannot separate

| id | control | what it cannot separate |
| --- | --- | --- |
| **N1** | **noise-only plant**: one real frame repeated `n` times with independent calibrated noise. True curve flat; every peak is noise. Sets `z*` | Blind to the calibration itself: it draws noise from `g` and normalises by `g` (AGENTS rule 34, fact 599). It validates the *operator*, never the gain |
| **N2** | **frame permutation** (M21's placebo). Preserves the observed marginal exactly | The marginal contains one very tall in-focus value, so a permuted curve is not a noise curve. Bounds order-dependence, not amplitude |
| **N3** | **real no-discontinuity cells**, `wrapped-text-*` and single-surface bee patches | Cannot separate "no occlusion here" from "an occlusion this operator cannot see" |
| **N4** | **periodic structure**: printed glyphs repeat at a fixed pitch | Cannot rule out periodicity at a pitch this text does not contain |
| **N5** | **boundary mass**: fraction with `k1` within 2 frames of either end | Nothing — it is a definition, reported as a separate diagnosis, not as evidence for or against H1 |
| **P1** | **two-layer plant** at known separation, real textures, calibrated noise | fact 738 / discipline 358: the plant's blur ladder is mine, so it is read out as *recovered vs planted separation* and never against the constant that generated it |
| **B1** | **fact-73 blindness check**: box-mean `\|∇\|` on a monotone step at four blurs, plus the real cells' own contrast | If the operator is blind at the cells, nothing about curve *shape* there is admissible |

## 8. Power — asserted before any result is read

Fact 779: a control on 22–107 px had no power and only its own count assertion
revealed it. So, before any hit rate is printed:

* the pixel population of **every** cell class is asserted `>= 20000`;
* the number of independent cells per class is asserted `>= 6`;
* the **minimum detectable difference** in hit rate is computed and printed at
  the realised `n` for a two-proportion test at α = 0.01, power 0.80, using the
  **between-cell** sd rather than the binomial sd, because pixels within a cell
  are not independent.

If a class fails these assertions the run stops and the class is reported as
underpowered rather than as a null.

## 9. What this milestone will not do

* No unmixing, no reconstruction, no merge change. **No Rust is written**;
  `crates/**` is read-only for M60.
* No claim about whether a two-component fit *recovers* usable background. That
  is a separate question and is out of scope even if H1 survives.
* No alignment model. Drift is measured (`data/02-drift.txt`) and reported as a
  bound; if it exceeds 1 green px on any stack used, the affected result is
  labelled UNVERIFIED rather than corrected.

## 10. The outcome that would end this line of work

If H1 fails — if the second peak is absent, or present at an amplitude
indistinguishable from the calibrated noise floor, or present but equally common
on a surface with no depth discontinuity — then the reviewer's cascade does not
have a foundation on this rig, and that is the result. It is not to be rescued
by re-tuning `R`, the prominence rule or `z*`. Any such retune is reported as a
**post-hoc** arm, labelled so, and does not replace the registered one.
