# M68 — the B plane's 0.84×: conversion gain, or attenuation?

Status: MEASURED (with two post-hoc gates NOT MET and their consequences honoured)
Scope: `experiments/M68-b-plane-mechanism/`, 220 dark frames from `D:\macro-dark-frames`
Predecessor: M61 §4.12, questions 10 and 11

---

## Headline

**Neither.** The commissioned binary is refused, and it is refused by a
pre-registered criterion that fired on its own terms.

The blue plane's ISO-scaling dark-noise power is **0.85235 ± 0.00316** of the
same-parity green's. A sense-node conversion-gain difference predicts
**1.000**. An analog attenuation sitting ahead of the read noise predicts
**s² = 0.705**. The measurement is 46σ from the first and 47σ from the second,
and it is not near either in any of 32 row bands taken separately.

What the number says instead is that the 0.84× acts **partway along the analog
read chain**, with a substantial fraction of the ISO-scaling dark noise
generated on each side of it — and that a scale applied *at or after the ADC*,
whether analog or digital, is excluded along with a scale applied at the
charge-to-voltage conversion.

The practical consequence for `profile.rs` is sharper than the mechanism
question: **blue's signal conversion and blue's dark noise do not scale by the
same factor**, so the defect cannot be repaired with one number.
The gain is 0.8396× green's; the dark σ is 0.9231× green's.
**A "fix" that scales only `gain_dn_per_e` by 0.84 would be as wrong as today's
model and wrong in the over-confident direction** (−9.0% against +8.3%).

---

## 0. Prior work read (rule 40)

Searched `docs/research/*.md` for `conversion gain` (5 hits), `photon
transfer|PTC` (15), `per-plane|per plane` (14), `dark[- ]frame|dark sigma|dark-σ`
(35), `B plane|B-plane|blue plane` (5), and `vertical gradient|top-to-bottom|row
band` (5).

| File | Read | What it settled that I did not redo |
| --- | --- | --- |
| `M61-ptc-high-iso-measured.md` | in full | The PTC, M61 fact 22 (B/green = 0.8396 ± 0.0112), M61 facts 50–58 (pre-quantisation, three ways), M61 fact 51 (QE cannot do it), the refutation of M48c's 2.174× step, M61 questions 10–11 |
| `M48c-defect-layer-measured.md` | §1–3 | The defect census, criterion B, the row-parity asymmetry (M48c fact 9), M48c discipline 1 (do not move a threshold with ISO) |
| `M4-fpn-measured.md` | §1, §2, §5, §8 | The folder→ISO map, the 11-ISO × 4-plane dark-σ table (my gate C0), §8.2 (ISO 50 is a pull setting at base gain) |
| `crates/strehl-core/src/profile.rs` | in full, **not modified** | `A7C2`, `gain_dn_per_e`, `read_noise_e_low/high`, `DARK_SIGMA_RMS_DN`, and `noise_model()`'s `[p; 4]` |
| `M48-read-noise-measured.md`, `M48b-fpn-rho-measured.md`, `M16`, `M50`, `M22` | grepped, headline claims only | Nothing in the corpus previously reports a spatial gradient in a *sensor read-noise* plane ratio; M16/M50's "vertical gradient" is image-domain texture energy, a different thing |
| `AGENTS.md` | rules 7, 32, 40, 41, 42 | Visible geometry, the rawpy buffer-view hazard, path-scoped commits |

M62's and M65's precedent on voiding one's own headline was followed as
described in §5 and §6.

---

## 1. The derivation, done before any measurement

Committed in `src/00-derivation.py` at `71cd54c`, together with a planted
signal-chain simulation that reproduces it.

The chain injects noise at three points in three different units:

```
electrons (+n_e) --[q/C]--> volts at the source follower (+n_V)
                 --[A(ISO)]--> --[c DN/V]--> DN (+n_D) --> quantise
```

so dark-frame variance in DN separates into a part that scales with the
programmable gain and a part that does not:

> **Fact 1 (DERIVED).** `σ²(ISO) = α·G² + δ`, with `G = max(ISO, base_iso)`,
> α carrying everything generated upstream of the programmable gain and δ
> everything downstream of it (ADC noise plus the 1/12 DN² quantisation floor).
> **The discriminating statistic is the α ratio, not the σ ratio**, because δ
> contaminates the σ ratio differently at every ISO. This is why the sweep fits
> two terms rather than reading a ladder.

