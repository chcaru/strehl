# M48 — Which statistic is the noise model predicting, and is 1.47 e- even close?

> **NOT INDEPENDENTLY VERIFIED.** Same author as the code change and the
> measurements. Rule 12: everything below is a hypothesis until someone else
> re-runs it. What *is* independent here is narrower and worth stating
> precisely: M4's dark-sigma table was re-derived through a different decoder
> (`rawpy`, not `strehl-raw`) by an author who had not read M4's code path, and
> it reproduced. That makes M4's table verified. It does not make this report
> verified.

Every claim is labelled **MEASURED** (a number this milestone computed from
data), **DERIVED** (a consequence of measured numbers plus stated arithmetic),
or **ARGUED** (a judgement).

**Facts, disciplines and open questions below are numbered LOCALLY from 1.**
The orchestrator renumbers on fold. Cross-references inside this document use
the local numbers; references to `SYNTHESIS.md` use its global numbers and say
so explicitly.

---

## 0. The headline, before the detail

1. **The constants file never said what statistic its constants are.** That is
   the exact failure class §5's preamble names as this project's worst — the
   arithmetic was right and the column heading was wrong. It is now written
   down, at the top of `profile.rs`, with the frame count and the estimator.
   (**ARGUED** that it is that failure class; **MEASURED** that it was absent.)

