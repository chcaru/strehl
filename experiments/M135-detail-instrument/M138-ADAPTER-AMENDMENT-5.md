# M138 adapter amendment 5 — consume only verified bytes

**Frozen before repaired execution:** yes  
**Affected production file:** `m138_adapter.py`  
**Verification harnesses:** `m138_adapter_race.py`,
`m138_adapter_mutation.py`

M149's independent review demonstrated two critical time-of-check/time-of-use
defects. The adapter hashed an evidence artifact and later reopened its path
for JSON parsing; it also hashed `comparison_checker.py` and later reopened
the path for compilation. Concurrent replacement converted a registered
missing-flat refusal into `DETAIL_FAIL / false`, and separately executed
unregistered core source while the output reported the registered bundle
hash. The first outcome converts no verdict into a scientific conclusion.

This amendment replaces path identity with immutable byte snapshots:

1. Every request, declared artifact, bundle manifest, and bundle member is read
   exactly once.
2. SHA-256 is computed from that in-memory byte string.
3. JSON is decoded only from that same string.
4. `comparison_checker.py` is compiled only from its verified bundle string.
5. The core's source, estimator, contract, and binding lookups are rebound to
   verified bundle snapshots. An attempt to read any unverified path refuses.
6. The request hash in output or refusal is the hash of the bytes actually
   parsed. No request path is reopened.
7. The commissioning hash-mutation control compares its declared alternate
   digest against the already verified artifact snapshot; it never reopens the
   artifact.

After a snapshot is created, later path contents are irrelevant to that
invocation. A replacement observed before the read has the wrong digest and
refuses; a replacement after the read cannot affect parsing or execution.
That is the structural race argument. Repeated non-rejection alone is not the
argument.

## Frozen rerun

The ordinary self-test must pass **51/51** checks. The previous 25 behavior
checks remain, 25 named guard probes are added, and one public-CLI
commissioning request must reach all five `false` control outcomes without
turning the request itself invalid.

The named guard probes cover:

- nested producer-supplied decisions;
- exact environment equality;
- common and physical request binding hashes separately;
- the canonical terminal newline;
- twenty commissioning predicates: three internally-invalid status refusals,
  the missing-control `NOT_APPLICABLE` refusal, mutated-digest syntax, exact
  output-key membership, three hash-mutation conditions, five physical-null
  conditions, two blur conditions, two improvement conditions, and two
  missing-flat conditions.

`m138_adapter_mutation.py` must:

- start with all 25 named probes green;
- neuter each predicate independently;
- require that mutation's predeclared named probe to turn red;
- report mutation kills separately from ordinary check count; and
- apply one inert docstring mutation that must leave all probes green.

The expected mutation result is **25/25 substantive mutations killed** and
**1/1 inert mutation surviving**. The count exceeds M149's minimum request of
24 because the common request-binding comparison and the physical-binding
comparison are commissioned separately.

`m138_adapter_race.py` must exercise both demonstrated replacement classes in
a synthetic physically-bound runtime:

- stable registered missing-flat bytes produce `INSTRUMENT_INVALID` with no
  Boolean;
- stable registered fail bytes produce `DETAIL_FAIL / false`;
- replacing the registered artifact with valid-fail bytes produces a nonzero
  refusal with empty stdout;
- replacing the registered core with a sentinel-bearing source produces a
  nonzero refusal, empty stdout, and no sentinel;
- concurrent alternation of each pair may yield either a verdict from the
  registered snapshot or a hash refusal, but never an unregistered verdict or
  sentinel execution.

The complete self-test, mutation harness, race harness, production
description, byte-identical replay, M135 audit, and M138 consumer self-test
must be rerun after this amendment is committed. The request and output
schemas, scientific thresholds, status-to-Boolean mapping, core statistic, and
physical `UNBOUND` state are unchanged.
