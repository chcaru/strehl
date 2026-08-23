# M9 — the merge regulariser is not coupled to the focus measure's support

**Status:** measured. Answers SYNTHESIS §10 open question 9 and rules on
plugin-review item **B3**.

Reproduction: `experiments/m9-support/README.md`. Every number below is in
`experiments/m9-support/data/analysis-*.txt`, produced by the exact commands in
that file. Harness: `experiments/m9-support/src/`. Pre-registration:
`experiments/m9-support/PREREGISTRATION.md`, committed in `f29e4db` **before any
cross-measure number existed** — the ordering is checkable from `git log`.

---

## Verdict

**B3 dies. `support_px()` comes off the plugin interface.** MEASURED, high
confidence, replicated on two stacks and robust to leave-one-out.

The decision was framed as: if the noise-optimal regulariser width tracks the
focus measure's support, a merge cannot be configured without knowing it and
`support_px()` is mandatory; if the optimum is independent of support, B3 dies.
The measurement answers a sharper version of that question — *what does a
framework gain by being told the support?* — and the answer is **nothing**.

A merge that knows only `support_px()` and picks the best width for each support
class achieves worst-case regret **0.0646** ratio units on 109MSDCF and
**0.0037** on 119MSDCF. A blind framework that picks one width for everything
achieves **0.0646** and **0.0045**. The value of the method is therefore
**+0.0000** and **+0.0009** ratio units, against a pre-registered severity floor
of 0.02 — between 200× and 20× below the bar. Dropping any single measure from
the design does not change this (worst leave-one-out: +0.0001 / +0.0010). For
scale, the *placebo* run — where the winner is elected on G1 and the noise
evaluated on G2, so no noise-election defect can exist to regularise away —
produces a spurious value of **+0.0326** for the same statistic. **The real
result sits an order of magnitude below the statistic's own false-positive
floor.**

The support radius is not what the merge is fighting. What it is fighting is
**how much of the focus response at a pixel comes from that pixel's own value** —
the centre-tap sensitivity fraction φ. Across the 16 crossed treatments, φ
predicts naive-argmax noise excess at Spearman **ρ = +0.917** (109MSDCF, p <
0.0001) and **+0.891** (119MSDCF, p < 0.0001), while the support radius is
**uncorrelated** with it: **ρ = −0.207** (p = 0.44) and **−0.243** (p = 0.37).
Two operators with an identical declared `support_px()` of 25 differ by a factor
of **86× in φ** (dsml-s12 at 0.465, tenengrad-w11 at 0.0031) and by **0.74
ratio units** in argmax excess. `support_px()` cannot distinguish them, so it
cannot be the input a merge needs.

And φ needs no interface at all. It is a property the framework can measure
itself, by finite-differencing any contributed measure — which is exactly how it
was measured here. **B3 should be replaced by nothing on the interface.**

Two things this does *not* say. It does not say the regulariser is unnecessary:
regularising is worth 0.23–0.32 ratio units on the shipped measure, and for the
worst measure in the design 0.77. It does not say fact 25 is wrong: fact 25's
3–7 px is a real measurement of the shipped operator. What is wrong is the
*reading* of fact 25 — the coincidence between "3–7 px" and "the shipped
operator's 3 and 7 px radii" is a coincidence, and the mechanism is φ. See
"Contradictions" below.

**One caveat on the epistemic status, stated up front rather than buried.** The
pre-registered decision rule does not cleanly cover the outcome that occurred
(§3.6): the confirm branch fails, the kill branch fails on its second clause,
and the Intermediate branch was written for the opposite sign of `R*` vs `T`.
The ruling therefore rests on (a) the failure of the confirm rule's load-bearing
clause — `W90` does not track support *specifically* — on both stacks, and
(b) S7, which was added after the pre-registered statistics returned an
unreadable answer, and which was validated against the placebo before being
believed. That is a weaker position than a clean pre-registered kill would have
been. It is not weak enough to change the ruling, given the two-order-of-
magnitude margin and the two-stack replication, but the reader should know which
part is pre-registered and which is not.

---

## Headline table

| # | Claim | 109MSDCF | 119MSDCF | Label |
| --- | --- | --- | --- | --- |
| 1 | **Value of `support_px()`** (worst-case regret saved) | **+0.0000** | **+0.0009** | **MEASURED** |
| 2 | Same, worst over all leave-one-out subsets | +0.0001 | +0.0010 | MEASURED |
| 3 | Pre-registered severity floor it must clear | 0.02 | 0.02 | pre-registered |
| 4 | Value of `support_px()` in the **placebo** (no defect exists) | +0.0326 | — | MEASURED (false-positive floor) |
| 5 | Value of an operator-**family** label | +0.0000 | +0.0000 | MEASURED |
| 6 | Value of family **and** support together (the oracle) | 0.0646 → 0.0000 | 0.0045 → 0.0000 | MEASURED |
| 7 | ρ(centre-tap fraction φ, argmax noise excess) | **+0.917**, p < 0.0001 | **+0.891**, p < 0.0001 | MEASURED |
| 8 | ρ(support radius, argmax noise excess) | **−0.207**, p = 0.44 | **−0.243**, p = 0.37 | MEASURED (null) |
| 9 | S2, ρ(support radius, knee width `W90`) | +0.372, p = 0.159 | +0.629, p = 0.012 | MEASURED |
| 10 | S2 within-family / between-family spread of `W90` | 0.55 | 0.93 | MEASURED (pre-reg wants ≥ 2.0) |
| 11 | S6 discriminator, same `support_px` = 25: dsml-s12 vs ring-4-12 `W90` | 13 vs 21 | 17 vs 81 | MEASURED — DIFFER |
| 12 | φ spread at fixed `support_px` = 25 | 0.465 / 0.0054 / 0.0031 | 0.437 / 0.0055 / 0.0028 | MEASURED — 86–156× |
| 13 | Null control: 5 declared supports, one operator | pooled `W90` = 17 for all 5 | = 21 for all 5 | MEASURED — PASS |
| 14 | Positive control: support genuinely varies | `W90` 17→161, ρ = +0.667 | 21→81, ρ = +0.462 | MEASURED — PASS |
| 15 | M2 reproduction, naive argmax, ROI `2272,1344,256,256` | **1.2527×** (M2: 1.253×) | — | VERIFIED |
| 16 | M2 reproduction, 17×17 regularised, same ROI | 1.0737× (M2: 1.075×) | — | VERIFIED to 0.08 % |
| 17 | Shipped measure ring(1,3): φ measured / analytic `1/(2·(2i+1)²)` | 0.05499 / 0.05556 | 0.05505 | MEASURED + DERIVED |
| 18 | Best and worst argmax excess in the design | 0.9952× (tenengrad-w0) to 1.8330× (dsml-s12) | 1.2232× to 1.9176× | MEASURED |
| 19 | Harm zone: regularising worse than not, shipped measure at w=3 | 1.3625× vs 1.2527× | 1.4213× vs 1.3729× | MEASURED |
| 20 | Widths swept / measures / ROIs / rows per sweep | 19 / 26 / 5 / 2,470 | same | — |

