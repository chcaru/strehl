# Output geometry adapter audit

2026-09-07. Bounded source audit requested by the root; no milestone allocated,
implementation, render, capture access, holdout access, or acceptance-bar change.
Only this file belongs to this audit. **VERIFIED** below means source inspected;
**DERIVED** means a coordinate equation derived from that source; proposed
commissioning controls are **UNRUN**. This is not independent verification of a
new adapter, because no such adapter was implemented here.

## Finding and smallest useful next implementation

**VERIFIED:** the useful components already exist, but they are not joined into
an authenticated product output-grid consumer:

1. M193b binds and validates the input-only overlap and denominator.
2. M165 reads exact common RGB16 TIFFs and proves merge-facing input sample
   identity. Its `strehl-common-input` executable optionally exercises a
   **one-frame** generic RGB `BandMerge` and writes a JSON receipt. It does not
   write the merged image or run a common-TIFF stack through the native CLI.
3. Native `run_pyramid` resolves actual alignment, coverage fit, and compact
   `PyramidDomain` before constructing its pyramid. These values can establish
   its output lattice without looking at an output image.
4. `write_merged` and `image_out` determine emitted dimensions. M193b has no
   actual-output-file argument, and its adapter/settings hashes are still
   syntactic identifiers, so it does not check that file against the declaration.

**ARGUED implementation recommendation:** add a small trusted output-plan
producer at the native resolved-domain boundary, carry that same immutable plan
to the writer, and add a separately bound post-write TIFF contract checker.
Join these to M193b's retained `TrustedInputBinding`; do not replace its registrar
or use the program's crop to reconstruct its denominator. Initially support the
existing full-resolution native Pyramid path with explicitly frozen settings.
The common-TIFF byte adapter is reusable input machinery, but calling its current
one-frame exercise a production common-merge renderer would overstate support.
Adding actual common-TIFF multi-frame render orchestration is a separate missing
integration, not an output-descriptor formatting task.

This completes an audit only. It does **not** close geometry blocker `(b)`,
establish comparator geometry, fix the known common-input color-semantic
disagreement, or qualify real input registration across a focus sweep.

## Prior work that already answers parts

| Source | Existing result and what it does not supply |
|---|---|
| `docs/research/M-COVER-NATIVE.md`, including amendments | Separates a native-sized array from native sampling; Crop and Scale have different coordinate maps. The denominator amendment explicitly distinguishes common input support from full-array area. Its old late-crop implementation statements are historical. |
| `docs/research/BUILD-CROP.md` | Coverage Crop leaves the placements unscaled; Scale stretches the supported scene into the original dimensions. Its identity control required holding chromatic-aberration correction constant. Geometry alone does not certify clean borders. |
| `docs/research/M130-crop-early.md`; commit `8e83dced` | Already moved the Pyramid crop before analysis and collapse, preserving full-plane warp coordinates and writing the compact plane once. The old suggestion to move Crop early is already implemented. Its pixel-area predicate is not M193's fixed common-overlap denominator. |
| `crates/strehl-cli/examples/cover-reference.rs` | `validate_map`, `reference_gauge`, `admit_reference_placement`, and `crop_source_index` already handle stack association, actual reference placement, and integer crop addressing. The comment connecting crop addressing to `write_merged` describes the older late-crop layout; current extraction implements that address translation. The example's FNV provenance is not M193b's exact byte binding. |
| `docs/research/M165-common-input.md`; `experiments/M165-common-input/consumer_gate.py` | Exact TIFF/payload/merge-boundary identity and executable/settings/invocation receipt machinery exist. The report explicitly keeps exact byte identity separate from color semantics (`PROPHOTO_DISPROVED`). Reuse the receipt concepts rather than invent a second unbound hash vocabulary. |
| `docs/research/M193-geometry-review.md` | Demonstrated a stale-denominator false pass and documented missing real adapter and post-render dimension check. Also demonstrated correct refusal under complementary focus content. |
| `docs/research/M193b-geometry-consumer.md` | Repairs denominator/schema/authority integrity and streams input construction. Explicitly leaves real adapter mapping truth and single-reference coverage open. Its independent descriptor mutation tests do not claim to authenticate a renderer. |
| `docs/research/M85-output-correctness.md`; `BUILD-OUTPUT.md`; `M95-resolution.md` | Output color/development and resolution work supplies writer and branch context. None licenses equating a binned grid with the native input grid or inferring a map from TIFF size. |

