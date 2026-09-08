# M193c: native output coordinates and complementary-focus coverage

**IN PROGRESS.** Private attempt2 passed all ten coordinate cases and both
conversion fixtures, and its complete execution evidence has passed independent
inspection. The earlier failed attempt is preserved. Native RAW derivatives
and real registration coverage remain unmeasured in this milestone.
HardFloor remains the default; no quality promotion follows
from this work. The [charter](../../experiments/m193c-output-grid/charter.md)
names the actual sampling-coordinate consumer and the fixed historical inputs.

## Current evidence

**MEASURED, independently inspected:** the final eleven Windows process controls
passed from source commit `e1488da8`. They exercise ordinary success, explicit
failure, exact and overflowing logs, direct and nested timeouts, allowed and
refused allocations, late log-binding failure, changed input and restoration.
The independent review retains the scope: owned process cleanup and operational
rejection, not an RSS measurement or a no-overshoot guarantee.

The first two control attempts remain failed. The first nested-child fixture
did not observe its child's startup marker. The second passed the repaired
nested fixture but rejected the combination of a child allocation refusal and
the parent's committed-memory refusal. The final revision added a successful
allocation companion and explicitly admitted those named refusal routes. No
previous result was rewritten.

**MEASURED:** the first Rust build reached `Compiling strehl-cli` and failed
with E0432: the private adapter imported `NoiseProvenance`, while the owned
module exports `Provenance`. The reviewed one-line import alias preserves the
existing noise coefficients. The second build, frozen at `7b861935`, completed
with actual compiler exit 0 and all four M193c ignored tests in its listing.
It has not executed those tests. The copied executable is 29,488,640 bytes,
SHA256 `8ecf5dfbb9270eef5ab99a9306bd1edb8cd0180e6128e86ad1bb18420b09b0e1`,
with software stamp `strehl 0.0.0 (7b8619351f74)`.

The independently authored reader uses analytic corner intersections and
explicit native inverse transforms. A separate component compares independently
reconstructed MHC/Catmull samples with actual Rust kernel and warp values.
Their fixed 45 controls now pass in private attempt2 before admission of all
ten private outputs; the finite synthetic scope is reported below.

**MEASURED, independently inspected:** private attempt 1, frozen at `f9ee06a4`,
returned actual outer exit 1 after 4.9988203 wall seconds. The first Rust plan
test returned 0 with one test passed and saved a 9,824-byte plan. Its enclosing
helper then rejected an active-process observation immediately after direct
exit and pipe EOF. The original nonzero observation was overwritten during
cleanup, so the retained record cannot distinguish natural shutdown from an
explicit cleanup termination. The final termination counter counts limit
violations; its zero value cannot supply that missing observation. The
[independent read](../../experiments/m193c-output-grid/independent-private-campaign-1-read.md)
preserves this uncertainty and the actual chain of refusals.

This attempt produced zero TIFFs and ran no precision component, independent
image reader, derivative or RAW operation. No admission gate exists. Actual
encompassing child CPU plus owner CPU was 4.890625 seconds; the observation is
operational accounting, not a performance result. The prospective repair keeps
the original resource limits while observing the owned process tree through
completion, retains the first shutdown observation and explicit termination
attempts, and adds a delayed-descendant success/refusal/restoration group to
the unchanged eleven process controls. It needs its own execution and a new
build before another private attempt, since the build source closure includes
the process helper. No image bar or image population changes.

**MEASURED, independently inspected:** controls4, frozen at `4339bdaa`, passed
all fourteen cases with actual outer exit 0. Both delayed-descendant companions
observed positive Job activity after direct exit and EOF, reached their saved
completion markers, and completed without a termination attempt. The persistent
descendant retained positive activity until the original five-second wall
refusal, then explicit owned termination reached zero active processes. The
original eleven controls also passed. The
[independent read](../../experiments/m193c-output-grid/controller-controls-4-independent-read.md)
binds the actual identities, complete artifacts and limits; it does not identify
the shutdown mechanism in the earlier failed private attempt.

**MEASURED, independently inspected:** build3, frozen at `43a72446`,
returned actual outer and compiler exit 0 with a fresh `Compiling strehl-cli`
line and all four ignored entry points listed. The copied executable is
29,488,640 bytes, SHA256
`fa03b12fe177608851d6758517c9bda050998cdc4d777195fab8e3dc1e0813a3`,
software stamp `strehl 0.0.0 (43a72446c2c7)`. The
[independent build read](../../experiments/m193c-output-grid/bridge-build-3-independent-read.md)
confirmed its source, artifact, listing and process associations. No test was
executed by the build.

