# Common-TIFF dimensions stage execution contract

2026-09-08. SOURCE ONLY. This contract releases no build, fixture generation,
product or checker execution. Root separately freezes the complete source map,
metadata releases and actual commands before each once-only stage. No retry or
automatic variant is authorized. Old common-TIFF and sampler artifacts remain
immutable; no old numerical study or process-control suite is rerun.

## Reused process and publication mechanisms

run-stage.py derives from ../common-tiff-stack/run-stage.py29852B,
SHA25625d9b11cd0b99c1720ff460a4237209eaa9c6a36a8ffa8ade50afa608f41cb05.
It retains the same source/input readers, release/prerequisite structure,
source closure, live parent+Job accounting, child-terminal retention before
admission, compile-artifact proof, exact raw-byte associations and final tail.

It authenticates the held M194h driver40626B,
SHA256b505a2fff0024691d98088c599f7f554c1543268de09c836a6bc1fe6c17b7410,
then evaluates its definition-only module. No old main/authority/metadata
controls/science is called. Selected reused methods are same-buffer read,
write_new/atomic, source_closure, scan, Budget, clean_env, load_process and
admit_compile_cleanup. Changed globals are START,HERE,SELF,TARGET,STAGES,
OUTPUTS,BUILD_PROCESS,BUILD_PROCESS_SHA,FIXED_ENV and TERMINAL_CAP.
TERMINAL_CAP is256KiB for scanner reservations; seven actual atomic calls
pass that cap explicitly because the inherited Python default was bound64KiB
at definition time. The atomic publication algorithm is unchanged.

bounded-build-process.py16517B,
SHA2561d52b3cd9a4f218b886049f9fcc29b95164e64eb7afb2717a1f3f9646987f31d,
differs from the old common-TIFF helper16512B/d27374f6b0fe00c53d2f7110f2ebd553067cb3e2c772d3076547b5f2db9e3d94
only by target/common-tiff-stack-3 -> target/common-tiff-dimensions-2.
Reversing that one string restores the entire original buffer. The full helper
is held; no process/pipe/Job/cleanup body is rewritten.

Only build child0 uses the compile helper. It requires the literal Cargo argv,
direct exit0 and EOF before any intentional cleanup of its own remaining Job.
Its existing five-second cleanup and fresh final-zero accounting are required.
Observed PIDs are never kill targets; no executable-identity claim is added.
Natural versus intentional completion remain distinct. Every nonbuild child
uses the original strict M193c helper47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b.
Generic emergency termination cannot admit even an expected semantic refusal.
The same closed M12 Job AST definitions/signatures are selected; no native
launcher, arbitrary process census or new control framework is introduced.

## Exact fresh stages, commands and authority

ROOT is this repository; HERE=ROOT/experiments/common-tiff-dimensions.
TARGET=ROOT/target/common-tiff-dimensions-2 must initially be absent.
Directories are build-2,prepare-1,render-1,verify-1 under HERE, all fresh.
Actual executable is HERE/build-2/strehl-common-input.exe. Existing CLI defaults
and fixed two-thread environment are retained.

Controller invocation from ROOT:

    PINNED_PYTHON -I -S -B ABS_RUN_STAGE --release ABS_RELEASE --release-sha256 ACTUAL_RELEASE_SHA256

Closed ten-key release: schema,stage,source_bindings,inputs,command,children,
executable,fixtures,run_bundle,prerequisites. Schema
common-tiff-dimensions-stage-release-v1. command is exact sys.orig_argv with
only ACTUAL_RELEASE_SHA256 replaced by the actual hash. stage is build,
prepare,render,verify; children contains exact {command,expected_exit_code} rows.

Positive source map: canonical repository-relative key ->{bytes,sha256},
<=512 entries,<=4MiB each,<=16MiB total. All listed bytes and the inherited
compiled-source closure are checked before/after the stage. Mandatory current
controller/helper/this contract/charter/implementation contract/independent
controls/spec and held driver/strict process/M12 helpers are bound. Root must
include final source reviews and its preparation/capture wrappers in the same
initial map. No source-map extension between stages.

The compiled closure covers root Cargo.toml/lock, local crate manifests/Rust,
explicit compiled defect-map text and inherited include!/path closure. It is
not a registry/native-DLL/toolchain-cache immutability claim. Cargo is locked
and offline; actual cargo/rustc and Python input identities are retained.
inputs remains<=128 positive unique FileRefs,<=64MiB each,<=256MiB aggregate.

