# M193c registration derivative — source-reviewed proposal

2026-09-07, implementation_audit. **DESIGN ONLY.** No RAW bytes, image decode,
build, renderer, registrar or scientific measurement was executed for this
proposal. This file is the only change. Root review and the later explicit
source/command release precede implementation and execution.

The smallest useful derivative reuses the project's single-frame decode,
active-row access, MHC demosaic and described RGB16 writer. It does not need a
new RAW backend, a merge or a warp. The result is a **camera-native registration
development input**, not a qualified common-merge TIFF or a colour-managed
picture. Registration coverage remains independently fallible.

## Inspected boundaries and scope

Read `SYNTHESIS.md` §3, the root-reviewed M193c charter, M193b's report and actual
consumer, M193's frozen reference/contract, and the project-owned sources below.
No rawler, LibRaw, GPL implementation or ExifTool Perl source was read.

| Existing boundary | Reuse or exclusion |
| --- | --- |
| `strehl_raw::decode`, `Frame::active_row`, `Frame::wb_gains` | One owned u16 frame; decoder-reported scalar levels and green-normalized as-shot RGB gains. No `decode_all`. |
| `image_out::write_demosaiced` with `Develop::measurement(false)` | Full native mosaic to row-wise MHC and u16 RGB; no full float RGB intermediate. Its `resolve_tone` immediately returns because `wants_tone=false`. |
| `demosaic::demosaic_row` | Existing default Malvar path. Fresh child must remove `STREHL_DEMOSAIC` before its OnceLock is initialized and record the removal. |
| `image_out::write_rgb16_described` | Existing classic RGB16 TIFF encoder; actual uncompressed/layout/tag properties must pass private and native independent reads. |
| `consumer.py::construct_overlap_paths` | Frozen M193b input-only ordering, snapshots, features, reference choice, registration and denominator. No output geometry may enter this constructor. |
| `align_cmd::warp_frame_in_place_fullres`, stack/merge/write_merged, binned writer | Not used for the derivative: they add unwanted geometry, merge, correction or sampling semantics. |
| `CommonTiffFrame` | Not used to declare this derivative qualified. Its canonical provenance/profile/tag contract is different; its identity success would not prove a common-TIFF merge route. |

The actual M193b consumer does not validate colour primaries. Its frozen
`prophoto_luma_u16` computes
`round_even((2880402 R + 7118741 G + 857 B)/10000000)`, then
`registration_u8` applies a per-image nearest-rank 1–99% stretch and SIFT at the
full input dimensions. On these camera-native derivatives this is a **fixed
channel projection used as an intensity proxy**, not physical ProPhoto
luminance. Do not change those weights or the stretch in this task, or claim
the old ProPhoto function name authenticates the new input space. The
derivative itself has no fitted tone operation; the registrar's existing
internal intensity stretch is explicitly retained. Its internal SIFT scale
space also remains part of that frozen algorithm, not a resized input TIFF.

This rehearsal does not restore M165's ProPhoto qualification, establish a
common RGB merge/noise contract, improve the frozen fixed-reference registrar,
or validate the actual product output-grid descriptor. Those scopes remain
separate in the charter.

## Nine inputs fixed before decode

Use exactly the charter's sorted indices
`[0,13,26,39,52,65,78,91,104]` under
`D:\personal\macro\coffee-bean`, with filenames and lengths exactly as its
table. They are development inputs, not a new holdout.

After private commissioning and execution release, a plan-only parent step
lists with `Get-ChildItem -Force`, validates all nine identities, streams their
complete hashes and writes the complete nine-entry input plan **before the
first decoder is called**. No prefix-selected replacement, dropped failure or
post-decode frame choice is allowed. This future hashing reads RAW bytes; it
has not happened during this design task. Pin the plan externally in the
later decode command and recheck every source before/after the complete stage.
Record original index, absolute path, filename, length, modification time,
attributes and SHA-256; metadata equality alone is not byte authentication.

For each selected source, make one counted, verified workspace ARW snapshot
with the original filename extension. Both decoders consume that same pinned
snapshot, one process at a time. No XMP, embedded JPEG, camera orientation
rotation, neighbouring file or corpus-side cache is consumed. Keep one input
snapshot at a time; retain its identity in the result after releasing the
temporary file. Any failure stops admission of the nine-file package and
retains the named partial attempt; it does not change the intended population.

## Exact derivative operation

For the primary decoder's returned frame, validate checked integer extents,
`data.len()==stride*buffer_height`, contained nonempty active area, even active
width/height and even active origin, and a supported active RGGB pattern.
Do not call `PlaneGeometry::from_active` to round dimensions or crop to quads.
The independent decode below must confirm the same full visible dimensions
and local CFA phase; different decoder padding origins are recorded separately.

