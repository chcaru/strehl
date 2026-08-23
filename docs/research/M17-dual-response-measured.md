# M17 — the dual (mean, max) focus response, measured against the blind spot it was proposed to fix

**Status:** measured. Answers SYNTHESIS §10 open question 19 (fact 73).
**Experiment:** `experiments/m17-dual-response/` — harness, controls, chain script, committed CSVs.
**Reproduce:** `experiments/m17-dual-response/run-m17.ps1`, then `python m17_analyse.py`
(writes `data/m17-analysis.txt`; every headline below is a line in that file, and every
line in that file comes from a committed CSV with no RAW access).
**Pre-registered before any candidate number was read:** `experiments/m17-dual-response/PREREGISTRATION.md`, commit `8de785f`.

Every claim below carries a label. `MEASURED` = a number this milestone
produced. `VERIFIED` = a number produced twice through disjoint paths.
`DERIVED` = follows from a stated rule applied to measured numbers.
`ARGUED` = a mechanism I believe and have not isolated. `UNVERIFIED` = a
belief I am flagging so nobody quotes it as fact.

---

## The one-paragraph answer

**The dual does not survive, and the reason is not the one anybody predicted.**
The reviewer's premise was that a box max fixes the monotone-edge blind spot but
pays for it in noise. On this project's real data the *first* half is right and the
*second* half is **false**: `max-w13` fixes the blind spot (D 1.0000 → 0.2592) and its
flat-ROI merged-noise ratio actually *improves* by ΔN = **−0.0081**. What kills it is the
axis question 19 made mandatory: on M13's own 30 occluding-edge cells the max costs
**+18.91 DN** of mean reconstruction excess — **21.7×** the pre-registered +0.87 DN bar —
**and it is worse than the shipped operator in 28 of 30 cells (sign test p = 8.7 × 10⁻⁷).**
Every dual rule that dilutes the max enough to survive that axis (`tie5`, +0.05·max)
dilutes it enough to be **still blind on a ramp** (D = 0.9815), and costs **2.26×** the
shipped operator's wall clock. Meanwhile question 19's *third* candidate, which was
listed almost as an afterthought, passes every pre-registered gate: **`tenengrad-sq-w13`**
— squared gradient magnitude under the same box — takes D from **1.0000 to 0.1860**, is
quality-neutral on the edge cells (mean −2.14 DN, but **15/30 cells**, p = 1.00 — see
§4.2, this is *neutral*, not *better*), leaves noise alone (ΔN = −0.0015), keeps
`box_mean`'s O(1)-in-radius cost, and is **0.96×** the shipped operator's cost because it
drops a per-pixel `sqrt`. **Recommendation: do not ship the dual; ship candidate (c).**

**The single number that decides it:** `max`, the dual's active ingredient, costs
**+18.91 DN** on the cells M13 used to pick w13, against a pre-registered budget of
**+0.87 DN**. Candidate (c) costs **−2.14 DN** on the same cells.

---

## 0. Gates — all five passed before any candidate was believed

| Gate | Claim | Result | Label |
| --- | --- | --- | --- |
| **G1** | M13's headline reproduces from M13's committed CSVs with code written from scratch for M17 | argmin **w13**, mean regret **3.1708**, worst **12.1110**, zero-step **w40 ENDPOINT** at **0.0002** | VERIFIED |
| **G2** | the O(1) running max equals a naive per-pixel gather | **exact** equality, 9 radii × 9 geometries × 2 field types; 13 crate tests pass | VERIFIED |
| **G3** | M17's forked edge harness reproduces M13 digit-for-digit | **216 rows** identical | VERIFIED |
| **G4** | M17's forked noise harness reproduces M13 digit-for-digit | **24 rows** identical | VERIFIED |
| **G5** | fact 73 reproduces | `tenengrad-w13-nonorm` = 37.03703…–37.03704 at σ = 0,1,2,3 (D = 1.0000001); `tenengrad-w1-nonorm` = **0.375464** vs fact 73's 0.376 | VERIFIED |

`data/gate1-m13-reproduction.txt`, `data/m17check.txt`, and the `GATES` block of
`data/m17-analysis.txt` are the artefacts. G1 is a hard stop: the milestone was not
allowed to proceed until M13's number came back out of M13's own data.

**G2's negative control (project rule).** `src/boxmax.rs` was copied to
`data/boxmax.rs.bak`, the van Herk suffix index was regressed from `prefix[x + 2r]` to
`prefix[x + 2r - 1]`, three tests were confirmed **red**, and the file was restored **from
the copy** — never `git checkout --`. MEASURED.

**One trap worth recording (see §8, discipline 52).** `edge_mode`'s tile margin is
`max_regulariser_radius + max_support(measures) + probe.max_blur_radius()`. Dropping
`tenengrad-w40` (support 41) from the measure list, or shortening `--steps`, moves the
tile and therefore moves *the planted edge and the extracted corpus texture* —
`vertical@261` instead of M13's `vertical@274`, and every number changes. G3 only
passes with the **full** M13 measure set and the **full** step ladder present.

---

## 1. What was measured, and against what

Ten registered candidates plus four controls, on four axes.

