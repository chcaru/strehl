# Proposed bounded reference interval diagnosis

2026-09-07. Design only, following the preserved first independent component
result `514520ee73ea4504be17f0520791c174d11f202c371cd1ce9f6b11a4a8da7b0b`.
No numerical helper was executed for this proposal. No source correction or
rerun is authorized by this document.

## What the retained evidence establishes

The result contains300 baseline rows:272 values and28 refusals. The14 case IDs,
each at primary and refined targets, are geometry-004,006,011,013,015,022,
060,062,067,069,071,078,116,117. Every refusal reports the frozen Cartesian
helper's quadrature warning, “Extremely bad integrand behavior”. The last
completeness check fails; the52 oracles and14 fault comparisons do not admit
these missing values. The author batch independently completed its own511
checks and331 calls; that does not repair the independent reference failure.

Source inspection identifies a candidate mechanism, **ARGUED, not measured**.
The frozen helper integrates each distinct Cartesian pupil-normal interval
directly in t. At geometry-004, n=(3,4), native centre(7,11), identity transform,
offset46.50000000000001 and foreground displacement−3 yield chief distance
approximately3.7−1.4e−15. The square's extreme normalized projection is.7, so
one clipping-topology cut is immediately below t=+1. The interval between that
cut and1 has very few representable coordinates. The saved call increments
462/546 are consistent with a normal interval followed by a63-call endpoint
interval; the other63-call refusals are consistent with a first interval near−1.
Those increments do not themselves prove where QUADPACK failed.

Before implementation, root fixes a falsifiable engineering definition:
a **suspected endpoint interval** has one bound exactly−1 or+1 and at most256
representable binary64 steps between its ordered bounds. Count steps by the
monotone IEEE754 binary64 encoding (the two signed zeros are distinct encodings;
this cannot affect an interval within256 steps of±1). Record the exact step
count for every interval, with no threshold-driven integration behavior.
This256-step diagnostic threshold is not an optical error bar and will not be
adjusted from the traced results. Preserve every warning, including warnings
on intervals outside this class, and actual distinct queried coordinates.

Two fixed positive companions already returned values: geometry-003 is the
adjacent exact offset46.5, returning15000.000000000016e at primary;
geometry-014 has offset83.49999999999994, returning9000.000000000011e.
Their scientific inputs must remain literal catalog records.

## Proposed diagnostic, before any method amendment

Replay exactly the14 failed IDs and the two positive IDs above, in catalog
order, at both original targets:32 calls per mode. Use off/count/placebo modes
under one diagnostic budget,96 calls total. The original reference source and
frozen independent-model.py stay unchanged; the diagnostic loads pinned bytes.
Only a temporary wrapper around the frozen module's `quad` dependency may be
installed, always restored in finally. It calls the original quadrature with
the same integrand, bounds, epsabs, epsrel and limit128. No integration formula,
point coordinate, clipping predicate, tolerance or warning disposition changes.

Count wraps each actual integrand callback and records its input/output without
altering either. Placebo reaches the observation hook without collecting;
off omits the hook. Capture each actual interval's bounds and their float.hex
forms, width, endpoint adjacency, requested absolute tolerance, call count,
returned integral/error when available, warning category/message, and distinct
queried coordinates. Retain the complete ordered count-mode(t,value) stream
as a bounded artifact. Capture warnings and re-emit them to the original outer
warning guard, preserving its refusal; do not convert a warning into success.
No use of full_output that suppresses the original warning path.

Normalize the per-call numerical signature to status, returned scalar/receipt
or refusal class/message, and actual integrand count. Require its bytes equal
across off/count/placebo and its statuses equal the retained first result.
Count/placebo must witness actual wrapper calls; only count collects samples.
The positive companions must return their original values within their original
targets. The diagnostic fails if any expected refusal changes disposition,
if instrumentation changes the numerical signature, or if the wrapper has no
power. Changing an actual interval-record bound in a copied diagnostic record
must fail the consuming correspondence check; the restored record must pass.
Retain that metadata-consistency fault and also power the sample-range consumer:
on geometry-003 primary's first ordinary interval, move the left bound to
nextafter(the minimum recorded t,+infinity), recompute its complete bound
metadata, and leave the actual samples unchanged. This coherent fault must
refuse specifically because an observed sample is outside the declared range;
a reopened restored record must pass. Reject JSON overflow literals as well as
explicit NaN/Infinity before consuming any diagnostic record.

Use a single100,000-integrand-call,10CPU/20wall-second diagnostic ceiling,
checked from process entry through final persistence; no clock reset per mode
or case. Limit retained trace to100,000 records and32MiB serialized bytes;
exceeding either refuses the diagnostic rather than dropping records. This is
a narrow attribution experiment, not a throughput estimate or model commission.
Pin all sources, inputs, exact command and thread environment before execution.
If it refuses its budget, retain it and do not expand this schedule automatically.

The hypothesis is supported only if the recorded warning intervals are the
prospectively defined suspected endpoint intervals and the actual queried-coordinate records show the expected
representability limitation. If warnings arise on ordinary-width intervals,
retain that contrary evidence and revisit the proposal; do not declare the
endpoint mechanism established from the source argument alone.

## Candidate correction, conditional on that diagnosis

A separate prospective numerical-method amendment could normalize every
Cartesian subinterval [a,b] to u∈[0,1], evaluating
`(b-a)*value_at_t(a+(b-a)*u)`. The Jacobian belongs in the integrand, so the
original absolute integral request can remain unchanged. An equivalent
unweighted-integrand implementation would need epsabs divided by(b-a);
mixing these two conventions would change the error allocation.

Keep every original split and its complete integration domain. Do not drop
small intervals, suppress warnings, enlarge limits or substitute a full-layer
answer for a nearly tangent cell. Refuse nonfinite/nonpositive interval width
or an out-of-domain mapped coordinate. Freeze the exact stable interpolation
expression and floating-point endpoint treatment before implementation. The
new wrapper may adapt the quadrature dependency; it must leave the original
M194e source bytes and original refused result intact.

Commission constant, affine and signed integrals on re-chosen unequal-width
intervals, including both endpoint slivers; a missing/doubled Jacobian and
wrong absolute-request scaling must be live faults. Retain normal-width
companions and both positive/negative endpoint cases. Then repeat the complete
300 independent baseline rows, all prior oracles and faults under unchanged
30m-call/600CPU/1200wall component limits. Keep targets.000125e/.0000078125e,
self-refinement.0005e, component maximum.004e and textured RMS.0008e. Every
scalar still faces the independent comparison. A normalized interval is a
numerical-method change, not proof of continuous-model accuracy or a pass for
the original refusal.
