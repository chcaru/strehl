# M138 adapter amendment 9 — route threshold tests through production config

**Frozen before repaired execution:** yes  
**Affected production file:** `m138_adapter.py`  
**Verification harnesses:** `m138_adapter_mutation.py`, M149's
`mutation_harness.py`, `artifact_race.py`, and `source_race.py`

M149 localised the surviving threshold defect more narrowly than amendment 8
stated. The production path selected the two commissioning contract keys, but
the direct helper probes supplied numeric `bar` arguments. Those probes could
therefore remain green while the configured key selection changed.

M149 also confirmed that all 19 stale mutation anchors still targeted present
predicates. They were not regression suspects. They were confirmed-present
predicates that the stale manifest did not exercise.

This amendment:

1. changes the blur and improvement helpers to accept the commissioning config,
   not a caller-supplied numeric bar;
2. makes each helper call its production contract-key selector internally;
3. passes the same complete commissioning config from production and direct
   probes;
4. adds one altered-config probe per helper so replacing the selector call with
   the current literal threshold is detectable;
5. retains the public-CLI near-miss controls: blur q95 `0.95` must fail strict
   `< 0.90`, and improvement q05 `1.00` must fail strict `> 1.10`;
6. requires the two M149 threshold mutants to fail distinct, direction-specific
   named checks; and
7. reanchors the complete M149 manifest after the structural edit.

No scientific threshold changes. No refusal, status-to-Boolean, read-once,
request, bundle, or output contract changes.

## Frozen acceptance

- ordinary adapter self-test: **58/58**;
- M135 helper mutation suite: **29/29 substantive mutations killed**, one
  inert mutation green;
- reanchored M149 manifest: **32/32 entries applied**, **31/31 substantive
  mutations killed**, **0 unapplied**, one inert mutation green;
- `commission-blur-threshold` fails only blur-specific threshold checks,
  including the marginal blur control;
- `commission-improvement-threshold` fails only improvement-specific threshold
  checks, including the marginal improvement control;
- both M149 vulnerable race controls reproduce before either repaired race is
  run;
- repaired artifact and source races exercise both registered-snapshot and
  refusal exits, with no conversion or sentinel execution;
- adapter and M135 mutation outputs replay byte-identically;
- core checker remains 14/14; and
- physical binding remains `UNBOUND`.

The report must state separately: ordinary check count, applied substantive
mutation coverage, unapplied manifest entries, and the smaller local mutation
result.