Ratio units throughout are **σ(stacked) / σ(single frame)**, both **spatial**
standard deviations of the same 256×256 flat ROI on the same plane, per M2.
Lower is better. No temporal quantity appears anywhere in this document
(project rule 10).

Stacks: 109MSDCF (f/11, ISO 160, 22 frames), 119MSDCF (f/5.6, ISO 50, 33
frames). Both decode to a 3516×2344 plane, black 512, white 15360.

---

## 1 — The question, and what would settle it

B3 argues that a contributed focus measure must declare `support_px()` because
the merge's regulariser has to be sized to match it. The motivating evidence is
**fact 25 (MEASURED, M2)**: naive per-pixel argmax raises flat-region noise to
**1.253×** a single frame, and the excess is spatially correlated over **3–7
px** — read at the time as "exactly the support of the shipped ring(1,3)
operator", hence "the measure and the merge are coupled through support".

That reading has an alternative it was never tested against. `ring(1,3)` is not
only a 7-px-support operator; it is also an operator whose response at a pixel
depends substantially on that pixel. Support and self-dependence move together
in the shipped measure, so M2 could not separate them. **Separating them is what
this milestone is for.**

### 1.1 The design

`src/measures.rs` defines 26 measures.

**16 treatments** — a fully crossed **4 families × 4 support radii** design:

| | radius 1 | radius 3 | radius 6 | radius 12 |
| --- | --- | --- | --- | --- |
| **ring** (difference of box means) | ring-0-1 | ring-1-3 *(shipped)* | ring-2-6 | ring-4-12 |
| **tenengrad** (Sobel magnitude, then box mean of width `w`) | tenengrad-w0 | tenengrad-w2 | tenengrad-w5 | tenengrad-w11 |
| **sml** (sum-modified Laplacian, then box mean of width `w`) | sml-w0 | sml-w2 | sml-w5 | sml-w11 |
| **dsml** (SML *dilated* to stride `s` — same 5 taps, spread wider) | dsml-s1 | dsml-s3 | dsml-s6 | dsml-s12 |

The crossing is the entire point. A sweep over support alone cannot distinguish
"the optimum tracks support" from "the optimum tracks whatever else changed with
it". Here, ring-0-1 / tenengrad-w0 / sml-w0 / dsml-s1 share a support radius and
differ in family; ring-0-1 / ring-1-3 / ring-2-6 / ring-4-12 share a family and
differ in support.

**dsml is the discriminator.** It reads exactly five pixels, dilated to a stride
of `s`. `dsml-s12` therefore declares `support_px() = 25` — identical to
`ring-4-12` — while reading 5 pixels rather than 625, a **125× lower read
density at the same declared support**. If anything on the interface is going to
mis-serve a plugin, this pair is where it shows.

**5 null controls** `nullctl-d{1,3,6,12,24}` — all literally `ring(1,3)`. Only
the *declared* `support_px()` differs. Any statistic that moves across these is
reading the declaration, not the operator.

**5 positive controls** `posctl-e{0,4,10,20,38}` — `ring(1,3)` followed by an
extra box mean, so the *real* support genuinely varies (3 / 7 / 13 / 23 / 41 px)
with the family fixed. A statistic that cannot move here cannot be trusted to
report absence when it does not move on the treatments.

### 1.2 Pre-registered statistics

Quoted from `PREREGISTRATION.md` §2–§4, written and committed before any
cross-measure result existed.

| | Statistic | Role |
| --- | --- | --- |
| **S1** | `W90(m)`, the smallest width at which measure `m` reaches within 10 % of its own best noise ratio | the per-measure quantity everything else is built from |
| **S2** | Spearman ρ(support radius, `W90`) over the 16 treatments, permutation p, plus within-family vs between-family spread | does the knee track support *specifically*? |
| **S3** | `R*`, worst-case regret of one blind width against a per-measure oracle | how much does blindness cost? |
| **S4** | Is there a single width inside every measure's usable band (noise within 10 % of floor **and** detail gradient within 5 % of peak)? | is one width even feasible? |
| **S5** | Harm zone `Wharm` — the widest width that is *worse* than no regularisation | does the danger zone track support? |
| **S6** | dsml-s12 vs ring-4-12: same declared support, 125× different read density | is the declaration *sufficient*? |

Quoted verbatim from `PREREGISTRATION.md` §3:

> **B3 is CONFIRMED** if all of:
> 1. `|rho| >= 0.6` with the within-family range of `W90` across support at least
>    twice the between-family range at fixed support — i.e. `W90` tracks support
>    specifically, not operator family; **and**
> 2. `R* > T` … **or** the band intersection of S4 is empty …
>
> **B3 is KILLED** if:
> 1. `R* <= T`, **and**
> 2. the band intersection of S4 is non-empty.
>
> **Intermediate** — `R* > T` but `W90` tracks family as strongly as support — is
> reported as "coupled, but not to support", and B3 still comes off the interface
> because `support_px()` would not be the number that fixes it.

**Severity threshold `T`** (pre-registered §4): `T = max(0.02, 3·s_roi)`, where
`s_roi` is the between-ROI spread of the shipped measure's ratio at width 17.
The 0.02 floor was justified in advance from M2's own reproducibility: M2 ran
one configuration on two flat ROIs and got 1.253× and 1.263×, so 0.02 is twice
the spread that pure ROI choice produces.

**The whole-sweep null** (pre-registered §5): re-run the entire sweep electing
the winner on the G1 plane and evaluating noise on G2. The two green planes see
independent read noise, so **no noise-election defect can exist**. Anything the
statistics report there is their own false-positive rate.

---

## 2 — Controls, before any result

### 2.1 The statistic, before any sensor

`cargo run --release -- selftest` — **102 assertions, all pass**. Group D is the
load-bearing one: the knee statistic `W90` is exercised against **planted**
curves before it is pointed at data. It must return the first grid crossing of
the 10 % target (property, not formula re-derivation), must be strictly monotone
across planted decay scales, and must handle a knee at the grid edge. Project
rule: a gate written from a model of the system tests the model, not the system.

Groups A–C and E–G additionally verify each measure's response ordering
(sharp > blurred), shift invariance, and read extent by spike test.

### 2.2 The measurement chain, against M2 and against the shipped CLI

`data/xcheck-109MSDCF.txt`:

| | σ(stacked) | σ(single) | ratio |
| --- | --- | --- | --- |
| Shipped `strehl stack --flat-roi`, **full plane** | 35.328 DN | 28.201 DN | 1.253× |
| This harness, **466² tile** | 35.328 DN | 28.201 DN | 1.2527× |

Every printed digit identical — VERIFIED. The tile path is additionally shown
**margin-independent**: identical rows at margin 11 and at margin 131. And the
`--measures` filter uses the *whole design's* maximum support to size the tile,
so a filtered run is byte-identical to the full run (verified, 16/16 pilot
rows).

M2's own headline reproduces exactly at width 1 (**1.2527×** vs published
1.253×). M2's 17×17 regularised row reproduces to **0.08 %** in stacked sigma
(30.280 vs 30.305 DN; 1.0737× vs 1.075×). That residual is not resolved — see
"What I could not establish".

Two internal consistency checks that must hold by construction and do:
`sml-w0 ≡ dsml-s1` (identical numbers throughout) and `posctl-e0 ≡ ring-1-3`
(identical top 1.2945 and floor 1.0646).

### 2.3 Null control — does the statistic read the declaration?

Five measures that are all literally `ring(1,3)`, differing only in what
`support_px()` returns.

| measure | declared | real | `W90` per ROI | pooled `W90` |
| --- | --- | --- | --- | --- |
| nullctl-d1 | 3 | 7 | [13, 41, 81, 17] | 17 |
| nullctl-d3 | 7 | 7 | [13, 41, 81, 17] | 17 |
| nullctl-d6 | 13 | 7 | [13, 41, 81, 17] | 17 |
| nullctl-d12 | 25 | 7 | [13, 41, 81, 17] | 17 |
| nullctl-d24 | 49 | 7 | [13, 41, 81, 17] | 17 |

**PASS** — one distinct value across five declarations, on both stacks (17 on
109MSDCF, 21 on 119MSDCF). The statistic ignores the declaration.

### 2.4 Positive control — can the statistic see support at all?

Five measures where support genuinely varies with the family fixed.

| measure | real support | pooled `W90` (109) | pooled `W90` (119) |
| --- | --- | --- | --- |
| posctl-e0 | 7 | 17 | 21 |
| posctl-e4 | 15 | 97 | 41 |
| posctl-e10 | 27 | 161 | 81 |
| posctl-e20 | 47 | 129 | 65 |
| posctl-e38 | 83 | 129 | 81 |

**PASS** — `W90` spans 17→161 (9.5×) with ρ = +0.667 on 109MSDCF, and 21→81
(3.9×) with ρ = +0.462 on 119MSDCF. **The statistic can detect support-driven
movement, so its null on the treatments is informative rather than merely
underpowered.** This is the control that licenses a negative result. It has a
real weakness, disclosed in §6.2.

### 2.5 The whole-sweep null — the statistic's false-positive floor

Re-running everything with selection on G1 and evaluation on G2 removes the
defect entirely. Whatever the statistics report there, they report from nothing.

| statistic | placebo | real (109MSDCF) |
| --- | --- | --- |
| S2 ρ(support, `W90`) | **+0.635**, p = 0.012 | +0.372, p = 0.159 |
| S2 within/between | 1.06 | 0.55 |
| `R*` | 0.0479 | 0.0646 |
| **value of `support_px()`** | **+0.0326** | **+0.0000** |
| value of family label | +0.0205 | +0.0000 |
| ρ(φ, argmax excess) | −0.189, p = 0.475 | **+0.917**, p < 0.0001 |
| ρ(support, argmax excess) | +0.557, p = 0.030 | −0.207, p = 0.441 |

Three things follow, and they matter more than any single real-data number.