| name | operator at the pixel | question 19 candidate |
| --- | --- | --- |
| `tenengrad-w13` | `box_mean₂₇(‖∇L‖) / σ` | **status quo** |
| `tgmax-w13` | `box_max₂₇(‖∇L‖) / σ` | the reviewer's non-TV-conserving term |
| `tgp95-w13`, `tgp99-w13` | exact windowed percentile | percentile variants |
| `tgdual-geo-w13` | `√(mean · max) / σ` | dual, geometric mean |
| `tgdual-sum-w13` | `(mean + max) / σ` | dual, sum |
| `tgdual-tie5-w13` | `(mean + 0.05·max) / σ` | dual, max as a tie-breaker |
| `tgrad-larger-w1-w13` | `max(mean₃, mean₂₇) / σ` | **(b)** dual-radius |
| `tgrad-geo-w1-w13` | `√(mean₃ · mean₂₇) / σ` | **(b)** dual-radius |
| `tenengrad-sq-w13` | `box_mean₂₇(‖∇L‖²) / σ²` | **(c)** tenengrad-sq |
| `tgrms-w13` | `√(box_mean₂₇(‖∇L‖²)) / σ` | post-hoc consistency arm |
| controls | `tenengrad-w0/w1/w3/w40` | fact 73's radius ladder |

**`tgrms-w13` is not a candidate — it is a trap-check.** Candidate (c) changes two
things at once: the response is squared *and* the normalisation degree goes 1 → 2. If
those two changes were separable, (c)'s result would be confounded. They are not:
`box_mean(g²)/σ² = (√(box_mean(g²))/σ)²`, a monotone map, and at regulariser width 1 the
winner map depends only on the per-pixel *ordering* across frames. So degree-2
normalisation is the *correct partner* of a squared response and there is no ÷σ² vs ÷σ
confound. DERIVED — and then VERIFIED empirically: `tgrms-w13` (degree 1) produced
**bit-identical** `excess_dn` and `acc` to `tenengrad-sq-w13` on all 18 cells of
`data/rms-consistency-109MSDCF.csv`.

---

## 2. Axis 1 — the blind spot itself

`D = response(defocused) / response(in-focus)` at the boundary column.
**D = 1.0000 is total blindness. Lower is better. D > 1 is worse than blind.**

### 2.1 The headline table

B1 = a synthetic 1000 DN hard step / 9-px ramp / broadband texture, σ = 0 → 3 blur.
B2 = M13's *real* compositor: two constant Lambertian layers, an occluding edge, real
sensor noise, frame 29 vs frame 20 (3.15 σ of extra defocus). MEASURED.

| candidate | **D step (op only)** | D step (shipped ÷σ) | **D ramp9** | D B2 real edge | D texture (positive control) |
| --- | --- | --- | --- | --- | --- |
| `tenengrad-w13` **(shipped)** | **1.0000** | **1.1299** | 0.9999 | 0.8547 | 0.1569 |
| `tgmax-w13` | 0.2592 | 0.2928 | 0.8587 | 0.2625 | 0.1237 |
| `tgp95-w13` | 0.2592 | 0.2928 | 0.8376 | 0.2481 | 0.1639 |
| `tgp99-w13` | 0.2592 | 0.2928 | 0.8587 | 0.2582 | 0.1532 |
| `tgdual-geo-w13` | 0.5091 | 0.5752 | 0.9266 | 0.4736 | 0.1393 |
| `tgdual-sum-w13` | 0.3102 | 0.3505 | 0.8940 | 0.3208 | 0.1316 |
| `tgdual-tie5-w13` | 0.7015 | 0.7925 | **0.9815** | 0.6688 | 0.1523 |
| `tgrad-larger-w1-w13` (b) | 0.3755 | 0.4242 | 0.8446 | 0.3142 | 0.1047 |
| `tgrad-geo-w1-w13` (b) | 0.6128 | 0.6923 | 0.9190 | 0.5182 | 0.1083 |
| **`tenengrad-sq-w13` (c)** | **0.1860** | **0.2375** | **0.6802** | **0.2001** | 0.0247 |
| `tenengrad-w1` (fact 73 control) | 0.3755 | 0.4242 | 0.8446 | 0.3142 | 0.0748 |
| `tenengrad-w0` | 0.2592 | 0.2928 | 0.8587 | 0.2480 | 0.0910 |

The `D B2` column is the **noisy** variant (3 seeds); the noiseless variant is in
`data/m17-analysis.txt` and differs by ≤ 0.06 for every candidate.

**Controls (mandatory, project rule 13).**
*Null:* two independent noise draws at σ = 0 vs σ = 0 give D = **1.0014–1.0339** for
every candidate — the ladder cannot manufacture discrimination out of noise. MEASURED.
*Positive, synthetic:* broadband texture, same blur ladder, every candidate
discriminates (0.13–0.76). MEASURED.
*Positive, real:* a real corpus texture patch, same ladder, every candidate
discriminates (0.02–0.16). MEASURED.
*Plant validity:* the plant reproduces fact 73's own radius ladder — `w13` = 1.0000,
`w1` = 0.3755 (fact 73: 0.376), `w3` = 0.7470 (fact 73: 0.747). VERIFIED.

### 2.2 The analytic predictions matched

For a Gaussian-blurred step of amplitude A, per row: `∫g dx = A` (TV, conserved — the
blind spot), `∫g² dx = A²/(2σ√π)`, `max g = A/(σ√(2π))`, and at σ = 0 the discrete Sobel
puts A/2 on each of the two straddling columns so `∫g² = A²/2` and `max g = A/2`:

| quantity | DERIVED | MEASURED | agreement |
| --- | --- | --- | --- |
| D(mean, σ3 vs σ0) | 1 (TV conserved) | 1.0000001 | 7 digits |
| D(sq, σ3 vs σ0) | `1/(σ√π)` = **0.18806** | **0.18603** | 1.1% |
| D(max, σ3 vs σ0) | `2/(σ√(2π))` = **0.26596** | **0.25916** | 2.6% |
| D(rms) = √D(sq) | √0.18603 = **0.43131** | **0.43131** | exact |

The measured 0.2592 for `box_max` also reproduces the orchestrator's independently
written synthetic value **0.2592** to four digits. VERIFIED.

### 2.3 Two findings beyond fact 73

**(i) The shipped normalised response is not merely blind, it is ±15% of pixel-dependent
junk straddling 1.0.** Read at the bright-side boundary column the shipped operator gives
D = **1.1299** — it *prefers the defocused frame*. Read one column to the dark side it
gives **0.8353**. The sign flips. MEASURED. The un-normalised operator gives
**1.0000001 on both sides** — the blindness is a property of the operator and is
pixel-side independent, but the ÷σ normalisation adds a term that is large compared to
the (zero) focus signal and whose sign depends on which side of the edge you sample.
ARGUED mechanism: blurring a bright-to-dark step lowers `L` at the bright-side boundary
pixel, lowering `σ(L)`, inflating `focus/σ`; on the dark side `L` rises and the effect
reverses. **Do not quote "the shipped operator prefers defocus" — quote "on a monotone
edge the shipped operator's ±15% of cross-frame variation is normalisation artefact, not
focus information."**

**(ii) The blind spot is not a hard-step artefact, but the hard step is its easiest
case.** On a 9-px linear ramp — the honest model of specular falloff on a carapace — the
max's advantage largely evaporates (0.8587 vs the shipped 0.9999) because a wide ramp's
peak gradient is already flat, so blurring it barely moves the peak. Only
`tenengrad-sq-w13` retains real discrimination there (**0.6802**). MEASURED. The ramp is
the adversarial control that separates the candidates; the step does not.

**(iii) On an untextured edge, percentiles collapse onto the max.** `tgmax`, `tgp95`,
`tgp99` and `tenengrad-w0` all read D = 0.2483 on B2 noiseless. The gradient ridge is a
full line through the window, so any percentile above the ridge's area fraction *is* the
max. They separate only on real texture (p95 = 0.1639, max = 0.1237). MEASURED —
the pre-registration predicted exactly this and it is why both were registered.

---

## 3. Axis 2 — the mandatory guard: M13's 36 occluding-edge cells

Question 19's guard: *"any fix must be scored on the same edge cells M13 used, so a
repair cannot silently regress the textured-occlusion case that picked w13."*
Cell = stack × shape × step, 3 seeds averaged, regulariser width 1, identical ROIs,
frames, σ₀, α, noise scale, band and baseline to M13. Primary statistic: mean
`excess_dn` over the **30 depth-step** cells (absolute, not regret — pre-registered,
per discipline 32). Lower is better.

| candidate | **mean `excess_dn`** | **ΔE vs w13** | worst cell | zero-step stratum |
| --- | --- | --- | --- | --- |
| **`tenengrad-sq-w13`** (c) | **22.7013** | **−2.1447** | 47.4121 | 15.6367 |
| `tgdual-tie5-w13` | 23.1729 | −1.6732 | 47.2994 | 15.4978 |
| `tenengrad-w13` **(shipped)** | 24.8460 | +0.0000 | 59.7734 | 20.0868 |
| `tgp95-w13` | 26.3006 | +1.4545 | 57.2953 | 16.6725 |
| `tgdual-geo-w13` | 29.5807 | +4.7346 | 49.5026 | 15.0344 |
| `tgp99-w13` | 37.3433 | +12.4973 | 73.2326 | 15.1765 |
| `tgdual-sum-w13` | 39.1482 | +14.3022 | 83.5465 | 14.9438 |
| `tgrad-larger-w1-w13` (b) | 40.2584 | +15.4123 | 90.9275 | 39.5055 |
| **`tgmax-w13`** | **43.7571** | **+18.9111** | 105.4634 | 15.0293 |
| `tgrad-geo-w1-w13` (b) | 50.3181 | +25.4721 | 98.9109 | 54.1118 |
| `tenengrad-w40` (M13 control) | 59.3818 | +34.5358 | 153.4223 | 14.2686 |

MEASURED. The pre-registered budget is **+0.87 DN** — M13's own basin-flatness
threshold, re-used by M15 (facts 81, 60), against a seed noise floor of 0.193 DN.

**The pure max misses it by 21.7×.** That is the milestone's deciding number. Every
dual rule that keeps a meaningful max weight inherits a large fraction of it:
`sum` +14.30, `geo` +4.73. Only `tie5` (max weighted 0.05) survives — and §2.1 shows
`tie5` is still blind on a ramp at 0.9815.

### 3.1 Why the max is so bad here — ARGUED

The cells are *textured* occluding edges. An extremum over a 27×27 window is spatially
non-local in a way a mean is not: the window max is inherited from the single strongest
gradient anywhere in the window, so the response is *constant* across a plateau of
pixels around every strong feature and the argmax across frames becomes a coin flip over
that plateau. The mean varies smoothly and the winner map varies smoothly with it. This
is the same "extremum statistics are non-local" objection that killed the ring
regulariser's max variant, and it is a *sharper* penalty than the noise penalty the
reviewer anticipated. UNVERIFIED as a mechanism — I did not isolate it.

