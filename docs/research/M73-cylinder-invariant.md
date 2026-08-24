# M73 — the cylinder invariant: does the merge admit correctly on a real capture?

**Milestone:** M73. **Pre-registration:** `experiments/M73-cylinder/PREREGISTRATION.md`,
committed at **`700f87b`** before any residual, ratio or hit rate existed.
**Predecessor:** `docs/research/M67-focus-correctness.md`, which designed this
test and deliberately did not run it.

---

## 1. Headline

**The transferred prediction reproduces.** M67's simulated plant measured
`E`'s election error at **12% tighter** than `ArgmaxBaseline`'s. On two
independent real captures, under two references with opposite bias, the
tightening is **12.3% – 15.1%**. All four numbers fall inside the band
registered at `700f87b`. **M67's ordering, and its magnitude, survive contact
with real data.**

**The admission verdict is INCONCLUSIVE at the shipped gate, and it is
inconclusive for a measured reason.** On this subject `DEFAULT_GATE = 4.0`
admits **1.238 and 1.766 frames of 130 and 120** — `n_eff/N` of **0.0095 and
0.0147**, at or below the bottom of the corpus range M64 measured. The admitted
set is a **singleton at 81.4% and 58.7%** of scored pixels. There is almost no
admission behaviour on this capture to score: the shipped estimating merge is
behaving as a selector.

**Where the gate does act, M67's headline reproduces too.** In a post-hoc,
explicitly exploratory gate ladder, at `n_eff/N` matched to M67's plant
(0.2736), the admitted set brackets the column consensus at **99.499% and
99.583%** against shape-matched nulls of 9.57% and 36.93% — beside M67's
simulated **99.955%** against a null of 32.36%.

**M67's *framing* does not transfer, and the reason is measured.** M67's
load-bearing sentence is that focus correctness lives in **the gate, not the
election**: its plant's election was exactly right 39.70% of the time and its
admitted set 99.96%, a **+60.26 pp** lift. Here the election is right **76.92%
and 70.45%** of the time and the shipped gate lifts that by only **+7.04 and
+12.09 pp**. Even at M67's own `n_eff/N` the lift is **+22.58 and +29.14 pp**,
about a third of the plant's. **The gate carries real correctness, but far less
of it than the plant implies, because on a real high-contrast subject the
election is roughly twice as accurate as the plant's.**

**The specific defect this test was built to detect is absent.** No ink-phase-locked
admission bias, in either capture: `z = +1.12` (`P = 0.118`) and `z = −1.00`
(`P = 0.833`) against a null distribution over 102 incommensurate pitches. Bounded:
an ink-locked bias of amplitude greater than **0.967** and **3.029 frames** is
excluded at 3 sd.

**One registered rule was defective and is reported as such.** The registered
`H_ax` clause compared an **integer** admitted interval against a **continuous**
line fit, which a width-1 admitted set can satisfy only on a set of measure
zero. As registered it returned 14.518% and 27.937% and its registered verdict
is **DOES NOT ADMIT CORRECTLY**. That verdict is an artefact of my own
pre-registration and §6 disqualifies it with a proof that does not depend on
which way it fell.

---

## 2. Report index

| report | what this milestone took from it |
| --- | --- |
| `M67-focus-correctness.md` | the test design, its three binding requirements, the `H` and shape-matched-null construction, the transferred prediction (`E` 0.71747 vs `A` 0.81473), fact 14's rule that **`H` must never be quoted without `n_eff/N` beside it**, and fact 14a's corpus `n_eff/N` range of 0.014–0.30 |
| `M65-election-gate-measured.md` | the real-stack path this milestone's instrument is copied from: `read_dir`/ARW handling, `Pipeline::field_for`, the paired raw/regularised elections, the K1 noise-SD procedure and `k_sd`, the K2 `Estimator::mean_n_eff()` identity |
| `M64-estimator-default.md` | `Command::Stack` is the estimating merge and the default; `DEFAULT_GATE = 4.0`; `Command::ArgmaxBaseline` is the retained pure selector |
| `M62-ruling-M64.md` | guard G (`n_eff/N ≥ 0.95`) and the statement that it establishes the merge *discriminates* and **nothing** about whether the frames it admits are the right ones |
| `M63-bimodality.md` | the house form for reporting a result that goes against the milestone's own expectation |

---

## 3. What was registered, and what deviated

Everything in §5 was fixed at `700f87b`. Two things in this report were not,
and both are labelled at every point of use:

