# Checked-sampler boundary correction

VERIFIED within the fixed saved software contract by a separate reviewer.
2026-09-08. Scope: scalar sampler coordinate correctness, not image quality.
The common-TIFF integration is complete and is not rerun here.

## Result and consumer

MEASURED on the exact public test path: the original implementation fails103
of344 fixed rows; the reviewed repair passes all344. The actual original test
exits101 and the repaired test exits0. All thirteen separately selected existing
unit regressions pass, with546 other library tests explicitly filtered/unvisited.

The public gather's declared coverage was already correct:11,844 accepted and
444 refused sites on the128x96 scalar grid. Original accepted values are wrong
at219 sites near the high boundaries, with a largest6-code-unit error on the
literal affine fixture. The repair reports zero wrong accepted values, unchanged
coverage and proper NaN values at every refusal. Residuals are scalar value code units. Coordinates use integer sample centres
and scalar-plane sample-pitch units. Neither is a measurement of native alignment
displacement or a physical camera calibration.

Consumer: warpmap::gather_checked treats Some as covered and None as NaN/false.
The earlier common-RGB identity path does not use these samplers. Native
full-resolution alignment performs a separate factor-two coordinate conversion;
this fixed scalar experiment does not certify that conversion or physical maps.

## What changed

Five interpolating samplers clamped accepted high-edge fractional coordinates
to an earlier integer centre even when their source taps fit. Bilinear at
x126.25 on width128, for example, sampled at126 although the checked domain
admits through126.5. The same issue appears in both cubic variants and Lanczos2/3,
with kernel-specific support, and independently on y.

The repair retains fractional phase in the final legal cell, caps the integer
stencil base so its taps remain valid, and permits phase1 at the final legal
centre. It also rejects nonfinite checked coordinates before sampling.
All12 original NaN-coordinate rows failed; positive/negative infinity rows
were already refused and remain so. Unchecked NaN safety is not newly promised.

Kernel coefficients, accumulation order, clamped-cubic value limiting, support
values, finite checked coverage, lower extension and default selection remain
unchanged. The patch is six hunks,39 added and15 removed source lines.

Compatibility change: unchecked upper extension now uses the final legal centre,
one sample farther than the old plateau. This also affects reached fallback
samplers and the positive-infinity coordinate that the unchecked clamp maps
to its upper endpoint. Twenty explicit tiny unchecked rows exercise fallback
endpoint/extension behavior. Positive-infinity unchecked behavior is source-
derived, not an additional executed row. No new nonfinite-source-data guarantee.

Preserving the old plateau after repairing the admitted half-cell would create
a discontinuity; narrowing the checked domain would discard legal stencils.
Root and the independent repair reviewer chose the complete legal-cell contract
before execution. The evidence supports that stated compatibility choice,
rather than silently describing every unchecked output as unchanged.

## Independent controls and preserved failure

The original source stayed intact until its complete negative evidence was
committed at9bbc0181068f0d9e975401915c7275ddb6a1a9b2. Only then was the exact
reviewed patch applied and committed at48285a9acc389169044b083aa3aff4edf4253527.
No assertion, fixture or tolerance changed between original and repaired runs.

| Fixed group | Rows | Original failed | Repaired failed |
|---|---:|---:|---:|
| Support | 6 | 0 | 0 |
| Checked boundary | 126 | 35 | 0 |
| Flat null | 18 | 0 | 0 |
| Nonfinite coordinates | 36 | 12 | 0 |
| Checked tiny planes | 48 | 5 | 0 |
| Unchecked endpoints/extension | 60 | 40 | 0 |
| Reached tiny fallbacks | 20 | 10 | 0 |
| Invalid constructors | 4 | 0 | 0 |
| Lanczos oracle commissioning | 18 | 0 | 0 |
| Cubic value limiter | 6 | 0 | 0 |
| Actual gather and direction destroyer | 2 | 1 | 0 |
| Total | 344 | 103 | 0 |

Coordinate_verification independently authored the test. Bilinear/cubic use
literal affine truth, while Lanczos compares actual same-phase translated
stencils with identical stored taps; normalization is not mistaken for affine
first moments. Wrong input/phase controls and the raw cubic hull excursion
must actually occur. The full gather retains all12,288 f32 words and masks.
The independent saved reader reconstructs literal and paired numeric predicates
from saved operands. Tap equality, changed-input counts, support/constructor
booleans and other unsaved runtime exercise flags remain source-bound reported
witnesses; they are not independently reconstructed runtime measurements.
All flat-null rows pass both variants, but they are not byte-identical: one
Lanczos3 upper-null value changes within its fixed tolerance. One affine-upper
cubic-limiter value also changes while passing in both variants.

The repair author and root independently reviewed the tests. They caught two
source-level gaps before any execution: a gather destroyer could accept untouched
sentinels after an error, and checked tiny refusals never exercised inner fallback
outputs. Those were fixed prospectively, expanding324 to344 rows without dropping
any earlier row. The thirteen existing regressions use their original fixtures,
including a widened-hull destroyer and in-hull bit identity. Their old support
helper is not used as the new high-coordinate oracle.

