# M72 — is ρ(G1,G2) = +0.073 real, and does it belong in the model?

Status: MEASURED (two pre-registered criteria NOT MET — one on its own terms, one after its comparator was refuted — and two post-hoc gates NOT MET; all four consequences honoured; one pre-registered verdict qualified by my own post-hoc test). **Amended after publication — see §12.**
Scope: `experiments/M72-green-correlation/`, 220 dark frames from `D:\macro-dark-frames`
Predecessor: M62 §9 (P17), the measurement M61 §4.13 designed and did not run

---

## Headline

**Yes, it is real. No, it does not belong in the model — and the reason it does
not is more interesting than the reason it might have.**

Three findings, in the order they change what the project should do.

**It replicates.** A direct per-cell estimator, on M62's own group, measures
**ρ(G1,G2) = +0.08261** against fact 895's **+0.0730**. That is inside my
pre-registered replication band. M62 obtained its number from a difference of
variances in which the answer is 6.8% of the quantity it is differenced out of;
the two independent estimators agree anyway.

**But it is not a property of the green pair.** ρ(G1,G2) is one entry in a
correlation field that covers the whole sensor. Every plane is correlated with
its own neighbours at +0.05 to +0.16, and the two greens sit **inside** that
range rather than above it: ρ(G1,G2) = +0.09133 against a within-green maximum
of +0.09090 on the same pixels — a margin of **+0.00043** where my pre-registered
gate required more than +0.010. My own C2 control returned GREEN-SPECIFIC and
**that verdict is misleading as stated**. The greens are not distinguished by
having a correlation. They are distinguished by which control I compared them
against.

**And its operational weight is smaller than the headline suggests, but it is
not negligible.** The error in σ is **over-confident everywhere, never changes
sign, peaks at 4.05%, and decays with signal**: 0.16% by 100 DN, 0.017% by
1000 DN. That much is measured and is not in question.

The *adjective* is. **C6, my materiality criterion, is VOID** — it was
pre-registered against an external input that has since been refuted, and
re-applying my own formula to the corrected input gives **NOT MET** under both
available readings of the comparator. See §4.7. What survives is the regime:
the effect exceeds the project's tolerated calibration error **below roughly
12–63 DN above black**, depending on ISO and on which reading is taken, and is
below it above that. **Whether the merge adjudicates down there is not something
this milestone measured, and it is the question that decides the matter.**

**Recommendation, described and not applied: do not patch `green_luma_sigma`.**
Adding a green covariance constant would be arithmetically right in one place,
silently absent in every other place the pipeline pools neighbouring pixels, and
would encode a green-pair mechanism that the field shows does not exist. The
change worth making is to **`noise.rs:122`, which states as fact something now
measured to be false**.

**The mechanism is located, not named.** The covariance splits cleanly in two by
distance, and the split is a generation-site split:

| | ρ across ISO 100→2000 | covariance upstream fraction | generated |
| --- | --- | --- | --- |
| orthogonal neighbours, \|Δ\|=1 | ×0.82 to ×1.23 — flat | 0.58 – 0.97 | **electron domain, upstream of the conversion gain** |
| everything at \|Δ\| ≥ √2 | ×0.26 to ×0.36 | 0.16 – 0.49 | **downstream of the conversion gain** |

The green variance's own upstream fraction is **0.6933**, which is where the
flat group lands and nowhere near where the steep group lands. Both predictions
of that split were pre-registered and both were met, with no overlap between the
groups and a rank correlation of **+0.9396** across all thirteen series.

**The G1/G2 pair is in the second group.** The correlation the model would have
been patching is a **read-chain** effect, not a photosite effect — and the field
excludes transport outright: **the nearest neighbour is not the most correlated
thing on this sensor.**

---

## 1. Rule 40 — what I read before measuring

| File | What I took from it | Did I re-derive it? |
| --- | --- | --- |
| `M62-sqrt-n.md` §9, §9.1, §10 | The source of fact 895. P17's ρ = +0.0730 and the estimator that produced it. P14's frame-mean span 0.079 DN. §9.1's precedent for reporting a tripped criterion as mis-specified. | The estimator, yes — see fact 4. The number, no; I measured it independently. |
| `M61-ptc-high-iso-measured.md` §4.13 | M61 §4.13 facts 59 and 60, in that report's own numbering: it designed this measurement and fixed the pairing geometry in advance so the pairing could not be chosen after the answer. | No. I executed its geometry unchanged. |
| `M48c-defect-layer-measured.md` | The recurrent defect layer, used to build the exclusion arms. | No. |
| `M68-b-plane-mechanism.md` | My own predecessor. The α/δ decomposition of a dark-frame variance against ISO, and the gain model read from `profile.rs`. | Reused the method. |
| `crates/strehl-core/src/noise.rs` | `green_luma_sigma` at line 126 and the independence claim in prose at line 122. Read only. | — |
| `crates/strehl-core/src/merge.rs:937` | `green_mean(i) = 0.5·(G1(i) + G2(i))` at the **same cell index**. This fixes the pairing any fix must use. Read only. | — |
| `crates/strehl-core/src/profile.rs` | Gain model, dual-gain switch, read-noise constants. Read only. | Partially — see fact 22. |

