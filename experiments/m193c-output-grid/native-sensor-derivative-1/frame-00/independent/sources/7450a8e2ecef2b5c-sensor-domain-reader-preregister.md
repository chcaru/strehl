# M193c explicit sensor-domain reader and original0 reuse

Prospective source-only revision. No new module/helper/control has been imported
or executed, no RAW/TIFF reread or producer run has occurred. Root must freeze
the source/input/command release after independent review. The original reader,
native parent, runtime capture, private commission, Rust implementation, build
and native1 failure remain immutable.

## Why this is a new reader method

Native1 refused original0 before admitting any derivative: the primary declared
7032x4688 at (0,0), while the independent reader selected rawpy's 7028x4688
visible view. Both reported a 7168x5120 decoded buffer. The separately released
active-domain probe's worker record is
`active-domain-probe-1/worker.json`, SHA
`1031e0bee6bec02473981911634857a700cc59f414d575cd18c7ff9a9b9cb03c`.
It reports exact full-domain and all 4688 row-hash agreement on the primary's
explicit rectangle; the four disputed columns contain nonzero data. Its declared
scope is decoder byte agreement, not physical photosite validity. Independent
reading of that diagnostic is a separate root prerequisite. Nothing makes
native1 a passing run or erases its visible-domain disagreement.

The new reader compares the *same samples the primary actually consumed*.
`independent-sensor-derivative-read.py` is a full explicit copy of held
`independent-derivative-read.py` SHA
`8c571654667f8ef66520aedfd1bddceb991c8a86d1a7355a4ed21cf2ba85eced`,
with a narrow native-only method/interface addition. `native-sensor-derivative-run.py`
is a full explicit copy of held `native-derivative-run.py` SHA
`94fe31fbd80854fac80114e0b16b150d9d70ed8899ced727dd8c052b74d0244a`,
with the corresponding native interface and one original0 reuse branch. There
is no monkeypatch, alternate RAW decode, alternate merge or Rust change.

The old private visible-copy helper, source32/private41 control implementation,
private output checks, TIFF parser and runtime capture implementation remain
unchanged. The new native helper is commissioned by the eight controls below;
the old private PASS is not renamed as evidence for that helper. No rebuild or
private 12-TIFF campaign is requested solely for this Python native-method change.

## Actual consuming domain and ownership

After validating the primary receipt and its exact original plan, the reader
passes `primary.source.active = {x,y,width,height}` to `owned_sensor`.
All four values must be actual bounded integers, with even origin/extents,
positive width/height and at most 36 million ROI samples. The independent
`rawpy.raw_image` must be a two-dimensional uint16 decoded array, with shape
equal to actual `raw.sizes.raw_height/raw_width` and at most 40 million samples.
The exact primary rectangle must fit that array. These are honest postdecode
checks; the enclosing committed-memory limit is the preallocation resource
barrier. No claim is made that the input dimensions were known before decode.

Inside the `with rawpy.imread(io.BytesIO(actual_pinned_snapshot_bytes))` context,
the reader takes `full[y:y+height,x:x+width].copy(order='C')`. It requires the
returned array to own its memory, be contiguous, have the exact selected shape,
and share no memory with the decoder array. Only this ROI is copied, not the
whole padded decoded frame. Existing named-array budget accounting charges it.
Full and per-row little-endian uint16 hashes are computed after context exit
and must equal the primary's hashes exactly. Every recorded row remains mandatory;
there is no crop, common-prefix comparison, tolerant code comparison or omitted
column. Padding outside the declared rectangle is not pooled into a statistic.

CFA indices are queried inside the live decoder at `(y+dy,x+dx)` for the
primary's actual origin, not at `(top_margin,left_margin)` and not assumed zero.
The local letters must still be exactly RGGB. The unchanged black/white and
green-normalized WB checks use those actual consumed channel indices. They keep
the original exact scalar comparisons and existing WB allowance `2^-20`.
Metadata records full shape, primary rectangle, independent visible rectangle
and shape, actual source-CFA origin, actual visible/full sizes and flip, and
whether the visible rectangle equals the selected rectangle. A disagreement is
retained as a fact. The visible view is checked against its own declared bounds
but is never substituted for the selected ROI. `physical_sensor_validity_claim`
is explicitly false. CameraLinear TIFF checks and all TIFF pixel reads are unchanged.

## Eight literal helper controls before each independent RAW reread

Each of the nine fresh independent reader processes runs the same eight small
in-memory controls on the actual new helper before it opens its snapshot bytes
for decode. The control run shares that reader's existing CPU/wall/array/metadata
budget; there is no fresh control budget, draw, TIFF, Rust invocation or RAW
fixture. The synthetic full buffer is uint16 12x16 with sample
`500 + 31*y + 3*x`. The primary rectangle is `(x=4,y=2,width=8,height=6)`.
Its independent oracle directly packs six rows of eight literal formula values
at x=4..11,y=2..7 using `struct.pack('<H', ...)`, then SHA-256. It does not read
the helper's output to manufacture its expected hashes.

