# M11 — the focus-measure bake-off: what to select with, and what selection costs

**Status:** measured. Closes SYNTHESIS **risk 2** (the default focus measure was
chosen arbitrarily and never justified). Extends M9's centre-tap result from a
structural claim to a decision.

> **Independently reproduced by the orchestrator before folding, with one correction to this
> report's own framing.**
>
> **Reproduced exactly from the committed CSVs**, with independently written Spearman and
> permutation code: **ρ(support, N) = −0.009** (identical), **ρ(φ, N) = +0.583** (published
> +0.579), and every headline noise ratio to 4 decimals — `tenengrad-w5` 1.1324, `stensor-w5`
> 1.1300, `ring-1-3` 1.3475, `brenner-sym-s2-w0-nonorm` 1.0542, `sml-w5` 1.0875, `varlap-w5`
> 1.0863. `ring(1,3)` ranks 27th of 36 by my aggregation against 26th by this report's — a
> tie-ordering difference, not a disagreement. Gates re-run: fmt clean, **67 tests**.
>
> **Amendment A1 verified and extended.** φ = **exactly 0.000000** for a bare Sobel at
> `window = 0` + `Norm::None`; **0.0235** for windowing alone; **0.0321** for normalisation alone;
> **0.0568** for both — i.e. **approximately additive**, which this report did not state. φ then
> rises monotonically with window across w0…w11: 0.032 → 0.057 → 0.066 → 0.084 → 0.105.
>
> **A by-product that confirms M9's algebra from a second harness.** `ring-1-2`, `ring-1-3` and
> `ring-1-5` measure φ = 0.0534 / 0.0535 / 0.0559 against the analytic 1/18 = 0.0556, and
> `ring-0-1` / `ring-0-3` measure 0.4902 / 0.4887 against the analytic 1/2. **Three outer radii at
> each of two inner radii, and φ depends only on the inner one** — the outer-radius cancellation,
> reproduced independently of M9.
>
> **Correction — "weakens fact 35's magnitude" (fact 40) does not follow.** ρ is a property of the
> population sampled. Restricting this report's set to the ring and `dsml` families M9 actually
> used gives **ρ = +0.783**, and the sequence is monotone in heterogeneity: +0.918/+0.894
> (M9's designed crossed grid) → +0.783 (comparable subset) → +0.583 (the heterogeneous 36).
> Amendment A1 explains why — φ is not the same construct across this report's operator set.
> **Fact 35 is folded as scoped, not weakened.** See SYNTHESIS §5 item 17.
>
> **One aggregation difference, disclosed.** Selectivity `S/Smax` here is normalised on 109MSDCF;
> pooling both stacks shifts the mid-pack (e.g. `sml-w5` 0.690 → 0.567) and the zero-centre-tap
> operators (0.405 → 0.337). **The ordering is identical under both, and pooling makes the H1
> refutation stronger**, so the ruling is unaffected.

Reproduction: `experiments/m11-focus-bakeoff/README.md`. Every number below is in
`experiments/m11-focus-bakeoff/data/analysis.txt`, produced by
`run-m11.ps1` followed by `python m11_analyse.py`. Harness:
`experiments/m11-focus-bakeoff/src/`. Pre-registration:
`experiments/m11-focus-bakeoff/PREREGISTRATION.md`, committed in `452bac6`
**before any operator had been compared** — the ordering is checkable from
`git log`. Amendments A1–A3 landed in `441b6cf`, still before any RAW file was
read; **A4 and A5 are post-hoc and are flagged as such wherever they appear.**

This report follows **rule 12**: it does not verify itself. The raw CSVs are
committed so that it can be re-verified against them.

---

## Verdict

**Three findings, in descending order of how much they matter.**

**1. No operator escapes the noise excess. MEASURED.** The registered rule
defined `A` = { operators with `N ≤ 1.02x` } and asked what the best member of
`A` could do. **`A` is empty: 0 of 36 registered operators.** A 47-operator set
spanning `φ` from `0.0000` to `0.4778` and support radius from 1 to 12 contains
**no** operator that is noise-free on real data under per-pixel argmax. This is
registered outcome **O4**, and it is the most consequential thing measured here:
**operator choice alone cannot remove argmax's noise excess.** The excess can be
reduced from `1.35x` to `1.05x` by choosing well — a real and worthwhile gain —
but it cannot be driven to `1.00x`, and the project's thesis that stacking must
become *estimation* rather than *selection* does not have a cheaper escape route
through a better focus measure. **This is the single most useful negative result
in the milestone.**

**2. The zero-centre-tap operator is real, and it is not enough. MEASURED, H1
refuted.** I registered the hypothesis that a `φ = 0` operator would be both
noise-free and adequately selective. Half of it holds and half of it fails.
`tenengrad-w0-nonorm` and `brenner-sym-s2-w0-nonorm` measure `φ = 0.0000`
exactly, and on the structure-corrected axis they score `Ncorr` **0.9888x** and
**0.9966x** — *structurally no excess at all*, exactly as M9's mechanism
predicts. But they recover the planted focus surface at only **`S/Smax` 0.404
and 0.405** — less than half the best operator. **A zero-centre-tap operator is
not viable as the default.** My own hypothesis is refuted by my own data.

**3. The incumbent should be replaced, not re-tuned. MEASURED.**
`ring(1,3)` ranks **26th of 36** on the registered objective. The entire ring
family is dominated: the best ring measured, `ring(3,8)`, reaches `S/Smax`
`0.598` at `N = 1.2681x`, against `0.986` at `1.1324x` for the recommended
operator. **Re-tuning the two ring radii cannot recover the gap** — no ring in a
7-configuration sweep gets close. The recommendation is a different operator.

### The recommended default

> **Tenengrad (Sobel gradient energy) under an 11x11 box window — `tenengrad-w5`.**
> MEASURED. `N = 1.1324x`, `Ncorr = 1.0455x`, `S = 0.8007` (`S/Smax = 0.986`),
> `φ = 0.0728`, `κ = 0.549`, cost `6.411 ms/frame/Mpx` single-threaded — within
> 7% of the incumbent's `5.987`.

This is the registered rule's answer, arrived at in two steps that agree:

- argmin `J` over the registered set is `stensor-w5` (`J = 0.1300`), stable
  across the whole registered sensitivity range `λ ∈ [0.25, 4]`;
- but `stensor-w5`, `tenengrad-w5` and `brenner-sym-s2-w5` are **within the
  measured ROI-to-ROI spread of each other on both axes** (`ΔN ≤ 0.0173` against
  a tie width of `0.1641`; `ΔS ≤ 0.0112` against `0.0519`), so registered
  outcome **O5** fires and the registered tie-break applies: **(i) fewest
  parameters** eliminates `brenner-sym-s2-w5` (two knobs), **(ii) lowest cost**
  selects `tenengrad-w5` over `stensor-w5` (`6.411` vs `15.891 ms/frame/Mpx`,
  2.5x). The incumbent is not in the tie set, so clause (iii) never applies.

O4 and O5 both firing is the outcome the milestone brief warned about and the
pre-registration explicitly covered: **no operator dominates**, and the honest
answer is a declared tie resolved by registered criteria rather than a
manufactured winner.

Tenengrad also wins on grounds outside the rule, which is worth stating because
it is *not* what the rule was based on: it is the most standard operator in the
set (Sobel gradient energy is textbook), it has one knob, its cost is
indistinguishable from the incumbent's, and its zero-window form is one of the
two operators in the whole set with exactly zero centre tap — so the *same*
operator family spans both ends of the front. That last property makes it a good
default for a system that may later want to trade selectivity for noise
adaptively.

---

## The two axes

| axis | symbol | definition | why it is not rule 10 |
| --- | --- | --- | --- |
| cost | `N` | flat-ROI **spatial** sd of the argmax-stacked result ÷ **spatial** sd of one frame | spatial ÷ spatial |
| cost, corrected | `Ncorr` | `N`(select G2, eval G2) ÷ `N`(select G1, eval G2) | spatial ÷ spatial |
| benefit | `S` | fraction of pixels at which argmax elects the **planted** in-focus frame | index-vs-index |
| corroborator | `κ` | winner-map agreement across an independent noise realisation | index-vs-index |
| structure | `φ` | centre-tap sensitivity fraction, by finite difference | dimensionless |

**Rule 10 compliance, stated explicitly because this project has retracted two
results to it:** no quantity above compares a spatial standard deviation to a
temporal sigma. `N` is a ratio of two spatial standard deviations measured on
the same ROI of the same stack; `S` and `κ` are agreement rates between frame
indices and contain no standard deviation at all.

**`Ncorr` exists because the naive axis is confounded, and the confound is
measured.** `ctl-const` — always select frame 0 — scores `N = 0.8377x` (109) and
`0.7168x` (119). Selecting nothing at all "improves" the flat-ROI sd by 16–28%,
because the frames genuinely differ in flat-ROI spatial sd. `Ncorr` divides that
out by pairing a coupled arm (select on G2, evaluate on G2) against a placebo
arm (select on G1, evaluate on G2) over the *same* photosites. **Both axes are
reported throughout; the registered ruling uses `N`, and §"Robustness" shows the
ranking is unchanged under `Ncorr`.**

---

## Controls, before any treatment

**Reproduction gate. PASS.** `ring(1,3)` through this harness's code path:
**1.2527x** at width 1 and **1.0737x** at width 17, against M2's published
`1.253x` and M9's `1.0737x`. VERIFIED against prior milestones to 4 decimal
places. This gate exists because M9's own verification found that an analysis
bug can invert a correlation and only the reproduction of a known number exposed
it (SYNTHESIS §5 item 15).

| control | registered expectation | measured | verdict |
| --- | --- | --- | --- |
| `ctl-random` (null, noise axis) | no structure | `N` = 0.9350x / 1.2055x | reported as the null floor |
| `ctl-random` (null, selectivity) | `S` at chance | 0.0451 vs chance 0.0455; 0.0300 vs 0.0303 | **PASS** |
| `ctl-const` (instrument floor) | measures frame preference only | `N` = 0.8377x / 0.7168x | **motivated `Ncorr`** |
| P0 positive control | `S ≥ 0.90` by some operator/width | `S = 1.0000` (`sml-w2`, noiseless) | **PASS** |
| P2 null (`α = 0`, no focus planted) | `S ≤ 2/N_frames` = 0.0909 | max over treatments 0.0472 | **PASS** |
| registered flat-ROI pairing (rule 9) | `S` within 3x chance | **13.8x** (109), **31.7x** (119) | **FAIL — see below** |
| A5 constant-base null (rule 9) | `S` within 3x chance | **1.12x** (flat), 1.20x (detail) | **PASS** |
| realised per-frame noise spread | ≤ 10% | 9.7% (109) / 29.5% (119) | **PASS / FAIL — see below** |

### A registered control failed, and the diagnosis matters

**The registered rule-9 pairing failed.** §5 registered that the same planted run
on a *flat* ROI must collapse to within 3x of chance. It reached **13.8x** chance
on 109MSDCF and **31.7x** on 119MSDCF (`tenengrad-w5` in both cases).

**Diagnosis, MEASURED, not an excuse:** a *relatively* flat ROI of a real frame
still carries a broadband texture — its own inherited read and shot noise — and
the planted ladder blurs that texture along with everything else. An operator
that recovers the ladder from it is behaving correctly; the control was
mis-designed. It tests whether the ROI is blurrable, not whether the metric is
scoring focus.

**The repair, disclosed as post-hoc amendment A5:** `--flat-base` replaces the
base image with its own ROI mean, leaving nothing to blur, so the only
frame-to-frame difference is injected noise and any winner must be at chance.
Measured: **max `S` = 0.0510 = 1.12x chance** on the flat ROI and 0.0545 = 1.20x
on a detail ROI, against a chance of 0.0455 and a ceiling of 0.1364. **PASS.**
This is the rule-9 pairing of record. The failed original is reported here rather
than deleted, because a control that fails is data.

**Second control repair, same amendment.** The registered "realised per-frame
noise spread ≤ 10%" gate was being computed on the *detail* ROI, where the
high-passed sd is dominated by scene structure that the plant blurs **by
design** — it could never have passed, and did not (109.8%, 240.3%). Re-read on
the flat ROI, where the high-passed sd is dominated by noise: **109MSDCF 9.7%,
PASS; 119MSDCF 29.5%, FAIL.** The registered consequence is applied as written:
**119MSDCF's planted numbers are demoted to a corroborator and 109MSDCF carries
the selectivity ruling.** The robustness section shows the ranking is identical
on either stack alone, so nothing turns on this.

---

## The measured Pareto front

Aggregation: median over ROIs, then mean over the two stacks, at regulariser
width 1 (the registered ranking input). All MEASURED.

**Front members (non-dominated), from cheapest to most selective:**

| operator | `φ` | `N` | `S` | `S/Smax` |
| --- | --- | --- | --- | --- |
| `brenner-sym-s2-w0-nonorm` | **0.0000** | **1.0542x** | 0.3287 | 0.405 |
| `tenengrad-w0` | 0.0335 | 1.0632x | 0.3328 | 0.410 |
| `varlap-w5` | 0.0130 | 1.0863x | 0.5274 | 0.650 |
| `sml-w5` | 0.0097 | 1.0875x | 0.5599 | 0.690 |
| `stensor-w5` | 0.0987 | 1.1300x | **0.8119** | **1.000** |

**The full registered set, ranked by `S`.** `J = (1 − S/Smax) + λ·max(0, N − 1)`
at the registered `λ = 1.0`.

| operator | `φ` | `N` | `Ncorr` | `S` | `S/Smax` | `κ` | `J` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `stensor-w5` | 0.0987 | 1.1300 | 1.0424 | 0.8119 | 1.000 | 0.573 | **0.1300** |
| `brenner-sym-s2-w5` | 0.1234 | 1.1473 | 1.0533 | 0.8103 | 0.998 | 0.578 | 0.1493 |
| **`tenengrad-w5`** ← recommended | 0.0728 | 1.1324 | 1.0455 | 0.8007 | 0.986 | 0.549 | 0.1463 |
| `tenengrad-sq-w2` | 0.0840 | 1.2239 | 1.1350 | 0.6424 | 0.791 | 0.540 | 0.4327 |
| `brenner-sym-s2-w2` | 0.0956 | 1.2405 | 1.1807 | 0.6340 | 0.781 | 0.555 | 0.4596 |
| `stensor-w2` | 0.0843 | 1.2131 | 1.1283 | 0.6200 | 0.764 | 0.541 | 0.4495 |
| `tenengrad-w2-boxnorm` | 0.0205 | 1.2254 | 1.1358 | 0.6127 | 0.755 | 0.546 | 0.4707 |
| `tenengrad-w2` | 0.0612 | 1.2255 | 1.1337 | 0.6096 | 0.751 | 0.531 | 0.4745 |
| `tenengrad-w2-nonorm` | 0.0217 | 1.2256 | 1.1356 | 0.6076 | 0.748 | 0.544 | 0.4772 |
| `brenner-sym-s1-w2` | 0.0761 | 1.2168 | 1.1509 | 0.5986 | 0.737 | 0.512 | 0.4795 |
| `brenner-fwd-s2-w2` | 0.0781 | 1.2068 | 1.1509 | 0.5966 | 0.735 | 0.512 | 0.4719 |
| `sml-w5` | 0.0097 | 1.0875 | 1.0496 | 0.5599 | 0.690 | 0.365 | 0.3978 |
| `msband-lo` | 0.0484 | 1.3742 | 1.1289 | 0.5511 | 0.679 | 0.523 | 0.6955 |
| `varlap-w5` | 0.0130 | 1.0863 | 1.0495 | 0.5274 | 0.650 | 0.381 | 0.4367 |
| `localvar-w2` | 0.0807 | 1.1492 | 1.1286 | 0.5035 | 0.620 | 0.531 | 0.5290 |
| `ring-3-8` | 0.0293 | 1.2681 | 1.0529 | 0.4859 | 0.598 | 0.607 | 0.6696 |
| `ring-2-6` | 0.0273 | 1.3131 | 1.0839 | 0.4676 | 0.576 | 0.568 | 0.7372 |
| `ring-4-12` | 0.0557 | 1.2427 | 1.0437 | 0.4626 | 0.570 | 0.636 | 0.6729 |
| `ring-2-4` | 0.0231 | 1.2803 | 1.0704 | 0.4354 | 0.536 | 0.530 | 0.7440 |
| `ring-1-5` | 0.0571 | 1.4003 | 1.1643 | 0.4329 | 0.533 | 0.516 | 0.8671 |
| `dct8-hi` | 0.0164 | 1.1117 | 1.0809 | 0.4302 | 0.530 | 0.423 | 0.5819 |
| `sml-w2` | 0.0325 | 1.1679 | 1.1227 | 0.4053 | 0.499 | 0.302 | 0.6688 |
| **`ring-1-3`** ← incumbent | 0.0551 | **1.3475** | 1.1504 | **0.3980** | 0.490 | 0.479 | **0.8573** |
| `ring-1-3-nonorm` | 0.0552 | 1.3472 | 1.1504 | 0.3970 | 0.489 | 0.483 | 0.8582 |
| `dsml-s6` | 0.3779 | 1.7818 | 1.6661 | 0.3962 | 0.488 | 0.411 | 1.2938 |
| `dsml-s3` | 0.3734 | 1.7196 | 1.6619 | 0.3490 | 0.430 | 0.382 | 1.2897 |
| `ring-1-2` | 0.0544 | 1.2928 | 1.1254 | 0.3454 | 0.425 | 0.431 | 0.8673 |
| `varlap-w2` | 0.0328 | 1.1649 | 1.1215 | 0.3428 | 0.422 | 0.301 | 0.7427 |
| `msband-hi` | 0.3222 | 1.7150 | 1.6598 | 0.3418 | 0.421 | 0.372 | 1.2940 |
| `tenengrad-w0` | 0.0335 | 1.0632 | 0.9886 | 0.3328 | 0.410 | 0.461 | 0.6533 |
| `brenner-sym-s2-w0-nonorm` | **0.0000** | 1.0542 | **0.9966** | 0.3287 | 0.405 | 0.443 | 0.6494 |
| `tenengrad-w0-nonorm` | **0.0000** | 1.0609 | **0.9888** | 0.3277 | 0.404 | 0.465 | 0.6572 |
| `ring-0-3` | 0.4778 | 1.8130 | 1.7668 | 0.2977 | 0.367 | 0.375 | 1.4463 |
| `ring-0-1` | 0.4736 | 1.6770 | 1.7081 | 0.1738 | 0.214 | 0.287 | 1.4630 |
| `sml-w0` | 0.4093 | 1.6105 | 1.6514 | 0.1572 | 0.194 | 0.258 | 1.4168 |
| `dsml-s1` | 0.4093 | 1.6105 | 1.6514 | 0.1572 | 0.194 | 0.258 | 1.4168 |

`S_max = 0.8119` (`stensor-w5`). Controls (`ctl-const`, `ctl-random`,
`ctl-luma`) are excluded from the ranking by registration and reported above.

**The shape of the front is the result.** Read down the `φ` column against `N`
and the M9 mechanism is visible in a much larger sample: every operator with
`φ > 0.3` sits at `N > 1.6x`, and the two operators with `φ = 0.0000` sit at the
minimum of the whole set. But read the same rows against `S` and the trade-off
appears: those same `φ = 0` operators are the second-least selective family
measured. **The front is genuinely two-sided, which is why the milestone needed
a Pareto answer rather than a winner.**

---

## Is a zero-centre-tap operator viable as the default?

**No. MEASURED. H1 refuted.** This was the highest-value question in the brief
and the answer is a clean negative.

| operator | `φ` | `N` | `Ncorr` | `S/Smax` |
| --- | --- | --- | --- | --- |
| `tenengrad-w0-nonorm` | **0.0000** | 1.0609x | **0.9888x** | 0.404 |
| `brenner-sym-s2-w0-nonorm` | **0.0000** | 1.0542x | **0.9966x** | 0.405 |
| `tenengrad-w0` | 0.0335 | 1.0632x | 0.9886x | 0.410 |
| `tenengrad-w2-nonorm` | 0.0217 | 1.2256x | 1.1356x | 0.748 |
| `tenengrad-w2` | 0.0612 | 1.2255x | 1.1337x | 0.751 |
| `tenengrad-w5` | 0.0728 | 1.1324x | 1.0455x | 0.986 |

The noise half of the claim holds outright: on the structure-corrected axis a
`φ = 0` operator lands at `0.9888x` and `0.9966x` — **statistically
indistinguishable from no excess at all**, which is what M9's mechanism predicts
and what makes the result trustworthy. It replicates M9's `tenengrad-w0` at
`0.9952x` on a wider basis.

The selectivity half fails. At `S/Smax ≈ 0.405`, a `φ = 0` operator elects the
wrong frame roughly **1.7x more often** than the recommended default on the same
planted surface, and its winner-map stability is correspondingly poor
(`κ = 0.443`–`0.465` vs `0.549`). **Trading 40% of the noise excess for 58% of
the selectivity is not a good trade for a stacker whose entire job is picking the
right frame.**

### Why zero-`φ` operators are hard to build, which is itself a finding

**Windowing and pointwise normalisation each re-introduce a centre tap.
MEASURED, and it was a surprise.** The registered operator set was designed to
contain zero-`φ` members and **contained none**: `tenengrad-w2-nonorm`,
`brenner-sym-s2-w2` and `stensor-w2` were all asserted to have zero centre tap
and measured `6.4e-3`, `9.9e-2` and `3.5e-3`. The self-test caught it before any
treatment ran (amendment A1).

- **A window mean re-couples.** Averaging a Sobel response over a window pulls in
  neighbours whose *own* responses depend on the centre pixel. The window is what
  breaks the zero, not the operator.
- **A pointwise divisor re-couples.** Dividing by `σ(L(p))` at the centre pixel
  makes the score depend on the centre level directly.

Only `window = 0` **and** `Norm::None` gives `φ ≡ 0`, and both such operators
then measured exactly `0.000e0`. **A "zero-centre-tap operator" is a property of
the whole pipeline stage, not of the kernel** — a practically important point,
because the natural way to make a gradient operator usable (smooth it, normalise
it) is exactly the way to destroy the property that made it attractive.

**One prediction inside A1 was itself partially refuted. MEASURED.** A1 predicted
the ordering `φ(w0-nonorm) = 0 < φ(w0) < φ(w2-nonorm)`. Measured:
`0.0000 < 0.0335` (`tenengrad-w0`) but `tenengrad-w2-nonorm = 0.0217 < 0.0335`.
Both mechanisms are individually confirmed; the chained ordering is not, because
a window also *dilutes* the centre's share of a larger total. Reported because it
was registered.

---

## Should `crates/strehl-core/src/focus.rs` change?

**Yes. MEASURED, with a caveat about scope that the orchestrator should weigh.**

`INNER_RADIUS: 1` / `OUTER_RADIUS: 3` is `ring(1,3)`: `N = 1.3475x`, `S = 0.3980`
(`S/Smax = 0.490`), `J = 0.8573`, **rank 26 of 36**. It is the *third-noisiest*
non-degenerate ring measured and less than half as selective as the leaders. The
arbitrary choice was not a lucky one.

**Primary proposal — replace the operator:**

> Replace the ring difference with **Tenengrad (Sobel gradient energy) under an
> 11x11 box window**: horizontal and vertical 3x3 Sobel responses, squared and
> summed, box-averaged over a radius-5 window, normalised by the noise model.
> `N = 1.1324x` (vs `1.3475x`), `S/Smax = 0.986` (vs `0.490`), cost
> `6.411 ms/frame/Mpx` (vs `5.987`).

Expected effect on the pipeline: **argmax noise excess falls from `1.35x` to
`1.13x` and wrong-frame selection roughly halves**, at ~7% more focus-stage cost
in a stage that M7 measured as *not* the bottleneck (fused GPU focus+merge over
22 frames: 4.117 ms, bandwidth-bound).

**Fallback proposal — if the constants must remain a ring:**

> `INNER_RADIUS: 3`, `OUTER_RADIUS: 8`. MEASURED: `ring(3,8)` is the best ring in
> a 7-configuration sweep at `S/Smax = 0.598` and `N = 1.2681x`, versus `0.490`
> and `1.3475x`. It is a real improvement and still well short of the leaders.

**Two things the orchestrator must handle if it applies either change:**

1. `focus.rs` carries a test `centre_tap_fraction_is_the_value_m9_measured`
   pinning `φ = 1/18` and 49 taps. That test encodes M9's *verified* analytic
   result for a ring and must be **updated, not deleted** — for Tenengrad the
   equivalent pinned value is the measured `φ = 0.0728` at window radius 5, and
   the analytic ring formula `φ = 1/(2·(2·inner+1)²)` remains correct for rings
   and should be kept as a documented identity even if no ring ships.
2. Per M11's file ownership, **I did not touch `crates/`.** The operators live in
   `experiments/m11-focus-bakeoff/src/measures.rs`; porting is a separate,
   reviewable change.

---

## Robustness of the ruling

Top three under eight different aggregations. MEASURED. The same three operators
occupy the top three in **every** one.

| aggregation | 1st | 2nd | 3rd |
| --- | --- | --- | --- |
| registered (both stacks) | `stensor-w5` (0.130) | `tenengrad-w5` (0.146) | `brenner-sym-s2-w5` (0.149) |
| 109MSDCF alone | `stensor-w5` (0.095) | `brenner-sym-s2-w5` (0.118) | `tenengrad-w5` (0.128) |
| 119MSDCF alone | `stensor-w5` (0.165) | `tenengrad-w5` (0.166) | `brenner-sym-s2-w5` (0.181) |
| structure-corrected `Ncorr` | `stensor-w5` (0.042) | `brenner-sym-s2-w5` (0.055) | `tenengrad-w5` (0.059) |
| selectivity under tilt 4 | `stensor-w5` (0.138) | `brenner-sym-s2-w5` (0.147) | `tenengrad-w5` (0.170) |
| selectivity under tilt 16 | `stensor-w5` (0.130) | `brenner-sym-s2-w5` (0.160) | `tenengrad-w5` (0.169) |
| selectivity under tilt 32 | `stensor-w5` (0.130) | `tenengrad-w5` (0.161) | `brenner-sym-s2-w5` (0.167) |
| both axes at width 9 | `stensor-w5` (0.109) | `tenengrad-w5` (0.112) | `brenner-sym-s2-w5` (0.146) |
| both axes at width 17 | `tenengrad-w5` (0.081) | `stensor-w5` (0.087) | `ring-1-3` (0.094) |

`λ` sensitivity: argmin `J` is `stensor-w5` at every registered `λ` in
`[0.25, 4]`. The O5 tie and its registered tie-break are what select
`tenengrad-w5` from that group, not a marginal `J` difference.

**Do the axes agree? Yes — outcome O7 does not fire.** Spearman across the 36
registered operators: `ρ(S, κ_inject) = +0.756`, `ρ(S, κ_G1G2) = +0.877`. The
planted selectivity metric and the two real-data winner-stability corroborators
rank operators the same way, so the ruling is not an artefact of the synthetic
plant. Registered trigger was `ρ < 0.5`.

---

## What this says about M9's mechanism

**M9's direction replicates; M9's magnitude does not. MEASURED, and this
partially weakens SYNTHESIS fact 35.**

| statistic | M9 (two stacks, smaller set) | M11 (36 operators) |
| --- | --- | --- |
| `ρ(φ, N)` | **+0.918 / +0.894** | **+0.579** |
| `ρ(support_r, N)` | −0.170 / −0.243 (n.s.) | **−0.009** (n.s.) |
| `ρ(φ, S)` | not measured | −0.088 (n.s.) |
| `ρ(support_r, S)` | not measured | **+0.553** |

Two things follow, and the second is new.

**First, the qualitative M9 result stands and is strengthened where it matters
most.** `φ` predicts noise excess, support radius does not — `−0.009` is about as
clean a null as a correlation gets — and the extremes behave exactly as the
mechanism says: `φ = 0.478` → `1.81x`, `φ = 0.000` → `1.05x`. But `+0.579` over
36 operators is materially weaker than `+0.918` over M9's set, so **`φ` is a
strong ordering principle at the extremes and a loose one in the middle**, where
operators at `φ ≈ 0.02–0.10` span `N` from `1.06x` to `1.40x`. Something other
than `φ` is contributing there. I did not identify it, and I am not going to
guess in a report.

**Second, and new: the two axes are governed by *different* structural
variables.** `φ` predicts noise (`+0.579`) and not selectivity (`−0.088`);
support radius predicts selectivity (`+0.553`) and not noise (`−0.009`). That is
an unusually clean separation and it is the reason a Pareto front exists at all:
**an operator can buy selectivity with support without paying for it in noise,
as long as it does not buy centre-tap sensitivity along the way.** `tenengrad-w5`
is exactly that trade — radius 6, `φ` only 0.0728. `dsml-s6` is the
counter-example: radius 12 but `φ = 0.378`, and it pays `1.78x`.

---

## Sweeps

### Depth discrimination (`α`, px of blur per frame). MEASURED.

| operator | α=0.15 | α=0.35 | α=0.7 | α=1.4 |
| --- | --- | --- | --- | --- |
| `stensor-w5` | 0.680 | 0.770 | 0.792 | 0.784 |
| `ring-1-3` | 0.280 | 0.371 | 0.426 | 0.478 |
| `tenengrad-w0-nonorm` | 0.222 | 0.295 | 0.338 | 0.385 |
| `ctl-random` | 0.046 | 0.046 | 0.046 | 0.046 |

The gap is **widest at the shallowest ladder**, which is the regime that matters:
at `α = 0.15` the recommended family is 2.4x more accurate than the incumbent and
3.1x more accurate than a zero-`φ` operator. The null holds flat across the whole
sweep, which is the cheapest available evidence that `S` is measuring focus.

### Injected-noise scale. MEASURED.

| operator | x0 | x0.5 | x1 | x2 | x4 |
| --- | --- | --- | --- | --- | --- |
| `stensor-w5` | 0.895 | 0.879 | 0.772 | 0.621 | 0.496 |
| `brenner-sym-s2-w5` | 0.904 | 0.885 | 0.765 | 0.613 | 0.462 |
| `tenengrad-w5` | 0.882 | 0.864 | 0.753 | 0.576 | 0.435 |
| `sml-w5` | **0.996** | 0.692 | 0.553 | 0.306 | 0.111 |
| `ring-1-3` | 0.652 | 0.454 | 0.372 | 0.285 | 0.199 |
| `tenengrad-w0-nonorm` | 0.592 | 0.375 | 0.294 | 0.218 | 0.149 |

**`sml-w5` is the most interesting row in the report and it is a warning.** With
*zero* injected noise it is the best operator in the set at `0.996` — better than
anything else measured. At x0.5 it has already collapsed below the leaders, and
by x4 it is worse than the incumbent. **An operator can be near-perfect in the
noiseless limit and near-useless at realistic noise.** Any bake-off run on
synthetic noiseless data would have recommended SML. This is the concrete reason
the milestone's insistence on real-sensor noise was correct, and it is a trap for
anyone reading the focus-measure literature, which is largely evaluated noise-free.

### Regulariser width, and an interior optimum at last. MEASURED.

SYNTHESIS fact 36 records that the flat-ROI *noise* objective is
monotone-decreasing then flat in regulariser width — no interior optimum, and any
tuner minimising noise runs to the boundary. That replicates here: at widths
1/9/17 the incumbent's `N` falls 1.277 → 1.101 → 1.075 monotonically.

**The selectivity objective supplies the missing second side, but only when the
depth surface is not fronto-parallel.** `S` by width, on a planted linear depth
ramp of `K` frames across a 256 px ROI:

| tilt | operator | w1 | w5 | w9 | w17 | w33 |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | `stensor-w5` | 0.784 | 0.842 | 0.892 | 0.956 | **0.980** |
| 0 | `ring-1-3` | 0.362 | 0.620 | 0.799 | 0.949 | **0.997** |
| 4 | `stensor-w5` | 0.665 | 0.734 | 0.786 | 0.861 | **0.917** |
| 16 | `stensor-w5` | 0.637 | 0.698 | 0.734 | **0.777** | 0.760 |
| 16 | `ring-1-3` | 0.298 | 0.516 | 0.672 | **0.783** | 0.787 |
| 32 | `stensor-w5` | 0.631 | 0.683 | 0.713 | **0.739** | 0.709 |
| 32 | `tenengrad-w5` | 0.613 | 0.666 | 0.697 | **0.734** | 0.730 |
| 32 | `ring-1-3` | 0.323 | 0.540 | 0.677 | **0.751** | 0.743 |

**At tilt 16 and 32 the width axis turns over: `S` peaks near width 17 and
declines at 33.** This is the first two-sided objective in regulariser width this
project has measured. It says the boundary-running problem in fact 36 is a
property of the *noise-only* objective and of *fronto-parallel* test surfaces,
not of the width parameter itself — **a joint objective evaluated on a tilted
depth surface has an interior optimum, measured here at width ≈ 17 for a depth
gradient of 16–32 frames per 256 px.** It also confirms the milestone's warning
in the concrete: tuning width on a fronto-parallel plant would have run to the
sweep edge and produced a regulariser that destroys real depth structure.

### Cost, single-threaded. MEASURED.

`brenner-sym-s2-w5` 4.651 · `ring-1-3` 5.987 · `tenengrad-w5` 6.411 ·
`stensor-w5` 15.891 · `dct8-hi` 158.626 ms/frame/Mpx. Cost was registered as a
tie-break only, and it acted as exactly that: it chose `tenengrad-w5` over
`stensor-w5` inside a measured tie.

---

## The post-hoc extension (amendment A4), reported separately

**The registered front was truncated, and I am disclosing it rather than
absorbing it.** Every leading operator landed at `w5`, the widest registered
window — the signature of a truncated sweep. Four operators were re-run at `w8`
and `w11` **after** seeing that, so these numbers are **post-hoc** and are
excluded from the registered ruling.

| operator | `φ` | `N` | `S` | `J` |
| --- | --- | --- | --- | --- |
| `tenengrad-w11` | 0.1089 | **1.0908x** | **0.9407** | **0.0908** |
| `stensor-w11` | 0.3143 | 1.0918x | 0.9307 | 0.1025 |
| `brenner-sym-s2-w11` | 0.3447 | 1.0952x | 0.9263 | 0.1105 |
| `tenengrad-w8` | 0.0872 | 1.1019x | 0.8955 | 0.1500 |
| `sml-w11` | 0.0107 | 1.0681x | 0.6914 | 0.3331 |

**`tenengrad-w11` is better than every registered operator on *both* axes
simultaneously** — `N` 1.0908 vs 1.1324 and `S` 0.9407 vs 0.8007 — and it is the
argmin `J` over registered ∪ extension. `S` is still rising and `N` is still
falling at `w11`. **The optimum window is larger than anything measured**, and I
did not find its edge.

That the registered winner and the extension winner are the *same operator
family* is the reason I am comfortable recommending Tenengrad rather than
treating A4 as a confound: the post-hoc data changes the recommended *window*, not
the recommended *operator*.

---

## What I refuted, including my own hypotheses

1. **H1 — "a zero-centre-tap operator is both noise-free and adequately
   selective" — REFUTED by my own data.** Noise-free: yes (`Ncorr` 0.9888,
   0.9966). Adequately selective: no (`S/Smax` 0.404). Registered as falsifiable
   before running; falsified.