Let `b=frame.levels.black`, `w=frame.levels.white`, and
`g=frame.wb_gains()` using only its first three colour coefficients. Require
finite `0 <= b < w <= 65535`, finite positive range and gains; unusable metadata
refuses instead of falling back. The fourth WB entry may be NaN and is never
multiplied. This is a fixed **metadata-selection rule**, not fixed camera
constants: persist each actually consumed f32 value as both JSON value and
bits. No per-image fitted WB, common-frame WB substitution or matrix choice.

For active-local integer centre `(x,y)`, read exactly
`frame.active_row(y)[x]`, and construct the f32 mosaic in this operation order:

```text
range = w - b
inverse_range = 1.0f32 / range
gain = g[R/G/B] according to active-local RGGB parity
m[y,x] = ((u16_sample as f32 - b) * inverse_range) * gain
```

Keep finite negative and above-one values through the mosaic and MHC. There
is no pre-demosaic black clamp or upper clamp. Call
`write_demosaiced(path, active.width, active.height, &m,
&Develop::measurement(false))` once. The existing `develop_pixel` performs
the final per-channel `[0,1]` clamp, identity transfer, and
`(value*65535.0f32+0.5) as u16`. It applies no matrix, highlight desaturation,
exposure, automatic tone, sRGB curve or sharpening in this state. MHC itself
can overshoot and alter detail; “no extra sharpening” is not a claim that a
linear demosaic cannot inflate a sharpness metric.

The fixed as-shot rule is deliberate. The existing TIFF description says
as-shot WB; unity WB through the same writer would misdescribe its pixels.
An earlier considered unity-WB alternative is not this proposal. It would
need an independently reviewed description seam, and adds no necessary
capability for the present input-only rehearsal.

Every output has the full active width/height, interleaved unsigned RGB16,
one page, compression 1, orientation absent-or-1, no alpha and no ICC profile.
Require the exact existing CameraLinear description and package-version
Software tag, derived from the compiled build record; do not guess the full
CLI build-stamp string. The sidecar calls the purpose
`registration-development-only`, states the actual gains/levels and records
`colour=linear-camera-native`, `transfer=identity`, `matrix=null`,
`spatial_transform=identity`, `orientation_applied=false`.

Output centre `(x,y)` is the active-local source centre `(x,y)`; its decoded
buffer centre is `(active.x+x,active.y+y)`. There is no half-pixel addition,
origin subtraction beyond active extraction, channel co-siting resample,
scale, crop, translation or orientation rotation. All borders are written;
MHC's existing parity-preserving mirror extension affects reconstructed
values there, not the stated sampling grid. Camera display orientation is not
the sensor-native orientation-1 coordinate convention.

## Concrete implementation and records

Propose one test-local source,
`experiments/m193c-output-grid/registration-derivative.rs`, included as
`m193c_registration_derivative` inside `merge_cmd/production-truth.rs`, beside
Zeno's proposed `m193c_output_grid` module. It does not edit his
`private-adapter.rs`. Root assigns the exact declaration before code. Core
helpers are `validate_frame`, `normalized_active_mosaic` and
`write_registration_derivative`; production `write_demosaiced` stays intact.
The ordinary merge, RAW decoder, demosaic and writer sources are not edited.

A small parent driver supplies the input-plan SHA, exact selected original
index, fresh output directory and released copied test executable. Its child
accepts no geometry/alignment/quality options. Pin and record all environment
variables the reachable path reads, with `RAYON_NUM_THREADS=2` and all
`STREHL_*` overrides removed except the explicitly named derivative arguments.
The proof is source closure plus the actual clean child environment, not a
claim that absent CLI arguments disable ambient OnceLocks.

The later closed schemas should be narrow:

- Input plan: schema/purpose, charter/build/source/command refs, exact nine
  source entries and fixed settings; no candidate-output geometry.
- Per-frame derivative receipt: original/source/snapshot refs, actual decoder
  identity, full buffer and active geometry, active-payload/per-row hashes,
  levels/WB values and bits, fixed operation settings, TIFF file and canonical
  pixel hashes, completion count, resource and source/input closure.
- Independent decode/read child: own decoder/runtime, visible geometry and
  phase, active hashes, own metadata comparisons, actual TIFF read/tag/pixel
  result and explicit refusal details. No producer self-PASS substitutes.
- Nine-entry package: all nine ordered receipts and independent reads,
  required completed cardinalities, actual command/exit/logs, source/input
  before/after bindings, error/finalization errors. Success means
  `COMPLETE_REGISTRATION_DERIVATIVES_ONLY`, not registration coverage.

The registrar receives the nine TIFF paths only after this package is
admitted. Retain the original-index-to-derivative map separately from its
byte-sorted reference order. Preserve duplicate multiplicity; if derivative
bytes coincide, list all associated originals rather than inventing a unique
reference identity. A successful frozen `(manifest, TrustedInputBinding)`
belongs to these exact derivative bytes. It is never reconstructed from a
candidate manifest or reused for changed output inputs.

