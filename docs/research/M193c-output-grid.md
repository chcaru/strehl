# M193c: native output coordinates and complementary-focus coverage

**IN PROGRESS.** The process controls and test build are complete. Private image
coordinates, RAW derivatives and real registration coverage remain unmeasured
in this milestone. HardFloor remains the default; no quality promotion follows
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
Those are prepared instruments, not yet geometric findings. Their fixed
45 controls must run before all ten private outputs can be admitted.

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

Final control result SHA256:
`39a6f6e93e3b8df83834ab4046c7f30d6f42612df0cb0ec57ea158815baa7cfd`.
Build 2 result SHA256:
`05154982aefcab418427c5311fb27ea499a42f1a1c6e9f714d9c46cb8e45c907`.

## Next decisions

Finish the independently reviewed encompassing private campaign. It owns one
600 CPU second / 1200 wall second / 128 MiB artifact allowance across the grid
producer, independent reader and two derivative fixtures. Local child samples
cannot reset that allowance. Failed children retain their partial artifacts
and original cause; a stale positive receipt cannot override a nonzero exit.

If the private geometry and derivative checks pass, decode the nine fixed
non-holdout coffee-bean inputs with one live workspace snapshot at a time and
an independent active-RAW reader before admitting each derivative. Then apply
the frozen input registrar. A first registration failure leaves later frames
unvisited and informs the next direct-pair alignment experiment. It is not
permission to fabricate a complete placement track or tune a quality score.
