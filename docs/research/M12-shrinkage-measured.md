# M12 — can the short-baseline magnification shrinkage be calibrated away?

Status: **Measured. The answer is no, and the reason is not the one the milestone was set up to test.**

Milestone: **M12**, a research/measurement milestone. Nothing here ships code into `crates/`.
Harness: a verbatim copy of M10's at `experiments/m12-shrinkage/` (M10's own directory was not
modified). Pre-registration: `experiments/m12-shrinkage/PREREGISTRATION.md`, committed as
`8326564` **before** any result in this report was computed.

Every claim is labelled **MEASURED** (something was run), **VERIFIED** (a primary artifact was
read and reproduced), **DERIVED** (computed from measured inputs, rule stated), **ARGUED**
(reasoned, not measured), **UNVERIFIED** (not established).

---

## 0. The headline, in four sentences

1. **Fact 43 does not replicate on the new stacks.** The shrinkage ratio is **3.260×** on
   `coffee-bean` and **1.048× / 1.027×** on `112MSDCF` / `113MSDCF` — at a *matched* per-frame
   differential displacement of 1.08 plane px and a *matched* total drift of 2.42%. Chaining 78
   adjacent edges on `112MSDCF` recovers **99.0%** of the direct long edge. (MEASURED)
2. **The ratio is highly reproducible between two captures of the same scene**: 0.9734 vs 0.9659,
   a difference of **0.15 σ_w** against the registered 2 σ_w threshold. (MEASURED)
3. **It is not a function of baseline in any parameterisation** — not frame-index span, not
   physical baseline, not true differential displacement. Two stacks matched to 0.3% in
   displacement differ 3.11× in shrinkage. (MEASURED)
4. **A fitted correction does not transfer**: **0 of 18** cross-scene ordered pairs pass, the worst
   makes the error **83.4× worse**, and even the registered 112↔113 pair fails one direction.
   Calibration by a fixed rule is **refuted**. (MEASURED)

And a fifth, which is the one that changes the project's plan:

5. **SYNTHESIS fact 49's central premise is false.** `112MSDCF` and `113MSDCF` do **not** sample the
   same focus interval at two densities. They share a **per-frame** step and 112 simply runs 16
   frames further. This is measured, not inferred: `rate(112)/rate(113) = 1.0044` where the
   fact-49 reading requires 0.7949. The consequence is that this pair **cannot** discriminate
   index-span from physical-baseline parameterisation, which was the milestone's most valuable
   advertised property. (MEASURED — §4)

---

## 1. What was measured

