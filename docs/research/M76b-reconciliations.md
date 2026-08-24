# M76b — two numeric reconciliations

## Headline

**MEASURED/DERIVED — both discrepancies reconcile.** M70's `e_flat` is a
**variance in DN²**, so its exponent 1.83 compares directly with PRNU's exponent
2. M71's measured κ accounts for **25.12%** of the six residuals in aggregate
(cell range 16.78–55.82%); it is part of the floor, not all of it. The remaining
74.88% is still unruled between low-contrast scene texture and another
level-dependent fixed term. This does **not** alter SYNTHESIS fact 1064:
M71's arithmetic already contains this κ, while the remainder has not been
shown to be sensor noise.

**MEASURED — SYNTHESIS fact 27's `0.2762 cyc/px` is reproducible and remains
the configured result.** M5's own §12 command says `--tile 128`; it reproduces
the entire published fingerprint: `f_sig=0.2762`, `dyn=1297.2`, `κ_floor=0.056`,
floor sd 11.91 DN, floor/model 0.950, `nfrm=4`, and placebo `0.2154`. M70 ran
the same driver at its **256 default**, which reproduces M70's entire other
fingerprint: `0.2375`, `322.6`, `1.214`, 11.72 DN, 0.935, `nfrm=1`, with the
same scalar placebo. This is an invocation/configuration mismatch, not a bad
number. SYNTHESIS fact 27 should retain `0.2762` and add `tile=128` to the
configuration. Its `B=5`, `B=1`, and conditional `p≈1.0–1.4` conclusions
survive unchanged.

**MEASURED — clarification to M76.** The suite behind M76's headline
“new tests 7/7 and 6/6” is
`experiments/M55-acceptance-spec/src/e19_m76_pooled_enumeration.py`. It is not
under an `experiments/M76*` directory. The 6/6 count was not a typo; the report
should have named the file.

---

## 1. Sources read before registration

**MEASURED.** I read M70's own §13.2–§13.3 and its drivers
`s02_reproduce_m5.py`, `s02c_m5_kappa.py`, and `s06_pedestal.py`; M71's own
κ derivation in §5, its §8.3, and drivers `05-kappa.py` and
`11-regime-and-m61.py`; M5's own §§1, 3.3, 4.1, 4.5, 7, 9, 10–12 and its
committed `m5_measure.py` and `m5_lib.py`. Numbers attributed to those
milestones below come from those sources, not from `SYNTHESIS.md`.

**MEASURED — M70's own §13.3:**

> **MEASURED** (`out/s06_pedestal.log`, 6 stacks, R² 0.97). The residual band power
> on flat patches after model subtraction scales as `level^1.83`. A slope near 2 is
> what PRNU produces (a fixed multiplicative pattern gives `(contrast × level)²`) —
> **but it is also what residual low-contrast scene texture produces**, for exactly
> the same reason. **These are not distinguishable without a dark frame or a flat
> field**, neither of which I may read from `D:\macro-dark-frames` for this purpose
> and neither of which I collected. **M71 is live on flat fields** and is the right
> owner. Recorded so it is not lost.

**MEASURED — M71's own headline:**

> **κ = 0.3096% per green photosite (MEASURED)**, and it clears the pre-registered
> materiality threshold by 1.81×. The paper-texture confound is not argued away — it
> is *measured* and bounded at **0.09–0.14% of the PRNU variance**, i.e. it moves κ by
> less than 0.07%.

**MEASURED — M70's own §13.2:**

> Running M5's committed driver unmodified on 109MSDCF
> returns `f_sig = 0.2375` and `B_max ≤ 3.563`, where `M5` publishes 0.2762 and
> `B_max` 3.064. In the same published table the *placebo* value 0.2154 reproduces
> exactly, and the floor sd reproduces to 1.6% — so this is not a broken checkout.

**MEASURED — M5's own §12 command:**

> `python m5_measure.py measure C:\dev\macro\test\109MSDCF    --n 11.0 --tile 128 --dark D:\macro-dark-frames\123MSDCF`

---

## 2. Pre-registration

Registration commit:
`26fe4613572792e1523d9828c9833663ca1058b5`. `git show --name-only` lists only
this report. The results below were run after that commit without changing any
criterion.

