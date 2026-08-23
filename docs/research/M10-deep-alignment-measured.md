# M10 — deep-stack alignment, measured

**Milestone:** M10. **Target:** SYNTHESIS risk 11 — neither of the project's two
alignment strategies survives a 100+ frame stack.
**Experiment:** [`experiments/m10-deep-align/`](../../experiments/m10-deep-align/).
**Registered design:** [`PREREGISTRATION.md`](../../experiments/m10-deep-align/PREREGISTRATION.md),
written before any solver ran, amended once (dated, pre-data) in its §8.

Every claim below is labelled **MEASURED** (a number produced by a command in
this repository), **VERIFIED** (a published number reproduced), **DERIVED**
(algebra over measured numbers), **ARGUED** (an interpretation) or
**UNVERIFIED**.

> **Units.** All figures are **plane px** at the worst plane corner, on the
> CFA-quad green plane (3516 × 2344, corner radius ρ = 2112.85 px). One plane px
> is two sensor px. **M3's headline "25 px chaining error at 60 frames" is a
> sensor figure and is 12.5 plane px.** M6's halo figures are already plane px.

---

## 0. Ruling in one paragraph

**Risk 11 is partially solved, and the reason it was open turns out to be
neither of the two reasons the project believed.** A global bundle adjustment
over a sparse graph of *directly measured* pairwise edges places all 105
coffee-bean frames — the fixed reference places 76 — and predicts held-out long
edges at **6.5–7.0 plane px median, 22.5 px max**, against **40.3 px** for the
adjacent chain. Under the registered decision rule that is **cell E: not solved,
but decisively better than chaining**. On both shallow stacks the identical
method reaches **0.58–0.67 px**, i.e. cell B, so the method is sound and the deep
stack is limited by its *measurements*, not by the solver: a solve that has
already seen the test edges only reaches 5.9 px. The mechanism behind that limit
is new and was not on the candidate list: **short-baseline edges systematically
under-report magnification change by up to 3.3×**, and the bias requires
sub-pixel differential displacement *together with* a real inter-frame content
change. Both existing strategies fail for the same underlying reason, expressed
at opposite extremes.

---

## 1. Design, and why it can answer the question

Every strategy is an estimator over one shared input: a CSV of **direct pairwise
fits between two real decoded frames**. The Rust harness never composes, never
resamples a frame into another frame's grid and never writes an aligned image.
Chaining, keyframe ladders, bundle adjustment and parametric curves are then
Python functions over that same edge set, so any difference between them is the
strategy and not the estimator.

**Algebra.** Write a similarity as a complex pair `(a, b)`, `T(p) = a·p + b`,
with `p` relative to the plane centre. Composition (`t1` then `t2`) is
`a = a1·a2`, `b = a2·b1 + b2`. With `G_j` the frame-0→frame-j transform and an
edge `M(i→j) = (a_ij, b_ij)`, the constraints are

```
A_j = a_ij · A_i          B_j = a_ij · B_i + b_ij
```

Both are **linear in the unknowns**, so bundle adjustment here is a single
complex linear least-squares problem — 208 complex unknowns for N = 105 — and
not a nonlinear one. **DERIVED**, and checked numerically in control P0.

**The objective is the corner error.** Because the four plane corners are
symmetric (`Σp = 0`, `mean|p|² = ρ²`), `mean_corners |Δa·p + Δb|²` equals exactly
`ρ²|Δa|² + |Δb|²`. Minimising `Σ w(ρ²|ΔA|² + |ΔB|²)` therefore *is* minimising
rms corner reprojection error. **MEASURED** as an identity to 2.8e-14 px
(`out/controls.txt`, P0).

### 1.1 The registered non-degeneracy check

Before running, the design had to survive the failure M6 found in M3's: an
experimental design that is structurally incapable of separating the hypotheses.

Here the trap is explicit. **A bundle adjustment over a training graph that is a
tree is algebraically identical to chaining along that tree.** All residuals are
zero and S3 cannot be distinguished from S1. `graph_stats()` therefore reports
cycle rank, component count and `is_tree` for every training subset; the tables
print `TREE`; and tree rows are excluded from the ruling by
`m10_ruling.py`, which recomputes tree-ness from the data rather than copying it.
This fired live — the span-1-only training row is a tree and S1, S2 and all three
S3 variants return bit-identical numbers in `out/headline.txt`. **MEASURED.**

### 1.2 Controls (project rule 11)

`out/controls.txt` ends with `ALL CONTROLS PASS`. Per PREREGISTRATION §5 no
number in this report would be quoted if it did not.