A per-plane scale `s` multiplies every noise term generated **upstream of it**
and none generated downstream. Five candidate positions:

| | mechanism | α_B/α_G | δ_B/δ_G | dark-σ ratio vs ISO |
| --- | --- | --- | --- | --- |
| P1 | charge-domain conversion gain (sense-node C) | **1.00** | 1.00 | flat at 1.00 |
| P2 | analog scale after the source follower, before the ADC | s² = 0.705 | 1.00 | falls 1.00 → 0.84 |
| P3 | P2 with δ → 0 | 0.705 | — | flat at 0.84 |
| P4 | post-ADC digital (already refuted by M61) | 0.705 | **≈ 2.8** | 0.99 → 0.85 |
| P5 | mean-preserving charge sharing | **1.00** | 1.00 | flat at 1.00 |

### Where I disagreed with M61, before measuring

> **Fact 2 (DERIVED).** **M61's question 10 forecast is half wrong, and the
> wrong half is the one that matters.** M61 states that a *sensor conversion
> gain* pins the dark-σ ratio "at 0.84 and flat". That holds only if the read
> noise is generated **upstream** of the charge-to-voltage conversion. The
> dominant CMOS read-noise term is source-follower **voltage** noise, which sits
> downstream of `q/C`; a sense-node capacitance difference therefore leaves the
> dark-σ ratio at **1.00, not 0.84**. The planted simulation confirms it:
> `where="charge"` returns an α ratio of 0.9977 and a flat σ ratio of 1.00.

> **Fact 3 (DERIVED).** M61's *other* branch is right. An analog attenuation
> ahead of the read noise gives α ratio s² and a σ ratio that **falls** with
> ISO toward s: the plant returns α 0.7047 and σ 0.8688 → 0.8409 over the sweep.
> So the observable does separate the hypotheses — but the two arms are
> **1.00 and 0.84**, not M61's **0.84 and falling-to-0.84**.

This mattered. Had I taken M61's forecast on trust, a measured null would have
been read as "analog attenuation, refuted" when it in fact means "conversion
gain, confirmed". The sign of the whole experiment was inverted.

### A fifth candidate M61 did not enumerate

> **Fact 4 (DERIVED).** **Lateral charge sharing (P5) reproduces the PTC ratio
> without any gain difference and M61 did not consider it.** If a fraction `b`
> of each pixel's photo-charge is redistributed to its four neighbours and
> received back symmetrically, the mean is conserved but
> `var/mean = (1−b)² + b²/4`. Solving for 0.84 gives **b = 0.0844** (numerically
> 0.8401). This is **not** the QE hypothesis M61 correctly killed — QE leaves
> `var/mean` alone, sharing does not. It is wavelength-dependent (blue absorbs
> shallowest), it passes the code-occupancy comb test, and it lets B reach
> 16383 because the mean is untouched. **In darkness it predicts an exact null,
> identical to P1.**

> **Fact 5 (DERIVED).** The observable therefore separates **{P1, P5}**
> (α ratio 1.00) from **{P2, P3, P4}** (α ratio 0.705) with no overlap and no
> choice of δ that moves either side, but it **cannot separate P1 from P5**.
> That residue was declared in the pre-registration as an unconditional
> limitation, before the result was known. As it turned out (§4) both are
> excluded together, so the residue never became binding.

---

## 2. Pre-registration

`src/01-dark-iso-sweep.py`'s module docstring, committed at **`71cd54c`**
together with `00-derivation.py`, its self-test output and nothing else — five
files, audited with `git show --name-only` — **before the corpus was touched**.
`02-criteria.py`, which classifies the result, was committed separately at
**`e960da9`** while the sweep was still decoding, so the classifier cannot have
been tuned to the answer.

**Hypotheses**: P1–P5 above. **Observable**: the per-plane α ratio from
`σ² = αG² + δ` fitted over **11 ISOs, 50–2000**, primary comparison **B vs G2**
(same row parity), secondary **B vs pooled green** (what a `profile.rs`
correction is phrased in). **Exclusions**: the owner's first two stabilisation
frames per folder (T = 20); `raw_image_visible` only; M48c criterion B unchanged
(excess against the median of 4 same-plane neighbours, `σ_rob = 1.4826·MAD`,
flag |excess| > 6σ_rob), recurrence ≥ 6 of 11 ISOs, that **fixed** set then
excluded at every ISO; one-pixel border dropped.

