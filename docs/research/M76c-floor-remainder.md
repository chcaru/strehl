# M76c — deciding M70's flat-floor remainder

## Headline

**STATUS: COMPLETE — THE PRE-REGISTERED VERDICT IS INCONCLUSIVE.**

**MEASURED.** The strongest working arm says what the remainder is *not*:
additional repeating multiplicative green structure accounts for **0.785%**
of M76b's remainder, with a registered 95% interval of **0–3.739%**. The
true-flat instrument recovered a remainder-sized fixed-pattern plant at
0.9877×, returned its independent null at 0.579 standard errors, and separated
the unshifted plant from its shift null by 109.9 standard deviations.

**MEASURED — result against the desired decision.** The mandatory dark control
failed and the scene-correlation control was insensitive. The registered rules
therefore forbid using either arm to name the remaining power. I report
**INCONCLUSIVE**, not “scene dominated”, even though the valid multiplicative
bound and the exploratory dark point both lean strongly that way.

**DERIVED — a defect in my own registration.** I registered M4's total spatial
variance as an upper bound on M70's *band-mean spectral density*. It is not one.
A post-result unit-variance sinusoid passed through the exact estimator returns
4.2667 DN² as the equal-three-band mean. The dark control failed because its
comparison was dimensionally invalid, not because its measured 0.103–0.170
DN² values were negative or unstable. Changing that rule after seeing it fail
would erase the pre-registration.

**DERIVED.** The admissible upper sensor-noise perturbation at `S = 8000` is
1.414%, below the registered 2% threshold for alerting M77. SYNTHESIS fact
1064 therefore does not change: its established −12.75% shipped-model error
stands. At the new upper sensitivity it would become −13.97%, so any eventual
correction makes the over-confidence worse, not better.

---

## 1. Sources read before registration

**MEASURED.** I read M70's `s04_through_focus.py`,
`s05_analyse.py`, `s06_pedestal.py`, `s25_floor_uniformity.py`, and M70's own
§13.3 and §20.3; M71's §§5.1–5.3 and its `05-kappa.py` and
`07-structure.py`; M4's §§1, 5, and 7; and M75's §§5 and 7. Numbers attributed
below come from those reports and drivers rather than from `SYNTHESIS.md`.

**MEASURED — M70's own §13.3:**

> **MEASURED** (`out/s06_pedestal.log`, 6 stacks, R² 0.97). The residual band power
> on flat patches after model subtraction scales as `level^1.83`. A slope near 2 is
> what PRNU produces (a fixed multiplicative pattern gives `(contrast × level)²`) —
> **but it is also what residual low-contrast scene texture produces**, for exactly
> the same reason.

**MEASURED — M71's own §5.2:**

> The **cross**-spectrum between the two independent 20-frame halves kills the temporal
> noise by independence, so no floor is subtracted anywhere. Hann-windowed Welch
> periodograms on 256×256 tiles, 60 tiles per map, radially averaged

and:

> | PRNU cross-spectrum, flats A × B | **0.9028** | white |
> | in-focus sweep frame, auto-spectrum | **0.0167** | steeply red — resolved texture |

**MEASURED — M71's own §5.3:**

> **The paper contributes 0.09–0.14% of the PRNU variance in the flats, i.e. 0.05–0.07%
> of κ.**

**MEASURED — M4's own headline:**

> the departure is measurable at **N = 2**. The curve
> asymptotes at a fixed-pattern floor of **0.377 DN** (ISO 100), reached at
> **N ≈ 7**

and M4's scope warning:

> These are dark frames, so they measure *offset* fixed-pattern noise (DSNU) and
> nothing else. **PRNU — the multiplicative, signal-proportional fixed pattern —
> is invisible here**

**MEASURED — M75's own headline:**

> **The green gradient is multiplicative, not additive**

and:

> a row-dependent per-plane analog scale and the first direct
> evidence that such scales are **not constant across the array**

