# Independent source review of camera-white coverage association

Status: VERIFIED source correspondence only; no blocking delta found. No
coverage helper, control, TIFF/RAW read or registration was executed. This
review does not admit a native result or authorize a coverage invocation.

Reviewed files:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `coverage-sensor-white-run.py` | 50,459 | `16f9e944673aa58b81727fabddadc7192a082cef149e950cd7dda24f217e51cf` |
| `sensor-white-coverage-preregister.md` | 6,580 | `12ec3389dacdb8ea79ba278fd14805e0399d2ec9230b53216b76df513d51e38c` |

The comparison base is held `coverage-sensor-run.py`, 46,924 bytes,
SHA `7732ce3a0529c31f3486732c365ab1d24f6021ca8fbce2db368ed75ba4a547f7`.
This review extends [its source verdict](independent-sensor-coverage-source-review.md)
and the [white-reader source verdict](independent-sensor-white-source-review.md).
The actual white reader/parent pins remain `6a318b439d1b9c5cb460808fc1388c7723d66a5adaf63b3303a6c791568a4bb8`
and `da1afc635851eaa8b60e29c1a6e677493b782d9e5e9cad19bad509d543de3ea1`;
their specification is `715c53c13002d3f4bb1cebaca0ca841459cda352599a202042d969d488fabb23`.

## Exact source scope

The complete read-only `git diff --no-index` was inspected. A separate
stdlib-only stdin script, run using the pinned Python with `-B -`, parsed
source bytes with `ast.parse`, compared top-level definitions using
`ast.dump(..., include_attributes=False)`, extracted literal tuples, and
hashed the two reviewed files. It did not import or execute their code.

Only `boot`, `native_authority`, `worker` and `parent` change. There are no
added or removed definitions. The other16 definitions are identical,
including budget, runtime, fixture/control, Fraction gauge, refusal extraction
and publication helpers. The worker and parent changes are only their
schema strings. The original eight coverage control IDs are unchanged.
The new local eleven native, eight domain and ten white IDs exactly match
both the held white reader and native parent. Native check6 has the intended
`scalar-black-camera-white` label.

The original five fixture TIFFs, frozen M193b/reference copies, constructor
population, thresholds, measured-support denominator, gauge direction/order,
first refusal/unvisited behavior and all resource limits therefore remain
unchanged by this source delta. It does not reinterpret the separate0.1
native-pixel output-map bar or add an image-quality score.

## Native and white-witness association

`boot` requires explicit sensor-white coverage release/scope and adds the
new coverage specification plus exercised white reader, parent and their
specification to the required source set. Historical source requirements
remain. The exact original argv, external release digest, pinned interpreter,
fresh cache/output, metadata parsing and source checks retain their original
implementation. The old native module remains the pinned standard-library
utility dependency; coverage does not call its RAW/native path.

`native_authority` now requires the new complete sensor-white native parent,
release, per-frame reader and request identities. It still requires nine
complete rows, all expected native checks, no error/finalization error,
no first refusal or unvisited input, successful actual child observations,
source/runtime/request/plan/TIFF associations and root terminal carry.
The ten additional white groups must be present in exact order as closed
`{id,pass,evidence}` records with literal true PASS and dictionary evidence.
Their23 metadata calls are not rerun by coverage. The detailed executed
attempt records remain part of the native reader's result and actual audit;
coverage does not mistake ten group labels for23 independently performed
coverage operations.

The new eleven-key `white_authority` is read from native check6 and checked
against the actual rawpy metadata retained in check1. CFA indices and both
generic/camera metadata have explicit integer, extent and range checks.
Selected white must be a positive u16-range integer; generic/camera/used-index
witness values must exactly match that metadata with genuine integer types.
The used set is derived from the recorded indices, and every used camera
channel must equal the selected value. The witness's finite primary scalar
must equal the primary receipt's scalar and selected value. Sixth-check
black/white are also associated with the primary values. The primary's full
typed source and black/WB admission remain the prerequisite native reader's
boundary; this adapter does not replace those checks with a new normalization.

Method, selection and forbidden-fallback identifiers are exact, and both
physical-calibration and primary-metadata-presence claims must be false.
`generic_matches_selected` uses identity against the actual Boolean equality;
it accepts a truthful false value and rejects integers or a stale flag.
Thus this adapter does not accidentally reintroduce the failed generic-white
equality or accept whichever generic/camera value happens to match.

The actual successful reader witness shape produced by
`validate_native_metadata` matches these fields. No reader/parent/schema
mismatch was found in the new association code.

## Historical and resource boundaries

The unchanged original0 branch still requires the original historical
primary receipt, TIFF, snapshot and launch, the full-nine-plan equality and
three reuse controls. It does not reuse a failed independent read. All nine
independent commands must belong to the new actual native release, while
the other eight primary outputs must be fresh. The original native and
sensor-native refusals remain historical failures. The retained snapshot is
only an association here; coverage adds no RAW reopen or deletion.

Root console/outer/exit and adjacent-DLL endpoint records, actual source/input
closure and final-work carry retain the previously reviewed code. The worker
still reserves all nine TIFF extents plus5 MiB before constructor snapshots,
without refund; original0's reused TIFF is not exempt. The nonreset total
1200 CPU/1800 wall,4 GiB file/128 MiB metadata, child240 wall/16 MiB log/8 GiB
committed-memory bounds and post-publication budget checks are unchanged.

No source correction is requested. An actual complete native result and a
separately frozen coverage release, concrete commands, source union, input
refs and full conservative carry are still required before execution. The
only prospective success is `COMPLETE_NINE_INPUT_REGISTRATION_ONLY`; it
does not establish physical sensor calibration, a qualified common-TIFF
route, alignment truth, or a successful final render. Any constructor
refusal must retain its actual first failure and unvisited population.