| control | result | label |
| --- | --- | --- |
| **P1** estimator port | ported estimator recovers four planted similarities: translation error **0.13–0.19 px**, worst scale error **6.51e-5** (`m3` cfg) / **3.93e-5** (`m10` cfg) = **0.137 / 0.083 px** at the corner. Same regime as M3 §0 (translation 0.151 px, worst scale 2.23e-5) but **not verbatim** — see note. | **MEASURED** |
| **P0** algebra | six identities, worst 9.5e-13 px | **MEASURED** |
| **P5** detector null | noiseless edges reproduce truth to **0.00e+00 px** over 1601 edges; exact-edge cycle consistency 7.0e-13 px over 4000 triples; training graph cycle rank 1497 | **MEASURED** |
| **P2b** positive, 0.5 px edge noise | BA **0.452 px** max vs chain **6.058 px**, fixed **2.254 px** | **MEASURED** |
| **P2c** positive, planted coherent lock bias 0.02 px/frame | chain max **4.902 px** (planted 2.08 px accumulates), BA **2.137 px** | **MEASURED** |
| **P2d** positive, every span > 40 deleted | fixed reference covers **41/105**, BA covers **105/105** at max **0.535 px** | **MEASURED** |
| **P3** null, randomised edge payloads | BA blows up to **89.2 px**; cycle consistency detects it at median **49.2 px** | **MEASURED** |
| **P4** end-to-end on synthetic frames | see §6 | **MEASURED** |

**P2c is the control that matters most for rule 6**: a coherent per-step bias was
*planted*, the chain accumulated it exactly as M3 measured, and the global solve
did not. A control that could not detect a planted effect would not be a control.

**Note on P1, and a correction to an earlier draft of this document.** An earlier
draft claimed P1 "reproduced M3 §0 verbatim". That claim is **retracted**: it was
true of the first version of this harness, which planted its known warp with the
*linearised* inverse `p - d(p)`, and it was not re-run after the `inv_at` fix described in §8 item 1.
The current harness plants the exact inverse `(p-b)/a`, and its residual column is
the post-fit RMS **over inlier tiles only**, whereas M3's residual column is over
its own tile set — so the two residual columns are not the same statistic and were
never comparable. What P1 does establish, and all this control was ever needed for,
is that the ported estimator lands in the same regime as M3's: translation error
0.13–0.19 px against M3's 0.151 px, and worst scale error 6.51e-5 = 0.137 px at the
corner against M3's 2.23e-5 = 0.047 px. Both are far below every effect claimed
here, the smallest of which is 3.786 px. The quantitative estimator floor this
report actually leans on is **P1b** (§8 item 1), a 432-warp distribution measured after
the fix, not P1's four hand-picked cases. Reproduce with
`m10-deep-align.exe synthetic C:\dev\macro\test\coffee-bean` (`out/p1-estimator-control.txt`).

---

## 2. Reproducing the failure, precisely

Running this crate's ported estimator with `AlignCfg::m3()` on
`coffee-bean` under a fixed reference (`out/edge-quality.txt`):

| quantity | M6 published | M10 measured |
| --- | --- | --- |
| direct-to-frame-0 pairs with no fit | 3 of 104 | **3 of 104** (frames 83, 93, 102) |
| median tiles used | 18 of 96 | **18** |
| median tile rms | 4.61 px | **4.61 px** |

**VERIFIED.** M6's deep-stack observation reproduces to the digit.

Edge yield across the whole span range, `cfg=m10` (margin 96), 1601 pairs:

| span | pairs | no-fit | median tiles | median tile rms | median \|g\| (e-3) |
| --- | --- | --- | --- | --- | --- |
| 1 | 104 | 0 | 89 | 0.376 | 0.161 |
| 2 | 103 | 0 | 91 | 0.808 | 0.413 |
| 3–4 | 203 | 0 | 92 | 1.451 | 0.793 |
| 5–8 | 297 | 0 | 87 | 2.669 | 1.606 |
| 9–16 | 282 | 0 | 55 | 3.885 | 6.073 |
| 17–32 | 252 | 4 (1.6%) | 23 | 4.069 | 13.803 |
| 33–64 | 240 | 38 (15.8%) | 13 | 4.569 | 26.034 |
| 65–104 | 120 | 98 (**81.7%**) | 9 | 4.712 | 36.883 |

**MEASURED.** The overlap collapse is real and steep: it is negligible to span
16, tolerable to span 32, and terminal beyond span 64. On the two shallow stacks
there are **zero** no-fits at any span in either config.

