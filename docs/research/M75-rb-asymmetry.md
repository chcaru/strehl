# M75 — Are the R/B gradient and the R decoupling one phenomenon?

**Status: MEASURED.** Runs against the owner's 242 delivered dark frames at
`D:\macro-dark-frames`, 11 ISO groups × 20 frames after dropping the two
stabilisation shots. Read-only. No file under `crates/` was modified. No flat
field was touched: `D:\personal\macro\flat-fields` belongs to M71.

**One pre-registered criterion fired against my own headline wording and its
consequence is honoured in §5.3.** Nothing else moved.

---

## Headline

**They are two phenomena, and neither is what it was called.**

1. **The gradient is not an R-and-B effect. It is a green effect, and M68's
   description of its own finding is inverted.** M68 §6 fact 22 concluded that
   "both chroma planes drift by the same ~6.5% in α against green from the top
   of the sensor to the bottom". Fitting the four planes' α **absolutely**
   rather than in ratio — the observable M68 did not have — the greens rise
   **+6.8% and +7.2%** while R and B sit at **−0.5% and −0.6%**, inside their
   own noise floors. The ratio M68 measured is real and I reproduce it; what
   moves in it is the denominator.

2. **The two findings implicate disjoint plane sets, on different sensor axes,
   and do not share a spatial signature.** The gradient lives in
   {G1, G2}, is **row**-organised, and is indifferent to the dual-gain switch.
   The temporal covariance that isolates R lives in {G1, G2, B}, is
   **column**-organised, and its upstream share climbs from 0.03 to 0.97 across
   the ISO range. The decisive gate failed both limbs with the power to detect
   them.

3. **The green gradient is multiplicative, not additive, and dark current is
   excluded outright.** That makes it the *same class of object* as M68's
   B-plane 0.84× — a per-plane analog scale — and it is the first direct
   evidence that such scales are **not constant across the array**, which is
   why M68 §5 gate D1 failed and why 0 of 32 row bands matched either candidate.

4. **Operationally this is immaterial, and unlike my own M72 finding it flips
   sign.** ±1.7% in σ on the two green planes, conservative in the top half and
   over-confident in the bottom half, crossing zero at mid-frame.

---

## 1. Rule 40 — what I read before measuring

Read in full: `docs/research/M68-b-plane-mechanism.md`, including its §7.1
retraction and its §10 error log; `docs/research/M72-green-plane-correlation.md`,
including the §12 post-publication amendment and the §9 α/δ decomposition;
`docs/research/M69-focus-noise-sd.md` headline and verdict.

Read in part: `docs/research/SYNTHESIS.md` facts 991–1009 and 1025–1034;
`docs/research/M50-fpn-anisotropy-measured.md` §5, which matters and is credited
in §7.3; `docs/research/M16-orientation-fpn-measured.md` §0–§1;
`docs/research/M48c-defect-layer-measured.md` for the defect criterion.

Code read, not modified: `crates/strehl-core/src/profile.rs`,
`crates/strehl-core/src/noise.rs`,
`experiments/M68-b-plane-mechanism/src/04-gradient.py` (to reproduce M68's
estimator faithfully), `experiments/M72-green-correlation/src/01-green-correlation.py`
and `src/02-criteria.py` (imported by path, see §12).

Searched `docs/research/*.md` for `row band|vertical gradient|row profile|
sublattice|checkerboard`; 21 files matched and the two with a genuine claim on
this territory are M16 and M50. Neither had been connected to M68 §6 fact 21.

---

## 2. The pre-registration

`experiments/M75-rb-asymmetry/src/01-preregistration.py`, committed at
**`34a3d39`** before any dark frame was read, and its planted self-test ran
after the commit. It names hypotheses H1 (one phenomenon), H2 (two), H3 (common
cause, different expression), H4 (artefact) and **H5 (the gradient is not a
chroma property at all)**; observables O1–O6; estimators E_alpha, E_rho,
E_trend, E_defect; nulls N_gain, N_indep, N_grad **each scoped to the statistic
it is null for**; and gates K0–K5 plus adversarial A1–A2, every one with both
branches written.

### 2.1 The derivation that made H5 worth a hypothesis

M68 measured `r(b) = α_B(b)/α_G2(b)` over row bands. Writing
`α_p(b) = α_p(0)·(1 + m_p·b)`,

