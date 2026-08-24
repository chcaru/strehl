# M107 — Colour fringing in the shipped render: attributing it across four mechanisms

**Status: diagnosis complete. No file under `crates/` was edited.**

---

## 0. Pre-registration

`experiments/M107-chroma/PRE-REGISTRATION.md`, committed at **`ed5a929`** before any
number in this report was computed. Bars B1–B5 are quoted verbatim in §7 and scored
there as written, including the one they fail.

### 0.1 What the corpus already decided, and what it did not

The rule-40 search found one directly relevant prior report and one directly relevant
fact.

- **`docs/research/M95-chroma-cositing.md`** measured and fixed a *co-siting* defect in
  the **binned** output path: R and B are read at opposite corners of the 2×2 quad, and
  `image_out.rs::develop_binned` now resamples them onto the quad centre with a Keys
  cubic at `COSITE_SHIFT = 0.25` binned px. Its §9.4 states explicitly that **it does
  not affect `--demosaic`**.
- **Fact 1378** records that the shipped `--srgb` path demosaics with Malvar-He-Cutler,
  and flags — before I started — that the natural `--binned` control for co-siting is
  *itself* contaminated by `COSITE_SHIFT`. It routes the question to M107 with the red
  herring already marked.
- **SYNTHESIS §6** already carries "per-channel focus stacking exploiting longitudinal
  CA" as an **UNVERIFIED novelty bet**. The idea is not new to the project. It had never
  been measured. That is what this milestone does.

Two structural facts I established by reading the source read-only, because the
attribution depends on them and neither was recorded:

1. **The render under investigation is the demosaic path.** `main.rs` sets
   `demosaic: demosaic || (srgb && !binned)`. Every `ORCH-gallery3` render used
   `--srgb`, so **M95's co-siting fix is inert in the images that prompted this
   milestone.**
2. **The election is driven by green alone.** `merge_cmd.rs:941` computes
   `green_luma_with_clip(...)` into `scratch.luma`, and `scratch.field.compute(...)`
   derives the focus field from that and nothing else. The comment at `merge_cmd.rs:2881`
   confirms the consequence: *"the merge already estimates all four CFA sites of every
   quad independently — `Estimator` carries four accumulators and reuses ONE focus
   decision across them."* Green is therefore always at its own best focus **by
   construction**, and red and blue are carried wherever green went. This is hypothesis
   (b)'s premise, confirmed at source rather than assumed.

### 0.2 The design, and why both instruments carry a free null

Every measurement here is made on **CFA planes**, not on RGB. A Bayer RGGB quad has
*two* green sites. G1 and G2 are the **same wavelength** on **different lattice sites**
with **independent noise**. So `G1 − G2` carries every channel-dependent-SNR, lattice,
resampling and estimator bias the instrument has, and **none** of the chromatic signal.

That is the whole design. A signal that does not beat `G1 − G2` is not a signal.

- **Instrument A** — per-channel edge-spread fit on raw CFA planes, each plane sampled
  at its **true sensel coordinate**. Co-siting is therefore removed *by construction*,
  and any residual displacement is optical. Measures **spatial displacement**, in sensel.
- **Instrument B** — per-plane focus response `F_c(x,y,k)` over the whole bracket, with
  sub-frame argmax by parabolic refinement. Measures **frame-of-best-focus offset**, in
  frames. Needs no width calibration, which is why it is the primary instrument for (b).

---

## 1. Verdict

**Two of the four candidate mechanisms are real and independently measured. They are
different effects, at different magnitudes, in different units, and both are present in
the shipped render.**

| | mechanism | verdict | magnitude | vs its null |
|---|---|---|---|---|
| **(a)** | **Lateral / transverse CA** | **REAL — dominant in spatial displacement** | `ε_R = −704.5 ppm` radial magnification error; **1.43 sensel** median displacement at r ≈ 2500 sensel, **→ 0 at the optical centre** | radial model R² = **0.9969**; the same fit on the G1−G2 null gives R² = 0.0524 and **fails to beat its own permutation null** (p = 0.71) |
| **(b)** | **Axial / longitudinal CA, baked in by the single election** | **REAL — confirmed on 5/5 stacks** | `k_R − k_G` = **−0.67 to −1.07 frames**, `k_B − k_G` = **−0.36 to −0.75 frames**; costs red **8.9–14.7 %** of its gradient energy | null `k_G1 − k_G2` ≤ **0.008 frames** in every stack; signal/null **75× to 231×** |
| **(c)** | Demosaic / co-siting | **BOUNDED SMALL in the shipped path, and not the cause** | shipped demosaic arm shows the *smallest* per-channel displacement of the three arms (0.08 sensel vs 0.34 for un-demosaiced `linear`, tweezers); independently, §12 K6 = 0.918–1.020 against a <0.50 bar for Nyquist-scale dominance | the registered `--binned` control **fired its own contamination clause** and is reported as unusable, not used |
| **(d)** | Resampler | **NOT A CONTRIBUTOR to (b); and it does not create the fringe at all** | gathering with the identity instead of the render's own warp moves `k_R − k_G` from −1.0476 to −1.0642, i.e. **1.6 %**. §12: blurring the `nearest` arm to the Catmull-Rom arm's luma reproduces its chroma to **ρ7 = 0.985/0.990**, so kernel-**created** chroma is ≤1.5 % of fringe amplitude | §12 K3's invariance band failed its own control at 10× the effect size; superseded by the K7 substitution test |

**On the orchestrator's favoured hypothesis (b): it is real, and the per-channel
election corollary is sound.** But **my registered bar B3 fails on its sign clause**, and
it fails for an interesting reason that I did not anticipate — see §4.2. I report that
failure rather than rewrite the bar around it.

**The single most important number for scheduling the follow-on:** red forfeits
**14.74 %** of its gradient energy on `tweezers-cpl` by being elected at green's frame,
against a null floor of **0.01 %**. That is a factor of **1474**.

---

## 2. Instrument validation

### 2.1 Instrument A — controls C1–C6

Run by `experiments/M107-chroma/src/c0_instrument.py` against a synthetic plant with
**truth by construction**.

```
python c0_instrument.py
```

| control | what it plants | result |
|---|---|---|
| C1 | noise-free null | `dR = −0.00866`, `dB = +0.00863`, G1−G2 null = **−0.01728 sensel** — the systematic floor |
| C2 | shifts ±0.40, ±0.15, +1.00, +0.60 | recovered, **worst error 0.0119 sensel** |
| C4 | 90 DN noise, 5 seeds | worst `dR` err 0.01497, worst `dB` err 0.02058, worst null **0.02535** |
| **C5** (power) | R planted blurrier, then R and B written to **each other's** lattice sites | the instrument **exchanges** `wR` and `wB` exactly: `+1.4593 / +0.0001` → `+0.0001 / +1.4593` |
| **C6** (power) | lattice offsets forced to (0,0) | reads `R−B = 1.168 sensel` against the geometric prediction `cos11° + sin11° = 1.172` — a **0.004 sensel** match, proving what the true-coordinate convention removes |

