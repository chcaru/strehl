# Prospective reference amendment: normalized Cartesian intervals

2026-09-07. **Design only; implementation and execution require root release.**
This changes the independent reference's quadrature parameterization, not the
continuous scene, scalar bars, original split locations or author renderer.
The original component refusal and its diagnostic remain immutable.

## Evidence and exact numerical change

The independently read diagnostic result `194dbdb0…` preserves all 96 original
off/count/placebo signatures. All 28 warned intervals terminate at -1 or +1
and span 5, 13 or 16 binary64 steps; their 63 queries revisit only 6, 14 or 17
coordinates. See `independent-interval-diagnostic-review.md` and its actual
artifact reader. These observations motivate a coordinate change. They do not
authorize suppressing warnings or treating a refused scalar as available.

Introduce `independent-normalized-interval.py`. Its scoped adapter replaces
only the loaded frozen M194e independent module's `quad` dependency during an
actual Cartesian render. Preserve that model file's bytes and its integrand,
clipping, break construction, sorted distinct intervals, summation, division by
pi, final indicator check and warning guard. Do not modify the independent
spatial-factor quadrature dependency or import the author's integrator/selector.

For each original call `quad(f,a,b,epsabs=e,epsrel=0,limit=128)`, require finite
`-1 <= a < b <= 1`, finite positive e, exactly epsrel 0 and limit 128, and
finite positive binary64 `w=b-a`. Call the captured original quadrature once
over `[0.0,1.0]`, with the **same** e, epsrel and limit. Its callback is exactly:

```text
require finite 0 <= u <= 1
if u == 0:       t = a
elif u == 1:     t = b
elif u <= 0.5:   t = a + w*u
else:           t = b - w*(1.0-u)
require finite a <= t <= b
v = f(t)
require finite v
weighted = w*v
require finite weighted
return weighted
```

All operations are ordinary Python binary64 in the written order; no fma,
extended-precision substitution, snapping or clipping. The explicit endpoint
branches preserve the supplied endpoint bits, including signed zero. The two
interior expressions are the same affine map in real arithmetic and choose
the nearer endpoint for its floating-point evaluation. Repeated represented t
values remain possible; normalization does not invent sub-ULP coordinates.

The returned value **and** error already have original integral units because
the Jacobian is inside the callback. Return both unchanged. Do not multiply
either by w again or divide/multiply e by w. The frozen requested value
`target_e*pi/number_of_original_intervals` remains intact. No full_output,
warning suppression, discarded interval, changed subdivision limit, analytic
replacement of near-tangent cells or wider target is allowed. Let original
warnings propagate into the existing refusal guard. Restore the dependency in
finally even after callback, quadrature or persistence failure; reject nested
installation. The adapter's live state is bounded counters, not frame arrays.

## Method and minimal receipt contract

Set row and engine method to **`m194g-independent-spatial-cache-v2`**. Envelope
schemas can remain structurally unchanged. Preserve the frozen Cartesian
receipt's method field as the identity of its underlying integrand, with the
new row method and this explicit normalization object identifying the changed
quadrature. Every returned row receipt and engine-before/after receipt contains
exactly these normalization children:

```json
{"adapter":"cartesian-unit-interval-v1",
 "mapping":"nearest-endpoint-affine-binary64-v1",
 "jacobian":"inside-weighted-callback",
 "request":"unchanged-epsabs",
 "target_e":0.000125,
 "intervals":0,
 "integrand_calls":0}
```

`target_e` is the actual Engine target: 0.000125 primary or 0.0000078125 refined,
not a copied constant. Counts are nonnegative integers, excluding bool. Row
counts are per call; engine counts accumulate within that engine. On a returned
numerical/point row, intervals must be positive and equal the frozen receipt's
interval count. Integrand calls must be positive and equal both the engine
counter difference and `work_after.chord_evaluations-work_before.chord_evaluations`.
Row interval count must also equal its engine difference. Analytic foreground
or background rows require zero normalization and chord deltas, although they
may execute independent spatial-factor quadrature. Refused rows retain partial
counters and no completed receipt; do not fabricate zero work or a value.

Include the new adapter, this amendment and any new executable controls in the
actual source closure and before/after snapshots. The strict reader's explicit
method/dependency list must change narrowly to v2 and these typed fields. It
must not accept arbitrary supplied source maps as authority.

## Fixed direct controls before any component rerun

Use all six literal intervals below and all four functions `2`, `3+2*t`,
`t-0.375`, and `1+t+t*t` (24 pairs). The signed function is an integration
component, not a nonnegative radiance scene. Endpoints written in hex are exact
`float.fromhex` literals, re-chosen from the observed 5/13/16-step intervals:

| ID | a | b |
| --- | --- | --- |
| A | -0.875 | -0.125 |
| B | 0.125 | 0.625 |
| C | -0.3125 | 0.9375 |
| D | -1.0 | 1.0 |
| E | -1.0 | -0x1.ffffffffffff9p-1 |
| F | 0x1.fffffffffffe9p-1 | 1.0 |

