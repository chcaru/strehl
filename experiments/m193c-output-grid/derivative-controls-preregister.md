# M193c derivative adapter — literal source-preparation contract

2026-09-07. **PROSPECTIVE / UNEXECUTED.** Resolves the conditions in
`independent-derivative-design-review.md` against Curie's held design
`f503af4c7805f8e4b2f4771b2baaf31599ed9f0ca583d2958a1a6da11a408d68`.
Root approved source preparation only. No include, build, RAW/image read,
decode, helper evaluation, TIFF write or registration execution is released.

The future nested module is `merge_cmd::production_truth::m193c_registration_derivative`,
including only the new `registration-derivative.rs`. Proposed listed tests are
`m193c_derivative_private` and `m193c_derivative_native`, both ignored, both
requiring an explicit fresh parent command. They reuse owned `strehl_raw::decode`,
`Frame::active_row`, `Frame::wb_gains`, MHC and
`image_out::write_demosaiced(Develop::measurement(false))`.

## Exact two TIFFs and in-memory controls

Private geometry is stride40, buffer height32, active(2,4,30,22), RGGB,
black64, white4160, raw WB[2,1,4,NaN]. Padding65000. Generate only these TIFFs:

1. `affine.tiff`: active-local CFA integers R=`320+4x+8y`,
   G1/G2=`1088+16x-8y`, B=`448-2x+2y`. These encode the three rational
   post-WB affine fields in the held design exactly.
2. `signed-border.tiff`: active baseline raw192; set raw48 atR(10,8), and
   corner raw codes2368 at(0,0),576 at(29,0),1088 at(0,21),1472 at(29,21).
   The two large chroma corners exceed1 after WB. No preclipping or impulse
   replacement after observing output is permitted.

All normalization uses the actual f32 sequence `(sample-black)*inverse_range*gain`,
where inverse_range is computed once as `1.0f32/(white-black)`. Signed and
above-one values survive into MHC. Final output is the existing clipped,
half-up RGB16 writer. Metadata bits and the full active/pixel hashes identify
what was consumed; no colour matrix or viewing transform is introduced.

The following32 control IDs are the complete **source-private** population.
Each invalid-frame arm calls the actual `validate_frame` helper and requires
the named rejection reason, with valid/restored affine companions. No invalid
large geometry allocates its declared buffer: mutate the small fixture header.

| ID | Literal intervention / required result |
|---|---|
|valid-affine|Baseline geometry/levels/gains admitted.|
|empty-active|width0 -> `active extent`.|
|odd-origin-x|active.x3 -> `active parity`.|
|odd-origin-y|active.y5 -> `active parity`.|
|odd-width|width29 -> `active parity`.|
|odd-height|height21 -> `active parity`.|
|stride-storage|stride41 -> `storage length`.|
|active-outside|active.x12, width30 -> `active containment`.|
|stride-overflow|stride usize::MAX, buffer_height2 -> `storage overflow`.|
|axis-bound|active.width8194 -> `axis bound`.|
|pixel-bound|active.width8000, height5000 -> `pixel bound`.|
|buffer-bound|stride10000, buffer_height4001 -> `buffer bound`.|
|black-nan|black quiet NaN -> `levels`.|
|black-negative|black−1 -> `levels`.|
|white-infinity|white+infinity -> `levels`.|
|white-container|white65536 -> `levels`.|
|zero-range|white64 -> `levels`.|
|negative-range|white63 -> `levels`.|
|red-gain-zero|raw WB R0 -> `WB coefficients`.|
|green-gain-zero|raw WB G0 -> `WB coefficients`.|
|blue-gain-nan|raw WB B NaN -> `WB coefficients`.|
|gain-ratio-overflow|raw WB R=f32::MAX, G=f32::MIN_POSITIVE -> `WB gains`.|
|fourth-wb-null|fourth coefficient NaN bits0x7fc00001 ->0xffc00002; normalized mosaic bits identical.|
|padding-null|all inactive sites65000 ->17; active hashes and normalized mosaic bits identical.|
|red-gain-live|raw WB R2 ->3; actual normalized red(10,8) changes; G1(11,8) unchanged.|
|black-clamp-live|In-memory early-clamp mutant changes actual MHC R atG1(11,8) by1/256 normalized; correct and restored rows identical.|
|wb-order-live|Actual MHC on pre-WB mosaic vs unbalanced mosaic with output gains; green atR(10,8) changes after final clamp by>1/512; correct/restored rows identical.|
|nine-plan-before-decode|Replace last original104 entry by91; actual prepare function refuses `nine input plan` before fake decode count increases.|
|decode-once-drop-before-write|Actual prepare function with fake owned-frame source calls decode once; returns owned mosaic/metadata after frame lease drops; the actual shared pre-write guard calls a no-TIFF callback at zero live leases, refuses an injected count1 before reaching its callback, and passes restored count0.|
|snapshot-changed|Bound private byte fixture changes from `m193c-before\n` to `m193c-after!\n`; actual same-byte hash guard refuses; original/restored pass. Not a RAW decode claim.|
|late-publication-revokes|Actual publication helper writes the known pretty-JSON provisional bytes, which the callback reads before raising `private late-finalization source fault`; require that exact returned error, persisted error and sole finalization error, final REFUSED status, and byte-identical retained first receipt. Record the actual before/retained hashes and retained FileRef. No extra TIFF.|
|restored-affine|Re-run valid affine helpers; all geometry/gain/mosaic bits and active hashes match first valid companion.|