Searched `docs/research/` for `0.073`, `0.5365`, `correlat`, `covarian`, `G1/G2`
and `G1 and G2`. The only prior measurement of this quantity is M62 P17.

Numbering note: `fact 895` above is a **SYNTHESIS global number**. All
`**Fact N**` items below are **local to this report**.

---

## 2. Did I agree with the prior reasoning before measuring?

I derived the consequence and the estimator from first principles first, in
`src/00-derivation.py`, with a planted signal chain to catch my own errors. It
caught two, and both were quantitatively important.

**Fact 1 (DERIVED, self-correction).** Quantisation dilutes a measured ρ by
`s²/(s² + 1/12)` where `s²` is the pre-quantisation variance in DN². Across the
ISO range on disk this factor runs **0.9243 at ISO 50 to 0.9974 at ISO 2000** —
an 8% ISO-dependent bias **in exactly the direction that mimics an upstream
covariance**, which is the signature I intended to use to locate the mechanism.
My instrument had a confound that pointed at a specific answer. Fixed by
pre-registering **Sheppard's correction** (`var − 1/12`, variances only) for
every ISO-dependent number, with the uncorrected value reported alongside
throughout. Verified live: the synthetic null's `var_a` reads **1.08240** for
unit-variance input, which is 1 + 1/12.

**Fact 2 (DERIVED, self-correction).** `ρ_adjacent − ρ_displaced` is **not**
`ρ_local`. It equals `s²ρ_local/(s² + v_c + q)` — diluted by the common mode
*and* by quantisation, both in the denominator. The decomposition has to be done
in covariance space. My first draft of C3 would have reported a biased
common-mode share.

**Fact 3 (DERIVED).** The operational number for `green_luma_sigma` is the
**total** ρ, not the local part. The code averages two specific photosites; it
does not care which term of a decomposition the covariance came from.

**Fact 4 (DERIVED).** M62's estimator was fragile and this is why the
replication mattered. P17 computed
`cov = (4·var(L) − var(G1) − var(G2))/2` from `var(L) = 0.53229`,
`σ(G1) = 0.99346`, `σ(G2) = 0.99905`. The numerator is **6.77%** of the quantity
it is differenced out of, an error amplification of about **14.8×**: a 0.5%
systematic difference in how `var(L)` and the singles were computed moves ρ by
±0.0054, which is 73% of the published finding. Note the sign constraint —
a clamp such as `(raw − black).max(0)`, which M62 §9.1 discloses, *reduces*
`var(L)` and makes the inferred covariance appear **negative**. Clamping is
therefore not a candidate explanation for the positive published value.

I agreed with the direction of the prior work and disagreed with nothing in it.
The two corrections were to my own draft, not to M62's.

---

## 3. Pre-registration

Written into the module docstring of `src/01-green-correlation.py` and committed
in `69f265b` **before any corpus frame was decoded**: seven hypotheses H0–H7, six
observables O1–O6, the ISO range, the defect-exclusion arms, criteria C0–C6 each
with its consequence stated in advance, a declared cannot-separate outcome, and a
non-blindness disclosure.

`src/02-criteria.py`, which applies the bands, was committed in `3bcd3c1`
**while the sweep was still decoding**. It copies every band from the
pre-registration and introduces none, and it could not have been tuned to an
answer that did not yet exist.

The instrument was validated before use: synthetic null **−0.00071**, permutation
null **+0.00004**, a planted ρ of 0.073 recovered as **0.07236**, and all six CFA
pair classes asserted against the measured plane offsets rather than assumed.

**Fact 5 (MEASURED).** CFA geometry, asserted at runtime from the decoder rather
than assumed: `raw_pattern [[0,1],[3,2]]`, `color_desc RGBG`, visible frame
**4688 × 7028**, planes **2344 × 3514**. R at (even, even), G1 at (even, odd),
G2 at (odd, even), B at (odd, odd). R–G1 and G2–B share a row; R–G2 and G1–B
share a column; **G1–G2 and R–B share neither — the two diagonals, at identical
distance √2 and opposite orientation.** R–B is therefore the matched control for
G1–G2, and it was named as such before the sweep.

---

## 4. The seven pre-registered criteria

### 4.1 C0 — instrument. **NOT MET.**

C0 required |ρ| ≤ 0.005 on two nulls. The synthetic null passed at 0.00071. The
real-data frame-permutation null reached **0.006588**, outside the band, on
G1–G2 at ISO 100 — the very cell C1 depends on.

Its declared consequence was that **no ρ in this report stands**. I report it as
failed and I did not quietly move the band.

I then wrote `src/03-c0-audit.py` with two declared branches and no third, and
**committed it before running it** (`4049457`), with an explicit disclosure that
3 of 11 groups had already printed when it was written.