```
r(b) = r(0)·(1 + m_B·b)/(1 + m_G2·b) ≈ r(0)·(1 + (m_B − m_G2)·b)
```

> **Fact 1 (DERIVED).** **A ratio measures only the difference of slopes.** A
> falling `r(b)` admits four mechanisms — B falls with green flat; **green
> rises with B flat**; both fall with B steeper; both rise with green steeper.
> The self-test plants all four and recovers ratio trends of −0.0640, −0.0602,
> −0.0682 and −0.0569 from absolute plane trends of (−0.064, 0), (0, +0.064),
> (−0.128, −0.064) and (+0.064, +0.128). **The same ratio trend from opposite
> physics.** M68's prose asserts the first or third; its instrument cannot
> distinguish them from the second.

This is why O1 — the **absolute** per-band α, which nobody had fitted — was
made the observable behind K5, and why H5 was pre-registered as a live
hypothesis rather than a formality.

---

## 3. Instrument gates

### 3.1 K0 — the noise floor is derived from the null, not guessed

Every band in this report is `3 × sd(N_grad)`, the spread of E_trend under
shuffling the band labels of that same statistic. **The band is measured, not
chosen**, which is the repair for the failure mode my own three M72
pre-registration errors shared.

> **Fact 2 (MEASURED).** **K0 MET.** N_grad sd on the two signal ratios is
> 0.01281 (B/G2) and 0.01382 (R/G1), against a void threshold of 0.0220. The
> instrument resolves M68's own −0.0659 at better than 4σ.

### 3.2 A1 — the adversarial control, and why it was necessary

Discipline 496: a confirming control that fires in your favour is never
scrutinised. M68's G2/G1 control is exactly that, and it compares two planes
with **equal** α, while the signal ratios compare planes with α ratio 0.85. An
estimator bias that cancels at 1.00 and not at 0.85 would make the control flat
**by construction** and the signal sloped **by construction**.

> **Fact 3 (MEASURED).** **A1 MET, and it is not a vacuous pass.** Planting two
> planes at α ratio 0.85 with **no** gradient, quantised, over the real ISO set
> at the real per-band surviving count of 256,235 pixels, E_alpha returns mean
> 0.84984 and trend **+0.00018**, r = +0.043. Planting a **real** −0.0650
> gradient through the identical code path recovers **−0.0666**, r = −0.993.
> The estimator is unbiased at the ratio that matters *and* sensitive to the
> effect it is asked about.

### 3.3 A2 — planted against the bias that flatters

Discipline 497. H1 is flattered by anything that gives both statistics a common
row profile, and M68 §6 fact 24 found the per-row dark mean is U-shaped with hot
edges.

> **Fact 4 (MEASURED).** **A2 MET.** The per-band surviving fraction under
> E_defect k=6 runs 0.98519–0.99936 with a row trend of ≤ +0.00006 and
> |r| ≤ 0.005 on every plane — the defect layer has **no** row organisation to
> donate. Across arms none/k3/k6/k9 the α-ratio trend moves by at most 0.01742
> (band 0.0220), and the worst ρ trend movement is **0.25** of its own 3σ floor.

---

## 4. K1 — M68 §6 fact 21 reproduced

> **Fact 5 (MEASURED).** **K1 MET.** With M68's own estimator, 32 row bands,
> arm k6: R/G1 **−0.0716** against M68's −0.0659 (Δ −0.0057, r = −0.936); B/G2
> **−0.0663** against −0.0625 (Δ −0.0038, r = −0.931); the G2/G1 control
> **+0.0037** against +0.0028. M68 §6 fact 21 is independently reproduced and
> its numbers are sound.

The reproduction matters because everything in §5 leaves M68's numbers standing
and overturns only what they were said to mean.

---

## 5. K5 — which planes actually move

### 5.1 The inversion

> **Fact 6 (MEASURED).** **The greens carry the gradient; R and B do not.**
> Absolute α_high per plane, normalised to its own mean, 32 row bands, arm k6:
>
> | plane | α_high | normalised trend | r | 3×N_grad | moves? |
> | --- | --- | --- | --- | --- | --- |
> | R | 1.36610 | −0.00543 | −0.144 | 0.01946 | no |
> | G1 | 1.38220 | **+0.06777** | +0.850 | 0.04214 | **YES** |
> | G2 | 1.38089 | **+0.07151** | +0.862 | 0.04393 | **YES** |
> | B | 1.18612 | −0.00619 | −0.124 | 0.02661 | no |
>
> **K5's pre-registered branch "the greens move and R and B do not" fires, and
> its declared consequence is that M68's description of its own finding is
> inverted.** The green planes' input-referred read-noise power rises ~7% from
> the top of the sensor to the bottom. R and B are flat.