1. **The S7 headline is safe.** The measured value of `support_px()` on real
   data (+0.0000) is *far below* what the same statistic manufactures from
   nothing (+0.0326). A negative result that is smaller than the statistic's own
   noise floor is as strong as a negative result gets.
2. **S2 is not trustworthy on its own.** The placebo produces ρ = +0.635 at
   p = 0.012 — a "significant" support correlation where no coupling exists.
   Mechanism: wider measures smooth the *focus field* more regardless of what is
   being elected, so the knee moves for reasons unrelated to noise election. Any
   reading of S2 alone would have been a false positive. This is exactly why S7
   was added.
3. **The φ result is not an artefact of the design.** ρ(φ, excess) collapses
   from +0.917 to −0.189 in the placebo. φ predicts noise excess only when there
   *is* a noise-election defect to predict — which is what "φ is the mechanism"
   requires.

---

## 3 — Results

### 3.1 S7 — what a framework gains from being told the support

This is the headline, and it is the statistic that most directly matches the
decision. For each of the 16 treatments, take the best achievable ratio over the
19 widths (the per-measure oracle). Then ask what worst-case regret against that
oracle a framework suffers under three information regimes.

**109MSDCF:**

| the framework knows | worst-case regret `R` |
| --- | --- |
| nothing — one width for everything | 0.0646 at w = 257 |
| **`support_px()` only** | **0.0646** |
| the operator family only | 0.0646 |
| family **and** support | 0.0000 |

**Value of `support_px()` = 0.0646 − 0.0646 = +0.0000 ratio units.**

**119MSDCF:**

| the framework knows | worst-case regret `R` |
| --- | --- |
| nothing | 0.0045 at w = 129 |
| **`support_px()` only** | **0.0037** |
| the operator family only | 0.0045 |
| family and support | 0.0000 |

**Value = +0.0009 ratio units.** Both are below the pre-registered 0.02 floor,
and far below the pre-registered `T` (0.1155 and 0.4839).

Leave-one-out: dropping any single treatment and recomputing leaves the value at
+0.0000 for 15 of 16 subsets on 109MSDCF, and at +0.0001 for the sixteenth
(dropping `tenengrad-w0`). The 119MSDCF worst case is +0.0010. **The result is
not carried by any single measure.**

Note row 6: the *oracle* — knowing family and support — does reach zero regret.
Per-measure tuning is worth 0.065 ratio units. **It is just not obtainable from
`support_px()`, or from a family label, or from both taken one at a time.**
Something identifies the right width; it is not this method.

### 3.2 S8 — what the noise excess actually tracks

The addition that explains why. Define the **centre-tap sensitivity fraction**

> φ = |∂r(p)/∂L(p)| ÷ Σ_d |∂r(p)/∂L(p+d)|

— the share of a measure's response at a pixel that comes from that pixel's own
value. All these operators are shift-invariant away from borders, so
`∂r(q)/∂L(p)` depends only on `q − p` and the whole kernel comes back from one
sparse-lattice perturbation pass at spacing `4·reach + 2` = 166 px, wider than
twice the largest support. Measured on **real frames at the real noise level**,
not on synthetic noise (project rule).

The intuition is a selection argument. Naive argmax picks, at each pixel, the
frame whose focus response is highest there. If the response at a pixel depends
strongly on that pixel, the election is decided partly by that pixel's own read
noise, and argmax systematically elects *upward noise excursions* — a
winner's-curse. If the response is dominated by neighbours, the pixel cannot
vote for itself and the defect largely disappears.

**109MSDCF**, sorted by φ:

| measure | support px | taps | **φ** | ratio at w=1 | floor | excess |
| --- | --- | --- | --- | --- | --- | --- |
| ring-0-1 | 3 | 9 | 0.4847 | 1.6917 | 1.0525 | 0.639 |
| dsml-s12 | **25** | **5** | 0.4653 | **1.8330** | 1.0608 | 0.772 |
| dsml-s6 | 13 | 5 | 0.4477 | 1.7924 | 1.0609 | 0.732 |
| dsml-s3 | 7 | 5 | 0.4380 | 1.7305 | 1.0628 | 0.668 |
| dsml-s1 / sml-w0 | 3 | 5 | 0.4357 | 1.6180 | 1.0294 | 0.589 |
| **ring-1-3 (shipped)** | 7 | 49 | **0.0550** | **1.2945** | 1.0646 | 0.230 |
| sml-w2 | 7 | 25 | 0.0357 | 1.0954 | 1.0353 | 0.060 |
| tenengrad-w2 | 7 | 25 | 0.0346 | 1.2150 | 1.0597 | 0.155 |
| ring-2-6 | 13 | 169 | 0.0192 | 1.2514 | 1.0600 | 0.191 |
| sml-w5 | 13 | 121 | 0.0079 | 1.0395 | 1.0395 | 0.000 |
| tenengrad-w5 | 13 | 121 | 0.0065 | 1.1142 | 1.0596 | 0.055 |
| ring-4-12 | **25** | **625** | 0.0054 | 1.1645 | 1.0497 | 0.115 |
| sml-w11 | 25 | 529 | 0.0037 | 1.0386 | 1.0386 | 0.000 |
| tenengrad-w11 | 25 | 529 | 0.0031 | 1.0911 | 1.0601 | 0.031 |
| **tenengrad-w0** | 3 | 9 | **0.0028** | **0.9952** | 0.9952 | 0.000 |

> **ρ(φ, excess) = +0.917, p < 0.0001. ρ(support radius, excess) = −0.207,
> p = 0.441.** Replicated on 119MSDCF: **+0.891** (p < 0.0001) and **−0.243**
> (p = 0.368).

Three rows carry the whole argument.

