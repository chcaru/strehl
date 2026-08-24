# M91 — pre-registration: should per-frame photometric normalisation be applied to the merged image, and in what form?

> **Written and committed before any arm was run.** Nothing below was edited
> after a number was read. Where a criterion had to be added later it is in a
> dated addendum section that says so in its own heading, per the project's
> convention (M60 §0.6, M60b §0.1).

---

## 0. What the corpus already says, read at source

Rule 40 discharge. Search run before writing this file:

```
Select-String -Path docs\research\*.md -Pattern 'photometric' -CaseSensitive:$false
  | Group-Object Filename
```

24 files match. The ones that carry the question, all read end to end:

| source | what it settles |
|---|---|
| `M24-photometric-drift-measured.md` | drift is real (0.91% / 2.88% / 6.84% / 8.93% / 11.70% ptp); EXIF does not predict it; **§5 leaves BOTH the offset question and spatial uniformity unmeasured, in as many words** |
| `M28-robustness-mask-measured.md` §6 | *how* to fit the gain: the mean over all pixels, never a median over a subject-centred region (fact 225) |
| `M60-robustness-mask-at-merge-time.md` F2/F3 | the gain-only correction removes **7.1%** of `109MSDCF`'s chi2 excess and is **negative** on both drifting stacks (−22.5% `coffee-bubbles`, −2.4% `foam`). **F3 asserts fact 225's own estimator absorbs focus into gain on a focus stack, and names the missing estimator: "fitted on pixels the sweep does not move, and nobody has one."** |
| `M60-prior-art-and-the-rival-explanations.md` §4.2, G6, G7 | ran gain-only / affine-LS / offset-only at merge time on 3 stacks. Affine passed at 94.8% on `foam` and **the pass is void**: fitted slope 0.1605..0.5783 against an admissible \|s−1\| ≲ 0.11, and `sqrt(2.1820/23.8430) = 0.3025` sits inside the fitted slope range. Offset-only recovers 0.3% / 7.6% / 5.0%. **G7 answers M24 §5 "no".** |
| SYNTHESIS facts 180, 181, 608, 626, 704 | drift measured; EXIF blind; the ordering rule (`c^2 * var` on unscaled DN); fittability (1.90% against EXIF); 0.15% of gain saturates a ±0.003 decision threshold |
| `crates/strehl-core/src/focus.rs:309-330` | a per-frame gain moves the *normalised* focus response by `sqrt(g)`, with a unit test |
| `crates/strehl-core/src/merge.rs:653-691` | `fold_censored_probing_photometry` applies `L' = L*s + o` **to the disagreement accumulator only**; its doc comment says *"this cannot change the merged image"* |
| `crates/strehl-cli/src/merge_cmd.rs:1872-1945` | prints a DERIVED sensitivity and closes with *"is NOT evidence that photometric variation is handled"* |

**Two absences, each asserted here only with the search that establishes it
(rule 43).**

1. **No merged image has ever been produced with or without a photometric
   correction.** Established by two independent statements in the corpus, both
   read at source: `M28-robustness-mask-measured.md` §8 — *"No merge output was
   produced. This measures a detector, not the effect of masking on a merged
   image"*; `M60-prior-art-and-the-rival-explanations.md` §5 item 4 — *"Nobody
   has produced a merged image either way. M28 §8 says so; M60 §8 C4 says so."*
   Plus the grep above, whose only merge-image-adjacent hits are those two files.
2. **Spatial uniformity of the drift has never been measured.** `M24` §5,
   verbatim: *"Whether a single global gain per frame suffices, or an offset
   term is also needed, is unmeasured — **as is whether the variation is
   spatially uniform**."* The grep above returns no other file that measures a
   per-block or per-region photometric fit.

**Consequence for this milestone's shape, stated before running anything.** The
orchestrator's brief presents M24 §5's headline as open. It is **half** open.
M60b closed the *disagreement-statistic* limb in the negative on three stacks.
What remains open, and what M91 therefore measures, is:

* the limb M60b explicitly could not reach — **the merged image**;
* the estimator M60b F3 said does not exist — one that defocus cannot move;
* M24 §5's second clause — **spatial uniformity**, never measured;
* three stacks the merge-time arms have never seen, including `coffee-bean`,
  the worst drift in the corpus at 11.70%.

---

## 1. The physics, fixed in advance

Frame `k` observes `L_k(i) = a_k * S(i) + b_k + n_k(i)` in black-subtracted DN,
with `S` the common scene, `a_k` a per-frame gain and `b_k` a per-frame offset.
The correction is `L'_k = c_k * L_k + o_k`, and the merge's job is to estimate
`S`.

**Fact 608 is binding and is applied as follows.** The noise model is evaluated
on the frame's **own unscaled DN**, `var_k = sigma^2(L_k)`, and the corrected
sample carries `var(c_k L_k) = c_k^2 * var_k`. Two consequences are registered
here as DERIVED predictions before measurement:

* **P-a.** In the shot-limited regime `sigma ~ sqrt(S)`, so `sigma(cL) = c
  sigma(L)` **only when the model is fed the scaled DN**. Feeding it the scaled
  DN is what makes `focus.rs`'s normalised response move by `sqrt(c)`. Under
  fact 608's ordering the focus field is computed on unscaled DN and is
  therefore **exactly invariant** to the correction. *This half is arithmetic,
  not evidence (rule 20): I am computing the field on the unscaled buffer, so of
  course it does not move. It is registered so that the report cannot later
  present it as a finding.* The evidential half is P-b.
* **P-b.** Under the **naive** ordering (scale the DN, then run the noise model
  on the scaled DN) the normalised response must move by `sqrt(c)`. Registered
  bar: the measured mean response ratio must agree with `sqrt(mean c)` to within
  **10%**. If it does not, my account of the mechanism is wrong and the naive
  arm's numbers are void.

The optimal combination of the corrected samples is inverse-variance weighted,
`w_k = 1 / (c_k^2 * var_k)`. The shipped merge uses an unweighted mean. **Both
weightings are run** (`W0` equal, `W1` fact-608 inverse-variance), because
"which functional form" has a weighting axis as well as a gain/offset axis.

---

## 2. Fitting forms under test

Reference `R(i)` = per-pixel mean over all frames of the stack. Block grid:
disjoint `32 x 32` plane-pixel blocks over the full plane (`109 x 73 = 7957`
blocks on a `3516 x 2344` plane), each block's mean signal accumulated per
frame.

| id | form | fit |
|---|---|---|
| `F1` | gain, mean-ratio | `c_k = grandmean / mean_k`, `o_k = 0` — **fact 225 / M28 §6's prescription** |
| `F2` | gain, least squares through origin | `c_k = Σ L R / Σ L²`, `o_k = 0` |
| `F3` | affine, ordinary least squares | `R ~ c_k L + o_k` — M60's A4 form |
| `F4` | offset only | `c_k = 1`, `o_k = grandmean − mean_k` — M60's A4b form |
| `F5` | gain, **block-median** | `c_k = median_b (R_b / L_{k,b})` over blocks — **new** |
| `F6` | affine, **block least squares** | OLS of `R_b` on `L_{k,b}` over blocks — **new** |

`F5`/`F6` are the estimator M60b F3 says does not exist, and the argument for
them is registered here before they are run: **a normalised blur conserves
light**, so a block mean over a window much larger than the defocus kernel is
nearly defocus-invariant, while a genuine photometric gain moves every block by
the same factor. Their known failure modes, stated now: focus breathing changes
magnification and so moves content across block boundaries; a block containing a
large specular highlight that clips is not conserved.

---

## 3. Criteria, with the numbers fixed now

### C1 — does the offset term earn its place? (M24 §5's headline)

**Held-out design.** Blocks are split by checkerboard parity of `(bx + by)`.
Every parameter is fitted on the **even** blocks only, and the residual
`Σ_k Σ_{b in odd} (R_b − (c_k L_{k,b} + o_k))^2` is evaluated on the **odd**
blocks only. Held-out, so the extra parameter is not free.