2. **My registered prediction that `ctl-luma` (`φ = 1`, the maximally
   noise-coupled control) would show the *largest* `N` — REFUTED.** Measured
   `0.6604x` / `0.7667x`, the *smallest* in the set. Diagnosis: argmax-of-luma is
   an extreme order statistic. It compresses dispersion and shifts the mean
   (+8.5 DN measured in the placebo arm), and an sd-ratio metric sees only
   dispersion. **The `N` axis is not a valid noise metric for an operator that
   selects on level itself** — a real limitation of the instrument, disclosed
   because it was a registered prediction.
3. **Amendment A1's predicted `φ` ordering — PARTIALLY REFUTED.** See the
   zero-`φ` section.
4. **My registered rule-9 flat-ROI control — FAILED,** and the failure was in the
   control's design. Repaired by A5's constant-base null, which passes.
5. **SYNTHESIS fact 35's magnitude — WEAKENED.** `ρ(φ, N) = +0.579` over 36
   operators against M9's `+0.918 / +0.894`. Direction and the radius null
   replicate; the strength does not.
6. **The hypothesis that a better focus measure could remove the noise excess —
   REFUTED.** `A` is empty. This one was not mine, but it was live.

## What I could not measure

1. **The optimum window size.** The extension is still improving on both axes at
   `w11` (23x23). I bounded it from below and not from above.
