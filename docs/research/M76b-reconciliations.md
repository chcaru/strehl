# M76b — two numeric reconciliations

## Headline

**STATUS: PRE-REGISTERED; RESULTS NOT YET RUN.**

This follow-up reconciles two measurements made concurrently by milestones that
could not see one another: M70's flat-patch residual against M71's PRNU, and
M5's published diffraction knee against M70's reproduction. Results will be
added only after this registration is committed.

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

Registration commit: **PENDING**. The full commit SHA will replace this marker
without changing any criterion below.

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

## Candidate facts

Results and numbered candidate facts will be added after measurement.

---

## What I did not measure

This list will be completed after the runs. The registration does not authorise
new captures, modification of read-only corpora, or edits to `SYNTHESIS.md`.
