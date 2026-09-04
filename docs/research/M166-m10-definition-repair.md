# M166 — M10 physical-depth definition repair

**Status:** proposal for lane M160 to apply; not a scorecard edit and not a
measurement result.

This proposal was prepared against
`docs/proposals/2026-09-sota-scorecard.md` SHA-256
`ef7cbb5cd740c647bdaf360dd574421449be4f24a17d971f295531a569892ccf`
as committed by M160 at `1549df476cb768048f8ff254f38ce0f9de9a35a8`.
The owner's `docs/proposals/2026-08-sota-path.md` remains authoritative.
The supporting audits are M144 (reference uncertainty), M154 (ruler angle
and coordinate ambiguity), M163 (uncertainty repair), M84b (focus-axis
nonuniformity), and `BUILD-BLEND` (uncommissioned synthetic boundaries).

## 0. Verdict

M163 repaired a real defect and its five uncertainty vetoes must be retained.
It did **not** define the seven depth-value inputs it consumes, the target
population behind `valid`, the serialized depth product, the flat-null
reduction, or synthetic layer/boundary scoring. Its standalone checker accepts
those as already-computed arrays or scalars.

The current M10 card therefore remains **ILL-DEFINED**. If M160 adopts the
complete specification below, the definition is closed; execution remains
**UNMEASURED — MISSING PHYSICAL TRUTH AND PRODUCT**. The missing inputs are
listed in §8. They must not be replaced by defaults.

## 1. What M163 fixed, and what it necessarily did not

### 1.1 The accepted repair

M163 commit `736e905a71742fef800efeb55c7549679abd9129` is incorporated
without lowering or deleting anything:

- `instrument-definition.json`, SHA-256
  `340715450cbdaf6ead4f67f28b2b129e6e887593eea12c1f4630448b6b123878`;
- `m10_checker.py`, SHA-256
  `e577a72717d7516e0211e2960b10f87c7586551181de5c3fd198b1bfb7722109`;
- `commission.json`, SHA-256
  `a6dabfc323aefe9012078ad41ed5ccd989431fdbdc678262e2ae5814b5464191`.

The repair retains all seven value bars and adds five mandatory vetoes:

1. finite non-negative one-sigma uncertainty at every candidate-valid target;
2. nominal 95% coverage in `[0.93,0.97]`;
3. empirical/predicted variance ratio in `[0.90,1.10]` in at least 9 of 10
   predicted-uncertainty deciles;
4. median reported 95% half-width `<=0.5` focus step;
5. p95 reported 95% half-width `<=1.0` focus step.

Its 20,000-pixel calibrated fixture passes. All-zero, all-infinite, random,
`0.50x`- and `1.25x`-scaled uncertainty, and a `1.50x` depth-error degradation
fail. Those are valid commissioning results for the uncertainty decision.

### 1.2 The unresolved interface

M163's `score_value_metrics` receives a dictionary containing seven finished
numbers. It does not derive any number from a depth file. Its
`UncertaintyInput.valid` is a caller-supplied Boolean array; the checker
flattens it but does not establish the independent truth-target mask or relate
it to a serialized product validity plane. Its unit adapter assumes residual,
candidate sigma, and truth sigma have already been converted to focus-step
units.

Consequently M163 cannot answer:

- which pixels are truth targets and which are merely candidate-valid;
- what grid, sign, origin, storage type, invalid sentinel, or field-curvature
  convention the physical-depth product uses;
- how the one allowed origin is fitted;
- how a nonuniform physical focus sweep becomes one “focus step”;
- which percentile convention defines the value p95;
- what “flat-null p95 range” means;
- what population and label rule define “layer confusion”;
- how the separately requested boundary bias affects the verdict; or
- how correlated ruler-angle, pitch, perspective, registration, and
  focus-scale uncertainty enter the result without becoming fake independent
  pixels.

That is not a criticism of M163's scope. It is the missing upstream contract
that the accepted uncertainty repair needs.

### 1.3 Constructive ambiguities in the current text

These examples use no candidate-specific assumption; each pair is permitted by
the current wording.

