# Fixed common-TIFF stage controller, build3 source revision

SOURCE ONLY. This protocol authorizes no execution by itself. The root releases
each of build, prepare, render and verify at most once, in that order, with an
exact frozen release hash. A failed stage leaves its output intact and stops
the dependent sequence. No retry, alternate fixture, build cache reuse, parameter
sweep, old M194h science or earlier control suite is dispatched.

## Reused source and changed seams

run-stage.py authenticates the exact original M194h build-and-run.py bytes
(40,626 bytes, SHA256 b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410)
before evaluating its definition-only module. The original main, authority,
metadata_controls, case_result, expected_children and scientific code are never
called. The module globals changed for reused primitives are START, HERE, SELF,
TARGET, STAGES, OUTPUTS, BUILD_PROCESS, BUILD_PROCESS_SHA and FIXED_ENV.
The controller calls the existing same-buffer read/write, source_closure, scan,
Budget, clean_env, load_process and compile-cleanup admission code. Its stage
limits wrapper supplies the new fixed per-child bounds.

The separate bounded-build-process.py differs from the held M194h compile helper
(16,334 bytes, 6c4b6e6222e1b58ec408fbd949d7a90bbb0c12778c292517c6eb6539eb4b036b)
only in the exact argv gate. It now names the fresh target3 and Cargo jobs2. Reverse replacement of that gate recovers every original byte.
All its Job, process, pipe, termination and cleanup functions are unchanged.
The gate admits only:

cargo build -p strehl-cli --bin strehl-common-input --jobs 2 --target-dir ABS_TARGET
--message-format=json-render-diagnostics --locked --offline

ABS_TARGET is exactly ROOT/target/common-tiff-stack-3, initially absent.
No feature flag is added. This helper is selected only for build child zero.
Other children use the original strict M193c bounded-process.py
47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b.
The reused load_process selects only the original declared M12 Job API AST
dependencies; compile policy adds its existing bounded Job PID list API.
Neither the original M12 harness main nor a new native launcher is run.

After direct Cargo exit zero and pipe EOF, the compile-only policy may terminate
remaining members of its own Job and wait within its original five-second
cleanup deadline. Natural completion and intentional owned cleanup stay
distinct. No executable identity is inferred for the remaining PID list, and
no PID is used as a kill target. All other children require natural empty-Job
completion and prohibit compile-policy and generic emergency-termination evidence.

## Frozen release and input authority

Every release is an object with exactly ten keys:
schema, stage, source_bindings, inputs, command, children, executable, fixtures,
run_bundle, prerequisites. Schema is common-tiff-stack-stage-release-v1.
stage is build, prepare, render or verify. Paths resolve from repository ROOT.
The controller itself is invoked from ROOT as:

PINNED_PYTHON -I -S -B ABS_RUN_STAGE --release ABS_RELEASE
--release-sha256 ACTUAL_RELEASE_SHA256

command contains that exact list with only ACTUAL_RELEASE_SHA256 as a placeholder.
The actual sys.orig_argv, selected executable and release bytes must agree.
Each source_bindings key is a canonical ROOT-relative path with a positive
{bytes,sha256} object. At most512 sources,4MiB each,16MiB aggregate.
Mandatory entries are the new controller/build helper/this protocol, consumer
source contract, independent controls/spec, held M194h driver and original
strict process/M12 Job helpers. Root includes its source reviews and decision
in the same source map before any stage release.

Before and after each stage, every listed source is read and authenticated.
The unchanged M194h source_closure additionally enumerates all local crate
Cargo manifests and Rust files, root Cargo.toml/lock, the explicit dust text
include, and its source-derived include!/path-attribute closure. It requires
every enumerated file in the map and verifies the before/after closure digest.
This is the held local source closure, not proof of registry dependency, native
DLL, toolchain-cache or OS immutability. Cargo is offline and locked; actual
cargo/rustc resolution and their same-buffer FileRefs are bound in inputs.
The current Python executable is also an input. Up to128 unique positive inputs,
64MiB each and256MiB total, are checked both before and after the stage.