### 3.2 The adversarial re-read: candidate (c)'s gain is NOT robust

The pre-registration's *tertiary* statistic is head-to-head cell counts in M13's idiom.
It changes the story and it is reported here as the honest headline. MEASURED:

| candidate | wins / 30 | median paired Δ | worst single-cell regression | best gain | sign test p |
| --- | --- | --- | --- | --- | --- |
| **`tenengrad-sq-w13`** | **15 / 30** | **−0.2748** | **+10.1009** | −18.9568 | **1.00000** |
| `tgdual-tie5-w13` | 14 / 30 | +0.2120 | +6.9321 | −15.3074 | 0.85554 |
| `tgp95-w13` | 14 / 30 | +1.2406 | +22.8320 | −20.3024 | 0.85554 |
| `tgdual-geo-w13` | 7 / 30 | +4.3925 | +29.2866 | −12.8041 | 0.00522 |
| `tgdual-sum-w13` | 3 / 30 | +9.3751 | +63.3304 | −12.8001 | 0.00001 |
| `tgp99-w13` | 3 / 30 | +8.7773 | +52.8102 | −13.5747 | 0.00001 |
| `tgmax-w13` | **2 / 30** | +13.4368 | +85.2474 | −12.7728 | **8.7e-7** |
| `tgrad-larger-w1-w13` | 0 / 30 | +11.9676 | +31.9201 | +6.6801 | ≈0 |
| `tgrad-geo-w1-w13` | 0 / 30 | +16.5735 | +62.7351 | +7.0836 | ≈0 |
| `tenengrad-w40` | 1 / 30 | +21.0111 | +125.4640 | −9.2829 | ≈0 |

**Candidate (c)'s −2.14 DN mean is a heavy-tail artefact, not a broad win.** It wins
exactly half the cells, its median paired delta is −0.27 DN (below M13's own 0.87 DN
indifference bar), and the sign test is a perfect coin flip. Split by shape:

| stack | shape | mean Δ | cells improved |
| --- | --- | --- | --- |
| 109MSDCF | `bar@274w24` | +0.1218 | 3/5 |
| 109MSDCF | `horizontal@210` | **+2.4891** | **0/5** |
| 109MSDCF | `vertical@274` | −1.3990 | 4/5 |
| 119MSDCF | `bar@274w24` | −1.0743 | 3/5 |
| 119MSDCF | `horizontal@210` | **+3.5583** | **0/5** |
| 119MSDCF | `vertical@274` | **−16.5641** | **5/5** |

The whole mean gain is one shape in one stack. **Candidate (c) loses uniformly on
`horizontal@210` in both stacks (0/10 cells, +2.5 and +3.6 DN).** The correct claim is
**quality-NEUTRAL, with a shape-dependent sign** — not "better". It passes the
pre-registered gate `ΔE ≤ +0.87` on the mean, and it should be *sold* as neutral.
This does not change the recommendation — the point of candidate (c) is that it buys the
blind-spot fix for free, and "free" is exactly what a coin flip means — but it removes
the temptation to advertise a quality win. MEASURED.

**The zero-step null stratum** (fact 61: no interior optimum exists there) shows every
candidate *below* the shipped operator, `tenengrad-w13` being the worst at 20.09 DN.
That stratum cannot discriminate window or operator quality and is reported, not decided
on, exactly as registered.

---

## 4. Axis 3 — noise, and the falsified premise

N = merged-noise ratio on flat ROIs (M11/M13 methodology): median over the 4 committed
flat ROIs of a stack, then mean over the two stacks. ROIs taken from the committed
`data/noise-*.csv`, per-stack discriminators (fact 88), never carried across stacks.

| candidate | **N pooled** | **ΔN** | 109MSDCF | 119MSDCF |
| --- | --- | --- | --- | --- |
| `tenengrad-w13` **(shipped)** | **1.08637** | +0.00000 | 1.07661 | 1.09613 |
| `tenengrad-sq-w13` (c) | 1.08491 | **−0.00147** | 1.07175 | 1.09806 |
| `tgp95-w13` | 1.08592 | −0.00045 | 1.07081 | 1.10103 |
| `tgp99-w13` | 1.08366 | −0.00271 | 1.06937 | 1.09795 |
| `tgdual-tie5-w13` | 1.08324 | −0.00313 | 1.07171 | 1.09478 |
| `tgdual-geo-w13` | 1.08084 | −0.00553 | 1.06355 | 1.09813 |
| `tgdual-sum-w13` | 1.07882 | −0.00756 | 1.05295 | 1.10468 |
| **`tgmax-w13`** | 1.07826 | **−0.00811** | 1.04771 | 1.10881 |
| `tgrad-geo-w1-w13` (b) | 1.27890 | **+0.19252** | 1.29321 | 1.26459 |
| `tgrad-larger-w1-w13` (b) | 1.32312 | **+0.23675** | 1.33888 | 1.30737 |

MEASURED. The shipped operator's N = **1.08637** pooled and **1.07661** on 109MSDCF's
`2272,1344,256,256` ROI reproduce the project's recorded 1.0864 / 1.067839 exactly —
a fifth independent tie to prior data. VERIFIED.