---

## 3. The finding: short-baseline edges are shrunk

This was not on the candidate list. It emerged from a consistency check and it
reframes the milestone.

### 3.1 The observation

Telescoping edges of a fixed span across a stack must give the same total
magnification change whatever the span, because `Σ log a_{j,j+s} = log a_{0,N-1}`
is an identity. It does not. `out/conservation.txt`, `cfg=m10`:

| span | links | frames covered | total scale change |
| --- | --- | --- | --- |
| 1 | 104 | 104/104 | **−1.6876 %** |
| 2 | 52 | 104/104 | −2.0814 % |
| 4 | 26 | 104/104 | −2.4119 % |
| 8 | 13 | 104/104 | −3.4880 % |
| 12 | 8 | 96/104 | −5.1440 % |
| 16 | 6 | 96/104 | **−5.8891 %** |
| 32 | 3 | 96/104 | −5.7348 % |
| 48 | 2 | 96/104 | −5.1860 % |
| 64 | 1 | 64/104 | −5.2877 % |

**MEASURED.** A factor **3.33** between the ends. `wide64` shows the same ramp
with a factor **3.90** and a later saturation point.

This calculation involves **no median, no weighting and no solver** — it is a
sum of logarithms. That was deliberate: the effect was first seen in a
median-of-per-frame-rates statistic, where a skew could have produced it
spuriously, and the telescoping identity was written specifically to kill that
confound. It survives. **The median-vs-mean explanation is refuted.**

### 3.2 Which end is wrong

The deep stack has no trustworthy anchor. The shallow stacks do — a direct
frame-0-to-last edge that succeeds with many tiles at low rms — and they settle
the direction:

| stack | span-1 telescoped | ladder saturates at | trustworthy direct edge | shrinkage |
| --- | --- | --- | --- | --- |
| 119MSDCF (33 fr) | −0.4644 % | −1.0185 % | **−1.0185 %** (0→32, 78 tiles, rms 1.24) | **2.19×** |
| 109MSDCF (22 fr) | −1.2966 % | −1.854 % | **−1.8544 %** (0→21, 61 tiles, rms 1.11) | **1.43×** |
| coffee-bean (105 fr) | −1.6876 % | −5.2 to −5.9 % | −6.9665 % (0→104, **16 tiles, rms 8.95** — not trustworthy) | **3.33×** |

**MEASURED.** On 119MSDCF the ladder converges onto the trusted direct edge to
four decimal places. **The long edges are right; the short edges are shrunk.**

On coffee-bean the ladder plateaus between −5.2 % and −5.9 % without a perfectly
flat region, and the only direct 0→104 edge uses 16 tiles at 8.95 px rms. The
coffee-bean total is therefore **bracketed, not pinned**. Stated as a limitation,
not smoothed over.

### 3.3 The mechanism, isolated with two controls

Two controls plant the *same* geometric increment and differ in exactly one
thing: whether the two frames also differ in real image content.

* **P6 `field` arm** — both frames are independent point samples of one
  continuous band-limited function. Same content, **no resampler anywhere**,
  only the geometry differs. This arm exists specifically because M6 measured
  that bilinear resampling plants a sub-pixel-phase sharpness modulation that a
  correlation estimator reads as defocus; a resampled control could not have
  answered this question.
* **P7 `increment` arm** — a real, defocus-mismatched coffee-bean pair, fitted
  twice: once as-is, once with a known extra similarity on the moving frame.
  The recovered increment is the difference, so the defocus mismatch, the tile
  dropout and the content overlap all cancel.

`out/p6-p7-mechanism.txt`, ratio = recovered / planted, `cfg=m10`:

| differential displacement | P6 field (same content) | P7 increment (real pair) |
| --- | --- | --- |
| 0.12 px | **1.008** [0.989, 1.050] | **0.559** [0.415, 0.691] |
| 0.24 px | **0.991** [0.982, 0.998] | **0.664** [0.539, 0.768] |
| 0.48 px | 0.996 [0.991, 1.002] | 0.988 [0.904, 1.093] |
| 0.96 px | 1.001 [0.998, 1.003] | 0.996 [0.949, 1.016] |
| 1.92 px | 1.000 [0.999, 1.002] | 1.015 [0.996, 1.034] |
| 4.80 px | — | 0.991 [0.987, 0.996] |

**MEASURED**, n = 12 and n = 42 respectively, brackets are the interquartile
range. Two facts follow directly:

