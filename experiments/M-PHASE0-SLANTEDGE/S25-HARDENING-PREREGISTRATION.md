# M-PHASE0-SLANTEDGE — S25 hardening preregistration

Status: **frozen before any hardening variant was executed on the score
battery**.

## Decision and scope

This experiment asks whether the target-locked `D_b` construction underlying
SCORECARD-BASELINE's `S_25` can simultaneously:

1. ignore post-render linear sharpening;
2. move quantitatively in both directions under known optical blur and known
   optical improvement;
3. survive common monotone tone transforms;
4. avoid rewarding or penalising a change in white output-noise amplitude; and
5. accept only the registered slanted-edge angle.

The alternative is a direct formal-M1 run.  Existing manifests already record
zero matched bee darks/flats, an undefined bee defocused-source denominator,
the wrong linear output colour space and invalid output geometry.  A
manifest-only preflight is therefore registered; it must not open capture or
render pixels and cannot promote a synthetic result to formal M1.

No ordinal variant is included.  A monotone edge's ordering does not identify
its blur width, and the already commissioned licensed Q25 rank statistic reads
USM as `5.560744x` while the real improvement reads `0.977981x`.  Any future
ordinal proposal requires a new preregistration and must run identity and USM
before any other arm.

## Scope decision: comparative, not MTF50

The output is a comparative inverse-pixel scale, not MTF50 or a cycles/pixel
cutoff.  The prior absolute-MTF50 and `UNLICENSED_GT_0.25` interface bars are
explicitly dropped: every candidate consumes only the licensed
`[0.20,0.25)` bins, and no value above 0.25 is inspected or reported.  The
physical **ratio** predicates remain unchanged.  Relabelling any result MTF,
MTF50, SFR, cutoff or resolution in cycles/pixel is a checker failure.

## Frozen source primitive

The only inherited candidate primitive is the source-pinned
`vendor_m1.py::m1_tile`, already AST-checked against
`experiments/SCORECARD-BASELINE/common.py::m1_tile`.  Its ten bins, Tukey-0.25
window, target-locked gain, repeat-difference noise, `D_b`, FRC and native
`S_25` are unchanged.  Candidate synthetic helpers and live candidate imports
remain forbidden.

For repeat images `A`, `B` and independent reference `R`, the inherited
quantity is

```text
g_b = Re(sum(((A+B)/2) conj(R))) / sum(|R|^2)
N_b = max(0.5 sum(|A-B|^2), U_b)
D_b = g_b^2 sum(|R|^2) / N_b .
```

## Independent floor and eligibility

All scored evaluations use 64 independent 256x256 sites.  A separate 128-pair
calibration set contains only independent Gaussian noise with sd 0.02.  For
each licensed bin, `U_b` is the empirical 95th percentile (`method="higher"`)
of `0.5 sum(|F_A-F_B|^2)` after the same Tukey window.  The calibration seed
namespace is `SeedSequence([2026091000, pair])`; it never supplies a scored
pixel.

The floor-activation fraction is reported.  A floor-aware variant must
activate the supplied floor in at least one licensed-bin/site cell on the base
arm and must fail a checker mutation that replaces every `U_b` by zero.

Eligibility is computed from another 64-site namespace,
`SeedSequence([2026094000, site, role])`.  The focused source is the registered
sigma-1.50 edge.  Its defocused partner receives the registered independent
sigma-0.75 convolution and fresh post-blur sd-0.02 noise.  Per bin, subtract
the median calibration noise power from focused and defocused windowed power.
The point estimate is the ratio of sums over sites.  The lower bound is the
5th percentile of 10,000 site-bootstrap ratios using PCG64 seed `2026095000`.
Every `[0.20,0.25)` bin must have point ratio at least 2.0 and lower bound at
least 1.5.  Eligibility reads source/reference data only and is common to all
output arms.

Three mandatory eligibility controls precede score measurement:

* the focused/defocused edge must pass;
* equal-focus and constant-flat sources must refuse; and
* a literal heterogeneous power population whose point ratio passes but
  bootstrap lower bound fails must refuse.

## Independent tone witness

Tone-aware variants receive eight exact copies of the scorecard's 33 linear
steps from 0.02 to 0.98.  The generator applies the same point map as the
scored render, but the candidate receives only observed step values and the
fixed nominal sequence.  It fits a monotone PCHIP inverse from observed
step medians to nominal linear values, then linearises A, B and R before any
FFT.  Non-finite, non-strict or out-of-range calibration refuses the arm.
The scored edge never estimates its own tone map.

## Gaussian-equivalent comparative scale

For the five bins with centres `f_b` from 0.205 through 0.245, let

```text
y_b = median_site(log(D_b)) + log(U_b) + 2 log(f_b)
x_b = f_b^2 .
```

For a Gaussian-blurred step in white noise, multiplication by the independently
measured noise profile and `f^2` removes noise amplitude, bin population and
step-spectrum scale, leaving slope `beta = -4*pi^2*sigma^2`.  The candidate
reports only

```text
Q_GES = 2*pi / sqrt(-beta),
```

