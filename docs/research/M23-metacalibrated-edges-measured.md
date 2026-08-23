# M23 — can a per-edge response calibration rescue the short alignment edges?

> ## ⚠ NOT INDEPENDENTLY VERIFIED
>
> Every number in this document was produced by the agent that wrote it. Rule 12 says the author
> never verifies their own work, so **nothing here is verified**. It is written to be attacked:
> each claim names the script, the data and the command that produced it, and each gate states what
> reading would have falsified it. The scripts are committed, including one whose first version was
> wrong (§9.1).

**Status:** measured. **The answer is no, and the reason kills the premise rather than the
implementation.** R4 ships nothing.

**Milestone:** M23, research/measurement. Nothing here ships code into `crates/`.
**Experiment:** `experiments/m23-metacal/`.
**Pre-registration:** `experiments/m23-metacal/PREREGISTRATION.md`, commit **`f1be27f`**, committed
before any number in `out/` existed.
**Harness:** verbatim copy of `experiments/m12-shrinkage/` (itself a verbatim copy of M10's), plus
one added Rust mode. M10's and M12's directories were not modified.
**Reproduce:** `experiments/m23-metacal/run-m23.ps1`.

Claim labels, as in M15. `MEASURED` = a number this milestone produced. `DERIVED` = follows from a
stated rule applied to measured numbers. `ARGUED` = a mechanism I believe and have not isolated.

---

## 1. The one-paragraph answer

The per-edge response `R` **does** read far below 1 on exactly the edges that shrink — `0.526` on
`coffee-bean` span-1 at `δ = 1e-4`, against `0.897` on the placebo stack. That looks like the
signal R4 wants. It is not. Two controls that were **not** in the original plan show why: the same
probe on a frame measured **against itself** — zero defocus difference — reads `R = 0.372`, *further*
from 1 than any real pair; and the same probe with the bilinear resampler removed entirely reads
`R = 0.965`. The deficit tracks the **resampler**, not the defocus. `R` also fails its own
pre-registered linearity test by 3.1× the threshold. Gate (a) is PARTIAL and the shuffled-`R` null
reproduces 93.3% of that movement with zero per-edge information. Gate (b) passes. Gate (c) — the
only gate that ships anything — **fails**: held-out error is unchanged at **6.758 px**, and on the
one training arm where the correction does help a lot, both nulls help *more*.

---

## 2. Pre-registered criteria — stated before any result below

Reproduced from `PREREGISTRATION.md` (`f1be27f`). Nothing in this section was written after a
number was read.

**Definitions.** Estimator returns `a = (1+g) + i·rot`; measured log-scale `L_e = log|a_e|`. Plant
`W(δ) = Fit{g: δ}` on the moving frame via `warp_known` (bilinear). Increment
`I_± = F_± ∘ F_0^{-1}`; `ℓ_± = log|a(I_±)|`. Primary estimator, two-sided:

```
R_e(δ) = (ℓ_+ − ℓ_−) / (log(1+δ) − log(1−δ))          corrected:  L'_e = L_e / R_e
```

**Failure direction of `R` (rule 18).** `R` is a slope, unbiased at `1.000`. `R < 1` = the
estimator under-reports the planted increment. `R` is a ratio of two small numbers, so its
per-edge noise is unbounded near zero, and `E[1/R] > 1/E[R]` for any `R` with variance — **a noisy
`R` inflates a corrected magnitude even when it carries no information at all.**

**Registered δ ladder** `{1e-4, 2e-4, 4e-4, 8e-4, 1.6e-3}`, **primary δ = 2e-4**. The ladder is a
test of the local-linearity premise, not a tuning sweep.
**Registered refutation criterion:** if `|median R(1e-4) − median R(8e-4)|` on `coffee-bean` span-1
exceeds **0.15**, local linearity is refuted and that is the headline regardless of the gates.

**Gate (a) — conservation.** M12's statistic unchanged: `1/S_W(1) = A_W / T_W(1)`, `W = 48`.
PASS if `|1/S' − 1| ≤ 0.15`; PARTIAL if `1/S' ≤ 2.13` but outside the band; FAIL otherwise
including overshoot below 0.85. *Failure direction: `1/S → 1` is manufactured by anything that
inflates span-1 magnitudes, so gate (a) is inadmissible alone and is scored only jointly with N1.*

**Gate (b) — placebo.** PASS if `median R` over `112MSDCF` spans 1–2 at the primary δ lies in
**[0.90, 1.10]** *and* the correction moves its `1/S_W(1)` by **< 0.10**. *Admissible only if the
positive control fires: `coffee-bean` span-1 at `δ = 1e-4` must read `R < 0.90` on the same code
and the same day.*

**Gate (c) — the only gate that ships anything.** M10's harness and test set unchanged:
`coffee-bean`, `cfg = m10`, test = every direct edge with `span ≥ 40` and `≥ 12` tiles. Baseline
**6.758 px**, recomputed here rather than quoted. PASS if a full-coverage strategy trained on a set
**including corrected spans 1–2** scores below `6.758 − 0.40 = 6.36 px`. *Failure direction: larger
is worse; margin set above M10's runner-up spread so a win cannot be a scan artefact.*

**Nulls.** N1 shuffled `R` (destroys per-edge correspondence, preserves the marginal). N2 constant
`R` = group median (**this is literally the scalar M12 refuted**). N3 self-pair (destroys the
defocus difference only). N4 resampler-free field.

**Rule-17 shared-path statement.** Gate (a) bins `L'` against the anchor `A_W`, and `L'`, `L` and
`R` all come from the same estimator on the same two frames. The mechanism that could drive both is
**tile dropout and per-edge noise**: a noisy `R` inflates `L/R` with no information. N1 breaks that
path and nothing else.

**Registered author predictions** (scored in §8): (1) `R` materially δ-dependent; (2) gate (b)
passes; (3) gate (a) PARTIAL not PASS; (4) gate (c) fails; (5) N1 restores conservation nearly as
well as measured `R`; (6) N3 reads closer to 1 two-sided than M10's one-sided resample arm.

---

## 3. Does M12 already refute R4? — answered before measuring, and the answer is no

**No, and the distinction is real** (ARGUED, from reading `M12-shrinkage-measured.md` §2.2–§2.3).
M12 refuted a **transfer**: a scalar `k = 1/S_W(1)` fitted on one stack and applied to a *different*
stack, which failed 0 of 18 cross-scene pairs (fact 52). R4 transfers nothing — `R` is measured on
the identical two frames whose edge it corrects, same run, same estimator, same tile set.

**But M12's own §2.2 C4 control already bounded R4 before this milestone ran, and that bound was
pre-registered so it could not be presented later as a discovery.** C4 is already a per-edge,
self-measured response, used as a diagnostic rather than a correction: `0.529` at `|g| = 1e-4`,
`0.640` at `2e-4`, rising to `1.020 / 0.994 / 1.015 / 0.990` at `4e-4 / 8e-4 / 2e-3 / 4e-3`.
Dividing by the most favourable of those inflates a span-1 log-scale by at most `1/0.529 = 1.89×`
against the `3.26×` the conservation identity needs. **DERIVED, pre-registered: R4 cannot close the
conservation gap at any plant size M12 tested.** §5 measures `1.90×` and confirms it.

M12 does not refute R4. It bounds gate (a). Gate (c) is independent of that bound, so the milestone
was worth running — and §4 found something M12 did not.

---

## 4. What was measured, on what

All arms: `cfg = m10`, green plane 3516×2344, 32 logical cores.
**Read-only audit** (rule 14, `Get-ChildItem -Force`), before and after, byte-identical:

```
C:\dev\macro       : 18530 files, 286893514060 bytes
D:\personal\macro  :   632 files,  18194001522 bytes
```

| arm | data | pairs × δ | fits | wall |
|---|---|---|---|---|
| `coffee-bean` spans 1,2,8,16,32,48 | `C:\dev\macro\test\coffee-bean`, 105 | 523 × 5 | 5753 | **93.0 s** |
| `112MSDCF` same spans | `D:\personal\macro\112MSDCF`, 79 | 367 × 5 | 4037 | **66.7 s** |
| `cb-self` (N3) frame *k* vs itself | coffee-bean | 52 × 5 | 572 | **10.4 s** |
| `cb-self-ped` (N3b) self + 4e-3 pedestal | coffee-bean | 52 × 5 | 572 | **10.3 s** |
| `cb-ped` real pairs + 4e-3 pedestal | coffee-bean | 52 × 5 | 572 | **10.3 s** |
| `cb-field` (N4b) synthetic field, no resampler | — | 12 reps × 5 | — | **207.7 s** |

**Reproduction gate G0** (MEASURED, `m23_conserve.py`): this milestone's own base fit `log|a|`
against the committed edge CSVs, span-1, both stacks — max deviation **5.3e-10** (coffee-bean
5.282e-10, 112MSDCF 5.297e-10). Same deterministic computation, so anything else would have meant
the harness moved. **PASS.**

**Reproduction gate G1** (MEASURED, `m23_conserve.py`): uncorrected `1/S_48(1)` on `coffee-bean` =
**3.2604**, against M12's published **3.260**. **PASS.**

**Reproduction gate G2** (MEASURED, `m23_heldout.py`): M10's baseline recomputed through M10's own
`train_sets` / `strategies` / `score`, imported unmodified — **6.758 px**, `S4-poly6` trained on
`span ≥ 32`, 35 test edges at span ≥ p75. Identical to the published figure. **PASS.** *This is a
consistency check, not independent evidence* (discipline 34): the same code reproducing its own
number proves the plumbing, not the physics.

---

## 5. The response `R`, and the pre-registered criterion it fails

**MEASURED** (`m23_response.py` → `out/response.txt`), median two-sided `R`:

| arm | δ=1e-4 | 2e-4 | 4e-4 | 8e-4 | 1.6e-3 |
|---|---|---|---|---|---|
| `coffee-bean` span 1 | **0.526** | 0.613 | 0.989 | 0.993 | 1.016 |
| `coffee-bean` span 2 | 0.571 | 0.662 | 0.974 | 0.997 | 1.012 |
| `112MSDCF` span 1 | 0.897 | 0.954 | 0.982 | 0.990 | 0.994 |
| `112MSDCF` span 2 | 0.966 | 0.986 | 0.988 | 0.998 | 0.994 |

**Positive control FIRES** (MEASURED): `coffee-bean` span-1 at `δ = 1e-4` reads **0.5264**, below
the registered 0.90. Every null below therefore has a known-real signal to be read against.

### 5.1 The registered δ-dependence criterion is refuted, by 3.1×

**MEASURED.** `median R(1e-4) = 0.5264`, `median R(8e-4) = 0.9928`, `|diff| = **0.4664**` against a
registered threshold of **0.15**.

> **Fact 170 (MEASURED).** The per-edge metacalibration response on `coffee-bean` span-1 edges is
> **0.5264 at δ=1e-4 and 0.9928 at δ=8e-4** — a swing of **0.4664**, 3.1× the pre-registered
> refutation threshold of 0.15. **Metacalibration's local-linearity premise is refuted on this
> data**: there is no single `R` that characterises an edge, so the identity `L' = L/R` holds at no
> `δ`. This alone is sufficient to reject R4, before any gate is scored.

Note the structure: `R → 1` as the plant grows. A response that approaches 1 as the probe gets
*larger* is the signature of a **probe-size-dependent artefact**, not of a scene property. The
scene's defocus asymmetry does not know how big the plant is.

### 5.2 Two-sided is doing its job, and it is not enough

**MEASURED** (`out/response.txt`). One- vs two-sided on `coffee-bean` span-1: at `δ=1e-4`,
`R⁺ = 0.440`, `R⁻ = 0.599`, `R² = 0.526`. The `+` and `−` arms sit either side of the two-sided
value, so the two-sided difference is visibly cancelling an additive offset the one-sided ratio
carries — as the `φ(1−φ)` argument in the pre-registration predicted (ARGUED). The pre-registered
consistency check against fact 45 also holds: the one-sided `R⁺` values (`0.440 / 0.513`) sit in the
same place as M12's C4 (`0.529 / 0.640`) and fact 45's `0.559 / 0.664`, same sign, same order.

**It does not save the estimator.** Two-sided or not, §6 shows the deficit survives removal of the
defocus and vanishes on removal of the resampler.

### 5.3 Long spans are noise, so the correction has nothing to offer them

**MEASURED.** At `δ=1e-4`, span 8 reads median `1.936` with **sd 1.304**; span 32 reads `0.973`
with **sd 5.695**; span 48 reads `−0.068`. Per-edge `R` at spans ≥ 8 is not usable at any δ in the
ladder. R4 is therefore confined to spans 1–2 by measurement, not by choice.

### 5.4 Per-edge noise, which is what the correction actually divides by

**MEASURED**, `coffee-bean` span-1, `sd/|median|` of `R`: **0.237** at `δ=1e-4`, **0.119** at
`2e-4`, 0.030 / 0.013 / 0.005 at `4e-4 / 8e-4 / 1.6e-3`. One edge in 104 (0.96%) has `|R| < 0.2` at
`δ=1e-4`; none anywhere has `R < 0`. So the pathological division does not occur here — the
inflation in §7 is not driven by a blown-up edge.

> **Fact 171 (MEASURED).** A single edge's response carries **23.7% fractional noise** at `δ=1e-4`
> and 11.9% at `2e-4` on `coffee-bean` span-1. Because `E[1/R] > 1/E[R]`, dividing by a per-edge
> `R` inflates on average even when `R` is pure noise. At the primary δ the total inflation is
> `mean(1/R) = 1.629` (+62.9%), of which the noise-driven Jensen part is a factor **1.0134**
> (+1.3 percentage points) and the rest, `1/mean(R) = 1.608`, is the response's **central
> tendency** — that is, the correction is overwhelmingly a scalar wearing a per-edge costume.

---

## 6. The finding that kills the premise: `R` measures the resampler, not the defocus

This section reports two arms that were **added after the pre-registered N3 fired**. That is
disclosed, not hidden: N3 was registered; N3b (`--pedestal`) and N4b (`--field`) were written in
response to it. They are confirmatory, not pre-registered, and are labelled as such.

**MEASURED** (`m23_controls.py` → `out/controls.txt`), median two-sided `R`:

| arm | what is present | 1e-4 | 2e-4 | 4e-4 | 8e-4 | 1.6e-3 |
|---|---|---|---|---|---|---|
| `cb` spans 1–2 | defocus ✔, resampler ✔ | **0.5465** | 0.6381 | 0.9801 | 0.9942 | 1.0139 |
| `cb-self` (**N3**) | defocus ✘, resampler ✔ | **0.3719** | 0.4716 | 0.9433 | 0.9923 | 1.0222 |
| `field-p0` (**N4b**) | defocus ✘, resampler ✘ | **0.9645** | 0.9717 | 0.9906 | 0.9994 | 1.0012 |
| `cb-ped` | defocus ✔, no locking zone | **0.9533** | 0.9162 | 0.9100 | 1.0448 | 1.0010 |
| `cb-self-ped` (**N3b**) | defocus ✘, no locking zone | **0.9346** | 0.8837 | 0.8469 | 1.0736 | 1.0017 |
| `112` spans 1–2 | placebo stack | 0.9287 | 0.9763 | 0.9853 | 0.9938 | 0.9942 |

Read the two differences at `δ = 1e-4`:

- **Remove the defocus** (`cb → cb-self`): `R` moves **−0.1746**, i.e. *away* from 1. The deficit
  not only survives the removal of the thing it is supposed to be measuring, it gets **worse**.
- **Remove the resampler** (`cb → field-p0`): `R` moves **+0.4180**, from 0.5465 to 0.9645. The
  deficit essentially vanishes.

> **Fact 172 (MEASURED).** The small-δ metacalibration response deficit is caused by the **plant's
> own bilinear resampler**, not by the defocus asymmetry it was meant to calibrate. Measuring a
> `coffee-bean` frame **against itself** — zero defocus difference, identical content, identical
> plant — gives `R = 0.372` at `δ=1e-4`, *further* from unity than any real defocus pair (0.526).
> Running the identical probe against a synthetic band-limited field rendered as point samples at
> the composed transforms, with **no interpolator anywhere in the path**, gives `R = 0.965`
> (12 independent noise realisations, sd 0.0071, range [0.953, 0.976]). Removing the defocus makes
> the response worse; removing the resampler fixes it. **The response is not a response to the
> defect.**

> **Fact 173 (MEASURED).** The deficit is a **sub-pixel locking artefact**, not a resampler
> bandwidth artefact. Composing the same single bilinear warp off a `4e-3` scale pedestal — a
> ≈4.8 plane px differential displacement, so no tile sits near zero fractional offset — moves real
> `coffee-bean` pairs from `R = 0.5465` to `R = 0.9533` and self-pairs from `0.3719` to `0.9346` at
> `δ=1e-4`, **with the defocus completely unchanged**. *Confound, stated: the pedestal moves the
> operating point as well as leaving the locking zone, so this arm changes two things at once; it
> is corroboration of fact 172, not an independent proof.*

**Why the self-pair is the extreme case, stated against my own interest.** On a self-pair every
tile sits at exactly the same sub-pixel phase (zero), so peak-locking bias is fully coherent across
tiles and cannot average down; a real pair's spatially varying displacement field dithers the
phase. The self-pair is therefore expected to read *worse* than a real pair, and it does. **That
does not weaken the conclusion**: it proves `R < 1` at small δ is achievable with zero defocus
difference, which is all fact 172 claims. The `field-p0` arm, which has no coherent-phase problem
because it has no interpolator at all, is the one that closes the attribution.

**What this means for fact 45 (DERIVED).** Fact 45's recovery ratios (`0.559 / 0.664` on real
defocus pairs against `1.008 / 0.991` on controls) came from M10's P6/P7 mechanism table, whose
control arm is the resampler-free `field` arm. M10's `resample` arm — real content, bilinear plant,
**no** defocus — reads `1.323` at 0.12 px and `0.863` at 0.24 px with IQRs `[0.656, 1.606]` and
`[0.596, 1.130]` over `n = 12`, and **is not in that mechanism table** (verified by reading
`experiments/m10-deep-align/out/p6-lock-summary.txt` and `out/p6-p7-mechanism.txt`). Its own IQR
spans unity, so it neither confirms nor refutes anything on its own — which is exactly the problem:
fact 45's attribution of the under-response to defocus was never closed against the resampler,
because the only arm that could have closed it was too noisy and was left out. M23 closes it with a
tighter arm (`cb-self`, `n = 52`, IQR `[0.353, 0.385]`), and the attribution does not hold.