**C3b is a declared limitation, not a pass.** The *width* arm reads high because the
plane lattice samples on a 2-sensel pitch; the additive-in-quadrature model
(`q ≈ 0.988 sensel`) has scatter 1.138 and **fails badly below w ≈ 1.8 sensel** (planted
1.00 → fitted 2.074). **Instrument A's width arm is trustworthy only for w ≳ 2 sensel**
and no width claim in this report leans on anything narrower. Instrument A's
*displacement* arm is unaffected.

### 2.2 Instrument B — controls N1, N2a, N2b, N3

```
python e3_controls.py all        # N1, N2a, N3
python e3_controls.py n2b ; python e3_n2b_check.py
```

| control | bar, registered in advance | result | |
|---|---|---|---|
| **N1** gather-crop null | `max|ΔF|/max(F) ≤ 1e-3` and `max|Δ| ≤ 1 DN` | **0.024 DN**, **1.10e-6** relative | **PASS** |
| **N2a** bookkeeping null | all three medians exactly 0 | `dR = dB = null = +0.0000` | **PASS** |
| **N2b** label-swap power | signal and null must **exchange places** | see below | **PASS** |
| **N3** SNR-bias null | `|median| ≤ 0.15 frames` | **−0.0034 frames** | **PASS** |

**N1** discharges a claim the code was already making: `gather_planes`'s docstring
asserted the bbox-crop optimisation was equal to the uncropped path. It had never been
run. A docstring asserting an unrun control is exactly the rule-43 defect this project
exists to remove, so I wrote and ran it.

**N2b is the decisive control**, and it is a control with a *number*, not a direction.
Swapping the **data** of the R and G1 sites in every frame — leaving geometry, lattice
offsets, warp and gate untouched — permutes which focus index lands in which slot. The
post-swap medians are then fully determined by the pre-swap ones with **zero free
parameters**:

```
dR' = −dR/2        dB' = dB − dR/2        null' = dR
```

| quantity | predicted | measured | error |
|---|---|---|---|
| `dR` | **+0.5238** | **+0.5234** | 0.0004 |
| `dB` | **−0.1010** | **−0.0978** | 0.0032 |
| `null` | **−1.0476** | **−1.0477** | 0.0000 |

Worst error **0.0032 frames** against a bar of 0.02. The signal moved *into the null
slot* and the null picked up the full signal. **The instrument measures the wavelength
carried by the data, not the lattice site it sits on.** This forecloses every co-siting,
lattice-phase and demosaic explanation for the Instrument B result at once.

**N3 closes the confound the orchestrator specifically named.** Red is **2.6× darker**
than green in the measured ROI (mean 491.9 vs 1296.2 DN), and a noisier channel's argmax
is biased. So G2 was scaled to red's photon level **with matched shot noise added**, and
the green–green null re-measured: **−0.0034 frames**. A 2.6× SNR deficit buys less than
**0.4 %** of the signal.

---

## 3. Hypothesis (a) — lateral chromatic aberration. REAL, and dominant in displacement.

**Figure: `M107-fig3-lateral-radial.png`.**

```
python e1_raw_edges.py tweezers-cpl leaf-2-cpl bee-3-cpl wrapped-text-1
python e2_lateral.py
```

### 3.1 The declared gate, applied

The fit-quality gate was written into the pre-registration before E1 was analysed and is
applied unchanged: every plane `w_abs ∈ [0.4, 8.0]` sensel, every plane `rms/amp ≤ 0.12`,
`|null_dG| ≤ 0.10` sensel, `|dR|,|dB| ≤ 8.0` sensel. **41 ROIs → 20 kept** (rejected:
width 8, rms/amp 13, green-null 0, blow-up 0). Both are reported so the gate's effect is
visible rather than hidden:

| | n | `|dR|` | `|dB|` | `|G1−G2|` NULL |
|---|---|---|---|---|
| ungated | 41 | 1.4700 | 0.3566 | 0.0375 |
| **gated** | **20** | **1.4274** | **0.2472** | **0.0135** |
| gated, `tweezers-cpl` | 12 | 1.7883 | 0.1333 | 0.0123 |
| gated, `bee-3-cpl` | 8 | 1.2149 | 0.3867 | 0.0219 |

The `|null_dG| ≤ 0.10` clause is the principled one: **an ROI where the two greens
disagree has not been measured**, whatever it says about red and blue.

### 3.2 The radial model

Lateral CA is a per-channel magnification error, so channel *c* is displaced from green
by `ε_c·(r − r₀)`. An ESF measures only the component along the edge normal **n**, giving
`d_i = ε_c·((r_i − r₀)·n_i)` — three free parameters (`ε`, and the optical centre `r₀`).
Using each edge's own normal is what lets a tangential edge contribute a small predictor
instead of masquerading as noise.

| | `ε` | R² | permutation p95 R² | p | residual rms |
|---|---|---|---|---|---|
| `dR` **signal** | **−704.5 ppm** | **+0.9969** | +0.3534 | **0.0000** | **0.073 sensel** |
| `dB` **signal** | +68.4 ppm | +0.6590 | +0.3471 | 0.0005 | 0.200 sensel |
| `G1−G2` **NULL** | −4.7 ppm | **+0.0524** | +0.3163 | **0.7095** | 0.025 sensel |

**The null does not beat its own permutation null.** The signal does, overwhelmingly.
Red's implied optical centre is (+893, −602) sensel from the frame centre — plausible for
a teleconverted system. **Blue's ε is ~10× smaller than red's and its implied centre
(−5937, −1724) falls outside the sensor, so blue's lateral model is poorly constrained
and I do not claim a blue magnitude.**

### 3.3 Out-of-sample extrapolation — the strongest evidence for (a)

`python e7_cross.py`. The radial model was fitted **only** on E1: raw CFA planes, at
r ≈ 2500–3700 sensel. It is then asked to predict Instrument A on **rendered TIFFs**, at
radii it never saw, through an entirely different code path.

| stack | arm | r (sensel) | predicted | measured | meas/pred |
|---|---|---|---|---|---|
| `tweezers-cpl` | **linear** | 597 | 0.3144 | **0.3368** | **1.07** |
| `bee-3-cpl` | **linear** | 2578 | 1.4977 | **1.9281** | **1.29** |
| `tweezers-cpl` | demosaic | 597 | 0.3131 | 0.0845 | 0.27 |
| `bee-3-cpl` | demosaic | 2578 | 1.4928 | 0.8081 | 0.54 |
| `tweezers-cpl` | binned | 597 | 0.3123 | 0.6374 | 2.04 |
| `bee-3-cpl` | binned | 2578 | 1.4985 | 3.3948 | 2.27 |

The **`linear`** arm is the honest comparison — byte-frozen default, no demosaic, no
colour matrix, no sRGB curve, no co-siting correction. The model predicts it to **7 % and
29 %**, including at r = 597 sensel where it is predicting its own near-vanishing. **This
is post-hoc — it was not registered** — but it is extrapolation, not fitting, and a
spurious fit has no reason to get a near-zero prediction right.

