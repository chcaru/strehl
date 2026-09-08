# Independent native derivative 1 refusal read

2026-09-07 local date. **VERIFIED by actual retained records and source/metadata
byte inspection:** native1 correctly remains REFUSED. Its first primary test
completed, but the independent first-frame reader refused unequal active
dimensions. No frame obtained complete independent agreement and no coverage
run occurred. This review did not reopen originals or the retained RAW
snapshot, read TIFF payloads, import subject/numerical code, decode an image,
rerender or alter a bound source. TIFF and snapshot sizes were inspected as
filesystem metadata only; their hashes below are the mutually associated
producer/request records, not a new payload rehash by this reviewer.

## Actual first refusal and preserved evidence

Execution used committed `5c64d6f111fd8d04573c93ac0cf5ccc6c38b7a0b` and the
44,038-byte release
`37f4f8ceb590dbff386f9a7a773d2f99381e8be481145f2dc9e0ec6896928dc2`.
Paths in this table are relative to `experiments/m193c-output-grid`.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| native-derivative-1/result.json | 93975 | 4299877897694e655ef04f88001e6406058c1b2d0efddded6d525510fbc9dfe0 |
| native-derivative-1/input-plan.json | 17484 | ed77972c956e9267dfb88907778ac8ff2f83887085457b83d7dccdc299db546f |
| native-derivative-1/frame-00/native/result.json | 350873 | e02482a38f3f15a2cc89ee83a809fdbdc590568db8a439754e956f20f8251427 |
| native-derivative-1/frame-00/read-request.json | 2368 | b0eddc04c19285980b4bb329297955a7a8aff0e671537e7af05c3b421ed3a261 |
| native-derivative-1/frame-00/independent/result.json | 32013 | 754485f20e99c0511465da98c228554229c0ff8a6c6a187e8ae9f38443a2a2f4 |
| native-derivative-1/frame-00/frame-result.json | 10752 | 5274f9d1e6963762e8d93c23a1ea7f8c2e5a2c7c29e8601e37702eb8bc60b5a6 |
| work/native-derivative-1-console.txt | 1537 | ca5f9f117157410846d788d424aa878524296851a5f2100b0b097d89c645c990 |
| work/native-derivative-1-outer.json | 2314 | 45e398ad4bf9fe51d0095e6b7be8f4132e53828866a51193cabcf644f5e8ec13 |
| work/native-derivative-1-exit.txt | 3 | f1b2f662800122bed0ff255693df89c4487fbdcf453d3524a42d4ec20c3d9c04 |

Root's retained outer observation reports OS exit 1 after 27.5765552 seconds,
with `admissible_parent_exit=false`, matching the actual parent argv and release
hash. The exit file is exactly `1` followed by CRLF. This is inspection of root's
original observation, not a second wait on that process. Parent final stdout
also says REFUSED, preserving the same error and empty finalization-error list.

There is exactly one attempted row, ordinal0/original0, DSC00016.ARW. The parent
stopped at `independent-child`, with `snapshot_deleted=false` and
`independent_read=null`. Its `first_refusal` and row traceback name the failed
zero-exit condition. The underlying reason is retained separately in the actual
independent result and 1,194-byte independent log: `ValueError: independent
active dimensions`, raised at reader line899 after its owned-copy check.
The parent wrapper's generic nonzero-exit message must not replace that specific
cause in the milestone account. No later failure obscured it.

The 211-byte primary log has the exact named native test and one actual libtest
summary: 1 passed, 0 failed, 0 ignored, 0 measured, 161 filtered out. The primary
receipt is `COMPLETE_REGISTRATION_DERIVATIVE_UNVERIFIED`, error null,
finalization errors empty, `decode_calls=1` and no live frame leases after
prepare. Its reported native duration is 17.1905188 seconds; the enclosing test
and Job times have broader scopes and must not be treated as conflicting
measurements.

## The measured disagreement and its limits

| Reported domain | Primary owned decoder | Independent rawpy/LibRaw record |
| --- | --- | --- |
| Decoded buffer | stride7168, height5120 | raw width7168, height5120 |
| Active/visible origin | x0, y0 | left margin0, top margin0 |
| Active/visible dimensions | 7032 × 4688 | 7028 × 4688 |

The primary records 32,966,016 active samples and 4,688 row hashes. The reader
records a contiguous owned visible copy, compared after the decoder context,
and zero postprocess calls. Its first and only completed check is
`owned-visible-copy`. The held source checks the owned copy against rawpy's own
sizes before persisting that evidence; it then compares the dimensions with the
primary active rectangle and refuses.

Consequently the full active-u16 comparison, row comparison, level/WB agreement
and TIFF pixel checks were not reached. Both independent pixel-hash fields are
null. Recorded metadata such as local colour labels or white levels is not an
asserted pass merely because it is present in the first check's evidence. This
refusal cannot establish that the four-column difference is harmless, synthetic
padding, an offset, a bad RAW decode or a defect in one particular decoder. No
correspondence or agreement over the common-width intersection was measured.

