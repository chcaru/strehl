# M189b — directional sharpening defeats the radial-bin envelope

**MEASURED: the frozen M189 v2 metric rewards a common directional linear
sharpening filter by `1.498791506x`, SEM `0.011647889`, over eight independent
noise batches.** Its predeclared `mean - 3*SEM` lower bound is `1.463847840x`,
above the inherited `1.01x` sharpening ceiling. The independently calculated
population ratio is `1.433905085x`: exact noise knowledge would still fail.

This confirms an **already-declared restriction**: M189's Amendment 1 explicitly
excludes “anisotropic transfer hidden by the radial bins.” It does not reverse
the measured isotropic controls. It does rule out reading M189's broader
common-LSI language as a guarantee for its implemented radial-bin envelope.

**Verification state:** this lane independently challenges M189's choices and
uses M189's actual `metric_v2.measure` unchanged. The new M189b harness and report
are measured by their author and await independent root review (rule 12). No
capture was opened, candidate repaired, scorecard changed, or shipping code edited.

## 1. Prior art and the exact delta

The dispatch ran:

```text
python experiments/ORCH-drift-check/prior_art.py noise colour covariance
```

The relevant conclusions read were M189-noise-colour-detail, M71-flat-fields,
M69-focus-noise-sd, BUILD-PYRNOISE, M48-read-noise-measured, V-GATHER,
BUILD-PYRNOISE-ADJUDICATION, M85-output-correctness, V-REVIEW-noise-verification,
and BUILD-HIGHLIGHT. Their shared lesson is that a metric must measure its
consumer's quantity, and that angular structure and noise covariance are not
captured by a global scalar. None supplies this experiment's numerical result.

The direct antecedents are:

- [M189 Amendment 1](../../experiments/M189-noise-colour-detail/AMENDMENT-1.md),
  structural repair and explicit anisotropy exclusion;
- [M189 V2-RESULT](../../experiments/M189-noise-colour-detail/V2-RESULT.md),
  held-out isotropic USM and physical improvement/degradation readings;
- [M189-repeat-referenced-detail](M189-repeat-referenced-detail.md) section 2.1,
  the existing warning that within-pool transfer variation has an unsafe sign;
- [M189-noise-colour-detail](M189-noise-colour-detail.md) sections 0, 3.3–3.5, 5.1,
  and 9, which mix broad common-LSI statements with a narrower final tested claim.

The delta is a concrete, powered counterexample on the frozen implementation,
with a new scene and filter and a population calculation. This is a restriction
test of an acknowledged gap, not a newly discovered pooling impossibility.

## 2. Reproducibility and frozen choices

Working directory: `C:\dev\blog\death-of-software\projects\strehl`.
Run commands, both exit `0`:

```text
python experiments/m189b-directional-detail/reproduce.py
python experiments/m189b-directional-detail/run.py
```

Python `3.12.10`, NumPy `2.4.4`; reproduction also uses SciPy `1.17.1`.
Before imports the scripts set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`,
`MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS` to `1`.
There are no unstated CLI flags and no stack/capture inputs. No timing claim is
made. The running HEAD was `cba20daef1b92e1c5b41d95df06a96c65c003051`.

The root instructed no commit before review. Therefore this is a **transcript-
and hash-frozen preregistration**, not a claim of a pre-run git commit:

| Frozen source | SHA-256 before the directional run |
|---|---|
| M189 `metric_v2.py` | `104F7414CE70C245AF0F4D14475047C05565084CA60C4DAAF2CA1AD486BC831E` |
| M189b `preregistration.md` | `A5FB2CD2116D0B73C47CAE2B5D9BA345C94A7F199F665DC75CFDCA004FB46A3C` |
| M189b `run.py` | `A63C52735F6506AECCAAC00D85DB8DE62C053AB7373841A058DC2ED5CCD835F1` |

Source hashes and byte lengths were identical before and after execution.
Before extending the fixture, `reproduce.py` called M189's unmodified v2 `main`,
rebinding only its output directory in memory. **Every original measurement,
ratio, fixture field, and scene hash reproduced exactly.** The new output lives
under M189b; M189's source and result files remain unchanged. Metadata HEADs are
expected to differ from the historical run; numerical payload equality is the
consistency check, not independent confirmation of its choices.

Complete evidence:

- [preregistration](../../experiments/m189b-directional-detail/preregistration.md);
- [source freeze](../../experiments/m189b-directional-detail/out/source-freeze.json);
- [reproduction check](../../experiments/m189b-directional-detail/out/reproduction-check.json);
- [flat-first readings](../../experiments/m189b-directional-detail/out/flat-first.json);
- [all measurements and population calculation](../../experiments/m189b-directional-detail/out/results.json).

## 3. Independent equation and falsifiable plant

**DERIVED.** For deterministic scene power `C_f >= 0`, independent photosite
noise, an unfiltered baseline, and a DC-preserving common convolution `K`,

```text
Q(Kx)/Q(x) = [sum_f |K_f|^2 C_f / sum_f C_f]
             / max(1, max_b mean_{f in b} |K_f|^2).