| | |
|---|---|
| New edge sets | `112MSDCF` 79 frames → 1017 pairs in 23.6 s; `113MSDCF` 63 frames → 761 pairs in 17.6 s (MEASURED) |
| Spans | 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, plus every direct `(0, j)` edge |
| Configs | `m10` (M3's estimator, `margin: 96`) as primary; `wide64` as a robustness arm |
| Reused corpus | `coffee-bean` (105), `119MSDCF` (33), `109MSDCF` (22) — edge CSVs copied from M10, not re-measured, so M10's published numbers are directly checkable against mine |
| Plane | CFA-quad green plane 3516×2344; 1 plane px = 2 sensor px; ρ = 2112.93 plane px |

### 1.1 The statistic, and why it is not M10's

M10's ladder summed span-`s` edges across as much of the stack as each span covered and rescaled
by `(n−1)/coverage`. That mixes an extrapolation error into a comparison that is supposed to
isolate the baseline. M12 fixes the endpoints instead.

For a window `0..W` and a span `s` dividing `W`:

- `T_W(s) = Σ_{k = 0, s, …, W−s} log|a_{k,k+s}|` — the telescoped total, which the conservation
  identity says must be **independent of `s`**;
- `A_W = log|a_{0,W}|` — the single direct anchor edge;
- `S_W(s) = T_W(s) / A_W` — the recovery fraction;
- **headline shrinkage ratio `1/S_W(1) = A_W / T_W(1)`.**

**The rule is stated because M10's was not.** SYNTHESIS already records that M10's "3.33×" is
underivable — span16/span1 gives 3.49×, plateau-mean/span1 gives 3.25×. Every ratio below names
its numerator and denominator.

`s = W` rows are **excluded by construction**: there `T_W(W) ≡ A_W`, the same measurement reported
twice (SYNTHESIS §5 item 20). `divisor_spans()` also refuses any span that does not tile the
window exactly, which kills the class of error where a row is computed from a single link and
reported as if it were a ladder rung.

**VERIFIED — the reproduction gate (C2).** Before using the new statistic on anything, M10's rule
was re-implemented and run against M10's committed `coffee-bean` CSV. It returns span-1
**−1.6876%** and span-16 **−5.8891%**, matching SYNTHESIS fact 43 exactly. The harness reads
M10's data the way M10 did.

---

## 2. Deliverable 1 — does the shrinkage reproduce on 112 and 113?

**No. It is essentially absent.** (MEASURED)

| stack | W | `S_W(1)` | **`1/S_W(1)`** | `A_W` % | `d_true(1)` px | anchor tiles |
|---|---|---|---|---|---|---|
| `coffee-bean` | 48 | 0.3067 | **3.260** | −2.4257 | 1.081 | 15 |
| `119MSDCF` | 32 | 0.4547 | **2.199** | −1.0185 | 0.676 | 78 |
| `109MSDCF` | 16 | 0.7590 | **1.318** | −1.4474 | 1.925 | 66 |
| `112MSDCF` | 48 | 0.9541 | **1.048** | −2.4180 | 1.077 | 42 |
| `113MSDCF` | 48 | 0.9739 | **1.027** | −2.3609 | 1.052 | 51 |

Restated without the ladder: on `112MSDCF`, telescoping all **78** adjacent span-1 edges gives
**−3.7096%** against a direct `(0,78)` edge of **−3.7448%** — **99.0% recovery** across the whole
79-frame stack; `113MSDCF` gives **97.5%** over 62 edges. (MEASURED) `coffee-bean`'s equivalent
chain recovers **28.7–33.5%** — 28.7% by M10's published rule (1.6876 / 5.8891), 30.7% inside the
W=48 window, 33.5% against its longest direct edge `(0,82)`, which survives on only 8 tiles.

Whole-stack chain recovery, telescoping *every* span-1 edge against the longest direct edge each
stack provides — disjoint measurements, and the plainest statement of the effect (MEASURED):

| stack | j | span-1 chain % | direct `(0,j)` % | **recovery** | anchor tiles |
|---|---|---|---|---|---|
| `coffee-bean` | 82 | −1.4425 | −4.2465 | **0.3348** | 8 |
| `119MSDCF` | 32 | −0.4644 | −1.0185 | **0.4547** | 78 |
| `109MSDCF` | 21 | −1.2966 | −1.8544 | **0.6972** | 61 |
| `112MSDCF` | 78 | −3.7096 | −3.7448 | **0.9904** | 67 |
| `113MSDCF` | 62 | −2.9472 | −3.0210 | **0.9752** | 67 |

### 2.1 The three objections, closed

**"The long anchor is the wrong number, not the short edges."** `coffee-bean`'s `(0,48)` edge
survives on only 15 tiles, so this is the serious objection. It is removed by deleting the anchor
from the statistic entirely: compare two *telescoped totals* in the same window,
`R(s*) = T_W(1) / T_W(s*)`, where `s*` is the largest divisor span whose edges still carry ≥ 50
tiles. Both sides are conserved quantities that must agree; both are sums over **disjoint** edge
sets; neither touches the anchor. (MEASURED)

| stack | `s*` | tiles(1) | tiles(`s*`) | `T_W(1)` % | `T_W(s*)` % | **`1/R(s*)`** | `1/S_W(1)` |
|---|---|---|---|---|---|---|---|
| `coffee-bean` | 12 | 89 | 55 | −0.7503 | −2.3966 | **3.221** | 3.260 |
| `119MSDCF` | 16 | 92 | 84 | −0.4644 | −1.0247 | **2.213** | 2.199 |
| `109MSDCF` | 8 | 80 | 66 | −1.1004 | −1.4346 | **1.306** | 1.318 |
| `112MSDCF` | 24 | 86 | 74 | −2.3082 | −2.4320 | **1.054** | 1.048 |
| `113MSDCF` | 24 | 88 | 76 | −2.3000 | −2.3820 | **1.036** | 1.027 |

Anchor-free and anchored agree to ≤ 1.2% on every stack. The effect is **not** an artifact of weak
long edges. A second, independent check points the same way: recomputing `S_W(1)` against a
*different* disjoint anchor `T_W(W/2)` (two edges instead of one) changes it by 0.6–1.1% on four
stacks and 8.3% on `coffee-bean` — an 8% perturbation on a 226% effect. (MEASURED)

**"The harness manufactures ladders."** C3, the null. Two synthetic stacks were built by resampling
a real 112 / 113 base frame along a *planted* magnification path whose total was set to that
stack's own measured total, so the planted geometry matches the treatment in magnitude and in
per-frame displacement. Result: `S_48(1) = 1.1151` (n=79) and `1.0580` (n=63) — flat, inside the
registered `[0.85, 1.20]`, **PASS**. The same code that returns 0.31 on `coffee-bean` returns 1.06–1.12
on planted geometry. (MEASURED)

**"`wide64` reports 0 no-fit pairs, so use that."** SYNTHESIS §5 item 19 says a 0-failure config is
a suspect, not a winner, so `wide64` was scored on an independent metric — whether its ladder
agrees with `m10`'s. It does: `1/S_48(1)` = 0.972 (112) and 1.000 (113) against `m10`'s 1.048 and
1.027, both saying *no shrinkage*, while its anchor rms is 2.4–2.8× worse (8.44 / 7.33 vs 3.23 /
3.04). The conclusion survives the config change; the 0-no-fit count was not used as evidence for
anything. (MEASURED)

### 2.2 An independent probe agrees — C4, the positive control

The increment control plants a **known** magnification increment `g` on a single real
defocus-mismatched pair and measures what fraction comes back. It **never telescopes**, **never
uses an anchor**, and touches **one pair at a time**. Its measurement operation is disjoint from
the ladder's, which is what SYNTHESIS §5 item 20 demands before two numbers may be said to agree.

Median recovery over spans 1–4, same command on all four stacks (MEASURED):

| stack | `1/S_W(1)` | \|g\|=1e-4 | 2e-4 | 4e-4 | 8e-4 | 2e-3 | 4e-3 |
|---|---|---|---|---|---|---|---|
| `coffee-bean` | 3.260 | **0.529** | **0.640** | 1.020 | 0.994 | 1.015 | 0.990 |
| `119MSDCF` | 2.199 | 0.878 | 0.897 | 1.016 | 0.999 | 0.987 | 1.001 |
| `112MSDCF` | 1.048 | 0.893 | 0.938 | 0.981 | 1.002 | 0.995 | 0.997 |
| `113MSDCF` | 1.027 | 0.926 | 0.983 | 0.980 | 0.987 | 0.998 | 0.996 |

The increment probe orders the stacks **identically** to the ladder — `coffee-bean` < `119MSDCF` <
`112MSDCF` < `113MSDCF`, most shrunk first — from a disjoint measurement path. It also reproduces
fact 45 on `coffee-bean` (0.529 / 0.640 here against M10's 0.559 / 0.664, different frame and span
sample), and confirms the harness is sound at large `g` (0.990–1.001 at `|g| = 4e-3` everywhere).

### 2.3 A registered control failed. Publishing the failure.

C4 was registered with **two** clauses: recovery ≥ 0.95 at `|g| = 4e-3`, **and** recovery < 0.9 at
`|g| = 2e-4` — the latter lifted straight from fact 45. On 112 and 113 the first passed (0.997,
0.996) and **the second failed** (0.938, 0.983).

**Diagnosis, before belief:** clause two was never a control. It was a *prediction of the treatment*
registered as if it were an instrument check. Fact 45 was measured on `coffee-bean` alone, and
whether it generalises is precisely what M12 exists to test; a control may not presuppose the
answer. The repair was to run the identical command on the shrinking stacks, which turns the clause
from an assumption into the measured contrast in §2.2 — where `coffee-bean` does show the fact-45
signature and 112/113 do not, on the same code, the same day. **The instrument passed; my
registration of it was defective, and the defect is recorded here rather than quietly dropped.**

---

## 3. Deliverable 2 — is the ratio consistent between two captures of the same scene?

**Yes, tightly.** (MEASURED)

The registered statistic is `S_24(1)` averaged over each stack's **disjoint** 24-frame windows —
disjoint so the comparison carries no shared edge, and 24-frame so both stacks contribute more than
one window. The threshold was built from measurement, not chosen: pooling the within-capture spread
of 112 and 113 over their disjoint windows gives **σ_w = 0.0510** (3 d.f.), and the registered rule
is MATCHING at ≤ 2 σ_w, MATERIALLY DIFFERENT at > 3 σ_w.

| stack | windows | `S_24(1)` per window | mean | sd |
|---|---|---|---|---|
| `coffee-bean` | 4 | 0.2652 / 0.2932 / 0.3276 / 0.3069 | 0.2982 | 0.0262 |
| `112MSDCF` | 3 | 0.9100 / 0.9894 / 1.0209 | **0.9734** | 0.0572 |
| `113MSDCF` | 2 | 0.9408 / 0.9910 | **0.9659** | 0.0355 |

**|0.9734 − 0.9659| = 0.0075 = 0.15 σ_w → MATCHING.** Restricting 112 to only the two windows 113
also covers gives 0.9497, i.e. 0.32 σ_w — still matching. The ratio-of-ratios
`Q = ρ_shrink(112)/ρ_shrink(113) = 0.9923`.

This is a real and useful result on its own: **the shrinkage is a stable property of a scene, not
capture noise.** Two independent captures, one stop apart in exposure (1/60 s vs 1/30 s, both f/11
ISO 500, same lens), agree to 0.15 σ_w. Whatever produces the effect is repeatable and does not
care about a one-stop SNR change.

It is also the fact that makes §5's failure damning rather than ambiguous: the quantity is
*measurable and stable*, and it *still* does not transfer.

---

## 4. Deliverable 3 — index span or physical baseline? And a correction to fact 49

### 4.1 The 112/113 pair cannot answer this, because fact 49's premise is false

SYNTHESIS fact 49 states that 112 and 113 both sweep **0.3189 → 0.3297 m**. That figure is a decode
of EXIF `FocusPosition2`, and **`FocusPosition2` takes exactly 3 distinct values across both
stacks** — 68, 69, 70 — in runs of {15, 16, 48} on 112 and {5, 10, 48} on 113. (MEASURED) A 3-tick
encoder cannot resolve a fine focus sweep, so the endpoints agreeing establishes nothing about what
happens between them.

Measured with magnification instead of with the encoder (MEASURED):

| quantity | measured | predicted if *same interval, two densities* | predicted if *same per-frame step, 112 runs further* |
|---|---|---|---|
| `rate(112)/rate(113)` | **1.0044** | 0.7949 | 1.0000 |
| `total(112)/total(113)` | **1.2442** (direct) / 1.2636 (chain) | 1.0000 | 1.2581 |

The per-frame rate profile is flat and identical in both: −0.4846e-3/frame on 112 and
−0.4825e-3/frame on 113, uniform across the sweep in blocks of ten. The `wide64` arm agrees
(1.0225 / 1.2584). **112 and 113 share a per-frame focus step; 112 simply runs 16 frames further.**

**Consequence:** span `s` is the *same physical baseline* in both stacks, so H-index and H-phys make
**identical** predictions on this pair. The registered §2 discrimination test is **degenerate and
was not run.** The dataset's most valuable advertised property does not exist. Reporting this is not
optional — the milestone brief called this "arguably the most valuable thing in the dataset", and it
is not there.

### 4.2 What can still be tested, and its answer

Across all five stacks, both parameterisations are refuted by the same table (MEASURED):

- **H-index** (`S` is a function of frame-index span): at `s = 1`, `S` ranges **0.3067 → 0.9739**.
  Refuted.
- **H-phys / H-disp** (`S` is a function of true differential displacement `d = ρ·s·rate`, fact 45's
  parameterisation): the decisive pair is `coffee-bean` span 1 at **d = 1.081 px, S = 0.3067**
  against `112MSDCF` span 1 at **d = 1.077 px, S = 0.9541** — displacement matched to **0.3%**,
  shrinkage differing by **3.11×**. Refuted.

These two stacks are matched on nearly everything geometric: per-frame rate 0.5116e-3 vs 0.5099e-3,
total drift over the same W=48 window −2.4257% vs −2.4180%, lever arm 1205 vs 1190 plane px, same
window, same estimator, same rig. **The answer to deliverable 3 is neither.** The shrinkage is not a
function of baseline in any parameterisation; across stacks it is a function of the *scene*.

### 4.3 What does predict it? Honestly: nothing yet

Ten candidates read off the edge sets, ranked by Spearman ρ against `1/S_W(1)` over n=5 stacks
(ARGUED — n=5 makes every one of these a screening statistic, none significant alone):

| candidate | `coffee-bean` | `119` | `109` | `112` | `113` | ρ |
|---|---|---|---|---|---|---|
| **`1/S_W(1)`** | **3.260** | **2.199** | **1.318** | **1.048** | **1.027** | — |
| span-1 NCC peak | 0.9355 | 0.9138 | 0.8747 | 0.9564 | 0.9737 | −0.600 |
| peak(8)/peak(1) | 0.9638 | 0.9788 | 1.0466 | 0.9486 | 0.9392 | +0.600 |
| span-1 tiles used | 89 | 92 | 80 | 87 | 88 | +0.500 |
| span-1 fit rms px | 0.376 | 0.172 | 0.419 | 0.280 | 0.226 | +0.200 |
| per-frame rate ×1e-3 | 0.512 | 0.320 | 0.911 | 0.510 | 0.498 | +0.200 |
| `d_true(1)` plane px | 1.081 | 0.676 | 1.925 | 1.077 | 1.052 | +0.200 |

Nothing separates. The two most tempting stories both break on a single row: "noisier ⇒ more
shrinkage" is killed by `119MSDCF`, which has the **lowest** span-1 rms in the corpus (0.172) and
still shrinks 2.20×; "less inter-frame correlation ⇒ more shrinkage" has the wrong sign, since
`113MSDCF` has the **highest** span-1 NCC peak (0.9737) and the **least** shrinkage.

**The mechanism is UNVERIFIED.** M12 measured that the effect is per-scene, stable within a scene,
and not a function of baseline. It did not find the scene property responsible, and does not claim
one. Naming the culprit needs a corpus with more than five stacks and deliberate variation in
subject depth and texture — that is a capture request, not an analysis.

---

## 5. Deliverable 4 — can a correction fitted on one stack predict the other?

**No.** (MEASURED)

The registered protocol: fit `k = 1/S_{A,W}(1)` on stack A, then use it to predict stack B's own
long anchor from **B's span-1 edges alone**. A's edges and B's edges are disjoint by construction;
within B, the span-1 chain and the anchor edge are disjoint. Registered VIABLE condition:
`rel_err_corrected ≤ 0.10` **and** `≤ 0.5 ×` uncorrected. The 0.10 came from the pre-registered
6.3-plane-px budget, not from the results.

**Positive control (C7)** — a `k` fitted and tested on the same stack must be exact by construction.
Worst in-sample relative error **1.45e-16** against a 1e-9 gate. **PASS.** The fitter works; what
follows is a property of the world, not of the code.

**The registered out-of-sample test** (MEASURED):

| fit on → test on | k | uncorrected err | corrected err | gain | ≤0.10? | ≤0.5×? |
|---|---|---|---|---|---|---|
| `112MSDCF` → `113MSDCF` | 1.048 | 0.0261 | 0.0208 | 0.798 | PASS | **FAIL** |
| `113MSDCF` → `112MSDCF` | 1.027 | 0.0459 | 0.0204 | 0.444 | PASS | PASS |
| `coffee-bean` → `112MSDCF` | 3.260 | 0.0459 | 2.1106 | **45.9** | FAIL | FAIL |
| `coffee-bean` → `113MSDCF` | 3.260 | 0.0261 | 2.1753 | **83.4** | FAIL | FAIL |
| `119MSDCF` → `113MSDCF` | 2.199 | 0.0261 | 1.1419 | 43.8 | FAIL | FAIL |
| `109MSDCF` → `113MSDCF` | 1.318 | 0.0261 | 0.2832 | 10.9 | FAIL | FAIL |
| `112MSDCF` → `coffee-bean` | 1.048 | 0.6933 | 0.6785 | 0.979 | FAIL | FAIL |
| `119MSDCF` → `coffee-bean` | 2.199 | 0.6933 | 0.3255 | 0.469 | FAIL | PASS |

- **Registered 112↔113 pair: FAILS**, because it must pass in both directions and 112→113 has gain
  0.798 against the registered 0.5.
- **Cross-scene: 0 / 18 ordered pairs pass both conditions.** (MEASURED)
- **Worst case: `coffee-bean` → `113MSDCF` makes the error 83.4× worse** — 0.0261 → 2.1753. This is
  the case the project would actually ship: fit on the deep stack you have, apply to the next
  capture. It is catastrophic, and it is catastrophic in a *silent* way, since the corrected number
  looks like a correction.

### 5.1 What the correction does to a real chain — C8

Composed span-1 chain against the **direct** `(0,j)` edges, which are disjoint from every edge in
the chain. Worst plane-px corner error (MEASURED):

| stack | correction | k | worst px | median px | worst scale part |
|---|---|---|---|---|---|
| `coffee-bean` | none | 1.000 | 36.99 | 7.26 | 33.29 |
| `coffee-bean` | **self-fitted, in-sample** | 3.260 | **13.92** | 3.54 | 10.46 |
| `119MSDCF` | none | 1.000 | 12.39 | 6.63 | 11.71 |
| `119MSDCF` | self-fitted, in-sample | 2.199 | 1.64 | 1.16 | 0.95 |
| `112MSDCF` | none | 1.000 | 5.27 | 3.77 | 3.71 |
| `112MSDCF` | self-fitted, in-sample | 1.048 | **5.66** | 3.00 | 3.35 |
| `112MSDCF` | fitted on `113MSDCF` | 1.027 | 4.66 | 3.13 | 3.04 |
| `113MSDCF` | none | 1.000 | 4.09 | 2.52 | 3.40 |
| `113MSDCF` | fitted on `112MSDCF` | 1.048 | 3.26 | 1.91 | 2.25 |

Two things worth reading twice:

- On `coffee-bean`, an **oracle** correction — fitted on the very stack it is applied to, which no
  shipping pipeline can have — takes the chain from 36.99 px to **13.92 px**. That is still **2.06×
  worse than M10's global solve over direct edges (6.76 px)**, and 3.5× worse than the pre-registered
  `T_usable` of 4.0 px. **Even a perfect scalar shrinkage correction does not rescue chaining.** (DERIVED
  — 13.92 / 6.76; the 6.76 px is M10's, measured on the same 105 frames)
- On `112MSDCF`, the self-fitted correction makes the **worst** case *worse* (5.27 → 5.66 px). When
  there is no shrinkage to correct, correcting adds error.

### 5.2 Disjointness audit — C6

Required by SYNTHESIS §5 item 20 before any agreement may be quoted. (VERIFIED)

- Ladder: only `s < W` rows are used anywhere; **0** overlaps between any `T_W(s)` and the anchor
  found by audit.
- §5 transfer: `k` from stack A's edges, test on stack B's edges — disjoint for every ordered pair.
- §5.1 chain: chain uses span-1 edges `(k, k+1)`, truth uses direct edges `(0, j)` — disjoint for
  every `j ≥ 2`.
- §2.2 increment probe vs the ladder: different measurement *operations* on shared image data — the
  increment ratio is a within-pair difference under a planted perturbation and shares no fitted
  quantity with the telescoped ladder. Stated as "independent probe", not as "disjoint data".
- Graph cycle rank (project rule 6): the ladder is not a solve, so there is no training graph to be
  a tree. The §5 test compares two *conserved totals*, not a fitted pose set.

---

## 6. Deliverable 5 — the ruling

### 6.1 The registered grid

| registered question | result |
|---|---|
| §4 — do 112 and 113 match? | **MATCHING** (0.15 σ_w) |
| §5 — does the correction transfer, registered pair? | **FAILS** |
| §5 — cross-scene transfer | **0 / 18** |
| §6 outcome grid | **PARTIAL / NEGATIVE** |

Registered refutation criterion **R2** — *"a correction that does not beat doing nothing is not a
calibration"* — fires. The ruling was produced by running the registered rules mechanically, before
being written up.

### 6.2 Ruling on fact 43's open question

> **The short-baseline magnification shrinkage cannot be calibrated away by any fixed rule, because
> it is not a property of the baseline. It is a per-stack property, reproducible within a scene to
> 0.15 σ_w and varying 3.2× between scenes at matched geometry. Fitting it per stack is possible but
> pointless: an oracle in-sample correction still leaves `coffee-bean`'s chain at 13.92 px, twice
> M10's 6.76 px global solve over direct edges. There is no route from calibrated chaining to a
> usable deep-stack alignment.** (DERIVED from §2–§5, all MEASURED)

And a correction to the project's own record, stated loudly as the milestone brief requires:

> **Fact 43 is over-scoped.** "Short-baseline alignment edges under-report magnification change by
> ~3.2–3.5×" reads as a property of the estimator. It is not. The range 3.2–3.5× is `coffee-bean`
> alone; the corpus range is **1.03× to 3.26×**, and two of five stacks show **no shrinkage at all**
> at matched displacement and matched drift. The *phenomenon* is real and replicated — the
> conservation identity is violated on three of five stacks, confirmed by an independent
> non-telescoping probe — but its **magnitude is not a constant of the optics.** This is the same
> lesson as fact 48 (scale centre) and the same lesson as §4.1: most "constants" in this project are
> per-stack artifacts.

### 6.3 What project rule 6 should say

Rule 6 currently says short spans must be discarded. M12 says that is right, and says *why*, and
says the fix is not a correction factor:

- Discarding short spans stays correct — but the reason is not "they are shrunk by 3.3×". It is that
  **you cannot know in advance whether this stack is a 1.03× stack or a 3.26× stack**, and the
  cheapest available diagnostic (residual rms) has the wrong sign.
- **Add**: do not fit a shrinkage correction. It is measurable, it is stable within a scene, and it
  still does not transfer — 0/18 across scenes, up to 83.4× worse.
- **Add**: `1/S_W(1)` is worth *computing* per stack as a **diagnostic**, because it is cheap and it
  cleanly separates the stacks that can be chained (112, 113 chain at 99.0% / 97.5% recovery over
  78 and 62 edges) from those that cannot (`coffee-bean` at ~30%). Use it to decide whether a global
  solve is
  needed, not to correct anything.

---

## 7. Controls — full register

| id | what | gate | result |
|---|---|---|---|
| C1 | four known warps through the estimator on 112/113 base frames | scale err ≤ 1e-4 | worst 4.95e-5 = 0.105 plane px — **PASS** |
| C2 | reproduce M10's published `coffee-bean` ladder from M10's CSV | exact | −1.6876% / −5.8891% — **PASS** |
| C3 | synthetic null at matched planted drift, n=79 and n=63 | `S_48(1) ∈ [0.85, 1.20]` | 1.1151 / 1.0580 — **PASS** |
| C4a | planted increment recovered at `\|g\| = 4e-3` | ≥ 0.95 | 0.996–1.001 all stacks — **PASS** |
| C4b | planted increment shrunk at `\|g\| = 2e-4` | < 0.9 | 0.938 / 0.983 on 112/113 — **FAIL**, diagnosed §2.3, repaired by the four-stack contrast |
| C5 | within-capture spread, disjoint windows | defines σ_w | σ_w = 0.0510 (3 d.f.) — **PASS** |
| C6 | disjointness audit | 0 overlaps | 0 — **PASS** |
| C7 | in-sample correction positive control | rel err ≤ 1e-9 | 1.45e-16 — **PASS** |
| C8 | corrected chain vs disjoint direct edges | reported, not gated | §5.1 |
| C9 | read-only tree audit | unchanged | **PASS**, see §8 |

---

## 8. Read-only audit (C9)

Identical method before and after, byte for byte (MEASURED):

```
BEFORE                    AFTER
C:\dev\macro          : files=17449 bytes=286581830721   ==   files=17449 bytes=286581830721
D:\macro-dark-frames  : files=242   bytes=8179392512     ==   files=242   bytes=8179392512
D:\personal\macro     : files=632   bytes=18194001522    ==   files=632   bytes=18194001522
```

Two disclosures, because a clean audit line is worth nothing if the method is not stated:

1. A recount **including hidden files** (`-Force`) reports `C:\dev\macro` at 18530 files /
   286893514060 bytes. The difference is `C:\dev\macro\.git` (1023 files, 311396039 bytes), which
   the original method excluded. This is a **methodological difference in my own audit, not a change
   to the tree**: no file anywhere under `C:\dev\macro` has a modification time inside the last three
   days, and the top-level directory mtimes are three months old. (MEASURED)
2. All **242** files under `D:\macro-dark-frames` carry a same-day mtime of 08/22/2026 14:47–14:50,
   which **precedes** this session's baseline snapshot and is unchanged by it. It was not this
   milestone. (MEASURED)

M12 issued no write, move, rename or delete against any of the three roots. All output went to
`experiments/m12-shrinkage/`.

---

## 9. Toolchain gates

Run at the repo root, Rust 1.98.0 MSVC (MEASURED):

```
cargo fmt --all -- --check                              exit 0
cargo clippy --workspace --all-targets -- -D warnings   exit 0
cargo test --workspace                                  exit 0
    18 passed; 41 passed; 8 passed; 0; 0   =  67 tests, 0 failed
```

`crates/` was not touched. The experiment crate at `experiments/m12-shrinkage/` is its own
workspace and is `fmt`/`clippy`-clean on the same gates.

---

## 10. Reproducing this

```
cd experiments/m12-shrinkage
cargo build --release

# edge sets (~24 s and ~18 s on 32 cores)
./target/release/m12-shrinkage edges D:\personal\macro\112MSDCF stack-112 \
    --cfg m10,wide64 --spans 1,2,3,4,5,6,8,10,12,16,20,24,32,40,48 --direct0
./target/release/m12-shrinkage edges D:\personal\macro\113MSDCF stack-113 ...  # same flags

python m12_conserve.py   > out/conservation.txt   # C2 gate + all-stack ladders
python m12_premise.py    > out/premise.txt        # fact 49's premise
python m12_ruling.py     > out/ruling.txt         # sections A-I, the registered ruling
python m12_controls.py   > out/controls.txt       # C3, C4, wide64 arm
python m12_diagnose.py   > out/diagnose.txt       # decorrelation + candidate predictors
python m12_repair.py     > out/repair.txt         # C4 repair + anchor-free shrinkage
python m12_verify.py     > out/verify.txt         # every derived ratio quoted in this report
```

`PREREGISTRATION.md` (commit `8326564`) is the binding contract; §6's grid was applied mechanically.

---

## Proposed changes to `SYNTHESIS.md` and `AGENTS.md`

*Exact paste-able text. M12 did not edit either file.*

### A. Replace the "What remains open" block under risk 11

Everything from **"What remains open is no longer…"** to the end of the **"UPDATE — that capture
already exists (fact 49)"** paragraph should be replaced with:

> **What remains open is no longer the shrinkage.** M12 answered it: **the short-baseline shrinkage
> cannot be calibrated away** (facts 50–53). It is not a function of baseline in any
> parameterisation, it varies 3.2× between scenes at matched geometry, a fitted correction transfers
> to **0 of 18** cross-scene pairs and makes the worst case **83.4× worse**, and even an oracle
> in-sample correction leaves `coffee-bean`'s chain at **13.92 px** — twice the 6.76 px the global
> solve already achieves without any correction. **Do not fit a shrinkage correction.** The
> remaining open question is the narrower one: **does 6.76 px still matter after the depth map is
> applied?**
>
> **What is now known about the shrinkage** is that it is a **per-scene** property, reproducible
> within a scene to 0.15 σ but ranging **1.03× to 3.26×** across the five-stack corpus. Its
> mechanism is **UNVERIFIED** — no measurable property of the edge sets predicts it (fact 53). The
> useful residue is diagnostic, not corrective: `1/S_W(1)` is cheap and cleanly separates stacks that
> can be chained from stacks that cannot.

### B. Amend fact 43 — append to its "So what" column

> ***M12 rescopes this: the magnitude is not a constant of the optics.*** *"~3.2–3.5×" is
> `coffee-bean` alone. The corpus range is **1.03× to 3.26×**, and `112MSDCF` / `113MSDCF` show
> essentially none (1.048× / 1.027×) at a per-frame displacement matched to 0.3% and a total drift
> matched to 0.3%. The phenomenon is real and replicated on three of five stacks, and is confirmed
> by an independent non-telescoping probe; its size is a per-stack artifact. Same lesson as fact 48
> and §4.1.* | M10 (MEASURED); rescoped by M12 (MEASURED)

### C. Correct fact 49 — replace "both sweeping 0.3189 → 0.3297 m at 0.51 s/frame"

> both reporting **0.3189 → 0.3297 m** at 0.51 s/frame — **but that reading is a decode of
> `FocusPosition2`, which takes only 3 distinct values across both stacks, and M12 measured that they
> do *not* sample one interval at two densities (fact 50)**

And append to its "So what" column:

> ***M12 correction: the "same focus range, two densities" reading is wrong.*** *Measured by
> magnification: `rate(112)/rate(113) = 1.0044` where that reading requires 0.7949, and
> `total(112)/total(113) = 1.2442` where it requires 1.0000. They share a per-frame step; 112 runs 16
> frames further. The pair is still a genuine same-subject replicate — it is **not** an index-vs-
> physical-baseline discriminator, which is what it was recruited for.*

### D. New facts

| # | Fact | So what | Source |
|---|---|---|---|
| 50 | **`112MSDCF` and `113MSDCF` share a per-frame focus step, not a focus interval.** Measured by magnification, not by EXIF: per-frame rates **−0.4846e-3** and **−0.4825e-3** per frame (ratio **1.0044**), totals **−3.7448%** and **−3.0210%** (ratio **1.2442**). A shared interval at two densities requires rate ratio 0.7949 and total ratio 1.0000; a shared per-frame step with 112 running 16 frames further predicts 1.0000 and 1.2581. The `wide64` arm agrees (1.0225 / 1.2584). The EXIF reading behind fact 49 comes from `FocusPosition2`, which takes **3 distinct values** (68/69/70) across both stacks | **Corrects fact 49 and removes the discriminator it promised.** Span `s` is the same physical baseline in both stacks, so index-span and physical-baseline parameterisations make identical predictions on this pair and cannot be separated by it. The pair remains a valid same-subject *replicate*. **General lesson: `FocusPosition2` is a coarse encoder — never infer a fine sweep from it; measure the sweep with magnification** | M12 (MEASURED) |
| 51 | **The shrinkage does not replicate on the new stacks, and it is not a function of baseline.** `1/S_W(1)` = **3.260** (`coffee-bean`), 2.199 (`119`), 1.318 (`109`), **1.048** (`112`), **1.027** (`113`). The decisive pair: `coffee-bean` span 1 at d = 1.081 px gives S = 0.3067, `112MSDCF` span 1 at d = 1.077 px gives S = 0.9541 — displacement matched to **0.3%**, shrinkage differing **3.11×**, at matched per-frame rate (0.512 vs 0.510 e-3) and matched window drift (−2.4257% vs −2.4180%). Chaining all 78 adjacent edges on 112 recovers **99.0%** of the direct `(0,78)` edge, and 113 recovers **97.5%** over 62 edges, where `coffee-bean` recovers ~30% | **Both parameterisations are refuted.** Not frame-index span (S at s=1 ranges 0.307→0.974), not physical baseline or differential displacement (matched d, 3.11× different S). Across stacks the shrinkage is a function of the **scene**. *Anchor-free confirmation: `T_W(1)/T_W(s*)` with s* the longest span above 50 tiles reproduces it to ≤1.2% on all five stacks with no long anchor in the statistic, so it is not an artifact of weak long edges* | M12 (MEASURED) |
| 52 | **The shrinkage is stable within a scene and does not transfer between scenes.** Two independent captures of the same subject agree to **0.15 σ_w** (0.9734 vs 0.9659, σ_w = 0.0510 from disjoint within-capture windows) — even one stop apart in exposure. But a correction `k = 1/S_W(1)` fitted on one stack and tested on another's disjoint edges passes both registered conditions on **0 of 18** cross-scene ordered pairs; `coffee-bean → 113MSDCF` makes the error **83.4× worse** (0.0261 → 2.1753); the registered 112↔113 pair fails one direction. On a real chain, an **oracle in-sample** correction takes `coffee-bean` from 36.99 px to **13.92 px** — still 2.06× worse than the 6.76 px global solve — and on `112MSDCF` the self-fitted correction makes the worst case *worse* (5.27 → 5.66 px) | **This closes fact 43's open question: no. Do not fit a shrinkage correction.** Measurable and stable is not the same as transferable, and the case the project would ship — fit on the deep stack you have, apply to the next capture — is the catastrophic one. The stability result is what makes this damning rather than ambiguous. **The useful residue is diagnostic**: `1/S_W(1)` is cheap and separates chainable stacks (112/113 at 99.0% / 97.5% over 78 and 62 edges) from unchainable ones (`coffee-bean` at ~30%) | M12 (MEASURED) |
| 53 | **Nothing measurable in the edge sets predicts which stacks shrink.** Ten candidates over five stacks, best Spearman \|ρ\| = 0.600 at n=5. The two natural stories each die on one row: "noisier ⇒ more shrinkage" is killed by `119MSDCF`, which has the corpus's **lowest** span-1 rms (0.172) and still shrinks 2.20×; "less inter-frame correlation ⇒ more shrinkage" has the **wrong sign**, since `113MSDCF` has the **highest** span-1 NCC peak (0.9737) and the least shrinkage. An independent non-telescoping probe — a known increment planted on one real defocus pair, no anchor and no chain — orders all four tested stacks **identically** to the ladder and reproduces fact 45's signature on `coffee-bean` (0.529 / 0.640 at \|g\| = 1e-4 / 2e-4) while showing 112/113 near-unbiased (0.893 / 0.938) | **The mechanism stays UNVERIFIED, and the corroboration is real because the probes are independent.** Fact 45's "requires a real inter-frame content change" survives, but its *quantitative* signature is `coffee-bean`-specific like fact 43's. Naming the scene property responsible needs a corpus with more than five stacks and deliberate variation in subject depth and texture — a capture request, not an analysis | M12 (MEASURED; mechanism UNVERIFIED) |

### E. New §5 discipline items

> **21. A control may not presuppose the treatment's answer.** M12 registered its positive control
> with two clauses, one of which ("a small planted increment must recover at < 0.9", lifted from
> fact 45) was a *prediction of the treatment* wearing a control's clothes. It failed, correctly, on
> the stacks that turned out not to shrink. Ask of every registered gate: *would this still be a
> valid instrument check if my hypothesis were false?* If not, it is a hypothesis, and it belongs in
> the results.
>
> **22. State the audit method, not just the audit result.** M12's read-only tree audit matched byte
> for byte — and a recount with hidden files included differed by 1081 files, purely because the
> original command omitted `-Force`. Same tree, different method, different number. An unchanged
> count proves nothing unless the enumeration is identical and stated.
>
> **23. Reproducible is not transferable.** The shrinkage reproduces between two captures of the same
> scene to 0.15 σ and transfers to **0 of 18** cross-scene pairs. Stability within a condition is
> evidence that a quantity is *real*; it is no evidence at all that it is a *constant*. Before
> calibrating anything, test it across the axis you intend to generalise over, not the axis you
> happen to have replicates on.

### F. `AGENTS.md` rule 6 — replace the rule text

> **6. Never chain alignments, and never correct a chain instead of avoiding one.** Compose nothing;
> fit every frame against a global model over **direct** pairwise edges. Discard spans 1–2 from any
> solve, and **never judge an edge by its residual** — short baselines look best by residual while
> being worst by truth (fact 45). Any least-squares solve whose training graph is a **tree** is
> chaining in disguise; check the cycle rank. **Do not fit a span-dependent shrinkage correction**:
> it is measurable and stable within a scene yet transfers to 0/18 cross-scene pairs and makes the
> worst case 83.4× worse, and even an oracle in-sample correction leaves a chain at 2× the error the
> plain global solve already achieves (fact 52). Computing `1/S_W(1)` per stack as a **diagnostic**
> is worthwhile — it separates chainable stacks from unchainable ones — but it is a gauge, not a
> gain.
