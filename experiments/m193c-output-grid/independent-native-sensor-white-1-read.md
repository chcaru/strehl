# Independent audit of the first camera-white native attempt

Status: VERIFIED saved evidence. **Parent REFUSED; original0 independent
reader PASS.** These are distinct terminal outcomes. Revision `8b0db533`
ran one new reader against the original retained primary/snapshot/TIFF and
then refused at the parent's artifact-type check. No new primary decode,
TIFF, later-frame reader, coverage or registration was performed.

The audit uses saved JSON/log/source records and opaque file hashes. It did
not import a subject/helper, execute its controls, decode RAW, parse TIFF
pixels or render. It rehashed the retained snapshot/TIFF and checked current
filesystem metadata for all nine corpus files, without reopening their RAW
bytes. It does not claim an additional independent pixel reconstruction.

## Actual artifacts and executed audit

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `native-sensor-white-derivative-release-1.json` | 60,531 | `70d44a9c43d9d8c194824b214b1287358a4f254e01ce6e1efc955d1f85af6611` |
| `native-sensor-white-derivative-1/result.json` | 125,088 | `af72a5964fe1434db61a1c40638cf0ab4ac1d14ba2133440c067e00cba7fa76f` |
| `frame-00/independent/result.json` | 438,743 | `6ec2727b5d8e2b6f3c12c50434d7591735bb57af92339a751fb76d4aae11f3aa` |
| `frame-00/read-request.json` | 2,391 | `56b08b23d9e9908845bbc6879b02e92bf240251cadcfe0dc8347fdd1dda27a4a` |
| `frame-00/independent-launch.json` | 4,408 | `2a16fdee8fd7e9099de45677bab6eedeef2a44560ca365e61bbc31225533894f` |
| `frame-00/independent.log` | 514 | `c64ac10b98551eb8a8cbc416008f3455c6cd9d0ae1e30fbce4fbdb9fa70ff642` |
| `work/native-sensor-white-1-console.txt` | 1,383 | `b2e5d1d489dd882cbbcc46a3f93d1c2dbba162bb2d6e431592601569a05aa62e` |
| `work/native-sensor-white-1-exit.txt` | 3 | `f1b2f662800122bed0ff255693df89c4487fbdcf453d3524a42d4ec20c3d9c04` |
| `work/native-sensor-white-1-outer.json` | 2,368 | `c25135fca535b84dd7ebb517a09f79a0a51dc680a091fda793afd39b0dfdd3d7` |

