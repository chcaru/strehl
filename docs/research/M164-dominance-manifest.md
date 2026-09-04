MANIFEST BLOCKED: M164 must freeze the complete cell expansion, calibrated bars, complete-S reduction, and production seed; M135/M147 must supply the final target, geometry, and resampler bindings, and execution owners must freeze candidate/comparator software

# M164 — production dominance manifest and fail-closed reader

## 0. Ruling

**VERIFIED BY RUNNING.** I built a versioned manifest record, a byte-bound
launcher, a fail-closed reader, a 54-case commissioning suite, and an
independent 17-check verifier under
`experiments/M164-dominance-manifest/`.

**VERIFIED BY RUNNING.** The bytes currently serialized as
`production-manifest-v1.json` have SHA-256
`7dd9c5e5da63bd68ffa49b645e59cedc4495fc08b5e5b8e423f6eb68552a22d9`.
The separate freeze record binds those manifest bytes, the launcher, and the
reader core. Its SHA-256 is
`2f1ca6ab1dcb97c0b41df938b5167f847456bb7375064df7324edf7d30e2eb7a`.

**INFERRED BY READING.** That digest identifies a **blocked-state record**, not
a production-ready manifest. The record deliberately says `status =
BLOCKED`, preserves unresolved fields as `null` or an empty hash group, and
names the producer for each missing input. It therefore does not clear M166's
zero-frame release gate.

**VERIFIED BY RUNNING.** Executing the production reader on that exact record
returns exit code `2`, family status `UNMEASURED`, and 17 persistent refusal
records. The distinct refusal codes are:

```text
MANIFEST_STATUS
DIMENSIONS_NONEMPTY
FAMILY_CARTESIAN
EPSILON_COMMON_RANGE
POWER_FLOORS_POSITIVE
RANK_CONDITION_BARS
REDUCTION_SPEC
HASH_GROUPS_COMPLETE
UNRESOLVED_FIELDS
```

**INFERRED BY READING.** The correct operational consequence is unchanged:
the two-frame M147 preflight remains allowed by M166, but no registered frame
of the 1,092-frame dominance rehearsal is licensed.

## 1. Why the manifest cannot honestly be marked `FROZEN`

| M166 §1 requirement | Current source state | Required producer |
| --- | --- | --- |
| complete licensed cell family | **INFERRED BY READING:** M166 §5.1 requires the exact Cartesian population across four strips, `sw4`/`sw10`, every registered channel, four frequencies, four orientations, and every field partition. M135 fixes the spectral 4 × 4 portion and 64 guarded sites, but the repository does not freeze the production channel list or subject-region/field partition list. | M164 registrar with the M135 target owner |
| positive `delta_I,k`, `delta_H,k` | **INFERRED BY READING:** M164 §4 requires a predeclared finite candidate grid, two disjoint known-ratio development partitions, bias/power selection, and untouched validation. No production calibration artifact exists. M164 explicitly says its `0.08` values are commissioning-only. | M164 calibration owner |
| `epsilon_common`, power floors, rank and conditioning bars | **INFERRED BY READING:** the current M164 implementation values were not validated as production physical bars, and M166's truth-reference audit leaves the design dimensions, support, rank evidence, and condition-number bar unresolved. | M164 calibration owner, after the target/reduction design fixes the measured design matrix |
| complete-`S` scalar or vector reduction | **INFERRED BY READING:** M164 §5 requires each `S_1/S_2` to represent a complete independently acquired input. M166 corrects that lineage to `55 + 55 + 27 + 27` frames. No candidate-blind sufficient scalar reducer or lossless vector checker is frozen. M135 also records that the physical payload generator is not implemented or commissioned. | M164 complete-input reduction owner |
| calibration, target, resampler, geometry, software, seed, checker hashes | **VERIFIED BY RUNNING / INFERRED BY READING:** the blocked record binds the available M165 calibration contracts, M135 rule/binding records, M147 preflight code, M164 estimator, and new checker. M135's physical binding still contains null commissioning/payload hashes; M147 has no accepted real scale/field result; the final target, native-output resampler, production seed, and complete candidate/comparator freezes do not exist. | M135/M147 target and geometry owners; M164 seed registrar; candidate/comparator execution owners |
| fail-closed reader | **VERIFIED BY RUNNING:** delivered and commissioned. | complete |

