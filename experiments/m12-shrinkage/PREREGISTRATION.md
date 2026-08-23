# M12 — pre-registration

**Written before any M12 analysis script was run.** The edge CSVs
(`data/stack-112-edges.csv`, `data/stack-113-edges.csv`) had been *measured* when
this was written — measurement is data collection, not analysis — but no ladder,
no ratio and no correction had been computed, and nothing in this document depends
on a no-fit count. Everything below is fixed. Where a number is filled in later it
is filled in by a script, mechanically, in `m12_ruling.py`.

SYNTHESIS §5 items 14, 18, 19, 20 and rule 8 govern this document.

---

## 0. The question

**Can the short-baseline magnification shrinkage (SYNTHESIS fact 43) be calibrated
away?**

Fact 43 says short-baseline pairwise similarity fits under-report the
log-magnification change coherently, so that telescoping them gives a total that
depends on the span — which is impossible for an unbiased estimator, because
`Σ log a` over any span must telescope to the same total. M10 declined to fit a
correction because it had one deep stack, so any fit could only be tested on the
stack it was fitted to.

`112MSDCF` (79 frames) and `113MSDCF` (63 frames) are two captures of one static
subject over an identical focus range (SYNTHESIS fact 49). They make the
correction testable out of sample, and — because they sample the same physical
sweep at two densities — they separate two hypotheses that are otherwise
confounded.

---

## 1. Definitions, fixed here

All geometry is in **plane px** (CFA-quad green plane 3516 x 2344, one plane px =
two sensor px). Corner radius `rho = 2112.93` plane px.

An edge `(i, j)` measured directly between frames `i` and `j` yields the complex
similarity coefficient `a_ij`. Its **log-magnification** is

    L_ij = log |a_ij|

### 1.1 The windowed conservation ladder

Fix a **window** `W` (frames `0 .. W`). For every span `s` that divides `W`:

    T_W(s) = sum over k in {0, s, 2s, ..., W-s} of L_{k, k+s}

Every `T_W(s)` estimates the *same* physical quantity — the total log
magnification from frame 0 to frame `W`. So for an unbiased estimator

    T_W(s) = L_{0,W}   for every s,      (the conservation identity)

exactly, with no median, no weighting, no solver and no extrapolation. This is a
strengthened form of M10's ladder: M10 telescoped to whatever coverage each span
happened to reach and then rescaled by `(n-1)/cov`, which mixes an extrapolation
error into the comparison. Here every span covers **exactly the same frame range
with exactly the same endpoints**, so the only thing that varies is the baseline.

### 1.2 Recovery fraction and shrinkage ratio

    A_W = L_{0,W}                      (the anchor: one directly measured edge)
    S_W(s) = T_W(s) / A_W              (recovery fraction; 1.0 == unbiased)
    rho_shrink(W) = 1 / S_W(1)         (THE HEADLINE SHRINKAGE RATIO)

**The rule producing the headline ratio is stated, per the M12 brief and
SYNTHESIS fact 43's note about M10's underivable "3.33x":** `rho_shrink` is
`A_W / T_W(1)` — the direct long edge over the telescoped span-1 sum, both across
the identical frame range `0..W`.

For comparability with M10's published figures I *also* report

    G_W = T_W(16) / T_W(1) = S_W(16) / S_W(1)

which is M10's span16/span1 form (`3.49x` on coffee-bean).

**Disjointness (SYNTHESIS §5 item 20).** `A_W` is the single edge `(0, W)`.
`T_W(s)` for `s < W` uses only span-`s` edges, and no span-`s` edge with `s < W`
is the edge `(0, W)`. So numerator and denominator are **disjoint measurements**
for every `s < W`. Rows with `s = W` are excluded from every ruling, because there
`T_W(W) = A_W` identically — that is exactly the circularity item 20 records.

A second, independent anchor `A'_W = T_W(W/2)` (two edges, `(0, W/2)` and
`(W/2, W)`) is reported alongside, and is likewise disjoint from `T_W(s)` for
`s < W/2`.