> **Fact 174 (MEASURED, correction to the corpus).** Fact 45's attribution of the planted-increment
> under-response to *defocus* is not supported. The control that would have decided it — real
> content, bilinear plant, zero defocus — was measured here (`cb-self`) and reads **0.372 at
> δ=1e-4**, *below* the real-pair value fact 45 attributes to defocus. Fact 45's numbers reproduce;
> its causal reading does not. **This does not disturb fact 43 or the M12 ruling**, which rest on
> the conservation identity `1/S_W(1)` computed from *unplanted* edge measurements and involve no
> resampler at all.

---

## 7. The three gates

### Gate (a) — conservation: **PARTIAL**, and the null takes 93.3% of it

**MEASURED** (`m23_conserve.py` → `out/conservation.txt`), `coffee-bean`, window `0..48`,
`A_48 = −2.4257%` over 15 tiles. Uncorrected `1/S_48(1) = 3.2604`.

| δ | measured `R` | **N1 shuffled `R`** | N2 constant = median | `|R|` floor 0.2 |
|---|---|---|---|---|
| 1e-4 | 1.5928 | 1.6550 `[1.5707, 1.7370]` | 1.7163 | 1.5928 |
| **2e-4** | **1.9095** | **2.0005** `[1.9609, 2.0396]` | 1.9974 | 1.9095 |
| 4e-4 | 3.2605 | 3.2054 | 3.2236 | 3.2605 |
| 8e-4 | 3.2181 | 3.2373 | 3.2370 | 3.2181 |
| 1.6e-3 | 3.3124 | 3.3108 | 3.3123 | 3.3124 |

