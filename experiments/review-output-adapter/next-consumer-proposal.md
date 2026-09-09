# Next common-TIFF consumer: a bounded three-frame RGB render

2026-09-08. SOURCE-READ findings; ARGUED, UNRUN proposal. No code, build, image,
metric or render execution. This continues [audit.md](audit.md), outside the held
M194h closure; no default, gate, milestone or grant changes.

Build an explicit manifest-driven common-TIFF **stack-to-image** mode, first
commissioned on three known-grid synthetic inputs, with declared RGB noise and
accurately tagged RGB16 output. Another one-frame receipt repeats M165. A pass
would establish software integration, not physical calibration or quality.

## Existing path and the actual gap

| Existing source | What it does; what remains missing |
|---|---|
| `strehl-cli/src/main.rs::raw_paths` (1199) | Native stack enumerates and sorts only `.arw`. Adding TIFF extensions here would still send RGB through a CFA-specific consumer. |
| `strehl-cli/src/bin/strehl-common-input.rs::run`, `exercise_core_merge` (43, 137) | Separate binary accepts one TIFF and expected hashes, verifies actual merge-facing samples, optionally folds one frame through three-plane `BandMerge`, checks finite shape, discards the result and writes JSON. Its selection proxy is `(R+2G+B)/4`; variance is the literal placeholder `1.0`. |
| `strehl-raw/src/common_tiff.rs::parse/verify/merge_planes` | Strict uncompressed chunky RGB16, exact identities and lossless u16-to-f32 code values. No color transform. `read` uses `fs::read`: cap bytes before allocating and parse the authenticated buffer. |
| `strehl-core/src/pyramid.rs::BandMerge::add_frame_with_gain` | Generic plane count already permits RGB. The caller supplies selection values, their level-zero variance and optional band transfer. This is the integration seam; no new merge algorithm is required. |
| `strehl-cli/src/image_out.rs::write_rgb16_described` (603), `OutputSpace` (850) | Writer semantics are CameraLinear, linear-sRGB/D65 or encoded sRGB. No existing mode means already-linear ProPhoto/D50. The native writer's development options cannot truthfully label this input by substitution. |

Table paths are under `crates/`. M193c has since commissioned the native
output-grid path proposed in the older audit; do not repeat it. Real geometry
remains unqualified: zero returned fit edges; 106 local translations alongside
4 agreeing, 17 disagreeing and 11 unavailable disjoint-window groups.

## Color and noise are separate authority requirements

M165's custom **linearized ProPhoto/ROMM-primaries D50** is not standard encoded
ProPhoto. Its tested producer was D50-compatible; the required retained fork
ignored the profile and used another transfer/output-space contract.
`PROPHOTO_DISPROVED` remains. Correct Strehl output would not repair that fork.

Admit the held profile and converter/fixture identity; retain RGB16 code units.
Do not repeat black subtraction, WB, camera matrix, demosaic, exposure or transfer
curve. The parser retains an ICC digest; bind the actual profile bytes supplied
to the new writer. An ICC signature cannot prove producer pixel semantics.

Inject noise once at this boundary. Raw-CFA gain/read noise cannot be copied to
developed RGB: demosaic, WB, matrix, clipping and resampling change covariance.
Identity geometry does not make developed RGB white; white `BandGain` is not
automatically valid.

Name `c=(1,2,1)/4` a selection proxy, not ProPhoto luminance. Its variance is
`c^T Sigma_RGB c` in squared RGB16 code units. Freeze variance/band-transfer
inputs and provenance; never estimate noise privately per stage or obtain it
from the energy its own gate tests. Normalization needs squared unit conversion.

First admit simulation-only independent additive RGB code noise with a known
law, plus a noiseless null. Unknown developed-RGB noise stays unsupported, with
no variance=1 fallback. This validates an operator, not camera calibration.
A real-input release needs evidenced conversion/noise propagation; M189's
covariance and adaptive-processing limitations apply.

## Smallest production integration to propose for review

Add a stack-manifest mode, mutually exclusive with the old single-file command:

