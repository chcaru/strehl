# Fixed-pupil coupled stencil commissioning

Prospective numerical experiment only. The author writes source; root compiles
and runs the independently authored controls. No optimizer, RAW decode, real
photograph, production integration or quality/speed claim belongs to this test.
All older model, fitter and observation files remain frozen. There is no author
CLI: the independent controls import `pupil-stencil.py` and own their `--out` run.

**Setup and fixed operator.** `build_table(pupil_xy,near_shift,far_shift)` accepts
1..16384 explicit finite equal-weight points in the unit disc, supplied shifts
bounded to24 native pixels, and aggregates the16 products of bilinear weights
for each same ray in f64. Group integer `(px,py,qx,qy)` tuples and store positive
f32 joint weights J, without renormalization. The near marginal U is accumulated
from the stored joint weights in f64 then rounded to f32. Table mass/array hashes,
ray count, shifts, entry count and byte size are exposed in metadata. CPU setup
uses O(rays) scratch; image kernels and their GPU tables use O(image+entries).
Dense4096/16384 quadrature changes setup accuracy, not a ray-sized image volume.

The pre-PSF forward is `sum_p U_p*(a*N)[x+p] +
sum_pq J_pq*(1-a[x+p])*F[x+q]`. It preserves premultiplication and shared-ray
visibility. Replacing J by outer marginals is a wrong operator. A header-free
CUDA kernel assigns one complete RGB output pixel to each thread and reduces
entries in fixed order. The backward kernel similarly owns one input pixel,
gathering each near/far RGB derivative and the shared scalar-alpha derivative.
No atomics or `[entries,H,W,channels]` intermediate occurs. All images and GPU
tables use f32 (indices int32); no half precision or fast math. The original
frozen `_blur` supplies the common PSF outside the custom autograd function;
the independent caller applies original CFA/black conventions when required.

Zero-extend latent samples and upstream derivatives. Outside alpha=0 means
transmission=1, so a valid far contribution survives an out-of-range near address.
Do not crop intermediate fields before convolution or scoring. The fixed
supported interior remains the authority for optical comparisons. Aggregated
weights are mathematically equivalent to a discrete pupil, but cannot be
bit-identical to normalized-coordinate grid_sample rounding at every position.
Use independently specified finite tolerances, not a claim of exact floats.

**Runtime and ABI.** The installed Torch NVRTC DLL and its builtins are loaded
from Torch's absolute library directory; the driver uses System32/nvcuda.dll.
Windows x64 only. All used function argument/return types are declared with
ctypes; kernel arguments are host pointers to their typed values. NVRTC compiles
to PTX for the exact current GPU architecture after querying supported targets,
with fmad/flush-to-zero disabled, precise division/sqrt and no fast-math option.
Compiler errors include the compile log. CUDA driver errors are checked; the
first version also checks finite outputs/gradients, which synchronizes and is
not a performance implementation. PTX/source/options/runtime metadata is retained.

NVIDIA's [NVRTC12.8 API](https://docs.nvidia.com/cuda/archive/12.8.0/nvrtc/index.html)
documents the create/compile/log/PTX/destroy and architecture-query signatures,
and runtime compilation without toolkit headers. The [driver module API](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-driver-api/group__CUDA__MODULE.html)
documents PTX module loading and function lookup; [execution control](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-driver-api/group__CUDA__EXEC.html)
defines `cuLaunchKernel` and its pointer-to-argument array. [Context management](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-driver-api/group__CUDA__CTX.html)
defines current-context/device queries. These public primary docs informed the
ABI; DLL loading and compilation remain unexecuted by the author.

Use Torch's existing current context/device and actual current stream, never
create another context. Refuse a later context/device change and CUDA graph
capture. Keep module/DLL handles alive for the process, save tensors/tables for
backward and record stream use to protect allocator lifetimes. Require contiguous
CUDAf32 inputs on the current device, native1..96 extents and finite radiance/
coverage. No higher-order differentiation, learned table, depth or optics
gradients are supported. The original model source hash is checked on import.

**Independent sequence and refusal power.** First commission fixed64 rays
against the frozen Torch forward and autograd, an independently enumerated
same-ray bilinear operator and small signed finite-difference directions.
Use constants, impulses, alpha endpoints, nonconstant near/far overlap, sensor
boundaries, odd rectangular dimensions and a non-default Torch stream. The
separate-marginal wrong-visibility operator and wrong-sign/offset adjoint must
be detectable. Invalid inputs/context/capture/higher-order requests must refuse.
No larger numerical-integration claim follows if this stage fails.

Only then evaluate the prospectively fixed candidate: independently supplied
equal-area polar128x128 (16384 points), angular phase0.23 radians. It must meet
the unchanged .75-noise-sigma whole/crossing adequacy bar at focus indices
0,2,4,6,8 against BOTH polar64x64 phase0.23 (4096 points) and polar128x128
phase0.60. Original64, golden-angle1024 and polar1024 are diagnostic comparators,
not vetoes for the fixed candidate and not truth. No density or rotation is
selected after results. Numerical self-consistency and operator mechanics are
separate decisions, and neither makes the finite references physical truth.
Report table sizes and allocator memory without claiming an end-to-end speedup.
A failed bar does not license an optimizer run, an optics claim or an unbounded
density/parameter search.
