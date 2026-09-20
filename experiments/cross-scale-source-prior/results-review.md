# Independent outcome review: fixed coarse-source prior

**MEASURED, rejected at both ISO100 and ISO400.** The two tests completed, but
the fixed photographic qualification did not pass. This is an exercised image
failure as well as an unexercised proposed positive. It does not license a full
render under the preregistered gate, a production change, or threshold/window
adjustment. No new run or source edit was made for this review.

Root ran the frozen test executable with:

```text
experiments/cross-scale-source-prior/build-1/cli-tests.exe merge_cmd::cross_scale_source_prior::independent_controls:: --nocapture --test-threads=1
```

[Completion](controls-1/completion.json) records two passing instrument tests,
unchanged bound sources, 2.907 seconds wall time, and
`photographic_replay_admitted=false`. The reviewed
[screen](controls-1/output/screen.json) SHA256 is
`a63516111176f8b68a2f3d433ca596f672ea0a02823f71e298c92be546ee9144`;
the executable SHA256 is
`894c34700759ece4efc8368161c8ea5da43a846b6d054ca2dcbafa886d14861a`.
The [independent plan](independent-plan.md) remains unchanged. Errors below are
truth-error RMS in the existing normalized WB camera-RGB domain, not sensor DN
or calibrated noise significance. “Whole” means the fixed supported native
interior [38,42]–[280,244], not a complete photograph.

## The contact gain is real, but the intended outside-spill positive is absent

The baseline outside-window RMS exceeds twice the same-ISO flat RMS at both
ISOs. The known defocused source also has ample spill error. The failing
liveness term is specifically the baseline's **signed bright excess**, not
RMS, component recovery, weight activation, or a lack of blur in the inputs.

| Fixed contact quantity | ISO100 | ISO400 |
| --- | ---: | ---: |
| Flat RGB RMS | .001109891 | .002220783 |
| Baseline outside RGB RMS | .007118779 | .007689727 |
| Baseline mean signed RGB excess outside | +.000485772 | +.000585745 |
| Candidate mean signed RGB excess outside | −.001758123 | −.001627585 |
| Known defocused source outside RGB RMS | .073608745 | .073608745 |
| Candidate / baseline outside RGB RMS | .99252 | .98861 |
| Candidate / baseline outside chroma RMS | 1.04224 | 1.03811 |
| Candidate / baseline interior RGB RMS | .35030 | .40292 |
| Candidate / baseline edge RGB RMS | .63410 | .66816 |
| Candidate / baseline whole RGB RMS | .86776 | .89192 |

**DERIVED interpretation:** the signed baseline excess is below even one flat
RMS, so the frozen bright-spill liveness requirement fails although both
greater-than-two-flat RMS conditions pass. Structure and colour errors can
produce a large RMS without a large positive brightness bias. A spread-out
source is present; the canonical consumer does not retain the required signed
outside defect. The candidate crosses to negative bias and misses the required
5% outside RGB improvement. It cannot be described as a qualified repair of
that defect.

The interior/edge gains should nevertheless be retained as genuine measured
effects. All three interior component recoveries rise: approximately
.820/.891/.827 to .912/.948/.892 at ISO100, and .819/.886/.823 to
.912/.944/.890 at ISO400. These gains cannot substitute for the missing
outside positive or cancel failures on other inputs.

## A live counterexample loses genuine coarse colour structure

The near-fine/far-coarse case exercises the intended prior and rejects it
without relying on the contact liveness condition. Its joint regression fits
both independent truth templates plus an intercept, retaining their
cross-covariance; increased near detail cannot conceal the far loss.

| Quantity | ISO100 | ISO400 |
| --- | ---: | ---: |
| Whole RGB error ratio | 2.45095 | 2.44083 |
| Whole chroma error ratio | 2.36913 | 2.37033 |
| Baseline near recovery, R/G/B | .536/.569/.547 | .541/.570/.553 |
| Candidate near recovery, R/G/B | .827/.914/.850 | .828/.914/.848 |
| Baseline far recovery, R/G/B | .765/.784/.772 | .765/.784/.773 |
| Candidate far recovery, R/G/B | .220/.220/.218 | .219/.219/.218 |

The far component retains roughly 28% of baseline, losing about 72%; both
baseline and candidate are below truth, so this is not an artefact of capping
overcontrast. The live forced-coarse-source0 destroyer yields far recoveries
near .217 and almost the same whole RGB error (.05113/.05126, versus the
candidate's .05096/.05112). This supports the expected wrong-source mechanism;
it does not establish that their weight fields are identical. Both baseline
and candidate have zero mean-fallback fraction in every AC band on this case.
The loss therefore does not arise from switching those bands to their mean.

**ARGUED:** transparent superposition is a concrete failure of universal
cross-scale source agreement, not proof that every opaque chip contact must
behave identically. It is nonetheless the preregistered live counterexample,
and the separate glint failures below prevent dismissing all damage as unique
to transparent superposition.

## Whole-window averages hide additional local damage

| Candidate / baseline error | ISO100 | ISO400 |
| --- | ---: | ---: |
| Neutral glint extension RGB | 1.22097 | 1.13012 |
| Neutral glint core RGB | 1.11707 | 1.09543 |
| Chromatic glint extension RGB | 1.22990 | 1.14991 |
| Chromatic glint extension chroma | 1.14131 | 1.09675 |
| Chromatic glint core chroma | 1.09912 | 1.07560 |

The glint whole-window RGB ratios remain only 1.004–1.008, within the whole
guard, while local core/extension guards fail. The neighbouring true texture
and depth-edge guards pass. This is spatially concentrated harm, not universal
degradation. Glint core template coefficients can exceed one in both outputs;
truth-capped component retention cannot diagnose that overshoot. The separate
local RGB/chroma errors supply the necessary rejection.

Flat RGB/chroma ratios remain approximately one at both ISOs. This is not
literal prior-output identity: 1096/1092 coarse weights change and tiny f32
output differences remain. The true coloured radial case passes, with local
RGB ratios .99070/.99557 and chroma ratios .97562/.98210, alongside increased
component recovery. Neither result offsets the exercised adverse cases.

## What the exact held-state controls do and do not establish

The operator oracle, mixed unsupported contributions, incorrect-normalization
destroyer, source/replay hashes, exact Off/Neutral outputs, and live wrong-donor
control all pass. The private accumulator comparison confirms identical finest
weighted state, unweighted fallback sums, terminal base, and hull bounds.
The actual altered coarse weights and output are live.

Identical finest coefficients do **not** imply identical visible fine
components. The production Laplacian bands are not disjoint ideal frequency
partitions. Changing coarse AC contributions changes their collapsed image
and can change the regression against a physical fine texture. Holding the
hull bounds also does not hold which reconstructed samples reach those bounds;
MHC subsequently consumes the changed CFA image. No new stage-isolation
experiment was run, so the relative contributions of collapse, clipping and
demosaic are not assigned here. The observed rise in near-fine recovery is
compatible with, rather than a contradiction of, exact finest accumulator
identity.

These generated plants exercise the injected camera model and actual rounded
GPU consumer, not noise calibration or a real optical capture. Two ISO settings
are two noise conditions on the same fixed scene/geometry, not independent
photographic replication. RMS can reward smoothing; template projection can
miss non-template errors and overshoot. Flat, local colour error, and absolute
component recovery must be read together. On that combined evidence the fixed
general recipe is rejected; no full-image gain has been measured by this run.
