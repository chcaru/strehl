# M138 adapter amendment 7 — non-crashing mutation probe

**Frozen before rerun:** yes  
**Affected harness:** `m138_adapter_mutation.py`  
**Production semantics:** unchanged

The first amendment-6 mutation run reached the
`commission-hash-requires-error` mutant and stopped because replacing only the
first short-circuit operand made the mutant dereference `None`. That is a
harness failure, not a killed named check.

This amendment changes only that mutation operator. It replaces the complete
hash-refusal helper with a compiling version that treats absence of an error as
success while preserving the other two predicates. The predeclared
`guard_commission_hash_requires_error` probe must therefore turn red without
raising. All other mutation definitions and all production code remain
unchanged.
