# M60b — What M28 settled, what it left open, and the two legitimate sources of disagreement it could not cover

> **NOT INDEPENDENTLY VERIFIED.** Same author as the measurements. Rule 12.
>
> **Companion to `M60-robustness-mask-at-merge-time.md`** (commit `4765816`), which
> holds findings F1–F11, the pre-registration of A1/A1b/A1c/A2′/A3, the negative
> controls and the architectural seam. This file is a **separate question**: it
> reads the prior art the first report was written without, and prices the two
> rival explanations for disagreement that are known to be *legitimate* — static
> defects (M29, M22) and photometric drift (M24). Nothing in the first report is
> retracted here; two things in it are strengthened and one is scoped.

---

**Headline.** *M28 answered half of the brief's step 1 — it measured the detector
at an index-chosen reference, and its own §8 names the merge's admitted set as
"the obvious next question" — and the two rival explanations the correction named
as the mask's biggest risks both turn out to be empty at this seam: static
defects can only lower this statistic, never raise it (exactly, by arithmetic),
and no per-frame photometric correction removes any of the disagreement, which
closes M24 §5's open question in the negative. Nothing should be built, and the
reason is M60's 15.7% null false-positive rate, not the confounds.*

**Second headline, on method.** *A pre-registered criterion was met at 94.8% and
is void, and the pre-registration is the only reason that is visible: the
two-parameter fit which cleared the bar has a slope of 0.16 on a stack with 10.6%
drift, and `√(2.1820 / 23.8430) = 0.3025` shows the entire "improvement" is the
fit shrinking its own numerator.*

---

## 0. Pre-registration for the one new measurement (A4)

*Written before the A4 run. The document analysis in §1–§4 needs no criterion:
it is reading, and it is checkable by reading the same rows.*

M24 §5 leaves an open question in as many words:

> "**No gain/offset was fitted.** Only the mean level was tracked. Whether a
> single global gain per frame suffices, **or an offset term is also needed, is
> unmeasured** — as is whether the variation is spatially uniform."

My F3 fitted a **gain only** — fact 225's prescribed estimator, the mean over all
pixels — and measured that it makes disagreement **worse** on both drifting
stacks (−22.5% on `coffee-bubbles`, −2.4% on `foam`). A one-parameter correction
failing is consistent with two different worlds: photometry does not explain the
disagreement, **or** the correction was the wrong shape and needed the offset
term M24 names. A4 separates them.

**A4.** Fit a per-frame affine `L' = s·L + c` by ordinary least squares of the
all-frame per-pixel mean on the frame's own luma, over every pixel, and re-measure
mean chi2 on the identical admitted set.

- **A4 is met** — photometric drift explains the disagreement, and the mask
  question reopens with drift removed first — if the affine arm removes **≥50% of
  the excess over 1.0** on at least one of `coffee-bubbles` / `foam`.
- **A4 fails** if the reduction is <50%, or negative, on both.
- **Control:** `109MSDCF`, which M24 measures as the corpus's quietest stack at
  0.91% peak-to-peak. A correction fitted on a stack with almost no drift should
  do almost nothing. If A4 moves `109MSDCF` substantially, the arm is absorbing
  something that is not photometry and the result is void.

**Asymmetry declared in advance, because it decides what the result can mean.**
The least-squares slope `s = Cov(L, ref)/Var(L)` also absorbs **focus-dependent
contrast**: a sharp frame has larger `Var(L)` than a blurry one, so `s` regresses
toward the mean frame regardless of any photometry. That is fact 225's failure
mode wearing a second costume, and it biases A4 **toward** success. Therefore:

- a **failure** of A4 is conclusive — two parameters plus a confound that helps
  them could not remove the excess;
- a **success** of A4 is **confounded** and would license no conclusion without a
  further arm separating contrast from photometry.

I am running A4 for the falsifying direction. This is stated here so that a pass
cannot later be read as a win.

### 0.1 A4b, pre-registered after A4's runs and before A4b's