Source and input readers retain each API's full before/after identity, including
ctime, while comparing only the shared identity fields between path stat and
handle fstat on Windows. Paths have plain non-reparse ancestry. No source is
rewritten or copied by this controller. A build executable is copied separately
and is never a source-map entry or a committed/shipped binary.

prerequisites is empty for build; prepare requires build; render requires build
and prepare; verify requires build, prepare and render. Every prerequisite is
the exact six-FileRef bundle result,tail,outer,stdout,stderr,exit. The root must
retain the actual external schema described below. Prior source maps must equal
the current map, so final reviews/wrapper sources belong in the initial freeze.

executable is null for build, otherwise the exact fresh copied EXE FileRef
from the completed build receipt. fixtures is null before render and then the
exact completed preparation's index FileRef. run_bundle is null except verify;
there it identifies ROOT/experiments/common-tiff-stack/render-bundle-1.json,
whose entire JSON value is the same authenticated six-role render prerequisite.

## Exact population and output paths

The build has one Cargo invocation. Its raw log must contain Compiling strehl-cli,
one actual fresh:false non-test bin artifact for strehl-common-input with the
exact src/bin/strehl-common-input.rs and CLI Cargo.toml, and the successful
build-finished JSON record. No M194h feature may be present. The source executable
must be under the new target; its exact bytes are copied to
build-3/strehl-common-input.exe and hashed again. No old executable is admitted.

The prepare child is PINNED_PYTHON -I -S -B independent-controls.py prepare
--output ABS/prepare-1/fixtures --source-sha256 ACTUAL_CONTROLS_SHA.
Its compact stdout must identify the actual index.json with schema
common-tiff-stack-independent-preparation-v1 and PREPARED_UNRUN_FIXTURES.
The index schema is common-tiff-stack-independent-fixtures-v1; its eight keys
are schema,source,spec,profile,recipe,recipe_sha256,generated_files,cases.
The controller binds source/spec to this source map, the exact existing548-byte
M165 profile, canonical recipe bytes, and the27 generated files:
recipe;12 standard TIFFs;wrong-size-third and altered-third TIFFs;12 manifests.
All actual fixture files are hashed before/after render. The deliberately
incorrect expected third-input FileRef inside case11's manifest is not used
to authenticate that actual fixture: the actual generated_files entry is.
Product must encounter and reject the discrepancy itself.

The twelve cases, in ordinal order, are constant-off, address-off, mixed-null-on,
noisy-off, noisy-on, noisy-placebo, noise-provenance, variance-one, profile,
camera-output, third-size, third-payload. Their exact modes are
off,off,on,off,on,placebo,off,off,off,off,off,off. Expected exits are six zeros
then six ones. Expected completed fold counts are3,3,3,3,3,3,0,0,0,0,2,2.
The controller retains these expectations; the independent checker must
establish actual folds and semantic refusal reasons from the saved receipts.
Every case command is exactly:

ABS_COPIED_EXE --stack-manifest ABS_FIXTURES/case-NN.json
--manifest-sha256 ACTUAL_MANIFEST_SHA --report ABS/render-1/case-NN/report.json
--observer FIXED_MODE

Each case directory is created fresh immediately before that one child.
Manifest output paths are fixed to case-NN/output.tiff. The controller accepts
only the declared final/incomplete/frame/stage file names, records actual refs,
and requires raw combined child log bytes to equal report.json. These fixed
product paths must not emit additional stderr diagnostics. The inherited helper
merges stdout and stderr; no independently separated product stderr claim is
made. Success needs the actual TIFF; expected refusal must lack it.
A child exit1 alone is insufficient: error/cleanup errors must be empty, actual
direct exit/EOF and post-exit drain complete, terminal Job accounting complete
and zero active, CPU monotone, and no generic termination attempt. Child log
and immutable child JSON are durable before any exit or capacity admission.
Available prefixes remain REFUSED on any later fault.