The fake decoder has a context manager whose exit overwrites its full backing
array with 65535 and marks it closed. Its CFA description is `RGBG`, and buffer
index table is `[[0,1],[3,2]]`; `raw_color` refuses after close. The default visible
rectangle is `(7,5,6,4)`, deliberately different in origin, size and CFA parity.
No synthetic image is presented as a physical capture.

Ordered records, each `{id,pass,evidence}`:

1. `sensor-nonzero-origin`: actual helper copies the primary rectangle inside
   context. After poisoning/close, full and all six row hashes must equal the
   separately packed oracle. The unequal visible domain must be observed.
2. `visible-crop-null`: change only visible metadata/view to `(2,4,10,6)`.
   The same actual helper and all hashes must still match the primary oracle.
   This would fail if selecting the visible view affected the consumed samples.
3. `wrong-offset-hash-refusal`: actual helper consumes rectangle x=6 instead of
   x=4, with all other primary dimensions fixed, and is compared to the original
   oracle through actual `compare_active`. It must specifically refuse
   `whole active u16 disagreement`; shape remains equal and all values are valid.
4. `truncated-buffer-refusal`: expose only seven decoded rows, with matching
   full-buffer metadata. The same declared ROI must specifically refuse
   `sensor ROI outside decoded buffer` before copying or hashing a subset.
5. `borrowed-sensor-refusal`: actual helper's test-only `copy=False` path must
   specifically refuse `owned sensor copy inside lifetime`. A different crash
   or silent borrow is not a passing negative.
6. `late-copy-lifetime-destroyer`: deliberately retain a view and copy only
   after fake close. The actual full and all six row hashes must disagree with
   the original oracle. This establishes that the lifetime fixture really
   damages late copies; a no-op context exit cannot pass it.
7. `restored-sensor-copy`: return to the actual inside-context helper. Exact full
   and row hashes must be restored after poisoning.
8. `source-origin-cfa`: actual helper at (4,2) must report RGGB and retain the
   correct hashes. Actual fake `raw_color` at the wrong visible origin (7,5)
   must instead return BGGR. This specifically powers rejection of the odd
   visible-origin CFA shortcut. The admitted ROI and (0,0) both have even CFA
   phase, so their identical CFA letters are arithmetic equivalence, not an
   independent zero-origin CFA test. The nonzero ROI's full/row pixel hashes
   separately reject selecting pixels at the wrong crop offset.

The existing refusal helper catches only exceptions from the called subject,
then checks expectations outside that catch. These controls fix what counts as
power before execution. They do not establish the correctness of rawpy or the
primary; actual independent byte agreement on every real row remains decisive.

## Explicit native interface version

The new release is `m193c-sensor-native-derivative-release-v1`, scope
`sensor-native-nine`. It retains the old closed release fields and adds exactly
`reuse_first`. The reader block still contains script/runtime/nine exact commands.
Request schema is `m193c-sensor-native-derivative-read-request-v1`; its fields are
unchanged: schema,execution_release,input_plan,original,snapshot,primary_receipt,
tiff,build,reader_runtime,limits. The unchanged Rust input plan and producer
receipt schemas remain original v1.

Native independent result schema is
`m193c-sensor-native-derivative-independent-frame-v1`; success is
`PASS_SENSOR_NATIVE_DERIVATIVE_FRAME_ONLY`. The original result fields remain,
with an additive `domain_controls` list of exactly the eight ordered records.
The eleven native checks are exactly:

`owned-sensor-copy`, `active-shape`, `local-rggb`, `active-u16-bytes`,
`active-row-u16-bytes`, `scalar-black-white`, `green-normalized-wb`,
`tiff-native-rgb16`, `tiff-linear-camera-description`, `tiff-full-pixel-read`,
`input-source-stability`.

The first check retains the actual domain witness within its independent decoder
metadata. Parent validates both exact ordered populations, actual true pass
values, request/files/build/runtime/source association, and actual reader exit.
Its result is `m193c-sensor-native-derivative-run-v1`, with success
`COMPLETE_NINE_SENSOR_DERIVATIVES_AWAITING_COVERAGE`. It adds `reuse_controls` and
per-row `primary_reused`, `reuse_provenance`,
`snapshot_retained_from_refused_run`. Invocation/source/work fields otherwise
retain the old structure. The separately held coverage reader deliberately does
not accept these new schemas yet; root will review any later consumer update.