Each prerequisite is exactly {result,tail,outer,stdout,stderr,exit}. Build has
none; prepare requires build; render requires build+prepare; verify requires
all three. Prior source maps must equal the current map. executable is null
before build, otherwise the exact copied executable from its prior result.
fixtures is null until render, then the exact prepared index. run_bundle is
null except verify, when HERE/render-bundle-1.json must contain exactly the
authenticated six-role render prerequisite.

Build command, exactly:

    cargo build -p strehl-cli --bin strehl-common-input --jobs 2 --target-dir ABS_TARGET --message-format=json-render-diagnostics --locked --offline

Require a Compiling strehl-cli line, exactly one fresh:false non-test bin
compiler-artifact with actual source/manifest paths, successful build-finished
record and no M194h feature. Copy only that actual target executable,<=64MiB,
to the fresh build-2 path and verify its hash. No stale-cache or old-binary
substitution is admitted.

Prepare child:

    PINNED_PYTHON -I -S -B ABS_CONTROLS prepare --output ABS_HERE/prepare-1/fixtures --source-sha256 ACTUAL_CONTROLS_SHA

Verify child:

    PINNED_PYTHON -I -S -B ABS_CONTROLS verify --fixtures ABS_HERE/prepare-1/fixtures/index.json --fixtures-sha256 ACTUAL_INDEX_SHA --run-bundle ABS_HERE/render-bundle-1.json --run-bundle-sha256 ACTUAL_BUNDLE_SHA --output ABS_HERE/verify-1/check --source-sha256 ACTUAL_CONTROLS_SHA

Prepare stdout is the exact independent-preparation advertisement:
schema common-tiff-dimensions-independent-preparation-v1,
status PREPARED_UNRUN_FIXTURES, cases24, generated_files59, actual index FileRef.
Verify final is check/result.json<=1MiB, exactly equal to raw child log:
schema common-tiff-dimensions-independent-verification-v1,
status PASS_COMMON_RGB_DIMENSIONS_SOFTWARE_INTEGRATION and
software_integration_complete=true. Missing operands or partial/REFUSED results
do not satisfy this dependent stage.

## Fixed fixtures and product population

Index9 keys: schema,source,spec,profile,recipe,recipe_sha256,legacy,
generated_files,cases. Schema common-tiff-dimensions-independent-fixtures-v1.
Exact controls/spec map identities,548-byte M165 ICC and canonical recipe
hash are required. generated_files has58 entries:33 TIFFs,24 manifests and
recipe; index makes59 files. TIFF names are mean-two-0..1,mean-five-0..4,
mean-eight-0..7,odd-address-0..4,odd-offset-0..4,odd-noisy-0..4,
count-nine-extra-0,last-geometry,last-file-hash, each with .tiff.
Manifests are case-00.json through case-23.json. Single TIFF<=1638400B,
generated JSON<=64KiB,index<=256KiB,total<=32MiB. Every actual generated file is
authenticated around rendering, independently of deliberately wrong claimed
hashes inside negative product manifests.

legacy is a closed index/report/manifest/output bundle. The known old index,
report and output identities are literal in both sources; the manifest link
comes from the authenticated old report. Its old input pixels/output are read,
not copied into the new fixture family. No broader old study is rerun.

Case row11 keys: ordinal,id,fixture_kind,version,observer,expected_exit_code,
expected_folded_frames,manifest,command,output_path,report_path. Source constants
close every row, including version1 only at08,17,18; all others version2.
IDs in order:
00 mean-two-min;01 mean-five-odd;02 mean-eight-max;03 odd-address;
04 odd-offset;05 odd-noisy-off;06 odd-noisy-on;07 odd-noisy-placebo;
08 legacy-constant;09 count-zero;10 count-one;11 count-nine;12 width-low;
13 width-high;14 height-low;15 height-high;16 width-u32-overflow;
17 legacy-count-two;18 legacy-odd;19 duplicate-input;20 wrong-profile;
21 wrong-proxy-variance;22 last-geometry;23 last-file-hash.
Modes off,off,off,on,on,off,on,placebo, then off for08..23.
Expected exits nine zeros then fifteen ones.
Expected folds2,5,8,5,5,5,5,5,3, then thirteen zeros, then4,4.
These are expected fields; actual image/fold/noise/offset/refusal truth belongs
to the independent checker, not this controller.

Each product command is fixed:

    ACTUAL_EXE --stack-manifest ABS_CASE_MANIFEST --manifest-sha256 ACTUAL_MANIFEST_SHA --report ABS_HERE/render-1/case-NN/report.json --observer FIXED_MODE