The **demosaic** arm reads 2–4× *lower* than predicted, in the direction the known
dilution demands: the colour matrix mixes channels and I deliberately did not invert it,
so matrixed measurements are **lower bounds**. The **binned** arm reads ~2× high on both
stacks and **I cannot explain it** — see §8.

---

## 4. Hypothesis (b) — axial CA baked in by the single election. REAL.

**Figures: `M107-fig2-argmax-maps.png` (the maps), `M107-fig5-axial-summary.png`.**

```
python e3_argmax.py ; python e3_analyse.py ; python e6_payoff.py all
```

### 4.1 The result, on five stacks

Restricted to pixels where **all four planes** have a confident, interior, unimodal focus
response (prominence ≥ 3× the through-focus median), plus a 27-px border drop.

| stack | CPL | conf px | `k_R − k_G` | `k_B − k_G` | **NULL** `k_G1 − k_G2` | signal/null |
|---|---|---|---|---|---|---|
| `tweezers-cpl` (achromatic metal) | yes | 151 566 (72.3 %) | **−1.0476** | **−0.6248** | −0.0045 | 231× / 138× |
| `bee-3-cpl` | yes | 96 287 (45.9 %) | **−0.7390** | **−0.7484** | +0.0034 | 216× / 219× |
| `leaf-2-cpl` | yes | 72 654 (34.6 %) | **−1.0728** | **−0.4700** | +0.0063 | 171× / 75× |
| `wrapped-text-1` | **no** | 208 462 | **−0.6741** | **−0.7110** | +0.0081 | 83× / 88× |
| `coffee-bean` | **no** | 194 371 | **−0.8036** | **−0.3585** | +0.0026 | 309× / 138× |

Standard errors on the medians are **0.0007–0.0021 frames**; every signal is three orders
of magnitude larger than its SE. The distributional statistic is more telling than the
median: **99.7 %, 99.7 % and 100.0 %** of confident pixels carry `dR` of the same sign,
while the null sits at **54.4 %, 52.2 %, 51.9 %** — a coin flip, as a null must be.

**I rendered every map and looked at it before quoting any median.** The three per-channel
argmax maps of each stack are structurally identical depth surfaces — the tweezers' tilted
plane, the bee's leg structures, the leaf's veins — confirming the argmax tracks real
depth and not noise. The two difference maps are **uniformly signed across the entire
ROI**, not edge-localised and not speckled. The null map is **flat grey**.

### 4.2 Registered bar B3 fails on its sign clause, and why

I registered that (b) is CONFIRMED only if the two medians are **non-zero with opposite
signs**. **They are not. Both R and B sit before green, on all five stacks.**

That clause encoded an assumption I did not examine: it is the behaviour of an
**uncorrected singlet**, where focal length falls monotonically with wavelength and R and
B necessarily straddle G. A **colour-corrected** design does the opposite. An achromatic
doublet is built to bring two widely separated wavelengths — typically the C (red) and F
(blue) lines — to a *common* focus, and the residual **secondary spectrum** leaves the
middle of the band, green, focusing elsewhere. **R and B on the same side of G is the
signature of a corrected lens, not the absence of axial CA.**

The optical path is a **FE 100mm F2.8 Macro GM OSS** (ED elements, strongly corrected)
behind a **2× Viltrox teleconverter** (facts 26, 28, 832, 1147, 1150). Same-side R and B
is the expected result for that stack of glass. That R and B are **unequal** (−1.05 vs
−0.62 on tweezers) says the correction is partial, which is also expected.

So: **the mechanism the orchestrator proposed is real; the sign prediction we both
carried was wrong.** I am reporting the bar as failed rather than narrowing it, because
the failure is the informative part.

### 4.3 Robustness — the number is not a property of the operator or the warp

All on `tweezers-cpl`:

| arm | `k_R − k_G` | `k_B − k_G` | NULL | loss R |
|---|---|---|---|---|
| shipped (Sobel, win 27, warp ON) | −1.0476 | −0.6248 | −0.0045 | 14.74 % |
| **warp OFF** (identity gather) | −1.0642 | −0.6347 | −0.0015 | 15.30 % |
| **Laplacian** energy | −1.0648 | −0.5253 | −0.0059 | 30.66 % |
| box window **15** | −1.0388 | −0.6073 | −0.0121 | 14.55 % |
| box window **41** | −1.0486 | −0.6269 | −0.0027 | 14.61 % |

`k_R − k_G` spans **−1.0388 to −1.0648**, a range of **±1.3 %**. The null stays ≤ 0.0121
frames throughout. **Hypothesis (d) is therefore not a contributor to (b): removing the
resampler entirely moves the answer by 1.6 %.**

### 4.4 What the shared election actually costs

This is the number that decides whether (b) is worth acting on. `loss_c = 1 −
F_c(k_G)/F_c(k_c)` is the fraction of gradient energy channel *c* forfeits by being
elected at green's frame instead of its own. The **null floor** is the same quantity
computed between the two greens.

| stack | R forfeited | B forfeited | **NULL floor** | through-focus half-width | R's offset in DoF |
|---|---|---|---|---|---|
| `tweezers-cpl` | **14.74 %** | 5.18 % | **0.01 %** | 4 frames | −0.262 |
| `wrapped-text-1` (no CPL) | **9.51 %** | 10.78 % | 0.02 % | 3 frames | −0.225 |
| `coffee-bean` (no CPL) | **8.96 %** | 2.20 % | 0.04 % | 4 frames | −0.201 |

Red is elected roughly **a quarter of a depth of field** away from its own best focus,
everywhere, in every stack. This is not an edge artifact — it is a uniform, permanent
sharpness tax on two of the three output channels.

---

## 5. Hypotheses (c) and (d) — bounded, and not the cause

**(c) demosaic / co-siting.** Two independent arguments bound it small *for the shipped
path*:

1. **Instrument B never demosaics at all.** It runs on raw CFA planes. The full
   −1.05-frame effect is present with no demosaic anywhere in the measurement path, and
   N2b proves the effect follows the data rather than the lattice site. **(c) cannot
   explain (b).**
2. On the render arms, the **shipped demosaic arm shows the *smallest* per-channel
   displacement of the three** — 0.0845 / 0.2566 sensel on tweezers against 0.3368 /
   0.9823 for the un-demosaiced `linear` arm. Malvar-He-Cutler co-sites the channels and
   thereby *reduces* the geometric component. It is not adding the fringing.

**(d) resampler.** §4.3: warp OFF moves the axial result by 1.6 %. For the spatial arm,
Instrument A samples each plane at its true sensel coordinate, so no resampling of the
measured quantity occurs at all. **(d) is a non-contributor at the magnitudes involved.**

---

## 6. Why the fringe is a different colour on different subjects

The orchestrator asked, correctly, that this be explained rather than noted.

**Figure: `M107-fig4-fringe-crops.png`** — 1:1 crops of the shipped render with a 100-px
scale bar, alongside `R−G` and `B−G` **high-passed at σ = 6 px**. The high-pass is the
point: a brown hair has `R > G` everywhere on it, and that is *chromaticity*, not a
fringe. A fringe is an edge-scale **sign reversal** across the edge, and only the
high-pass isolates it.