*A4 has been run at this point; A4b has not. The A4 numbers that motivate this
are in §5. Stating the order explicitly because it matters: A4b is a
**disambiguating** arm added because A4's pass on one stack was accompanied by
fitted parameters that are not physically admissible as photometry, and I am
declaring what would separate the two readings before I look.*

**A4b.** The same measurement with the slope **pinned to `s = 1`**, so the fit
has exactly one degree of freedom — the offset — and cannot buy a reduction by
shrinking the frame onto the reference. `c_k = grand mean − frame k's mean`,
which is the offset analogue of fact 225's gain estimator and is the estimator
M24 §5's question actually names.

Two readings of A4's result on `foam`, and A4b separates them:

- **Reading P (photometric).** The offset term is the missing piece M24 named.
  Then **A4b alone should recover most of A4's 94.8%**, because the offset is
  doing the work and the slope is incidental.
- **Reading D (degenerate).** The two-parameter fit collapsed the frame onto the
  reference — `s → 0`, `c → grand mean` predicts the mean and destroys the
  numerator. Then **A4b should recover almost none of it**, because a pure
  translation cannot shrink a variance at all.

**These predictions are opposite and exhaustive, so A4b decides between them.**
Note that reading D is *arithmetically* certain to give A4b ≈ 0 on a
mean-centred statistic: adding a constant to every sample of a frame changes the
cross-frame spread only through the between-frame component. If A4b lands near
zero on `foam`, D is confirmed and A4's pass is void by the asymmetry above.

**Discipline 358 check.** A4's numerator (the cross-frame luma spread) and its
denominator (`σ_pred` from the calibrated model) come from different places: the
spread is accumulated from decoded sensor samples, the sigma from `profile.rs`'s
`σ²(S) = g·S + (RN_e·g)²`. **No perturbation is synthesised in A4 at all** — the
disturbance is whatever the real stack contains — so there is no possibility of
dividing a planted signal by the constant that planted it. The one shared
quantity is the mean luma, which enters the numerator as a centre and the
denominator as a level; that is the ordinary structure of a chi2 and is not
circular.

---

## 1. G1 — What M28 settled, and the half of step 1 it could not do

**M28 settled six things** (all MEASURED by its author, none independently
verified):

| # | what M28 settled | key number |
|---|---|---|
| S1 | Outlier signal **is** separable from defocus, if the reference is the **adjacent frame** rather than the running/whole-stack estimate | residual 1.13 → 12.30 over `dk` 1→16; radial profile flat at 0.98 outer/inner with an adjacent reference, 1.82× with a whole-stack one |
| S2 | The calibrated noise model predicts the clean adjacent-frame residual with no free parameters | median tile \|z\| 0.7416 vs 0.6745 half-normal = **1.099× pure noise** |
| S3 | A planted displacement is detected monotonically, and the `s = 0` placebo is clean at FPR ≤ 1% | 89.4% detection at `s = 4` @ FPR 5%; placebo 0.0% @ FPR 1% |
| S4 | Tile scale is **not** a sensitivity knob | near-flat over a 4× range |
| S5 | A clean-calibrated threshold transfers, in the predicted order | 1.01% / 8.33% / 17.88% @ FPR 1% |
| S6 | Per-frame gain must be fitted as the **mean over all pixels** | 4.28% (subject-centred median) vs 0.94–1.02% (three other estimators) |

**M28 left one thing open, and says so in its own §8 in as many words:**

> "**No merge output was produced. This measures a detector, not the effect of
> masking on a merged image.** Whether flagging 8.33% of `coffee-bubbles`' tiles
> improves or harms the result is unmeasured and **is the obvious next
> question**."

Also open, per the same section: no aligned-stack control; the plant is a rigid
translation only, so the sensitivity is a lower bound for translation and says
nothing about deformation, occlusion or illumination change; no leave-one-out;
and §2's 0.6745 comparison assumes Gaussianity in exactly the tails §3 and §5
are measuring.

**G1. The correction's premise is half right. M28 measured noise-normalised
disagreement on real stacks — but between frames it chose by index, not between
the frames the merge chooses by gate.** Those are different sets, and the
difference is not incidental:

- M28's reference is **frame `k` against frame `k ± 1`**. That is a design
  choice made *outside* the merge, and §1 is a sweep over that choice.
- The merge's admitted set at a pixel is **whichever frames pass the gate at
  that pixel**, selected by focus-response similarity to the winner. It is
  chosen per pixel, it is not an index neighbourhood, and on `foam` it is empty
  (`n_eff = 1`) for 91.80% of pixels.

So step 1 of the brief was done by M28 **for a detector at a chosen reference**,
and was not done — and could not have been done by M28's instrument — for the
merge's own averaging set. `M60-robustness-mask-at-merge-time.md` did that, at
the second seam, and M28's §8 names it as the next question. **The two are
complementary, not duplicative, and I am not claiming otherwise for having run
mine first: had M28 been named in the brief I would have framed M60 as
continuing it, but I would have run the same measurement.**

---

## 2. G2 — Two instruments that share no code agree to 2.9%, and that is the strongest validation either has

Nobody has put M28's number and mine side by side. They are measuring the same
physical quantity — *how far above pure sensor noise do two frames of a clean
stack sit, where there is no detail to be defocused* — through entirely separate
implementations.

| | M28 §2 | M60 F4 |
|---|---|---|
| language / path | Python, offline scripts | Rust, through the shipped merge |
| region | green sublattice of a centred 3072 px crop | full 2344 × 3514 plane |
| frame set | adjacent pairs, `dk = 1` | the gate's admitted set at each pixel |
| statistic | median over tiles of \|z\| | mean over pixels of chi2 |
| low-defocus isolation | tile median (robust to the textured minority) | lowest decile of the winner's focus response |
| **result** | **1.099 × pure noise** (amplitude) | **1.173** (variance) |

**G2. DERIVED: M28's 1.099 in amplitude is 1.099² = 1.208 in variance, against
M60's MEASURED 1.173 — a 2.9% disagreement between two instruments that share no
code, no language, no region and no frame-selection rule.**

Three caveats, all of which must travel with the number:

1. **The functionals differ.** Squaring a ratio-of-medians to compare against a
   ratio-of-means is exact only if the distribution shape is preserved between
   the two regimes. It is not exactly preserved. This is DERIVED with an
   assumption, not a measured identity, and I would not quote it to three
   figures.
2. **Rule 34 / discipline 358 disclosure — they share one constant family.**
   Both divide by `σ²(S) = g·S + (RN_e·g)²` from the same calibration lineage.
   So this cross-validates **the statistic and the two pipelines**, and does
   *not* cross-validate the calibration. If `g` were wrong by 20%, both would be
   wrong by 20% and would still agree.
3. **But they do not share the constant's *value*, and it does not matter.**
   M28 ran under `read_noise_e_high = 1.47`; M48 has since moved it to 1.2392.
   DERIVED: on `109MSDCF` the mean signal is 1391–1404 DN above black
   (MEASURED, §4), so the shot term `g·S` is ~500 DN² while `(RN_e·g)²` is
   ~0.2–0.3 DN². **Any read noise below 3 e⁻ changes the predicted variance by
   under 0.25% at this signal level**, so the agreement in G2 is insensitive to
   M48's change and would have been insensitive to a much larger one. That is
   worth recording on its own: this particular cross-check has no leverage on
   read noise, and should not be cited as if it did.

**One ambiguity in M28 I could not resolve without re-running it, which I was
told not to do.** M28 §7 P1 reads *"median `|z|` on the clean stack is **1.01**
at full resolution, the noise floor."* Read as a raw `|z|` that is 1.01/0.6745 =
**1.50× the floor**, not at it; read as a ratio it is 1.01× and the prose is
right. §2's table gives the ratio explicitly (1.099), so I used §2 and left P1
alone. Flagging it because a future reader quoting "1.01 at the noise floor"
will get a different number depending on which reading they take.

---

## 3. G3–G4 — Static defects (M29, M22) cannot fire this mask, and today the sign is the opposite of the brief's

