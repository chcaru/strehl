# Independent source review: M194h checker launcher

2026-09-08. PASS_SOURCE_REVIEW_ONLY against the exact pins below. No launcher,
driver, checker, Job control, renderer or numerical helper was executed. This
review covers root's new wrapper; I authored the reused driver and do not claim
a second independent verification of that driver's commissioned controls.

## Held files

- `work/check-run.py`: 5,770 B,
  `c862f54e5811c07a4167c0ae6e03bedf43d7cc42bbd73c225abe7eb7d06edc15`.
- Reused `build-and-run.py`: 34,552 B,
  `21d363a66633a3c973986a2a03503aa503dcdc063bd3781aa4e30c8b245eaf1e`.
- Compatibility read of `independent-verify.py`: 68,539 B,
  `045fb2a20126440446e9128c05b7eb1d5d4a1ed8c4b2f3276b5dc95130936579`.

All paths above are beneath `experiments/m194h-pedestal-causality/`.
The wrapper is under `work/`, belongs to the independent release source map,
and does not alter the producer's top-level compiled closure or require a new
build. Include this review in the independent release closure.

## Source findings

The root calculation correctly reaches the repository from the extra work
directory. The wrapper authenticates its exact bytes and the driver against the
five-key `m194h-independent-check-release-v1` source map before compiling the
driver as a named module. That does not enter its main. It then verifies the
whole positive source map through the held driver reader before launch and again
after the completed checker, and rechecks the release against the original
buffer's FileRef.

Only one command is permitted: this Python executable, `-I -B`, the exact
`independent-verify.py`, release path/hash, source hash, and fixed sibling
`independent-check-1` output. No retries or render invocation are added.
The fresh wrapper output is `independent-run-1`; the checker separately requires
its own fixed output directory to be fresh.

`Budget("components")` is only a constructor convenience: stage becomes
`checker` and caps are replaced before its first check. The inherited methods
consult those fields dynamically; no stale 60-second component deadline survives.
Setting `driver.START=START` retains wrapper setup in whole elapsed time.
The operative limits are combined parent plus owned Job 60 CPU seconds, 120 wall
seconds, and 1 GiB committed memory for the checker child Job. The child receives
remaining CPU minus 2 seconds, and remaining wall minus separate 12-second cleanup
and 3-second publication reserves. No cap increase follows from cleanup.

The Job path is the pinned bounded-process source with the driver's closed AST
selection of required Windows definitions. It does not call the whole M12
harness loader. Live queries update the combined CPU check; the returned terminal
Job record is written and linked before admission checks. Terminal active-process
zero, complete accounting, successful exit, pipe EOF and drain remain required.
Job CPU is transferred from live to completed exactly once; a CPU-incomplete
prefix cannot become successful through a final JSON status.

The checker final-record reader and log ceiling are each 1 MiB, matching the
checker's current result writer. The final-reader change was reverse-substituted
back to 512 KiB and reproduced the previously reviewed wrapper hash exactly.
Both output roots are
scanned under one 16 MiB ceiling with another 192 KiB reserved for publication.
The checker itself caps emitted records at 8 MiB, so its own 16 MiB advertised
limit is not an extra allowance. Parent result slots, child receipt, log and
tail remain in the wrapper root. This is observed file accounting, not a claim
that filesystem stalls or delayed scans cannot cause refusal.

A successful child is insufficient: actual `result.json` must equal the entire
retained child log byte for byte, carry the held PASS status, true
`independent_complete`, and no error. An emitted refusal or warning interleaved
with stdout cannot satisfy that exact equality. The wrapper labels its success
`COMPLETE_INDEPENDENT_WRAPPER_UNVERIFIED`; it does not set a quality verdict.

## Publication and external admission

Canonical publication precedes the parent tail sample. The tail binds that
canonical FileRef, retains parent CPU plus completed/live Job CPU and accounting
completeness, and charges 2 CPU / 3 wall seconds inside 60/120. Bounded, complete
raw stdout advertises exact result/tail refs. If terminal/tail publication fails,
the wrapper returns refusal and attempts to retain the failure; an old positive
canonical file alone is never admission.

Two concrete omissions found in the first draft were repaired: final release
recheck and explicit bounded/full stdout write. No scientific function changed.

Root must retain an independent actual wrapper outer command/source/exit, raw
stdout/stderr and exit file. Admission requires actual exit zero, no timeout,
the exact advertisement and result/tail association, complete child accounting,
and whole outer wall within both 120 seconds and the tail sample plus 3 seconds.
Parent CPU remains a sample plus reserved tail, not GetProcessTimes completion;
CPU is not inferred from wall. The wrapper's own process memory is not the
child Job's 1 GiB guarantee. The outer records must fit the released evidence
allowance as well.

No new control run is required by this source review. The existing helper's
process/publication controls are reused; actual terminal evidence is still
required from the one separately released checker invocation.
