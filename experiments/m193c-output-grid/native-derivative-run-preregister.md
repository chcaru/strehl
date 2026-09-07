# M193c native derivative parent — source preparation

Status: prospective, source only. No source RAW bytes have been hashed or read,
no decoder/helper has run, and no build, TIFF or registrar execution is released
by this document. This adds only the native parent and this specification. It
does not change the held Rust derivative, its two private fixtures or the ten
grid fixtures. Architecture and colour scope remain those in `charter.md`,
`registration-derivative-design.md` and `derivative-controls-preregister.md`.

## Literal population and sequence

The sole source directory is `D:/personal/macro/coffee-bean`. In this order:

| Original index | Basename | Bytes |
| --- | --- | ---: |
| 0 | DSC00016.ARW | 39030784 |
| 13 | DSC00029.ARW | 39878656 |
| 26 | DSC00042.ARW | 40873984 |
| 39 | DSC00055.ARW | 40669184 |
| 52 | DSC00068.ARW | 39497728 |
| 65 | DSC00081.ARW | 39235584 |
| 78 | DSC00094.ARW | 39096320 |
| 91 | DSC00107.ARW | 39018496 |
| 104 | DSC00120.ARW | 38969344 |

These are non-holdout development inputs. Original52/local4 is the later product
anchor, not a private fixture index or a promise about the frozen registrar's
byte-selected reference. No directory search, replacement, XMP access or RAW
fallback is permitted. Before the first decode the parent streams and hashes
all nine originals, observing size, nanosecond modification time, Windows
attributes and file identity before/after each hash. It records the actual UTC
mtime with its subsecond precision. The historical listing is not used as an
invented current hash. Reparse points and multiply named selected identities
refuse. The nine exact names/sizes/order must hold.

The parent then writes the closed `m193c-registration-input-plan-v1` required by
the held Rust source. Its build is the absolute **copied executable** reference,
and its sha-only source map is the exact compiled build source map. Current run
controllers and the independent reader have a separately pinned execution
closure, not a claim that they were compiled into the executable.

For one original at a time: stream a new same-basename workspace snapshot,
compare its bytes with the complete plan and the original metadata, launch the
native child, authenticate its receipt and output, then launch the independent
reader while that same snapshot is still present. Recheck source/snapshot/TIFF
and observed child outcomes. Only after its independent read passes may the
snapshot be removed and the next original visited. A failed snapshot or frame
is retained. Deleted snapshot extents remain charged to the file budget.
Original files are opened read-only; no corpus metadata or attributes are set.

On the first refusal, record the original index, stage and original exception;
do not visit the remaining frames. Final read-only before/after authenticity
hashes are allowed for the already planned originals, including originals not
decoded. This is not a decoder visit. All planned original metadata and hashes
are rechecked at the end, and failures in that recheck are secondary errors,
never replacements for the first cause. An interrupted initial hash pass retains
the exact prefix it observed and performs no decode.

## Execution authority and the build association

CLI, with actual absolute interpreter and paths supplied by root:

```
python -B -X faulthandler -X pycache_prefix=<fresh-cache> experiments/m193c-output-grid/native-derivative-run.py --release <absolute-release> --release-sha256 <external-sha256> --output <absolute-fresh-directory>
```

Release `m193c-native-derivative-release-v1`, scope `native-nine`, is closed:
`schema,scope,source_bindings,inputs,commands,build,private_admission,reader,prior_work`.
`source_bindings` is a repository-relative path to `{sha256,bytes}` map. It must
contain the complete compiled source map, this parent/specification, charter,
the build driver, bounded process helper, owned M12 Job helper, and the reader
entry; root also lists every executable reader dependency. `inputs` are unique
repository-relative FileRefs for the exact build result, its execution release,
private admission, reader runtime and any reviewed prerequisite records.
The root's externally hashed release fixes this closure, not the producer. Parent
`-B` is mandatory so startup cannot write unaccounted bytecode outside its output.
`commands` contains the exact `sys.orig_argv` array, replacing only the token
`ACTUAL_EXECUTION_RELEASE_SHA256` with the externally supplied release hash.

`build` is a FileRef to the completed `m193c-bridge-build-v1` result. Parent
requires actual exit0, rebuilding evidence, no error/finalization error, stable
sources, the actual compiler artifact message, byte-identical original/copy,
successful observed listing and exactly one listed native test. It validates
the artifact source/manifest/package/target/test identity, compiler log rebuild
line and corresponding emitted compiler-artifact object. The build release and
actual observed compiler/list commands must agree. An arbitrary self-hashed
executable or success string cannot stand in for this association.