- **`dsml-s12` vs `ring-4-12`** — identical declared `support_px()` of 25, and
  the worst and near-best excess in the design (0.772 vs 0.115). They differ by
  86× in φ and 125× in read density. `support_px()` returns the same number for
  both. It is not the input a merge needs.
- **`tenengrad-w0` is a built-in placebo.** A 3×3 Sobel has a zero centre column
  and a zero centre row, so it is *structurally blind to its own centre pixel*
  and cannot elect its own noise. Measured excess: **0.0000** — naive argmax
  with this measure is not noisier than a single frame at all (0.9952×). Its
  residual φ = 0.0028 is not zero only because `focus = raw / max(σ(L), ε)`
  normalises by a sigma evaluated at the centre pixel's own level.
- **The shipped `ring-1-3` at φ = 0.0550.** Analytically, a ring difference
  `|mean(2i+1) − mean(2o+1)|` has centre coefficient `1/a − 1/b` and total
  absolute coefficient `2(1 − a/b)` for `a = (2i+1)²`, `b = (2o+1)²`, so

  > **φ = 1 / (2a) = 1 / (2·(2·INNER_RADIUS + 1)²)**

  — a function of the **inner** radius alone, independent of the outer radius
  entirely. `1/18 = 0.05556` against 0.05499 measured; the shortfall is the
  sigma normalisation, which also moves when the centre pixel moves. DERIVED,
  and it is checked in `crates/strehl-core/src/focus.rs` by a regression test
  (see §5). This is the cleanest possible statement that support and
  self-dependence are different quantities: **for a ring operator, changing the
  support changes φ not at all unless the inner radius changes.**

`taps` (kernel entries above 1e-6) independently validates each measure's read
extent from the same probe: ring-0-1 → 9, ring-1-3 → 49, ring-2-6 → 169,
ring-4-12 → 625, tenengrad-w0 → 9, sml-w0 → 5, dsml-s12 → 5.

### 3.3 S2 — the pre-registered correlation, and why it does not decide anything

| | 109MSDCF | 119MSDCF | placebo | pre-reg confirm needs |
| --- | --- | --- | --- | --- |
| ρ(support, `W90`) | +0.372 | +0.629 | +0.635 | \|ρ\| ≥ 0.6 |
| p (permutation) | 0.159 | 0.012 | 0.012 | — |
| within/between | 0.55 | 0.93 | 1.06 | ≥ 2.0 |

The pre-registered confirm condition is **not met on either stack**. On 109MSDCF
neither half passes. On 119MSDCF ρ = +0.629 clears 0.6, but within/between =
0.93 is far below the required 2.0 — and that half is the one that carries the
meaning, since the condition is glossed in the pre-registration as "`W90` tracks
support *specifically*, not operator family".

The within/between ratio is the informative half and it is decisive on both
stacks. `W90` grids, rows = family, columns = support radius:

**109MSDCF** — within-family range 41.5 px, between-family range 75.5 px:

| family | r=1 | r=3 | r=6 | r=12 | range |
| --- | --- | --- | --- | --- | --- |
| dsml | 7 | 9 | 9 | 13 | 6 |
| ring | 5 | 17 | 21 | 21 | 16 |
| sml | 7 | 17 | 1 | 1 | 16 |
| tenengrad | 1 | 49 | 129 | 129 | 128 |
| **range** | **6** | **40** | **128** | **128** | |

**119MSDCF** — within-family 41.0 px, between-family 44.0 px:

| family | r=1 | r=3 | r=6 | r=12 | range |
| --- | --- | --- | --- | --- | --- |
| dsml | 13 | 13 | 17 | 17 | 4 |
| ring | 13 | 21 | 33 | 81 | 68 |
| sml | 13 | 25 | 33 | 33 | 20 |
| tenengrad | 33 | 25 | 81 | 97 | 72 |
| **range** | **20** | **12** | **64** | **80** | |

Changing the family at a fixed support moves `W90` at least as much as changing
the support at a fixed family. Whatever the merge is tracking, `support_px()` is
not a sufficient statistic for it.

**But S2 must not be read on its own**: the placebo yields ρ = +0.635 at
p = 0.012 with no defect present at all (§2.5). S2's apparent significance on
119MSDCF is within what the statistic manufactures from nothing.

### 3.4 S6 — the discriminator

`dsml-s12` and `ring-4-12` both declare `support_px() = 25`. Their noise-optimal
knees:

| | 109MSDCF | 119MSDCF |
| --- | --- | --- |
| dsml-s12 (5 taps) | `W90` = 13 | 17 |
| ring-4-12 (625 taps) | `W90` = 21 | 81 |

**DIFFER on both stacks**, by 1.6× and 4.8×. Pre-registered reading: the
declaration is **not** sufficient to size the regulariser. Combined with S7 —
which shows the declaration also does not *help* — the method is neither
sufficient nor useful.

### 3.5 S3, S4, S5 — the supporting statistics

**S3, one blind width.** `R*` = **0.0646** at w = 257 (109MSDCF, worst measure
tenengrad-w0) and **0.0045** at w = 129 (119MSDCF). Against the pre-registered
`T` (0.1155 / 0.4839): **BELOW — one width serves everything.** Against the
stricter 0.02 floor: 109MSDCF exceeds it, 119MSDCF does not. Note this is a
statement about *blind* regret; S7 shows knowing the support does not reduce it.

**S4, is there a width in every measure's usable band?** Band = noise within
10 % of the measure's own floor **and** detail-ROI gradient within 5 % of its
peak. **Intersection empty on both stacks** — pre-registered as *confirming*
B3. It does not, and the reason is in the per-measure detail:

> measures whose own band is empty (109MSDCF): `dsml-s1, dsml-s3, dsml-s6,
> ring-0-1, sml-w0, tenengrad-w0`