The verify child is PINNED_PYTHON -I -S -B independent-controls.py verify
--fixtures ABS/prepare-1/fixtures/index.json --fixtures-sha256 ACTUAL_INDEX_SHA
--run-bundle ABS/render-bundle-1.json --run-bundle-sha256 ACTUAL_BUNDLE_SHA
--output ABS/verify-1/check --source-sha256 ACTUAL_CONTROLS_SHA.
Its result.json and raw log must be byte-identical; actual exit must be zero;
schema common-tiff-stack-independent-verification-v1 and status
PASS_COMMON_RGB_STACK_SOFTWARE_INTEGRATION must be present. The controller does
not recompute its numerical predicates. Full saved-data verification is owned
by that independent source and remains limited to the fixed common-RGB fixture.

## Finite resource and publication contract

These are maximum allocated slices, not measurements or refundable balances.

Stage | CPU seconds | whole wall seconds | child committed-memory cap | retained files | observed scratch
build | 600 | 300 | 3GiB | 128MiB | 4GiB
prepare | 60 | 120 | 512MiB | 16MiB | none
render | 60 | 120 | 512MiB stage child ceiling | 16MiB | none
verify | 60 | 120 | 512MiB | 16MiB | none

Each actual product child is further limited to15CPU/15wall/256MiB; this
per-child ceiling does not multiply the render-stage60/120 grant. The stage
accounts its own parent CPU plus each whole child Job once. Polling supplies
live total user+kernel CPU; the final Job counter replaces live accounting
and is added once. No strict no-overshoot or complete final parent CPU claim
is inferred from a sample. The unchanged helper provides committed memory,
not RSS, and clean final active counts. A missing terminal Job denies completion.

Two CPU and three wall seconds are reserved for parent publication. Twelve wall
seconds for possible process cleanup are subtracted before launch, within the
same stage allowance; they are not an extra grant. Final positive publication
requires sampled parent plus all child CPU plus2 within the CPU cap and sampled
whole wall plus3 within the wall cap. Root independently binds actual terminal
exit and external whole wall, which must also fit the stage cap and sample+3.

The new environment removes inherited STREHL_/M194H_/RAYON_/BLAS/OpenMP and Rust
wrapper overrides through the held clean_env, then inserts only RAYON_NUM_THREADS=2
and CARGO_NET_OFFLINE=true. No native M194h FIXED_ENV knobs are inserted.
The actual consumer additionally uses its declared two-thread local pool.
The sanitized environment is constructed once per stage and supplied unchanged.

The retained build128MiB covers copied executable<=64MiB, log<=16MiB,
child record<=32KiB, compiler JSON<=16KiB inside the terminal, and all terminal/
external slots below. Cargo scratch is separate and initially fresh.
The held scratch scan permits only observed FileNotFoundError races after an
initially existing root; it records bounded samples/counts and never ignores
permission/reparse/nonregular/oversize errors. Its extent is explicitly
non-atomic observed bytes, not atomic full inventory or a disk-peak guarantee.
Retained-artifact scans remain strict, with the same labelled initial-absence
behavior as the held primitive.

A product case has436KiB simultaneous file slots:
output128 + output-stage128 + final64 + final-stage64 + incomplete4 +3frame16.
Its child log256KiB plus child record32KiB makes724KiB; twelve total8,688KiB.
Adding parent canonical/stage128KiB, extra reserved terminal64KiB, tail8KiB,
external outer64KiB+stage64KiB, stdout8KiB, stderr32KiB and exit1KiB gives
9,057KiB, below16MiB. The full remaining margin is not authority to add cases.
Prepare's4MiB fixture family and verify's4MiB checker family each fit16MiB
with their one256KiB log and32KiB child plus the same terminal/external slots.
Terminal JSON is capped64KiB, stdout advertisement8KiB, child JSON32KiB,
parent tail8KiB. No output contents or raw child logs are printed to tools;
root capture writes actual raw streams directly to files.

