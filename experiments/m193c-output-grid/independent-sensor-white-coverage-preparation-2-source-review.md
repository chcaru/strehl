# Independent review of the coverage preparation stat repair

Status: **VERIFIED source correspondence; no remaining source blocker found.**
The six private metadata controls and the successor preparer have not been run
by this reviewer. Root must freeze their actual invocation and inspect the
result before treating the new release as prepared. No RAW/TIFF payload,
native reader, coverage constructor, registration or quality computation was
executed in this review.

Reviewed successor: `work/prepare-sensor-white-coverage-release-2.py`,
43,517 bytes, SHA256
`290ee0598f3704d6ddfeafe6516ba9b15a71aefe40a0ad8ce689a620bf538804`.
The original remains 33,553 bytes,
`db33e171b786cbdef81fc8863aa2e77d9cb132075d6910a473e419066991cbfe`.
The old source and
`independent-sensor-white-coverage-preparation-source-review.md` are preserved.
My earlier source review did not flag the whole-stat-result comparison; that
was a missed choice point, and the old review is not evidence that this
boundary had been commissioned successfully.

## Actual failure and what was not recorded

I read the original retained console, exit and outer observation. The command
used the old source's exact external digest. Root observed exit1 and
1.3611104 seconds of elapsed wall time. The traceback reaches `Metadata.bytes`
while parsing the native outer record, and reports
`ValueError: same-buffer metadata identity`. This happened before release or
preparation-details publication. It is a preparation refusal, not a failed
registration or a revoked native nine-frame admission.

The failed check combined buffer length, buffer hash and stat-result equality.
Neither the failed operand nor the before/after stat fields were retained.
Root's subsequent observation that the outer file still had2,393 bytes and
its expected `078747cc...` digest does not establish what every operand saw
during the failed read. Access time is therefore **not a proved historical
cause**. No exact CPU cost is inferred from the wall observation.

| Retained record | Bytes | SHA256 |
| --- | ---: | --- |
| `work/sensor-white-coverage-preparation-1-console.txt` | 1,137 | `673bdcaebef2db173ac53269c2bed7eb76dfce41d31c325eebc7b9331a6d0380` |
| `work/sensor-white-coverage-preparation-1-exit.txt` | 3 | `f1b2f662800122bed0ff255693df89c4487fbdcf453d3524a42d4ec20c3d9c04` |
| `work/sensor-white-coverage-preparation-1-outer.json` | 2,469 | `788e4f605e34ebc30f2407bd3f5135f267804f452b17b42dcc86982f932559fb` |

## Independent API choice

Python documents access time separately from content-modification time, exposes
nanosecond timestamp attributes, and describes the legacy stat tuple containing
access time. It identifies `st_ino` as a file identifier on supported Windows
filesystems. Comparing explicitly selected named fields is therefore a better
fit for this content/identity contract than treating an entire stat result as
one immutable quantity. The new check uses `st_mtime_ns`, preserving the
declared modification-time precision. [Python3.12 os.stat_result documentation](https://docs.python.org/3.12/library/os.html#os.stat_result).

Microsoft documents that file timestamps have filesystem-dependent update
behavior, including delayed NTFS access-time updates, and can be changed
without modifying file contents. That supports a prospective access-time-only
permissive control; it does not diagnose this particular failed invocation.
[Microsoft File Times](https://learn.microsoft.com/en-us/windows/win32/sysinfo/file-times).
Microsoft also documents volume/file-index comparisons as a way to identify
the same target. The helper retains device/inode checks for the opened handle
and path instead of replacing identity with a timestamp or hash alone.
[GetFileInformationByHandle](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfileinformationbyhandle).

## Repair and powered controls

`stable_metadata` selects exactly device, inode, extent, `st_mtime_ns` and
Windows file attributes. `Metadata.bind` and `Metadata.bytes` use it; the byte
reader additionally checks the actually opened device/inode against its
pre-read path observation. Buffer extent, SHA256 and final selected metadata
now have separate refusal messages. JSON parsing still consumes those exact
authenticated bytes. The method does not use access-time tolerance, skip the
content digest, accept a changed modification time, or weaken reparse/ordinary
file checks. Later source/input rechecks remain in place.

The six private calls use the actual `Metadata.bytes` path in one fresh owned
directory. Their proposed powers are concrete:

- Baseline returns the original bytes. The access-time-only callback changes
  the actual access timestamp after the read closes; the control requires that
  timestamp to differ while selected metadata and content hash stay unchanged,
  and requires the same returned bytes.
- Changed content is written at the same length before the byte-reader call,
  with original modification time restored. It must have an actually different
  SHA and unchanged selected metadata, and must fail specifically at the
  buffer-SHA boundary.
- The modification-time-only callback changes the actual timestamp while
  preserving content and the other selected fields. It must fail specifically
  at the selected-metadata boundary.
- The inode callback retains the original fixture and substitutes a separately
  created same-byte, same-modification-time file. Its inode must actually
  differ, with all other selected fields and content unchanged; it must reach
  the selected-metadata refusal.
- A final fresh restored companion returns the original bytes without a fault.

Each row records actual before/after selected fields, access timestamps,
original/actual/returned digests and the expected versus observed exception.
Only the named `ValueError` message can satisfy a refusal; a setup error or
unrelated exception cannot masquerade as the desired negative. Real changed
fields and hashes are required, so an ineffective timestamp or replacement
operation fails the control. These are prospective powers, not six measured
passes. The private fixtures do not establish the cause of preparation1.

## Closed scope and retained costs

I parsed both source versions with the standard library AST and compared
top-level definitions. Only `Metadata` and `main` differ; `stable_metadata`,
`save_bytes` and `metadata_controls` are added. Ten other definitions are
unchanged and none is removed. The fixed coverage consumer, native authority,
TIFF stat-only policy, runtime requirement, gauges and numerical bars remain
those of the preceding review. The new file writes release2/details2 and a
fresh controls directory; it retains the still-uncreated coverage output1.

The v2 root carry basis must bind the immutable first preparation carry, its
source, console, exit and outer record, and follow that saved command's actual
input/review references. The old30 CPU/60 wall/2 MiB reservation is fully
spent, not replaced by a guessed measured CPU or refunded from its short wall
time. The second attempt receives a distinct reservation of exactly the same
size; Decimal checks enforce both additions from the original native base.
The original1200 CPU/1800 wall/4 GiB file/128 MiB metadata caps remain fixed.
The separate sum-of-nine-TIFF-extents plus5 MiB constructor reservation remains
separate and unchanged.

Controls, repeated/failed writes, receipts, release publication and final
checks share the new attempt's limits. `save_bytes` charges every requested
write before writing, including overwrites; no write allowance resets after
the controls. A failed control cannot issue a prepared release. The existing
late-publication path retains its primary exception, records revocation
failures and attempts canonical refusal if rename fails. Root must still
require the actual zero preparation exit and inspect its artifacts.

This is a bounded source repair verdict with primary API support. The
successor's actual metadata controls, complete preparation and subsequent
coverage outcome require their own retained execution records.