**Criteria, with their consequences fixed in advance:**

| | test | consequence if not met |
| --- | --- | --- |
| C0 | rawpy reproduces M4 §8.1's 44 cells to 0.5% | **the milestone stops** |
| C1 | control: G2/G1 α ratio within 0.10 of 1, σ-ratio excursion ≤ 0.03 | the B result is uninterpretable and I say so |
| C2 | split-half null on disjoint 10-frame halves of the *same* plane | (a) headline void; (b) decline to split P2 from P3 |
| C3 | α_B/α_G in 1.000 ± 0.05 ⇒ {P1,P5}; in 0.705 ± 0.05 ⇒ {P2,P3,P4}; **else NEITHER** | report the number and **refuse the binary** |
| C4 | declares in advance the four ways the observable could fail to separate | report them |

The pre-registration states the mechanism and the observable and **never the
expected sign**, as required; §1's derivation is stated as an algebraic
prediction attached to each named position, not as a direction to confirm.

> **Fact 6 (ARGUED).** **Non-blindness disclosure, made in the pre-registration
> before the run.** M4 §8.1's table *is* my observable's numerator and
> denominator, and rule 40 required reading it. While designing the fit I did a
> two-point (ISO 400/2000) solve on M4's published green and B rows. It returned
> **α ratio ≈ 0.86, δ ratio ≈ 0.59 — cleanly inside neither hypothesis band**,
> and it established that δ ≈ 0.25 DN² is large enough to resolve (≈ 15% of the
> ISO-400 variance), which is why the α/δ decomposition rather than a raw σ
> ladder is the primary estimator. Recording that in advance is what stops
> §4's NEITHER verdict from reading as a discovery and stops either other branch
> from reading as motivated. **What was genuinely blind**: the effect of defect
> exclusion (60× heavier on B/G2 than on R/G1), the 11-point shared-δ fit, the
> split-half null, and the G1/G2 control.

---

## 3. The instrument

11 folders × 22 ARW, first two dropped, **220 frames decoded**. The folder→ISO
map was rediscovered from EXIF and matches M4 §1 exactly. Visible geometry
(4688, 7028); per plane (2344, 3514) = 8,236,816 px. CFA asserted at run time as
`raw_pattern [[0,1],[3,2]]`, `color_desc RGBG` → R G1 / G2 B, so **R and G1 sit
on even sensor rows, G2 and B on odd**, and **B shares rows with G2 and columns
with G1**.

> **Fact 7 (MEASURED).** **C0 MET.** rawpy/LibRaw reproduces M4's rawler numbers
> in **44/44 cells**, worst disagreement **0.027%** at (ISO 400, B), against a
> 0.5% band. A cross-implementation loader agreement of that quality, on a
> statistic computed by two different pipelines, retires any residual decoder
> doubt about the dark table.

> **Fact 8 (MEASURED).** The recurrent-defect census independently reproduces
> M48c fact 9's row-parity asymmetry: at recurrence ≥ 6 of 11 ISOs,
> **R 630, G1 660, G2 7,695, B 6,154** (M48c: 101, 98, 7,757, 5,674). The odd
> rows carry an order of magnitude more recurrent defects than the even rows on
> a fresh decode by a different loader. My R/G1 counts are 6× M48c's — a
> threshold-detail difference, not a structural one — and the asymmetry that
> motivated splitting B against **same-parity** G2 stands.

---

## 4. The pre-registered result

### The control, first

> **Fact 9 (MEASURED).** **C1 MET. The control did not move.** G2 against G1:
> α ratio **0.99937 ± 0.00511** (band ±0.10), and the σ ratio over all 11 ISOs
> ranges 0.99753 → 1.00222, an **excursion of 0.00469** against a 0.03 band.
> The two green planes, read out on opposite row parities through what M48c
> argues are different readout chains, agree on their dark noise to five parts
> in ten thousand. **The instrument shows no spurious trend, so the blue result
> is interpretable.**

> **Fact 10 (MEASURED).** **C2 MET, all four arms.** Disjoint 10-frame halves of
> the *same* plane return unity: G1 α 0.99960, δ 1.01103; B α 1.00166,
> δ 0.97067 (bands ±0.05 and ±0.35). The fit does not manufacture a ratio out of
> frame-count or ordering.