## Concrete source boundaries

Locations below refer to the inspected tree; another allocated agent is adding
the M194 decoded-frame seam to `merge_cmd.rs`, so symbols are the durable anchors.

| Boundary | Current symbol and location | Adapter consequence |
|---|---|---|
| Input authority | `experiments/m193b-geometry-consumer/consumer.py::construct_overlap_paths`, `TrustedInputBinding`, `validate_overlap`, `validate_output_grid` at 409, `output_retention` at 416 | Trusted runner must retain the original binding. Candidate-supplied JSON cannot replace it. Neither output method reads an output file. |
| Frozen output schema | `experiments/M193-cover-overlap/reference.py::OUTPUT_GRID_KEYS` at 834, `validate_output_grid` at 854, `output_retention` at 991, `make_output_grid` at 1042 | Last helper is a fixture constructor, with hashes of literal fixture strings. Do not use it as evidence of artifact existence. Exact descriptor keys mean extra evidence belongs in a separately authenticated receipt. |
| Common TIFF input | `crates/strehl-raw/src/common_tiff.rs::ExpectedIdentity` at 79, `CommonTiffFrame::read` at 110, `verify` at 333, `merge_planes` at 381, `hash_merge_planes` at 405 | Already strict RGB16 input parsing, whole-file/payload/provenance verification, and exactly representable u16-to-f32 planes. Preserve these checks. This input parser is not a general output parser: it requires the frozen common-input ICC/provenance. |
| Current common consumer | `crates/strehl-cli/src/bin/strehl-common-input.rs::run` at 43, `exercise_core_merge` at 137 | One TIFF, optional one-frame core exercise, finite/output-shape check, JSON output only. Search of all Rust crate callers found no other production caller of `CommonTiffFrame`. |
| Native source lattice | `crates/strehl-raw/src/lib.rs::Frame::sample` at 132, `QuadSource::geometry` at 238; `strehl-core/src/plane.rs::PlaneGeometry::from_active`, `sensor_coord` | Coordinates are active-area coordinates; plane dimensions are active dimensions divided by two with integer truncation. Bind active origin, extent, parity and any odd trailing row/column; never use padded decoded-buffer size. |
| Input selection | `crates/strehl-cli/src/main.rs::raw_paths` at 1199 | Filename-sorted `.arw` inputs, optional truncation. This path does not accept common TIFFs. Bind the exact ordered files actually selected as well as the M193 byte multiset. |
| Actual warp/settings resolution | `merge_cmd.rs::alignment_for` at 2382; `align_cmd.rs::load_or_solve`, `merge_reference` at 1420 | Explicit `STREHL_WARPMAP` can override the requested resampler; the sidecar wins. `STREHL_ALIGN=0` wins over the override. Default reference is selected by the program, not M193's hash order. Record resolved values, not just CLI strings. |
| Existing sidecar identity | `strehl-core/src/warpmap.rs::StackIdentity` at 194, `from_paths` at 238, `WarpMap::check_stack` at 419 | FNV over names and byte lengths is an accidental-mismatch check, not exact content identity. Same-name/same-size altered inputs can retain it. Additional SHA-256 binding to consumed inputs is required. |
| Crop/Scale resolution | `align_cmd.rs::CoverFit` at 1109, `cover_or_explain` at 1647, `cover_rect` at 1766, `fit_to_cover` at 2555, `cover_scale` at 2586 | Record actual `k`, actual rectangle, full geometry, map reference and serialized transforms. Crop composes no Scale transform; Scale composes `S_k.then(t)` into every placement. Skip/uncovered must not become an implicit identity certificate. |
| Earliest native plan boundary | `merge_cmd.rs::run_pyramid` at 5561, immediately following `alignment_for`, `cover_or_explain`, and `pyramid_domain`; `PyramidDomain` at 4550, `pyramid_domain` at 4607 | Full grid plus compact rectangle are known before pyramid allocation. Produce the plan here and use this exact retained value throughout rendering. Crop without actual coverage is already refused. |
| Crop is applied | `merge_cmd.rs::extract_planes` at 4645 and `load_frame` | Warping uses `domain.full`; extraction copies sites at `2*(rect origin + local coordinate) + CFA site offset`. No destination outside the compact domain enters the pyramid. The decoded-frame seam in M194 may provide a useful synthetic entry into this path. |
| Warp direction and site coordinates | `strehl-core/src/warpmap.rs` module contract; `align.rs::Similarity::apply_at` at 290 and `then` at 314; `align_cmd.rs::warp_frame_in_place_fullres` at 2011 | Placement is program-reference to source, already a pull. Full-resolution gather uses `2*t.apply_at(px+dx/2,py+dy/2,W/2,H/2)`. Inverting that pull inside the gather is wrong. The output descriptor needs the inverse direction after composing the gauge bridge. |
| Native output | `merge_cmd.rs::write_merged` at 7167, demosaic branch around 7427; `image_out.rs::write_demosaiced` at 1369 | `merged.geometry()` is already compact. Interleaving emits `2*width` by `2*height`; demosaic and TIFF writer retain those dimensions. No second Crop occurs. |
| Binned output | `image_out.rs::write_binned` at 1488, `develop_binned` at 1501; final measurement branch in `write_merged` | One pixel per quad. Developed branch co-sites R/B by quarter-plane-pixel shifts; byte-frozen measurement branch does not. A full-native common grid cannot be certified by silently declaring this half-pitch image identity. |
| TIFF encoding | `image_out.rs::write_rgb16_described` at 603 | Asserts payload size and writes supplied width/height, description, optional ICC, Software and resolution metadata. It does not take an overlap binding, pre-output receipt, Q32 map, or settings digest. Its Software version is not the executable bundle hash. |

