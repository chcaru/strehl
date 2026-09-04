# M138 adapter amendment 8 — bind commissioning thresholds

**Frozen before repaired execution:** yes  
**Affected production file:** `m138_adapter.py`  
**Verification harnesses:** `m138_adapter_mutation.py`, M149's
`mutation_harness.py`, `artifact_race.py`, and `source_race.py`

M149's re-attack accepted the read-once repair at the mechanism level but
found that both commissioning threshold-key mutations survived all 51 adapter
checks:

- blur q95 `0.95` incorrectly passed when the configured strict `< 0.90` key
  was replaced by the improvement key (`1.10`);
- improvement q05 `1.00` incorrectly passed when the configured strict
  `> 1.10` key was replaced by the blur key (`0.90`).

The helper tests supplied their own numeric bars and therefore bypassed the
contract-key selection that production used. A count of green checks did not
prove that wiring.

This amendment:

1. makes each contract-key lookup a named function used by production;
2. adds a named probe requiring the blur lookup to return `0.90`;
3. adds a named probe requiring the improvement lookup to return `1.10`;
4. adds a public-CLI commissioning fixture with blur q95 `0.95` and
   improvement q05 `1.00`, requiring both output controls to remain `false`;
5. adds a stale-bundle-member fixture requiring nonzero hash refusal with
   empty stdout; and
6. reanchors all 19 stale entries in M149's 32-entry mutation manifest to
   their current implementations.

No scientific threshold changes. No refusal, status-to-Boolean, read-once,
request, bundle, or output contract changes.

## Frozen acceptance

- ordinary adapter self-test: **56/56**;
- M135 helper mutation suite: **27/27 substantive mutations killed**, one
  inert mutation green;
- reanchored M149 manifest: **32/32 entries applied**, **31/31 substantive
  mutations killed**, **0 unapplied**, one inert mutation green;
- both M149 vulnerable race controls reproduce before either repaired race is
  run;
- repaired artifact and source races exercise both registered-snapshot and
  refusal exits, with no conversion or sentinel execution;
- adapter and M135 mutation outputs replay byte-identically;
- core checker remains 14/14; and
- physical binding remains `UNBOUND`.

Any failure requires another frozen amendment. The check count, applied
substantive mutation fraction, and unapplied manifest count must be reported
separately.

## Reconciliation of M149's 19 stale anchors

Every targeted predicate remains present; none was deleted. The reanchored
manifest records these locations:

| M149 mutation | Current predicate |
|---|---|
| `artifact-hash-guard` | `m138_adapter.py:334` |
| `byte-replay-guard` | `m138_adapter.py:572` |
| `common-binding-hash-guard` | `m138_adapter.py:516` |
| `physical-binding-hash-guard` | `m138_adapter.py:520` |
| `environment-match-guard` | `m138_adapter.py:406` |
| `commission-null-lower-bound` | `m138_adapter.py:747` |
| `commission-missing-flat-reason` | `m138_adapter.py:781` |
| `bundle-member-verification` | `m138_adapter.py:453` |
| `null-invalid-refusal` | `m138_adapter.py:712` |
| `null-status` | `m138_adapter.py:746` |
| `null-center-q05` | `m138_adapter.py:748` |
| `null-center-q95` | `m138_adapter.py:749` |
| `null-upper` | `m138_adapter.py:750` |
| `blur-invalid-refusal` | `m138_adapter.py:718` |
| `blur-status` | `m138_adapter.py:754` |
| `improvement-invalid-refusal` | `m138_adapter.py:724` |
| `improvement-status` | `m138_adapter.py:758` |
| `missing-not-applicable-refusal` | `m138_adapter.py:730` |
| `missing-status` | `m138_adapter.py:780` |

The two surviving threshold entries are also reanchored to the new named
contract-key selectors. The full manifest must apply all 32 entries: 31
substantive plus one inert control.