1. **The estimator's response to geometry is unbiased.** With no content change
   it recovers a planted scale to within 1 % down to 0.12 px of differential
   displacement — well below the 0.19 px at which real span-1 edges sit. The
   bias is not in the fit, the tiling, the interpolation or the solver.
2. **A real inter-frame content change is necessary, and the bias lives below
   about 0.5 px of differential displacement.** At 0.12 and 0.24 px the two arms'
   interquartile ranges do not overlap. At 0.48 px and above they coincide.

Naming the effect **pixel locking amplified by the defocus step** — sub-pixel
correlation estimates biased toward integer positions, with the broadened and
asymmetric peak of a defocus-mismatched pair pulling every tile toward a common
value that the similarity fit reads as "no scale change" — is **ARGUED**. The two
necessary conditions above are **MEASURED**.

**An unexplained residual, stated plainly.** P7 measures the *marginal* response
`df/dg` and finds it unbiased above 0.48 px, whereas the real ladder is still
shrunk at span 4 and span 8. A pure marginal-response model therefore does not
account for the full size of the ladder. This is not resolved here.

### 3.4 The pipeline does not manufacture the ladder

The P4 synthetic stack has a known answer, a genuine growing defocus ramp
(median tile rms rises 0.57 → 1.72 px from span 1 to span 104), the same
estimator and the same code path. Running the identical telescoping identity on
it (`out/p4-conservation.txt`), over rows with full stack coverage:

| span | total | ratio to planted truth |
| --- | --- | --- |
| 1 | −5.1307 % | 1.1245 |
| 2 | −4.8883 % | 1.0700 |
| 4 | −4.7235 % | 1.0331 |
| 8 | −4.6189 % | 1.0096 |
| 16 | −4.4515 % | 0.9722 |
| 32 | −4.4379 % | 0.9692 |
| 48 | −4.4178 % | 0.9647 |

**MEASURED.** The synthetic ladder spans 0.96–1.12, a range of **1.17×**, against
**3.33×** on the real stack — and the span-1 row errs in the *opposite* direction.
The harness, the tiling, the fit and defocus-in-general do not create the ramp.
The planted span-1 differential displacement is 0.415 px, just at the threshold
§3.3 located, which is consistent with the mild residual error seen.

---

## 4. The headline measurement

### 4.1 Metric

There is no ground truth, so the primary metric is **held-out prediction of
trustworthy long edges**. A fixed test set of directly measured long edges is
withheld; each strategy is fitted on a training set disjoint from it; each then
predicts every test edge; the error is the worst plane corner. Test sets are
fixed per stack so rows are comparable:

* coffee-bean: span ≥ 40 **and** ≥ 12 surviving tiles → 125 test edges (m10)
* 109MSDCF: span ≥ 12, ≥ 40 tiles → 24 test edges
* 119MSDCF: span ≥ 16, ≥ 40 tiles → 41 test edges

Cycle consistency is reported alongside as a data-only diagnostic, and a
**`REF-insample` row** — a solve that has already seen the test edges — bounds
what any held-out method could achieve.

### 4.2 Result, coffee-bean, `cfg=m10`, trained on all measurable edges

`out/headline.txt`. 1336 training edges, cycle rank 1232, one component.

| strategy | frames placed | median | p90 | max | scale part | trans part |
| --- | --- | --- | --- | --- | --- | --- |
| `REF-insample` *(bound, not a strategy)* | 105/105 | **5.875** | 10.672 | 20.131 | 4.104 | 2.084 |
| **S5-centre4** parametric, fixed centre | **105/105** | **6.591** | 12.499 | 20.428 | 4.919 | 1.876 |
| **S4-poly4** parametric in j | 105/105 | 6.822 | 13.240 | 20.024 | 4.919 | 2.573 |
| **S3-ba-unit** bundle adjustment | 105/105 | 6.997 | 13.529 | 19.570 | 5.067 | 2.800 |
| S6-ba-smooth | 105/105 | 6.997 | 13.529 | 19.570 | 5.067 | 2.800 |
| S3-ba-count | 105/105 | 8.254 | 15.285 | 21.001 | 5.634 | 3.323 |
| S0-fixed **(status quo)** | **76/105** | 9.037 | 18.385 | 35.495 | 6.156 | 3.796 |
| S2-hops32 keyframe ladder | 105/105 | 14.549 | 21.522 | 28.705 | 11.069 | 3.131 |
| S3-ba-invvar | 105/105 | 24.011 | 30.581 | 33.205 | 20.414 | 3.914 |
| S1-hops1 **(chaining)** | 105/105 | **40.342** | 48.152 | 58.890 | 36.407 | 5.069 |