## Coordinate equation and minimal admission restrictions

**DERIVED from the actual pull convention.** Let `u` be an absolute full-plane
coordinate, `c=(W/2,H/2)` its centre, and the actual resolved placement for a
selected anchor input `r` be `P_r(u)=A_r*(u-c)+b_r+c`. Use the serialized actual
placement even when `r` is named the program reference; M-COVER-NATIVE's
reference-gauge evidence forbids replacing it with an assumed identity.

Let `B_r` map that input's decoded active sensor coordinates to its common-TIFF
coordinates, and let `T_r` be M193's input-r-to-common-reference transform.
For native demosaiced output coordinate `o` and plane crop origin `d`, the
predeclared output-to-common map is:

```text
u = o/2 + d
raw_sensor_r = 2 * P_r(u)
common = T_r(B_r(raw_sensor_r))
common_to_output = inverse of the composed map above
```

For Scale, `d=0` and `P_r` includes the actual coverage scale. For Crop, `d` is
the integer compact-domain origin and the placement has no added scale. With
identity gauge and identity `B_r`, native Crop gives `o=common-2*d`. Scale with
identity raw reference gives `common=k*o+(1-k)*(W,H)` and therefore
`o=(common-(1-k)*(W,H))/k`. The centre here is the implementation's `W/2,H/2`
in **plane units**, not `(native_dimension-1)/2` substituted from convention.

This equation establishes the declared raster lattice, not correctness of every
frame's placement or image detail. An arbitrary anchor and a wrong placement can
still define a self-consistent false physical map. The independently chosen
input-only held-out landmarks must validate the bridge across the supported
input set; do not report zero residual merely because one equation inverts
another. Inadequate focus overlap remains a valid refusal.

**VERIFIED:** M165's converter already records active width/height, raw dimensions,
top/left margins (`converter.py::raw_metadata` at 2055), requests full size and
`user_flip=0` (`postprocess_kwargs` at 1944), and checks output shape against
active shape. These are useful evidence for `B_r`, but output dimensions alone
do not prove identical origin/parity across LibRaw and the native decoder. Bind
the converter manifest/source hash to each native input and verify the active
coordinate bridge on synthetic known-address data. Refuse unexplained crop,
orientation or decoder-origin disagreement. No external decoder source was read.

**ARGUED smallest initial support:** full-resolution native Pyramid, actual
full-resolution gather, verified RGGB active geometry, frozen known resampler,
and explicitly disabled CA correction for the first coordinate commission.
Record/refuse the unsupported per-channel optical transform rather than pretend
one similarity proves every channel's map. This is an adapter support restriction,
not a proposed default change. The binned branch can be reported accurately as a
separate grid, but its approximately 0.5 common-to-output scale fails the frozen
native +/-0.1% bar. A real Scale map may likewise correctly fail; no compensation
or bar relaxation is part of this task.

## Exact missing integration