No direction is predicted. Mechanisms and observables are registered; expected
answers are deliberately omitted.

### 2.1 Item 1 — flat residual versus measured PRNU

**ARGUED mechanism.** A fixed multiplicative photosite response with fractional
standard deviation κ contributes spectral power, hence variance, proportional
to `(κS)²`. A standard-deviation observable would instead scale as `κS`.
Therefore the units of M70's `e_flat` decide whether its exponent 1.83 is
compared with 2 or with 1.

**Registered observable and units decision.** I will trace `e_flat` from M70's
driver expression to its input quantity and unit. “Variance” requires that it
is a power or variance residual in DN², formed by subtracting modelled
`sigma²`; “standard deviation” requires a square root before the regression.
The code, not the report prose, decides.

**Registered cells and magnitude statistic.** I will use exactly the six
finite `e_flat` rows emitted by M70's committed `s06_pedestal.py`:
`109MSDCF`, `112MSDCF`, `coffee-bean`, `bee-1`, `bee-2`, and `bee-3`. For each
row I will compute

`V_PRNU = (0.003096 × level)²`,

`fraction = V_PRNU / e_flat`, and

`remainder = e_flat − V_PRNU`.

The pooled summaries will be the ratio of sums, the median row fraction, and
the range. I will also fit the same log-log slope used by M70 to the positive
remainder when at least three cells remain positive. No cells will be dropped
except by that stated positivity requirement.

**Registered decision rule.** “Accounts for” means the PRNU prediction is
within a factor of two of `e_flat` in at least five of six cells and the
ratio-of-sums lies in `[0.5, 2]`. “Accounts for part” means the ratio-of-sums is
in `(0, 0.5)` with a positive aggregate remainder. A ratio above 2 or negative
aggregate remainder means the two quantities are inconsistent under the
registered mapping. Cell heterogeneity will be reported even if the pooled
rule passes.

**Registered check against SYNTHESIS fact 1064.** I will recompute M71's
§8.3 shipped-versus-truth arithmetic from M71's own formula and inputs, then
test whether substituting or adding M70's residual changes it. It changes
SYNTHESIS fact 1064 only if M70 measured a noise term absent from M71's
`gS + sigma0² + (κS)²` truth model rather than an alternate estimate of the
same PRNU term.

### 2.2 Item 2 — the two M5 diffraction knees

**ARGUED candidate mechanisms.** The discrepancy can arise from frame/tile
selection, ROI, tile size, window or detrending, frequency normalisation,
bin-centre versus bin-edge reporting, or a changed driver default. These are
separable because most change diagnostic fields (`nfrm`, `dyn`, frequency
step, or reach) as well as the knee.

**Registered primary reproduction.** I will run the exact M5 §12 command on
`109MSDCF`, including `--tile 128`, and separately run the committed default
tile size. The primary row is centre/GQ/tile/Hann/isotropic. I will record
`f_sig`, `dyn`, `kappa`, floor sd, floor/model, and `nfrm`; the placebo is the
in-run negative control.

**Registered mechanism rule.** A configuration difference explains the
discrepancy only if one arm reproduces M5's full diagnostic fingerprint
(`f_sig`, `dyn`, `kappa`, floor sd, and `nfrm`) while the other reproduces
M70's full fingerprint. Matching `f_sig` alone is insufficient. If tile size
does not do this, I will vary one remaining candidate axis at a time and
report the unresolved result rather than choose a near match.

**Registered convention checks.** I will derive the GQ sensor-frequency
conversion and reported knee edge directly from `m5_lib.py`, and compare their
maximum possible one-bin shift with the observed discrepancy. I will inspect
Git history for code changes. These checks can eliminate normalisation,
bin-centre/edge, and post-M5 code drift without fitting.

**Registered downstream propagation.** For the supported lower bound on
`f_c`, I will recompute

`B_max = 5.12 / (0.550 × 11 × f_sig)`.

I will retain M5's independent reverse bound only if its clean-floor premise
reproduces, and retain the independent f/8 model-free bound unchanged. With
conditional `m = 2`, I will map any surviving `B` interval through
`p = m / (B − 1)`. I will state separately whether `B = 5`, `B = 1`, and
M5's published `p ≈ 1.0–1.4` survive.

