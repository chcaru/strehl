# M193c process controls3 — independent retained-result read

2026-09-07. **VERIFIED BY RECORD/FILE INSPECTION, NO RERUN.** This is a
separate addendum to the held `controller-amendment-2-review.md`; the earlier
source review and both failed attempts remain unchanged. No child process,
helper, build, image reader or RAW decoder was invoked by this reviewer.

The parent reports that the exact command committed at `e1488da8` terminated
with exit 0 after about 7.96 seconds. That OS exit and launch duration are
attributed to the parent's collected command, not independently observed by
this reviewer. I reopened the terminal result, release and all listed files:

- `controller-controls-3/result.json`, 25150 bytes, SHA256
  `39a6f6e93e3b8df83834ab4046c7f30d6f42612df0cb0ec57ea158815baa7cfd`.
- `controller-controls-release-3.json`, 3158 bytes, SHA256
  `55edb7eb650bd1f55c2050228f189c092ea5b2cdd4052e1a522934a595a10849`.

The actual recorded `sys.orig_argv` equals the release's sole command after
its one self-release-SHA substitution. It uses the registered fresh
`cache-controller-controls-3` and output directory. All four current source
files, their retained snapshots, the eleven logs, the restored watched file
and all release inputs match their declared SHA256 and lengths. The sixteen
listed artifacts are four source snapshots, eleven logs and that watched
file. Source maps before and after agree. The sources are exactly the held
amendment2 versions: helper `1dba8d87...`, child `b38b5f18...`, controller
`e653c448...`, and unchanged M12 Job helper `6cfb4089...`.

The terminal status is `PASS_OWNED_PROCESS_CONTROLS_ONLY`; `error` is null
and `finalization_errors` is empty. All eleven deciding rows occur once in
the registered order, with no omitted or replacement arm:

| Control | Independently inspected outcome |
| --- | --- |
| valid | Exit 0, exact valid marker, clean observation. |
| nonzero | Actual exit 7 and the named exit marker. |
| exact-log | Exit 0 and exactly 65536 actual `x` bytes. |
| overflow-log | Named log-bound refusal and exactly 65536 retained `x` bytes. |
| timeout | Body marker present; named 1-second wall refusal. |
| nested-timeout | Parent PID 20912, executing/requested child PID 32276; 4 Job processes versus the valid companion's 2; body marker and named 5-second wall refusal. |
| memory-allowed | Actual 134217728-byte allocation marker, exit 0, clean observation under the 268435456-byte limit. |
| memory | Named parent committed-memory refusal; observed peak 143798272 bytes versus the unchanged 67108864-byte limit; route `parent-observed-peak`. The retained child log also has its MemoryError marker. |
| late-log-binding | Original log-bound refusal retained alongside the single expected `M193C_PRIVATE_LATE_LOG_READ` cleanup error; 65536 actual `x` bytes remain. |
| changed-input | Child exited 0 but the parent refused the changed watched input. |
| restored | Exact valid marker and clean exit 0; final watched bytes are the original private input. |

Every row records terminal Job accounting and zero active processes.
Cleanup errors are empty except the one deliberately injected late-log
error. Every configured flag readback is 8704 (`0x2200`) and every configured
memory limit matches that row's declaration. The positive memory peak is
144113664 bytes, below its 256 MiB limit. The negative remains an expected
protective refusal, not a successfully completed allocation/product.

All returned child CPU totals are finite and below their 10-second limits.
The result's controller elapsed value is 7.687 seconds **before terminal
result persistence**, below the outer 120-second allowance; it is not the
parent's process-exit duration. Timeout rows legitimately report later
terminal observations after the configured refusal point. This is bounded
process commissioning, not an exact no-overshoot or timing benchmark claim.

The observed memory peak does not establish RSS or explain the earlier
above-limit peak/MemoryError combination. The process-count observations
do not establish a cause for the 2/4 multiplicity. Original run1/run2
statuses remain uncommissioned and are not pooled into this completion.

**Disposition:** the actual completed eleven-control result supports the
scoped owned-process-control prerequisite. It admits no private pixels,
derivative, RAW decode, numerical precision, registration result or final
campaign budget. Those retain their separately registered consumers and
encompassing budget owner.