Six of the sixteen have **no width at all** that satisfies them — no possible
value of `support_px()` could help, because there is nothing to point at. All
six are high-φ measures (or, for tenengrad-w0, a measure with no noise problem
whose *floor is its width-1 value*, so the noise half of the band is trivially
satisfied while the detail half never is). Restricted to the ten measures with a
non-empty band, the intersection is still empty on 109MSDCF but is **{97}** on
119MSDCF. S4's "confirm" is therefore an artefact of measures that are
unregularisable rather than differently-regularisable, and it is not evidence for
an interface method.

**S5, the harm zone.** Regularising can be *worse* than not regularising. The
shipped `ring-1-3` at width 3 scores **1.3625×**, worse than **1.2527×** at
width 1. Mechanism: a 3×3 average of a focus field whose decision noise is
already correlated over ~3 px does not average the noise down, but does spread
each spike over a 3×3 patch, making the selection error more spatially coherent.
`Wharm` vs support: ρ = **+0.229** (109MSDCF), and **−0.335** in the placebo.
For the three lowest-φ measures (tenengrad-w0, sml-w5, sml-w11) *every* width is
worse than width 1 — again φ-driven, not support-driven. Pre-registered reading:
`Wharm` does not track support. **Kills, does not confirm.**

---

### 3.6 How the pre-registered decision rule actually resolves

It does not resolve cleanly, and that has to be said plainly.

| pre-registered branch | requires | observed 109MSDCF | observed 119MSDCF | met? |
| --- | --- | --- | --- | --- |
| **CONFIRMED** cond. 1 | \|ρ\| ≥ 0.6 **and** within/between ≥ 2 | ρ = 0.372, w/b = 0.55 | ρ = 0.629, w/b = 0.93 | **no** (both) |
| CONFIRMED cond. 2 | `R*` > `T` **or** S4 empty | S4 empty | S4 empty | yes |
| **KILLED** cond. 1 | `R*` ≤ `T` | 0.0646 ≤ 0.1155 | 0.0045 ≤ 0.4839 | yes |
| **KILLED** cond. 2 | S4 intersection non-empty | empty | empty | **no** |
| **Intermediate** | `R*` > `T` **and** family tracks as strongly as support | `R*` ≤ `T` | `R*` ≤ `T` | n/a |

So the outcome falls in a cell the pre-registration did not enumerate: **the
confirm rule fails, the strict kill rule fails on its second clause, and the
Intermediate branch is defined only for the opposite sign of `R*` vs `T`.**
Writing a decision rule that does not cover the observed data is a real defect
in the pre-registration and it is recorded here rather than smoothed over.

Two things make the ruling nonetheless unambiguous, and both were available
without any post-hoc licence:

1. **The load-bearing clause of CONFIRMED fails on both stacks, and it fails on
   the half that carries the meaning.** Condition 1 is explicitly glossed in the
   pre-registration as "`W90` tracks support *specifically*, not operator
   family". Within/between is 0.55 and 0.93 — family moves the knee at least as
   much as support does, on both stacks. That is precisely the situation the
   Intermediate branch was written for, and the pre-registration states its
   consequence in advance: *"B3 still comes off the interface because
   `support_px()` would not be the number that fixes it."* The only mismatch is
   that `R*` came in below `T` rather than above, which makes the case for B3
   **weaker**, not stronger.
2. **S4's "empty" is not evidence of coupling** (§3.5). Six of sixteen measures
   have no width that satisfies *them*, so no value of `support_px()` could help.
   S4 was pre-registered on the assumption that an empty intersection means
   "different measures need different widths"; the data say it means "some
   measures cannot be regularised into a usable band at all". The pre-registered
   reading of S4 is wrong on its own terms.

## 4 — Why the objective has no interior optimum

A structural finding that changes how the brief's "find the optimum" should be
read, and it must be stated plainly because it constrains everything above.

**The flat-ROI noise objective is monotone-decreasing then flat. It has no
interior minimum.** On 109MSDCF the last ten widths for the shipped measure sit
inside a 0.005-unit band, and the grid argmin lands at the sweep edge (257) for
9 of 16 treatments even after the grid was extended from 129 to 257.

The mechanism is degeneracy, not optimality. As the regulariser widens, the
winner map goes constant over the ROI — distinct winners fall from 22 to 2 — the
stack degenerates to a single frame, and the ratio asymptotes to
σ(elected frame) / σ(middle frame) ≈ 1.07. That asymptote is *above* 1.0 because
the selector correctly picks the **sharper** frame, whose spatial standard
deviation is higher in any region carrying residual structure. Widths beyond the
256-px ROI are degenerate by construction.

Consequences, all honoured above:

- The pre-registered statistic is the **knee** `W90`, not the argmin. This was
  fixed in the pre-registration, from a pilot on the shipped measure alone,
  disclosed in `PREREGISTRATION.md` §0.
- S4 is **two-sided** — a detail-ROI gradient control is required, or the
  "optimum" is just "smooth until nothing is selected".
- A noise-only objective cannot be used to argue for *any* width. The real merge
  will be tuned against a detail-preservation objective this milestone does not
  own.

---

## 5 — The regression test and its negative control

New test: `crates/strehl-core/src/focus.rs :: centre_tap_fraction_is_the_value_m9_measured`.
It measures φ for the shipped focus measure **on the shipped code path** by
finite difference and pins:

- the read extent — **49 taps**, the 7×7 outer box, which fixes `OUTER_RADIUS`;
- φ at low contrast against the analytic `1/(2·(2·INNER_RADIUS+1)²) = 1/18`,
  which fixes `INNER_RADIUS`;
- φ at a realistic operating point, 0.0507 ± 0.0015 (below 1/18 because the
  sigma normalisation also responds to the centre pixel, and that term scales
  with the response);