### 2.3 Controls and ways this can fail

**Registered controls.** Item 1 uses M71's two-green covariance estimator,
whose rolled covariance and paper-texture controls are already committed, but
M70's six cross-stack cells are not independent sensor replicates. Item 2's
placebo must reproduce in the same run, and the complete diagnostic
fingerprint must match rather than one scalar.

**Registered failure conditions.** Item 1 remains heterogeneous rather than
settled if the six cell fractions cross both below 0.5 and above 2. Item 2
remains unresolved if no single registered configuration reproduces both
fingerprints. Neither failure will be promoted into a directional conclusion.

---

## 3. Item 1 — the flat residual is variance, and measured PRNU explains one quarter

### 3.1 Units, settled from M70's driver

**MEASURED.** M70's `s06_pedestal.py` calls:

```python
s, nvar = A5.signal(d)
e_flat = float(np.mean(s[:, ~tex, :][:, :, j]))
```

and `s05_analyse.py::signal` is:

```python
nvar = M.noise_var_dn2(d["level"], d["iso"]) * sigma_scale
return d["power"] - nvar[:, :, None], nvar
```

`d["power"]` is Welch periodogram power and `nvar` is `sigma²`. There is no
square root before either `e_flat` or the log-log regression. M70's own emitted
unit line confirms the trace:

```text
e_flat  mean residual (P - modelled sigma^2) on FLAT patches, DN^2
```

**DERIVED.** `e_flat` is a variance/power residual in DN², not a standard
deviation. The measured exponent is therefore compared directly with the
variance law `(κS)² ∝ S²`; halving 1.83 would be a units error.

### 3.2 Magnitude reconciliation

**MEASURED.** The command was:

```text
$env:PYTHONIOENCODING='utf-8'
python experiments\M76b-reconciliations\analyse.py
```

Its complete output is
`experiments/M76b-reconciliations/out/item1.log`; the machine-readable result
is `out/item1.json`. The decisive output was:

```text
stack              level     e_flat     V_PRNU   fraction   remainder     k_rem
109MSDCF          1570.2     106.02      23.63      22.3%       82.39   0.5781%
112MSDCF           122.7       0.86       0.14      16.8%        0.72   0.6895%
coffee-bean       4762.1    1104.45     217.37      19.7%      887.08   0.6254%
bee-1             2200.5     115.77      46.41      40.1%       69.36   0.3785%
bee-2             2296.8     158.27      50.56      31.9%      107.71   0.4519%
bee-3             2574.1     113.77      63.51      55.8%       50.26   0.2754%

original exponent = 1.8261, R2 = 0.9713
remainder exponent = 1.7546, R2 = 0.9295
PRNU/e_flat ratio of sums = 25.12%; median = 27.12%; range = 16.78%..55.82%
aggregate remainder = 1197.50 DN^2 of 1599.14 DN^2
m71_pair_min: ratio of sums 22.17%, cell range 14.81%..49.27%
m71_pair_max: ratio of sums 28.46%, cell range 19.01%..63.26%
```

**MEASURED/DERIVED — the registered “accounts for” rule fails.** Only one of
six predicted values is within a factor of two of `e_flat`, not the required
five, and the ratio of sums is 0.2512 rather than `[0.5, 2]`.

**MEASURED/DERIVED — the registered “accounts for part” rule passes.** The
ratio of sums lies in `(0, 0.5)` and every remainder is positive. M71's
`κ=0.3096%` contributes **401.64 DN² of the aggregate 1599.14 DN²**, leaving
**1197.50 DN², or 74.88%**, unaccounted for by measured green-photosite PRNU.

**MEASURED — honest κ sensitivity, not a confidence interval.** M71's five
matched-pair estimates span 0.2909–0.3296%. Substituting those endpoints moves
the aggregate explained fraction only from **22.17% to 28.46%**. This is a
re-draw range, not a 95% interval. M70 supplied no cellwise uncertainty for
`e_flat`, so a joint probabilistic interval cannot be constructed from the
committed outputs.