| Omission | Reading A | Reading B | Consequence |
|---|---:|---:|---|
| Valid denominator | A frozen target has 10,000 pixels; 9,800 carry valid candidate depth, so `valid=9800/10000=0.98` | Remove candidate-invalid pixels before forming the denominator, so `valid=9800/9800=1.00` | Same product fails or passes the 99% bar. M163 receives the chosen mask and cannot distinguish the readings. |
| One fitted origin | Residuals `[0,0,0,1.2]` steps use their unweighted mean `0.3`; nearest-rank p95 absolute error is `0.9` | Anchor the origin at the first reference point; p95 is `1.2` | Same depth samples pass or fail the 1-step bar. |
| Value p95 | For 20 errors containing 19 zeros and one `30`, nearest-rank p95 is `0` | Hyndman-Fan type-7 linear p95 is `1.5` | Same errors pass or fail the 1-step bar. M163 defines type 7 for its uncertainty-width p95 through NumPy, but the supplied depth-value p95 remains undefined. |
| Flat “p95 range” | For 100 residuals containing 95 zeros and five ones, `q95-q05=0` | The central-95% span `q97.5-q02.5=1` | Same flat map passes or fails the 0.5-step bar. |
| Synthetic boundary population | Exclude a 400-pixel transition band from 10,000 target pixels: layer confusion is `0/9600=0%` | Count every transition pixel whose depth is not within the correct layer tolerance: `400/10000=4%` | Same smoothed map passes or fails the 1% bar. The current boundary-bias quantity is report-only and cannot veto the first reading. |
| Depth-axis sign | Truth `[0,1,2]`, stored prediction `[0,-1,-2]`, with metadata interpreted as positive toward camera, is flipped before scoring: rank and slope ratio are `1` | Treat positive as away from camera without a declared transform: rank and fitted slope are `-1`, giving 200% slope error | The semantic phrase “micrometres” does not select an axis direction. |

The synthetic example is also a loose-direction defect. A map can be exact in
both interiors and replace a four-percent boundary band with a smooth
transition. Under the boundary-excluded reading it has zero layer confusion.
M163's width p95 can ignore a top four-percent wide-uncertainty tail, while a
calibrated top decile and 96% interval coverage can remain inside its bars.
Thus uncertainty calibration does not define or repair boundary truth.

## 2. Normative candidate product

M10 scores the common-merge shipping-default mode. The RGB render and every
depth-product file bind the same input-manifest, executable, complete settings,
gear-profile, and output-grid hashes. No per-arm tuning is permitted.

Each output contains:

1. `depth-um.tif`: one-channel, uncompressed little-endian BigTIFF,
   `SampleFormat=IEEEFP`, `BitsPerSample=32`, `SamplesPerPixel=1`, and
   `Orientation=1`;
2. `depth-sigma-um.tif`: the same representation and dimensions;
3. `depth-valid.tif`: one-channel unsigned 8-bit BigTIFF, values only `0` or
   `1`, `SamplesPerPixel=1`, and `Orientation=1`; and
4. `depth-manifest.json`: hashes of those files and the RGB output, width,
   height, pixel-origin convention, units, axis direction, capture/focus-map
   hashes, field-curvature profile hash, executable hash, and settings hash.

The three planes are on the native RGB output grid. Pixel centre `(x,y)` is
the centre of integer column `x` and row `y`, origin top-left, x right and y
down. No checker resampling is allowed. The depth axis is camera optical-axis
distance in micrometres and increases away from the sensor. It is relative
depth with one additive origin per capture; no sign, scale, slope, plane, or
nonlinear remapping may be fitted after output.

The scored values are the actual decoded binary32 values, not higher-precision
internal values. At `valid=1`, depth and sigma must be finite and sigma's sign
bit must be zero. At `valid=0`, both float planes must contain the
canonical quiet-NaN binary32 payload `0x7fc00000`. Any other mask code, shape
or grid mismatch, missing file, non-finite valid value, negative valid sigma,
or sentinel mismatch is a candidate product-contract failure. Lossy TIFF
compression, an implicit integer scale, and a unitless confidence plane are
forbidden.

The depth plane represents scene depth after the frozen optical
field-curvature correction required by C5. The checker does not fit away a
candidate-derived bowl or plane. Candidate uncertainty excludes independent
truth uncertainty; the checker combines the independent local terms.

## 3. Normative truth package and populations

### 3.1 Truth package

Before candidate output is opened, an independent truth producer writes and
hashes `m10-truth-manifest-v1`. Every numeric field is stored as a decimal plus
its IEEE-754 binary64 hexadecimal value; the hexadecimal bit pattern is
normative and the decimal is display-only. Every target row contains:

- stable `cell_id`, `site_id`, capture/arm ID, x, y, and target class;
- nominal physical truth depth in micrometres;
- independent local one-sigma truth uncertainty in micrometres;
- truth validity;
- for synthetic rows, true layer, both local layer-surface depths, and signed
  native-pixel distance from the true boundary; and