The ratio is not wrong; the attribution was. `R/G1 = −0.0716` is almost exactly
`−(G1's +0.0678)`, and `B/G2 = −0.0663` almost exactly `−(G2's +0.0715)`.

### 5.2 The mechanism cannot be the CFA, and that is the puzzle

R and G1 share rows; G2 and B share rows. R and G2 share columns; G1 and B share
columns. **R is flat while G1 rises, so it is not a shared row wire. R is flat
while G2 rises, so it is not a shared column wire.** The split that survives is
{R,B} on the `(row+col)` even sublattice against {G1,G2} on the odd one — the
CFA's own checkerboard, which in a dark frame is a per-photosite property and
not a bus.

### 5.3 The criterion that fired against me — K5 scoped

K5 was pre-registered on `alpha_high` because that is what M68 used and K1 had
to match it. `alpha_low` tells a different story, and I went looking for its
floor rather than let the pre-registered estimator flatter the headline.

> **Fact 7 (MEASURED).** **"R and B are flat" is TRUE of `alpha_high` and FALSE
> of `alpha_low`.** R **−0.0396** (r = −0.870, floor 0.02397) and B **−0.0419**
> (r = −0.831, floor 0.02656) both clear their floors in the low-gain mode,
> with the greens at +0.0808 and +0.0824. **The headline in §5.1 is therefore
> scoped to the high-gain mode**, and the general statement is that the greens
> carry a rise in *both* modes while R and B carry a fall in the *low* mode
> only.

The δ trends are opposite-signed to the α trends and split by the same
partition (+0.018 R, −0.030 G1, −0.037 G2, +0.014 B) — precisely the signature a
three-parameter fit degeneracy would leave. I did not want to assert that
`alpha_high` is the trustworthy one from the structure of the fit, so I removed
the fit.

### 5.4 The same result with no model at all

`06-modelfree.py` takes the **raw** per-band temporal variance at each ISO
separately, normalised to its own mean. No gain model, no dual-gain switch, no
δ, no Sheppard term.

> **Fact 8 (MEASURED).** **The green rise is present at 11 of 11 ISOs, above
> its own floor at every one, and is nearly ISO-independent:** G1 spans +0.055
> to +0.072 and G2 +0.043 to +0.073. **The R/B fall is present at 4 of 4 ISOs
> below the dual-gain boundary** (−0.029 to −0.042, all above floor) **and at 0
> of 7 ISOs at or above it** (−0.010 to +0.007, none above floor). The fit was
> not lying; §5.3's scoping is a property of the sensor.

> **Fact 9 (MEASURED).** **The R/B gradient steps at the dual-gain boundary and
> the green gradient does not.** Mean trend below/above ISO 400: R −0.0319 →
> −0.0031 (**step +0.0288**), B −0.0333 → −0.0043 (**step +0.0290**), G1 +0.0647
> → +0.0590 (−0.0057), G2 +0.0669 → +0.0619 (−0.0049). **A row-dependent effect
> that vanishes when the chip changes gain mode, and one that is indifferent to
> it, are not the same effect.** There are two gradients here, not one.

---

## 6. The answer to M75's question

### 6.1 K2 — the groupings

> **Fact 10 (MEASURED).** **K2: the partitions DIFFER.** The α arm selects
> **{R,B} | {G1,G2}** with separation +0.07171. The ρ arm does not: pooled
> correlations are G1–B **+0.05638**, G2–B **+0.05277**, G1–G2 **+0.04107**,
> R–G2 +0.01081, R–B **+0.00433**, R–G1 **−0.00067**. Scoring the α arm's
> partition under the ρ statistic gives **−0.0071** — worse than chance. The
> covariance isolates **R**; the gradient isolates the **greens**. The
> implicated sets are disjoint.

