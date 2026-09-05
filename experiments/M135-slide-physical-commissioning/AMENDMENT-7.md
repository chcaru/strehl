# M135 slide commissioning amendment 7

Status: **FINAL REVIEW HARDENING BEFORE COMMIT**

A third read-only review found:

1. top-level schema and hash-chain checks alone did not semantically establish
   the statuses consumed by `summarize`;
2. twelve unique top-level source groups made `IDENTIFIABLE` unreachable from
   Stage A's four frozen groups; and
3. a scratch-directory junction could redirect rawler dump writes.

The repair adds stage-specific semantic validators and makes this burned-slide
schema categorically incapable of emitting a sufficient physical flat
certificate.  Stage A now records factual leaf capture units inside the four
top-level groups; roles bind one complete unique leaf unit, so the gate is
expressible without pretending that one directory split is two captures.
Decoder scratch is resolved, checked component-by-component for symlinks and
Windows reparse points, and proved disjoint from the resolved source tree
before every write and read-back.

New controls reject a self-consistent spliced artifact chain, a mismatched flat
ledger, incomplete capture-unit consumption, and source-contained/reparse
scratch.  No authorized data was accessed and no physical bar changed.