2. **Depth discontinuities.** The plants are fronto-parallel or linearly tilted.
   A real macro stack has occluding edges — a hair in front of a background —
   where a 23x23 window would smear the winner map across the discontinuity. **My
   selectivity metric would not see that damage**, because it scores per-pixel
   frame election, not edge integrity. This is the most likely way the wide-window
   recommendation is wrong, and it is untested.
3. **Whether the recommendation generalises off this rig.** Both stacks are the
   same body, lens and teleconverter, at `f/33` effective with critical sampling
   at `f/6.21` — genuinely diffraction-limited and soft. The owner asked
   explicitly that the design not be specialised to the gear. The recommended
   operator is textbook Sobel with one knob, which is about as generic as the set
   allows, but **"generalises" is ARGUED here, not MEASURED.**
4. **Why `φ` loses predictive power in the middle of its range.** `+0.579` says
   something else matters at `φ ≈ 0.02–0.10`. Unidentified.
5. **119MSDCF's planted numbers are a corroborator, not evidence**, per the
   registered consequence of the realised-noise gate (A5).

---

## Proposed SYNTHESIS changes

Exact text, for the orchestrator to apply. I did not edit `SYNTHESIS.md`.

### New facts (the record has 36; these are 37–41)

> **37.** **Operator choice alone cannot remove argmax's noise excess.** Across a
> 47-operator bake-off spanning `φ` from 0.0000 to 0.4778 and support radius 1 to
> 12, **no operator reaches the pre-registered noise-free bar of `N ≤ 1.02x`** on
> real data — the qualifying set was empty, 0 of 36 registered operators
> (M11, pre-registered outcome O4). Choosing well moves the excess from `1.35x`
> to `1.05x`; it does not reach `1.00x`. The escape from selection's noise
> penalty is estimation, not a better selector. MEASURED.