M75 also states the operational amplitude as ±1.7% in σ and scopes its
measurement to dark-frame temporal variance. Whether that slowly varying
scale contributes power inside M70's 0.100–0.2762 sensor-cyc/px bands is not
assumed.

---

## 2. Pre-registration

Registration commit:
**`15ed5cb5f862543166092d0edc76306e790eae1f`**. This SHA predates every
measurement reported below. Replacing the pending-SHA marker and adding results
did not change any registered estimator, threshold, or branch.

No direction is predicted. The mechanisms, observables, controls, uncertainty,
and decision branches are fixed here before any new cross-spectrum is
computed.

### 2.1 The object being allocated

**MEASURED input from M76b.** The six registered rows are `109MSDCF`,
`112MSDCF`, `coffee-bean`, `bee-1`, `bee-2`, and `bee-3`. For row `i`, define

`R_i = e_flat_i − (0.003096 × S_i)²`.

The registered aggregate remainder is `ΣR_i = 1197.50 DN²`. No row will be
removed.

**ARGUED mechanisms.** An additional multiplicative sensor pattern repeats in
sensor coordinates and contributes relative cross-power independent of
subject. Offset FPN also repeats in sensor coordinates but contributes
absolute DN² rather than `S²`. Scene texture repeats between captures of the
same subject but not between unrelated subjects, and it is absent from a true
flat-field cross-spectrum except for M71's already bounded paper term.

### 2.2 Arm A — all fixed multiplicative green power on true flats

**Registered data.** Use M71's five clean matched 20-frame half-pairs:
`e0.004`, `e0.008`, `e0.016666...`, `e0.033333...`, and `e0.05`, from the
committed cached G1/G2 mean maps. The cache was generated by M71's committed
decoder; raw pixels will not be decoded a second way.

**Registered geometry.** Reconstruct each green quincunx patch directly from
the two plane means at M70's 24 fixed sensor centres. Use M70's exact
`PATCH=256`, `TILE=128`, periodic Hann window, 50%-overlapped 3×3 Welch tiles,
GQ-to-sensor frequency conversion, and its three mid bands:
0.100–0.150, 0.150–0.200, and 0.200–0.2762 cyc/px.

**Registered preprocessing.** For each half and patch, divide the patch by
M71's committed 61-pixel, three-pass smooth surface and subtract one. This
puts unequal A/B illumination in relative units and preserves pattern above
the smooth cutoff. Compute the real cross-periodogram between corresponding
A/B Welch tiles. Independent temporal noise cancels in expectation; common
fixed sensor structure remains. Average with M70's FFT-bin weighting.

**Registered primary statistic.** `V_flat` is the arithmetic mean relative
cross-power over all five half-pairs, 24 patches, nine Welch tiles, and the
three M70 bands. It measures total repeating green fixed power, including
M71's κ and any common-mode term that M71's G1−G2 headline estimator would
cancel. Define

`V_extra = max(V_flat − 0.003096², 0)`.

Its contribution to M76b's remainder is

`F_mult = V_extra × ΣS_i² / ΣR_i`.

Negative cross-power is retained until the final physical truncation; no cell
or Fourier bin is half-wave rectified.

**Registered uncertainty.** Use a two-level block bootstrap: resample the five
exposure pairs, then the 24 sensor patches within each selected pair, 10,000
draws with seed 76003. Report the percentile 95% interval for `V_flat` and
`F_mult`, the five pair estimates, and all 24 patch estimates. This interval
quantifies re-draw variation over level and position, not camera-to-camera
variation.

### 2.3 Arm B — additive fixed power from darks

**Registered data and estimator.** Read, never modify, M4's 20 post-stabilisation
frames at ISO 50 (`122MSDCF`), 100 (`118MSDCF`), 200 (`123MSDCF`), 400
(`119MSDCF`), and 500 (`125MSDCF`). Split each folder 10/10, average each
half, and run the same absolute-DN GQ cross-spectrum, geometry, and bands as
Arm A. The cross-spectrum cancels temporal noise and returns mid-band DSNU
power without subtracting an estimated floor.