Stage outputs have schema common-tiff-stack-owned-stage-v1 and either
INITIAL_INCOMPLETE, REFUSED or COMPLETE_STAGE_UNVERIFIED. The final raw stdout
is only {status,result,tail}, with an actual canonical FileRef and tail FileRef;
a finalization refusal may instead advertise an error and null terminal.
Parent tail schema is common-tiff-stack-parent-tail-v1. It identifies canonical
bytes and actual post-publication samples plus final_external_allowance2/3.
A stale canonical positive is insufficient without the final advertisement,
actual external exit and tail.

Root external outer schema common-tiff-stack-stage-external-v1 has exactly:
schema,command,source,exit_code,timeout_terminated,elapsed_wall_seconds,
stdout,stderr,exit,stdout_bytes,stderr_bytes,scope.
Each raw role is an actual {path,bytes,sha256} FileRef; zero-byte stderr is
valid evidence, not a source binding. External stdout must exactly equal the
canonical compact JSON advertisement plus LF, exit text must mean0, the command
must equal actual recorded invocation, and source must identify executed
run-stage.py. Root retains this outer and exact release before the next stage.

Source validation is AST/symbol closure and metadata construction only.
No build, fixture, product, numerical checker or process-control commission
has run during authoring. Root independently reviews these changed interfaces
and source pins before any release.

A plain metadata-only serialization proxy of the widest render shape measured
64,236 bytes under the64KiB terminal slot:12cases, all eight possible case
artifact names, twelve child refs, two actual render prerequisites,384-character
prior paths,4KiB invocation,8KiB environment, two6KiB error placeholders and a
conservative4KiB inventory placeholder. This is a sizing construction, not a
controller or numerical execution, and not a universal error-text bound.
A first proxy incorrectly combined render's cases with verify's three
prerequisites and exceeded the slot; that impossible combined-stage shape was
corrected, not used to widen capacity. Verify has no case array. Actual encoded
capacity guards remain authoritative and any overflow remains operational refusal.

## Preserved first build and narrow second release

The first build actually refused before any executable, fixture, product case
or saved-data verification existed. Its child reported committed-memory rejection:
peak Job committed3,287,552,000 bytes versus the unchanged3GiB cap3,221,225,472.
The retained final Job has53 total processes and zero active; the pre-termination
observation has32 active. Owned generic termination succeeded, with no cleanup
errors. Direct exit and EOF were not observed before the rejection, and the
compile-only successful-completion policy remained UNVISITED. The12-byte raw
log contains only an incomplete Compiling prefix; it is not successful build
or compiler diagnostic evidence. No executable identity or failing compiler
subprocess can be inferred from that log.

The saved child interval is0.6560000000026776 seconds with5.171875 whole-Job CPU;
parent work sample is1.265625 CPU and1.6090000000112923 wall; actual external
controller interval is1.6569999999919673 seconds, exit1. These are retained
measurements, not a retrospective successful build or an estimate of Cargo's
optimal parallelism. Root independently captured and reviewed the attempt.

Before any second-source write, root preserved and read back all156 source
buffers,5,217,607 bytes, in work/frozen-source-1.zip,5,265,631 bytes/SHA256
 e63e9a7e5dd227b8de097588194e07224b0bcbf224559c08e4fff01da7c81db3.
The original build-1, target/common-tiff-stack-1 and first release/external
records remain intact. The old source-contract and independent product/control
intent are preserved. This source revision changes only controller/helper
Cargo argv to --jobs 2, target/common-tiff-stack-2, the copied build-2 executable
and build stage directory, and the helper's new SHA binding. The parent release
and external constructors supply their separately reviewed version2 names.
Prepare-1, render-1, verify-1 and every fixed product/checker command and case
remain unvisited and unchanged. No new control population is added.

