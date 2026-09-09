# Native sensor transfer source handoff

SOURCE-ONLY producer handoff, 2026-09-09. No crate file has been edited.
The patch is unapplied. No RAW payload, candidate, native probe, synthetic control,
Cargo build or numerical test has been executed by this author. Independent
source and choice review, root application/freeze and a finite process release
remain required. The producer author does not verify the scientific result.

Current entry point proposed by the adapter is the ignored CLI test
merge_cmd::native_sensor_transfer::fixed_native_sensor_transfer_pair.
It accepts only NATIVE_SENSOR_TRANSFER_INVOCATION=0..8, resolves the fixed
originals from the contract and creates a fresh native-run-{ordinal} directory.
STREHL_PYRAMID_WORKERS=4 is required; production band_workers may clamp the
execution pool to the frame count, while canonical arithmetic stays independent.
A separately released child would use the built test executable with:
--ignored --exact merge_cmd::native_sensor_transfer::fixed_native_sensor_transfer_pair
--nocapture --test-threads=1.
This is an argv design, not a command that ran. The libtest stdout/stderr remains
raw transport and must not be described as identical to result.json.

Prospective builds are two fresh CLI test binaries with/without the feature.
Root selects fresh targets and verifies Compiling/source/binary identities.
Syntax parsing is not an API/build check. No build ceiling is granted here.

## Exact serialized shape

Every file reference has path, bytes and sha256. Original ROI and prepared ROI
are independent131072-byte u16 little-endian256x256 row-major payloads. Per-route
collapsed output is262144 bytes of four plane-major128x128 f32 bit arrays in
R/G1/G2/B order. Native TIFF uses existing write_merged on these same planes,
256x256, CameraLinear, demosaic=true, Exposure::None, restore=None.

Trace starts with8 bytes NSTRC001 then a u32 little-endian field count52.
Each field has four u32 header words(tag,level,plane,count), followed by count
u32 little-endian words. Float values are original f32 to_bits. Unused level/
plane is u32::MAX. Source-only fixed complete population is46 core fields plus
6 CLI arrays, with separate actual visitation assertions.

Core tags:1 common config18words;2 supplied beta prefix0 or3words;3 band/base
context9words;10 luma level;11 Gaussian variance;12 smoothed squared energy;
13 actual weight;20 already prepared plane coefficient. Each Laplacian emits
context/L/V/E/W then four plane arrays. Base emits context/L/V/W then four plane
arrays. CLI100..103 are consumed R/G1/G2/B,104 luma,105 injected variance.

Tag1 words are: chunk-local merge frame index, requested bands, actual Laplacian
count, gate bits, exponent bits, sharpen bits, mean_coarse, hull_lambda bits,
hull_low_only, fallback_k, fallback_power bits, hull_from_level,
significance_scale bits, then five reserved zero words. Other enum choices are
asserted in source and recorded in final config text; reserved zeros are not
measured enum encodings. Tag3 words: base flag, averaged flag, supplied-beta
selection flag, selected beta bits, white beta bits, gate bits, effective
exponent bits, significance scale bits, effective significance-floor bits.
Base uses explicit bypass markers and zeros, not a fictitious base beta/floor.
Tag3 selected beta/exponent/effective significance are DERIVED re-evaluations of
actual config/prefix, not retained weight-closure locals. Frame JSON records
scalar_context_provenance=DERIVED_FROM_ACTUAL_CONFIG_AND_PREFIX. Actual arrays,
copied config/prefix and numeric trace layout remain unchanged.

On records actual arrays. Placebo's optional arrays/context are zero placeholders,
with the same fixed array extents and visit population; source/variance hashes
are common mandatory identity observations. Its map records have the same eight
positions/keys with explicit placeholders, not actual transform observations.
Off stores no optional arrays or map records. Feature-off baseline has no hook
calls and therefore no CLI optional/mandatory hook input records; original
source/config and final f32/TIFF remain independently comparable.

Frame schema native-sensor-transfer-frame-v1 stores invocation/index/original
ordinal/route/observer, source_metadata, prepared_roi, trace, inputs,
variance_after_sha256, gather_site_records, folded and feature.
Source_metadata includes original FileRef and ROI/256 row hashes, active/buffer
geometry, source path/camera/ISO bits, levels/WB bits and four injected model
entries in consumer order. inputs stores hashes of the four actual planes,
luma, variance before, plus supplied beta bits; the after hash is separate.