| item | status |
| --- | --- |
| arms E / A / A′, the per-column line reference, both bias directions, the scored mask, `S`, `H_ax`, `H_null`, `span`, `A_P` | **REGISTERED** |
| K1 – K3, C1 – C5, thresholds `C1 > 3`, `C2 > 10`, `C3 > 3×`, `H ≥ 0.95` / `< 0.80`, `T1 < 1.000`, `T2 ∈ [0.761, 0.940]` | **REGISTERED** |
| the repaired hit rate `P(lo − 0.5 ≤ ŵ ≤ hi + 0.5)` | **DECLARED DEVIATION**, post-hoc (§6) |
| C3's null *distribution* over 102 incommensurate pitches, replacing the single `P·√2` null | **DECLARED DEVIATION**, post-hoc; strictly more conservative than what was registered |
| the gate ladder of §8 | **EXPLORATORY**, post-hoc, not read by any decision |

---

## 4. The subject, and what was measured from it before anything was scored

Every number in this section came from image **intensity**. No focus operator
appears anywhere in its derivation, which is M67's requirement R2.

### 4.1 There is no silhouette — M67's circumferential arm is unrunnable here

Median DN above black in a 64-px border strip, against the label's own body
median, from the frame-mean green luma:

| stack | body | left | right | top | bottom |
| --- | --- | --- | --- | --- | --- |
| `wrapped-text-1` | 1457.6 | 80.9% | 130.5% | 132.3% | 127.6% |
| `wrapped-text-2` | 1810.2 | 85.8% | 141.8% | 123.7% | 111.6% |

Every border strip sits between 81% and 142% of the label body. **The label fills
the sensor edge to edge; there is no background in either capture.** M67's
circumferential arm needs a silhouette to fit `R` and `x_c`, and R2 forbids
taking that geometry from the index map instead. **M67's registered blind spot —
a bias constant in `y`, which it measured at `devmax` 8.25–8.34 frames while
`H ≈ 1` — is therefore unclosable on this data, not merely outside this
milestone's scope.**

### 4.2 The axis, from the text baselines

| stack | axis from image `+y` | text row pitch | ink fraction |
| --- | --- | --- | --- |
| `wrapped-text-1` | −0.2° | 375.2 plane px | 0.120 |
| `wrapped-text-2` | −0.2° | 469.0 plane px | 0.120 |

A second estimator — the structure tensor of the heavily low-passed frame-mean,
whose isophotes should run along a cylinder's axis — was run and **discarded**:
its anisotropy was 0.049 and 0.237, too near isotropic for the direction to mean
anything, because the label's printed layout and the scene illumination both
contribute low-frequency structure. Its marginal profiles are nonetheless
consistent with a vertical axis, with a low-frequency swing across `x` of 51.1%
and 54.5% of the body level against 14.8% and 17.3% along `y`.

### 4.3 Drift, rotation and breathing are four orders of magnitude below the signal

Phase correlation between the **first and last** frame of each bracket, in two
bands 1544 plane px apart:

| stack | translation | rotation, whole stack | `y` magnification, whole stack |
| --- | --- | --- | --- |
| `wrapped-text-1` | < 0.02 px | +0.0002° | +0.0006% |
| `wrapped-text-2` | < 0.08 px | +0.0044° | +0.0048% |

The concern that lens breathing or a frame-to-frame rotation would inject a
spurious `y`-dependence is real in principle and **absent in this data**.

---

## 5. The registered result

### 5.1 Controls

| control | `wrapped-text-1` | `wrapped-text-2` | registered | outcome |
| --- | --- | --- | --- | --- |
| **K1** regularised noise SD | 1.521409e-2 vs declared 1.521400e-2 | same | within 4 SEM | **PASS**, 0.00 SEM |
| **K1** `k_sd` = sd(raw)/sd(reg) | 1.23770 | 1.23770 | — | — |
| **K2** harness `n_eff` vs `Estimator::mean_n_eff()` | 1.238414493 = 1.238414493 | 1.765689248 = 1.765689248 | `f64` equality | **PASS** |
| **K3** admitted bounds bracket the winner | 0 of 8 241 504 | 0 of 8 241 504 | 0 violations | **PASS** |
| **C1** axis swap, must fail loudly | `S_swap/S` = **8.766×** | **4.728×** | > 3 | **PASS** |
| **C2** frame-label permutation placebo | `S_perm/S` = **47.349×** | **25.693×** | > 10 | **PASS** |

C1's absolute value is nearly identical across the two captures (`S_swap` = 5.107
and 5.027 frames) while `S` differs by 1.8×. That is the expected signature: the
swapped arm is measuring the curvature of `k*(x)` for the same bottle, and it is
the same bottle.

### 5.2 D2 — the transferred prediction: **REPRODUCES**

M67's plant: `E` 0.71747, `A` 0.81473, ratio **0.88063**, an 11.94% tightening.
Mean `\|r\|` in frames over the scored interior, both references:

| stack | reference | `S(E)` | `S(A)` | ratio | tightening | RMS ratio |
| --- | --- | --- | --- | --- | --- | --- |
| `wrapped-text-1` | ref E (favours E) | 0.58256 | 0.68575 | **0.84952** | 15.05% | 0.86832 |
| `wrapped-text-1` | ref A (favours A) | 0.61145 | 0.70961 | **0.86168** | 13.83% | 0.87289 |
| `wrapped-text-2` | ref E (favours E) | 1.06336 | 1.22749 | **0.86629** | 13.37% | 0.90825 |
| `wrapped-text-2` | ref A (favours A) | 1.10985 | 1.26498 | **0.87736** | 12.26% | 0.91212 |

* **T1 (ordering, `< 1.000`): PASS**, all four.
* **T2 (magnitude, `∈ [0.761, 0.940]`): PASS**, all four.
* **Registered outcome: REPRODUCES**, in both captures, under both references.

The primary and secondary masks are identical here: **no column** in either
capture has more than 20% bracket-boundary winners (boundary-winner pixels are
0.158% and 0.018% of the plane), so the declared secondary mask drops nothing.

The registered caveat still applies and now runs in the project's favour: any
residual common-mode geometry error is shared by both arms and compresses the
ratio *toward* 1.000, so **12.3%–15.1% is a lower bound on the true separation.**

### 5.3 D1 — admission, as registered: **DOES NOT ADMIT CORRECTLY**, and that verdict is an artefact

| | `wrapped-text-1` | `wrapped-text-2` |
| --- | --- | --- |
| `H_ax`, as registered | **14.518%** | **27.937%** |
| shape-matched null | 0.230% | 1.101% |
| registered verdict (`H < 0.80`) | DOES NOT ADMIT CORRECTLY | DOES NOT ADMIT CORRECTLY |

§6 shows this is a defect in the registered clause. It is recorded here in full
because that is what a pre-registration is for.

### 5.4 C3 — the ink-shape diagnostic: **no signature**

The defect this whole test exists to detect is a merge following ink instead of
depth, which must appear as a signed residual locked to the printed text rows.

| | `wrapped-text-1` | `wrapped-text-2` |
| --- | --- | --- |
| `A_P` at the text pitch | 0.67627 frames | 1.10081 frames |
| null over 102 incommensurate pitches | 0.50164 ± 0.15528 | 1.58151 ± 0.48243 |
| `z` | **+1.12** | **−1.00** |
| `P(null ≥ observed)` | 0.118 | 0.833 |
| correlation of the residual phase profile with the ink template's | −0.2614 | +0.4768 |

Neither reaches the registered 3× flag, the two captures disagree in sign on the
ink correlation, and the registered single-pitch null is superseded by a
distribution. **Bounded negative result: an ink-phase-locked admission bias of
amplitude greater than 0.967 frames (`wrapped-text-1`) or 3.029 frames
(`wrapped-text-2`) is excluded at 3 sd.**

### 5.5 C4 — texture stratification, and a surprise

Scored mask split into terciles of frame-mean gradient magnitude:

| stratum | stack | `S(E)` | `S(A)` | ratio | share |
| --- | --- | --- | --- | --- | --- |
| high gradient | `wrapped-text-1` | 0.48025 | 0.65333 | 0.73508 | 33.3% |
| low gradient | `wrapped-text-1` | 0.58115 | 0.61491 | 0.94511 | 33.3% |
| high gradient | `wrapped-text-2` | 0.83045 | 1.08823 | 0.76312 | 33.3% |
| low gradient | `wrapped-text-2` | 1.09036 | 1.17525 | 0.92777 | 33.3% |

Two things fall out that were not anticipated.

**The regulariser's advantage is *larger* where there is more texture**, not less
— ratio 0.735/0.763 on the high-gradient tercile against 0.945/0.928 on the low.
This is the opposite of the naive expectation and is **not further investigated**
here.

**Most of the frame carries no printed glyph and the merge does fine there
anyway.** 75.6% and 77.1% of pixels have less than 0.5% ink coverage inside the
focus operator's 27×27 window (68.8% and 70.7% inside the 43×43 effective
support after regularisation), yet `S` on the low-gradient tercile is only 1.21×
and 1.31× the high-gradient tercile's — not the order of magnitude a featureless
surface would give. **The label stock's own texture, not the print, is supplying
most of the focus signal across most of the frame.** That also explains why C3
has little to find: at the operator's scale the contrast field is not
glyph-dominated.

### 5.6 C5 — cross-stack replication

Every headline above holds in both captures. The two are the same subject at
slightly different angle and depth, so this is replication across capture
geometry, not across subject.

---

## 6. The registered `H_ax` clause is defective, and here is the proof

The pre-registration defined

```text
    H_ax = P( lo_adm ≤ ŵ ≤ hi_adm )
```