- every finite correlated-nuisance truth realization described below.

The manifest also binds target geometry, certified pitch, external pose,
focus-axis mapping, registration, field-curvature profile, generator, source
inputs, all masks, the pre-materialized bootstrap schedule, and a hash-bound
little-endian binary64 matrix of 10,000 independent-reference error draws,
row-major by draw then ascending `cell_id`. That matrix comes from the
independently commissioned local/repeat truth-error model, including
covariance wherever independence has not been demonstrated. Synthetic exact
truth uses all-zero reference draws.

`cell_id` is the UTF-8 encoding of
`arm|capture_id|site_id|xxxxxxxx|yyyyyyyy`, with zero-padded lowercase
hexadecimal unsigned x/y coordinates and no trailing NUL. These fields may
not be chosen independently to steer the population hash.

The scored campaign contains exactly three primary inputs and outputs: one
ruler arm, one flat arm, and one synthetic arm. Their capture IDs are
predeclared before any candidate output; all three and the pooled result must
pass, with no post-output selection. Repeats used only to estimate independent
truth uncertainty are also hash-bound and cannot be substituted after
scoring.

Target and site selection is input/truth-only. If an eligible mask contains
more pixels than its quota, retain the quota having the lowest unsigned
256-bit value of
`SHA256(UTF8("M10-POP-V1|")+cell_id)`; ties use `(y,x)`. If any quota cannot be
filled, the campaign is `UNMEASURED_CAPTURE_INADEQUATE`; no arm or site may
borrow from another. Quotas are filled only from independently truth-valid
cells that remain truth-valid in every admitted realization. A duplicate
`cell_id`, an out-of-bounds coordinate, a non-finite truth depth/sigma, a
negative truth sigma, or a target selected from a truth-invalid cell makes
the truth package inadmissible rather than becoming a candidate failure.

### 3.2 Physical ruler arm

Use a fresh untouched metrology-backed tilted planar target, not any burned
`10.26`-degree unit. The target must expose at least 20 predeclared,
non-overlapping strips across the depth span. Score exactly 20 strips and
exactly 1,000 target pixels per strip: 20,000 pixels total.

Certified ruler coordinates are arclength `s` along the target. For each truth
realization,

`z_true=(s-s_ref)*sin(theta_ext)`.

Equivalently using lateral projection is allowed only when the manifest
defines `x=(s-s_ref)*cos(theta_ext)` and obtains the identical truth. The
signed `theta_ext` is the angle from the plane perpendicular to the positive
optical axis to the ruler's positive-`s` direction, so its sign fixes whether
depth increases or decreases along the ruler. The
pixel-to-`s` projective mapping, lens-distortion correction, target pitch,
camera-relative angle, and their uncertainty come from external metrology,
not candidate focus or depth. `s_ref` is arbitrary because the one allowed
origin removes it.

Each strip's admitted truth depths must contain at least two distinct binary64
values and span at least eight `Delta_v`. Otherwise the ruler arm is
`UNMEASURED_CAPTURE_INADEQUATE`; a nearly depth-constant strip may not supply a
nominal rank or slope result.

External-angle uncertainty must contribute at most 2.5% slope error, as the
current scorecard already requires: for frozen nominal angle `theta_0`, every
admitted angle realization `theta_v` must satisfy
`abs(sin(theta_0)/sin(theta_v)-1)<=0.025`. A single-view image fit is not
external pose truth. The camera/lens/teleconverter/aperture, crop,
field-curvature profile, focus schedule, target pose, and common-input
conversion are fixed.

### 3.3 Flat physical null

Use exactly 20 non-overlapping 1,000-pixel sites on a physically certified
planar face: 20,000 pixels total. The existing clean ISO-100 round-battery
stack may fill this role only if an output-blind mask and an external
planarity bound are admitted before rendering; its current inventory record
alone does not establish either. Rim, embossing, scratches, and unsupported
background are ineligible.

The truth package supplies the physical plane depth at every selected pixel.
The checker fits no plane to candidate output. The external certificate must
supply the per-cell nominal surface, local sigma, complete systematic
envelope, and reference-error draws required by §§3.1 and 3.5. If any is
absent, the arm is `UNMEASURED_FLAT_TRUTH`; a visually flat photograph is not
a substitute.

### 3.4 Hidden synthetic non-planar two-layer arm

