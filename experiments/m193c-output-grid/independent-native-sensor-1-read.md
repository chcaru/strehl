# Independent saved-record audit of sensor-native attempt 1

Status: VERIFIED refusal and evidence associations. The scientific subject
remains **REFUSED**. Frozen revision `b7e0be39` ran one fresh independent
sensor reader for original0, reused its historical primary image, and stopped
before any later frame. No new primary decode or TIFF was produced. No nine-
frame derivative admission, coverage, registration or final render follows
from this attempt.

This audit reads saved records, project source and file hashes. It did not
import either reader, execute its controls, decode another RAW, parse TIFF
pixels, render, or launch registration. The retained old snapshot and TIFF
were rehashed as opaque bytes. The nine corpus files were checked by current
filesystem metadata against the recorded identities; their RAW bytes were
not reopened by this audit. The actual parent did record all-nine byte hashes
before and after its attempt.

## Actual artifacts and invocation

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `native-sensor-derivative-release-1.json` | 54,343 | `fb651f3b4aa5eeb891d6cef77e8719e13bb556ba086bd2dbd2add742d93505b8` |
| `native-sensor-derivative-1/result.json` | 113,744 | `00ae754f28277c69196a55da5fff88c8c807de17f6c48123d73c8b3ee1a6eadb` |
| `frame-00/independent/result.json` | 408,686 | `58f4a7208a12a5a17913f1c048a54d106faa9a40e0ee3c849c83cbc71c962db7` |
| `frame-00/read-request.json` | 2,382 | `bba08b3b530cf19e1b176dc047b3bbb9d4baa142a764b58cb904d45460ed5ea9` |
| `frame-00/independent-launch.json` | 4,359 | `fc27f9afaaf1838df00ab4774f60135e8b0791a547736524d56e306fcec6db7d` |
| `frame-00/independent.log` | 1,492 | `4452b6cbd53ef76a99c817a71ae8c39b6e99d1d9c76fa6a2fd98cce39bf7bdcc` |
| `work/native-sensor-1-console.txt` | 1,578 | `d256eb2a353639ca02e62bde2959d994764c8710c1c316469dea06b5f8c5f007` |
| `work/native-sensor-1-exit.txt` | 3 | `f1b2f662800122bed0ff255693df89c4487fbdcf453d3524a42d4ec20c3d9c04` |
| `work/native-sensor-1-outer.json` | 2,344 | `d5b1950c49691cdfcea2e2fd5fbc70440c81a8474db06ebc0463ab6470d83c2e` |

