# Coverage preparation1: retained metadata-identity refusal

MEASURED: the reviewed metadata-only preparer
`work/prepare-sensor-white-coverage-release-1.py`33553 bytes, SHA256
`db33e171b786cbdef81fc8863aa2e77d9cb132075d6910a473e419066991cbfe`,
returned actual exit1 before writing either the proposed release or details.
No coverage process, constructor, registration, RAW or TIFF payload read ran.
All nine previously admitted native derivatives remain unchanged.

The exact executed argv is retained in
`work/sensor-white-coverage-preparation-1-outer.json`2469 bytes, SHA256
`788e4f605e34ebc30f2407bd3f5135f267804f452b17b42dcc86982f932559fb`.
Its actual outer duration is1.3611104 seconds. Console1137 bytes at
`673bdcaebef2db173ac53269c2bed7eb76dfce41d31c325eebc7b9331a6d0380`
and the three-byte exit1 record remain beside it.

The traceback stops at `Metadata.bytes` while reading the native root outer
record, with `ValueError: same-buffer metadata identity`. The conjunction checks
length, SHA and equality of the entire before/after `os.stat_result`. It did not
retain the two stat values or identify which term failed. Subsequent root reads
still find2393 bytes at the original SHA
`078747cc22ec8e74101ea173075182ad09151723d7ca0854328ef08d13cd0fc1`.
That later agreement does not prove the state during the failed read.

ARGUED correction: full stat-result equality is the wrong stable-file contract
because it includes access time. Python distinguishes access time from content
modification time, and Windows documents delayed access-time updates. Use
explicit device/file identity, extent, modification time in nanoseconds and
attributes, plus opened-file identity and complete same-buffer SHA. Retain
access-time-only, identity/mtime/content destroyers and restoration on the same
new check path. This is a prospective correction, not proof that access time
caused the historical refusal. Sources: [Python3.12 stat attributes](https://docs.python.org/3.12/library/os.html#os.stat_result.st_atime),
[Windows file times](https://learn.microsoft.com/en-us/windows/win32/sysinfo/file-times).

The prior source review remains preserved. Its independent reviewer confirmed
that whole-stat equality was missed; the new source/review are separate files.
The old30 CPU/60 wall-second/two-MiB preparation allowance remains fully charged.
Exact CPU for the failed preparer was not separately recorded, so it receives
no refund from its prospective bound. Another identical bounded allowance is
added explicitly for the successor within unchanged global caps. New root carry
is324.453125 CPU seconds,347.4812478 wall seconds,2157421716 file bytes and
20967233 metadata bytes. These values include reserved work, not merely measured
usage. The constructor's1785427283-byte snapshot reservation remains separate.

The successor must pass independent source review and actual metadata controls,
publish a checked release, and then run the unchanged coverage subject once.
This refusal supplies no evidence about registration support or image quality.