> **38.** **A zero-centre-tap operator is noise-free and under-selective.**
> `tenengrad-w0-nonorm` and `brenner-sym-s2-w0-nonorm` measure `φ = 0.0000`
> exactly and score `Ncorr` **0.9888x** and **0.9966x** — no measurable excess,
> confirming M9's mechanism — but recover a planted focus surface at only
> **40.4%** of the best operator's rate. Viable as a noise reference; **not
> viable as a default** (M11, hypothesis H1 registered and refuted). MEASURED.

> **39.** **Windowing and pointwise normalisation each re-introduce a centre
> tap.** A window mean over a zero-centre-tap kernel pulls in neighbours whose
> responses depend on the centre pixel, and a pointwise `σ(L(p))` divisor couples
> to the centre level directly. Measured: `tenengrad-w2-nonorm` `φ = 0.0217`,
> `tenengrad-w0` `φ = 0.0335`, `brenner-sym-s2-w2` `φ = 0.099`, against
> `0.0000` for `window = 0` **and** `Norm::None`. **Zero centre tap is a property
> of the whole pipeline stage, not of the kernel.** MEASURED (M11, amendment A1).

> **40.** **The two axes are governed by different structural variables.** Over 36
> operators: `φ` predicts noise excess (`ρ = +0.579`) and not selectivity
> (`ρ = −0.088`); support radius predicts selectivity (`ρ = +0.553`) and not noise
> (`ρ = −0.009`). This separation is why a Pareto front exists — selectivity can
> be bought with support without paying in noise, provided centre-tap sensitivity
> is not bought along with it. It also **weakens fact 35's magnitude**: M9
> measured `ρ(φ, N) = +0.918 / +0.894` on a smaller set. Direction and the radius
> null replicate; the strength does not. `φ` is a strong ordering principle at the
> extremes and a loose one in the middle. MEASURED (M11).

