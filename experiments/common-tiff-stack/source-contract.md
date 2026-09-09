# Common-TIFF stack consumer v1

SOURCE CONTRACT / PREREGISTRATION. No build, fixture generation, test, metric or
render has run. This is the narrow software integration following M194h, whose
diagnosis is closed. No merge/default, native output, RAW parser or M194h artifact
is changed. Sources: SYNTHESIS sections3.1-3.3; M165 common_tiff public adapter;
experiments/review-output-adapter/next-consumer-proposal.md; current BandMerge API.

## Consumer and scope

Add a mutually exclusive mode to strehl-common-input:
`--stack-manifest PATH --manifest-sha256 HEX --report PATH --observer off|on|placebo`.
The existing single-TIFF arguments and behavior keep their old dispatch. Exactly
three ordered128x96 RGB16 inputs are streamed through one three-plane BandMerge,
with one reused FrameWorkspace, no alignment/materialized stack, and one final
finish. The gauge is identity common-RGB pixels. This is neither CFA data nor an
alignment claim. No external corpus or new model/converter intake is included.

Only synthetic-noiseless-v1 and synthetic-independent-rademacher8-v1 are admitted
noise declarations. The latter declares independent per-pixel/per-channel zero
mean +/-8 code values: covariance diag(64,64,64), cross-covariances0. The selection
proxy is c=(1,2,1)/4, not ProPhoto luminance. Its variance c^T Sigma c is24 in
squared RGB16 code units (0 for noiseless). Inject one constant actual variance
array and retain its f32 byte hash before/after each fold. The actual core white
BandGain is retained and explicitly passed as frame_beta for every fold; this
built-in deterministic operator probe is not physical noise calibration.

## Closed manifest

Top-level keys exactly schema, grid, color, noise, merge, inputs, output.
Schema: common-tiff-stack-v1. All objects reject duplicate/unknown fields;
arrays and types are strict, including three inputs and three covariance rows.

- grid: width128, height96, channels RGB, coordinates identity-common-rgb-pixels.
- color: space linear-prophoto-d50; icc FileRef.
- noise: model as above; units rgb16-code-squared; rgb_covariance3x3 zero or
  diag64; proxy_variance0 or24; band_transfer core-white-bandgain-v1.
- merge: bands3, gate2, exponent2, sharpen_per_octave1.4, select SoftPower,
  admission HardFloor, base Mean, mean_coarse0, hull InputRange, hull_lambda2,
  hull_low_only false, fallback Mean, fallback_k3, fallback_power4,
  hull_from_level1, significance_scale0.
- inputs: each has id, tiff FileRef, pixel_sha256, provenance. IDs are distinct
  bounded ASCII names. Provenance has exactly schema common-tiff-stack-input-v1,
  id matching the input, fixture_sha256, color_space linear-prophoto-d50,
  noise_model matching the declaration, geometry identity-common-rgb-pixels.
  The complete embedded ImageDescription is parsed as this exact JSON object.
  It is never admitted by a substring search. fixture_sha256 is a declaration
  bound by the independent fixture preparation; it is not a calibration proof.
- output: path, space linear-prophoto-d50, sample_format RGB16,
  quantization finite-clamp-round-half-away-v1.

FileRef keys are path, bytes, sha256. Input/profile relative paths resolve against
the manifest's directory; absolute paths are also allowed. Reject aliases,
duplicate input paths, output/report/input collisions, symlinks/reparse ancestry,
unbounded paths and unsupported geometry. Outputs must be fresh in an existing
plain directory. Declared source identities and actual command/binary are retained
in the report; root's release binds exact binary and source closure independently.

Manifest<=64KiB; each TIFF<=256KiB; profile exactly548 bytes with SHA256
16c8cad1299737e912d72ad83e959a9f879519a5fd2aaddb82ce103ebeca08ef
(the held M165 linearized ROMM/ProPhoto primaries D50 profile). This is linear
ProPhoto, not the standard encoded ProPhoto transfer. PROPHOTO_DISPROVED for the
previous fork remains unchanged. A valid ICC alone never proves pixel semantics.

The adapter authenticates one bounded open/read buffer and preflights its IFD for
unique LONG/count1 width128,height96 before calling CommonTiffFrame::parse.
This prevents its declared-payload preallocation from exceeding the fixed grid.
IFD offset/order and admitted strip layouts are not otherwise narrowed. The public
parser still enforces its exact13-tag uncompressed little-endian chunky RGB16
subset. Verify actual whole-file, payload, ICC and merge-facing hashes. Release
the encoded/decoded frame after its one fold; no future frame is loaded early.

## Output and observation