The separate second build keeps600CPU/300wall/3GiB committed/128MiB retained/
4GiB observed scratch. The prior600CPU/300wall build allocation is retained,
not refunded using its small measured prefix; two entered build allocations
therefore sum1,200CPU/600wall. Memory remains a3GiB per-Job cap, not a6GiB cap.
Old and new scratch/output families are separate and both remain preserved.
This is an explicit build concurrency limit, not evidence that two jobs will
succeed or that the first process count proves a particular compiler cause.
Success still requires the full current zero-exit/EOF/empty-owned-Job,
actual Compiling, fresh:false executable and build-finished success evidence.
No build2, fixture, product, checker, native API or control has run during this
source amendment. Root must hold new source pins and release once before it runs.

## Preserved second build and third source release

Build2 did not hit the committed-memory cap. Its saved compiler log contains
three E0277 errors: LowerHex is not implemented for the sha2 0.11 digest array
at the old files.rs lines23,194,240. Cargo retained build-finished success:false
and actual exit101. No executable, fixture, product or checker was produced.
Direct Cargo exit and pipe EOF were observed; compile successful-completion
then refused its required zero-exit guard. This is distinct from a resource
failure and is not a successful intentional descendant-cleanup admission.
Generic failure cleanup observed one remaining owned member, terminated that
owned Job successfully and retained final active0 with no cleanup errors.
The earlier compile-cleanup after-accounting sample had3 active; these are
separate times, not contradictory or an executable-identity witness.

Actual retained whole-Job CPU is107.46875 seconds, parent CPU sample41.84375,
combined149.3125. Child wall is58.21799999999348; parent wall sample
59.905999999988126; actual outer59.937999999994645 seconds, exit1 without external
timeout. Peak Job committed1,342,238,720 bytes is below the3GiB3,221,225,472 cap.
Those are measured properties of this failed attempt, not a successful build,
consumer test or proof that two Cargo jobs are an optimum.
The child receipt is2,686 bytes/SHA256
 dc42ef310b6ef9cc5fd120d6e8f654d512e98a1c5d7618568099fcfe9e3d2ca8;
raw compiler log185,743 bytes/
 b543b27359f2cb0abd1200ecf5018580206775cbb3a7876acdfa8dc1bfc417f2;
outer1,591 bytes/
 9400e4b6b5e9ac0a2c9966aadd51625e9b660e8b08380bade56ef48da610e837.

Root preserved all156 build2 source buffers before edits through the original
source archive plus work/frozen-source-2-delta.zip,182,485 bytes/SHA256
 6acf8b148922310e66346901ba8e097feb977e597cdd9910f43df53bad2897e5.
The implementation author's separately reviewed correction is limited to
explicit lowercase hex encoding at the three digest serialization sites and
an unused import. Controller build3 changes only target/common-tiff-stack-3,
build-3 executable/output references and the matching helper source pin; the
helper changes only its exact target path. Cargo remains --jobs 2, placed
before --target-dir. All controller function bodies, cleanup/CPU/file readers,
per-attempt resource caps and12 product/checker cases remain unchanged.
Old build-1/build-2, targets and release/external files remain preserved.
Prepare-1/render-1/verify-1 remain fresh, with their exact original population.

A separately released build3 has the same600CPU/300wall/3GiB/128MiB/4GiB caps.
The first two complete600CPU/300wall allocations remain charged, so three
entered build allocations total1,800CPU/900wall. Per-Job memory is still3GiB,
not a cumulative or increased memory ceiling. Root additionally authorizes
one5CPU/7.5 active-wall metadata preparation slot: six fixed slots (two failed
build preparations plus current build/prepare/render/verify) total30CPU/45
active wall. The metadata schema and per-slot sampled tail allowance remain
unchanged. No control, build3, fixture, product, checker or numerical function
was run while authoring this source correction. Root independently reviews
new exact source pins and the third release before any execution.
