# Build 2 compile-completion source addendum

2026-09-08. SOURCE ONLY. No helper, driver, metadata control, build, test listing,
component test, render or numerical checker was executed by this author.

Build 1 remains REFUSED and retained. Root's actual retained outcome records
Cargo core exit zero plus pipe EOF at about 10.375 seconds, followed by one active
owned-Job process until the old finite limit; final owned cleanup reached zero.
That observation does not identify the lingering process or prove it was idle.
This correction does not relabel that run or refund its charged work.

## Exact source

- New `bounded-build-process.py`: 16,334 B,
  `6c4b6e6222e1b58ec408fbd949d7a90bbb0c12778c292517c6eb6539eb4b036b`.
- Revised `build-and-run.py`: 38,240 B,
  `8276fc134d7db6dfcf2381bffb8796d4946ad1aa2a551ca3e275ddf3c78d8cf6`.
- Immutable source base `experiments/m193c-output-grid/bounded-process.py`:
  `47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b`,
  checked unchanged after the source write.

The new helper derives from that base: add the compile-only guard, cleanup
record/function and replace only the post-exit wait policy, plus descriptive
scope. Log pumping, suspended launch/Job assignment, resource polling, emergency
cleanup and terminal observation remain inherited. The unused original
whole-harness loader is not called; the driver supplies the closed AST Job API.

Driver dispatch changes only for build compile indices 0 and 1. Its
`load_process(bindings, compile_only=False)` preserves the strict default,
including compatibility with `work/check-run.py`. Compile mode selects the new
source/hash and adds only `JOB_OBJECT_BASIC_PROCESS_ID_LIST_CLASS` and
`job_process_ids` to the existing M12 AST selection. The latter has its existing
fixed 1024-entry buffer. Test listings, components, renders and the checker keep
the original strict helper. A process-policy assertion enforces that split.

The new scratch target is `target/m194h-pedestal-causality-2`; the build output
is `build-2`. `components-1` and `subject-1` are unchanged. The new helper is
a mandatory positive source binding. Fresh compile artifacts and subsequent
actual test listings remain required before build completion. No Cargo feature,
Rust body, scientific population or resource maximum changed.

## Cleanup record and admission

Every compile-helper record has `compile_cleanup` with these 17 keys:
`schema, policy, disposition, attempted, succeeded, completed,
before_accounting, after_accounting, remaining_process_ids,
pid_query_performed, pid_query_error, started_wall_seconds,
ended_wall_seconds, wait_seconds, max_wait_seconds, error, scope`.

Schema is `m194h-compile-owned-descendant-cleanup-v1`; policy is
`AFTER_DIRECT_ZERO_AND_PIPE_EOF`. Before any intentional termination, the actual
direct Cargo process must have returned zero and its pipe reached EOF.

- `NATURAL_JOB_EXIT`: no intentional termination attempted or succeeded;
  complete actual before/after accounting has active count zero.
- `INTENTIONAL_OWNED_JOB_CLEANUP`: actual pre-termination accounting has active
  processes; a bounded PID census was retained; the owned Job handle alone is
  terminated with marker `0xE194B002`; final active count is zero. Attempt,
  success and completion are all true.
- `UNVISITED` and `REFUSED` cannot admit completion.

PID values are a list of distinct positive Windows PID integers, at most 1024,
or null when no query was performed. They are observations only, never kill
targets. No executable/creation-identity API was added, per root's narrowed
scope. The PID census precedes the fresh `before_accounting` observation;
cardinalities can differ. Natural exit during that query is recorded as natural,
with the observed PID list retained rather than invented empty.

The cleanup interval starts before its observation/query/check callbacks.
`max_wait_seconds=5`; the deadline is the earlier of that interval's five-second
limit and the original child wall deadline. Successful records have numeric
start/end/wait, with wait=end-start and wait at most five seconds. This allowance
includes scratch scans and resource checks, not just sleeping. An OS call or
scan that overspends can therefore refuse even if the Job eventually reaches zero.

Generic `termination` keeps its original meaning of failure/emergency cleanup.
It must remain unattempted for a successful child. PID query or termination
failure retains the new record's error and falls through the unchanged bounded
failure cleanup; it cannot become an intentional-success receipt.

The driver durably saves and links the child terminal record before cap or
admission assertions. It requires the existing error-free direct exit, EOF,
drain, final Job-zero/accounting and resource checks, then validates the closed
new record only for compile indices 0/1. It forbids the new record elsewhere.
Final Job CPU remains counted once. Original stage limits and publication/
cleanup reserves are unchanged.

## Source checks and release

Metadata-only AST inspection found only `load_process`, `child_call` and
`main` changed among the driver's existing named definitions, plus new
`admit_compile_cleanup`; all other named bodies, including the Windows reader
repair and metadata control population, remain unchanged. Path/source constants
and the required helper binding changed as described above.

The independent source reviewer and checker author received the exact schema
and candidate files before this note. Root owns build2 preparation/capture,
failed-attempt carry and finite release. The checker independently admits this
cleanup policy only for the two compiled artifacts. This note is a source
amendment, not an execution result or independent scientific verification.