At the registered primary δ: **`1/S' = 1.9095`** ⇒ **PARTIAL** (≤ 2.13, outside the ±0.15 pass
band). It closes **59.8%** of the gap from 3.2604 to 1 and stops, exactly where the §3 ceiling put
it: `1/0.6381 = 1.567×` of inflation applied to a 3.2604 deficit leaves `2.081`, and the measured
1.9095 is that value less the 6.7% the per-edge component is worth.

**Null N1 (registered).** Shuffling `R` across edges — destroying every bit of R4's claimed
per-edge information, preserving the marginal distribution exactly — gives **2.0005**, which is
**93.3%** of the measured correction's movement. The measured value does sit outside the shuffled
`[p05, p95]` band, so the per-edge information is statistically real; it is worth **6.7%** of the
movement.

**Null N2 (registered).** Dividing every edge by the group median gives **1.9974**, i.e. **93.5%**
of the movement — within 0.003 of the shuffled null. **N2 *is* the scalar M12 refuted**, and it
does 93.5% of what the per-edge correction does.

> **Fact 175 (MEASURED).** Per-edge response calibration moves `coffee-bean`'s conservation ratio
> from **3.2604** to **1.9095** at δ=2e-4 (**PARTIAL**, never reaching the 1.0 the identity
> requires), and a **shuffled** `R` carrying zero per-edge information reproduces **93.3%** of that
> movement (2.0005), while a **constant** median `R` reproduces **93.5%** (1.9974). The per-edge
> content of R4 is worth **6.7%** of an already-insufficient correction. **R4 reduces, in
> measurement, to the scalar correction M12 refuted.**