**MEASURED, independently inspected:** private attempt2, frozen at `3090dc0c`,
returned actual outer exit 0 and `PASS_M193C_PRIVATE_STAGE_ONLY`. All ten grid
products, 45 grid controls, 3712 fixed precision samples and two conversion
fixtures completed. The conversion stage passed 32 source and 41 independent
controls. Its two fixtures have zero measured maximum code error over their
54 and 660 declared sites, within the unchanged one-code allowance.

The [independent terminal read](../../experiments/m193c-output-grid/independent-private-campaign-2-read.md)
reconstructed the complete pixel streams of all twelve actual TIFFs, inspected
their actual launches and deciding records, and verified the source/input
chain. Correct-map cases meet the 0.1 native-pixel paired-coordinate bar in
their named reference; deliberate swapped/inverse maps agree with their fault
oracle and disagree with the correct map. The constant fixture is explicitly
rank zero and supplies no coordinate inverse. Off/count/placebo outputs are
byte-identical with live hooks. These are finite coordinate and conversion
checks, not preserved-detail, calibration or real-placement measurements.

Terminal work is 143.4375 CPU seconds: owner 2.4375 plus the encompassing Job
141, counted once. Outer wall is 135.3224576 seconds. All 194 retained files
total 14,761,297 bytes, matching this run's observed output high-water total;
this is not exact write-I/O accounting. The original 600 CPU / 1200 wall /
128 MiB private limits are unchanged. No RAW byte was read by this execution.
The actual result SHA256 is
`5c962797001d5e0fbc9ffd09605f6ad5d46c3e5a786d8a5e07e5f3ed5aa2de7e`.

## Reproduction and preserved attempts

Each release contains the complete actual argument array, input references and
source bindings. Replace only its named release-hash token with the digest of
that release. Output directories are exclusive and fresh; do not overwrite
these attempts when reproducing them.

| Attempt | Frozen source | Release | Terminal result |
| --- | --- | --- | --- |
| Process controls 1 | `5a727a12` | [release 1](../../experiments/m193c-output-grid/controller-controls-release-1.json) | [retained refusal](../../experiments/m193c-output-grid/controller-controls-1/result.json) |
| Process controls 2 | `3cfefcbf` | [release 2](../../experiments/m193c-output-grid/controller-controls-release-2.json) | [retained refusal](../../experiments/m193c-output-grid/controller-controls-2/result.json) |
| Process controls 3 | `e1488da8` | [release 3](../../experiments/m193c-output-grid/controller-controls-release-3.json) | [eleven controls passed](../../experiments/m193c-output-grid/controller-controls-3/result.json) |
| Test build 1 | `1e5e100a` | [build release 1](../../experiments/m193c-output-grid/bridge-build-release-1.json) | [retained compiler refusal](../../experiments/m193c-output-grid/bridge-build-1/result.json) |
| Test build 2 | `7b861935` | [build release 2](../../experiments/m193c-output-grid/bridge-build-release-2.json) | [compiled tests only](../../experiments/m193c-output-grid/bridge-build-2/result.json) |
| Private attempt 1 | `f9ee06a4` | [private release 1](../../experiments/m193c-output-grid/private-campaign-release-1.json) | [first-plan process refusal](../../experiments/m193c-output-grid/private-campaign-1/result.json) |
| Process controls 4 | `4339bdaa` | [control release 4](../../experiments/m193c-output-grid/controller-controls-release-4.json) | [fourteen controls passed](../../experiments/m193c-output-grid/controller-controls-4/result.json) |
| Test build 3 | `43a72446` | [build release 3](../../experiments/m193c-output-grid/bridge-build-release-3.json) | [compiled tests only](../../experiments/m193c-output-grid/bridge-build-3/result.json) |
| Private attempt 2 | `3090dc0c` | [private release 2](../../experiments/m193c-output-grid/private-campaign-release-2.json) | [private checks passed](../../experiments/m193c-output-grid/private-campaign-2/result.json) |

Final control result SHA256:
`39a6f6e93e3b8df83834ab4046c7f30d6f42612df0cb0ec57ea158815baa7cfd`.
Build 2 result SHA256:
`05154982aefcab418427c5311fb27ea499a42f1a1c6e9f714d9c46cb8e45c907`.

## Next decisions

Capture and bind the actual independent reader's dependency runtime using the
separately reviewed, bounded metadata-only command. Then decode the nine fixed
non-holdout coffee-bean inputs with one live workspace snapshot at a time and
an independent active-RAW reader before admitting each derivative. Then apply
the frozen input registrar. A first registration failure leaves later frames
unvisited and informs the next direct-pair alignment experiment. It is not
permission to fabricate a complete placement track or tune a quality score.
