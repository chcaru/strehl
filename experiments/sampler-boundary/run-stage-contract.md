# Fixed sampler test build/run contract

SOURCE ONLY, 2026-09-08. The charter authorizes source preparation, not execution
from this document alone. Root separately freezes and releases each of five
stages. All commands below are prospective; no build/test result is asserted.
The independently authored integration test and independent-test-spec.md fix
all input rows, oracles, tolerances and the single final aggregate assertion.
This controller checks authority, transport and population, not sampler quality.

## Five exact operations

One integration-test target, sampler-boundary, in strehl-core; default features,
no manifest or dependency additions. The only direct test is
sampler_boundary_public_contract. Baseline and repaired variants each get one
fresh build and one once-only direct binary invocation. A fifth, repaired-only regression stage runs the thirteen exact existing unit
names listed below on the library test executable. No cargo-run, workspace
campaign, second listing, retry, capture/image/RAW/model/merge or prior experiment
main is invoked. Earlier experiments, sources, binaries and outputs stay intact.

The fixed working directory is the repository root. Controller invocation:

    PY -I -S -B ABS/experiments/sampler-boundary/run-stage.py --release ABS/experiments/sampler-boundary/work/VARIANT-STAGE-release-1.json --release-sha256 ACTUAL_SHA

PY is the exact released Python executable. VARIANT is baseline or repaired;
STAGE is build or test, or repaired-only regression. Build child, exact order:

    cargo test -p strehl-core --lib --test sampler-boundary --no-run --jobs 2 --target-dir ABS/target/sampler-boundary-VARIANT-1 --message-format=json-render-diagnostics --locked --offline

The fresh copied artifacts are VARIANT-build-1/sampler-boundary-tests.exe and
VARIANT-build-1/core-unit-tests.exe. Exactly
one direct invocation follows its separately released build:

    ABS/VARIANT-build-1/sampler-boundary-tests.exe --exact sampler_boundary_public_contract --nocapture --test-threads=1

Build expected child exit is 0. Baseline test expected child exit is 101 only
with the source-predicted exercised failing public boundary assertion and the
complete fixed transcript. Repaired test expected exit is 0 with every row
passing. The parent can complete operationally after recording the expected
baseline failure; test_passed remains false. A crash, timeout, truncated row
population, arbitrary error, or clean but unexpected exit does not substitute
for the commissioned baseline assertion. No quality claim follows from a pass.

## Source and release authority

Closed ten-key schema sampler-boundary-stage-release-v1:
schema, stage, variant, source_bindings, inputs, command, children, executable,
prerequisites, prediction. The three-key prediction is spec FileRef, test_source
FileRef and typed expected_exit_code, 101 for baseline and 0 for repaired.
Both references must match released source bindings. The command after filling
ACTUAL_RELEASE_SHA256 must equal sys.orig_argv. The sole child must match the
literal derived command and typed expected exit. Python and actual resolved
Cargo/rustc inputs are hashed; they are not identified by a display name alone.

Every source key is a unique canonical ROOT-relative positive FileRef binding,
<=4 MiB each, <=512 members and <=16 MiB aggregate. Before and after each stage,
rehash the entire source map and require equal actual current Rust closure,
including Cargo.toml/Cargo.lock, crate source/test files, explicit includes and
the existing dust data include. The ordinary source map is not a claim that
all system libraries, compiler caches or environment files are inventoried.
The exact compiler and Cargo paths are separately bound inputs; toolchain
location fields are observed. Cargo uses two jobs and Rayon uses two threads.
Inherited STREHL_, M194H_, SAMPLER_BOUNDARY_, RUST_TEST_, Rayon/BLAS and compiler
overrides are removed by the held environment path plus the narrow sampler
wrapper. RUST_BACKTRACE and RUST_LIB_BACKTRACE are both fixed to 0, preserving
ordinary panic evidence without inherited verbose stacks. No panic hook changes.

Baseline requires original compiled align.rs SHA256
6d33f0e24f21d4370ccd8df0bf618e54a5ad615b838bc265469b4f85051c2786.
The repair stays outside crates until baseline evidence is committed by root.
Repaired-build consumes the six-reference baseline-test bundle and the actual
saved negative test-observation record. Source keysets must match baseline;
only align.rs may differ, while tests, spec, controller, helpers and all other
compiled/authority sources remain identical. The root constructor additionally
requires the independently reviewed repaired hash and archives the exact changed
source. Repair drafts never replace the compiled-source association. Freeze all
prospective reviews before baseline; append actual outcome notes outside the
frozen map. No controller Git operation pretends to certify root's commit step.

Each test stage consumes its variant's completed build result, exact executable
FileRef and matching source/prediction map. A build has no preexisting executable.
The repaired regression stage consumes both the repaired build and its actual
344-row passing public-test evidence, with the same complete source map.
The baseline build has no prior stage. The repaired build requires baseline
negative evidence; no original failure is overwritten or refunded.

## Reused owned execution

