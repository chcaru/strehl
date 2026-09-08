# Driver file-identity source-fix addendum

2026-09-08. SOURCE-ONLY amendment after failed preparation 1. No driver,
preparation, metadata control, checker, build or render was executed by this
author. The earlier independent reviews remain unchanged historical records.

Original source and failure are preserved in commit
`b2475a48f4fb73000b9748142c3e2cbc121850ab`. Root reports that the retained
Windows preparation observation has stable but different ctime values from
Path.stat and os.fstat, with dev/ino/size/mtime/nlink matching. For pyramid.rs
those reported values are 1787691937435767000 and 1788888507528517700
respectively. This source amendment does not independently remeasure that
observation or refund the failed 10 CPU / 20 wall preparation slice.

## Exact source change

File: `experiments/m194h-pedestal-causality/build-and-run.py`.

- Archived: 34,552 B,
  `21d363a66633a3c973986a2a03503aa503dcdc063bd3781aa4e30c8b245eaf1e`.
- Candidate: 34,864 B,
  `5738d18ac41044361b6083ed38fa743dedee2a3005470130c19b2b5d1e2dadb3`.

The existing full `identity` tuple still includes
dev/ino/size/mtime/ctime/nlink. New `shared_identity` excludes only ctime.
The read path retains the initial handle stat and final named-path stat, then
requires:

1. Initial path and opened handle agree on all shared fields.
2. Initial/final path stats agree on the full tuple, including their ctime.
3. Initial/final handle stats agree on the full tuple, including their ctime.
4. Final handle still agrees with the initial path on shared fields, and the
   read byte count equals the original extent.

Thus ctime differences between APIs are permitted; ctime changes within either
API are still refused. Existing lexical/reparse checks, plain-file and byte
caps, read cadence, expected FileRef association and content hashes stay intact.
The prior driver tuple did not include attributes; this patch preserves that
scope rather than silently changing another identity policy.

## Scope and release requirement

A metadata-only AST comparison found 31 named definitions unchanged, only
`read` changed, and `shared_identity` added. Every other top-level AST node
is unchanged. This is structural source evidence, not execution verification.
The edit is confined to that reader block; all control IDs/counts, schemas,
scientific calls, resource constants, output paths and terminal logic remain.

Root owns the corresponding preparation/capture/check wrappers, the separate
finite metadata correction decision, and execution of shared-seam metadata
controls. The independent checker author owns its matching reader changes.
An independent review and the new exact source bindings are required before
release. This amendment grants no build or render and does not turn the failed
preparation into a success.