**The reviewer's premise about noise is falsified on this data.** The proposal, and
pre-registered prediction 2, both said the max would fail on noise (predicted
ΔN > +0.05). Measured: **ΔN = −0.0081**. The max is *better* than the shipped operator on
the merged-noise axis. ARGUED explanation: N is measured after the *merge*, and a window
max is spatially constant over plateaus, so the winner map it produces is *smoother*
across a flat ROI than the mean's — the same non-locality that destroys it on Axis 2
helps it here. The orchestrator's synthetic finding (CoV 0.0265 for max vs 0.0065 for
mean on a noisy step) is not contradicted — it measures the *response*'s coefficient of
variation, not the *merged output*'s noise. **Both are true; only one of them is the
axis the project ships against.**

**So the honest statement of the trade is: there is no noise trade.** The max's
blind-spot fix is not paid for in noise. It is paid for in reconstruction quality on
textured occluding edges, at 21.7× the budget. The dual was proposed to buy off a cost
that does not exist, at the price of the one that does.

**Question 19's candidate (b) dies on noise instead.** `tgrad-*` cost ΔN = +0.19 to
+0.24, roughly **10–12×** the +0.02 threshold — and they fail Axis 2 as well (0/30 cells).
Worse, `tgrad-larger-w1-w13` reads *exactly* the same D as `tenengrad-w1` on both B1
(0.3755) and B2 (0.3142): near any structure, the pointwise max of a radius-1 and a
radius-13 field is just the radius-1 field. Candidate (b) is not a dual radius, it is a
radius-1 operator with extra steps. MEASURED. **Candidate (b) is dead.**

---

## 5. Axis 4 — cost

Alternating sweep direction, 10 passes, **per-setting minimum** (discipline 30, project
rule 16), 512×512, release build.

### 5.1 The filter, swept in radius

ms/frame/Mpx, per-setting minimum:

| filter | r=1 | r=2 | r=3 | r=5 | r=8 | **r=13** | r=21 | r=34 | r=40 | **max/min** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `box_mean` | 1.478 | 1.484 | 1.481 | 1.479 | 1.475 | **1.473** | 1.467 | 1.459 | 1.455 | **1.02×** |
| `box_max` (vHGW) | 1.357 | 1.643 | 1.899 | 2.438 | 3.087 | **3.966** | 5.158 | 6.262 | 6.656 | **4.90×** |
| `window_p95` (exact) | 17.0 | — | 130.8 | — | 400.4 | **818.2** | 1949.8 | — | 5979.5 | **352×** |

MEASURED. `box_mean` is flat: quoted as a **bound**, `≤ 1.02×` across r = 1…40, not a
point value. `box_max` is **not** flat.

**This falsifies pre-registered prediction 7 and it is the milestone's most
uncomfortable result.** Van Herk / Gil-Werman is provably O(1) *in comparisons* — ≈3 per
element regardless of radius (DERIVED, and the implementation's comparison count was
checked). The **measured wall clock is not O(1)**: 4.90× over the ladder, and 2.69×
`box_mean` at the shipped r = 13. Two hypotheses were tested and **falsified**:

1. *Allocation.* The per-block prefix/suffix arrays were hoisted into a reusable
   `MaxScratch` and re-used across calls. Profile unchanged (≈4.9× before and after).
   MEASURED.
2. *Runtime modulo.* The `% k` in the vHGW inner loops was removed by iterating block by
   block. Profile unchanged. MEASURED.

Accounted-for terms — the max-ops fraction rising from 2/3 to 80/81, and padded length
growing 16% — explain only ≈1.7× of the 4.90×. **The remaining ≈2.9× is unexplained.**
Empirically the curve tracks `√r` to within ±5% over r = 2…40, which I record as an
observation and *not* as a claim about the algorithm. A better implementation may well
be flat; I did not find one in the time available. This is a limitation of **this
implementation**, and the honest form of the claim is: *vHGW is O(1) in comparisons
(DERIVED); my implementation of it is not O(1) in wall clock (MEASURED); the gap is
unexplained (UNVERIFIED).*

The `window_p95` row is from an auxiliary run that overlapped the edge sweep (spreads to
+127%) and its absolute values are not trustworthy — but the growth is three orders of
magnitude, so the ordering is not in doubt. The exact percentile is not shippable
without a sliding histogram, which was pre-registered as out of scope and not built.

### 5.2 The whole measure, at the shipped radius

ms/frame/Mpx, min over alternating passes, r = 13:

| measure | cost | vs shipped |
| --- | --- | --- |
| `tenengrad-w0` | 1.942 | 0.57× |
| **`tenengrad-sq-w13`** (c) | **3.279** | **0.96×** |
| `tenengrad-w40` | 3.385 | 0.99× |
| `tenengrad-w13` **(shipped)** | 3.414 | 1.00× |
| `tgrms-w13` | 3.483 | 1.02× |
| `tgrad-larger-w1-w13` (b) | 5.633 | 1.65× |
| `tgrad-geo-w1-w13` (b) | 5.728 | 1.68× |
| `tgmax-w13` | 5.836 | 1.71× |
| `tgdual-tie5-w13` | 7.725 | **2.26×** |
| `tgdual-sum-w13` | 7.913 | 2.32× |
| `tgdual-geo-w13` | 8.221 | 2.41× |

