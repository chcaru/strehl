# Controller amendment 1 — independent source-choice review

2026-09-07. **READ-ONLY EVIDENCE REVIEW / AMENDED SOURCE UNEXECUTED.**
Disposition: the amended fixture and predicates are adequate for a newly
frozen finite process-control command. No remaining source blocker was found
for that scoped run. This review did not launch a child, import a helper,
rerun a control, compile, or read RAW/image data. Only this review was written.

## Retained first outcome and the review miss

The first exact release was committed at
`5a727a12bd31abd450455dce91a6ae2f83b9f0a1`, release SHA256
`8fb5686c322513f9a35a5eca6ef147d4b70b506d03ad2c9e4b8f1086458cd716`.
I independently read its actual `controller-controls-1/result.json`
(14891 bytes, SHA256
`e64683aaab93aca3590607e7d6f3d1d0d80a7ed710beb178ccb3a7bb01139889`)
and nested log (24 bytes, SHA256
`46786f88b680adb1e32c2e48fbdd95f3d8fb28fddc11dd03021d04ac58eb6b99`).
Root separately reported collecting the actual launch exit 1. I did not
independently observe that operating-system exit.

The result is `UNCOMMISSIONED_CONTROLLER`: five passed controls, then a failed
sixth `nested-timeout`. Memory, late-log-binding, changed-input and restored
controls were unvisited. The six recorded rows all have terminal Job
accounting, zero active processes and no cleanup errors. The nested row
records `ValueError('child wall bound')`, approximately 1.047 seconds, and four
total Job processes. The first five rows each record two total processes.
Sources before/after agree and finalization errors are empty.

The nested log contains only `M193C_NESTED_PID=46736`. It does not contain
`M193C_SLEEP_STARTED`. Both the literal total-process requirement of2 and
the startup-marker requirement failed. These observations support retained
timeout/cleanup accounting; they do not establish that the intended nested
sleep body executed. There is no complete controller PASS to carry forward.

My preceding source review accepted the literal two-process predicate and
implicit nested standard handles. I missed these fixture-choice weaknesses.
The actual failure remains necessary evidence; this amendment does not
retroactively make the first review or first run a successful commission.

## What the installed source explains, and what it does not

I read only the installed PSF Python standard-library subprocess code and
executable metadata, without executing Python. The installed
`C:/Users/chris/AppData/Local/Programs/Python/Python312/Lib/subprocess.py`
is 90963 bytes, SHA256
`e9886605ccac88bcfe2330a1b4cd8f132cbaf97ebb6834b1dcb5a69b127b8d5b`.
Its Windows `_get_handles` returns six `-1` values when all three standard
streams are `None`. Consequently `_execute_child` does not take its explicit
`STARTF_USESTDHANDLES`/standard-handle-list path. The old nested `Popen` used
exactly those defaults. With `stdin=DEVNULL`, `stdout=sys.stdout.buffer` and
`stderr=STDOUT`, the same installed code obtains and duplicates the supplied
stdout file handle and passes the explicit standard handles to the child.

That is a concrete reason to repair stream forwarding. It is consistent with
the missing message, but does not prove the body failed to start, that one
second was insufficient, or that stdout alone caused the observed failure.

The recorded interpreter path is a regular 104952-byte file with Python
3.12.10 version metadata and no filesystem link/reparse target. Its SHA256 is
`4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a`.
Neither that metadata nor the2/4 aggregate process counts identifies an
extra process, its executable, or its cause. In particular, this review does
not call the multiplicity a launcher/shim effect. No new process census or
diagnostic launch was performed.

## Amended power and exact source scope

The reviewed amendment is `controller-amendment-1.md`, 2444 bytes, SHA256
`a6689921a17c08523e50faf85bb67ed87c3b410ca4395ba12652577a812297c8`.
The final source changes inspected are:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| controller-child.py | 1645 | 3aec48e775e2864cae8df2daafc4d10a9b5857b8fc928112ef8bec6b2da74da0 |
| controller-controls.py | 11004 | 2c0c7c803393d24d7a5a8bfd34066d59317346f82d328d060e8118c6b0c7ac6f |

The process helper remains `0983606a...`; no Job, memory, CPU or log arithmetic
change is proposed. The reviewed changes make the nested stdin null and
forward stdout/stderr explicitly. The parent prints its actual PID; the
sleeping body prints `os.getpid()` itself before the unchanged 30-second
sleep. The requested `Popen.pid` is retained separately. The reader requires
exactly one parent, body and requested PID marker, with distinct parent/body
PIDs. It deliberately does not assume the body PID equals `Popen.pid`.

The control uses the same run's already passed valid companion: its Job
process count must be positive, and the nested count must be strictly larger.
Both the companion count and the actual difference are recorded. This
re-chooses the question from “is the entire Job exactly two processes?” to
“did this explicit nested fixture add processes and reach its distinct body?”
It neither hardcodes the observed 4 nor invents a universal multiplicity.
Missing the nested call, losing the body marker, repeating a marker, using the
parent's PID as the body, or leaving the count unchanged fails the predicate.

All controls additionally require `terminal_job_accounting is True` and
`active_processes == 0`; the existing exact refusal/exit/log and cleanup-error
predicates remain. The nested case still must refuse at its wall boundary,
not return normally or fail with an unrelated exception. Its prospective
wall allowance changes from 1 to 5 seconds while the body still sleeps 30.
This leaves real timeout power, but does not promise that every possible
machine will reach the body in 5 seconds. A missing marker remains a refusal.
The single-timeout's 1-second allowance is unchanged.

The ten-control population, 120-second wrapper allowance, 64 MiB Job committed
memory, 10-second child CPU allowance and 65536-byte log cap are retained.
No image tolerance, precision reserve, render population or scientific bar
changes. The amended child adds a PID line to the single-timeout log as well;
that existing control already tests the startup marker by containment, so
the added diagnostic does not alter its required outcome.

Freeze this amendment, reviewed source and exact fresh command before the
next run. Preserve the complete first result, logs and original snapshots.
Only a complete new ten-control result can commission the amended population;
passing this source review cannot admit the unvisited controls, a compiled
build, precision witness, production output or native rehearsal.