**Registered mapping.** Use the exact ISO row for the five rows that have one.
For `109MSDCF` at ISO 160, use the larger of the ISO-100 and ISO-200 estimates;
this is conservative for a sensor explanation. Define

`F_add = ΣV_dark,ISO(i) / ΣR_i`.

Use the larger of the point estimate and zero per ISO. A second bound uses
M4's total spatial `sigma_FPN²` at that ISO; because mid-band power cannot
exceed total variance, this is a deliberately conservative cross-check.

### 2.4 Arm C — the sensor-coordinate repetition signature in M70

**Registered data and statistic.** Use M70's committed `tfs-*.npz` files; no
new subject raw decode. For every stack and each of its 24 fixed patches,
compute

`q = mean_frames,bands[(power − modelled sigma²) / level²]`

over the same three mid bands. Pearson-correlate the 24-element `q` vectors
between stacks.

**Registered pair classes.** Same-subject controls are `(112,113)`,
`(wrapped-text-1,wrapped-text-2)`, and the three pairings among
`bee-1,bee-2,bee-3`. Every other stack pair is “unrelated”; duplicates within
the same named subject class are never counted as unrelated.

**Registered interpretation.** A positive same-subject median with an
unrelated median inside its coordinate-permutation null demonstrates
scene-sensitive but not sensor-repeating structure. A positive unrelated
median outside a 10,000-draw coordinate-permutation null supports a repeating
sensor component. Arm C cannot set the magnitude by itself; it can corroborate
or attack Arms A/B.

### 2.5 Controls that can express the failure

**Registered positive fixed-pattern plant.** Add one common, seeded white
pattern to both members of otherwise independent synthetic maps at fractional
variance

`V_plant = ΣR_i / ΣS_i²`,

the amplitude required for a single multiplicative term to explain all of
M76b's remainder. The exact Arm-A path must recover 90–110% of planted
variance. An independent-pattern null must land within three null standard
deviations of zero.

**Registered shift control.** Circularly shift one member of each flat pair by
large nonzero offsets before cross-power. Use 1,000 seeded shifts with both
axes in `[32,224]`. The unshifted planted pattern must exceed the shift-null
mean by at least 10 null standard deviations. This control is sensitive to
the sensor-coordinate correspondence the primary claim requires.

**Registered scene control.** Arm C's five same-subject pairs must have a
median correlation above the 95th percentile of their own coordinate-
permutation null. If it does not, Arm C is declared insensitive and contributes
nothing to the verdict; Arms A/B remain independently admissible.

**Registered dark control.** Arm B's total mid-band cross-power must be
non-negative on at least four of five ISOs, and no estimate may exceed M4's
total `sigma_FPN²` by more than its bootstrap 95% upper bar. Otherwise Arm B is
void and only M4's conservative total-variance bound is used.

### 2.6 Decision rule

Define the extra fixed-sensor share of M76b's remainder:

`F_sensor = F_mult + F_add`.

Use the upper/lower bounds formed from Arm A's bootstrap interval and the
larger of Arm B's measured or M4-total bound.

- If the 95% upper bound on `F_sensor` is below 0.50, report
  **SCENE-DOMINATED REMAINDER**: more than half cannot be either
  multiplicative or additive fixed sensor power.
- If the 95% lower bound is above 0.50, report
  **SENSOR-DOMINATED REMAINDER**.
- Otherwise report **SPLIT OR UNDECIDABLE**, state the bounded shares, and name
  the capture or statistic needed to separate them.
- Any failed mandatory control makes the corresponding arm
  **INCONCLUSIVE**, never evidence for the other hypothesis.

The exponent is a consistency check, not a selector. After subtracting the
measured fixed terms, fit M70's exact log-log regression to positive row
remainders. Report its exponent and R², but do not use “near 2” to rename
scene contrast as sensor PRNU: both square with level.

### 2.7 Consequences fixed before the answer