### 1.3 Window choice

Headline `W = 48`, available in both stacks (79 and 63 frames), divisors
`s in {1, 2, 3, 4, 6, 8, 12, 16, 24}`.
Robustness `W = 24` (`s in {1,2,3,4,6,8,12}`), `W = 32` (`s in {1,2,4,8,16}`),
`W = 16` (`s in {1,2,4,8}`).

Headline configuration is `cfg = m10` (M3's estimator with margin 96).
`cfg = wide64` is reported as a robustness arm only, and per SYNTHESIS §5 item 19
its "0 no-fit" is not evidence of anything.

---

## 2. The three parameterisations being tested

`112` and `113` sweep the **same focus interval** with `78` and `62` inter-frame
steps respectively, so one frame-index step in `113` is `78/62 = 1.258x` the
physical baseline of one step in `112`.

| Hypothesis | Claim | Prediction |
| --- | --- | --- |
| **H-index** | shrinkage is a function of frame-index span | `S_112(s) = S_113(s)` |
| **H-phys** | shrinkage is a function of physical focus baseline | `S_113(s) = S_112(1.258 s)` |
| **H-disp** | shrinkage is a function of the edge's *true* differential corner displacement `d = rho * s * r_true`, where `r_true = |A_W| / W` (fact 45's variable) | all stacks collapse onto one curve in `d` |

H-index and H-phys are distinguished **only** by the 112/113 pair, because those
two stacks hold subject and sweep constant and vary sampling density alone. That
is the single most valuable thing in the dataset and it is why this experiment is
possible at all.

H-disp is the fact-45 hypothesis and is tested across **five** stacks
(112, 113, coffee-bean, 119MSDCF, 109MSDCF).

### Registered decision rule for the parameterisation

Over the comparison set `s in {1, 2, 3, 4, 6, 8, 12}` at `W = 48`, compute

    SSD_index = sum_s [ S_113(s) - S_112(s) ]^2
    SSD_phys  = sum_s [ S_113(s) - Shat_112(1.258 s) ]^2

where `Shat_112` is a log-span linear interpolation of the measured 112 curve.
**Declare a winner only if one SSD is <= 0.5x the other.** Otherwise: *not
distinguishable by this data*, and I say so.

For H-disp, fit `S(d) = d / (d + d0)` per stack by least squares on
`s in {1,2,3,4,6,8,12}` and compare `d0` across the five stacks. H-disp is
supported only if `d0` agrees across the 112/113 pair to within the same 2-sigma
band defined in §3, and is **strongly** supported only if it also agrees across
all five stacks to within a factor of 2.

---

## 3. Pre-registered answer to brief question 1: the exact comparison statistic

**Primary statistic: `S_48(1)`** — the span-1 recovery fraction over the common
48-frame window, `cfg = m10`, computed on 112 and on 113.

**Primary comparison:** the difference `S_112(1) - S_113(1)` and the
ratio-of-ratios `Q = rho_shrink,112 / rho_shrink,113 = S_113(1) / S_112(1)`.

---

## 4. Pre-registered answer to brief question 2: the matching threshold

A threshold has to come from a **measured** spread, not from taste
(SYNTHESIS §5 item 13: set a gate's tolerance above the measured run-to-run
spread of its own two sides).

**Registered null control C5 (within-capture spread).** Compute `S_W(1)` at
`W = 24` over **disjoint** 24-frame windows inside each capture:

* 112 (79 frames): windows `[0,24]`, `[24,48]`, `[48,72]` — 3 replicates
* 113 (63 frames): windows `[0,24]`, `[24,48]` — 2 replicates

These five replicates share subject, rig, sweep and estimator and differ only in
which part of the sweep they sit in. Their **pooled within-capture standard
deviation `sigma_w`** is the noise floor of the statistic — the amount by which
`S(1)` moves for reasons a span-keyed or baseline-keyed rule can never see.

