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

---

# Appendix A — Rust implementation specification for `sigpow`

**Added 2026-08-23.** Nothing above this line is edited; §1–§11 and the P1–P20
table are folded as facts 607-626 (`30d7aff`) and stay put.

**Supporting scripts:** `experiments/m46-detail-metric/src/b6_spec.py`,
`src/b7_split_cost.py`. **Artifacts:** `out/b6_spec.log`, `out/b6_golden.json`,
`out/b7_split_cost.log`, `out/b7_split_cost.json`.

`crates/` was not touched. This is a specification, not an implementation.

---

## A.0 What was not cleanly specifiable — read this first

The brief asked me to say so if any part of `sigpow` turned out to rest on an
implicit choice I could not justify. **Two did**, and both were in the exact
shape the corpus keeps getting bitten by: a NumPy convention I inherited without
noticing I had chosen it.

### A.0.1 The two factors were evaluated at different frequencies

`m46lib.frc_at` selects the correlation by **linear interpolation** between
adjacent ring centres (`np.interp`). `b3_separation.ring_power` selects the
power by **nearest ring**, no interpolation. **MEASURED**, `out/b6_spec.log` §1:
at `f_sig = 0.2762` with `n = 512, nbin = 64` the straddling ring centres are
**0.269531** and **0.277344**, and `f_sig` sits **85.4 %** of the way between
them. So the correlation factor was an 85/15 blend of two rings and the power
factor was one of them outright. **The product was not a per-ring quantity and I
had no reason for it beyond that the two helpers were written months apart.**

### A.0.2 The power reference was asymmetric

`ring_power` used `|A|²` from the **first** image only. **MEASURED**: swapping
the two merges changes the reported value by **1.96 × 10⁻²** — 2 %, on real
data. A statistic whose value depends on which half-merge you pass first is not
a statistic.

### A.0.3 Both are fixed by the same change, and it makes `sigpow` simpler

Write the product out on a single ring, with a symmetric power reference:

```
FRC_i = Re( Σ A·conj(B) ) / sqrt( Σ|A|² · Σ|B|² )
P_i   = sqrt( Σ|A|² · Σ|B|² ) / count_i
────────────────────────────────────────────────
FRC_i · P_i = Re( Σ A·conj(B) ) / count_i
```

> **`sigpow` is the mean per-mode real cross-power of one ring.**
> No ratio. No interpolation. No asymmetry. Nothing to divide by zero.