**DERIVED.** If the remainder were another independent multiplicative term,
its equivalent fractional amplitude would have to range from **0.2754% to
0.6895%** across cells, as the final column shows. It is not one common
amplitude. Subtracting the measured PRNU term leaves a still level-dependent
residual with exponent **1.7546** and R² **0.9295**.

**ARGUED — the remainder is unruled, not “texture measured.”** M70's “flat”
cells are low-texture patches in real subjects, not sensor flat fields. The
remainder can therefore be low-contrast scene texture, a spectrally shaped
fixed sensor term not represented by scalar κ, or both. M71's two-green
cross-covariance isolates sensor PRNU from paper texture in M71's captures; it
does not measure scene texture in M70's six cells. The exponent cannot choose
among those terms because all multiplicative amplitudes square into an
approximately quadratic power law.

### 3.3 SYNTHESIS fact 1064

**MEASURED.** Re-evaluating M71's own §8.3 formula from M71's `03-ptc.json`
gives the same **504.4 DN** crossover and **−12.752%** shipped-model error at
8000 DN:

```text
M71 model check: crossover 504.4 DN, shipped error at 8000 -12.752%
```

**DERIVED — no change to SYNTHESIS fact 1064.** M71's truth model already
contains `(κS)²`; the 25.12% contribution above is the same term observed
through M70's spectral statistic and must not be added a second time. The
74.88% remainder has not been isolated as sensor noise. Treating real-subject
texture as noise would make the model more conservative for the wrong reason.
If a future flat-field spectrum establishes that some remainder is a distinct
sensor term, SYNTHESIS fact 1064's over-confidence magnitude must then be
recomputed; this reconciliation does not establish that premise.

---

## 4. Item 2 — `--tile 128` versus the 256 default

### 4.1 Independent reproduction

**MEASURED.** I first ran M5's exact §12 command, including the option M70
omitted:

```text
cd experiments\m5-diffraction
$env:PYTHONIOENCODING='utf-8'
python m5_measure.py measure C:\dev\macro\test\109MSDCF --n 11.0 --tile 128 --dark D:\macro-dark-frames\123MSDCF
```

The actual primary and control output was:

```text
centre   GQ    tile  reach 0.351  dyn 1297.2  kappa 0.056 | f_sig 0.2762  B_max 3.064 | floorSD 11.91  nfrm 4
centre   GQ placebo | best f_sig 0.2762  plac f_sig 0.2154 | best floorSD 11.91  plac floorSD 12.00 | best dyn 1297.2 plac dyn 893.9
TIGHTEST VALID BOUND
   centre / GQ / tile   dyn 1297   floor 0.950x model
   f_sig  = 0.2762 sensor cyc/px = 53.9 cyc/mm
   B     <= 3.064
```

The full output is
`experiments/M76b-reconciliations/out/m5-tile128.log`.

**MEASURED.** I then omitted `--tile`, invoking the committed default of 256:

```text
python m5_measure.py measure C:\dev\macro\test\109MSDCF --n 11.0
```

The actual output was:

```text
centre   GQ    tile  reach 0.352  dyn 322.6  kappa 1.214 | f_sig 0.2375  B_max 3.563 | floorSD 11.72  nfrm 1
centre   GQ placebo | best f_sig 0.2375  plac f_sig 0.2154 | best floorSD 11.72  plac floorSD 11.84 | best dyn 322.6 plac dyn 206.8
TIGHTEST VALID BOUND
   centre / GQ / tile   dyn 323   floor 0.935x model
   f_sig  = 0.2375 sensor cyc/px = 46.4 cyc/mm
   B     <= 3.563
```

The full output is
`experiments/M76b-reconciliations/out/m5-default-tile256.log`.

### 4.2 Mechanism and eliminated alternatives

**MEASURED — tile size reproduces both complete fingerprints.**

| source/configuration | tile | `f_sig` | `dyn` | M5 scatter `kappa` | floor sd | floor/model | `nfrm` | placebo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M5 §4.1 published | 128 | 0.2762 | 1297 | 0.056 | 11.91 | 0.950 | 4 | 0.2154 |
| M76b exact M5 §12 command | 128 | 0.2762 | 1297.2 | 0.056 | 11.91 | 0.950 | 4 | 0.2154 |
| M70 reproduction | 256 | 0.2375 | 323 | 1.214 | 11.72 | 0.935 | 1 | 0.2154 |
| M76b committed default | 256 | 0.2375 | 322.6 | 1.214 | 11.72 | 0.935 | 1 | 0.2154 |