Red is the outlier in **both** mechanisms: it carries ~10× blue's lateral magnification
error (`ε_R = −704.5 ppm` vs `ε_B = +68.4 ppm`) **and** the largest axial offset on 3 of 5
stacks. So red is the channel most often in the wrong place. A radial displacement of red
produces **red excess on the inward side of an edge and red deficit on the outward side** —
which renders as orange/magenta on one flank and cyan on the other. Which flank the
observer notices depends on the edge's orientation relative to the radius and on the
subject's base colour, not on a different mechanism.

The `tweezers-cpl` panel settles it: **magenta and cyan fringing on bare metal**, an
achromatic subject, so the fringe colour cannot be inherited from the subject.

---

## 7. Registered bars — scored as written

### B1 — single-frame control. **PASSED, and it decided the spatial question first.**

> *Stacking is NOT the cause if the single-frame offset is ≥ 0.30 sensel and the merged
> render agrees within 2×.*

Single-frame gated `|dR| = 1.4274 sensel` ≫ 0.30. The merged `linear` render agrees at
matched radius to **1.07× and 1.29×** (§3.3). Instrument-broken clause: `|null_dG| =
0.0135` < 0.10. **→ Stacking is not the cause of the *spatial* fringing; (a) or (c) is.**
This is why the report separates displacement from focus offset throughout — B1 answers
only the former, and (b) lives entirely in the latter.

### B2 — radius sweep for (a). **INDETERMINATE as registered.**

> *(a) CONFIRMED if the radial component of `d0_R − d0_B` is linear in radius with
> R² ≥ 0.5, |intercept| < 0.15 sensel, corner extrapolation ≥ 0.30 sensel. (a) DEAD if
> mean|offset| inner ≥ 50 % of outer, or R² < 0.2.*

Scored exactly as written: slope **−829.1 ppm**, intercept **+0.7043 sensel**,
**R² = 0.3129**, corner extrapolation −2.0552 sensel. **CONFIRMED clause: False**
(R² < 0.5, intercept > 0.15). **DEAD clause: also False** — inner/outer =
**0.212** (bar 0.50) and R² = 0.313 (bar 0.20). The bar lands between its own clauses.

The registered form is the weaker analysis and I should have seen it: regressing on raw
radius **discards the edge normal**, so a tangential edge contributes near-zero
displacement at large radius and inflates the residual. The per-normal fit in §3.2
(R² = 0.9969) is the correct analysis and **it is post-hoc**. I flag it as such. The
registered *inner/outer ratio of 0.212* is the part of B2 that survives unambiguously,
and it clears the DEAD threshold decisively: **fringing at the centre is 21 % of that at
the edge**, exactly (a)'s signature.

### B3 — per-channel argmax for (b). **SIGN CLAUSE FAILED; magnitude and null clauses passed overwhelmingly.**

- non-zero: **yes**
- **opposite signs: NO — clause FAILED** (§4.2)
- each `|median| ≥ 0.5 frames`: yes for `dR` on 5/5; **`dB` = 0.3585 on `coffee-bean` is below 0.5**
- each ≥ 3× the null: **yes — 75× to 309×**
- KILLED clause (both < 0.5, or neither exceeds 3× null): **not met — (b) is not killed**
- instrument broken if `|null| ≥ 0.25`: max observed **0.0081**. **PASS**
- achromatic-subject control on `tweezers-cpl`: **run, and it is the *strongest* stack**
- every map rendered and looked at before any median quoted: **done**

### B4 — demosaic path comparison. **CONTROL CONTAMINATED — reported as such, exactly as registered.**

> *Registered hazard (fact 1378): the `--binned` arm contains `COSITE_SHIFT`. Instrument A
> on the binned render must read `|d0_R − d0_Ḡ|` < 0.15 binned px. If it reads ≈ 0.5 the
> control is contaminated and is reported as such rather than used.*

It reads **0.328 binned px** on `tweezers-cpl` — above the 0.15 threshold. **The clause
fires and the arm is not used.** Fact 1378 called this correctly in advance. (c) is
instead bounded by the two arguments in §5, neither of which needs the binned arm.

**I introduced and then found one error in this arm.** I initially gave `binned` the
*uncorrected* lattice offsets, ignoring that `develop_binned` (`image_out.rs:302-304`)
has already carried R and B onto the quad centre. That double-count manufactured exactly
**1.0 source sensel** of spurious R–B separation — the full size of the correction. It is
fixed, and the wrong table is kept reachable as `OFFSETS_UNCORRECTED` so the size of the
mistake can be reproduced rather than merely asserted. **This is a caution for whoever
schedules the fix: the binned arm's geometry is easy to get wrong in exactly the
direction that would falsely incriminate M95's correction.**

### B5 — CPL and subject-colour control. **CPL EXONERATED on the axial arm; marginal on the lateral arm.**

> *The CPL is exonerated if lateral CA there is within 2× of the CPL stacks; implicated if
> it reads < 0.3×.*

- **Axial (Instrument B): clean exoneration.** `wrapped-text-1` (no CPL) reads
  `dR = −0.6741` against tweezers' −1.0476 — a ratio of **0.64**, well within 2×. A second
  non-CPL stack, `coffee-bean`, reads −0.8036. **Two non-CPL stacks reproduce the effect
  at full strength.**
- **Lateral (Instrument A): marginal.** `wrapped-text-1` gives `|dR| = 0.7090` sensel
  against tweezers' 1.7945 — a ratio of **0.40**. Not implicated (bar 0.30), but the
  exoneration clause (within 2×) is **missed at 2.5×**. On **n = 3 ROIs** at uncontrolled
  radii, and lateral CA is radius-dependent, so this comparison is not radius-matched and
  I do not read it as evidence against the CPL. **Honest status: CPL not implicated;
  lateral exoneration not cleanly established.**

---

## 8. What I could **not** determine, and why

This section is required and it is not a formality — several of these bound the
recommendation.

1. **The sign of the axial offset is not proven optical by a direction-reversal test.**
   The decisive control would be a bracket racked the *opposite* way: if `k_R − k_G` is
   optical its sign must flip. `e5_sweep.py` recovers sweep direction from the sidecar's
   per-frame magnification trend, and **all five available stacks sweep the same way**
   (decreasing magnification, Pearson r ≤ −0.99). The owner always racks in one
   direction. **This test is unavailable from the existing capture library and requires a
   new capture.** Reversing frame order synthetically is vacuous — it flips the argmax by
   arithmetic identity and tests nothing. This is the single largest remaining gap in
   (b), and N2b/N3 constrain the alternatives but do not close it.