`lo_adm` and `hi_adm` are **integer** frame indices. `ŵ` is a **continuous**
OLS line. For a singleton admitted set, `lo = hi = w`, the clause requires
`ŵ = w` exactly — a set of measure zero. **The clause is therefore bounded above
by `P(span ≥ 2)`, and it measures span width rather than admission
correctness.**

That argument is analytic and does not depend on the result. The data confirms
it:

| | `wrapped-text-1` | `wrapped-text-2` |
| --- | --- | --- |
| `P(span = 1)` | 81.384% | 58.664% |
| `P(span ≥ 2)` — the hard ceiling | **18.616%** | **41.336%** |
| `H_ax` as registered | 14.518% | 27.937% |
| fraction of the ceiling attained | 0.7799 | 0.6759 |

**DECLARED DEVIATION.** The repaired clause treats frame index `k` as covering
`[k − 0.5, k + 0.5]`, which is what an integer frame index means:

```text
    H^R = P( lo_adm − 0.5 ≤ ŵ ≤ hi_adm + 0.5 )   ≡   P( lo_adm ≤ round(ŵ) ≤ hi_adm )
```

| | `wrapped-text-1` | `wrapped-text-2` |
| --- | --- | --- |
| `H^R(E)`, ref E | **83.959%** | **82.539%** |
| `H^R(E)`, ref A | 82.007% | 80.679% |
| `H^R(A′)`, ref E | 81.487% | 78.878% |
| `H^R(A′)`, ref A | 79.870% | 77.403% |
| shape-matched null | 1.003% | 1.948% |
| margin over null | **+82.96 pp** | **+80.59 pp** |

`E` beats `A′` under **both** references, so that ordering is not a reference
artefact. Against the registered bands the repaired statistic lands at
**83.96% and 82.54%**, i.e. in the registered **INCONCLUSIVE** interval
`[0.80, 0.95)`. **The registered bands are not moved.**

This is post-hoc and carries less evidential weight than the registered
statistic. It is reported because the registered statistic is provably not
measuring the registered quantity, and reporting only the artefact would be the
worse error.

Residual distributions, for scale:

| | `\|r\| ≤ 0.5` | `\|r\| ≤ 1` | `\|r\| ≤ 2` | `\|r\| ≤ 5` |
| --- | --- | --- | --- | --- |
| `wrapped-text-1`, E | 76.92% | 93.96% | 97.19% | 98.71% |
| `wrapped-text-1`, A | 72.98% | 92.43% | 96.51% | 98.16% |
| `wrapped-text-2`, E | 70.45% | 86.19% | 91.28% | 96.71% |
| `wrapped-text-2`, A | 64.25% | 83.89% | 90.56% | 95.98% |

---

## 7. The per-column line fit was load-bearing, not cosmetic

§2.3 of the pre-registration chose to remove a **line** in `y` rather than a
constant, registered before any winner map was scored, to absorb axis-angle
error, taper and rotation. What it bought:

| | `wrapped-text-1` | `wrapped-text-2` |
| --- | --- | --- |
| median column slope | +4.055e-3 frames/px | +5.203e-3 frames/px |
| end-to-end swing over 2299 rows | **+9.323 frames** | **+11.962 frames** |
| `S(E)`, line fit | 0.58256 | 1.06336 |
| `S(E)`, constant fit | 2.54724 | 3.49468 |
| inflation | **4.373×** | **3.286×** |
| ratio `S(E)/S(A)`, line fit | **0.84952** | **0.86629** |
| ratio `S(E)/S(A)`, constant fit | **0.97413** | **0.96837** |

The bottle's axis is not in the image plane: there is a real, systematic
depth trend of **9.3 and 12.0 frames** from the top of the frame to the bottom.
That is 31× larger than the 0.30 frames a 0.2° in-plane axis error would inject,
and 16× larger than `S(E)` itself.

**The consequence is decisive.** A constant-fit version of this test — the
obvious way to write it — would have returned ratios of **0.974 and 0.968**,
outside T2's registered band, and would have reported *"ordering transfers,
magnitude does not"*, understating M67's effect by roughly a factor of five. The
common-mode geometry term does exactly what §5.2's registered caveat says it
does: it compresses the ratio toward 1.000. **The line fit is the difference
between a working instrument and a swamped one, and it was registered before the
data could influence it.**

---

## 8. The gate ladder — EXPLORATORY, post-hoc, no decision reads it

At the shipped gate this subject barely admits, so a report that merely asserted
"the gate is nearly inert here" would be asserting rather than showing. The
ladder shows it. **Choosing an operating gate from this curve would be exactly
the circularity the pre-registration forbids; the whole curve is reported and no
point on it is picked.**

`wrapped-text-1`, K = 130, election exact-index 76.92%:

