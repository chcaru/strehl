# M149 independent verification report — M135 → M138 adapter

**Verdict:** SEND BACK / defects found  
**Reviewed adapter SHA-256:** `6d4366533b2b12fc1e03c44d96faa1af3d7e89e6c6f35ed5420dd33b8e5e6290`  
**Reviewed production bundle SHA-256:** `fa3f5135693766114aed6db58bfa74197236e5a51b454a421951f645cdcb27ea`

## Critical defect 1: artifact hash/use TOCTOU

Locations in the preserved adapter: `m138_adapter.py:256` and `m138_adapter.py:469`.

`verify_artifact_ref` hashes a path and returns the path. `load_core_payload` later reopens that path. The bytes parsed by the core are therefore not necessarily the bytes whose digest was accepted.

Fixture:

- request SHA: `7bdff42588cef3c63661656864f63c3348d1a05e8b574a64f49be616863a2324`
- registered missing-flat bytes: `de4523fc4a1c41ced93da0c29a2aa2ea25062ae67248b1e09334d2d78bd7c574`
- unregistered valid-fail bytes: `2aca17c001945544ec60a85eff9a88763d5d77a808817f621673cda855e5e84a`
- declared filler: 10 MiB, used to widen the interval after the target's hash and before its parse

Stable result:

```json
{"detail_pass_by_capture":{},"detail_state_by_capture":{"invalid":"INSTRUMENT_INVALID"}}
```

Observed raced result:

```json
{"detail_pass_by_capture":{"invalid":false},"detail_state_by_capture":{"invalid":"DETAIL_FAIL"}}
```

The published rerun in `artifact-race-report-original.json` reproduced on attempt 14.

## Critical defect 2: core-source hash/use TOCTOU

Locations in the preserved adapter: `m138_adapter.py:58` and `m138_adapter.py:365`.

`validate_bundle` hashes `comparison_checker.py`, closes it, and discards the bytes. `install_core_module` later reopens the path with `path.read_bytes()`. A replacement between those operations is compiled and executed even though its digest was never accepted.

Fixture:

- request SHA: `0621ee8f37d8d97cd07c34fbd8bbfc2734774921bf485a47be11afd70b102ef2`
- registered core SHA: `a8f92dbfc436e7a0ffab0fd0cc8bbc9d6708cc829f0435a5bdda510e2a30af5b`
- replacement core appends an `adjudicate` definition that writes a sentinel and returns `DETAIL_FAIL`

Stable result is the same invalid/no-Boolean result above. The raced result contains `DETAIL_FAIL:false` and the sentinel exists. The published rerun in `source-race-report-original.json` reproduced on attempt 5.

## Direct answer to the governing question

Yes. The artifact race takes a request whose registered payload is an instrument failure (`INSTRUMENT_INVALID`, no Boolean) and produces a scientific conclusion (`DETAIL_FAIL`, `false`) under the same request SHA.

## Mutation results

`mutation-report-original.json` contains all 32 exact anchored mutations. Every anchor landed exactly once. The inert control stayed GREEN. The following substantive mutations also stayed GREEN, demonstrating missing negative coverage in the 25-check suite:

- `recursive-supplied-decision-guard`
- `common-binding-hash-guard`
- `physical-binding-hash-guard`
- `environment-match-guard`
- `terminal-newline`
- `commission-null-lower-bound`
- `commission-blur-threshold`
- `commission-improvement-threshold`
- `commission-missing-flat-reason`
- `commission-hash-control`
- `bundle-member-verification` (covered by the separate bootstrap harness, not the 25-check suite)
- `null-invalid-refusal`
- `null-status`
- `null-center-q05`
- `null-center-q95`
- `null-upper`
- `blur-invalid-refusal`
- `blur-status`
- `improvement-invalid-refusal`
- `improvement-status`
- `missing-not-applicable-refusal`
- `missing-status`

The mutations that did go RED and their exact failed checks are also recorded in that report.

## Bootstrap mutation result

`bootstrap-mutation-report-original.json` confirms:

- a conventional loader executed a timestamp-eligible poisoned `.pyc`;
- the original adapter ignored that `.pyc`;
- the direct-loader mutant executed it;
- static stale-hash core tampering was refused by the original adapter before execution; and
- removing bundle-member verification allowed the stale-hash core sentinel to execute.

## Stable behavior that passed

Under immutable files, direct fixtures confirmed:

- `DETAIL_PASS → true`;
- `DETAIL_FAIL → false`;
- missing-flat and flat-ROI invalidity → `INSTRUMENT_INVALID` with no Boolean;
- supplied null, empty, invalid-plus-Boolean, Boolean-only, and contradictory state maps → nonzero refusal with no stdout;
- unbound binding → `INSTRUMENT_UNBOUND`, nonzero, no stdout;
- static artifact/source hash tampering → refusal; and
- repeated successful output → byte-identical.
