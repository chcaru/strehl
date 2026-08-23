# M46 — Is there an admissible detail metric on this sensor?

**Status:** measured, complete.
**Pre-registration:** `experiments/m46-detail-metric/PREREGISTRATION.md`, committed
`2474e5d` with `src/` empty at that commit. Every prediction below was written
before the first script existed.
**Scripts:** `experiments/m46-detail-metric/src/{m46lib,b1_pair,b2_recovery,b3_separation,b4_leakage,b5_bar}.py`
**Artifacts:** `experiments/m46-detail-metric/out/b{1,2,3,4,5}_*.{log,json}`

Every claim below is labelled **MEASURED**, **DERIVED** or **ARGUED**.

---

## 1. The verbatim bar

From the milestone assignment, quoted before it is scored:

> **The acceptance bar is the one your fact 477 sets: recovery ≥ +0.9 on detail
> AND ≤ +0.3 on flat.**

And the framing it came with:

> Fact 52 records `112MSDCF`/`113MSDCF` as a same-subject pair shot a full stop
> apart. Two *independent captures* means the read-noise realisation and the
> subject sampling are not common-mode, while FPN still is — so per your (1−ρ)
> law from fact 478 the recovery should rise from the 0.02-0.37 you measured
> toward 1.0, and the residual shortfall **measures the FPN fraction**.

## 2. Verdict, in one paragraph

**An admissible detail metric exists.** It is

```
sigpow(f) = FRC(f) · P_ring(f)        evaluated at f_sig = 0.2762 cyc/px
```

the product of the ring correlation and the ring power of a **pair** of merges.
It scores **S = 0.937** on real detail, **0.973** as the paired detail/flat
statistic, and **0.931** against a linear post-filter where plain FRC scores
exactly **0.000** — all at a plant magnitude where the incumbent `hp_sd` is
pinned at 0.500 by construction. **MEASURED**, `out/b3_separation.log`.

**It did not come from the two captures.** The pair `112`/`113` did **not**
decorrelate anything: the flat/detail FRC ratio at `f_sig` is 0.771, and the
absolute flat reading is +0.7310 — barely different from M41's within-capture
split-half (+0.6569). Two independent captures of the same sensor share the same
fixed pattern, so the (1−ρ) shortfall the assignment predicted would shrink
**does not shrink**. **MEASURED**, `out/b1_pair.log`. The winning statistic needs
only a *pair*, not an *independent* pair, so a split-half of one stack supplies
it — which is what makes it shippable.

**And the assigned bar cannot be met by anything, including two different
oracles, for a reason that is now measured rather than suspected.** There is no
source on this sensor that is simultaneously featureless and blurrable. The bar's
second half is therefore not a hard test that everything failed; it is an
**ill-posed test**. §5 shows this three separate ways.

**Question 120 is answered and the answer is not leakage.** Leakage at 0.45
cyc/px is **−138.6 dB** under the incumbent Hann window. The censoring is caused
by **common-mode fixed-pattern noise**, which is white to Nyquist and holds FRC
above 1/7 in every ring. No window repairs it. **MEASURED**, `out/b4_leakage.log`.

---

## 3. What ran

| script | what it did | runtime |
|---|---|---|
| `b1_pair.py` | two-capture FRC on `112MSDCF`/`113MSDCF` | 85.9 s |
| `b2_recovery.py` | the assigned bar across 3 plant models × 2 noise levels × 3 sources × 5 blur levels | 520 log lines |
| `b3_separation.py` | BLUR-ONLY vs SMOOTH-ONLY at matched `hp_sd` cost, + PM_C completeness | 225.7 s |
| `b4_leakage.py` | question 120: window ladder against a band-limited latent | 4.6 s |
| `b5_bar.py` | assigned bar + repaired bar for the new statistics | 48.3 s |

`b1` and `b2` were run and reported in the previous session segment and are
frozen under rule 15. `b3` was rewritten once **before** it reported anything
(the first matching direction was infeasible — §6.1 — and that infeasibility is
re-measured inside the frozen version rather than carried over from a discarded
run). `b4` and `b5` are new.

`m41lib.py` and `m41lib3.py` are imported unchanged via `sys.path`, never edited,
so every number here is comparable to M41's line by line. Where `b4` needed the
window as a parameter it **copies** the body of `m41lib.frc` and says so in the
docstring; the ring edges, the `fftshift` convention, the ≥8-pixel ring floor and
the mean-removal are byte-identical.

---

## 4. The two-capture FRC (scope item 1)

### 4.1 The exposure difference is TIME, not gain

**MEASURED**, from EXIF, `out/b1_pair.log`:

| | `112MSDCF` | `113MSDCF` |
|---|---|---|
| frames | 79 | 63 |
| ISO | 500 | 500 |
| shutter | 1/60 s | **1/30 s** |
| aperture | f/11 | f/11 |
| focal | 200 mm | 200 mm |

`t113/t112 = 2.0000` — **+1.0000 stops of exposure time at identical gain.**
Fact 52's "a full stop apart" is true, but it is not a stop of gain, and the
noise algebra is completely different. **MEASURED.**

