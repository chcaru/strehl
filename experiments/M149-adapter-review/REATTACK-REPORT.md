# M149 independent re-attack - repaired M135 to M138 adapter

**Verdict: SEND BACK**

Reviewed repair commits: `9f1ffd6d`, `f0467ba4`, `8eeefcbc`; evidence commit `0d67b88d`.

- Repaired adapter SHA-256: `09ff1e1456038e70780dc5564ec0f26c4e8264d40c6c4cb22b6214cfb1fce789`
- Repaired production bundle SHA-256: `56bc2990e7cf6b14988adf874b711f1bcf693c701116e21dfb7bd5f329e83945`

The two original CRITICAL hash/use races are closed at the mechanism level and were not reproduced in 512 attempts each. The adapter's refusal semantics also remain correct. The SEND BACK is for a separate HIGH test-coverage defect: two contract-threshold wiring mutations still pass all 51 official checks and produce incorrect commissioning Booleans on discriminating fixtures.

## Required race numbers

1. Vulnerable-fixture positive control:
   - Artifact race: reproduced `FAIL_RACE_REPRODUCED` at attempt 20/120 in the control-first run. A publication rerun reproduced at attempt 6/120.
   - Source race: reproduced `FAIL_RACE_REPRODUCED` with sentinel execution at attempt 8/120 in the control-first run. A publication rerun reproduced at attempt 2/120.
2. Repaired tree:
   - Artifact race: not reproduced in 512 attempts; 233 exit-0 registered-invalid outcomes and 279 hash refusals.
   - Source race: not reproduced in 512 attempts; 252 exit-0 registered outcomes and 260 hash refusals; no sentinel execution.
3. M149 mutation manifest:
   - 32 total entries: 31 substantive plus one inert control.
   - 13 applied cleanly: 12 substantive plus one inert.
   - 10 applied substantive mutations killed.
   - 2 applied substantive mutations survived: `commission-blur-threshold` and `commission-improvement-threshold`.
   - 19 `ANCHOR_ERROR` hard refusals.
   - The inert control stayed GREEN with 51/51.
4. Predicates no longer locatable: none. All 19 old anchors were mapped to current implementations below.

M135's reported 25/25 is real but is a different, smaller, helper-level mutation set in `m138_adapter_mutation.py`; it is not an execution of M149's 32-entry manifest.

## HIGH defect - commissioning threshold wiring is not load-bearing

Locations:

- `m138_adapter.py:936-953` selects the two contract threshold keys.
- `m138_adapter.py:1078-1086` tests the threshold helpers with a caller-supplied `bar`, bypassing the contract-key selection.
- `m138_adapter.py:1410-1466` uses strong positive controls and wrong-status negative controls, which do not distinguish the two configured thresholds.
- `m138_adapter_mutation.py:245-279` mutates the helper predicates, not the integration wiring.

Exact discriminating fixture:

- Blur decision status: `DETAIL_FAIL`; information-ratio q95: `0.95`; required threshold: strict `< 0.90`.
- Improvement decision status: `DETAIL_PASS`; information-ratio q05: `1.00`; required threshold: strict `> 1.10`.
- All other commissioning controls are valid.

Observed baseline, request SHA `00b6bfbe984d2b0c6ab428873d5936179f8d9efae4668a313cf00007b03c93a3`:

```json
{"pre_noise_blur_lowers_information":false,"pre_noise_optical_improvement_raises_information":false}
```

Observed `commission-blur-threshold` mutant, adapter SHA `e032c3205560547c4ead9665fa786e0c35e874e319f4350bc6a2b189bf728110`, request SHA `40b1a2745001ad8e61d9412709226754bdd195dd6893e86899a1c639198917d7`:

```json
{"pre_noise_blur_lowers_information":true,"pre_noise_optical_improvement_raises_information":false}
```

Observed `commission-improvement-threshold` mutant, adapter SHA `e7acba844dfc9b68ba91022f71123e9682681c87cfd019310d18e6853477a06b`, request SHA `9ad1eeaedc0d67921bc6bba180201453f4970256442c1289c1056a44f194b803`:

```json
{"pre_noise_blur_lowers_information":false,"pre_noise_optical_improvement_raises_information":true}
```

Both mutants returned 0 and all 51 official adapter checks remained PASS. Full outputs are in `threshold-mutation-probe-repaired.json`; the official self-test observations are in `mutation-report-repaired.json`.

## Mechanism-level race closure

Artifact path:

- `FileSnapshot` contains immutable `data` and its SHA (`m138_adapter.py:59-63`).
- `read_file_once` creates that snapshot (`:170-178`).
- `verify_artifact_ref` verifies `snapshot.sha256` and returns the snapshot (`:310-339`).
- `load_core_payload` parses `snapshot.data` through `snapshot_json_object` (`:576-585`).
- There is no reopen between accepted hash and JSON parse.

Source/module path:

- `validate_bundle` saves each verified member as a `FileSnapshot` (`:427-461`).
- `install_core_module` compiles `bundle.files["comparison_checker.py"].data` (`:80-133`).
- Snapshot-backed replacements serve the core's JSON and hash reads from those same captured bytes.
- A timestamp-eligible poisoned `.pyc` executed under a conventional loader but was ignored by the repaired adapter.
- Static stale-hash source tampering exited 2 with no stdout and did not execute the sentinel.

Request path:

- `main` reads the request once, parses that snapshot, and passes `request_snapshot.sha256` to output/refusal (`:1597-1614`).

## Refusal semantics and governing question

No tested repaired-adapter input converted instrument failure into a scientific conclusion.

- Registered missing-flat invalid input emitted `INSTRUMENT_INVALID` and no Boolean.
- Literal null state, empty supplied state map, invalid-plus-Boolean, Boolean-only, and contradictory pairs exited 2 with no stdout.
- Bad artifact hash exited 2 with no stdout.
- Unbound binding exited 2 with `INSTRUMENT_UNBOUND` on stderr and no stdout.
- Valid `DETAIL_PASS` and `DETAIL_FAIL` still mapped to `true` and `false`, respectively.

The old artifact race was specifically re-probed with a working vulnerable positive control; the repaired tree never emitted `DETAIL_FAIL:false` for the registered invalid input in 512 attempts.

## Reconciliation of 19 ANCHOR_ERROR entries

The hard refusals are legitimate structural-anchor changes, not missing predicates:

| Old mutation ID | Current mechanism |
|---|---|
| `artifact-hash-guard` | `snapshot.sha256 != row["sha256"]`, `m138_adapter.py:333` |
| `byte-replay-guard` | request snapshot read/parse/SHA propagation, `:1597-1614`; stable-output checks remain |
| `common-binding-hash-guard` | `common_binding_hash_matches`, `:515-516`, used at `:537-538` |
| `physical-binding-hash-guard` | `physical_binding_hash_matches`, `:519-520`, used at `:548-552` |
| `environment-match-guard` | `environment_matches`, `:405-408`, used at `:414` |
| `commission-null-lower-bound` | `physical_null_control_passes`, q05 lower bound at `:746` |
| `commission-missing-flat-reason` | `missing_flat_control_passes`, reason guard at `:761-765` |
| `bundle-member-verification` | verified snapshots assigned at `:452-454` |
| `null-invalid-refusal` | `null_decision_requires_refusal`, `:711-714` |
| `null-status` | null status predicate at `:745` |
| `null-center-q05` | q05 upper/center predicate at `:747` |
| `null-center-q95` | q95 lower/center predicate at `:748` |
| `null-upper` | q95 upper predicate at `:749` |
| `blur-invalid-refusal` | `blur_decision_requires_refusal`, `:717-720` |
| `blur-status` | blur status predicate at `:754` |
| `improvement-invalid-refusal` | `improvement_decision_requires_refusal`, `:723-726` |
| `improvement-status` | improvement status predicate at `:758` |
| `missing-not-applicable-refusal` | `missing_decision_requires_refusal`, `:729-730` |
| `missing-status` | missing-flat status predicate at `:763` |

The corresponding current helper mutations in M135's 25-entry suite were independently killed where applicable. Static tamper, exact replay, and integration fixtures exercised the remaining mechanisms.

## Other independently reproduced claims

- Adapter self-test: 51/51, exit 0.
- Repeated adapter self-test output: byte-identical to itself and checked-in `m138-adapter-verification.json`; SHA-256 `3e71fab3a846a76480b8e6a325033dce3b1cc801345b1652b0a5ba5d04d10b8d`.
- M135's own mutation suite: 25/25 killed, inert control survived, exit 0.
- M135's own race suite: 7/7 at 128 attempts, exit 0.
- Core checker self-test: 14/14, status PASS, exit 0.
- Full audit: PASS, no findings, exit 0.
- M138 consumer self-test: exit 0; invalid, null, unbound, and valid-fail distinctions passed.

## Evidence files

- `artifact-race-report-reattack-control.json`
- `source-race-report-reattack-control.json`
- `artifact-race-report-repaired.json`
- `source-race-report-repaired.json`
- `mutation-report-repaired.json`
- `threshold-mutation-probe-repaired.json`
- `semantics-report-repaired.json`