Here “M5 scatter `kappa`” is the knee estimator's per-bin floor-scatter
parameter, not M71's photosite PRNU κ.

**DERIVED.** Tile size changes two mechanisms at once. A 512-sample ROI yields
49 half-overlapped 128 tiles but only 9 half-overlapped 256 tiles; the finer
tiling selected four distinct frames at the published centre/GQ cell while
the default selected one. Tile size also sets the FFT and radial-bin
resolution. The ROI-policy row independently moves from 0.2762 at tile 128 to
0.2375 at tile 256, so frame selection is not the whole effect.

**MEASURED — the “control reproduced” clue was real but incomplete.** The
scalar placebo knee is 0.2154 under both sizes. Its other diagnostics are not
the same: placebo `dyn` is **893.9 versus 206.8**, and floor sd is **12.00
versus 11.84 DN**. One coincident scalar concealed a changed configuration.

**MEASURED — no changed default.** `git log --all` finds one M5 code commit,
`dea3cfd17a82f2222ec273a374de86fb1d22efe0`, and it introduces
`TILE = 256`. M5's report explicitly overrides that default with `--tile 128`.
M70 ran the same code but not the published invocation. The mechanism is an
omitted command-line argument, not code drift since M5.

**MEASURED/DERIVED — the other candidates are eliminated.** Both runs use the
same 22 frames, centre GQ ROI, Hann window, isotropic sector, and per-tile mean
detrending. `m5_lib.py` converts GQ frequencies to sensor units identically in
both runs. It reports the upper bin edge as `f[idx] + 0.5*step`; a
centre-versus-edge choice can move tile 128 by at most 0.0028 cyc/px and tile
256 by at most 0.0014 cyc/px, far below the observed 0.0387 difference. The
near-identical reaches, 0.351 and 0.352, also rule out a different Nyquist
normalisation.

**MEASURED — verdict.** `0.2762 cyc/px` is the right value for M5's
pre-existing, documented tile-128 measurement. `0.2375 cyc/px` is also a real
output, but for a different tile-256 configuration. M70's “does not
reproduce” claim is refuted because it did not execute M5's documented
command.

### 4.3 What SYNTHESIS fact 27 should say

**DERIVED.** The corrected wording should be:

> With `ROI=512`, `tile=128`, centre/GQ, Hann window and isotropic radial
> averaging on `109MSDCF`, M5 measures `f_sig=0.2762 cyc/px` as a lower bound
> on `f_c`, giving `B≤3.064`; the clean top-of-band floor gives the weaker
> reverse bound `B≳2.412`. The committed tile-256 default gives 0.2375 and is a
> different configuration, not a reproduction of the published command.

**DERIVED — downstream conclusions are unchanged.** With M5's configured
result, `B ∈ [2.412, 3.064]`. Conditional on `m=2`,
`p = 2/(B−1) ∈ [0.969, 1.416]`, which is M5's rounded
`p≈1.0–1.4`. `B=5` remains refuted by signal above its predicted cutoff on
5/5 GQ cells at both f/11 and f/8. `B=1` remains excluded by the independent
clean-floor reverse bound. No downstream number in SYNTHESIS fact 27 needs
repair; the configuration does.

**DERIVED — counterfactual, not the ruling.** Had tile 256 been the registered
configuration, its knee and reverse bounds would give approximately
`B ∈ [2.403, 3.563]` and `p ∈ [0.780, 1.425]`. `B=5` and `B=1` would still be
refuted, but `p≈1.0–1.4` would widen. This counterfactual shows why attaching
the tile size to the fact is load-bearing; it is not a reason to replace M5's
registered tile-128 result after the fact.

---

## 5. Verification

**MEASURED.** After generating both independent logs, I ran:

```text
$env:PYTHONIOENCODING='utf-8'
python experiments\M76b-reconciliations\verify.py
```

Actual output:

```text
PASS M70 exponent reproduces
PASS registered aggregate fraction
PASS all six remainders positive
PASS tile-128 primary fingerprint
PASS tile-128 placebo fingerprint
PASS tile-256 primary fingerprint
PASS tile-256 placebo fingerprint
PASS M5 report specifies tile 128
PASS committed driver defaults to tile 256
PASS bin convention cannot explain discrepancy
verify: 10/10 PASS
```

The committed output is
`experiments/M76b-reconciliations/out/verify.log`.

**MEASURED.** The required full corpus lint, run separately after the report
and artifacts were complete, returned:

```text
corpus_lint: 101 markdown file(s), 30 rust file(s); 890 facts, 366 disciplines, 137 questions, 11 risks, 42 rules
corpus_lint: checks run: A1 A2 A4 C1 C2 C3 N1 N2 N4 N5 S1 S2 S3 S4 S5 S6

corpus_lint: OK — no violations
```

---

## Candidate facts

`P1` **MEASURED.** M70's `e_flat` is `mean(power − sigma²)` in DN² with no
square root. Its exponent 1.8261 compares directly with PRNU variance's
exponent 2.

`P2` **MEASURED/DERIVED.** M71's `κ=0.3096%` accounts for 25.12% of M70's six
finite `e_flat` values by ratio of sums; median cell fraction 27.12%, range
16.78–55.82%. M71's five-pair κ range moves the aggregate fraction only to
22.17–28.46%.

`P3` **MEASURED/ARGUED.** After subtracting measured PRNU, 1197.50 of 1599.14
DN² remains (74.88%), with exponent 1.7546 and equivalent cellwise
multiplicative amplitudes 0.2754–0.6895%. It remains unruled between
low-contrast scene texture and another spectrally shaped fixed term.

`P4` **DERIVED.** SYNTHESIS fact 1064 is unchanged. M71's over-confidence
arithmetic already contains the measured κ; M70's remainder has not been
established as sensor noise and cannot be inserted into the truth model.

`P5` **MEASURED.** M5's exact documented `--tile 128` command reproduces its
full centre/GQ fingerprint, including `f_sig=0.2762`, `dyn=1297.2`,
floor-scatter `kappa=0.056`, floor sd 11.91 DN, ratio 0.950, `nfrm=4`, and
placebo 0.2154.

`P6` **MEASURED.** Omitting M5's documented tile override invokes the committed
256 default and reproduces M70's full fingerprint: `f_sig=0.2375`,
`dyn=322.6`, floor-scatter `kappa=1.214`, floor sd 11.72 DN, ratio 0.935,
`nfrm=1`, and placebo 0.2154. M70 reproduced a different configuration.

`P7` **DERIVED.** SYNTHESIS fact 27's number and conclusions survive. It should
retain `0.2762 cyc/px`, `B ∈ [2.412,3.064]`, the refutations of `B=5` and
`B=1`, and conditional `p≈1.0–1.4`, while naming `tile=128` as part of the
measurement configuration.

`P8` **MEASURED.** M76's previously unnamed 6/6 suite is
`experiments/M55-acceptance-spec/src/e19_m76_pooled_enumeration.py`; the count
was correct and its location was not reported clearly enough.

---

## What I did not measure

- **NOT MEASURED.** M70's six `e_flat` values have no committed cellwise
  uncertainty, so the reported PRNU fractions are conditional point-estimate
  reconciliations, not confidence intervals.
- **NOT MEASURED.** I did not measure the spatial spectrum of M71's green PRNU.
  Mapping its total high-passed variance to a flat mid-band power assumes the
  mapping M70 used; spatial correlation could redistribute power by frequency.
- **NOT MEASURED.** I did not identify M70's 74.88% remainder. Doing so needs
  the same spectral observable on true flat fields, not further arithmetic on
  real-subject “flat” patches.
- **NOT MEASURED.** I did not choose which of tile 128 or 256 is the better
  scientific estimator, nor sweep tile sizes. This commission reconciles the
  published measurement with its command; changing M5's registered analysis
  after seeing both outcomes would be a new milestone.
- **NOT MEASURED.** I made no new capture, changed no M5/M70/M71 harness code,
  and did not edit `SYNTHESIS.md` or `AGENTS.md`.