Use an independently implemented renderer and truth producer that imports no
candidate estimator, focus model, regularizer, or depth code. Freeze its code
and input contract before the candidate binary/settings; choose and conceal
the scored seed and latent labels until those hashes are frozen.

The generated scene contains 20 spatially disjoint non-planar two-layer
instances. At every scored coordinate both local layer depths lie inside the
focus bracket, satisfy `z_near<z_far`, and are separated by at least eight
conservative focus steps.
For every instance and admitted truth realization, the independently
certified minimum, over all affine planes `a+b*x+c*y`, of nearest-rank p95
absolute truth residual must be strictly greater than `1.0*Delta_v`. Thus even
an oracle-selected plane cannot meet the retained p95 bar. The certificate
and its interval/global-optimum proof are part of the frozen truth package.
Per instance select:

- 500 near-layer and 500 far-layer interior pixels with `|distance|>32`
  native px; and
- 500 near-side and 500 far-side boundary pixels with
  `0<|distance|<=32` native px.

`distance` is the Euclidean distance between pixel centres and the latent
continuous boundary on the native output grid, negative on the near side and
positive on the far side. Equality at 32 is boundary; equality at zero is
ineligible.

This gives 20,000 interior and 20,000 boundary pixels. The existing
`blend-truth` edge scene is not admissible: its own report says the scene is
not commissioned and refuses its edge rows.

The synthetic instrument must include a zero-noise exact-map commissioning
case whose latent depths, `Delta_v`, and zero uncertainty are exactly
representable in binary32. The serialized exact map must pass every value bar
and M163's exact-zero exception. A frozen rank-reversal mutation must produce
`rho=-1`; constant-plane and boundary-smoothing mutations must fail their
respective vetoes. This explicitly tests the representation step rather than
assuming an ideal real-valued output survives it.

### 3.5 Focus-axis and systematic truth

Each capture/arm supplies an independently measured, strictly monotone
physical focus-plane table `z_focus_um[frame]`. Reorder that table by
increasing physical depth, retaining the bound frame identities, and define
the conservative focus step for truth realization `v` as

`Delta_v = min_j(z_focus_um[j+1]-z_focus_um[j])`.

`Delta_v` must be finite and positive. Using the minimum rather than the mean
prevents the measured 1.53x within-stack step drift from making errors in
coarser parts of a sweep look artificially small. Report every gated error in
both micrometres and units of `Delta_v`; the focus-step bars use the latter.

Correlated angle, pitch, perspective/distortion, registration,
field-curvature, and focus-scale uncertainty must not be divided by the
number of pixels. The truth package enumerates the complete Cartesian vertex
set of their independently bounded intervals. If extrema are not certified to
occur on that vertex set, the truth producer must supply an interval-arithmetic
envelope or the arm is `UNMEASURED_TRUTH_ENVELOPE`. Local/repeat reference
draws are nested inside each systematic realization and outside site
resampling as specified in §4.3. The same local uncertainty remains the
per-cell truth sigma used by M163; the sampled draw is not added to that sigma.
Discrete alternatives for registration correspondence, layer identity, or
boundary membership are separate admitted realizations; they may not be
averaged or resolved after candidate output. A cell whose truth-valid status
is itself unresolved is ineligible before quota selection. If any admitted
alternative no longer satisfies the fixed per-class quotas, the result is
`UNMEASURED_TRUTH_ENVELOPE`, not a reduced denominator.

For each complete M10 result, let `P(v)` mean that all value and uncertainty
components pass under systematic realization `v`. The uncertainty decision is
`PASS` only if every admitted `v` has `P(v)=true`, `FAIL` only if every
admitted `v` has `P(v)=false`, and `UNMEASURED_TRUTH_ENVELOPE` otherwise.
Thus a favourable realization cannot create a pass, while a reference
interval crossing a bar cannot be misreported as a candidate failure.

## 4. Common reductions

### 4.1 Valid target and the one origin

For a truth-target cell, `candidate_valid` means mask `1`, finite depth, and
finite non-negative sigma. Every truth-target cell remains in the
valid-fraction denominator. Missing rows are never deleted. A finite
out-of-bracket prediction remains valid and accumulates its full error; it
may not be reclassified as a refusal.

For each capture and truth realization, fit exactly one candidate-dependent
quantity:

`raw_step=(z_pred_um-z_true_um)/Delta_v`,

`origin_step=exact_sum(raw_step over candidate-valid target cells)/N`, and

`origin_um=origin_step*Delta_v`.