**Every width-48 window, not one** (M12's verification lesson applied pre-emptively). MEASURED, 48
windows: at δ=2e-4 the corrected `1/S` has median **1.8126**, range `[1.6778, 1.9641]`, against
uncorrected median **2.8356**. No window choice reaches the pass band.

**Gate (a2), local telescoping, 103 instances instead of one aggregate** (MEASURED, added by this
milestone). `ρ_k = l(k,k+2) / [l(k,k+1) + l(k+1,k+2)]`; unbiased ⇒ 1.000. Uncorrected median
**1.1816**, i.e. the span-2 edge reads 18% *more* scale change than the two span-1 edges that
span the same interval — the defect, seen locally. Corrected at δ=2e-4 the median is **1.1205**:
the correction removes a third of a local defect it should remove all of.

> **Fact 176 (MEASURED).** The response is **almost span-independent** where the defect is
> **strongly span-dependent**: `median R` at δ=2e-4 is 0.6126 (span 1) and 0.6621 (span 2), an 8%
> difference, while the local telescoping ratio `l(k,k+2) / [l(k,k+1)+l(k+1,k+2)]` reads **1.1816**
> uncorrected over 103 triples — the span-2 edge sees 18% more than the span-1 pair beneath it.
> Correcting both by their own responses moves that ratio only to **1.1205**. A correction whose
> magnitude does not track the defect's span structure cannot restore a telescoping identity.

### Gate (b) — placebo on `112MSDCF`: **PASS**, both clauses

**MEASURED.** Median `R` over `112MSDCF` spans 1–2 at δ=2e-4 = **0.9763**, `[p25 0.925, p75 1.014]`,
n = 155 — inside the registered `[0.90, 1.10]` band. On the same code, same δ, `coffee-bean` spans
1–2 reads **0.6381** `[0.584, 0.694]`, n = 207, so the probe demonstrably has power and the placebo
is admissible.

**MEASURED.** `112MSDCF` `1/S_48(1)` moves **1.0482 → 1.0104** at δ=2e-4, `|Δ| = 0.0378 < 0.10`.
Across all 31 width-48 windows the corrected median is 0.9706 against 1.0119 uncorrected.

**Gate (b): PASS.** *This is the one gate R4 passes, and it is the cheapest one to pass — a
correction that is nearly inert on a stack with nothing to correct is necessary, not sufficient.*

### Gate (c) — held-out error: **FAIL**

**MEASURED** (`m23_heldout.py` → `out/heldout.txt`). Test set: 125 direct edges, `span ≥ 40`,
`≥ 12` tiles, spans 40–72. **Sanity check reported by the script: 0 test edges have span ≤ 2**, so
no arm modifies anything it is scored on.

Global best over every non-degenerate full-coverage row:

| arm | best `E*` | Δ vs baseline | verdict |
|---|---|---|---|
| uncorrected (baseline) | **6.758** | — | — |
| metacal spans 1–2, δ=2e-4 | **6.758** | +0.000 | **FAIL** |
| N1 shuffled `R` | 6.758 | +0.000 | FAIL |
| N2 constant `R` | 6.758 | +0.000 | FAIL |

The global best is unchanged **by construction**: the winning row is `S4-poly6` trained on
`span ≥ 32`, which contains no corrected edge. The informative comparison is the paired one,
restricted to training sets that actually contain span ≤ 2 edges (MEASURED, same test set, same
strategy, δ=2e-4):

| train set | % span≤2 | strategy | uncorrected | metacal | Δ | **N1 shuffled** | **N2 constant** |
|---|---|---|---|---|---|---|---|
| `all measurable` | 15.5% | S4-poly2 | 7.241 | 7.252 | **+0.011** | 7.252 | 7.252 |
| `span ≤ 32` | 16.7% | S4-poly2 | 8.689 | 8.712 | +0.023 | 8.712 | 8.713 |
| `span ≤ 16` | 20.9% | S5-centre4 | 13.180 | 13.015 | −0.165 | 13.005 | 13.010 |
| `span ≤ 8` | 29.3% | S2-hops8 | 24.444 | 24.444 | +0.000 | 24.444 | 24.444 |
| `span ≤ 4` | 50.5% | S2-hops8 | 40.760 | 40.771 | +0.011 | 40.771 | 40.718 |
| `span ≤ 2` | 100% | S2-hops8 | 43.679 | **32.426** | **−11.253** | **30.931** | **31.245** |

`chain (span 1)` was excluded as a **TREE** — a solve over a tree is chaining in disguise (M10's own
non-degeneracy guard, recomputed here, not copied).

> **Fact 177 (MEASURED).** Re-admitting metacalibrated span-1–2 edges does **not** beat the 6.758 px
> held-out baseline on `coffee-bean`. Best corrected `E*` = **6.758 px** (unchanged; the winning
> training set contains no corrected edge), and on the best short-edge-inclusive training set the
> correction makes it **worse**: 7.241 → 7.252 px. **Gate (c) FAILS, so R4 ships nothing.**

> **Fact 178 (MEASURED).** On the one arm where the correction helps substantially — training on
> `span ≤ 2` alone, 43.679 → **32.426 px** — both nulls help **more**: shuffled `R` gives
> **30.931 px** and a constant median `R` gives **31.245 px**. The improvement is undirected
> magnitude inflation of an under-reporting chain, not per-edge calibration, and a **random**
> assignment of responses does it better than the measured ones.

**δ sweep over short-edge-inclusive training sets** (MEASURED; rule 16 — reported as a bound, not a
value; no argmin is called an optimum):

| δ | median `R` | metacal `E*` | N1 shuffled | N2 constant |
|---|---|---|---|---|
| 1e-4 | 0.5465 | 7.259 | 7.258 | 7.257 |
| 2e-4 | 0.6381 | 7.252 | 7.252 | 7.252 |
| 4e-4 | 0.9801 | 7.242 | 7.242 | 7.242 |
| 8e-4 | 0.9942 | 7.242 | 7.242 | 7.242 |
| 1.6e-3 | 1.0139 | 7.241 | 7.241 | 7.241 |

Uncorrected over the same sets: **7.241 px**. The whole sweep spans 0.018 px and the three columns
agree to 3 decimals. **The correction changes held-out error by less than 0.02 px on any arm that
could win, at any δ in the ladder — a bound, not a value.** The minimum sits at the sweep's
`δ = 1.6e-3` endpoint where `R ≈ 1` and the correction is a no-op, i.e. **no turnover was found
within the sweep**.

---

## 8. Author predictions, scored

| # | prediction | outcome |
|---|---|---|
| 1 | `R` materially δ-dependent, low at 1e-4, ≈1 by 8e-4 | **RIGHT** (0.526 → 0.993, swing 0.4664) |
| 2 | Gate (b) passes | **RIGHT** (0.9763 in band; `1/S` moves 0.038) |
| 3 | Gate (a) PARTIAL, `1/S'` near 2 | **RIGHT** (1.9095) |
| 4 | Gate (c) fails | **RIGHT** (6.758 px, unchanged) |
| 5 | N1 restores conservation nearly as well as measured `R` | **RIGHT** (93.3%) |
| 6 | N3 reads closer to 1 two-sided than M10's one-sided resample arm | **WRONG** — N3 reads **0.372**, further from 1 than M10's `resample` 1.323 / 0.863. The two-sided estimator cancels the resampler's *even* component, and the dominant term turned out not to be even. |

*Caveat on prediction 6, stated against my own interest.* M10's `resample` arm and this milestone's
`cb-self` arm are **not the same construction**: M10's is `n = 12` base frames with a direct
recovered/planted ratio, and its IQR at 0.12 px is `[0.656, 1.606]` — so wide that its median of
1.323 cannot be compared sharply with anything. `cb-self` is `n = 52` with IQR `[0.353, 0.385]` and
measures the increment relative to the base fit. Prediction 6 is scored WRONG on the face of the
numbers, but the comparison is between two differently-built arms and should not be leaned on. The
load-bearing comparison is `cb-self` against `field-p0`, both from this milestone's own code.

5 of 6. **Prediction 6 being wrong is the milestone's most valuable result**: it is what forced N4b,
which is what turned "R4 does not work" into "R4 cannot work, because `R` is not measuring the
defect".

---

## 9. Cost

**MEASURED** (`m23_cost.py` → `out/cost.txt`), 104 span-1 pairs of `coffee-bean`, cfg=m10, 32 cores.
Rule 16: two settings (1 δ = 3 fits/pair; 2 δ = 5 fits/pair), each run twice, orders alternated
`d1 → d2 → d2 → d1`, **per-setting minimum** taken.

| setting | measure time | ms/pair |
|---|---|---|
| 1 δ (3 fits/pair) | 5.10 s | 49.0 |
| 2 δ (5 fits/pair) | 8.90 s | 85.6 |

**DERIVED:** one ±δ pair — the milestone's budgeted "two extra correlation evaluations per edge" —
costs **≤ 36.5 ms/edge**, and the base fit alone is **≈ 12.5 ms/edge**, so one δ costs
**≤ 3.92× a plain edge measurement**. *Quoted as a bound: the settings differ by a fixed 2 fits, so
the difference is an upper bound on the marginal cost and the implied base is a lower bound.
Failure direction: wall clock fails upward.*

At deployment scale (DERIVED): 207 span-1–2 edges ⇒ **7.6 s** extra; the full 1601-edge `m10` graph
⇒ **58.5 s** extra. The budget in the brief was met — it is the only success criterion R4 does
meet, and it buys nothing.

### 9.1 A script whose result was wrong, kept in the record

`m23_heldout.py`'s first version is committed unchanged as
**`m23_heldout_v1_BROKEN.py`**, with its wrong output at `out/heldout-v1-BROKEN.txt`. It scored
gate (c) as *"the minimum `E*` over every non-degenerate full-coverage row"*, which is M10's own
rule and is correct for M10. It reported **6.758 px for all four arms including both nulls**, and I
nearly wrote that down as "the correction is inert". It *is* inert, but that table could not have
shown it: the winning row (`S4-poly6` on `span ≥ 32`) contains no corrected edge, so **all four
arms were identical by construction and the comparison had zero power**. The fix was the paired,
short-edge-inclusive table in §7, which is what exposed fact 178 — the arm where the correction
helps 11 px and both nulls help more. The diff is the `SHORT_FRAC` / `TREES` bookkeeping and the
second, joined table. **Lesson: a comparison that cannot move is not a null result, it is a broken
instrument.**

---

## 10. What was NOT measured

- **R5 (blur-equalised edges) was not attempted.** It is the review's secondary item and the brief
  said to do R4 properly first. §6 makes it *more* interesting, not less: if the small-δ probe
  deficit is a resampler artefact, then a blur-symmetrisation approach that never plants anything
  sidesteps the entire mechanism that broke R4. It remains untested here.
- **Only one deep stack.** Gates (a) and (c) rest on `n = 1` scene. `coffee-bean` is the only
  100-frame stack with a large shrinkage; `112MSDCF` is a placebo, not a replicate of the effect.
  `113MSDCF`, `109MSDCF` and `119MSDCF` were not run through the metacal probe.
- **`cfg = wide64` was not run.** Every arm is `cfg = m10`. M10 scored both.
- **The response is measured about the *measured* operating point, not the true one.** If `L_meas`
  and `L_true` sit on opposite sides of a nonlinearity, `R` measured at `L_meas` is the wrong slope.
  This was pre-registered as untestable within the milestone and remains so.
- **Only scale was corrected.** Rotation and translation were left untouched, as registered. If
  short edges also carry a translation bias, gate (c) could not have passed regardless of `R`.
- **The pedestal arm changes two things at once** (operating point *and* locking zone) and is
  labelled corroboration, not proof.
- **`--pedestal` and `--field` were added after N3 fired.** They are post-hoc, disclosed, and are
  not treated as pre-registered evidence. The Rust refactor that introduced the shared `mc_row()`
  helper alongside them was verified bit-identical: the self-pair arm re-run after the refactor
  produced a CSV with MD5 `4C268FA8C024B9E2FE286927231FA396`, matching the pre-refactor file.
- **No timing was measured on the field arm's per-rep cost** beyond the aggregate 207.7 s.
- **Gate (c) was not scored on `109MSDCF` / `119MSDCF`.** Their shallow depth makes the short-edge
  question moot, but that is an argument, not a measurement.

---

## 11. Proposed corpus changes

*The orchestrator folds these; they are proposals, not edits. `SYNTHESIS.md` was not touched.*

**New facts:** 170–178 above.

**Facts to qualify:**

- **Fact 45** — the numbers reproduce, the causal attribution does not. Suggested amendment: keep
  the recovery ratios, and append "*the attribution to defocus is not supported: a zero-defocus
  self-pair on the same code reads 0.372 and a resampler-free field reads 0.965 (fact 174)*".
- **Fact 47** (alignment bounded by short edges) — unchanged, and now bounded from a second side:
  the short edges cannot be rescued by per-edge response calibration.
- **Fact 52** (M12's scalar refutation) — strengthened. M23 shows a *per-edge* correction reduces in
  measurement to that same scalar (fact 175), so the refutation is broader than a transfer failure.

**Discipline items:**

> **Discipline 80.** When a probe's response approaches unity as the probe gets *larger*, suspect
> the probe, not the scene. A scene property does not know the plant size. On this project that
> pattern (0.526 at δ=1e-4 → 0.993 at δ=8e-4) was the first visible sign that the measured response
> was a sub-pixel locking artefact of the plant's own resampler.

> **Discipline 81.** A control that removes the *cause* is worth more than a control that removes
> the *content*. M10's mechanism table compared a real-pair arm against a synthetic-field arm and
> concluded "defocus", but it omitted the arm with real content and no defocus. Two of the three
> cells of a 2×2 are not a mechanism. Enumerate the 2×2 (defect present/absent × instrument
> artefact present/absent) and fill all four.

> **Discipline 82.** Before reporting "all arms are identical, so the treatment is inert", check
> that the winning row *could* have differed. A comparison whose optimum is set by a row the
> treatment cannot touch has zero power and is a broken instrument, not a null result. (§9.1.)

> **Discipline 83.** Register the null's arithmetic, not just its existence. `1/S` moving from 3.26
> to 1.91 reads as a large effect until the shuffled null lands at 2.00; the informative number is
> the **fraction of the movement the null reproduces** (93.3%), and that number should be computed
> and printed by the same script, not left for the reader.

**Open questions:**

> **Open question 25.** Does the sub-pixel locking artefact identified in fact 173 also bias the
> *unplanted* edge measurements the pipeline actually uses? The `1/S` conservation defect is
> measured with no resampler in the path, so it is not the same artefact — but `coffee-bean`'s
> span-1 edges have a measured displacement of ~0.19 px, squarely in the locking zone, while its
> long edges do not. If locking contributes to fact 43's span dependence, the fix is a
> phase-dither or an upsampled correlation peak, not a calibration. **Testable:** re-measure
> `coffee-bean` span-1 edges with the moving frame pre-shifted by a known integer-plus-half-pixel
> offset that is then removed analytically, and see whether `1/S_48(1)` moves off 3.26.

> **Open question 26.** Is R5 (blur-equalised edges) now the better candidate? It attacks the same
> defect without planting anything, so it is immune to the mechanism that broke R4. Untested.

---

## 12. Questions for the owner

1. **Is fact 45's causal reading load-bearing anywhere else?** M23 says the numbers hold but the
   defocus attribution does not (fact 174). I checked that fact 43 and the M12 ruling do not depend
   on it, but I have not audited every downstream use.
2. **Should the `112`/`113` replicate pair have been run as a second placebo?** I ran only `112`.
   The pre-registration named `112` and I did not extend it; `113` is cheap (63 frames) and would
   turn gate (b) from n=1 into n=2.
3. **Is a 0.40 px PASS margin on gate (c) right?** It came from M10's runner-up spread. Nothing in
   this milestone came close enough for it to matter, but a future proposal might land at 6.5 px
   and the margin would then be the whole ruling.
4. **Do you want the `--pedestal` / `--field` modes promoted?** They are two small Rust functions in
   an experiment crate and they answered the question that mattered. They are the natural home for
   open question 25.

---

## 13. Reproduction

```powershell
cd projects\strehl\experiments\m23-metacal
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"   # cargo is not on PATH
$env:PYTHONIOENCODING = 'utf-8'
powershell -File run-m23.ps1                          # everything, ~8 min + gates
```

Individually:

| script | produces | what it decides |
|---|---|---|
| `src/main.rs` mode `metacal` | `data/*-metacal.csv` | the per-edge responses; `--self`, `--pedestal`, `--field` are the control arms |
| `m23_response.py` | `out/response.txt` | §5 — `R` tables, δ-dependence criterion, positive control, gate (b) R-band, N3, per-edge noise |
| `m23_controls.py` | `out/controls.txt` | §6 — the resampler/defocus 2×2 and the attribution |
| `m23_conserve.py` | `out/conservation.txt` | §7 gate (a), nulls N1/N2, G0, G1, every-window sweep, local telescoping |
| `m23_heldout.py` | `out/heldout.txt` | §7 gate (c), G2, the paired short-edge table, the δ sweep |
| `m23_heldout_v1_BROKEN.py` | `out/heldout-v1-BROKEN.txt` | **§9.1 — the wrong version, kept deliberately. Do not run for a result.** |
| `m23_cost.py` | `out/cost.txt` | §9 — alternated timing sweep, per-setting minimum |
| `m23_mc.py`, `m23_lib.py` | — | shared helpers; `m23_lib.py` is M10's `m10_lib.py` verbatim |

*Layout note: Python analysis sits at the experiment root and `src/` holds the Rust crate, matching
`experiments/m10-deep-align/` and `experiments/m12-shrinkage/`.*

**Provenance and hashes.** `data/m10-coffee-bean-edges.csv` MD5
`5FAFAF327256EB974F974AEF2989E1B0` (matches M12's published hash);
`data/m12-stack-112-edges.csv` MD5 `7B22151496CA3CEEB53FA5BBECC4D05B`.

**Falsifiers, stated so the verifier can aim.**

- Fact 170 dies if `median R(1e-4)` and `median R(8e-4)` on `coffee-bean` span-1 differ by less than
  0.15 — recompute from `data/coffee-bean-metacal.csv`, columns `span`, `delta`, `r_two`.
- Fact 172 dies if `data/cb-field-metacal.csv` reads `r_two < 0.9` at `delta = 1e-4`, or if
  `data/cb-self-metacal.csv` reads `r_two > 0.9` there.
- Fact 175 dies if the shuffled null in `m23_conserve.py` reproduces materially *less* than the
  measured correction's movement — re-run with different seeds; `NSHUF = 400` at seed 20230823.
- Fact 177 dies if any full-coverage, non-tree strategy trained on a set containing corrected
  spans 1–2 scores below 6.36 px on the 125-edge test set.
- Fact 178 dies if N1/N2 on the `span ≤ 2` arm score *above* 32.426 px.
- **The whole report dies** if `m23_conserve.py`'s G0 check no longer reads ≤ 1e-7, because then the
  base fits in `data/*-metacal.csv` are not the same measurements as M10's committed edges and none
  of the comparisons are like-for-like.