1. **Trusted plan authority.** The trusted runner needs an immutable binding for
   the canonical output plan, parallel to M193b's input binding. Bind the exact
   overlap/input bundle, ordered consumed input hashes, adapter source/runtime
   bundle, resolved settings/environment, selected sidecar bytes, reference
   identity, active geometry, coverage result, output branch and guard. The
   renderer receives the same retained plan used to generate the descriptor;
   arbitrary JSON plus a recomputed self-hash is insufficient. Establish this
   before any output pixels are produced. A receipt written after rendering
   with `created_before_output=true` would not establish chronology.
2. **One physical gauge bridge.** Resolve `B_r`, compose the actual map above,
   and quantize to the frozen Q32 representation. Retain the unquantized source
   operands and independent input-only residual evidence. The registrar's
   denominator remains independent of the stacker's sidecar. The output map may
   use the sidecar actually consumed, but it must be checked against input-only
   geometry rather than assumed true because it parses.
3. **Settings enforcement.** Freeze effective settings after precedence has
   resolved them; render must consume exactly those values. Include geometry
   switches (`cover`, alignment mode/map, full-resolution gather, demosaic,
   resampler, reference, limit/frame selection, CA/profile) and the development
   branch. Reuse M165 registry/invocation/bundle verification where applicable.
   Prevent input/sidecar changes between binding and consumption through a
   verified snapshot or locked/read-once handoff; a pre-run path hash alone has
   a substitution window. Do not retain every full-resolution RGB input in RAM.
4. **Writer boundary and actual-file check.** Assert the actual writer-call
   dimensions/branch equal the retained plan, then independently parse the
   completed TIFF's dimensions, channel/sample format, orientation and promised
   metadata. Bind the actual output bytes and receipt to this invocation. Settings
   cannot be recovered in general from the TIFF header, so inspect the consumed
   plan/receipt as well. A plausible same-sized file with wrong geometry cannot
   be detected by dimensions alone; production-path synthetic commissioning and
   trusted execution of the frozen adapter are both necessary.
5. **Call M193b on retained authority.** Only after those checks should the
   trusted consumer pass the bound overlap and authenticated descriptor to
   `validate_output_grid` and `output_retention`. Keep undefined/unsupported
   adapters and failed contracts explicit. Never rebuild the descriptor from
   actual dimensions or replace a failed crop's denominator with its own area.

## Realizable commissioning controls, proposed before any execution

All controls below are **UNRUN** proposals. They use cheap synthetic decoded CFA
and deterministic RGB16 TIFFs in the workspace, no RAW captures or holdouts. A
future brief should choose fresh dimensions, offsets, scenes and warp signs and
freeze them before running. Use the actual product extraction/gather/writer
entry, preferably the independently commissioned M194 decoded-frame seam; a
Python surrogate of the writer alone cannot establish production mapping truth.

| Control | Independent stimulus and expected outcome; failure power |
|---|---|
| Valid untreated | Known asymmetric textured scene on an even active CFA grid, nonzero active buffer origin and padding, identity geometry, full-resolution output. Valid input-only registration and authenticated grid/file receipt pass. Avoid a flat as the only registrar success stimulus. |
| Flat/null | Constant image with the same geometry. Geometry planning and writer dimension checks still work, while texture-dependent registration may correctly refuse. Constant output cannot detect a false translation, so it is not the mapping positive control. |
| Crop with native pitch | Nonzero unequal x/y plane offsets and a non-square rectangle. Known native coordinates must shift by exactly twice those offsets and TIFF dimensions be exactly twice the rectangle. Compare coordinate-coded inputs/impulses away from interpolation support to an independently calculated map. |
| False map of unchanged size | Keep the actual render and dimensions fixed, change the declaration by a subpixel translation (e.g. a defensibly re-chosen fraction) and rehash it. M193b alone can accept a well-formed transform; the new trusted plan binding must reject it. Separately mutate product crop addressing while leaving its receipt correct, and require the known-coordinate output oracle to detect this same-size error. |
| Scale rather than Crop | Use a nonidentity coverage factor and independently calculate the map above, preserving the actual dimensions. Correctly report the map and reject it when the unchanged scale bar is exceeded. A descriptor claiming identity for this same-sized output must fail plan authentication. |
| Dimension mismatch | After the plan is sealed, route a different crop rectangle/demosaic branch to the actual writer, or supply a complete valid TIFF of mismatched dimensions. Both must fail the output contract. Do not repair by changing expected dimensions. |
| Live FOV failure | A supported declared crop that removes more than 1% of the fixed common support, paired with an identity/support-preserving pass. The contract must report field-of-view failure while retaining the original denominator. This tests a physical loss, not malformed JSON alone. |
| Gauge choice | Choose an anchor whose input hash order differs from the program frame order, a nonidentity actual reference placement, and nonzero rotation/translation. Independent coordinate points must expose accidental identity substitution, inverted pulls, wrong centre, or forgotten native/plane conversion. |
| Settings and input mutation | Change an environment override after planning; substitute a same-name/same-size source or sidecar; replace the settings bundle and rehash the untrusted descriptor. Each must refuse against retained authority. Control: unchanged snapshot at another path, with deliberately permitted path relocation, retains the same content identity. |
| Observer placebo | Render with receipt/diagnostic off, on and allocated-but-disabled placebo. Require byte-identical TIFF and pixel hashes for identical effective settings. A changed crop is a meaningful nonidentity control and must change geometry/output. |