The seven functions need, bootstrap, load_base, file_ref, source_check,
input_check and child_call are verbatim from common-TIFF run-stage.py,
29852 bytes/SHA256
25d9b11cd0b99c1720ff460a4237209eaa9c6a36a8ffa8ade50afa608f41cb05.
They reuse the held M194h driver at
b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410.
Only its non-scientific Budget/read/scan/owned Job definitions are used; no old
main or control population executes. Budget globals point to the current stage,
variant target and output, and START includes controller authority work.

New bounded-build-process.py is derived from the held common compile helper
16512 bytes/SHA256
d27374f6b0fe00c53d2f7110f2ebd553067cb3e2c772d3076547b5f2db9e3d94.
Only its exact command gate changes to the two Cargo test-build commands above.
No cleanup, native API, pipe, polling, Job or accounting body changes. Its current
16663-byte SHA256 is
bdd7ff3328de37789ac212cf5f4d868ad3580939827c4a7ca10a669c2ddc995c.

For compilation only, successful direct Cargo exit plus pipe EOF permits the
reviewed owned-descendant cleanup: retain Job/PID observations, terminate only
that owned Job if descendants remain, wait <=5 seconds to zero, and retain
final accounting. PIDs are observations, not kill targets or executable-identity
proof. Generic failure termination cannot admit a compile. Test invocations use
the unchanged strict bounded-process helper: no compile policy field, no generic
termination, no process/cleanup error, direct expected exit, EOF, complete drain,
zero active count and complete terminal Job CPU are all required.

Every child receipt and raw log is durable before expected-exit assertions.
Whole owned Job user+kernel CPU is counted once, with current parent CPU added;
live monotone observations enter ordinary budget checks. No doubling of an
individual process inside the same Job, and no inference of CPU from wall/RSS.
An incomplete Job sample stays explicitly incomplete. Only owned children/Jobs
are terminated. No unrelated process lookup, attachment or kill is performed.

## Actual compile and transcript evidence

The compile log must contain Compiling strehl-core, exactly one successful
Cargo build-finished JSON and exactly two fresh:false test artifacts: the
sampler-boundary integration target and strehl_core library target. Their respective kinds are test/lib, profile.test is true and features are
empty. Both bind strehl-core/Cargo.toml and their exact integration/lib.rs sources.
Artifact path lies in the fresh variant target. Copy actual bytes into the fresh
retained executable, require identical extent/hash, and rehash it around the
test. A successful status without these actual artifact records is insufficient.

The test emits a leading-newline BEGIN marker, every fixed ROW marker in exact
order, the complete GATHER marker, then SUMMARY before its only aggregate assert.
The controller checks the schema, typed bit encodings, unique ordered source-
derived IDs, group totals, exercised/passed consistency and summary arithmetic.
The exact complete population is344 rows: support6, boundary126, null18,
nonfinite36, tiny48, unchecked60, unchecked-tiny20, constructor4,
lanczos-commission18, cubic-limiter6, gather2. The newly commissioned unchecked
tiny rows follow all six ordinary kernel groups and precede constructors. They
exercise actual fallback outputs, which checked-domain refusals alone cannot. All rows,
including failed and panicked outcomes, remain in the 1 MiB raw log. Nonfinite
numbers use IEEE integer bit patterns, not invalid JSON numeric constants.

GATHER retains all 128x96 actual f32 bits (98304 hex characters) and both full
coverage masks (3072 hex characters each), the exact reference-to-source map,
returned/observed counts and mismatch censuses. The parser retains their raw
byte range/hash and checks extent/type only; it does not recompute the image
oracle. A compact test-observation.json holds complete population/disposition,
failed row identities and the original raw-log reference. Independent root
outcome reading must judge the scientific choices. No full-array copy is hidden
inside the 64 KiB parent result.

Baseline admission also requires an actual exercised failed boundary row from
sample_checked returning a finite value, the exact aggregate-assertion message,
exit 101, and libtest's one-failed/zero-passed summary after SUMMARY. Repaired
admission requires no failed rows, exit 0 and libtest's one-passed/zero-failed
summary. This preserves a disproved source prediction as a refusal rather than
silently calling an unexpected baseline pass the requested failure.

## Resources, publication and independent read

Per build: 600 combined CPU seconds, 300 whole-wall, 3 GiB committed owned Job,
128 MiB retained files, 4 GiB observed scratch. Per direct test or the one regression invocation: 30 combined CPU,
60 whole-wall, 512 MiB committed Job, 16 MiB retained, no scratch. Five metadata
slices reserve 5 CPU/7.5 active-wall each: total25/37.5/8 MiB. Across this commission
the execution plus metadata subtotal is 1315 CPU seconds and 817.5 sequential wall/active-wall
seconds, with312 MiB retained plus two separate4 GiB observed scratch budgets.
These are DERIVED reservation sums, not timings; each entered allocation stays
charged after a failure. No retry authority exists inside any stage.