* **C1 is MET (the offset ships)** if `F6` reduces held-out residual RMS by
  **≥ 5.0%** relative to `F5` on **at least 3 of the 6 stacks**.
* **C1 FAILS (gain-only ships)** otherwise.
* 5.0% is deliberately weak against a two-order-of-magnitude drift-vs-threshold
  headroom (fact 704). A weak bar makes a negative result strong, which is the
  direction this milestone expects.

**C1b — admissibility guard, from M60b G6, which this arm would otherwise
repeat.** Any fitted correction is **VOID** and may not be counted as a win if
either holds:
* `|c_k − 1| > 3 × ptp` for that stack (a gain must track the drift it corrects:
  M60b measured slopes reaching 0.84 away from 1 on a 10.6% drift), or
* `|o_k| > 0.02 × grandmean` (an offset larger than 2% of the signal is a level
  translation, not a photometric offset).

Both guards are evaluated and reported for every form on every stack whether or
not they fire.

### C2 — is the drift spatially uniform? (M24 §5's second clause)

Per frame `k`, per block `b`: `r_{k,b} = R_b / L_{k,b}`.

```
U  =  sd_k( median_b r_{k,b} )  /  median_k( sd_b r_{k,b} )
```

the ratio of between-frame spread of the frame gain to the within-frame spread
across blocks.

* **A genuine global photometric term** on a stack if `U ≥ 3.0`.
* **NOT spatially coherent — must not be applied as a global gain** if
  `U < 1.5`.
* `[1.5, 3.0)` is equivocal and will be reported as equivocal. **I commit now
  not to round it toward a verdict.**

**C2-power (mandatory, rule 20 / rule 39).** `U` is void on every stack unless
the planted arm demonstrates it can move: with a known uniform ladder of ptp
11.7% planted on a stack whose unplanted `U < 3.0`, planted `U` must reach
**≥ 3.0**. A statistic that cannot be made to read "uniform" has not measured
non-uniformity.

### C3 — does it change the picture, and for the better?

Two halves. **C3a is the only arm in this milestone with ground truth, and it is
the only one that can license the word "better".**

**C3a — planted recovery (the SHIP decider).** On `119MSDCF` (33 frames, 2.88%
native drift, so the plant dominates), with the winner election **frozen** from
the unplanted pass one so that only the averaging stage differs:
* `M0` = merged green from unplanted frames.
* Plant a known ladder `gamma_k` uniformly on signal above black,
  `gamma_k ∈ [1 − 0.117, 1]` so the ptp matches `coffee-bean`'s 11.70% and no
  new saturation is created. Ladder shape is a deterministic pseudo-random
  sequence fixed by seed before the run.
* `E_uncorr` = RMS over pixels of `M_planted_uncorrected − M0`, **after
  rescaling `M_planted_uncorrected` to `M0`'s global mean** — a global scale is
  a re-exposure, not a picture defect, and must not be counted.
* `E_corr` = the same for the corrected merge.
* **Recovery** `R = 1 − E_corr / E_uncorr`.
* **SHIP requires `R ≥ 0.50`.** Below that the correction does not undo a
  disturbance it was handed on a plate, and nothing else in this milestone can
  rescue it.
* **Recovery ratio of the fit itself** is reported separately: `mean_k(ĉ_k *
  gamma_k)` normalised to its own mean, and its spread. A perfect fit gives 1.000
  with zero spread.

**C3a-placebo.** The identical run with `gamma_k ≡ 1`. `E_uncorr` and `E_corr`
must both be **< 0.01 DN** RMS. Anything larger is machinery artefact and every
C3a number is void.

**C3b — materiality on real, unplanted stacks (a NECESSARY condition, never
evidence of benefit).** Per stack, frozen election, corrected minus uncorrected
merged green, after removing the global scale:
* `f1sig` = fraction of pixels with `|delta| > predicted_sigma` of the merged
  pixel.
* **SHIP requires `f1sig ≥ 1.0%` on at least 2 of the 6 stacks.** If
  `f1sig < 1.0%` everywhere the correction is below the noise floor of the
  output and the honest verdict is NO SHIP regardless of C3a.