Known limits must remain visible: a header-only check cannot discover a shifted
image of identical dimensions; one anchor's algebra cannot test its own mapping
truth; a synthetic success does not qualify real focus-varying registration;
and per-channel optical corrections need additional support evidence. A frozen
adapter is an explicitly trusted implementation boundary, not cryptographic
proof that arbitrary candidate pixels followed its declaration.

## Reproducible audit commands and provenance

Commands run from the repository root, plus targeted `Get-Content` slices of the
named reports and source symbols:

```powershell
python experiments/ORCH-drift-check/prior_art.py output geometry adapter
rg -n 'common.?tiff|CommonTiff|strehl-common-input' crates --glob '*.rs' --glob 'Cargo.toml'
rg -n 'output.*(dimension|grid)|common_to_output|adapter_sha256|expected_width' crates experiments/m193b-geometry-consumer experiments/M193-cover-overlap --glob '*.rs' --glob '*.py' --glob '*.json'
rg -n 'fn alignment_for|fn run_pyramid|fn pyramid_domain|struct PyramidDomain|fn extract_planes|fn write_merged|domain.rect|domain.full' crates/strehl-cli/src/merge_cmd.rs
rg -n 'fn reference_gauge|fn validate_map|fn crop_source_index' crates/strehl-cli/examples/cover-reference.rs
git log -4 --oneline -- crates/strehl-cli/src/merge_cmd.rs
git rev-parse HEAD
```

The prior-art query returned M193b, M95-resolution, M193 review,
M95-merge-vs-frame-sharpness, BUILD-CROP, BUILD-OUTPUT, M85, V-REVIEW-geometry,
M99-photometric and M164-transfer-veto, with further topic references including
M-COVER-NATIVE. Following the code/history added M130 and M165 rather than
repeating historical claims of absence.

HEAD at final source inspection: `9156a111d3487f51961f18344e3c49136fc8c5a6`.
The tree is shared and dirty; no assertion of a pristine checkout is made.
M194 owns the concurrent uncommitted `merge_cmd.rs` change. SHA-256 of files
inspected (not a build certificate):

| File | SHA-256 |
|---|---|
| `crates/strehl-cli/src/merge_cmd.rs` | `288326406534C6CBC227D5DE3CF08102AAD2FDFA1D5BDB0EAF020FBAAC1EB23A` |
| `crates/strehl-cli/src/align_cmd.rs` | `B3DE7738151A6BC0500C66DD916F9FCB20CDB9BE0BF698AD00425D3EBB397C69` |
| `crates/strehl-cli/src/image_out.rs` | `C1362363740CB0176985283455CD6DDEF80479854B1BBC9F0396851C490F82B6` |
| `crates/strehl-raw/src/common_tiff.rs` | `BAC1D18F036B8960A8E82D01B610AE945D00D259D4CC3FE7EB9106E8A8077F42` |
| `crates/strehl-cli/src/bin/strehl-common-input.rs` | `0ABF5917357365BA83028F82C0A2855917AD45071D95D3EC2D404702DE1EF31F` |
| `experiments/m193b-geometry-consumer/consumer.py` | `41E087797866505CC30384888ED83CD7A94DBCD7B757054433186003B37D2B26` |
| `experiments/M193-cover-overlap/contract-v1.json` | `19421729AC39273A5F61CDA5068026F3458BA08C98F0AA954DE7C219CBFABF47` |

No compile or test was run for this read-only audit. Existing source tests were
read, including the early-Crop outside-domain poison/inside-domain specificity
pair, invalid rectangles, compact writer addressing and estimator-Crop refusal;
their existence is not a new test result. No GPL/LGPL implementation source was
opened, and no capture tree was enumerated or decoded.