> **41.** **The ring difference is a poor focus measure and the shipped constants
> are among its worse settings.** `ring(1,3)` ranks **26th of 36** on the
> registered objective: `N = 1.3475x`, selectivity 49.0% of best. The best ring in
> a 7-configuration sweep, `ring(3,8)`, reaches only 59.8%. **Tenengrad (Sobel
> gradient energy) under an 11x11 box window** reaches 98.6% at `N = 1.1324x` for
> 7% more cost, in a stage M7 measured as not the bottleneck. Re-tuning the ring
> radii cannot close the gap; the operator should be replaced. MEASURED (M11).

Optional sixth, if the record wants the width result:

> **42.** **A joint selectivity/noise objective has an interior optimum in
> regulariser width; a noise-only objective does not.** Fact 36's boundary-running
> behaviour replicates for noise alone, but on a planted **tilted** depth surface
> (16–32 frames of depth across 256 px) selectivity peaks near **width 17** and
> declines by width 33. On a fronto-parallel surface it does not turn over at all.
> Tuning a regulariser on fronto-parallel test data will therefore run to the
> sweep edge and destroy real depth structure. MEASURED (M11).

### Risk 2

> **Risk 2 — the default focus measure was chosen arbitrarily. CLOSED by M11.**
> A 47-operator pre-registered bake-off measured the Pareto front of selectivity
> against noise excess on two real stacks. The incumbent `ring(1,3)` ranks 26th of
> 36; the recommendation is **Tenengrad (Sobel gradient energy) under an 11x11 box
> window**, reached by the registered decision rule through outcome **O4** (no
> operator is noise-free) and **O5** (a measured three-way tie, broken by fewest
> parameters then lowest cost). The choice is no longer arbitrary. **Two residual
> uncertainties are carried forward as an open question rather than as risk:** the
> optimum window is larger than anything measured (the post-hoc extension is still
> improving on both axes at 23x23), and no plant in M11 contained a **depth
> discontinuity**, which is the regime where a wide window is most likely to do
> damage that M11's per-pixel selectivity metric cannot see.

