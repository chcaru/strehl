# Independent review of the sensor-native coverage association

Status: VERIFIED source correspondence only. No blocking defect found in the
reviewed delta. This is not an executed coverage result or native admission.
The reviewer did not import the subject or its helpers, run controls, launch
registration, read RAW/TIFF payloads, or change any held source.

## Reviewed bytes and boundary

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `coverage-sensor-run.py` | 46,924 | `7732ce3a0529c31f3486732c365ab1d24f6021ca8fbce2db368ed75ba4a547f7` |
| `sensor-coverage-preregister.md` | 9,036 | `4176be1c68d461d41fcd3629701f213420a29159254218043c92a83fda6cb521` |
| Original `coverage-run.py` | 40,858 | `080bafe2900617a6b4d66f9d818a92c44d0ab53df8cfb814566b3888fe30883d` |
| `native-sensor-derivative-run.py` | 53,533 | `10ec80290bc7bb5c2e7fc140cb831d539e517844281b40b372055b409113a1ed` |
| `independent-sensor-derivative-read.py` | 68,424 | `eeed1ea3c45927f81e34d99ca31dc57715f898b718dfef26dcf0ea2cddf3fbe7` |
| `sensor-domain-reader-preregister.md` | 15,934 | `7450a8e2ecef2b5c3c883e63fd2f636dc84c5bc6ac07df80fc1277bf5bdf7125` |

This review reads the complete old-to-new diff and new coverage specification,
then checks the changed associations against the held sensor parent's
`first_reuse`, `run_one` and `independent_result` implementations. It extends
[the original coverage source review](independent-coverage-source-review.md),
whose accepted computation and resource boundary remain applicable. The
[sensor reader source review](independent-sensor-domain-source-review.md)
separately covers the owned sensor-domain copy and its eight prospective
controls. None of these source verdicts stands in for a future executed result.

## Mechanical scope check

The actual read-only command was `git diff --no-index --
experiments/m193c-output-grid/coverage-run.py
experiments/m193c-output-grid/coverage-sensor-run.py`; its exit 1 reports the
expected source difference. An additional standard-library-only script was
sent on stdin to the pinned Python 3.12 executable with `-B -`. It parsed both
files using `ast.parse`, compared each top-level definition using
`ast.dump(..., include_attributes=False)`, extracted literal ID tuples with
`ast.literal_eval`, and hashed source bytes. It did not execute their ASTs.

The only changed definitions are `boot`, `native_authority`, `worker` and
`parent`; there are no added or removed definitions. The other 16 definitions
are identical, including `make_budget`, `refusal_observation`,
`associate_refusal`, `inverse_then`, `gauge_rows`, `runtime`,
`private_controls` and `publish`. Within `worker` and `parent`, the diff changes
only the request/result envelope schema strings. The eight `CONTROL_IDS` are
identical. The new local eleven `NATIVE_CHECK_IDS` and eight `DOMAIN_IDS`
exactly equal the corresponding literal tuples in the held sensor parent.

Thus this delta does not change the five fixture TIFFs, eight coverage
controls, actual frozen constructor calls, registration thresholds, source
support denominator, Fraction gauge computation, or failure extraction. It
does not amend the meaning of the separate 0.1 native-pixel output-map bar.

## New authority associations

`boot` requires the explicitly versioned sensor coverage release and adds the
new sensor parent, reader and two specifications to its required source set.
It retains the original pinned utility, registrar, reference, fixture,
contract and process-helper sources. It still verifies the actual executing
coverage bytes, exact released original argv, interpreter options, root cwd
and owned fresh output/cache. The old native module is used for its existing
standard-library utility interface; the coverage path does not call its
native producer or RAW-reader methods.

`native_authority` requires a complete sensor-native result with nine rows,
no error, finalization error, first refusal or unvisited input. The new native
release identity must agree. Existing root-observed console/exit/outer checks,
adjacent-DLL endpoint association, and source/input before-and-after closure
remain. The carried work must cover the last native stdout and the previous
native wall carry plus the actual outer elapsed observation. The complete
exercised native source map must be present in the coverage source map.

Every original index/name must reach `COMPLETE_FRAME_INDEPENDENTLY_READ`.
Each reopened independent result must carry the new sensor result schema and
PASS status, exact eleven ordered true checks and eight ordered true domain
controls. The independent result's file refs, request, active hash, invocation,
source map and runtime agree with the native row and release. Its command
must equal that ordinal's released reader command after replacing the actual
request digest. Both child observations require the existing successful
process predicate and bound logs. Actual TIFF bytes are hashed and all nine
filesystem identities must be distinct.

These checks are compatible with what the held sensor parent actually writes.
In particular, all nine independent reads are fresh commands from the new
attempt, even though the first primary image and its primary-child observation
are historical. The source does not accidentally require a ninth fresh Rust
primary render or a successful historical native parent.

## Historical first image remains historical

The new release's exact seven `reuse_first` metadata refs must be released and
byte-valid. The historical result remains the literal
`native-derivative-1/result.json`, old-schema `REFUSED`, with original0 first
refusal, its one retained row, and the other eight indices unvisited. The
separate historical frame and primary-launch records must equal that result's
contents. Fresh and old complete nine-input plans are reopened and must agree
in parsed contents and actual digest/extent. The three required parent reuse
controls include the specific later-entry plan-refusal record.

Only ordinal0 may have `primary_reused=true`, retained snapshot true and
snapshot deletion false. Its provenance must bind those exact historical
refs, the same three controls, and the literal historical CPU-scope statement.
Snapshot, primary receipt, primary launch and TIFF must equal the old row.
Its fresh sensor-reader request and actual primary receipt use the old plan
ref. The other eight rows require a fresh primary, deleted owned snapshot,
no reuse provenance and the new plan ref. This matches the parent's explicit
`plan_ref` substitution in its one permitted reuse branch.

The retained original0 snapshot pathname is checked as metadata. It is not
opened by this coverage association code. Deleted fresh snapshots are not
reopened or recreated. The worker receives admitted TIFF/receipt/reader
descriptors and the two reuse flags, without a RAW payload ref. The historical
independent refusal and outer records are byte-bound here; their detailed
semantic admission remains the completed sensor parent's `first_reuse`
boundary, whose source and terminal result are prerequisites. Coverage does
not relabel that old refusal as success.

## Preserved resource and interpretation limits

The unchanged budget reserves the sum of all nine TIFF extents plus 5 MiB
before starting the worker, without refund. Reusing a historical TIFF does
not remove its new constructor snapshot cost. Actual fixture writes and
retained artifacts are still separately charged. The unchanged total
1200 CPU/1800 wall, 4 GiB file and 128 MiB metadata limits carry prior work;
the existing child caps and terminal Job accounting remain in force. The
unchanged publication path performs its full recheck before final stdout and
its final budget check after flushing.

A later release must bind the actual complete native result, exact source
union, metadata inputs, two concrete commands, fresh paths and conservative
root carry. No such future release or runtime result is admitted by this
source review. Its input set must preserve the stated metadata/TIFF scope;
it must not insert corpus RAW payloads merely as convenient generic inputs.

The prospective success remains `COMPLETE_NINE_INPUT_REGISTRATION_ONLY`.
It is neither physical sensor-domain qualification nor a common-TIFF route,
alignment truth, final merge render, or quality claim. The unchanged frozen
M193b constructor may still refuse at its first unsupported input; the
existing failure/unvisited recording remains the authority for that outcome.
No numerical method, control population, threshold, product default or
historical refusal was changed for this review.
