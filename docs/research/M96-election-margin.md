# M96 — The focus election is decisive, not a coin flip

> **NOT INDEPENDENTLY VERIFIED.** Same author as the measurements. Rule 12.
>
> Pre-registration: `experiments/M96-election-margin/PREREGISTRATION.md`, committed
> at `cf2c5bd` — **before any Task 2 measurement ran**.
> Instrument: `crates/strehl-cli/examples/m96-election-margin.rs`.
> Raw output: `experiments/M96-election-margin/out/`.
> Renders: `C:\dev\strehl-out\M96-election-margin\`.
> Task 1's fix: `crates/strehl-cli/examples/m60-disagreement.rs`, committed at `cf2c5bd`.
>
> **Renumbered M94 → M96 mid-session**, after the measurements were taken. All
> filenames were renamed with `git mv`. **The raw logs under `out/` were left
> byte-identical and still print the original `M94` label and output path** — they
> are the provenance of every number here, and rewriting them would have made them
> no longer the output the instrument printed. Renderer output moved to
> `C:\dev\strehl-out\M96-election-margin\`. Renumber script:
> `experiments/M96-election-margin/src/renumber.py`.

---

## Verdict

**The election is decisive.** On all seven corpus stacks, the elected frame beats
every rival more than 8 frames away by a **large** fraction of the pixel's own
through-focus range, and it does so **6.0× to 23.0×** more strongly than the same
pixels with the frame order destroyed. In a paired test against its own
permutation placebo — same pixels, same response multiset, only the frame
*ordering* removed — the real election wins at **96.226% to 99.952%**, against a
measured null band of **[22.304%, 81.134%]**.

**The softness is not caused by an arbitrary election.** That closes the link the
brief identified as unexamined. It corroborates fact 1196's exoneration of the
gate from the other side: the combination stage is not choosing badly, and it is
not averaging badly either. The cause remains upstream, and the two live
candidates are the ones already measured — uncorrected drift (fact 1177) and
motion winning the election on merit (facts 1186–1190).

### The answer to the question M96 was actually commissioned for

The orchestrator asked which of two branches my data supports. **It supports the
second, and not marginally.**

> **The margin is large, the election is well-determined, and M93's targeted
> frame-rejection gate is exactly the right shape.**
>
> The rejected branch was: *if the winner routinely beats the runner-up by less
> than the noise, the election is substantially arbitrary and removing
> contaminated frames will not make it decisive.* That branch is **falsified** on
> every corpus stack. The election is already decisive **among the frames it is
> given**; it is not a coin flip that a gate would be powerless to improve.
>
> **Why this licenses M93 specifically.** A decisive argmax means the response
> surface has a real peak that the election reliably finds. So when a
> motion-contaminated frame wins (fact 1189: 4.78% of `foam`'s output pixels), it
> wins because contamination **raised its response above a genuine peak** — not
> because the peak was flat and the choice was a toss-up. Removing that frame
> therefore hands the election back to a well-determined competition, and the
> runner-up it falls back to is a real winner rather than another arbitrary pick.
> **That is the precondition M93's gate needs, and it holds.**
>
> This is a *precondition*, not a benefit measurement. It does not predict how
> much M93's gate will improve the image; M93 measured that itself (−25.25% on
> `lead-1-cpl`, −24.46% on `foam`). It says the gate is not operating on noise.

**Three things I got wrong and am reporting as wrong:**

1. **The brief's literal metric is uninformative.** Winner-minus-runner-up is an
   order statistic of the per-pixel multiset, so it is **bit-identical** under any
   permutation of the frame axis. I measured this: **0.000% wins, 100.00% ties, on
   all 8,241,504 pixels of all seven stacks.** A statistic invariant to the thing
   it is meant to test cannot test it. Everything below is at frame-distance
   `d ≥ 2`, which is the smallest `d` at which the question is answerable at all.
2. **B5 (index-map spatial coherence) is under-powered and I retire it.** The
   17×17 regulariser correlates neighbouring pixels' response curves, so
   neighbours elect the same index **even when that index is arbitrary**. In a
   planted stack where B1, B2 and B3 all read NEARLY ARBITRARY, B5 still read
   DECISIVE. Index-map coherence is manufactured by the regulariser and is not
   evidence about the election.
3. **B4's registered prediction is not supported as I summarised it**, though the
   underlying effect is real and large on deep stacks. Details in §4.

---

## Headlines

| | |
| --- | --- |
| Winner-minus-runner-up (`d=1`) under frame permutation | **100.00% ties**, 7 of 7 stacks — provably uninformative |
| Median margin at `d=8`, as a fraction of the pixel's own through-focus range | **0.290 to 0.813** (real) vs **0.022 to 0.127** (permuted) |
| Real / permuted ratio of that margin | **6.01× to 22.97×** |
| Paired win rate, `d=8` | **96.226% to 99.952%**; null band **[22.304%, 81.134%]** |
| Fraction of pixels whose `d=8` margin is under one `FOCUS_NOISE_SD` | **0.06% to 25.46%**; permuted **3.26% to 37.23%** |
| Pixels with a **disconnected** competitive set at the shipped gate, `bee-3-cpl` | **25.247%**, mean gap **29.12 frames**, `rho` p90 = **243** of 299 |
| Elected-index speckle, real vs i.i.d. null | **0.0033%–0.4639%** vs **13.06%–85.69%** — but see retirement (2) above |
| `sigma_R_hat` (analytic null, no fitted constant) / shipped `FOCUS_NOISE_SD` | **1.047× to 1.973×** on all 7 stacks |
| **Does M93's frame-rejection gate have a well-determined election to work with?** | **Yes.** See §1. |

---

## 0. Rule 40 — prior work, and the one hole it left

Searched `docs/research/`, `docs/`, `crates/` for `margin`, `runner-up`, `top-2`,
`argmax`, `winner`, `speckle`, `index map`, `coherence`, `election`, `churn`.
Six hits, one of them a live sibling I was told about only after measuring.

| Where | What it already had | Why it did not answer this |
| --- | --- | --- |
| `B-algorithms-sota.md` §2.3 | Surh et al., CVPR 2017 — "Winner Margin" as a *published confidence measure* for focus stacking | It is a method to build a weight map, not a measurement of this pipeline. No corpus number. |
| `M2-*.md` §3.1 | Elected-index speckle with two nulls: **34.381%** real, **53.496%** i.i.d., **66.174%** uniform | Measured on the **ring-difference** operator, which the project has since **retired**. Not the shipped regularised Tenengrad. |
| `M7-*.md` §3.1, §3.4 | A top-2 margin, at **one hand-picked pixel** | `n=1`. No distribution, no null. |
| `M65-*.md` | **56.70%** winner churn under an intervention | Churn measures *sensitivity to a change*, not whether the un-intervened election is determined. |
| `M93-merge-vs-frame-sharpness.md` | A spatial-coherence bar that failed in the wrong direction | See §0.1 — I initially attributed this to the wrong M93 document. |
| **`M93-election-gate.md` (`9a17d64`)** | **A live sibling building the fix my diagnostic tests the precondition for** | §0.1. |

**The hole.** `merge.rs`'s own `Gate::admits` doc-comment names it: *"No corpus row
publishes a regularised Tenengrad speckle."* TABLE 5 supplies that row. And no
corpus row published a **margin distribution** on any operator, on any stack, at
any `n > 1`.

### 0.1 Deconfliction with M93, and three things it changes

The orchestrator disclosed after I had finished measuring that
**`docs/research/M93-election-gate.md` is committed at `9a17d64` and its author is
live.** My own rule-40 search had found *a* M93 coherence failure but attributed
it to `M93-merge-vs-frame-sharpness.md`; the result actually lives in
`M93-election-gate.md` §7.2 / `P6` / `D-b`. **I read `M93-election-gate.md` in
full before writing this section.** The boundary holds and I agree with it: M93
changes *which frames may compete*; M96 measures *how decisively the argmax wins*
on the pipeline as it ships. I built no frame-rejection stage, did not touch
`robust.rs`, and did not re-derive fact 1186.

**(a) I am NOT re-deriving fact 1186, and here is the precise difference.** Both
M93 and I apply the kernel `[1,−4,6,−4,1]/6` along the frame axis, which looks
like a collision and is not one:

| | fact 1186 / M89 / M93 | M96 `sigma_R_hat` |
| --- | --- | --- |
| signal the kernel runs on | **pixel luma** `L(f)` | **focus response** `R_k` |
| normalisation | `strehl_core::noise` photon-transfer model | **none** |
| output | dimensionless `z`, analytic null `E[z²]=1` | a **scale in response units** |
| purpose | flag frames discrepant from their neighbours | bound the response noise **without a fitted constant** |

I make **no contamination claim** and I do not restate 1186's null, leakage bound,
or any of its numbers. Verified in source: `m96-election-margin.rs` imports
`FOCUS_NOISE_SD` from `merge`, and its noise-model use is confined to *synthesising*
the plant (`noise.green_luma_sigma`), never to normalising `sigma_R_hat`.

**(b) M93 §2.3 predicts a hazard that my TABLE 7 avoids, and I can now show the
hazard is real.** M93 records that on a *synthetic* stack — one base frame blurred
by a different sigma per frame — the fourth-difference statistic is inflated
(`z²` ≈ 1.69 against an analytic 1.0), because the base frame's own noise is
attenuated by a different factor in each frame. **My synthetic plants show exactly
that inflation**: `sigma_R_hat / FOCUS_NOISE_SD` reads **10.7452** (δ=1.0) and
**6.5977** (δ=0.02), versus **1.047–1.973** on all seven real stacks. TABLE 7 is
**real stacks only** and always was; M93 supplies the independent explanation for
why that was the right restriction. Two milestones reached the same conclusion
about synthetic frame-axis statistics from opposite directions.

**(c) M93's `P4` makes a DERIVED claim that my B4 measures directly — and my data
qualifies it.** `P4` states that *"low-detail pixels are elected near-arbitrarily"*
while high-detail pixels have an unambiguous peak. That is my registered B4
hypothesis, asserted as DERIVED by a sibling. **Measured (TABLE 6), it is
directionally right but not monotone and not universal:** the spread across detail
deciles is large on deep stacks (**20.85×** `coffee-bean`, **7.79×** `bee-3-cpl`
max/min) but the *lowest* decile is **not** the least decisive on either — the
minimum sits at decile 2, and on `109MSDCF`, `119MSDCF` and `wrapped-text-1` the
relationship **inverts** (`d9/d0` = 0.76×, 0.54×, 0.64×). So M93's `P4` should be
folded as a claim about the *high-detail* end, where both milestones agree, and
**not** as a general statement that low detail implies arbitrary election.

**(d) What I must not claim as novel.** M93's `P10` already records that a
faithfulness bar registered at exactly `100.000000%` catches a planted tie-break
inversion (21 of 8,250,880 px, 2.5 ppm). My F1/F3 pair is the **same control
design reaching the same conclusion independently** (12 of 8,241,504 px) on the
same night. I report it as corroboration of `P10`, not as a discovery; it does
not appear in my candidate facts.

---

## 1. Task 1 — the pedestal defect, fixed at the call site

Fact 1199: `Estimator::fold_inner` accumulates **black-inclusive raw DN**
(`merge.rs:770`), while `Estimator::disagreement` subtracts black at read time
(`merge.rs:877`). A gain `c` fitted on black-subtracted signal must therefore be
applied about the pedestal, not about zero:

```text
want:  (v - b) -> c*(v - b)          i.e. v -> c*v + b*(1 - c)
so:    luma_offset = black * (1 - c)      NOT 0.0
```

Fixed in `crates/strehl-cli/examples/m60-disagreement.rs` — the call site, **not**
`merge.rs`. Delivered:

- `pedestal_pivot_offset(black, gain)` — the one-line derivation above, named.
- `assert_pivot_preserves_the_pedestal()` — a runtime, two-sided assertion that a
  pixel *at* the black level maps to itself under the corrected transform and does
  **not** under the zero-pivot one. This is the regression guard: it fails if
  anyone re-introduces `0.0`.
- `--zero-pivot` — an escape hatch that reproduces the defective behaviour on
  demand, so the defect's price stays measurable without editing source.
- Three unit tests. `cargo test --example m60-disagreement`: **3 passed**.
- The misleading comment corrected. It described `pipe.luma`, **a buffer this path
  never reads**; that is what let the defect survive review.

**A defect fact 1199 did not name: the affine arm carried it too.** Fact 1199
identifies the gain arm. The affine arm at the same call site passed the same
`0.0`. Corrected, `109MSDCF`'s affine arm moves **+5.4% → +6.4%**.

**Two-sided verification against an independent instrument.** M91 measured the
same quantity with a different instrument (its C9 column). The corrected
`m60-disagreement.rs` now reproduces it:

| stack | M96 (this session) | M91 C9 |
| --- | --- | --- |
| `109MSDCF` gain | +4.4% | +4.41% |
| `109MSDCF` affine | +6.4% | +6.44% |
| (row 3) | −0.1% | −0.11% |
| (row 4) | +3.0% | +3.01% |

Raw: `out/t1-109-blackpivot.txt`, `out/t1-109-zeropivot.txt`.

**I did not re-open M60's conclusion**, per the brief. Fact 1200 established
against a pre-registered prediction that this defect is not the mechanism behind
M60's negative results. Nothing here bears on that.

---

## 2. The instrument, and the units problem I refused to inherit

The instrument is a **second implementation of the election** written against the
public `strehl-core` API. It does not edit `merge.rs`. This is fact 1205's asset
spent as intended.

**F1 — faithfulness.** Before any bar is read, the instrument re-elects every
pixel and compares to the merge's own result:

- **winner index: 100.000000%** (8,241,504 of 8,241,504)
- **winner value: 100.000000%**, f32 bit-identical

on every real stack. F2, the same check on the winner's response value, is also
exactly **100.000000%**. If either is not exactly 100%, no other number in the run
is quoted.

### 2.1 Units: I did not denominate the headline in `FOCUS_NOISE_SD`

`FOCUS_NOISE_SD` is a shipped constant that **two milestones failed to calibrate**
(M69, M81), and M69 established that the operator's response noise is **not
measurable from a focus sweep at all** — macro depth of field is one to two frames
wide, so the through-focus curve is a peak no smoothing window can follow
(`docs/captures-needed.md` §12). Discipline 590: every fitted constant in this
project has so far failed to transfer.

So the headline is denominated two ways that **need no constant at all**:

- **`q_d = m_d / (R_win − R_min)`** — the margin as a fraction of the pixel's
  *own* through-focus range. Self-normalising, per pixel, dimensionless.
- **The paired permutation test** — a win/loss count against the same pixels with
  the frame order destroyed. Constant-free by construction.

`s_d = m_d / FOCUS_NOISE_SD` is printed, labelled *"the shipped constant, reported
for reference only"*, and no verdict rests on it.

### 2.2 A constant-free noise scale — and it corroborates the shipped constant

Following M89's model (`[1,−4,6,−4,1]/6`, analytic null `E[z²]=1`, measured
0.9897), I applied the same 4th-difference estimator **along the frame axis** of
the focus response. It needs no fitted constant.

**TABLE 7** (`out/TABLE7-noise-scale.txt`):

| stack | N | `sigma_R_hat` q50, real | / const | q50 permuted | / const | perm/real |
| --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | 22 | 0.018743 | **1.2320** | 0.077866 | 5.1181 | 4.15 |
| 119MSDCF | 33 | 0.017847 | **1.1731** | 0.164994 | 10.8449 | 9.24 |
| 112MSDCF | 79 | 0.017427 | **1.1455** | 0.364250 | 23.9418 | 20.90 |
| foam | 100 | 0.030010 | **1.9726** | 1.731181 | 113.7887 | 57.69 |
| coffee-bean | 105 | 0.028516 | **1.8743** | 1.829728 | 120.2661 | 64.16 |
| wrapped-text-1 | 130 | 0.024210 | **1.5913** | 0.703622 | 46.2483 | 29.06 |
| bee-3-cpl | 299 | 0.015930 | **1.0471** | 0.568089 | 37.3399 | 35.66 |

`FOCUS_NOISE_SD = 0.015214`.

Two readings, and the weaker one is the honest one:

- **The permuted column is this estimator's own power control.** Destroy the frame
  ordering and the same estimator on the same pixels reports **4.15× to 64.16×**
  larger. It can say otherwise, loudly. Discipline 594 satisfied for the
  instrument itself.
- **`sigma_R_hat` is an upper bound on the response noise**, not an estimate of
  it: a 4th difference along the frame axis absorbs genuine through-focus
  *curvature* as well as noise. So this shows `FOCUS_NOISE_SD` is **not more than
  about 2× too small** on any corpus stack, and on `bee-3-cpl` the bound is tight
  enough (1.047×) that the constant sits within 5% of the tightest available upper
  bound on the truth. **It does not rule out the constant being too large.** It is
  the first corroboration of that constant from an estimator with an analytic
  null, and it is one-sided.

---

## 3. Measurements

Scope for every bar: the **7,985,600 interior pixels** of 8,241,504 (96.89%);
22 px border excluded so the 17×17 regulariser and the neighbourhood statistics
are fully supported. F1/F2 run on the full plane.

Definitions as implemented:

```text
rho(t) = max(|hi(t) - k_win|, |k_win - lo(t)|)     furthest competitive frame
gap(t) = (hi - lo + 1) - n(t)                      competitive set DISCONNECTED if > 0
m_d    = R_win - max{ R_k : |k - k_win| >= d }     margin at frame-distance d
q_d    = m_d / (R_win - R_min)                     fraction of own through-focus range
t      = c * sqrt(2) * FOCUS_NOISE_SD              c = 4.0 is DEFAULT_GATE
```

### 3.1 TABLE 1 — the pre-registered bars, real vs its own paired placebo

| stack | N | B1 `rho`/N | B2 gap>0 % | B3 `q_8` | B3 perm | ratio | B5 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | 22 | 0.13636 | 13.001 | **0.76543** | 0.12742 | **6.01×** | 0.00164 |
| 119MSDCF | 33 | 0.09091 | 7.600 | **0.61870** | 0.04402 | **14.05×** | 0.00038 |
| 112MSDCF | 79 | 0.02532 | 17.162 | **0.49985** | 0.02997 | **16.68×** | 0.00439 |
| foam | 100 | 0.00000 | 1.552 | **0.63226** | 0.02753 | **22.97×** | 0.00096 |
| coffee-bean | 105 | 0.00000 | 23.289 | **0.73573** | 0.03907 | **18.83×** | 0.00520 |
| wrapped-text-1 | 130 | 0.00000 | 0.424 | **0.81315** | 0.07053 | **11.53×** | 0.00004 |
| bee-3-cpl | 299 | 0.00334 | 25.247 | **0.28985** | 0.02205 | **13.15×** | 0.00541 |

**B3 is DECISIVE on all seven.** The winner beats every frame 8 or more away by
29% to 81% of the pixel's own through-focus range.

### 3.2 TABLE 3 — the paired test, the constant-free headline

Same pixels, same response multiset, **only the frame ordering destroyed**.

| stack | `d=1` w/(w+l) | ties | `d=8` w/(w+l) | `d=8` ties |
| --- | --- | --- | --- | --- |
| 109MSDCF | 0.000% | **100.00%** | **99.496%** | 0.20% |
| 119MSDCF | 0.000% | **100.00%** | **99.773%** | 0.18% |
| 112MSDCF | 0.000% | **100.00%** | **98.591%** | 6.35% |
| foam | 0.000% | **100.00%** | **99.914%** | 0.62% |
| coffee-bean | 0.000% | **100.00%** | **96.226%** | 20.64% |
| wrapped-text-1 | 0.000% | **100.00%** | **99.952%** | 0.62% |
| bee-3-cpl | 0.000% | **100.00%** | **98.833%** | 18.26% |

The `d=1` column is the registered invariant, and it holds **per pixel, exactly**:
the brief's literal winner-minus-runner-up margin is bit-identical under
permutation on every one of 7,985,600 pixels of every stack. That is §4's B-bar
retirement, measured rather than argued.

**The null band.** Measured, not assumed, over 5 permutation seeds on `109MSDCF`
at `d=8`: **69.368 / 22.304 / 27.251 / 81.134 / 81.086%** → **[22.304%, 81.134%]**.
The real arm over 4 placebo seeds: **99.387 / 99.709 / 99.669 / 99.419%**. Cleanly
separated, with no overlap and a wide margin.

### 3.3 TABLE 2 — where the margin *is* below the noise

`frac(m_d < 1 σ_F)`, real over permuted, at `d=8`:

| stack | real | permuted |
| --- | --- | --- |
| 109MSDCF | **0.25%** | 17.14% |
| 119MSDCF | **0.15%** | 29.76% |
| 112MSDCF | **8.45%** | 34.01% |
| foam | **0.12%** | 5.52% |
| coffee-bean | **25.46%** | 29.85% |
| wrapped-text-1 | **0.06%** | 3.26% |
| bee-3-cpl | **21.11%** | 37.23% |

This is the brief's requested headline — *fraction of pixels where the margin is
below the noise* — and it is **0.06% to 25.46%**, well under half on every stack,
and below its own permutation placebo on every stack. It rests on
`FOCUS_NOISE_SD`, so per the brief's caution it is reported **as a ratio against
the placebo**, not as a standalone number.

**And the near-ties are not a defect — they are what the gate is for.** On
`bee-3-cpl` at `d=1`, `frac(m_d < gate tol)` is **64.292%**: two thirds of pixels
have an immediate neighbour within the gate. That is the gate correctly
identifying frames worth averaging, and fact 1196 already measured what averaging
them costs — facet sharpness moved **0.985×** across a 61× change in frames
averaged. The near-ties are handled, not arbitrary. Meanwhile at that same median
pixel the winner already beats its immediate neighbour by **2.3771 σ_F**.

### 3.4 TABLE 4 — the confusion radius, and a real finding

At the shipped gate `c=4`:

| stack | N | n_eff | `rho` med | `rho` p90 | `rho` p99 | gap>0 |
| --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | 22 | 4.969 | 3 | 4 | 12 | 13.00% |
| 119MSDCF | 33 | 4.716 | 3 | 4 | 8 | 7.60% |
| 112MSDCF | 79 | 11.670 | 2 | 43 | 75 | 17.16% |
| foam | 100 | 1.359 | 0 | 1 | 5 | 1.55% |
| coffee-bean | 105 | 31.002 | 0 | 89 | 104 | 23.29% |
| wrapped-text-1 | 130 | 1.231 | 0 | 1 | 2 | 0.42% |
| bee-3-cpl | 299 | 58.919 | 1 | **243** | **295** | **25.25%** |

**On `bee-3-cpl`, 25.247% of pixels have a *disconnected* competitive set** — the
gate admits frames at two or more separated depths, mean gap **29.12 frames**,
`rho` p90 = 243 of 299. The median pixel is tight (`rho` = 1); the tail is
enormous. These are not noise: in the `margin-q8` render they are **thin
contours** lying exactly along depth and occlusion boundaries, where two genuinely
different surfaces are in focus at two genuinely different frames. That is a
correct reading of a bimodal scene, not an undetermined election — but it is
precisely the population where averaging across the gate mixes two depths.

### 3.5 TABLE 5 — the regularised-Tenengrad speckle row the corpus lacked

| stack | real | N1 i.i.d. | N2 uniform | real/iid |
| --- | --- | --- | --- | --- |
| 109MSDCF | 0.0214% | 13.0616% | 66.2011% | 0.00164 |
| 119MSDCF | 0.0243% | 64.5782% | 73.7562% | 0.00038 |
| 112MSDCF | 0.3111% | 70.8930% | 82.5680% | 0.00439 |
| foam | 0.0487% | 50.9507% | 83.9008% | 0.00096 |
| coffee-bean | 0.4162% | 80.0804% | 84.1283% | 0.00520 |
| wrapped-text-1 | 0.0033% | 81.5875% | 85.0282% | 0.00004 |
| bee-3-cpl | 0.4639% | 85.6939% | 87.2011% | 0.00541 |

This fills the hole `Gate::admits`' doc-comment names, and it is **not**
comparable to M2 §3.1's 34.381% — that was the retired ring-difference operator.
**Report it as description, not as evidence about the election**, for the reason
in §4/B5.

---

## 4. The pre-registered bars, and how each landed

Scored against `PREREGISTRATION.md` §2. I am reporting the failures first.

**B4 — NOT SUPPORTED AS REGISTERED.** I predicted smooth regions would be at least
**3×** worse than detailed ones (`d9/d0 ≥ 3×`). That holds on **only 2 of 7**
stacks. TABLE 6, decile vectors of median `q_8`, low detail → high detail:

```text
109MSDCF        0.7450 0.7907 0.7992 0.7993 0.7974 0.7970 0.7915 0.7290 0.6274 0.5654   d9/d0 0.76x
119MSDCF        0.6281 0.6820 0.6762 0.6765 0.6730 0.6590 0.6258 0.5213 0.4263 0.3399   d9/d0 0.54x
112MSDCF        0.1159 0.4507 0.5428 0.5493 0.5475 0.5441 0.5343 0.5234 0.5065 0.4951   d9/d0 4.27x
foam            0.5358 0.5876 0.6112 0.6197 0.6288 0.6403 0.6458 0.6587 0.6650 0.6741   d9/d0 1.26x
coffee-bean     0.2078 0.0696 0.0389 0.3149 0.8088 0.8008 0.7914 0.8112 0.7974 0.7286   max/min 20.85x
wrapped-text-1  0.9330 0.9258 0.9151 0.9004 0.8554 0.7387 0.6334 0.6206 0.6248 0.5928   d9/d0 0.64x
bee-3-cpl       0.3522 0.0629 0.0569 0.1124 0.3938 0.4066 0.3982 0.4145 0.4087 0.4431   max/min 7.79x
```

Two separate problems, both mine:

- **`d9/d0` is a bad summary** because decile 0 is non-monotone: on `coffee-bean`
  and `bee-3-cpl` the minimum is at decile **2**, not 0. On `max/min` the effect is
  large and in the predicted direction — **20.85×** and **7.79×**. I registered
  the wrong summary statistic for a real effect.
- **The detail axis itself is weak on deep stacks.** It is the local standard
  deviation of **one middle frame's** luma. In a 299-frame stack that frame is out
  of focus almost everywhere, so the axis partly measures "how defocused is the
  middle frame here", not "how detailed is the scene here". I do not know why
  decile 0 rises again and I am **not** going to explain it post hoc; it is a
  limitation, stated.

**B5 — RETIRED, UNDER-POWERED.** See §5.2. Its numbers are in TABLE 5 as
description only.

**B2 — NEARLY ARBITRARY on `bee-3-cpl` (25.247%).** The bar reads "arbitrary" but
§3.4 shows the mechanism is a bimodal depth structure, not indecision. **I am not
reinterpreting a failed bar into a pass**: B2 fails as registered on that stack,
and my reading of why is a hypothesis supported by the render, not a measurement.

**B1 — DECISIVE on 5, INTERMEDIATE on `119MSDCF` and `109MSDCF`.** Both are short
stacks (33 and 22 frames) where a `rho` of 3 is a larger fraction of N.

**B3 — DECISIVE on all 7.** This is the bar the verdict rests on, and it is the
one denominated in a constant-free unit.

**Rule 30 pre-registered prediction.** I predicted before measuring that if
softness were caused by an arbitrary election, `q_8` would sit below 0.10 on the
owner's deep stacks. It is **0.28985** on `bee-3-cpl` — the prediction's
falsifying branch. Recorded as registered.

---

## 5. Controls, including every one I made fail

### 5.1 F3 — the falsifier that must fail, and did

`--invert-tiebreak` inverts the election's tie-break rule. F1 must then break.

```text
PLANT           : tie-break inverted (F3)
  winner index  : 99.999854%  (8241492 of 8241504 pixels)
  winner value  : 100.000000%  (f32 bit-identical)
  F1            : FAIL
