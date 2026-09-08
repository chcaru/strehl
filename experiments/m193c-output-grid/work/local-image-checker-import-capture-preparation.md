# Capture metadata preparation — source-only recipe

No command in this document has been executed by the author. This prepares
one no-data isolated NumPy capture; it neither imports that collector nor
imports/discovers numerical packages or reads saved patches.

The preparer is work/local-image-checker-import-capture-prepare.py. It reads
the exact old476283-byte local-image-probe-plan-1.json, five fixed audit2
result/outer/stdout/stderr/exit records, the old pinned Python executable and
the explicitly supplied new source/recipe/review files. No runtime tree walk,
old subject rerun, AST subject import, model or image operation is included.

Use the pinned Python312 executable under -I -S -B, the repository cwd and
--self-sha256 with the held preparer digest. Supply one --source ABSOLUTE_PATH
per file in the final reviewed closure. The required ten files under work are:

- local-image-checker-isolated-runtime.py;
- local-image-checker-bootstrap-closure-design.md;
- local-image-checker-import-capture-preregister.md;
- local-image-checker-import-capture-ledger.json;
- independent-local-image-checker-import-capture-source-review.md;
- local-image-checker-import-capture-launch.py;
- independent-local-image-checker-import-capture-launch-review.md;
- local-image-checker-import-capture-prepare.py;
- local-image-checker-import-capture-preparation.md;
- independent-local-image-checker-import-capture-preparation-review.md.

Include any further actually executed new source/review dependency too.
The final closure permits at most32 unique positive .py/.md/.json files,
all below work and256KiB aggregate. Check all extents before reading contents.
Original source/runtime keys cannot be replaced or silently reclassified.
Zero diagnostic stderr is read only through its fixed historical FileRef;
it never enters the positive new source namespace.

Invocation template, expanded to full Windows paths and exact held SHA:

    Python312/python.exe -I -S -B work/local-image-checker-import-capture-prepare.py
      --self-sha256 HELD_PREPARER_SHA
      --source ABSOLUTE_FILE_1 ... --source ABSOLUTE_FILE_N

Root independently reviews and freezes sources, then supplies the actual
once-only invocation and bounded external preparation receipt. Nothing here
authorizes invoking this template before release.

## Exact output authority

All five outputs must be fresh:

- local-image-checker-import-capture-grant-1.json, at most256KiB;
- local-image-checker-import-capture-preparation-1.json, at most32KiB;
- local-image-checker-import-capture-preparation-controls-1.json, at most32KiB;
- local-image-checker-import-capture-preparation-1-failure.json, at most16KiB;
- local-image-checker-import-capture-preparation-1-stage.json, at most16KiB.

The failure file is initially durable INITIAL_INCOMPLETE. A later failure
writes a compact actual sampled CPU/wall/error/control-prefix record through
the stage and replaces it atomically after fsync/readback. Failure detail
does not duplicate the whole source registry; an existing grant/control
FileRef is retained. If the filesystem itself prevents that replacement,
the default failure record and root outer remain the evidence.

The grant has exactly ten keys, matching the collector's held authority:
schema, original_plan, failed_audit2, source_bindings, python_executable,
startup_policy, prior_work, resources, cumulative_limits, command.
Schema m193c-isolated-numpy-import-grant-v1. Its command is the exact collector
argv with the one ACTUAL_CAPTURE_GRANT_SHA256 placeholder. The collector SELF
digest is already an actual held source hash. The wrapper's own command is
separately source-checked and retained in its actual outer evidence.

Successful preparation reports COMPLETE_CAPTURE_METADATA_PREPARATION_ONLY
and emits a compact raw stdout JSON binding receipt and grant FileRefs.
Require complete binary write/flush. A nonzero actual process exit always
denies release even if a positive receipt or grant was written before a
later stdout failure. The launcher is not released from a grant alone:
root must inspect the actual preparation command/outer/exit, receipt,
controls and exact grant/closure associations first.

## Reader and controls

Each read checks lexical ancestors before resolution, exact finite extent,
plain/non-reparse metadata, same before/open/post object and SHA256 of the
same parsed byte buffer. Owned files must be singly linked; the pinned
external interpreter may use the permitted external-file link policy.
Duplicate JSON keys, non-finite literals and exponent overflow are rejected.
Final source content rereads and held metadata identity checks precede grant
publication. No source/protocol/review mutation is permitted after freeze.

Seven controls run in the one released metadata preparation, before grant:

- positive source namespace;
- wrong-plan -> original plan immutable;
- zero-source -> positive source FileRef;
- bool-extent -> positive source FileRef;
- duplicate-source -> unique source identity (replace a copied final row
  with the first, preserving the actual list count);
- wrong-source-hash -> bound file SHA256 on an actual small held SELF reread
  with one changed expected digest character;
- restored -> identical whole original/restored source-list hashes.

Active rows are retained before calling their predicate; fixed exact refusal
messages determine power. Controls copy metadata and do not alter files.
The false hash reread consumes the same current preparation budget. They
cannot certify NumPy compatibility, saved diagnostics or the producer.

## Finite resource ledger and release

Preparation ordinary work stops at4CPU/9wall and reserves1CPU/1wall for
publication inside5CPU/10wall. CPU is the current whole process clock from
zero; own wall starts immediately after import time. Root outer covers
startup and termination. Samples/tail are not a terminal-process CPU claim.
No owned child or numerical import is launched by the preparer.

The1MiB stage reserves256KiB source/recipe/review closure,256KiB grant,
32KiB success receipt,32KiB controls,32KiB failure/stage,8KiB raw stdout,
16KiB stderr,1KiB exit and32KiB outer:665KiB,359KiB unallocated. Maximum8
publication writes; no retries or use of unallocated space for another run.
Prior old files are read, not copied into this new-family byte total.

Retain1588.443678CPU/1601.9278447999966wall/4140565273file bytes/
149304339metadata bytes. This preparation's full5CPU/10wall/1MiB charge is
nonrefundable. The full new phase remains60CPU/90wall/8MiB:
5/10/1MiB preparation,15/25/2MiB capture,5/10/1MiB later preparation,
25/30/3MiB saved audit,10/15/1MiB independent/external work. Cumulative
1660CPU/1800wall/4GiB/168MiB limits are prospective amendments; no earlier
cost or refusal is erased. Observed overshoot is added and prevents release.

Exact source review precedes this metadata command. Independent capture
review and a second immutable grant are still required before a later saved
audit. No saved-data or producer-completion flag becomes true here.