2. **The `binned` render arm reads ~2× high and I cannot explain it.** After fixing my
   own double-count, `binned` still measures 2.04× and 2.27× the model prediction on two
   stacks. I verified the units are right (both `linear` and `binned` TIFFs are
   2344×3520, i.e. 2 sensel/px; the demosaic TIFF is 4688×7040). The arm confounds three
   changes at once — colour matrix, sRGB curve, `COSITE_SHIFT` — on n = 4 ROIs. **I am
   not claiming a defect in M95's correction.** Isolating this needs an arm with the
   matrix disabled, which does not exist as a flag.

3. **Blue's lateral magnitude is not established.** `ε_B = +68.4 ppm` beats its
   permutation null (p = 0.0005) but R² = 0.659 and the implied optical centre falls
   outside the sensor. Blue's lateral CA is *small*; how small is not measured.

4. **`leaf-2-cpl` contributed no Instrument A ROIs.** The edge detector's contrast and
   coherence gates found 0 candidates on that subject, so all lateral numbers rest on
   `tweezers-cpl`, `bee-3-cpl` and 3 ROIs of `wrapped-text-1`. Its Instrument B result is
   unaffected.

5. **Why R and B split unequally on some stacks and equally on others** (tweezers −1.05/
   −0.62 vs bee −0.74/−0.75) is unexplained. The plausible cause is that the *effective
   wavelength* within each filter band depends on the subject's spectral radiance, so a
   subject whose red content sits at 620 nm focuses differently from one at 660 nm. This
   is testable with a spectrally controlled target and was not tested.

6. **My plane grid may be offset from strehl's by the visible-area crop.** The sidecar
   reports `plane 3520x2344` (= 7040/2) while `raw_image_visible` is 7028 wide (= 3514).
   A translation offset applied about the wrong origin introduces ≲0.3 px of
   misregistration at the largest `|a−1|`. It affects **all four planes identically** and
   so cannot manufacture a per-channel difference, but it slightly blurs Instrument B's
   confidence mask. Not corrected.

7. **No number here is traceable to a lens bench.** These are measurements of the
   *system* — GM prime + 2× Viltrox + (sometimes) CPL — and per the brief they must not be
   compared against published MTF or CA figures for the bare 100 mm.

---

## 9. Recommendation, with a cost estimate

### 9.1 Per-channel election for (b) — recommended, behind a flag, and it is not free

The corollary holds: **running the election per channel would remove the axial component
at its source**, with no lens database, no radial model and no calibration. But "close to
free" is not what the machinery says. The costs below are extrapolated from the
**measured** per-frame costs `gallery.log` printed for `bee-3-cpl` (299 frames), not
measured directly — I could not measure them without editing contended files.

**Measured baseline (`bee-3-cpl`, 299 frames):**

```
workers      : 13 chunks (13 allowed by the 6144 MB budget, 32 by CPU)
working set  : 321 MB/worker pass 1, 469 MB/worker pass 2
pass 1       : wall 27.328 s;  decode 39.874 s summed;  focus + reg 293.205 s summed
pass 2       : wall 26.494 s;  decode 28.362 s summed
```

**The critical structural fact: the merge is already memory-bound, not CPU-bound.** 13
workers are allowed by the memory budget against 32 by CPU. So added memory costs wall
clock *twice* — once directly, once by reducing parallelism.

- **CPU.** `focus + reg` is **293.2 s of 333.1 s** of pass-1 work — **88 %**. Computing
  the field on R, Ḡ and B instead of green luma alone triples it: pass-1 CPU
  → ~919 s, **≈2.8×**. Decode is unchanged.
- **Memory.** The per-worker `Scratch` f32 plane buffers that must triple — `luma`,
  `box_scratch`, `reg`, and `FocusField` — are ≈4 × 8.25 Mpx × 4 B ≈ **132 MB**. Adding
  two more channels adds ~264 MB/worker. Pass 2 is the binding constraint: 469 →
  ~733 MB/worker, so workers allowed by the 6144 MB budget fall **13 → ~8**.
- **Net wall clock:** ~919 s over ~8 workers ≈ 115 s against today's ~26 s, so
  **roughly 4–4.5×** for a stack of this size — about **3.5–4 minutes** for `bee-3-cpl`
  instead of ~54 s. Raising the memory budget recovers most of it, since CPU allows 32
  workers; **this is a budget-tuning problem more than an algorithmic one.**

**What it would break — and item 1 is the real one:**

1. **M93's election gate is calibrated on green.** `noise.green_luma_sigma(...)` is
   literally named for the channel it models, and the log prints `focus noise sd
   0.015214` for the regularised green field. R and B have materially fewer photons — I
   measured **R/G = 0.3795** in the tweezers ROI — so a green-derived threshold applied to
   red is the wrong gate, in the direction that lets the election chase noise. **A
   per-channel noise model is a prerequisite, not a follow-up.**
2. **The halo plan** (`merge_cmd.rs:1537`, `halo::Plan::build(&luma, p1.stats.best_index(),
   …)`) is built from green luma and *one* best-index map. With three index maps it is
   ambiguous which one it should key on. This intersects M87's territory.
3. **Byte-freeze.** The default path is byte-frozen; per-channel election changes output
   bytes and must ship behind a flag with the existing single-election path preserved.
4. **A new artifact risk worth naming before anyone implements it:** giving each channel
   its own depth means that at an **occlusion boundary** the three channels can elect
   frames on *opposite sides* of the occluder, producing coloured edges where today there
   is a single (possibly wrong) depth. That is precisely M87's veil region. **Per-channel
   election should be measured against M87's occlusion metric, not only against
   sharpness.**
5. It does **nothing** for (a), which is the larger effect in spatial terms.

**Expected benefit:** recovery of the **8.9–14.7 %** of gradient energy red currently
forfeits and **2.2–10.8 %** for blue — equivalently, moving two of three channels from
~0.2–0.26 DoF off-focus to on-focus. Green is unchanged by construction.

### 9.2 Lateral CA for (a) — a post-merge plugin, not the aligner

**It belongs after the merge, not in the aligner.** Three reasons, all measured:

1. It is a **static property of the optical system**, identical in every frame (B1: full
   strength in a single frame). The aligner solves a per-frame similarity; folding a
   per-channel radial scale into it would make a per-frame estimator carry a constant,
   which is both wasteful and a new way for the solve to go wrong.
2. The correction is a **per-channel radial resample**, exactly the operation
   `image_out.rs` already performs for `COSITE_SHIFT` — same Keys cubic, same
   "correction must not cost more sharpness than the misregistration it removes"
   argument. The machinery is already there and already justified in the right place.
3. The aligner's files are M85's and the correction does not need them.

**Concretely:** one radial scale per channel, `ε_R ≈ −704.5 ppm` and `ε_B` small and
**not yet reliably measured**, about an optical centre offset from the frame centre
(fitted here at (+893, −602) sensel on 20 ROIs — **too few to fix a centre for
production**). Cost is one Keys resample per channel per output, i.e. the same order as
`COSITE_SHIFT`'s, which the corpus already accepts. **Before implementing, the parameters
should be re-fitted on a purpose-shot flat, high-contrast, radially-covering target with
≥ 100 ROIs** — `highly-angled-ruler-mm-cpl` and `flat-on-ruler-cpl` exist in the library
and look suitable. My 20 ROIs are enough to establish the mechanism, not to calibrate a
shipped correction.