```

The unitary Fourier noise marginal is the mean photosite variance, including
for the signal-dependent PTC plant. Applying `K` multiplies both coherent and
noise power by `|K_f|^2`. But the two averages above weight different things:
the numerator weights **scene power**, while the denominator weights **modes**.
A bin mean is not an upper bound on its cells. The inequality in Amendment 1
would apply if its `K_b` were constant within each bin (or replaced by a certified
upper bound), not when `K_b^2` is the implemented average of an angularly varying
`|K_f|^2`. This claim is restricted to the stated white-baseline population;
already-coloured pipeline baselines require their own derivation.

**New fixture:** a continuous periodic scene with mean `8000 DN` and three
horizontal-coordinate cosines, each amplitude `600 DN`, Fourier indices
`68,71,74` on a `256 x 256` output, phases `0.2,1.1,2.4` radians. Frequencies
are `0.265625`, `0.27734375`, `0.2890625` cycles/output-pixel, all inside M189's
unchanged licensed band. Gaussian optics act before sensor noise at sigma
`0.85` (base), `0.45` (physical improvement), `1.30` (physical degradation), in
output pixels. These are bandlimited analytic cosines; no resampling simulation
is needed. This is a synthetic pre-noise optical change, not a real capture.

The common post-capture filter is the local three-tap stencil

```text
y[x] = 1.75*x[x] - 0.375*x[x-1] - 0.375*x[x+1]
K(f_x,f_y) = 1 + 0.75*(1 - cos(2*pi*f_x)).
```

It applies identically to scene and noise in every completed repeat. There is
no adaptive operation, denoising, re-noising, filter fit, clipping, tone, demosaic,
or PRNU. The perpendicular placebo uses the same stencil along `y`: it has the
same population radial noise gains but unit transfer on this scene. Post-blur
uses `[0.25,0.5,0.25]` along `x`. An unfiltered copied pair is the identity.

Each of eight independent batches contains 16 independent repeat pairs.
Gaussian temporal noise has variance
`0.221113*scene + (0.221113*1.2392)^2 DN^2`; seeds are `189200..189215` paired
in order. Optical/control arms reuse noise draws within a batch. The population
calculation uses the closed-form cosine powers and transfers, **no image FFT
or candidate call**. A separate spatial-stencil/cosine check differed by at most
`5.456968211e-12 DN`, below the frozen `1e-8 DN` bar.

The noise constants are supplied to both plant and candidate. This tests the
operator; it cannot validate sensor calibration. No parameters were fitted.

## 4. Flat and null first; control failure power

**MEASURED.** All flat batches were evaluated before any detail arm. Scores
are signed `DN^2 per licensed Fourier mode`; the null's population value is zero.
Do not interpret these as temporal sigmas or divide them by one another.

| Flat arm | Mean score | SEM over 8 batches |
|---|---:|---:|
| independent flat repeats | `0.303041368` | `1.197401720` |
| same common horizontal sharpening | `0.357057088` | `1.070842556` |
| sabotage: same noise realization supplied to both repeat members | `1770.516156595` | `1.537934998` |

Both independent flat arms satisfy the frozen `abs(mean)+3*SEM <100` bound.
The correlated-noise sabotage fails that bound by design, proving power to
detect repeat-correlated false structure. It is not a valid independent-noise
acquisition and is not used to reject the candidate.

The positive-control checker was also forced red by replacing each improvement,
physical-degradation, or post-blur ratio with identity. All three mutations were
rejected. The corresponding actual arrays can be produced by using base optics
or replacing the filter by identity; the gates have realizable failure inputs.
These mutations commission the checker, not the metric's quality validity.

## 5. Powered counterexample with placebo and physical controls

**MEASURED**, eight independently seeded batches. All means are means of paired
per-batch ratios to base. SEM describes noise-stream uncertainty on this one
fixed scene/filter, not a cross-scene generalization interval. The preregistered
`mean +/-3*SEM` bounds are a decision rule, not distribution-free confidence.

| Arm | Mean `Q_sup / base` | SEM | DERIVED population ratio |
|---|---:|---:|---:|
| identity | `1.000000000` | `0` | `1.000000000` |
| physical improvement | `4.808806534` | `0.001301918` | `4.808719229` |
| physical degradation | `0.055493579` | `0.000021657` | `0.055503099` |
| common horizontal sharpening | **`1.498791506`** | **`0.011647889`** | **`1.433905085`** |
| perpendicular sharpening placebo | `0.426637002` | `0.004266028` | `0.409247456` |
| common horizontal post-blur | `0.184005676` | `0.001087094` | `0.176523966` |

All physical/identity/placebo controls pass their predeclared predicates. The
noise-gain nulls also pass: weighted temporal-noise gains for base/improved/
degraded are `1.000105487 / 1.000153114 / 1.000075712`, SEM
`0.000850088 / 0.000842380 / 0.000854482`, each entire three-SEM range inside
`[0.97,1.03]`. A flat scene never receives the corresponding high detail score.

The sharpening intervention is real: weighted noise gain rises to
`1.845368511`, SEM `0.001943106`. The perpendicular placebo's raw coherent
power remains inside the frozen `[0.97,1.03]` null while its noise is penalized.
Thus merely running a filter does not force an increased score; matching the
filter's high-gain direction to the scene is load-bearing.

**DERIVED population mechanism:** horizontal sharpening raises coherent power
by `3.503760535x`, but the largest radial mean noise gain is only `2.443509387x`,
so the corrected score still rises by `1.433905085x`. Power gains at the scene's
three frequencies are `3.325199133`, `3.527715690`, `3.733532617`; the largest
cell gain anywhere in the licensed band is `3.871896449`. Charging a bin mean
as though it bounded these cells is the failure.

Finite estimation changes the size, not the existence, of that failure. The
sample maximum-bin baseline is `1.042386384`, SEM `0.006158659`, whereas the
population baseline is `1`; the sharpened sample maximum is `2.437252910`, SEM
`0.012433034`. The mean score ratio therefore need not equal the population
ratio even when weighted-noise averages are near their expectations. No extra
repeat-count sweep or bias correction was introduced after viewing results.

**Failure direction at the point of use:** coherent spectral energy, even after
this radial normalization, can rise under manufactured directional sharpening.
It can establish responsiveness and reject collapse in this synthetic fixture;
it cannot certify delivered detail against general common LSI processing.

## 6. Program disposition and a precise next falsifier

**ARGUED from the measured counterexample:** keep M189's isotropic control
results and genuine-improvement response, but restrict the words “common-LSI
safe” to the exact commissioned fixture. A declared absence of adaptive
re-noising does not exclude this failure: it uses an ordinary fixed convolution.
M189b supplies no evidence that any named comparator applies this filter.

A replacement transfer envelope must dominate the relevant **cell** gains,
or state and enforce an independently validated bound on within-bin variation.
Increasing repeat count alone cannot repair this structural undercharge.
An angular subdivision would itself need a within-cell variation argument and
finite-estimator commissioning; it is not automatically a repair.

The concrete next falsifier is this same deterministic directional scene and
post-capture stencil, with new independent noise seeds frozen before testing a
replacement. Require a retained physical-improvement positive, flat specificity,
and no sharpening rise under a predeclared uncertainty rule. Also re-choose
orientation and within-bin radial position; copying these settings alone would
not establish the proposed bound. A certified per-cell envelope is a candidate
direction, **not implemented or commissioned here**.

No owner capture is justified to repair this particular algebraic defect. M1
admission, actual comparator output tests, fixed-pattern and nonlinear pipeline
effects remain separate questions under the root's program.

## 7. Independent root verification

**VERIFIED by a separately written command:**
`python -B experiments/m189b-directional-detail/verify-directional.py`.
The root changed the scene from horizontal to diagonal, moved all three spatial
frequencies, changed the filter direction and amount, and used four new batches
of noise. The untouched `metric_v2.py` SHA-256 remained
`104f7414ce70c245af0f4d14475047c05565084ca60c4daaf2ca1ad486bc831e`.

The diagonal common filter scored `1.357701840x` the unfiltered baseline,
SEM `0.010787841`; the perpendicular-filter placebo scored `0.475042482x`,
SEM `0.004265598`. Genuine optical improvement remained positive at
`4.468111625x`, SEM `0.000900452`, and copied identity was exactly `1.0`.
The first executed flat control was `0.911867708` score units, SEM
`0.822183601`, consistent with zero; a deliberately shared-noise flat violated
the same control. This verifies the directional limitation under a different
defensible scene and operator, not general comparator behavior or calibration.
The full readings are in `out/independent-verification.json`.

## 8. Rule discharge for this bounded synthetic experiment

- Rules 8/11/18/20/24/34–36: commands, claim labels, flat-first and realizable
  mutations, failure direction, independently chosen scene/filter, shared-gain
  limitation, and nonzero intervention checks appear above and in `run.py`.
- Rules 9/10/17/39: flat/null first; spectral power is never called sigma;
  fixed frequency bins do not select from observations; analytic direction
  matching is the intentionally tested defect; all empirical headline ratios
  have batch SEM and identity/noise nulls. Population ratios are DERIVED.
- Rules 12/40/41/43: prior-art search/read, root-allocated M189b ledger entry,
  and independent root review are explicit. No assertion of novel absence.
- Rules 1–7/13–16/21/23/26/27/30/32/33/45/47–49: no shipping architecture,
  corpus decode, alignment, argmax, parameter/timing sweep, fitted calibration,
  merge observer, process intervention, native RAW views, Cargo, or visual
  verdict. All filters operate on named spatial axes. One numeric thread,
  exact invocation/environment, no scheduling authority exercised.
- Rules 19/22/25/28/29/31/31b/37/38/42/44/46: new experimental files use
  kebab-case; the allocated report preserves the milestone naming convention.
  No SYNTHESIS fold, numbered-fact allocation, existing structural edit, or
  commit occurred. Full gate output and exit codes were read without a
  truncating pipeline. Source content, symbols, hashes, and artifacts identify
  the evidence; pre-run sources were not changed after execution.