The correction states the concern this way:

> "**`M29-static-defects-measured.md`** — defects fixed in sensor coordinates.
> **Under alignment** these move relative to the subject, so they produce
> cross-frame disagreement that is real, is not motion, and must not be masked
> as if it were."

The conditional is load-bearing, and **it is not satisfied by the code that
exists.** The merge does not align. M29 §5 measures what actually happens
instead: adjacent-frame displacement of **0.07–0.22 green px** (median over
tiles, two stacks, four radii, sixteen tiles each), and a dilution factor
`D = 0.999` at `n_eff = 3` — which is M29's way of saying that a sensor-fixed
defect **does not move between the frames the merge averages**.

M60's statistic is a variance across the admitted frames **at a fixed pixel
index**. So the consequence is arithmetic, not empirical:

**G3. DERIVED, exactly. A static additive defect (M22's 11,393 hot pixels,
0.0346% of the sensor) lowers chi2. It cannot raise it.**
Observed `x_k = S_k + h` with `h` constant across frames. The numerator is
`Var_k(x) = Var_k(S)` — `h` cancels identically. But the denominator is computed
from the observed mean `S̄ + h`, so `σ²_pred = g(S̄ + h) + c` is **larger** than
the truth. Numerator unchanged, denominator inflated ⇒ **chi2 is
under-estimated**.