No CLI input, geometry, noise or population value is tuned here. A case directory
is created immediately before its only launch. Exact expected exit and clean
terminal Job/EOF are required. Product log equals final report raw bytes.
A successful process must retain output.tiff; a registered refusal must not.
Semantic wrong-reason/fold failures are adjudicated by the independent reader.
An operational failure stops the producer stage; absent remaining cases cannot
be called semantic passes.

## Resource ledger and simultaneous storage

Root-adopted finite stage ceilings; CPU includes parent process+owned child Job
once, not wall-derived CPU. Job memory is the child-tree committed-memory bound,
not a measurement or a cap on the controller's own address space.

| Stage | CPU / whole wall seconds | Child Job memory | Retained family | Fresh scratch |
|---|---:|---:|---:|---:|
| build |600 /300|3GiB|128MiB|4GiB|
| prepare |30 /60|1GiB|34MiB|0|
| render |180 /240|1GiB|128MiB|0|
| verify |60 /120|1GiB|19MiB|0|

Every render child<=20CPU/20wall; prepare child<=20/40; checker<=45/90.
Actual dynamic remaining checks can grant less and refuse later launches.
Separate five-second cleanup and2CPU/3wall publication tail remain inside the
stage envelope. No unused allocation authorizes another invocation.

Raw child log ceiling: build16MiB,prepare/render256KiB,verify1MiB.
Each durable child JSON<=32KiB. Parent canonical/result-stage each256KiB,
tail8KiB. Stage root stdout<=8KiB; external stderr32KiB,outer64KiB,exit1KiB
are retained by root outside the stage directory in its metadata family.

Product v1 output/stage128KiB, report/stage64KiB,three frame slots16KiB each.
Product v2 TIFF/stage6*source_set_pixels+64KiB, report/stage192KiB,eight frame
slots16KiB each. Every incomplete4KiB. The fixed-source grid, not a malformed
manifest's oversized axis, defines capture caps. Retain any bounded orphan
stage for refusal diagnosis; its presence cannot turn a failure into success.

Using the maximum v2 family3805184B for every case (deliberately wider than the
actual schedule), the complete prospective physical-file maxima are:
build84451328B,prepare34381824B,render98934784B,verify18391040B.
They include full declared fixtures/checker family, child logs/receipts,
simultaneous parent stages and tail. Inherited Budget.scan additionally
subtracts3*256KiB=786432B as a terminal reserve even when observing actual
terminal files. Margins after this extra reserve are respectively48979968,
483328,34496512,745472B. Verify was therefore raised prospectively from18 to19MiB
before execution;16MiB checker+1MiB log+transport+extra reserve does not fit18MiB.
No observed overrun or scientific threshold change motivated this arithmetic.

Root owns four fresh metadata construction slots10CPU/20wall each plus the
already spent build1 constructor10/20:50CPU/100wall cumulative, with the same
32MiB metadata/archive family. The full failed build1 reservation600CPU/300wall
remains charged; the fresh build2 receives600/300 once. The unchanged later
stages270/420 make cumulative stage reservations1470CPU/1020wall. Independent
failed-build review retains10CPU/20wall/64MiB read/2MiB write; the separately
reviewed scratch control phase reserves5CPU/10wall/1MiB read/1MiB write; its
separate capture wrapper reserves another5CPU/10wall/1MiB read/1MiB write.
Their combined outer interval is bounded by20wall. Earlier
source-preparation/formatter records remain; no aggregate CPU for them is
invented. Wall reservations are ceilings, not forecasts, and no old grant resets.

## Terminal capacity, timing and failure qualifications

SOURCE-DERIVED metadata construction only: exaggerated normal complete parent
includes108 actual case artifact roles from the fixed schedule,24 child refs,
all three prior six-role bundles,24 operations,4KiB command,8KiB environment
and64KiB allowance for remaining fields. Every FileRef uses512 ASCII
backslashes (worst escaping in that stated path domain), a bounded extent
1638400 and a64-character hash. Encoded result
255854B fits262144B, margin6290B. FileRef proxy itself1128B includes newline.
This is a normal-shape bound conditional on the fixed release/output paths
being ASCII<=512 characters, not a universal arbitrary-path/failed-record bound.
Root must inspect its actual release paths; the writer still enforces256KiB.
The proxy used no controller functions, images, process calls or numerical code.
The independent reviewer must check role/field coverage before source hold.

Product N8 normal final192KiB sizing is separately required from the independent
fixture/product source read. Do not confuse this parent bound with that receipt.
Oversized/error-stage metadata may refuse; bounded detailed traceback suffix,
full traceback hash/extent and durable prior canonical/child files remain.
No unbounded retry is added to make an exhausted terminal fit.

