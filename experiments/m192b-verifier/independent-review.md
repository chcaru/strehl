# M192b independent review

**VERIFIED, 2026-09-07:** accept the prospective verifier for its stated
recorded-evidence consistency scope. The final independent command exits **0**:
all **12 adversarial whole packages refuse**, while the untouched package and
the inert re-sealed package pass artifact verification. Both admissible controls
retain exactly **one PASS, zero FAIL, three UNMEASURED**, overall **UNMEASURED**.
No memory or timing disposition is improved by this review.

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B experiments/m192b-verifier/independent-verify.py
```

The tested verifier SHA-256 is
`A06C918F8171F0825FCF6AB1426F973F1570D67BF570E4A69CE5E76C77CBBBE4`.
The script asserts that source bytes stay fixed throughout each invocation.
Its final result is [independent-verification.json](independent-verification.json).

## What was independently challenged

Each case copies the complete original 300-file result package, alters a
semantic choice, recomputes every journal link, updates the certificate's
record-file/terminal-chain bindings, and rehashes every terminal member. The
public `verify_artifact` entry point therefore receives a package whose hash
chain is intact. A stale-checksum refusal cannot satisfy these controls.

The final refusals cover an omitted cleared environment key; failed
commissioning exit; wrong commissioning gate or executable; uncleared
commissioning gate environment; contradictory commissioning terminal flags;
embedded commissioning log hash disagreeing with the archived log; boolean CPU
repetition; unknown CPU schema; zero enclosing CPU mean with a busy trace;
unregistered archive member; and empty CPU trace. The instrument has a live
inert control: simply re-sealing the original content must stay admissible.

The final code factors `validate_invocation` across scored and commissioning
runs. It binds complete arguments and binary metadata, the declared environment
domain from the pinned source, cleared values and active paths, terminal witness
membership and boolean values, and log paths. This repairs the control path
itself, instead of special-casing the three initial mutated fields. CPU sweep
repetition now requires a real integer or null. These are checks on stored
contradictions, not authentication of an independently fabricated telemetry set.

## Earlier failures are retained

[independent-first-pass.json](independent-first-pass.json) records the first
review at verifier hash `FA8FFD53EAAAB7D3144431F5488469529CFD3C54CB0AFF6205B7DEA80A878FC0`.
Six bad packages were accepted: omitted cleared environment key, failed
commissioning exit, wrong commissioning gate, contradictory embedded log hash,
unknown CPU schema, and impossible zero boundary mean. The extra archive member
and empty trace were already rejected.

[independent-first-recheck.json](independent-first-recheck.json) records those
initial failures becoming refusals. The broader choice check in
[independent-second-pass.json](independent-second-pass.json), at hash
`3F45AD923EC55B0E13A147803E0C0B67A2A31D20412564314E307C02C99A66D9`,
then found four additional accepted contradictions: commissioning executable,
uncleared environment and terminal flags, plus boolean CPU repetition. The
final shared invocation validation rejects all four. These are verifier defects
found and repaired during review; no equivalent inconsistency was found in the
original completed campaign.

## Limits and preservation

The frozen M192 verifier still supplies the product-bar reductions, and its
source is checked against the pinned revision. The original package's 133 runs,
300 files and one-pass/three-unmeasured result remain intact. The independent
script hashes every original file before and after testing and requires exact
equality. It executes no command named inside a record, reads no RAW/capture
files, and deletes only its checked workspace fixture directories.

The exact sweep boundary CPU mean cannot be reconstructed: raw boundary system
counters were not retained. The new contradiction check correctly rules out
an entirely idle enclosing interval containing a busy interval, or the converse;
it does not claim to derive every possible boundary average from the trace's
arithmetic mean. Output pixel hashes remain campaign receipts because TIFFs
were removed after hashing. No integrity checker can authenticate a party
rewriting all telemetry and supporting logs consistently; that is explicitly
outside this verifier's trust model.

This review does not change thresholds, reclassify historical failures, claim
M12 acceptance, or substitute for a newly commissioned measurement instrument.
No original evidence, product source, protocol, scorecard, or SYNTHESIS entry
was modified or committed by the independent reviewer.