Frame-relative names above are under `native-sensor-derivative-1`.
The retained audit command actually ran, exit0:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B experiments/m193c-output-grid/work/independent-native-sensor-1-audit.py
```

[That standard-library audit](work/independent-native-sensor-1-audit.py) is
15,346 bytes, SHA
`9c96b022c05b247e13d591bfc835099336e4b1f40fa7edcc637858ca5aa55eae`.
Its terminal `PASS_SAVED_SENSOR_REFUSAL_AUDIT` describes the audit, not a
successful subject. It checked 253 distinct hashed files, all 146 released
sources, all 93 released metadata inputs, the retained primary/snapshot/TIFF,
runtime dependencies, actual output artifacts and root terminal records.
Git records confirm all 146 source paths were committed at `b7e0be39`, remain
unchanged, and the committed release has the actual supplied digest.

The parent command equals the released original argv after its single release
digest substitution. The only new child command equals reader command0 after
substituting the actual request digest. Its original argv, pinned Python,
fresh frame-00 reader cache, request path and independent output path agree
with the saved invocation. No frame-01 through frame-08 output directory
exists. The new output tree has 13 metadata/log/source-copy files and no
RAW/TIFF. The old Rust primary launch is unchanged historical evidence, not
a second newly observed process invocation.

## What actually passed, and where it stopped

The reader retains exactly five ordered true native checks:

1. `owned-sensor-copy`: owned contiguous copy, compared after closing the
   decoder context, zero postprocess calls, explicit primary sensor ROI.
2. `active-shape`: 4,688 rows by 7,032 columns.
3. `local-rggb`: indices `[0,1,3,2]`, letters `R,G,G,B`.
4. `active-u16-bytes`: all 32,966,016 samples share the primary's complete
   active hash.
5. `active-row-u16-bytes`: the complete saved list of 4,688 row hashes equals
   the original primary's list, with no omitted row or malformed digest.

The common whole-region hash is
`e5b8c066623e6f64d4f945ae22dafb4ccb5238fd76fff36f39de8a16cd4739e1`.
This audit compared every saved row hash to the separately bound primary
receipt, rather than relying on the reader's PASS label. It does not claim a
third independent decode. The rawpy visible domain remains 7,028 by 4,688,
while the selected primary sensor domain is 7,032 by 4,688 at origin0 inside
the 7,168 by 5,120 buffer. `visible_domain_agrees=false` and
`physical_sensor_validity_claim=false` remain in the actual witness.

Next, unchanged `validate_independent_metadata` at source line636 requires
rawpy's global `white` to equal the primary scalar white. The saved values
are global **16,383**, channel whites **[15,360,15,360,15,360,15,360]**, and
primary scalar white **15,360**. That global equality refuses with the exact
traceback ending `ValueError: scalar white disagrees`. It occurs before the
subsequent channel-white checks and before returning the joint metadata/WB
agreement object.

Consequently `scalar-black-white`, `green-normalized-wb`, the three TIFF
checks and `input-source-stability` are not completed native check records.
`tiff_pixel_sha256_u16_le` is null. Rawpy recorded black `[512]*4` and WB
`[2697,1024,1509,1024]`, but their presence does not confer a completed
metadata/WB admission. The new reader's pixel parser was not reached. This
audit's opaque TIFF hash check is likewise not a new TIFF pixel admission.

The reader exits1. The parent correctly preserves its own refusal at
`independent-child` when the observed child exit is nonzero. Its row's
`independent_read` is null because it refuses before binding a successful
reader result. The separate result file, actual child log and launch bind
the underlying white-level failure. Both parent and reader retain empty
finalization-error lists. The parent result is not silently converted into
a successful partial run.

## Controls have retained failure evidence

All three parent reuse controls are present in exact order. The changed
later-plan-entry case preserves original0 but refuses with the specific
`full nine-plan byte/content equality` exception; its valid and restored
companions pass. The audit reopens both complete plans: parsed contents and
actual byte digest/extent agree. This checks the whole planned population,
not only the one reused frame's entry.

All eight domain controls precede the real independent decode and are
retained, true, with their actual evidence. The nonzero sensor origin `(4,2)`
selects an 8-by-6 ROI in the 16-by-12 fixture. The positive copy, changed-
visible-crop null and restored copy have identical whole and all six row
hashes after the backing buffer is poisoned. The null's visible geometry
actually differs. Wrong-offset, truncated-buffer and borrowed-view cases
retain their distinct expected ValueError messages. The late-copy destroyer
records a different whole hash and all six rows changed after poisoning;
it is not just a configured fault name. The CFA control records RGGB at
the selected even origin and BGGR at the wrong visible origin `(7,5)`.
It cannot distinguish `(0,0)` from other even origins by parity alone, as
the corrected preregistration states.

The audit checked these complete records and read their actual consumed
helper paths. It did not rerun those controls or infer physical sensor
validity from the fixture. Their scope is domain selection, ownership,
lifetime and correspondence. They do not test the inherited choice between
global and per-channel white metadata.

## Reuse, source and resource closure

The old native result remains `REFUSED`, SHA
`4299877897694e655ef04f88001e6406058c1b2d0efddded6d525510fbc9dfe0`.
Original0's primary receipt, primary launch, TIFF and retained snapshot equal
that historical row exactly. `primary_reused=true`, snapshot deletion false,
retained-from-refusal true, and the provenance's historical CPU scope all
agree. Its fresh request deliberately uses the original plan ref. Its new
reader release/source/runtime associations belong to this new attempt.

The retained snapshot is 39,030,784 bytes, SHA
`35ccc60a2cadbcdc999fb6765a326f5baaa298776fb951d12287e05c5892ed36`;
the TIFF is 197,798,267 bytes, SHA
`97af13814d35ca2bf5320587268c722903ef5204ae3d9b379eef2bb384753d5f`.
Both current byte hashes match their historical refs. All nine recorded
original-before/original-after records equal one another and the old
attempt's records. Current size, mtime, device, file ID and attributes agree.
Original indices13,26,39,52,65,78,91,104 remain unvisited by frame processing.

The parent source/input before-and-after maps equal the actual release;
the reader invocation source map does too. Its five retained execution
source copies match the corresponding committed source bytes. Its runtime
record equals the captured runtime. This audit rehashed the pinned Python,
six captured module files and two separately supplemented adjacent DLLs;
the root before/after dependency records equal that supplement. This is the
declared dependency observation boundary, not full interpreter hermeticity
or proof of every loaded system library.

The one fresh reader Job reports exit1, direct exit and pipe EOF observed,
no process-helper error or cleanup errors, terminal active-process count0,
two total processes and zero terminated processes. Its completed drain
retains terminal accounting; no termination was attempted. User plus kernel
ticks total24,843,750, or **2.484375 CPU seconds**. Observed child wall is
2.5320000000065193 seconds; peak committed Job memory332,058,624 bytes.
All are within its original remaining limits. Two Job processes do not
mean two scientific reader invocations.

The final parent stdout, rather than its earlier serialized work snapshot,
reports **43.46875 CPU seconds**, **37.92508029995952 wall seconds**,
**241,651,810 file bytes** and **4,822,759 metadata bytes**. Relative to the
released prior work, the output-file and metadata increments equal the
complete 13-file actual new output inventory, 694,771 bytes. The published
result's earlier `work` is explicitly a prepublication observation and must
not replace that final carry. The new child CPU is charged once; historical
primary work remains in the prior carry.

Root's actual direct invocation exits1, with
`admissible_parent_exit=false`, matching dependencies and no dependency
exception. Its measured outer elapsed is5.8436039 seconds. Conservative next
wall carry is **32.1440803 + 5.8436039 = 37.9876842 seconds**. These are
observed resource-accounting records, not timing-performance claims. All
work stays below the unchanged total stage ceilings.

## Missed metadata issue and disposition

The earlier native1 reader already retained global16,383 and four
channel-white15,360 values alongside the same primary15,360 scalar. This
audit reopened that earlier result and confirmed the equality of those
recorded fields. AST comparison also confirms
`validate_independent_metadata` is identical between the old reader and
the sensor-reader copy. The earlier failure at dimensions merely prevented
that later predicate from being reached.

Thus the white mismatch was visible in saved metadata before this release.
The narrowly scoped sensor-domain review established its source delta and
ownership controls but did not discharge this inherited metadata choice.
The old validator was authored in this implementation lane; this report
does not present its choice as independently validated photometric truth.
The current actual refusal exposes that missed boundary. A future explicit
metadata rule and powered controls need their own source/design review;
neither dropping this failed check nor relabeling this run as PASS is an
admissible interpretation of these records.

No held source, threshold, product default, historical refusal or actual
attempt artifact was edited during this audit.