**Fact 6 (DERIVED).** A frame-permutation null **cannot** be zero when a real
correlation exists, and the offset is forced with no free parameters. Removing
each cell's temporal mean gives `cov(x̃_s, ỹ_t) = c(δ_st − 1/T)`. A derangement
has `δ_{t,π(t)} = 0` for every `t`, so the permuted estimator sums to `−c` while
the matched estimator sums to `c(T−1)`. Therefore

```
cov_perm / cov_matched  =  −1/(T−1)  =  −0.052632   for T = 20
```

At ρ = +0.083 that is −0.0044, which is most of the −0.0066 observed.

**Fact 7 (MEASURED).** The predicted ratio is confirmed at **−0.053521**
(sd 0.0208) across **40 pair-ISO cells** against a prediction of −0.052632. The
bias-corrected null's worst value is **0.00224**, which meets C0's *original*
band. The synthetic null, where no correlation exists, shows no such offset —
which is why C0 passed there and failed here.

Reporting a tripped criterion as mis-specified is always available after the
fact. What makes this checkable rather than convenient is that the replacement is
**parameter-free**, that it was **tested 66 times**, and that the audit was
**committed before it ran**.

### 4.2 C1 — replication. **REPLICATED.**

Group `118MSDCF`, ISO 100, M62's own group, direct per-cell estimator:

| defect arm | cells retained | var G1 | var G2 | cov | ρ raw | ρ Sheppard |
| --- | --- | --- | --- | --- | --- | --- |
| M48c 6σ | 0.99759 | 1.00335 | 1.00780 | 0.076184 | +0.07576 | **+0.08261** |
| M48c 3σ | 0.97689 | 0.97563 | 0.97081 | 0.075579 | +0.07766 | +0.08493 |
| none | 0.99858 | 1.00827 | 1.02094 | 0.076322 | +0.07522 | +0.08196 |

**Fact 8 (MEASURED).** ρ(G1,G2) = **+0.08261** at ISO 100 against fact 895's
+0.0730 — a difference of +0.0096, inside the pre-registered ±0.020 REPLICATED
band. The result is insensitive to defect exclusion: the three arms span 0.0030.

**Fact 9 (MEASURED).** ISO 50 and ISO 100 have identical gain in `profile.rs`
because 50 is a pull ISO, and they return ρ = **+0.08210** and **+0.08261**.
Agreement to 0.0005 between two independently captured groups bounds
within-session repeatability at that level.

### 4.3 C2 — green specificity. **GREEN-SPECIFIC — and misleading as stated.**

The control could have failed. It did not.

**Fact 10 (MEASURED).** At ISO 100, ρ(G1,G2) = **+0.08261** and its matched
diagonal control ρ(R,B) = **+0.00964** — the same displacement class, the same
distance, the opposite orientation, 8.6× smaller. C2's band called that
GREEN-SPECIFIC.

**That verdict is wrong as a statement about the sensor**, and my own post-hoc
field measurement is what shows it. See §5. It is right as a statement about the
comparison C2 makes.

### 4.4 C3 — common mode. **LOCAL.**

**Fact 11 (MEASURED).** The spatially uniform per-frame term accounts for
**1.43%** of the covariance at ISO 100 (`cov` of the frame means 0.001093 against
a per-cell covariance of 0.076184). H1 — a shared per-frame offset — is excluded.
Per-frame plane-mean spans of 0.135 DN are consistent with M62 P14's 0.079 DN.

### 4.5 C4 — geometry. **CLASSES DIFFER.**

**Fact 12 (MEASURED).** Local covariance by M61's pre-fixed geometry classes at
ISO 100: row 0.024099, column 0.030960, diagonal 0.040919, spread **0.016821**
against a band of 0.010. Row / column / diagonal does **not** cleanly explain the
pattern, and §5 shows why: the classes each mix pairs that behave completely
differently.

### 4.6 C5 — mechanism location. **Upstream fraction +0.249.**

**Fact 13 (MEASURED).** ρ(G1,G2) falls monotonically with ISO, from **+0.08261**
at ISO 100 to **+0.02799** at ISO 2000. Slope against log G is **−0.016577**
(r = −0.964); the uncorrected series agrees on direction (−0.014543, r = −0.955),
so the pre-registered cannot-separate branch did not fire.

**Fact 14 (MEASURED).** Fitting `cov(ISO) = α G² + δ` gives
`α_low = +0.58127 ± 0.17122`, `α_high = +0.03710 ± 0.00646`,
`δ = +0.091977 ± 0.024490`, residual rms 0.038991. No jackknife bar spans zero.
The upstream fraction at base ISO is **0.2488**.

**Fact 15 (MEASURED).** That number had nothing to be compared against until I
fitted the **variance's own** split the same way:

| series | α_low | α_high | δ | upstream fraction |
| --- | --- | --- | --- | --- |
| var R | 13.26354 ± 0.33890 | 1.36580 ± 0.02150 | 0.311228 ± 0.056438 | 0.6908 |
| var G1 | 13.43518 ± 0.41432 | 1.38144 ± 0.01671 | 0.315379 ± 0.046503 | 0.6907 |
| var G2 | 13.35833 ± 0.33439 | 1.38078 ± 0.00544 | 0.305989 ± 0.023506 | 0.6959 |
| var B | 11.27719 ± 0.19723 | 1.18288 ± 0.01387 | 0.185341 ± 0.040550 | 0.7613 |
| cov G1–G2 | 0.58127 | 0.03710 | 0.091977 | **0.2488** |