MEASURED. **Candidate (c) is cheaper than the shipped operator** — it computes
`gx² + gy²` and skips the per-pixel `sqrt` entirely. `tgrms-w13` puts one `sqrt` back
(on the box output) and lands at 1.02×, which corroborates the mechanism. Every
max-based candidate is ≥ 1.71×, and every *dual* is ≥ 2.26×, because a dual pays for
both windows.

**The conclusion is robust to the O(1) argument.** Even if a flat vHGW existed, the dual
would still cost 2.26× at the shipped radius while candidate (c) costs 0.96×.

---

## 6. The pre-registered decision

SHIP iff `D ≤ 0.90` **and** `ΔE ≤ +0.87 DN` **and** `ΔN ≤ +0.02` **and** cost is O(1)
in the radius. (The numeric operationalisation of the last clause — max/min ≤ 1.25×
over r = 1…40 — is **post-hoc**; it is disclosed here and it is not load-bearing,
because `box_mean` measures 1.02× and `box_max` 4.90×, so nothing lands near any
plausible bar.)

| candidate | D (step, ÷σ) | ΔE (DN) | ΔN | radius-flat? | **verdict** |
| --- | --- | --- | --- | --- | --- |
| `tenengrad-w13` (shipped) | 1.1299 | +0.0000 | +0.00000 | yes | NO (blind) |
| `tgmax-w13` | 0.2928 | **+18.9111** | −0.00811 | NO | **NO** |
| `tgp95-w13` | 0.2928 | +1.4545 | −0.00045 | NO | FLAG (nominal) |
| `tgp99-w13` | 0.2928 | +12.4973 | −0.00271 | NO | **NO** |
| `tgdual-geo-w13` | 0.5752 | +4.7346 | −0.00553 | NO | **NO** |
| `tgdual-sum-w13` | 0.3505 | +14.3022 | −0.00756 | NO | **NO** |
| `tgdual-tie5-w13` | 0.7925 | −1.6732 | −0.00313 | NO | **NO (cost)** |
| `tgrad-larger-w1-w13` (b) | 0.4242 | +15.4123 | +0.23675 | yes | **NO** |
| `tgrad-geo-w1-w13` (b) | 0.6923 | +25.4721 | +0.19252 | yes | **NO** |
| **`tenengrad-sq-w13`** (c) | **0.2375** | **−2.1447** | **−0.00147** | **yes** | **SHIP** |

**Exactly one candidate reaches SHIP, and it is not a dual.** `tgp95-w13` reaches FLAG
on the letter of the rule — the FLAG branch, as written, does not carry the cost clause —
but it is 352× in radius and 818 ms/frame/Mpx at r = 13, so it is not implementable
without a sliding histogram that was pre-registered as out of scope. I record the FLAG
as nominal rather than quietly re-writing the rule after the fact.

Note the pre-registration's §8 abandonment criterion fired on its own terms: *"If `max`
alone passes ΔN, the dual is unnecessary complexity and the recommendation is `max` or
nothing."* `max` alone **does** pass ΔN (−0.0081) — and `max` alone fails ΔE by 21.7×.
So: **nothing**, on the dual branch. The dual is abandoned by its own registered rule.

Note also that had the cost clause been dropped, `tgdual-tie5-w13` would have tied on
the registered tie-break (smallest ΔN: −0.00313 vs −0.00147). It is disqualified by the
cost clause, and independently it is the weakest blind-spot fix in the set — **still
blind on a ramp at D = 0.9815**, which is the case the blind spot actually shows up in.
Both routes reach the same place. DERIVED.

### 6.1 The registered predictions, scored

| # | prediction | outcome |
| --- | --- | --- |
| 1 | `max-w13` fixes the blind spot, `D ≤ 0.30` | **CONFIRMED** (0.2592) |
| 2 | `max-w13` fails ΔN, predicted `> +0.05` | **FALSIFIED** (−0.0081) |
| 3 | at least one dual passes ΔN with `D ≤ 0.90` | CONFIRMED (`tie5`), but moot |
| 4 | `tie5` has the smallest ΔN of any blind-spot fix | **FALSIFIED** (`max` −0.0081 < `tie5` −0.0031) |
| 5 | `sq-w13` passes the blind spot and **fails** ΔE | **FALSIFIED** — it passes both |
| 6 | `dualrad-*` fail ΔN | **CONFIRMED** (+0.193, +0.237) |
| 7 | the running max is O(1) in radius, flat, `< 2×` `box_mean` | **FALSIFIED** (4.90×; 2.69× at r=13) |
| 8 | candidate (a) — cross-frame spread flags the monotone edge | partially CONFIRMED: the un-normalised cross-frame spread is 1e-7 on B1's step (an unmistakable flag) and **0.145** on the realistic B2 edge, against **0.843** on a real texture patch — a real but ~6× weaker signal |

**Four of eight registered predictions were falsified.** That is the value of having
written them down.

---

## 7. Recommendation

**DO NOT SHIP the dual (mean, max), in any of the three combination rules tested, and do
not ship `max` alone or either dual-radius form.**

**DO ship, or at minimum register as the new default candidate, question 19's candidate
(c): `tenengrad-sq-w13` = `box_mean₂₇(gx² + gy²) / σ²`.** It is the only arm that clears
all four pre-registered conditions. It takes the blind-spot ratio from **1.0000 to
0.1860** (from 0.9999 to 0.6802 on the harder ramp plant), is quality-neutral on M13's
occluding-edge cells (15/30, median −0.27 DN, mean −2.14 DN), leaves merged noise alone
(ΔN = −0.0015), holds `box_mean`'s ≤1.02× radius-flat cost, and is **0.96×** the shipped
operator's wall clock.

