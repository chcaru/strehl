# M138 adapter amendment 2 — unbound test-fixture hash

**Frozen before rerun:** yes  
**Affected file:** `m138_adapter.py`

The amendment-1 self-test completed 24 of 25 checks. The sole failure was
`unbound_status_is_explicit`.

The production adapter was not at fault. The test helper used
`dict.get(key, fallback)` for the synthetic request's physical-preregistration
hash. The real unbound binding contains the key with JSON `null`, so the
fallback was not selected. The request was correctly rejected as malformed
before the adapter reached its explicit `INSTRUMENT_UNBOUND` branch.

This amendment changes only the self-test fixture: it supplies a valid dummy
64-hex hash when the unbound binding value is not itself a valid SHA-256. The
production request parser, decision mapping, commissioning controls, and core
checker are unchanged.

The 24/25 artifact is preserved as
`m138-adapter-verification-run2-failed.json`. The complete 25-check self-test
must be rerun from the beginning under the newly frozen bundle.