> **Fact 11 (MEASURED).** A free replicate: ISO 50 is a pull setting reading out
> at base analog gain (M4 §8.2), so ISO 50 and ISO 100 share an abscissa.
> Their σ ratios are **R 1.00307, G1 1.00116, G2 1.00150, B 1.00282** — two
> independent 20-frame captures at the same gain agree to **≤ 0.31%**. That
> bounds session-level repeatability of the whole instrument.

### The headline number

> **Fact 12 (MEASURED).** **α_B/α_G2 = 0.85235 ± 0.00316** (jackknife over the
> 11 ISO groups), and **α_B/α_Gpool = 0.85208 ± 0.00126**. In σ this is an
> asymptote of **0.92308**. The per-ISO dark-σ ratio B/G2 does not fall and is
> not flat — it **rises**, 0.91071 at ISO 50 to 0.92273 at ISO 2000, because
> δ_B/δ_G2 = 0.595 is smaller than the α ratio and pulls the low-ISO end down.
> Neither behaviour appears in the hypothesis table of §1.

> **Fact 13 (MEASURED).** **C3 NOT MET in either direction: NEITHER BAND.**
> 0.85235 is 0.148 above the {P2,P3,P4} band centre and 0.148 below the
> {P1,P5} band centre — almost exactly midway, and **46σ / 47σ from the two
> predictions**. The pre-registered consequence was "report the number and
> refuse the binary", and this report does that. **The question as
> commissioned — conversion gain or analog attenuation — has no correct answer.**

> **Fact 14 (MEASURED).** **δ_B/δ_G2 = 0.59528 ± 0.09280**, with
> δ_G2 = 0.25305 DN² resolved at 3.1× its jackknife sd (C4(d) satisfied).
> **This independently corroborates M61's refutation of P4** by a route M61 did
> not use: a post-ADC digital scale re-quantising a 14-bit integer by 0.84 is a
> deterministic sawtooth, not additive dither, and the plant in
> `00-derivation.py` returns δ_B/δ_G ≈ **2.78** for it. Measured 0.595 is on the
> opposite side of unity. P4 is dead twice over.

> **Fact 15 (MEASURED).** **The effect is not readout geometry.** A per-row-parity
> scale would put 0.705 on G2/G1 (measured **0.9994**) and on B/R (measured
> **0.8619**). A per-column-parity scale would put 1/0.705 = 1.419 on R/G1
> (measured **0.9883**). All four are excluded. The 0.84× tracks the **colour
> filter**, not a readout-electronics parity.

---

## 5. Post-hoc: where does it act? — and the gate that stopped me

C3's third branch is a refusal, not an answer, so `03-where-is-the-scale.py`
asked the follow-up. It was committed at **`9116d5a`** *before it ran*, with
three failable checks and their consequences declared. It is labelled
**post-hoc throughout**; nothing in it is confirmatory.

Both pre-registered endpoints are special cases of one family. Let the 0.84 act
at a point X, and let `f` be the fraction of the ISO-scaling dark variance
generated upstream of X:

> **Fact 16 (DERIVED).** `α_B/α_G = f·s² + (1−f)`, so `f = (1 − α_B/α_G)/(1 − s²)`.
> **f = 1 is P2** (attenuation ahead of all the read noise); **f = 0 is P1 and
> equally P5**. The measured ratio inverts to **f = 0.500 ± 0.042** (0.028 from
> the α jackknife, 0.032 propagated from M61's ±0.0112 on s). Half the
> ISO-scaling dark-noise power on each side of the scale point.

Two of the three checks passed:

> **Fact 17 (MEASURED).** **D2 clear.** Per-plane dark level, median of the
> temporal-mean map: R 512.136, G1 512.127, G2 512.146, **B 512.200** DN.
> |mean_B − mean_G2| = **0.055 DN** against a 1.0 DN flag. A black-level error
> large enough to bias `var/mean` by 16% would need to be hundreds of DN, so
> **M61's 0.8396 is not a pedestal artefact.**

> **Fact 18 (MEASURED).** **D3 clear, with a caveat worth recording.** B's
> residuals are not single-signed inside a gain mode (low 2/4 positive, high 4/7).
> But B's worst residual is **+8.97%** against the greens' 1.8–2.1%, and it sits
> at **ISO 50 and ISO 100** — where *every* plane is high (R +3.61/+2.98,
> G1 +1.86/+1.62, G2 +2.08/+1.78). The two-term model under-predicts the base-ISO
> variance for all four planes; B strains hardest because its δ is smallest. This
> is why `alpha_high` (ISO ≥ 400, seven points) was pre-registered as the
> estimator rather than a joint α.

The third did not:

> **Fact 19 (MEASURED).** **D1 NOT MET.** Fitting α independently on a 4×4 block
> grid, the B/G2 ratio ran **0.8845 … 0.8248**, spread **0.0597** against a
> declared 0.05 threshold, while the G2/G1 control on the same grid was flat at
> spread **0.0139**. **The 0.84× is not a uniform per-plane scale.** Row-band
> means fell monotonically top to bottom — 0.876, 0.858, 0.844, 0.833 — while
> left/right barely moved (0.8559 against 0.8496).

> **Fact 20 (ARGUED).** **The pre-registered consequence of D1 is honoured:
> the position claim is withdrawn.** `f = 0.500 ± 0.042` is **not** reported as a
> point estimate of where the scale sits. It is a whole-array average of a
> quantity that demonstrably varies across the array, and the coincidence with
> exactly one half is not evidence of anything. What survives is the interval:
> over the array f runs **0.37 to 0.62**, never approaching 0 or 1.

---

## 6. The gradient, and a self-correction inside one step

`04-gradient.py`, committed at **`2bbca22`** before running, set out to
characterise what D1 found. Its gate E1 required that a control's row profile
not have more than half the signal's spread.

> **Fact 21 (MEASURED).** **E1 NOT MET, and the failure is the finding.** Over
> 32 row bands the spreads are **B/G2 0.0737, B/G1 0.0736, G2/G1 0.0338,
> R/G1 0.0729**. The control R/G1 moves **as much as B/G2 does**, and moves the
> same way: linear trend over the full sensor height **−0.0659, r = −0.911** for
> R/G1 against **−0.0625, r = −0.896** for B/G2. The green-against-green control
> is flat: **+0.0028, r = +0.082**.

> **Fact 22 (ARGUED).** **I withdraw the B-specific gradient claim, as E1's
> declared consequence requires** — and I record that my reading of D1 one step
> earlier was wrong. D1 found a gradient in B/G2 and I took it for a B-plane
> property. It is not. **Both chroma planes drift by the same ~6.5% in α against
> green from the top of the sensor to the bottom, and the two greens track each
> other perfectly.** In Bayer terms R and B share the `(row+col) even`
> checkerboard sublattice and the greens share the other. The gradient is a
> property of that split, not of blue. Its mechanism is **entirely open**; I have
> not measured it and will not guess at it here.

The gradient is nonetheless real, not an artefact of my exclusions:

> **Fact 23 (MEASURED).** **E4: arm-independent.** Top-half minus bottom-half in
> B/G2 is **−0.0293 / −0.0300 / −0.0301 / −0.0295** under exclusion arms
> none / r3 / r6 / r9, while the G2/G1 control's is **+0.0004 / −0.0015 /
> +0.0005 / +0.0006**. Removing between zero and 1,653 recurrent defects per
> plane changes the gradient by 3%.

> **Fact 24 (MEASURED).** **E3 clear: it is not glow.** The per-row-band dark
> mean spans 0.105–0.120 DN and is strongly **U-shaped** — 0.236 DN at the top
> edge, 0.159 in the middle, 0.241 at the bottom (G2). That is a real
> edge-thermal/glow signature and it is worth someone's attention. But the B/G2
> ratio is **monotone**, not U-shaped: Pearson r against the band mean is
> **−0.250 (G2) and −0.071 (B)**, far below the declared 0.7. The two structures
> are unrelated.

> **Fact 25 (MEASURED).** **E2: the column direction is consistent with noise.**
> B/G2 spreads 0.0398 across 32 column bands against the G2/G1 control's 0.0418.
> The control is *larger*. There is no column-direction effect.

And the load-bearing question — does the gradient rescue either hypothesis?

> **Fact 26 (MEASURED).** **E5 MET: the NEITHER verdict survives.** Across 32 row
> bands the B/G2 α ratio spans **0.8181 … 0.8918**. Bands falling inside the
> {P1,P5} band 1.000 ± 0.05: **0 of 32**. Bands inside the {P2,P3,P4} band
> 0.705 ± 0.05: **0 of 32**. **C3's refusal of the binary does not depend on the
> uniformity assumption that D1 refuted.** Not one strip of this sensor behaves
> like a conversion-gain difference, and not one behaves like an attenuation
> ahead of the read noise.

---

## 7. What the corrected model should say — *described, not changed*

`crates/strehl-core/src/profile.rs` is **unmodified**. `noise_model()` builds one
`PlaneNoise { gain_dn_per_e, read_noise_e, levels }` and hands the same one to
all four planes via `NoiseModel::new([p; 4], …)`. That structure has exactly the
two knobs this result needs, and the result is that **they must move by
different factors.**

> **Fact 27 (DERIVED).** For the B plane, against pooled green:
> `gain_dn_per_e` × **0.8396** (M61 fact 22, signal domain) and
> `read_noise_e` × **1.09943** (= 0.92308 / 0.8396). **Blue's read noise in
> electrons is ~10% higher than green's**, which is not a second defect but the
> arithmetic consequence of the first: the same DN-domain noise divided by a
> smaller conversion gain is more electrons.
> For the R plane: gain × 0.985, `read_noise_e` × **1.00945** — a 0.9% effect,
> below the spatial residual in fact 29, and probably not worth carrying.

> **Fact 28 (DERIVED).** **The obvious repair is not a repair.** Predicted dark σ
> against truth for the B plane:
> – shipped model (both knobs at 1.0): **+8.3%**, over-stating blue's noise, the
>   conservative direction;
> – "scale the gain by 0.84 and leave read noise alone": **−9.0%**,
>   **under-stating** blue's noise, the over-confident direction.
> The naive fix trades an 8% conservative error for a 9% over-confident one.
> Every gate, weight and threshold denominated in this model would become
> *less* safe on blue than it is today. **If only one knob is going to move,
> moving it is worse than moving neither.**

> **Fact 29 (MEASURED).** A single per-plane constant leaves a spatial residual.
> From the 32 row bands, B's dark-σ ratio to same-parity green runs
> **0.9045 … 0.9444** about 0.9232, i.e. **−2.0% to +2.3%** across the sensor
> height; R's runs **−1.8% to +1.9%**. That residual is a quarter of the error
> the constant removes, so the constant is still worth having — but it is a
> floor on how well any per-plane scalar can do, and it should be stated
> wherever the constant is.

> **Fact 30 (ARGUED).** **The orchestrator's standing ruling — carry the 0.84×
> as a measured per-plane scale of unknown origin rather than a conversion
> gain — is upheld and should be tightened.** It is now measured, not merely
> assumed, that the two behave differently when ISO changes, and the measurement
> excludes the conversion-gain reading outright. But the ruling's phrasing still
> understates the problem: **the model does not need one per-plane scale of
> unknown origin, it needs two different per-plane numbers**, one for signal and
> one for noise, because 0.8396 and 0.9231 are separately measured and are not
> the same quantity. Routing that is the orchestrator's call, not mine.

---

## 8. What this does not settle

> **Fact 31 (ARGUED).** **Where in the analog chain, precisely.** The result
> excludes the two ends and D1 then showed there is not a single well-defined
> point to name. The interval f ∈ [0.37, 0.62] is a description of the array,
> not a location. Localising it further needs an observable I did not run: a
> decomposition of the temporal dark noise into row-common, column-common and
> pixel-independent parts, which would say whether the un-scaled half is
> column-chain noise. That is one fresh decode of the same 220 frames.

> **Fact 32 (ARGUED).** **Analog attenuation versus an in-camera digital
> pre-ADC scale — settled in one direction only, and this is the answer to the
> second half of the commissioned question.** Any scale applied *at or after* the
> ADC is at the very end of the chain and therefore predicts **f = 1**, i.e. an
> α ratio of 0.705. That is excluded at 47σ, in every row band. It is excluded
> whether the scale is analog, or digital on a 14-bit output (M61's comb test,
> plus fact 14's δ ratio), **or digital on a wider internal ADC path where no
> comb would appear** — a loophole M61's evidence leaves open and this one
> closes, because the loophole does not change the position and the position is
> what is measured. What I **cannot** say is whether the mechanism inside the
> analog chain is a deliberate per-channel trim register or a physical asymmetry
> in the column path. This observable does not distinguish intent from physics.

> **Fact 33 (ARGUED).** **Whether the PTC's 0.84 and the dark 0.852 are one
> effect at all.** §5's f-inversion assumes a single linear scale acting on both
> signal and noise. If instead there are two independent differences — a
> signal-path scale of 0.8396 and an unrelated dark-noise reduction to 0.923 —
> every number in fact 27 stands unchanged (they are separately measured) but
> fact 16's f becomes meaningless. **Nothing measured here distinguishes the two
> readings**, and the `profile.rs` recommendation deliberately does not depend
> on which is true.

> **Fact 34 (ARGUED).** **The gradient's mechanism, entirely.** Fact 22 reports a
> ~6.5% top-to-bottom drift in both chroma planes against green, robust to
> exclusion arm, uncorrelated with the dark level, absent in the column
> direction and absent between the two greens. I have measured that it exists
> and that it is not any of the things I could cheaply rule out. I have no
> mechanism for it and I decline to offer one.

> **Fact 35 (ARGUED).** **Generality.** One body, one session, 220 frames,
> 1/100 s throughout. Fact 11 bounds *within-session* repeatability at 0.31%.
> Nothing here says the 0.84× or the gradient is stable across bodies,
> temperatures or firmware. `profile.rs` is a per-model profile, so that
> distinction matters to it.

> **Fact 36 (ARGUED).** **The secondary task was not attempted.** M61's
> ρ(G1,G2) = +0.073 and the resulting `var(mean) = 0.5365σ²` are untouched. The
> brief conditioned it on the headline being "finished and clean"; two declared
> gates were not met and their consequences reshaped the report, so the budget
> went to §6 and §7 instead. M61 fact 60's discriminating design — ρ computed for
> same-column against different-column pairings — remains the right next step and
> the 220-frame decode it needs is 3 minutes.

---

## 9. Errors, and what caught them

> **Fact 37 (ARGUED).** Four self-corrections, all recorded in committed code
> before the corpus was touched or in the step that followed:
> 1. `00-derivation.py` v1 used unphysical constants (electron-domain noise 136×
>    the source-follower term) and returned the wrong answer for **both** P1 and
>    P4. Fixed by pinning the constants to a two-point solve of M4's published
>    green rows. **The plant caught a derivation error that the algebra alone
>    would not have.**
> 2. v2's analytic P4 prediction (`δ_B/δ_G ≈ 1.04`) was wrong; the plant returned
>    2.78. Cause: re-quantising an already-integer signal by a rational factor is
>    a deterministic sawtooth, not additive uniform dither — M61 fact 53's comb,
>    seen in the variance domain.
> 3. §5's reading of D1 as a *B-plane* gradient was wrong, and §6's own control
>    refuted it one step later (fact 22).
> 4. `03` first assumed a JSON key (`iso_by_folder`) that `01` never wrote; it
>    crashed rather than silently mis-indexing, and the cache filenames were used
>    instead.

> **Fact 38 (ARGUED).** **Nothing under `crates/` was modified**, no binary was
> measured from a warm `target/`, nothing was pushed, and every commit was
> path-scoped with `git commit -- <paths>` and audited with
> `git show --name-only`: `71cd54c` (5 files), `e960da9` (1), `9116d5a` (1),
> `2bbca22` (5). `D:\macro-dark-frames` was opened read-only;
> `D:\personal\macro` and `C:\dev\macro` were never touched. This milestone is
> entirely Python and never needed `cargo`.

---

## 10. Reproduction

```powershell
cd experiments\M68-b-plane-mechanism
$env:PYTHONIOENCODING='utf-8'
python src\00-derivation.py                  # the algebra + planted plant
python src\01-dark-iso-sweep.py --selftest   # fit recovers planted ratios
python src\01-dark-iso-sweep.py              # 220 decodes, ~4 min, writes cache/
python src\02-criteria.py                    # C0-C4, the pre-registered verdict
python src\03-where-is-the-scale.py          # D1-D3, post-hoc
python src\04-gradient.py                    # E1-E5, post-hoc
python src\05-profile-numbers.py             # the numbers in section 7
```

Outputs are committed under `data/`. `cache/` (11 × ~530 MB) is gitignored and
is rebuilt by `01`.