**G4. DERIVED, exactly. A static multiplicative defect (M29's dust) attenuates
chi2 by a factor `(1 − A)`. It cannot raise it.**
Observed `x_k = (1 − A)S_k`. Numerator `(1 − A)²Var(S)`. Denominator, in the
shot-dominated regime, `≈ g(1 − A)S̄`. Ratio `∝ (1 − A)²/(1 − A) = (1 − A)`. M29
§3 puts real sensor dust at **1–15%** at working apertures, so **chi2 falls by
1–15% on affected pixels**.

**Both classes of static defect can therefore produce only false *negatives* at
this seam, never false positives. The brief's worry is correct as a property of
a future aligned pipeline and is inverted in sign for the pipeline that exists.**

Two things follow, and they are more useful than the guard the correction asked
for:

- **The right home for the concern is a precondition on alignment, not on the
  mask.** ARGUED: a defect of depth `A` displaced by `dx` between frames
  contributes disagreement of order `(A·|∇S|·dx)²/σ²`, which vanishes at M29's
  measured `dx ≈ 0.2 px` and grows **quadratically** with whatever displacement
  alignment introduces. Whoever lands alignment inherits this, and can price it
  in advance from M29's own numbers. A mask built today and validated today
  would carry a guard against a term that is currently zero — which is worse
  than no guard, because it would look tested.
- **The real gap is temporal stability, and neither M22 nor M29 measured it.**
  Everything above assumes the defect is *constant across frames*. A flickering
  defect — random telegraph signal, the classic mechanism in exactly the
  hot-pixel population M22 counted — is **not** static, produces genuine
  per-pixel cross-frame disagreement with no motion whatsoever, and would fire a
  mask. M22 measured the population as a **count** (11,393 pixels); M29 measured
  dust as **sensor-fixed structure**. Neither measured whether the population is
  temporally stable. At 0.0346% of 8.2M pixels that is ~2,800 pixels — invisible
  in a mean of 1.85, potentially visible at p0.999 = 87.1. **This is a real open
  question and I am naming it rather than assuming it away; `D:\macro-dark-frames\`
  has 242 frames across 11 ISOs and could settle it without a subject at all.**

---

## 4. G5–G7 — Photometric drift (M24): the question M24 left open, closed in the negative

### 4.1 G5 — M24 §1 reproduces on an independent instrument

M24 tracked per-frame mean level in Python on **subsampled** stacks (every 2nd or
3rd frame; §5 calls its jitter figures lower bounds). M60 computes the same
quantity in Rust over **every frame and every pixel** of the full plane.

| stack | M24 §1 peak-to-peak | M60 MEASURED | agreement |
|---|---:|---:|---|
| `109MSDCF` | 0.91% | **0.910%** | 3 s.f. |
| `coffee-bubbles` | 8.93% | **8.909%** | 0.24% |
| `foam` | *excluded from M24* | **10.604%** | new row |

**G5. MEASURED: M24 §1's drift table reproduces on an independent instrument to
0.24%, and `foam` — which M24 excluded — is the second-largest drift measured in
the corpus at 10.604% peak-to-peak, behind `coffee-bean`'s 11.70%.**

### 4.2 The three arms

M24 §5's open question, verbatim: *"Whether a single global gain per frame
suffices, or an offset term is also needed, is unmeasured."* All three arms below
run on the **identical admitted pixel set**, asserted equal in the code, so the
comparison is paired.

| stack | raw mean chi2 | **A1b** gain only (fact 225's estimator) | **A4** affine, LS | **A4b** offset only, `s ≡ 1` |
|---|---:|---:|---:|---:|
| `109MSDCF` | 1.8508 | 1.7906 (**7.1%**) | 1.7631 (10.3%) | 1.8482 (**0.3%**) |
| `coffee-bubbles` | 2.1712 | 2.4345 (**−22.5%**) | 2.0713 (8.5%) | 2.0827 (**7.6%**) |
| `foam` | 23.8430 | 24.3811 (**−2.4%**) | 2.1820 (**94.8%**) | 22.7002 (**5.0%**) |

*(percentages are the fraction of the excess over 1.0 removed; negative means the
correction made disagreement worse. All MEASURED, gate 1.0.)*

### 4.3 G6 — A4 met its pre-registered threshold and the pass is void, exactly as pre-registered

A4 removed **94.8%** on `foam`, clearing the ≥50% bar in §0. By the asymmetry
declared in §0 before the run, a pass licenses no conclusion — and here the
fitted parameters refute the photometric reading outright:

| stack | measured drift (ptp) | A4 fitted slope `s` | A4 fitted offset `c` | mean signal |
|---|---:|---|---|---:|
| `109MSDCF` | 0.910% | 0.9886 .. 1.0034 | −4.98 .. 11.19 DN | ~1397 DN |
| `coffee-bubbles` | 8.909% | 0.8172 .. 0.8535 | 39.29 .. 71.51 DN | ~340 DN |
| `foam` | 10.604% | **0.1605 .. 0.5783** | **350.60 .. 741.05 DN** | ~862 DN |

**G6. DERIVED from MEASURED inputs: A4's pass on `foam` is a degenerate fit, not
a photometric correction, and three independent arguments say so.**

1. **The parameters are not physically admissible.** A photometric gain must
   satisfy `s ≈ 1/(1 + drift)`, i.e. `|s − 1| ≲ 0.11` for a 10.6% drift. On
   `foam` it reaches **0.84**. Across the three stacks the drift spans 11.7×
   while `|s − 1|` spans ~160×; the fit is not tracking the drift.
2. **The arithmetic of the reduction is exactly a slope shrink.**
   `2.1820 / 23.8430 = 0.09151`, and `√0.09151 = 0.3025` — which sits **inside**
   the measured fitted-slope range 0.1605..0.5783. The "improvement" is the
   numerator being multiplied by `s²`, not a nuisance being removed. At
   `s ≈ 0.3, c ≈ 550` a pixel at the mean maps to `0.3·862 + 550 ≈ 809 ≈` the
   mean; the fit predicts the grand mean and squashes every frame into a band
   around it.
3. **A4b decides it, and was pre-registered to.** §0.1 laid out two exhaustive
   opposite predictions. Reading P (the offset is M24's missing piece) requires
   A4b to recover most of 94.8%. Reading D (degeneracy) requires A4b ≈ 0.
   **A4b reads 5.0%. Reading D is confirmed.**

### 4.4 G7 — the answer to M24 §5

**G7. MEASURED, three stacks: no per-frame photometric correction removes
merge-time disagreement. A gain alone removes 7.1% on the quiet stack and makes
it *worse* on both drifting stacks (−22.5%, −2.4%). An offset alone removes
0.3% / 7.6% / 5.0%. The honest joint fit degenerates. M24 §5's question — "is an
offset term also needed?" — is answered *no*, and for a reason stronger than the
question anticipated: the offset is not what is missing, because nothing
photometric is missing.**

Photometric drift is real in this corpus — M24 established that and G5
reproduces it — **and it is not what the admitted frames disagree about.** The
mechanism is not mysterious: the gate admits frames whose *focus response*
matches the winner's, and a global level shift moves every frame's response
together, so the drift largely commutes with the selection. G7 also strengthens
M60's C1 (fact 225's estimator is scoped by this seam) rather than replacing it.

---

## 5. G8 — The decision: nothing to build, and the reason is not the one the correction expected

Arguing from M28 + M24 + M29 + M60's F1–F11, in descending order of strength:

1. **The threshold is forced and it is bad.** (M60 F10) At `n_eff = 2` the
   MSE-optimal rule is `E[chi2] > 2` with **no free parameter** — and the
   realised statistic has 1 dof, so `P(χ²₁ > 2) = 0.1573`: a **15.7%
   false-positive rate on a perfectly clean stack**. `n_eff = 2` is the modal
   case. This is the argument that decides it.
2. **The surface is small.** (M60 F1) On `foam`, the corpus's worst stack,
   **91.80%** of pixels have `n_eff = 1`, where chi2 is undefined and no mask can
   act. The winner is admitted unconditionally — that is what makes "never
   noisier than one frame" provable — so a mask can only ever touch 8.20% of the
   worst case, 38.26% of `coffee-bubbles`, 58.34% of the control.
3. **Most of the raw signal is detail composition, not motion.** (M60 F5/F6)
   Matched on detail octaves, `foam`'s raw 12.883× over the control collapses to
   **2.02–3.12×** — matching removes 76–84%. `coffee-bubbles`, which has real
   bubble motion, comes out at **1.184×**, and **0.671×** — *below the clean
   control* — in the [4,8) octave.
4. **Nobody has produced a merged image either way.** M28 §8 says so; M60 §8 C4
   says so. Two independent measurements of the *detector* now exist and both
   decline to bound the *effect*. That asymmetry is itself evidence about
   priority.
5. **Question 45's standing objection is unanswered.** Masking removes
   contamination *and* removes focus coverage, and fact 213 holds that coverage
   is the scarcer resource in most brackets.
6. **New here, and it cuts against my own convenience:** the two legitimate
   sources of disagreement the correction named as the mask's biggest risks are
   **both empty at this seam today**. Static defects can only suppress the
   statistic (G3, G4); photometric drift does not explain it (G7). **I am not
   claiming these as reasons against building — they are neutral, and I would be
   overselling if I folded them into the case.** What they do is remove the last
   argument that a mask is needed for *safety*, and equally remove two arguments
   that it would be *dangerous*. The reason not to build remains (1) and (2).

**G8. Nothing should be built. The robustness mask is machinery whose best
available operating point costs 15.7% of good frames on a clean stack to defend
8.20% of the pixels of the corpus's worst stack, against a disagreement that is
76–84% detail composition. The correct output of this milestone is a note in the
ship order, not a mask.**

**Suggested ship-order note.** *Robustness/outlier mask: measured twice (M28 at
the adjacent-frame seam, M60 at the merge's admitted set) and declined. Blocked
on a merged-image measurement, not on a detector. Revisit if and only if (a)
alignment lands, which turns M29's static defects from a zero term into a
quadratically growing one, or (b) a capture arrives whose `n_eff ≥ 2` surface is
large enough for a 15.7% null false-positive rate to be worth paying.*

---

## 6. What changed in code

Three files, all mine.

| file | change |
|---|---|
| `crates/strehl-core/src/merge.rs` | `fold_censored_probing_photometry`'s last parameter goes from `black_dn` (a pivot: `black + (L−black)·s`) to `luma_offset` (`L·s + c`). **Behaviourally identical at every existing call site**, all of which pass `0.0`, and confirmed by `109MSDCF` reproducing 1.8508 and 7.1% to four figures after the change. The affine form is required because a scale-only signature cannot ask M24 §5's question. |
| `crates/strehl-core/src/merge.rs` (tests) | `the_photometric_probe_moves_the_statistic_and_leaves_the_image_alone` gains an offset arm and a **derived** cross-arm prediction (gain/offset chi2 ratio = 0.9112 at pixel 1, from `(9.545/10)²`), so the new parameter cannot be silently ignored. |
| `crates/strehl-cli/examples/m60-disagreement.rs` | pass 1 accumulates a per-pixel all-frame mean; pass 2 adds the A4 (least-squares affine) and A4b (`s ≡ 1`) arms, both asserted to cover the identical admitted set as the raw arm. |

**Nothing here needs a file I do not own, and there is no hand-off from this
report.** M60's existing hand-off (`merge_cmd.rs:819`, already routed to M53 with
the caveat not to extend it into the election) is unchanged.

**Rule 35 note on the test.** The new assertion's subject is the code's measured
chi2 ratio; its object is `(9.545/10)² = 0.9112`, arithmetic done by hand from
the fixture's literal luma values. They are not the same value and the assertion
has power to fail — demonstrated below.

---

## 7. Criteria and negative control

| criterion | pre-registered in | result |
|---|---|---|
| **A4** ≥50% of excess removed on `coffee-bubbles` or `foam` | §0 | **MET on `foam` (94.8%) — and VOID by the asymmetry declared in the same section.** Failed on `coffee-bubbles` (8.5%). |
| **A4 control**: `109MSDCF` must move little | §0 | **MET.** 10.3%, with `s ∈ 0.9886..1.0034` and `c ∈ −4.98..11.19 DN` on a ~1397 DN signal — consistent with M24's 0.91%. |
| **A4b** decides between reading P and reading D | §0.1 | **Reading D.** 5.0% on `foam` against A4's 94.8%. P required "most of 94.8%". |

**NC1 — negative control on the new offset parameter.** `merge.rs` backed up to
`$env:TEMP\m60b-merge-backup.rs` (98,655 bytes), then `fold_inner` patched to
drop the offset term: `f64::from(raw * luma_scale + luma_offset)` →
`f64::from(raw * luma_scale)`. Patch confirmed applied by reading the line back.

```
Compiling strehl-core v0.0.0 (...)
thread 'merge::tests::the_photometric_probe_moves_the_statistic_and_leaves_the_image_alone'
  panicked at crates\strehl-core\src\merge.rs:2064:9
test result: FAILED. 0 passed; 1 failed; 135 filtered out
```

Red at 2064 — the offset arm no longer zeroes pixel 0 — which is the intended
assertion. Restored from the `$env:TEMP` copy (never `git checkout --`, per the
method: four other agents have uncommitted work in this tree), `LastWriteTime`
reset, and **verified two ways rather than by exit code** (discipline 366, and
fact 776, which exists because a restore of mine failed silently in M58): the
line reads back as `f64::from(raw * luma_scale + luma_offset)` and the file is
98,655 bytes, identical to the backup.

**What NC1 does and does not establish.** It establishes that the offset
parameter is live and load-bearing in the test. It does **not** establish that
A4b's corpus numbers are right; those rest on the three-way separation in §4.2
(0.3% / 7.6% / 5.0% are three distinct values, and A4b differs from the raw arm
at 1.8482 vs 1.8508, so the arm is demonstrably not an identity).

---

## 8. Verification

Read with real cargo progress lines, per rule 33 as amended (`Compiling` for
build/test/run, `Checking` for check/clippy); no `-q` anywhere.

```
cargo test --workspace      Compiling strehl-core, strehl-raw, strehl-plugin, strehl-cli
                            40 + 136 + 35 + 8 + 1 = 220 passed; 0 failed
cargo clippy --workspace --all-targets
                            Checking strehl-core, strehl-raw, strehl-plugin, strehl-cli
                            Finished — no warnings
cargo fmt --all -- --check  exit 0
```

220/220, unchanged from M60's commit `4765816`: the new assertions live inside an
existing test, so the count is the same and the *coverage* is not.

Corpus runs: `109MSDCF` (22 frames), `coffee-bubbles` (19), `foam` (100), all at
`--gate 1.0`, all read-only over `D:\personal\macro`.

---

## 9. Contradictions and corrections to the corpus

- **C5 (new).** The correction brief's static-defect guard is **inverted in sign
  for the pipeline that exists**. M29's and M22's defects can only produce false
  negatives at an unaligned merge (G3, G4). The concern is valid, and belongs on
  alignment.
- **C6 (new).** **M24 §5's open question is closed, in the negative** (G7). No
  per-frame gain, offset, or honest joint fit removes merge-time disagreement.
- **C7 (new).** M28 §2 and M60 F4 **agree to 2.9%** across independent
  implementations (G2) — a corroboration, not a contradiction, but neither
  report can cite it because neither knew about the other's number.
- **C8 (new).** M28 §7 P1's *"median `|z|` … is 1.01 … the noise floor"* is
  ambiguous between a raw `|z|` (= 1.50× the floor) and a ratio (= 1.01×). Not
  resolvable without re-running M28's script, which this milestone was told not
  to do.
- **C9 (new).** M24 excluded `foam`. It is the corpus's second-largest measured
  drift at **10.604%** peak-to-peak (G5), behind `coffee-bean`'s 11.70%, and it
  is the stack M28 used as its positive control — so M28's positive control is
  also, unknown to it, a near-worst-case photometric-drift stack. G7 shows that
  does not explain its disagreement, but the coincidence should be on the record.
- **Carried from M60, unchanged:** C1 (fact 225's estimator is scoped at this
  seam), C2 (`coffee-bubbles` is a near-no-op), C3 (`foam`'s 12.883× is 76–84%
  detail composition), C4 (no merged image has been produced by anyone).

**Still live and deliberately untouched: question 180.** M60 concluded
`through_focus.rs:514` needs 5.943; M53 concluded its `--stats` site needs 1.815.
`merge_cmd.rs` is M53's file and I have not looked at it.

---

## 10. Findings index

| # | label | statement |
|---|---|---|
| G1 | ARGUED from source | M28 settled the detector question at an index-chosen reference; the merge's gate-chosen admitted set is a different set, and M28 §8 names it as the next question. Step 1 was half done. |
| G2 | DERIVED from two MEASURED | M28's 1.099× (amplitude) = 1.208 in variance vs M60's 1.173 — 2.9% apart, across implementations sharing no code. Insensitive to read noise below 3 e⁻. |
| G3 | DERIVED, exact | A static **additive** defect leaves the numerator unchanged and inflates the denominator ⇒ chi2 under-estimated. Cannot cause a false positive. |
| G4 | DERIVED, exact | A static **multiplicative** defect of depth `A` attenuates chi2 by `(1 − A)`; real dust is 1–15%. Cannot cause a false positive. |
| G5 | MEASURED | M24 §1 reproduces to 0.24% on an independent instrument; `foam`, excluded by M24, reads 10.604% ptp. |
| G6 | DERIVED from MEASURED | A4's 94.8% pass on `foam` is a degenerate slope shrink: `√(2.1820/23.8430) = 0.3025`, inside the fitted slope range. Void by pre-registration; confirmed by A4b. |
| G7 | MEASURED, 3 stacks | No per-frame photometric correction removes merge-time disagreement. M24 §5 answered **no**. |
| G8 | ARGUED from all of the above | Nothing to build. 15.7% null false-positive rate to defend 8.20% of the worst stack's pixels against a 76–84% detail-composition signal. Ship-order note, not a mask. |
| — | OPEN | **Temporal stability of the M22 defect population is unmeasured.** A flickering hot pixel is not static and would fire a mask. ~2,800 pixels. `D:\macro-dark-frames\` can settle it with no subject. |

