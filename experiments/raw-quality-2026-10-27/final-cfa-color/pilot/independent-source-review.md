# Independent source review before execution

2026-10-27. **SOURCE-VERIFIED / NOT EXECUTED.** No numerical module was imported,
no GPU/RAW/build/export job was started, and no running spectral-pilot or shared
Rust/Cargo file was edited. This reviewer authored the controls; the producing
operator author separately reviewed their direct reference and API usage.

No remaining source-level blocker was found for the root's bounded sequence,
after the active full299 job has completed cleanly. This is not a passed
mechanical screen or a photographic admission.

| Reviewed file | SHA256 |
| --- | --- |
| spectral-completion.py | `4ff4e1db4c7cbb3dfee835d8bc653a08eff4df070e2fd8a90dc6bfea8cec32d7` |
| controls.py | `cc451fba76287c7975dba85cabd41f56802b2bf124e4546967e5afc2ce133f75` |
| controls-protocol.md | `6c393c989acbf1a7667a161773122a7bd0e03354bc674552f582c2eda43ffc8a` |
| normalized-camera-develop.rs | `6b2b94aa74b7b3b94c67448740e59286f81c64170e555c6a98e9a839b076826e` |
| saved-field.py | `3f595de6156d37600cc6f48d0f312c84c1088c9a4661f7a19bb545ee4a81a2a9` |
| views.py | `cf5baf1b36d20c251552bcc9d1796bb9f6be36d433eef14ae47ac722e2d6ac7d` |
| run.py | `33ed757cfcb069ade79eb1648ed9d7268d6f5295dcb161dc1f8b239570683127` |

## Producing operator and writer

The three custom CUDA signatures match their ctypes argument lists. Counts and
frequency products use 64-bit integers; shape/origin validation bounds the
remaining indices. The kernels use the existing Torch context and current
stream and record tensor lifetimes. The private pinned runtime composition
retains precise compiler options and its no-FMA guard. This review does not
predict whether the first NVRTC startup or an exact full-size FFT will succeed.

Reflection uses `2(n-1)` periods without endpoint duplication. The source color
is selected at reflected physical sites, including both green phases. Masks
use literal integer quarter-axis/diamond boundary comparisons. The orthonormal
real FFT and inverse preserve f32/complex64; the pre-restoration field is
observed before known values are restored. No extra aperture inverse, color
coupling, input-derived noise model or tiled fallback is introduced.

The normalization kernel is the explicit native `max0 * gain * 1 / range`
sequence, including rounded f32 division. The new writer accepts actual signed
normalized camera RGB, copies its bytes, and applies the existing matrix,
highlight/tone and native TIFF paths. It performs no input clamp, WB/range
normalization, MHC or remosaic. The mandatory held-camera null must establish
full RGB16/linear pixels and material metadata before any new completion result
is used. Source inspection alone does not replace that null.

## Controls and actual-field joins

The [protocol](controls-protocol.md) fixes the tolerances and two-sided quality
flags. Constants and the two saved noisy flats precede detail cases; all twenty
saved CFA fields remain. A small independent full f64 DFT commissions missing
sites, all origin parities, exact boundary masks and center/edge impulses.
The actual producer foils reach the same transform and scorer. Known-site
identity does not substitute for these tests. The exact same-input/two-truth
ambiguity stays descriptive, without an impossible universal pass requirement.

The full saved-field driver binds the original CFA, MHC camera/master chain,
held null, executable, profile and runtime helper before construction, then
rehashes inputs afterward. Its per-color pre-restoration guard uses the same
prospective normalized scale-relative bars as controls. It saves finite fields
and guard results before refusing a failed null. The exact-site overwrite
cannot itself authorize delivery. Four CPU/one interop threads are explicit;
full-field timing uses QPC via `perf_counter`.

Views validate both candidate/uniform same-CFA pairs, native dimensions/origin,
actual completion evidence, pre-restoration pass, owned camera/master paths,
held development and material identity. They deliver four complete JPEGs and
forty fixed native384 PNGs with identical ICC and rounded RGB16-to-8 conversion.
The source-generation and clean-process claim remains root-owned; it is not
inferred from a readable image. Helicon references retain their distinct gauge
and development caveats.

## Root wrapper and practical limits

The wrapper refuses every stage until the current spectral full299 receipt and
owned process are complete and clean. Its build/null/controls/cost/saved-field
arguments match the actual sources. The narrow cached build recovery requires
successful fresh Cargo compilation and direct exit/EOF before the documented
owned-descendant timeout; it is not a generic retry of a failed compiler.
The original process record remains preserved.

Controls follow the exact writer null. Cost requires `controls_pass` and an
identical numerical dependency manifest; candidate/uniform additionally require
the clean full-shape cost with that same manifest. All use fresh output paths
and post-job binding checks. Quality failures remain recorded rather than
being relabeled as mechanics failures or photographic success.

The cost field has the real 6896x4596 input and 13790x9190 FFT extension, so it
can expose planning/workspace failures that the tiny reference cannot. Torch's
8-GiB allocator/reservation cap does not measure every CUDA driver/FFT-plan
allocation; root's process/device accounting remains necessary. No claim about
actual runtime, total memory, ringing, neutral/color tradeoffs or photographic
gain is made before execution and complete-image review.

## Prospective six-arm presentation follow-up

**SOURCE-VERIFIED / NOT EXECUTED.** The earlier four-arm presentation description
above records the prior checkpoint. The following reviewed update supersedes
only that presentation population; operator, controls, writer and saved-field
driver hashes remain unchanged.

| Updated file | SHA256 |
| --- | --- |
| run-delivery.py | `aa56e4ca071f30243c1888d27ee112383883859ae1b73c680d3936523840ec85` |
| views.py | `da27880dc4d690df275b65594dd39e0ffe2532fa9a347b9549c5feafcc8e5117` |
| brief.md | `9318ea9b0fa3bd25382d2058a4fa2fb8e903c4027553b88231eea4a5bc5b3ae9` |
| delivery-notes.md | `b26c4b0a230d9c120fe9f39d3853d81bfbd2b1cb684da52d41a67a88e6897f77` |

No remaining source-level blocker was found. The root wrapper requires the
clean complete spectral run and clean candidate, uniform, cost and null jobs,
rehashes their completed report artifacts, and requires each saved-field job's
numerical manifest to match the current sources. The cost source is identified
with `Path.samefile`, then checked against the pinned held CFA, actual MHC
camera, RGB16 pixels and linear pixels. This handles Windows extended-path
aliases without weakening content identity. All inputs and prerequisite
receipts remain bound through the presentation job.

The exporter requires `--held-receipt` and verifies that its MHC source is the
same actual receipt supplying the commissioned null. The paired CFA identity,
pre-restoration pass, owned native output, exact writer executable and common
development/material checks apply to all three pairs. Six distinct master
paths are required in the fixed order held-MHC/color, candidate-MHC/color,
uniform-MHC/color. The existing ten witnesses are exported for every arm:
six full-size JPEGs and sixty exact unresized 384-pixel PNGs, using the same
rounded conversion and ICC/readback checks. No additional completion job,
crop selection, registration or tone estimation is added.

The held pair isolates the final completion change on the usable native
baseline. The other pairs retain their respective upstream fusion effects;
the six-arm layout does not erase those differences or the Helicon gauge and
development confounds. Clean execution, actual memory cost, photographic
appearance and source-population qualification remain pending root execution
and independent review. AST parsing and source hashes were checked without
importing or executing numerical modules.