```

**12 pixels** of 8,241,504. F1 is a bar at *exactly* 100.000000% precisely so that
a 12-pixel disagreement is a failure and not a rounding note.

**Deviation from the registered form, disclosed.** F3 was registered as a source
mutation restored from `$env:TEMP`. I implemented it as a **runtime flag**
instead. Strictly safer — no file is mutated in a tree with live sibling agents —
but the consequence is that the plant now lives in the shipped instrument. A
reader should know `--invert-tiebreak` exists and is not a research knob.

### 5.2 The δ sweep — the power curve that retired B5

Discipline 594: a null is a claim only if the instrument could have said
otherwise, **and you show it saying otherwise.** The plant is a synthetic
band-limited texture (white noise smoothed 3×3, `PLANT_MEAN_DN=2000`,
`PLANT_AMP_DN=700`), 60 frames, 512², sharp at **every** pixel by construction;
blur radius grows `δ` px per frame off each pixel's own in-focus frame. Lowering
`δ` flattens the through-focus peak continuously.

| δ | B1 `rho`/N | B2 gap% | B3 `q_8` | B5 | speckle % | verdicts B1/B2/B3/B5 |
| --- | --- | --- | --- | --- | --- | --- |
| 1.0 | 0.00000 | 0.003 | 0.92996 | 0.00000 | 0.0000 | DEC / DEC / DEC / DEC |
| 0.5 | 0.00000 | 0.000 | 0.84234 | 0.00000 | 0.0000 | DEC / DEC / DEC / DEC |
| 0.25 | 0.00000 | 0.000 | 0.68976 | 0.00000 | 0.0000 | DEC / DEC / DEC / DEC |
| 0.1 | 0.05000 | 19.996 | 0.43722 | 0.01626 | 1.2933 | DEC / INT / DEC / DEC |
| 0.05 | 0.15000 | 61.107 | 0.00191 | 0.06390 | 5.0669 | INT / **NEAR** / **NEAR** / DEC |
| 0.02 | 0.41667 | 89.764 | 0.00130 | 0.09729 | 7.6651 | **NEAR** / **NEAR** / **NEAR** / **DEC** |

- **Discipline 595 (power control) discharged.** B1, B2 and B3 walk monotonically
  DECISIVE → NEARLY ARBITRARY. The instrument can say the opposite of my headline,
  and here it is doing so.
- **B5 never breaks.** At δ=0.02, where every other bar reads NEARLY ARBITRARY,
  B5 = 0.09729 and still passes its ≤0.20 bar. The mechanism is the 17×17
  regulariser: it correlates neighbouring pixels' response curves, so neighbours
  elect the same index **even when that index is arbitrary**. **Spatial coherence
  of the elected-index map is manufactured by the regulariser and is not evidence
  about the election.** This qualifies M2 §3.1.

**This is a *different* failure mode from M93's, and the two together are worth
more than either.** M93 `D-b` retired speckle **as a bar on an intervention**: it
scores *change* rather than *correctness*, so it fails in the wrong direction when
a gate substitutes a better winner (+201% to +429%). M96 retires it **as a bar on
the un-intervened election**: it cannot detect an arbitrary election at all,
because the regulariser manufactures the coherence it measures. M93 shows the
statistic cannot grade a *fix*; M96 shows it cannot grade a *diagnosis*. Note the
two used different thresholds — M93's is `|k − median3×3| > 5`, mine is `> 2`
(M2 §3.1's definition) — and it failed at both.

At δ=1.0 the positive control passes cleanly: **B1 = 0.00000, B2 = 0.00274%,
B3 = 0.92996, B5 = 0.00000, F1 PASS**.

### 5.3 The positive control I had to throw away

My **first** positive control planted the ramp on a real `wrapped-text` crop. It
read **B1/B2 = NEARLY ARBITRARY** and **B4 inverted (0.155)**. I initially took
this as an instrument failure. It was not: a text crop is mostly featureless
paper, where the election genuinely **is** undetermined. The metric was right and
the control was contaminated. That is why the plant base is synthetic and sharp
everywhere — reported because "I built a positive control that failed and the
reason was the control" is exactly the kind of thing that gets quietly dropped.

### 5.4 The paired null was biased, and the three-step diagnosis

The paired placebo's null should be 50%. It read **69.368%**. Three steps:

1. **Is the statistic biased?** An independent numpy simulation of the same
   win/loss rule on synthetic exchangeable data: **50.1%–50.3%**. Unbiased.
   (`src/paired_bias_sim.py`, `out/c9-paired-bias-sim.txt`.)
2. **Are the shuffles uniform?** A Python replication of the instrument's
   SplitMix64 + Fisher-Yates streams: **both uniform**.
   (`src/shuffle_check.py`, `out/c10-shuffle-check.txt`.)
3. **Diagnosis.** **One global permutation is a single draw shared by all
   7,985,600 pixels.** The null therefore has *permutation-level* variance, not
   pixel-level variance — `n` is 1, not 8 M. Over 5 seeds it spans
   **[22.304%, 81.134%]**, which is exactly the spread a single draw should have.
   The real arm at 99.387%–99.709% sits far outside it.

**A genuine defect found en route:** both arms originally shared an RNG seed,
which made arm B a deterministic function of arm A (σ² of arm A). Fixed; the
5-seed scan above is on the fixed code.

**An "arbitrary real" control** on the same axis: forcing the real arm to elect
arbitrarily gives **0.491 / 0.393 / 0.459 / 1.064%** against a permuted opponent,
and **19.4%–71.6%** in the null configuration. Both bracket the null and neither
approaches the real arm. Discipline 596: same scale, so a mis-wiring produces a
recognisable number.

### 5.5 Nulls N1, N2, N4

- **N1 (i.i.d. index map)** and **N2 (uniform index map)** — TABLE 5, the spatial
  nulls. Descriptive only, per B5's retirement.
- **N4** — registered invariants under permutation held **bit-identically** at
  `d=0` and `d=1`. This is the control that discovered the brief's metric is
  invariant.

### 5.6 Reproducibility after the quality-gate edits

The instrument was edited after the results were produced (clippy fixes, a test
module, `rustfmt`). I re-ran `109MSDCF` end to end and diffed against the
pre-edit log: **bit-identical** on B1, B2, B3, B5 and all six rows of the paired
table. (`out/r4-109MSDCF.txt` vs `out/r5-109MSDCF-repro.txt`.)

---

## 6. Two self-corrections

**6.1 — N3 is not a valid null for B5, and I registered it as one.** A *global*
permutation relabels every pixel identically, so it preserves **any** spatial
statistic of the index map by construction. It cannot test spatial coherence. I
registered it as B5's null and I was wrong. The δ sweep (§5.2) is the valid power
test, and B5 fails it.

**6.2 — TABLE 2's permuted column is not "flat by construction", and I claimed it
was.** Excluding more frames at larger `d` shrinks the rival set and therefore
grows `m_d` combinatorially — for **any** ordering, focus-driven or not. So the
permuted column drifts, and it should. That drift is exactly why a same-scale
placebo is required (discipline 596). What focus explains is the real column's
**excess** drop over the permuted one, not the drop itself.

---

## 7. Renders

`C:\dev\strehl-out\M96-election-margin\<stack>\` for **all seven** stacks —
`elected-index`, `elected-index-null-iid`, `confusion-radius`, `margin-q8`, each
as a full plane and a 1024² 1:1 crop (8 TIFFs), plus `summary.json`. PNG previews
for five of the seven are in `preview/`, named `<stack>--<map>.png`.

**On the owner's own 299-frame `bee-3-cpl`, which the brief asked for
specifically:** the elected-index map shows **coherent depth structure across the
subject** — smooth index gradients that track the bee's surface. Salt-and-pepper
is confined to the featureless background, where there is nothing to focus on and
nothing is lost. This is the visual counterpart of TABLE 1 and it does not look
like an arbitrary election.

The `margin-q8` map shows **thin blue contours lying exactly along depth and
occlusion boundaries** — the 25.247% disconnected-competitive-set population of
§3.4, localised. **Caveat, per §5.2: the map's coherence is partly manufactured by
the regulariser.** Read it as *where* the margin is small, not as proof that the
election is good.

---

## 8. Scope, and what would falsify this

**Scope.**

- Seven corpus stacks, 22–299 frames; interior 7,985,600 px of 8,241,504 each.
- The **shipped regularised Tenengrad** operator only. Says nothing about any
  other focus measure.
- **Frames as given**: unaligned, unnormalised. Fact 1177's 232.7 px and 299.2 px
  drifts are **present** in every stack measured here.
- The election **as it is**, not as it would be after alignment lands.

**What would falsify it.**

1. A stack where `q_8` sits below 0.10 with a paired win rate inside
   [22.304%, 81.134%]. That is a genuinely undetermined election and I did not
   find one.
2. Showing `q_d` is not monotone-decreasing in the true sharpness of the
   underlying scene — that would break the metric's meaning, not just its value.
3. A demonstration that F1 at 100.000000% is achievable by an instrument that is
   *not* reproducing the election (e.g. through a shared cached buffer). I believe
   this is excluded because the surrogate recomputes from `Frame` data, but I have
   not proved the exclusion.
4. **Most likely to bite:** after alignment lands, re-running this shows a
   *materially different* margin distribution. Everything here is measured on
   misregistered stacks. If registration changes the election's decisiveness, the
   right reading of this milestone is "the election was decisive **given** the
   frames it was handed", which is weaker than it sounds.

**What this does not say.** It does not say the output is sharp. It says the
*choice* of frame is well-determined. A confident election over a misregistered
stack still produces a soft image, and facts 1177 and 1186–1190 describe exactly
that mechanism.

**Relationship to M93, stated so neither milestone is over-read.** M96 measures
the election **as it currently ships** — ungated. M93 changes which frames may
compete. M96 does **not** measure M93's gate, does not validate it, and its
numbers will change once the gate ships; `P11` is a statement about the
precondition, not about the outcome. Conversely M93's benefit numbers are not
evidence about the margin. **Re-running M96's instrument after M93's gate lands is
the cheap, obvious follow-up** and I recommend it: if the margin *widens* under the
gate, that is direct confirmation the gate is removing frames that were winning
spuriously.

---

## 9. Requests for the orchestrator

**9.1 A capture request**, for `docs/captures-needed.md` (the orchestrator's
file — I did not edit it):

> **Frame-axis noise calibration without a focus sweep.** §12 records that the
> focus operator's response noise cannot be measured from a focus sweep, because
> macro depth of field is 1–2 frames wide. M96 §2.2 offers a way around it: a
> **static repeat burst** — 40+ frames, tripod locked, focus untouched, on a
> textured subject at the working aperture. With focus constant, the entire
> frame-axis variation of the focus response is noise, so `sigma_R_hat` becomes an
> unbiased *estimate* rather than the upper bound M96 could only establish
> (1.047×–1.973× of `FOCUS_NOISE_SD`). That would be the first direct calibration
> of the constant M69 and M81 both failed to obtain.

**9.2 Patches to non-owned files:** none. Nothing outside my owned set needed to
change. No `lib.rs` or `main.rs` registration was required — `m96-election-margin`
is an example, which cargo discovers without a registration point (verified: no
`[[example]]` stanza in `crates/strehl-cli/Cargo.toml`).

**9.3 Two premises in the deconfliction brief are stale, measured just now:**

- **`C:\dev\strehl-head` does not exist.** `Test-Path` returns false; there is no
  such worktree. I did not need it, but nobody else should be told to read from it.
- **The workspace compiles.** `cargo check -p strehl-cli --bins` returns **rc=0**,
  and `crates/strehl-cli/src/align_cmd.rs` is **tracked**, not untracked. M86 must
  have landed since the brief was written. (Note `cargo check -p strehl-cli --lib`
  fails with *"no library targets found"* — `strehl-cli` is a binary-only crate, so
  that is the expected error and not a build break.)

---

## 10. Candidate facts

**P1** — *claim:* The winner-minus-runner-up margin is **provably uninformative**
about whether a focus election is well-determined: it is an order statistic of the
per-pixel response multiset and is therefore **bit-identical** under any
permutation of the frame axis. Measured on all **7,985,600** interior pixels of
all **7** corpus stacks: **0.000% wins, 100.00% ties** at frame-distance `d=1`.
*Significance:* the natural formulation of "how decisively did the argmax win" is
invariant to the thing it is meant to test; any future margin work must be stated
at `d ≥ 2`, and Surh et al.'s published "Winner Margin" confidence measure
(`B-algorithms-sota.md` §2.3) inherits this limitation. *Label:* MEASURED,
M96 §3.2.

**P2** — *claim:* The shipped focus election is **decisive, not arbitrary**, on
every corpus stack. Median margin at frame-distance 8, as a fraction of the
pixel's own through-focus range, is **0.28985 to 0.81315**, versus **0.02205 to
0.12742** for the same pixels with the frame order destroyed — a ratio of
**6.01× to 22.97×**. In a paired permutation test the real election wins at
**96.226% to 99.952%** against a measured null band of **[22.304%, 81.134%]**
(5 seeds, `109MSDCF`, `d=8`). *Significance:* closes the last unexamined link in
the softness investigation. The output is **not** a mosaic of near-random picks;
softness cannot be explained by an undetermined argmax, and gate tuning was never
the lever. Corroborates fact 1196 from the selection side as 1196 did from the
combination side. *Label:* MEASURED, M96 §3.1, §3.2.

**P3** — *claim:* Spatial coherence of the elected-index map is **manufactured by
the 17×17 regulariser** and therefore cannot detect an arbitrary election. In a
planted stack at δ=0.02 where B1 (0.41667), B2 (89.764%) and B3 (0.00130) all
read NEARLY ARBITRARY, the speckle bar still read **0.09729**, passing its ≤0.20
DECISIVE threshold. *Significance:* this is a **second, independent** failure mode
of the same statistic M93 `D-b` retired. M93 showed speckle cannot grade an
*intervention* (it scores change, not correctness); M96 shows it cannot grade the
*un-intervened election* either (the regulariser supplies the coherence). It
failed at both thresholds tried — M93's `> 5` frames and M2 §3.1's `> 2`. Any
milestone reading index agreement or index speckle as evidence about election
quality is reading the smoothing kernel. *Label:* MEASURED, M96 §5.2.

**P4** — *claim:* On the owner's 299-frame `bee-3-cpl`, **25.247%** of interior
pixels have a **disconnected** competitive set at the shipped gate (`c=4`): the
gate admits frames at two or more separated depths, mean gap **29.12 frames**,
confusion radius p90 = **243** of 299 while the median is **1**. These pixels lie
on depth and occlusion boundaries. *Significance:* a quarter of the deep stack's
pixels are averaged across two genuinely different depths by a gate that has no
representation of disconnectedness. This is a **new, specific, localised**
softness mechanism, distinct from drift (fact 1177) and motion (facts 1186–1190),
and it is testable: a connectivity constraint on the admitted set would change
only these pixels. *Label:* MEASURED, M96 §3.4.

**P5** — *claim:* `FOCUS_NOISE_SD = 0.015214` is corroborated to within a factor
of two by an estimator with an **analytic null and no fitted constant**. M89's
`[1,−4,6,−4,1]/6` applied along the frame axis of the focus response gives a
median scale of **1.047× to 1.973×** the shipped constant on all seven stacks;
the same estimator on the same pixels with the frame ordering destroyed reports
**4.15× to 64.16×** larger, which is its power control. The estimate is an
**upper bound** on the response noise, since it absorbs genuine through-focus
curvature, so it bounds the constant from **one side only**. *Significance:* the
first corroboration of a constant that M69 and M81 both failed to calibrate, from
a method M69's "not measurable from a focus sweep" finding does not block.
Discipline 590 says every fitted constant here has failed to transfer; this one
survives a first independent check. *Label:* MEASURED, M96 §2.2.

**P6** — *claim:* The corpus's first **regularised-Tenengrad** elected-index
speckle row: real **0.0033%–0.4639%**, i.i.d. null **13.0616%–85.6939%**, uniform
null **66.2011%–87.2011%**, over 7 stacks. *Significance:* fills the hole
`merge.rs`'s own `Gate::admits` doc-comment names ("No corpus row publishes a
regularised Tenengrad speckle"), and supersedes M2 §3.1's 34.381%, which was
measured on the **retired** ring-difference operator and is not comparable.
Publish it as description, not as evidence about the election, per `P3`.
*Label:* MEASURED, M96 §3.5.

**P7** — *claim:* Fact 1199's pedestal defect also affected the **affine** arm of
`m60-disagreement.rs`, which fact 1199 did not name. The correct pivot is
`luma_offset = black*(1−c)` in both arms; correcting the affine arm moves
`109MSDCF` from **+5.4% to +6.4%**. The fix is at the call site and
`merge.rs` was not modified. *Significance:* completes fact 1199, which as folded
under-states the defect's extent by one arm. *Label:* MEASURED, M96 §1.

**P8** — *claim:* `m60-disagreement.rs`, pedestal-corrected, reproduces M91's
independently-measured C9 column from a **different instrument**: +4.4%/+6.4%/
−0.1%/+3.0% against M91's +4.41%/+6.44%/−0.11%/+3.01%. *Significance:* a
two-sided cross-instrument agreement on a number that a live defect had been
corrupting; raises confidence in both M91 §2.3 and the corrected call site.
*Label:* MEASURED, M96 §1.

**P9** — *claim:* A single global frame permutation is **not** a pixel-level null:
it is one draw shared by all 7,985,600 pixels, so its win-rate null has
permutation-level variance and spans **[22.304%, 81.134%]** over 5 seeds rather
than concentrating at 50%. An independent simulation confirmed the statistic
itself is unbiased (**50.1%–50.3%**) and both shuffle streams uniform.
*Significance:* a permutation placebo over a shared draw must have its null band
**measured over seeds**, never assumed at 50%. A milestone that ran one seed and
compared to 50% would have reported a 19-point spurious effect. *Label:* MEASURED,
M96 §5.4.

**P10** — *claim:* A positive control planted on a **real** image crop can fail
for a reason that is not an instrument fault. Planting a synthetic focus ramp on a
`wrapped-text` crop produced NEARLY ARBITRARY on B1/B2 and an inverted B4 (0.155),
because the crop is mostly featureless paper where the election genuinely is
undetermined. Replanting on a synthetic band-limited texture, sharp at every pixel
by construction, passed all bars (B1 0.00000, B2 0.00274%, B3 0.92996, B5 0.00000).
*Significance:* discipline 594's "show it saying otherwise" needs a plant base
whose ground truth is **known at every pixel**, which a real photograph is not.
*Label:* MEASURED, M96 §5.3.

**P11** — *claim:* The focus election **is** well-determined enough for
frame-rejection to be the right shape of fix. The branch "the election is
substantially arbitrary, so removing contaminated frames cannot make it decisive"
is falsified on all 7 stacks (`P2`). A decisive argmax means a contaminated frame
wins by being pushed *above a genuine peak*, not by a flat response surface, so
rejecting it returns the pixel to a real competition. *Significance:* this is the
**precondition** M93's election-side gate needs, measured independently of it and
on the un-gated pipeline. It is not a benefit estimate — M93 measured the benefit
(−25.25% `lead-1-cpl`, −24.46% `foam`) — it is the evidence that the gate operates
on signal rather than on noise. *Label:* DERIVED from M96 §3.1–§3.2, M96 §1.

**P12** — *claim:* M93's `P4` — *"low-detail pixels are elected
near-arbitrarily"* — holds at the **high-detail** end but **not** as a general
monotone rule. Measured across detail deciles (TABLE 6): spread is large on deep
stacks (**20.85×** `coffee-bean`, **7.79×** `bee-3-cpl` max/min), but the *lowest*
decile is not the least decisive on either — the minimum sits at decile 2 — and on
`109MSDCF`, `119MSDCF` and `wrapped-text-1` the relationship **inverts**
(`d9/d0` = 0.76×, 0.54×, 0.64×). *Significance:* qualifies a sibling milestone's
DERIVED claim with direct measurement before it folds. Fold `P4` as a statement
about high-detail pixels, where both milestones agree; do **not** fold it as "low
detail implies arbitrary election". *Label:* MEASURED, M96 §4, §0.1(c).

**P13** — *claim:* A frame-axis fourth-difference statistic is **inflated on
synthetic through-focus stacks** built by blurring one base frame, because the
base frame's own noise is attenuated differently in each frame. Measured on M96's
plants: `sigma_R_hat / FOCUS_NOISE_SD` = **10.7452** (δ=1.0) and **6.5977**
(δ=0.02), against **1.047–1.973** on all seven real stacks. *Significance:*
independently reproduces M93 §2.3's `z²` ≈ 1.69 artefact on a **different signal**
(focus response, unnormalised) and from the opposite direction, confirming it is a
property of synthesis-by-blur rather than of either statistic. Any frame-axis
noise estimate calibrated on a blur-synthesised stack is biased high by 4–10×.
*Label:* MEASURED, M96 §0.1(b).

---

## 11. Verification

| Check | Result |
| --- | --- |
| `cargo test --example m96-election-margin` | **5 passed** |
| `cargo test --example m60-disagreement` | **3 passed** |
| `cargo clippy --example m96-election-margin -- -D warnings` | **rc=0** |
| `cargo clippy --example m60-disagreement -- -D warnings` | **rc=0** |
| `cargo fmt --check` on both owned files | clean |
| F1 faithfulness, all 7 real stacks | **100.000000%**, index and value |
| F1 under F3 plant | **FAIL**, 99.999854% |
| Post-edit reproduction of `109MSDCF` | bit-identical |
| `python scripts/corpus_lint.py` | exit 0 |
| Post-rename rebuild of `m96-election-margin` | tests/clippy/fmt all green |
| `cargo check -p strehl-cli --bins` (workspace state) | **rc=0** — it compiles |

`cargo clippy --all-targets -p strehl-cli` is red on `m86-align.rs` (M86, in
flight) and `m89-robust.rs` — both other milestones' files. Not mine, not touched.
Clippy was therefore scoped to the two examples I own.

**Renumber verification.** After `git mv` and the source rewrite, zero `M94`/`m94`
strings remain in any tracked source file (`.rs`, `.md`, `.py`) except the
docstring of `renumber.py`, which documents the rename. The raw logs under `out/`
retain the original label deliberately (see the header note). The renumber script
is idempotent: re-running it reports `0 replaced` on every target.