The held Budget reserves2 CPU/3 wall publication plus12 wall cleanup before
launch, and child limits use the remaining combined stage envelope. Final parent
sample plus whole Job plus2 must fit the CPU cap; final wall sample plus3 must
fit the wall cap. Root's actual external interval and exit are required and
must satisfy outer <= sample+3 and <=stage cap. The metadata constructor has its
own fixed1 CPU/2 wall final allowance inside each5/7.5 slice. No external wrapper
CPU completeness is inferred from those interval records.

Output dirs are baseline-build-1, baseline-test-1, repaired-build-1,
repaired-test-1 and repaired-regression-1, all fresh and retained. Per stage: canonical result64 KiB and
simultaneous staging64 KiB, parent-tail8 KiB, child record32 KiB. Build log16 MiB,
two copied executables<=32 MiB each, each compiler message<=16 KiB. Test/regression
log1 MiB and detached
public observation128 KiB or regression observation32 KiB. External raw stdout8 KiB, stderr32 KiB, exit1 KiB, outer64 KiB.
These sum below each stage family, including simultaneous publication slots.
The scratch scan tolerates only observed disappearance and records its raced
paths; permission/reparse/type/cap errors remain strict. Observed bytes are a
non-atomic census, not a peak-storage or atomic-snapshot claim. Retained outputs
use strict disappearance handling. Source/JSON read and write bounds are checked
at the actual read/publication path; overflow cannot invent a complete result.

Controller schemas: sampler-boundary-owned-stage-v1 and
sampler-boundary-parent-tail-v1. Root outer schema is
sampler-boundary-stage-external-v1. The six prior roles are exactly result, tail,
outer, stdout, stderr, exit, bound by actual bytes, source and command. Raw parent
stdout advertises exact final result/tail refs. Positive canonical status alone
cannot escape a late refusal, missing tail, timeout or external nonzero exit.
The terminal status COMPLETE_STAGE_UNVERIFIED states operational completion;
full test interpretation still requires independent actual saved-output review.

Source-only review includes AST/symbol closure, exact reused-body comparison,
command/interface inspection and finite metadata sizing. It executes no candidate
helper, Rust test, scientific control, build or numerical oracle. Root owns the
independent source/result review and every exact stage release.

## Exact repaired-only regression selection

One direct libtest invocation, OR of full exact names, no Cargo delimiter:

    ABS/repaired-build-1/core-unit-tests.exe --exact --nocapture --test-threads=1 NAME1 ... NAME13

The fixed names in argv order are:

1. align::tests::catmull_rom_reproduces_the_samples_at_integer_positions
2. align::tests::clamped_catmull_rom_stays_inside_the_exact_support16_hull
3. align::tests::clamped_catmull_rom_is_bit_identical_until_catmull_leaves_the_hull
4. align::tests::clamped_catmull_rom_preserves_integer_samples_and_constant_planes_exactly
5. align::tests::clamped_catmull_rom_has_catmull_support_and_checked_domain
6. align::tests::a_widened_clamp_makes_the_hull_guard_fail
7. align::tests::a_gather_under_the_identity_is_the_identity
8. align::tests::lanczos3_is_interpolating_and_preserves_dc
9. align::tests::lanczos3_support_matches_its_reach
10. align::tests::lanczos2_is_interpolating_and_costs_no_extra_border
11. warpmap::gather_tests::gather_marks_uncovered_pixels_instead_of_clamping
12. warpmap::gather_tests::gather_refuses_a_geometry_mismatch
13. warpmap::gather_tests::gather_refuses_a_refused_frame

The controller requires the actual running13 header, each exact name once with
ok, and the13-passed/zero-failed/zero-ignored summary. It retains actual execution
order and the count of other library tests filtered/unvisited. No omitted selected
test or executed extra can pass. This is a single separately bounded owned child,
not thirteen independent allocations. The selected existing tests are unchanged.
Primary command grammar was checked by the independent repair author against
Rust's test filters/--exact documentation and libtest filter_tests implementation;
no test binary was run to discover or adapt the command.

## Final source sizing and independent review reservation

DERIVED, source/metadata only: a parent-shape proxy using the retained prior
controller shape, two near16 KiB compiler-message slots, an8 KiB environment
slot, complete prerequisite/compiled refs and two6000-character ASCII traceback
proxies serializes to58484 bytes <65536. A344-failed-row observation proxy with
80-character IDs, longest actual API/kernel labels and6000 bytes for remaining
fields serializes to90915 bytes <131072. These are finite metadata sizing
constructors, not test/metric executions or universal arbitrary-escaped-error
bounds. Runtime publication caps remain necessary. The source symbol closure
has no missing globals; exactly seven reused function AST bodies are unchanged.
Only the compile helper's command gate differs from its held parent.

The1315 CPU/817.5 wall/312 MiB figures above are execution plus metadata subtotals.
Root separately authorized four independent saved-result reads at10 CPU/15
active-wall each, with768 MiB aggregate reads,128 MiB per file and8 MiB retained
review outputs. That adds40 CPU/60 active-wall/8 MiB, for combined prospective
1355 CPU/877.5 wall or active-wall/320 MiB retained. The independent read plan is
separately committed and is not rewritten into this immutable execution map.
No review, run or success is implied by those reservation sums.