**DERIVED consequence.** `g = 1.14469` DN/e⁻ and read noise 1.47 e⁻ are identical
between the two captures. `113` collected twice the photons, so after rescaling
to `112`'s level it is **quieter**, not noisier. Predicted `σ113·c/σ112 =
1/√2 = 0.7071`; **MEASURED 0.7107** (0.5 % agreement). Had the stop been gain,
the ratio would have been 1.0.

### 4.2 The ordering, fixed in advance

PREREGISTRATION §4.1 fixed the ordering before any data was read:

> the photon-transfer model is evaluated on each capture's **own unscaled DN**,
> and the variance is carried through the photometric scale as `c²·var`.

This matters and the wrong order manufactures correlation. Applying the model
*after* rescaling charges `113` shot noise for photons it never collected — it
would report `113` as *noisier* than `112` by exactly √2, inverting the sign of
the whole comparison. **DERIVED.**

The scale itself is measured, not assumed, and then checked against EXIF:
measured `c = 0.5095` (detail) / `0.5082` (flat) against EXIF's `0.5000` —
**1.90 % disagreement, PASS** at the pre-registered ≤5 % tolerance. **MEASURED.**

### 4.3 The result

Depth-range matched per fact 50 (`112` restricted to indices 6..67, 62 frames;
`113` uses all 63). Global registration `dy=0, dx=0`; residual sub-pixel shift
`dy=+0.125, dx=−0.047` px. **MEASURED.**

| | crossing | FRC @ `f_sig` | @0.10 | @0.20 | @0.35 | @0.45 |
|---|---|---|---|---|---|---|
| two-capture, detail | **0.4961 [CENSORED]** | **+0.9477** | +0.9965 | +0.9825 | +0.8176 | +0.3865 |
| two-capture, flat | **0.4961 [CENSORED]** | **+0.7310** | +0.9843 | +0.8708 | +0.4974 | +0.2511 |
| within-`112` split-half, detail | 0.4872 | +0.8691 | | | | |
| within-`112` split-half, flat | 0.4755 | +0.6569 | | | | |

**The prediction in the assignment is refuted. MEASURED.** Two independent
captures were expected to push recovery toward 1.0 by decorrelating the
read-noise realisation. They did not: the flat ROI reads **+0.7310**, *higher*
than the within-capture split-half's +0.6569, and the rule-9 flat/detail ratio at
`f_sig` is **0.7714** — nowhere near decorrelated.

**DERIVED, and this is the mechanism.** FPN is common-mode between any two
captures *of the same sensor*, not merely between two halves of one stack.
Independent captures decorrelate the shot and read noise, which the split-half
already decorrelated. They change nothing about the term that was actually
binding.

### 4.4 The residual shortfall does measure the FPN fraction

Solving the two-capture flat reading for the FPN variance fraction:

```
ρ = FRC_flat / (1 − FRC_flat) / n_eff = 0.7310/0.2690/8.784 = 0.3094
```

**ρ = 0.3094 — fixed-pattern variance as a fraction of single-frame noise
variance. DERIVED from b1, not chosen.** Every downstream script uses this value
and none of them re-picks it (rule 24).

**And the law reproduces on a source whose truth is known independently.** `b4`
§2 builds a latent that is band-limited at 0.20 cyc/px by construction, adds FPN
at this ρ and independent noise at `n_eff = 10.366`, and measures FRC at 0.45
cyc/px — a frequency where the latent has *exactly zero* power. Closed form
predicts the pure FPN floor:

```
ρ/(ρ + 1/n_eff) = 0.3094/(0.3094 + 0.09647) = 0.7622
```

**MEASURED +0.7653** (rect window), +0.7668 (Hann). **0.4 % agreement, on
synthetic data where ρ was not fitted.** **MEASURED + DERIVED.**

### 4.5 The harness has power (rule 20)

A deliberate-misalignment ladder, because a metric that cannot fall is not a
metric. **MEASURED:**

| extra shift (px) | 0.00 | 0.25 | 0.50 | 1.00 | 2.00 | 4.00 |
|---|---|---|---|---|---|---|
| crossing | 0.4961 [C] | 0.4961 [C] | 0.4961 [C] | **0.4430** | **0.2908** | **0.1131** |
| FRC @ `f_sig` | +0.9477 | +0.9319 | +0.8746 | +0.6663 | +0.2049 | +0.1601 |

The instrument moves, monotonically, over 4 px. The censoring at small shifts is
not a dead harness; it is the FPN floor of §4.4 sitting above 1/7.

---

## 5. The assigned bar cannot be met, and the reason is not that the metrics are bad

### 5.1 Every metric fails, including the oracle

`b2`, planted optical blur `sb = 2.0` px at merged noise, recovery ratio
`rec_lin` (fact 477's arithmetic, unchanged). **MEASURED:**

| metric | PM_A det/flat | PM_B det/flat | PM_C det/flat |
|---|---|---|---|
| `frc2_cross` | undefined (censored) | undefined | undefined |
| `frc2_at_fsig` | +0.9695 / +0.9588 | +1.0242 / +1.0011 | **−0.0184 / −0.4561** |
| `hp_sd` | +0.9958 / +0.9789 | +0.9956 / +0.9758 | +1.0036 / +1.0192 |
| `p_ratio` | +0.9975 / +0.9349 | +0.9948 / +0.9775 | +1.0532 / +1.1725 |
| `mean_grad` | +0.9972 / +0.9825 | +0.9873 / +0.9165 | +1.0128 / +1.0522 |
| **`oracle_fsc`** | **+0.9976 / +0.9513** | +164.98 / +221.55 | +1.0103 / +1.0222 |

`b5` adds the new candidates in the same arithmetic. **MEASURED:**

| metric | PM_A det/flat | PM_B det/flat | PM_C det/flat |
|---|---|---|---|
| `ringpow` | +1.0011 / +0.9978 | +1.0005 / +0.9940 | +1.0101 / +1.0728 |
| `sigpow_fsig` | +1.0014 / +0.9989 | +1.0007 / +0.9939 | +1.0009 / +0.9956 |
| **`oracle_mtf`** | **+1.0000 / +1.0000** | +1.0000 / +1.0000 | +1.0006 / +0.9989 |

**Eight statistics, two of them oracles holding the ground truth, three plant
models. Not one passes.** PREREGISTRATION §3 pre-declared exactly this signature:

> if even the oracle reads > +0.3 on flat, the **bar** is unachievable and must
> be rebuilt rather than the metrics discarded.

### 5.2 Why: the "flat" ROI is not flat

The rule-10 detector (`hp_sd / model_σ`) on the merged plane reads **detail
15.79, flat 6.43**. **MEASURED**, `b2`. A noise-dominated region reads ≈1. The
flat ROI carries roughly six times the high-pass energy the photon-transfer model
accounts for, which is fact 469's ~99 %-residual-scene measurement showing up
again on a different ROI.

**ARGUED, and this is the crux.** Blurring a region that *has* content destroys
real content. A metric that stays silent there would be *broken*. So the assigned
bar asks every metric to fail to detect a real loss — and the oracle, which knows
the true latent, correctly refuses.

### 5.3 Why it cannot be fixed by picking a better flat region

`b5` tried the honest version: `S_null`, a **constant** latent with no content by
construction. **The recovery ratio came back `undefined` for every metric under
PM_A. MEASURED.**

That is not a bug. Under PM_A the plant is `H·L + P + N`, and `H·const = const`,
so the truth channel does not move; `rec_lin` correctly returns `None` rather
than 0. **A featureless source cannot be blurred, so it cannot host a recovery
ratio.**

Under PM_B and PM_C the plant *does* move — because it blurs the fixed pattern
along with everything else. **MEASURED**, `b5` §3:

| metric | rec(PM_B, `S_null`) | rec(PM_C, `S_null`) |
|---|---|---|
| `hp_sd` | +0.6095 | +1.1695 |
| `p_ratio` | +0.1849 | +1.0023 |
| `mean_grad` | +0.6193 | +1.1698 |
| `ringpow` | +0.9798 | +1.3518 |
| `sigpow_fsig` | +0.9752 | +0.9834 |
| `oracle_mtf` | +1.0000 | +1.1889 |

The registered failure mode fired, exactly as `b5`'s docstring predicted before
the run: on a featureless source under PM_B the only structure present *is* the
fixed pattern, and blurring it is a genuine loss of structure. **Even the oracle
reads +1.0000.**

**MEASURED, and this is the general result: on this sensor there is no source
that is both featureless and blurrable.** Take away the scene and the fixed
pattern is still structure. The "does it fire on nothing?" test is not hard —
it is **unconstructible**. Fact 477's ≥ +0.94 flat readings were never false
alarms; they were correct detections of a real content loss.

### 5.4 What replaces it

**ARGUED.** The admissibility question was never really "does it fire on
nothing". It is:

> can it tell *destroying structure* from *removing independent noise*?

That question needs no featureless source at all. It is a **within-source
contrast at matched cost**, and it is what §6 measures.

---

## 6. The separation test (scope item 3)

### 6.1 The design, and the direction that was infeasible

Two plants on the same source:

* **BLUR-ONLY** — `H·L + P + N`. The scene is degraded; the noise is untouched.
* **SMOOTH-ONLY** — `L + P + N/k`. The independent noise is reduced; the scene
  and the fixed pattern are untouched. `P` survives, because averaging more
  frames does not average away a fixed pattern.

The two magnitudes are tied so that both produce **the same `hp_sd`**. The
incumbent noise statistic therefore cannot distinguish them *by construction* —
its score is 0.500 by definition, not by measurement — and every other statistic
is asked whether it can do better on the same pair.

```
S = |d_blur| / (|d_blur| + |d_smooth|),   d_x = (m_base − m_x)/|m_base|
S = 1.000  pure resolution metric      S = 0.500  cannot tell them apart
S = 0.000  pure noise metric
```

**The first matching direction had no solution and is reported, not deleted.**
Solving for the smoothing `k` that imitates a given blur fails at every width
down to 0.125 px. **MEASURED:**

| planted blur `sb` | `hp_sd` target | residual with **all** noise removed |
|---|---|---|
| 2.000 | 27.4937 | +31.1960 |
| 1.000 | 44.4940 | +14.1957 |
| 0.500 | 54.0292 | +4.6605 |
| 0.250 | 57.4566 | +1.2331 |
| 0.125 | 58.4523 | +0.2374 |

The merged detail ROI carries `hp_sd` 58.8 DN of scene against σ 3.69 DN of
noise, so **deleting every last electron of noise costs less than a 0.125 px
blur**. **DERIVED consequence: on this corpus a merge cannot fake sharpness by
denoising.** That is a fact about the data, not about any metric, and it is worth
more than the failed bisection it came from.

The solvable direction fixes a *realistic* merge change — `k = √2`, the noise a
**doubling of the acceptance set** buys — and solves for the blur that costs the
same `hp_sd`: **`sb = 0.04999` px** on the detail ROI. **MEASURED.**

### 6.2 Separation scores

**MEASURED**, `out/b3_separation.log` §6. `S_null` is a constant latent; `S_flat`
and `S_detail` are `b1`'s merged ROIs; `S_synth` is a broadband synthetic.

| statistic | `S_null` | `S_flat` | `S_detail` | `S_synth` |
|---|---|---|---|---|
| `frc2_at_fsig` | 0.000 | 0.011 | 0.014 | 0.015 |
| `frc2_cross` | — | — | — | — |
| `hp_sd` | 0.000 | 0.186 | **0.501** ← pinned | 0.987 |
| `p_ratio` | 0.000 | 0.079 | 0.267 | 0.988 |
| `mean_grad` | 0.000 | 0.067 | 0.233 | 0.984 |
| `ringpow` | 0.000 | 0.128 | 0.587 | 0.995 |
| **`sigpow_fsig`** | 0.000 | **0.917** | **0.937** | 0.990 |
| `oracle_fsc` | 0.000 | 0.052 | 0.060 | 0.060 |
| **`oracle_mtf`** | 0.000 | **0.919** | **0.958** | 0.990 |

**Two statistics separate. `oracle_mtf` is the positive control — it holds the
true latent, so if *it* could not separate, the plant would be at fault.** It
separates at 0.958. `sigpow_fsig` reaches 0.937 **without the truth**, and needs
only a pair of merges.

The `S_null` column reads 0.000 for everything because under PM_A a constant
latent cannot be blurred at all (§5.3) — it is a degenerate control, and is
reported as such rather than counted as a pass.

### 6.3 The paired statistic (question 119)

Detail reading conditioned on the same merge's flat reading. **MEASURED:**

| statistic | ratio form `m(det)/m(flat)` | difference form |
|---|---|---|
| `frc2_at_fsig` | 0.011 | 0.011 |
| `hp_sd` | 0.060 | 0.457 |
| `p_ratio` | 0.048 | 0.066 |
| `mean_grad` | 0.018 | 0.302 |
| `ringpow` | 0.050 | 0.721 |
| **`sigpow_fsig`** | **0.973** | **0.938** |

**Question 119 is answered, and the answer is that conditioning does not rescue a
metric that cannot separate on its own.** Every incumbent gets *worse* in ratio
form than it was unconditioned (`hp_sd` 0.501 → 0.060; `ringpow` 0.587 → 0.050),
because the flat denominator moves with the numerator under smoothing and
cancels the very signal being sought. Only `sigpow_fsig`, which already separated,
improves — to 0.973, its best score anywhere.

**DERIVED.** Pairing is a *normalisation*, not an *instrument*. It can remove a
common-mode nuisance but it cannot manufacture sensitivity that the underlying
statistic does not have.

### 6.4 The completeness test: does it see a post-filter?

Separating blur from smoothing is not enough. The failure mode the project
actually fears is **PM_C — a merge that low-passes its own output**. `b2` measured
that `frc2_at_fsig` is blind to it: recovery **−0.0184**.

**DERIVED, and this is a theorem, not an observation.** Ring FRC is `C/(C+U)` with
`C` the common power and `U` the uncorrelated power. A linear post-filter scales
*both* by `|H|²`, so the ratio cannot move. **Any correlation-based metric,
including an FSC against ground truth, is blind by construction to a merge that
low-passes its output.** Conversely `hp_sd`/`p_ratio`/`mean_grad` are
absolute-power statistics and read the full +1.0 — fully fooled, because they
cannot tell the lost power was noise.

`b3` §4 matches the post-filter to the **same `hp_sd` cost** as the smoothing, so
`hp_sd` cannot tell any of the three apart. **MEASURED:**

| statistic | `S_flat` S | `S_detail` S |
|---|---|---|
| `frc2_at_fsig` | **0.000** | **0.000** |
| `hp_sd` | 0.499 | 0.501 |
| `p_ratio` | 0.368 | 0.304 |
| `mean_grad` | 0.280 | 0.249 |
| `ringpow` | 0.365 | 0.566 |
| **`sigpow_fsig`** | **0.976** | **0.931** |
| `oracle_fsc` | **0.000** | **0.000** |
| **`oracle_mtf`** | 0.969 | 0.953 |

Matched post-filter widths `sb_pc = 0.08460` px (flat), `0.04681` px (detail).

`frc2_at_fsig` and `oracle_fsc` read **exactly 0.000** — the theorem, measured.
`sigpow_fsig` reads 0.931.

### 6.5 Why `sigpow` works

**DERIVED.** `FRC = C/(C+U)` and ring power `= C + U`. Their product is

```
sigpow = FRC · P_ring = C
```

— the per-ring **common** power, which is signal.

* **SMOOTH-ONLY** reduces `U`, leaves `C`. `sigpow` should not move. **MEASURED
  d_smooth = +0.0005** on detail.
* **BLUR-ONLY** attenuates `C` by `|H|²`. `sigpow` should fall. **MEASURED
  d_blur = +0.0073.**
* **POST-FILTER** attenuates `C` and `U` together. The FRC term cannot move, but
  the power term falls by `|H|²`, so the product falls. **MEASURED d_pc =
  +0.0066.**

FRC alone measures *recoverable information per ring*; ring power alone measures
*delivered energy*, signal and noise together. Their product measures **delivered
signal**, which is the quantity the project has been trying to name since fact
145. Neither factor works alone and that is why fourteen milestones of
single-statistic candidates all failed.

### 6.6 Shippability

**DERIVED, and this is the part that makes the result usable.** `sigpow` needs
two images of the same scene. It does **not** need them to be independent
captures — §4.3 measured that independence buys nothing here anyway. `b3`'s
`draw()` gives `y1` and `y2` the **same** fixed pattern and independent noise,
which is exactly the configuration of **two merges built from disjoint halves of
one stack**. Every score in §6.2–6.4 was therefore already measured in the
shippable configuration.

The FPN contributes an additive pedestal to `C` that does not move with blur
under PM_A, so it biases the *level* and not the *response*. Under PM_B/PM_C it
moves with the plant and is correctly counted.

---

## 7. Question 120: why is `sb = 0` censored everywhere?

### 7.1 The decisive input, registered in advance

PREREGISTRATION §4.4 registered a latent that is **band-limited by construction**:
`synth_broadband(n, seed, cutoff=0.20)` zeroes every Fourier coefficient above
0.20 cyc/px. Any ring power measured at 0.45 cyc/px on it is leakage, 100 %,
with no modelling assumption and no nuisance estimator to choose.

**Rule 20, written before the run:** if that power came back near machine zero
under Hann, leakage would be **ruled out**; if it came back high under Hann and
low under Blackman-Harris, leakage would be **confirmed and repaired**; if the
floor fell but the real sources stayed censored, leakage would be **present but
not binding**. Three distinguishable outcomes.

### 7.2 The leakage floor

**MEASURED**, noiseless, `out/b4_leakage.log` §1:

| window | P(0.45)/P_peak | dB |
|---|---|---|
| rect | 1.02e−16 | **−159.9** |
| **hann (incumbent)** | 1.38e−14 | **−138.6** |
| blackman | 2.08e−15 | −146.8 |
| blackman-harris | 1.24e−16 | −159.1 |
| hann + 9×9 pre-filter | 3.63e−14 | −134.4 |

**Leakage is fourteen orders of magnitude below the signal. It cannot be the
cause of anything. Rule 20's first branch fired: leakage is RULED OUT.**

### 7.3 The actual cause

Same band-limited latent, two noisy realisations. **MEASURED**, §2:

| | FRC(0.45) | FRC(0.2762) | crossing |
|---|---|---|---|
| **no FPN**, hann | +0.0181 | +0.0095 | **0.2058** — uncensored |
| no FPN, rect | +0.0043 | −0.0040 | 0.2058 |
| no FPN, blackman | +0.0160 | +0.0119 | 0.2076 |
| no FPN, blackman-harris | +0.0135 | +0.0124 | 0.2122 |
| **with FPN** (ρ=0.3094), hann | **+0.7668** | +0.7738 | **0.4961 [CENSORED]** |
| with FPN, blackman-harris | +0.7688 | +0.7833 | 0.4961 [CENSORED] |

**Without FPN the harness is not merely uncensored — it recovers the true cutoff.
The latent is band-limited at 0.20 cyc/px and the measured crossing is 0.2058.**
The FRC machinery is correct and has power. **MEASURED.**

**Add the fixed pattern and the crossing pins at 0.4961 on a source with exactly
zero true power above 0.20 cyc/px.** The FRC at 0.45 jumps from +0.018 to +0.767
— which §4.4 showed is the closed-form FPN floor `ρ/(ρ + 1/n_eff) = 0.7622` to
within 0.4 %.

**Answer to question 120, MEASURED:** the `sb = 0` reference is censored because
**fixed-pattern noise is common-mode between the two half-merges and is white to
Nyquist**, so it holds FRC above the 1/7 threshold in *every* ring. It is a
property of the **sensor**, not of the window and not of the scene. That is why
it appears identically on the analytic channel: the analytic channel is given the
same FPN, and once FPN is present the source no longer matters.

### 7.4 No window repairs it

Window ladder × blur ladder on real ROIs and on a broadband synthetic. **MEASURED**,
§3 — **60 of 60 cells** read `0.4961 [CENSORED]`:

| source | `sb` | rect | hann | blackman | b-harris | hann+pre9 |
|---|---|---|---|---|---|---|
| real detail | 0, 1, 2, 4 | 0.4961 [C] | 0.4961 [C] | 0.4961 [C] | 0.4961 [C] | 0.4961 [C] |
| real flat | 0, 1, 2, 4 | 0.4961 [C] | 0.4961 [C] | 0.4961 [C] | 0.4961 [C] | 0.4961 [C] |
| broadband | 0, 1, 2, 4 | 0.4961 [C] | 0.4961 [C] | 0.4961 [C] | 0.4961 [C] | 0.4961 [C] |

**M41's withdrawal of the FRC crossing (fact 476) is NOT reversible by
windowing.** M44's observation that Blackman and a 9×9 pre-filter each restored
an uncensored crossing at `sb = 4` does not reproduce here, and the reason is now
visible: those measurements were made without an FPN term at this ρ. Windows
change the leakage floor by 25 dB and change the censoring by nothing.

**The crossing stays withdrawn. The FRC *curve at a fixed frequency* does not** —
it is one of the two factors in the statistic that works.

---

## 8. Scope item 5: what a working metric lets us test in shipped code

**Enumeration note (rule 24).** `crates/strehl-core/src/merge.rs` contains no
literal list of five acceptance invariants. I enumerated the tests that assert a
**quality contract** rather than a mechanical one (order-independence, memory
bounds, error paths and argument validation are excluded). A verifier should
re-choose this enumeration rather than re-derive my line numbers. Read-only; I
edited nothing under `crates/`.

| # | invariant | `merge.rs` | what it proves | what it does **not** prove |
|---|---|---|---|---|
| 1 | `averaging_beats_one_frame_and_selection_does_not` | 1140 | merged σ falls as `1/√n` for `n ≥ 2` | that the merged image is not blurrier than one frame |
| 2 | `with_one_frame_clearly_sharpest_the_estimator_degenerates_to_a_selector` | 1006 | the **weights** collapse to a delta | that selection delivered the sharp frame's resolution |
| 3 | `with_frames_that_agree_the_estimator_averages_them` | 1025 | the **weights** flatten | that averaging cost no detail |
| 4 | `the_regulariser_dilutes_a_focus_spike_by_its_area_and_no_more` | 1298 | the **focus field** is diluted by exactly the kernel area | that the diluted field produced a sharp image |
| 5 | `the_regulariser_preserves_a_real_depth_edge` | 1343 | the **field** keeps its edge | that the image keeps its edge |

**ARGUED, and this is the point.** Invariant 1 is a noise assertion. Invariants
2–5 are assertions about the *weights* and the *focus field* — intermediates.
**Not one of the five measures the delivered image's resolution.** The project can
prove that it smooths noise correctly and that its weight-selection logic behaves,
and it cannot prove that the thing it hands the user is not blurred. That gap is
precisely the thesis it claims.

The CLI states the pair explicitly (`crates/strehl-cli/src/merge_cmd.rs:30-34`):

> Two acceptance invariants, and they are a **pair**. Fact 19 measured a plain
> mean at 0.534x the single-frame noise; fact 24 measured that the same plain
> mean collapses detail-region gradient by 58%. Either number alone can be won
> trivially by a merge that is wrong in the other direction.

**MEASURED, and this is a live defect in shipped acceptance.** The CLI's
"ACCEPTANCE INVARIANT 2 of 2: detail retention" is a **detail-region gradient** —
i.e. `mean_grad`. `b3` measured `mean_grad` at **S = 0.233** on real detail,
**0.249** against a post-filter and **0.018** in paired form. **The shipped detail
half of the pair cannot distinguish blur from noise smoothing.** The pairing was
supposed to make the two numbers hard to game together; §6.3 measured that
pairing does not rescue a statistic that cannot separate.

**What a working `sigpow` would let the project test, that it cannot today:**

1. **That the merged plane is not blurrier than its own sharpest input** — the
   missing half of invariant 1. Two half-stack merges give the pair; `sigpow` at
   `f_sig` gives the number. **This is the thesis, and it is currently unscored.**
2. **That the regulariser (invariants 4 and 5) costs no delivered resolution.**
   Both are currently proved on the focus *field*. `sigpow` moves the assertion to
   the image, where the claim actually lives.
3. **That gate width trades noise against resolution as claimed** — `sigpow` vs
   gate is measurable per ring, so M42's window ladder gets a resolution axis.
4. **That the estimator is not a low-pass filter in disguise** — §6.4 is exactly
   this test, and it is the one every correlation metric fails by construction.
5. **That `selection_inflation` can be re-priced honestly.** `merge.rs:122` now
   reads `SELECTION_INFLATION: f32 = 1.0` because M40 refuted the 1.074, leaving
   `n = 1` *unpriced* and the model "known to be optimistic" (comment at 1136).
   Pricing selection needs a statistic that reads what selection delivers, not
   what it promises.

---

## 9. What I could not measure

1. **A false-alarm rate on a featureless source.** §5.3 — no such source exists on
   this sensor. Once the scene is removed the fixed pattern is still structure.
   The assigned bar's second half is unconstructible, not merely unmet.
2. **`sigpow` on a real merge from shipped code.** Everything here is a Python
   reimplementation reading raw frames; `crates/` was read-only for this
   milestone. The statistic is defined and validated but not wired.
3. **Whether `sigpow` holds across sensors.** ρ = 0.3094 is this body's fixed
   pattern. On a sensor with lower ρ, `sigpow`'s FPN pedestal shrinks and the
   statistic should get *better*, but that is **ARGUED**, not measured. The corpus
   has one body.
4. **An absolute resolution number.** `sigpow` is a **contrast** statistic: it
   compares two merges. It does not report "this image resolves X cyc/px". Fact
   475's censoring means no absolute crossing is available and §7.4 measured that
   no window recovers one.
5. **`sigpow` against real optical defocus.** The blur here is a synthetic
   Gaussian. Real defocus is a disc with zero crossings and the response may not
   be monotonic through them.
6. **Whether ρ is stable across the frame.** It was estimated once, on one flat
   ROI. PRNU is multiplicative and should scale with level.

---

## 10. Reproducing this

```powershell
$env:PYTHONIOENCODING = 'utf-8'
cd C:\dev\blog\death-of-software\projects\strehl\experiments\m46-detail-metric

