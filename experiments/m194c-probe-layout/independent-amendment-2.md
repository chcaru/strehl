# Correct the harness lifecycle and NaN boundary

2026-09-07, after independent-run-2. The root's fixed40 matrix is active at
writing; no compiled source is changed until its terminal record is announced.

The additive checkerboard also failed the finite-floor power check in both
gather processes. This disproved the adequacy of the first diagnostic argument.
**Withdraw the attenuation attribution in amendment1.** It was not measured.
The actual source/API error is that the independent harness did not call
FrameWorkspace::next_frame() before each BandMerge::add_frame_with_gain().
PlaneCache::ensure therefore kept frame0's colour pyramids while weights were
computed from later luma. Changed weights were accumulating the same cached
signal. Production BandWorker::fold explicitly calls next_frame; this is a
verification-harness mistake, not a product traversal defect. Curie independently
confirmed the missing lifecycle call from the two source paths.

The second scope error is that BandMerge::beta_for returns a supplied beta[k]
without a finite check. The production BandWorker retains only the finite prefix
of Probe::last() before it calls BandMerge. Directly supplying a raw NaN slice
does not exercise that production caller contract. Prior claims that the core
itself falls back to white for raw NaN are withdrawn. The ordinary length
fallback (None/empty slice) remains a legitimate component assertion.

Correction fixed prospectively: retain the old sinusoid/omitted-reset harness
as the same named expected-failure control. Call next_frame in the additive
checkerboard arm only. Change no dimensions, samples, transforms, thresholds,
or noise coefficients. Check None==empty, while raw NaN is explicitly labelled
a core fault injection and must produce the same mean as the huge finite floor,
different from the ordinary selecting arm. Retain the previously fixed mean
and non-mean assertions. Production finite-prefix conversion is a source-derived
contract, not an independently injected end-to-end NaN claim. The actual tiny
empty Probe and direct pooling/NaN tests keep their existing narrow scope.

Both failed full runs, their exact source hashes and full logs are retained.
Independent-artifacts-2 separately decodes all48 actual delivered TIFFs from
run2 and passes the layout, active-site/model/warp/WB power and on/off/placebo
byte+pixel comparisons. Those measured groups do not depend on the flawed
direct BandMerge harness. If the corrected lifecycle still fails, stop this
component investigation; do not add another fixture or tune parameters.
