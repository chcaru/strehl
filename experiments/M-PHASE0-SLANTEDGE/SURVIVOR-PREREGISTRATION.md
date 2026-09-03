# M-PHASE0-SLANTEDGE — survivor audit preregistration

Status: **frozen before this lane measured either candidate on its plants**.

## Question

Two non-MTF statistics have survived controls that defeated slanted-edge
MTF50:

1. `experiments/SCORECARD-BASELINE/common.py::m1_tile`, with native outputs
   `f_licensed` and `S_25`; and
2. V-HEADTOHEAD3's ordinal statistic.  The current licensed implementation is
   `experiments/V-HEADTOHEAD3/sharpening_core.py::q25`.  The historical
   `ordinal.py::ordinal_shares()[3]` value that produced the original
   head-to-head result is retained as a diagnostic because its denominator
   imports bands above 0.25.

The decisive question is whether sharpening invariance coexists with response
to real blur and real improvement.  A statistic that is unchanged by USM and
also unchanged by both physical arms is blind, not sharpening-safe evidence.

## Frozen candidates and provenance

The candidate trees are read-only.  Only the functions needed for measurement
are copied verbatim into this experiment.  The adapter imports those owned
copies, never live code.  A separate provenance process reads the following
repository-relative files, checks their LF-normalised SHA-256, and requires the
vendored function ASTs to equal the live function ASTs:

| source | LF-normalised SHA-256 |
|---|---|
| `experiments/SCORECARD-BASELINE/common.py` | `dff25996f1b4c055f5740e0fbd29b2e9ee848eaca7d5207dcb12f08e78d5ea45` |
| `experiments/V-HEADTOHEAD3/ordinal.py` | `8f27f44ae317880ca6bad2bc3fda9de03c9ca728dbb2432c91a92d896f27355f` |
| `experiments/V-HEADTOHEAD3/sharpening_core.py` | `0ea758cba1be5506ab370e9e7205ff0354ed63288e4d9c319e8bdb8389bc798d` |

Source drift or any AST mismatch stops the run.  Candidate synthetic helpers,
commissioning fixtures, thresholds and output files are forbidden inputs.

## Frozen plants

All constants, transforms and seeds are unchanged from
`PREREGISTRATION.md`:

| arm | plant |
|---|---|
| base | Gaussian edge sigma 1.50 native px |
| identity | byte copy |
| blur | independent Gaussian convolution sigma 0.75 px |
| real improvement | independently sampled sigma 1.20 px edge |
| sharpening | unclipped float USM, radius 1.00 px, amount 0.50 |
| tone | affine `1.7*x+0.13`, gamma 3, logistic slope 10 |
| noise | 24 seeds `2026090300..2026090323`, sd 0.02 |
| angle | 0.5, 1, 5 and 12 degrees |
| licence | sigma 0.60, whose physical MTF50 is above 0.25 |

M1 requires equal square repeats and a reference, so the adapter uses a
256x256 version of the same 5-degree edge.  For each frozen seed it draws
independent A, B and reference noise.  Blur and real improvement change the
clean A/B signal, then receive the same paired noise; the independent base
reference is unchanged.  USM operates on the complete noisy A/B renders, not
the reference.  Each tone map is applied commonly to A, B and the reference.
The noise arm adds a second independent sd-0.02 realisation to A/B.  Results
are medians over the 24 seeds, with every noise reading retained.

Q25 and historical A20-25 consume the noise-free 256x256 frozen image arms
directly.  The noise arm uses the same 24 seeds.  No candidate helper creates
or transforms a plant.

## Unchanged bars and native units

Neither candidate reports MTF50.  Their values remain named `f_licensed`,
`S_25`, `Q25` and `A20_25`; no adapter may relabel or fit them to MTF50.
The absolute MTF50 anchors are therefore `UNSUPPORTED`, never silently passed.
The existing dimensionless ratio bars are applied unchanged as a deliberately
strict compatibility test:

1. identity movement at most `1e-12`;
2. blur/base `0.8944271909999159`, within 5%;
3. improvement/base `1.25`, within 5%;
4. USM/base at most `1.01`, unless explicitly refused as sharpening;
5. affine, gamma-3 and logistic movement at most 1%;
6. all 24 noise ratios within 5%, median within 3%;
7. accept and recover 5 degrees within 0.2 degrees; refuse 0.5, 1 and
   12 degrees; and
8. the sigma-0.60 arm emits exactly `UNLICENSED_GT_0.25`.

The angle and sentinel bars can pass only from candidate-native output.  The
adapter may record values by angle and frequency scope, but may not manufacture
an angle estimate, refusal or sentinel from the known plant label.  Structural
licensed-band exclusion is reported separately from the exact sentinel bar.

Per native field:

* `USM_VULNERABLE` — USM rises by more than 1%;
* `USM_INVARIANT_AND_QUANTITATIVELY_RESPONSIVE` — USM passes and both physical
  ratios pass;
* `USM_INVARIANT_BUT_BLIND` — USM passes and both physical arms equal identity
  within `1e-12`; or
* `USM_INVARIANT_BUT_UNCALIBRATED` — USM passes but neither preceding response
  classification applies.

No candidate is admitted by the full frozen battery unless every bar passes.
A narrower survivor classification does not establish formal scorecard M1,
physical resolution, or a real-capture win.

## Checker power

The independent checker imports no generator, adapter or candidate.  Before
measurement it must pass a literal all-GREEN native-score fixture and catch at
least these single-property sabotages: identity, blur, improvement,
sharpening, tone, noise, angle, licensing, source drift and MTF50 relabelling.
Any miss stops the run.