# b1 and b2 are frozen (rule 15) and their artifacts are committed.
# b1 needs read access to C:\dev\macro (READ-ONLY) and takes ~86 s.
python -u src\b1_pair.py       > out\b1_pair.log       2>&1   # 85.9 s
python -u src\b2_recovery.py   > out\b2_recovery.log   2>&1
python -u src\b3_separation.py > out\b3_separation.log 2>&1   # 225.7 s
python -u src\b4_leakage.py    > out\b4_leakage.log    2>&1   #   4.6 s
python -u src\b5_bar.py        > out\b5_bar.log        2>&1   #  48.3 s
```

`b3`, `b4` and `b5` read `out/b1_merges.npz` and `out/b1_results.json` and need
no raw access. `b1_merges.npz` is **not committed** (repo-root `.gitignore`
excludes `*.npz`); re-run `b1` to regenerate it.

Do **not** use `Tee-Object` — it swallows all output if the process faults.
`rawpy`'s `raw_image_visible` is a view into a buffer freed when the
`with rawpy.imread(...)` block exits; slicing it afterwards is an access
violation (exit `-1073741819`). All slicing happens inside the `with`.

Environment: Python 3.12, numpy 2.4.4, scipy 1.17.1, rawpy 0.27.0, exifread.

**Every number above is deterministic.** Seeds are fixed (`SEED_FPN = 4242`,
draw seeds `base + 1000·r + 7`), ρ is read from `b1_results.json` rather than
re-estimated, and `m41lib`/`m41lib3` are imported unchanged.

---

## 11. Deviations from pre-registration

| # | deviation | why |
|---|---|---|
| D6 | PM-1 "post-capture" split into **PM_A / PM_B / PM_C** | the registered wording was ambiguous between two physically different operations. An arm was **added**, never removed. Declared in `m46lib.py` and `b2`'s docstring at the time, not retrospectively. |
| D7 | `b3`'s matching direction reversed | the registered direction (solve `k` from `sb`) has **no solution** on this data at any width down to 0.125 px. The failed direction is re-measured *inside* the frozen script (§6.1) rather than dropped. |
| D8 | `oracle_fsc` supplemented by `oracle_mtf` | `oracle_fsc` is itself a correlation metric and inherits §6.4's blindness: `FSC(H·L, L) = 1` for any real positive `H`, so its truth channel is degenerate and its recovery denominator → 0 (hence the +144 to +222 blow-ups in §5.1). `oracle_mtf` is the amplitude-sensitive regression estimate `Re⟨Y·conj(L)⟩/⟨|L|²⟩`. Both are reported. |
| D9 | the assigned bar's flat half replaced by a separation contrast | pre-declared in PREREGISTRATION §3 as the response to "even the oracle fails", and §4.3 pre-registered BLUR-ONLY/SMOOTH-ONLY as the replacement instrument. The replacement is **harder**: it adds a post-filter arm (§6.4) that the assigned bar never asked for and that most incumbents fail. |

The pre-registration document itself was not edited after `2474e5d`.

---

## Proposed disciplines

*(unnumbered — §5 has had four numbering collisions)*

- **A metric built from a single statistic will fail here; the working one is a
  product of two.** `FRC` measures recoverable information per ring and is blind
  to any linear post-filter. Ring power measures delivered energy and cannot tell
  signal from noise. Their product measures delivered *signal*. Before proposing
  a new detail metric, state which of those two quantities it estimates; if the
  answer is "one of them", it will fail one of §6.2 or §6.4.

- **Before scoring a metric on a "flat" region, measure the region's rule-10
  detector.** A featureless ROI reads ≈1. Anything above ~2 has content, and a
  metric that fires there is detecting a real loss, not raising a false alarm.
  Fact 477's flat readings were correct detections misread as failures.

- **A false-alarm control needs a source that is both featureless and
  perturbable.** On a sensor with fixed-pattern noise, removing the scene does
  not remove the structure, so the control cannot be built. Use a within-source
  contrast at matched cost instead: it needs no featureless source.

- **When a negative control returns the same value as the live arm, ask what is
  common-mode between the two halves before blaming the estimator.** Two
  independent captures 76 s apart failed to decorrelate the flat ROI because FPN
  is common to the sensor, not to the stack. The 0.4961 censoring survived four
  windows and a pre-filter for the same reason.

- **Pair a statistic to remove a nuisance, never to create sensitivity.**
  Conditioning a detail reading on a flat reading made every incumbent *worse*
  (`hp_sd` 0.501 → 0.060) because the denominator moves with the numerator.
  Only a statistic that already separates gains from being paired.

- **A matched-cost design must state which direction of the matching is
  feasible, and report the infeasible one.** That the detail ROI's entire noise
  budget is worth less than a 0.125 px blur is a stronger result than the
  bisection that failed to find it.

## Proposed owner questions

*(unnumbered)*

- `sigpow_fsig` is validated in Python against synthetic plants. Wiring it into
  the CLI as a third acceptance invariant means merging two disjoint half-stacks
  on every run — roughly 2× the merge cost. Is that acceptable as a `--verify`
  flag, as a default, or not at all?

- The CLI's shipped "ACCEPTANCE INVARIANT 2 of 2: detail retention" is a
  detail-region gradient, measured here at S = 0.233. Should it be replaced, or
  kept alongside `sigpow` as a cheap screen with its limitation documented?

- `merge.rs:122` sets `SELECTION_INFLATION = 1.0`, leaving `n = 1` unpriced and
  the noise model "known to be optimistic". With a resolution statistic available,
  is re-pricing selection a milestone worth opening?

- ρ = 0.3094 was measured on one flat ROI of one body. Does the corpus contain a
  second body, or a dark-frame series at matched exposure, that would let the FPN
  fraction be measured independently rather than solved from an FRC reading?

- Invariants 4 and 5 prove the regulariser's behaviour on the focus *field*.
  Should they be restated on the delivered image, given that the field-level
  proof is what the thesis is actually claimed about?

---

## Proposed SYNTHESIS entries

| # | Fact | Consequence | Source |
|---|---|---|---|
| P1 | The `112MSDCF`/`113MSDCF` "full stop" of fact 52 is a stop of **exposure time**, not gain: ISO 500 on both, 1/60 s vs 1/30 s, f/11, 200 mm. `g` and read-noise-in-DN are therefore identical and `113` is **quieter** after rescaling — measured ratio 0.7107 against the predicted 1/√2 = 0.7071. | | MEASURED, `experiments/m46-detail-metric/out/b1_pair.log` §1 |
| P2 | The photon-transfer model must be evaluated on each capture's **own unscaled DN** with variance carried through the photometric scale as `c²·var`. The reverse order charges the longer exposure shot noise for photons it never collected and inverts the sign of the comparison by √2. | | DERIVED, pre-registered `PREREGISTRATION.md` §4.1 before any data was read |
| P3 | Two **independent captures** of the same subject do not decorrelate the flat ROI: two-capture FRC at `f_sig` reads +0.7310 on flat against the within-capture split-half's +0.6569, and the rule-9 flat/detail ratio is 0.7714. Fixed-pattern noise is common-mode to the **sensor**, not to the stack. | | MEASURED, `out/b1_pair.log` §7-8 |
| P4 | The fixed-pattern variance fraction on this body is **ρ = 0.3094** of single-frame noise variance, solved as `FRC_flat/(1−FRC_flat)/n_eff`. The pure-FPN FRC floor `ρ/(ρ + 1/n_eff)` predicts +0.7622 and measures **+0.7653** on a synthetic source where ρ was not fitted — 0.4 % agreement. | | DERIVED from `out/b1_pair.log`; confirmed MEASURED, `out/b4_leakage.log` §2 |
| P5 | The `sb = 0` FRC censoring of question 120 is **not spectral leakage**. On a latent band-limited at 0.20 cyc/px by construction, ring power at 0.45 cyc/px is **−138.6 dB** under the incumbent Hann window and −159.1 dB under Blackman-Harris. Leakage is 14 orders of magnitude below the signal. | | MEASURED, `out/b4_leakage.log` §1 |
| P6 | The censoring is caused by **common-mode fixed-pattern noise, which is white to Nyquist**. Without FPN the harness recovers the true band limit exactly — crossing 0.2058 on a latent cut at 0.20 cyc/px, uncensored. Adding FPN at ρ = 0.3094 pins the crossing at 0.4961 [CENSORED] and lifts FRC(0.45) from +0.018 to +0.767 on a source with **zero** true power there. | | MEASURED, `out/b4_leakage.log` §2 |
| P7 | No window repairs the censoring: **60 of 60 cells** (rect, Hann, Blackman, Blackman-Harris, Hann+9×9 pre-filter) × (real detail, real flat, broadband) × (`sb` = 0, 1, 2, 4) read 0.4961 [CENSORED]. Fact 476's withdrawal of the FRC **crossing** is not reversible by windowing. | | MEASURED, `out/b4_leakage.log` §3 |
| P8 | The merged detail ROI carries `hp_sd` 58.8 DN of scene against σ 3.69 DN of noise, so **removing every electron of noise costs less `hp_sd` than a 0.125 px blur** (residual +0.2374). On this corpus a merge cannot fake sharpness by denoising. | | MEASURED, `out/b3_separation.log` §1 |
| P9 | Fact 477's flat-ROI firings were **correct detections, not false alarms**. The observed flat ROI's rule-10 detector reads 6.43 — it has real content — so blurring it destroys real content and an honest metric must fire. The oracle holding the true latent fires too, at +0.9513 to +1.0000. | | MEASURED, `out/b2_recovery.log`; `out/b5_bar.log` §1 |
| P10 | **On a sensor with fixed-pattern noise there is no source that is both featureless and blurrable**, so a flat-ROI false-alarm control cannot be constructed. A constant latent yields an undefined recovery ratio under PM_A (`H·const = const`, truth denominator exactly zero); under PM_B/PM_C the only structure present is the fixed pattern and every statistic including `oracle_mtf` reads ≈ +1.0. | | MEASURED, `out/b5_bar.log` §2-3 |
| P11 | Ring FRC is `C/(C+U)`; a linear post-filter scales `C` and `U` by the same `\|H\|^2`, so the ratio cannot move. **Every correlation metric — including an FSC against ground truth — is blind by construction to a merge that low-passes its own output.** Measured separation against a matched post-filter: `frc2_at_fsig` **0.000**, `oracle_fsc` **0.000**. | | DERIVED; MEASURED, `out/b2_recovery.log`; `out/b3_separation.log` §4 |
| P12 | Absolute-power statistics are the mirror failure: against a post-filter matched to the same `hp_sd` cost, `hp_sd` 0.501, `p_ratio` 0.304, `mean_grad` 0.249, `ringpow` 0.566 — they read the loss at full strength and cannot tell that what was removed was noise. | | MEASURED, `out/b3_separation.log` §4 |
| P13 | **`sigpow(f) = FRC(f) · P_ring(f)` is an admissible detail metric.** It equals the per-ring common power `C`, which is signal. Separation against noise smoothing at matched `hp_sd` cost: **0.937** on real detail, **0.917** on the flat ROI, **0.990** on broadband; against a matched post-filter **0.931**; as a paired detail/flat ratio **0.973**. It requires no ground truth. | | MEASURED, `out/b3_separation.log` §3-6 |
| P14 | `sigpow`'s scores were measured in the **shippable** configuration: the two images share one fixed pattern and differ only in independent noise, which is exactly two merges built from disjoint halves of one stack. Independent captures are not required — P3 measured that they buy nothing. | | DERIVED from `b3_separation.py::draw`; MEASURED, `out/b3_separation.log` |
| P15 | `oracle_mtf` — the ring-averaged regression `Re⟨Y·conj(L)⟩/⟨\|L\|^2⟩` — separates at **0.958** on detail and **0.953** against a post-filter, confirming the plant can express the effect (rule 20). `oracle_fsc` cannot be used as a positive control: `FSC(H·L, L) = 1` for any real positive `H`, so its truth channel is degenerate and its recovery blows up to +144 to +222. | | MEASURED, `out/b3_separation.log` §3-4; `out/b5_bar.log` §1 |
| P16 | **Pairing is a normalisation, not an instrument** (question 119). Conditioning a detail reading on the same merge's flat reading made every incumbent worse — `hp_sd` 0.501 → 0.060, `ringpow` 0.587 → 0.050, `mean_grad` 0.233 → 0.018 — because the denominator moves with the numerator under smoothing. Only `sigpow`, which already separated, improved (0.937 → 0.973). | | MEASURED, `out/b3_separation.log` §5 |
| P17 | The five quality invariants in `crates/strehl-core/src/merge.rs` (lines 1140, 1006, 1025, 1298, 1343) assert noise behaviour and **focus-field** behaviour. **None measures the delivered image's resolution**, so the project can prove it smooths noise correctly and cannot prove it does not blur — which is the thesis it claims. | | ARGUED from read-only inspection of `merge.rs`; enumeration stated for re-choice per rule 24 |
| P18 | The CLI's shipped "ACCEPTANCE INVARIANT 2 of 2: detail retention" (`crates/strehl-cli/src/merge_cmd.rs:30-34`) is a detail-region gradient, i.e. `mean_grad`, measured here at separation **0.233** on real detail and **0.018** in paired form. The shipped detail half of the acceptance pair cannot distinguish blur from noise smoothing. | | MEASURED, `out/b3_separation.log` §3, §5; ARGUED against `merge_cmd.rs` |
| P19 | The 512 px two-capture harness has demonstrated power: a deliberate-misalignment ladder moves the crossing 0.4961 [C] → 0.4430 → 0.2908 → 0.1131 and FRC at `f_sig` +0.9477 → +0.6663 → +0.2049 → +0.1601 over 0 to 4 px. Censoring at small shifts is the FPN floor, not a dead instrument. | | MEASURED, `out/b1_pair.log` §9 |
| P20 | The measured photometric scale between the pair, 0.5095 (detail) / 0.5082 (flat), agrees with the EXIF exposure ratio 0.5000 to **1.90 %**, passing the pre-registered ≤5 % tolerance. Photometric normalisation on this corpus can be measured from the data rather than taken from metadata. | | MEASURED, `out/b1_pair.log` §6 |