| gate | `n_eff` | `n_eff/N` | `H^R` | null | margin | mean span | lift over the election |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1.060 | 0.00815 | 78.894% | 0.833% | +78.06 pp | 1.078 | +1.98 pp |
| 2 | 1.119 | 0.00860 | 80.704% | 0.894% | +79.81 pp | 1.154 | +3.79 pp |
| **4** | **1.231** | **0.00947** | **83.959%** | **1.012%** | **+82.95 pp** | **1.299** | **+7.04 pp** |
| 8 | 1.456 | 0.01120 | 88.943% | 1.223% | +87.72 pp | 1.584 | +12.03 pp |
| 16 | 1.939 | 0.01491 | 94.366% | 1.663% | +92.70 pp | 2.180 | +17.45 pp |
| 32 | 3.133 | 0.02410 | 97.811% | 2.750% | +95.06 pp | 3.647 | +20.90 pp |
| 64 | 11.494 | 0.08842 | **99.499%** | 9.566% | +89.93 pp | 12.795 | +22.58 pp |

`wrapped-text-2`, K = 120, election exact-index 70.45%:

| gate | `n_eff` | `n_eff/N` | `H^R` | null | margin | mean span | lift over the election |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1.189 | 0.00991 | 74.267% | 1.131% | +73.14 pp | 1.290 | +3.82 pp |
| 2 | 1.381 | 0.01151 | 77.528% | 1.416% | +76.11 pp | 1.556 | +7.08 pp |
| **4** | **1.744** | **0.01453** | **82.539%** | **1.950%** | **+80.59 pp** | **2.054** | **+12.09 pp** |
| 8 | 2.480 | 0.02067 | 88.820% | 3.066% | +85.75 pp | 3.051 | +18.37 pp |
| 16 | 5.802 | 0.04835 | 94.955% | 6.868% | +88.09 pp | 7.083 | +24.51 pp |
| 32 | 18.270 | 0.15225 | 98.617% | 18.153% | +80.46 pp | 19.937 | +28.17 pp |
| 64 | 41.190 | 0.34325 | **99.583%** | 36.931% | +62.65 pp | 42.337 | +29.14 pp |

Three things read off this, all of them beside `n_eff/N` as M67's fact 14
requires:

1. **At `n_eff/N` matched to M67's plant, M67's headline reproduces on real
   data.** `wrapped-text-2` at gate 64 sits at `n_eff/N` = 0.343 with
   `H^R` = 99.583% against a null of 36.93%; M67's plant sat at 0.2736 with
   `H` = 99.955% against a null of 32.36%. **The nulls agree as closely as the
   hit rates do**, which is what a size-driven comparison should look like.
2. **The margin over the null peaks and then falls** — +95.06 pp at gate 32 for
   `wrapped-text-1`, +88.09 pp at gate 16 for `wrapped-text-2` — as the growing
   set lets the blind guess catch up. This is the same power collapse M67
   measured at its degenerate cells, approached from below rather than above.
3. **Reaching M67's regime on this subject needs a gate of about 64**, sixteen
   times the shipped `DEFAULT_GATE`.

---

## 9. What this says about M67, precisely

**Confirmed.** The transferred quantitative prediction — `E`'s election error
~12% tighter than `ArgmaxBaseline`'s — reproduces on two real captures at
12.3%–15.1%, under two references with opposite bias, with a registered band
fixed in advance. That is a simulated prediction surviving transfer to real data,
which is the thing plants exist to earn and rarely do.

**Confirmed, exploratorily.** `H` near unity at matched `n_eff/N`: 99.499% and
99.583% against 99.955%.

**Not transferred: the framing.** M67's load-bearing sentence is that focus
correctness lives in *the gate, not the election*. On these captures:

| | M67's plant | `wrapped-text-1` | `wrapped-text-2` |
| --- | --- | --- | --- |
| `n_eff/N` at the operating gate | 0.2736 | 0.0095 | 0.0147 |
| election exactly right | 39.70% | **76.92%** | **70.45%** |
| admitted set contains the reference | 99.96% | 83.96% | 82.54% |
| **gate's lift over the election** | **+60.26 pp** | **+7.04 pp** | **+12.09 pp** |
| gate's lift at matched `n_eff/N` | — | +22.58 pp | +29.14 pp |

**The election on a real high-contrast subject is roughly twice as accurate as
on M67's plant, and the gate correspondingly has much less left to add.** At the
shipped gate it adds 7–12 points; even opened to M67's own set size it adds
23–29, about a third of the plant's 60.

This is **not** a refutation of M67's measurement, which stands on its own plant.
It is a demonstration that the *regime* the plant chose — an election wrong 60%
of the time — is not the regime a real capture of a textured subject occupies,
and that M67's headline sentence is regime-dependent in a way its report does
not say.