**The caveat that must travel with the recommendation:** w13 was optimised by M13 *for
the mean operator*. There is no reason to think it is the optimum window for a squared
one, and the squared response's effective window is narrower (it weights the ridge
centre harder). The shape-split in §3.2 — a uniform loss on `horizontal@210`, a large win
on `vertical@274` — is consistent with a window mismatch. **`tenengrad-sq` should get its
own window sweep before it is called shipped.**

---

## 8. What I could not measure

1. **Why `box_max` is not flat in radius.** Two hypotheses falsified, ≈2.9× unexplained.
   This does not change the verdict (§5.2) but it is an open implementation question.
2. **A constant-time percentile.** A sliding histogram was pre-registered as out of
   scope. The exact percentile is 352× over the radius ladder and unusable as measured.
3. **Any window other than w13 for candidate (c).** This is the largest gap and it is
   the one that could *move* the recommendation's magnitude (not its sign) — see §7.
4. **Real, non-planted monotone-edge subjects.** B2 uses M13's compositor with two
   constant Lambertian layers — a synthetic monotone edge composited through real optics,
   real sensor noise and the real frame ladder, but still a plant. The project has no
   captured subject annotated as an untextured smooth-gradient region.
5. **Regulariser widths > 1.** All 594 rows per stack are at width 1, inheriting M13's
   scope limit (SYNTHESIS question 17). A wider regulariser might blunt the max's
   non-locality penalty on Axis 2, which is the one number that decides this milestone.
6. **A third stack.** 119MSDCF and its `D:\personal\macro` copy are byte-identical
   (fact 69), so this is a two-stack result, as M13's was.
7. **The `tie5` weight.** 0.05 was fixed in advance and not swept. A weight between
   0.05 and 1.0 might trade §2.1's ramp blindness against §3's quality cost more
   favourably — but it would still pay the ≥2.26× cost, so I did not pursue it.

---

## 9. Proposed SYNTHESIS §4 facts (numbered from 100)

| # | Fact | Consequence | Source |
| --- | --- | --- | --- |
| 100 | The box **max** of \|∇L\| does fix fact 73's monotone-edge blind spot: on a 1000 DN hard step, blur σ0→σ3, D goes from **1.0000** (mean, blind) to **0.2592**, matching the analytic prediction 0.2660 to 2.6%. | The reviewer's core claim is correct and is now VERIFIED twice from disjoint code. | M17 §2.1, §2.2; `experiments/m17-dual-response/data/blindspot-nonorm.csv` |
| 101 | The box max **costs +18.91 DN mean `excess_dn`** on M13's 30 occluding-edge cells — **21.7×** the pre-registered +0.87 DN bar — and loses **28 of 30** cells (sign test p = 1.2e-6). | The dual (mean, max) is rejected. Question 19's proposed fix fails the guard question 19 itself made mandatory. | M17 §3, §3.2; `data/edge-{109,119}MSDCF.csv` |
| 102 | The max's cost is **not** noise. Its flat-ROI merged-noise ratio *improves*: ΔN = **−0.0081** (N 1.08637 → 1.07826). Pre-registered prediction 2 (ΔN > +0.05) is falsified. | The premise the dual was designed around does not hold on real data. A response-level CoV does not predict merged-output noise; only the merged statistic decides. | M17 §4; `data/noise-{109,119}MSDCF.csv` |
| 103 | **`tenengrad-sq-w13`** (question 19 candidate (c), `box_mean₂₇(gx²+gy²)/σ²`) is the only arm clearing all four pre-registered gates: D **0.1860**, ΔE **−2.14 DN**, ΔN **−0.0015**, radius-flat cost, and **0.96×** the shipped operator's wall clock. | Recommended replacement for `tenengrad-w13`. The blind-spot fix is available for free — cheaper, in fact, since it drops a per-pixel `sqrt`. | M17 §6, §5.2; `data/m17-analysis.txt` |
| 104 | Candidate (c)'s quality gain is **not robust**: 15/30 cells, median paired Δ **−0.27 DN**, sign test **p = 1.00**. The −2.14 DN mean is one shape in one stack (`vertical@274`/119MSDCF, −16.56); it loses **0/10** on `horizontal@210`. | Sell candidate (c) as **quality-neutral**, never as a quality win. A mean over 30 cells must always be paired with its sign test. | M17 §3.2 |
| 105 | `tenengrad-sq` and `√(box_mean(g²))` (degree-1 normalisation) produce **bit-identical** `excess_dn` and `acc` on all 18 cells — the squared response and degree-2 normalisation are a monotone pair, so candidate (c) carries **no ÷σ² vs ÷σ confound**. | Any future "squared vs magnitude" comparison must apply the matching normalisation degree, or it measures the normalisation, not the operator. | M17 §1; `data/rms-consistency-109MSDCF.csv` |
| 106 | Question 19 candidate (b), dual-radius, is dead on two axes: ΔN = **+0.193** (geo) and **+0.237** (larger), ~10–12× the threshold, and ΔE = +15.4 / +25.5 DN (0/30 cells). `tgrad-larger-w1-w13` reads *exactly* `tenengrad-w1`'s D on every plant — near structure the pointwise max of radius 1 and radius 13 **is** radius 1. | Do not revisit dual-radius. It is a radius-1 operator with extra cost, and M13 already measured radius-1's noise at N ≈ 1.34. | M17 §4, §2.1 |
| 107 | On a **9-px ramp** — the realistic monotone gradient — the max's advantage largely evaporates (D 0.8587 vs the mean's 0.9999) while `tenengrad-sq` holds **0.6802**. A hard step is the easiest case for an extremum statistic. | Fact 73's hard-step plant *overstates* what a max buys. Any future blind-spot claim must include a ramp plant. | M17 §2.3(ii); `data/blindspot-nonorm.csv` |
| 108 | The shipped operator's monotone-edge reading is **±15% of normalisation artefact straddling 1.0**: D = **1.1299** at the bright-side boundary column and **0.8353** one column to the dark side. The **un-normalised** operator reads 1.0000001 on **both** sides. | Extends fact 73: the shipped focus field on a monotone edge is not merely constant, it carries pixel-side-dependent junk of the same magnitude as a real focus signal. Confidence derived from it is worse than uninformative. | M17 §2.3(i); `data/blindspot-norm.csv`, `data/blindspot-nonorm.csv` |
| 109 | On an untextured edge, `max`, `p95`, `p99` and `w0` all read **identically** (D = 0.2483 on the realistic B2 plant): the gradient ridge spans the window, so any percentile above the ridge's area fraction **is** the max. They separate only on texture (p95 0.164 vs max 0.124). | Percentile variants are not a distinct family on the case they were proposed for. Register a textured plant or the comparison is vacuous. | M17 §2.3(iii); `data/blindspot-edge.csv` |
| 110 | Van Herk / Gil-Werman is O(1) in **comparisons** (≈3/element, DERIVED) but this implementation is **not O(1) in wall clock**: **4.90×** over r = 1…40 and **2.69×** `box_mean` at r = 13, against `box_mean`'s ≤ **1.02×** bound. Hoisting all allocation and removing the inner-loop modulo changed nothing; ≈2.9× of the growth is unexplained. | Fact 66's "widening the window is free" does **not** generalise to a running max. Any max-based operator must be re-timed, not assumed. | M17 §5.1; `data/boxcost.csv` |
| 111 | At the shipped radius, whole-measure cost is **0.96×** for `tenengrad-sq-w13`, **1.71×** for `max`, and **≥2.26×** for every dual (a dual pays for both windows). `tenengrad-sq` is cheaper than the shipped operator because it never computes a per-pixel `sqrt`. | The dual's rejection is robust even to a hypothetical flat vHGW. | M17 §5.2; `data/cost-measures.csv` |
| 112 | Exact windowed percentile is **352×** over the radius ladder (818 ms/frame/Mpx at r = 13). | A percentile focus measure is unshippable without a sliding histogram; none was built. | M17 §5.1; `data/boxcost-pct.csv` |