**MEASURED.** Three things to read off it:

1. **The best strategies sit within 12 % of the in-sample bound** (6.59 vs 5.88).
   The solver is not the limiting factor; the pairwise measurements are.
2. **The fixed reference places only 76 of 105 frames** and could predict just 31
   of the 125 test edges. Its 9.04 px median is over that easy subset.
3. **Almost all of the error is the scale part** (4.9 of 6.6 px). Translation is
   under 2 px.

### 4.3 Result, shallow stacks — the method itself is sound

`119MSDCF`, `cfg=m10`, trained on the medium band (span 8–32), test set disjoint:

| strategy | median | p90 | max |
| --- | --- | --- | --- |
| `REF-insample` *(bound)* | 0.435 | 0.705 | 1.103 |
| **S3-ba-invvar** | **0.531** | 0.834 | **0.976** |
| S3-ba-unit | 0.552 | 0.993 | 1.098 |
| S2-hops16 | 0.672 | 1.451 | 1.850 |
| S1-hops1 (chaining) | 7.928 | 10.611 | 12.391 |

**MEASURED.** Sub-pixel, and **15× better than chaining**. `109MSDCF` reaches
0.489 px median / 2.761 px max with an in-sample bound of 0.274 px.

### 4.4 The data's own inconsistency bounds the deep stack

Cycle consistency of the **raw edges**, no solver, `T(i→k)` against
`T(j→k)∘T(i→j)` (`out/headline.txt`):

| shortest leg | coffee-bean m10 median | 119MSDCF m10 median | 109MSDCF m10 median |
| --- | --- | --- | --- |
| 1 | 0.364 | 0.404 | 0.648 |
| 2–3 | 1.783 | 0.789 | 0.310 |
| 4–7 | 5.069 | 0.731 | 0.382 |
| 8–15 | 6.829 | 0.533 | 0.581 |
| 16–31 | 9.609 | 0.214 | — |
| 32–104 | 13.026 | — | — |

**MEASURED.** On the shallow stacks the measurements agree with each other to
about 1 px at every scale. On coffee-bean they disagree with each other by 5–13
px once a leg exceeds span 4. **No estimator over these edges can be better than
the edges are mutually consistent**, and the best strategies are already at that
floor. **DERIVED.**

Short coffee-bean edges are *precise but biased* (cycle error 0.364 px at leg 1,
shrunk 3.33×); long ones are *unbiased but imprecise* (13 tiles, ~4.6 px rms,
cycle error 13 px). That is the bias–variance trade-off the milestone actually
ran into.

### 4.5 The registered decision rule, applied mechanically

`out/ruling.txt`. `T_solved` = 1.0, `T_usable` = 4.0, `T_chain` = 12.5 plane px,
all fixed before the data existed. Tree training graphs and partial-coverage
strategies are excluded, as cells A–C require all frames to be placed.

| stack | best full-coverage row | `E*` registered | `E*` robust | slope on test span | cell |
| --- | --- | --- | --- | --- | --- |
| coffee-bean m10 | S4-poly6 on span ≥ 32 | 6.758 px (n=1) | **6.758 px** (n=35) | +0.062 ± 0.041 px/frame, **not** significant | **E** |
| coffee-bean wide64 | S2-hops32 on span ≤ 32 | 53.428 px | 31.071 px | +0.603 ± 0.030, **significant** | **F** |
| 109MSDCF m10 | S2-hops16 on span ≤ 16 | 1.836 px (n=1) | **0.581 px** (n=11) | +0.062 ± 0.054, not significant | **A/B** |
| 119MSDCF m10 | S2-hops16 on span 8–32 | 0.809 px (n=1) | **0.672 px** (n=17) | −0.023 ± 0.014, not significant | **A/B** |

**Two registered refinements, disclosed rather than hidden.** (i) The registered
`E*` — the median at the single longest test span — has n = 1 on three of four
rows, which is not a usable statistic; the median over the longest-span quartile
is reported beside it and the ruling uses that. (ii) Coverage is treated as a
precondition rather than a tiebreak, because cells A, B and C all require every
frame to be placed.

**M7, agreement with the known-good fixed reference where one exists:** BA vs
S0-fixed, median **0.305 px** / max 1.295 px on 109MSDCF and median **0.582 px** /
max 1.450 px on 119MSDCF. **MEASURED.** Cell A additionally required ≤ 0.5 px
agreement on *both* shallow stacks; 119MSDCF misses it. The shallow-stack ruling
is therefore **cell B**, not A.