**Registered consequence for SYNTHESIS fact 1064.** Only the Arm-A/B fixed
sensor contribution can enter sensor-noise arithmetic. If `F_sensor` has a
nonzero lower bound, recompute M71's shipped-versus-truth σ error across
S=0–15360 with that term and report the changed crossover and S=8000 error.
If it is bounded small or null, SYNTHESIS fact 1064 remains as written.

**Registered consequence for M77.** If the inferred sensor σ at working levels
moves by at least 2% relative to M71's existing truth model, flag that M77's
σ-denominated gate constant requires re-denomination. Below 2%, report the
bound and do not route a gate change. M77's files will not be read or touched.

---

## 3. Execution and controls

### 3.1 Exact input correction before the successful run

**MEASURED.** The first attempted run used rounded copies of M76b's six
remainders and stopped before writing a result because the row tuple had the
wrong arity after correction. I changed the driver to load M76b's committed
`item1.json` directly. The successful run used the exact aggregate
**1197.5035281728155 DN²**, not the report-rounded 1197.50 DN². This was
required by §2.1 and was not an estimator change.

**MEASURED.** The successful command was:

```text
$env:PYTHONIOENCODING='utf-8'
python experiments\M76c-floor-remainder\analyse.py
```

Its actual summary output was:

```text
ARM A — total repeating multiplicative green power on M71 true flats
e0.004                     V_flat=1.12519462e-05 k=0.3354%
e0.008                     V_flat=1.04723234e-05 k=0.3236%
e0.016666666666666666      V_flat=9.70469971e-06 k=0.3115%
e0.03333333333333333       V_flat=9.00790715e-06 k=0.3001%
e0.05                      V_flat=8.61154427e-06 k=0.2935%

pooled V_flat=9.80968414e-06
95% [9.00055141e-06, 1.06539068e-05]
k_total=0.3132%  M71 kappa=0.3096%
V_extra=max(V_flat-kappa^2,0)=2.24468145e-07
F_mult=0.00785 95% [0.00000, 0.03739] of remainder

V_plant=2.85789035e-05; recovered=2.82269370e-05 (0.9877x)
independent null=+2.65798296e-08, SE=4.592e-08, z=+0.579
shift null mean=-7.57930339e-09, sd=2.645e-07, unshifted z=109.9

ISO  50: V_dark=+0.1544471 DN^2 95% [+0.1530740,+0.1557692]
ISO 100: V_dark=+0.1536629 DN^2 95% [+0.1522865,+0.1550233]
ISO 200: V_dark=+0.1026690 DN^2 95% [+0.0957392,+0.1095349]
ISO 400: V_dark=+0.1530071 DN^2 95% [+0.1515780,+0.1545160]
ISO 500: V_dark=+0.1695351 DN^2 95% [+0.1674961,+0.1717060]
F_add measured=0.0007833; M4-total conservative upper=0.0007210
dark control: nonnegative 5/5, upper CI <= total FAIL -> FAIL

same-subject median r=+0.1525; null p95=+0.1790 -> INSENSITIVE
unrelated median r=+0.0391; null p95=+0.0333 -> REPEATS

F_sensor point=0.00864; decision interval [0,0.03812]
VERDICT: INCONCLUSIVE
post-fixed-term remainder exponent=1.8346, R^2=0.9351
upper-bound sigma movement at S=8000: 1.414% -> M77 NO FLAG
```

### 3.2 A control that killed my dark rule

**DERIVED, POST-HOC.** M70's `band_average` is a mean spectral density over
FFT bins, not integrated variance. Total spatial variance constrains the sum
of spectral power; it does not bound the density in every subset of bins.
Therefore §2.3's sentence “mid-band power cannot exceed total variance” is
false.

**MEASURED, POST-HOC CONTROL.** I put a unit-variance sinusoid wholly in M70's
`b3_mid` band and passed it through the exact Arm-B estimator. This control was
chosen after the real dark comparison failed, so it diagnoses the failure but
cannot repair the registered verdict:

```text
spatial variance: 1.0000000
b3_mid: 12.8000000
b4_mid: 0.0000000
b5_mid: 0.0000000
equal-three-band mean: 4.2666667
PASS: a unit-variance pattern produces band-density power above 1
```

