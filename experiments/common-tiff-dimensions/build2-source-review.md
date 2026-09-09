# Root review of the dimensions build2 sources

2026-09-08. Independent of the implementation and checker authors. SOURCE REVIEW
ONLY; the fixed scratch controls and build2 remain unexecuted at this revision.

The current code retains the three product modules committed at c9d84f93.
The independent checker differs from the original preserved source by exactly
one executable-path literal, build-1 to build-2. Reversing it restores all65751
original bytes. The specification's matching explanation is append-only.
The24 application cases,135 private controls, recipes and numerical tolerances
are unchanged. No output-quality or successful-build claim follows.

## Review that changes choices

Root read the complete new shim/control/capture sources, the controller
integration, compile helper delta and the compositional archive constructor.
The recorded independent AST comparison at
work/build2-root-source-read.json5705B/
8f5fbe1f8d4d06460e6dd8575b2ab31fef07700a244dd2511153f56f5559faba
used authenticated original bytes from source1. Its exact stdin is retained as
work/build2-root-source-audit.py; invocation was the fixed local Python with
-I -S -B - from the repository, not an import of candidate code.

The controller has16 unchanged functions; only authority changes to authenticate
and install the shim in a private held module before Budget construction.
The helper reverses byte-for-byte through its single target literal.
Capture changes the build-attempt selector only. The preparer adds base_sources,
changes source_map/archive_sources/main and preserves eight other functions.
Root read every deletion in these deltas: replaced path/hash constants,
required-source list and constructor bodies, with corresponding replacements.
The execution contract intentionally updates paths and reservations and appends
the operational correction. No SYNTHESIS or other structural source is edited.

Root independently found the preparer's allowlist omitted the checker
specification append. The author corrected the list to seven original entries
before execution. Root also required the new capture source in the source map
and its separate reservation. The earlier addendum/patch remain preserved.

## Consumer and failure boundaries

The scratch shim serves only the exact fresh target2 with true boolean policy.
False policy delegates to the captured original scanner; nonbuild stages do not
install the shim. The private no-follow ancestry pass rejects present reparse
or symlink metadata even if exists would be false. FileNotFoundError alone can
reach the inherited scratch-disappearance path. Canonical mismatch still refuses,
with both spellings, as do permission, nonregular and capacity faults.
No arbitrary race-proof or peak-space guarantee is made.

Separate review identified the dangling-reparse loophole in the initial
exists-gated proposal. That proposal and its control/spec drafts are preserved.
Current controls have16 groups and17 dispatcher calls, with two injected reparse
variants within one group. Actual deletion occurs on the owned11-byte file
immediately before native resolve; named fault/reached-event checks and restored
positives distinguish operative tests from unvisited branches.

The new outer capture starts one fixed childless Python interpreter and keeps
its own Popen handle. Timeout or capture overflow terminates only that child.
It preserves actual exit, streams and final result association. Source identity
is checked before and after; no compiler, old experiment main or peer census is
called. The independent source review must be final before control release.
Actual results require a separate independent read after the one permitted run.

## Source and resource closure

The fixed25815-byte source1 freeze and5661467-byte archive remain immutable.
The fresh source2 archive contains changed/new entries only. The constructor
checks all181 original member hashes and every current member reconstructed
from base-or-delta, keeping all old keys and admitting only the closed new list.
The base archive's exact hash fixes order; count plus key-set equality rejects
duplicates without falsely assuming JSON order matches ZIP order.
All later stages select build2 evidence and the same full source2 map.
No build1 evidence, source or target is replaced.

Full failed build1 allocation600CPU/300wall remains; build2 receives a separate
600/300. Together with unchanged prepare/render/verify, stage reservations are
1470CPU/1020wall. Constructor reservations are50CPU/100wall, including the first
failed-build constructor; metadata archive family stays32MiB.
Scratch controls and capture each retain5CPU/10wall and1MiB read/write, combined
outer20wall. The separate failed-build review retains10CPU/20wall.
This root source audit additionally retains5CPU/10wall,16MiB read/1MiB write:
observed source reads6074752B, CPU sample0.078125s, wall0.09399999999732245s.
These explicit reservations are not elapsed whole-program usage.

## Release decision at this source revision

Source integration is acceptable subject to the independently reviewed fixed
scratch controls passing their actual one-shot execution and independent saved
result review. This document does not authorize a build by its existence.
Root must commit these final sources, then issue a separately committed actual
build2 release/archive. If a stage refuses, preserve its complete prefix and
investigate that evidence before any new grant. No image/checker retry is
licensed by a metadata repair. The historical build1 cause remains unknown.
