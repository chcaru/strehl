# M17 — PREREGISTRATION

**Question (SYNTHESIS §10 q19, fact 73).** The shipped focus operator
`focus = box_mean_13(|∇L|) / σ_L` is *exactly* blind to defocus on an untextured
monotone edge, because the mean of `|∇|` over a window wider than the blur is
total variation ÷ area and blur conserves total variation. Does a dual
`(mean, max)` response fix it without costing noise performance?

**Committed before any candidate was run.** Gate 1 (reproduction of M13's already
published headline from M13's own committed CSVs) is the only measurement that
precedes this file, and it is a reproduction of someone else's number, not a
result of mine.

Status: **PREREGISTERED.** Nothing below may be re-cut after the fact; a
threshold that turns out to be on the wrong quantity is to be reported as firing
and then overridden **explicitly**, on stated grounds (SYNTHESIS discipline 27).

---

## 0. Gates that must pass before any candidate number is believed

| Gate | What | Pass condition |
| --- | --- | --- |
| **G1** | M13's headline, recomputed from `experiments/m13-window-depth/data/edge-{109,119}MSDCF.csv` by code written for M17 | argmin mean regret **w13 = 3.171 DN**, argmin worst regret **w13 = 12.111 DN**, zero-step argmin **w40 ENDPOINT at 0.000 DN** |
| **G2** | O(1) running max (van Herk / Gil-Werman), against a naive 2-D gather with the identical clamped-window rule | exact equality (max is a selection, not an accumulation — no tolerance is warranted) on random, adversarial and degenerate inputs |
| **G3** | The M17 edge harness is M13's harness. Run M13's edge sweep parameters with `tenengrad-w13` and `tenengrad-w40` in the measure set (so `max_support` and hence the tile geometry are identical) | every printed digit of the `tenengrad-w13` and `tenengrad-w40` rows equals M13's committed `edge-*.csv` |
| **G4** | The M17 noise harness is M13's harness | `tenengrad-w13` and `tenengrad-w0` ratios equal M13's committed `noise-*.csv` on all 8 flat ROIs |
| **G5** | Fact 73 reproduces on M17's own blind-spot plant | status-quo `mean` reads the same value at σ = 0, 1, 2, 3 to ≥ 6 significant figures, and that value is `A/27` for a step of amplitude `A` |

**If G1 fails the milestone stops.** If G3 or G4 fails, no candidate comparison is
valid and the harness must be fixed before any number is quoted.

---

## 1. Candidates

All are aggregators of the **same** Sobel gradient magnitude `g = √(Gx²+Gy²)`
(`/8`-scaled, replicate-clamped) over the **same** 27×27 window (radius 13), then
divided by `σ_L(p)` from the injected noise model, exactly as
`crates/strehl-core/src/focus.rs` does. Only the aggregator changes, so the
comparison prices the aggregator and nothing else (SYNTHESIS discipline 210).

| Name | Aggregator | Role |
| --- | --- | --- |
| `mean-w13` | `box_mean_13(g)` | **status quo** — `tenengrad-w13`, the shipped operator |
| `max-w13` | `box_max_13(g)` | the reviewer's non-TV-conserving statistic, alone |
| `p95-w13` | 95th percentile of `g` in the window | percentile variant |
| `p99-w13` | 99th percentile of `g` in the window | percentile variant |
| `dualgeo-w13` | `√(mean·max)` | dual, geometric mean |
| `dualsum-w13` | `mean + max` | dual, arithmetic |
| `dualtie-w13` | `mean + 0.05·max` | dual, "mean with a max tie-break" |
| `dualrad-max` | `max(box_mean_1(g), box_mean_13(g))` | question 19 candidate **(b)**, max form |
| `dualrad-geo` | `√(box_mean_1(g)·box_mean_13(g))` | question 19 candidate **(b)**, spread form |
| `sq-w13` | `box_mean_13(g²)`, divided by `σ_L²` | question 19 candidate **(c)**, `tenengrad-sq` |

**Registered in advance: `product` and `geometric mean` are the same candidate.**
`mean·max` and `√(mean·max)` are related by a positive monotone map, and the merge
consumes only the *ranking* of the field across frames at a fixed pixel, so at
regulariser width 1 they produce bit-identical winner maps. Only `dualgeo-w13`
is run; the product is not a separate arm and will not be reported as one.

Question 19 candidate **(a)** — "keep the wide window and let cross-frame-spread
confidence handle it" — is not an operator and is scored separately in §4.4.

## 2. Axis 1 — the blind spot (the headline)

### 2.1 Plant

**B1, analytic.** A hard vertical step of amplitude `A = 1000` DN on an otherwise
flat field, Gaussian-blurred at σ ∈ {0, 1, 2, 3, 4}, no noise. This is fact 73's
own plant and reproducing `A/27 = 37.037037` at every σ for `mean-w13` is gate G5.

**B2, realistic.** The same monotone edge rendered through M13's two-layer
occlusion compositor with real sensor noise from the injected model, over M13's
own 41-frame ladder (`sigma0 = 0.8`, `alpha = 0.35`), both layers **untextured**
(constant DN, different levels) so the only content is the boundary.

### 2.2 Statistic

**Blind-spot discrimination ratio**

```
D = r(defocused) / r(in-focus)
```

evaluated on the boundary column/row, where `r` is the candidate's field. On B1
the pair is σ = 3 against σ = 0 (fact 73's pair). On B2 the pair is the frame
`w + Δ` against `w`, with Δ = 9 frames, which is `alpha·Δ = 3.15` σ of extra blur
— the same optical increment as B1's pair.

`D = 1.0000` is total blindness. `D < 1` is discrimination; smaller is better.

### 2.3 Controls (mandatory — SYNTHESIS rule 13, discipline 33)

* **Null.** The identical plant with **no** blur change: σ = 0 against σ = 0 with
  an independent noise realisation. Every candidate must read `D ≈ 1.0000`. A
  candidate that reads `D` far from 1 here is responding to the noise
  realisation, and its B2 number means nothing.
* **Positive control.** Broadband texture (a real corpus tile) on the same ladder,
  where the status quo is known to work (fact 73: 45.13 → 2.24). Every candidate
  must discriminate here, or the plant is not expressing defocus at all.
* **Second positive control.** `mean-w1` (radius 1), which fact 73 records as
  discriminating the σ 0→3 monotone pair at **0.376**. Recovering ≈0.376 on B1
  proves the plant is fact 73's plant and not a different one.

### 2.4 Registered prediction

`mean-w13` reads exactly 1.0000 on B1 (this is a re-measurement, not a
prediction). `max-w13`, `p95`, `p99`, and every dual containing `max` read
`D < 0.9` on B1. `sq-w13` reads `D < 1` but **greater than** `max-w13`'s, because
squaring breaks TV conservation only through Jensen's gap rather than by taking
an extremum. `dualrad-*` read `D` between `mean-w1`'s 0.376 and 1.0000.

## 3. Axis 2 — quality on M13's occluding-edge cells (the mandatory guard)

Question 19: *"this must be scored on the same edge cells M13 used, so a repair
cannot silently regress the textured-occlusion case that picked w13."*

* **Cells.** 2 stacks × 3 shapes (`vertical`, `horizontal`, `bar`) × 6 depth steps
  (0, 2, 4, 8, 16, 32) = **36 cells**, 30 of them carrying a depth step, each
  averaged over M13's **3** noise seeds (20260823, 771117, 4242424), at
  regulariser width 1. Identical ROIs, frames, `sigma0`, `alpha`, `noise_scale`,
  band and baseline to M13.
* **Primary statistic.** Mean `excess_dn` over the 30 depth-step cells —
  **absolute** reconstruction excess over the physical oracle floor, in DN.
  Absolute rather than regret, because the treatment here changes the *operator*
  and SYNTHESIS discipline 32 records that a regret statistic is only comparable
  across a treatment that leaves the per-cell dispersion alone.
* **Secondary.** Mean regret and worst-case regret with the per-cell best taken
  over the candidate set, reported but **not decided on** — worst-case regret is
  registered here as inadmissible for the decision, in advance, for the reason
  above.
* **Tertiary.** Head-to-head win counts against `mean-w13`, cell by cell, in
  M13's own idiom ("beats it in 36 of 36").
* **Null stratum.** The 6 zero-step cells, published separately. Fact 61: they
  have no interior optimum at all, so they are the stratum on which an
  occlusion-halo effect must be *absent*.

### 3.1 Registered threshold

A candidate is **quality-non-regressive** iff

```
mean_excess_dn(candidate) - mean_excess_dn(mean-w13)  <=  +0.87 DN
```

over the 30 depth-step cells. **0.87 DN is not chosen here** — it is M13's own
pre-registered basin-flatness threshold, re-used by M15 (facts 81, 60), against a
seed noise floor of 0.193 DN. A change the project already agreed is too small to
move the window is too small to reject an operator.

## 4. Axis 3 — noise

* **Statistic.** M11/M13's flat-ROI merged-noise ratio `N = σ(stacked) / σ(single
  frame)` on the green plane, `median` over the 4 flat ROIs of a stack, then
  `mean` over the 2 stacks. ROIs taken from M13's **committed**
  `data/noise-*.csv`, never from a run script (AGENTS.md).
* **Reference.** The shipped `tenengrad-w13` sits at **N = 1.08637** pooled and
  **1.067839** on 109MSDCF's `2272,1344,256,256`.
* **Per-stack discriminator check** (fact 88): the four 109MSDCF ROIs must read
  `single_sigma` in 27.6–30.0 DN and the four 119MSDCF ROIs in 43.2–53.1 DN. A
  threshold is never carried across stacks.
* **Positive control.** `tenengrad-w0` is in the same run. M13 measured it far
  from w13 (1.34 on 109MSDCF ROI 1), so the instrument is shown resolving a
  large, already-published noise difference in the same invocation.

### 4.1 Registered threshold

```
DELTA_N = N(candidate) - N(mean-w13)  <=  +0.02
```

**+0.02 is not chosen here either**: it is M9's pre-registered severity floor on
this exact quantity, and it is the same size as M11's noise-free bar
(`N ≤ 1.02×`) measured from 1.00. A candidate above it has bought a rare failure
with a common one.

### 4.2 Supporting number, not a gate

Coefficient of variation of the candidate's response on a noisy step, in the flat
region beside the boundary, which is the mechanism behind any ΔN. The
orchestrator measured 0.0265 (max) against 0.0065 (mean) synthetically; this
re-measures it on the real-sensor plant.

## 5. Axis 4 — cost

* Time `FocusField`-equivalent computation per frame per megapixel for each
  candidate on a real ROI.
* Sweep the **radius** 1…40 for `mean` and for `max` to test whether the running
  max holds `box_mean`'s O(1)-in-radius property (fact 66).
* **Alternating sweep direction, at least 4 sweeps, per-setting minimum**
  (SYNTHESIS discipline 30, project rule 16). A near-flat result is quoted as a
  **bound**, not a point value.
* Registered in advance: percentile candidates are **not** in the O(1) class and
  are measured for information, not as ship candidates.

## 6. Decision rule

Let `D` = B1 blind-spot discrimination ratio (lower is better, 1.0000 = blind),
`ΔE` = mean-`excess_dn` change on the 30 depth-step cells, `ΔN` = pooled
flat-ROI noise-ratio change.

| Verdict | Condition |
| --- | --- |
| **SHIP** | `D ≤ 0.90` **and** `ΔE ≤ +0.87 DN` **and** `ΔN ≤ +0.02` **and** cost is O(1) in the radius |
| **SHIP BEHIND A FLAG** | `D ≤ 0.90` **and** exactly one of `ΔE`, `ΔN` fails, and it fails by less than **2×** its threshold |
| **DO NOT SHIP** | anything else |

If more than one candidate reaches **SHIP**, the recommendation is the one with
the smallest `ΔN`, because noise is paid on every pixel of every frame and the
blind spot is paid only where the scene is smooth.

**A negative result is an acceptable outcome and will be reported as the
headline if that is what the numbers say.**

## 7. Registered predictions (so they can be falsified)

1. `max-w13` fixes the blind spot: `D ≤ 0.30` on B1.
2. `max-w13` fails `ΔN` — it is an extremum statistic and extrema are
   noise-seeking; predicted `ΔN > +0.05`.
3. At least one dual passes `ΔN` while keeping `D ≤ 0.90` — this is the
   proposal's whole premise.
4. `dualtie-w13` (mean + 0.05·max) has the smallest `ΔN` of any candidate that
   fixes the blind spot, because a monotone edge's mean term is *exactly*
   constant across frames, so an arbitrarily small max weight resolves the tie
   completely while barely perturbing a textured pixel.
5. `sq-w13` passes the blind spot and **fails** `ΔE`, because it is a different
   operator that M11 benchmarked only at `w2` and M13 never benchmarked at all.
6. `dualrad-*` fail `ΔN`, because a radius-1 term is most of a radius-1 operator
   and M13 measured `tenengrad-w1` at N ≈ 1.34.
7. The running max is O(1) in the radius, flat to within the timing noise, and
   costs **less than 2×** `box_mean` per pass.
8. On the B2 plant, `mean-w13`'s per-pixel cross-frame peak contrast is near zero
   on the monotone edge and large on texture, so question 19 candidate (a) does
   flag these pixels — subject to discipline 120, which disqualifies a
   self-normalised shape statistic as the confidence *output* regardless.

## 8. What would make me abandon the dual

* If `max` alone passes `ΔN`, the dual is unnecessary complexity and the
  recommendation is `max` or nothing.
* If **no** candidate passes `ΔE`, the answer to question 19 is candidate (a) —
  no operator change — and that is the deliverable.
* If the blind spot's fix costs more than 2× the threshold on either axis, the
  answer is "do not ship", and the number that says so is the headline.