which is proportional to inverse Gaussian width.  `beta >= 0`, a non-positive
`D_b`, or fewer than 58/64 finite sites in any bin is an explicit refusal.
No exponent, offset or scale is fitted to score outcomes.

Two slope estimators are frozen:

* `OLS`: ordinary least squares with intercept over the five `(x_b,y_b)`
  points;
* `TS`: the median of all ten pairwise slopes.

## Angle estimator

The angle-aware variants average the 64 independent references, Gaussian
smooth with sigma 1, and form the global gradient structure tensor on the
central 224x224 crop.  The principal gradient angle is folded to the nearest
axis in `[0,45]` degrees.  The candidate accepts `[2,10]` degrees inclusive,
reports its measured angle, and refuses everything else.  It is never given
the planted angle or arm name.

## Frozen variant family

Every row is run and reported even after failure; no ensemble or post-outcome
selection is allowed.

| ID | score | floor / eligibility | ramp inverse | angle gate |
|---|---|---|---|---|
| `C0_NATIVE_MIN` | median native `S_25` | no / no | no | no |
| `V1_FLOOR_ELIG_MIN` | median floored `S_25` | yes / yes | no | no |
| `V2_GES_OLS` | `Q_GES`, OLS | yes / yes | no | no |
| `V3_RAMP_GES_OLS` | `Q_GES`, OLS | yes / yes | yes | no |
| `V4_RAMP_GES_OLS_ANGLE` | `Q_GES`, OLS | yes / yes | yes | yes |
| `V5_RAMP_GES_TS_ANGLE` | `Q_GES`, Theil-Sen | yes / yes | yes | yes |

`C0` is a historical control, not eligible for admission.  V1 isolates whether
the formal floor/eligibility lever alone fixes the observed failures.  V2
isolates the noise-profile/spectral-shape conversion.  V3 adds tone
linearisation.  V4 adds the angle gate.  V5 is a preregistered robust slope
alternative, not a fallback chosen after V4 is seen.

## Frozen score battery

Signal and transforms are unchanged:

| arm | plant |
|---|---|
| base | sigma-1.50 Gaussian edge, 5 degrees |
| identity | exact copy |
| blur | independent sigma-0.75 convolution |
| real improvement | independently sampled sigma-1.20 edge |
| USM | unclipped float, radius 1.00, amount 0.50 |
| tone | affine `1.7*x+0.13`, gamma 3, logistic slope 10 |
| noise | second independent sd-0.02 realisation, seeds `2026090300..0323` |
| angle | 0.5, 1, 5 and 12 degrees |

For site `s`, base A/B/R noise comes from
`SeedSequence([2026092000,s,role])`.  Blur and improvement change the clean A/B
signal before adding the same paired noise; R stays independent and fixed.
USM filters complete noisy A/B renders but not R.  Point tone is common to
A/B/R and the ramp witness.  Noise challenge `j` uses
`SeedSequence([2026090300+j,s,role])` for its second independent A/B
realisation.  Angle arms use the same site noise and an independent reference
at the planted geometry.

Rule 9 controls run before these arms.  Constant-0.5 flat A/B/R sites are
measured both untouched and after the same USM.  Every admission-eligible
variant must refuse both through source-only flat eligibility; returning a
favourable number is RED.

## Unchanged acceptance predicates

For each candidate's native score:

1. identity movement `<=1e-12`;
2. blur/base equals `0.8944271909999159` within 5%;
3. improvement/base equals `1.25` within 5%;
4. USM/base is at most `1.01`;
5. affine, gamma-3 and logistic movement is at most 1%;
6. 24/24 noise readings exist, median movement is at most 3%, and every
   reading moves at most 5%; and
7. 5 degrees is numeric and recovered within 0.2 degrees, while 0.5, 1 and
   12 degrees are explicit refusals.

Admission additionally requires all floor, eligibility, flat, provenance,
completeness and determinism controls.  `C0` cannot be admitted by definition.
One passing preregistered variant yields
`COMPARATIVE_ADMISSIBLE_ON_FROZEN_BATTERY`, not physical resolution, a
competitive win or formal M1.  Otherwise the verdict is
`NO_ADMISSIBLE_S25_VARIANT`.

## Checker independence and power

The checker imports no fixture, variant, adapter or candidate code.  It runs
measurement as a child process and compares JSON only with the literal
predicates above.  Before score measurement it must pass an all-GREEN literal
fixture and catch single-property mutations for at least:

* identity, blur, improvement, USM and each tone family;
* noise median and one worst-case noise reading;
* missing 5-degree recovery and accept-all angle logic;
* MTF50 relabelling;
* zero/ignored floor, flat admission, point-only eligibility and source drift;
* missing variant, omitted arm, omitted noise row, zero/non-finite base and
  survivor-only output.

The complete child measurement runs twice and the parsed JSON must be exactly
equal.  Scientifically negative outcomes still exit zero; harness,
provenance, completeness or nondeterminism failures do not.

No result JSON is written.  Complete machine-readable results go to stdout and
the report records every registered row.

