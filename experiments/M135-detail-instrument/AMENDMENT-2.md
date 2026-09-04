# M135 commissioning amendment 2

Status: **FROZEN BEFORE REPLACEMENT OUTCOME GENERATION**

The corrected second execution produced `commission-run2-superseded.json` and
passed the frozen battery. A subsequent design audit found that C15's repeated
constant template is only one periodic-target failure. A periodic target with
varied phase can retain full covariance rank and repeat coherence while still
being predictable. No image statistic can prove that a target was unknown to
the renderer from the rendered pixels themselves.

The same audit made the fixed-pattern boundary executable. A shared sensor
pattern in both the output and reference can make a physically flat field look
informative unless the independent calibration lineage rejects it.

This amendment tightens the complete certificate without changing any numeric
threshold:

1. `CaptureSet` carries target lineage. Only a frozen nonperiodic-random target
   is eligible. A periodic target returns `PREDICTABLE_TARGET` before scoring.
2. C15 now requires `PREDICTABLE_TARGET` in 128/128 populations rather than
   relying on the weaker covariance failure of one repeated template.
3. C19b adds a physically flat, shared-fixed-pattern plant. With the registered
   blank-residual correlation of `0.20`, it must return `SHARED_REFERENCE`.
4. The same C19b plant is also evaluated with its lineage witness deliberately
   disabled. That diagnostic is expected to produce a false numeric reading
   and is retained to expose, rather than hide, the instrument's structural
   dependence on independent calibration and sensor-coordinate decorrelation.

The first run remains invalid for its C14/C15 repetition error. The second run
is valid under the original battery but superseded by this stricter battery.
The third run may begin only after this amendment and source are committed.