Independently read each complete native TIFF through a separately versioned
bounded reader, with an externally supplied file hash, exact expected shape,
checked strip extents and duplicate-tag/type guards before pixel allocation.
Its 36-million-pixel limit replaces neither the frozen M194g reader's small
limit nor CommonTiffFrame's colour contract. Hash every decoded RGB sample in
native row order; the selected private coordinate sites are an additional
oracle, not a substitute for complete-file reading. Close the writer, sync
the output, and include the final payload/source/input recheck and terminal
persistence in the parent budget. Late failure preserves the original error
and secondary cleanup errors and cannot leave an admitted nine-file package.

M193b hard-codes its temporary TIFF directory to its module's `HERE`.
Recommend a byte-identical source snapshot under the new attempt, preserving
the sibling layout `m193b-geometry-consumer/consumer.py` and
`M193-cover-overlap/reference.py`. Import the actual copied module with a fresh
cache, pin both copies and original files, and do not monkeypatch its math or
`TemporaryFile`. This routes its one temporary snapshot inside the new budget
without touching frozen sources. Exact old small companions must reproduce
their full manifests before the nine derivatives reach that constructor.

## Private power and independent decode

Freeze literal controls before code execution. The following minimal proposal
uses two derivative TIFFs (one affine and one non-affine border/clamp fixture)
alongside Zeno's ten proposed geometry renders, exactly the charter's twelve
small private render slots. The derivative adds no optional observer; its
mandatory source/extent/operation receipts run on every call. Zeno's geometry
population separately commissions the actual production observer. A later
optional derivative observer would need its own prospectively allocated
off/count/placebo executions, not an inferred exemption from rule 26.

1. **Active extraction and rank-two coordinates.** A synthetic buffer has
   stride 40, height 32, active origin `(2,4)`, extent `30×22`, levels
   `b=64,w=4160`, WB `[2,1,4,NaN]`; padding has a distinct sentinel. Plant the
   post-WB continuous fields
   `R=1/8+x/512+y/256`, `G=1/4+x/256-y/512`,
   `B=3/8-x/512+y/512`, by the exact integer CFA formula
   `64+4096*field/gain`. Read actual TIFF RGB at all Cartesian pairs
   `x={2,5,8,11,14,17,20,23,26}`, `y={2,5,8,11,14,17}`.
   Independent rational affine predictions allow at most one u16 code for
   f32 quantization. The two nonparallel channel gradients power both axes.
   Wrong stride/origin, swapped axes, half dimensions, parity shift and a
   rehashed one-pixel translation must fail the consuming pixel/shape check.
2. **Borders and signed input.** Use the same geometry with constant
   `sample=b+128`, replace the R site `(10,8)` by `b-16`, and place different
   known DN impulses at all four corners. An independently assembled exact
   MHC stencil/mirror oracle checks all pixels, including the edge band.
   The premature black-clamp mutant must alter consumed neighbours, not only
   the already-clipped R output. Padding sentinel changes are null; active
   impulse movement is live. Primary and independent oracle f32/quantized
   comparisons use the same prospectively declared one-code allowance.
3. **Normalization metadata.** Actual normalized-mosaic helpers reject NaN,
   zero/negative range, invalid RGB gain and overflow geometry. Literal
   black/white and half-code companions check sign, gain ordering and final
   quantization. Changing only the fourth WB NaN representation is null;
   changing an actual RGB gain is live. These are input arrays, not RAW
   captures or extra TIFF render populations.
4. **Reader boundaries.** Private rehashed TIFF/schema faults
   change dimensions, compression/orientation, sample width, strip extent,
   input association or a coordinate pixel. Restored actual files pass. Do
   not count a stale hash refusal as power against a coherently wrong map.
5. **Source lifecycle.** A fake source adapter proves all-nine plan validation
   precedes the first decode, one frame is live, the previous frame drops,
   metadata/input changes refuse and late persistence revokes completion.
   Allocation/time/extent equality companions and over-limit faults are
   bounded private controls, not unperformed assertions of resource safety.

Independently decode **all nine** snapshots with rawpy/LibRaw, without calling
`postprocess`. Copy `raw_image_visible` explicitly inside its context manager
(`.copy(order='C')`), account that allocation, and hash the owned u16 active
array and each native row before releasing it. Do not rely on
`ascontiguousarray` alone: it may return the borrowed view. Releasing the
context while continuing to inspect that view is forbidden. Record the actual
rawpy/LibRaw module/version hashes and phase through its public visible CFA
metadata; this proposal requires no LibRaw source inspection.