**Two comparability limits on the paragraph above, stated so it is not read
further than it goes.** My reference is a per-column line fitted to `win_E`, not
a true `k*`; it favours `E`, and the exact-index rates under ref A (75.03% /
68.48% for `E`, 71.46% / 62.77% for `A`) are the bracketing figures. And an
exact-index rate against a smooth column consensus is not the same object as an
exact-index rate against a plant's `k*`. The two quantities that **are**
directly comparable across the studies are `n_eff/N`, which is reference-free,
and the within-study **lift**, which is a difference taken against the same
reference in each study. Both disagree with the plant by a wide margin.

---

## 10. Verdict

**On whether the merge admits correctly on real captures, scoped exactly as far
as the invariant supports:**

> On two real captures of text wrapped around a bottle, the shipped estimating
> merge's admitted-frame field shows **no admission error that varies along the
> cylinder axis beyond what the instrument's own floor explains**, and in
> particular **no ink-phase-locked bias** — the specific contrast-driven defect
> this test was built to detect — bounded at amplitude 0.967 and 3.029 frames at
> 3 sd. The admitted set brackets the column consensus at 83.96% and 82.54% of
> scored pixels against shape-matched nulls of 1.00% and 1.95%.
>
> **This does not certify the merge.** By the bands registered at `700f87b` the
> result is **INCONCLUSIVE**, and it is inconclusive for a measured reason
> rather than for want of data: at `DEFAULT_GATE = 4.0` this subject admits
> `n_eff/N` = 0.0095 and 0.0147, the admitted set is a singleton at 81.4% and
> 58.7% of pixels, and **admission correctness collapses into election
> correctness because there is barely any admission**. The merge is running as a
> selector on this subject.
>
> The verdict is a statement about **self-consistency with an assumed
> cylindrical geometry along one image axis**. It is not a statement about
> absolute depth accuracy, and it is blind to any admission error that is
> constant **or linear** in `y` within a column.

**On the transferred prediction:** **REPRODUCES.** `S(E)/S(A)` = 0.84952 /
0.86168 (`wrapped-text-1`) and 0.86629 / 0.87736 (`wrapped-text-2`), against
M67's 0.88063; all four inside the registered `[0.761, 0.940]`. M67's result is
**not** refuted; it is confirmed, and by a route that could have refuted it.

**On whether the instrument works on this data:** **it works, on one axis, with a
smaller reach than M67 expected.** The axial arm has power — C1 8.77×/4.73×, C2
47.3×/25.7×, nulls at 1.0%/1.9% — and it answered the question it was built to
answer. The circumferential arm is **dead on this subject** for want of a
silhouette, and with it dies any hope of closing M67's constant-in-`y` blind
spot on this capture.

---

## 11. Candidate facts

Numbered `P1…` locally. **These are proposals for the corpus, not corpus
numbers**: facts, disciplines and questions share one integer space in
`SYNTHESIS.md` and every number below is a *local* label with no global meaning
until folded.

**P1 (MEASURED).** M67's transferred prediction reproduces on real captures.
Mean `\|`winner − per-column line`\|`, in frames, over the scored interior of two
`wrapped-text` brackets: `S(E)/S(A)` = **0.84952** and **0.86168**
(`wrapped-text-1`, references fitted to `win_E` and to `win_A` respectively) and
**0.86629** and **0.87736** (`wrapped-text-2`), against M67's simulated
**0.88063**. All four inside the band `[0.761, 0.940]` registered at `700f87b`
before any result existed. *Provenance: M73 §5.2; `experiments/M73-cylinder/out/03-score.json`.*

**P2 (MEASURED).** On a high-contrast textured subject the shipped merge barely
admits. `DEFAULT_GATE = 4.0` gives `n_eff` = **1.238** of 130 and **1.766** of
120 frames, `n_eff/N` = **0.0095** and **0.0147**, with the admitted set a
**singleton at 81.4% and 58.7%** of scored pixels. M64's PR3 corpus range is
0.014–0.30 with `foam` at 0.0136, so `wrapped-text-1` sits **below** the measured
corpus range. *Provenance: M73 §1, §8; `out/s1.json`, `out/s2.json`.*

**P3 (MEASURED).** M67's `H` reproduces on real data once `n_eff/N` is matched.
On an exploratory gate ladder, `wrapped-text-2` at gate 64 reaches `n_eff/N`
= 0.343 with a repaired hit rate of **99.583%** against a shape-matched null of
**36.93%**; `wrapped-text-1` at gate 64 reaches 0.0884 with **99.499%** against
**9.57%**. M67's plant: 99.955% against 32.36% at `n_eff/N` = 0.2736.
*Provenance: M73 §8, EXPLORATORY and post-hoc; `out/05-ladder.json`.*