The required private admission is a small root-owned record, not created by this
parent: schema `m193c-derivative-private-admission-v1`, status
`PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY`, exact keys
`schema,status,build,private_result,independent_read,error,finalization_errors`.
The three references bind the same build and the genuine two-output private
producer/independent read. Root reviews/creates this only after those controls
pass; this parent merely consumes its externally pinned bytes and checks the
declared build association. It does not independently re-adjudicate that gate.

Native argv is exactly:

```
<copied-exe> --exact merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_native --ignored --test-threads=1 --nocapture
```

The actual compiled listing must authenticate this namespace before any RAW
read. Require exactly one named `... ok` line and one libtest summary with
1passed/0failed/0ignored/0measured; zero filtered execution never passes.
The parent removes every ambient STREHL/Rayon/OpenMP/BLAS/NumExpr override and
Rustflags/target override using the pinned `bounded-process.py`. It supplies
only `RAYON_NUM_THREADS=2` and `STREHL_M193C_DERIVATIVE_`:
`OUTPUT_DIR,INPUT_PLAN,INPUT_PLAN_SHA256,ORIGINAL_INDEX,SNAPSHOT`.
All paths are absolute; output directory is fresh, with an existing parent.
The primary receipt command/environment must match actual launch values.

## Independent per-frame consumer interface

This required implementation is separate and remains to be frozen by root.
Missing independent-reader source/runtime/admission prevents the first RAW read;
there is no producer-only shortcut through nine frames. No reader module or
numerical dependency is imported into this parent.

Release `reader` has exactly `script,runtime,commands`. Script and runtime are
repository-relative FileRefs; script is also in source_bindings. Commands is
nine literal argv arrays, one per original, with only
`ACTUAL_FRAME_REQUEST_SHA256` substituted at runtime. Each must invoke the
root-pinned interpreter with `-B -X faulthandler`, a distinct fresh
`-X pycache_prefix=<frame reader cache>`, the exact reader script, then
`--request <absolute-request> --request-sha256 <hash> --output <absolute-new-dir>`.
The reader runtime file pins its actual interpreter/module byte identities;
parent verifies the interpreter file against its `python_executable` FileRef.
That runtime record is closed by the reader's separate design, not invented or
regenerated by this producer. `-B` prevents nine copies of Python bytecode caches;
the fresh per-frame prefixes also prevent reading an earlier cache. Ambient
`PYTHON*` environment overrides are removed for this child. Reader runs under a separate owned bounded Job,
and its full CPU is added to the same nonresetting real budget.

Request `m193c-native-derivative-read-request-v1` is closed:
`schema,execution_release,input_plan,original,snapshot,primary_receipt,tiff,build,
reader_runtime,limits`. References are absolute; original is the selected plan
entry. Limits are exactly remaining `cpu_seconds,wall_seconds`, fixed
`committed_bytes=8589934592`, and remaining `metadata_bytes` (at most4MiB for
reader products). The input snapshot is live throughout reader execution.
Reader may produce only bounded metadata in its output directory; no second
TIFF/RAW/NPY dump, new render, sampler, registrar or fitted pixel transform.

Reader `result.json` has exact keys `schema,status,request,original_index,
snapshot,primary_receipt,tiff,active_sha256_u16_le,tiff_pixel_sha256_u16_le,
checks,invocation,error,finalization_errors`. Schema is
`m193c-native-derivative-independent-frame-v1`, success
`PASS_NATIVE_DERIVATIVE_FRAME_ONLY`. References must match the actual request.
`invocation` is a closed metadata object with
`argv,orig_argv,executable,cwd,xoptions,thread_environment,runtime,source_bindings,work`.
Require the exact actual `orig_argv` array, script-only `argv`, interpreter/cwd,
the two interpreter options and four string-valued thread caps. Runtime must
match the separately pinned runtime JSON, and source_bindings the complete
released source map. Work is a closed record with finite nonnegative
`cpu_seconds,wall_seconds` and integer `artifact_bytes,artifact_limit,
owned_array_peak_bytes,owned_array_limit,bounded_bytes_read`; these remain local
reader observations, not substitutes for parent process accounting. The full
metadata object stays in the bound independent result. This is the root-approved
source-only interface amendment to the earlier argv-list wording; no numeric
fixture, tolerance, population or decoder changed.
Checks are ordered `{id,pass,evidence}` records with literal true and these IDs:
`owned-visible-copy,active-shape,local-rggb,active-u16-bytes,active-row-u16-bytes,
scalar-black-white,green-normalized-wb,tiff-native-rgb16,
tiff-linear-camera-description,tiff-full-pixel-read,input-source-stability`.
They require an owned rawpy visible-array copy inside decoder lifetime; exact
full active and row u16 agreement; independent native shape/CFA/level checks;
the held WB tolerance; strict full native RGB16 TIFF reading and independent
canonical pixel hash. Rawpy postprocess is forbidden. Inherited absent-metadata
fallbacks are not reclassified as metadata presence. This result grants frame
agreement only, not a common-TIFF route, physical calibration or coverage.
The parent checks exact ordered IDs and associations; the separate independent
implementation/root review owns their arithmetic and powered controls.