Compare primary and independent full active u16 payloads **exactly**, with
matching dimensions/local RGGB phase. Independently require all actual CFA
black levels equal the scalar primary black and the usable white metadata
agree; do not hide per-plane variation behind the primary wrapper's
first-level selection. Record as-shot RGB coefficients separately and compare
their normalized values with an explicit pre-run f32 metadata allowance
(`max abs <= 2^-20 * max(1,abs(primary_gain))`), not a fitted colour transform.
The pixel hash comparison has no such tolerance. Any difference refuses
decoder agreement and preserves both records; no align/crop/offset search
reconciles the two decoders. Exact reread is a decode/data check, not proof
of real registration truth or a camera calibration measurement.

## Resource feasibility and two explicit review choices

Use the charter's one non-resetting real-stage envelope: 1200 CPU seconds,
1800 wall seconds, 8 GiB process-tree ceiling, 4 GiB new workspace bytes and
128 MiB metadata/logs. Each child remains within 240 wall seconds/16 MiB log.
Private commissioning shares its 600 CPU/1200 wall envelope. Include setup,
hashing, both decoders, derivative writes, independent reads, registrar
snapshots, later product output and final persistence; do not reset the clock
when the module or child changes. There is no cost or throughput claim.

Proposed admission limits are source file at most 64 MiB, each native axis at
most 8192, active pixels at most 36,000,000, and decoded buffer at most
40,000,000 u16 samples. For the owned writer path the conservative sum
`2*40m + 4*36m + 6*36m + 2*8192*3*4 = 440,196,608` bytes covers a still-live
RAW buffer, normalized mosaic, RGB16 output and two scratch rows. This is an
allocation derivation, **not** measured RSS or a bound on decoder/SIFT/encoder
scratch. Drop the RAW frame before the writer when only its scalar metadata
is still needed. Independent TIFF reading and registration run after the
primary child exits, with only one decoded image at a time.

Nine derivative payloads, two later native output payloads and one temporary
TIFF payload have a conservative `12*6*36m = 2,592,000,000` byte allowance.
The actual TIFF tags, one ARW snapshot, metadata/logs and all failed artifacts
remain charged to the same 4 GiB limit. Headerless raw debug arrays and extra
native duplicate TIFFs are not retained. These proposed limits accommodate
the historical M1 shape without asserting that these nine files have that
shape. Every actual decoded extent still must be read and checked.

Two points need an explicit root decision before implementation release:

- **Decoder preallocation boundary.** The inspected public
  `strehl_raw::decode` allocates through the dependency before exposing
  `Frame` geometry; it cannot perform the proposed shape checks before that
  internal allocation. A 64 MiB file cap is not a decompressed-size cap.
  Recommend a parent-enforced Windows Job Object memory ceiling from child
  creation, plus immediate post-decode checked extents before any owned
  mosaic/RGB allocation. Do not label that as a pre-decode shape proof or an
  exact RSS ceiling: committed-memory enforcement and observed working set
  are different. If the charter requires literal geometry validation before
  any decoder allocation, a separately scoped metadata API is prerequisite;
  there is no such demonstrated seam in the inspected project wrapper.
- **Derivative versus registrar contract.** Accept the fixed CameraLinear
  as-shot development and existing mechanical channel projection solely for
  input-registration coverage; also accept the byte-identical relocated
  registrar snapshot for its temporary-file root. If colorimetric ProPhoto
  input is required instead, retain this proposal as unexecuted and design
  that separate conversion explicitly. Do not relabel these pixels or relax
  CommonTiffFrame to make them appear qualified.

Inspected pins (not an execution release):

| Source | SHA-256 |
| --- | --- |
| `charter.md` | `0620c4858bb7a09d20251c50a5fedb5694af05549f09bab6bb489904f5cc0909` |
| M193b `consumer.py` | `41e087797866505cc30384888ed83cd7a94dbcd7b757054433186003b37d2b26` |
| M193 `reference.py` | `c08340f6f0658fae048dda92629a543b5a539462a93db196aaae29e1862ba790` |
| M193 `contract-v1.json` | `19421729ac39273a5f61cda5068026f3458ba08c98f0aa954de7c219cbfabf47` |
| `crates/strehl-raw/src/lib.rs` | `1513fd3e682f2edb8c54c7d47083f20f66525ad72a5687fb2e530bb5697fef2a` |
| `crates/strehl-core/src/demosaic.rs` | `425d6889485011cf6f2aaf57b0b873f15fd6ee3250853f3ba5f6540b496b3810` |
| `crates/strehl-core/src/noise.rs` | `d88dc9cf419a8fdb1e3ff2c51f0b0ac80d785c17de7f9e71e905fc977fce0ecc` |
| `crates/strehl-cli/src/image_out.rs` | `c1362363740cb0176985283455cd6ddef80479854b1bbc9f0396851c490f82b6` |