1. Read a closed manifest: ordered input identities, common RGB grid, profile,
   noise provenance, explicit settings and output. Bind executable/invocation;
   reject duplicates, unknown fields and unsupported geometry.
2. Authenticate and parse one TIFF buffer, verify actual input-plane identity,
   fold once into persistent three-plane `BandMerge`, then release the frame.
   Reuse one workspace: u16 decoded storage, f32 arithmetic, no aligned stack.
3. Finish once and encode already-RGB with the bound profile. Separate this
   declaration from camera `Develop`; reuse TIFF encoding without native
   demosaic. Freeze nonfinite handling, clipping and u16 rounding; report clips.
4. Bind the pre-output plan to actual dimensions, payload, ICC, whole file and
   complete consumed population. Independently parse the output; strict M165
   input parsing is not general output parsing. Retain refusals/visited prefixes
   and reserve terminal space. Reuse commissioned process/receipt machinery.

First release: three 128x96 synthetic frames, three bands, fully explicit frozen
HardFloor settings, identity in the **common RGB pixel gauge**. No CFA half-grid
conversion, crop, scale, rotation, fit or sidecar. Source-derived allocation/file
bounds and an independent finite release precede execution; no existing native
memory certificate transfers to this consumer.

## Fixed controls that can reject the integration

Use existing M165 synthetic construction conventions, no external corpus.
Freeze these new multi-frame/writer controls before building:

| Control | Positive evidence and fixed failure it must expose |
|---|---|
| Three actual contributors | Constant RGB frames (12000,17000,23000), (15000,20000,26000), (24000,32000,38000) must emit (17000,23000,29000) on the declared mean/fallback path. No input equals this answer. Independent literal arithmetic detects a copied reference/last frame, omitted frame or duplicate fold; also require all three actual contribution receipts. |
| Address and color preservation | Three identical asymmetric coordinate/channel-coded frames, with interior constant color witnesses. Independently calculate grid locations and literal flat-region codes; predeclare the textured reconstruction/rounding bound from the frozen operator. A same-size one-pixel shift, channel permutation or second transfer curve must fail. Inspect actual output ICC and development receipt, not just dimensions. |
| Noise injection and actual gate use | For an unclipped independent per-channel +/-8-code fixture, the generating channel variance is 64 and proxy variance is 24 (DERIVED, not measured calibration). Verify the actual injected arrays and band inputs. Substituting the old variance=1 must be rejected. Include a fixed mixed flat/textured fixture and require both below-floor and above-floor participation; an unexercised gate is a failed control. Do not count the model's algebra as independent validation of camera noise. |
| Model/semantic refusal | Same bytes with an unadmitted noise provenance, wrong profile or camera-native output declaration must refuse, even if a descriptive receipt is rehashed. A syntactically valid ICC is insufficient authority. |
| Partial population | Substitute a wrong-sized or altered third file after two valid inputs. The run must retain the exact visited prefix and refuse final admission; an existing output or positive child record cannot certify all three frames. |
| Observer nonperturbation | Run the fixed positive through the exact output receipt observer off/on/allocated-placebo. Require identical whole-TIFF and pixel hashes and unchanged input hashes; preserve all outcomes. A changed-pixel destroyer must be detected by the same comparison. |

The independent verifier uses literal pixel oracles and inspects serialized
color/noise inputs. No sharpness, spatial-SD-as-temporal-noise or SOTA score is
proposed. Apparent detail gain cannot serve as software admission.

## Decision after the bounded integration

Failure closes this version without a larger campaign or relaxed bar. Passing
permits bounded common-RGB software use; physical noise, per-frame placement and
comparator semantics remain open. Nonidentity geometry first needs a consumer,
gauge, interpolation/noise contract and independent known-map truth.

This adds the missing consumer for either M194h outcome, preserving its merge
policy and completed matrix. Sources read: SYNTHESIS 3.1-3.3, M165 verdict and
residual doubts, M189 4.3-4.4, prior output audit, current SOTA program and the
Rust symbols above. No historical result was independently rerun.
