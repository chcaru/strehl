# Conditional probe acceleration recommendation

2026-10-27. Source/receipt audit only. No implementation, execution, RAW access
or speed/quality claim. Proceed only if the complete dual-tree photographs
justify retaining that consumer.

**ARGUED smallest faithful route:** retain all sixteen existing CPU-generated
original-u16 draws and replace only their callback's full-color CPU remosaic
with the existing Device256 MHC/Catmull remosaic, then use the unchanged
`extract_planes` and CUDA wire. Use one persistent, explicitly owned
`GpuGather::new_with_schedule(Device256)` in a test-only callback. Keep the
canonical CPU route and its global `STREHL_GPU_GATHER=off` contract unchanged;
do not toggle the cached process-global environment. Do not begin with a CUDA
gather rewrite, RNG port, direct-plane replacement or graphics/CUDA interop.

## What the measured interval contains

The retained [source149 receipt](../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-cost-1/output/receipt.json)
records **MEASURED** `probe_prepare_and_gather_seconds=8.5464554`, separately
`original_variance_seconds=0.1082384` and
`wire_and_synchronized_cuda_seconds=2.1586134`. The latter includes signal and
end-source exchanges as well as probes. These are one-source wall intervals,
not isolated kernel times or a repeated speed comparison.

The producing timer in `dual-tree-cfa-gpu/bridge.rs::add_source` encloses, for
each draw: `noisy_source`, the complete gather callback, dropping the temporary
source, and four-plane finite/shape validation. It excludes the subsequent
serialization, pipe transfer, CUDA upload/transform and synchronized response.
The current callback in `dual-tree-cfa/full-adapter.rs` clones the noisy frame,
allocates four cropped planes and a new `WarpScratch`, performs full-resolution
CPU MHC/Catmull/quantizing remosaic, then calls actual `extract_planes`.
Full RGB reconstruction is one source at a time; there is no aligned volume.

`boundary-cfa-wavelet/probe.rs` computes original variances once per source.
Each draw clones a normals frame, fills its complete active quads, clones the
output frame, validates variances, recomputes each site's f32 square root,
scales the quantized normal and rounds into u16 with headroom refusals. The
normal generator is the retained CPU SplitMix64/Box-Muller implementation,
already row-parallel and active-relative; its internal transcendental work is
f64 before u16 quantization. Preserve it byte-for-byte rather than silently
replacing it with CUDA f32 normals. The receipt does **not** separate this
preparation from reconstruction, allocation or gather. Therefore 8.5464554s
is not an available gather-only saving, and Device256's benefit here is unknown.

## Exact reuse boundary

Device256 already accepts original u16 storage/active rectangle, black, WB and
inverse WB, three composed pulls, Malvar and Catmull. With `green_only=false`
it reconstructs source RGB, constructs coordinates on device, gathers all
physical CFA sites, quantizes into packed u16 and returns coverage. Preserve
that packed remosaic/writeback and the existing cropped extraction, including
`max(code-black,0)`, reference coordinates and CA-off profile checks. Reuse the
existing input construction/writeback helpers through a narrow test seam;
do not duplicate a second WB, phase or quantization policy.

[Device256 results](../../native-gpu-gather/device-results.md) retain exact
complete-image and independent descriptor/rounding controls for earlier
inputs, including full-color calls. They are prior support for this reuse,
not proof for these sixteen noisy fields. Its finite f64 coordinate domain,
strict shader arithmetic and explicit Parallel256 coordinate fallback remain
load-bearing; record actual schedule/fallback rather than labeling every call
Device256. Unsupported image/device configurations must still refuse.

[Green-probe specialization](../../native-green-probe/results.md) saves unused
R/B outputs for the canonical green guide. Here every CFA phase contributes
complex energy and pair-difference variance, so that omission is invalid.
The old M7 resident focus-volume timing concerns another operator and supplies
no cost estimate. [M194c verification](../../m194c-probe-layout/independent-report.md)
requires active-relative RNG traversal, unchanged padding/odd tails, correct
per-frame lifecycle and live seed/WB/warp effects; preserve those constraints.

## Required release evidence

1. Keep original source IDs, the exact sixteen seeds and independent pair order,
   injected variance bytes and every noisy u16 sample identical to the frozen
   CPU path. No reduced draw count, cached previous-source floor or antithetic
   substitution. Compare all four gathered planes against the existing CPU
   callback, first on bounded fractional-translation/scale/rotation and
   active-origin/boundary controls, then all sixteen full source149 draws.
   Source149 alone is an almost-identity pull and cannot qualify general warps.
2. Reuse the independent Device256 coordinate/coverage/rounding falsifiers and
   live red/blue-source impulses. A wrong phase/coordinate or dropped color
   must fail equality; padding relocation must not change consumed probes.
   Through the actual frozen CUDA consumer, retain flat-first controls,
   positive selected-weight cases, uniform/single-source nulls and all original
   quality failures. Require unchanged coefficients/floors/weights/output for
   equal delivered probe fields; do not invent new tolerances to admit a
   changed noise law. Preserve canonical complete-output goldens.
3. Only after parity, measure the same complete source/probe/finish path in
   alternating CPU-callback/Device256-callback order with four CPU workers,
   host load, synchronized endpoints and exact worker/build/runtime bindings.
   Separate probe generation from gather in that later receipt. A useful
   acceleration must preserve the complete rendered master and metadata,
   not merely satisfy a coefficient or timing score.

Device256 is wgpu, not a Torch CUDA tensor producer: it uploads packed u16,
returns packed samples to host, then the existing wire uploads cropped f32.
Those transfers and per-call allocation remain. Its source RGB/staging and
driver allocations coexist with CUDA coefficient state and are outside the
Torch allocator cap. Check combined device and host high-water use and adapter
identity; do not claim zero-copy or use old isolated wgpu memory figures as the
combined bound. Keep one source/draw live and no cross-source/probe volume.

The prior lookup commands are recorded in the brief. This audit used scoped
`rg` searches and reads of the cited reports, receipt and producing Rust code;
it performed no image calculation. The ongoing full-photo result remains the
decision point before any of this conditional work is implemented.
