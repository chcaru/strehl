# M193c process-memory amendment — independent review

2026-09-07. **SOURCE AND RETAINED-RECORD REVIEW ONLY.** No process-control
command, helper import, allocation fixture, build, image read or RAW decode
was executed by this reviewer. The original two failed attempts remain
unchanged. This review permits freezing the next finite process-control
command; it is not a claim that the amended eleven controls have passed.

## Reviewed source and preserved failure

| File in experiments/m193c-output-grid | Bytes | SHA256 |
| --- | ---: | --- |
| controller-amendment-2.md | 2637 | e2cf41d846baa5bb4adf1da3606cd6662d8b61d2c367fbd79dc702be6740db68 |
| bounded-process.py | 10522 | 1dba8d87c8818aecf98078d1a926e5ff9c059a7d242cf5c46fcc962f14dfc5ab |
| controller-child.py | 1687 | b38b5f188be358f669a0d00de63c1e2968d6f270cdcb767dfa09c108315f8f02 |
| controller-controls.py | 11965 | e653c448aaece6caee1d28ada436cbb2bb0b799b951f4d338b85cc6dc48f282a |
| controller-controls-2/result.json | 16988 | c68f94e71a2ad95018a91b060a87a8afa9ac828c185893e0041bd494ec029244 |

The original run2 release is
`e1aa6aa1a8de77d6b1da6ba7b4ee135fd0adf24451df6a8bf88af9a04a6cfbda`,
committed by the parent at `3cfefcbf` before launch. The parent reports
collecting that launch's actual exit code 1. This reviewer independently
read the terminal JSON and the relevant actual logs, not the original OS
wait result. The terminal status is `UNCOMMISSIONED_CONTROLLER`; source
maps before and after are equal, and finalization errors are empty.

There are seven attempted rows. The first six passed; the seventh, memory,
failed its then-registered predicate. Later controls were not visited.
The repaired nested row records parent PID 44440 and executing/requested
child PID 43384, four Job processes against the valid companion's two,
the named wall refusal, empty cleanup errors, terminal accounting and
zero active processes. Its 92-byte log hashes to
`a94c08e0e8617bc4909e4938adb73fbd7f6f17e0ce42784a1633145edc97c6cb`.
This is a successful witness for that repaired control in run2; it does
not explain run1's process multiplicity or missing body marker.

The memory log is exactly `M193C_MEMORY_REFUSED` plus CRLF: 22 bytes,
SHA256 `1128b5db9d7ca34bd50a8740f673da48cbb4f4ed3b94034db230cc2a9fc2cd18`.
The actual result records `ValueError('child committed-memory bound')`,
peak Job memory 143831040 bytes against a declared 67108864-byte limit,
owned termination exit 3784556766, empty cleanup errors, terminal
accounting and zero active processes. The original assertion required
a clean exit 7 with no parent error; therefore this combination correctly
failed that assertion. The parent refusal must not retrospectively turn
the old complete result into PASS.

The original control's missing successful allocation companion and narrow
clean-exit assumption were not caught in this reviewer's prior static
review. The retained failure, rather than a successful source argument,
exposed the latter choice.

## Prospective predicate and power

The amended controller runs `memory-allowed` before `memory`. Both invoke
the same child branch and the same `bytearray(128 << 20)` expression. Only
the declared Job limit and successful-allocation exit disposition differ.

The positive arm has a 256 MiB limit and requires the actual size marker
`M193C_MEMORY_ALLOWED=134217728`, exit 0, no parent error and no cleanup
error. A failed positive arm stops the schedule before the negative arm.
This is necessary evidence that the literal fixture can allocate the
requested volume in a finite process under the allowed setting.

The negative arm retains 64 MiB. Its two explicitly named acceptable
routes are:

1. No parent or cleanup error, exit 7 and the child's `MemoryError` marker.
2. The exact parent error `ValueError('child committed-memory bound')`
   and an actual returned Job peak strictly above the same 64 MiB limit.

The negative row also requires the immediately preceding positive row to
have passed. Both routes require empty cleanup errors, terminal Job
accounting and zero active processes. The chosen route is recorded. A
generic exception, a wall/log/CPU refusal, a changed-input refusal or an
unprotected clean exit 9 does not satisfy the new predicate. A memory
refusal accompanied by a cleanup failure is not accepted either.

The second route intentionally tests the parent's operational rejection.
It does not require that a particular child marker reached the retained
log before the parent stopped the process, or establish which allocation
caused a reported high-water value. Its admissible claim is that this
fixed task was rejected at the named observed-memory boundary and its
owned process tree was cleaned up. The independently required successful
same-allocation companion supplies the previously missing positive power;
it does not explain the negative arm's memory-accounting mechanism.

The helper still returns an error for a memory-bound child. The new test
predicate interprets that error as an expected negative-control outcome;
it does not reclassify it as successful product work. No production cap,
image budget, numerical tolerance or image population changes.

## Readback, ownership and remaining scope

After setting the Job limits, the helper now queries the actual extended
limit record before creating or resuming the child. It stores the flags
and limit and requires the Job-memory flag plus exact requested limit.
Every control repeats those assertions against its declared limits.
The delta does not replace the previously reviewed suspended-start,
owned-Job assignment, explicit owned termination, final live-handle
accounting, zero-active observation or guarded log finalization paths.
The source sets the existing kill-on-close flag as before; the additive
readback assertion specifically commissions the Job-memory flag and value.

The total population is now exactly eleven. Child wall limits remain
10 seconds ordinarily, 1 second for the single timeout and 5 seconds for
the nested timeout; child CPU remains 10 seconds and retained logs remain
65536 bytes. The controller's non-resetting 120-second outer allowance
and final source/input/artifact checks are unchanged. Actual completion
of all eleven under the new release remains required; the seven-row
historical result cannot substitute for it.

Microsoft documents the Job-memory limit as committed virtual memory,
with peak Job/process memory fields separate from working-set limits.
The cited definitions do not justify relabeling this peak as RSS or
deducing why this specific above-limit value accompanied `MemoryError`.
See the [basic limit definition](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information)
and [extended limit definition](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information).
The asynchronous observed rejection and cleanup are not a proof that
instantaneous memory or elapsed work never exceeded a bound.

**Disposition:** no additional blocking defect found in the reviewed
amendment2 source delta. Freeze these bytes and the exact fresh command
before executing the new eleven-control schedule. Preserve all actual
outcomes, including any new refusal, before considering a later image
release. This is a scoped source-review disposition, not process or
scientific admission.