## 10. Proposed SYNTHESIS §5 discipline items (numbered from 50)

| # | Discipline |
| --- | --- |
| 50 | **A mean over cells is not a result until its sign test is next to it.** M17's candidate (c) shows a −2.14 DN mean improvement and a 15/30 win rate with p = 1.00 — the mean is a heavy tail, the operator is neutral. Report mean, median paired delta, win count and worst single-cell regression together, or the mean will be quoted as a win it is not. |
| 51 | **Before claiming two operators differ, check they are not a monotone reparameterisation of each other.** At regulariser width 1 the winner map depends only on the per-pixel *ordering* across frames, so any strictly increasing map of the response is the *same operator*. M17 verified `tenengrad-sq` ≡ `√box_mean(g²)` bit-for-bit on 18 cells; without that check its degree-2 normalisation would have looked like a confound. |
| 52 | **A planted-scene harness whose tile margin depends on the measure set will silently move the scene when you change the measure set.** M17's edge probe rendered `vertical@261` instead of M13's `vertical@274` purely because a wide measure was dropped from the list; every number changed and nothing warned. Pin the margin, or pin the full measure list and step ladder, and gate on digit-for-digit reproduction of the prior milestone's rows before believing any new row. |
| 53 | **When a timing profile is not flat, report which hypotheses you falsified, not just the number.** M17 tested allocation (hoisted scratch) and the inner-loop modulo (block iteration) on `box_max`; both changed nothing, ≈2.9× remains unexplained. Recording the *failed* explanations is what stops the next milestone re-running them. |
| 54 | **An algorithmic complexity claim and a wall-clock claim are different claims and need different labels.** vHGW is O(1) in comparisons (DERIVED) and 4.90× in wall clock (MEASURED). Quoting the first as if it settled the second would have shipped a 2.7× regression. |

---

## 11. Question for the repo owner

**Candidate (c), `tenengrad-sq-w13`, beats the shipped operator on the blind spot
(1.0000 → 0.1860), ties it on quality (15/30 cells, p = 1.00), ties it on noise
(ΔN = −0.0015), and is *cheaper* (0.96×). But w13 was chosen by M13 for the **mean**
operator, and §3.2 shows candidate (c)'s per-shape sign is not uniform — consistent with
a window mismatch.**

**Do you want M18 to run M13's window ladder again for `tenengrad-sq` before this is
called shipped — or do you want (c) landed at w13 now, behind a flag, with the sweep as
follow-up?** My own view: land it behind a flag, sweep in M18. The blind spot is a
correctness hole in the confidence story and a neutral-quality, cheaper operator that
closes it should not wait on an optimisation.
