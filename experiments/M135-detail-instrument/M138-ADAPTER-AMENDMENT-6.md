# M138 adapter amendment 6 — canonical mutation source text

**Frozen before rerun:** yes  
**Affected harness:** `m138_adapter_mutation.py`  
**Production semantics:** unchanged

The first amendment-5 mutation-harness invocation stopped before evaluating a
mutation. The harness decoded raw source bytes and searched for line-feed
anchors, while this Windows checkout stores the worktree file with CRLF line
endings. The first anchor therefore had zero matches.

This amendment canonicalises decoded source to LF before applying the already
frozen textual mutations. It changes no adapter predicate, request handling,
output, threshold, or mutation expectation. The complete 51-check self-test
and 25-substantive-plus-one-inert mutation run must be repeated under the
replacement bundle.