---

## 10. Candidate facts for the fold

Numbered `P1…` per rule 28. All MEASURED unless marked.

- **P1.** The shipped `--srgb` render path demosaics (`main.rs`: `demosaic || (srgb &&
  !binned)`), so M95's `COSITE_SHIFT` correction — which lives in
  `image_out.rs::develop_binned` — is **inert in the shipped default render**. DERIVED
  from source.
- **P2.** The focus election is computed from `green_luma_with_clip` alone
  (`merge_cmd.rs:941`) and the single resulting index is applied to all four CFA
  accumulators. **Green is at its own best focus by construction; R and B are not.**
  DERIVED from source.
- **P3.** The optical system exhibits **lateral CA of `ε_R = −704.5 ppm`** radial
  magnification error for red relative to green; radial model R² = **0.9969** over 20
  gated ROIs, permutation p < 0.0005, residual rms **0.073 sensel**. The G1−G2 null fits
  R² = 0.0524 and **fails** its permutation null (p = 0.7095).
- **P4.** Median per-channel edge displacement on raw CFA planes at r ≈ 2500 sensel is
  **1.43 sensel** for red, **0.25 sensel** for blue, against a G1−G2 null of **0.0135
  sensel**. Displacement at r < 0.35·r_max is **21 %** of that at r > 0.75·r_max.
- **P5.** The lens's **axial** CA places both R and B **before** green in the focus
  bracket on **5/5 stacks**: `k_R − k_G` = −0.67 to −1.07 frames, `k_B − k_G` = −0.36 to
  −0.75 frames, against a `k_G1 − k_G2` null of ≤ **0.008 frames**. 99.7–100 % of
  confident pixels share the sign of `dR`; the null sits at 52–54 %.
- **P6.** R and B on the **same** side of G is the signature of a **colour-corrected**
  design's residual secondary spectrum, not of absent axial CA. The commonly assumed
  "R and B straddle G" holds for an uncorrected singlet and **does not hold for this
  system**. ARGUED from optics, supported by P5.