Build the independent oracle using exact Fraction representations of the
endpoints and polynomial coefficients, integrating monomials analytically.
Do not use the adapter's map or quadrature to produce the oracle. With
`scale=(b-a)*max(1,abs(A)+abs(B)+abs(C))` for `A+B*t+C*t²`, request
`e=2^-40*scale`. Require finite value/indicator, no warning, indicator ≤e,
and value error ≤`256*2^-52*scale` relative to the exact oracle. These tight
polynomial software checks do not replace or loosen the registered scene bars.
Constant tests establish interval mass; signed/affine and quadratic tests
prevent cancellation or a midpoint shortcut from masquerading as coverage.

Observe the **actual original quadrature call** behind the adapter, delegating
to it unchanged. Require exactly one call on [0,1], incoming e bit-identical,
epsrel0/limit128, nonzero callbacks, and returned integral/error unscaled. Also
exercise callback u values `0, 2^-20, 0.25, 0.5, 0.75, 1-2^-20, 1` through a
test dependency, preserving endpoint bits and monotonicity. Independently
compare mapped t with the exact rational affine map within
`2*max(ulp(a),ulp(b),ulp(float(exact_t)))`; the comparison acknowledges rounding
and is not the interpolation fault's sole power test.
Invalid/nonfinite/reversed/zero-width domains and invalid u
must refuse; neither NaN nor out-of-domain samples may be silently clamped.

Each fault below is separate, followed by restored execution of its same
control. A restored numeric result/indicator/call signature must reproduce the
unmodified result. Do not retune coefficients, intervals or tolerances.

| Fault | Named active test |
| --- | --- |
| Omit w from callback | Constant on B and both slivers; exact integral fails. |
| Multiply returned value/error by w again | Constant on B and both slivers; exact integral fails. |
| Map only the left half with `a+(w/2)*u` but keep full w | Affine on C; exact integral fails. |
| Replace mapped coordinates by the midpoint | Quadratic on C; exact integral fails. Constant/affine are declared inert for this defect. |
| Use e/w or e*w with the weighted callback | B and C: spy observes the actual quadrature invocation, then rejects changed e. Polynomial accuracy alone cannot establish request correctness. |
| Suppress an original IntegrationWarning | A test dependency calls its callback at u=0.375, emits IntegrationWarning('normalized-interval-control-warning'), then returns (0.0,0.0). Require that same warning reaches the frozen render refusal guard; swallowing it must be detected. |
| Install into reference spatial-factor quad instead of frozen Cartesian quad | Geometry-004 primary retains the old warning/zero normalized work; its required successful normalized call fails. |
| Also wrap spatial-factor quad | While the Cartesian adapter is installed, actual `integrate_factor('disc',4.5,1e-6,budget)` must retain its original value/receipt/calls and zero normalization work. The wrong dependency receives its out-of-pupil domain and must be caught. |

Request faults are **call-contract** controls, not claims of measured accuracy
loss. Jacobian and interpolation faults are independently checked scalar
errors. All controls must witness their actual changed consumer path, not just
a descriptor. Keep off/count/placebo numeric equality for the 24 direct
pairs, with the adapter enabled in all three modes. All observers retain the
same mapping and callbacks, with count showing
positive collection and placebo showing reached hooks without collection.

As a retained historical arm, geometry-004 primary with the adapter disabled
must reproduce the original warning refusal. Restoring the adapter must use
the same literal scientific case. Callback/quad exceptions and warning failures
must restore both original dependency identities; exercise this with a sentinel
callback exception. The old refusal is expected evidence, not a failing test
silently removed from the normal suite.

## Complete rerun and unchanged admission scope

These are additive bounded controls; no scalar from a former successful subset
is substituted. After source freeze and a new joint execution release, run the
complete author component batch and the complete independent reference batch
(all 150 cases, both targets, 300 reference baseline rows, existing oracles,
faults/restored pairs and observer population). Keep the independent shared
30-million actual-integrand-call, 600-CPU/1200-wall-second and 32-MiB named-array
limits, including the additive controls. The author's previously registered
resource limits remain unchanged. Refusal remains an honest terminal outcome.
Direct polynomial/test-dependency callbacks charge the shared integrand budget
once per evaluation. Frozen Cartesian callbacks already charge it themselves;
the adapter counts its calls but must not charge that budget a second time.

Use fresh interpreter/cache commands and the complete final source snapshot.
Refresh all 145 strict private reader controls, then the narrow additional v2
metadata controls using the actual new reference result, before consuming the
two fresh numerical batches. Keep all earlier result packages immutable; no
mixed revision can confer authority. The consuming reader must reject malformed
or coherently rehashed normalization fields/deltas and accept restored actual
rows. Root supplies external result/release hashes.

Keep self-refinement ≤0.0005 electrons, component maximum discrepancy ≤0.004
electrons and textured RMS ≤0.0008 electrons, all required rows and prior fault
power. No full-image/reference arm or dependent CFA emission is released by this
amendment alone. Full arrays, whole/edge-band bars and software-only optical
scope remain those already registered. A successful new numerical method would
not retroactively admit the original run or establish physical capture accuracy.
