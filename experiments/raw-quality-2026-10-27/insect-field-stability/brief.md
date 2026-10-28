# One fixed measured-field stability discriminator

Root release, 2026-10-27. This follows the complete insect-placement-observer,
its unchanged full299 map, conditional footprint census, and independent
photographic nomination of tiles15,41,56. No signed per-site result has been
inspected to select this hypothesis. This test can identify a predictable
matcher pattern, not its physical cause. It does not modify alignment or render
a photograph, and cannot admit image quality.

## Prior and changed question

Root ran unified search for sliding pair / held field / defocus bias and the
mechanical search `sliding pair defocus field`. Read M6's sliding-pair amendment
and the preceding observer's full independent review. M6 showed why a fixed
reference confounds defocus and depth; M97b's uniform-blur counterexample and
M103's consumer-gauge/curvature requirement still apply. The new evidence is
the actual current299-source tile population and conditional overlap, not a
new claim that those old failures vanished. Short-span discard is prohibited;
this diagnostic changes no measurement or solver population.

## Frozen hypothesis and population

For each of the three fixed sites, one two-component vector v describes the
measured final-similarity residual per bracket step: r(i,j)= (j-i)*v. Frame
ordinal is a bracket coordinate, not depth. No radial centre, richer spatial
basis, optical metadata coefficient, temporal spline or learned warp is fitted.
This is a deliberately narrow stationarity hypothesis. Its failure does not
disprove focus-dependent geometry generally.

Use all correlated original observations at tiles15,41,56, retaining MAD flags.
Train on span8 pairs whose TWO sources are in[0,95]. Fit v as the arithmetic
mean of each observed signed residual divided by8. No selection by direction,
size, peak, outlier status or quality score. The existing summary CSV's f64
measured-minus-saved-fit vectors are the target, in source-i-to-j guide pixels.
Do not call them original-sensel displacement truth or newly retained vectors.
Do not use the held global map as a predictive amplitude or normalize by a
scale estimated from all acquisitions. Its role remains conditional support.

Primary held sources are[112,207]; replication held sources[224,298]. Each
pair must have BOTH sources inside its interval. There must be no original
capture shared between training and either held interval or between the held
intervals. Primary scored spans are1 and8 at every site. Span32 is retained as
an adverse readout with every correlated/refused status counted. Cross-boundary
and unused-gap pairs are retained in the census but never silently assigned to
another arm. No replacement sites, splits, spans or threshold adjustment after
inspection. Missing primary population must refuse, not delete hard cases.

The null predicts zero residual. Report signed v, squared-error reduction versus
zero, residual means/scatter and complete counts separately per site/span/held
interval. The fixed stability gate requires at least20percent lower MSE than
zero at every site for spans1 and8 in BOTH held intervals. A zero-null energy
means no affirmative evidence, not infinite improvement. Also report deltas in
consecutive16-source subblocks of each held interval, using only pairs fully
inside each block (last short block explicit). These subblocks describe shared
source dependence; no row-count-based p-value, IID confidence claim or camera
noise calibration is allowed. The headline gate remains the complete declared
held population, not a selected set of blocks.

The score can be fooled by persistent defocus-sensitive matching bias. A stable
result licenses only a bounded original-structure check, not a correction.
An unstable result closes this exact per-step hypothesis without a larger basis
or new crop/span search under this allocation.

## Independent controls and ownership

- cfa-residual owns `analyze.py`: small callable fit/score functions and strict
  saved-observation loader/receipts. Bind complete observer, summary and support
  jobs; emit every population/status and preserve inputs. No RAW reads or fits
  beyond the declared six scalar coefficients.
- photo-review owns `controls.py` and independent results. First exercise
  zero/noise residuals and a known stable per-step vector field with shared
  per-acquisition noise plus independent pair noise; fresh known noise is not a
  fitted camera model. A held sign reversal, wrong site or wrong span must fail
  through the same scorer. Exercise acquisition-overlap rejection. Freeze exact
  seeds/vectors/noise before execution. A persistent-bias lookalike may pass,
  but physical attribution must remain false; demonstrate this limitation.
- integration-review owns `source-review.md`, challenging stationarity,
  coordinate quantity, training leakage, missing data and the meaning of the
  gate. Raise concrete issues before source freeze; do not expand the model.
- root owns `run.py`, source freeze, one generated control job and one saved-data
  job, independent result dispatch and any later direction choice.

No author launches numerical jobs. Root uses one worker,120s wall/120CPU seconds/
4GiB commitment per job, fresh output directories and the existing owned-job
helper. Generated controls must finish before actual evaluation. This is not
an image-sharpness test; no synthetic score satisfies the photographic goal.
