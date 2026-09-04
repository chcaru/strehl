# M131 Candidate 2 ruling — pre-results protocol

**Status: FROZEN before M131 opened any capture RAW or ran any Candidate 2
measurement.**

## Question and decision rule

The only program decision is whether the already-defined Candidate 2 clears
scorecard blocker `(a)`, “missing admissible detail instrument.”

Candidate 2 clears only if all of the following hold:

1. its synthetic optical-direction result survives independent choice audits;
2. its estimand can lawfully compare the natural dense and sparse outputs
   without deriving target labels or truth from those outputs;
3. the proposed existing-capture arm supplies the registered target,
   covariance, derivative, test, replication, geometry, and no-target
   controls; and
4. it satisfies the frozen M55 detail-metric acceptance contract without
   changing that contract or changing Candidate 2's estimand.

Failure or non-instantiability of any clause means **DOES NOT CLEAR**. A
development result, an uncommissioned successor, or a task-specific claim that
the scorecard has not admitted does not clear `(a)`.

## Ordered work

### 0. Rule-40 prior art

Run the repository prior-art command exactly as dispatched and name every
report it returns. Read the required Candidate 2, M46, M55, M57, M92, and M95
reports before interpreting a result.

### 1. Flat/no-target control — first measurement

This runs before any M131 RAW decode or optical re-score.

- Use the frozen Candidate 2 dimension, folds, covariance estimator, and
  independent covariance/derivative/test streams.
- Use spatially constant backgrounds.
- Set the physical target amplitude to exactly zero while retaining independent
  noise draws and the nominal `+`/`-` labels.
- Repeat enough independent seeds to report the mean and standard error of the
  null `d'^2`.
- **Pass:** a typed `NO_TARGET`/inadmissible refusal, or an explicitly
  null-calibrated result that cannot be read as positive detail.
- **Failing input:** the zero-target data above.
- **Power input:** the same flat backgrounds with the registered nonzero
  target restored must produce a materially larger reading.
- **Planted wrong answer:** mutate the checker to accept a numeric zero-target
  reading; the checker must reject the mutation.

A positive finite `d'^2` with status `NUMERIC` on zero-target data fails this
control even if its expectation is small. Candidate 2's failure direction here
is upward: finite-sample label separation can be credited as detail.

### 2. M55 acceptance battery

Apply M55's executable B0 contract to Candidate 2 as shipped, without an
adapter that invents `value(a,b,ctx)`. Then classify B1–B9 as runnable,
failed, or not instantiable under the frozen Candidate 2 inputs.

- **Failing input:** an object that exposes Candidate 2's actual observation-set
  interface but lacks the M55 natural-render pairwise contract.
- **Power check:** run M55's existing known-bad and passability self-tests, if
  available, to show the battery can reject and admit.
- No field, threshold, task label, zero-target population, or comparison
  function may be added merely to make the battery run. Such an adapter would
  be a successor instrument.

Candidate 2's failure direction under a naive dense/sparse class adapter is
either direction: any stable cross-capture difference can increase
detectability, regardless of whether it is detail, density, IBIS, geometry,
tone, or exposure.

### 3. Synthetic optical choice audit

Verify the frozen artifacts and independently re-score their stored held-out
arrays. Re-choose, rather than merely recompute, these defensible choices:

- native versus display-referred values;
- arithmetic mean, median, and minimum across the four registered tasks;
- acquisition-block jackknife versus the frozen block bootstrap;
- complete sites versus predeclared balanced macro subsets; and
- an independent same-optics/noise realization as the null, reported with its
  standard error.

The optical arms fail if blur is not below unity or improvement is not above
unity under a defensible choice. Their known fooling direction is model
dependence: a plant that filters only its supplied target while redrawing noise
can force the registered direction without establishing transfer to captures.

### 4. Existing-capture admissibility and confounds

Before opening any RAW, test whether the stacks can instantiate Candidate 2's
registered physical task. If they cannot, no Candidate 2 score will be taken.
Existing image-derived geometry evidence may still be audited.

The following are separate gates:

1. **Task/stream gate:** fixed physical `+theta/-theta` alternatives,
   independent zero-target covariance observations, separate derivative and
   held-out observations, and five acquisition blocks must exist without
   relabelling dense/sparse outputs as target classes.
2. **Coverage gate:** any claimed common interval or 64 interior focus peaks
   must come from image data, never the coarse EXIF focus encoder.
3. **Tail gate:** the `26/14` tail mismatch is a real asymmetry. If the dense
   arm ends earlier or misses target peaks, its bias is downward; if endpoints
   or physical steps differ in another way, the sign is indeterminate.
4. **IBIS/geometry gate:** cross-capture sensor motion must be bounded by
   input-only geometry. A fitted scored-detail warp is forbidden. A
   within-capture full-versus-subset arm may diagnose density but cannot by
   itself remove the cross-capture confound.

The real arm is admissible only if all four gates pass. Otherwise its result is
`UNCOMMISSIONED`, not evidence for or against natural-image detail.

### 5. Ruling

The report will distinguish:

- what Candidate 2 measured on its synthetic task;
- what a Hotelling task observer can license in principle;
- what the existing captures can instantiate;
- what M55 accepted or rejected; and
- what remains unestablished.

No threshold or interpretation will be changed after a result is seen.