Use a new owned writer module, not camera Develop. Finite f32 already-RGB code
values are clamped0..65535, rounded half away from zero and encoded RGB16. Retain
per-channel low/high clip counts, prequantization f32 hash, interleaved u16 payload
hash, dimensions, exact ICC hash and whole-TIFF FileRef. No black subtraction,
WB, color matrix, demosaic, exposure, tone curve or transfer curve is applied.
TIFF description/software are fixed semantic strings independent of observer,
manifest filename, output path and receipt, so observer modes can be compared by
whole-file bytes. Embed the actual548 profile bytes as ICC UNDEFINED data. Pinned tiff0.11.3
(MIT) writes BitsPerSample16/16/16, SampleFormat1/1/1, Predictor1,
X/YResolution1/1 and ResolutionUnit1. Explicit PlanarConfiguration1 is added;
no alpha, orientation transform or viewing resolution is inferred. The host
must be little-endian. These output tags are not the strict13-tag input subset.

After each actual fold retain input identities, consumed plane/proxy/variance
hashes before/after, merge.frames(), on-mode raw averaged_fraction(), level sizes, and zero/positive
accumulated-denominator counts recovered from that actual core observation.
Off performs no gate census; placebo allocates four GateRow records without
reading the merge. On observes after each fold; final_gate reuses the third
observation rather than calling it again. These describe accumulated denominators, not per-frame threshold
decisions. The always-mean base is excluded from the independent gate-power bar.

The output observer is called once after finish on the same actual f32 planes
for all three modes. On hashes/visits actual samples; allocated-placebo allocates
the same population without observing samples; off records invocation only.
Mandatory output encoding/hashes remain common in all modes. Off/on/placebo must
preserve whole TIFF/pixel/input identities; this commissions these after-call diagnostics, not a hypothetical in-core hook.

## Terminal and finite bounds

A fresh durable incomplete receipt exists before manifest/data processing.
Three immutable per-frame receipts retain visited folds. A bounded final receipt
is written through a fresh same-directory stage and linked create-only to an absent final path; remove
only the owned stage after a successful hard link. Output uses the same
create-only publication. Unsupported hard links refuse without replacement. Refusals
retain completed prefixes and any orphan output, never silently overwrite or
admit an existing positive. A final positive alone is insufficient: exact outer
command/binary, actual exit0/no timeout, raw stdout/report identity and resource
closure are required by the independent runner/checker. No retries.

Fixed new per-invocation ceilings: TIFF128KiB plus simultaneous TIFF stage128KiB;
incomplete4KiB; three frame receipts16KiB each; final64KiB plus stage64KiB;
stdout64KiB; stderr16KiB; outer16KiB. Total632KiB; reserve1MiB. Source/input
fixtures and build scratch have separate finite phase allocations before release.

Three bands reach grids128x96,64x48,32x24,16x12 (sum16,320 sites).
Core accumulator187,968 f32 values plus FrameWorkspace196,608, finish Workspace
24,704, finish/reconstruction temporaries, one encoded TIFF, decoded u16 frame,
three f32 planes, proxy/variance and output buffers fit a conservative16MiB
explicit-data bound. This is DERIVED allocation reasoning, not a process peak
certificate. Core BandGain's32 deterministic256x256 realizations retain one
field plus work/pyramid buffers at a time. Pin a local Rayon pool to2 threads;
reject STREHL_/M194H_ overrides before constructing core state. Proposed actual
per-invocation backstop:15CPU/15wall/256MiB owned process, subject to root review.
Build/control aggregate reservations and fixed run count will be held alongside
the independent controller; there is no build/run authority in this document.

## Falsifiable fixed independent controls

The independent author owns fixtures and controls, without importing subject
implementation. Freeze exact population before execution:
three constant contributors must yield literal RGB(17000,23000,29000), never an
input; identical asymmetric coordinate/channel fields must survive exactly under
InputRange hull (address/color test, not reconstruction quality); a mixed flat/
textured +/-8 fixture must exercise both zero and positive accumulated
denominators among Laplacian levels, with variance24 actually injected. Wrong
variance1/noise provenance/profile/output space must refuse. Wrong or altered
third input must refuse after exactly two visited folds. Observer off/on/placebo
must preserve complete output/input identities. Same-size shift/channel/transfer
and changed-pixel metadata faults must defeat the corresponding independent
literal predicates. Any unexercised claimed branch is failure. No sharpness,
spatial-SD-as-temporal-noise, camera calibration or SOTA score is an admission bar.

Pass establishes bounded common-RGB software integration only. Failure closes
this version without widening geometry/population or relaxing a bar. Real
developed-RGB noise propagation, per-frame placement, and comparator semantics
remain unresolved; no P0 quality sweep/default change follows.

Source reader qualification: Windows byte consumption is authenticated by exact
SHA256/extent and stable size/mtime/attributes, with creation time stability
compared within each API family. No Windows inode/volume-ID proof or complete
hostile-filesystem model is claimed.