**ARGUED.** A replacement bound would need the spectral-bin population, window
weighting, sampled sensor area, and uncertainty of M4's whole-array variance.
Inventing that bound now, after seeing the failed comparison, would be a new
analysis. The clean remedy is a separately registered rerun with an
integrated-band statistic or a Parseval-consistent density bound.

### 3.3 Independent arithmetic verification

**MEASURED.** `verify.py` recomputed the primary mean, the exact two-level
bootstrap, the M76b allocation, all control branches, the post-fixed-term
regression, and the consequence threshold from `result.json`. Actual output:

```text
PASS 01: all five flat pairs and 24 patches are present
PASS 02: V_flat is the unrectified 5 x 24 arithmetic mean
PASS 03: reported exposure-pair values reproduce from the patch matrix
PASS 04: registered two-level flat bootstrap reproduces exactly
PASS 05: multiplicative remainder share reproduces from exact M76b rows
PASS 06: all three mandatory Arm-A controls pass
PASS 07–11: all five dark points reproduce as their 24-patch means
PASS 12: registered dark control fails rather than being silently relaxed
PASS 13: same-subject median reproduces
PASS 14: registered scene-sensitivity control fails
PASS 15: post-fixed-term exponent and R-squared reproduce
PASS 16: failed mandatory Arm-B control forces the registered verdict
PASS 17: registered M77 re-denomination threshold does not bind

17/17 checks passed
```

---

## 4. Arm A — repeating multiplicative sensor power

**MEASURED.** Across the five independent flat A/B pairs, total repeating
green power fell from `1.12519e-5` to `8.61154e-6` in relative-variance units.
The pooled value is `9.809684e-6`, equivalent to κ = **0.31320%**, with a
two-level 95% interval `9.000551e-6–1.065391e-5`.

**DERIVED.** M71's κ = 0.3096% contributes `9.585216e-6`, leaving an extra
point contribution `2.244681e-7`. Allocated over M76b's exact six rows, that is
**0.7854%** of the unexplained remainder, 95% interval **0–3.7394%**. Thus this
arm excludes an additional repeating multiplicative green term as the
*majority* explanation by a factor much larger than the 50% decision margin.

**MEASURED.** All mandatory Arm-A controls passed. The instrument recovered
98.77% of a fixed pattern sized to explain the entire remainder; the
independent-pattern null was 0.579 standard errors from zero; and breaking
sensor-coordinate correspondence displaced the plant by 109.9 shift-null
standard deviations.

**ARGUED.** This arm measures all green-common repeating multiplicative power
that survives M71's 61-pixel smooth removal, including a term that G1−G2 would
cancel. It does not measure structure below that high-pass cutoff. M75's
slow row-dependent scale can therefore exist while contributing essentially
none of M70's registered mid bands.

---

## 5. Arm B — additive fixed sensor power

**MEASURED.** All five dark cross-powers were positive and tightly resolved:
0.15445, 0.15366, 0.10267, 0.15301, and 0.16954 DN² at ISO 50, 100, 200, 400,
and 500. Directly allocating those point estimates over the six M70 rows gives
**0.07833%** of M76b's remainder.

**MEASURED — disqualifying result.** Four of five bootstrap upper bars exceeded
the corresponding M4 total-variance number, so the mandatory dark control
failed. Under §2.5, Arm B is **INCONCLUSIVE** and its attractive 0.07833% point
must not support classification.

**DERIVED.** The control failure exposed the false density-versus-integral
comparison in §3.2. It is not evidence that the cross-spectrum is noisy:
all five point estimates are positive and their intervals are narrow. Nor is
it permission to waive the rule; the rule was registered precisely to prevent
that move.

---

## 6. Arm C — coordinate repetition in M70

**MEASURED.** Same-subject correlations were 0.9905 for `112/113`, 0.0180 for
the two `wrapped-text` stacks, and 0.0632, 0.1525, and 0.9651 for the three bee
pairs. Their median, 0.1525, did not clear its own permutation-null 95th
percentile of 0.1790. The registered scene-sensitivity control therefore
failed.