**Rule 18 — the direction each metric can be fooled in.** `f1sig` measures
*change*, not *improvement*: a wrong correction inflates it. It is therefore
admissible only as a necessary condition (a correction that cannot move the
picture above its own noise cannot help it) and is **inadmissible as evidence of
quality**. `R` in C3a is direction-bearing because it is measured against a
merge of the same frames without the disturbance.

### C4 — the null (mandatory)

`109MSDCF`, the corpus's quietest stack at 0.91% (fact 180). The correction must
be measurably close to a no-op. Registered expectation, and reported either way:
`f1sig(109MSDCF) < 0.5 × f1sig(coffee-bean)`. There is no pass/fail attached —
the number itself is the deliverable, and a null that came out *larger* than the
worst stack would falsify the whole account.

### C5 — the negative control (mandatory; a check never made to fail is not a check)

The correction in my own example is deliberately broken — `c_k` replaced by
`1/c_k`, which is the sign error a real implementation makes — and C3a re-run.
* **The control passes only if `R` goes strictly negative**, i.e. the "corrected"
  image is further from `M0` than the uncorrected one.
* The break is applied by editing my own file after copying it to
  `experiments/M91-photometry/backup/`, and restored from that copy with
  `LastWriteTime` reset to `Get-Date` (rule 33). **Never `git checkout --`** —
  six agents hold uncommitted work in this tree.
* The restore is verified by **reading the restored line back** and by byte
  length, never by an exit code (discipline 366).

### C6 — replication and extension of M60b §4.2

The three merge-time photometric arms re-run at gate 4.0 (the shipped default;
M60 ran gate 1.0) on all six stacks, including the three the arms have never
seen. Descriptive; no bar. Its value is that `coffee-bean`, the worst drift in
the corpus, has never been through them.

### C7 — the price of getting fact 608's ordering backwards

On the worst stack, recompute pass one with the luma scaled **before** the noise
model (the naive ordering fact 608 forbids) and report: mean response ratio
against P-b's `sqrt(c)` prediction, fraction of pixels whose winner changes, and
the change in mean `n_eff`. This prices the failure mode fact 608 names.

### C8 — the independent-reimplementation identity control

My example accumulates its own merge rather than editing the contended
`merge.rs`. With `c_k = 1, o_k = 0` it must reproduce
`Estimator::green_mean` **exactly** (bit-identical `f32`) at every pixel,
including the censoring rule. If it does not, the accumulator is not the shipped
merge and every image number is void.

---

## 4. Stacks

| stack | n | ptp (fact 180 / M60b G5) | role |
|---|---:|---:|---|
| `109MSDCF` | 22 | 0.91% | **null** (C4) |
| `119MSDCF` | 33 | 2.88% | **plant host** (C3a) |
| `112MSDCF` | 79 | 6.84% | never seen by the merge-time arms |
| `coffee-bubbles` | 19 | 8.93% | M60's intermediate |
| `foam` | 100 | 10.60% | M60's positive control |
| `coffee-bean` | 105 | **11.70%** | **worst drift in the corpus; never seen by the merge-time arms** |

Read-only. Nothing is written under `D:\personal\macro` or `D:\macro-dark-frames`.

## 5. What would make each gate FAIL (rule 20, per gate)

| gate | an input that fails it |
|---|---|
| C1 | a stack whose per-frame level shift is a genuine additive pedestal (dark-current or stray-light drift) — `F6` would then beat `F5` by far more than 5% |
| C1b | M60b's own `foam` fit, which reads slope 0.16 on a 10.6% drift and is void by this guard |
| C2 | a stack lit by a slowly moving light source, giving a spatially varying gain and `U < 1.5`; and its converse, the planted uniform ladder, which must give `U ≥ 3.0` |
| C3a | a correction whose fit is wrong or whose ordering is wrong: `R ≤ 0`. C5 constructs exactly such an input on purpose |
| C3b | a drift small enough to sit under the merged pixel's own sigma — which is the expected outcome on `109MSDCF` |
| C7 | a merge whose election is genuinely gain-invariant would show 0% winner change under the naive ordering too; `focus.rs:309`'s test says it is not |
| C8 | any accumulator that is not the shipped merge — e.g. one that forgets the censoring rule, which changes only saturated pixels and would otherwise pass unnoticed |

