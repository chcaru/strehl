# Root sampler source review and release decision

SOURCE REVIEW ONLY, 2026-09-08. No sampler, build, test or numerical control
has run at this decision. The source freeze created after this document binds
the exact bytes of this review and all reviewed inputs. The first release is
the original baseline; the candidate cannot replace align.rs until actual
negative evidence has been retained and committed.

## Independent roles and choices

Coordinate_verification authored the public integration test independently
of the existing implementation and repair. Factor_eight_implementation
authored the external repair patch, then independently reviewed the test.
Root separately read the entire public test and its specification. The
controller author reviewed the root constructor/capture sources; root read
the controller's authority, source/input checks, process accounting, artifact
selection, prerequisites and transcript interpretation. Independent repair
and test source reviews are separately frozen alongside this decision.

The test uses literal affine truth for Bilinear/cubic, and actual translated
interior stencil comparisons for Lanczos. The latter preserves the phase and
stored tap values without copying the proposed floor/base-cap rule; it does
not certify Lanczos first moments. Tiny unchecked cases choose effective
fallback endpoints independently from fixed dispatch dimensions and integer
truth. Wrong input, wrong phase, raw cubic excursions and wrong gather
direction are actual exercised controls. The flat null precedes any possible
detail interpretation; no sharpness or physical-noise metric is used here.

Source review found and corrected two real coverage gaps before execution:
the gather destroyer required successful actual count/mask population rather
than being allowed to reject untouched error sentinels, and checked tiny
refusals were supplemented by20 unchecked fallback rows. The full fixed
public population is344 across11 groups. Both axes, corners, inclusive upper
coverage, refusal positions, nonfinite values, original interior/lower values,
the cubic value limiter and actual full gather operands remain distinct.

The existing13 exact unit regressions retain their own fixtures and limiter
destroyer, selected by the repair author and reviewed by root. In particular,
old cubic hull helpers follow old coordinate ranges and cannot certify the
new requested-coordinate behavior. Their random/integer/null controls remain
useful regressions. The unchecked identity-gather test explicitly excludes
its border from the interior-identity claim. No high-frequency-energy test
is used to infer quality.

## Repair decision and limitations

Root accepts the prospective unchecked extension contract: complete the last
legal cell through phase1 and then extend its endpoint constantly. Keeping
the old plateau after repairing the accepted half-cell would introduce a
discontinuity; narrowing checked coverage would discard legal queries. The
chosen behavior still needs the fixed actual tests. It changes unchecked
upper-edge outputs, positive-infinity clamping and reached fallback values;
the final report must state this explicitly.

Only five sampler coordinate/base selections and the checked nonfinite guard
change. Size guards precede subtraction; base caps keep all selected taps in
bounds even at the final centre. Kernel coefficients, accumulation expressions,
cubic value limiting, finite checked support, lower extension, warpmap and
default kernel selection are unchanged. Unchecked NaN safety and nonfinite
sample data are not newly guaranteed. The scalar-grid tests do not establish
physical placement, native CFA conversion, quality, a performance gain or SOTA.

Original align.rs:147932B/
6d33f0e24f21d4370ccd8df0bf618e54a5ad615b838bc265469b4f85051c2786.
Held unapplied patch:4873B/
dbf4396c2b52e52fc369061c0f0dc73a6d03d8ec7341fe9b396b6e411b4968ff.
Reviewed candidate:148796B/
e5003cf05a2805a0a6a72b6f59f2724bcc8873ebbcc8bbb95a69120bda7a24a1.
The candidate must match exactly after application. No broader source edit
or fallback/kernel rewrite is authorized by this patch.

## Execution and evidence decision

Both independently frozen builds request --lib and --test sampler-boundary,
with exactly two Cargo jobs and fresh separate targets. Retain actual
Compiling strehl-core and non-fresh Cargo artifact messages for each emitted
test executable. A direct original integration-test exit101 counts only as
an operationally complete negative baseline when the full344 rows, full
gather bits/mask and final exercised boundary assertion failure are present.
It is not a passing test. No exact number of failures has been assumed.

The repaired integration test must pass all344 unchanged rows with actual
exit0. The separately released repaired library binary must pass exactly13
named existing regressions with no ignored selected test. All other library
tests stay filtered and unvisited. Keep the whole raw streams, actual child
and external exits, EOF, terminal owned Job accounting, finite resource
reservations and absence of emergency termination. Failed attempts remain.

The source/command freeze precedes each first execution. Across original
and repaired maps the only changed prior source is align.rs; tests/spec,
controllers and reviews remain immutable. The original source archive and
repaired delta preserve exact bytes after the live tree moves forward.
The controller checks source closure before and after execution, and later
stages bind all six actual prior result/tail/outer/stream/exit roles.
Root's preparer compares path identity as well as extent and hash; its first
draft's relative-versus-absolute dictionary mismatch was found and corrected
by independent source review before invocation.

The charter's prospective fifth-stage amendment is the governing allocation:
two600CPU/300wall/3GiB/128MiB builds, three30CPU/60wall/512MiB/16MiB test stages,
and five5CPU/7.5active-wall metadata slices. Actual costs and failed resources
are separately reported; these are reservations, not measured performance.
No old common-TIFF, M194h, M194g, M193c science/checker or capture runs follow.

Root may publish a software correction only after independent saved-result
review; any unexpected failures require interpretation without changing a
frozen assertion. This release does not fold SYNTHESIS facts or modify a
scorecard. AGENTS prior-art search and the M136 value-hull distinction are
recorded in the committed charter. No external prohibited source is used.