- that φ sits clear of the values the neighbouring inner radii would give
  (1/2 and 1/50).

The number the test defends is M9's mechanism: if the shipped measure's
noise-election behaviour changes, this ruling's basis changes with it.

**Negative control** (`experiments/m9-support/negative-control.ps1`, output in
`data/negative-control.txt`) — the test is proven to fire, not merely to pass:

```
red as required: INNER_RADIUS 1 -> 2 (phi 1/18 -> 1/50)
red as required: OUTER_RADIUS 3 -> 5 (read extent 49 -> 121 taps)
    assertion `left == right` failed: read extent must be the 7x7 outer box, got 121 taps
restored and green again
NEGATIVE CONTROL PASSED: the test fires for both planted regressions.
```

The script restores from a byte copy and bumps `LastWriteTime` afterwards —
`Copy-Item` preserves the source mtime and cargo would otherwise silently skip
the rebuild. It never uses `git checkout --`.

Workspace: **67 tests** (66 + 1), `cargo fmt --all -- --check` clean,
`cargo clippy --workspace --all-targets -- -D warnings` clean.

---

## 6 — Deviations from the pre-registration

`PREREGISTRATION.md` §7 requires these be listed. Five.

**6.1 S7 and S8 are additions, not pre-registered.** S7 (value of the method)
and S8 (φ) were added after the pre-registered statistics returned an unreadable
answer: S2 near its kill boundary, S4 "confirming" for the wrong reason. They
are the headline, so this matters. Two mitigations: both were run **through the
placebo** before being believed (§2.5), where S7 manufactures +0.0326 from
nothing and ρ(φ, excess) collapses to −0.189; and both replicate on a second
stack. S8 in particular is a **post-hoc mechanism**, and should be read as a
strong hypothesis with two-stack support and a working placebo, not as a
pre-registered confirmation.

**6.2 The pre-registered threshold `T` is badly matched, and I report against a
stricter one.** Measured `s_roi` = 0.0385 on 109MSDCF → `T` = 0.1155, and 0.1613
on 119MSDCF → `T` = 0.4839 (119MSDCF has no genuinely flat region: best
structure-corrected sd 26 DN vs 10 DN). But `s_roi` is a **between-ROI
difference of levels** while `R*` is a **within-ROI difference across measures**;
`T` is therefore over-permissive by construction. I report against all three
yardsticks — `T`, the 0.02 floor, and a supplementary `3 ×` sd-of-per-ROI-`R*`
(0.0367 on 109MSDCF, 0.0251 on 119MSDCF). **The S7 conclusion is identical under
all three**, because +0.0000 and +0.0009 are below the smallest of them.

**6.3 The width grid was extended mid-run**, from 10 widths ending at 33 to 19
ending at 257, because argmins were landing at the edge. It was not enough — see
§7. Extending a grid after seeing that an optimum is not interior is a
pre-registered-in-spirit action (the brief requires it explicitly) but it is a
deviation from the written grid and is recorded as one.

**6.4 `W_eff` is reported alongside `W90`, never instead of it.** The
pre-registered relative-10 % knee is **undefined in practice when a curve has no
improvement to make**: if `top == floor`, any width is within 10 % of the floor.
It returns width 1 for `tenengrad-w0` (correct — that measure has no noise
defect) but 129/161 for `posctl-e38`, from a 0.014-unit wobble at the sweep edge.
`W_eff` — the smallest width within an **absolute** 0.02 ratio units of the
measure's own floor — is degeneracy-free. It agrees with the ruling:
ρ(support, `W_eff`) = **+0.302** (p = 0.261) on 109MSDCF and **+0.102**
(p = 0.721) on 119MSDCF, both further from coupling than `W90`'s.

**6.5 The pilot.** A pilot on the shipped measure alone, run before the
pre-registration, fixed the *form* of the statistic (knee, not argmin) after the
curve was found to saturate. This is disclosed in `PREREGISTRATION.md` §0 and
its data is committed (`data/pilot-shape.csv`, `data/pilot-placebo.csv`). No
cross-measure comparison existed at that point.

**6.6 The pre-registered decision rule does not cover the observed outcome.**
Fully worked in §3.6. The confirm rule fails, the strict kill rule fails on its
second clause because S4's intersection is empty, and the Intermediate branch is
defined only for `R* > T` while the data gave `R* ≤ T`. The ruling therefore
rests on the *failure of the confirm rule's load-bearing clause* plus S7, not on
a clean trip of a pre-written kill switch. That is weaker than a
fully-specified pre-registration would have been, and the fix for next time is
to enumerate the full 2×2 rather than three of its cells.

**6.7 One ROI was substituted.** On 109MSDCF the top-ranked flat block
(`2361,1417`, structure sd 9.967 DN) was replaced by M2's `2272,1344`
(sd 10.663 DN, ranked 51st of 22,538), so that M2's exact published measurement
appears as a row of the sweep and the whole chain is anchored to it. The two
blocks overlap the same flat region and differ by 0.7 DN in structure sd. The
other three flat ROIs and the detail ROI are the top-ranked non-overlapping
blocks as reported by `rois`.

---

## 7 — What I could not establish

- **The pre-registered decision rule did not decide this.** §3.6 and §6.6. The
  ruling rests on the failure of the confirm rule's load-bearing clause plus a
  post-hoc statistic (S7) that was validated against the placebo before being
  believed. That is a weaker epistemic position than a clean pre-registered kill
  and is stated as such.
- **The noise-only objective has no interior optimum, so "the noise-optimal
  width" does not exist as the brief assumed.** §4. The brief asked for argmins
  interior to the sweep range; 9 of 16 treatments on 109MSDCF have their grid
  argmin at the widest width, 257, and extending further is pointless because the
  ROI is 256 px. I report this rather than manufacturing interiority. Everything
  above uses knee statistics, which *are* interior, but a knee is a weaker object
  than a minimum.