**Ruling: cell E on the deep stack, cell B on the shallow stacks.**

---

## 5. The candidates, judged against their registered falsifiers

### (a) Hierarchical / keyframe ladder — **FALSIFIED on the deep stack**

Registered falsifier: *held-out error at the longest span exceeds S3's by more
than 2×*. Best ladder on coffee-bean m10 is S2-hops32 at **14.549 px** median
against S3-ba-unit's **6.997 px** — a ratio of **2.08**. Falsified, if narrowly.
**MEASURED.**

On the shallow stacks the ladder is not falsified and is in fact competitive
(119MSDCF: hops16 0.672 px vs ba-invvar 0.705 px). The honest statement is that
**a hop ladder is adequate where a fixed reference already works and inadequate
where it does not** — which is precisely where it was needed. Its structural
weakness is visible in the ruling table: the only wide64 row that survives is a
hop ladder, and it has the one **significantly positive slope on test span**
(+0.603 px/frame), which is the accumulation signature the ladder was supposed to
avoid.

### (b) Global bundle adjustment — **FALSIFIED as a solution, vindicated as the best available**

Registered falsifier: *held-out error grows significantly with test span, or
exceeds `T_usable`*. On coffee-bean `E*` = 6.76 px > 4.0 px, so **falsified as a
solution**. The slope is **not** significantly positive (+0.062 ± 0.041
px/frame), so it does *not* accumulate with depth — the failure is a floor, not a
ramp. On both shallow stacks it passes. **MEASURED.**

Its two structural wins are not in doubt: **105/105 coverage where the fixed
reference manages 76**, and P2d, where deleting every edge longer than span 40
leaves the fixed reference covering 41/105 while BA covers 105/105 at 0.535 px.

**Weighting is load-bearing and must be reported.** Inverse-variance weights
(`σ_B ≈ rms/√used`, `σ_A ≈ rms/(lever·√used)`) downweight long-span edges hard —
exactly the edges that break the tree degeneracy and carry the unbiased scale.
On coffee-bean `ba-invvar` scores **24.011 px** against `ba-unit`'s **6.997 px**,
a 3.4× penalty for the statistically natural choice. On the shallow stacks, where
the scale is unbiased at every span, `invvar` is the *better* choice (0.531 vs
0.552 px). **MEASURED.** This is a trap for anyone implementing it.

### (c) Parametric model in stack index — **TRUE, and worth about 6 %**

The parameters *are* smooth and low-order in frame index. Fitting a degree-`d`
polynomial through the BA solution (`out/headline.txt`):

| stack | total corner motion | deg 1 | deg 3 | deg 6 |
| --- | --- | --- | --- | --- |
| coffee-bean m10 | 116 px (−5.52 % scale) | 7.087 px | 4.858 px | **3.786 px** |
| 119MSDCF m10 | 21 px (−1.01 % scale) | 0.883 px | 0.807 px | **0.573 px** |

**MEASURED.** A degree-6 curve captures **96.7 %** of coffee-bean's corner motion
and a *straight line* captures 93.9 %. **DERIVED.** But the residual, 3.8 plane
px, is 20× the 0.19 px estimator floor, so smoothness alone does not deliver
alignment.

Registered falsifier 2 — *`S4`/`S5`/`S6` do not beat `S3`* — is **not** triggered:
S5-centre4 (6.591) and S4-poly4 (6.822) do beat S3-ba-unit (6.997). But the
margin is **6 %**, well inside the spread between neighbouring training sets, so
the honest reading is **cell I, a tie**. The registered note that "smoothness may
be true and useless" was the right thing to have written down. **MEASURED.**

Registered falsifier 3 — *`S5`'s single scale centre is rejected if its residual
exceeds 3× the free-`B` residual* — is **not** triggered. `out/scale-centre.txt`:

| stack | fitted centre (sensor px) | S5 / free-B residual ratio |
| --- | --- | --- |
| coffee-bean m10 | (+425, −449) | **1.04** |
| 109MSDCF m10 | **(−27, −131)** | 1.84 |
| 119MSDCF m10 | (−106, −378) | 2.42 |

**MEASURED.** Two consequences. First, **the whole 105-frame translation is
explained to within 4 % by pure magnification about one fixed point** — a real
structural finding and the reason S5 wins on the deep stack. Second, and
negatively: **the centre is not a constant of the optics.** M3 measured (−22,
−113) sensor px; 109MSDCF independently gives **(−27, −131)**, which corroborates
M3 from a completely different estimator path, but 119MSDCF and coffee-bean land
elsewhere and coffee-bean's two configs disagree with each other by 150 px.
**M3's (−22, −113) must not be treated as a calibration constant.**