Frame-relative paths above are within `native-sensor-white-derivative-1`.
This command actually completed exit0:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B experiments/m193c-output-grid/work/independent-native-sensor-white-1-audit.py
```

[The saved audit script](work/independent-native-sensor-white-1-audit.py) is
21,892 bytes, SHA
`db09546a781c33e3768d78dbe3fb820311cf32a81fade31df5c2da0356ea0961`.
It reports `PASS_SAVED_SENSOR_WHITE_PARENT_REFUSAL_AUDIT` for279 distinct
hashed files. This label means the recorded outcome and associations passed
the audit; the subject parent is still REFUSED. The audit covers all150
released sources, all118 released metadata inputs, exact parent/child argv,
request/result/primary associations, actual controls, full saved row hashes,
runtime/DLL endpoints, output inventory and terminal work. Git confirms the
released sources remain unchanged from `8b0db533` and its committed release
matches the external digest.

## Exact operational refusal

The reader really returned `PASS_SENSOR_WHITE_NATIVE_DERIVATIVE_FRAME_ONLY`
with `error=null`, no finalization errors, and actual child exit0. Its final
stdout names the same persisted result. The parent passed the child-process
check and reached `independent-result`; then line726 of the frozen
`native-sensor-white-derivative-run.py` required every recursive file under
the independent output directory to have suffix `.json`, `.log` or `.txt`.
Its exact refusal is `ValueError: independent reader metadata-only output`.

The six offending files are all under
`frame-00/independent/sources/`:

| Exact filename | Bytes |
| --- | ---: |
| `6a318b439d1b9c5c-independent-sensor-white-derivative-read.py` | 76,606 |
| `715c53c13002d3f4-sensor-white-reader-preregister.md` | 13,341 |
| `7450a8e2ecef2b5c-sensor-domain-reader-preregister.md` | 15,934 |
| `9acceb498568967b-independent-derivative-tiff.py` | 8,144 |
| `bf8a6c2a13b109fb-independent-derivative-reader-preregister.md` | 10,711 |
| `d01a74aefcfa15b2-independent-rgb-tiff.py` | 7,305 |

Each actual file's complete SHA/extent matches its corresponding released
source. The audit retains every full ref in its output. These are the reader's
explicitly selected execution-source and specification snapshots, written
by its `snapshot_names` path before runtime loading. They are neither
unexpected images nor bytecode. The source directory itself is permitted
by the predicate; all six files individually fail it. The JSON result is
the only other file in the reader directory.

The recursive inventory has eight entries: one source directory and seven
files. Its570,784 retained bytes consist of the438,743-byte result plus
132,041 source-copy bytes. This equals the reader's final artifact receipt
and is below the original4 MiB per-frame metadata cap. The256-entry limit
also passes. Thus the observed refusal is the filename-suffix mismatch;
it is not a metadata-byte overflow, unknown TIFF output, failed white check
or failed process cleanup. The next size assertion and parent
`independent_result` validator are not reached. The parent row consequently
has `independent_read=null`, despite the independently retained reader file.

The mismatch was visible in the source contract before execution: the reader
intentionally copies `.py`/`.md` files, while the inherited parent predicate
rejects them. Earlier failures stopped before this point. Source-delta reviews
did not discharge this complete artifact-publication interface. Recording
that miss is necessary; interpreting a successful reader as successful
parent admission would hide the actual failure. No subject is patched here.

## Actual native and metadata evidence

All eleven native checks are retained in exact order, true, with the new
sixth `scalar-black-camera-white` ID. Whole active u16 hash remains
`e5b8c066623e6f64d4f945ae22dafb4ccb5238fd76fff36f39de8a16cd4739e1`.
The audit compared all4,688 saved independent row hashes with the original
primary receipt; their complete lists agree. Shape is4,688 by7,032 and local
CFA letters areRGGB. This is recorded independent decoder agreement on the
explicit primary sensor region, not physical photosite qualification.

The actual white-authority witness uses all four CFA indices and camera
whites `[15360,15360,15360,15360]`, selecting15,360 exactly equal to the
primary scalar. Generic16,383 remains recorded and
`generic_matches_selected=false`. Fallback is forbidden and physical-
calibration/primary-metadata-presence claims remain false. Recorded black is
512; normalized WB `[2.6337890625,1,1.4736328125]` equals the primary's
recorded gains. The new method did not alter the old primary's normalization.

The actual reader reached and completed its strict TIFF parser. Its receipt
records little endian RGB16, shape `[4688,7032,3]`,196 strips and
197,796,096 consumed pixel bytes. The complete decoded pixel digest is
`3caece4a2dc67b37f2bc84c307fe735a7dcfadc3fc18681b1c8f29ee1c3db545`.
The final source/input check records the snapshot recheck and no reader
opening of the original corpus. These are the executed independent reader's
observations, bound to its source and the actual TIFF; this metadata audit
does not recompute them with a second pixel parser or turn them into a
photometric reconstruction claim.

The eight domain control records equal those retained in the preceding
sensor attempt, including distinct actual wrong-offset, truncation,
borrowed-view and late-copy outcomes and valid/restored companions. The
ten white groups retain23 actual metadata attempts:21 exact expected
refusals and two valid/restored calls. The audit checked every nested input,
source, exact exception string, and `inputs_unchanged` witness using
type-preserving JSON comparison, rather than only group PASS fields.

The positive/restored cases use camera12,000, generic16,383 and exact WB
`[1.5,1,2.5]`. The opposite case makes generic12,000 match the primary while
all camera values are11,000, and actually refuses at selected-camera
agreement. The mixed-channel case actually refuses before scalar selection.
Absent metadata, all8 malformed camera rechoices,5 generic rechoices and3
index rechoices have their promised distinct records. Black and WB faults
retain their actual rejection messages with valid camera authority. These
observations establish the specified metadata-rule failure power within
the control population; they do not establish physical sensor calibration.

## Reuse and complete file associations

The new tree contains14 files, all metadata/log/source artifacts, with no
new RAW or TIFF. It contains only `frame-00`; the other eight frame
directories do not exist. All three full-plan reuse controls passed, and
the full fresh nine-input plan's bytes/content equal the original plan.
Original0 still has historical primary reuse true, snapshot deletion false,
retained-from-refused-run true, and the same seven-ref provenance authority.
The reused primary launch equals the original launch; it is not a newly
executed Rust child or free scientific work.

The retained snapshot SHA is
`35ccc60a2cadbcdc999fb6765a326f5baaa298776fb951d12287e05c5892ed36`
and TIFF SHA is
`97af13814d35ca2bf5320587268c722903ef5204ae3d9b379eef2bb384753d5f`;
both current opaque byte hashes match their old refs. Primary receipt and
old plan associations are unchanged. The new request and reader invocation
bind the current release/runtime/source set and original primary files.
Original indices13,26,39,52,65,78,91,104 remain unvisited by frame processing.

All nine original-before/original-after records agree with each other and
the original attempt's records, including hashes. Current filesystem size,
mtime, file ID/device and attributes match. Source/input before-and-after
maps equal the150-source/118-input release. The reader's actual source map
and captured runtime agree with that release, and its source snapshots have
the correct actual bytes. The pinned Python, six captured module files and
two adjacent DLLs were rehashed. Root dependency-before/dependency-after
records equal the released supplement and have no dependency exception.
This remains a bounded dependency observation, not complete hermeticity.

## Process closure and full carry

There was one fresh reader Job. It has direct exit and pipe EOF observed,
exit0, no process-helper error or cleanup error, terminal active-process
count0, two total processes and no terminated processes. Its drain completed
with matching final accounting; no termination was attempted. User/kernel
ticks sum to37,187,500, or **3.71875 CPU seconds**. Child wall is
3.812000000034459 seconds; peak committed Job memory332,464,128 bytes.
These are within the original remaining limits. Two processes in the Job
do not imply two scientific reads.

The actual root invocation exits1 and records
`admissible_parent_exit=false`, as required for the parent's refusal.
Parent and child finalization-error lists are empty. The last parent stdout
reports **50.46875 CPU seconds**, **45.06568420003168 wall seconds**,
**243,457,739 file bytes** and **6,628,688 metadata bytes**. The complete
new14-file inventory sums to757,353 bytes; both file/metadata increments
equal this amount relative to the released prior work. The earlier result
`work` snapshot is not used in place of the terminal receipt.

Root's observed outer wall is7.1395216 seconds. Conservative next wall carry
is **37.9876842 + 7.1395216 = 45.1272058 seconds**. Historical primary work
stays in the prior carry; only this fresh reader's Job is newly charged.
All current work remains below the unchanged stage limits. These are resource
accounting observations, not a runtime-performance claim.

The completed original0 reader result may be cited within its declared
per-frame scope. The parent remains REFUSED at artifact admission, all eight
later frames remain unvisited, and coverage is not released by this audit.
Every failed attempt and source revision is preserved. Any operational
successor belongs to root's separate prospective source/release decision;
this report changes no parser, metadata rule, artifact cap or historical
status.