- **`R*`'s argmin is at the sweep edge on 109MSDCF** (w = 257), for the same
  reason. The S7 comparison is unaffected — both regimes are optimised over the
  same grid — but the absolute value of `R*` should not be quoted as "the regret
  of the best blind width" without that caveat.
- **The positive control passes partly for the wrong reason.** `W90` per ROI for
  `posctl-e10` is [1, 193, 129, 65] — enormous instability. The pooled statistic
  moves with support as required, but on flat curves it moves because the curves
  *flatten*, not only because knees *shift*. The control establishes that the
  statistic is not blind to support; it does not establish that it is a precise
  estimator of support-driven movement. A reader who wants to discount S2
  entirely on this basis would not be unreasonable — which is why the ruling
  rests on S7, whose control is the placebo, not on S2.
- **Two stacks, one camera, one lens, one subject class.** 109MSDCF and
  119MSDCF are both A7C II macro stacks. The 105-frame `coffee-bean` stack was
  not swept — it would have added a third replication at ~25 min of compute, and
  was cut for time. Nothing here is established across sensors.
- **φ is a mechanism hypothesis, not a proven causal chain.** ρ = +0.9 on 16
  points, twice, with a working placebo, plus one structural case
  (`tenengrad-w0`'s zero centre tap giving zero excess) that is close to a
  natural experiment. But no intervention experiment was run — nothing here
  *varies* φ while holding everything else fixed, which is what a causal claim
  would need. Labelled ARGUED, not MEASURED, in that form. The **correlations**
  are MEASURED.
- **M2's 17×17 regularised row reproduces to 0.08 %, not exactly** (30.280 vs
  30.305 DN). M2's regularised figure came from its own verification script,
  whose smoothing border convention and accumulator order are not recorded in the
  published document. The discrepancy is not resolvable from the doc and is not
  worth re-deriving; the width-1 headline reproduces exactly.
- **No detail-preservation optimum is offered.** The detail-ROI gradient is used
  only as a *guard* inside S4 and as context in S8's final table. A real merge
  wants a joint objective. That is a merge-stage milestone, not this one.
- **The ruling is about `support_px()` specifically.** It does not establish
  that the focus/merge interface needs *no* information — only that support
  radius is not the information it needs. φ looks like the right quantity, but
  the framework can measure φ itself, so it is an argument *against* an interface
  method, not for a different one.

---

## 8 — Contradictions with existing SYNTHESIS facts

**Fact 25 is correct and its reading is wrong.** Fact 25 records that argmax
excess noise is spatially correlated over 3–7 px and reads that as the shipped
ring(1,3) support (inner 3, outer 7). Three measurements say the coincidence is
a coincidence:

1. The focus-field autocorrelation of the shipped `ring-1-3` gives
   `L(1/e) = 2 px` and `L(0.1) = 2 px` — **shorter than its 7-px support box**
   (`data/analysis-acf-109MSDCF.txt`). The correlation length tracks internal
   averaging, not read extent: all four `dsml` measures give `L(1/e) = 1` despite
   support radii up to 12, because they read 5 pixels and average none of them.
2. Support radius does not predict argmax excess at all (ρ = −0.21 / −0.24,
   both p > 0.36), while φ predicts it at ρ = +0.92 / +0.89.
3. For a ring operator, φ = `1/(2·(2i+1)²)` depends only on the **inner**
   radius. Fact 25's "3" is the inner radius — the quantity that does drive the
   effect — and its "7" is the outer radius, which does not. Reading the pair as
   "the support" merges a load-bearing number with an irrelevant one.

No retraction is needed. A correction to the *interpretation* is, and proposed
text is in the milestone's final message.

---

## 9 — How to quote this

- **"`support_px()` is worth +0.0000 / +0.0009 ratio units against a 0.02
  floor"** — MEASURED, two stacks, leave-one-out robust, below the statistic's
  own +0.0326 false-positive floor. This is the ruling.
- **"argmax noise excess tracks centre-tap sensitivity φ at ρ ≈ +0.9, and
  support radius not at all"** — correlations MEASURED on two stacks with a
  working placebo; the *causal* reading is ARGUED.
- **"φ = 1/(2·(2·INNER_RADIUS+1)²) for a ring difference"** — DERIVED,
  regression-tested, verified against measurement to 1 %.
- **"the flat-ROI noise objective has no interior optimum"** — MEASURED,
  structural.
- **Do not quote** any single `W90` as "the optimal width for measure X". `W90`
  is a knee on a saturating curve with per-ROI instability up to 190 px. It is
  used only in aggregate and only where a control licenses it.

---

## Reproduction

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cd experiments\m9-support
powershell -NoProfile -ExecutionPolicy Bypass -File run-m9.ps1
```

Stage by stage, with the traps, in `experiments/m9-support/README.md`. The
analysis alone, from committed CSVs and with no RAW corpus:

```powershell
cd experiments\m9-support
python m9_analyse.py data\sweep-109MSDCF-coupled.csv
python m9_analyse.py data\sweep-109MSDCF-placebo.csv
python m9_analyse.py data\sweep-119MSDCF-coupled.csv
python m9_acf.py     data\acf-109MSDCF.csv
```

The regression test and its negative control:

```powershell
cargo test -p strehl-core focus::tests::centre
powershell -NoProfile -ExecutionPolicy Bypass -File experiments\m9-support\negative-control.ps1
```

**Read-only corpora.** Nothing in this milestone writes to `C:\dev\macro` or
`D:\macro-dark-frames`. Verified after the run against a pre-run baseline: file
counts, total bytes and maximum last-write times unchanged on both paths.