**The rule:**

| Condition on `\|S_112(1) - S_113(1)\|` (at matched `W = 24`, averaged over each stack's windows) | Verdict |
| --- | --- |
| `<= 2 sigma_w` | **MATCHING** — reproducible function of baseline; calibration is viable in principle |
| `> 3 sigma_w` | **MATERIALLY DIFFERENT** — a fixed calibration cannot work |
| between | **INDETERMINATE** — the ruling falls to §5 alone |

**Justification.** A fixed calibration keyed on span or baseline must reproduce
*between* captures at least as well as the statistic reproduces *within* one
capture. If between-capture spread exceeds the within-capture spread by more than
2-3x, the excess is capture-specific by definition and no rule keyed on span or
physical baseline can absorb it. 2 sigma / 3 sigma leaves an explicit
indeterminate band rather than forcing a verdict — SYNTHESIS §5 item 14 requires
the full outcome grid, including the cell where neither branch fires.

---

## 5. The out-of-sample test, and the operational threshold

**Fit on one stack, test on the other, both directions.**

Fit: from stack A, derive `k_A(s) = 1 / S_A,48(s)`, the multiplicative correction
that a span-`s` edge's `log |a|` needs.

Test on stack B: predict B's total log-magnification over B's own window from B's
**span-1 edges alone**, corrected by `k_A(1)`:

    Lhat_B = k_A(1) * T_B,W(1)
    rel_err_corrected   = |Lhat_B - A_B,W| / |A_B,W|
    rel_err_uncorrected = |T_B,W(1) - A_B,W| / |A_B,W|

`A_B,W` is B's directly measured long edge. It is **disjoint** from B's span-1
edges and from every edge in A.

**Registered operational threshold — calibration is VIABLE iff, in both
directions:**

1. `rel_err_corrected <= 0.10`, **and**
2. `rel_err_corrected <= 0.5 * rel_err_uncorrected` (at least 2x better than
   doing nothing).

**Justification for the 10%.** A relative error `e` on a total log-magnification
`L` costs `rho * |L| * e` plane px at the corner. These stacks carry a few percent
of total drift, so `|L| ~ 0.03` and `e = 0.10` costs `2113 * 0.03 * 0.10 = 6.3`
plane px — the same size as the 6.76 plane px that M10's global least-squares
solve already achieves without any correction (fact 46). **A correction whose
residual error is as large as the thing it is competing with buys nothing**, so
10% is where viability ends for a project reason, not a statistical one.

**Positive control for this test (C7):** the *in-sample* version — fit `k` on B
and test on B — must give `rel_err_corrected` at or near machine zero for
`s = 1`. If it does not, the fitting code is broken and nothing downstream is
believed.

**Practical arm (C8).** Apply `k_A(1)` to every span-1 edge of stack B, compose
the corrected chain from frame 0, and measure the worst-corner error against the
**directly measured** `(0, j)` edges, which are disjoint from the chain. Report
corrected vs uncorrected chain error. This is the quantity project rule 6 is about.

---

## 6. Pre-registered answer to brief question 3: what refutes calibration

I will conclude **calibration is impossible with a fixed rule** if either:

* **(R1)** `|S_112(1) - S_113(1)| > 3 sigma_w` — two captures of the same scene
  over the same sweep disagree on the shrinkage by more than three times the
  within-capture spread; **or**
* **(R2)** the §5 out-of-sample test fails condition 2 (`<= 0.5x` uncorrected) in
  **either** direction — the correction does not beat doing nothing, which is the
  only thing it exists to do.

(R2) alone is sufficient regardless of (R1), because a correction that
cross-applies no better than no correction is not a calibration whatever the
statistics say.

I will conclude **calibration is viable** only if **all** of:

* `|S_112(1) - S_113(1)| <= 2 sigma_w`, and
* both directions pass both operational conditions in §5, and
* the winning parameterisation from §2 is declared (SSD ratio <= 0.5).

Anything else is **PARTIAL** and will be reported as partial, with the specific
cell of the grid that fired named explicitly.

### The full outcome grid (SYNTHESIS §5 item 14)

| §4 verdict | §5 out-of-sample | Ruling |
| --- | --- | --- |
| MATCHING | passes both directions | **VIABLE** — fit it, ship it as a span/baseline-keyed correction, rule 6 relaxes |
| MATCHING | fails | **PARTIAL/NEGATIVE** — the ratio reproduces but the correction does not transfer; report the gap and keep rule 6 |
| INDETERMINATE | passes both | **PARTIAL/POSITIVE** — usable, but the evidence for a *fixed* rule is weak; recommend per-stack estimation |
| INDETERMINATE | fails | **NEGATIVE** — per-stack estimation or discard short spans |
| MATERIALLY DIFFERENT | passes both | **CONTRADICTION** — do not paper over it; report both and say the statistic and the objective disagree |
| MATERIALLY DIFFERENT | fails | **REFUTED** — no fixed calibration; rule 6 stands as written |

---

## 7. Controls. Nothing below §7 is believed if any of these fails

Every headline number in M12 needs a null control and a positive control
(project rule 11).

| ID | Kind | What | Pass condition |
| --- | --- | --- | --- |
| **C1** | positive | M3 §0's four known warps through this crate's estimator, on a 112 base frame and a 113 base frame | worst `g` error `< 1e-4`, i.e. `< 0.3` plane px at the corner |
| **C2** | positive / reproduction | My copied analysis code, run on **M10's committed** `coffee-bean-edges.csv`, must reproduce M10's published ladder (span-1 `-1.6876%`, span-16 `-5.8891%`) | both to `<= 0.0002` absolute in percent. SYNTHESIS §5 item 15 — reproduce a published number before trusting a re-implementation |
| **C3** | **null** | Synthetic stacks of `n = 79` and `n = 63` built by resampling a real 112 / 113 base frame along a planted magnification path — **planted geometry, no real defocus change**. Fact 45 predicts no shrinkage | `S_48(1)` within `[0.85, 1.20]`. If the real ladder rises and this one does not, the ladder is not an artifact of the estimator or the resampler |
| **C4** | positive | P7 planted-increment recovery on **real** 112 / 113 defocus-mismatched pairs | ratio `>= 0.95` at `\|g\| = 4e-3`; and `< 0.9` at `\|g\| = 2e-4` (the fact-45 signature) |
| **C5** | null | Within-capture disjoint-window spread of `S_24(1)` (§4) | reported as `sigma_w`; used as the threshold, so it cannot "fail", but it is published |
| **C6** | audit | Disjointness audit: every quoted agreement lists the two measurement sets and asserts they share no edge | printed by `m12_ruling.py`; any overlap is a defect |
| **C7** | positive | In-sample correction (§5) | `rel_err_corrected < 1e-9` |
| **C8** | practical | Corrected vs uncorrected chain corner error against direct `(0,j)` anchors | reported, not gated |
| **C9** | audit | Read-only capture trees unchanged: file count and total bytes for `C:\dev\macro`, `D:\macro-dark-frames`, `D:\personal\macro` before and after | byte-identical totals |

**Robustness scoring (SYNTHESIS §5 item 19).** `wide64` reports 0 no-fit pairs on
both stacks. That is **not** evidence it is better. It is scored on the
independent metric of whether its ladder and its `S_48(1)` agree with `m10`'s,
and the report says so.

---

## 8. What I expect (recorded so it can be wrong)

I expect the ladder to reproduce qualitatively on both stacks — a rising `T_W(s)`
— because fact 43 has now been seen on three unrelated stacks. I have no
expectation about whether the *ratio* matches between 112 and 113, and the brief
is explicit that a clean refutation is worth as much as a clean fit. I expect
H-disp to be at least as good as H-index because fact 45 identifies differential
displacement as the governing variable, but the 1.258x lever is small and may not
resolve it.