*Estimator limitation, stated:* my bipartition search considers only 2–2 splits,
and the ρ arm's real structure is the 1–3 split {R} | {G1,G2,B}, which it cannot
express. The conclusion is unaffected — {R,B} | {G1,G2} *was* available to the ρ
arm and scored below chance — but the reported "best" ρ partition
({G2,R} | {B,G1}, separation +0.00922) is an artefact of the forced 2–2 form and
should not be quoted as a finding.

### 6.2 K3 — the decisive gate, and K4 — the power to believe it

> **Fact 11 (MEASURED).** **K3: NEITHER limb met.** (a) The ρ(R–B) row trend is
> **−0.00036** (r = −0.322) against a 3σ floor of 0.00065 — not real. (b) The
> cross-statistic band correlation between ρ(R–B) and the mean of the R/G1 and
> B/G2 α profiles is **+0.3039**, against the required 0.70. Across the full
> 6 × 6 matrix, no cell reaches 0.70; the largest is R–G2 against R/G2 at
> **−0.646**.

> **Fact 12 (MEASURED).** **K4 MET, so the null is evidence and not fatigue.**
> The N_grad sd of the K3(b) band correlation is **0.1899**, giving 3σ = 0.5698,
> comfortably inside the 0.233 sd required to resolve 0.70 at 3σ. **H2 may be
> concluded.** This gate exists because H2 is the hypothesis that noise
> flatters, and without it a null here would be uninterpretable.

**The pre-registered branch "NEITHER MET and K4 satisfied → TWO PHENOMENA"
fires.**

---

## 7. Mechanism — located by where the noise is generated

Discipline 473, applied twice more.

### 7.1 F3 — multiplicative, not additive

An additive input-referred power (dark-current shot noise being the obvious
candidate, since `var_e = mean_e`) adds the **same e²** to `alpha_low` and
`alpha_high`. A multiplicative scale `s` multiplies both by `s²`, so it is equal
in **fraction**. `alpha_low ≈ 13 e²` and `alpha_high ≈ 1.4 e²` are a factor of
ten apart, so the two predictions are far apart.

> **Fact 13 (MEASURED).** **The green gradient is MULTIPLICATIVE.** G1: absolute
> ratio Δ(α_low)/Δ(α_high) = **11.60**, fractional ratio **1.19**. G2: **11.15**
> and **1.15**. The fractional form agrees within the floor and the absolute
> form fails it by an order of magnitude. **The gradient is a row-dependent
> per-plane analog scale — the same class of object as M68's B-plane 0.84×.**

### 7.2 F4 — dark current excluded directly

> **Fact 14 (MEASURED).** **It is not dark current, on two independent counts.**
> The mean dark signal rises in **all four** planes (Δ in electrons: R +0.0290,
> G1 +0.0425, G2 +0.0469, B +0.0253) while α rises in the greens only
> (+0.0937, +0.0987) and falls in R and B. And the dark-signal profile is
> **U-shaped** on every plane (r = +0.40 to +0.61 against band index), matching
> M68 §6 fact 24's edge-thermal signature, whereas the green α profile is
> **monotone** — 0.988 → 1.053 top to bottom for G1.

### 7.3 F2 — the two phenomena sit on different axes

> **Fact 15 (MEASURED).** **The gradient is row-organised and the covariance is
> column-organised.** Each trend divided by its own N_grad floor:
>
> | statistic | row/floor | col/floor | organised by |
> | --- | --- | --- | --- |
> | α_G1 | 4.5 | 1.5 | **row** |
> | α_G2 | 4.8 | 1.4 | **row** |
> | α_R | 0.8 | 0.5 | neither |
> | α_B | 0.7 | 0.1 | neither |
> | ρ(G1–G2) | 1.3 | **5.2** | **column** |
> | ρ(R–G1) | 2.0 | **5.2** | **column** |
> | ρ(R–B) | 1.6 | **4.3** | **column** |
> | ρ(R–G2) | 3.3 | 5.7 | both |
>
> ρ(G1–G2) varies by **+0.0224 across the sensor width** (r = +0.942, floor
> 0.01281, permutation null −0.00168) — more than half its own pooled value of
> +0.041 — while its row trend is inside the floor. **This is a second
> separator, independent of K3, and it is a positive statement rather than a
> null.**