The primary TIFF reference is 197,798,267 bytes,
`97af13814d35ca2bf5320587268c722903ef5204ae3d9b379eef2bb384753d5f`.
Primary output, parent row, request and refused independent result all name the
same resolved file and SHA/extent. The retained snapshot reference is
39,030,784 bytes,
`35ccc60a2cadbcdc999fb6765a326f5baaa298776fb951d12287e05c5892ed36`;
the same identity is associated across plan selection, primary receipt, row,
request and independent result. Both files exist at those extents. Their
presence is evidence of an incomplete attempt, not admitted TIFF pixel identity.

## Coverage, source and launch associations

All nine original observations are present before and after, byte-for-byte
equal as records, in order 0,13,26,39,52,65,78,91,104. The plan entries agree
with their original metadata and hashes, and the recorded device/file-identity
pairs are distinct. This reviewer did not rehash the corpus; these are actual
parent observations. Only original0 reached the primary decoder and independent
reader. The exact remaining list is 13,26,39,52,65,78,91,104, with no later
frame directory. Final authenticity hashing of planned originals is not a
decoder visit or coverage evidence.

All 139 released sources and 58 input refs match the parent's before/after
maps and current bytes. The reader's invocation source map equals the same
release. A scoped git diff of those paths against `5c64d6f1` is empty. The
input plan binds the complete 119-source compiled map and actual build3 copied
executable; the primary's four derivative-source bindings agree with it. The
four retained independent-reader source snapshots match their current bound
source bytes. In total the audit rehashed 216 distinct non-image source,
metadata, executable and dependency files and repeated those hashes at its end.

The released parent vector equals both actual parent invocation and root outer
command. The first reader vector equals the launch observation and its actual
`orig_argv` after substitution of the exact request SHA. Its runtime object
matches the captured runtime; the six recorded module files and interpreter
still match their pins. Primary command/environment, input-plan hash,
original index, snapshot, output directory and Rayon cap match the actual
request/receipt chain. Both launch JSON files equal the rows retained in the
parent result, and their logs match their bound hashes and extents.

The adjacent raw_r.dll and vcomp140.dll FileRefs in root's actual before and
after observations equal the frozen supplement, and `dependency_error` is
null. Their current byte hashes also match. This discharges the required two
endpoint file checks for this attempt; it does not enlarge the six-file runtime
capture or prove loaded-module/hermetic closure.

## Actual resource and terminal accounting

| Owned child | Observed exit | Terminal CPU seconds | Wall seconds | Peak Job committed bytes |
| --- | ---: | ---: | ---: | ---: |
| Primary native test | 0 | 27.65625 | 21.829 | 344461312 |
| Independent reader | 1 | 2.3125 | 2.359 | 333123584 |

Both observations have direct exit and EOF, complete terminal Job accounting,
active processes 0, no helper error and no cleanup errors. Both ordinary drains
observe active 0 immediately; explicit termination was not attempted. Their
terminal CPU equals recorded user plus kernel CPU. The reader's exit1 is a
controlled semantic refusal, not a process-controller failure. Each was within
the actual 240-second child wall limit, remaining CPU limit, 8GiB committed
memory limit and 16MiB combined-log limit. Peak committed memory is not RSS.

Final parent stdout records 34.984375 CPU seconds. This decomposes as carried
capture 1.65625 + primary 27.65625 + reader 2.3125 + new parent 3.359375. Child Job
CPU is added once. The earlier stored-result sample is 34.515625 seconds; it
predates terminal publication and final rechecks. The independent reader's own
final log reports 2.28125 CPU / 2.25 wall, 119,514 artifact bytes and 65,894,528
owned-array peak bytes, with 444,020,678 bounded bytes read. Those are local
reader scopes, not additional CPU to add to the parent total.

Final parent wall is 29.2583753 seconds including capture carry 1.7583753, so its
new native invocation sample is 27.5 seconds. Root's complete outer native
observation is 27.5765552. For subsequent carry, preserve the larger complete
outer scope: 27.5765552 + prior 1.7583753 = **29.3349305 seconds**. Do not add
outer wall to the already carried parent total, which would count the native
invocation twice. These are operational accounting values, not timing claims.

Recursive metadata enumeration, including hidden entries, finds 17 files with
237,455,575 bytes in the native output tree: one retained RAW snapshot, one TIFF
and 15 metadata/source/log files. Metadata totals 626,524 bytes. Adding the
carried one-MiB reservations yields the actual final stdout totals 238,504,151
file bytes and 1,675,100 metadata bytes exactly. The stored-result observation
is earlier by 93,975 bytes, the size of the final result. No deleted snapshot is
silently omitted. The outer record and later investigation/review evidence are
outside this native tree and need explicit accounting when preparing later
stage carry; this enumeration is not total write I/O. The original real-stage
1200 CPU / 1800 wall / 4 GiB files / 128 MiB metadata ceilings remain unchanged.

An initial read-only display helper incorrectly assumed the parent's invocation
was a dict, though its actual schema is a list, and stopped with AttributeError.
That helper did not alter evidence or call subjects. The corrected display and
the complete independent association/accounting pass completed; no failing
scientific assertion was repaired or rerun.

Disposition: preserve native1 as a real first-frame active-domain refusal with
one unverified primary TIFF and eight unvisited originals. The next bounded
investigation should use the already retained first-frame snapshot to establish
the actual active-domain relationship before any repair is registered. Neither
relax the shape condition nor crop to the smaller width merely to obtain a
pass. Registration, nine-frame coverage, product quality and calibration remain
unmeasured by this attempt.