gather_site_records uses the already resolved actual profile/model/lens and WB
gain, dx/dy and four f64 similarity bits(a.re,a.im,b.re,b.im), at four real and
four synthetic-probe positions per observed placed fold. It performs no lookup.
A nominal identity is not a claim that these effective channel maps are identity.

Traversal schema native-sensor-transfer-traversal-v1 retains source handoff/
decode/fold counts, expected fullres/probe counts, retained_map_record_count,
expected_map_callback_visits (not individually counted),
shape/config/environment/canonical partition,100-family frame references and
the two final output pairs for that invocation. INITIAL_INCOMPLETE and REFUSED
are separate immutable files; neither authorizes interpreting a prefix as
COMPLETE_NATIVE_CROP_TRAVERSAL. A panic can leave only incomplete/partial files
and raw transport; failure.json is not guaranteed. Attempted-but-unpublished
counts are unknown. The external owned parent retains actual exit/tail and
writer bytes:512KiB TIFF checking occurs after write_merged, not online.
The complete status is traversal only, not scientific acceptance.

## Preparation checks and limits

These exact source-tool commands ran with stdout discarded, each exit0:
C:/Users/chris/.cargo/bin/rustfmt.exe --edition 2024 --emit stdout
experiments/native-sensor-transfer/source/core-hook.rs
and the same command with source/native-adapter.rs.
Reported shell wall intervals were0.4674338s and0.4832874s. They parsed the
8092-byte core/a2d71b5c... and23852-byte adapter/cf3cfbea... source state.
The subsequent adapter delta only renamed two JSON keys
actual_gather_sites -> gather_site_records and
actual_map_sites_observed -> map_callback_visits; no algorithm changed.
No formatter output was applied. These are syntax preparation receipts, not
compiled API validation or numerical evidence. Both source processes count.

The patch constructor applied each hunk to owned in-memory source text and
reversed it. All five original exact byte buffers were recovered, and live
source bytes remained unchanged. It separately records preserved-line-ending
and all-LF candidate hashes; actual application/formatting must authenticate
its own representation. An initial source draft placed the new core include
between KERNEL's documentation and declaration; it was relocated before the
documentation. Worker-name and TIFF fsync source corrections also preceded execution.

The51281d20 candidate remains archived. Corrections return source_ref's exact
checked hash-time length/mtime baseline, checking it before/after decode and after
both folds; there is no fresh predecode baseline. This is metadata continuity,
not an atomic snapshot or complete filesystem/native-library identity. Guarded
timestamps are not serialized. retained_map_record_count is actual On/constant
Placebo records, zero Off/feature-off; expected_map_callback_visits includes
feature-on Off early-return calls, and is explicitly unmeasured. Neither count
proves every pixel gather. No draft correction executed the producer.

The contract derives198.6875MiB independent artifact slots against a proposed
208MiB ceiling, including nine2MiB orphan stages. The explicit source pin pass
read883974 bytes; earlier source reads and subsequent source writes/readbacks
are additional. No complete process CPU/read total was instrumented. This lane
remains inside its declared64MiB read/4MiB retained source scope; current authored
source set before this handoff was53565 bytes. Numerical permissions remain
unissued, and all previous RAW/profile/calibration caveats remain in force.

Source-only path correction after the reviewed producer candidate: the ignored
test canonicalizes the existing experiment root before creating native-run-I.
This removes literal parent components from emitted artifact paths; ordinary
and Windows verbatim absolute drive spellings remain supported by the reader.
Only that root expression changes. No array/operator/writer ordering, input,
population or numerical configuration changes. The prior adapter was24251 B/
fa96ad627f5d20321467a9a3b5343a495a23f8a965e165555f5285a1734aa884;
current adapter is24327 B/7e471b2512930dba0e2264de69d2f94a32bdf86d3d85a58f7a875f77054a0fc2.
An in-memory one-expression reverse recovered the prior exact bytes. No
crate patch changed or candidate ran; root separately owns live integration.