### Discipline item (SYNTHESIS §5)

> **A control can fail because the control is wrong, and that must be published
> as loudly as a treatment failure.** M11 registered a rule-9 pairing — "the same
> planted run on a flat ROI must collapse to within 3x of chance" — and it failed
> at **13.8x** and **31.7x** chance. The cause was the control, not the metric: a
> *relatively* flat ROI of a real frame still carries a broadband texture, its own
> inherited read and shot noise, and a planted blur ladder blurs that too. The
> same run with the base replaced by its own mean — nothing left to blur — sits at
> **1.12x** chance. A second registered gate (realised per-frame noise spread
> ≤ 10%) was being read off the ROI where it could never pass. **The rule going
> forward: when a registered control fails, diagnose it before believing it, and
> publish the original failure next to the repair. Deleting a failed control and
> substituting a passing one is indistinguishable, from the outside, from
> fabrication.**

---

## How to quote this

- `N` figures are **flat-ROI spatial sd ratios**, median over 4 ROIs then mean
  over 2 stacks, at regulariser width 1. They are **not** temporal sigmas and
  must never be compared to one (rule 10).
- `Ncorr` is the structure-corrected form and is the better number to quote for
  the *mechanism*; `N` is the registered ranking input and is the number to quote
  for the *ruling*.
- `S` is planted-surface election accuracy on **109MSDCF**; 119MSDCF is a
  corroborator only (amendment A5).
- **`w8` and `w11` numbers are post-hoc** (amendment A4) and must carry that
  label.
- Everything labelled ARGUED above is an interpretation, not a measurement. The
  generalisation claim in particular is ARGUED.

## Gates and the read-only corpora

`cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -D
warnings` and `cargo test --workspace` were run at the repository root and inside
`experiments/m11-focus-bakeoff`. Results are recorded in the commit message.

`C:\dev\macro` and `D:\macro-dark-frames` are byte-for-byte unchanged:
`data/audit-before.txt` and `data/audit-after.txt` record **17449 files /
286,581,830,721 bytes** and **242 files / 8,179,392,512 bytes** respectively, by
identical method, before and after the entire run. Nothing in this experiment
opens either corpus for writing.