- **P7.** The single shared election costs red **8.96–14.74 %** and blue **2.20–10.78 %**
  of gradient energy, against a null floor (electing G1 at G2's index) of **0.01–0.04 %**.
  Red is elected ≈ **0.20–0.26 depth-of-field** from its own best focus.
- **P8.** The axial result is stable to **±1.3 %** across Sobel/Laplacian operators, box
  windows 15/27/41, and warp ON/OFF. **The resampler contributes 1.6 %** — hypothesis (d)
  is a non-contributor.
- **P9.** In the shipped demosaic arm, per-channel displacement is the **smallest** of the
  three render arms (0.0845 sensel vs 0.3368 for un-demosaiced `linear`, `tweezers-cpl`).
  Malvar-He-Cutler **reduces** the geometric component; it does not create the fringing.
- **P10.** The Breakthrough X4 CPL is **not** the cause: two non-CPL stacks
  (`wrapped-text-1`, `coffee-bean`) reproduce the axial effect at full strength
  (−0.674, −0.804 frames).
- **P11.** All five aligned stacks in the capture library were racked in the **same**
  focus direction (decreasing magnification, Pearson r ≤ −0.99). **The sign-reversal
  control for axial CA is therefore unavailable without a new capture.**
- **P12.** The merge is **memory-bound, not CPU-bound**: 13 workers allowed by the
  6144 MB budget against 32 by CPU, and `focus + reg` is **88 %** of pass-1 work
  (293.2 s of 333.1 s, `bee-3-cpl`). Any per-channel focus work therefore costs wall
  clock twice — directly, and by reducing worker count. MEASURED from `gallery.log`.

### Proposed disciplines

- **D1.** On a Bayer sensor, **G1 vs G2 is a free internal null** for any per-channel
  claim: same wavelength, different lattice site, independent noise. Any per-channel
  measurement that does not report it alongside the signal should not be believed.
- **D2.** A permutation-style control is only a *power* control if it predicts a
  **number**. N2b's swap algebra predicted all three post-swap medians with zero free
  parameters and matched to 0.0032 frames; a control that predicts only a direction would
  have passed just as easily on a broken instrument.
- **D3.** When comparing render arms that carry a geometric correction, **read the
  correction's source before assigning lattice offsets.** Giving the corrected arm the
  uncorrected offsets manufactures spurious displacement of exactly the correction's own
  magnitude — an error that lands precisely on "the correction is wrong".

---

## 11. Status / Changes / Verified / Not verified / Notes

**Status: DONE (diagnosis).** No fix implemented; none was in scope.

**Changes** — all additive, path-scoped, nothing under `crates/` touched:
- `experiments/M107-chroma/PRE-REGISTRATION.md` — committed at `ed5a929` before measurement.
- `experiments/M107-chroma/src/{common,edges,c0_instrument}.py` — Instrument A and its controls.
- `experiments/M107-chroma/src/{e1_raw_edges,e2_lateral}.py` — hypothesis (a).
- `experiments/M107-chroma/src/{e3_argmax,e3_analyse,e3_controls,e3_n2b_check}.py` — hypothesis (b) and its four controls.
- `experiments/M107-chroma/src/{e4_render_arms,e4_summary}.py` — hypotheses (c)/(d).
- `experiments/M107-chroma/src/{e5_sweep,e6_payoff,e7_cross}.py` — sweep direction, cost, out-of-sample test.
- `experiments/M107-chroma/src/{figures,fig_esf,fig_preview,show}.py`, `{render_arms,align_b5}.ps1`.
- `docs/research/M107-chroma.md` — this report.

**Verified:**
- Instrument A: C1, C2, C4, C5, C6 pass; C3b is a declared limitation on the width arm.
- Instrument B: N1 (0.024 DN / 1.10e-6), N2a (exactly 0), N2b (worst error 0.0032 frames
  against a zero-free-parameter prediction), N3 (−0.0034 frames at 2.6× SNR deficit) all pass.
- Six render arms produced at binary SHA-256 `3C596BC5…`, all `sidecar-override`, all
  `N placed / 0 refused`, all exit 0 (rule 46: exit code read outside any pipeline).
- Every map rendered and inspected before its median was quoted.

**Not verified:**
- Everything in §8. Most importantly: **the direction-reversal control for (b) could not
  be run**, and the `binned` arm's residual 2× is unexplained.
- The §9.1 cost figures are **extrapolations** from logged per-frame costs, not measured.
  Measuring them requires editing `merge_cmd.rs`, which is contended.

**Notes:**
- Rule 45 honoured throughout: every `stack`/`align` invocation ran with `STREHL_WARPMAP`
  pointing at my own sidecar under `C:\dev\strehl-out\M107-chroma\renders\`. Nothing was
  written into `D:\personal\macro`.
- The binary was **not** rebuilt — it is the one that produced `ORCH-gallery3`.
- `ORCH-gallery3` was not re-rendered.
- **One error found and fixed in my own work**, reported in §7/B4 rather than silently
  corrected: the binned arm's lattice offsets initially double-counted `COSITE_SHIFT`,
  manufacturing 1.0 sensel of spurious R–B separation in the direction that would have
  falsely incriminated M95.

**Figures**, all in `C:\dev\strehl-out\M107-chroma\fig\`:
- `M107-fig1-esf-tweezers.png` — raw per-channel edge-spread fits with the ESF evidence.
- `M107-fig2-argmax-maps.png` — the three argmax maps, the two difference maps, and the
  G1−G2 null map, per stack, on a shared diagnostic stretch.
- `M107-fig3-lateral-radial.png` — the radial model, the permutation null, magnitude vs radius.
- `M107-fig4-fringe-crops.png` — the fringing at 1:1 with a 100-px scale bar and the
  high-passed channel decomposition.
- `M107-fig5-axial-summary.png` — per-stack axial offsets and the cost of the shared election.
- `M107-fig6-kernel-roi-{auto,centre}.png` — **where** §12 measured, with the ROI box on the
  frame, 1:1 crops of all three kernel arms, and their high-passed chroma at 25× gain.
- `M107-fig7-kernel-bars.png` — K2, K7 and K5 scored against the bars registered at
  `bf975e0` / `e96040d`.

---

## 12. Addendum — the ORCH-kernel arms (E8)

Three renders of `bee-3-cpl` arrived after this report was committed at `a16976f`:
same solve, placements, reference and stack digest, differing **only** in the gather
kernel, produced by rewriting one `resampler` line in a copied sidecar
(`experiments/ORCH-drift-check/kernel_ab.ps1`, `d3a49e4`). The orchestrator observes
**by eye, and explicitly flags as ARGUED**, that the chroma fringing on the bee hairs is
"markedly stronger" under `nearest`, and reads that as evidence the fringe is pre-existing
and merely blurred by Catmull-Rom — which would bound candidate (d) small for free. I was
asked to check that reading, not adopt it, and the falsifier the orchestrator named
themselves is that `nearest` also aliases, and aliasing on a Bayer-derived image can
synthesise colour.

Bars **K1–K6** registered in `experiments/M107-chroma/PRE-REGISTRATION-2.md`, committed
`bf975e0` before a pixel was read. Bar **K7** registered in
`PRE-REGISTRATION-2-AMENDMENT.md`, committed `e96040d` before K7 was run and labelled
**POST-HOC relative to K1–K6** because looking at K1–K6 is what suggested it.

### 12.1 One mechanism excluded from source, before measuring

Before registering anything I checked whether `nearest` could manufacture
*channel-differential* displacement by quantising each CFA plane's sample phase onto its
own lattice — a third mechanism neither of us had named, and one that would have made the
fringe kernel-created without any aliasing.

It cannot. `align_cmd.rs::warp_frame_in_place` loops the four CFA sites `(dx, dy)` and
calls `gather_checked(src, t, geom, resampler, …)` with **the same `t` and the same
`geom`** on every pass; `warpmap.rs::gather_into` samples at
`t.apply_at(px as f64, py as f64, cx, cy)`, which depends only on the plane coordinate and
not on `(dx, dy)`. All four planes therefore land on identical fractional coordinates and
`sample_nearest`'s `x.round()` quantises **common-mode**. A common-mode geometric shift is
achromatic by definition. This is a source fact, not a measurement, and it is recorded in
the pre-registration so it cannot be re-presented as a finding.

### 12.2 The ROI trap, caught by looking

The fringe-weighted ROI selector, run unrestricted, went straight to `(996, 8)` — the top
edge of the frame, **on the wing**, at r = 2713 px. That is where the highest-contrast fine
edges are *and* where lateral CA is near maximum, but it is **not bee hair**, which is what
the orchestrator's claim is about. `M107-fig6-kernel-roi-auto.png` shows this plainly; the
first version of its chroma panel also rendered the wing's warm cast as a saturated orange
field, i.e. it showed **subject chromaticity, not fringing** — the identical mistake fig4
made on first draft.

Both were fixed: the chroma panels now show the σ = 6 px **high-passed** field that the
statistic actually consumes, and a second ROI restricted to r < 900 px selects `(3100, 1912)`,
r = 125 px, squarely on the hair mass (`M107-fig6-kernel-roi-centre.png`). **Every K-bar was
scored on both ROIs and they agree on every verdict.** In `fig6-centre` the three chroma
panels visibly carry the *same* hair-aligned magenta/green streaks at slightly different
contrast — the map says what K4 and K7 say numerically.

### 12.3 Results

All figures linear-light, σ = 6 px high-pass, edge mask = top 10 % of `|∇L|` taken from the
**Catmull-Rom arm only** so the identical pixel set is used for every arm and the mask
cannot respond to the kernel. `cr = R−G`, `cb = B−G`. Command:
`python -u e8_kernel.py centre 900` and `python -u e8_kernel.py auto`; scored by
`python -u e8_score.py` → `C:\dev\strehl-out\M107-chroma\e8-scorecard.txt`.

| bar | centre (hair, r=125) | wing (r=2713) | verdict |
|---|---|---|---|
| **K1** validity | bytes ≡ gallery; `r(L)` = 0.9147 | bytes ≡ gallery; 0.8594 | **PASS** |
| **K2** premise `cr` | 1.0861 | **1.0200** | **NOT CONFIRMED** / **PREMISE FALSE** |
| **K2** premise `cb` | 1.0677 | 1.1133 | **NOT CONFIRMED** (bar 1.15) |
| K2 luma reference | 1.0441 | 1.0769 | — |
| **K3** ρ invariance `cr`/`cb` | 1.0402 / 1.0225 | 0.9471 / 1.0338 | **pre-existing** (band 0.85–1.18) |
| **K4** `r_chroma/r_luma`, slope | 0.967 / 0.977, +0.96 | 1.075 / 0.981, +0.94 | **same fringe** (bar ≥0.70, slope >0) |
| **K5** chroma axis-anisotropy | 0.39 / 0.71 | 0.71 / 0.66 | **not aliasing** (bar >1.5) |
| **K5** *luma* axis-anisotropy | **2.71** | **3.79** | lattice signature present — **in luma only** |
| **K6** ρ bilinear/nearest | 0.918 / 0.955 | 1.020 / 0.935 | **(c) bounded small** (band 0.70–1.40) |
| **K7** ρ7 matched-luma | **0.9851 / 0.9901** | **0.9326 / 0.9881** | **pre-existing, merely blurred** |
| K7 NULL catmull→bilinear | 0.9498 / 0.9732 | 0.9974 / 0.9745 | **PASS** (band 0.90–1.10) |
| K7 σ\* | 0.4897 px | 0.6106 px | Catmull-Rom's lowpass vs a zero-order hold |

**K7 is the decisive one.** It performs the substitution the orchestrator's reading
literally asserts: blur `nearest` with a **channel-independent** Gaussian until its luma
high-pass rms equals Catmull-Rom's (matched to a relative 1.6e-14 by root-find), then
compare chroma. If the fringe were created by the kernel, chroma would survive the
luma-matching; it does not. **ρ7 = 0.985 / 0.990 at the hair ROI**, and the headline sits
*closer to unity than the procedure's own null* (0.950 / 0.973), so the residual 1.5 % is
smaller than the matching bias itself.

**Controls.** `K3-CTRL` blurs the Catmull-Rom arm by a synthetic channel-independent
Gaussian and requires ρ to hold; it returned 0.694 at σ = 2.0 px, **outside K3's own band**.
That failure is why K7 exists. Adding `rms_L` to each control point showed why: the two arms
differ by only ×0.958 in luma rms, which sits between the σ = 0.25 point (×0.9999 → ρ ×0.9998)
and the σ = 0.5 point (×0.9643 → ρ ×0.9498). Interpolated, a pure-blur explanation predicts
ρ_nearest/ρ_catmull ≈ 1.01–1.05; measured 1.0402. K3 was never calibrated against the size of
the effect it was testing, and an uncalibrated invariance band is an argument, not a
measurement — this is recorded as a defect in my own bar, not in the data.
`K3-POWER` shifts **only** the red channel by a known subpixel amount: ρ_cr rises
monotonically (×1.026 at 0.3 px, ×1.134 at 0.6 px) while ρ_cb stays flat (×1.001, ×1.003).
The instrument is both **responsive** to chromatic displacement and **specific** to the
channel that moved.

### 12.4 What this settles, and what it does not

**The orchestrator's conclusion is confirmed. Their premise, as stated, is not.**

- *Confirmed:* the fringe is pre-existing in the data and Catmull-Rom is merely blurring it.
  K7 = 0.985/0.990, K4 slopes positive with chroma correlating as well as luma does.
- *Not confirmed:* "markedly stronger" under `nearest`. Chroma rms rises 2.0–11.3 % across
  the two ROIs and both axes — and **luma rms rises 4.4–7.7 % on the same pixels**. On the
  wing ROI the R−G fringe rises by 2.0 % against a 7.7 % luma rise, i.e. relative to the
  edge energy carrying it, the magenta fringe is *weaker* under `nearest`. The eye was not
  lying, but a good part of what it read as colour was luma acutance plus `nearest`'s very
  real lattice structure — which K5 finds at anisotropy **2.71–3.79 in luma** and
  **0.39–0.71 in chroma**. The aliasing signature the orchestrator correctly worried about
  is present; it is simply not chromatic.
- *(c) bounded small, independently:* K6 in [0.918, 1.020], nowhere near the <0.50 that
  Nyquist-scale co-siting would require. Consistent with §5.
- *(d) bounded, now quantitatively:* any kernel-**created** chroma is ≤1.5 % of the fringe
  amplitude at the hair ROI and ≤6.7 % at the wing, and both deficits are *negative* — the
  kernel removes fringe, it does not add it. Calibrating against K3-POWER
  (0.3 px of pure red shift ⇒ +2.6 % centre, +8.9 % wing), that bounds any kernel-induced
  **channel-differential displacement** at roughly **≤0.05 px at the centre and ≤0.23 px at
  the wing** — against the 1.43-sensel median lateral displacement measured in §3.
- *The sign is preserved across all three kernels* (K6 slopes +0.865 … +0.964, all
  positive), which was the registered falsifier for (b)'s mechanism as described in §4. It
  did not fire.

**This addendum cannot revise (a) or (b), and I will not let it be read as corroborating
them.** Both were measured on raw CFA planes that never entered strehl's gather at all
(§3, §4), and `e6_payoff.py`'s warp-OFF arm already moved `dR` by 1.6 %. Three renders that
differ only in a post-election resampling kernel have no reach into which frame a channel
was elected from. The reach limit was written into the pre-registration before measuring.

**The veil.** The orchestrator cautioned that the occlusion veil and the fringing occupy the
same pixels. The σ = 6 px high-pass removes it (it is a low-frequency brightness anomaly),
and the robustness arm confirms this is not a knob: at σ = 3 and σ = 12 the K3 ratios move
to 1.015/1.013 and 1.054/1.026 (centre), and K2 to 1.112 and 1.079 — every verdict
unchanged. Had the veil been driving the numbers, a 4× change in high-pass scale would not
have left them alone.

### 12.5 One observation I am **not** claiming as a measurement

`ρ_cr` — chroma-to-luma ratio on edge pixels — is 0.366 at r = 125 px and 0.876 at
r = 2713 px, a factor of 2.39. That is the radius dependence §3 attributes to lateral CA,
and it is reassuring. **But the two ROIs are different subjects** (tan hair vs a warm
translucent wing), so this comparison confounds radius with subject and is worth exactly
nothing as evidence. §3's radius result stands on the gated ROI set with a permutation
null; this is an anecdote consistent with it, recorded here only so that nobody later
mistakes it for a second independent confirmation. Note also that ρ_cr = 0.366 at r = 125 px
means the fringe **does not vanish at the frame centre**, which is the qualitative
signature §4 relies on — but §4 already establishes that properly and does not need this.

### 12.6 Candidate facts from the addendum

- **P13.** strehl's warp gathers all four CFA planes with the same `Similarity` and the
  same `PlaneGeometry`, so `Resampler::Nearest`'s coordinate rounding is common-mode across
  R/G1/G2/B and cannot produce channel-differential displacement.
  (`align_cmd.rs::warp_frame_in_place`, `warpmap.rs::gather_into`.)
- **P14.** Catmull-Rom's lowpass, relative to a zero-order hold, is equivalent to a
  channel-independent Gaussian of **σ ≈ 0.49–0.61 px** on `bee-3-cpl`, measured by matching
  high-pass luma rms. This is a direct, kernel-only number and may interest M85.
- **P15.** The colour fringing in the shipped render is **not created by the gather kernel**:
  blurring the `nearest` arm to the Catmull-Rom arm's luma reproduces its chroma to
  ρ7 = 0.985/0.990 (hair ROI), against a same-procedure null of 0.950/0.973.
- **P16.** `Resampler::Nearest` *does* leave a CFA-axis-aligned lattice signature above
  0.7 Nyquist — **anisotropy 2.71–3.79 in luma, 0.39–0.71 in chroma.** A by-eye judgement of
  "colour fringing" on a `nearest` render is at risk of reading achromatic lattice structure
  and luma acutance as colour; scoring chroma against luma on the same pixels separates them.

### 12.7 Discipline

- **D4.** When scoring a by-eye claim about *colour*, always report the **luma** statistic on
  the same pixels beside it. Chroma and luma both rose here; only the pair distinguishes
  "more fringing" from "more acutance". Twice in this milestone a chroma panel was rendered
  that showed subject chromaticity rather than fringing until it was high-passed.
- **D5.** An invariance bar must be calibrated against the magnitude of the effect it is
  testing. K3's band was set from physics but never checked against the ×0.958 luma
  separation the two arms actually have; its own control failed at a blur 10× the effect.
  Reporting `rms_L` at each control point converted a failed control into a calibration
  curve, and motivated the substitution test (K7) that actually settled the question.