**INFERRED BY READING.** The M165 real A/B/V maps are run evidence, not values
that can exist before the first exposure. The pre-exposure manifest instead
binds their contract, estimator, thresholds, and required lineage. I have not
made the manifest circular by requiring a future fitted map hash before
capture.

**INFERRED BY READING.** The v1 reader accepts only
`scalar-linear-sufficient`. That is the only reduction supported by the
existing M164 scalar estimator. If the program selects a lossless vector
reduction instead, it needs a new versioned estimator and reader rather than a
string change that silently feeds vector data to the scalar gate.

## 2. Delivered fail-closed mechanism

**INFERRED BY READING.** `reader.py` establishes the execution chain in this
order:

1. read the freeze record;
2. read the checker core once, verify its digest, and compile those same
   captured bytes;
3. read the manifest once, compute SHA-256 over those bytes, and pass those
   same bytes to the checker core;
4. read the evidence once, hash it, and pass those same bytes to the checker;
5. read each non-runtime artifact once, verify the captured bytes, and execute
   the captured `dominance.py` bytes rather than reopening its path.

**VERIFIED BY RUNNING.** The independent verifier parses the launcher AST and
finds exactly one `manifest_resolved.read_bytes()` call. It also confirms the
same `manifest_bytes` variable is hashed and handed to the parser. Manifest,
checker-core, launcher, and artifact digest mutations each produce a
persistent `UNMEASURED` refusal.

**INFERRED BY READING.** There is no manifest default path for a margin,
common-mode fraction, power floor, rank bar, condition bar, reduction, cell,
artifact, or seed. Required values are indexed directly and validation
returns before evidence evaluation when any value is absent or malformed.

**VERIFIED BY RUNNING.** The production manifest contains no byte sequence
`0.08`. Missing numerical values remain null and refuse; M164's
commissioning-only value is never substituted.

**INFERRED BY READING.** A future complete manifest must enumerate its full
Cartesian cell family. The reader recomputes that product, rejects missing or
extra tuples, rejects duplicate IDs, and requires a finite positive
information and transfer margin in every cell.

**INFERRED BY READING.** The evidence reader requires identical ordered cell
families, at least 64 common physical sites, finite complex witnesses, exact
control classes, complete frozen A/B frame counts, disjoint A/B sources,
candidate exclusion, reduction-hash agreement, full design rank, and the
frozen condition-number bar before invoking M164.

**INFERRED BY READING.** The common-mode family spends its declared alpha
across the frozen control classes, takes the maximum path/cell upper bound,
and feeds those bounds to the existing four-way M164 charge. The family result
is `PASS` only when every information and transfer lower bound passes and the
common-mode fraction passes. Every other result is `UNMEASURED`.

## 3. Commissioning

**VERIFIED BY RUNNING.** `commission.py` passed 54 cases covering all 45
declared launcher, manifest, evidence, lineage, hash, rank, conditioning,
power, common-mode, and dominance checks. `required_checks` and
`observed_checks` are byte-for-byte equal as sorted lists; there are no missing
checks and no failed cases.

**VERIFIED BY RUNNING.** Every content mutation used an exact byte anchor,
asserted that the anchor count was exactly one, and hard-failed the harness
when that condition was false. The first attempted common-mode red canary did
exactly that: a newline-mismatched anchor had count zero and stopped the run
rather than producing green evidence. The corrected unique anchor has count
one.

**VERIFIED BY RUNNING.** The positive synthetic family passed. A zero-power
cell returned `UNMEASURED / DOMINANCE_POWER`. A single weakened reference cell
returned `UNMEASURED / DOMINANCE_FAMILY`; stronger companion cells did not
compensate.