Subtract that physical origin from every candidate depth in the capture.
Candidate uncertainty may not weight or move it. The origin is fitted once on
the full capture population for each systematic/reference-truth realization
and then held fixed during that realization's site resample; it is never
refitted on a bootstrap-selected subset. If `N=0`, every metric takes its
candidate-worst value. No other translation, sign, scale, slope, plane, or
nonlinear fit is allowed.

Define signed error

`e_step=raw_step-origin_step`

and

`e_um=e_step*Delta_v`, with canonical adjusted prediction
`z_adjusted_um=z_true_um+e_um`.

Candidate and local truth sigmas in step units are respectively
`sigma_candidate_um/Delta_v` and `sigma_truth_um/Delta_v`. This is M163's
accepted unweighted residual-demeaning operation, shared by value and
uncertainty scoring and performed exactly once; an integrated checker must
not fit another uncertainty-only origin. A candidate-invalid synthetic
interior cell is also a layer confusion.

Except where synthetic invalidity is expressly a confusion violation, value
statistics use the candidate-valid subset of the fixed truth-target
population; validity always uses the full fixed denominator. Fewer than two
candidate-valid cells makes rank and slope candidate-worst, and an empty
candidate-valid subset makes every error/range statistic candidate-worst.
Bootstrap replicates preserve this rule rather than dropping an invalid
replicate.

### 4.2 Quantiles, ties, correlation, and regression

- Value medians and p95 values use nearest-rank quantiles: sorted one-based
  rank `ceil(qN)`, no interpolation.
- M163's reported half-width median/p95 retain its accepted type-7 convention:
  with sorted values and `h=(N-1)q`, linearly interpolate elements
  `x[floor(h)]` and `x[ceil(h)]` using zero-based indices:
  `x[floor(h)]+(h-floor(h))*(x[ceil(h)]-x[floor(h)])`.
- Spearman rho assigns average ranks to exact binary64 ties and is Pearson
  correlation of the two rank vectors. Fewer than two distinct truth or
  prediction ranks, a zero denominator, or a non-finite result yields
  `rho=-1`.
- The predicted/true slope is the unweighted OLS coefficient
  `beta=sum((t-tbar)*(p-pbar))/sum((t-tbar)^2)`, where `t=z_true_um` and
  `p=z_adjusted_um`. A zero/non-finite denominator yields
  `slope_error=+inf`; otherwise `slope_error=abs(beta-1)`.
- Decode binary32 exactly into binary64. Elementary arithmetic is IEEE-754
  binary64, round-to-nearest ties-to-even, without fused multiply-add. Every
  sum is the exact real sum of its binary64 summands rounded once to binary64;
  products are formed before that sum. Thresholds use unrounded binary64
  results and equality passes. The precomputed truth manifest, not the
  checker, owns trigonometric evaluation.
- Any non-finite derived value makes its upper-bounded component `+inf` and
  its lower-bounded component candidate-worst (`0` for a fraction and `-1`
  for correlation); it is never omitted.

### 4.3 Confidence and pooling

Every arm/capture and every stated pooled population must pass its point bar.
The pooled one-sided 95% bound also passes. Use 10,000 hierarchical bootstrap
draws with seed `20260902`. For draw `b` under systematic realization `v`,
first add the frozen independent-reference error draw `(b,cell_id)` to every
nominal truth depth, refit the one allowed origin on the full target
population, and hold it fixed within that draw. Then sample the original
number of captures with replacement; within each selected capture, sample its
original number of non-overlapping `site_id` clusters with replacement and
retain all pixels of every selected cluster. A duplicated cluster contributes
its full rows again. Materialize and hash the complete integer resampling
schedule before candidate outputs so library RNG changes cannot move a
result. Point estimates use zero reference perturbation and the full
unresampled population.

For a lower bar, the score is the minimum of the point estimate and
nearest-rank bootstrap q05. For an upper bar, it is the maximum of the point
estimate and nearest-rank bootstrap q95. Validity and confusion additionally
retain their one-sided 95% Wilson bound on the exact pixel numerator and
denominator; the pessimistic value across point, Wilson, and cluster bootstrap
is scored. For validity, `k` is the candidate-valid count and the lower bound
is used; for confusion, `k` is the violation count and the upper bound is
used. The site bootstrap prevents a large correlated pixel count from
pretending to be independent evidence.