## Budget, persistence and terminal result

`prior_work` has exactly nonnegative finite `cpu_seconds,wall_seconds,file_bytes,
metadata_bytes`. Root freezes actual previously spent real-stage work here;
zeros are valid only before any earlier real stage. Native reports inherited
plus new totals for the later registrar to consume. CPU includes parent process
startup/import CPU (process clock from zero)
plus **terminal** total user+kernel CPU from each owned child Job, failed calls
included. Wall includes this invocation's authentication, snapshots, callbacks
and all final persistence/rechecks, from the source's first monotonic observation.
Root also observes the complete outer launch; this parent does not claim its
first Python clock read predates interpreter creation. Totals cannot exceed1200CPU/1800wall,
4GiB new file extents/128MiB metadata and logs. A child receives remaining CPU
and at most240wall/16MiB live combined log. The pinned Windows Job API assigns
the suspended process before resuming and enforces8GiB **committed memory** for
the child tree; this is not measured RSS or a predecode shape check. Observed
polling can overshoot; terminal excess is a refusal, not an adjusted budget.

Storage counts cumulative maximum observed extents of every new output path,
including removed snapshots and prior publication files. It is an output-space
account, not disk-I/O traffic. The parent monitors the fresh output tree during
children and rechecks at exit; growth beyond a cap refuses. Metadata includes
logs/JSON/source/cache files; only the single raw snapshot and declared TIFFs
are binary-product exclusions. New symlinks/reparse paths refuse. On each
successful child exit all new products must be exactly its declared result,
TIFF or bounded reader metadata. Inputs and source snapshots also consume the
remaining output budget. There is no claim of a zero-overshoot disk quota.

Top result `m193c-native-derivative-run-v1` records exact invocation/release/
build/private gate, source/input bindings, nine-plan reference, original
observations, per-frame stage/launch/receipt/independent-read associations,
unvisited original indices, current stage/attempted original, first refusal,
work and original/secondary errors. Its `work` is explicitly the observation
before terminal publication; actual parent stdout retains
`work_through_final_checks`, including publication and the post-write hashes.
Root's observed parent exit/log remains the outer authority. Its successful
status is `COMPLETE_NINE_DERIVATIVES_AWAITING_COVERAGE`, never an admitted-nine
registrar or merge binding. It requires nine actual primary and independent
zero exits. A separate root consumer still authenticates the whole package
before the unchanged registrar; the original first-refusal/unvisited registrar
behaviour remains unchanged.

Publish the terminal result, then recheck every retained authority/product,
source closure, original identity/hash and full budget. A late failure preserves
the first terminal as `result.first.json`, writes a REFUSED result with the
original cause and secondary failures, and returns nonzero. A failed rewrite
is retained on stderr; no success exit is possible. A hash-only producer receipt
cannot grant independent TIFF or decoder authority.

## Prospective rejection cases (no calls performed)

Before native execution root must commission actual parent entry boundaries:
wrong build/list/source/exe pins; nonzero child and zero-test summary; stale
output receipt/changed actual TIFF; poisoned ambient overrides; changed source
metadata or copy bytes; independent nonzero/false check/mismatched snapshot;
missing reader; oversized log/time/storage; failed final source/hash recheck.
Use bounded private process/metadata fixtures and existing private TIFF bytes,
not additional renders or real RAWs. Valid/restored companions must reach the
same actual path. Mere helper parsing does not commission the top-level run.
Exact control source/commands and any independent consumer implementation need
a later root release. This source preparation makes no control-pass claim.
