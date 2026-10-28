# One forward arithmetic correction

2026-10-27. Continuation allocation
`raw-quality-2026-10-27-dual-tree-cfa-gpu-ordered-fir`.

Screen1 completed all cases in87.047s and refused the frozen stage-parity
limits. All original reconstruction checks, final output comparisons, noise
floor/weight comparisons, angular tests, historical quality flags and live
foils pass. Failures concentrate in coarse AC coefficients and level7 energy.
This is consistent with convolution reduction/FMA ordering, not causal proof.
Keep every failure and threshold; no RAW cost/full run is released by screen1.

Root authorizes one forward-only correction: independently written CUDA FIR
kernels must implement the CPU's tap-index order with explicit round-to-nearest
f32 multiply followed by f32 add, all seven levels and both axes. Keep the
current inverse, packing, filters, original-u16 probes, S5, weights and output
path unchanged. A patch limited to failed coarse levels would retain upstream
rounding differences and is not selected. No tolerance expansion or parameter
sweep. cfa-residual owns the kernel/helper and worker edit; integration-review
audits addressing, bindings and runtime; photo-review retains frozen controls.
Root alone schedules execution under the unchanged120s/8GiB/24GiB screen and
300s/14GiB/24GiB source-cost limits.

For practical launch cost, use the already installed NVRTC library with a small
independently authored CUDA source, rather than creating dozens of temporary
tensors per tap. Root's read-only inventory found `nvrtc64_120_0.dll` and
`nvrtc-builtins64_128.dll` in the installed Torch lib directory. This is not a
successful compilation or runtime observation. Record actual NVRTC/driver
version, source and library hashes, compiler options, PTX/cubin hash and current
Torch stream. No external install, copied vendor algorithm, f64 image arithmetic,
fast-math, FMA contraction, atomics or hidden backend fallback. Refuse compiler
or launch failure. Keep allocated tensors under the existing Torch memory cap;
compiled module memory is separately disclosed rather than called allocator
memory. No new CUDA context or detached process.

Prior lookup actually run: `research.py search --any NVRTC "tap order"` and
`experiments/ORCH-drift-check/prior_art.py NVRTC`; the latter points to
[D-rust-and-hardware](../../../docs/research/D-rust-and-hardware.md), whose old
Rust-wrapper survey does not establish current library availability. The root
read the official [NVRTC API documentation](https://docs.nvidia.com/cuda/nvrtc/index.html)
for runtime compilation/driver-loading APIs. Do not infer installed API support
from a newer web version; query the installed library and bind it.

Preserve build1 and first server bytes before editing. A Python/kernel-only
revision may reuse the existing frozen Rust executable only after verifying
every compiled Rust/Cargo input unchanged and creating a new immutable revision
manifest binding the changed runtime source. This is explicitly a runtime
rebind, not a fresh Rust build. AST/compile checks and the entire unchanged
screen must run again; passing intermediate arithmetic alone is insufficient.
If this correction fails, retain the failed result and reconsider before more
implementation. No photographic or competitive-speed claim is made here.