There are exactly two product writer calls in this private invocation. MHC
row calls for stage controls, fake-source normalization, TIFF byte/header
mutations and restored metadata checks are not extra TIFF writes. My ten held
geometry renders plus these two exhaust the charter's12 slots. An additional
product writer invocation requires a prospective amendment; failed attempts
remain counted/preserved under the same budget.

An independent reader, still to be separately frozen, reads both actual TIFFs.
The affine oracle checks all54 Cartesian sites from
`x={2,5,8,11,14,17,20,23,26}`, `y={2,5,8,11,14,17}` and all3 channels using
the held rational fields, max1 u16 code. The signed-border oracle independently
assembles the complete parity/mirror MHC stencils and checks all660 RGB pixels,
max1 code. It must see signed input/upper excursions and the neighbour power
above, not merely an equal clipped centre. Rehashed wrong stride/origin/parity,
coordinate translation, sample type/shape/tag/strip/reference defects must fail
the actual reader entry; valid/restored files pass. Exact independent reader
control IDs/source/commands need a later freeze before this private execution.

## Native nine-plan and ownership contract

The native child accepts an externally hashed input plan with exactly these
ordered original/name/byte triples, under the charter's absolute corpus root:

```
0   DSC00016.ARW 39030784
13  DSC00029.ARW 39878656
26  DSC00042.ARW 40873984
39  DSC00055.ARW 40669184
52  DSC00068.ARW 39497728
65  DSC00081.ARW 39235584
78  DSC00094.ARW 39096320
91  DSC00107.ARW 39018496
104 DSC00120.ARW 38969344
```

The parent plans/hashes all nine source bytes before the first decoder call,
then gives one selected, counted workspace snapshot to each child. The child
validates the complete literal plan before calling its source, verifies the
snapshot against the selected original's byte hash and size before/after
decode, and returns only one derivative. Snapshot must have the matching ARW
basename, be outside the corpus under the fresh workspace attempt, and remain
until both primary/independent decoders consume it. No XMP/adjacent files are
copied. The parent rechecks all original source bytes before/after the whole
stage and releases only an all-nine derivative package, with unmodified order.

The owned decoder may already have resolved absent levels to0/65535. The
adapter validates **resolved values**, not metadata presence. Record primary
f32 black/white/gains and bits, raw RGB coefficient bits, geometry, active row
hashes, active payload hash and selected-source identity. The independent
rawpy/LibRaw reader must copy visible u16 data inside its context and compare
the complete payload exactly; map public CFA/colour labels explicitly. Require
all independent per-CFA black levels to agree with the resolved scalar and the
specified usable white to agree; WB normalized RGB allowance remains
`2^-20*max(1,abs(primary_gain))`. No fitted metadata or offset reconciliation.

`validate_frame` checks each axis<=8192, active pixels<=36,000,000,
allocated samples<=40,000,000, checked products/endpoints, nonempty even
active region and exact owned buffer length before allocating a mosaic.
`prepare_from_source` owns a frame lease, extracts/hash-checks active rows,
builds one f32 mosaic, retains scalar metadata, and drops the frame before
returning to the writer callback. This does not intercept the dependency's
internal decode allocations. A parent Windows Job Object must impose the
charter's8GiB committed-memory ceiling from launch; observed working set and
postdecode extents remain separate facts. No claimed predecode shape proof.
The lease counter observes the explicit owned Frame block. It is not an
independent measurement of allocator liveness or process RSS. The writer guard
is factored once and used by both real writing and the private no-TIFF callback.

## Closed child schemas and exact environment

All file references below are `{path,sha256,bytes}` with absolute paths. Parent
must authenticate build/input source closures independently; arbitrary
self-hashed files cannot substitute for a compiler-artifact record.