**VERIFIED BY RUNNING.** The required improvement-shaped defect raised both
unadjusted family minima:

| quantity | clean | contaminated |
| --- | ---: | ---: |
| minimum information ratio | 2.016823 | 2.084359 |
| minimum transfer ratio | 1.879597 | 2.081237 |

**VERIFIED BY RUNNING.** Independent featureless controls exposed that
repeatable contamination. The intact reader returned
`UNMEASURED / DOMINANCE_COMMON_MODE`, not a reward.

**VERIFIED BY RUNNING.** A source-level red canary replaced the two
common-bound assignments with zeros using one exact anchor. With the bad core
itself re-hashed and executed from those verified bytes, the same contaminated
evidence returned `PASS`. The commissioning expectation rejected that bad
checker. The common-mode charge is therefore load-bearing, not decorative.

**VERIFIED BY RUNNING.** The commissioning artifact is
`out/commission.json`, SHA-256
`3c3c2797908275dc9e6a951d8e82d9eba83e0790a2406a8d2261154fa044f418`.

## 4. Independent verification

**VERIFIED BY RUNNING.** `verify.py` passed 17/17 checks. It independently:

- recomputed the manifest, launcher, core, and every present artifact hash;
- checked the CRLF source / exact-LF JSON checkout policy that preserves those
  hashes;
- checked the single-byte-flow manifest loader;
- reran the production refusal and obtained byte-identical output;
- reran all commissioning cases and obtained byte-identical output;
- checked complete declared-check coverage;
- checked the upward contamination and load-bearing red canary;
- checked every plant's exact-one anchor; and
- found no commission workspace, partial output, or bytecode residue.

**VERIFIED BY RUNNING.** The persistent production refusal is
`out/production-refusal.json`, SHA-256
`8913fb83f0114c8bf1aa88e8bf3b8ad66e92d2151927e8f732afc2cdadc66d7d`.

**VERIFIED BY RUNNING.** The independent verification record is
`out/verification.json`, SHA-256
`6ca0ab021ccf70deee5dfaff95558f47172c9b327664d0f0f63e9b3e37eb9485`.

## 5. Exact release path

**INFERRED BY READING.** The zero-frame gate can clear only after the six
entries in `production-manifest-v1.json.unresolved` are replaced by:

1. exact channel and field-partition arrays plus their complete Cartesian cell
   records;
2. validated positive per-cell margins and calibrated common-mode, power,
   rank, conditioning, and control-site bars;
3. a hash-bound complete-input scalar sufficiency proof and implementation, or
   a newly versioned vector estimator/reader;
4. the final target, resampler, accepted M147 scale/field, and geometry
   artifacts;
5. all candidate/comparator binaries, settings, adapters, and environment
   records; and
6. the target/randomization/checker seed artifact.

**INFERRED BY READING.** Changing `status` to `FROZEN` without those values
will not work: the reader independently recomputes the family, validates every
bar and artifact, and refuses unresolved entries.

**INFERRED BY READING.** No bar was lowered and no value was invented to make
the file constructible. The result is a commissioned fail-closed mechanism
and an exact blocker ledger, not a false release.

## 6. Reproduction

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
$env:MKL_NUM_THREADS='1'
$env:NUMEXPR_NUM_THREADS='1'
$env:BLIS_NUM_THREADS='1'
$env:VECLIB_MAXIMUM_THREADS='1'

python -B experiments\M164-dominance-manifest\build_blocked_manifest.py

python -B experiments\M164-dominance-manifest\reader.py `
  --repo-root . `
  --freeze experiments\M164-dominance-manifest\production-manifest-v1.freeze.json `
  --manifest experiments\M164-dominance-manifest\production-manifest-v1.json `
  --output experiments\M164-dominance-manifest\out\production-refusal.json
# Expected exit code: 2; status: UNMEASURED.

python -B experiments\M164-dominance-manifest\commission.py
python -B experiments\M164-dominance-manifest\verify.py
```