---

## 5b. ADDENDUM — C9, registered after reading `merge.rs:777` and before running any arm

*Added while writing the example, after §0–§5 were committed at `065ab3b` and
before a single number had been read. It is here rather than in §3 so the order
is visible.*

**What I found by reading.** `Estimator::fold_inner` builds the probe's luma from
`row[2 * px + ox]`, which is `Frame::active_row` — the **raw u16 sensor sample,
black included**. `Estimator::disagreement` confirms it by subtracting black only
at read time: `green_luma_sigma((mean - black_dn) as f32)`. So the probe's `L` in
`L' = L * luma_scale + luma_offset` is black-inclusive DN.

`m60-disagreement.rs:302-305` passes `scale[index], 0.0` under the comment
*"`green_luma_with_clip` subtracts black, so the luma the accumulator sees is
already signal and the offset is zero."* That comment is about `pipe.luma`, a
different buffer, used only for the focus field. **The estimator never sees
`pipe.luma`.** So M60's gain arms multiplied the **black pedestal** by a gain
fitted on black-subtracted signal.

**Why this could matter, in arithmetic done before the run.** The physically
correct gain-only correction is `black + c*(L - black)`, i.e.
`luma_scale = c`, `luma_offset = black * (1 - c)`. Passing `luma_offset = 0`
instead applies a correction larger than intended by the factor
`raw_mean / signal_mean = 1 + black / signal_mean`:

| stack | black | mean signal (M60b §4.3) | over-correction factor |
|---|---:|---:|---:|
| `109MSDCF` | 512 | ~1397 DN | **1.37x** |
| `foam` | 512 | ~862 DN | **1.59x** |
| `coffee-bubbles` | 512 | ~340 DN | **2.51x** |

**C9, and its prediction fixed now.** Run the gain arm both ways — M60's
`luma_offset = 0` and the pedestal-correct `luma_offset = black*(1-c)` — on the
identical admitted set.

* **Registered prediction:** the pedestal-correct arm removes strictly more
  excess than M60's arm on **every** stack, and the gap is **ordered by
  `black / mean_signal`**, so it must be largest on `coffee-bubbles` and
  smallest on `109MSDCF`.
* **C9 is MET, and M60's F3 and G7 are partly refuted**, if the pedestal-correct
  arm turns M60's negative reductions (−22.5% on `coffee-bubbles`, −2.4% on
  `foam`) **positive**.
* **C9 FAILS and M60's F3 stands** if the two arms agree to within 2 percentage
  points of excess removed, or if the pedestal arm is also negative.
* Rule 20 — the input that fails it: a stack whose black pedestal is negligible
  against its signal would show no gap at all. `109MSDCF` at `512/1397` is the
  corpus's closest approach to that and is registered as the low-effect case
  **before** the run, so a flat result there is a prediction met and not an
  excuse.
* **A4b (offset-only) is unaffected by this** and I say so before measuring: an
  additive offset commutes with the pedestal, so M60's A4b numbers need no
  correction. If my A4b reproduces M60's 0.3% / 7.6% / 5.0% while my gain arm
  does not reproduce its 7.1% / −22.5% / −2.4%, that pattern is itself the
  signature of the defect and is registered as the confirming observation.

**Binding on everything else in this file:** the image path of C3 uses the
pedestal-correct form, `black + c*(L − black) + o`, throughout.

---

---

## 5c. ADDENDUM — C3a has no power as registered, and C3a-hard replaces it

*Written after the `fit` arm ran on all six stacks and **before** any planted arm
ran. The order matters and is stated so it can be checked: no planted number
existed when this was written.*

