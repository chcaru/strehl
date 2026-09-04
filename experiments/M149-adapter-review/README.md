# M149 adapter review evidence

This directory preserves lane M149's independent review of the original M135 → M138 adapter with adapter SHA-256 `6d4366533b2b12fc1e03c44d96faa1af3d7e89e6c6f35ed5420dd33b8e5e6290`.

It contains review-only fixtures and harnesses. The harnesses copy their input runtime to `%TEMP%`; they do not mutate `experiments/M135-detail-instrument` or `experiments/M138-w1-gate-audit`.

This package is a **standing regression gate**, not only a record of one review. The same two race probes and the same 32 exact anchored mutations can be run against M135's repaired tree and any future adapter implementation through `--source-dir`.

## Files

- `.gitattributes`: disables text normalization for this subtree so the SHA-bound fixtures round-trip byte-for-byte.
- `artifact_race.py`: races a registered missing-flat payload against an unregistered valid `DETAIL_FAIL` payload.
- `source_race.py`: races the registered core source against an unregistered core that forces `DETAIL_FAIL`.
- `mutation_harness.py`: applies each exact full-line mutation from `mutation-manifest.json`, hard-errors unless the anchor lands exactly once, rebundles the copied runtime, and runs `--self-test`.
- `bootstrap_mutations.py`: reproduces the poisoned-`.pyc` and removed-bundle-member-verifier mutations.
- `mutation-manifest.json`: all 32 behavioral mutations plus both special bootstrap mutations, their anchors, replacements, expected RED/GREEN behavior, and original observations.
- `mutation-report-original.json`: complete rerun against the preserved vulnerable unbound runtime.
- `artifact-race-report-original.json`, `source-race-report-original.json`: exact successful race reproductions.
- `bootstrap-mutation-report-original.json`: exact poisoned-bytecode and static-tamper results.
- `fixture-manifest.json`: SHA-256 inventory of every preserved fixture.
- `review-report.json`: machine-readable consolidated verdict, defects, race observations, and mutation summary.
- `fixtures/vulnerable-unbound-runtime/`: exact production unbound bundle (`fa3f5135…`) used by the original 25-check and bootstrap mutation runs.
- `fixtures/vulnerable-bound-runtime/`: exact synthetic bound runtime (`437f0498…`) used by the direct CLI/race fixtures. Its adapter bytes are still the production `6d436653…` bytes.
- `fixtures/payloads/registered-invalid.json`: missing-flat input, SHA `de4523fc…`.
- `fixtures/payloads/unregistered-fail.json`: same-capture valid scientific-failure replacement, SHA `2aca17c0…`.

## Reproduce the original defects

From the Strehl repository root:

```powershell
python -B experiments/M149-adapter-review/artifact_race.py
# Expected on preserved vulnerable fixture: exit 1, status FAIL_RACE_REPRODUCED.

python -B experiments/M149-adapter-review/source_race.py
# Expected on preserved vulnerable fixture: exit 1, status FAIL_RACE_REPRODUCED.

python -B experiments/M149-adapter-review/mutation_harness.py
# Expected on preserved vulnerable fixture: exit 1, status FAIL_SURVIVORS.

python -B experiments/M149-adapter-review/bootstrap_mutations.py
# Expected on preserved vulnerable fixture: exit 0, status PASS.
```

## Standing regression gate: control first, candidate second

The race scripts are probabilistic probes. Each defaults to 80 attempts and a 2 ms swap interval. The original artifact race reproduced on attempt 14 and the original source race on attempt 5 in the published reruns. **A run that reports no reproduction does not, by itself, prove a repair.** It may only mean that process scheduling missed the vulnerable interval.

A candidate clean run is meaningful only alongside a same-session control showing that the harness can still reproduce the defect on the preserved vulnerable runtime. `fixtures/vulnerable-bound-runtime/` is the race-test control; `fixtures/vulnerable-unbound-runtime/` is the mutation/bootstrap control. These preserved-vulnerable-fixture arms are the race equivalent of an inert mutation control and must not be removed when this package is updated.

Use this exact sequence from the Strehl repository root:

```powershell
$review = 'experiments/M149-adapter-review'
$candidate = 'experiments/M135-detail-instrument'

# Artifact-race positive control: must reproduce the known defect.
python -B "$review/artifact_race.py" `
  --source-dir "$review/fixtures/vulnerable-bound-runtime"
if ($LASTEXITCODE -ne 1) {
  throw 'artifact-race vulnerable control did not reproduce; candidate result is inconclusive'
}

# Artifact-race candidate: must not reproduce, and its stable baseline must remain invalid/no-Boolean.
python -B "$review/artifact_race.py" --source-dir $candidate
if ($LASTEXITCODE -ne 0) {
  throw 'artifact-race candidate failed'
}

# Source-race positive control: must reproduce the known defect.
python -B "$review/source_race.py" `
  --source-dir "$review/fixtures/vulnerable-bound-runtime"
if ($LASTEXITCODE -ne 1) {
  throw 'source-race vulnerable control did not reproduce; candidate result is inconclusive'
}

# Source-race candidate: must not reproduce, and its stable baseline must remain invalid/no-Boolean.
python -B "$review/source_race.py" --source-dir $candidate
if ($LASTEXITCODE -ne 0) {
  throw 'source-race candidate failed'
}

# Mutation control: preserves the original 32-mutation result.
python -B "$review/mutation_harness.py" `
  --source-dir "$review/fixtures/vulnerable-unbound-runtime"
if ($LASTEXITCODE -ne 1) {
  throw 'mutation vulnerable control no longer matches the frozen review result'
}

# Candidate mutation gate.
python -B "$review/mutation_harness.py" --source-dir $candidate
if ($LASTEXITCODE -ne 0) {
  throw 'candidate mutation gate failed or refused'
}
```

For a race-safe candidate, each candidate race command exits 0 with `PASS_NO_RACE_OBSERVED`, its stable baseline is still `INSTRUMENT_INVALID` with no Boolean, and the corresponding preserved-vulnerable control exits 1 with `FAIL_RACE_REPRODUCED`. If the vulnerable control does not reproduce in that session, increase `--attempts` and rerun both arms; do not treat the candidate's clean result as evidence.

## Designed refusal: `ANCHOR_ERROR`

`mutation_harness.py` requires every mutation anchor to occur **exactly once**. Zero matches or multiple matches produce `ANCHOR_ERROR` and exit 2. This is deliberate fail-closed behavior, not a harness bug and not a warning to suppress. A mutation that silently fails to apply is indistinguishable from a passing test. If a repaired implementation changes structurally, update and independently review that mutation's anchor; never convert `ANCHOR_ERROR` into a skip.

## Failure condition

The critical failure is this exact transition for capture `invalid` under the same request hash:

```json
{"detail_pass_by_capture":{},"detail_state_by_capture":{"invalid":"INSTRUMENT_INVALID"}}
```

becoming:

```json
{"detail_pass_by_capture":{"invalid":false},"detail_state_by_capture":{"invalid":"DETAIL_FAIL"}}
```

See `REPORT.md` and the machine-readable `*-report-original.json` files for exact outputs.