**MEASURED**, `out/b6_spec.log` §2: the identity holds to a relative
**1.4 × 10⁻¹⁶** on the detail ROI and **0.0** on the flat ROI — machine
precision. **MEASURED**: the canonical form is exactly symmetric under swap
(0.000 × 10⁰ vs the old form's 1.96 × 10⁻²), and reads 0.9898 × the old value.

### A.0.4 The conclusion survives the re-choice, and improves

Rule 24 demands that verification **re-choose**. Fact 619's separation score was
re-measured under the canonical conventions on the same plants, same seeds, same
ρ. **MEASURED**, `out/b6_spec.log` §3:

| source | contrast | old (fact 619) | **canonical** |
|---|---|---|---|
| `S_detail` | blur vs smoothing | 0.937 | **0.995** |
| `S_detail` | post-filter vs smoothing | 0.931 | **0.994** |
| `S_flat` | blur vs smoothing | 0.917 | **0.936** |
| `S_flat` | post-filter vs smoothing | 0.976 | **0.982** |

**Fact 619 is not an artifact of the inconsistent selection — it was measured
*through* it, and the clean form is strictly better.** Implement the canonical
form. Everything below specifies it.

### A.0.5 One error in a frozen docstring

`b6_spec.py::sigpow`'s docstring says the value "scale[s] as the fourth power of
a linear scaling of the input". **That is wrong; it is the second power.**
`a → λa, b → λb` gives `A → λA, B → λB` and the product `→ λ²`. **MEASURED**: a
×3 input scaling multiplies `sigpow` by 8.999999999999991. `b6_spec.py` is
frozen under rule 15 and is not edited; the correction is recorded here and
A.4.1 states the right rule.

---

## A.1 The definition, unambiguously

Anywhere a NumPy default is load-bearing it is **named**, because that is the
shape of most defects in this corpus.

### A.1.1 Signature

```rust
pub enum SigpowStatus { Ok, NoRings, ZeroPower }

/// Mean per-mode real cross-power of the ring nearest `f_sig`.
pub fn sigpow(
    a: &[f64], b: &[f64],   // row-major, len == n*n
    n: usize,
    f_sig: f64,             // cyc/px; ships as 0.2762
    nbin: usize,            // ships as 64
) -> Result<(f64, SigpowStatus), SigpowError>;
```

### A.1.2 Input validation — reject, do not coerce

| condition | behaviour | why |
|---|---|---|
| `a.len() != b.len()` | `Err(ShapeMismatch)` | |
| not square (`len != n*n`) | `Err(NotSquare)` | the ring grid assumes one `n` |
| **`n` odd** | **`Err(OddSize)`** | see below — **this is a ruling, not an inheritance** |
| `n < 32` | `Err(TooSmall)` | see A.1.9 |
| `nbin == 0` | `Err(BadBins)` | |
| any non-finite input | `Err(NonFinite)` | |

**MEASURED**, `out/b7_split_cost.log` §D: the Python reference **accepts** odd
`n` and returns a number (n=15 → `+9.45820296e+00`, n=17 → `+9.82483260e+00`).
**The spec overrides the reference here.** For odd `n`, `fftshift` places DC at
index `n/2` and the positive and negative frequency counts differ by one, so the
ring masks are asymmetric by one sample and the answer depends on an FFT
library's shift convention rather than on the image. A merge ROI is chosen by
the caller and can always be even. Rejecting is free; a silently
convention-dependent number is not.

### A.1.3 Mean removal, then window — in that order

```
mean_a = (1/n²) Σ a[y][x]              // arithmetic mean of the RAW ROI
a'[y][x] = (a[y][x] − mean_a) · w[y] · w[x]
```

**The mean is removed BEFORE the window is applied.** The windowed field is
therefore *not* zero-mean. Reversing the order — windowing first, then removing
the windowed mean — is a different statistic. **MEASURED**: `sigpow` is
invariant to a constant offset (adding 1000 DN changes it by 2 × 10⁻¹⁴
relative), which is the property this ordering buys.

### A.1.4 The window — **symmetric** Hann, not periodic

```
w[k] = 0.5 − 0.5·cos( 2π·k / (n − 1) ),   k = 0 .. n−1
```

**Note the `n − 1`.** This is `numpy.hanning`. It is **not** the periodic
(DFT-even) Hann `0.5 − 0.5·cos(2πk/n)` that most DSP texts and
`scipy.signal.get_window("hann", n)` give by default. The symmetric form has
`w[0] = w[n−1] = 0` exactly; the periodic form has `w[n−1] ≠ 0`.

**This is the single likeliest porting bug and it is measurable. MEASURED**,
`out/b6_spec.log` §4:

| n | `max abs(w_sym − w_per)` | `w_sym[n−1]` | `w_per[n−1]` |
|---|---|---|---|
| 16 | 1.545085e−01 | 0.0 | 0.038060 |
| 64 | 3.787507e−02 | 0.0 | 0.002408 |
| 512 | 4.706208e−03 | 0.0 | 0.000038 |

On the real detail pair the two windows give `5.11913118e+07` (symmetric) vs
`5.12660861e+07` (periodic) — a relative **1.4607 × 10⁻³**. That is **146 ×**
the golden-vector tolerance of A.2.4, so **the golden vectors catch this bug.**

The 2-D window is the **outer product** `w[y]·w[x]`, not a radial window.

### A.1.5 The FFT — unnormalised forward, f64

* **Forward transform, no scaling factor.** `numpy.fft.fft2` with `norm=None`
  applies **no** normalisation on the forward direction (the `1/N` lives on the
  inverse). A Rust FFT crate that applies `1/N` or `1/√N` forward will produce a
  `sigpow` too small by `n⁴` or `n²`. **Name the convention in the code.**
* **Full complex 2-D transform**, not `rfft2`. The ring masks below index the
  full `n × n` shifted grid. An `rfft2` layout stores only `n/2 + 1` columns and
  **must not** be substituted without re-deriving the masks and the
  double-counting of conjugate pairs. Using the full transform is ~2 × the FFT
  cost and removes an entire class of bug; A.5 shows the FFT is 0.1 % of the
  pipeline, so buy the safety.
* **Accumulate in `f64`.** NumPy silently upcasts `float32` input to
  `complex128`, so the Python reference has always been f64 internally even when
  handed f32 arrays. An f32 pipeline is *permitted* — A.2.4's tolerance is set
  to allow it — but the reference is f64 and the tolerance assumes f64 for the
  ring sums.

### A.1.6 The shift — DC to the centre

Apply `fftshift` in both axes, so DC lands at index `(n/2, n/2)` with integer
division. Equivalently, index the ring grid at
`rr = hypot(y − n/2, x − n/2)` over the shifted array.

### A.1.7 Ring geometry

```
rmax   = floor(n / 2)                  as f64        // INTEGER division first
edges[i] = rmax · i / nbin,            i = 0 .. nbin // linspace(0, rmax, nbin+1)
centre_cycpx[i] = 0.5·(edges[i] + edges[i+1]) / n
mask_i  = { (y,x) : edges[i] ≤ rr < edges[i+1] }     // LOWER INCLUSIVE, UPPER EXCLUSIVE
count_i = |mask_i|
```

Four consequences a Rust author will not guess:

1. **`rmax` is `n/2`, not `n/2 − 1` and not `n/√2`.** The FFT square's corners
   sit at `rr = (n/2)·√2 > rmax` and are therefore **outside every ring and
   discarded**. **MEASURED** at `n = 512`: **205 857 of 262 144 modes** are
   binned — **78.5 %**. The corners are not a rounding detail; they are a fifth
   of the plane, deliberately dropped, because they are not isotropically
   sampled.
2. **DC is inside ring 0** (`rr = 0` satisfies `0 ≤ 0 < edges[1]`). The mean
   removal of A.1.3 is what keeps it from dominating. Do not special-case it.
3. **Nyquist is at `rr = n/2` exactly, which is `edges[nbin]`, and is EXCLUDED**
   by the half-open upper bound. Only `rr < n/2` is binned.
4. **The last ring's centre is fact 613's censoring endpoint.** At `n = 512,
   nbin = 64`: `edges[63] = 252, edges[64] = 256`, centre
   `254/512 = 0.49609375` = **0.4961**. If an implementer ever reduces this
   ring grid to a 1/7 crossing, that constant is what they will get; see A.4.3.

### A.1.8 Sparse rings are **dropped**, and dropping renumbers

```
if count_i < 8 { skip this ring entirely }
```

The surviving rings form a **compacted** list. Ring *positions* in that list do
**not** equal ring *indices* `i`. The original Python had this bug latent:
`frc_at` interpolated on the compacted array while `ring_power` computed centres
from the full `edges` array. At `n = 512, nbin = 64` no ring is ever dropped so
it never fired, but at small `n` it would.

**Compute the correlation, the power and the centre for each surviving ring in
ONE pass and keep them together.** Never index two parallel arrays built by
different code paths. This is the structural fix, and it is why A.1.1 returns a
single value rather than exposing the two factors.

**MEASURED**, `out/b7_split_cost.log` §D — dropping is real at small sizes:

| n | nbin | rings surviving | status |
|---|---|---|---|
| 8 | 64 | 3 of 64 | Ok |
| 9 | 2 | 2 of 2 | Ok |
| 15 / 16 / 17 | 4 | 4 of 4 | Ok |
| 4 | 8 | 0 of 8 | **NoRings** |
| 2 | 4 | 0 of 4 | **NoRings** |

### A.1.9 Ring selection — nearest centre, among survivors

```
j = argmin over SURVIVING rings of |centre_cycpx − f_sig|
```

No interpolation (A.0.1). Ties: take the lower index.

`f_sig = 0.2762` cyc/px is **fact 27's measured optical cutoff for the green
plane of this body and lens**. It is a **calibration constant, not a tuning
knob** — changing it changes what "detail" means and invalidates comparison with
every number in this document. At `n = 512, nbin = 64` it selects the ring with
centre **0.277344** and **3580 modes**.

`n ≥ 32` is required (A.1.2) so that the selected ring is populated by more than
a handful of modes; at `n = 512` it holds 3580, at `n = 64` it holds 32.

### A.1.10 The value

```
Ok  =>  Σ_{mask_j} Re( A·conj(B) ) / count_j
```

with `Re(A·conj(B)) = Re(A)·Re(B) + Im(A)·Im(B)`.

Guards, in order:

| check | status | value |
|---|---|---|
| no surviving rings | `NoRings` | `0.0` |
| `Σ abs(A)²  ≤ 0` **or** `Σ abs(B)² ≤ 0` on ring `j` | `ZeroPower` | `0.0` |
| otherwise | `Ok` | the sum above |

`ZeroPower` fires on a constant image, because mean removal makes the windowed
field identically zero. **Return the status; do not return `NaN` and do not
return a bare `0.0` that a caller can mistake for a measurement.** Fact 475 is
what happens when a sentinel is returned without a flag.

---

## A.2 Golden vectors

### A.2.1 Building the inputs with no shipped data

Two closed-form generators. Both are exactly reproducible in Rust.

**Sinusoid.** `ky, kx` integers:

```
sine(n, ky, kx, amp, phase)[y][x] = amp · cos( 2π·(ky·y + kx·x)/n + phase )
```

**Hash field.** A splitmix-style 32-bit mixer. **All arithmetic is wrapping
`u32`** — `wrapping_mul`, `wrapping_add`, logical `>>`:

```rust
fn mix32(y: u32, x: u32, seed: u32) -> u32 {
    let mut h = y.wrapping_mul(0x9E37_79B1);
    h = h.wrapping_add(x.wrapping_mul(0x85EB_CA77));
    h = h.wrapping_add(seed);
    h ^= h >> 16;  h = h.wrapping_mul(0x7FEB_352D);
    h ^= h >> 15;  h = h.wrapping_mul(0x846C_A68B);
    h ^= h >> 16;
    h
}
// hash_field[y][x] = (mix32(y,x,seed) as f64) / 4294967296.0 * 2.0 - 1.0   in [-1, 1)
```

`4294967296.0` is `2^32` as an exact `f64`. Cast `u32 → f64` directly; do not go
via `i32`. In Python this must be done with arbitrary-precision `int` and an
explicit `& 0xFFFFFFFF`, because NumPy `uint32` raises on overflow — that is why
the reference implements it the long way.

### A.2.2 The vectors

**MEASURED**, `out/b6_golden.json`. Compare with the **relative** tolerance of
A.2.4.

| # | input `a` | input `b` | `n` | `nbin` | `f_sig` | expected `sigpow` | status |
|---|---|---|---|---|---|---|---|
| G1 | `const 7.0` | `const 7.0` | 16 | 8 | 0.25 | `0.0` | **ZeroPower** |
| G2 | `sine(16,0,4)` | `sine(16,0,4)` | 16 | 8 | 0.25 | `+3.7865519412e+01` | Ok |
| G3 | `sine(16,0,4)` | `sine(16,0,4,phase=π)` | 16 | 8 | 0.25 | `−3.7865519412e+01` | Ok |
| G4 | `hash(32,seed=1)` | `hash(32,seed=2)` | 32 | 8 | 0.25 | `+1.7820505318e+00` | Ok |
| G5 | `sine(32,3,5,10)+hash(32,11)` | `sine(32,3,5,10)+hash(32,12)` | 32 | 16 | 0.20 | `+4.8922777909e+04` | Ok |
| G6 | `hash(16,seed=3)` | `hash(16,seed=3)` | 16 | **1** | 0.25 | `+8.9943617850e+00` | Ok |
| G7 | `hash(8,seed=4)` | `hash(8,seed=4)` | 8 | 64 | 0.25 | `+4.5688350859e+00` | Ok\* |
| G8 | `hash(64,seed=21)` | `hash(64,seed=21)` | 64 | 64 | 0.2762 | `+1.8957532293e+02` | Ok |

Sinusoid amplitudes are 1.0 unless given. G2/G3 use `ky=0, kx=4`; G5 uses
`ky=3, kx=5, amp=10`.

Ring bookkeeping, which should be asserted separately because it localises a
failure to the geometry rather than the arithmetic:

| # | selected ring centre | `count_j` | surviving rings |
|---|---|---|---|
| G1–G3 | 0.21875 | 20 | 8 of 8 |
| G4 | 0.21875 | 84 | 8 of 8 |
| G5 | 0.203125 | 36 | 16 of 16 |
| G6 | 0.25 | 193 | 1 of 1 |
| G7 | 0.27734375 | 8 | **3 of 64** |
| G8 | 0.27734375 | 32 | 64 of 64 |

### A.2.3 What each one pins

* **G1 — degenerate, constant image.** Mean removal zeroes the field. Pins the
  `ZeroPower` path. An implementation that divides before checking returns
  `NaN`; one that returns a bare `0.0` looks like a measurement.
* **G2/G3 — adversarial sign.** Same magnitude, **opposite sign**. `sigpow` is a
  cross-power and **is signed**. Anti-correlated merges give a negative reading.
  An implementation that takes `abs()` or squares somewhere passes G2 and fails
  G3, which is exactly why the pair exists.
* **G4 — near-zero common power.** Two independent hash fields. The reading is
  small but **not** zero: 84 modes of finite-sample cross-power. Pins that the
  implementation does not "helpfully" clamp small values.
* **G5 — the real case.** Shared sinusoid under independent noise: large
  positive common power. The comfortable middle.
* **G6 — a single ring.** `nbin = 1`, one ring spanning the band, 193 modes.
  Pins the ring loop against off-by-one at the boundaries.
* **G7 — 61 of 64 rings dropped.** `n = 8, nbin = 64`. Pins A.1.8's compaction:
  the selected ring's *position* is 2 while its *index* is 35. An
  implementation that indexes the full `edges` array selects the wrong ring or
  panics. **This is the vector that catches the latent parallel-array bug.**
* **G8 — the shipping configuration.** Real `f_sig`, real `nbin`.

\* G7's status is `Ok`, not `NoRings`: at `n = 8` three rings still clear the
8-mode floor. `NoRings` needs `n ≤ 4` — assert it separately with
`sigpow(hash(4,1), hash(4,1), n=4, nbin=8)` → `NoRings`. Both G7 and that case
sit below the `n ≥ 32` guard of A.1.2, so **test the library function directly,
below the guard**; shipped code can never reach them.

Rejection cases — assert `Err`, not a value:

| input | expected |
|---|---|
| `n = 15` (odd) | `Err(OddSize)` — reference returns `+9.45820296e+00`; **spec overrides** |
| 16×32 | `Err(NotSquare)` |
| `a` 16×16, `b` 32×32 | `Err(ShapeMismatch)` |
| `n = 16` through the shipped entry point | `Err(TooSmall)` |

### A.2.4 The tolerance, and why

**Relative tolerance `1e-5`. Absolute tolerance is meaningless here** — the
values span `1.78e+00` to `4.89e+04` in the vectors and `5.1e+07` on real data.

The bound is bracketed by measurement, not guessed.

**Floor — differences a correct implementation may legitimately have.**
**MEASURED**, `out/b6_spec.log` §5 and `out/b7_split_cost.log` §C:

| perturbation | relative difference |
|---|---|
| ring summation order reversed | 1.455e−16 |
| pairwise vs naive accumulation | 0.0 |
| full `f32` pipeline, n = 16 | 8.209e−08 |
| full `f32` pipeline, n = 32 | 4.597e−07 |
| **full `f32` pipeline, n = 64** | **2.187e−06** |
| full `f32` pipeline, n = 512 | 3.213e−07 |

**Ceiling — the smallest *real* bug.** The periodic-Hann substitution of A.1.4:
**1.4607e−03** on real data at `n = 512`, and larger on the small vectors
because `max abs(w_sym − w_per)` grows as `n` shrinks (0.155 at `n = 16` against
0.0047 at `n = 512`).

`1e-5` sits **4.6 ×** above the worst legitimate f32 error in the golden-vector
size range and **146 ×** below the smallest real defect. That gap is why an f32
implementation is permitted (A.1.5) without weakening the test.

**Do not tighten this to `1e-12` to "be safe".** It would fail any
implementation that does not use f64 end to end, which is a constraint the
statistic does not need. **Do not loosen it past `1e-4`** — the margin to the
Hann bug closes.

The digits above are quoted to 11 significant figures so the constants can be
pasted; **only the first ~5 are being tested.**

---

## A.3 The half-stack split contract

Fact 620 says the shippable configuration is two merges over disjoint halves. It
does not say **which** halves, and **MEASURED, that choice is worth a factor of
212.**

### A.3.1 The measurement

Real stack `112MSDCF`, depth-matched indices 6..68 (62 frames), detail ROI, arm A
merge, canonical `sigpow`. **MEASURED**, `out/b7_split_cost.log` §A:

| split | `n_A` | `n_B` | FRC(`f_sig`) | ring power | `sigpow` | vs parity |
|---|---|---|---|---|---|---|
| **parity** (even / odd) | 31 | 31 | **+0.866129** | 5.16366e+07 | **4.47240e+07** | **1.0000** |
| **contiguous** (first / last) | 31 | 31 | **+0.012041** | 1.75509e+07 | 2.11333e+05 | **0.0047** |
| block-of-2 interleave | 32 | 30 | +0.851047 | 5.33433e+07 | 4.53977e+07 | 1.0151 |
| block-of-4 interleave | 32 | 30 | +0.522431 | 5.49012e+07 | 2.86821e+07 | 0.6413 |
| random permutation | 31 | 31 | +0.681333 | 5.67691e+07 | 3.86787e+07 | 0.8648 |

**The registered prediction was right and the effect is catastrophic. A
contiguous split reads 0.47 % of parity — a 99.5 % collapse.**

**DERIVED, and the mechanism is not subtle.** A focus stack sweeps depth
monotonically. A contiguous half holds only **half the sweep**, so the two
half-merges are in focus on **different parts of the subject**. They are not two
views of one image, so there is almost no common power to measure: FRC falls
from +0.866 to **+0.012**, and the ring power itself falls by a factor of 3
because each half-merge is mostly out of focus.

**The gradient is informative and the spec must respect it.** Block-of-2 is fine
(1.0151), block-of-4 already loses **36 %**, random loses **14 %**. Random loses
because a random half clumps: it will contain runs of three or four consecutive
frames, and those runs are local depth gaps. **So "any interleave" is not
sufficient, and "any random split" is actively wrong.**

### A.3.2 The contract

> **Split by parity of the frame's index in the FOCUS-SORTED stack: even indices
> to half A, odd indices to half B.**
>
> The ordering **must** be the acquisition/focus order — not filename order, not
> a hash, not a shuffle. **MEASURED**: any rule that lets two adjacent frames
> land in the same half degrades the reading monotonically with the run length.

Consequences to write into the implementation:

* **The split applies to the depth-sorted index**, so it interacts with any
  frame reordering or rejection upstream. If the pipeline drops frames (speckle,
  bracket boundary), split **after** the drop, on the surviving order — parity
  of the *original* filename index would leave a run of two on one side wherever
  a frame was removed.
* **Odd frame counts are fine. MEASURED**: forcing `nf = 61` gives `n_A = 31,
  n_B = 30` and `sigpow = 4.47315e+07` — **1.0002 ×** the even-count parity
  value. No special handling, no dropped frame, no padding.
* **Unequal halves do not bias the reading.** A deliberate 3:1 split (46 vs 16)
  reads **1.0585 ×** parity. **MEASURED.** The statistic is not sensitive to
  `n_eff` imbalance, so an implementation need not enforce a balanced split — it
  needs to enforce **interleaving**.
* **Both halves must use the SAME winner field and the SAME regulariser
  settings as the shipped merge**, or the comparison measures the configuration
  rather than the merge.

### A.3.3 Why parity is also the cheapest

The per-frame focus fields (fine / coarse / regularised) are properties of a
**frame**, not of a stack, so both halves reuse them unchanged. Parity requires
no sorting, no auxiliary buffer and no second pass over the focus fields — it is
a stride-2 view. See A.5.

---

## A.4 What the number means at the boundaries

### A.4.1 It is a CONTRAST, never an absolute

**`sigpow` has no meaningful absolute value.** It carries units of (input DN)²
per mode and, **MEASURED**, scales as **λ²** under `a → λa` — a ×3 input scaling
gives ×8.999999999999991. (A.0.5 corrects the frozen docstring, which says λ⁴.)
It also changes with `n`, with `nbin`, with the ROI's content and with the
exposure.

> **Only ever compare `sigpow` values computed with the same `n`, the same
> `nbin`, the same `f_sig`, the same ROI and the same frames.**

The shipped use is a **within-ROI, within-stack A/B**: merge configuration 1 vs
configuration 2, reported as the fractional change

```
d = (sigpow_ref − sigpow_test) / abs(sigpow_ref)
```

so that **positive `d` means the test merge lost signal**. Reporting a bare
`sigpow` in a log is not wrong, but it is not a result.

### A.4.2 Good, bad, and how large a change matters

Scale reference from the milestone measurements. **MEASURED**,
`out/b6_spec.log` §3, real detail ROI at merged noise:

| what happened | `d` |
|---|---|
| a `sb = 0.05 px` optical blur | **+0.00727** |
| a matched-cost linear post-filter | **+0.00662** |
| halving the noise variance (`k = √2` more frames) | **+0.00004** |

**The signal-to-nuisance ratio is roughly 180:1** — a blur that costs the same
`hp_sd` as a real doubling of the acceptance set moves `sigpow` by 180 × as much
as the doubling itself does. That is the entire point of the statistic, and it
is why the separation score is 0.995.

Practical reading, **ARGUED** from those numbers:

* `abs(d) < 0.0005` — indistinguishable from a pure noise change. **No detail
  claim in either direction.**
* `d > +0.003` — the test merge **delivered less signal**. At this ROI that is
  roughly a 0.02 px equivalent blur or worse.
* `d < −0.003` — the test merge delivered **more** signal. Legitimate for a
  genuinely better merge; but see A.4.3, because it is also what
  **misregistration in the reference** looks like.

These thresholds are ROI-dependent and are a starting point, not a calibration.
Re-derive them on a new ROI by planting a blur of known width and reading `d`.

### A.4.3 What makes a reading invalid

**Rule 20 applied to the metric's own output — each of these is an input that
makes `sigpow` return a number that must not be believed:**

1. **`Status != Ok`.** `NoRings` and `ZeroPower` return `0.0`, which is a
   perfectly plausible reading. **Never compare on the value without checking
   the status.**
2. **FRC at `f_sig` below ≈ 0.3.** Report it alongside `sigpow`; it costs
   nothing, since both come from the same ring. **MEASURED**: parity +0.866,
   block-4 +0.522, random +0.681, **contiguous +0.012**. A low FRC means the two
   halves are not two views of one image — a broken split, a misregistration, or
   a stack that does not actually overlap in depth. The margin between
   contiguous (0.012) and every working split (≥ 0.52) is a factor of 43, so
   this diagnostic is not delicate. It is **a diagnostic, not a hard reject**: a
   genuinely noisy few-frame stack can be legitimately low.
3. **Sub-pixel misregistration between the halves.** §4.5 measured FRC at
   `f_sig` falling +0.9477 → +0.6663 → +0.2049 over 0 → 1 → 2 px. Half-merges
   from one stack are inherently registered, so a large apparent shift means the
   pipeline reordered or resampled one half.
4. **THE CAUTIONARY CASE — fact 613. Do not reduce this ring grid to a 1/7
   crossing.** The same rings that give a live `sigpow` give a **dead**
   crossing: §7 measured 60 of 60 window × blur cells returning
   `0.4961 [CENSORED]`, which is exactly `centre[nbin−1] = 254/512`
   (A.1.7 note 4). **A statistic can be alive in one reduction of the same
   spectra and dead in another.** An implementer who reuses this ring code to
   "also report the resolution limit" will ship the dead one, and it will look
   like a number. **If a crossing is ever computed here it MUST carry a censored
   flag and the flag MUST be checked** — that is fact 475 restated.
5. **A different `f_sig`.** `0.2762` is a measured constant for this body and
   lens (A.1.9). A reading at another `f_sig` is a different measurement and is
   not comparable to anything in this document.

### A.4.4 Which shipped acceptance invariants this unblocks

Stated rather than implied, per §8. **`crates/` was read, not written.**

`crates/strehl-cli/src/merge_cmd.rs:30-34` ships two acceptance invariants. The
detail half is a detail-region gradient — `mean_grad` — measured at separation
**0.233** on real detail and **0.018** in paired form (fact 624 / P18). It
cannot distinguish blur from noise smoothing, which is the distinction the
project's thesis turns on. A working `sigpow` at separation **0.995** replaces
it directly, and with it the three `merge.rs` quality invariants that currently
assert only that the merge did *something* can be given a detail-side
counterpart. **That is the connection to shipped code: the spec exists so that
the replacement is mechanical rather than a second discovery process.**

---

## A.5 The cost, measured

Question 139 asks the owner to choose default / `--verify` / never, and says he
cannot choose on "roughly 2 ×". **"Roughly 2 ×" is wrong by two orders of
magnitude.**

**MEASURED**, `out/b7_split_cost.log` §B. Real stack, 62 frames, 512×512 ROI
(576² with pad), Python reference, wall clock, 3 repetitions for the merges and
10 for `sigpow`:

| stage | time | repeated by verification? |
|---|---|---|
| decode 62 ARW frames | **31.300 s** | **no** — the same frames, read once |
| per-frame focus fields | **0.562 s** | **no** — a property of a frame, not a stack |
| merge, full stack | 0.072 s | — |
| **merge, two halves** | **0.103 s** | the only repeated work (1.439 × one merge) |
| **`sigpow` evaluation** | **0.0318 s** | two 512² complex FFTs |
| baseline pipeline | 31.934 s | |
| with verification | 32.069 s | |
| **marginal cost** | **0.135 s = 0.4 %** | |

**MEASURED: the marginal cost of the whole verification is 0.4 % of the
pipeline.** Decode dominates at 98 % and is not repeated. The two half-merges
together cost 1.439 × one full merge — not 2 ×, because they process the same
total number of frames and share the focus fields; the 0.439 is the second
output buffer and the second gate pass.

**DERIVED extrapolation to the full green quad plane**, stated as an
extrapolation because it was not run: the plane is 3514 × 2344 / 4 = 2.059e+06
px against this ROI's 2.621e+05, so accumulation scales **7.9 ×** and the extra
merge becomes ≈ **0.8 s**. **`sigpow` does not scale with the plane** — it is
evaluated on one square ROI of fixed size, so it stays at **0.032 s**. A
full-plane run decodes proportionally more data too, so the marginal fraction
stays in the same place.

**Recommendation for question 139, ARGUED from the above: make it the default.**
At 0.4 % it does not warrant a flag, and a verification that is off by default
is the M49 failure mode (facts 569-589) arranged in advance — a measured
capability that never reaches the executable. Provide `--no-verify` for the rare
case, not `--verify` for the common one.

Caveat, stated rather than buried: these are **Python** timings. The Rust merge
will be far faster in absolute terms, which makes decode dominate **more**, not
less — the marginal fraction can only fall. The FFT is the one stage that will
not speed up proportionally, and at 0.032 s it does not need to.

---

## A.6 Implementation checklist

Mechanical, in order. Each line is checkable.

1. Validate: square, **even**, `n ≥ 32`, shapes equal, all finite. Reject, do not coerce. (A.1.2)
2. Build the **symmetric** Hann `0.5 − 0.5cos(2πk/(n−1))` and the outer product. (A.1.4)
3. Subtract the **raw** ROI mean, **then** multiply by the window. (A.1.3)
4. Forward complex 2-D FFT, **unnormalised**, **f64**, **full** — not `rfft2`. (A.1.5)
5. `fftshift` both axes; DC at `(n/2, n/2)`. (A.1.6)
6. Build rings with `rmax = floor(n/2)`, `nbin` equal-width edges, **`[lo, hi)`**. Corners fall outside and are discarded. (A.1.7)
7. In **one pass**, for each ring compute `Σ Re(A conj B)`, `Σ abs(A)²`, `Σ abs(B)²`, `count`, `centre`. **Drop `count < 8` and keep the survivors compacted together.** (A.1.8)
8. Select the surviving ring whose centre is nearest `f_sig`. No interpolation. (A.1.9)
9. Guard `ZeroPower`; return `Σ Re(A conj B) / count` with a status. (A.1.10)
10. Golden tests G1–G8 at **relative `1e-5`**, plus the ring-count assertions and the four rejection cases. (A.2)
11. Caller: split the **depth-sorted** stack by **parity**; merge each half with the shipped configuration. (A.3.2)
12. Caller: report `d = (ref − test)/abs(ref)` **and** the FRC at `f_sig` as a validity diagnostic. Never report a bare `sigpow`. (A.4.1, A.4.3)
13. **Do not** reuse the ring grid to emit a 1/7 crossing without a censored flag. (A.4.3 item 4)

---

## A.7 Reproducing Appendix A

```powershell
$env:PYTHONIOENCODING = 'utf-8'
cd C:\dev\blog\death-of-software\projects\strehl\experiments\m46-detail-metric
python -u src\b6_spec.py       > out\b6_spec.log       2>&1   #  3.5 s, no raw access
python -u src\b7_split_cost.py > out\b7_split_cost.log 2>&1   # 34.1 s, reads D:\personal\macro (READ-ONLY)
```

`b6` reads `out/b1_merges.npz`; regenerate with `b1_pair.py` if absent (§10).
`b7` decodes the real stack and is the only script here needing raw access.
Every value is deterministic: fixed seeds, ρ read from `out/b1_results.json`,
and `m41lib` / `m41lib3` imported unchanged. Both scripts are frozen under
rule 15 as of this commit.

---

## A.8 What Appendix A does not settle

- **The `n ≥ 32` floor is ARGUED, not measured.** `NoRings` was measured at
  `n = 4` and `n = 2`; between 8 and 32 the statistic returns values whose ring
  occupancy (8 modes at `n = 8`) is too thin to trust but was not characterised.
- **The odd-`n` rejection is a ruling, not a measurement of harm.** The
  reference returns numbers for `n = 15` and `n = 17`; I did not measure how
  wrong they are, only that they depend on a shift convention.
- **The full-plane cost is extrapolated**, not timed.
- **The `d` thresholds in A.4.2 are one ROI's calibration.** They are a starting
  point for a new ROI, not a constant.
- **M55 is independently attacking fact 619.** This spec describes the canonical
  form, which scores *higher* than the form M55 is testing (0.995 vs 0.937). If
  M55 refutes 619, A.0.4 is the relevant evidence and A.0.3 is the form that
  should be re-tested — but nothing here was written to pre-empt that verdict.

---

## Proposed disciplines (Appendix A)

*(unnumbered — §5 has had four numbering collisions)*

- **A statistic assembled from two helpers written at different times must be
  re-derived as one expression before it is specified.** `sigpow` was an
  interpolated correlation times a nearest-ring power taken from one of the two
  images. Writing the product on a single ring collapsed it to
  `Re⟨A·conj(B)⟩` — symmetric, exact, and stronger in every separation test. The
  defect was invisible in Python because both halves were "obviously" right on
  their own.

- **When specifying for another language, enumerate the library defaults the
  source language chose for you, and measure what each one costs.**
  `numpy.hanning` is symmetric where DSP convention is periodic; `numpy.fft` is
  unnormalised forward; `float32` is silently upcast to `complex128`. The Hann
  convention alone is worth 1.5e-3 — 146 × the test tolerance.

- **Set a test tolerance by bracketing it between a measured floor and a
  measured ceiling, and record both.** The floor is the largest difference a
  correct implementation may legitimately show (f32 pipeline: 2.2e-6); the
  ceiling is the smallest real defect (periodic Hann: 1.5e-3). A tolerance with
  no measured ceiling is not a test.

- **Golden vectors must include a case where the data structure, not the
  arithmetic, is wrong.** G7 drops 61 of 64 rings and is the only vector that
  catches an index built from the uncompacted edge list. Every comfortable
  middle case passes with that bug present.

- **Before shipping a derived quantity, measure the cost of what it actually
  repeats rather than what it appears to repeat.** Two half-merges look like
  2 × a merge; measured, they are 1.439 ×, and against a pipeline that is 98 %
  decode the whole verification is 0.4 %.

## Proposed owner questions (Appendix A)

*(unnumbered)*

- The split contract requires parity **on the depth-sorted index**. Does the
  shipped pipeline guarantee a stable depth ordering at the point where a split
  would be taken, including after speckle and bracket-boundary rejection?

- `sigpow` is defined on one square ROI. Should that be the same ROI the
  existing flat/detail acceptance invariants use, a new one, or should the CLI
  read several and report the worst?

- At 0.4 % marginal cost, should verification be the default with `--no-verify`
  as the escape, rather than an opt-in `--verify`?

## Proposed SYNTHESIS entries (Appendix A)

| # | Fact | Consequence | Source |
|---|---|---|---|
| Q1 | `sigpow` as measured in M46 evaluated its two factors at DIFFERENT frequencies — the correlation by linear interpolation between ring centres, the power by nearest ring — and at `f_sig = 0.2762`, `n = 512`, `nbin = 64` the straddling centres are 0.269531 and 0.277344, so the correlation was an 85.4 % blend of two rings while the power was one ring outright. | | MEASURED, `experiments/m46-detail-metric/out/b6_spec.log` §1 |
| Q2 | The same statistic took its power reference, `abs(A)^2`, from the FIRST image only, making it asymmetric under swapping the two half-merges by **1.96e-02** on real data. A statistic whose value depends on argument order is not a statistic. | | MEASURED, `out/b6_spec.log` §1 |
| Q3 | Both defects vanish in one re-derivation: on a single ring with a symmetric power reference, `FRC_i * P_i = Re(sum A conj(B)) / count_i`. **`sigpow` is the mean per-mode real cross-power of one ring** — no ratio, no interpolation, no asymmetry, nothing to divide by zero. The identity holds to a relative **1.4e-16**. | | DERIVED; MEASURED, `out/b6_spec.log` §2 |
| Q4 | Fact 619 survives the rule-24 re-choice and improves. Canonical separation: **0.995** on real detail (was 0.937), **0.994** against a matched post-filter (was 0.931), **0.936** on the flat ROI (was 0.917). The inconsistent frequency selection was not load-bearing; it was costing power. | | MEASURED, `out/b6_spec.log` §3 |
| Q5 | **A contiguous half-stack split destroys the statistic: 0.47 % of the parity value, with FRC at `f_sig` collapsing from +0.866129 to +0.012041.** A focus stack sweeps depth monotonically, so a contiguous half holds half the sweep and the two half-merges are focused on different parts of the subject. | | MEASURED, `out/b7_split_cost.log` §A |
| Q6 | The degradation is monotonic in run length, so "any interleave" is insufficient and a random split is actively wrong: parity 1.0000, block-of-2 1.0151, block-of-4 **0.6413**, random permutation **0.8648**. Random loses because a random half contains runs of three or four consecutive frames. **The contract is parity on the depth-sorted index.** | | MEASURED, `out/b7_split_cost.log` §A |
| Q7 | Neither an odd frame count nor an unequal split harms the reading: `nf = 61` parity (31/30) reads 1.0002x the even value, and a deliberate 3:1 split (46/16) reads 1.0585x. The statistic is insensitive to `n_eff` imbalance and sensitive only to interleaving. | | MEASURED, `out/b7_split_cost.log` §A |
| Q8 | **The marginal cost of half-stack verification is 0.4 % of the pipeline, not the assumed 2x.** Decode is 31.300 s of a 31.934 s baseline and is not repeated; per-frame focus fields (0.562 s) are a property of a frame and are shared by both halves; two half-merges cost 0.103 s against one full merge's 0.072 s (1.439x); `sigpow` itself costs 0.0318 s for two 512^2 FFTs. | | MEASURED, `out/b7_split_cost.log` §B |
| Q9 | Substituting the PERIODIC Hann window for NumPy's SYMMETRIC `0.5 - 0.5cos(2*pi*k/(n-1))` changes `sigpow` by a relative **1.4607e-03** on real data — 146x the golden-vector tolerance. `w_sym[n-1] = 0` exactly; `w_per[n-1]` is 3.8e-05 at n = 512 and 0.038060 at n = 16. | | MEASURED, `out/b6_spec.log` §4 |
| Q10 | A golden-vector tolerance of **relative 1e-5** is bracketed by measurement rather than guessed: the largest legitimate difference is a full f32 pipeline at **2.187e-06** (n = 64), and the smallest real defect is the periodic-Hann substitution at **1.4607e-03**. Summation order contributes 1.455e-16 and pairwise-vs-naive accumulation 0.0. | | MEASURED, `out/b6_spec.log` §5; `out/b7_split_cost.log` §C |
| Q11 | The ring grid discards the FFT square's corners: with `rmax = floor(n/2)` and half-open rings, **205 857 of 262 144 modes (78.5 %)** are binned at n = 512. DC falls inside ring 0 and is controlled by mean removal; Nyquist at `rr = n/2` is excluded by the upper bound. | | MEASURED |
| Q12 | Rings with fewer than 8 modes are DROPPED and the survivors compacted, so a ring's position is not its index. At n = 8, nbin = 64 only **3 of 64** rings survive and the selected ring's position is 2 while its index is 35. Any implementation indexing a parallel array built from the full edge list selects the wrong ring or panics. | | MEASURED, `out/b7_split_cost.log` §D; `out/b6_golden.json` |
| Q13 | `sigpow` is **signed** — anti-correlated inputs give a negative reading of equal magnitude, `+3.7865519412e+01` against `-3.7865519412e+01` — scales as **lambda^2** under `a -> lambda a` (a x3 scaling gives x8.999999999999991), and is invariant to a constant offset. It is a contrast statistic with no meaningful absolute value and is not comparable across different `n` or `nbin`. | | MEASURED, `out/b6_golden.json`; `out/b6_spec.log` |
| Q14 | On the real detail ROI a `sb = 0.05 px` blur moves `sigpow` by `d = +0.00727` and a matched-cost post-filter by `+0.00662`, while halving the noise variance moves it by `+0.00004` — **a signal-to-nuisance ratio of about 180:1**. | | MEASURED, `out/b6_spec.log` §3 |
| Q15 | The Python reference **accepts** odd-sized ROIs and returns a number (n = 15 -> `+9.45820296e+00`, n = 17 -> `+9.82483260e+00`), but for odd n the shifted grid is asymmetric by one sample and the value depends on the FFT library's shift convention rather than on the image. The specification overrides the reference and rejects odd n. | | MEASURED, `out/b7_split_cost.log` §D; ARGUED |
| Q16 | The same ring grid that yields a live `sigpow` yields a DEAD 1/7 crossing: fact 613's 60-of-60 `0.4961 [CENSORED]` is exactly `centre[nbin-1] = 254/512`. **A statistic can be alive in one reduction of a set of spectra and dead in another**, so any crossing computed from this grid must carry a censored flag and the flag must be checked. | | DERIVED from fact 613 and A.1.7; MEASURED |