Runtime remains the same captured `m193c-derivative-reader-runtime-v1` dictionary,
six module/library pins and actual executable. The actual reader recomputes and
compares that dictionary and rechecks every runtime FileRef. The separately
bound adjacent rawpy `raw_r.dll` and `vcomp140.dll` endpoint observations remain
required by root's external launch, with actual before/after equality. Reuse also
authenticates the old supplement against the same captured runtime and rehashes
both files. Neither old nor new evidence claims complete loaded-module closure.
Private runtime/capture behavior and frozen binary bytes are not changed.

## One-case original0 reuse, without a general resume engine

Native2 has **one reused primary TIFF plus eight fresh primary TIFFs, nine fresh
independent reads, and 17 newly launched children**. The old primary successful
launch exists inside a refused parent run. The new parent neither rejects that
artifact solely for the outer failure nor turns the outer failure into success.
Original0 reuse is mandatory for this variant; any mismatch refuses rather than
automatically rerendering or choosing another case.

`reuse_first` is exactly seven repository-relative FileRefs:
`result, frame_result, primary_launch, independent_refusal, outer, console, exit`.
They bind actual native1 metadata and are listed in released inputs. Large RAW
and TIFF refs are followed from this pinned metadata; they are not unbounded
objects hidden in a generic resume payload. The historical result path is fixed
to `native-derivative-1/result.json`, its schema/status must remain old-v1/REFUSED,
and it must retain original0 first refusal at `independent-child`, exactly one
row and the other eight unvisited. The old independent result must remain the
old visible-domain `independent active dimensions` refusal. Old finalization
errors or changed historical sources, input observations, products or launch
associations invalidate reuse.

The parent still hashes/measures all nine original corpus inputs before any
new decode, produces a fresh complete nine-entry plan using the unchanged
compiled source map, actual build/executable and settings, and requires that
fresh plan's actual serialized canonical bytes **and complete parsed contents**
equal the old plan. No claim of that equality is made before the future run.
The old before/after original metadata records must equal all nine newly
measured observations, including file identities and hashes.

Three cheap actual plan-boundary controls run before reuse: valid full-plan
comparison, a deliberately changed original13 SHA while original0 remains
unchanged (must specifically refuse full-nine equality), and restored full-plan
comparison. These controls create metadata only and share the parent's existing
budget. They prevent an original0-only identity predicate from passing as a
complete unchanged plan.

For original0 the fresh reader request keeps the **old** plan, snapshot, primary
receipt and TIFF paths, because the original producer command/environment bind
those paths. Its execution release, reader source/runtime authority, request SHA,
new reader output and actual reader launch belong to the new attempt. Existing
`native_summary` checks the old actual one-passed test, exact command/log and
zero-active terminal Job. Existing `primary_result` checks old selected index,
plan/snapshot/TIFF, compiled source witness, complete source receipt, and exact
two-file producer output. The new parent records that launch as historical reuse
and never passes its accounting to the new child-CPU accumulator.

The historical primary CPU, TIFF, snapshot and metadata are already paid in the
root's carried work. The parent checks that carry covers old actual final stdout
work and old root-observed elapsed time. Active-domain diagnostic and other
actual stage work also remain root's explicit carry; the parent does not infer
they cost zero. There is no file-byte or CPU refund. Only the fresh reader and
subsequent eight fresh producers/readers add new child CPU.

The old original0 snapshot/TIFF/plan/receipt/logs are verified before and after
the fresh read, never copied over, deleted or mutated. Row0 says
`primary_reused=true`, `snapshot_deleted=false`,
`snapshot_retained_from_refused_run=true` and binds the historical authorities.
On fresh reader refusal, those files remain unchanged and the remaining eight
new reads/producers remain unvisited. Fresh rows1..8 retain the original owned
snapshot creation/verification/deletion path. The old failed run remains an
immutable observation, with no new files written inside it.

## Resource and execution limits

All original nonreset limits persist: 1200 total CPU seconds, 1800 total wall,
4 GiB new-file charge,128 MiB metadata/logs; per child at most 240 wall seconds,
16 MiB log and8 GiB committed process memory. Reader named arrays remain bounded
at128 MiB, with one actual sensor ROI copy; file-buffer/native allocations are
also subject to the process committed-memory bound, not called measured RSS.
Controls consume the existing reader budget before decoding. Original0 reuse
saves a prospective extra render and snapshot copy, but no numerical timing or
storage saving is claimed until actual work is recorded. Root independently
binds original attempts, probe costs and other prior work before execution.

The release must bind new source/spec plus the full unchanged old private/build,
reader/parser/runtime/parent dependencies and actual prerequisite artifacts.
The source-parent command uses the new parent basename; the nine hashed-request
reader commands use the new reader basename with existing `-B -X faulthandler`
and fresh per-frame `pycache_prefix`, `ACTUAL_FRAME_REQUEST_SHA256` token, exact
workspace paths and clean child environment. No source generation helper is an
execution release. No automatic retry, threshold change, physical-sensor claim,
quality result or coverage authority follows from this source preparation.