**P4 (MEASURED).** M67's framing — *"focus correctness lives in the gate, not
the election"* — is regime-dependent and does not hold at the shipped gate on a
real capture. The gate's lift over the election is **+7.04 pp** and **+12.09 pp**
here, against M67's plant's **+60.26 pp**; even at M67's own `n_eff/N` it is
**+22.58 pp** and **+29.14 pp**. The election itself is exactly right **76.92%**
and **70.45%** of the time (75.03% / 68.48% under the reference that favours
`ArgmaxBaseline`) against the plant's **39.70%**. *Provenance: M73 §9.*

**P5 (MEASURED).** The `wrapped-text` captures carry **no silhouette**: every
64-px border strip sits at 81–142% of the label body median in both stacks.
M67's circumferential arm cannot be run on them, and M67's registered
constant-in-`y` blind spot — its own `devmax` 8.25–8.34 frames at `H ≈ 1` — is
**unclosable on this subject**, not merely out of scope. *Provenance: M73 §4.1;
`out/01-geometry.json`.*

**P6 (DERIVED).** M67's stated invariant is too broad. It holds for a **right
circular cylinder**, not for "any surface of revolution": with profile radius
`r(s)` varying along the axis, nearest-point depth is `z₀ − r(s)`, which varies
with `s`. What is required is local axial translation invariance of the profile.
A taper therefore appears as a smooth low-order-in-`y` term rather than as
nothing. *Provenance: M73 pre-registration §2.1, `700f87b`.*

**P7 (MEASURED).** The `wrapped-text` bottle's axis is well out of the image
plane: the per-column depth trend is **+9.32** and **+11.96 frames** from the top
of the frame to the bottom (median column slope 4.055e-3 and 5.203e-3
frames/px over 2299 rows). This is 16× `S(E)` itself and 31× what a 0.2° in-plane
axis error would inject. *Provenance: M73 §7; `out/06-detrend.json`.*

**P8 (MEASURED).** Removing a per-column **constant** instead of a **line** would
have broken this test. Constant-fit ratios are **0.97413** and **0.96837** —
outside the registered `T2` band — against 0.84952 and 0.86629 for the line fit,
with `S(E)` inflated 4.37× and 3.29×. A common-mode geometry term compresses an
`E`-over-`A` ratio toward 1.000, here by a factor of about five in effect size.
*Provenance: M73 §7.*

**P9 (DISCIPLINE, ARGUED).** **A containment test between an integer set and a
continuous reference must widen the set by half a unit, or it measures set width
instead of containment.** M73's registered `H_ax = P(lo ≤ ŵ ≤ hi)` compared an
integer admitted interval against an OLS line and was therefore bounded above by
`P(span ≥ 2)`; it attained 0.78 and 0.68 of that ceiling and returned 14.5% and
27.9% where the repaired rule returns 84.0% and 82.5%. The defect is provable
analytically, without reference to the result. *Provenance: M73 §6.*

**P10 (MEASURED).** No ink-phase-locked admission bias is present in either
capture. Signed residual folded at the measured text row pitch gives `z` = +1.12
(`P` = 0.118) and −1.00 (`P` = 0.833) against a null distribution over 102
incommensurate pitches, with the ink correlation disagreeing in sign between
captures (−0.26, +0.48). Bounded: amplitude greater than **0.967** and **3.029
frames** excluded at 3 sd. *Provenance: M73 §5.4; `out/04-repair.json`.*

**P11 (MEASURED).** On a printed label at macro magnification the **stock, not
the print, carries most of the focus signal**. 75.6% and 77.1% of pixels have
under 0.5% ink coverage inside the focus operator's 27×27 window (68.8% and
70.7% inside the 43×43 effective support), yet mean `\|r\|` on the lowest
gradient tercile is only **1.21×** and **1.31×** the highest tercile's, not the
order of magnitude a featureless surface would give. *Provenance: M73 §5.5.*

**P12 (MEASURED, unexplained).** The regulariser's advantage over the raw argmax
is **larger** where there is more texture, not less: `S(E)/S(A)` = **0.735** and
**0.763** on the highest gradient tercile against **0.945** and **0.928** on the
lowest. This is the opposite of the naive expectation and M73 did not
investigate it. *Provenance: M73 §5.5.*

**P13 (MEASURED).** The `wrapped-text` brackets are exceptionally stable:
translation under 0.02 and 0.08 plane px, rotation +0.0002° and +0.0044°, and
`y` magnification +0.0006% and +0.0048% **across an entire 130- or 120-frame
bracket**, measured by phase correlation between first and last frame in two
bands 1544 px apart. Lens breathing is not a confound on this rig.
*Provenance: M73 §4.3; `out/02-drift.json`.*