Child result is saved before CPU or expected-exit admission. Invalid/nonmonotone
Job accounting prevents further work. Final parent canonical is written before
a tail records actual parent CPU sample, completed Job CPU, no live child,
accounting flag and2CPU/3wall allowance. The root outer must prove actual exit0,
timeoutfalse and whole wall<=sample+3 and<=stage cap. No sample alone is complete
whole-process CPU. Exact child user+kernel accounting is counted once with
parent CPU; the controlled observer never substitutes elapsed wall for CPU.

Parent result schema common-tiff-dimensions-owned-stage-v1 and successful
status COMPLETE_STAGE_UNVERIFIED. Tail schema
common-tiff-dimensions-parent-tail-v1. External schema
common-tiff-dimensions-stage-external-v1, exact keys schema,command,source,
exit_code,timeout_terminated,elapsed_wall_seconds,stdout,stderr,exit,
stdout_bytes,stderr_bytes,scope. The external command/source/three raw refs,
exit.txt and source hash must associate to the same invocation.
stdout is exactly the compact {status,result,tail} advertisement, not a copy
of the padded parent result. No parent CPU field is invented in the outer.

Failure leaves its exact prefix and nonzero disposition; INITIAL_INCOMPLETE,
canonical positive alone, unlinked files or stdout text cannot override actual
terminal/outer refusal. Refusal-preserving behavior is reused from the held
controller; no new publisher/process-control commission is claimed.

The exact metadata constructor and observed output are retained in
stage-layout-construction.md and must be included in the source release.

## Build2 operational correction and compositional source closure

Build1's eight negative evidence files remain committed at834a3c61; the exact
original181-source archive remains committed at8017d2f3. No product executable,
fixture preparation or render resulted from that attempt. Its observed scanner
canonical mismatch has an unknown historical cause; source-derived race
possibility and the later missing-path observation do not reproduce it.

Only build2 installs the separately pinned scratch-scan.py dispatcher into the
private imported primitive module. The source is authenticated from the positive
map and checked against its literal SHA before execution, before Budget creation.
The shim clones the original scan code with a private owned binding using
no-follow ancestry and strict resolution. Missing scratch entries can use the
original FileNotFoundError recovery; extant canonical mismatches, reparse,
permission, nonregular, containment and capacity errors still refuse. Only the
exact TARGET may select tolerance. Retained scans delegate to the exact captured
original function; nonbuild stages do not install the shim at all.

The helper's sole change from build1 is its literal Cargo target1-to-target2
guard. Process accounting, five-second cleanup, direct-zero/EOF admission and
all scientific/product/checker choices remain unchanged. Capture uses build
release/external suffix2; later stage suffixes stay1 and their prerequisite
bundle selects the actual build2 result, tail and streams.

Metadata preparation writes fresh work/source-freeze-2.json and
work/source-2-delta.zip exclusively. It authenticates source-freeze-1.json
(25815B, SHA2567b37fe67c8cee38e655d461ee9c5b498b60808b834d2b97d61ee3be9a76b6de4)
and its exact source-1.zip(5661467B,
SHA2560dbe11b91a4351e041bff97201506600fee03ab3b37bf1b32e5b34cd63016770).
The new freeze schema common-tiff-dimensions-root-source-freeze-v2 has exactly
schema,source_bindings,base_freeze,base_archive,delta_archive,changed_or_new,scope.

The full current map keeps every original key. Changed original entries are
restricted to this controller, compile helper, prepare/capture wrappers, this
contract, the independent checker's build-path adaptation and its matching
independent-spec.md explanatory append(seven original entries). New entries are
the exact named shim/control/spec/rationale/review/addendum files, including
scratch-control-capture.py. Delta ZIP
contains only changed/new entries. Constructor verifies the base's unique
complete inventory, all181 original member hashes, the delta inventory and
every current source reconstructed as delta when named, otherwise base. Base
archive ordering may differ from sorted JSON-map ordering; its complete original
bytes/hash still bind its order. No original source buffer is overwritten in
either archive.

Later constructors require the same frozen2 map and unchanged base/delta
identities. All stages bind the complete revised map; no additions after freeze.
The new archive/records remain inside the existing32MiB metadata family.
No result-size increase is required: the parent already records references to
source-bearing release/metadata, not duplicate source archives or full maps.

Root must first accept the actual fixed16 scanner groups(17 dispatcher calls,
including two metadata variants in the reparse group) and independent
scratch-scan-source-review.md. Root also owns build2-source-review.md for the
complete controller/constructor/capture/contract delta. These notes and the
independent control source/spec enter the full map only when final. Source-only
syntax and archive design checks are not those controls and authorize no build.
