# M193c dependency runtime capture

Prospective source only. Root must freeze this parent, its reader and helper
closure and the exact command release before execution. No capture, import of
NumPy/rawpy, decoder call, image read, build or RAW access is performed while
preparing these files. This stage records the installed dependency bytes used
by the forthcoming independent native reader. It grants no decoder agreement,
native derivative, placement, coverage or image-quality admission.

## Fixed entry and prerequisites

The parent is `runtime-capture.py`, output exactly `runtime-capture-1`.
The one reader child writes exactly `derivative-runtime-1.json` beside that
directory. Both destinations must be absent. The release is a root-pinned
repository-contained file whose supplied SHA256 is checked on the same bytes
parsed. No missing prerequisite is replaced with a synthetic gate.

Release `m193c-runtime-capture-release-v1`, scope `dependency-runtime-only`, has
exact keys `schema,scope,source_bindings,inputs,commands,build,private_admission,
independent_review,python_executable`. Source bindings are repository-relative
path to `{sha256,bytes}` and include this parent/specification, repaired
`bounded-process.py`, pinned M12 Job helper, `independent-derivative-read.py`,
its TIFF extension/specification, and the original held M194g TIFF parser.
The repaired helper SHA is
`47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b`.
Sources are checked before importing the helper from those exact source bytes.
The parent imports no reader or numerical dependency.

Inputs are unique FileRefs and include actual successful build-3 result,
private-campaign-2 result, derivative private gate, its producer and independent
reader results, and the root-pinned independent review. The review is read as
bytes even when Markdown. Build/private gate associations must match. The
capture relies on root's reviewed private admission; it does not rerun pixel
controls. The Python executable is a separately pinned absolute FileRef;
repository evidence refs have exactly `{path,sha256,bytes}`.

`commands` has exactly `parent,reader`. With all paths absolute and cwd the
repository root, their argv arrays are:

```
<python> -B -X faulthandler -X pycache_prefix=<runtime-capture-1>/cache-parent <runtime-capture.py> --release <release> --release-sha256 ACTUAL_EXECUTION_RELEASE_SHA256 --output <runtime-capture-1>
<python> -B -X faulthandler -X pycache_prefix=<runtime-capture-1>/cache-reader <independent-derivative-read.py> --capture-runtime <derivative-runtime-1.json>
```

The sole placeholder is replaced by the externally supplied release hash in
the parent command; actual `sys.orig_argv` must equal it. Child argv is literal,
with no `--request`, `--output`, `--private` or other subject operation.
The parent clears all ambient `PYTHON*` and the existing helper's
STREHL/Rayon/OpenMP/BLAS/NumExpr/Rust-flags/target overrides. It records removed
names, no explicit overrides and the actual empty remaining controlled subset;
unrelated inherited environment values are not copied into evidence. The reader
sets its four numerical thread limits to the string `2` before imports.

## Actual observation and bounds

One invocation has a total 30 CPU-second / 60 wall-second allowance, including
parent preparation, source/input and runtime hashing, child, persistence and
post-write checks. Child receives only the remaining time, a 2 GiB Windows Job
committed-memory limit and a 1 MiB live combined log cap. Job CPU is the actual
terminal user+kernel total, added once to parent process CPU.
Before the launch attempt, `cpu_accounting_complete` becomes false. Only valid
actual terminal Job accounting with zero active processes restores it to true.
While false, `cpu_seconds` is null; `observed_cpu_seconds` retains parent CPU
plus any observed partial child counter, and `child_cpu_seconds` is null when
unavailable. `child_cpu_accounting` distinguishes `not-launched`, `unavailable`,
`observed-partial` and `terminal`. Live budget callbacks check the observed
lower bound without refusing merely because a child is still running; the
helper enforces actual live Job CPU. Success requires complete accounting.
An exception or missing/nonterminal helper receipt never reports unknown child
work as zero or as a complete total. Wall never resets
after direct-child exit or pipe EOF. The repaired helper drains remaining Job
processes under the original bounds and retains termination evidence on refusal.
Polling does not promise zero overshoot. This is committed memory, not RSS.

The parent retains the full actual helper observation, exact child argv,
controlled environment evidence, direct exit/EOF, terminal zero-active Job,
log FileRef and raw runtime FileRef. Success requires actual exit 0, no helper
error/cleanup error, terminal accounting and the single child's completion
message referring to those same runtime bytes. A string in a file cannot replace
that observed outcome. The runtime JSON remains the reader's existing closed
schema: interpreter/version, NumPy/rawpy/LibRaw versions, actual module/DLL
FileRefs and thread settings. Parent rehashes those actual dependency files and
the interpreter after the capture, without importing or executing them.

Each runtime and log is bounded to 1 MiB, each result to 4 MiB, and the module
list to 32 distinct refs, each at most 128 MiB read in 1 MiB chunks. Source/input
reads are bounded and require unchanged identity, extent, timestamp and bytes.
No source snapshots or new image arrays are emitted. The retained artifacts are
the one log, one unchanged runtime JSON, terminal result and bounded failure
publication copies. The original runtime JSON may remain after refusal as failed
evidence; it has no independent authority without the completed parent record.

## Result and failure boundary

Result `runtime-capture-1/result.json`, schema `m193c-runtime-capture-v1`, succeeds
only as `COMPLETE_DEPENDENCY_RUNTIME_CAPTURE_ONLY`. Its fields bind execution
release, parent/child commands, build/private admission/review, source and input
maps before/after, controlled environment, actual helper observation, log,
runtime, module refs, work and original/secondary errors. The work in the file
is prepublication; the final parent stdout includes work through final checks
and the actual terminal result FileRef. Root's observed parent exit and final
stdout are required alongside this result. The native release preparer must
receive this actual completed record's external SHA, not a proposed value.

All source/input/interpreter/runtime bindings and the exact serialized terminal
result are checked again after publication. Late serialization/write/flush,
source/hash or time failure revokes the canonical positive result, preserves
the first bytes and writes a refused replacement. The first error remains
primary; cleanup/persistence/stderr failures are separate, with no stdout or
stderr exception allowed to recover success. Failed attempts retain any bounded
log/runtime files and their actual hashes where readable. No automatic retry,
second capture, runtime rewriting or native launch is permitted.

The already independent process controls commission the underlying Job/log/time
mechanism. Before this release root reviews concrete refusal paths: stale
source/input/executable, missing private2 or wrong build, wrong argv, nonzero
capture, mismatched runtime/log ref, nonterminal Job, exceeded bound and changed
post-write evidence. Those are rejection conditions of this wrapper; this
document claims no wrapper execution or new control pass.