The Wilson bound has no continuity correction and uses
`z=1.6448536269514722`. For `p=k/n`, define
`d=1+z^2/n`, `c=(p+z^2/(2n))/d`, and
`h=z*sqrt(p*(1-p)/n+z^2/(4*n^2))/d`; the lower bound is
`max(0,c-h)` and the upper bound is `min(1,c+h)`. An empty denominator takes
the candidate-worst bound.

## 5. Exact value decision

### 5.1 Ruler accuracy and physical scale

For each ruler strip and for the pooled 20 strips, compute candidate-valid
fraction on the full fixed target denominator. On the candidate-valid subset,
compute:

- Spearman rho of adjusted predicted versus truth depth;
- nearest-rank median and p95 `abs(e_step)`; and
- predicted/true OLS slope error.

The ruler arm passes only when every strip, the pooled point statistic, and
the pooled confidence score satisfy:

- valid fraction `>=0.99`;
- rank correlation `>=0.99`;
- median absolute error `<=0.5` focus step;
- p95 absolute error `<=1.0` focus step; and
- slope error `<=0.05`.

Report the same absolute errors in micrometres. No candidate-derived scale
correction is applied.

### 5.2 Flat-null span

For the candidate-valid subset of each flat site and of the pooled flat
population, sort signed `e_step` and define

`flat_range_95 = nearest_rank(e_step,0.975) - nearest_rank(e_step,0.025)`.

Every site and the pooled/confidence score must have candidate-valid fraction
`>=0.99` and `flat_range_95<=0.5` focus step. The range uses the
candidate-valid subset, with an empty subset candidate-worst. This is the sole
meaning of “flat-null p95 range”; `q95-q05`, max-minus-min, and a p95 of
hand-chosen tile ranges are not alternate implementations.

### 5.3 Synthetic non-planarity and layer boundaries

Apply the ruler valid/rank/median/p95 bars independently to every 2,000-cell
synthetic instance and to the complete 40,000-pixel truth population. Also
apply the valid/median/p95 bars, without a rank requirement, to every
1,000-cell `(instance,true_layer)` population and each 20,000-cell global
layer. The complete population receives the pooled confidence score. Rank and
error statistics use each population's candidate-valid subset; validity uses
its full fixed denominator.

For each interior pixel, classify adjusted candidate depth to the closer of
the two local truth surfaces in micrometres. An exact binary64 distance tie,
candidate-invalid cell, or selection of the wrong true layer is a violation.
Compute violation and valid fractions for every `(instance,true_layer)`
500-cell population, every 1,000-cell instance, each 10,000-cell global
layer, and the pooled 20,000-cell interior population. Their pessimistic
maximum confusion is `layer_confusion`; it must be `<=0.01`. Every listed
valid fraction must be `>=0.99`.

Boundary bias is no longer report-only. For each instance and each true side
of the `0<|distance|<=32` band, for each global side, and for the pooled
boundary population, first require candidate-valid fraction `>=0.99`. On the
candidate-valid subset compute:

- `boundary_bias_side=abs(nearest_rank(e_step,0.5))`; and
- `boundary_abs_p95_side=nearest_rank(abs(e_step),0.95)`,

with an empty subset candidate-worst. The maximum over sides, instances, and
pooled populations must have boundary bias `<=0.5` step and boundary absolute
p95 `<=1.0` step. These reuse the existing median/p95 error magnitudes as
non-compensating boundary vetoes; they introduce no easier threshold.

### 5.4 Seven retained scalar values

For each truth realization, fold the exact populations into M163's seven
unchanged value names in the candidate-adverse direction:

- `valid_fraction`: minimum across every required ruler strip, flat site,
  synthetic instance/layer/side, arm-wide population, and required confidence
  score;
- `rank_correlation`: minimum across every ruler strip, pooled ruler, complete
  synthetic target, every synthetic instance, and their required confidence
  scores;
- `median_abs_error_steps`: maximum across every ruler strip, pooled ruler,
  complete synthetic target, every synthetic instance/layer, and their
  required confidence scores;
- `p95_abs_error_steps`: maximum across every ruler strip, pooled ruler,
  complete synthetic target, every synthetic instance/layer, and their
  required confidence scores;
- `ruler_slope_error_fraction`: maximum across ruler strips and pooled ruler;
- `flat_null_p95_range_steps`: maximum across flat sites and pooled flat; and
- `synthetic_layer_confusion_fraction`: maximum across layers, instances, and
  pooled synthetic interior.

All seven retain M163's accepted bars:

`valid>=0.99`, `rho>=0.99`, median error `<=0.5`, p95 error `<=1.0`,
slope error `<=0.05`, flat range `<=0.5`, and confusion `<=0.01`.

The two boundary quantities are additional mandatory vetoes. A truth
realization has `P(v)=true` only if all nine value components and all five
uncertainty vetoes pass.

## 6. Exact integration of M163's uncertainty decision

For each of ruler, flat, synthetic interior, synthetic boundary, complete
synthetic target, and the global pooled population, form arrays in ascending
`cell_id` order. The global array concatenates arm order
`(ruler,flat,synthetic)` after each arm's own origin and `Delta_v` conversion:

- `residual_steps=e_step`;
- `candidate_sigma_steps=sigma_candidate_um/Delta_v`;
- `truth_sigma_steps=sigma_truth_um/Delta_v`; and
- `valid=truth_target && candidate_valid`.

Each listed population supplies at least 10,000 usable candidate-valid target
pixels or fails M163's minimum-population veto. Apply the accepted exact-zero
special case only when every residual, candidate sigma, and truth sigma is
exactly zero. `residual_steps` is already the once-demeaned result from §4.1;
do not demean it again.

Sort deciles by `(candidate_sigma_steps,cell_id)`. With
`N=10q+r`, the first `r` deciles contain `q+1` rows and the remainder `q`.
For decile `d`,

`V_emp=mean(residual_steps^2)`,

`V_pred=mean(candidate_sigma_steps^2+truth_sigma_steps^2)`, and

`R_d=V_emp/V_pred`.

When `V_pred=0`, `R_d=1` only if `V_emp=0`; otherwise the decile fails. At
least 9 of 10 ratios must lie in `[0.90,1.10]`.

Coverage uses

`abs(e_step) <= 1.959963984540054 * hypot(candidate_sigma_steps,truth_sigma_steps)`

and must lie in `[0.93,0.97]`. Candidate-only half-width is
`1.959963984540054*candidate_sigma_steps`; its type-7 median must be `<=0.5`
step and type-7 p95 `<=1.0` step. Every candidate-valid target must have
finite non-negative sigma.

Mean Gaussian CRPS in step units remains a mandatory disclosure without a
pass threshold. For combined sigma `s`, its per-cell value is `abs(e_step)`
when `s=0`; otherwise, with `z=e_step/s`,
`s*(z*(2*Phi(z)-1)+2*phi(z)-1/sqrt(pi))`, where `phi` and `Phi` are the
standard-normal density and CDF. Report the arithmetic mean in the canonical
M163 checker arithmetic. CRPS cannot rescue or veto a candidate.

Within a fixed systematic realization, every listed population must pass all
five uncertainty vetoes. The final cross-realization decision uses §3.5:
every realization must pass for M10 to pass, while a mixed pass/fail envelope
is `UNMEASURED_TRUTH_ENVELOPE`.

## 7. Loose-direction closure

This definition rejects the depth-product degradations the current text can
reward or ignore:

- **Constant depth:** predicted ranks have zero variance and score `rho=-1`;
  ruler slope error is 100%. On balanced synthetic layers, a constant equal to
  one layer misclassifies at least 50%; a midpoint tie violates every cell.
- **Hard-coded tilted plane:** it may imitate the ruler, but the hidden
  non-planar two-layer arm fails rank, absolute error, or layer confusion.
- **Over-smoothed depth:** the flat arm may improve, but the separately scored
  synthetic boundary bands fail bias or p95 error. Boundary pixels cannot be
  silently removed from their fixed scoring population. Constructively, the
  canonical smoothing mutation replaces every boundary value by the midpoint
  of its two local surfaces. Their separation is at least eight steps, so
  every boundary error is at least four steps and both boundary vetoes fail.
- **Correct ordering with wrong units or sign:** Spearman alone may look good,
  but the unfitted physical slope and absolute micrometre/step errors fail.
  Axis reversal gives `beta=-1` and 200% slope error.
- **Refusal:** candidate-invalid truth targets remain in the validity
  denominator and synthetic-interior invalids are confusion violations.
  Boundary invalids remain in every side's validity denominator. An
  all-invalid product has zero valid fraction.
- **Fabricated uncertainty:** M163's commissioned zero/infinity/random,
  scale-0.50, scale-1.25, and depth-error-1.50 controls retain their failures.
  Width vetoes prevent all-wide intervals.
- **Target or synthetic hard-coding:** physical ruler and flat truth are
  independent; the synthetic seed/labels are hidden until the executable and
  settings are frozen; one unchanged mode must pass all arms.