**The defect in my own pre-registration.** C3a plants a spatially **uniform**
per-frame gain `gamma_k` and corrects with `F1`, whose fit is the ratio of
whole-image means. A uniform plant multiplies the whole-image mean by exactly
`gamma_k`, so `c_hat_k = 1 / gamma_k` **exactly**, and then

```
correct_dn(black + (d - black) * gamma_k, black, 1/gamma_k, 0) = d
```

identically, to f64 rounding. `R = 1` is therefore **algebra, not evidence**.
This is AGENTS rule 35 — a test whose subject and object are the same value has
no power — and I got it wrong when I wrote §3. Recording it rather than quietly
replacing it.

**What C3a is still worth, and it is not nothing.** The identity above holds
only if the pedestal pivot, the correction's direction and fact 608's ordering
are all right. It is a **plumbing control**: it cannot say the correction helps,
but it goes red when the correction is built wrong. C5 is the demonstration —
the negative control breaks exactly this arm. C3a is therefore reported as a
control and **never as evidence of benefit**, and `R = 1.000` will be presented
as "the arithmetic closes", not as a result.

**C3a-hard, registered now, with power.** Plant a per-frame gain that is
**spatially non-uniform**, which is the disturbance a single global gain
genuinely cannot absorb and the one M24 §5's second clause is about:

```
g_k(x) = 1 + (gamma_k - 1) * (1 + a * (2x/W - 1)),    a = 0.5
```

so the drift depth runs from half its nominal value at the left edge to one and
a half times it at the right, while the whole-image mean of `g_k` stays
`gamma_k`. `a = 0.5` and `gamma_k` from the same seeded ladder are fixed here,
before the run.

* `E_uncorr_hard`, `E_corr_hard` and `R_hard = 1 - E_corr/E_uncorr` are computed
  exactly as in C3a, global scale removed, election frozen.
* **`R_hard >= 0.50`**: a single global gain removes most of the damage a
  realistically non-uniform drift does. The functional form is adequate.
* **`0 < R_hard < 0.50`**: partially adequate; the residual is the price of the
  global form.
* **`R_hard <= 0`**: a global gain makes a non-uniform drift *worse*. Global
  correction is contraindicated and that is a publishable negative.
* Reported beside it, and **the number that actually decides materiality**:
  `f1sig` of the *uncorrected* non-uniform plant against the merged pixel's own
  `predicted_sigma`. If a 11.7% drift with a 50% spatial ramp cannot move the
  merged picture above its own noise, nothing weaker can.
* Rule 20 — the input that fails it: `a = 0` reduces C3a-hard to C3a and must
  give `R_hard = 1`. That degenerate case is run as its own check.

---

## 5d. POST-HOC, DISCLOSED — least-squares shrinkage in the C1 ladders

**This is not a pre-registered criterion and is not used to decide C1.** It is
recorded because it changes how C1's number should be read, and hiding it would
be worse than admitting the order it was found in.

The `fit` arm's ladders show the least-squares forms `F2`, `F3` and `F6`
producing gains biased **downward**: on `foam`, `F2` fits every one of 100
frames in `0.814..0.947`, entirely below 1, against a drift whose true gains
must straddle 1 because they are defined about the grand mean. The reference
`R_b` is an average over frames and is smoother than any single frame, so
minimising `sum_b (R_b - c L_kb)^2` shrinks `c` toward the reference — ordinary
regression attenuation.

**Direction of the bias, which is the reason this does not rescue the affine
form.** Held-out residual RMS *rewards* shrinkage, and the two-parameter form
has more freedom to shrink than the one-parameter form. C1's criterion is
therefore biased **in favour of** the offset term, and C1 fails anyway on 4 of 6
stacks with the other 2 void under C1b. The negative verdict is conservative
under this bias, not threatened by it.

**The diagnostic, stated so it can be reused and so its post-hoc status is
permanent:** a photometric gain ladder fitted about the grand mean must straddle
1. A ladder lying wholly on one side is measuring shrinkage, not gain. This is
offered as a candidate discipline, not as a criterion this milestone decided
anything with.

---

## 5e. ADDENDUM — C10, the decomposition C2 failed to deliver; and two disclosed instrument defects

