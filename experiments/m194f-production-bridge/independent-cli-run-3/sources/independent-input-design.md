# M194f independent input and reread controls

2026-09-07, roadmap_audit. Written after the committed root protocol
`9da113f5`, before reading or executing the new Rust adapter. I read the
existing M194b strict reader, the actual M194e manifest/CFA gate/child result,
and the final M194f protocol. This is the bounded input lane; Zeno owns actual
TIFF, coordinate and centrality values, and root owns build/driver closure.
The old numerical sources and consumers remain unchanged.

## Authority and independently selected failure inputs

The actual manifest hash is
`f47c2b8720560fe9dbd777eeed3281ce2531f1f2287f5c88ef7b51a083d03299`;
the actual CFA gate hash is
`706462ad18a5a3846cadd99e1ef24d6b92b77e064df2e34cbe72e45907fc06a6`.
The child result is `8901be629a789d2959482baed15bef3e8cf23ba5f13418f66afdfb9fbf8bacdd`.
All genuine-load controls start from these independently supplied values.

I will separately exercise parsed private validators with revised JSON to
reach semantic checks beyond stale checksums. Those inputs remain private API
controls and cannot become genuine optical authority. Rehashing both a child
and an untrusted gate is not authorization. The valid companion is the same
unchanged parsed record and the complete genuine chain.

1. Reject top-level and nested duplicate keys, trailing JSON, nonfinite values,
   scalar roots, missing/unknown fields, unknown schemas and incorrect exact
   types. In particular, exercise `false` versus index0, `15360.0` versus the
   integer sample count, and `0` versus the noise/fixture/source booleans.
2. Re-choose gate/result discrepancies: fixture-only or nonterminal status,
   missing child, wrong child hash, child sample count15359, wrong manifest or
   float authority, source_unchanged=false, different before/after source maps,
   omitted actual source and a rehashed false source binding. A matching
   status string does not replace actual child/source closure.
3. Exercise manifest structure beyond the gate digest: missing/duplicate or
   reordered original indices, wrong sensor phase, swapped dimensions with
   the same sample count, wrong active origin/black/white/gain/noise/rounder,
   different frame transform with unchanged dimensions, and altered source or
   model meaning. Strictness is specific to the registered M194e contract;
   do not mislabel it as the M194b schema or invent general optics validation.
4. Re-choose file paths: parent traversal, absolute/drive/UNC-like paths,
   empty path, directory in place of file, and a normalized alias that escapes
   the intended bundle. An existing valid nested relative path is the passing
   companion. A copied unchanged bundle is a valid companion if the adapter's
   declared relocation contract permits it. Never edit the admitted package.
5. Reject same-length changed CFA bytes, short and appended payloads even with
   freshly computed candidate hashes, and malformed JSON at or beyond its
   declared size bound. Use exact6144-byte CFA and exactly1MiB valid JSON
   companions. Source inspection must also show one bounded open and hashing
   the same bytes decoded. File-size observations alone do not prove bounded
   reads, and these controls will not claim a process-RSS measurement.
6. Recompute the plan from validated inputs. Change the native offset while
   preserving output dimensions; change exposure, observer, source association
   and effective levels while resealing the candidate plan. Reject these at
   the actual comparison boundary with the unchanged computed plan as companion.

## Actual source observer and second read

Use a private copy of the five valid6144-byte CFA inputs through the actual
new `BridgeSource` decoder, independently comparing returned active samples
and geometry. The input root need not grant optical authority for this API
test. Decode in the fixed nonsequential order `[3,0,4,1,2]` to catch a counter
indexed by arrival order instead of frame identity. Off/count/placebo must
return identical sample bytes. Successful counts are all zero for off/placebo
and all one for count; hook calls are respectively0/5/5. A second complete
pass produces all two successes and10 hooks only for count.

For the live failure, let original index3 complete its first successful fold
decode, then alter its private file before its next bounded read. The exact
old digest must fail on that second read. A separate fail-on-attempt=2 hook is
acceptable for testing confidence traversal and must be disclosed as such;
it cannot replace the real changed-file bounded-read check. Assert that the
fault index has exactly one successful decode and that failed attempts never
increment the success ledger. Hook/attempt counts and planning file reads
are different quantities, per the prospective protocol.

The actual confidence pass must exercise the same source instance's second
decode and return an error. A healthy companion must see all five frames
twice and produce the registered output; its TIFF identity and values belong
to the root/Zeno eleven-file comparison. Private failure artifacts remain
separate, and no completed receipt may survive a refusal.

## Evidence and limits

Implement only the allocated independent Rust child and a small command/result
record if needed. All malformed cases must return controlled errors rather
than panic; an unexpected accepted case is a retained failure, not a reason
to remove that case. Preserve first compilation or harness failures separately
from product defects. Run only after an explicit CLI compilation with the
complete including-source set bound; execute tests serially in a clean,
recorded process environment. Do not mutate process environment concurrently
inside the Rust test harness.

These checks establish bounded parsing, consumed bytes, recorded authority and
source reread behavior for this small adapter. They do not independently
re-establish M194e's optical math, prove OS race freedom, measure process peak
memory, or commission boundary quality, camera calibration or a noisy merge.
Additional inexpensive checks may be added only for a concrete API boundary
revealed by the implementation; record that timing rather than calling it
prospective design.