M10 is a physical-depth-product gate, not an RGB sharpness gate. A visually
blurred RGB render accompanied by an independently exact depth product can
legitimately pass M10, but cannot pass the program's independent M1/M2/M3/M8
requirements. Claiming that M10 itself certifies RGB quality would expand its
scope beyond the owner plan.

**Repair direction:** preserve M163's five uncertainty vetoes, define the
physical product and truth populations upstream, and make hidden boundary
accuracy a non-compensating value veto.

## 8. Inputs that do not yet exist

| Missing input | Why no definition can manufacture it | State until supplied |
|---|---|---|
| Fresh untouched metrology ruler unit | The original three `10.26`-degree stacks are burned; their only angle record has unbounded uncertainty. The new unit needs certified pitch, externally bounded camera-relative pose, distortion/registration, 20 strips, and an angle contribution `<=2.5%` slope error. | `UNMEASURED_PHYSICAL_TRUTH` |
| Independent physical focus-axis map | Existing evidence shows step size can drift 1.53x inside one sweep. M10 needs per-frame focus-plane positions and a bounded conservative minimum step for each arm. | `UNMEASURED_FOCUS_SCALE` |
| Depth/uncertainty/validity product | Strehl emits none of the three required planes today. A checker cannot infer an omitted product from the RGB render. | `UNMEASURED_PRODUCT_ABSENT` |
| Flat-null truth | The ISO-100 battery stack is registered clean, but no admitted output-blind face mask or planarity bound exists. If it cannot be certified, a fresh planar unit is required. | `UNMEASURED_FLAT_TRUTH` |
| Hidden synthetic depth instrument | The existing two-layer edge scene explicitly refused its edge rows as uncommissioned. A separate renderer, latent truth, certified affine-plane defeat, population, and mutation controls are required. | `UNMEASURED_SYNTHETIC_TRUTH` |
| Local/repeat truth uncertainty | Physical value and calibration scoring needs independent repeat/local truth sigma, the frozen 10,000-draw error matrix, and dark/FPN/registration covariance treatment; M163's synthetic fixture cannot supply a future capture's values. | `UNMEASURED_UNCERTAINTY_TRUTH` |
| Integrated commissioned checker | M163 commissions the five uncertainty formulas, not product decoding, truth construction, seven value reductions, boundary vetoes, or nuisance-envelope traversal. The integrated checker needs exact-map null, origin-shift null, sign/scale mutations, constant-plane, boundary-smoothing, mask-refusal, and independent reimplementation controls. | `UNMEASURED_CHECKER_UNCOMMISSIONED` |

Until all rows are supplied, M10 has neither `PASS` nor `FAIL`. After this
definition is adopted, those are evidence blockers, not remaining permission
to choose a statistic.

## 9. No-softening audit

- All seven existing value thresholds are retained.
- All five M163 uncertainty vetoes are retained.
- Value and uncertainty bars apply to their non-compensating arm/sub-arm
  populations and pooled populations under every admitted
  correlated-nuisance realization.
- A truth envelope that crosses a threshold becomes `UNMEASURED`, never
  `PASS`; only an all-realization pass licenses M10.
- The focus-step conversion uses the smallest measured physical step, not a
  favourable mean.
- Candidate-invalid targets remain in denominators.
- Ruler strips, flat sites, synthetic instances/layers/sides, and pooled
  populations are non-compensating; a bad local region cannot be diluted by
  the rest of the image.
- The report-only boundary quantity becomes two mandatory vetoes using the
  existing 0.5-step and 1-step magnitudes.
- No candidate-derived sign, scale, slope, plane, field-curvature, or
  uncertainty-weighted origin correction is added.

Nothing in this proposal can turn a miss under the current M10 bars into
`PASS`.

**Non-emptiness / representation control.** On the required checker-only
fixture, choose distinct truth depths and `Delta_v` exactly representable in
binary32, zero truth uncertainty, all-valid masks, and serialize the exact
truth with zero candidate sigma. Then origin and every error are zero,
`rho=1`, `beta=1`, flat range/confusion/boundary errors are zero, and M163's
exact-zero rule passes. At the smallest 500-cell subgroup, all-valid Wilson
LCB95 is `0.994618035370158` and zero-confusion UCB95 is
`0.005381964629842`, so the added confidence rules also pass. This is a
commissioning null, not physical score evidence, but it proves that binary32
serialization itself does not recreate M8-O's impossible-representation
defect.