### (d) Coarse-to-fine pyramid rescue — **FALSIFIED**

`wide64` (pyramid 32/16/8, 64 px template, 16×11 grid, radius 12) converts
**every** no-fit into a fit: **0 of 1601** coffee-bean pairs fail, against 140 for
`m10`, including all 98 failures beyond span 64. On the raw yield table it looks
like the answer.

It is not. Registered falsifier: *converts no-fit pairs into fits whose residual
is worse than the edges it replaces*. Median tile rms at span 33–64 is **9.29 px**
against `m10`'s **4.57 px**; raw-edge cycle consistency at long legs is **35.2 px**
against **13.0 px**; and in the ruling table `wide64` lands in **cell F** at
31.1 px with the only significantly positive span slope. **MEASURED. Falsified.**

**Zero no-fit was false confidence.** The fits exist; they are worse. This is the
clearest negative result in the milestone and it would have been easy to publish
the yield table alone and claim a win.

---

## 6. P4 — end-to-end recovery of a planted path

A 105-frame stack built from one real coffee-bean frame by a known smooth
similarity sequence plus a growing depth-dependent blur, so long pairs genuinely
decorrelate. Planted total drift 98.6 plane px (−4.574 % scale, matching M6's
measured coffee-bean drift). Scored in **absolute** corner px against truth
(`out/p4-warp.txt`), trained on all 761 measurable edges:

| strategy | frames placed | median | p90 | max |
| --- | --- | --- | --- | --- |
| **S5-centre6** | 104/105 | **0.616** | 0.735 | 0.797 |
| S3-ba-unit | 104/105 | 0.622 | 0.746 | 0.888 |
| S4-poly6 | 104/105 | 0.651 | 0.729 | **0.774** |
| S0-fixed | 104/105 | 0.683 | 1.283 | 1.644 |
| S2-hops8 | 104/105 | 0.567 | 1.311 | 2.137 |
| **S1-hops1 (chaining)** | 104/105 | **5.497** | 11.438 | **14.565** |

**MEASURED.** The whole path — ARW decode, plane extraction, tiled NCC,
similarity fit, global solve — recovers a planted 105-frame camera path to
**0.62 px median, 0.89 px max**, while the adjacent chain accumulates to
**14.57 px**. Direct edge accuracy against truth is 0.289 px at span 1 rising to
0.921 px at span 65–104, with **no shrinkage at any span**.

**Disclosure, per SYNTHESIS §5 item 11 and the registered design.** The warp is
bilinear, which M6 measured to plant a sub-pixel-phase sharpness modulation that
a correlation estimator reads as defocus. **This control is used for recovery
only. It is never evidence about defocus, and no conclusion in §3 rests on it.**
Its role in §3.4 is strictly the negative one: the pipeline does not manufacture
a scale-rate ladder.

---

## 7. What this means for the architecture

**The recommended deep-stack alignment procedure**, as measured:

1. Measure a **sparse multiscale edge set** — spans 1, 2, 4, 8, 16, 32, 48, 64
   plus direct-to-frame-0 — with each edge a **direct fit between two real
   frames**. Never compose to obtain an edge.
2. **Discard span-1 and span-2 edges.** They are precise and wrong.
3. Solve one **complex linear least squares** for the per-frame `(A_j, B_j)` with
   Huber IRLS, **`unit` weighting on a deep stack** (`invvar` on a shallow one),
   optionally constraining `B_j = (1 − A_j)·c` for a single fitted centre.
4. Verify with **cycle consistency** and **held-out long-edge prediction**. Both
   are ground-truth free and both detect a scrambled solution (P3).

**Cost. MEASURED.** Edge measurement is 13.6 ms/pair (`m10`) and 27 ms/pair
(`wide64`); the full 1601-pair coffee-bean sweep across both configs took 68 s
including decode. A practical ~760-pair single-config set for 105 frames is about
10 s of fitting. The global solve is 208 complex unknowns and is milliseconds.
**Alignment is not the bottleneck; measuring good edges is.**

**Accuracy to expect. MEASURED.** 0.5–0.7 plane px on stacks of 20–35 frames;
6.5–7.0 plane px median and ~22 px max on a 105-frame stack whose focus sweep
covers the whole subject. The deep-stack figure is a property of the *pairwise
measurements*, not the solver.