> **Fact 16 (ARGUED).** **This independently supports M50 §5's argued
> mechanism, from a different statistic.** M50 argued — explicitly *not*
> measured — that "a column-parallel readout with shared per-column ADCs would
> impose more correlation along a row than down a column", from a **spatial**
> fixed-pattern statistic. M75 finds the **temporal** inter-plane covariance's
> strength varies with column index and not with row index, which is what
> per-column shared circuitry produces. The two are different observables
> pointing the same way. I claim no priority here and it remains ARGUED: a
> column-organised statistic is evidence of column-organised *circuitry*, not
> proof of which circuit.

### 7.4 F5 — where the covariance lives in ISO

> **Fact 17 (MEASURED).** The upstream share of the inter-plane covariance
> climbs from **0.025–0.086 at ISO 50** to **0.910–0.974 at ISO 2000** on all
> six pairs alike. This reconciles M72's 0.58–0.97 range, which was quoted at
> mixed ISOs, and shows the split is a property of where each ISO sits on the
> `α·G² + δ` curve rather than a per-pair property.

---

## 8. What this says about M68's still-open B-plane question

The orchestrator asked whether this bears on `alpha_B/alpha_G2 = 0.85235 ±
0.00316`, ruled neither conversion gain nor analog attenuation and located only
as "partway along the analog chain". It does, in three ways.

> **Fact 18 (MEASURED).** **An independent pipeline agrees with M68 within *my*
> error bar and not within M68's.** M75 measures α_high B/G2 = **0.85894 ±
> 0.01069** (jackknife over the ISO set) against M68's 0.85235 ± 0.00316. The
> difference of +0.00659 is **0.62 of my σ and 2.1 of M68's**. The central
> values agree; **at least one of the two quoted uncertainties is understated**,
> and mine is the larger. This is offered to M71 as a caution on the precision
> of any B-plane ratio, not as a correction to the value.

> **Fact 19 (MEASURED, NULL).** **This measurement does not detect a gain-mode
> dependence in the B scale, and does not exclude one below ~3%.** A single
> multiplicative pre-ADC scale predicts the *same* ratio `s²` in both modes.
> Measured: α_low B/G2 = **0.84565 ± 0.02582**, α_high = **0.85894 ± 0.01069**,
> a difference of **−1.55%** against a combined error of **3.30%** — **0.48σ.**
> I report this as **not significant** rather than as support for the
> mode-dependence it superficially suggests.

> **Fact 20 (ARGUED).** **The per-plane analog scale is demonstrably not
> constant across the array, and that is the constructive contribution.** Fact
> 13 establishes a row-dependent per-plane multiplicative scale of ~7% in α
> (~3.4% in amplitude) on the green planes, in the same frames and the same
> analog domain as the B-plane 0.84×. **M68 §5 gate D1's failure and its "0 of
> 32 row bands" are therefore expected rather than anomalous**: a search for a
> single well-defined position `f` was looking for a constant that the sensor
> does not have. This does not name the B mechanism. It removes the assumption
> whose failure M68 recorded and could not explain.

Also consistent, and unchanged: δ_B/δ_green = **0.587** here against M72 §9
fact 32's 0.5966, and R's δ = 0.31077 sits with the greens' 0.31453 and 0.30660.
**B is anomalous in both α and δ; R is anomalous in neither.**

---

## 9. What the model should say — described, not applied

`crates/` is off-limits this milestone (M73 and M74 are live in it) and I have
changed nothing. **My recommendation is to change nothing here either**, for a
reason that is measured rather than deferential.

> **Fact 21 (MEASURED).** **The regime, not just the magnitude.** A single
> per-plane read-noise figure mis-states the green planes' σ by **±1.7%**
> (α varies ±3.4% about its mean; σ is the square root), and the error **flips
> sign at mid-frame** — conservative in the top half, over-confident in the
> bottom half. On R and B the same figure is correct to ≤0.6% in the high-gain
> mode and mis-states by ∓2% in the low-gain mode, also sign-flipping.

That is a materially different object from my own M72 finding, which was 4.0% in
σ and **never** flipped sign, and from the B-plane 0.84×, which is ~8% in σ and
uniform. A sign-flipping ±1.7% cannot be repaired by any per-plane scalar,
because a scalar has nowhere to put the sign change; it needs a spatial term
`profile.rs` does not have. Against M69's finding that `FOCUS_NOISE_SD` is
right to a median **1.0147×**, ±1.7% is not the binding error anywhere in this
pipeline.