The original failures include finite wrong values, five nonfinite values, four
caught panics and one false gather predicate. Every row still precedes the sole
aggregate assertion. Thus the original test is a real recorded failure, not a
relabelled expected-success test or a population stopped at its first mismatch.

## Commands and execution evidence

Actual commands, each released from committed exact sources:

    python -I -S -B experiments/sampler-boundary/capture-stage.py baseline build
    python -I -S -B experiments/sampler-boundary/capture-stage.py baseline test
    python -I -S -B experiments/sampler-boundary/capture-stage.py repaired build
    python -I -S -B experiments/sampler-boundary/capture-stage.py repaired test
    python -I -S -B experiments/sampler-boundary/capture-stage.py repaired regression

Python was C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe.
Each corresponding prepare-release.py invocation ran first and its release
committed before capture. The exact complete child argv is in each release.
Both builds use fresh target directories, --lib --test sampler-boundary,
--no-run --jobs2, locked/offline dependencies and actual Compiling strehl-core
messages with fresh:false integration/library artifact records. The direct
integration command selects only sampler_boundary_public_contract; the library
command selects thirteen full names with --exact, not a substring sweep.

| Stage | Actual child exit | Owned child CPU seconds | Parent final CPU sample | External whole wall seconds |
|---|---:|---:|---:|---:|
| Original build | 0 | 25.609375 | 11.015625 | 19.093 |
| Original public test | 101 | 0.015625 | 1.281250 | 1.406 |
| Repaired build | 0 | 25.500000 | 10.234375 | 18.140 |
| Repaired public test | 0 | 0.015625 | 1.281250 | 1.422 |
| Repaired existing regressions | 0 | 0.031250 | 1.250000 | 1.469 |

These are execution/accounting records, not a performance comparison. The CPU
columns exclude the finite reserved final allowance and the external wrapper's
unmeasured CPU; whole wall is not used to infer CPU. Peak owned build Job
committed bytes are993,394,688 and992,907,264 under the3GiB caps. Each direct
test stays below its512MiB cap. All five controllers exit0 with no timeout,
error or finalization error; the original child still exits101.

Both compiles retain intentional owned-Job descendant cleanup after successful
direct Cargo exit and pipe EOF, with final active count zero. This is the
prospectively reviewed compile-only policy, separate from emergency termination.
Direct tests have complete exit/EOF/drain/terminal Job evidence and no such
compile cleanup or emergency termination. There is no retry or operationally
failed sampler stage to overwrite. Earlier common-TIFF/M194h failures stay intact.

## Exact provenance and review status

Source/test/review commit:ee6098d8b518bbce8d5378e7653a5402d9276b0e.
Original build release89e7e632, original test release62b6a8d3 and negative
evidence9bbc0181. Repaired source48285a9a, build releasebf9ef373, public-test
release32d32568, public result/regression release16449d26 and final regression
evidence3ceebceb. Independent saved-review release4ae4a0dc; completed independent evidence2c76b8c6.

Both frozen source maps contain177 entries, with only align.rs different.
Original exact source archive baseline-source-1.zip:5,554,495B/
7bc4ad1597b14df0ac842c06b891530c192ac193e0412585f26005405a973c78.
Repaired source delta archive:148,956B/
8233d63ac83883f40762bd7a52faef0c3bc10db583f67c7f776935a9790e290a.
Both are under experiments/sampler-boundary/work and were read back at freeze.

The original working source uses CRLF while its preceding Git blob uses LF.
The exact-byte repair commit preserves the certified CRLF. The saved
git-source-format-audit-1.json, committed at2c553939, proves normalized prior Git equals original
archived source and accounts for all apparent whole-file Git deletions:
the substantive delta is39/15, with no unrelated source content removed.

Independent source reviews are in experiments/sampler-boundary. The final saved
reader is independent of the sampler, patch, test and stage controller and
re-chooses full gather partitions, literal/paired predicates and source/transport
associations. Its exact source9af714765a05bfe4ca33052704a1e6612f69aa93e525c0731aa083fe9354701b
was separately source-reviewed before the first saved read. Its four actual
reads completed once each with child/adapter exit0, empty external stderr and
no timeout. The independent review is21654B/
b814851d352ab6a01c5589e6075282fe525bf15dfd30a3dae7a7bc83e9877f95
at experiments/sampler-boundary/independent-result-review.md; its original
7293-byte prospective plan remains an exact prefix.

That review independently confirms the344-row populations, all13 named existing
regressions, source-map sole change, exact stage associations and terminal Job
evidence. It partitions the full gather by declared coordinates:11625 accepted
interior values are already exact;93 final-column values change from residual-2
to0,125 final-row values from-4 to0, and the corner from-6 to0. All444 refusals
remain NaN. The opposite-direction literal fails at all11844 accepted values
in both variants despite identical masks.

