# M193c complete private-stage owner

Prospective source preparation only. No process, compiler, helper, pixel reader,
RAW decoder or image writer is executed by preparing these files. Root must
freeze the complete source/command release before execution. The existing image
population remains exactly ten grid-product TIFFs plus two derivative-product
TIFFs. Reader byte mutations are instruments, not additional product renders.

## One observed encompassing process tree

`private-campaign.py` has owner and `--worker` entry points. The owner uses the
externally source-pinned `bounded-process.py` and its pinned owned M12 Job API
to launch one worker suspended, assign it to one encompassing Windows Job, then
resume. That Job contains the worker, both producer stages, both independent
readers and all their descendants. Nested stage Jobs provide bounded logs and
cleanup; their CPU values are never added to the outer Job CPU a second time.

Admission uses the actual terminal encompassing Job user+kernel CPU, zero active
processes and observed exit, plus owner process CPU from zero. It does not carry
forward the grid producer's pre-write or locally reported work. Shared limits
are600CPU/1200wall/128MiB of new artifacts. The encompassing Job enforces8GiB
committed memory, not RSS. Its limits are reduced by work already spent by the
owner; final checks include owner work after the Job completes. Polling is not
a no-overshoot guarantee: terminal excess refuses. Root also observes the outer
Python invocation, including interpreter startup before its first clock read.

All Python commands require `-B`; fresh pycache prefixes prevent old cache
inputs without writing duplicate caches. The owner/worker clear ambient
STREHL/Rayon/OpenMP/BLAS/NumExpr and Python overrides plus Rustflags/target
overrides. The sole direct Rust derivative stage receives `RAYON_NUM_THREADS=2`
and `STREHL_M193C_DERIVATIVE_OUTPUT_DIR=<fresh worker/derivative>`.

Exactly four stages run sequentially, once, with first-refusal stopping:

1. `grid_producer`: root's frozen `private-grid-run.py`, with all ten plans and
   the precision component preceding its ten product renders. Result
   `worker/grid/run-index.json`, schema `m193c-private-grid-run-v1`, status
   `COMPLETE_PRIVATE_OUTPUTS_UNVERIFIED`.
2. `grid_reader`: root's `independent-private-read.py`. Its controls execute
   before its actual ten-case/precision admission. Result at
   `worker/grid-reader/result.json`, schema `m193c-private-grid-admission-v1`,
   status `PASS_GRID_ADAPTER_PRIVATE_ONLY`.
3. `derivative_producer`: exact copied executable, `--exact
   merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_private
   --ignored --test-threads=1 --nocapture`. Exactly one named test and one
   1passed/0failed/0ignored/0measured summary are required. Result
   `worker/derivative/result.json`, schema `m193c-derivative-private-v1`, status
   `COMPLETE_PRIVATE_DERIVATIVE_PRODUCTS_UNVERIFIED`. It writes only
   `affine.tiff` and `signed-border.tiff` as product images.
4. `derivative_reader`: Curie's `independent-derivative-read.py --private`.
   Source32 and independent instrument controls precede admitting the two
   actual product TIFFs. Result `worker/derivative-reader/result.json`, schema
   `m193c-derivative-private-independent-v1`, status
   `PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY`.

The orchestration producer may use the remaining overall wall budget; its own
individual Rust children retain240wall/16MiB logs. Other stage children have
at most240wall/16MiB combined logs. Readers additionally receive at most
120CPU/240wall/32MiB artifacts, clamped to actual remaining work; these are local
early refusals, not separate replenished allowances. No retry/replacement or
partial passing population grants private admission.

## Root-frozen release and requests

Closed release: schema `m193c-private-campaign-release-v1`, scope
`private-twelve`, exact keys `schema,scope,source_bindings,inputs,commands,build,
reader_runtime`. Source bindings map repository-relative POSIX paths to
`{sha256,bytes}`. They include all compiled sources, owner/specification,
bounded process/M12 helper, each producer/reader entry and its actual executable
dependencies. Inputs are unique FileRefs to the actual compiled build,
prerequisite controller controls and every stage-specific release/design.
The build, copied executable, actual compiler/list observations and current
source closure are authenticated before the worker or any stage is launched.

`reader_runtime` is an absolute FileRef to the actual Python executable;
it intentionally lies outside the repository. Other references stay within
the repository. `commands` is a closed object containing one literal argv array
for each of `owner,worker,grid_producer,grid_reader,derivative_producer,
derivative_reader`. Actual original interpreter argv must match its released
array. Only three exact tokens can be substituted:
`ACTUAL_EXECUTION_RELEASE_SHA256`, `ACTUAL_GRID_REQUEST_SHA256`,
`ACTUAL_DERIVATIVE_REQUEST_SHA256`. Stage-specific producer release digests are
literal inputs, not another template language. All output/cache paths are fresh
descendants of the owner output. Worker output is exactly its `worker` child.