**MEASURED — result not promoted.** The unrelated-pair median was 0.0391,
slightly above its null 95th percentile of 0.0333. Because the same instrument
failed its mandatory same-subject control, this apparent sensor repetition is
not admissible evidence. Arm C contributes nothing to the verdict.

**ARGUED.** The pairwise spread explains why a median-only 24-cell test was
weak: two controls were nearly perfectly correlated while three were not.
A decisive coordinate experiment should move or rotate one subject relative
to the sensor while keeping capture settings fixed, rather than infer
coordinate identity from unrelated historical stacks.

---

## 7. The exponent and the two clues in M76b

**MEASURED.** M76b's PRNU-only remainder exponent was 1.7546 with R² 0.9295.
After subtracting Arm A's pooled total fixed multiplicative point and Arm B's
exploratory dark points, all six residuals remained positive and the exponent
was **1.8346**, R² **0.9351**.

**ARGUED.** The exponent is consistent with level-proportional contrast power,
but cannot say whether that contrast is scene-fixed or sensor-fixed; §2.6
pre-registered it as a consistency check only. It does rule against *only*
level-independent DSNU as an adequate explanation of the aggregate.

**MEASURED.** The endpoints behind M76b's 16.78–55.82% PRNU-share range were
`112MSDCF` at 122.7 DN and `bee-3` at 2574.1 DN. After subtracting the newly
measured fixed points, they retain 0.5428 and 48.6175 DN² respectively.

**ARGUED.** The range is not a clean sensor signature: it spans both level and
subject, and the ISO-500 low-level row has the *smallest* PRNU share despite
the largest measured dark point among its mapped ISOs. Existing rows do not
orthogonalise subject, level, and ISO.

---

## 8. Verdict and consequences

**ARGUED, BINDING PRE-REGISTERED VERDICT: INCONCLUSIVE.** Arm A validly bounds
additional repeating multiplicative power below 3.7394% of the remainder.
Arm B's mandatory control failed because I registered an invalid upper bound,
and Arm C's sensitivity control failed. The decision rule says any failed
mandatory control makes that arm inconclusive. The available experiment
therefore does not decide scene texture versus all fixed sensor power.

**ARGUED.** The capture that decides it is one scene at fixed exposure and
focus captured in two sensor registrations, plus a matched uniform diffuser
and lens-capped sequence at the same ISO and level. Scene power follows the
registered scene; sensor power remains at array coordinates. This removes the
historical-stack confounding that defeated Arm C and supplies the
Parseval-matched dark comparison that Arm B lacked.

**DERIVED — SYNTHESIS fact 1064.** The valid additional multiplicative lower
bound is zero, so the registered condition for changing the shipped noise
model does not fire. SYNTHESIS fact 1064's crossover near 504 DN and −12.75%
error at 8000 DN remain the established values. At Arm A's upper bound, plus
M4's ISO-100 total offset variance for the per-pixel noise consequence, true σ
at 8000 DN rises by 1.414%; the shipped error would deepen to **−13.97%**.
Nothing measured here can make the model less over-confident.

**DERIVED — M77.** The 1.414% upper movement is below the registered 2%
re-denomination threshold. **Do not route a gate-constant change to M77 from
this milestone.** This statement concerns the valid noise-model sensitivity,
not the disqualified classification share.

---

## 9. Candidate facts

Numbered `P1…` locally. These are proposals for the corpus, not global
`SYNTHESIS.md` numbers.

**`P1` (MEASURED).** On five matched M71 true-flat half-pairs, the exact M70
mid-band cross-spectrum measures total repeating green power
`V_flat = 9.809684e-6`, κ = 0.31320%, with two-level bootstrap 95% interval
`9.000551e-6–1.065391e-5`. *Provenance: M76c §4;
`experiments/M76c-floor-remainder/out/result.json`.*