**The next milestone this implies.** Deep-stack accuracy is bounded by the
pairwise estimator's behaviour on defocus-mismatched pairs — both its debiasing
below ~0.5 px of differential displacement and its precision at 13 surviving
tiles. That is a new, well-posed problem and it is where the remaining 6 px lives.

---

## 8. What was refuted, including my own hypotheses

1. **"Chaining fails because of accumulated random error."** Refuted. It fails
   because span-1 edges carry a **coherent 3.3× scale shrinkage**; the scale part
   is 36.4 px of the chain's 40.3 px total error, and the translation part is
   5.1 px. **MEASURED.**
2. **"Zero no-fit means a better aligner."** Refuted — candidate (d), §5.
3. **"A wide-baseline geometric penalty limits long edges."** Refuted, and it was
   **my own bug**. An early sweep showed error rising steeply with planted |g|.
   The cause was that `warp_known` applied the *linearised* inverse `p − d(p)`
   instead of the exact inverse `(p − b)/a`, planting exactly `g²ρ` of fake corner
   error — 4.3 px at coffee-bean's drift, the same size as the effect under
   study. The tell was that a config change returned **bit-identical** results and
   the error matched `g²ρ` across all four |g| bins. Fixed via `Fit::inv_at()`.
   Post-fix the floor is **flat in |g|**: `m10`/margin 96 gives 0.125 px median /
   0.365 px max, `wide64` gives 0.056 / 0.159 px over 432 planted warps.
   **MEASURED.** There is no intrinsic wide-baseline geometric penalty.
4. **"The scale-rate ladder is a median-vs-mean artefact."** Refuted by the
   telescoping identity, which contains no median and no weighting (§3.1).
5. **"The ladder is a property of the estimator's response to geometry."**
   Refuted by P6 and P7 (§3.3).
6. **"The ladder is produced somewhere in this harness."** Refuted by P4's flat
   synthetic ladder (§3.4).
7. **"M3's scale centre (−22, −113) is a calibration constant."** Refuted: it
   varies per stack (§5c). 109MSDCF independently corroborates M3's value; the
   other two stacks do not.
8. **A latent bug this milestone found in its own solver.** On a *disconnected*
   training graph, `numpy.linalg.lstsq` returned a minimum-norm solution of order
   1e16 for the unconstrained frames while still reporting full coverage. Fixed
   by restricting the solution to the connected component containing frame 0 and
   reporting the rest as unplaced. Anyone implementing this in `strehl-core`
   must do the same. **MEASURED** (it appeared in the 109MSDCF span 8–32 row,
   5 components).
9. **"P1 reproduces M3 §0 verbatim."** My own claim, **retracted** (§1.2). It was
   true only of the pre-fix harness, and the residual columns being compared were
   never the same statistic. The corrected statement is that the port lands in the
   same regime, and the estimator floor this report relies on is P1b's 432-warp
   distribution, measured post-fix. Recorded here rather than quietly edited,
   because the project's rule 8 is about what was actually run.

## 9. What could not be measured

* **The true total magnification change of coffee-bean.** Bracketed at −5.2 % to
  −5.9 %; not pinned, because the stack has no trustworthy long anchor (§3.2).
* **Why the ladder persists at spans 4–8** when the marginal-response control is
  unbiased above 0.48 px (§3.3).
* **Whether the shrinkage can be calibrated away.** A span-dependent correction
  fitted from the long edges is the obvious next move, but fitting and testing it
  on the same 105 frames would not be an out-of-sample test, and no second deep
  stack exists. **Not attempted rather than attempted badly.**
* **Absolute accuracy on real deep data.** There is no ground truth. Every real
  figure here is held-out or cycle-based; the only absolute figures are P4's, on
  synthetic frames.

---

## 10. Data provenance

`C:\dev\macro` and `D:\macro-dark-frames` were opened read-only throughout.
File counts and total bytes, recorded at the start of M10 and re-audited at the
end (`out/data-audit.txt`):

| directory | files | bytes |
| --- | --- | --- |
| `C:\dev\macro\test\coffee-bean` | 105 | 4,161,077,248 |
| `C:\dev\macro\test\109MSDCF` | 22 | 836,440,064 |
| `C:\dev\macro\test\119MSDCF` | 35 | 1,275,820,519 |
| `D:\macro-dark-frames` | 242 | 8,179,392,512 |

**Unchanged.** **MEASURED.**

Raw CSVs are committed under `experiments/m10-deep-align/data/` and console logs
under `out/`, per project rule 12, so every table above can be re-derived without
trusting this prose.