The green covariance is **2.8× more downstream-weighted** than the green variance
it correlates. That is why ρ falls with ISO, and it is a statement about where in
the chain the covariance is generated rather than about its size.

### 4.7 C6 — operational regime. **VOID; re-applied, NOT MET.**

`green_luma_sigma` computes `var(L) = (var G1 + var G2)/4`, i.e. ρ = 0. The truth
is `var(L) = (var G1 + var G2 + 2 cov)/4`, so the modelled σ is too small by
`√(1+ρ) − 1` — **over-confident**, in the direction that matters.

**Fact 16 (MEASURED).** The error in σ, using the measured dark covariance at
each ISO and adding shot noise for a signal level S in DN:

| ISO | S=0 | S=10 | S=100 | S=1000 | S=4000 |
| --- | --- | --- | --- | --- | --- |
| 100 | **+4.038%** | +1.178% | +0.160% | +0.017% | +0.004% |
| 400 | +3.568% | +0.447% | +0.050% | +0.005% | +0.001% |
| 1000 | +2.162% | +0.567% | +0.074% | +0.008% | +0.002% |
| 2000 | +1.264% | +0.524% | +0.084% | +0.009% | +0.002% |

**Fact 17 (WITHDRAWN — superseded by facts 33 and 34).** As published, this fact
read: *"the worst error anywhere in the 11-ISO × 5-signal table is 4.038%,
against a pre-registered materiality threshold of 4.75% (= 0.25 × M69's 19%).
C6 passes by a 15% margin."* **The measurement is unchanged and the threshold is
void.** The 19% was an external input taken from a report in flight; see §4.7.1.

**Fact 18 (MEASURED).** The regime, which is the part that matters and not the
magnitude. The error is **positive in every cell of the table** — the model is
over-confident everywhere and **never flips sign**, so no gate anywhere in the
pipeline can be pushed across a threshold in the dangerous direction by a
correction that is currently absent. It decays with signal: 4.0% at S=0, 1.2% at
S=10, 0.16% at S=100, 0.017% at S=1000. **This fact does not depend on any
comparator and is untouched by §4.7.1.**

### 4.7.1 C6's comparator was refuted, and the verdict does not survive it

C6 was pre-registered with an **external input**, in these words:

> *"PRE-DECLARED COMPARISON: M69 is finding `FOCUS_NOISE_SD` 19–21% off on real
> texture. If the worst-case sigma error over the operating range is below 1/4
> of that, the item is reported as IMMATERIAL IN PRACTICE regardless of whether
> ρ is real."*

**That input is false.** M69's report refutes it at its own headline: the 19–21%
is M66's, it reproduces only on M66's own plant, and it does not generalise — on
three further real latents the same measurement gives 0.8380, 1.0274 and 1.0246
and *"the sign is not even consistent"*. M69's finding is that
`FOCUS_NOISE_SD`'s **value is very nearly right** — per-stack response noise
between 0.9285× and 1.1009× the shipped number, **median 1.0147×** — and it
**recommends against changing it**. What M69 refutes is the constant's *form*.

I do not get to keep a verdict whose input has been withdrawn, and I do not get
to pick a new comparator that rescues it. The formula was pre-registered, so I
re-applied the formula to the corrected input. The comparator apples-to-apples
with a multiplicative σ error is `FOCUS_NOISE_SD`'s **scale** error, not its form
error; both available readings of the scale error are carried through rather than
one being chosen.

**Fact 33 (MEASURED, supersedes fact 17).** C6's own arithmetic on the corrected
input:

| comparator | value | threshold = 0.25 × | measured worst 4.048% | verdict |
| --- | --- | --- | --- | --- |
| M66's 19%, as pre-registered | 19.00% | 4.750% | below | MET — **REFUTED INPUT** |
| M69 median scale error | 1.47% | **0.367%** | above | **NOT MET** |
| M69 worst single stack | 10.09% | **2.522%** | above | **NOT MET** |

**C6's IMMATERIAL IN PRACTICE verdict is VOID.** Re-applying my own formula gives
**NOT MET under both readings**, so the outcome does not depend on which reading
is taken. The adjective is withdrawn. Facts 16 and 18, which are measurements of
my own dark frames, are not.

**Fact 34 (MEASURED).** The two readings agree on the verdict and **disagree on
the regime**, which is the part that can be acted on. `S*` is the signal in DN
above black at which the σ error falls below the threshold:

| ISO | σ error at S=0 | `S*` vs median comparator | `S*` vs worst-stack comparator |
| --- | --- | --- | --- |
| 100 | 4.048% | 41.2 DN | 2.5 DN |
| 250 | 3.182% | 63.3 DN | 2.2 DN |
| 400 | 3.325% | 12.4 DN | 0.5 DN |
| 1000 | 2.294% | 17.6 DN | never exceeded |
| 2000 | 1.390% | 17.9 DN | never exceeded |

Against M69's **median** scale error the effect is above threshold at **every
ISO**, out to 12–63 DN above black. Against its **worst single stack** it is
above threshold at 8 of 11 ISOs and only within about 2.5 DN of black. **I am not
choosing between them.** The honest statement is that the effect matters
somewhere between the first 2 DN and the first 60 DN above black, and that
**whether the merge adjudicates in that range is the question that settles it —
a question this milestone did not measure and does not own.**

**Fact 19 (DERIVED).** Fact 895's stated consequence should be updated. The
measured ρ = +0.08261 gives `var(mean) = 0.5413 σ²` rather than the quoted
`0.5365 σ²`, and **4.0% in σ rather than 3.6%** — at ISO 100, at zero signal.
The 3.6% is not wrong; it is the value at M62's ρ, and it is quoted without the
two conditions that make it small.

---

## 5. The post-hoc field — where my own C2 verdict fails

C2 and O5 disagreed about the headline and I was not entitled to pick between
them. O5, pre-registered for a different purpose, reports **every plane
correlated with its own in-plane neighbours** at ISO 100:

| plane | same sensor row | same sensor column |
| --- | --- | --- |
| R | +0.07561 | +0.06474 |
| G1 | +0.08207 | +0.06419 |
| G2 | +0.08192 | +0.06387 |
| B | **+0.16242** | +0.08904 |

ρ(G1,G2) = +0.0826 sits **inside** that range. A reader given only C2 would
conclude the greens share something the other planes do not.

So I measured the whole thing: `src/04-correlation-field.py` computes the
temporal autocorrelation against the **sensor-pixel displacement vector**, with
no reference to the CFA, then stratifies by the CFA phase of the origin. Every
number C2 and O5 report is one entry of that field. It was **committed before it
ran** (`a6ba9f2`), with a commit message that names F4 as a check designed to
invalidate my own C2 headline.

**Fact 20 (MEASURED).** F3. Pooled over all origins at ISO 100, correlation
against displacement:

```
|Δ| = 1      +0.02992
|Δ| = √2     +0.04649
|Δ| = 2      +0.09451
```

**The nearest neighbour is not the most correlated thing on this sensor.**
Correlation *increases* with distance out to two pixels, at both ISOs measured.
Every transport mechanism — charge diffusion, optical crosstalk, anything
carried through the silicon — is monotonically decreasing in distance. **All of
them are excluded by the shape of the field alone**, before any modelling. This
is discipline 473 applied to my own question: the mechanism is where the noise is
generated, not where it is nearest.

**Fact 21 (MEASURED).** F4. At ISO 100, ρ(G1,G2) = **+0.09133** on the field's
pixels against a within-green |Δ|=2 maximum of **+0.09090** — a margin of
**+0.00043** where my pre-registered gate required more than +0.010. At ISO 1600
the margin is **−0.00074**, the wrong sign entirely. F4 fired at both ISOs.

**Consequence, as declared: C2's GREEN-SPECIFIC verdict is MISLEADING AS
STATED, and the model recommendation follows the field rather than C2.** The two
greens are not distinguished by having a correlation. They are two pixels
1.41 px apart in a sensor whose read-domain noise is correlated over a
neighbourhood of about 2 px, and R–B — the control that made C2 look decisive —
is simply the *weakest* pair in that field rather than a normal one.

**Fact 22 (MEASURED).** Colour dominates geometry, and this is why C4 could not
resolve anything. Same displacement, different planes: G1→G1 along a row at
Δ=(0,±2) gives **+0.0907**, while G1→R along the same row at Δ=(0,±1) gives
**−0.0021**. Across the six cross-plane pairs at ISO 100, **every pair containing
R is at or near zero** (R–G1 −0.0019, R–G2 +0.0088, R–B +0.0096) while **every
pair among {G1, G2, B} is strong** (G1–G2 +0.0826, G1–B +0.0645, G2–B +0.0599).
R is normally self-correlated (+0.0756 along a row) and shares with nothing.

**Fact 23 (MEASURED).** A second structural asymmetry with no explanation. At
Δ=(±2,±2) — the pure diagonal within a plane — R→R holds at **+0.0726** while
G1→G1 collapses to **+0.0084**, a ninefold difference at identical geometry.

### 5.1 F1 and F2 both failed, and I had declared both fatal

F1 required ρ(0,0) = 1.000000 and measured 1.11276. F2 required the field to
agree with `02-criteria` to 0.005 and found +0.00872 on G1–G2. I had declared
that an F1 failure means nothing in the field is reported and an F2 failure kills
the field — which would take F3 and F4 with it.

`src/05-field-audit.py` was **committed before it ran** (`04257889`), with the
two branches declared and no third.

**Fact 24 (DERIVED, then MEASURED to machine precision).** F1 was mis-specified
by me. `04` applies Sheppard's correction to the **denominator only**, so at zero
lag the estimator is `V̄/(V̄ − 1/12)` by construction, where `V̄` is the
mask-weighted mean temporal variance. Predicted against measured, nothing fitted:

| group | V̄ | predicted | measured | difference |
| --- | --- | --- | --- | --- |
| 118MSDCF, ISO 100 | 0.822354 | 1.11276188 | 1.11276188 | −2.2×10⁻¹⁶ |
| 121MSDCF, ISO 1600 | 11.932807 | 1.00703266 | 1.00703266 | 0.0 |

F1's failure **confirms** Sheppard's correction is applied. I asked for a value
my own correction guarantees is not 1.

**Fact 25 (MEASURED).** F2 was also mis-specified by me — it compared two
different pixel sets. Running `01`'s `pooled_moments`, **unmodified**, on `04`'s
identical crop with an identical mask reproduces the field to **3.2×10⁻⁵**
(G1–G2) and **2.2×10⁻⁵** (R–B) at ISO 100, and to 6×10⁻⁶ and 4×10⁻⁶ at ISO 1600.
The two code paths are the same estimator. The whole +0.0087 gap is the pixel
set.

**F1 and F2 are reported as FAILED AS WRITTEN. F3 and F4 stand**, and they stand
on the argument declared in advance rather than one invented afterwards: both are
**internal comparisons within a single field over a single pixel set**, which
neither the zero-lag normalisation nor the pixel-set difference can reach.

**Fact 26 (MEASURED, new).** F2's gap turned out to be a finding. ρ is
systematically **higher in the quiet centre of the sensor**: crop against full
plane, **1.106×** at ISO 100 and **1.244×** at ISO 1600, for **both** G1–G2 and
R–B (1.114× and 1.330×). The central 2400² crop carries **0.820** and **0.642**
of the full plane's mean temporal variance. The extra variance towards the edges
is therefore largely **uncorrelated**. The full-plane value is the operational
one, because the merge reads the whole frame — and that is the value C2 and C6
used.

---

## 6. The mechanism, located

C2 and O5 contain two distinct ISO signatures in the same sweep, and they sort by
distance rather than by colour or by CFA class.

`src/06-mechanism-split.py` was **committed before it ran** (`02b5176`) with a
prediction that could fail: if the flat/steep split is an upstream/downstream
split, the flat pairs' covariance upstream fraction must land near the
variance's 0.6933 and the steep ones must not. P1 required **no overlap at all**
between the two groups. R–G1 was excluded by name, before the numbers, because
its ρ is too close to zero for a ratio to mean anything.

**Fact 27 (MEASURED).**

| series | \|Δ\| | ρ @100 | ρ @2000 | ratio | upstream fraction |
| --- | --- | --- | --- | --- | --- |
| R–G2 | 1 | +0.00883 | +0.01084 | 1.228 | **0.9655** |
| G2–B | 1 | +0.05992 | +0.05006 | 0.835 | **0.6007** |
| G1–B | 1 | +0.06452 | +0.05304 | 0.822 | **0.5787** |
| R–B | √2 | +0.00964 | +0.00345 | 0.358 | 0.4852 |
| **G1–G2** | **√2** | **+0.08261** | **+0.02799** | **0.339** | **0.2488** |
| G1 row | 2 | +0.08207 | +0.02810 | 0.342 | 0.2530 |
| G2 row | 2 | +0.08192 | +0.02793 | 0.341 | 0.2487 |
| B row | 2 | +0.16242 | +0.05290 | 0.326 | 0.2250 |
| R row | 2 | +0.07561 | +0.02139 | 0.283 | 0.1999 |
| B col | 2 | +0.08904 | +0.03227 | 0.362 | 0.2428 |
| G1 col | 2 | +0.06419 | +0.01739 | 0.271 | 0.1714 |
| G2 col | 2 | +0.06387 | +0.01712 | 0.268 | 0.1671 |
| R col | 2 | +0.06474 | +0.01697 | 0.262 | 0.1645 |
| *green variance reference* | | | | | *0.6933* |

**P1 MET**: flat group 0.5787–0.9655, steep group 0.1645–0.4852. No overlap.
**P2 MET**: Spearman rank correlation between the ISO ratio and the upstream
fraction, across all thirteen series, **+0.9396**.

**Fact 28 (DERIVED).** The two ISO signatures are a generation-site split
ordered by distance. **Orthogonal nearest neighbours at |Δ|=1 carry a covariance
generated in the electron domain, upstream of the conversion gain.** Everything
at |Δ| ≥ √2 — both diagonals and every within-plane pair — carries a covariance
**generated downstream of it**, in the late analog chain or the ADC.

**Fact 29 (DERIVED).** **ρ(G1,G2) is in the downstream group.** The correlation
this milestone was asked about is a read-chain effect, not a photosite effect.
Combined with fact 20 — nearest neighbour is not largest — the two most
intuitive mechanisms for a green-pair correlation, charge diffusion and optical
crosstalk between adjacent photosites, are **both excluded**, and they are
excluded by two independent observables.

**What this does not do is name a circuit.** Upstream in a dark frame means the
electron domain at or before the sense node. It does not distinguish a shared
floating diffusion from correlated dark current from anything else generated
there, and this milestone has no instrument that can. I am reporting a location
in the signal chain, not a component.

---

## 7. What this does not settle

**Fact 30 (DERIVED).** **H6 — signal-proportional crosstalk — is outside this
instrument entirely, and I declared that before measuring.** A dark frame has
S ≈ 0 and is structurally blind to a covariance of the form `cov = k·g·S`. No
result here, of any sign, can exclude it. **A dark null means "no read-domain
covariance", never "no covariance."** The data that could settle it is
`D:\personal\macro\flat-fields`, which **M71 owns exclusively** and which I did
not touch.

**Unsettled, in descending order of how much I think they matter:**

1. **Why R is decoupled from everything** (fact 22) while {G1, G2, B} are
   mutually coupled, and why R→R survives the pure diagonal while G1→G1 does not
   (fact 23). Not geometry, not distance, not a uniform common mode. No candidate
   mechanism identified.
2. **Whether any of this generalises** beyond one body and one dark session.
   Every number here is from a single camera on a single set of captures.
3. **The signal dependence of ρ**, which fact 30 puts out of reach here. C6's
   table assumes the dark covariance is fixed in DN² while shot noise grows — the
   H-read hypothesis. If H6 is also present, C6's decay with signal is too fast
   and the operational error is larger at high signal than reported. C6's
   conclusion would survive a substantial H6 term, but its *table* would not.
4. **Whether ρ varies with position for a physical reason** (fact 26) or whether
   the edges simply carry more uncorrelated variance.

---

## 8. Recommendation for `noise.rs` — described, not applied

I did not modify anything under `crates/`. M67 and M69 were live in it when this
was written; M73 and M74 are now.

**Do not add a green covariance constant to `green_luma_sigma`.** Two reasons,
and the third one this report originally gave has been withdrawn:

1. **It would encode a mechanism that does not exist.** Fact 21 shows the greens
   are not a privileged pair. A constant named for the green pair tells the next
   reader that G1 and G2 share something, and they do not — they are two pixels
   in a locally correlated field.
2. **It would be right in one place and absent everywhere else.** The same
   correlation exists between *every* pair of nearby pixels at +0.05 to +0.16.
   Any code path that pools or differences spatially adjacent samples carries the
   same class of error. Correcting the one place it is easy to correct makes the
   model *less* uniformly calibrated, not more, and that is precisely the failure
   mode M68 found on the B plane: a partial repair that improves one term and
   silently decouples it from the others.
3. ~~**It is immaterial.**~~ **Withdrawn** (facts 33, 34). C6's comparator was
   refuted and the criterion is NOT MET on re-application. This reason no longer
   supports the recommendation and is struck rather than restated. Reasons 1 and
   2 were the primary ones and are untouched, so the recommendation **not to
   patch locally** stands on them alone.

**What changes as a result is the urgency, not the direction.** With C6 void, the
item can no longer be filed as documented-and-deliberately-unmodelled. On the
median comparator the error exceeds the project's tolerated calibration error at
**every ISO** below 12–63 DN above black (fact 34). The correct response is to
**schedule the general fix, not to reach for the local one** — and the input that
decides how urgently is whether the merge adjudicates in that signal range. **That
belongs to whoever owns the merge; it is not mine and I have not measured it.**

**What should change now, and is cheap, is the documentation.**
`noise.rs:122` currently states:

> *"The two greens are separate photosites and their read noise is independent,
> so Var(L) = (Var(G1) + Var(G2)) / 4."*

The first clause is true and the second is **measured to be false**. The prose
asserts as physics something this milestone has now falsified, which is exactly
the kind of claim that stops the next agent from checking. It should record the
measured value, the direction of the error, and the regime — that the assumption
costs up to 4.05% in σ, always in the over-confident direction, decaying to
0.16% by 100 DN, and that it exceeds the project's tolerated calibration error
below roughly 12–63 DN above black.

**If it is ever modelled**, the right object is a **spatial correlation length of
the read-domain noise**, ISO-dependent and signal-dependent, applied wherever
neighbours are pooled — not a green pair constant. That is a larger change than
this defect justifies on its own, and it should be motivated by a path where the
error is material rather than by this one.

---

## 9. Incidental, routed and not adjudicated

Two by-products of fitting `var(ISO) = α G² + δ` per plane (fact 15). Neither was
pre-registered here and I am not adjudicating either.

**Fact 31 (MEASURED).** The fit recovers `α_high = 1.38` e² → **1.175 e**, against
`profile.rs`'s `read_noise_e_high = 1.2392`, and a total of **4.41 e** at ISO 100
against `read_noise_e_low = 4.20`. Independent corroboration of the read-noise
constants from a statistic nobody fitted them to.

**Fact 32 (MEASURED).** M68 measured the B plane at 0.84× the greens' apparent
conversion gain and could not distinguish a true gain difference from a pre-ADC
scale, because a PTC ratio cannot. A dark-frame variance fit splits into a term
that scales with G² and one that does not, so it carries information a PTC ratio
does not have:

```
alpha_B / alpha_green = 0.8418          delta_B / delta_green = 0.5966
```

A single scale `s` applied to everything upstream of the ADC predicts
`α_B/α_green = s² = 0.7049` and `δ_B/δ_green = 1` — quantisation is added after
the scale and cannot be scaled by it. **Neither prediction is met.** This is
consistent with M68's own conclusion that the 0.84× acts partway along the analog
chain, and it is arrived at from a different statistic on the same frames.
**This is M68's open question and M71's evidence, and I am routing it rather than
answering it.**

---

## 10. Error log

1. **I mis-specified C0's band** by writing a permutation null that cannot be
   zero when a real correlation exists (facts 6, 7). Caught mid-sweep, audited
   with a parameter-free prediction confirmed 66 times, and the audit was
   committed before it ran. **C0 is still reported as NOT MET.**
2. **I mis-specified F1** by requiring a zero-lag value of exactly 1 from an
   estimator whose Sheppard correction guarantees otherwise (fact 24).
3. **I mis-specified F2** by comparing a 2400² crop against a full plane and
   requiring them to agree (fact 25).
4. **Two errors in my own derivation**, caught by a planted simulation before any
   corpus data was touched (facts 1, 2). One of them was a confound in my
   instrument that pointed at a specific answer.
5. **My pre-registered C2 verdict is misleading as stated** and I found that with
   a test I designed to break it (fact 21).
6. **C6 had two defects that I did not see when I wrote it, and both are worse
   than a mis-specified band** (facts 33, 34).
   - **It depended on an external input from a report still in flight.** I quoted
     M69's 19–21% as a fixed comparator. It was a number M69 was in the middle of
     refuting. A pre-registered criterion is only as durable as its inputs, and I
     hard-coded one that belonged to someone else's open question. **Cite an
     external number as a comparator only if you are willing to void your own
     verdict when it moves** — and if you are not, do not use it.
   - **It was asymmetric: only the favourable branch carried a consequence.** C6
     said what to conclude if the error was small and said *nothing* about the
     other case. I noticed the missing branch only when I needed it. That is
     discipline 496 in a second guise — I built a criterion that could only
     confirm, in the same milestone in which I caught myself doing it to C2.
     **A criterion with one branch is not a criterion.**

Three of my own gates were mis-specified — C0, F1 and F2 — and one, C6, was
sound in form but built on an input that did not hold. Each was audited with a
prediction that could fail, each audit was committed before it ran, and none of
the four audits moved a band. Four defects in one milestone is more than I would
like. Three share a single cause: **I wrote bands for idealised estimators and
then used corrected ones.** A gate should be written against the estimator that
will actually run, and its comparator should be a number you own.

---

## 11. Verdict on the question asked

**Is ρ = +0.073 real?** Yes. +0.08261, replicated by an independent estimator
against a fragile one, robust across defect arms, repeatable across sessions to
0.0005.

**Does it belong in the model?** **Not as a green covariance constant.** It is
not a green-pair property, and patching the one place it is convenient to patch
would encode a mechanism that does not exist while leaving the same error
everywhere else. **It does belong in the model eventually**, as a spatial
correlation length of the read-domain noise applied wherever neighbours are
pooled.

**Does 3.6% matter operationally?** **I do not know, and I can now say exactly
what would settle it.** The number is 4.05%, not 3.6%, at ISO 100 and zero
signal. It is over-confident everywhere and never flips sign — so it cannot push
a gate the dangerous way — and it decays to 0.16% by 100 DN. My materiality
criterion is void (facts 33, 34) and re-applying it gives NOT MET, so I am not
entitled to the word "immaterial". What remains is the regime: the error exceeds
the project's tolerated calibration error **below somewhere between 2 and 63 DN
above black**, the two available comparators disagreeing about where in that
range. **Whether the merge adjudicates down there is the deciding input, and it
is not mine.**

**The item should be closed as measured, understood and documented — and left
open as a scheduled model change rather than a deliberate omission.** Not an
artefact; not a defect awaiting a local patch; a general defect whose priority
depends on one measurement nobody has taken.

---

## 12. Amendment, after publication

§4.7 originally reported C6 as **IMMATERIAL IN PRACTICE**, and §8 and §11 leaned
on that word. The orchestrator subsequently reported that M69 had refuted the
19–21% `FOCUS_NOISE_SD` error I had used as C6's comparator, and asked me to
correct the sentence.

**The sentence was not the defect.** Correcting it voided the criterion. §4.7.1,
facts 33 and 34, §8 reason 3, §10 item 6, and this section are the result;
`src/07-materiality-recheck.py` was committed before it ran, as with every other
audit in this milestone.

**Nothing measured was changed.** Facts 16 and 18 stand exactly as published;
fact 17 is withdrawn because it quoted a threshold, not because it quoted a
measurement. The headline findings — replication, non-specificity, the
downstream mechanism location — do not touch C6 and are untouched by it.

This is the second time in two milestones that an orchestrator query about a
single sentence of mine has turned out to be load-bearing. Both times the
correction went further than asked, and both times the direction was **against**
my own published conclusion. I note it because the pattern is the useful part:
**a claim that rests on someone else's number is not my claim until I have
checked it, and I did not check this one.**
