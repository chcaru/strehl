# Coupled pupil kernel: installed runtime and minimal bridge

**VERIFIED FILE INVENTORY, not a compile/runtime test (2026-09-20).** The active
Python executable found by `Get-Command python` is
`C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe`.
Its `Lib\site-packages\torch\version.py` declares **2.11.0+cu128 / CUDA12.8**.
Under that same Python directory, `Lib\site-packages\torch\lib\` contains:

| File | Bytes | Intended use, not yet exercised |
| --- | ---: | --- |
| nvrtc64_120_0.dll | 86,728,192 | Runtime CUDA source compilation |
| nvrtc-builtins64_128.dll | 6,356,480 | Matching compiler builtins |
| cudart64_12.dll | 573,952 | Torch's CUDA runtime |
| nvJitLink_120_0.dll | 77,860,352 | Present; unnecessary for a self-contained kernel |
| caffe2_nvrtc.dll | 17,920 | Present; no need to depend on this private shim |

The CUDA driver DLL is `C:\Windows\System32\nvcuda.dll`, 4,714,728 bytes,
file version32.0.16.1062. `Get-Command nvcc` found nothing; the conventional
NVIDIA toolkit directory was absent. The Torch include inventory did not show
public `nvrtc.h`/`cuda_runtime.h`/driver `cuda.h` headers. This supports trying
the bundled runtime compiler, not a conventional compiled Torch C++ extension.
DLL presence does not establish exported symbols, dependency loading, supported
GPU targets, successful PTX JIT or interoperability. None was tested here.

**Plausible smallest bridge.** A small Python `ctypes` wrapper can load the
absolute NVRTC path (keep an `os.add_dll_directory(torch/lib)` handle alive),
declare the used C ABI prototypes, compile one header-free CUDA source string
with `nvrtcCreateProgram/CompileProgram/GetPTX`, then load/launch through
`cuModuleLoadDataEx/cuModuleGetFunction/cuLaunchKernel` from nvcuda. No nvcc,
MSVC, package installation or runtime download should be necessary for simple
float/int arithmetic kernels. Use the current device's supported architecture,
retain the compiler log and explicit error checks; do not assume compatibility
from DLL names. Keep fast-math off and commission any f32 association changes.
This is an **unexecuted API proposal**, not an available-performance claim.

Expose `joint_pupil(near,far,alpha,table)->RGB` as one `torch.autograd.Function`.
Inputs are same-device contiguous f32 HWC/HW tensors, fixed integer offsets and
f32 weights. Save latent tensors/table for backward; allocate outputs and
gradients with Torch. The existing PyTorch PSF and CFA operations remain outside
the custom function. Return no focus/depth/table derivatives and explicitly
refuse higher-order differentiation initially. The first commission is the
fixed64 table against the retained operator and independent finite differences;
dense-pupil accuracy follows separately, before fitting anything.

**Atomic-free adjoint (DERIVED).** Let `e[x,c]` be the incoming RGB derivative,
`U_p=sum_q J_pq`, and use the exact coupled forward from pupil-stencil-design:

`Y_x = sum_p U_p a[x+p] N[x+p] + sum_pq J_pq (1-a[x+p]) F[x+q]`.

For each valid input pixel z, gather rather than scatter:

`dN[z,c] = a[z] sum_p U_p e[z-p,c]`

`dF[z,c] = sum_pq J_pq (1-a[z+p-q]) e[z-q,c]`

`da[z] = sum_c N[z,c] sum_p U_p e[z-p,c]`
`         - sum_pq,c J_pq F[z+q-p,c] e[z-p,c]`.

One thread owns each output/gradient element, with fixed table reduction order;
no atomic scatter or `[table_entries,H,W,channels]` intermediate is required.
The scalar alpha gradient sums all three colours. Work remains O(HW|J|), with
two joint-table traversals for far/alpha gradients plus the marginal work;
memory is O(HW+|J|) per live observation. The earlier conservative2704-entry
bound is an operation estimate, not evidence this beats1024-ray grid_sample.

**Boundary and stream hazards.** Zero-extend N/F/alpha and incoming e exactly.
An out-of-array near alpha is0, hence transmission is1: do **not** discard a
joint far contribution merely because its near address is outside. Differentiated
variables outside the array do not exist. Keep the original supported crop and
common PSF apron. Translation-invariant stencil arithmetic differs slightly
from position-dependent normalized-grid f32 rounding; no bit-identity promise.

Use Torch's already initialized current CUDA context and launch on
`torch.cuda.current_stream(tensor.device).cuda_stream`; the installed Python
API exposes both this accessor and the stream handle. Do not create a second
driver context or silently launch on the default stream. Retain module/table
and tensor lifetimes through asynchronous use; use the appropriate Torch stream
recording when lifetime crosses streams. A commissioning synchronization can
localize launch errors, but unconditional production synchronization would alter
performance. CUDA graph capture, multiple devices, noncontiguous strides and
double backward should be explicit initial refusals. No kernel implementation,
DLL loading, compilation, fitting or timing was performed for this inventory.