Input plan `m193c-registration-input-plan-v1`, status`PLAN_ONLY` has exactly
`schema,status,entries,build,source_bindings,settings`. Each entry has exactly
`original_index,name,path,bytes,sha256,mtime_utc,attributes`; entries follow the
nine triples above. `attributes` is an unsigned32-bit Windows file-attribute
mask; `mtime_utc` is the parent's recorded UTC metadata string. `build` is the actual copied executable FileRef supplied
by a separately pinned compiled-build result. `source_bindings` maps repository
relative names to sha256 strings; it must contain the compiled derivative,
this preregistration, the held derivative design and independent review pins.
Parent verifies the full reachable source closure and actual build association.
Settings are exactly`{purpose:"registration-development-only",colour:"linear-camera-native",
transfer:"identity",matrix:null,orientation_applied:false,spatial_transform:"identity"}`.

Per-frame result `m193c-registration-derivative-v1` has exactly
`schema,status,input_plan,selected,snapshot,source,output,command,environment,
elapsed_seconds,error,finalization_errors`. `input_plan` and snapshot/output
are FileRefs; selected is original index. Unresolved references/selection may
be null on refusal. `source` holds actual normalized metadata and active/per-row
hashes, including compiled-source pins and the inherited-level-default
disclosure. Its exact successful keys are `stride,buffer_height,allocated_samples,
allocated_bytes,active,active_samples,active_sha256_u16_le,active_row_sha256_u16_le,
black,white,black_f32_bits,white_f32_bits,inverse_range_f32_bits,wb_rgb,wb_rgb_f32_bits,
raw_wb_f32_bits,normalized_min,normalized_max,mosaic_bytes,cfa_validation,
level_selection,operation,compiled_sources,decode_calls,live_frame_leases_after_prepare`.
`active` is `{x,y,width,height}`; bit/count fields are integers, hashes are
lowercase SHA-256, and gain/value arrays contain finite JSON numbers. Canonical
decoded TIFF pixel hashes belong to the separate independent read; the Rust
prototype records actual TIFF file hashes and does not claim to inspect its
own output pixels. Status is
`COMPLETE_REGISTRATION_DERIVATIVE_UNVERIFIED` or`REFUSED`; success does not
grant independent decode agreement, TIFF correctness or registration coverage.
`elapsed_seconds` is the observation before terminal publication; the parent's
authoritative elapsed budget includes publication and its final rechecks.

Private result `m193c-derivative-private-v1` has exactly
`schema,status,checks,outputs,command,environment,elapsed_seconds,error,finalization_errors`.
Each check is`{id,pass,evidence}` in the32-ID order above. Outputs is exactly
`{affine:FileRef,signed_border:FileRef}` after successful writes; on refusal it
retains only actual completed refs. Success status is
`COMPLETE_PRIVATE_DERIVATIVE_PRODUCTS_UNVERIFIED`; the independent TIFF reader
and parent exit/source checks must still pass before native decode release.

Environment prefix is`STREHL_M193C_DERIVATIVE_`. Both tests require
`OUTPUT_DIR` as a new absolute workspace attempt directory with existing
parent, and`RAYON_NUM_THREADS=2`. The native test additionally requires
`INPUT_PLAN`, `INPUT_PLAN_SHA256`, `ORIGINAL_INDEX`, `SNAPSHOT`. No other
STREHL environment variable is accepted. Parent must clear ambient overrides
before startup, record the exact environment and bind the actual executable.
No numeric stimulus/settings overrides exist. The plan is hashed and parsed
from the same bounded JSON buffer. The RAW snapshot instead has a before/after
file binding: `verify_file` hashes its own opened stream, the owned
`strehl_raw::decode(path)` opens the path separately, and the adapter rehashes
it afterward. This is not a decode of the hashed buffer and cannot by itself
exclude a transient replacement between opens. Parent-created stable snapshots
and before/after authentication are the declared seam; no atomic lock/handle
guarantee is claimed. All output paths are fresh descendants of the new
attempt. The publication helper preserves its
first receipt on final-recheck failure, writes a REFUSED replacement, keeps
the original and secondary errors, and returns nonzero. Parent independently
rechecks sources/outputs/executable after child exit and cannot admit a
nonzero child or a provisional receipt.

Later exact commands, only after a source/command release and actual listing:

```
<copied exe> --exact merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_private --ignored --test-threads=1 --nocapture
<copied exe> --exact merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_native --ignored --test-threads=1 --nocapture
```

Native command runs once per original in the fixed order. Same source/executable
and distinct directories, no different decoder or fallback profile. Both
source/runtime snapshots and terminal persistence count within the existing
nonresetting budgets: private600CPU/1200wall shared with grid controls; real
1200CPU/1800wall for the entire rehearsal,4GiB new files/128MiB metadata/logs;
240wall/16MiB live log per child. The parent, independent rawpy/TIFF reader and
byte-identical relocated registrar controllers are not implemented by this
Rust prototype. Their exact input/runtime/source/command closure remains a
required separate release. Frozen registrar first-refusal/unvisited semantics
are retained; no partial constructor binding or claimed all-nine coverage.