*Written after `fit`, `chi2`, `image` and the three planted arms had run, and
before `C10`, `C5` or `C7` had run. Every number quoted below already existed
when this was written; every number C10 produces did not.*

### The two defects my own controls found, recorded before they are reported

1. **C2 is void on all six stacks by its own mandatory power control.** The
   planted uniform ladder of ptp 11.7% raised `U` to 1.72 / 2.49 / 0.27 / 0.56 /
   0.30 / 0.48, never to the registered 3.0. `U`'s denominator
   `median_k(sd_b r_{k,b})` is dominated by defocus on a focus stack, so `U`
   cannot read "uniform" even when the drift *is* uniform by construction. The
   statistic is underpowered and M24 §5's second clause is **NOT ESTABLISHED**
   by it. C10 exists because of this.
2. **C3a's registered comparison target was wrong.** It compared the corrected
   planted merge against `M0`, the *uncorrected* unplanted merge, so it charged
   the correction for removing the stack's own native drift. The placebo caught
   it: at `gamma == 1` it reported `E_corr = 26.58985 DN`, which is exactly
   C3b's independently computed corrected-vs-`M0` RMS. The right reference is
   the corrected *unplanted* merge, and with that the placebo reads
   `E_uncorr = 1.3e-4 DN` and `E_corr = 0.0 DN`. **The registered wording of
   C3a-placebo therefore FAILED and is reported as failed**; the fix is an
   instrument correction the control forced, not a bar moved after seeing data.

### C10 — how much of the drift is a single global gain?

Per block `b` and frame `k`, from pass one's block means, `y_{k,b} = R_b /
L_{k,b}` normalised so `mean_k y_{k,b} = 1`. The single global ladder is
`g_k = mean_b y_{k,b}`, normalised the same way.

```
EV  =  1  -  sum_{k,b} (y_{k,b} - g_k)^2  /  sum_{k,b} (y_{k,b} - 1)^2
```

the fraction of block-ladder variance a **single global gain per frame**
explains.

* **`EV >= 0.50`**: the drift is predominantly global; a per-frame scalar is the
  right functional form and M24 §5's second clause resolves to "uniform".
* **`EV < 0.20`**: the drift is predominantly spatial; a per-frame scalar is the
  **wrong** functional form, and applying one can add disagreement rather than
  remove it. That would explain the measured negative chi2 reductions on `foam`
  and `coffee-bubbles` without appeal to anything else.
* `[0.20, 0.50)` is mixed and will be reported as mixed, not rounded.

**C10-power (mandatory, and the thing C2 lacked).** Recompute `EV` with a known
uniform ladder of ptp 11.7% planted on top of the real data. **`EV_planted`
must exceed 0.90.** If it does not, `EV` cannot see globality and C10 is void
exactly as C2 was.

**C10-null (mandatory).** Recompute `EV` with the real drift *divided out*
frame by frame, leaving only whatever spatial structure remains. `EV_null` must
fall to near zero; a large `EV_null` would mean `EV` is reading something that
is not the drift.

**Disclosed confound, stated before the run.** Defocus moves `y_{k,b}` and is
not global, so it deflates `EV`. A **high** `EV` is therefore strong evidence of
globality; a **low** `EV` is ambiguous between spatially varying photometry and
defocus contamination, and the report must say so rather than claim
non-uniformity outright. C10-power calibrates how much deflation there is:
`1 - EV_planted` on a plant that is uniform by construction is the deflation
floor.

**Rule 20 — the input that fails it:** a stack whose lamp is perfectly stable in
shape and varies only in output gives `EV -> 1`. The C10-power arm constructs
exactly that input and requires it.

---

## 6. Ownership

Writes only to `crates/strehl-cli/examples/m91-photometry.rs`,
`experiments/M91-photometry/`, and `docs/research/M91-photometry.md`.
`merge.rs` and `merge_cmd.rs` are contended and are **not edited** — the whole
image path is reimplemented in the example, which C8 turns from a workaround
into a control. Commits use explicit paths (rule 42) and nothing is pushed.