Grid reader argv contains `--request worker/grid-reader-request.json
--request-sha256 ACTUAL_GRID_REQUEST_SHA256 --output worker/grid-reader`.
Its closed request has schema `m193c-grid-reader-request-v1` and keys
`schema,execution_release,build,producer_result,producer_launch,reader_runtime,
remaining_limits`. Derivative argv adds `--private` and uses
`worker/derivative-reader-request.json`, token
`ACTUAL_DERIVATIVE_REQUEST_SHA256`, output `worker/derivative-reader`.
Its request has schema `m193c-derivative-private-read-request-v1` and the same
reference keys but calls its limits object `limits`.
Both limit objects have exactly `cpu_seconds,wall_seconds,artifact_bytes`.
`build` preserves the release's repository-relative FileRef byte-for-byte, also
matching the actual grid producer's build field. Other request FileRefs are
absolute and hash the actual completed input files.
The request binds the corresponding actual producer launch, not a constructed
successful observation. Each reader must report those associations unchanged.

Stage launch schema is `m193c-campaign-child-launch-v1`, exact keys
`schema,stage,status,command,environment,removed_environment_names,observation,
log,started_monotonic_ns,ended_monotonic_ns,error`. Success is
`COMPLETE_CHILD_EXIT_ZERO`; otherwise `FAILED_CHILD`. Observation is the actual
bounded helper result, including terminal Job accounting and log reference.
The parent records the environment additions and removed variable names;
normal inherited OS variables are not mistaken for experimental settings.

The grid wrapper's full source-owned result schema remains root's independent
responsibility; owner requires its fixed status, exact request/build/producer
associations, empty errors and completed controls/case/precision fields.
Derivative reader has its separately frozen source32/reader41/outputs shape;
owner requires all73 literal IDs in order, actual request/build/producer
associations and empty errors. The added41st instrument is the explicitly
registered refusal-helper false-acceptance tripwire, not another image. Its
invocation is the closed object `argv,orig_argv,executable,cwd,xoptions,
thread_environment,runtime,source_bindings,work`; owner checks actual orig_argv
and typed retained metadata. The two output rows are closed
`tiff,pixel_sha256_u16_le,shape,compared_sites,max_code_error`, requiring the actual
TIFF refs,22x30x3 shape,54/660 sites and the unchanged one-code bar.
Grid owner checks the actual45 control outcome records, ten case references and
all3712 precision observations, including the precision witness's checked resolved
path, SHA256 and extent against the actual producer precision result. The reader's
request FileRef may be repository-relative or absolute; both actual references
are verified and must resolve to the same path with identical SHA256 and extent.
The other exact build and producer associations are unchanged.
The source-pinned independent implementations own arithmetic and
control ordering. Owner does not convert a producer's booleans into a reader
pass, nor invent a second pixel oracle.

## Artifact and failure accounting

The owner polls the complete owned output tree during the encompassing Job,
including hidden files, live logs, unfinished files, reader mutations and
worker publication. It counts cumulative per-path high-water extents, retaining
deleted path charges. This is observed output-space accounting, not exact
write-I/O traffic; transient growth entirely between polls is not claimed.
Any retained excess fails at terminal inventory. Empty failed files are retained
with their actual zero extent and empty-payload digest. Failure-only inventory
salvage may itself run after a bound was exceeded; its observed additional work
cannot recover a passing status. No source/corpus file is
modified or removed. Reparse paths and escapes refuse.

Each launch/worker result retains the original error and unvisited stages. A
worker can only finish as `COMPLETE_PRIVATE_CHILD_OUTPUTS_UNVERIFIED`, never
issue a private gate. The owner independently consumes its completed actual
stage refs and corresponding12 product refs only after observed worker exit0
and terminal encompassing accounting. Product TIFFs must have12 distinct actual
file identities. Exactly the declared TIFFs may occur inside producer output
directories; independent reader mutation fixtures remain separately named.

Only then may owner publish `derivative-private-admission.json`, schema
`m193c-derivative-private-admission-v1`, status
`PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY`, exact keys
`schema,status,build,private_result,independent_read,error,finalization_errors`.
This is the prerequisite consumed by the later native parent. Overall result
schema `m193c-private-campaign-v1` succeeds as `PASS_M193C_PRIVATE_STAGE_ONLY`,
binding both independent reads, the derivative gate, actual encompassing Job,
source/input before-after bindings and byte inventory. It is not native,
common-TIFF, registration-coverage or quality admission.

Final `artifact-index.json` hashes every retained output except itself and
`result.json`; their final FileRefs and actual full work observation are emitted
in the outer stdout receipt. Sources, inputs, every indexed file, gate and
terminal result are rechecked after publication. Any late failure revokes the
canonical derivative gate and result, preserves their first versions, records
original/secondary failures and returns nonzero. This includes final stdout
payload construction, JSON serialization, write and flush in both worker and
owner. The first error remains primary; subsequent independent errors are
retained separately. A later refused publication retains the previous canonical
bytes in one of three bounded `.refused-N` slots after the immutable `.first`
version; this is failure evidence preservation, never another child execution.
Failed-status persistence and its stderr diagnostic are best effort; stderr
serialization/write/flush failure is caught and cannot interrupt the remaining
canonical revocation attempts. No canonical gate is usable
without the actual owner zero exit and matching final outer receipt.

Before intended private execution, root must review the actual owner entry and
its finalization paths against existing process instrument controls. Additional
cheap fixtures, if needed to power a boundary, use private metadata/processes,
not another product TIFF or RAW input. This document claims no executed pass.