**`P2` (DERIVED).** Above M71's κ = 0.3096%, additional repeating
multiplicative green power explains 0.7854% of M76b's exact 1197.5035 DN²
remainder, 95% interval 0–3.7394%. A majority multiplicative-sensor
explanation is excluded within this instrument's spatial band and smoothing
scope. *Provenance: M76c §4.*

**`P3` (MEASURED).** M76c's fixed-pattern controls were sensitive: a
remainder-sized common plant was recovered at 0.9877×, the independent null
was 0.579 standard errors from zero, and the unshifted plant was 109.9 shift-
null standard deviations from broken coordinate correspondence.
*Provenance: M76c §3.1, §4.*

**`P4` (MEASURED — DISQUALIFYING).** M76c's dark arm measured positive,
tightly resolved mid-band cross-power at all five tested ISOs, but its
mandatory comparison against M4's total spatial variance failed in four of
five upper intervals. Under the registered rule, the arm is inconclusive and
its 0.07833% point share cannot classify the remainder. *Provenance: M76c §5.*

**`P5` (DERIVED — REGISTRATION DEFECT).** A total spatial variance is not an
upper bound on a band-mean spectral density. The exact M70/M76c estimator
returns an equal-three-band mean of 4.2667 for a unit-variance sinusoid
concentrated in `b3_mid`. This false premise caused M76c's dark control to
fail. *Provenance: M76c §3.2;
`experiments/M76c-floor-remainder/out/band-density-control.log`.*

**`P6` (MEASURED — DISQUALIFYING).** M76c's scene-coordinate arm was
insensitive: the same-subject median correlation 0.1525 did not exceed its
permutation-null 95th percentile 0.1790. Its unrelated median of 0.0391 above
0.0333 is consequently not admissible sensor-repetition evidence.
*Provenance: M76c §6.*

**`P7` (MEASURED).** After subtracting the measured fixed multiplicative and
exploratory dark points, all six M70 residuals remain positive and scale as
`level^1.8346`, R² 0.9351. This is consistent with level-proportional contrast
but does not distinguish sensor PRNU from scene texture. *Provenance: M76c
§7.*

**`P8` (ARGUED).** M76c's binding pre-registered verdict is
**INCONCLUSIVE**, not scene-dominated: Arm A excludes an additional
multiplicative majority, but Arm B and Arm C each failed a mandatory control.
A same-scene sensor-registration shift with matched true-flat and dark
captures is required to decide the remainder. *Provenance: M76c §8.*

**`P9` (DERIVED).** M76c does not change SYNTHESIS fact 1064 and does not
trigger M77 re-denomination. The valid upper noise perturbation is 1.414% at
8000 DN, below the registered 2% M77 threshold; at that upper sensitivity the
shipped-model error would deepen from −12.75% to −13.97%.
*Provenance: M76c §8.*

---

## 10. What I did not measure

- **NOT MEASURED.** No new capture was made. Subject, level, ISO, and sensor
  registration therefore remain confounded in M70's historical stacks.
- **NOT MEASURED.** Arm A does not constrain multiplicative structure removed
  by M71's 61-pixel smooth surface, power outside M70's three mid bands, or
  camera-to-camera variation.
- **NOT MEASURED.** M4 has no ISO-160 folder. The registered mapping used the
  larger ISO-100/200 point, and no interpolation law was inferred.
- **NOT MEASURED.** I did not construct a post-hoc Parseval-consistent
  uncertainty bound for Arm B. Doing so after its control failed would be a
  new analysis and cannot rescue this pre-registration.
- **NOT MEASURED.** The source of the five-flat exposure trend in `V_flat`
  (0.3354% to 0.2935% equivalent κ) was not separated into sensor response,
  illumination, and smooth-removal effects.
- **NOT MEASURED.** Temperature and session stability of M4's offset pattern
  relative to the later M70 and M71 captures were not available.
- **NOT MEASURED.** The report makes no change to `PlaneNoise::variance`, the
  M77 gate constant, `SYNTHESIS.md`, or any live milestone directory.