**Recommended: record it, do not patch it.** Adding a green-only spatial term
while B's uniform 8% remains unmodelled would be the same trap as M68 §7.1's
retracted partial fix — a local patch to a general defect, converting a visible
error into an invisible one.

---

## 10. Error log

1. **My K5 verdict string overstated its own scope.** It printed "the GREENS
   move, R and B do not" without naming the estimator, when the pre-registration
   had bound K5 to `alpha_high` specifically. Facts 7 and 8 scope it. **This is
   the same failure the orchestrator named after M72 — state the regime, not
   only the number — committed again in the very milestone whose design caution
   was "state the estimator next to the band".** I stated it next to the *band*
   and not next to the *verdict*.
2. **My K2 bipartition search can only express 2–2 splits** and the ρ arm's
   structure is 1–3. Disclosed inline in §6.1; the reported "best" ρ partition
   is an artefact of the search space and I have said so rather than quoting it.
3. **`02-band-sweep.py` stores `mean_dn` as a masked sum, not a mean.** Harmless
   — `04-mechanism.py` divides by the co-stored `n` — but the field name is
   wrong and would mislead anyone reading the JSON directly.
4. **I nearly asserted that `alpha_high` was the trustworthy estimator from the
   structure of the fit** (δ/α degeneracy at low ISO) rather than measuring it.
   §5.4 exists because that reasoning would have been an argument standing in
   for a measurement, and it would have reached the right answer for a reason I
   had not checked.

---

## 11. Verdict, and what remains unsettled

**Answered.** M68 §6 fact 21's gradient and M72's R decoupling are **two
phenomena**, on disjoint plane sets ({G1,G2} against {R}), on different sensor
axes (row against column), with no shared spatial signature (K3 both limbs
failed at adequate power). SYNTHESIS fact 995's unallocated artefact is now
allocated: it is a **row-dependent multiplicative scale on the green planes**,
not a chroma drift.

**Also answered, and not asked.** There are **two** gradients, not one: the
green one is indifferent to the dual-gain switch, and a second R/B one exists
only below it (facts 8, 9).

**Unsettled, precisely.**

- **What circuit produces a monotone, row-organised, multiplicative scale on the
  CFA's odd sublattice only.** Fact 6's elimination rules out a shared row bus
  and a shared column bus, F4 rules out dark current, and A2 rules out the
  defect layer. I can bound it and cannot name it. Dark frames alone may not be
  able to: a mechanism needing photocurrent to express is invisible here.
- **Why the R/B gradient disappears above the dual-gain boundary.** Fact 9
  measures the step; nothing here explains it.
- **The B-plane mechanism.** Fact 20 removes an assumption; it does not answer
  M68's question. Fact 19 is a null with a ~3% detection limit, not a result.
- **Whether ρ's column organisation is the per-column ADC bank.** Fact 16 is
  ARGUED and shares M50's evidentiary status, not better.
- **Whether the +0.09133 within-plane R correlation of M72 relates to any of
  this.** Out of scope here; still open.

---

## 12. Reproduction

```powershell
$env:PYTHONIOENCODING='utf-8'
cd experiments\M75-rb-asymmetry
python src\01-preregistration.py   # planted self-tests; reads no dark frame
python src\02-band-sweep.py        # 11 groups -> data/02-band-sweep.json (~4 min)
python src\03-criteria.py          # K0-K5, A1-A2, the pre-registered verdicts
python src\04-mechanism.py         # F1-F5, post-hoc mechanism work
python src\05-checks.py            # G1-G3, scoping and the M68 cross-check
python src\06-modelfree.py         # H1-H3, the same result with no fit
```

Scripts 01–06 were each committed **before** being run: `34a3d39`, `1623502`,
`4268a57` (written while the sweep was still in flight), `a755c29`, `1e0bd9c`,
`44ecea3`.

`02-band-sweep.py` computes per-cell temporal second moments **once** and masks
them per arm, so the four exclusion arms are the same measurement differently
masked — which is what A2 requires to mean anything.

M75 imports `load_group`, `split_plane`, `defect_flags`, `derangement`,
`rho_from`, `fit_alpha_delta`, `gain` and `mode` from
`experiments/M72-green-correlation/src/` by explicit path rather than
re-implementing them. That is deliberate: reusing the instrument M72 validated
makes the cross-milestone comparison exact, and it is disclosed here because it
means M75 inherits any defect in those helpers.