2. **`read_noise_e_high = 1.47` was wrong on every basis available.** +18.4%
   against the pooled RMS, +36.5% against the mean pixel, +51.9% against the
   median pixel. It over-predicted measured dark sigma by 12.3% at ISO 400
   rising to 22.2% at ISO 1600. It is now **1.2392**. (**MEASURED**/**DERIVED**.)

3. **The basis is the pooled RMS, and that decision reverses the direction the
   brief leaned.** The brief's argument — a pooled RMS inflated by a hot-pixel
   tail desensitises the gate at every pixel to pay for a defect in a few — is
   sound in form and **false in fact on this sensor**. Two independent measured
   reasons, §2.

4. **The hot-pixel explanation of the estimator gap is refuted.** M22's entire
   recurrent map (11,393 px, 0.0346%) carries 2.2%–3.6% of temporal variance.
   Oracle excision of all of it moves the pooled RMS 1.1%–1.8% — about **one
   tenth** of the RMS/mean gap. (**MEASURED**, local fact 6.)

5. **`read_noise_e_low` deliberately stays 4.20**, and the test now asserts its
   error rather than hiding it. Its defect is a *shape* error no scalar can fix,
   and the best scalar is worse where the corpus actually shoots. §4.

6. **The additive DN noise floor survived five attacks.** Fitted across all 11
   ISOs at once it beats the shipped model shape on held-out error by 7.3x, and
   a single shared floor beats two mode-specific ones. But dark frames cannot
   break its degeneracy with a sub-proportional gain, the test I designed to
   break it has **no power**, and the experiment that would settle it depends on
   a statistic M25 already measured as unreliable. §6. **The model shape is
   unchanged, as instructed — and I would not change it on this evidence even if
   I had been asked to.**

7. **I found and disclosed a real defect in my own script 03** (`np.sort` axis).
   The first version of local fact 6 was garbage and said the opposite. §7.

---

## 1. What the constants actually are

**Local fact 1 (MEASURED).** M4 §8.1's dark-sigma table is the estimator
`rms_sd = sqrt(mean over pixels of the per-pixel temporal variance)` over **20**
frames per ISO — the owner's 22 minus the first two stabilisation shots per
directory — computed on raw integer DN with no black subtraction. Reproduced
through `rawpy` at **all 44 published cells** (4 planes x 11 ISOs) at ratios
**0.99986–0.99998**. Script `03-sigma-distribution.py`; the 4-plane-mean version
was `02-estimator-reconciliation.py` (already folded as SYNTHESIS fact 555).

This is the first end-to-end reconstruction of M4's method from its outputs
alone. M4 published values and never published its estimator; two candidate
estimators of the same data differ by up to 24%, so "the values reproduce"
was not previously a statement anyone could make.

**Local fact 2 (MEASURED).** The same 242 frames under the other two estimators,
as a fraction of the pooled RMS, 4-plane mean:

| ISO | pooled RMS (DN) | mean pixel / RMS | median pixel / RMS |
|---|---|---|---|
| 50 | 0.98652 | 0.94086 | 0.90249 |
| 100 | 0.98444 | 0.94003 | 0.90403 |
| 200 | 1.74149 | 0.90731 | 0.84416 |
| 250 | 2.16274 | 0.90118 | 0.83306 |
| 400 | 1.19854 | 0.89278 | 0.82923 |
| 500 | 1.46783 | 0.88050 | 0.80922 |
| 640 | 1.80781 | 0.86973 | 0.79063 |
| 800 | 2.24638 | 0.86068 | 0.77301 |
| 1000 | 2.80837 | 0.85835 | 0.76677 |
| 1600 | 4.40516 | 0.85389 | 0.75935 |
| 2000 | 5.53272 | 0.85601 | 0.76300 |

The gap grows with ISO and is **not small**: choosing the wrong one of these
three is a 6%–24% error before any fitting happens.

**Local fact 3 (DERIVED).** The per-pixel temporal sigma distribution widens
with ISO. From `mean_sd/rms_sd` and the unbiasing constant `c4(20) = 0.98693`,
the coefficient of variation of per-pixel sigma is **0.32 at ISO 100** rising to
**0.58 at ISO 1600**. Independently, **MEASURED**: the 99th-percentile pixel
sits at **2.5x** the median at ISO 100 and **4.3x** at ISO 1600.

**No scalar on any basis represents that distribution.** This is the honest
statement of the problem, and §3 says what to do about it.

---

## 2. The decision: pooled RMS, on measured grounds

The brief asked me to argue it both ways. Here is the case against the pooled
RMS, in its strongest form, followed by why it loses on this sensor.

**The case against (ARGUED, and it is a good argument).** A pooled RMS is a
second-moment average: a small number of very bad pixels moves it a lot. The
merge gate compares a *per-pixel* focus response against a *per-pixel* predicted
sigma. If the predicted sigma is inflated by pixels that are not representative,
the gate is desensitised everywhere to pay for a defect in a tiny minority — and
this project already treats static defects as a separate concern with its own
map (M22) and its own milestone (M29). Under that reading the mean pixel is the
right basis and the pooled RMS is double-counting a problem that is handled
elsewhere.

**Why it loses, reason 1 (MEASURED + DERIVED). The consumer averages, and the
gate is calibrated on a fluctuation, not on a level.** Following the actual code
path: `FocusField::compute` divides a 27x27 windowed mean of `|grad|` by the
model's sigma; `merge::regularise` averages that again over 17x17; `merge::Gate`
then compares response *differences* against the single scalar
`sqrt(2) * FOCUS_NOISE_SD`. The combined support is 43x43 = 1849 px. For a mean
over pixels with unequal variances, the *level* scales with the mean sigma but
the *standard deviation* scales as `sqrt(mean variance)/sqrt(N_eff)` — and
`FOCUS_NOISE_SD` is a standard deviation. Mean variance is exactly the pooled
RMS squared.

Normalising by the mean pixel instead would therefore leave the real response
**6.3% noisier at ISO 50 and 17.1% noisier at ISO 1600** than `FOCUS_NOISE_SD`
asserts, i.e. the gate would be that much too tight, and progressively worse
with ISO. (**DERIVED** from local fact 2: `1/0.94086 - 1` and `1/0.85389 - 1`.)

I want to be exact about the strength of this. The `sqrt(mean variance)` result
is exact for a mean of independent zero-mean variables. `|grad|` is neither
zero-mean nor independent across the window. So this is a **leading-order**
argument, not an identity — I verified the code path by reading it, and the
statistical claim analytically, but I did **not** measure the fluctuation of
`FocusField` output on real darks at two ISOs. That measurement is local open
question 2 and it would settle the point empirically.

**Why it loses, reason 2 (MEASURED, and this one is decisive). The typical-pixel
basis cannot be delivered, because there is no tail to hand off.**

| ISO | var carried by M22's map (0.0346%) | pooled RMS after oracle excision | fraction of every plane needed to reach mean pixel |
|---|---|---|---|
| 50 | 2.18% | −1.08% | 0.640% |
| 100 | 2.20% | −1.09% | 0.642% |
| 400 | 3.19% | −1.59% | 0.849% |
| 1000 | 3.56% | −1.77% | 1.165% |
| 1600 | 3.59% | −1.79% | 1.232% |

**Local fact 4 (MEASURED).** M22's entire recurrent hot-pixel map carries
2.18%–3.59% of the temporal variance.

**Local fact 5 (MEASURED).** Excising every pixel in that map — an *oracle*
excision, better than any runtime map can do — moves the pooled RMS by **1.1% to
1.8%**, against an RMS/mean gap of 5.9%–14.6%. **The hot pixels explain about
one tenth of the estimator gap.**

**Local fact 6 (MEASURED).** To bring the pooled RMS down to the mean pixel you
must excise **0.64% of every plane at ISO 50, rising to 1.23% at ISO 1600** —
18x to 36x the size of M22's map. That is not a defect set; that is the upper
tail of an ordinary distribution.

So the premise of the case against is false here. The pooled RMS is not inflated
by a handful of hot pixels that M29 will remove. It is higher than the mean pixel
because **per-pixel sigma has a genuinely wide distribution** (local fact 3), and
that width is a property of the sensor, not a defect list. Re-basing onto the
mean pixel would not "hand the tail to M29" — it would simply under-predict the
noise of every average the pipeline takes.

**Decision (ARGUED, on the above MEASURED grounds): pooled RMS.** Written into
the `profile.rs` module header with the estimator, the frame count, the dropped
stabilisation frames and the DN convention, so the next person fitting a constant
to it knows what they are fitting to.

---

## 3. Is a distribution the honest answer? Yes — and it is a field, not a scalar

**Local fact 7 (ARGUED, on local fact 3's MEASURED width).** The honest object is
not a scalar of any flavour and not a distribution either: it is a **per-pixel
sigma field**, `sigma_read(x, y)`, the same shape as the sensor. A distribution
alone would still be wrong per-pixel — it would say "17% of pixels are 1.3x
noisier" without saying *which*, which is exactly the information the gate needs
and the only information that makes the correction actionable.

The data to build one already exists: 242 darks, 20+ per ISO, which is enough for
a per-pixel sigma estimate with ~16% standard error per pixel per ISO, and much
better if the ISO dependence is fitted per pixel rather than estimated
independently.

**Scoped, not built** — the brief says so and I agree with the reasoning. It
would change `NoiseModel` from a handful of scalars into a resource with a
storage format, a provenance story, a per-body calibration workflow and a
fallback when the field is absent. That is a milestone, not a constant. Local
open question 1.

What I will say against my own recommendation: the width of the sigma
distribution (local fact 3) is not by itself evidence that a *field* would
improve merge decisions, because the merge gate acts on a 43x43 average where
per-pixel variation is already substantially averaged out. The case for the
field is strongest for per-pixel operations, weakest for the gate as it stands
today. I did not measure the end-to-end benefit and it may be small.

---

## 4. The constants

**Local fact 8 (DERIVED).** With `S = 0` a dark frame gives `RN_e = sigma_DN / g`
directly, using the gain the code actually uses, `g = max(iso, base_iso)/436.8`:

| ISO | sigma_DN | implied RN_e | vs shipped 1.2392 / 4.20 |
|---|---|---|---|
| 50 | 0.98652 | 4.3091 | −2.53% |
| 100 | 0.98444 | 4.3000 | −2.33% |
| 200 | 1.74149 | 3.8034 | +10.43% |
| 250 | 2.16274 | 3.7787 | +11.15% |
| 400 | 1.19854 | 1.3088 | −5.32% |
| 500 | 1.46783 | 1.2823 | −3.36% |
| 640 | 1.80781 | 1.2338 | +0.44% |
| 800 | 2.24638 | 1.2265 | +1.04% |
| 1000 | 2.80837 | 1.2267 | +1.02% |
| 1600 | 4.40516 | 1.2026 | +3.05% |
| 2000 | 5.53272 | 1.2083 | +2.56% |

**Local fact 9 (DERIVED). `read_noise_e_high` = 1.2392.** This is
`argmin_RN sum_i (RN/RN_i − 1)^2` over the seven high-mode ISOs — **relative**
least squares, because sigma spans 4.6x across the mode and an absolute fit would
be decided by ISO 2000 alone. Closed form `sum(1/RN_i) / sum(1/RN_i^2)` =
1.23923192; grid search over 1.0–1.5 at 2e-4 agrees. The unweighted mean of the
seven, 1.2413, is 0.17% away — I mention it because that is the number the brief
quoted and they are not the same estimator.

**Only the first two digits are physical.** The residual spread across the mode
is ±5.3%. The remaining digits are carried so the fit is reproducible and so the
regression test can assert the derivation rather than a rounding.

**Local fact 10 (MEASURED, against the shipped value). 1.47 was wrong on every
basis:** +18.4% on the pooled RMS, +36.5% on the mean pixel, +51.9% on the
median. There is no estimator of this data under which 1.47 was defensible. The
shipped model over-predicted measured dark sigma by +12.3% at ISO 400, +14.6% at
500, +19.1% at 640, +19.9% at 800, +19.8% at 1000, +22.2% at 1600, +21.7% at
2000.

**Local fact 11 (DERIVED). `read_noise_e_low` stays 4.20, deliberately.** The
implied read noise *falls monotonically* by 12% from ISO 100 to ISO 250. That is
not scatter about a constant, it is a **shape** error, and no scalar fixes it.
The relative-LS optimum, 4.0153, gives −6.8% / −6.6% / +5.6% / +6.3%, against
4.20's −2.5% / −2.3% / +10.4% / +11.1%. Re-fitting would buy a smaller worst case
at ISO 200/250 — which **no capture in the corpus uses** — and pay 4.3
percentage points of accuracy at ISO 50 and 100, where every real stack lives
(M25 fact 200: `119MSDCF` ISO 50, `coffee-bean` ISO 50, `109MSDCF` ISO 160).

**ARGUED:** changing it would look like progress and would make the pipeline
worse. The error is asserted at its wrong value instead (§5), so the moment
someone fixes the shape, the test tells them.

**Local fact 12 (DERIVED, and it bounds how much any of this matters).** The
blast radius of the constant change itself is small. Going 1.47 → 1.2392 moves
total predicted sigma by more than 2% only below **S ≈ 12.8 DN above black** at
ISO 400, and below **S ≈ 51 DN** at ISO 1600. Separately, the read term is a
>2% contributor to total sigma only below **S ≈ 35 DN** at ISO 400, and it equals
shot noise at **S = 1.4 DN** (ISO 400) and **S = 4.0 DN** (ISO 100).

**This constant governs the deep-shadow end and essentially nothing else.** A
+18% error in it is a serious defect in the noise model's *honesty* — and a
small one in most pixels' predicted sigma. I would rather say that here than
have a reader discover it and conclude the rest of this report was oversold.
The case for fixing it is that a constant nobody can trace to a statistic is a
constant nobody can re-fit, not that the pixels were visibly wrong.

---

## 5. The tests — rule 30, no carve-outs

Three tests in `crates/strehl-core/src/profile.rs`.

**`the_model_is_checked_against_measured_dark_sigma_at_every_iso`.** The shipped
model against measured pooled-RMS dark sigma at **all eleven ISOs**, tolerance
0.1% on the model/measured ratio. The two knowingly-wrong low-mode rows (ISO 200:
+10.4%, ISO 250: +11.1%) are asserted **at their expected wrong values** with a
comment naming the cause and naming what would fix it. Nothing is excluded.

This is the direct answer to rule 30's origin: M25's dark-noise self-test
excluded ISO 50 *because the model was known to be wrong there*, and thereby
silenced the only assertion that would have caught a 2x gain defect. Carrying the
wrong value as an expectation costs one comment and keeps the coverage.

**`the_iso_50_and_iso_100_darks_imply_the_same_read_noise`** — local fact 13
(**DERIVED**). ISO 50 is an extended/pull setting, so it reads out at ISO 100's
gain and the two must imply the same electron read noise. Under `base_iso` they
do: 4.3091 vs 4.3000, **+0.21%**. The test asserts <1%.

It also carries a **placebo**, per rule 20: the same two measurements under the
marked-ISO relation `g = 50/436.8` imply 8.6183 vs 4.3000, a ratio of **2.004**,
and the test asserts that ratio is still >1.9. Without the placebo the first
assertion could pass on an identity rather than on the fix. M4 §8.3 published
exactly that 8.62 e- and called it "visibly nonsense … the tell" — this makes
that observation a permanent guard for the cost of three lines.

**`the_high_mode_read_noise_is_the_relative_least_squares_optimum`.** Recovers
the constant by brute-force grid search from the measured table, so the
*derivation* is tested and not just the number, and pins the ±5.3% residual
spread that says how many digits mean anything.

---

## 6. Finding 5 — I tried to kill the DN noise floor and failed

The hypothesis: `sigma_DN^2 = (RN_e * g)^2 + floor^2`, i.e. a constant additive
noise term in the DN domain, downstream of the analogue gain. Fitted across
**all 11 ISOs simultaneously** (not anchored on endpoints), by relative least
squares, on both bases.

Models: **M0** pure `RN_e * g` with two read noises (the shipped shape); **M1**
two read noises + **one shared floor**; **M2** two read noises + **two
mode-specific floors**; **M3** the confound — `sigma_DN = a * ISO^p` per mode
with a shared exponent, i.e. gain sub-proportional to marked ISO, at the *same
parameter count as M1*.

**Local fact 14 (MEASURED, pooled-RMS basis).**

| model | params | rms rel resid | worst | AIC | LOO-CV held-out rms |
|---|---|---|---|---|---|
| M0 pure RN | 2 | 4.454% | 6.82% | −64.45 | **5.731%** |
| M1 shared floor | 3 | 0.577% | 0.96% | −107.40 | **0.781%** |
| M2 two floors | 4 | 0.489% | 0.89% | −109.04 | **0.721%** |
| M3 power law | 3 | 2.556% | 3.78% | −74.67 | **3.718%** |

**The floor survives all five attacks:**

1. *Fit everything at once, don't anchor.* Worst residual 6.82% → **0.96%**.
2. *Punish the extra parameter.* AIC −64.4 → **−107.4**. F(M0→M1) = **468**,
   p = **2.2e-8**.
3. *Hold data out.* Leave-one-ISO-out held-out error 5.73% → **0.78%**, a 7.3x
   improvement. This is the attack I expected to kill it and it did not.
4. *Ask whether one floor or two.* F(M1→M2) = **2.75, p = 0.14**; LOO 0.72% vs
   0.78% — a tie. **A single shared floor beats two mode-specific ones**, which
   is the answer the brief asked for, and it is the parsimonious one.
5. *Try the obvious confound at equal cost.* M3 loses badly: LOO **3.72%** vs
   0.78%, AIC −74.7 vs −107.4.

**Local fact 15 (MEASURED).** Shared floor **0.5099 ± 0.0128 DN** (pooled-RMS
basis) and **0.5411 ± 0.0103 DN** (mean-pixel basis), standard errors by both
Jacobian and delete-one-ISO jackknife (they agree to ~10%). The floor is
**17.3 sigma** (RMS) and **24.6 sigma** (mean) above the **0.2887 DN** that
14-bit quantisation alone would produce. Under M1, `RN_lo = 3.666`,
`RN_hi = 1.196`.

The conclusion is basis-independent, which is worth noting: the floor is *not*
an artefact of choosing the pooled RMS.

### 6.1 Why this is not enough to change the model

**Local fact 16 (ARGUED, and this is the important part of §6).** Dark frames
**cannot** distinguish an additive post-gain DN term from a gain that is
sub-proportional to marked ISO. Both bend `sigma_DN` the same way. M1 beating M3
shows the *specific* power-law form loses; it does not show no gain relation
fits. This is discipline 289's general form and it is not broken by anything I
did.

**Local fact 17 (MEASURED, and it is a negative result about my own test).** The
per-plane test that could break the degeneracy **has no power**. The two
hypotheses predict per-plane ISO-2000 sigma ratios at most **7.9%** apart, and
the measured ratio standard error is **2.6%–4.4%**. Z-scores against the floor
hypothesis: R **+0.48**, G1 **+0.06**, B **−2.67**. The one significant cell
points **away** from the floor. Per-plane floors: R 0.5314, G1 0.5237, G2 0.5229,
B **0.4614** — the B plane is 12% below the others and the least well determined.

I designed this test expecting it to discriminate. It does not. Reporting it as
"consistent with the floor" would be exactly the metric-validity failure this
milestone is about: three of four cells are consistent with *both* hypotheses
because the test cannot tell them apart, and the fourth disagrees.

**Local fact 18 (ARGUED, with a caveat that nearly kills it). The candidate
discriminator is a photon-transfer curve at two ISOs *inside one gain mode*.**
An additive DN floor moves the PTC **intercept**; a gain error moves the
**slope**. They are orthogonal there, and degenerate in darks. M25 already has
the code (`16-iso50-gain.py`) and closed SYNTHESIS §10 item 8 with it.

**But M25 measured that its own PTC intercept is not trustworthy**, and said so
explicitly: the intercept "is inflated by residual scene texture (it implies
6.9 e- read noise at ISO 160 against fact 14's 4.20 e-), so this measurement
says nothing about `RN_e`". My proposed test leans on precisely the quantity
M25 found unreliable. I nearly published this recommendation without checking
that, which would have been the same class of error this milestone is about.

The recommendation survives only in a modified form, and the modification is
standard practice rather than an invention: **compute the PTC from the
difference of two nominally identical frames** of the same scene. Differencing
cancels scene texture and fixed-pattern noise exactly, leaving `2 x` the
temporal variance, which is what a PTC intercept is supposed to measure. M25's
single-frame spatial-variance estimator cannot do this, so it is a new script,
not a re-run — and it needs a capture the corpus may not contain (two exposures
of a static scene at each of two in-mode ISOs). **That, not the fit quality, is
the real cost of settling question 129.**

**Local fact 19 (ARGUED, and weaker than it first looks — recorded with its own
refutation).** M25 fact 200 measured `g` at ISO 160 as **−10.7%** against
`ISO/436.8` and attributed it to estimator calibration. A pure-gain explanation
of the low-mode curvature would need `g(200)/g(100) = 1.769` instead of 2.0,
i.e. **−11.5%**. Same sign, same magnitude, and it is tempting to call it one
effect seen twice.

**I do not think that holds, and here is why.** M3's fitted exponent (0.9263)
predicts `g(160)/g(100) = 1.6^0.9263 = 1.546`, only **−2.8%** below the
relation — a *quarter* of M25's −10.7%. The two numbers are the same size by
coincidence of framing: M25's is an **absolute** deviation of one measurement
from a relation, mine is a **shape** deviation of a ratio. A constant
multiplicative bias in M25's 5th-percentile variance estimator would produce the
former and leave the latter untouched, and M25 has only **one** in-mode ISO, so
it cannot separate bias from shape at all.

This is a further argument for the two-in-mode-ISO design in local fact 18: the
**ratio** of two in-mode PTC slopes cancels any constant estimator bias, which
is exactly what one ISO cannot do. I am recording local fact 19 mainly so that
nobody else spends an evening on the coincidence I spent one on.

**Verdict: the model shape does not change in this milestone** — the brief said
report only, and I agree independently: the evidence is strong and the
degeneracy is unbroken, and shipping a three-parameter model on the strength of a
degenerate fit is how you get a constant that is +18% for two years.

**What it would cost if adopted (ARGUED):** one `f32` in `CameraProfile`, one
term in `NoiseModel::variance`, a re-fit of both read noises (3.666 / 1.196), and
a re-derivation of every constant calibrated against the current shape —
including `FOCUS_NOISE_SD`, which is fitted through the noise model and is owned
by another milestone. It is not a one-line change and it should not be made
until the PTC test is done.

---

## 7. What I got wrong, and how I found it

**Local fact 20 (MEASURED — my own defect).** Script `03-sigma-distribution.py`
computes its variance-concentration and excision fields with `np.sort(var)` on a
**2-D per-plane array**. `np.sort` defaults to `axis=-1`, so it sorted each row
independently; the following `np.cumsum` then flattened. Every
concentration and excision number in that file's `var_frac_top`,
`var_frac_top4`, `rms_excised`, `rms_excised4` fields is **wrong**.

**Its first answer was not merely noisy, it was the opposite of the truth.** It
reported the top 0.0346% of pixels carrying **0.04%** of variance, from which I
briefly concluded the tail story was refuted outright. The correct figure is
**2.18%–3.59%** — a factor of ~80. I found it by disbelieving a number that was
*too* clean and re-deriving it on a 4x5 probe array where I could check the
answer by hand.

Handling, per rule 15: script 03 is **left exactly as it ran**. The correction is
a new numbered script, `04-variance-concentration.py`, and its JSON carries a
`supersedes` field naming the four dead fields by name. Every other field in 03
is correct — `rms_sd`, `mean_sd`, `median_sd`, the percentiles and the max are
reductions that flatten by default — and 03 remains the source of the 44-cell
verification of M4.

**Local fact 21 (a correction to the brief that commissioned this work).** The
brief's Finding 2 stated that the RMS/mean gap "tracks the hot-pixel tail". The
*correlation* is real — both grow with ISO — but the tail is **not the
mechanism**: it accounts for roughly one tenth of the gap (local facts 4–6). The
mechanism is the ordinary width of the per-pixel sigma distribution (local fact
3). This matters because the tail story implies the gap is someone else's problem
to remove, and it is not: it is a permanent property of the sensor.

**Everything else in the brief reproduced.** Findings 1, 3 and 4 I recomputed
independently and they were correct to the digits given. Finding 5 I attacked
five ways and could not kill.

**Local fact 22 (a near-miss I caught on the last pass, recorded because the
process matters more than the outcome).** I had written local fact 18's
recommendation — settle the floor with a photon-transfer curve — and was about
to ship it when I re-read M25 fact 200's caveat and found that M25 had
*already measured* its PTC intercept to be untrustworthy on textured scenes.
My recommendation rested on the one quantity the existing tool cannot deliver.
The fix (difference two frames) is standard and the recommendation survives in
modified form, but it survives because I checked a citation I had already used
twice, not because I reasoned carefully. **The citation I had used twice was
the one that refuted me.** Local discipline 8.

**What I did not verify (stated plainly):**

- I did **not** measure the fluctuation of `FocusField` output on real darks at
  two ISOs. §2's reason 1 is analytic plus a code reading, not a measurement.
  It is the weaker of the two reasons and I have not hidden that.
- I did **not** re-derive `FOCUS_NOISE_SD` under the new constant. It was
  calibrated through the noise model, so a −18% change in `read_noise_e_high`
  may perturb it. It is owned by another milestone and I did not touch it.
  **This is the most likely place for my change to have an unintended
  consequence.** Local open question 3.
- I did **not** confirm the 20-frame estimator is unbiased for the *max* and
  *p99* statistics quoted in local fact 3; with 20 samples the upper percentiles
  of an estimated-sigma distribution are inflated by estimation noise. The CV
  figure is unbiasing-corrected (`c4(20)`); the percentile ratios are not.
- The medians in `dark-sigma.json` repeat *exactly* across R/G1/G2 planes
  (0.9119095…). That is a quantisation artefact of taking a median of 20 integer
  samples, not a bug, but it means median-basis figures are the least trustworthy
  of the three and I did not build on them.

---

## 8. The negative control

Rule 20. Backed `profile.rs` up to `$env:TEMP`, reverted **only** the constant to
1.47 leaving the tests intact, touched the file to defeat cargo's same-second
mtime staleness, and confirmed a `Compiling` line appeared.

**Result: three tests went red**, with
`the_model_is_checked_against_measured_dark_sigma_at_every_iso` reporting
`ISO 400: model 1.3461539 DN / measured 1.198538 DN = 1.1231633, expected
0.94682 (+12.32% vs -5.32%)` — which independently reproduces the brief's +12.3%
figure through the shipped Rust code path rather than through Python.

**`the_iso_50_and_iso_100_darks_imply_the_same_read_noise` correctly stayed
green**, because it is a guard on `base_iso` and does not depend on
`read_noise_e_high`. A negative control that reddens *everything* would have told
me the tests were coupled.

Restored **from the temp backup** (SHA-256 prefix `33D12591E576AB75` verified
identical before and after), never `git checkout --`.

---

## 9. Proposed disciplines (numbered locally from 1)

**Local discipline 1.** *A constant fitted to a measured statistic must name the
statistic, the sample size and the domain, next to the constant.* Not in the
research doc — next to the constant, where the next person to change it will
read it. Two candidate estimators of the same darks differ by up to 24% here, so
"fitted to M4 §8.1" was never enough information to re-fit against.

**Local discipline 2.** *When a downstream consumer averages over a window, the
noise statistic it needs is the one governing the fluctuation of that average
(the mean variance), not the one describing a typical element.* Choosing the
"more representative" statistic makes the calibration wrong in the direction
that tightens gates.

**Local discipline 3.** *Before attributing a distributional gap to a tail, measure
what fraction of the moment the tail carries and what excising it does.* Mine
carried a tenth of what the story required. The story was plausible, the
correlation with ISO was real, and it was still the wrong mechanism.

**Local discipline 4.** *A model-selection result is not evidence until the
alternative is fitted at equal parameter count and both are scored out of
sample.* In-sample residuals said the floor won by 7.7x; that is partly the free
parameter buying itself a fit. LOO-CV said 7.3x and M3 at equal parameter count
said 4.8x — those are the numbers worth quoting, and only the second one is a
statement about model *shape* rather than about model *size*.

**Local discipline 5.** *State a test's power before its result.* My per-plane
discrimination test separates hypotheses 7.9% apart with a 2.6%–4.4% standard
error. Had I reported "three of four planes consistent with the floor" without
that, I would have manufactured support out of an inability to measure.

**Local discipline 6.** *`np.sort`, `np.cumsum`, `np.argsort` and friends have
default axis behaviour that differs between them* — `sort` keeps shape and sorts
the last axis, `cumsum` flattens. Any reduction over a multi-dimensional array
must state its axis explicitly. (Rule 23's general form; this is the second
instance in this project.)

**Local discipline 7.** *A known-wrong model value should be asserted at its
wrong value, not excluded from the test.* Exclusion silences the assertion
forever; assertion at the wrong value costs one comment and fails loudly the day
someone improves the model — which is precisely when you want to know.

**Local discipline 8.** *When you recommend an experiment, re-read what the last
milestone measured about that experiment's estimator before recommending it.* A
prior milestone had already found the exact statistic my proposed test depends
on to be unreliable, and had written it down, in a document I had cited twice
for other numbers. Citing a document is not reading it.

---

## 10. Open questions (numbered locally from 1)

**Local question 1.** Should `NoiseModel` carry a **per-pixel sigma field**
rather than scalars? Per-pixel sigma has CV 0.32→0.58 and no scalar represents
that. The 242 delivered darks are already sufficient to build one. Cost: a
storage format, a provenance story, a per-body calibration step, a fallback when
absent. Benefit unmeasured, and plausibly small for the 43x43-averaged merge gate
specifically. **Recommend: measure the benefit before building it** — simulate
the gate with a real sigma field vs a scalar and see if any decision changes.

**Local question 2.** Measure the fluctuation of `FocusField` output on real
darks at two ISOs and confirm it scales with the pooled RMS rather than the mean
pixel. This converts §2's stronger-in-theory argument into a measurement. Cheap:
the darks are on disk and the operator is already exposed.

**Local question 3.** Does `FOCUS_NOISE_SD = 0.015214` need re-deriving now that
`read_noise_e_high` moved 18%? It was calibrated through the noise model. I did
not touch it (it is in `merge.rs`, owned by another milestone) and I did not
measure the sensitivity. **This is the outstanding risk from my change.**

**Local question 4.** Four files hard-code **1.47** as a *test fixture*:
`noise.rs` (8 occurrences), `focus.rs:287`, `strehl-plugin/src/measure.rs:340`,
`strehl-core/examples/focus-window-cost.rs:50`. None is a shipped constant, and
all still pass. Two observations. First, they are now fixtures asserting a value
the profile no longer holds. Second, `noise.rs` pairs `1.47` with `g = 0.229`,
which is the ISO-**100** gain — a combination the profile has never produced,
since 1.47 was the ISO-400-and-above value. They are arbitrary numbers wearing
the costume of measured ones. Updating them risks perturbing constants other
milestones calibrated against them, so I left them. They should be reconciled
deliberately, in one pass, by whoever owns `FOCUS_NOISE_SD`.

**Local question 5.** Run a **differenced-frame** photon-transfer test at two
ISOs inside one gain mode, to settle the DN floor (local facts 18 and 19). This
is the highest-value follow-up in this report: it resolves question 129, and the
slope *ratio* also settles whether M25's −10.7% ISO-160 deviation is estimator
bias or real gain shape. It likely needs a capture the corpus does not have —
two exposures of a static scene at each of two in-mode ISOs — which makes it an
owner request, not a re-analysis.

**Local question 6.** The B plane's fitted floor (0.4614 DN) is 12% below R/G1/G2
(0.523–0.531) and it is the only plane whose ISO-2000 behaviour disagrees with the
floor hypothesis at all (z = −2.67). Is that a real per-plane difference — B has
the lowest quantum efficiency and different amplifier loading — or the noisiest
plane's noise? Unresolved and unresolvable from darks.

**Local question 7 (would have asked the owner).** Is the corpus ever going to be
shot in the ISO 200–250 range? My decision to leave `read_noise_e_low` at 4.20
trades +11% error there for −2.3% at ISO 50/100 and rests entirely on M25 fact
200's answer that real stacks are ISO 50 and ISO 160. If ISO 200 captures appear,
the trade should be revisited — and the honest fix is the floor, not a re-fitted
scalar.

**Local question 8 (would have asked the owner).** M4 §8.1's estimator drops the
first two frames per directory. I reproduced that convention because it
reproduces M4 to 0.9999 (and including all 22 frames gives 1.0004 with 57x the
spread), but I never found it *documented* — I inferred it from the outputs. Was
it deliberate, and is it the right convention for a future re-capture?

---

## 11. How to reproduce

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
$env:PYTHONIOENCODING = 'utf-8'
cd C:\dev\blog\death-of-software\projects\strehl\experiments\m48-noise-floor
python src\03-sigma-distribution.py       # ~7 min, 242 raws; NOTE the defect in §7
python src\04-variance-concentration.py   # ~7 min, supersedes 03's 4 bad fields
python src\05-read-noise-fit.py           # instant, reads JSON only
python src\06-floor-uncertainty.py        # instant, reads JSON only
```

Scripts 03 and 04 read `D:\macro-dark-frames` read-only. 05 and 06 consume the
JSON from 02–04 and touch no raws.

```powershell
cd C:\dev\blog\death-of-software\projects\strehl
cargo test --workspace                                  # 187 passing
cargo fmt --all -- --check                              # clean
cargo clippy --workspace --all-targets -- -D warnings   # clean
```

Commits: `f95f6f4` (the constant, the estimator decision, the three tests),
`df76014` (scripts 03–06 and their data), on top of the already-folded `4f7f683`
(scripts 01–02).