**P14 (DISCIPLINE, ARGUED).** **Fit the nuisance geometry as a low-order function
and remove it, rather than estimating a geometric parameter and scoring residuals
about it.** M73 registered a per-column line rather than fitting an axis angle,
which removed the last tunable parameter from the test: no angle can be chosen to
improve the result because no angle enters. §7 shows the removed term was 16×
the residual being measured. *Provenance: M73 pre-registration §2.3 at `700f87b`,
result §7.*

---

## 12. Outside my charter — flagged, unruled

1. **There appears to be no acceptance guard for a gate that is too *narrow*.**
   M62's guard G fails a run when `n_eff/N ≥ 0.95` — too wide. At `n_eff/N` =
   0.0095 the shipped estimator is admitting 1.24 of 130 frames and is
   functionally a selector, which is the defect `strehl stack` was replaced to
   fix. Whether that warrants a lower guard is **not mine to rule**, and I did
   not measure image quality at either end.
2. **`DEFAULT_GATE = 4.0` may be badly matched to high-contrast subjects.** §8's
   ladder shows this subject needs about 16× the shipped gate to reach the set
   size M67's plant used. M65's question 90 already records the gate as
   uncalibrated. I am not proposing a value and I did not measure one.
3. **`corpus_lint` currently FAILs on a file I must not touch.**
   `docs/research/M70-through-focus-spectrum.md:740` has an S1 violation — a
   table row with 7 unescaped pipes against a 5-column header, discarding 2
   cells at render. M70 is live in that file; the violation is pre-existing,
   tracked at `a384682`, and none of my own files contribute a violation.
   Flagged for M70 or for the owner, not repaired by me.
4. **`wrapped-text-1` sits below the corpus `n_eff/N` range** M64's PR3 measured
   (0.014–0.30). Whether the range should be restated is the corpus owner's call.

---

## 13. What I deliberately did not measure

1. **The circumferential arm.** Unrunnable: no silhouette (§4.1), and M67's R2
   forbids fitting the geometry from the index map instead. M67's
   constant-in-`y` blind spot stays open, and on this subject it cannot be
   closed at all.
2. **Any admission error constant or linear in `y` within a column.** Removed by
   design (§7) to buy immunity from axis error, taper and rotation. This is an
   additional blindness beyond M67's and it is not small: §7 shows the removed
   linear term is 16× the residual retained.
3. **Absolute depth accuracy.** Impossible without a true `k*`. A merge uniformly
   8 frames wrong in a column scores `S = 0` here, which is exactly M67's
   measured degenerate mode.
4. **Through-focus curve shape or asymmetry.** M70's territory; SYNTHESIS fact
   1006 records that no corpus fact establishes asymmetry. Nothing here is built
   on either answer.
5. **The winner's focus-response magnitude and peak sharpness**, which would
   explain *why* `n_eff` is 1.24 on this subject rather than merely establishing
   that it is. That needs a per-pixel response dump the instrument does not take.
6. **Image quality of the merged output.** This milestone scores index fields
   only. Whether a merge admitting 1.24 frames produces a worse image than one
   admitting 12 is unmeasured, and it is the question P2 and §12.1 actually
   raise.
7. **Any gate other than `DEFAULT_GATE` in a decision.** §8's ladder exists and
   is reported in full precisely so that no point on it is picked.
8. **The other five corpus stacks.** Only `wrapped-text` carries the invariant;
   nothing here generalises to a subject that is not a surface of revolution.

---

## 14. Reproduction

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cargo build --release --example m73-cylinder      # must print `Compiling`

.\target\release\examples\m73-cylinder.exe --dir "D:\personal\macro\wrapped-text-1" `
  --out experiments\M73-cylinder\out\s1
.\target\release\examples\m73-cylinder.exe --dir "D:\personal\macro\wrapped-text-2" `
  --out experiments\M73-cylinder\out\s2

$env:PYTHONIOENCODING='utf-8'
python -X faulthandler experiments\M73-cylinder\src\01-geometry.py   # geometry, intensity only
python -X faulthandler experiments\M73-cylinder\src\02-drift.py      # drift and rotation
python -X faulthandler experiments\M73-cylinder\src\03-score.py      # the REGISTERED scoring
python -X faulthandler experiments\M73-cylinder\src\04-repair.py     # the declared deviation
python -X faulthandler experiments\M73-cylinder\src\05-ladder.py     # the exploratory ladder
python -X faulthandler experiments\M73-cylinder\src\06-detrend.py    # line vs constant
```

Wall clock is 30 s per stack for the instrument (115 ms/frame per pass, two
passes) and a few minutes for the scoring. `D:\personal\macro` is read-only and
is never written to. The `.bin` dumps total about 700 MB and are not committed;
`out/*.json` holds every number quoted above.