The review itself had one failed metadata attempt before any numeric reader ran:
its adapter compared absolute and ROOT-relative FileRef dictionaries literally
and exited1 on association. Exact source and failure remain in work/independent-
transport-failed-1.py and independent-transport-failure-1.json. Its unpublished
CPU and actual read count are unknown, not zero. Root charged the entire
10CPU/15active-wall allocation and513MiB of reads; the originally suggested
129MiB charge was corrected against the failed adapter's actual128MiB per-read
limit for four executables. The correction and added fifth allocation preceded
the independently reviewed canonical-path adapter release9fba84db. No sampler
or test was rerun, and no numeric-reader command or acceptance bar changed.

The amended audit bound is50CPU/75active-wall seconds,768MiB charged reads
and8MiB retained output. The four successful external whole intervals are
0.125/0.141/0.141/0.203 seconds; combined parent CPU samples plus completed
owned-reader CPU are0.078125/0.078125/0.0625/0.125 seconds, each with a
separate1CPU/2wall final reserve. These samples do not measure wrapper CPU.
The closing publication receipt records590597674 cumulative charged read
bytes and403911 retained family bytes before that small receipt, within caps.
It includes the failed charge. Root separately checked the four outer stream
hashes/exits, ledger dispositions, final review hash and preserved plan prefix;
this publication inspection does not add a numeric-reader execution.

No SYNTHESIS fold or absolute fact block is proposed. No quality, default,
noise calibration, physical-placement, full-workspace test or SOTA claim follows.

## Next consumer step

The next committed source-only charter is
experiments/common-tiff-dimensions/charter.md at87d3136b: generalize the existing
identity common-TIFF consumer to2..8 frames and64..512 axes while preserving
v1's exact admission and output bytes. Separate authors prepare the bounded
implementation and independently chosen constant/address/noise/refusal fixtures.
Source preparation is authorized; builds and images require their own frozen
finite release. Integer maps and resampling-aware covariance remain later work.

## AGENTS execution checklist for this scope

| Rules | Concrete discharge or explicit inapplicability |
|---|---|
| 1,2 | No production storage/merge working-set change. Public scalar-view fixtures and one gather output live in sampler-boundary.rs; no aligned stack is materialized. |
| 3,4,5,6,7 | No noise estimation, selection, geometry fitting/chaining or decoded RAW statistic in the patch or commands. |
| 8 | Five actual capture commands, exact releases, raw logs and committed result references above; claims labelled measured or source-derived. |
| 9,10 | ordinary_rows executes18 flat-null checks; no sharpness metric or spatial/temporal sigma comparison. |
| 11,12 | Original public-path103 failures retained; null/interior/Nearest controls, actual destroyers and independent source/result reviewers. |
| 13,16 | No parameter sweep or optimum. Timing table is execution accounting, explicitly not a performance comparison. |
| 14,32 | No capture-tree inspection or RAW decoding; no rawpy view lifetime. |
| 15 | No plugin-margin or occlusion-artifact assertion. |
| 17,18,24 | Independent saved reader partitions by literal output coordinates, not outcomes; coordinate predicates have wrong-phase/direction destroyers and no quality interpretation. |
| 19 | New files and directories use kebab-case; existing Rust symbols/crate names retained. |
| 20,35,36 | Declared test guards require changed taps/phase, actual raw hull excursions and completed gather; original runtime fails; repaired controls still exercise those cases. |
| 21,30,34,39 | No fitted constant, calibration, statistical ratio or sigma claim. Every original case remains; deterministic code-unit tolerances and duplicate points are disclosed. |
| 22 | This checklist maps all49 numbered rules plus31b to code/evidence or scope. |
| 23 | No SciPy or frame-axis filtering. |
| 25,28,31,31b,37,44 | No SYNTHESIS fold, fact/discipline/question numbering or exemption. Sources and outcomes commit before downstream consumption. |
| 26 | No production diagnostic/observer added; transcript code is a separate integration-test target. |
| 27,49 | Root releases once-only owned processes; healthy builds awaited, no peer process termination or fabricated host hold. |
| 29 | Exact six-hunk patch hash; normalized39/15 substantive diff and separately committed whole-file newline audit; heading/table structure checked before report commit. |
| 33 | Two fresh targets, actual Compiling strehl-core, both emitted artifacts fresh:false, and refreshed edited-source mtime; no quiet Cargo gate. |
| 38,40,43 | Charter records actual prior_art query and all surfaced reports; M136 census/default-decision passages read for their actual claims, not inferred absence. |
| 41 | Descriptive sampler-boundary identity, no new or reused M-number. |
| 42 | Every commit uses an exact pathspec and verifies its resulting path set and every Git blob against intended bytes; no shared-index sweep. |
| 45 | No registration, capture path or warpmap sidecar write. |
| 46,47 | Complete raw stdout/stderr/actual exit retained; exact argv/input/source/environment bindings in releases and receipts, not a truncated display pipeline. |
| 48 | No visual quality verdict. Complete scalar bits are the data, not resized screenshots. |
